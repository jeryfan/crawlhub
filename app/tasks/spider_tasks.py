import logging
from datetime import datetime, timedelta

from celery import shared_task
from croniter import croniter
from sqlalchemy import select

from models.crawlhub import Spider, SpiderTask, SpiderTaskStatus
from models.crawlhub.alert import AlertLevel
from models.engine import AsyncSessionLocal
from services.crawlhub.alert_service import AlertService
from services.crawlhub.spider_runner_service import SpiderRunnerService

logger = logging.getLogger(__name__)


@shared_task
async def run_scheduled_spiders():
    """定时扫描并执行启用了 cron 的爬虫"""
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Spider).where(
                Spider.is_active == True,
                Spider.cron_expr.isnot(None),
                Spider.cron_expr != "",
            )
        )
        spiders = list(result.scalars().all())

        for spider in spiders:
            try:
                cron = croniter(spider.cron_expr, one_minute_ago)
                next_run = cron.get_next(datetime)
                if next_run <= now:
                    execute_spider.delay(str(spider.id), trigger_type="schedule")
            except Exception as e:
                logger.error(f"Failed to process spider {spider.id} cron '{spider.cron_expr}': {e}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
async def execute_spider(self, spider_id: str, task_id: str | None = None, trigger_type: str = "schedule"):
    """执行单个爬虫任务"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Spider).where(Spider.id == spider_id)
        )
        spider = result.scalar_one_or_none()
        if not spider:
            logger.error(f"Spider {spider_id} not found")
            return

        runner = SpiderRunnerService(session)

        # 复用已有 task 或创建新 task
        if task_id:
            task_result = await session.execute(
                select(SpiderTask).where(SpiderTask.id == task_id)
            )
            task = task_result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found")
                return
        else:
            task = await runner.create_task(spider, trigger_type=trigger_type)

        await runner.run_spider_sync(spider, task)

        # 更新 retry_count (无论成功失败)
        task.retry_count = self.request.retries
        await session.commit()

        # Webhook 通知
        if spider.webhook_url:
            from services.crawlhub.webhook_service import WebhookService
            duration = (task.finished_at - task.started_at).total_seconds() if task.started_at and task.finished_at else 0
            await WebhookService.notify_task_result(
                webhook_url=spider.webhook_url,
                spider_name=spider.name,
                spider_id=spider_id,
                task_id=str(task.id),
                status=task.status.value,
                total_count=task.total_count,
                success_count=task.success_count,
                error_message=task.error_message,
                duration=duration,
            )

        if task.status == SpiderTaskStatus.FAILED:
            if self.request.retries < self.max_retries:
                raise self.retry(exc=Exception(task.error_message), kwargs={
                    "spider_id": spider_id,
                    "task_id": str(task.id),
                    "trigger_type": trigger_type,
                })
            else:
                # Retries exhausted — create alert
                alert_service = AlertService(session)
                await alert_service.create_alert(
                    type="task_failed",
                    level=AlertLevel.ERROR,
                    message=f"爬虫 [{spider.name}] 执行失败（已重试 {self.max_retries} 次）: {task.error_message or '未知错误'}",
                    spider_id=spider_id,
                    task_id=str(task.id),
                )


@shared_task
async def check_task_heartbeats():
    """检查 RUNNING 状态任务的心跳，超时则标记失败"""
    now = datetime.utcnow()
    heartbeat_timeout = timedelta(minutes=2)
    min_running_time = timedelta(minutes=3)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SpiderTask).where(
                SpiderTask.status == SpiderTaskStatus.RUNNING,
            )
        )
        tasks = list(result.scalars().all())

        for task in tasks:
            try:
                # 跳过运行时间不足 3 分钟的任务
                if task.started_at and (now - task.started_at) < min_running_time:
                    continue

                # 检查心跳超时
                if task.last_heartbeat:
                    if (now - task.last_heartbeat) > heartbeat_timeout:
                        task.status = SpiderTaskStatus.FAILED
                        task.error_category = "system"
                        task.error_message = "心跳超时：任务可能已停止响应"
                        task.finished_at = now
                        logger.warning(f"Task {task.id} heartbeat timeout, marking as failed")
                elif task.started_at and (now - task.started_at) > min_running_time:
                    # 从未收到心跳且已运行超过3分钟 — 可能未使用 SDK，不强制标记
                    pass

            except Exception as e:
                logger.error(f"Error checking heartbeat for task {task.id}: {e}")

        await session.commit()
