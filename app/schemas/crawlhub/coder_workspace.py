"""Coder 工作区相关 Pydantic 模型"""

from typing import Literal

from pydantic import BaseModel


WorkspaceStatus = Literal["pending", "starting", "running", "stopping", "stopped", "failed", "unknown"]


class CoderWorkspaceResponse(BaseModel):
    """工作区响应"""

    id: str
    name: str
    status: WorkspaceStatus
    url: str | None = None
    created_at: str | None = None


class CoderWorkspaceStatusResponse(BaseModel):
    """工作区状态响应"""

    status: WorkspaceStatus
    url: str | None = None
    last_used_at: str | None = None


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    success: bool
    files_count: int
    uploaded_files: list[str]
    errors: list[str] | None = None
