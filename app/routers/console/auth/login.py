from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from constants.languages import get_valid_language
from dependencies.auth import get_current_account_with_tenant
from events.tenant_event import tenant_was_created
from exceptions.common import (
    AccountNotFoundError,
    BadRequestError,
    EmailCodeError,
    EmailSendIpLimitError,
    InvalidTokenError,
    LoginRateLimitError,
    UnauthorizedError,
    WorkspaceLimitExceededError,
)
from libs.helper import extract_remote_ip
from libs.token import (
    clear_access_token_from_cookie,
    clear_csrf_token_from_cookie,
    clear_refresh_token_from_cookie,
    set_access_token_to_cookie,
    set_csrf_token_to_cookie,
    set_refresh_token_to_cookie,
)
from models.engine import get_db
from schemas.auth import EmailCodeLoginPayload, EmailPayload, LoginIn
from schemas.response import ApiResponse
from services.account_service import AccountService, RegisterService, TenantService
from services.feature_service import FeatureService

router = APIRouter()


@router.post("/login", response_model=ApiResponse)
async def login(
    request: Request,
    response: Response,
    login_in: LoginIn,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and login."""

    # if app_config.BILLING_ENABLED and BillingService.is_email_in_freeze(args.email):
    #     raise AccountInFreezeError()

    is_login_error_rate_limit = AccountService.is_login_error_rate_limit(login_in.email)
    if is_login_error_rate_limit:
        raise LoginRateLimitError()

    # TODO: why invitation is re-assigned with different type?
    invitation = login_in.invite_token  # type: ignore
    if invitation:
        invitation = await RegisterService(db).get_invitation_if_token_valid(
            None, login_in.email, invitation
        )  # type: ignore

    try:
        if invitation:
            data = invitation.get("data", {})  # type: ignore
            invitee_email = data.get("email") if data else None
            if invitee_email != login_in.email:
                raise BadRequestError("Invitation email does not match.")
            account = await AccountService(db).authenticate(
                login_in.email, login_in.password, login_in.invite_token
            )
        else:
            account = await AccountService(db).authenticate(login_in.email, login_in.password)
    except Exception as e:
        raise BadRequestError(str(e))
    # SELF_HOSTED only have one workspace
    tenants = await TenantService(db).get_join_tenants(account)
    if len(tenants) == 0:
        system_features = FeatureService.get_system_features()

        if (
            system_features.is_allow_create_workspace
            and not system_features.license.workspaces.is_available()
        ):
            raise WorkspaceLimitExceededError()
        else:
            raise BadRequestError("Workspace not found, please contact admin to invite you.")

    token_pair = await AccountService(db).login(
        account=account, ip_address=extract_remote_ip(request)
    )
    AccountService.reset_login_error_rate_limit(login_in.email)

    set_access_token_to_cookie(request, response, token_pair.access_token)
    set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
    set_csrf_token_to_cookie(request, response, token_pair.csrf_token)

    return ApiResponse()


@router.post("/logout")
def logout(
    response: Response,
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    clear_access_token_from_cookie(response)
    clear_refresh_token_from_cookie(response)
    clear_csrf_token_from_cookie(response)
    return ApiResponse()


@router.post("/reset-password")
async def reset_password(args: EmailPayload, db: AsyncSession = Depends(get_db)):
    if args.language is not None and args.language == "zh-Hans":
        language = "zh-Hans"
    else:
        language = "en-US"
    account = await AccountService(db).get_user_through_email(args.email)

    token = AccountService.send_reset_password_email(
        email=args.email,
        account=account,
        language=language,
        is_allow_register=FeatureService.get_system_features().is_allow_register,
    )

    return ApiResponse(data={"token": token})


@router.post("/email-code-login")
async def email_code_login(
    args: EmailPayload, request: Request, db: AsyncSession = Depends(get_db)
):
    ip_address = extract_remote_ip(request)
    if AccountService.is_email_send_ip_limit(ip_address):
        raise EmailSendIpLimitError()

    if args.language is not None and args.language == "zh-Hans":
        language = "zh-Hans"
    else:
        language = "en-US"
    account = await AccountService(db).get_user_through_email(args.email)

    if account is None:
        if FeatureService.get_system_features().is_allow_register:
            token = AccountService.send_email_code_login_email(email=args.email, language=language)
        else:
            raise AccountNotFoundError()
    else:
        token = AccountService.send_email_code_login_email(account=account, language=language)

    return ApiResponse(data={"token": token})


@router.post("/email-code-login/validity")
async def post(
    request: Request,
    response: Response,
    args: EmailCodeLoginPayload,
    db: AsyncSession = Depends(get_db),
):
    user_email = args.email
    language = args.language

    token_data = AccountService.get_email_code_login_data(args.token)
    if token_data is None:
        raise InvalidTokenError()

    if token_data["email"] != args.email:
        raise BadRequestError("Invalid email.")

    if token_data["code"] != args.code:
        raise EmailCodeError()

    AccountService.revoke_email_code_login_token(args.token)
    account = await AccountService(db).get_user_through_email(user_email)
    if account:
        tenants = await TenantService(db).get_join_tenants(account)
        if not tenants:
            workspaces = FeatureService.get_system_features().license.workspaces
            if not workspaces.is_available():
                raise WorkspaceLimitExceededError()
            if not FeatureService.get_system_features().is_allow_create_workspace:
                raise BadRequestError("Workspace not found, please contact admin to invite you.")
            else:
                new_tenant = await TenantService(db).create_tenant(f"{account.name}'s Workspace")
                await TenantService(db).create_tenant_member(new_tenant, account, role="owner")
                await account.set_current_tenant(db, new_tenant)
                tenant_was_created.send(new_tenant)

    if account is None:
        account = await AccountService(db).create_account_and_tenant(
            email=user_email,
            name=user_email,
            interface_language=get_valid_language(language),
        )
    token_pair = await AccountService(db).login(
        account, ip_address=request.client.host if request.client else ""
    )
    AccountService.reset_login_error_rate_limit(args.email)

    set_csrf_token_to_cookie(request, response, token_pair.csrf_token)
    set_access_token_to_cookie(request, response, token_pair.access_token)
    set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
    return ApiResponse()


@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise UnauthorizedError("No refresh token provided.")

    try:
        new_token_pair = await AccountService(db).refresh_token(refresh_token)

        set_csrf_token_to_cookie(request, response, new_token_pair.csrf_token)
        set_access_token_to_cookie(request, response, new_token_pair.access_token)
        set_refresh_token_to_cookie(request, response, new_token_pair.refresh_token)
        return ApiResponse()
    except Exception as e:
        raise UnauthorizedError(str(e))
