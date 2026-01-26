from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub import ProxyProtocol, ProxyStatus


class ProxyBase(BaseModel):
    host: str = Field(..., min_length=1, max_length=255, description="主机地址")
    port: int = Field(..., ge=1, le=65535, description="端口")
    protocol: ProxyProtocol = Field(default=ProxyProtocol.HTTP, description="协议")
    username: str | None = Field(None, max_length=100, description="用户名")
    password: str | None = Field(None, max_length=100, description="密码")


class ProxyCreate(ProxyBase):
    pass


class ProxyBatchCreate(BaseModel):
    proxies: list[ProxyCreate] = Field(..., min_length=1, description="代理列表")


class ProxyUpdate(BaseModel):
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    protocol: ProxyProtocol | None = None
    username: str | None = None
    password: str | None = None
    status: ProxyStatus | None = None


class ProxyResponse(ProxyBase):
    id: str
    status: ProxyStatus
    last_check_at: datetime | None
    success_rate: float
    fail_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProxyListResponse(BaseModel):
    items: list[ProxyResponse]
    total: int
