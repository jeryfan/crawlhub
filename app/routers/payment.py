"""支付回调路由"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from libs.payment import get_payment_provider
from models.account import Tenant
from models.billing import (
    BalanceLog,
    BalanceLogType,
    PaymentMethod,
    RechargeOrder,
    RechargeOrderStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["Payment Callback"])


async def process_recharge_success(
    db: AsyncSession,
    out_trade_no: str,
    trade_no: str,
):
    """处理充值成功"""
    # 查找订单
    order = await db.scalar(select(RechargeOrder).where(RechargeOrder.out_trade_no == out_trade_no))

    if not order:
        logger.warning(f"支付回调：订单不存在 {out_trade_no}")
        return False

    # 检查订单状态，避免重���处理
    if order.status == RechargeOrderStatus.PAID:
        logger.info(f"支付回调：订单已处理 {out_trade_no}")
        return True

    if order.status != RechargeOrderStatus.PENDING:
        logger.warning(f"支付回调：订单状态异常 {out_trade_no}, status={order.status}")
        return False

    # 获取租户
    tenant = await db.get(Tenant, order.tenant_id)
    if not tenant:
        logger.error(f"支付回调：租户不存在 tenant_id={order.tenant_id}")
        return False

    # 更新订单状态
    order.status = RechargeOrderStatus.PAID
    order.trade_no = trade_no
    order.paid_at = datetime.utcnow()

    # 增加余额
    balance_before = tenant.balance
    tenant.balance = tenant.balance + order.amount

    # 记录余额变动
    balance_log = BalanceLog(
        tenant_id=tenant.id,
        type=BalanceLogType.RECHARGE,
        amount=order.amount,
        balance_before=balance_before,
        balance_after=tenant.balance,
        related_order_id=order.id,
        remark=f"充值 ¥{order.amount}",
    )
    db.add(balance_log)

    await db.commit()

    logger.info(f"支付回调：充值成功 {out_trade_no}, amount={order.amount}")
    return True


@router.post("/wechat/notify")
async def wechat_pay_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """微信支付回调"""
    try:
        # 获取请求数据
        body = await request.body()
        headers = dict(request.headers)

        # 验证回调
        provider = get_payment_provider(PaymentMethod.WECHAT)
        result = await provider.verify_callback(headers, body)

        if not result.success:
            logger.error(f"微信支��回调验证失败: {result.error_msg}")
            return Response(
                content='{"code": "FAIL", "message": "验证失败"}',
                media_type="application/json",
            )

        # 处理充值
        success = await process_recharge_success(
            db=db,
            out_trade_no=result.out_trade_no,
            trade_no=result.trade_no,
        )

        resp = provider.get_callback_response(success)
        return Response(
            content=str(resp) if isinstance(resp, str) else str(resp),
            media_type="application/json",
        )

    except Exception as e:
        logger.exception(f"微信支付回调异常: {e}")
        return Response(
            content='{"code": "FAIL", "message": "系统错误"}',
            media_type="application/json",
        )


@router.post("/alipay/notify")
async def alipay_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """支付宝支付回调"""
    try:
        # 获取请求数据
        body = await request.body()
        headers = dict(request.headers)

        # 验证回调
        provider = get_payment_provider(PaymentMethod.ALIPAY)
        result = await provider.verify_callback(headers, body)

        if not result.success:
            logger.error(f"支付宝回调验证失败: {result.error_msg}")
            return Response(content="fail", media_type="text/plain")

        # 处理充值
        success = await process_recharge_success(
            db=db,
            out_trade_no=result.out_trade_no,
            trade_no=result.trade_no,
        )

        resp = provider.get_callback_response(success)
        return Response(content=resp, media_type="text/plain")

    except Exception as e:
        logger.exception(f"支付宝回调异常: {e}")
        return Response(content="fail", media_type="text/plain")
