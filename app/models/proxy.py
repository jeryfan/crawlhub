from datetime import datetime
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from libs.uuid_utils import uuidv7

from .base import TypeBase
from .types import StringUUID


class ProxyRouteStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class ProxyLoadBalanceMode(StrEnum):
    """Load balance mode for multiple target URLs."""

    ROUND_ROBIN = "round_robin"  # 轮询
    FAILOVER = "failover"  # 故障转移（按顺序尝试，失败则下一个）


class ProxyRoute(TypeBase):
    """
    Proxy route configuration model.

    Stores the mapping between incoming request paths and target URLs.
    """

    __tablename__ = "proxy_routes"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="proxy_route_pkey"),
        sa.UniqueConstraint("path", name="proxy_route_path_key"),
        sa.Index("proxy_route_status_idx", "status"),
        sa.Index("proxy_route_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        default=lambda: str(uuidv7()),
        init=False,
    )

    # Route path pattern, e.g., "/chat/completions"
    path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Route path pattern to match incoming requests",
    )

    # Target URLs (JSON array)
    target_urls: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        comment="Target URLs for load balancing or failover",
    )

    # Load balance mode
    load_balance_mode: Mapped[str] = mapped_column(
        String(32),
        default=ProxyLoadBalanceMode.FAILOVER,
        comment="Load balance mode: round_robin or failover",
    )

    # HTTP methods allowed (comma-separated or * for all)
    methods: Mapped[str] = mapped_column(
        String(128),
        default="*",
        comment="Allowed HTTP methods, comma-separated or * for all",
    )

    # Route status
    status: Mapped[str] = mapped_column(
        String(32),
        default=ProxyRouteStatus.ENABLED,
        comment="Route status: enabled or disabled",
    )

    # Description
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Route description",
    )

    # Request timeout in seconds
    timeout: Mapped[int] = mapped_column(
        Integer,
        default=60,
        comment="Request timeout in seconds",
    )

    # Whether to preserve the original Host header
    preserve_host: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether to preserve the original Host header",
    )

    # Whether to log requests for this route
    enable_logging: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether to log requests for this route",
    )

    # Whether to use streaming mode for responses
    streaming: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether to use streaming mode for responses (recommended for SSE/large files)",
    )

    # Creator ID (admin user)
    created_by: Mapped[str | None] = mapped_column(
        StringUUID,
        nullable=True,
        default=None,
        comment="Admin user ID who created this route",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
        init=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
        init=False,
    )

    @property
    def is_enabled(self) -> bool:
        return self.status == ProxyRouteStatus.ENABLED

    def allows_method(self, method: str) -> bool:
        """Check if the route allows the given HTTP method."""
        if self.methods == "*":
            return True
        allowed = [m.strip().upper() for m in self.methods.split(",")]
        return method.upper() in allowed

    def get_all_target_urls(self) -> list[str]:
        """Get all target URLs."""
        return self.target_urls or []
