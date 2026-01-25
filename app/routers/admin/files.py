import datetime
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, status
from fastapi import UploadFile as FastAPIUploadFile
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from models.engine import get_db
from dependencies.auth import get_current_admin
from extensions.ext_storage import storage
from models.admin import Admin
from models.common import UploadFile
from schemas.file import UploadFileOut
from schemas.response import ApiResponse
from core.file import helpers as file_helpers

router = APIRouter(prefix="/files", tags=["Platform - Files"])


@router.post("/upload", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: FastAPIUploadFile = File(...),
    source_url: Optional[str] = Form(""),
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "unknown"
    content = await file.read()
    mimetype = file.content_type or "application/octet-stream"

    extension = os.path.splitext(filename)[1].lstrip(".").lower()
    if any(c in filename for c in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名包含非法字符",
        )

    if len(filename) > 200:
        filename = filename.split(".")[0][:200] + "." + extension

    file_size = len(content)
    file_uuid = str(uuid.uuid4())
    file_key = f"upload_files/{current_admin.id}/{file_uuid}.{extension}"

    await storage.save(file_key, content)

    upload_file = UploadFile(
        tenant_id=None,
        storage_type=app_config.STORAGE_TYPE,
        key=file_key,
        name=filename,
        size=file_size,
        extension=extension,
        mime_type=mimetype,
        created_by=current_admin.id,
        created_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        source_url=source_url or "",
    )

    if not upload_file.source_url:
        upload_file.source_url = file_helpers.get_public_file_url(upload_file_id=upload_file.id)

    db.add(upload_file)
    await db.commit()
    await db.refresh(upload_file)

    data = TypeAdapter(UploadFileOut).validate_python(upload_file)

    return ApiResponse(data=data, code=status.HTTP_200_OK, msg="文件上传成功")
