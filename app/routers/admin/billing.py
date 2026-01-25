from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from dependencies.auth import get_current_admin
from models.account import Account, Tenant
from models.admin import Admin
from models.billing import (
    BalanceLog,
    BalanceLogType,
    RechargeOrder,
    RechargeOrderStatus,
    SubscriptionOrder,
    SubscriptionOrderStatus,
    SubscriptionPlan,
)
from schemas.billing import (
    AdjustBalanceRequest,
    BalanceLogAdminItem,
    BillingStats,
    RechargeOrderAdminItem,
    SubscriptionOrderAdminItem,
    SubscriptionPlanCreate,
    SubscriptionPlanItem,
    SubscriptionPlanUpdate,
    UpdatePlanRequest,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse

router = APIRouter(tags=["Platform - Billing"])


# ============ 充值订单管理 ============
@router.get(
    "/recharge-orders",
    response_model=ApiResponse[PaginatedResponse[RechargeOrderAdminItem]],
)
async def list_recharge_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="搜索关键词（订单号/租户名称）"),
    status: str | None = Query(None, description="订单状态"),
    payment_method: str | None = Query(None, description="支付方式"),
    start_date: datetime | None = Query(None, description="开始日期"),
    end_date: datetime | None = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取充值订单列表"""
    # 基础查询
    query = (
        select(
            RechargeOrder,
            Tenant.name.label("tenant_name"),
            Account.name.label("account_name"),
        )
        .outerjoin(Tenant, RechargeOrder.tenant_id == Tenant.id)
        .outerjoin(Account, RechargeOrder.account_id == Account.id)
    )

    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                RechargeOrder.out_trade_no.ilike(f"%{keyword}%"),
                Tenant.name.ilike(f"%{keyword}%"),
                Account.name.ilike(f"%{keyword}%"),
            )
        )

    # 状态筛选
    if status:
        query = query.where(RechargeOrder.status == status)

    # 支付方式筛选
    if payment_method:
        query = query.where(RechargeOrder.payment_method == payment_method)

    # 日期范围筛选
    if start_date:
        query = query.where(RechargeOrder.created_at >= start_date)
    if end_date:
        query = query.where(RechargeOrder.created_at <= end_date)

    # 统计总数
    count_subquery = query.subquery()
    count_query = select(func.count()).select_from(count_subquery)
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(RechargeOrder.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        order = row[0]
        tenant_name = row[1]
        account_name = row[2]
        items.append(
            RechargeOrderAdminItem(
                id=order.id,
                tenant_id=order.tenant_id,
                tenant_name=tenant_name,
                account_id=order.account_id,
                account_name=account_name,
                amount=order.amount,
                payment_method=order.payment_method,
                status=order.status,
                trade_no=order.trade_no,
                paid_at=order.paid_at,
                created_at=order.created_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/recharge-orders/{order_id}", response_model=ApiResponse[RechargeOrderAdminItem])
async def get_recharge_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取充值订单详情"""
    order = await db.get(RechargeOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    tenant = await db.get(Tenant, order.tenant_id)
    account = await db.get(Account, order.account_id) if order.account_id else None

    return ApiResponse(
        data=RechargeOrderAdminItem(
            id=order.id,
            tenant_id=order.tenant_id,
            tenant_name=tenant.name if tenant else None,
            account_id=order.account_id,
            account_name=account.name if account else None,
            amount=order.amount,
            payment_method=order.payment_method,
            status=order.status,
            trade_no=order.trade_no,
            paid_at=order.paid_at,
            created_at=order.created_at,
        )
    )


# ============ 订阅订单管理 ============
@router.get(
    "/subscription-orders",
    response_model=ApiResponse[PaginatedResponse[SubscriptionOrderAdminItem]],
)
async def list_subscription_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="搜索关键词（租户名称）"),
    plan: str | None = Query(None, description="订阅计划"),
    status: str | None = Query(None, description="订单状态"),
    order_type: str | None = Query(None, description="订单类型（new/renew/upgrade/downgrade）"),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取订阅订单列表"""
    query = (
        select(
            SubscriptionOrder,
            Tenant.name.label("tenant_name"),
            Account.name.label("account_name"),
        )
        .outerjoin(Tenant, SubscriptionOrder.tenant_id == Tenant.id)
        .outerjoin(Account, SubscriptionOrder.account_id == Account.id)
    )

    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                Tenant.name.ilike(f"%{keyword}%"),
                Account.name.ilike(f"%{keyword}%"),
            )
        )

    # 计划筛选
    if plan:
        query = query.where(SubscriptionOrder.plan == plan)

    # 状态筛选
    if status:
        query = query.where(SubscriptionOrder.status == status)

    # 订单类型筛选
    if order_type:
        query = query.where(SubscriptionOrder.order_type == order_type)

    # 统计总数
    count_subquery = query.subquery()
    count_query = select(func.count()).select_from(count_subquery)
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(SubscriptionOrder.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        order = row[0]
        tenant_name = row[1]
        account_name = row[2]
        items.append(
            SubscriptionOrderAdminItem(
                id=order.id,
                tenant_id=order.tenant_id,
                tenant_name=tenant_name,
                account_id=order.account_id,
                account_name=account_name,
                plan=order.plan,
                price=order.price,
                status=order.status,
                starts_at=order.starts_at,
                expires_at=order.expires_at,
                is_auto_renew=order.is_auto_renew,
                order_type=order.order_type,
                billing_cycle=order.billing_cycle,
                created_at=order.created_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


# ============ 余额变动记录 ============
@router.get("/balance-logs", response_model=ApiResponse[PaginatedResponse[BalanceLogAdminItem]])
async def list_balance_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: str | None = Query(None, description="租户ID"),
    log_type: str | None = Query(None, description="变动类型"),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取余额变动记录"""
    query = (
        select(
            BalanceLog,
            Tenant.name.label("tenant_name"),
            Admin.name.label("operator_name"),
            Account.name.label("account_name"),
        )
        .outerjoin(Tenant, BalanceLog.tenant_id == Tenant.id)
        .outerjoin(Admin, BalanceLog.operator_id == Admin.id)
        .outerjoin(Account, BalanceLog.account_id == Account.id)
    )

    # 租户筛选
    if tenant_id:
        query = query.where(BalanceLog.tenant_id == tenant_id)

    # 类型筛选
    if log_type:
        query = query.where(BalanceLog.type == log_type)

    # 统计总数
    count_subquery = query.subquery()
    count_query = select(func.count()).select_from(count_subquery)
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(BalanceLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        log = row[0]
        tenant_name = row[1]
        operator_name = row[2]
        account_name = row[3]
        items.append(
            BalanceLogAdminItem(
                id=log.id,
                tenant_id=log.tenant_id,
                tenant_name=tenant_name,
                type=log.type,
                amount=log.amount,
                balance_before=log.balance_before,
                balance_after=log.balance_after,
                remark=log.remark,
                operator_name=operator_name,
                account_id=log.account_id,
                account_name=account_name,
                created_at=log.created_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


# ============ 租户余额/计划管理 ============
@router.patch("/tenants/{tenant_id}/balance", response_model=ApiResponse[dict])
async def adjust_tenant_balance(
    tenant_id: str,
    data: AdjustBalanceRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """调整租户余额"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 检查调整后余额不能为负
    new_balance = tenant.balance + data.amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="调整后余额不能为负数")

    # 记录余额变动
    balance_log = BalanceLog(
        tenant_id=tenant.id,
        type=BalanceLogType.ADMIN_ADJUST,
        amount=data.amount,
        balance_before=tenant.balance,
        balance_after=new_balance,
        remark=data.remark,
        operator_id=current_admin.id,
    )
    db.add(balance_log)

    # 更新余额
    tenant.balance = new_balance

    await db.commit()

    return ApiResponse(
        msg=f"余额调整成功，当前余额: ¥{new_balance}",
        data={"balance": float(new_balance)},
    )


@router.patch("/tenants/{tenant_id}/plan", response_model=ApiResponse[dict])
async def update_tenant_plan(
    tenant_id: str,
    data: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """修改租户订阅计划"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    tenant.plan = data.plan
    if data.expires_at:
        tenant.plan_expires_at = data.expires_at
    elif data.plan == "basic":
        tenant.plan_expires_at = None
    else:
        # 默认设置为30天后过期
        tenant.plan_expires_at = datetime.utcnow() + timedelta(days=30)

    await db.commit()

    return ApiResponse(
        msg=f"计划已更新为 {data.plan.upper()}",
        data={
            "plan": tenant.plan,
            "plan_expires_at": (
                tenant.plan_expires_at.isoformat() if tenant.plan_expires_at else None
            ),
        },
    )


# ============ 统计数据 ============
@router.get("/billing/stats", response_model=ApiResponse[BillingStats])
async def get_billing_stats(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取账单统计数据"""
    # 总充值金额 (所有已支付)
    total_recharge = await db.scalar(
        select(func.coalesce(func.sum(RechargeOrder.amount), 0)).where(
            RechargeOrder.status == RechargeOrderStatus.PAID
        )
    ) or Decimal("0")

    # 订阅收入 (生效中 + 已过期)
    total_subscription_revenue = await db.scalar(
        select(func.coalesce(func.sum(SubscriptionOrder.price), 0)).where(
            SubscriptionOrder.status.in_(
                [SubscriptionOrderStatus.ACTIVE, SubscriptionOrderStatus.EXPIRED]
            )
        )
    ) or Decimal("0")

    # 活跃订阅数
    active_subscriptions = (
        await db.scalar(
            select(func.count()).where(SubscriptionOrder.status == SubscriptionOrderStatus.ACTIVE)
        )
        or 0
    )

    # 待支付订单数
    pending_orders = (
        await db.scalar(
            select(func.count()).where(RechargeOrder.status == RechargeOrderStatus.PENDING)
        )
        or 0
    )

    return ApiResponse(
        data=BillingStats(
            total_recharge_amount=total_recharge,
            total_subscription_revenue=total_subscription_revenue,
            active_subscriptions=active_subscriptions,
            pending_orders=pending_orders,
        )
    )


# ============ 订阅计划管理 ============
@router.get("/subscription-plans", response_model=ApiResponse[list[SubscriptionPlanItem]])
async def list_subscription_plans(
    include_inactive: bool = Query(False, description="是否包含未激活的计划"),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取所有订阅计划"""
    query = select(SubscriptionPlan)
    if not include_inactive:
        query = query.where(SubscriptionPlan.is_active == True)
    query = query.order_by(SubscriptionPlan.sort_order.asc())

    result = await db.execute(query)
    plans = result.scalars().all()

    return ApiResponse(data=[SubscriptionPlanItem.model_validate(plan) for plan in plans])


@router.get("/subscription-plans/{plan_id}", response_model=ApiResponse[SubscriptionPlanItem])
async def get_subscription_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """获取单个订阅计划详情"""
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="订阅计划不存在")

    return ApiResponse(data=SubscriptionPlanItem.model_validate(plan))


@router.post("/subscription-plans", response_model=ApiResponse[SubscriptionPlanItem])
async def create_subscription_plan(
    data: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """创建新的订阅计划"""
    # 检查ID是否已存在
    existing = await db.get(SubscriptionPlan, data.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"计划ID '{data.id}' 已存在")

    # 如果设置为默认计划，取消其他默认计划
    if data.is_default:
        await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_default == True))
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.is_default == True)
        )
        for plan in result.scalars().all():
            plan.is_default = False

    plan = SubscriptionPlan(
        id=data.id,
        name=data.name,
        price_monthly=data.price_monthly,
        price_yearly=data.price_yearly,
        discount_percent=data.discount_percent,
        first_month_discount_percent=data.first_month_discount_percent,
        first_month_discount_enabled=data.first_month_discount_enabled,
        team_members=data.team_members,
        apps_limit=data.apps_limit,
        api_rate_limit=data.api_rate_limit,
        features=data.features,
        description=data.description,
        sort_order=data.sort_order,
        is_active=data.is_active,
        is_default=data.is_default,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return ApiResponse(data=SubscriptionPlanItem.model_validate(plan))


@router.put("/subscription-plans/{plan_id}", response_model=ApiResponse[SubscriptionPlanItem])
async def update_subscription_plan(
    plan_id: str,
    data: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """更新订阅计划"""
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="订阅计划不存在")

    # 如果设置为默认计划，取消其他默认计划
    if data.is_default is True and not plan.is_default:
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.is_default == True)
        )
        for other_plan in result.scalars().all():
            other_plan.is_default = False

    # 更新非空字段
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)

    return ApiResponse(data=SubscriptionPlanItem.model_validate(plan))


@router.delete("/subscription-plans/{plan_id}", response_model=ApiResponse[dict])
async def delete_subscription_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """删除订阅计划"""
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="订阅计划不存在")

    # 检查是否有租户正在使用该计划
    tenant_count = await db.scalar(select(func.count()).where(Tenant.plan == plan_id))
    if tenant_count and tenant_count > 0:
        raise HTTPException(
            status_code=400, detail=f"该计划正在被 {tenant_count} 个租户使用，无法删除"
        )

    await db.delete(plan)
    await db.commit()

    return ApiResponse(msg=f"订阅计划 '{plan_id}' 已删除", data={"id": plan_id})


@router.post("/subscription-plans/init-default", response_model=ApiResponse[dict])
async def init_default_plans(
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """初始化默认订阅计划（basic, pro, max）"""
    default_plans = [
        {
            "id": "basic",
            "name": "Basic",
            "price_monthly": Decimal("0"),
            "price_yearly": Decimal("0"),
            "team_members": 1,
            "apps_limit": 10,
            "api_rate_limit": 100,
            "sort_order": 0,
            "is_active": True,
            "is_default": True,
        },
        {
            "id": "pro",
            "name": "Professional",
            "price_monthly": Decimal("99"),
            "price_yearly": Decimal("999"),
            "discount_percent": 15,
            "team_members": 10,
            "apps_limit": 50,
            "api_rate_limit": 1000,
            "sort_order": 1,
            "is_active": True,
            "is_default": False,
        },
        {
            "id": "max",
            "name": "Enterprise Max",
            "price_monthly": Decimal("299"),
            "price_yearly": Decimal("2999"),
            "discount_percent": 20,
            "team_members": 0,  # 无限
            "apps_limit": 0,  # 无限
            "api_rate_limit": 0,  # 无限
            "sort_order": 2,
            "is_active": True,
            "is_default": False,
        },
    ]

    created_count = 0
    updated_count = 0

    for plan_data in default_plans:
        existing = await db.get(SubscriptionPlan, plan_data["id"])
        if existing:
            # 更新现有计划
            for key, value in plan_data.items():
                if key != "id":
                    setattr(existing, key, value)
            updated_count += 1
        else:
            # 创建新计划
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)
            created_count += 1

    await db.commit()

    return ApiResponse(
        msg=f"初始化完成：创建 {created_count} 个计划，更新 {updated_count} 个计划",
        data={"created": created_count, "updated": updated_count},
    )
