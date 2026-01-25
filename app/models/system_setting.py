from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SystemSetting(Base):
    """系统配置表，使用 key-value 结构存储系统级配置"""

    __tablename__ = "system_settings"
    __table_args__ = (sa.PrimaryKeyConstraint("key", name="system_setting_pkey"),)

    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
        onupdate=func.current_timestamp(),
    )
