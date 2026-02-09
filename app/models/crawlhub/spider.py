import enum

from sqlalchemy import Boolean, Float, Integer, String, Text
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
    start_url: Mapped[str | None] = mapped_column(String(2000), nullable=True, comment="目标抓取URL")
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
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Webhook 回调 URL")
    active_deployment_id: Mapped[str | None] = mapped_column(
        StringUUID, nullable=True, comment="当前活跃部署ID"
    )
    code_sync_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="代码同步状态: syncing/synced/failed"
    )
    # 执行配置
    timeout_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True, server_default="300", comment="执行超时(秒)"
    )
    max_items: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="最大采集条数"
    )
    memory_limit_mb: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="内存限制(MB)"
    )
    requirements_txt: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="依赖列表"
    )
    env_vars: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="自定义环境变量 JSON"
    )
    # 代理与限速
    proxy_enabled: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="false", comment="启用代理"
    )
    rate_limit_rps: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="请求频率限制(次/秒)"
    )
    autothrottle_enabled: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="false", comment="自动限速"
    )
    # 数据去重
    dedup_enabled: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, server_default="false", comment="启用去重"
    )
    dedup_fields: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="去重字段(逗号分隔)"
    )

    def __repr__(self) -> str:
        return f"<Spider {self.name}>"
