from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import SpiderTaskStatus


class TaskResponse(BaseModel):
    id: str
    spider_id: str
    status: SpiderTaskStatus
    progress: int
    total_count: int
    success_count: int
    failed_count: int
    started_at: datetime | None
    finished_at: datetime | None
    worker_id: str | None
    container_id: str | None
    error_message: str | None
    trigger_type: str = "manual"
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class TaskCreate(BaseModel):
    spider_id: str = Field(..., description="爬虫ID")
