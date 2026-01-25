"""管理后台 Schema 定义"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field


T = TypeVar("T")


# ============ 分页相关 ============
class PaginationParams(BaseModel):
    """分页参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    keyword: str | None = Field(default=None, description="搜索关键词")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ 用户管理 Schema ============
class AccountListItem(BaseModel):
    """用户列表项"""

    id: str
    name: str
    email: str
    avatar: str | None = None
    avatar_url: str | None = None
    status: str
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountDetail(AccountListItem):
    """用户详情"""

    interface_language: str | None = None
    timezone: str | None = None
    last_active_at: datetime | None = None
    initialized_at: datetime | None = None
    updated_at: datetime | None = None


class AccountCreate(BaseModel):
    """创建用户"""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8)
    status: str = Field(default="active")
    avatar: str | None = Field(default=None, description="头像文件ID")
    tenant_id: str | None = Field(default=None, description="关联的工作区ID")
    role: str | None = Field(default=None, description="在工作区中的角色: admin, editor, normal")


class AccountUpdate(BaseModel):
    """更新用户"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    status: str | None = None
    avatar: str | None = None
    interface_language: str | None = None
    timezone: str | None = None


class AccountStatusUpdate(BaseModel):
    """更新用户状态"""

    status: str = Field(..., description="状态: active, banned, closed")


class AccountPasswordUpdate(BaseModel):
    """更新用户密码"""

    password: str = Field(..., min_length=8)


# ============ 管理员管理 Schema ============
class AdminListItem(BaseModel):
    """管理员列表项"""

    id: str
    name: str
    email: str
    avatar: str | None = None
    avatar_url: str | None = None
    status: str
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminDetail(AdminListItem):
    """管理员详情"""

    timezone: str | None = None
    last_active_at: datetime | None = None
    initialized_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCreate(BaseModel):
    """创建管理员"""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)


class AdminUpdate(BaseModel):
    """更新管理员"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    status: str | None = None
    avatar: str | None = None
    timezone: str | None = None


class AdminPasswordUpdate(BaseModel):
    """更新管理员密码"""

    password: str = Field(..., min_length=8)


# ============ 租户管理 Schema ============
class TenantListItem(BaseModel):
    """租户列表项"""

    id: str
    name: str
    plan: str
    status: str
    created_at: datetime
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TenantDetail(TenantListItem):
    """租户详情"""

    encrypt_public_key: str | None = None
    custom_config: dict | None = None
    updated_at: datetime | None = None


class TenantCreate(BaseModel):
    """创建租户"""

    name: str = Field(..., min_length=1, max_length=255)
    plan: str = Field(default="basic")


class TenantUpdate(BaseModel):
    """更新租户"""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan: str | None = None
    status: str | None = None
    custom_config: dict | None = None


class TenantMember(BaseModel):
    """租户成员"""

    id: str
    account_id: str
    account_name: str
    account_email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 邀请码管理 Schema ============
class InvitationCodeListItem(BaseModel):
    """邀请码列表项"""

    id: int
    batch: str
    code: str
    status: str
    used_at: datetime | None = None
    used_by_tenant_id: str | None = None
    used_by_account_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationCodeCreate(BaseModel):
    """批量创建邀请码"""

    batch: str = Field(..., min_length=1, max_length=255)
    count: int = Field(default=10, ge=1, le=1000)


class InvitationCodeDeprecate(BaseModel):
    """作废邀请码"""

    ids: list[int] = Field(..., min_items=1)


# ============ Dashboard 统计 Schema ============
class DashboardStats(BaseModel):
    """Dashboard 统计数据"""

    total_accounts: int = 0
    active_accounts: int = 0
    new_accounts_today: int = 0
    new_accounts_week: int = 0

    total_admins: int = 0
    active_admins: int = 0

    total_tenants: int = 0
    active_tenants: int = 0

    total_invitation_codes: int = 0
    used_invitation_codes: int = 0


class DashboardTrend(BaseModel):
    """趋势数据"""

    date: str
    count: int


class DashboardTrends(BaseModel):
    """Dashboard 趋势"""

    account_trends: list[DashboardTrend] = []
    tenant_trends: list[DashboardTrend] = []
