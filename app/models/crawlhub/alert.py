import enum

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class AlertLevel(enum.StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Alert(DefaultFieldsMixin, Base):
    """告警记录"""

    __tablename__ = "crawlhub_alerts"

    type: Mapped[str] = mapped_column(String(50), nullable=False, comment="告警类型")
    level: Mapped[AlertLevel] = mapped_column(
        EnumText(AlertLevel), default=AlertLevel.WARNING, comment="告警级别"
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="告警信息")
    spider_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, comment="关联爬虫")
    task_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True, comment="关联任务")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已读")

    def __repr__(self) -> str:
        return f"<Alert {self.type} level={self.level}>"
