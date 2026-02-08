from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub.deployment import DeploymentStatus


class DeployRequest(BaseModel):
    deploy_note: str | None = Field(None, max_length=500, description="部署备注")


class DeploymentResponse(BaseModel):
    id: str
    spider_id: str
    version: int
    status: DeploymentStatus
    entry_point: str | None
    file_count: int
    archive_size: int
    deploy_note: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    items: list[DeploymentResponse]
    total: int
