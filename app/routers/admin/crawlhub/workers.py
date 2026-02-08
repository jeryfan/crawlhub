from fastapi import APIRouter, Request

from schemas.response import ApiResponse

router = APIRouter(prefix="/workers", tags=["CrawlHub - Workers"])


@router.get("")
async def list_workers(request: Request):
    """获取所有 Worker 状态"""
    from services.crawlhub.worker_service import WorkerService

    celery_app = request.app.state.celery
    service = WorkerService(celery_app)
    workers = service.get_workers()

    return ApiResponse(data={
        "workers": workers,
        "total": len(workers),
    })


@router.get("/active-tasks")
async def get_active_tasks(request: Request):
    """获取正在执行的任务"""
    from services.crawlhub.worker_service import WorkerService

    celery_app = request.app.state.celery
    service = WorkerService(celery_app)
    tasks = service.get_active_tasks()

    return ApiResponse(data={
        "tasks": tasks,
        "total": len(tasks),
    })


@router.get("/queued-tasks")
async def get_queued_tasks(request: Request):
    """获取排队中的任务"""
    from services.crawlhub.worker_service import WorkerService

    celery_app = request.app.state.celery
    service = WorkerService(celery_app)
    tasks = service.get_queued_tasks()

    return ApiResponse(data={
        "tasks": tasks,
        "total": len(tasks),
    })
