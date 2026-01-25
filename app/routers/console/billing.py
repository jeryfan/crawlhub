import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from models.engine import get_db
from dependencies.auth import get_current_user
from libs.payment import get_payment_provider
from models import Account
from models.account import Tenant, TenantAccountJoin
from models.billing import (
    BalanceLog,
    BalanceLogType,
    PaymentMethod,
    PendingChangeStatus,
    PendingPlanChange,
    RechargeOrder,
    SubscriptionOrder,
    SubscriptionOrderStatus,
    SubscriptionOrderType,
    SubscriptionPlan,
)
from schemas.billing import (
    BalanceLogItem,
    CurrentSubscription,
    DowngradePreviewResponse,
    DowngradeRequest,
    PendingDowngradeInfo,
    RechargeOrderItem,
    RechargeOrderResponse,
    RechargeRequest,
    SubscribeRequest,
    SubscriptionOrderItem,
    SubscriptionPlanItem,
    SubscriptionPlanList,
    SubscriptionUsage,
    UpgradePreviewRequest,
    UpgradePreviewResponse,
    UpgradeRequest,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans", response_model=ApiResponse[SubscriptionPlanList])
async def get_subscription_plans(
    db: AsyncSession = Depends(get_db),
    _: Account = Depends(get_current_user),
):
    """获取订阅计划列表"""
    query = (
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.sort_order)
    )
    result = await db.execute(query)
    plans = result.scalars().all()

    if not plans:
        default_plans = [
            SubscriptionPlanItem(
                id="basic",
                name="Basic",
                price_monthly=Decimal("0"),
                price_yearly=Decimal("0"),
                features={"api_calls": 1000, "storage": "1GB"},
                description="基础版，适合个人使用",
                sort_order=0,
            ),
            SubscriptionPlanItem(
                id="pro",
                name="Pro",
                price_monthly=Decimal(str(app_config.PLAN_PRO_PRICE)),
                price_yearly=Decimal(str(app_config.PLAN_PRO_PRICE * 10)),
                features={
                    "api_calls": 10000,
                    "storage": "10GB",
                    "priority_support": True,
                },
                description="专业版，适合小型团队",
                sort_order=1,
            ),
            SubscriptionPlanItem(
                id="max",
                name="Max",
                price_monthly=Decimal(str(app_config.PLAN_MAX_PRICE)),
                price_yearly=Decimal(str(app_config.PLAN_MAX_PRICE * 10)),
                features={
                    "api_calls": -1,
                    "storage": "100GB",
                    "priority_support": True,
                    "dedicated_support": True,
                },
                description="旗舰版，适合企业使用",
                sort_order=2,
            ),
        ]
        return ApiResponse(data=SubscriptionPlanList(plans=default_plans))

    return ApiResponse(
        data=SubscriptionPlanList(plans=[SubscriptionPlanItem.model_validate(p) for p in plans])
    )


@router.get("/current", response_model=ApiResponse[CurrentSubscription])
async def get_current_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant = current_user.current_tenant

    # 计算剩余天数
    days_remaining = None
    now = datetime.now()
    if tenant.plan_expires_at:
        delta = tenant.plan_expires_at - now
        days_remaining = max(0, delta.days)

    # 获取是否自动续费和计费周期
    is_auto_renew = True
    billing_cycle = None
    starts_at = None

    # 查找当前正在生效的订阅订单（starts_at <= now <= expires_at）
    current_subscription = await db.scalar(
        select(SubscriptionOrder)
        .where(
            SubscriptionOrder.tenant_id == tenant.id,
            SubscriptionOrder.status == SubscriptionOrderStatus.ACTIVE,
            SubscriptionOrder.starts_at <= now,
            SubscriptionOrder.expires_at >= now,
        )
        .order_by(SubscriptionOrder.starts_at.asc())
    )
    if current_subscription:
        starts_at = current_subscription.starts_at
        billing_cycle = current_subscription.billing_cycle

    # 查找最新的订阅订单以获取自动续费设置
    latest_subscription = await db.scalar(
        select(SubscriptionOrder)
        .where(
            SubscriptionOrder.tenant_id == tenant.id,
            SubscriptionOrder.status == SubscriptionOrderStatus.ACTIVE,
        )
        .order_by(SubscriptionOrder.created_at.desc())
    )
    if latest_subscription:
        is_auto_renew = latest_subscription.is_auto_renew
        # 如果没有当前生效的订阅，使用最新订阅的计费周期
        if not billing_cycle:
            billing_cycle = latest_subscription.billing_cycle

    # 从数据库获取计划名称
    plan_info = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan))
    plan_name = plan_info.name if plan_info else tenant.plan

    # 查询使用量
    # 1. 团队成员数量
    team_members_count = (
        await db.scalar(select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id)) or 0
    )

    # 2. 应用数量（目前项目中没有 App 模型，暂时返回 0）
    apps_count = 0

    # 查询待降级信息
    pending_downgrade = None
    pending_change = await db.scalar(
        select(PendingPlanChange).where(
            PendingPlanChange.tenant_id == tenant.id,
            PendingPlanChange.status == PendingChangeStatus.PENDING,
        )
    )
    if pending_change:
        target_plan_info = await db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.id == pending_change.target_plan)
        )
        pending_downgrade = PendingDowngradeInfo(
            target_plan=pending_change.target_plan,
            target_plan_name=(
                target_plan_info.name if target_plan_info else pending_change.target_plan
            ),
            effective_at=pending_change.effective_at,
        )

    return ApiResponse(
        data=CurrentSubscription(
            plan=tenant.plan,
            plan_name=plan_name,
            balance=tenant.balance,
            starts_at=starts_at,
            expires_at=tenant.plan_expires_at,
            is_auto_renew=is_auto_renew,
            days_remaining=days_remaining,
            billing_cycle=billing_cycle,
            usage=SubscriptionUsage(
                team_members=team_members_count,
                apps_count=apps_count,
            ),
            pending_downgrade=pending_downgrade,
        )
    )


# ============ 充值 ============
@router.post("/recharge", response_model=ApiResponse[RechargeOrderResponse])
async def create_recharge_order(
    data: RechargeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """创建充值订单"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant_id = current_user.current_tenant_id

    # 生成订单号
    out_trade_no = f"RC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

    # 计算过期时间
    expire_minutes = app_config.RECHARGE_ORDER_EXPIRE_MINUTES
    expired_at = datetime.now() + timedelta(minutes=expire_minutes)

    # 获取支付服务
    payment_provider = get_payment_provider(data.payment_method)

    # 确定回调地址
    if data.payment_method == PaymentMethod.WECHAT:
        notify_url = (
            app_config.WECHAT_PAY_NOTIFY_URL
            or f"{app_config.CONSOLE_API_URL}/api/payment/wechat/notify"
        )
    else:
        notify_url = (
            app_config.ALIPAY_NOTIFY_URL
            or f"{app_config.CONSOLE_API_URL}/api/payment/alipay/notify"
        )

    # 创建支付订单
    result = await payment_provider.create_native_order(
        out_trade_no=out_trade_no,
        amount=data.amount,
        description=f"账户充值 ¥{data.amount}",
        notify_url=notify_url,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_msg or "创建支付订单失败")

    # 保存订单到数据库
    order = RechargeOrder(
        tenant_id=tenant_id,
        account_id=current_user.id,
        amount=data.amount,
        payment_method=data.payment_method,
        out_trade_no=out_trade_no,
        qr_code_url=result.qr_code_url,
        expired_at=expired_at,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    return ApiResponse(
        data=RechargeOrderResponse(
            id=order.id,
            amount=order.amount,
            payment_method=order.payment_method,
            qr_code_url=order.qr_code_url,
            expired_at=order.expired_at,
            status=order.status,
            out_trade_no=order.out_trade_no,
        )
    )


@router.get("/recharge/{order_id}/status", response_model=ApiResponse[RechargeOrderResponse])
async def get_recharge_order_status(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """查询充值订单状态"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    order = await db.get(RechargeOrder, order_id)
    if not order or order.tenant_id != current_user.current_tenant_id:
        raise HTTPException(status_code=404, detail="订单不存在")

    return ApiResponse(
        data=RechargeOrderResponse(
            id=order.id,
            amount=order.amount,
            payment_method=order.payment_method,
            qr_code_url=order.qr_code_url,
            expired_at=order.expired_at,
            status=order.status,
            out_trade_no=order.out_trade_no,
        )
    )


@router.get(
    "/recharge/history",
    response_model=ApiResponse[PaginatedResponse[RechargeOrderItem]],
)
async def get_recharge_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """获取充值历史记录"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant_id = current_user.current_tenant_id

    # 查询总数
    count_query = select(func.count()).where(RechargeOrder.tenant_id == tenant_id)
    total = await db.scalar(count_query) or 0

    # 分页查询
    query = (
        select(RechargeOrder)
        .where(RechargeOrder.tenant_id == tenant_id)
        .order_by(RechargeOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[RechargeOrderItem.model_validate(o) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


# ============ 订阅 ============
@router.post("/subscribe", response_model=MessageResponse)
async def subscribe_plan(
    data: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """订阅计划（使用余额扣款）"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant = await db.get(Tenant, current_user.current_tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 从数据库获取计划信息
    plan_info = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == data.plan,
            SubscriptionPlan.is_active == True,
        )
    )
    if not plan_info:
        raise HTTPException(status_code=400, detail="无效的订阅计划")

    if plan_info.is_default:
        raise HTTPException(status_code=400, detail="默认计划无需订阅")

    # 根据计费周期选择价格和订阅时长
    if data.billing_cycle == "yearly":
        original_price = plan_info.price_yearly
        subscription_days = 365
    else:
        original_price = plan_info.price_monthly
        subscription_days = 30

    # 确定订单类型和是否享受首月折扣
    now = datetime.now()
    order_type = SubscriptionOrderType.NEW
    is_first_month_discount = False
    discount_amount = Decimal("0")
    price = original_price

    if tenant.plan_expires_at and tenant.plan_expires_at > now and tenant.plan == data.plan:
        # 续费：从当前到期时间开始
        order_type = SubscriptionOrderType.RENEW
        starts_at = tenant.plan_expires_at
    else:
        # 新订阅：从现在开始
        starts_at = now

        # 检查是否有历史订阅（排除降级订单）
        has_subscription_history = (
            await db.scalar(
                select(func.count()).where(
                    SubscriptionOrder.tenant_id == tenant.id,
                    SubscriptionOrder.order_type.in_(
                        [
                            SubscriptionOrderType.NEW,
                            SubscriptionOrderType.RENEW,
                            SubscriptionOrderType.UPGRADE,
                        ]
                    ),
                    SubscriptionOrder.price > 0,
                )
            )
            or 0
        )

        # 首月折扣：仅限月付、新用户、且计划启用了首月折扣
        if (
            data.billing_cycle == "monthly"
            and has_subscription_history == 0
            and plan_info.first_month_discount_enabled
            and plan_info.first_month_discount_percent > 0
        ):
            is_first_month_discount = True
            discount_amount = (
                original_price * Decimal(plan_info.first_month_discount_percent) / Decimal(100)
            )
            price = original_price - discount_amount

    expires_at = starts_at + timedelta(days=subscription_days)

    # 检查余额
    if tenant.balance < price:
        raise HTTPException(status_code=400, detail="余额不足，请先充值")

    # 扣除余额
    balance_before = tenant.balance
    tenant.balance = tenant.balance - price
    tenant.plan = data.plan
    tenant.plan_expires_at = expires_at

    # 创建订阅订单
    subscription_order = SubscriptionOrder(
        tenant_id=tenant.id,
        account_id=current_user.id,
        plan=data.plan,
        billing_cycle=data.billing_cycle,
        price=price,
        original_price=original_price,
        discount_amount=discount_amount,
        order_type=order_type,
        is_first_month_discount=is_first_month_discount,
        starts_at=starts_at,
        expires_at=expires_at,
        is_auto_renew=data.auto_renew,
    )
    db.add(subscription_order)

    # 取消待降级请求（如果有）
    pending_change = await db.scalar(
        select(PendingPlanChange).where(
            PendingPlanChange.tenant_id == tenant.id,
            PendingPlanChange.status == PendingChangeStatus.PENDING,
        )
    )
    if pending_change:
        pending_change.status = PendingChangeStatus.CANCELLED

    # 记录余额变动
    cycle_text = "年" if data.billing_cycle == "yearly" else "月"
    discount_text = (
        f"（首月折扣 {plan_info.first_month_discount_percent}%）" if is_first_month_discount else ""
    )
    balance_log = BalanceLog(
        tenant_id=tenant.id,
        account_id=current_user.id,
        type=BalanceLogType.SUBSCRIBE,
        amount=-price,
        balance_before=balance_before,
        balance_after=tenant.balance,
        related_order_id=subscription_order.id,
        remark=f"订阅 {plan_info.name} 计划（{cycle_text}付）{discount_text}",
    )
    db.add(balance_log)

    await db.commit()

    return MessageResponse(msg="订阅成功")


@router.post("/cancel-auto-renew", response_model=MessageResponse)
async def cancel_auto_renew(
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """取消自动续费"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    # 查找当前生效的订阅订单
    order = await db.scalar(
        select(SubscriptionOrder)
        .where(
            SubscriptionOrder.tenant_id == current_user.current_tenant_id,
            SubscriptionOrder.status == SubscriptionOrderStatus.ACTIVE,
        )
        .order_by(SubscriptionOrder.created_at.desc())
    )

    if not order:
        raise HTTPException(status_code=404, detail="没有找到有效的订阅订单")

    order.is_auto_renew = False
    await db.commit()

    return MessageResponse(msg="已取消自动续费")


@router.get(
    "/subscription/history",
    response_model=ApiResponse[PaginatedResponse[SubscriptionOrderItem]],
)
async def get_subscription_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """获取订阅历史记录"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant_id = current_user.current_tenant_id

    # 查询总数
    count_query = select(func.count()).where(SubscriptionOrder.tenant_id == tenant_id)
    total = await db.scalar(count_query) or 0

    # 分页查询
    query = (
        select(SubscriptionOrder)
        .where(SubscriptionOrder.tenant_id == tenant_id)
        .order_by(SubscriptionOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[SubscriptionOrderItem.model_validate(o) for o in orders],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


# ============ 余额 ============
@router.get("/balance/logs", response_model=ApiResponse[PaginatedResponse[BalanceLogItem]])
async def get_balance_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """获取余额变动记录"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant_id = current_user.current_tenant_id

    # 查询总数
    count_query = select(func.count()).where(BalanceLog.tenant_id == tenant_id)
    total = await db.scalar(count_query) or 0

    # 分页查询
    query = (
        select(BalanceLog)
        .where(BalanceLog.tenant_id == tenant_id)
        .order_by(BalanceLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[BalanceLogItem.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


# ============ 升级/降级 ============
@router.post("/upgrade/preview", response_model=ApiResponse[UpgradePreviewResponse])
async def preview_upgrade(
    data: UpgradePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """预览升级信息（计算按比例抵扣）"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant = current_user.current_tenant

    # 获取当前计划信息
    current_plan_info = await db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan)
    )

    # 获取目标计划信息
    target_plan_info = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == data.target_plan,
            SubscriptionPlan.is_active == True,
        )
    )

    if not target_plan_info:
        raise HTTPException(status_code=400, detail="目标计划不存在")

    if target_plan_info.is_default:
        raise HTTPException(status_code=400, detail="不能升级到免费计划，请使用降级接口")

    # 获取价格
    if data.billing_cycle == "yearly":
        current_price = current_plan_info.price_yearly if current_plan_info else Decimal("0")
        target_price = target_plan_info.price_yearly
        total_days = 365
    else:
        current_price = current_plan_info.price_monthly if current_plan_info else Decimal("0")
        target_price = target_plan_info.price_monthly
        total_days = 30

    # 验证是升级（目标计划价格应高于当前）
    if target_price <= current_price and current_plan_info and not current_plan_info.is_default:
        raise HTTPException(status_code=400, detail="目标计划价格不高于当前计划，请使用降级接口")

    # 计算剩余天数和价值
    now = datetime.now()
    if tenant.plan_expires_at and tenant.plan_expires_at > now:
        remaining_days = (tenant.plan_expires_at - now).days
        # 剩余价值 = 当前计划价格 * (剩余天数 / 总天数)
        remaining_value = current_price * (Decimal(remaining_days) / Decimal(total_days))
        # 新计划剩余周期费用
        new_plan_cost = target_price * (Decimal(remaining_days) / Decimal(total_days))
        # 差价
        difference = new_plan_cost - remaining_value
    else:
        remaining_days = 0
        remaining_value = Decimal("0")
        new_plan_cost = target_price
        difference = target_price

    return ApiResponse(
        data=UpgradePreviewResponse(
            current_plan=tenant.plan,
            target_plan=data.target_plan,
            current_plan_name=(current_plan_info.name if current_plan_info else tenant.plan),
            target_plan_name=target_plan_info.name,
            remaining_days=remaining_days,
            remaining_value=remaining_value.quantize(Decimal("0.01")),
            new_plan_cost=new_plan_cost.quantize(Decimal("0.01")),
            difference=difference.quantize(Decimal("0.01")),
            billing_cycle=data.billing_cycle,
            effective_immediately=True,
        )
    )


@router.post("/upgrade", response_model=MessageResponse)
async def upgrade_plan(
    data: UpgradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """升级计划（按比例抵扣）"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant = await db.get(Tenant, current_user.current_tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取当前计划信息
    current_plan_info = await db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan)
    )

    # 获取目标计划信息
    target_plan_info = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == data.target_plan,
            SubscriptionPlan.is_active == True,
        )
    )

    if not target_plan_info:
        raise HTTPException(status_code=400, detail="目标计划不存在")

    if target_plan_info.is_default:
        raise HTTPException(status_code=400, detail="不能升级到免费计划，请使用降级接口")

    # 获取价格
    if data.billing_cycle == "yearly":
        current_price = current_plan_info.price_yearly if current_plan_info else Decimal("0")
        target_price = target_plan_info.price_yearly
        total_days = 365
    else:
        current_price = current_plan_info.price_monthly if current_plan_info else Decimal("0")
        target_price = target_plan_info.price_monthly
        total_days = 30

    # 验证是升级
    if target_price <= current_price and current_plan_info and not current_plan_info.is_default:
        raise HTTPException(status_code=400, detail="目标计划价格不高于当前计划，请使用降级接口")

    # 计算差价
    now = datetime.now()
    if tenant.plan_expires_at and tenant.plan_expires_at > now:
        remaining_days = (tenant.plan_expires_at - now).days
        remaining_value = current_price * (Decimal(remaining_days) / Decimal(total_days))
        new_plan_cost = target_price * (Decimal(remaining_days) / Decimal(total_days))
        difference = (new_plan_cost - remaining_value).quantize(Decimal("0.01"))
    else:
        remaining_value = Decimal("0")
        difference = target_price

    # 检查余额
    if difference > 0 and tenant.balance < difference:
        raise HTTPException(status_code=400, detail="余额不足，请先充值")

    # 保存旧计划信息
    previous_plan = tenant.plan
    balance_before = tenant.balance

    # 扣款
    if difference > 0:
        tenant.balance = tenant.balance - difference

    # 更新计划（到期时间保持不变，如果没有到期时间则设置新的）
    tenant.plan = data.target_plan
    if not tenant.plan_expires_at or tenant.plan_expires_at <= now:
        tenant.plan_expires_at = now + timedelta(days=total_days)

    # 创建订阅订单
    subscription_order = SubscriptionOrder(
        tenant_id=tenant.id,
        account_id=current_user.id,
        plan=data.target_plan,
        billing_cycle=data.billing_cycle,
        price=difference,
        original_price=target_price,
        prorated_credit=remaining_value.quantize(Decimal("0.01")),
        order_type=SubscriptionOrderType.UPGRADE,
        previous_plan=previous_plan,
        starts_at=now,
        expires_at=tenant.plan_expires_at,
        is_auto_renew=True,
    )
    db.add(subscription_order)

    # 取消待降级请求（如果有）
    pending_change = await db.scalar(
        select(PendingPlanChange).where(
            PendingPlanChange.tenant_id == tenant.id,
            PendingPlanChange.status == PendingChangeStatus.PENDING,
        )
    )
    if pending_change:
        pending_change.status = PendingChangeStatus.CANCELLED

    # 记录余额变动
    if difference > 0:
        balance_log = BalanceLog(
            tenant_id=tenant.id,
            account_id=current_user.id,
            type=BalanceLogType.UPGRADE_CHARGE,
            amount=-difference,
            balance_before=balance_before,
            balance_after=tenant.balance,
            related_order_id=subscription_order.id,
            remark=f"从 {current_plan_info.name if current_plan_info else previous_plan} 升级到 {target_plan_info.name}",
        )
        db.add(balance_log)

    await db.commit()

    return MessageResponse(msg="升级成功")


@router.post("/downgrade", response_model=ApiResponse[DowngradePreviewResponse])
async def request_downgrade(
    data: DowngradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """请求降级（下个周期生效）"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    tenant = await db.get(Tenant, current_user.current_tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取当前计划信息
    current_plan_info = await db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan)
    )

    # 获取目标计划信息
    target_plan_info = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == data.target_plan,
            SubscriptionPlan.is_active == True,
        )
    )

    if not target_plan_info:
        raise HTTPException(status_code=400, detail="目标计划不存在")

    # 验证是降级
    if current_plan_info:
        current_price = current_plan_info.price_monthly
        target_price = target_plan_info.price_monthly
        if target_price >= current_price and not target_plan_info.is_default:
            raise HTTPException(
                status_code=400, detail="目标计划价格不低于当前计划，请使用升级接口"
            )

    # 确定生效时间
    now = datetime.now()
    effective_at = (
        tenant.plan_expires_at if tenant.plan_expires_at and tenant.plan_expires_at > now else now
    )

    # 检查是否已有待降级请求（无论状态）
    existing = await db.scalar(
        select(PendingPlanChange).where(
            PendingPlanChange.tenant_id == tenant.id,
        )
    )

    if existing:
        # 更新现有请求
        existing.target_plan = data.target_plan
        existing.target_billing_cycle = data.billing_cycle
        existing.effective_at = effective_at
        existing.current_plan = tenant.plan
        existing.status = PendingChangeStatus.PENDING
    else:
        # 创建新请求
        pending = PendingPlanChange(
            tenant_id=tenant.id,
            current_plan=tenant.plan,
            target_plan=data.target_plan,
            target_billing_cycle=data.billing_cycle,
            effective_at=effective_at,
        )
        db.add(pending)

    await db.commit()

    return ApiResponse(
        data=DowngradePreviewResponse(
            current_plan=tenant.plan,
            target_plan=data.target_plan,
            current_plan_name=(current_plan_info.name if current_plan_info else tenant.plan),
            target_plan_name=target_plan_info.name,
            effective_at=effective_at,
            message=f"已预约降级，将在 {effective_at.strftime('%Y-%m-%d')} 生效",
        )
    )


@router.post("/downgrade/cancel", response_model=MessageResponse)
async def cancel_downgrade(
    db: AsyncSession = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """取消降级请求"""
    if not current_user.current_tenant:
        raise HTTPException(status_code=400, detail="当前用户没有租户")

    pending = await db.scalar(
        select(PendingPlanChange).where(
            PendingPlanChange.tenant_id == current_user.current_tenant_id,
            PendingPlanChange.status == PendingChangeStatus.PENDING,
        )
    )

    if not pending:
        raise HTTPException(status_code=404, detail="没有待处理的降级请求")

    pending.status = PendingChangeStatus.CANCELLED
    await db.commit()

    return MessageResponse(msg="已取消降级请求")
