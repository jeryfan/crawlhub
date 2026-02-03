"""Coder 工作区 API 路由

管理爬虫的 Coder 工作区。
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from schemas.crawlhub.coder_workspace import (
    CoderWorkspaceResponse,
    CoderWorkspaceStatusResponse,
    FileUploadResponse,
)
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import SpiderService
from services.crawlhub.coder_workspace_service import CoderWorkspaceService
from services.crawlhub.filebrowser_service import FileBrowserService, FileBrowserError
from services.crawlhub.coder_client import CoderAPIError

router = APIRouter(prefix="/spiders/{spider_id}/workspace", tags=["CrawlHub - Coder Workspaces"])


@router.post("", response_model=ApiResponse[CoderWorkspaceResponse])
async def create_or_get_workspace(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """创建或获取爬虫的 Coder 工作区

    如果工作区已存在，返回现有工作区信息。
    如果工作区不存在或已被删除，创建新的工作区。
    """
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    workspace_service = CoderWorkspaceService(db)
    try:
        workspace = await workspace_service.ensure_workspace_running(spider)

        # 获取 code-server URL
        url = await workspace_service.get_workspace_url(spider)

        return ApiResponse(
            data=CoderWorkspaceResponse(
                id=workspace["id"],
                name=workspace["name"],
                status=workspace.get("latest_build", {}).get("status", "unknown"),
                url=url,
                created_at=workspace.get("created_at"),
            )
        )
    except CoderAPIError as e:
        raise HTTPException(status_code=500, detail=f"Coder API 错误: {e}")
    finally:
        await workspace_service.close()


@router.get("", response_model=ApiResponse[CoderWorkspaceStatusResponse])
async def get_workspace_status(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取工作区状态"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    if not spider.coder_workspace_id:
        return ApiResponse(
            data=CoderWorkspaceStatusResponse(
                status="stopped",
                url=None,
                last_used_at=None,
            )
        )

    workspace_service = CoderWorkspaceService(db)
    try:
        status = await workspace_service.get_workspace_status(spider)
        if not status:
            return ApiResponse(
                data=CoderWorkspaceStatusResponse(
                    status="stopped",
                    url=None,
                    last_used_at=None,
                )
            )

        return ApiResponse(
            data=CoderWorkspaceStatusResponse(
                status=status["status"],
                url=status.get("url"),
                last_used_at=status.get("last_used_at"),
            )
        )
    except CoderAPIError as e:
        raise HTTPException(status_code=500, detail=f"Coder API 错误: {e}")
    finally:
        await workspace_service.close()


@router.post("/start", response_model=MessageResponse)
async def start_workspace(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """启动工作区"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    workspace_service = CoderWorkspaceService(db)
    try:
        await workspace_service.ensure_workspace_running(spider)
        return MessageResponse(msg="工作区启动中")
    except CoderAPIError as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {e}")
    finally:
        await workspace_service.close()


@router.post("/stop", response_model=MessageResponse)
async def stop_workspace(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """停止工作区"""
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    if not spider.coder_workspace_id:
        raise HTTPException(status_code=400, detail="工作区不存在")

    workspace_service = CoderWorkspaceService(db)
    try:
        success = await workspace_service.stop_workspace(spider)
        if success:
            return MessageResponse(msg="工作区停止中")
        else:
            raise HTTPException(status_code=500, detail="停止工作区失败")
    except CoderAPIError as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {e}")
    finally:
        await workspace_service.close()


@router.post("/upload", response_model=ApiResponse[FileUploadResponse])
async def upload_to_workspace(
    spider_id: str,
    file: UploadFile = File(...),
    path: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """上传文件/压缩包到工作区

    支持的文件类型:
    - .py, .json, .yaml, .yml 等代码文件: 直接上传
    - .zip 压缩包: 解压后逐个上传

    流程:
    1. 获取 spider 关联的 workspace
    2. 确保 workspace 处于 running 状态
    3. 等待 FileBrowser 服务就绪
    4. 上传文件
    """
    spider_service = SpiderService(db)
    spider = await spider_service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    # 确保工作区运行中
    workspace_service = CoderWorkspaceService(db)
    try:
        workspace = await workspace_service.ensure_workspace_running(spider)

        # 等待工作区完全就绪
        ready = await workspace_service.wait_for_workspace_ready(
            spider.coder_workspace_id, timeout=120
        )
        if not ready:
            raise HTTPException(status_code=504, detail="等待工作区就绪超时")

    except CoderAPIError as e:
        await workspace_service.close()
        raise HTTPException(status_code=500, detail=f"工作区启动失败: {e}")

    # 读取文件内容
    content = await file.read()
    filename = file.filename or "uploaded_file"

    # 上传文件
    filebrowser_service = FileBrowserService(workspace_service.coder_client)
    try:
        files_count, uploaded_files, failed_files = await filebrowser_service.upload_to_workspace(
            workspace_id=spider.coder_workspace_id,
            filename=filename,
            content=content,
            base_dir=path,
        )

        return ApiResponse(
            data=FileUploadResponse(
                success=files_count > 0,
                files_count=files_count,
                uploaded_files=uploaded_files,
                errors=failed_files if failed_files else None,
            )
        )
    except FileBrowserError as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {e}")
    finally:
        await workspace_service.close()
