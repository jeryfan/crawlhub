import json
import logging
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import func, select

from models.crawlhub import SpiderTask, SpiderTaskStatus
from models.crawlhub.alert_rule import AlertRule, AlertRuleType
from models.crawlhub.notification_channel import NotificationChannelConfig
from models.engine import TaskSessionLocal, run_async
from services.crawlhub.notification_service import NotificationService

logger = logging.getLogger(__name__)


@shared_task
def evaluate_alert_rules():
    """定时评估告警规则"""
    run_async(_evaluate_alert_rules())


async def _evaluate_alert_rules():
    now = datetime.utcnow()

    async with TaskSessionLocal() as session:
        # 查询所有启用的告警规则
        result = await session.execute(
            select(AlertRule).where(AlertRule.is_enabled == True)
        )
        rules = list(result.scalars().all())

        for rule in rules:
            try:
                # 检查冷却期
                if rule.last_triggered_at:
                    cooldown_end = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
                    if now < cooldown_end:
                        continue

                condition = json.loads(rule.condition) if isinstance(rule.condition, str) else rule.condition
                triggered = False
                alert_message = ""

                match rule.rule_type:
                    case AlertRuleType.TASK_FAILURE_RATE:
                        triggered, alert_message = await _check_task_failure_rate(
                            session, condition, rule.spider_id, now
                        )
                    case AlertRuleType.TASK_DURATION:
                        triggered, alert_message = await _check_task_duration(
                            session, condition, rule.spider_id, now
                        )
                    case AlertRuleType.ITEMS_COUNT:
                        triggered, alert_message = await _check_items_count(
                            session, condition, rule.spider_id, now
                        )
                    case AlertRuleType.HEARTBEAT_TIMEOUT:
                        triggered, alert_message = await _check_heartbeat_timeout(
                            session, condition, rule.spider_id, now
                        )

                if triggered:
                    rule.last_triggered_at = now
                    await session.commit()

                    # 加载通知渠道并发送
                    if rule.notification_channel_id:
                        ch_result = await session.execute(
                            select(NotificationChannelConfig).where(
                                NotificationChannelConfig.id == rule.notification_channel_id
                            )
                        )
                        channel = ch_result.scalar_one_or_none()
                        if channel and channel.is_enabled:
                            notification_service = NotificationService(session)
                            await notification_service.send(
                                channel=channel,
                                title=f"告警: {rule.name}",
                                message=alert_message,
                            )

            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule.id} ({rule.name}): {e}")


async def _check_task_failure_rate(
    session, condition: dict, spider_id: str | None, now: datetime
) -> tuple[bool, str]:
    """检查任务失败率"""
    threshold = condition.get("threshold", 0.5)
    window_minutes = condition.get("window_minutes", 30)
    window_start = now - timedelta(minutes=window_minutes)

    # 查询时间窗口内的总任务数
    total_query = select(func.count()).select_from(
        select(SpiderTask).where(
            SpiderTask.created_at >= window_start,
            SpiderTask.status.in_([SpiderTaskStatus.COMPLETED, SpiderTaskStatus.FAILED]),
        ).subquery()
    )
    if spider_id:
        total_query = select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.created_at >= window_start,
                SpiderTask.spider_id == spider_id,
                SpiderTask.status.in_([SpiderTaskStatus.COMPLETED, SpiderTaskStatus.FAILED]),
            ).subquery()
        )
    total = await session.scalar(total_query) or 0

    if total == 0:
        return False, ""

    # 查询失败任务数
    failed_query = select(func.count()).select_from(
        select(SpiderTask).where(
            SpiderTask.created_at >= window_start,
            SpiderTask.status == SpiderTaskStatus.FAILED,
        ).subquery()
    )
    if spider_id:
        failed_query = select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.created_at >= window_start,
                SpiderTask.spider_id == spider_id,
                SpiderTask.status == SpiderTaskStatus.FAILED,
            ).subquery()
        )
    failed = await session.scalar(failed_query) or 0

    rate = failed / total
    if rate > threshold:
        return True, (
            f"任务失败率过高: {rate:.1%} (阈值: {threshold:.1%})，"
            f"过去 {window_minutes} 分钟内 {failed}/{total} 个任务失败"
        )
    return False, ""


async def _check_task_duration(
    session, condition: dict, spider_id: str | None, now: datetime
) -> tuple[bool, str]:
    """检查任务执行时长"""
    max_duration_seconds = condition.get("max_duration_seconds", 3600)
    window_minutes = condition.get("window_minutes", 60)
    window_start = now - timedelta(minutes=window_minutes)

    query = select(SpiderTask).where(
        SpiderTask.created_at >= window_start,
        SpiderTask.started_at.isnot(None),
        SpiderTask.finished_at.isnot(None),
    )
    if spider_id:
        query = query.where(SpiderTask.spider_id == spider_id)

    result = await session.execute(query)
    tasks = list(result.scalars().all())

    for task in tasks:
        duration = (task.finished_at - task.started_at).total_seconds()
        if duration > max_duration_seconds:
            return True, (
                f"任务执行时间过长: 任务 {task.id} 耗时 {duration:.0f}s "
                f"(阈值: {max_duration_seconds}s)"
            )
    return False, ""


async def _check_items_count(
    session, condition: dict, spider_id: str | None, now: datetime
) -> tuple[bool, str]:
    """检查采集数量"""
    min_items = condition.get("min_items", 1)
    window_minutes = condition.get("window_minutes", 60)
    window_start = now - timedelta(minutes=window_minutes)

    query = select(SpiderTask).where(
        SpiderTask.created_at >= window_start,
        SpiderTask.status == SpiderTaskStatus.COMPLETED,
    )
    if spider_id:
        query = query.where(SpiderTask.spider_id == spider_id)

    result = await session.execute(query)
    tasks = list(result.scalars().all())

    for task in tasks:
        if task.success_count < min_items:
            return True, (
                f"采集数量不足: 任务 {task.id} 仅采集 {task.success_count} 条 "
                f"(最低要求: {min_items} 条)"
            )
    return False, ""


async def _check_heartbeat_timeout(
    session, condition: dict, spider_id: str | None, now: datetime
) -> tuple[bool, str]:
    """检查心跳超时"""
    timeout_minutes = condition.get("timeout_minutes", 5)
    timeout_threshold = now - timedelta(minutes=timeout_minutes)

    query = select(SpiderTask).where(
        SpiderTask.status == SpiderTaskStatus.RUNNING,
    )
    if spider_id:
        query = query.where(SpiderTask.spider_id == spider_id)

    result = await session.execute(query)
    tasks = list(result.scalars().all())

    for task in tasks:
        if task.last_heartbeat and task.last_heartbeat < timeout_threshold:
            return True, (
                f"心跳超时: 任务 {task.id} 已超过 {timeout_minutes} 分钟未发送心跳，"
                f"上次心跳时间: {task.last_heartbeat.isoformat()}"
            )
    return False, ""
