import logging

from celery import shared_task
from sqlalchemy import delete, update

from models.engine import AsyncSessionLocal
from models import Account
from models.account import (
    AccountIntegrate,
    InvitationCode,
    Tenant,
    TenantAccountJoin,
    TenantAccountRole,
    TenantStatus,
)
from models.billing import BalanceLog, RechargeOrder, SubscriptionOrder
from tasks.mail_account_deletion_task import send_deletion_success_task

logger = logging.getLogger(__name__)


@shared_task
async def delete_account_task(account_id: str) -> dict:
    """
    Celery 任务：异步删除账户

    删除策略：
    1. 级联删除：AccountIntegrate, TenantAccountJoin
    2. 置空引用：RechargeOrder, SubscriptionOrder, BalanceLog, InvitationCode
    3. 特殊处理：如果是 Tenant 唯一 owner，归档该 Tenant

    Args:
        account_id: 账户 ID

    Returns:
        删除结果统计
    """
    async with AsyncSessionLocal() as session:
        # 获取账户信息
        account = await session.get(Account, account_id)
        if not account:
            logger.error("Account %s not found.", account_id)
            return {"success": False, "error": "Account not found"}

        account_email = account.email
        logger.info("Starting account deletion for %s (email: %s)", account_id, account_email)

        try:
            # 1. 处理用户作为 owner 的租户
            # 查找用户作为 owner 的所有租户
            owner_joins = await session.execute(
                TenantAccountJoin.__table__.select().where(
                    TenantAccountJoin.account_id == account_id,
                    TenantAccountJoin.role == TenantAccountRole.OWNER,
                )
            )
            owner_tenant_ids = [row.tenant_id for row in owner_joins.fetchall()]

            for tenant_id in owner_tenant_ids:
                # 检查该租户是否还有其他成员
                other_members = await session.execute(
                    TenantAccountJoin.__table__.select().where(
                        TenantAccountJoin.tenant_id == tenant_id,
                        TenantAccountJoin.account_id != account_id,
                    )
                )
                other_member_list = other_members.fetchall()

                if not other_member_list:
                    # 没有其他成员，归档租户
                    await session.execute(
                        update(Tenant)
                        .where(Tenant.id == tenant_id)
                        .values(status=TenantStatus.ARCHIVE)
                    )
                    logger.info("Archived tenant %s (no other members)", tenant_id)
                else:
                    # 有其他成员，将第一个管理员或成员提升为 owner
                    # 优先选择管理员
                    new_owner = None
                    for member in other_member_list:
                        if member.role == TenantAccountRole.ADMIN:
                            new_owner = member
                            break
                    if not new_owner:
                        new_owner = other_member_list[0]

                    await session.execute(
                        update(TenantAccountJoin)
                        .where(TenantAccountJoin.id == new_owner.id)
                        .values(role=TenantAccountRole.OWNER)
                    )
                    logger.info(
                        "Transferred ownership of tenant %s to account %s",
                        tenant_id,
                        new_owner.account_id,
                    )

            # 2. 删除第三方账户集成记录
            result = await session.execute(
                delete(AccountIntegrate).where(AccountIntegrate.account_id == account_id)
            )
            integrates_deleted = result.rowcount
            logger.info("Deleted %d account integrations", integrates_deleted)

            # 3. 删除租户-账户关联记录
            result = await session.execute(
                delete(TenantAccountJoin).where(TenantAccountJoin.account_id == account_id)
            )
            joins_deleted = result.rowcount
            logger.info("Deleted %d tenant account joins", joins_deleted)

            # 4. 置空账单相关记录中的 account_id（保留账单数据用于审计）
            result = await session.execute(
                update(RechargeOrder)
                .where(RechargeOrder.account_id == account_id)
                .values(account_id=None)
            )
            recharge_orders_updated = result.rowcount

            result = await session.execute(
                update(SubscriptionOrder)
                .where(SubscriptionOrder.account_id == account_id)
                .values(account_id=None)
            )
            subscription_orders_updated = result.rowcount

            result = await session.execute(
                update(BalanceLog)
                .where(BalanceLog.account_id == account_id)
                .values(account_id=None)
            )
            balance_logs_updated = result.rowcount

            # 同时处理 operator_id（管理员操作记录）
            result = await session.execute(
                update(BalanceLog)
                .where(BalanceLog.operator_id == account_id)
                .values(operator_id=None)
            )
            operator_logs_updated = result.rowcount

            logger.info(
                "Nullified billing references: recharge=%d, subscription=%d, balance=%d, operator=%d",
                recharge_orders_updated,
                subscription_orders_updated,
                balance_logs_updated,
                operator_logs_updated,
            )

            # 5. 置空邀请码中的 used_by_account_id
            result = await session.execute(
                update(InvitationCode)
                .where(InvitationCode.used_by_account_id == account_id)
                .values(used_by_account_id=None)
            )
            invitation_codes_updated = result.rowcount
            logger.info("Nullified %d invitation code references", invitation_codes_updated)

            # 6. 删除账户本身
            await session.delete(account)

            # 提交事务
            await session.commit()
            logger.info("Successfully deleted account %s", account_id)

        except Exception:
            await session.rollback()
            logger.exception("Failed to delete account %s", account_id)
            raise

    # 发送删除成功邮件（在事务外执行，确保删除成功后才发送）
    send_deletion_success_task.delay(account_email)
    logger.info("Queued deletion success email for %s", account_email)

    return {
        "success": True,
        "account_id": account_id,
        "integrates_deleted": integrates_deleted,
        "joins_deleted": joins_deleted,
        "billing_references_nullified": {
            "recharge_orders": recharge_orders_updated,
            "subscription_orders": subscription_orders_updated,
            "balance_logs": balance_logs_updated,
            "operator_logs": operator_logs_updated,
        },
        "invitation_codes_updated": invitation_codes_updated,
    }
