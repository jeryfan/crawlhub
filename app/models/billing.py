"""账单相关数据模型"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, Numeric, String, Text, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import StringUUID


class RechargeOrderStatus(StrEnum):
    """充值订单状态"""

    PENDING = "pending"  # 待支付
    PAID = "paid"  # 已支付
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期


class SubscriptionOrderStatus(StrEnum):
    """订阅订单状态"""

    ACTIVE = "active"  # 生效中
    EXPIRED = "expired"  # 已过期
    CANCELLED = "cancelled"  # 已取消
    PENDING = "pending"  # 待生效（用于降级订单）


class SubscriptionOrderType(StrEnum):
    """订阅订单类型"""

    NEW = "new"  # 新订阅
    RENEW = "renew"  # 续费
    UPGRADE = "upgrade"  # 升级
    DOWNGRADE = "downgrade"  # 降级


class BalanceLogType(StrEnum):
    """余额变动类型"""

    RECHARGE = "recharge"  # 充值
    SUBSCRIBE = "subscribe"  # 订阅扣款
    REFUND = "refund"  # 退款
    ADMIN_ADJUST = "admin_adjust"  # 管理员调整
    UPGRADE_CHARGE = "upgrade_charge"  # 升级扣款


class PaymentMethod(StrEnum):
    """支付方式"""

    WECHAT = "wechat"
    ALIPAY = "alipay"


class SubscriptionPlan(Base):
    """订阅计划配置表"""

    __tablename__ = "subscription_plans"
    __table_args__ = (sa.PrimaryKeyConstraint("id", name="subscription_plan_pkey"),)

    id: Mapped[str] = mapped_column(String(32))  # basic, pro, max
    name: Mapped[str] = mapped_column(String(64))

    # 价格相关
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # 月付价格
    price_yearly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # 年付价格
    discount_percent: Mapped[int] = mapped_column(Integer, default=0)  # 折扣百分比 (0-100)

    # 首月折扣
    first_month_discount_percent: Mapped[int] = mapped_column(
        Integer, default=0
    )  # 首月折扣百分比 (0-100)
    first_month_discount_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # 是否启用首月折扣

    # 配额限制
    team_members: Mapped[int] = mapped_column(Integer, default=1)  # 团队成员数量限制，0 表示无限
    apps_limit: Mapped[int] = mapped_column(Integer, default=10)  # 应用数量限制，0 表示无限
    api_rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # API 速率限制（每分钟）

    # 其他配置
    features: Mapped[dict | None] = mapped_column(JSONB, default=None)  # 其他自定义功能
    description: Mapped[str | None] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否为默认计划

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class RechargeOrder(Base):
    """充值订单表"""

    __tablename__ = "recharge_orders"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="recharge_order_pkey"),
        sa.Index("recharge_order_tenant_id_idx", "tenant_id"),
        sa.Index("recharge_order_status_idx", "status"),
        sa.Index("recharge_order_trade_no_idx", "trade_no"),
    )

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    account_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_method: Mapped[str] = mapped_column(String(16))  # wechat / alipay
    status: Mapped[str] = mapped_column(String(16), default=RechargeOrderStatus.PENDING)
    trade_no: Mapped[str | None] = mapped_column(String(64), default=None)  # 平台交易号
    out_trade_no: Mapped[str] = mapped_column(String(64))  # 商户订单号
    qr_code_url: Mapped[str | None] = mapped_column(Text, default=None)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    expired_at: Mapped[datetime] = mapped_column(DateTime)  # 订单过期时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )


class SubscriptionOrder(Base):
    """订阅订单表"""

    __tablename__ = "subscription_orders"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="subscription_order_pkey"),
        sa.Index("subscription_order_tenant_id_idx", "tenant_id"),
        sa.Index("subscription_order_status_idx", "status"),
        sa.Index("subscription_order_type_idx", "order_type"),
    )

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    account_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    plan: Mapped[str] = mapped_column(String(32))  # pro / max
    billing_cycle: Mapped[str] = mapped_column(String(16), default="monthly")  # monthly / yearly
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # 实际支付金额
    status: Mapped[str] = mapped_column(String(16), default=SubscriptionOrderStatus.ACTIVE)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)

    # 新增字段：订单类型和抵扣信息
    order_type: Mapped[str] = mapped_column(
        String(16), default=SubscriptionOrderType.NEW
    )  # 订单类型
    original_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # 原价
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0")
    )  # 折扣金额
    prorated_credit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0")
    )  # 按比例抵扣金额
    previous_plan: Mapped[str | None] = mapped_column(
        String(32), default=None
    )  # 之前的计划（升级/降级时记录）
    is_first_month_discount: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # 是否使用了首月折扣

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )


class BalanceLog(Base):
    """余额变动记录表"""

    __tablename__ = "balance_logs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="balance_log_pkey"),
        sa.Index("balance_log_tenant_id_idx", "tenant_id"),
        sa.Index("balance_log_type_idx", "type"),
    )

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    account_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # 变动金额（正增负减）
    balance_before: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    related_order_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    remark: Mapped[str | None] = mapped_column(String(255), default=None)
    operator_id: Mapped[str | None] = mapped_column(StringUUID, default=None)  # 管理员ID
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )


class PendingChangeStatus(StrEnum):
    """待执行计划变更状态"""

    PENDING = "pending"  # 待执行
    EXECUTED = "executed"  # 已执行
    CANCELLED = "cancelled"  # 已取消


class PendingPlanChange(Base):
    """待执行的计划变更（用于降级）"""

    __tablename__ = "pending_plan_changes"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pending_plan_change_pkey"),
        sa.Index("pending_plan_change_tenant_id_idx", "tenant_id"),
        sa.Index("pending_plan_change_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        StringUUID, unique=True
    )  # 每个租户只能有一个待执行的变更
    current_plan: Mapped[str] = mapped_column(String(32))  # 当前计划
    target_plan: Mapped[str] = mapped_column(String(32))  # 目标计划
    target_billing_cycle: Mapped[str] = mapped_column(String(16), default="monthly")
    effective_at: Mapped[datetime] = mapped_column(DateTime)  # 生效时间（当前订阅到期时）
    status: Mapped[str] = mapped_column(String(16), default=PendingChangeStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
