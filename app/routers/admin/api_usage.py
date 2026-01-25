import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_admin
from models.account import Tenant
from models.api_key import ApiKey
from models.engine import get_db
from schemas.api_usage import (
    ApiUsageByEndpoint,
    ApiUsageItem,
    ApiUsageListResponse,
    ApiUsageStats,
    ApiUsageStatsResponse,
    ApiUsageTrendItem,
)
from schemas.response import ApiResponse
from services.api_key_service import ApiUsageService

router = APIRouter(tags=["Platform - API Usage"])


@router.get("/api-usage", response_model=ApiResponse[ApiUsageListResponse])
async def list_api_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    endpoint: str | None = Query(None),
    service_type: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    service = ApiUsageService(db)
    logs, total = await service.list_usage_logs(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        service_type=service_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    api_key_ids = list(set(log.api_key_id for log in logs))
    tenant_ids = list(set(log.tenant_id for log in logs))

    api_keys = {}
    if api_key_ids:
        result = await db.execute(select(ApiKey).where(ApiKey.id.in_(api_key_ids)))
        for key in result.scalars():
            api_keys[key.id] = {"name": key.name, "prefix": key.key_prefix}

    tenants = {}
    if tenant_ids:
        result = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        for tenant in result.scalars():
            tenants[tenant.id] = tenant.name

    items = []
    for log in logs:
        item = ApiUsageItem.model_validate(log)
        key_info = api_keys.get(log.api_key_id, {})
        item.api_key_name = key_info.get("name")
        item.api_key_prefix = key_info.get("prefix")
        item.tenant_name = tenants.get(log.tenant_id)
        items.append(item)

    return ApiResponse(
        data=ApiUsageListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/api-usage/stats", response_model=ApiResponse[ApiUsageStatsResponse])
async def get_api_usage_stats(
    tenant_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    granularity: str = Query("day"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    service = ApiUsageService(db)

    stats_data = await service.get_usage_stats(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
    )

    error_rate = 0.0
    if stats_data["total_requests"] > 0:
        error_rate = (stats_data["total_errors"] / stats_data["total_requests"]) * 100

    stats = ApiUsageStats(
        total_requests=stats_data["total_requests"],
        avg_latency_ms=stats_data["avg_latency_ms"],
        total_errors=stats_data["total_errors"],
        error_rate=round(error_rate, 2),
    )

    by_endpoint_data = await service.get_usage_by_endpoint(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
    )
    by_endpoint = [
        ApiUsageByEndpoint(
            endpoint=item["endpoint"],
            request_count=item["request_count"],
            avg_latency_ms=item["avg_latency_ms"],
        )
        for item in by_endpoint_data
    ]

    trends_data = await service.get_usage_trends(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )
    trends = [
        ApiUsageTrendItem(
            period=item["period"],
            request_count=item["request_count"],
        )
        for item in trends_data
    ]

    return ApiResponse(
        data=ApiUsageStatsResponse(
            stats=stats,
            by_endpoint=by_endpoint,
            trends=trends,
        )
    )


@router.get("/api-usage/by-endpoint", response_model=ApiResponse[list[ApiUsageByEndpoint]])
async def get_usage_by_endpoint(
    tenant_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    service = ApiUsageService(db)
    data = await service.get_usage_by_endpoint(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
    )

    items = [
        ApiUsageByEndpoint(
            endpoint=item["endpoint"],
            request_count=item["request_count"],
            avg_latency_ms=item["avg_latency_ms"],
        )
        for item in data
    ]

    return ApiResponse(data=items)


@router.get("/api-usage/trends", response_model=ApiResponse[list[ApiUsageTrendItem]])
async def get_usage_trends(
    tenant_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    granularity: str = Query("day"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    service = ApiUsageService(db)
    data = await service.get_usage_trends(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    items = [
        ApiUsageTrendItem(
            period=item["period"],
            request_count=item["request_count"],
        )
        for item in data
    ]

    return ApiResponse(data=items)


@router.get("/api-usage/export")
async def export_api_usage(
    tenant_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    service = ApiUsageService(db)

    logs, _ = await service.list_usage_logs(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000,
    )

    api_key_ids = list(set(log.api_key_id for log in logs))
    tenant_ids = list(set(log.tenant_id for log in logs))

    api_keys = {}
    if api_key_ids:
        result = await db.execute(select(ApiKey).where(ApiKey.id.in_(api_key_ids)))
        for key in result.scalars():
            api_keys[key.id] = {"name": key.name, "prefix": key.key_prefix}

    tenants = {}
    if tenant_ids:
        result = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        for tenant in result.scalars():
            tenants[tenant.id] = tenant.name

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "ID",
            "API Key",
            "Tenant",
            "Endpoint",
            "Method",
            "Service Type",
            "Latency(ms)",
            "Status Code",
            "IP Address",
            "Time",
        ]
    )

    for log in logs:
        key_info = api_keys.get(log.api_key_id, {})
        writer.writerow(
            [
                log.id,
                key_info.get("name", "Unknown"),
                tenants.get(log.tenant_id, "Unknown"),
                log.endpoint,
                log.method,
                log.service_type,
                log.latency_ms,
                log.status_code,
                log.ip_address,
                log.created_at.isoformat() if log.created_at else "",
            ]
        )

    output.seek(0)

    filename = f"api_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
