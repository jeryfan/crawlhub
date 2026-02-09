import enum

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin
from models.types import AdjustedJSON, EnumText


class DataSourceType(enum.StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class DataSourceMode(enum.StrEnum):
    EXTERNAL = "external"
    MANAGED = "managed"


class DataSourceStatus(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CREATING = "creating"
    ERROR = "error"


class DataSource(DefaultFieldsMixin, Base):
    """外部数据源"""

    __tablename__ = "crawlhub_datasources"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据源名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    type: Mapped[DataSourceType] = mapped_column(
        EnumText(DataSourceType), nullable=False, comment="数据库类型"
    )
    mode: Mapped[DataSourceMode] = mapped_column(
        EnumText(DataSourceMode), default=DataSourceMode.EXTERNAL, comment="连接模式"
    )
    status: Mapped[DataSourceStatus] = mapped_column(
        EnumText(DataSourceStatus), default=DataSourceStatus.ACTIVE, comment="状态"
    )

    # 连接信息
    host: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="主机地址")
    port: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="端口")
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="用户名")
    password: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="密码")
    database: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="数据库名")
    connection_options: Mapped[dict | None] = mapped_column(
        AdjustedJSON, nullable=True, comment="连接选项(SSL/charset等)"
    )

    # Docker 托管字段
    container_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="容器ID")
    container_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="容器名称")
    docker_image: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Docker镜像")
    mapped_port: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="宿主机映射端口")
    volume_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="数据卷路径")

    # 健康检查
    last_check_at: Mapped[str | None] = mapped_column(DateTime, nullable=True, comment="最后检查时间")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最后错误信息")

    def __repr__(self) -> str:
        return f"<DataSource {self.name} ({self.type})>"
