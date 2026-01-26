from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import TaskStatus


class TaskResponse(BaseModel):
    id: str
    spider_id: str
    status: TaskStatus
    progress: int
    total_count: int
    success_count: int
    failed_count: int
    started_at: datetime | None
    finished_at: datetime | None
    worker_id: str | None
    container_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class TaskCreate(BaseModel):
    spider_id: str = Field(..., description="爬虫ID")
