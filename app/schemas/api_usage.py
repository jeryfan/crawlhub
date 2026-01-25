from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiUsageItem(BaseModel):
    id: str
    api_key_id: str
    api_key_name: str | None = None
    api_key_prefix: str | None = None
    tenant_id: str
    tenant_name: str | None = None
    endpoint: str
    method: str
    service_type: str
    latency_ms: int
    status_code: int
    error_message: str | None = None
    ip_address: str
    request_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiUsageListResponse(BaseModel):
    items: list[ApiUsageItem]
    total: int
    page: int
    page_size: int


class ApiUsageStats(BaseModel):
    total_requests: int = 0
    avg_latency_ms: float = 0.0
    total_errors: int = 0
    error_rate: float = 0.0


class ApiUsageByEndpoint(BaseModel):
    endpoint: str
    request_count: int
    avg_latency_ms: float


class ApiUsageTrendItem(BaseModel):
    period: str
    request_count: int


class ApiUsageStatsResponse(BaseModel):
    stats: ApiUsageStats
    by_endpoint: list[ApiUsageByEndpoint] | None = None
    trends: list[ApiUsageTrendItem] | None = None


class ApiUsageQueryParams(BaseModel):
    tenant_id: str | None = None
    api_key_id: str | None = None
    endpoint: str | None = None
    service_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ApiUsageStatsParams(BaseModel):
    tenant_id: str | None = None
    api_key_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    granularity: str = Field(default="day")
