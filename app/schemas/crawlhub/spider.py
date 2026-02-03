from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import ScriptType, ProjectType, ProjectSource


class SpiderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="爬虫名称")
    description: str | None = Field(None, description="爬虫描述")
    script_type: ScriptType = Field(default=ScriptType.HTTPX, description="脚本类型")
    script_content: str | None = Field(None, description="脚本内容")
    is_active: bool = Field(default=True, description="是否启用")
    cron_expr: str | None = Field(None, description="Cron表达式")
    project_type: ProjectType = Field(default=ProjectType.SINGLE_FILE, description="项目类型")
    entry_point: str | None = Field(None, description="入口点")
    source: ProjectSource = Field(default=ProjectSource.EMPTY, description="项目来源")
    git_repo: str | None = Field(None, description="Git 仓库地址")


class SpiderCreate(SpiderBase):
    project_id: str = Field(..., description="项目ID")


class SpiderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    script_type: ScriptType | None = None
    script_content: str | None = None
    is_active: bool | None = None
    cron_expr: str | None = None
    project_type: ProjectType | None = None
    entry_point: str | None = None
    source: ProjectSource | None = None
    git_repo: str | None = None


class SpiderResponse(SpiderBase):
    id: str
    project_id: str
    coder_workspace_id: str | None = None
    coder_workspace_name: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpiderListResponse(BaseModel):
    items: list[SpiderResponse]
    total: int
