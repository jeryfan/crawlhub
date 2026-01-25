from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from dependencies.auth import get_current_account_with_tenant
from schemas.response import ApiResponse
from services.feature_service import FeatureService


router = APIRouter()


@router.get("/features", response_model=ApiResponse)
async def get_features(
    db: AsyncSession = Depends(get_db),
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    """Get feature configuration for current tenant"""
    current_user, current_tenant_id = current_account_with_tenant

    # 使用异步方法从数据库获取完整的订阅计划配置
    features = await FeatureService.get_features_async(
        db,
        current_tenant_id,
        current_user.current_tenant.plan if current_user.current_tenant else None,
    )

    return ApiResponse(data=features.model_dump())


@router.get("/system-features", response_model=ApiResponse)
async def get_system_features(db: AsyncSession = Depends(get_db)):
    """Get system-wide feature configuration"""
    system_features = await FeatureService.get_system_features_async(db)
    return ApiResponse(data=system_features.model_dump())
