import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import UUID, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import EnumText


class TaskStatus(enum.StrEnum):
    """任务状态枚举"""

    PENDING = "pending"  # 等待执行
    STARTED = "started"  # 已开始
    SUCCESS = "success"  # 成功
    FAILURE = "failure"  # 失败
    RETRY = "retry"  # 重试中
    REVOKED = "revoked"  # 已撤销


class TaskType(enum.StrEnum):
    """任务类型枚举"""

    DEFAULT = "default"  # 默认任务
    EMAIL = "email"  # 邮件任务
    IMPORT = "import"  # 导入任务
    EXPORT = "export"  # 导出任务
    REPORT = "report"  # 报告生成任务
    CLEANUP = "cleanup"  # 清理任务


class TaskPriority(enum.IntEnum):
    """任务优先级枚举（数值越大优先级越高）"""

    LOW = 0  # 低优先级
    NORMAL = 5  # 普通优先级（默认）
    HIGH = 10  # 高优先级
    URGENT = 15  # 紧急优先级


class Task(Base):
    """通用任务表"""

    __tablename__ = "tasks"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="task_pkey"),
        sa.Index("task_task_id_idx", "task_id"),
        sa.Index("task_task_type_idx", "task_type"),
        sa.Index("task_status_idx", "status"),
        sa.Index("task_priority_idx", "priority"),
        sa.Index("task_created_at_idx", "created_at"),
        # 复合索引：用于按优先级和状态查询
        sa.Index("task_priority_status_idx", "priority", "status"),
    )

    id: Mapped[str] = mapped_column(UUID, default=uuid.uuid4)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="Celery任务ID")
    task_type: Mapped[TaskType] = mapped_column(
        EnumText(TaskType), nullable=False, comment="任务类型"
    )
    task_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="任务名称")
    status: Mapped[TaskStatus] = mapped_column(
        EnumText(TaskStatus), default=TaskStatus.PENDING, comment="任务状态"
    )
    priority: Mapped[int] = mapped_column(
        sa.Integer,
        default=TaskPriority.NORMAL,
        nullable=False,
        comment="任务优先级(0-15,数值越大优先级越高)",
    )

    # 任务参数和结果
    params: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment='任务参数(JSON格式: {"args": [...], "kwargs": {...}})'
    )
    result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="任务结果(JSON)")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误堆栈")

    # 时间字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
        comment="更新时间",
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )
    duration: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, comment="任务耗时(秒)")

    # 额外信息
    user_id: Mapped[str | None] = mapped_column(UUID, nullable=True, comment="用户ID")
    progress: Mapped[int] = mapped_column(
        sa.Integer, default=0, nullable=False, comment="任务进度(0-100)"
    )
    retry_count: Mapped[int] = mapped_column(
        sa.Integer, default=0, nullable=False, comment="重试次数"
    )
    max_retries: Mapped[int] = mapped_column(
        sa.Integer, default=3, nullable=False, comment="最大重试次数"
    )
