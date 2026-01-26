from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from schemas.crawlhub import (
    SpiderCreate,
    SpiderUpdate,
    SpiderResponse,
    SpiderListResponse,
)
from services.crawlhub import SpiderService

router = APIRouter(prefix="/spiders", tags=["CrawlHub - Spiders"])


@router.get("", response_model=SpiderListResponse)
async def list_spiders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: str | None = Query(None),
    keyword: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫列表"""
    service = SpiderService(db)
    spiders, total = await service.get_list(page, page_size, project_id, keyword, is_active)
    return SpiderListResponse(
        items=[SpiderResponse.model_validate(s) for s in spiders],
        total=total,
    )


@router.get("/templates")
async def get_templates(
    db: AsyncSession = Depends(get_db),
):
    """获取脚本模板"""
    service = SpiderService(db)
    return service.get_templates()


@router.get("/{spider_id}", response_model=SpiderResponse)
async def get_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫详情"""
    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="Spider not found")
    return SpiderResponse.model_validate(spider)


@router.post("", response_model=SpiderResponse)
async def create_spider(
    data: SpiderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建爬虫"""
    service = SpiderService(db)
    spider = await service.create(data)
    return SpiderResponse.model_validate(spider)


@router.put("/{spider_id}", response_model=SpiderResponse)
async def update_spider(
    spider_id: str,
    data: SpiderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新爬虫"""
    service = SpiderService(db)
    spider = await service.update(spider_id, data)
    if not spider:
        raise HTTPException(status_code=404, detail="Spider not found")
    return SpiderResponse.model_validate(spider)


@router.delete("/{spider_id}")
async def delete_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除爬虫"""
    service = SpiderService(db)
    success = await service.delete(spider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Spider not found")
    return {"message": "Spider deleted"}
