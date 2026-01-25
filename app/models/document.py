"""文档相关模型"""

import base64
from enum import StrEnum, auto
import hashlib
import hmac
from json import JSONDecodeError
import json
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import String, Text, func, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs import app_config
from models.account import Account
from models.common import UploadFile

from .base import Base
from .types import AdjustedJSON, LongText, StringUUID, adjusted_json_index
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession


class BuiltInField(StrEnum):
    document_name = auto()
    uploader = auto()
    upload_date = auto()
    last_update_date = auto()
    source = auto()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="document_pkey"),
        sa.Index("document_is_paused_idx", "is_paused"),
        sa.Index("document_tenant_idx", "tenant_id"),
        adjusted_json_index("document_metadata_idx", "doc_metadata"),
    )

    # initial fields
    id = mapped_column(StringUUID, nullable=False, default=lambda: str(uuid4()))
    tenant_id = mapped_column(StringUUID, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    data_source_type: Mapped[str] = mapped_column(String(255), nullable=False)
    data_source_info = mapped_column(LongText, nullable=True)
    batch: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_from: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by = mapped_column(StringUUID, nullable=False)
    created_api_request_id = mapped_column(StringUUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # start processing
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # parsing
    file_id = mapped_column(LongText, nullable=True)
    word_count: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )  # TODO: make this not nullable
    parsing_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # cleaning
    cleaning_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # split
    splitting_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # indexing
    tokens: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    indexing_latency: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # pause
    is_paused: Mapped[bool | None] = mapped_column(
        sa.Boolean, nullable=True, server_default=sa.text("false")
    )
    paused_by = mapped_column(StringUUID, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # error
    error = mapped_column(LongText, nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # basic fields
    indexing_status = mapped_column(
        String(255), nullable=False, server_default=sa.text("'waiting'")
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_by = mapped_column(StringUUID, nullable=True)
    archived: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    archived_reason = mapped_column(String(255), nullable=True)
    archived_by = mapped_column(StringUUID, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    doc_type = mapped_column(String(40), nullable=True)
    doc_metadata = mapped_column(AdjustedJSON, nullable=True)
    doc_form = mapped_column(String(255), nullable=False, server_default=sa.text("'text_model'"))
    doc_language = mapped_column(String(255), nullable=True)

    DATA_SOURCES = ["upload_file", "notion_import", "website_crawl"]

    @property
    def display_status(self):
        status = None
        if self.indexing_status == "waiting":
            status = "queuing"
        elif self.indexing_status not in {"completed", "error", "waiting"} and self.is_paused:
            status = "paused"
        elif self.indexing_status in {"parsing", "cleaning", "splitting", "indexing"}:
            status = "indexing"
        elif self.indexing_status == "error":
            status = "error"
        elif self.indexing_status == "completed" and not self.archived and self.enabled:
            status = "available"
        elif self.indexing_status == "completed" and not self.archived and not self.enabled:
            status = "disabled"
        elif self.indexing_status == "completed" and self.archived:
            status = "archived"
        return status

    @property
    def data_source_info_dict(self) -> dict[str, Any]:
        if self.data_source_info:
            try:
                data_source_info_dict: dict[str, Any] = json.loads(self.data_source_info)
            except JSONDecodeError:
                data_source_info_dict = {}

            return data_source_info_dict
        return {}

    async def get_data_source_detail_dict(self, db: AsyncSession) -> dict[str, Any]:
        if self.data_source_info:
            if self.data_source_type == "upload_file":
                data_source_info_dict: dict[str, Any] = json.loads(self.data_source_info)

                file_detail = (
                    await db.execute(
                        select(UploadFile).where(
                            UploadFile.id == data_source_info_dict["upload_file_id"]
                        )
                    )
                ).scalar_one_or_none()
                if file_detail:
                    return {
                        "upload_file": {
                            "id": file_detail.id,
                            "name": file_detail.name,
                            "size": file_detail.size,
                            "extension": file_detail.extension,
                            "mime_type": file_detail.mime_type,
                            "created_by": file_detail.created_by,
                            "created_at": file_detail.created_at.timestamp(),
                        }
                    }
            elif self.data_source_type in {"notion_import", "website_crawl"}:
                result: dict[str, Any] = json.loads(self.data_source_info)
                return result
        return {}

    async def average_segment_length(self, db: AsyncSession):
        segment_count = await self.get_segment_count(db)
        if self.word_count and self.word_count != 0 and segment_count and segment_count != 0:
            return self.word_count // segment_count
        return 0

    async def get_segment_count(self, db: AsyncSession):
        return (
            await db.execute(
                select(func.count(DocumentSegment.id)).where(DocumentSegment.document_id == self.id)
            )
        ).scalar()

    async def get_hit_count(self, db: AsyncSession):
        return (
            await db.execute(
                select(func.coalesce(func.sum(DocumentSegment.hit_count), 0)).where(
                    DocumentSegment.document_id == self.id
                )
            )
        ).scalar()

    async def get_uploader(self, db: AsyncSession):
        user = await db.get(Account, self.created_by)
        return user.name if user else None

    @property
    def upload_date(self):
        return self.created_at

    @property
    def last_update_date(self):
        return self.updated_at

    async def get_built_in_fields(self, db: AsyncSession) -> list[dict[str, Any]]:
        built_in_fields: list[dict[str, Any]] = []
        built_in_fields.append(
            {
                "id": "built-in",
                "name": BuiltInField.document_name,
                "type": "string",
                "value": self.name,
            }
        )
        built_in_fields.append(
            {
                "id": "built-in",
                "name": BuiltInField.uploader,
                "type": "string",
                "value": await self.get_uploader(db),
            }
        )
        built_in_fields.append(
            {
                "id": "built-in",
                "name": BuiltInField.upload_date,
                "type": "time",
                "value": str(self.created_at.timestamp()),
            }
        )
        built_in_fields.append(
            {
                "id": "built-in",
                "name": BuiltInField.last_update_date,
                "type": "time",
                "value": str(self.updated_at.timestamp()),
            }
        )

        return built_in_fields

    async def to_dict(self, db: AsyncSession) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "position": self.position,
            "data_source_type": self.data_source_type,
            "data_source_info": self.data_source_info,
            "batch": self.batch,
            "name": self.name,
            "created_from": self.created_from,
            "created_by": self.created_by,
            "created_api_request_id": self.created_api_request_id,
            "created_at": self.created_at,
            "processing_started_at": self.processing_started_at,
            "file_id": self.file_id,
            "word_count": self.word_count,
            "parsing_completed_at": self.parsing_completed_at,
            "cleaning_completed_at": self.cleaning_completed_at,
            "splitting_completed_at": self.splitting_completed_at,
            "tokens": self.tokens,
            "indexing_latency": self.indexing_latency,
            "completed_at": self.completed_at,
            "is_paused": self.is_paused,
            "paused_by": self.paused_by,
            "paused_at": self.paused_at,
            "error": self.error,
            "stopped_at": self.stopped_at,
            "indexing_status": self.indexing_status,
            "enabled": self.enabled,
            "disabled_at": self.disabled_at,
            "disabled_by": self.disabled_by,
            "archived": self.archived,
            "archived_reason": self.archived_reason,
            "archived_by": self.archived_by,
            "archived_at": self.archived_at,
            "updated_at": self.updated_at,
            "doc_type": self.doc_type,
            "doc_metadata": self.doc_metadata,
            "doc_form": self.doc_form,
            "doc_language": self.doc_language,
            "display_status": self.display_status,
            "data_source_info_dict": self.data_source_info_dict,
            "average_segment_length": self.average_segment_length,
            "segment_count": await self.get_segment_count(db),
            "hit_count": await self.get_hit_count(db),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls(
            id=data.get("id"),
            tenant_id=data.get("tenant_id"),
            position=data.get("position"),
            data_source_type=data.get("data_source_type"),
            data_source_info=data.get("data_source_info"),
            batch=data.get("batch"),
            name=data.get("name"),
            created_from=data.get("created_from"),
            created_by=data.get("created_by"),
            created_api_request_id=data.get("created_api_request_id"),
            created_at=data.get("created_at"),
            processing_started_at=data.get("processing_started_at"),
            file_id=data.get("file_id"),
            word_count=data.get("word_count"),
            parsing_completed_at=data.get("parsing_completed_at"),
            cleaning_completed_at=data.get("cleaning_completed_at"),
            splitting_completed_at=data.get("splitting_completed_at"),
            tokens=data.get("tokens"),
            indexing_latency=data.get("indexing_latency"),
            completed_at=data.get("completed_at"),
            is_paused=data.get("is_paused"),
            paused_by=data.get("paused_by"),
            paused_at=data.get("paused_at"),
            error=data.get("error"),
            stopped_at=data.get("stopped_at"),
            indexing_status=data.get("indexing_status"),
            enabled=data.get("enabled"),
            disabled_at=data.get("disabled_at"),
            disabled_by=data.get("disabled_by"),
            archived=data.get("archived"),
            archived_reason=data.get("archived_reason"),
            archived_by=data.get("archived_by"),
            archived_at=data.get("archived_at"),
            updated_at=data.get("updated_at"),
            doc_type=data.get("doc_type"),
            doc_metadata=data.get("doc_metadata"),
            doc_form=data.get("doc_form"),
            doc_language=data.get("doc_language"),
        )


class DocumentSegment(Base):
    __tablename__ = "document_segments"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="document_segment_pkey"),
        sa.Index("document_segment_document_id_idx", "document_id"),
        sa.Index("document_segment_tenant_document_idx", "document_id", "tenant_id"),
        sa.Index("document_segment_tenant_idx", "tenant_id"),
    )

    # initial fields
    id = mapped_column(StringUUID, nullable=False, default=lambda: str(uuid4()))
    tenant_id = mapped_column(StringUUID, nullable=False)
    document_id = mapped_column(StringUUID, nullable=False)
    position: Mapped[int]
    content = mapped_column(LongText, nullable=False)
    answer = mapped_column(LongText, nullable=True)
    word_count: Mapped[int]
    tokens: Mapped[int]

    # indexing fields
    keywords = mapped_column(sa.JSON, nullable=True)
    index_node_id = mapped_column(String(255), nullable=True)
    index_node_hash = mapped_column(String(255), nullable=True)

    # basic fields
    hit_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_by = mapped_column(StringUUID, nullable=True)
    status: Mapped[str] = mapped_column(String(255), server_default=sa.text("'waiting'"))
    created_by = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_by = mapped_column(StringUUID, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    indexing_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error = mapped_column(LongText, nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    async def get_document(self, db: AsyncSession):
        return await db.get(Document, self.document_id)

    async def get_previous_segment(self, db: AsyncSession):
        return await db.scalar(
            select(DocumentSegment).where(
                DocumentSegment.document_id == self.document_id,
                DocumentSegment.position == self.position - 1,
            )
        )

    async def get_next_segment(self, db: AsyncSession):
        return await db.scalar(
            select(DocumentSegment).where(
                DocumentSegment.document_id == self.document_id,
                DocumentSegment.position == self.position + 1,
            )
        )

    async def get_child_chunks(self, db: AsyncSession) -> list[Any]:
        document = await self.get_document(db)
        if not document:
            return []

        child_chunks = (
            await db.scalars(
                select(ChildChunk)
                .where(ChildChunk.segment_id == self.id)
                .order_by(ChildChunk.position.asc())
            )
        ).all()
        return list(child_chunks)

    async def get_sign_content(self) -> str:
        signed_urls: list[tuple[int, int, str]] = []
        text = self.content

        # For data before v0.10.0
        pattern = r"/files/([a-f0-9\-]+)/image-preview(?:\?.*?)?"
        matches = re.finditer(pattern, text)
        for match in matches:
            upload_file_id = match.group(1)
            nonce = os.urandom(16).hex()
            timestamp = str(int(time.time()))
            data_to_sign = f"image-preview|{upload_file_id}|{timestamp}|{nonce}"
            secret_key = app_config.SECRET_KEY.encode() if app_config.SECRET_KEY else b""
            sign = hmac.new(secret_key, data_to_sign.encode(), hashlib.sha256).digest()
            encoded_sign = base64.urlsafe_b64encode(sign).decode()

            params = f"timestamp={timestamp}&nonce={nonce}&sign={encoded_sign}"
            base_url = f"/files/{upload_file_id}/image-preview"
            signed_url = f"{base_url}?{params}"
            signed_urls.append((match.start(), match.end(), signed_url))

        # For data after v0.10.0
        pattern = r"/files/([a-f0-9\-]+)/file-preview(?:\?.*?)?"
        matches = re.finditer(pattern, text)
        for match in matches:
            upload_file_id = match.group(1)
            nonce = os.urandom(16).hex()
            timestamp = str(int(time.time()))
            data_to_sign = f"file-preview|{upload_file_id}|{timestamp}|{nonce}"
            secret_key = app_config.SECRET_KEY.encode() if app_config.SECRET_KEY else b""
            sign = hmac.new(secret_key, data_to_sign.encode(), hashlib.sha256).digest()
            encoded_sign = base64.urlsafe_b64encode(sign).decode()

            params = f"timestamp={timestamp}&nonce={nonce}&sign={encoded_sign}"
            base_url = f"/files/{upload_file_id}/file-preview"
            signed_url = f"{base_url}?{params}"
            signed_urls.append((match.start(), match.end(), signed_url))

        # For tools directory - direct file formats (e.g., .png, .jpg, etc.)
        # Match URL including any query parameters up to common URL boundaries (space, parenthesis, quotes)
        pattern = r"/files/tools/([a-f0-9\-]+)\.([a-zA-Z0-9]+)(?:\?[^\s\)\"\']*)?"
        matches = re.finditer(pattern, text)
        for match in matches:
            upload_file_id = match.group(1)
            file_extension = match.group(2)
            nonce = os.urandom(16).hex()
            timestamp = str(int(time.time()))
            data_to_sign = f"file-preview|{upload_file_id}|{timestamp}|{nonce}"
            secret_key = app_config.SECRET_KEY.encode() if app_config.SECRET_KEY else b""
            sign = hmac.new(secret_key, data_to_sign.encode(), hashlib.sha256).digest()
            encoded_sign = base64.urlsafe_b64encode(sign).decode()

            params = f"timestamp={timestamp}&nonce={nonce}&sign={encoded_sign}"
            base_url = f"/files/tools/{upload_file_id}.{file_extension}"
            signed_url = f"{base_url}?{params}"
            signed_urls.append((match.start(), match.end(), signed_url))

        # Reconstruct the text with signed URLs
        offset = 0
        for start, end, signed_url in signed_urls:
            text = text[: start + offset] + signed_url + text[end + offset :]
            offset += len(signed_url) - (end - start)

        return text


class ChildChunk(Base):
    __tablename__ = "child_chunks"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="child_chunk_pkey"),
        sa.Index(
            "tenant_id",
            "document_id",
            "segment_id",
            "index_node_id",
        ),
        sa.Index("child_chunks_node_idx", "index_node_id"),
        sa.Index("child_chunks_segment_idx", "segment_id"),
    )

    # initial fields
    id = mapped_column(StringUUID, nullable=False, default=lambda: str(uuid4()))
    tenant_id = mapped_column(StringUUID, nullable=False)
    document_id = mapped_column(StringUUID, nullable=False)
    segment_id = mapped_column(StringUUID, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content = mapped_column(LongText, nullable=False)
    word_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    # indexing fields
    index_node_id = mapped_column(String(255), nullable=True)
    index_node_hash = mapped_column(String(255), nullable=True)
    type = mapped_column(String(255), nullable=False, server_default=sa.text("'automatic'"))
    created_by = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=sa.func.current_timestamp()
    )
    updated_by = mapped_column(StringUUID, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=sa.func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    indexing_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error = mapped_column(LongText, nullable=True)

    async def get_document(self, db: AsyncSession):
        return await db.get(Document, self.document_id)

    async def segment(self, db: AsyncSession):
        return await db.get(DocumentSegment, self.segment_id)
