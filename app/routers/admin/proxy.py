from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_admin
from models.engine import get_db
from schemas.proxy import (
    ProxyLogEntry,
    ProxyLogListResponse,
    ProxyLogStatistics,
    ProxyRouteCreate,
    ProxyRouteListResponse,
    ProxyRouteResponse,
    ProxyRouteUpdate,
)
from schemas.response import ApiResponse, MessageResponse
from services.proxy_service import ProxyLogService, ProxyRouteService

router = APIRouter(prefix="/proxy", tags=["proxy"])


# ============ Proxy Routes Management ============


@router.get("/routes", response_model=ApiResponse[ProxyRouteListResponse])
async def list_proxy_routes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all proxy routes with pagination."""
    service = ProxyRouteService(db)
    routes, total = await service.list_routes(page=page, page_size=page_size, status=status)

    return ApiResponse(
        data=ProxyRouteListResponse(
            items=[ProxyRouteResponse.model_validate(r) for r in routes],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/routes", response_model=ApiResponse[ProxyRouteResponse])
async def create_proxy_route(
    data: ProxyRouteCreate,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new proxy route."""
    service = ProxyRouteService(db)

    # Check if path already exists
    existing = await service.get_route_by_path(data.path)
    if existing:
        raise HTTPException(status_code=400, detail=f"Route path '{data.path}' already exists")

    route = await service.create_route(data, created_by=current_admin.id)
    return ApiResponse(data=ProxyRouteResponse.model_validate(route))


@router.get("/routes/{route_id}", response_model=ApiResponse[ProxyRouteResponse])
async def get_proxy_route(
    route_id: str,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a proxy route by ID."""
    service = ProxyRouteService(db)
    route = await service.get_route(route_id)

    if not route:
        raise HTTPException(status_code=404, detail="Proxy route not found")

    return ApiResponse(data=ProxyRouteResponse.model_validate(route))


@router.put("/routes/{route_id}", response_model=ApiResponse[ProxyRouteResponse])
async def update_proxy_route(
    route_id: str,
    data: ProxyRouteUpdate,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a proxy route."""
    service = ProxyRouteService(db)

    # Check if new path conflicts with existing route
    if data.path:
        existing = await service.get_route_by_path(data.path)
        if existing and existing.id != route_id:
            raise HTTPException(status_code=400, detail=f"Route path '{data.path}' already exists")

    route = await service.update_route(route_id, data)
    if not route:
        raise HTTPException(status_code=404, detail="Proxy route not found")

    return ApiResponse(data=ProxyRouteResponse.model_validate(route))


@router.delete("/routes/{route_id}", response_model=MessageResponse)
async def delete_proxy_route(
    route_id: str,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a proxy route."""
    service = ProxyRouteService(db)
    deleted = await service.delete_route(route_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Proxy route not found")

    return MessageResponse(msg="Proxy route deleted successfully")


@router.post("/routes/{route_id}/toggle", response_model=ApiResponse[ProxyRouteResponse])
async def toggle_proxy_route_status(
    route_id: str,
    current_admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the status of a proxy route."""
    service = ProxyRouteService(db)
    route = await service.toggle_status(route_id)

    if not route:
        raise HTTPException(status_code=404, detail="Proxy route not found")

    return ApiResponse(data=ProxyRouteResponse.model_validate(route))


# ============ Proxy Logs ============


@router.get("/logs", response_model=ApiResponse[ProxyLogListResponse])
async def list_proxy_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    route_id: str | None = Query(None),
    route_path: str | None = Query(None),
    status_code: int | None = Query(None),
    client_ip: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    has_error: bool | None = Query(None),
    current_admin=Depends(get_current_admin),
):
    """Search proxy logs with filters."""
    service = ProxyLogService()
    logs, total = await service.search_logs(
        page=page,
        page_size=page_size,
        route_id=route_id,
        route_path=route_path,
        status_code=status_code,
        client_ip=client_ip,
        start_time=start_time,
        end_time=end_time,
        has_error=has_error,
    )

    return ApiResponse(
        data=ProxyLogListResponse(
            items=[ProxyLogEntry.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/logs/statistics", response_model=ApiResponse[ProxyLogStatistics])
async def get_proxy_log_statistics(
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    route_id: str | None = Query(None),
    current_admin=Depends(get_current_admin),
):
    """Get proxy log statistics."""
    service = ProxyLogService()
    stats = await service.get_statistics(
        start_time=start_time,
        end_time=end_time,
        route_id=route_id,
    )

    return ApiResponse(data=ProxyLogStatistics.model_validate(stats))


@router.get("/logs/{log_id}", response_model=ApiResponse[ProxyLogEntry])
async def get_proxy_log(
    log_id: str,
    current_admin=Depends(get_current_admin),
):
    """Get a proxy log entry by ID."""
    service = ProxyLogService()
    log = await service.get_log(log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Proxy log not found")

    return ApiResponse(data=ProxyLogEntry.model_validate(log))


@router.delete("/logs", response_model=MessageResponse)
async def clear_proxy_logs(
    route_id: str | None = Query(
        None, description="Optional route ID to clear logs for specific route"
    ),
    current_admin=Depends(get_current_admin),
):
    """Clear proxy logs. If route_id is provided, only clear logs for that route."""
    service = ProxyLogService()

    if route_id:
        deleted_count = await service.delete_logs_by_route(route_id)
        return MessageResponse(msg=f"Deleted {deleted_count} logs for route {route_id}")
    else:
        deleted_count = await service.delete_all_logs()
        return MessageResponse(msg=f"Deleted {deleted_count} logs")
