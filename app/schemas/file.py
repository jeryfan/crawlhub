"""文件上传相关 Schema 定义"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class UploadFileOut(BaseModel):
    """文件上传返回信息"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    storage_type: str
    key: str
    name: str
    size: int
    extension: str
    mime_type: Optional[str] = None
    created_by: str
    source_url: str
    created_at: Optional[datetime] = None

    # 动态计算的字段
    file_url: Optional[str] = None


class UploadFromUrlRequest(BaseModel):
    """从 URL 上传文件的请求"""

    url: HttpUrl
    filename: Optional[str] = None


class UploadChunkRequest(BaseModel):
    """分片上传请求"""

    upload_id: str
    chunk_number: int


class CompleteChunkedUploadRequest(BaseModel):
    """完成分片上传请求"""

    upload_id: str
    filename: str


class StartChunkedUploadRequest(BaseModel):
    """开始分片上传请求"""

    filename: str


class UploadChunkResponse(BaseModel):
    """分片上传响应"""

    upload_id: str
    chunk_number: int
    status: str


class StartChunkedUploadResponse(BaseModel):
    """开始分片上传响应"""

    upload_id: str
    status: str


__all__ = [
    "UploadFileOut",
    "UploadFromUrlRequest",
    "UploadChunkRequest",
    "CompleteChunkedUploadRequest",
    "StartChunkedUploadRequest",
    "UploadChunkResponse",
    "StartChunkedUploadResponse",
]
