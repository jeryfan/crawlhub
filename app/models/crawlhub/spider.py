import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, DefaultFieldsMixin
from models.types import StringUUID


class ScriptType(str, enum.Enum):
    """脚本类型"""
    HTTPX = "httpx"
    SCRAPY = "scrapy"
    PLAYWRIGHT = "playwright"


class Spider(DefaultFieldsMixin, Base):
    """爬虫定义"""

    __tablename__ = "crawlhub_spiders"

    project_id: Mapped[str] = mapped_column(
        StringUUID, ForeignKey("crawlhub_projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="爬虫名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="爬虫描述")
    script_type: Mapped[ScriptType] = mapped_column(
        Enum(ScriptType), default=ScriptType.HTTPX, comment="脚本类型"
    )
    script_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="脚本内容")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Cron表达式")

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="spiders")
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="spider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Spider {self.name}>"
