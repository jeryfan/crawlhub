from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from models.crawlhub import ProxyStatus
from schemas.crawlhub import (
    ProxyCreate,
    ProxyBatchCreate,
    ProxyUpdate,
    ProxyResponse,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import ProxyService

router = APIRouter(prefix="/proxies", tags=["CrawlHub - Proxies"])


@router.get("", response_model=ApiResponse[PaginatedResponse[ProxyResponse]])
async def list_proxies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ProxyStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取代理列表"""
    service = ProxyService(db)
    proxies, total = await service.get_list(page, page_size, status)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[ProxyResponse.model_validate(p) for p in proxies],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.post("", response_model=ApiResponse[ProxyResponse])
async def create_proxy(
    data: ProxyCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建代理"""
    service = ProxyService(db)
    proxy = await service.create(data)
    return ApiResponse(data=ProxyResponse.model_validate(proxy))


@router.post("/batch", response_model=MessageResponse)
async def batch_create_proxies(
    data: ProxyBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    """批量创建代理"""
    service = ProxyService(db)
    count = await service.batch_create(data.proxies)
    return MessageResponse(msg=f"成功创建 {count} 个代理")


@router.post("/check-all", response_model=MessageResponse)
async def check_all_proxies():
    """检测所有代理可用性（异步）"""
    from tasks.proxy_tasks import check_all_proxies as check_all_proxies_task

    check_all_proxies_task.delay()
    return MessageResponse(msg="代理批量检测已提交")


@router.get("/{proxy_id}", response_model=ApiResponse[ProxyResponse])
async def get_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取代理详情"""
    service = ProxyService(db)
    proxy = await service.get_by_id(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    return ApiResponse(data=ProxyResponse.model_validate(proxy))


@router.put("/{proxy_id}", response_model=ApiResponse[ProxyResponse])
async def update_proxy(
    proxy_id: str,
    data: ProxyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新代理"""
    service = ProxyService(db)
    proxy = await service.update(proxy_id, data)
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    return ApiResponse(data=ProxyResponse.model_validate(proxy))


@router.delete("/{proxy_id}", response_model=MessageResponse)
async def delete_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除代理"""
    service = ProxyService(db)
    success = await service.delete(proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="代理不存在")
    return MessageResponse(msg="代理删除成功")


@router.post("/{proxy_id}/check", response_model=MessageResponse)
async def check_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """检测单个代理可用性"""
    service = ProxyService(db)
    proxy = await service.get_by_id(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")

    success = await service.check_proxy(proxy)
    if success:
        return MessageResponse(msg="代理可用")
    else:
        return MessageResponse(msg="代理不可用")
