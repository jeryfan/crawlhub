from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter
from sqlalchemy import select

from exceptions.common import AccountAlreadyInitedError, InvalidInvitationCodeError
from libs.datetime_utils import naive_utc_now
from models.account import Account, InvitationCode
from models.engine import get_db
from core.file import helpers as file_helpers
from dependencies.auth import get_current_account_with_tenant
from schemas.auth import AccountModel
from schemas.response import ApiResponse
from schemas.account import (
    AccountAvatarPayload,
    AccountInitPayload,
    AccountNamePayload,
    AccountPasswordPayload,
    AccountDeletePayload,
    AccountDeletionFeedbackPayload,
    AccountTimezonePayload,
    AccountInterfaceLanguagePayload,
)
from services.account_service import AccountService
from sqlalchemy.ext.asyncio import AsyncSession
from configs import app_config

router = APIRouter()


def _build_account_response(account) -> AccountModel:
    """构建账户响应，包含 avatar_url"""
    data = TypeAdapter(AccountModel).validate_python(account)
    if data.avatar:
        data.avatar_url = file_helpers.get_signed_file_url(data.avatar)
    return data


@router.post("/account/init")
async def handle_account_init(
    args: AccountInitPayload,
    current_account_with_tenant: tuple[Account, str] = Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    account, _ = current_account_with_tenant

    if account.status == "active":
        raise AccountAlreadyInitedError()

    if app_config.EDITION == "CLOUD":
        if not args.invitation_code:
            raise ValueError("invitation_code is required")

        # check invitation code
        invitation_code = await db.scalar(
            select(InvitationCode).where(
                InvitationCode.code == args.invitation_code,
                InvitationCode.status == "unused",
            )
        )

        if not invitation_code:
            raise InvalidInvitationCodeError()

        invitation_code.status = "used"
        invitation_code.used_at = naive_utc_now()
        invitation_code.used_by_tenant_id = account.current_tenant_id
        invitation_code.used_by_account_id = account.id

    account.interface_language = args.interface_language
    account.timezone = args.timezone
    account.status = "active"
    account.initialized_at = naive_utc_now()
    await db.commit()

    return ApiResponse()


@router.get("/account/profile", response_model=ApiResponse[AccountModel])
async def profile(current_account_with_tenant=Depends(get_current_account_with_tenant)):
    current_user, _ = current_account_with_tenant
    data = _build_account_response(current_user)
    return ApiResponse(data=data)


@router.post("/account/avatar")
async def handle_avatar_edit(
    args: AccountAvatarPayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant

    updated_account = await AccountService(db).update_account(current_user, avatar=args.avatar)
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)


@router.post("/account/name")
async def handle_name_edit(
    args: AccountNamePayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant

    updated_account = await AccountService(db).update_account(current_user, name=args.name)
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)


@router.post("/account/password")
async def handle_password_edit(
    args: AccountPasswordPayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant
    await AccountService(db).update_account_password(current_user, args.password, args.new_password)
    return ApiResponse()


@router.get("/account/delete/verify")
async def handle_account_delete_verify(
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    current_user, _ = current_account_with_tenant
    token, code = AccountService.generate_account_deletion_verification_code(current_user)
    AccountService.send_account_deletion_verification_email(current_user, code)

    return ApiResponse(data={"token": token})


@router.post("/account/delete")
async def handle_account_delete(
    args: AccountDeletePayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant
    if not AccountService.verify_account_deletion_code(args.token, args.code):
        raise HTTPException(detail="Invalid account deletion code.", status_code=400)

    AccountService.delete_account(current_user)

    return ApiResponse()


@router.post("/account/delete/feedback")
async def handle_account_delete_feedback(
    args: AccountDeletionFeedbackPayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse()


@router.post("/account/timezone")
async def handle_timezone_change(
    args: AccountTimezonePayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant

    updated_account = await AccountService(db).update_account(current_user, timezone=args.timezone)
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)


@router.post("/account/interface-language")
async def handle_language_change(
    args: AccountInterfaceLanguagePayload,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant

    updated_account = await AccountService(db).update_account(
        current_user, interface_language=args.interface_language
    )
    data = _build_account_response(updated_account)

    return ApiResponse(data=data)
