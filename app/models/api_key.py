from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TypeBase
from .types import StringUUID, LongText


class ApiKeyStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class ApiKey(TypeBase):
    __tablename__ = "api_keys"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="api_key_pkey"),
        sa.Index("api_key_tenant_id_idx", "tenant_id"),
        sa.Index("api_key_key_hash_idx", "key_hash", unique=True),
        sa.Index("api_key_key_prefix_idx", "key_prefix"),
        sa.Index("api_key_status_idx", "status"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    name: Mapped[str] = mapped_column(String(128))
    key_prefix: Mapped[str] = mapped_column(String(12))
    key_hash: Mapped[str] = mapped_column(String(64))
    tenant_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    created_by: Mapped[str | None] = mapped_column(StringUUID, default=None)
    whitelist: Mapped[list | None] = mapped_column(JSON, default=None)
    status: Mapped[str] = mapped_column(String(16), default=ApiKeyStatus.ACTIVE)
    rpm: Mapped[int | None] = mapped_column(Integer, default=None)
    rph: Mapped[int | None] = mapped_column(Integer, default=None)
    balance: Mapped[float | None] = mapped_column(Numeric(12, 2), default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, init=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        init=False,
    )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def is_valid(self) -> bool:
        return self.status == ApiKeyStatus.ACTIVE and not self.is_expired


class ApiUsageLog(TypeBase):
    __tablename__ = "api_usage_logs"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="api_usage_log_pkey"),
        sa.Index("api_usage_log_api_key_id_idx", "api_key_id"),
        sa.Index("api_usage_log_tenant_id_idx", "tenant_id"),
        sa.Index("api_usage_log_created_at_idx", "created_at"),
        sa.Index("api_usage_log_endpoint_idx", "endpoint"),
        sa.Index("api_usage_log_service_type_idx", "service_type"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuid4()),
        default_factory=lambda: str(uuid4()),
        init=False,
    )
    api_key_id: Mapped[str] = mapped_column(StringUUID)
    endpoint: Mapped[str] = mapped_column(String(256))
    method: Mapped[str] = mapped_column(String(10))
    service_type: Mapped[str] = mapped_column(String(32))
    status_code: Mapped[int] = mapped_column(Integer)
    ip_address: Mapped[str] = mapped_column(String(45))
    tenant_id: Mapped[str | None] = mapped_column(StringUUID, default=None)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(LongText, default=None)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None)
    request_id: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False, init=False
    )
