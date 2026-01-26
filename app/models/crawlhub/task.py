import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, DefaultFieldsMixin
from models.types import StringUUID


class SpiderTaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpiderTask(DefaultFieldsMixin, Base):
    """爬虫任务"""

    __tablename__ = "crawlhub_tasks"

    spider_id: Mapped[str] = mapped_column(
        StringUUID, ForeignKey("crawlhub_spiders.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[SpiderTaskStatus] = mapped_column(
        Enum(SpiderTaskStatus), default=SpiderTaskStatus.PENDING, comment="任务状态"
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度百分比")
    total_count: Mapped[int] = mapped_column(Integer, default=0, comment="总数量")
    success_count: Mapped[int] = mapped_column(Integer, default=0, comment="成功数量")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, comment="失败数量")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Worker ID")
    container_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="容器ID")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # Relationships
    spider: Mapped["Spider"] = relationship("Spider", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<SpiderTask {self.id} status={self.status}>"
