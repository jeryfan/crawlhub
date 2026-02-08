import enum

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import EnumText, StringUUID


class DeploymentStatus(enum.StrEnum):
    """部署状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class Deployment(DefaultFieldsMixin, Base):
    """部署快照"""

    __tablename__ = "crawlhub_deployments"

    spider_id: Mapped[str] = mapped_column(StringUUID, nullable=False, comment="爬虫ID")
    version: Mapped[int] = mapped_column(Integer, nullable=False, comment="版本号")
    status: Mapped[DeploymentStatus] = mapped_column(
        EnumText(DeploymentStatus), default=DeploymentStatus.ACTIVE, comment="部署状态"
    )
    file_archive_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="GridFS 文件ID"
    )
    entry_point: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="入口点"
    )
    file_count: Mapped[int] = mapped_column(Integer, default=0, comment="文件数量")
    archive_size: Mapped[int] = mapped_column(Integer, default=0, comment="包大小(bytes)")
    deploy_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="部署备注")

    def __repr__(self) -> str:
        return f"<Deployment spider={self.spider_id} v{self.version}>"
