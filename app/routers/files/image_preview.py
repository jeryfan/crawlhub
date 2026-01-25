from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from models.engine import get_db
from services.file_service import FileService
from urllib.parse import quote
from models.common import UploadFile
from extensions.ext_storage import storage

router = APIRouter(prefix="/files")


@router.get("/{file_id}/image-preview")
async def get_image_preview(
    request: Request,
    file_id: str,
    timestamp: str = Query(),
    nonce: str = Query(),
    sign: str = Query(),
    db: AsyncSession = Depends(get_db),
):
    file_id = str(file_id)

    if not timestamp or not nonce or not sign:
        return {"content": "Invalid request."}, 400

    generator, mimetype = await FileService(db).get_image_preview(
        file_id=file_id,
        timestamp=timestamp,
        nonce=nonce,
        sign=sign,
    )

    return StreamingResponse(generator, media_type=mimetype)


@router.get("/{file_id}/file-preview")
async def get_file_preview(
    request: Request,
    file_id: str,
    timestamp: str = Query(),
    nonce: str = Query(),
    sign: str = Query(),
    as_attachment: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    file_id = str(file_id)

    if not timestamp or not nonce or not sign:
        return {"content": "Invalid request."}, 400

    generator, upload_file = await FileService(db).get_file_generator_by_file_id(
        file_id=file_id,
        timestamp=timestamp,
        nonce=nonce,
        sign=sign,
    )
    response = StreamingResponse(
        generator,
        media_type=upload_file.mime_type,
        headers={},
    )
    # add Accept-Ranges header for audio/video files
    if upload_file.mime_type in [
        "audio/mpeg",
        "audio/wav",
        "audio/mp4",
        "audio/ogg",
        "audio/flac",
        "audio/aac",
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "audio/x-m4a",
    ]:
        response.headers["Accept-Ranges"] = "bytes"
    if upload_file.size > 0:
        response.headers["Content-Length"] = str(upload_file.size)
    if as_attachment:
        encoded_filename = quote(upload_file.name)
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
        response.headers["Content-Type"] = "application/octet-stream"

    return response


@router.get("/{file_id}/public")
async def get_public_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    公开访问的文件端点（仅限平台资源如 Logo、Favicon）
    只有 tenant_id 为 NULL 的文件才能通过此端点访问
    """
    upload_file = await db.get(UploadFile, file_id)

    if not upload_file:
        return {"error": "File not found"}, 404

    # 安全检查：只允许访问平台级别的文件（tenant_id 为空）
    if upload_file.tenant_id is not None:
        return {"error": "Access denied"}, 403

    generator = await storage.load(upload_file.key, stream=True)

    response = StreamingResponse(
        generator,
        media_type=upload_file.mime_type or "application/octet-stream",
    )

    if upload_file.size and upload_file.size > 0:
        response.headers["Content-Length"] = str(upload_file.size)

    # 添加缓存头，平台资源可以长期缓存
    response.headers["Cache-Control"] = "public, max-age=31536000"

    return response
