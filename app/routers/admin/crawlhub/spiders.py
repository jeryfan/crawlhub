import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import SpiderTask, SpiderTaskStatus
from models.engine import get_db
from schemas.crawlhub import (
    SpiderCreate,
    SpiderUpdate,
    SpiderResponse,
)
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub import SpiderService
from services.crawlhub.spider_runner_service import SpiderRunnerService

router = APIRouter(prefix="/spiders", tags=["CrawlHub - Spiders"])


@router.get("", response_model=ApiResponse[PaginatedResponse[SpiderResponse]])
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
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=[SpiderResponse.model_validate(s) for s in spiders],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/templates", response_model=ApiResponse[list])
async def get_templates():
    """获取脚本模板"""
    service = SpiderService(None)
    return ApiResponse(data=service.get_templates())


@router.get("/{spider_id}", response_model=ApiResponse[SpiderResponse])
async def get_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取爬虫详情"""
    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    return ApiResponse(data=SpiderResponse.model_validate(spider))


@router.post("", response_model=ApiResponse[SpiderResponse])
async def create_spider(
    data: SpiderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建爬虫"""
    service = SpiderService(db)
    spider = await service.create(data)
    return ApiResponse(data=SpiderResponse.model_validate(spider))


@router.put("/{spider_id}", response_model=ApiResponse[SpiderResponse])
async def update_spider(
    spider_id: str,
    data: SpiderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新爬虫"""
    service = SpiderService(db)
    spider = await service.update(spider_id, data)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    return ApiResponse(data=SpiderResponse.model_validate(spider))


@router.delete("/{spider_id}", response_model=MessageResponse)
async def delete_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除爬虫"""
    service = SpiderService(db)
    success = await service.delete(spider_id)
    if not success:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    return MessageResponse(msg="爬虫删除成功")


@router.post("/{spider_id}/test-run")
async def test_run_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """启动测试运行"""
    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    runner = SpiderRunnerService(db)
    task = await runner.create_test_task(spider)

    async def event_generator():
        async for event in runner.run_test(spider, task):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.post("/{spider_id}/run", response_model=MessageResponse)
async def run_spider(
    spider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """手动触发爬虫执行（走 Celery 队列）"""
    from tasks.spider_tasks import execute_spider

    service = SpiderService(db)
    spider = await service.get_by_id(spider_id)
    if not spider:
        raise HTTPException(status_code=404, detail="爬虫不存在")

    # Check for existing running/pending tasks
    running_count = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.spider_id == spider_id,
                SpiderTask.status.in_([SpiderTaskStatus.PENDING, SpiderTaskStatus.RUNNING]),
            ).subquery()
        )
    )
    if running_count and running_count > 0:
        raise HTTPException(status_code=409, detail="该爬虫已有运行中或等待中的任务")

    # 先创建任务记录，确保前端 refetch 后立即可见
    runner = SpiderRunnerService(db)
    task = await runner.create_task(spider, trigger_type="manual")

    execute_spider.delay(spider_id, task_id=str(task.id), trigger_type="manual")
    return MessageResponse(msg="任务已提交到执行队列")
