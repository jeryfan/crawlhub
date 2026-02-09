import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class SpiderTaskStatus(enum.StrEnum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpiderTask(DefaultFieldsMixin, Base):
    """爬虫任务"""

    __tablename__ = "crawlhub_tasks"

    spider_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    status: Mapped[SpiderTaskStatus] = mapped_column(
        EnumText(SpiderTaskStatus), default=SpiderTaskStatus.PENDING, comment="任务状态"
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
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为测试运行")
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual", comment="触发类型: manual/schedule")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="已重试次数")
    max_retries: Mapped[int] = mapped_column(Integer, default=3, comment="最大重试次数")
    # Phase 2-3 扩展字段
    error_category: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="错误分类: network/parse/system/auth"
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后心跳时间"
    )
    checkpoint_data: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="断点数据 JSON"
    )
    items_per_second: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="采集速率"
    )
    peak_memory_mb: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="峰值内存(MB)"
    )

    def __repr__(self) -> str:
        return f"<SpiderTask {self.id} status={self.status}>"
