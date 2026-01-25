import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TypeBase
from .types import StringUUID
from libs.uuid_utils import uuidv7


class FastAPISetup(TypeBase):
    __tablename__ = "fastapi_setups"
    __table_args__ = (sa.PrimaryKeyConstraint("version", name="fastapi_setup_pkey"),)

    version: Mapped[str] = mapped_column(String(255), nullable=False)
    setup_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=func.current_timestamp(), init=False
    )


class UploadFile(Base):
    __tablename__ = "upload_files"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="upload_file_pkey"),
        sa.Index("upload_file_tenant_idx", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str | None] = mapped_column(StringUUID, nullable=True)
    storage_type: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    extension: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=True)

    created_by_role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="account",
    )

    created_by: Mapped[str] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=func.current_timestamp()
    )

    used: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(sa.TEXT, default="")

    def __init__(
        self,
        *,
        tenant_id: str | None,
        storage_type: str,
        key: str,
        name: str,
        size: int,
        extension: str,
        mime_type: str,
        created_by: str,
        created_at: datetime,
        hash: str | None = None,
        source_url: str = "",
    ):
        self.id = str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.storage_type = storage_type
        self.key = key
        self.name = name
        self.size = size
        self.extension = extension
        self.mime_type = mime_type
        self.created_by = created_by
        self.created_at = created_at
        self.hash = hash
        self.source_url = source_url


class OAuthProviderApp(TypeBase):
    """
    Globally shared OAuth provider app information.
    """

    __tablename__ = "oauth_provider_apps"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="oauth_provider_app_pkey"),
        sa.Index("oauth_provider_app_client_id_idx", "client_id"),
    )

    id: Mapped[str] = mapped_column(
        StringUUID,
        insert_default=lambda: str(uuidv7()),
        default_factory=lambda: str(uuidv7()),
        init=False,
    )
    app_icon: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    app_label: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default_factory=dict)
    redirect_uris: Mapped[list] = mapped_column(sa.JSON, nullable=False, default_factory=list)
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=sa.text(
            "'read:name read:email read:avatar read:interface_language read:timezone'"
        ),
        default="read:name read:email read:avatar read:interface_language read:timezone",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=func.current_timestamp(), init=False
    )
