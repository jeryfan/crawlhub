from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from models.crawlhub import ProxyStatus
from schemas.crawlhub import (
    ProxyCreate,
    ProxyBatchCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyListResponse,
)
from services.crawlhub import ProxyService

router = APIRouter(prefix="/proxies", tags=["CrawlHub - Proxies"])


@router.get("", response_model=ProxyListResponse)
async def list_proxies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ProxyStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取代理列表"""
    service = ProxyService(db)
    proxies, total = await service.get_list(page, page_size, status)
    return ProxyListResponse(
        items=[ProxyResponse.model_validate(p) for p in proxies],
        total=total,
    )


@router.get("/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取代理详情"""
    service = ProxyService(db)
    proxy = await service.get_by_id(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.post("", response_model=ProxyResponse)
async def create_proxy(
    data: ProxyCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建代理"""
    service = ProxyService(db)
    proxy = await service.create(data)
    return ProxyResponse.model_validate(proxy)


@router.post("/batch")
async def batch_create_proxies(
    data: ProxyBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    """批量创建代理"""
    service = ProxyService(db)
    count = await service.batch_create(data.proxies)
    return {"message": f"Created {count} proxies"}


@router.put("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: str,
    data: ProxyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新代理"""
    service = ProxyService(db)
    proxy = await service.update(proxy_id, data)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return ProxyResponse.model_validate(proxy)


@router.delete("/{proxy_id}")
async def delete_proxy(
    proxy_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除代理"""
    service = ProxyService(db)
    success = await service.delete(proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {"message": "Proxy deleted"}
