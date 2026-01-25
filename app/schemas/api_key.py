"""API Key相关Schema定义"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============ API Key 请求Schema ============
class ApiKeyCreate(BaseModel):
    """创建API Key请求"""

    name: str = Field(..., max_length=128, description="API Key名称")
    tenant_id: str | None = Field(default=None, description="租户ID，后台管理员创建时可为空")
    whitelist: list[str] | None = Field(
        default=None, description="IP白名单，支持CIDR格式，空则允许所有"
    )
    rpm: int | None = Field(default=None, ge=0, description="每分钟请求限制 (Requests Per Minute)")
    rph: int | None = Field(default=None, ge=0, description="每小时请求限制 (Requests Per Hour)")
    balance: float | None = Field(default=None, ge=0, description="初始余额")
    expires_at: datetime | None = Field(default=None, description="过期时间")


class ApiKeyUpdate(BaseModel):
    """更新API Key请求"""

    name: str | None = Field(default=None, max_length=128, description="API Key名称")
    whitelist: list[str] | None = Field(
        default=None, description="IP白名单，支持CIDR格式，空则允许所有"
    )
    rpm: int | None = Field(default=None, ge=1, description="每分钟请求限制 (Requests Per Minute)")
    rph: int | None = Field(default=None, ge=1, description="每小时请求限制 (Requests Per Hour)")
    balance: float | None = Field(default=None, ge=0, description="余额")
    expires_at: datetime | None = Field(default=None, description="过期时间")
    status: str | None = Field(default=None, description="状态")


# ============ API Key 响应Schema ============
class ApiKeyItem(BaseModel):
    """API Key列表项"""

    id: str
    name: str
    key_prefix: str
    tenant_id: str | None = None
    tenant_name: str | None = None
    whitelist: list[str] | None = None
    status: str
    rpm: int | None = None
    rph: int | None = None
    balance: float | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyDetail(ApiKeyItem):
    """API Key详情"""

    created_by: str | None = None
    created_by_name: str | None = None


class ApiKeyCreateResponse(BaseModel):
    """创建API Key响应（包含完整key）"""

    id: str
    name: str
    key: str  # 完整的API Key，仅在创建时返回
    key_prefix: str
    tenant_id: str | None = None
    whitelist: list[str] | None = None
    status: str
    rpm: int | None = None
    rph: int | None = None
    balance: float | None = None
    expires_at: datetime | None = None
    created_at: datetime


class ApiKeyRegenerateResponse(BaseModel):
    """重新生成API Key响应"""

    id: str
    name: str
    key: str  # 新的完整API Key
    key_prefix: str


class ApiKeyListResponse(BaseModel):
    """API Key列表响应"""

    items: list[ApiKeyItem]
    total: int
    page: int
    page_size: int


# ============ 查询参数 ============
class ApiKeyQueryParams(BaseModel):
    """API Key查询参数"""

    tenant_id: str | None = None
    status: str | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
