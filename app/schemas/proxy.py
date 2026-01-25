from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProxyRouteBase(BaseModel):
    """Base schema for proxy route."""

    path: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Route path pattern, e.g., /chat/completions",
    )
    target_urls: list[str] = Field(
        ...,
        min_length=1,
        description="Target URLs for load balancing or failover",
    )
    load_balance_mode: str = Field(
        default="failover",
        description="Load balance mode: round_robin or failover",
    )
    methods: str = Field(
        default="*",
        max_length=128,
        description="Allowed HTTP methods, comma-separated or * for all",
    )
    description: str | None = Field(
        default=None,
        max_length=1024,
        description="Route description",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    preserve_host: bool = Field(
        default=False,
        description="Whether to preserve the original Host header",
    )
    enable_logging: bool = Field(
        default=True,
        description="Whether to log requests for this route",
    )
    streaming: bool = Field(
        default=True,
        description="Whether to use streaming mode for responses (recommended for SSE/large files)",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.startswith("/"):
            v = "/" + v
        return v.rstrip("/") or "/"

    @field_validator("target_urls")
    @classmethod
    def validate_target_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one target URL is required")
        validated = []
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Target URL must start with http:// or https://: {url}")
            validated.append(url.rstrip("/"))
        return validated

    @field_validator("load_balance_mode")
    @classmethod
    def validate_load_balance_mode(cls, v: str) -> str:
        if v not in ("round_robin", "failover"):
            raise ValueError("Load balance mode must be 'round_robin' or 'failover'")
        return v

    @field_validator("methods")
    @classmethod
    def validate_methods(cls, v: str) -> str:
        if v == "*":
            return v
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        methods = [m.strip().upper() for m in v.split(",")]
        for m in methods:
            if m not in valid_methods:
                raise ValueError(f"Invalid HTTP method: {m}")
        return ",".join(methods)


class ProxyRouteCreate(ProxyRouteBase):
    """Schema for creating a proxy route."""

    pass


class ProxyRouteUpdate(BaseModel):
    """Schema for updating a proxy route."""

    path: str | None = Field(default=None, min_length=1, max_length=512)
    target_urls: list[str] | None = Field(default=None)
    load_balance_mode: str | None = Field(default=None)
    methods: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None)
    description: str | None = Field(default=None, max_length=1024)
    timeout: int | None = Field(default=None, ge=1, le=300)
    preserve_host: bool | None = Field(default=None)
    enable_logging: bool | None = Field(default=None)
    streaming: bool | None = Field(default=None)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("/"):
            v = "/" + v
        return v.rstrip("/") or "/"

    @field_validator("target_urls")
    @classmethod
    def validate_target_urls(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("At least one target URL is required")
        validated = []
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Target URL must start with http:// or https://: {url}")
            validated.append(url.rstrip("/"))
        return validated

    @field_validator("load_balance_mode")
    @classmethod
    def validate_load_balance_mode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("round_robin", "failover"):
            raise ValueError("Load balance mode must be 'round_robin' or 'failover'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("enabled", "disabled"):
            raise ValueError("Status must be 'enabled' or 'disabled'")
        return v


class ProxyRouteResponse(ProxyRouteBase):
    """Schema for proxy route response."""

    id: str
    status: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProxyRouteListResponse(BaseModel):
    """Schema for proxy route list response."""

    items: list[ProxyRouteResponse]
    total: int
    page: int
    page_size: int


# Proxy Log Schemas
class ProxyLogRequest(BaseModel):
    """Schema for logged request data."""

    method: str
    path: str
    query_params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    body: Any | None = None
    body_size: int = 0


class ProxyLogResponse(BaseModel):
    """Schema for logged response data."""

    status_code: int
    headers: dict[str, str] | None = None
    body: Any | None = None
    body_size: int = 0


class ProxyLogEntry(BaseModel):
    """Schema for a proxy log entry."""

    id: str = Field(alias="_id")
    route_id: str
    route_path: str
    target_url: str
    request: ProxyLogRequest
    response: ProxyLogResponse | None = None
    status: str = "pending"  # pending, completed, error
    latency_ms: int = 0
    client_ip: str | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)


class ProxyLogListResponse(BaseModel):
    """Schema for proxy log list response."""

    items: list[ProxyLogEntry]
    total: int
    page: int
    page_size: int


class ProxyLogStatistics(BaseModel):
    """Schema for proxy log statistics."""

    total_requests: int
    success_count: int
    error_count: int
    success_rate: float
    avg_latency_ms: float
    requests_by_route: dict[str, int]
    requests_by_status: dict[str, int]
