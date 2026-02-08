from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.crawlhub import (
    Proxy, ProxyStatus,
    Spider, SpiderTask, SpiderTaskStatus,
)
from models.crawlhub.alert import Alert
from models.engine import get_db
from schemas.response import ApiResponse

router = APIRouter(prefix="/dashboard", tags=["CrawlHub - Dashboard"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取仪表盘统计数据"""

    # 爬虫统计
    spider_total = await db.scalar(select(func.count()).select_from(Spider)) or 0
    spider_active = await db.scalar(
        select(func.count()).select_from(
            select(Spider).where(Spider.is_active == True).subquery()
        )
    ) or 0

    # 任务统计 (最近24小时)
    since = datetime.utcnow() - timedelta(hours=24)
    tasks_24h = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(SpiderTask.created_at >= since).subquery()
        )
    ) or 0
    tasks_completed = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.created_at >= since,
                SpiderTask.status == SpiderTaskStatus.COMPLETED,
            ).subquery()
        )
    ) or 0
    tasks_failed = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.created_at >= since,
                SpiderTask.status == SpiderTaskStatus.FAILED,
            ).subquery()
        )
    ) or 0
    tasks_running = await db.scalar(
        select(func.count()).select_from(
            select(SpiderTask).where(
                SpiderTask.status == SpiderTaskStatus.RUNNING,
            ).subquery()
        )
    ) or 0

    # 代理统计
    proxy_total = await db.scalar(select(func.count()).select_from(Proxy)) or 0
    proxy_active = await db.scalar(
        select(func.count()).select_from(
            select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE).subquery()
        )
    ) or 0
    proxy_inactive = await db.scalar(
        select(func.count()).select_from(
            select(Proxy).where(Proxy.status == ProxyStatus.INACTIVE).subquery()
        )
    ) or 0

    # 未读告警数
    unread_alerts = await db.scalar(
        select(func.count()).select_from(
            select(Alert).where(Alert.is_read == False).subquery()
        )
    ) or 0

    return ApiResponse(data={
        "spiders": {
            "total": spider_total,
            "active": spider_active,
        },
        "tasks_24h": {
            "total": tasks_24h,
            "completed": tasks_completed,
            "failed": tasks_failed,
            "running": tasks_running,
            "success_rate": round(tasks_completed / tasks_24h * 100, 1) if tasks_24h > 0 else 0,
        },
        "proxies": {
            "total": proxy_total,
            "active": proxy_active,
            "inactive": proxy_inactive,
        },
        "unread_alerts": unread_alerts,
    })


@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """获取最近 N 天的任务趋势"""
    trends = []
    for i in range(days - 1, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        total = await db.scalar(
            select(func.count()).select_from(
                select(SpiderTask).where(
                    SpiderTask.created_at >= day_start,
                    SpiderTask.created_at < day_end,
                ).subquery()
            )
        ) or 0

        completed = await db.scalar(
            select(func.count()).select_from(
                select(SpiderTask).where(
                    SpiderTask.created_at >= day_start,
                    SpiderTask.created_at < day_end,
                    SpiderTask.status == SpiderTaskStatus.COMPLETED,
                ).subquery()
            )
        ) or 0

        failed = await db.scalar(
            select(func.count()).select_from(
                select(SpiderTask).where(
                    SpiderTask.created_at >= day_start,
                    SpiderTask.created_at < day_end,
                    SpiderTask.status == SpiderTaskStatus.FAILED,
                ).subquery()
            )
        ) or 0

        trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total": total,
            "completed": completed,
            "failed": failed,
        })

    return ApiResponse(data=trends)
