from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_admin
from models.engine import get_db
from schemas.response import ApiResponse
from schemas.settings import (
    GeneralSettingsConfig,
    GeneralSettingsConfigUpdate,
    GeneralSettingsTarget,
)
from services.system_settings_service import SystemSettingsService

router = APIRouter()


@router.get(
    "/settings/general/{target}",
    response_model=ApiResponse[GeneralSettingsConfig],
)
async def get_general_settings(
    target: GeneralSettingsTarget,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _: None = Depends(get_current_admin),  # noqa: B008
):
    """获取基础配置"""
    service = SystemSettingsService(db)
    config = await service.get_general_settings(target)
    return ApiResponse(data=config)


@router.put(
    "/settings/general/{target}",
    response_model=ApiResponse[GeneralSettingsConfig],
)
async def update_general_settings(
    target: GeneralSettingsTarget,
    data: GeneralSettingsConfigUpdate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _: None = Depends(get_current_admin),  # noqa: B008
):
    """更新基础配置"""
    service = SystemSettingsService(db)
    config = await service.update_general_settings(data, target)
    return ApiResponse(data=config)
