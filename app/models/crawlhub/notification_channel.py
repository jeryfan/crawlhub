import enum

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText


class NotificationChannelType(enum.StrEnum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"
    SLACK = "slack"


class NotificationChannelConfig(DefaultFieldsMixin, Base):
    """通知渠道配置"""

    __tablename__ = "crawlhub_notification_channels"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="渠道名称")
    channel_type: Mapped[NotificationChannelType] = mapped_column(
        EnumText(NotificationChannelType), nullable=False, comment="渠道类型"
    )
    config: Mapped[str] = mapped_column(Text, nullable=False, comment="渠道配置 JSON")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    def __repr__(self) -> str:
        return f"<NotificationChannelConfig {self.name} type={self.channel_type}>"
