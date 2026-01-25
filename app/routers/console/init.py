from fastapi import APIRouter, Depends, HTTPException

from models.engine import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from enums.response_code import ResponseCode
from schemas.response import ApiResponse
from schemas.account import InitValidatePayload
from services.account_service import TenantService

router = APIRouter(prefix="/init")


@router.get("", response_model=ApiResponse)
async def get_init():
    return ApiResponse(data={"status": "finished"})


@router.post("", response_model=ApiResponse, status_code=201)
async def post_init(
    payload: InitValidatePayload,
    db: AsyncSession = Depends(get_db),
):
    tenant_count = await TenantService(db).get_tenant_count()
    if tenant_count > 0:
        raise HTTPException(
            status_code=ResponseCode.FORBIDDEN,
            detail="Setup has been successfully installed.",
        )

    return ApiResponse()
