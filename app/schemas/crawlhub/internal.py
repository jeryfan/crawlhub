from pydantic import BaseModel, Field


class ItemsIngestRequest(BaseModel):
    task_id: str
    spider_id: str
    items: list[dict] = Field(..., min_length=1, max_length=1000)


class ProgressReport(BaseModel):
    task_id: str
    progress: int = Field(..., ge=0, le=100)
    message: str | None = None


class HeartbeatReport(BaseModel):
    task_id: str
    memory_mb: float | None = None
    items_count: int | None = None


class CheckpointSave(BaseModel):
    task_id: str
    checkpoint_data: dict


class CheckpointQuery(BaseModel):
    spider_id: str
