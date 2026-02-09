from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import StringUUID


class SpiderDataSource(DefaultFieldsMixin, Base):
    """爬虫-数据源关联（多对多）"""

    __tablename__ = "crawlhub_spider_datasources"

    spider_id: Mapped[str] = mapped_column(StringUUID, nullable=False, index=True, comment="爬虫ID")
    datasource_id: Mapped[str] = mapped_column(StringUUID, nullable=False, index=True, comment="数据源ID")
    target_table: Mapped[str] = mapped_column(String(255), nullable=False, comment="目标表名/集合名")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    def __repr__(self) -> str:
        return f"<SpiderDataSource spider={self.spider_id} ds={self.datasource_id}>"
