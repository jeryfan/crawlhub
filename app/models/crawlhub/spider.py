import enum

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class ProjectSource(enum.StrEnum):
    """项目来源"""
    EMPTY = "empty"
    SCRAPY = "scrapy"
    GIT = "git"
    UPLOAD = "upload"


class Spider(DefaultFieldsMixin, Base):
    """爬虫定义"""

    __tablename__ = "crawlhub_spiders"

    project_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="爬虫名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="爬虫描述")
    script_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="脚本内容")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Cron表达式")
    entry_point: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="入口点")
    # Coder 工作区相关
    source: Mapped[ProjectSource] = mapped_column(
        EnumText(ProjectSource), default=ProjectSource.EMPTY, comment="项目来源"
    )
    git_repo: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Git 仓库地址")
    coder_workspace_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Coder 工作区 ID"
    )
    coder_workspace_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Coder 工作区名称"
    )

    def __repr__(self) -> str:
        return f"<Spider {self.name}>"
