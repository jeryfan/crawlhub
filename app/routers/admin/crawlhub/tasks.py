from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import SpiderTask, SpiderTaskStatus
from models.engine import get_db
from schemas.crawlhub import TaskResponse
from schemas.platform import PaginatedResponse
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.log_service import LogService

router = APIRouter(prefix="/tasks", tags=["CrawlHub - Tasks"])


@router.get("", response_model=ApiResponse[PaginatedResponse[TaskResponse]])
async def list_tasks(
    spider_id: str | None = Query(None),
    status: SpiderTaskStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    query = select(SpiderTask)

    if spider_id:
        query = query.where(SpiderTask.spider_id == spider_id)
    if status:
        query = query.where(SpiderTask.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    total_pages = (total + page_size - 1) // page_size

    query = query.order_by(SpiderTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tasks = list(result.scalars().all())

    return ApiResponse(data=PaginatedResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    ))


@router.get("/{task_id}", response_model=ApiResponse[TaskResponse])
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取任务详情"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ApiResponse(data=TaskResponse.model_validate(task))


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
):
    """获取任务日志"""
    log_service = LogService()
    log = await log_service.get_by_task(task_id)
    if not log:
        return ApiResponse(data={"stdout": "", "stderr": "", "message": "暂无日志"})
    return ApiResponse(data=log)


@router.post("/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """取消任务"""
    result = await db.execute(
        select(SpiderTask).where(SpiderTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in (SpiderTaskStatus.PENDING, SpiderTaskStatus.RUNNING):
        raise HTTPException(status_code=409, detail="任务已完成，无法取消")

    task.status = SpiderTaskStatus.CANCELLED
    await db.commit()
    return MessageResponse(msg="任务已取消")
