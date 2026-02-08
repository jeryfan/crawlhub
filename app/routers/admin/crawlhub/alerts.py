from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub.alert import AlertLevel
from models.engine import get_db
from schemas.response import ApiResponse, MessageResponse
from services.crawlhub.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["CrawlHub - Alerts"])


@router.get("")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: AlertLevel | None = Query(None),
    is_read: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取告警列表"""
    service = AlertService(db)
    alerts, total = await service.get_list(page, page_size, level, is_read)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(data={
        "items": [
            {
                "id": a.id,
                "type": a.type,
                "level": a.level.value,
                "message": a.message,
                "spider_id": a.spider_id,
                "task_id": a.task_id,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
):
    """获取未读告警数"""
    service = AlertService(db)
    count = await service.get_unread_count()
    return ApiResponse(data={"count": count})


@router.post("/{alert_id}/read", response_model=MessageResponse)
async def mark_as_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    """标记告警已读"""
    service = AlertService(db)
    success = await service.mark_as_read(alert_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="告警不存在")
    return MessageResponse(msg="已标记为已读")


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
):
    """全部标记已读"""
    service = AlertService(db)
    count = await service.mark_all_as_read()
    return MessageResponse(msg=f"已标记 {count} 条告警为已读")
