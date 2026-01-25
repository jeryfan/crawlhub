import json
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Numeric, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, reconstructor
from dataclasses import field
from .base import Base, TypeBase
from .types import LongText, StringUUID


class AccountStatus(StrEnum):
    PENDING = "pending"
    UNINITIALIZES = "uninitialized"
    ACTIVE = "active"
    BANNED = "banned"
    CLOSED = "closed"


class TenantStatus(StrEnum):
    NORMAL = "normal"
    ARCHIVE = "archive"


class TenantAccountRole(StrEnum):
    ADMIN = "admin"
    OWNER = "owner"
    EDITOR = "editor"
    NORMAL = "normal"

    @staticmethod
    def is_valid_role(role: str) -> bool:
        if not role:
            return False
        return role in {
            TenantAccountRole.ADMIN,
            TenantAccountRole.OWNER,
            TenantAccountRole.EDITOR,
            TenantAccountRole.NORMAL,
        }

    @staticmethod
    def is_admin_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False

        return role in {TenantAccountRole.ADMIN}

    @staticmethod
    def is_non_owner_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {
            TenantAccountRole.ADMIN,
            TenantAccountRole.EDITOR,
            TenantAccountRole.NORMAL,
        }

    @staticmethod
    def is_editing_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {
            TenantAccountRole.OWNER,
            TenantAccountRole.ADMIN,
            TenantAccountRole.EDITOR,
        }

    @staticmethod
    def is_privileged_role(role: Optional["TenantAccountRole"]) -> bool:
        if not role:
            return False
        return role in {TenantAccountRole.OWNER, TenantAccountRole.ADMIN}


class Account(TypeBase):
    __tablename__ = "accounts"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="account_pkey"),
        sa.Index("account_email_idx", "email"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255), default=None)
    password_salt: Mapped[str | None] = mapped_column(String(255), default=None)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    interface_language: Mapped[str | None] = mapped_column(String(255), default=None)
    timezone: Mapped[str | None] = mapped_column(String(255), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    last_login_ip: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    status: Mapped[str] = mapped_column(String(16), default="active")
    initialized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
        init=False,
        onupdate=func.current_timestamp(),
    )

    role: TenantAccountRole | None = field(default=None, init=False)
    _current_tenant: "Tenant | None" = field(default=None, init=False)

    @reconstructor
    def init_on_load(self):
        self.role: TenantAccountRole | None = None
        self._current_tenant: "Tenant" | None = None

    @property
    def is_password_set(self) -> bool:
        return self.password is not None

    @property
    def current_tenant(self):
        return self._current_tenant

    async def set_current_tenant(self, session: AsyncSession, tenant: "Tenant"):
        """设置当前租户并加载用户在该租户下的角色"""
        query = (
            select(Tenant, TenantAccountJoin)
            .join(TenantAccountJoin, Tenant.id == TenantAccountJoin.tenant_id)
            .where(TenantAccountJoin.account_id == self.id, Tenant.id == tenant.id)
        )
        result = await session.execute(query)
        row = result.first()

        if row:
            loaded_tenant, tenant_join = row
            self.role = TenantAccountRole(tenant_join.role)
            self._current_tenant = loaded_tenant
        else:
            self._current_tenant = None

    @property
    def current_tenant_id(self) -> str | None:
        return self.current_tenant.id if self._current_tenant else None

    async def set_tenant_id(self, session: AsyncSession, tenant_id: str):
        """通过租户ID设置当前租户"""
        query = (
            select(Tenant, TenantAccountJoin)
            .where(Tenant.id == tenant_id)
            .where(TenantAccountJoin.tenant_id == Tenant.id)
            .where(TenantAccountJoin.account_id == self.id)
        )
        result = await session.execute(query)
        row = result.one_or_none()
        if not row:
            return
        tenant, join = row
        self.role = TenantAccountRole(join.role)
        self._current_tenant = tenant

    def get_status(self) -> AccountStatus:
        status_str = self.status
        return AccountStatus(status_str)

    @property
    def is_admin_or_owner(self):
        return TenantAccountRole.is_privileged_role(self.role)

    @property
    def is_admin(self):
        return TenantAccountRole.is_admin_role(self.role)

    @property
    def is_editor(self):
        return TenantAccountRole.is_editing_role(self.role)

    @classmethod
    async def get_by_email(cls, session, email: str) -> Optional["Account"]:
        query = select(Account).where(Account.email == email)

        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_id(cls, session, id: str) -> Optional["Account"]:
        query = select(Account).where(Account.id == id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_openid(cls, session: AsyncSession, provider: str, open_id: str):
        account_integrate = await session.scalar(
            select(AccountIntegrate).where(
                AccountIntegrate.provider == provider,
                AccountIntegrate.open_id == open_id,
            )
        )
        if account_integrate:
            return await session.get(Account, account_integrate.account_id)
        return None


class Tenant(TypeBase):
    __tablename__ = "tenants"
    __table_args__ = (sa.PrimaryKeyConstraint("id", name="tenant_pkey"),)

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    name: Mapped[str] = mapped_column(String(255))
    encrypt_public_key: Mapped[str | None] = mapped_column(LongText, default=None)
    plan: Mapped[str] = mapped_column(
        String(255), server_default=sa.text("'basic'"), default="basic"
    )
    status: Mapped[str] = mapped_column(
        String(255), server_default=sa.text("'normal'"), default="normal"
    )
    custom_config: Mapped[str | None] = mapped_column(LongText, default=None)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), server_default=sa.text("0"), default=Decimal("0")
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        init=False,
        onupdate=func.current_timestamp(),
    )

    async def get_accounts(self, session) -> list[Account]:
        query = select(Account).where(
            Account.id == TenantAccountJoin.account_id,
            TenantAccountJoin.tenant_id == self.id,
        )
        result = await session.execute(query)
        return result.scalars().all()

    @property
    def custom_config_dict(self) -> dict:
        return json.loads(self.custom_config) if self.custom_config else {}

    @custom_config_dict.setter
    def custom_config_dict(self, value: dict):
        self.custom_config = json.dumps(value)


class TenantAccountJoin(TypeBase):
    __tablename__ = "tenant_account_joins"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="tenant_account_join_pkey"),
        sa.Index("tenant_account_join_account_id_idx", "account_id"),
        sa.Index("tenant_account_join_tenant_id_idx", "tenant_id"),
        sa.UniqueConstraint("tenant_id", "account_id", name="unique_tenant_account_join"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    tenant_id: Mapped[str] = mapped_column(StringUUID)
    account_id: Mapped[str] = mapped_column(StringUUID)
    current: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("false"), default=False
    )
    role: Mapped[str] = mapped_column(String(16), server_default="normal", default="normal")
    invited_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
        init=False,
        onupdate=func.current_timestamp(),
    )


class AccountIntegrate(TypeBase):
    __tablename__ = "account_integrates"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="account_integrate_pkey"),
        sa.UniqueConstraint("account_id", "provider", name="unique_account_provider"),
        sa.UniqueConstraint("provider", "open_id", name="unique_provider_open_id"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    account_id: Mapped[str] = mapped_column(StringUUID)
    provider: Mapped[str] = mapped_column(String(16))
    open_id: Mapped[str] = mapped_column(String(255))
    encrypted_token: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
        init=False,
        onupdate=func.current_timestamp(),
    )


class InvitationCode(TypeBase):
    __tablename__ = "invitation_codes"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="invitation_code_pkey"),
        sa.Index("invitation_codes_batch_idx", "batch"),
        sa.Index("invitation_codes_code_idx", "code", "status"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, init=False)
    batch: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(16), server_default=sa.text("'unused'"), default="unused"
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    used_by_tenant_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    used_by_account_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=sa.func.current_timestamp(), nullable=False, init=False
    )
