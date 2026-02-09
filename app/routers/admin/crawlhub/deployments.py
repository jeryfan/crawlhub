from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from schemas.crawlhub.deployment import (
    DeployRequest,
    DeploymentResponse,
    DeploymentListResponse,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import SpiderService
from services.crawlhub.deployment_service import DeploymentService
from services.crawlhub.filebrowser_service import FileBrowserError

router = APIRouter(prefix="/spiders/{spider_id}/deployments", tags=["CrawlHub - Deployments"])


@router.post("", response_model=ApiResponse[DeploymentResponse])
async def create_deployment(
    spider_id: str,
    data: DeployRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """从工作区部署当前代码"""
    spider = await SpiderService(db).get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    service = DeploymentService(db)
    try:
        deployment = await service.deploy_from_workspace(
            spider,
            deploy_note=data.deploy_note if data else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileBrowserError as e:
        raise HTTPException(status_code=504, detail=f"工作区文件服务未就绪: {e}")

    return ApiResponse(data=DeploymentResponse.model_validate(deployment))


@router.get("", response_model=ApiResponse[PaginatedResponse[DeploymentResponse]])
async def list_deployments(
    spider_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取部署历史"""
    service = DeploymentService(db)
    deployments, total = await service.get_list(spider_id, page, page_size)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[DeploymentResponse.model_validate(d) for d in deployments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/{deployment_id}", response_model=ApiResponse[DeploymentResponse])
async def get_deployment(
    spider_id: str,
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取部署详情"""
    service = DeploymentService(db)
    deployment = await service.get_deployment(deployment_id)
    if not deployment or deployment.spider_id != spider_id:
        raise HTTPException(status_code=404, detail="部署记录不存在")
    return ApiResponse(data=DeploymentResponse.model_validate(deployment))


@router.post("/{deployment_id}/rollback", response_model=ApiResponse[DeploymentResponse])
async def rollback_deployment(
    spider_id: str,
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """回滚到指定版本"""
    spider = await SpiderService(db).get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    service = DeploymentService(db)
    try:
        deployment = await service.rollback(spider, deployment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ApiResponse(data=DeploymentResponse.model_validate(deployment))


@router.delete("/{deployment_id}", response_model=MessageResponse)
async def delete_deployment(
    spider_id: str,
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除部署版本（不能删除活跃版本）"""
    spider = await SpiderService(db).get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    service = DeploymentService(db)
    try:
        await service.delete_deployment(spider, deployment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MessageResponse(msg="部署已删除")
