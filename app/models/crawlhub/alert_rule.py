import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class AlertRuleType(enum.StrEnum):
    TASK_FAILURE_RATE = "task_failure_rate"
    TASK_DURATION = "task_duration"
    ITEMS_COUNT = "items_count"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"


class AlertRule(DefaultFieldsMixin, Base):
    """告警规则"""

    __tablename__ = "crawlhub_alert_rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="规则名称")
    rule_type: Mapped[AlertRuleType] = mapped_column(
        EnumText(AlertRuleType), nullable=False, comment="规则类型"
    )
    condition: Mapped[str] = mapped_column(
        Text, nullable=False, comment="规则条件 JSON"
    )
    notification_channel_id: Mapped[str | None] = mapped_column(
        StringUUID, nullable=True, comment="通知渠道ID"
    )
    spider_id: Mapped[str | None] = mapped_column(
        StringUUID, nullable=True, comment="关联爬虫ID，null表示全部"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, default=30, comment="冷却时间（分钟）"
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="上次触发时间"
    )

    def __repr__(self) -> str:
        return f"<AlertRule {self.name} type={self.rule_type}>"
