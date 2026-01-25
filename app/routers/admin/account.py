from fastapi import APIRouter, Depends
from pydantic import TypeAdapter

from models.engine import get_db
from dependencies.auth import get_current_admin
from schemas.auth import AdminModel
from schemas.response import ApiResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.file import helpers as file_helpers
from schemas.account import (
    AccountAvatarPayload,
    AccountNamePayload,
    AccountPasswordPayload,
    AccountTimezonePayload,
    AccountInterfaceLanguagePayload,
)

from services.admin_service import AdminService

router = APIRouter()


def _build_account_response(account) -> AdminModel:
    """构建账户响应，包含 avatar_url"""
    data = TypeAdapter(AdminModel).validate_python(account)
    if data.avatar:
        data.avatar_url = file_helpers.get_signed_file_url(data.avatar)
    return data


@router.get("/account/profile", response_model=ApiResponse[AdminModel])
async def profile(current_admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    admin = TypeAdapter(AdminModel).validate_python(current_admin)
    data = _build_account_response(admin)
    return ApiResponse(data=admin)


@router.post("/account/avatar")
async def handle_avatar_edit(
    args: AccountAvatarPayload,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updated_account = await AdminService(db).update_account(current_user, avatar=args.avatar)
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)


@router.post("/account/name")
async def handle_name_edit(
    args: AccountNamePayload,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updated_account = await AdminService(db).update_account(current_user, name=args.name)
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)


@router.post("/account/password")
async def handle_password_edit(
    args: AccountPasswordPayload,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await AdminService(db).update_account_password(current_user, args.password, args.new_password)
    return ApiResponse()


@router.post("/account/timezone")
async def handle_timezone_change(
    args: AccountTimezonePayload,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updated_account = await AdminService(db).update_account(current_user, timezone=args.timezone)
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)


@router.post("/account/interface-language")
async def handle_language_change(
    args: AccountInterfaceLanguagePayload,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updated_account = await AdminService(db).update_account(
        current_user, interface_language=args.interface_language
    )
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)
