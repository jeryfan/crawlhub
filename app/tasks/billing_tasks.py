import logging
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from sqlalchemy import select, update

from configs import app_config
from models.engine import TaskSessionLocal, run_async
from models.account import Tenant
from models.billing import (
    BalanceLog,
    BalanceLogType,
    PendingChangeStatus,
    PendingPlanChange,
    RechargeOrder,
    RechargeOrderStatus,
    SubscriptionOrder,
    SubscriptionOrderStatus,
    SubscriptionOrderType,
    SubscriptionPlan,
)

logger = logging.getLogger(__name__)


@shared_task
def expire_recharge_orders():
    """定时任务：过期充值订单处理（每分钟执行）"""
    return run_async(_expire_recharge_orders())


async def _expire_recharge_orders():
    async with TaskSessionLocal() as session:
        now = datetime.utcnow()

        # 查找所有已过期但状态仍为 pending 的订单
        result = await session.execute(
            update(RechargeOrder)
            .where(
                RechargeOrder.status == RechargeOrderStatus.PENDING,
                RechargeOrder.expired_at < now,
            )
            .values(status=RechargeOrderStatus.EXPIRED)
            .returning(RechargeOrder.id)
        )

        expired_ids = [row[0] for row in result.fetchall()]
        await session.commit()

        if expired_ids:
            logger.info(f"已将 {len(expired_ids)} 个充值订单标记为过期")

        return {"expired_count": len(expired_ids)}


@shared_task
def process_subscription_expiry():
    """定时任务：订阅到期处理（每小时执行）"""
    return run_async(_process_subscription_expiry())


async def _process_subscription_expiry():
    async with TaskSessionLocal() as session:
        now = datetime.utcnow()

        # 查找所有到期的租户（非 basic 计划）
        result = await session.execute(
            select(Tenant).where(
                Tenant.plan != "basic",
                Tenant.plan_expires_at != None,
                Tenant.plan_expires_at < now,
            )
        )
        expired_tenants = result.scalars().all()

        renewed_count = 0
        downgraded_count = 0

        for tenant in expired_tenants:
            # 查找最近的订阅订单，检查是否自动续费
            latest_order = await session.scalar(
                select(SubscriptionOrder)
                .where(
                    SubscriptionOrder.tenant_id == tenant.id,
                    SubscriptionOrder.status == SubscriptionOrderStatus.ACTIVE,
                )
                .order_by(SubscriptionOrder.created_at.desc())
            )

            # 获取计划价格
            plan_prices = {
                "pro": Decimal(str(app_config.PLAN_PRO_PRICE)),
                "max": Decimal(str(app_config.PLAN_MAX_PRICE)),
            }
            price = plan_prices.get(tenant.plan, Decimal("0"))

            should_auto_renew = latest_order and latest_order.is_auto_renew

            if should_auto_renew and tenant.balance >= price:
                # 余额充足，自动续费
                balance_before = tenant.balance
                tenant.balance = tenant.balance - price
                tenant.plan_expires_at = now + timedelta(days=30)

                # 创建新的订阅订单
                new_order = SubscriptionOrder(
                    tenant_id=tenant.id,
                    plan=tenant.plan,
                    price=price,
                    starts_at=now,
                    expires_at=tenant.plan_expires_at,
                    is_auto_renew=True,
                )
                session.add(new_order)

                # 将旧订单标记为过期
                if latest_order:
                    latest_order.status = SubscriptionOrderStatus.EXPIRED

                # 记录余额变动
                balance_log = BalanceLog(
                    tenant_id=tenant.id,
                    type=BalanceLogType.SUBSCRIBE,
                    amount=-price,
                    balance_before=balance_before,
                    balance_after=tenant.balance,
                    related_order_id=new_order.id,
                    remark=f"自动续费 {tenant.plan.upper()} 计划",
                )
                session.add(balance_log)

                renewed_count += 1
                logger.info(f"租户 {tenant.id} 自动续费成功")

            else:
                # 降级为 basic
                old_plan = tenant.plan
                tenant.plan = "basic"
                tenant.plan_expires_at = None

                # 将旧订单标记为过期
                if latest_order:
                    latest_order.status = SubscriptionOrderStatus.EXPIRED

                downgraded_count += 1
                logger.info(f"租户 {tenant.id} 已从 {old_plan} 降级为 basic")

        await session.commit()

        return {
            "renewed_count": renewed_count,
            "downgraded_count": downgraded_count,
        }


@shared_task
def send_expiry_reminders():
    """定时任务：订阅到期提醒（每天执行）"""
    return run_async(_send_expiry_reminders())


async def _send_expiry_reminders():
    async with TaskSessionLocal() as session:
        now = datetime.utcnow()
        remind_before = now + timedelta(days=3)  # 提前3天提醒

        # 查找即将到期的租户
        result = await session.execute(
            select(Tenant).where(
                Tenant.plan != "basic",
                Tenant.plan_expires_at != None,
                Tenant.plan_expires_at > now,
                Tenant.plan_expires_at <= remind_before,
            )
        )
        tenants = result.scalars().all()

        reminded_count = 0
        for tenant in tenants:
            # TODO: 发送提醒邮件
            # 这里可以调用邮件服务发送提醒
            logger.info(f"租户 {tenant.id} ({tenant.name}) 订阅将于 {tenant.plan_expires_at} 到期")
            reminded_count += 1

        return {"reminded_count": reminded_count}


@shared_task
def process_pending_plan_changes():
    """定时任务：处理待执行的计划变更（每小时执行）"""
    return run_async(_process_pending_plan_changes())


async def _process_pending_plan_changes():
    async with TaskSessionLocal() as session:
        now = datetime.utcnow()

        # 查找所有到期的待执行降级请求
        result = await session.execute(
            select(PendingPlanChange).where(
                PendingPlanChange.status == PendingChangeStatus.PENDING,
                PendingPlanChange.effective_at <= now,
            )
        )
        pending_changes = result.scalars().all()

        executed_count = 0

        for change in pending_changes:
            # 获取租户
            tenant = await session.get(Tenant, change.tenant_id)
            if not tenant:
                logger.warning(f"待降级记录 {change.id} 的租户 {change.tenant_id} 不存在")
                change.status = PendingChangeStatus.CANCELLED
                continue

            # 获取目标计划信息
            target_plan_info = await session.scalar(
                select(SubscriptionPlan).where(SubscriptionPlan.id == change.target_plan)
            )

            # 记录旧计划
            old_plan = tenant.plan

            # 执行降级
            tenant.plan = change.target_plan

            # 如果目标是默认计划（免费），清除到期时间
            if target_plan_info and target_plan_info.is_default:
                tenant.plan_expires_at = None
            else:
                # 如果降级到非免费计划，设置新的到期时间
                if change.target_billing_cycle == "yearly":
                    subscription_days = 365
                else:
                    subscription_days = 30
                tenant.plan_expires_at = now + timedelta(days=subscription_days)

            # 将之前的订阅订单标记为过期
            await session.execute(
                update(SubscriptionOrder)
                .where(
                    SubscriptionOrder.tenant_id == tenant.id,
                    SubscriptionOrder.status == SubscriptionOrderStatus.ACTIVE,
                )
                .values(status=SubscriptionOrderStatus.EXPIRED)
            )

            # 如果降级到非免费计划，创建新的降级订阅订单
            if target_plan_info and not target_plan_info.is_default:
                # 获取价格
                if change.target_billing_cycle == "yearly":
                    price = target_plan_info.price_yearly
                else:
                    price = target_plan_info.price_monthly

                downgrade_order = SubscriptionOrder(
                    tenant_id=tenant.id,
                    plan=change.target_plan,
                    billing_cycle=change.target_billing_cycle,
                    price=Decimal("0"),  # 降级不收费
                    original_price=price,
                    order_type=SubscriptionOrderType.DOWNGRADE,
                    previous_plan=old_plan,
                    starts_at=now,
                    expires_at=tenant.plan_expires_at,
                    is_auto_renew=False,
                    status=SubscriptionOrderStatus.ACTIVE,
                )
                session.add(downgrade_order)

            # 更新待降级记录状态
            change.status = PendingChangeStatus.EXECUTED

            executed_count += 1
            logger.info(f"租户 {tenant.id} 降级执行成功: {old_plan} -> {change.target_plan}")

        await session.commit()

        return {"executed_count": executed_count}
