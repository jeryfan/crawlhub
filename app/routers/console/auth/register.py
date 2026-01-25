from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from exceptions.common import (
    AccountNotFoundError,
    EmailAlreadyInUseError,
    EmailCodeError,
    EmailRegisterLimitError,
    EmailSendIpLimitError,
    InvalidEmailError,
    InvalidTokenError,
    PasswordMismatchError,
)
from libs.helper import extract_remote_ip
from models.account import Account
from models.engine import get_db
from schemas.auth import (
    EmailRegisterResetPayload,
    EmailRegisterSendPayload,
    EmailRegisterValidityPayload,
    RegisterIn,
)
from schemas.response import ApiResponse
from services.account_service import AccountService, RegisterService
from constants.languages import languages

router = APIRouter()


@router.post("/register", response_model=ApiResponse)
async def register(
    request: Request,
    register_in: RegisterIn,
    session: AsyncSession = Depends(get_db),
):
    name = register_in.name
    email = register_in.email
    password = register_in.password

    account = await RegisterService(session).register(email, name, password)
    return ApiResponse(data=account)


@router.post("/email-register/send-email")
async def handle_email_register_send_email(
    request: Request,
    args: EmailRegisterSendPayload,
    session: AsyncSession = Depends(get_db),
):
    ip_address = extract_remote_ip(request)
    if AccountService.is_email_send_ip_limit(ip_address):
        raise EmailSendIpLimitError()
    language = "zh-hans"
    if args.language in languages:
        language = args.language

    # if app_config.BILLING_ENABLED and BillingService.is_email_in_freeze(args.email):
    #     raise AccountInFreezeError()

    account = await session.scalar(select(Account).filter_by(email=args.email))
    token = None
    token = AccountService.send_email_register_email(
        email=args.email, account=account, language=language
    )
    return ApiResponse(data={"token": token})


@router.post("/email-register/validity")
async def handle_validity(
    request: Request,
    args: EmailRegisterValidityPayload,
    session: AsyncSession = Depends(get_db),
):
    user_email = args.email

    is_email_register_error_rate_limit = AccountService.is_email_register_error_rate_limit(
        args.email
    )
    if is_email_register_error_rate_limit:
        raise EmailRegisterLimitError()

    token_data = AccountService.get_email_register_data(args.token)
    if token_data is None:
        raise InvalidTokenError()

    if user_email != token_data.get("email"):
        raise InvalidEmailError()

    if args.code != token_data.get("code"):
        AccountService.add_email_register_error_rate_limit(args.email)
        raise EmailCodeError()

    # Verified, revoke the first token
    AccountService.revoke_email_register_token(args.token)

    # Refresh token data by generating a new token
    _, new_token = AccountService.generate_email_register_token(
        user_email, code=args.code, additional_data={"phase": "register"}
    )

    AccountService.reset_email_register_error_rate_limit(args.email)
    return ApiResponse(
        data={"is_valid": True, "email": token_data.get("email"), "token": new_token}
    )


@router.post("/email-register")
async def handle_email_register(
    request: Request,
    args: EmailRegisterResetPayload,
    session: AsyncSession = Depends(get_db),
):
    # Validate passwords match
    if args.new_password != args.password_confirm:
        raise PasswordMismatchError()

    # Validate token and get register data
    register_data = AccountService.get_email_register_data(args.token)
    if not register_data:
        raise InvalidTokenError()
    # Must use token in reset phase
    if register_data.get("phase", "") != "register":
        raise InvalidTokenError()

    # Revoke token to prevent reuse
    AccountService.revoke_email_register_token(args.token)

    email = register_data.get("email", "")

    account = await session.scalar(select(Account).filter_by(email=email))

    if account:
        raise EmailAlreadyInUseError()
    else:
        account = await AccountService(session).create_account_and_tenant(
            email=email,
            name=email,
            password=args.password_confirm,
            interface_language=languages[0],
        )
        if not account:
            raise AccountNotFoundError()
        token_pair = await AccountService(session).login(
            account=account, ip_address=extract_remote_ip(request)
        )
        AccountService.reset_login_error_rate_limit(email)

    return ApiResponse(data={"token_pair": token_pair.model_dump()})
