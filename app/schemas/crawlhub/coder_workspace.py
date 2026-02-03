"""Coder 工作区相关 Pydantic 模型"""

from typing import Literal

from pydantic import BaseModel


WorkspaceStatus = Literal["pending", "starting", "running", "stopping", "stopped", "failed", "unknown"]
AgentStatus = Literal["connecting", "connected", "disconnected", "timeout"]


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
    agent_status: AgentStatus | None = None
    url: str | None = None
    last_used_at: str | None = None
    # 详细状态信息
    build_status: str | None = None
    build_job: str | None = None
    is_ready: bool = False


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    success: bool
    files_count: int
    uploaded_files: list[str]
    errors: list[str] | None = None
