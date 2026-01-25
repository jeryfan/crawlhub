"""账单相关 Schema 定义"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ============ 订阅计划 ============
class SubscriptionPlanItem(BaseModel):
    """订阅计划项"""

    id: str
    name: str
    price_monthly: Decimal = Decimal("0")
    price_yearly: Decimal = Decimal("0")
    discount_percent: int = 0

    # 首月折扣
    first_month_discount_percent: int = 0
    first_month_discount_enabled: bool = False

    # 配额限制
    team_members: int = 1
    apps_limit: int = 10
    api_rate_limit: int = 100

    features: dict | None = None
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanList(BaseModel):
    """订阅计划列表"""

    plans: list[SubscriptionPlanItem]


class SubscriptionPlanCreate(BaseModel):
    """创建订阅计划"""

    id: str = Field(..., max_length=32, description="计划ID，如 basic, pro, max")
    name: str = Field(..., max_length=64, description="计划名称")
    price_monthly: Decimal = Field(default=Decimal("0"), ge=0, description="月付价格")
    price_yearly: Decimal = Field(default=Decimal("0"), ge=0, description="年付价格")
    discount_percent: int = Field(default=0, ge=0, le=100, description="折扣百分比")

    # 首月折扣
    first_month_discount_percent: int = Field(default=0, ge=0, le=100, description="首月折扣百分比")
    first_month_discount_enabled: bool = Field(default=False, description="是否启用首月折扣")

    team_members: int = Field(default=1, ge=0, description="团队成员限制，0表示无限")
    apps_limit: int = Field(default=10, ge=0, description="应用数量限制，0表示无限")
    api_rate_limit: int = Field(default=100, ge=0, description="API速率限制")

    features: dict | None = Field(default=None, description="其他自定义功能")
    description: str | None = Field(default=None, description="计划描述")
    sort_order: int = Field(default=0, description="排序顺序")
    is_active: bool = Field(default=True, description="是否激活")
    is_default: bool = Field(default=False, description="是否为默认计划")


class SubscriptionPlanUpdate(BaseModel):
    """更新订阅计划"""

    name: str | None = Field(default=None, max_length=64, description="计划名称")
    price_monthly: Decimal | None = Field(default=None, ge=0, description="月付价格")
    price_yearly: Decimal | None = Field(default=None, ge=0, description="年付价格")
    discount_percent: int | None = Field(default=None, ge=0, le=100, description="折扣百分比")

    # 首月折扣
    first_month_discount_percent: int | None = Field(
        default=None, ge=0, le=100, description="首月折扣百分比"
    )
    first_month_discount_enabled: bool | None = Field(default=None, description="是否启用首月折扣")

    team_members: int | None = Field(default=None, ge=0, description="团队成员限制")
    apps_limit: int | None = Field(default=None, ge=0, description="应用数量限制")
    api_rate_limit: int | None = Field(default=None, ge=0, description="API速率限制")

    features: dict | None = Field(default=None, description="其他自定义功能")
    description: str | None = Field(default=None, description="计划描述")
    sort_order: int | None = Field(default=None, description="排序顺序")
    is_active: bool | None = Field(default=None, description="是否激活")
    is_default: bool | None = Field(default=None, description="是否为默认计划")


# ============ 当前订阅状态 ============
class SubscriptionUsage(BaseModel):
    """订阅使用量"""

    team_members: int = 0  # 当前团队成员数
    apps_count: int = 0  # 当前应用数量


class PendingDowngradeInfo(BaseModel):
    """待降级信息"""

    target_plan: str
    target_plan_name: str
    effective_at: datetime


class CurrentSubscription(BaseModel):
    """当前订阅状态"""

    plan: str
    plan_name: str
    balance: Decimal
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_auto_renew: bool = True
    days_remaining: int | None = None
    billing_cycle: str | None = None  # monthly / yearly
    usage: SubscriptionUsage = Field(default_factory=SubscriptionUsage)
    pending_downgrade: PendingDowngradeInfo | None = None  # 待降级信息


# ============ 充值相关 ============
class RechargeRequest(BaseModel):
    """充值请求"""

    amount: Decimal = Field(..., gt=0, description="充值金额")
    payment_method: str = Field(..., pattern="^(wechat|alipay)$", description="支付方式")


class RechargeOrderResponse(BaseModel):
    """充值订单响应"""

    id: str
    amount: Decimal
    payment_method: str
    qr_code_url: str | None = None
    expired_at: datetime
    status: str
    out_trade_no: str | None = None


class RechargeOrderItem(BaseModel):
    """充值订单列表项"""

    id: str
    amount: Decimal
    payment_method: str
    status: str
    trade_no: str | None = None
    paid_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RechargeOrderDetail(RechargeOrderItem):
    """充值订单详情"""

    out_trade_no: str
    qr_code_url: str | None = None
    expired_at: datetime


# ============ 订阅相关 ============
class SubscribeRequest(BaseModel):
    """订阅请求"""

    plan: str = Field(..., description="订阅计划")
    billing_cycle: str = Field(
        default="monthly", pattern="^(monthly|yearly)$", description="计费周期"
    )
    auto_renew: bool = Field(default=True, description="是否自动续费")


class SubscriptionOrderItem(BaseModel):
    """订阅订单列表项"""

    id: str
    plan: str
    price: Decimal
    status: str
    starts_at: datetime
    expires_at: datetime
    is_auto_renew: bool
    order_type: str = "new"  # new/renew/upgrade/downgrade
    previous_plan: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 升级/降级相关 ============
class UpgradePreviewRequest(BaseModel):
    """升级预览请求"""

    target_plan: str = Field(..., description="目标计划ID")
    billing_cycle: str = Field(
        default="monthly", pattern="^(monthly|yearly)$", description="计费周期"
    )


class UpgradePreviewResponse(BaseModel):
    """升级预览响应"""

    current_plan: str
    target_plan: str
    current_plan_name: str
    target_plan_name: str
    remaining_days: int
    remaining_value: Decimal  # 当前计划剩余价值
    new_plan_cost: Decimal  # 新计划剩余周期费用
    difference: Decimal  # 需要支付的差价
    billing_cycle: str
    effective_immediately: bool = True


class UpgradeRequest(BaseModel):
    """升级请求"""

    target_plan: str = Field(..., description="目标计划ID")
    billing_cycle: str = Field(
        default="monthly", pattern="^(monthly|yearly)$", description="计费周期"
    )


class DowngradeRequest(BaseModel):
    """降级请求"""

    target_plan: str = Field(..., description="目标计划ID")
    billing_cycle: str = Field(
        default="monthly", pattern="^(monthly|yearly)$", description="计费周期"
    )


class DowngradePreviewResponse(BaseModel):
    """降级预览响应"""

    current_plan: str
    target_plan: str
    current_plan_name: str
    target_plan_name: str
    effective_at: datetime  # 生效时间
    message: str


# ============ 余额变动 ============
class BalanceLogItem(BaseModel):
    """余额变动记录项"""

    id: str
    type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    remark: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 管理端扩展 ============
class RechargeOrderAdminItem(RechargeOrderItem):
    """管理端充值订单列表项"""

    tenant_id: str
    tenant_name: str | None = None
    account_id: str | None = None
    account_name: str | None = None


class SubscriptionOrderAdminItem(SubscriptionOrderItem):
    """管理端订阅订单列表项"""

    tenant_id: str
    tenant_name: str | None = None
    account_id: str | None = None
    account_name: str | None = None
    billing_cycle: str | None = None


class BalanceLogAdminItem(BalanceLogItem):
    """管理端余额变动记录项"""

    tenant_id: str
    tenant_name: str | None = None
    operator_name: str | None = None
    account_id: str | None = None
    account_name: str | None = None


class AdjustBalanceRequest(BaseModel):
    """调整余额请求"""

    amount: Decimal = Field(..., description="调整金额（正增负减）")
    remark: str = Field(..., min_length=1, max_length=255, description="备注")


class UpdatePlanRequest(BaseModel):
    """修改订阅计划请求"""

    plan: str = Field(..., pattern="^(basic|pro|max)$", description="目标计划")
    expires_at: datetime | None = Field(default=None, description="到期时间（可选）")


# ============ 统计相关 ============
class BillingStats(BaseModel):
    """账单统计数据"""

    total_recharge_amount: Decimal = Decimal("0")
    total_subscription_revenue: Decimal = Decimal("0")
    active_subscriptions: int = 0
    pending_orders: int = 0
