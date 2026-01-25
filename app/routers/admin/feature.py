from fastapi import APIRouter, Depends

from dependencies.auth import get_current_account_with_tenant, get_current_admin
from schemas.response import ApiResponse
from services.feature_service import FeatureService


router = APIRouter()


@router.get("/features", response_model=ApiResponse)
def get_features(current_admin=Depends(get_current_admin)):
    """Get feature configuration for current tenant"""

    return ApiResponse(data=FeatureService.get_features(None).model_dump())


@router.get("/system-features", response_model=ApiResponse)
def get_system_features():
    """Get system-wide feature configuration"""
    return ApiResponse(data=FeatureService.get_system_features().model_dump())
