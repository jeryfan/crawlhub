from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import ProjectSource


class SpiderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="爬虫名称")
    description: str | None = Field(None, description="爬虫描述")
    script_content: str | None = Field(None, description="脚本内容")
    is_active: bool = Field(default=True, description="是否启用")
    cron_expr: str | None = Field(None, description="Cron表达式")
    entry_point: str | None = Field(None, description="入口点")
    source: ProjectSource = Field(default=ProjectSource.EMPTY, description="项目来源")
    git_repo: str | None = Field(None, description="Git 仓库地址")
    webhook_url: str | None = Field(None, max_length=500, description="Webhook 回调 URL")
    # 执行配置
    timeout_seconds: int | None = Field(None, description="执行超时(秒)")
    max_items: int | None = Field(None, description="最大采集条数")
    memory_limit_mb: int | None = Field(None, description="内存限制(MB)")
    requirements_txt: str | None = Field(None, description="依赖列表")
    env_vars: str | None = Field(None, description="自定义环境变量 JSON")
    # 代理与限速
    proxy_enabled: bool | None = Field(None, description="启用代理")
    rate_limit_rps: float | None = Field(None, description="请求频率限制(次/秒)")
    autothrottle_enabled: bool | None = Field(None, description="自动限速")
    # 数据去重
    dedup_enabled: bool | None = Field(None, description="启用去重")
    dedup_fields: str | None = Field(None, description="去重字段(逗号分隔)")


class SpiderCreate(SpiderBase):
    project_id: str = Field(..., description="项目ID")


class SpiderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    script_content: str | None = None
    is_active: bool | None = None
    cron_expr: str | None = None
    entry_point: str | None = None
    source: ProjectSource | None = None
    git_repo: str | None = None
    webhook_url: str | None = None
    timeout_seconds: int | None = None
    max_items: int | None = None
    memory_limit_mb: int | None = None
    requirements_txt: str | None = None
    env_vars: str | None = None
    proxy_enabled: bool | None = None
    rate_limit_rps: float | None = None
    autothrottle_enabled: bool | None = None
    dedup_enabled: bool | None = None
    dedup_fields: str | None = None


class SpiderResponse(SpiderBase):
    id: str
    project_id: str
    coder_workspace_id: str | None = None
    coder_workspace_name: str | None = None
    active_deployment_id: str | None = None
    code_sync_status: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpiderListResponse(BaseModel):
    items: list[SpiderResponse]
    total: int
