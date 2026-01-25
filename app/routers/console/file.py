from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, status
from fastapi import UploadFile
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from models.engine import get_db
from dependencies.auth import get_current_user
from models.account import Account
from schemas.file import (
    UploadFileOut,
)
from schemas.response import ApiResponse
from services.file_service import FileService

router = APIRouter(prefix="/files", tags=["文件上传"])


def validate_file_size(file: UploadFile) -> None:
    """验证文件大小是否超过限制"""
    if file.size and file.size > app_config.MAX_FILE_SIZE:
        max_size_mb = app_config.MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({max_size_mb:.2f} MB)",
        )


@router.post("/upload", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    source_url: Optional[str] = Form(""),
    current_user: Account = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    validate_file_size(file)

    uploaded_file = await FileService(db).upload_file(
        filename=file.filename or "unknown",
        content=await file.read(),
        mimetype=file.content_type or "application/octet-stream",
        user=current_user,
        source_url=source_url or "",
    )

    data = TypeAdapter(UploadFileOut).validate_python(uploaded_file)

    return ApiResponse(data=data, code=status.HTTP_201_CREATED, msg="文件上传成功")


@router.post("/file_id:str/preview", response_model=ApiResponse)
async def preview_file(file_id: str, db: AsyncSession = Depends(get_db)):
    file_id = str(file_id)
    text = FileService(db).get_file_preview(file_id)
    return ApiResponse(data={"content": text})
