"""文档相关 Schema"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.document import Document


class DocumentBase(BaseModel):
    """文档基础信息"""

    name: str = Field(..., description="文档名称")
    doc_type: str = Field(..., description="文档类型")


class DocumentCreate(BaseModel):
    """创建文档请求"""

    upload_file_id: str = Field(..., description="上传文件ID")
    name: str = Field(..., description="文档名称")
    doc_type: str = Field(..., description="文档类型")
    file_size: int = Field(..., description="文件大小")


class DocumentOut(BaseModel):
    """文档输出"""

    id: str
    tenant_id: str
    file_id: str
    name: str
    doc_type: str
    file_url: Optional[str] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    parse_started_at: Optional[datetime] = None
    parse_completed_at: Optional[datetime] = None
    parse_error: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentWithTask(DocumentOut):
    """文档及任务信息"""

    task: Optional["ParseTaskOut"] = None


class ParseTaskOut(BaseModel):
    """解析任务输出"""

    id: str
    document_id: str
    task_id: str
    status: str
    progress: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    items: Optional[list[DocumentOut]] = []
    total: int
    page: int
    page_size: int


class StartParseRequest(BaseModel):
    """开始解析请求"""

    document_id: str = Field(..., description="文档ID")


class StartParseResponse(BaseModel):
    """开始解析响应"""

    task_id: str = Field(..., description="任务ID")
    document_id: str = Field(..., description="文档ID")


class DocumentStatusResponse(BaseModel):
    """文档状态响应"""

    document_id: str
    status: str
    progress: int
    task_id: Optional[str] = None
    error_message: Optional[str] = None


class UploadAndParseResponse(BaseModel):
    """上传并解析响应"""

    document_id: str = Field(..., description="文档ID")
    task_id: str = Field(..., description="解析任务ID")
    file_url: str = Field(..., description="文件URL")
