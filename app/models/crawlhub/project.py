from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin


class Project(DefaultFieldsMixin, Base):
    """爬虫项目"""

    __tablename__ = "crawlhub_projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")

    def __repr__(self) -> str:
        return f"<Project {self.name}>"
