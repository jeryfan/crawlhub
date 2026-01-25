from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from constants import COOKIE_NAME_ADMIN_REFRESH_TOKEN
from models.engine import get_db
from dependencies.auth import get_current_admin
from enums.response_code import ResponseCode
from libs.token import (
    clear_admin_access_token_from_cookie,
    clear_admin_csrf_token_from_cookie,
    clear_admin_refresh_token_from_cookie,
    set_admin_access_token_to_cookie,
    set_admin_csrf_token_to_cookie,
    set_admin_refresh_token_to_cookie,
)
from schemas.auth import AdminLoginIn
from schemas.response import ApiResponse
from services.admin_service import AdminService


router = APIRouter()


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    login_in: AdminLoginIn,
    db: AsyncSession = Depends(get_db),
):
    account = await AdminService(db).get_user_through_email(login_in.email)
    if not account:
        AdminService.add_login_error_rate_limit(login_in.email)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token_pair = await AdminService(db).login(
        account, ip_address=request.client.host if request.client else ""
    )
    AdminService.reset_login_error_rate_limit(login_in.email)

    set_admin_csrf_token_to_cookie(request, response, token_pair.csrf_token)
    set_admin_access_token_to_cookie(request, response, token_pair.access_token)
    set_admin_refresh_token_to_cookie(request, response, token_pair.refresh_token)
    return ApiResponse()


@router.post("/logout")
def logout(
    response: Response,
    current_admin=Depends(get_current_admin),
):
    clear_admin_access_token_from_cookie(response)
    clear_admin_refresh_token_from_cookie(response)
    clear_admin_csrf_token_from_cookie(response)
    return ApiResponse()


@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    response: Response,
    admin_refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME_ADMIN_REFRESH_TOKEN),
    db: AsyncSession = Depends(get_db),
):
    if not admin_refresh_token:
        raise HTTPException(
            status_code=ResponseCode.UNAUTHORIZED,
            detail="No refresh token provided",
        )

    try:
        new_token_pair = await AdminService(db).refresh_token(admin_refresh_token)

        set_admin_csrf_token_to_cookie(request, response, new_token_pair.csrf_token)
        set_admin_access_token_to_cookie(request, response, new_token_pair.access_token)
        set_admin_refresh_token_to_cookie(request, response, new_token_pair.refresh_token)
        return ApiResponse()
    except Exception as e:
        raise HTTPException(
            status_code=ResponseCode.UNAUTHORIZED,
            detail=str(e),
        )
