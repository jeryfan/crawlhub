import sys
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from models.engine import get_db
from dependencies.auth import get_current_admin
from libs.datetime_utils import naive_utc_now
from models.account import Account, AccountStatus, InvitationCode, Tenant, TenantStatus
from models.admin import Admin, AdminStatus
from schemas.platform import DashboardStats, DashboardTrend, DashboardTrends
from schemas.response import ApiResponse

router = APIRouter(tags=["Platform - Dashboard"])


@router.get("/dashboard/stats", response_model=ApiResponse[DashboardStats])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取 Dashboard 统计数据"""
    now = naive_utc_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # 账户统计
    total_accounts = await db.scalar(select(func.count()).select_from(Account)) or 0
    active_accounts = (
        await db.scalar(select(func.count()).where(Account.status == AccountStatus.ACTIVE)) or 0
    )
    new_accounts_today = (
        await db.scalar(select(func.count()).where(Account.created_at >= today_start)) or 0
    )
    new_accounts_week = (
        await db.scalar(select(func.count()).where(Account.created_at >= week_start)) or 0
    )

    # 管理员统计
    total_admins = await db.scalar(select(func.count()).select_from(Admin)) or 0
    active_admins = (
        await db.scalar(select(func.count()).where(Admin.status == AdminStatus.ACTIVE)) or 0
    )

    # 租户统计
    total_tenants = await db.scalar(select(func.count()).select_from(Tenant)) or 0
    active_tenants = (
        await db.scalar(select(func.count()).where(Tenant.status == TenantStatus.NORMAL)) or 0
    )

    # 邀请码统计
    total_invitation_codes = await db.scalar(select(func.count()).select_from(InvitationCode)) or 0
    used_invitation_codes = (
        await db.scalar(select(func.count()).where(InvitationCode.status == "used")) or 0
    )

    return ApiResponse(
        data=DashboardStats(
            total_accounts=total_accounts,
            active_accounts=active_accounts,
            new_accounts_today=new_accounts_today,
            new_accounts_week=new_accounts_week,
            total_admins=total_admins,
            active_admins=active_admins,
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_invitation_codes=total_invitation_codes,
            used_invitation_codes=used_invitation_codes,
        )
    )


@router.get("/dashboard/trends", response_model=ApiResponse[DashboardTrends])
async def get_dashboard_trends(
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取 Dashboard 趋势数据"""
    now = naive_utc_now()
    start_date = now - timedelta(days=days)

    # 账户趋势
    account_trends = await _get_daily_counts(db, Account, Account.created_at, start_date, now)

    # 租户趋势
    tenant_trends = await _get_daily_counts(db, Tenant, Tenant.created_at, start_date, now)

    return ApiResponse(
        data=DashboardTrends(
            account_trends=account_trends,
            tenant_trends=tenant_trends,
        )
    )


async def _get_daily_counts(
    db: AsyncSession,
    model,
    date_column,
    start_date,
    end_date,
) -> list[DashboardTrend]:
    """获取每日统计数据"""
    # 使用 date_trunc 获取每日统计
    result = await db.execute(
        select(
            func.date(date_column).label("date"),
            func.count().label("count"),
        )
        .where(
            and_(
                date_column >= start_date,
                date_column <= end_date,
            )
        )
        .group_by(func.date(date_column))
        .order_by(func.date(date_column))
    )

    rows = result.all()
    return [DashboardTrend(date=str(row.date), count=row.count) for row in rows]


@router.get("/dashboard/recent-accounts", response_model=ApiResponse[list[dict]])
async def get_recent_accounts(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取最近注册的用户"""
    result = await db.execute(select(Account).order_by(Account.created_at.desc()).limit(limit))
    accounts = result.scalars().all()

    return ApiResponse(
        data=[
            {
                "id": acc.id,
                "name": acc.name,
                "email": acc.email,
                "status": acc.status,
                "created_at": acc.created_at.isoformat() if acc.created_at else None,
            }
            for acc in accounts
        ]
    )


@router.get("/dashboard/recent-tenants", response_model=ApiResponse[list[dict]])
async def get_recent_tenants(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取最近创建的租户"""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()).limit(limit))
    tenants = result.scalars().all()

    return ApiResponse(
        data=[
            {
                "id": t.id,
                "name": t.name,
                "plan": t.plan,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tenants
        ]
    )


@router.get("/dashboard/system-info", response_model=ApiResponse[dict])
async def get_system_info(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取系统信息"""
    return ApiResponse(
        data={
            "python_version": sys.version,
            "debug_mode": app_config.DEBUG,
            "database_type": "postgresql",
        }
    )
