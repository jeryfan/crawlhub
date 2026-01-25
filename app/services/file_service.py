import datetime
import logging
import os
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from constants import (
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
)
from core.file import helpers as file_helpers
from core.rag.extractor.extract_processor import ExtractProcessor
from exceptions.common import (
    FileNotFoundError,
    FileTypeNotSupportedError,
    InvalidFileTypeError,
    InvalidSignatureError,
)
from extensions.ext_storage import storage
from libs.datetime_utils import naive_utc_now
from models.account import Account
from models.common import UploadFile

logger = logging.getLogger(__name__)


PREVIEW_WORDS_LIMIT = 3000


class FileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_file_by_id(self, file_id: str) -> UploadFile | None:
        result = await self.db.execute(select(UploadFile).where(UploadFile.id == file_id))
        return result.scalar_one_or_none()

    async def upload_file(
        self,
        *,
        filename: str,
        content: bytes,
        mimetype: str,
        user: Account | Any,
        source_url: str = "",
    ) -> UploadFile:
        extension = os.path.splitext(filename)[1].lstrip(".").lower()
        if any(c in filename for c in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]):
            raise ValueError("文件名包含非法字符")

        if len(filename) > 200:
            filename = filename.split(".")[0][:200] + "." + extension

        file_size = len(content)
        file_uuid = str(uuid.uuid4())
        file_key = f"upload_files/{user.id}/{file_uuid}.{extension}"

        await storage.save(file_key, content)

        upload_file = UploadFile(
            tenant_id=user.current_tenant_id,
            storage_type=app_config.STORAGE_TYPE,
            key=file_key,
            name=filename,
            size=file_size,
            extension=extension,
            mime_type=mimetype,
            created_by=user.id,
            created_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            source_url=source_url,
        )

        if not upload_file.source_url:
            upload_file.source_url = file_helpers.get_signed_file_url(upload_file_id=upload_file.id)

        self.db.add(upload_file)
        await self.db.commit()
        await self.db.refresh(upload_file)

        logger.info(f"File {upload_file.id} uploaded")

        return upload_file

    async def upload_text(
        self, text: str, text_name: str, user_id: str, tenant_id: str
    ) -> UploadFile:
        if len(text_name) > 200:
            text_name = text_name[:200]
        # user uuid as file name
        file_uuid = str(uuid.uuid4())
        file_key = "upload_files/" + tenant_id + "/" + file_uuid + ".txt"

        # save file to storage
        await storage.save(file_key, text.encode("utf-8"))

        # save file to db
        upload_file = UploadFile(
            tenant_id=tenant_id,
            storage_type=app_config.STORAGE_TYPE,
            key=file_key,
            name=text_name,
            size=len(text),
            extension="txt",
            mime_type="text/plain",
            created_by=user_id,
            created_at=naive_utc_now(),
        )

        self.db.add(upload_file)
        await self.db.commit()
        await self.db.refresh(upload_file)

        return upload_file

    async def get_file_preview(self, file_id: str):
        upload_file = await self.db.get(UploadFile, file_id)

        if not upload_file:
            raise FileNotFoundError()

        # extract text from file
        extension = upload_file.extension
        if extension.lower() not in DOCUMENT_EXTENSIONS:
            raise FileTypeNotSupportedError()

        text = await ExtractProcessor().load_from_upload_file(
            self.db, upload_file, return_text=True
        )
        text = text[0:PREVIEW_WORDS_LIMIT] if text else ""

        return text

    async def get_image_preview(self, file_id: str, timestamp: str, nonce: str, sign: str):
        result = file_helpers.verify_image_signature(
            upload_file_id=file_id, timestamp=timestamp, nonce=nonce, sign=sign
        )
        if not result:
            raise InvalidSignatureError()

        upload_file = await self.db.get(UploadFile, file_id)

        if not upload_file:
            raise FileNotFoundError()

        # extract text from file
        extension = upload_file.extension
        if extension.lower() not in IMAGE_EXTENSIONS:
            raise InvalidFileTypeError()

        generator = await storage.load(upload_file.key, stream=True)

        return generator, upload_file.mime_type

    async def get_file_generator_by_file_id(
        self, file_id: str, timestamp: str, nonce: str, sign: str
    ):
        logger.info("Get file preview by file id")
        result = file_helpers.verify_file_signature(
            upload_file_id=file_id, timestamp=timestamp, nonce=nonce, sign=sign
        )
        if not result:
            raise InvalidSignatureError()

        upload_file = await self.db.get(UploadFile, file_id)

        if not upload_file:
            raise FileNotFoundError()

        generator = await storage.load(upload_file.key, stream=True)

        return generator, upload_file

    async def get_public_image_preview(self, file_id: str):
        upload_file = await self.db.get(UploadFile, file_id)

        if not upload_file:
            raise FileNotFoundError()

        # extract text from file
        extension = upload_file.extension
        if extension.lower() not in IMAGE_EXTENSIONS:
            raise InvalidFileTypeError()

        generator = await storage.load(upload_file.key)

        return generator, upload_file.mime_type

    async def get_file_content(self, file_id: str) -> str:
        upload_file: UploadFile | None = await self.db.get(UploadFile, file_id)

        if not upload_file:
            raise FileNotFoundError()
        content = await storage.load(upload_file.key)

        return content.decode("utf-8")

    async def delete_file(self, file_id: str):
        upload_file = await self.db.scalar(select(UploadFile).where(UploadFile.id == file_id))
        if not upload_file:
            return
        await storage.delete(upload_file.key)
        await self.db.delete(upload_file)
