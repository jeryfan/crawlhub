import logging

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from events.tenant_event import tenant_was_created
from exceptions.common import (
    AccountNotFoundError,
    WeChatLoginDisabledError,
    WorkspaceCreationDisabledError,
)
from libs.datetime_utils import naive_utc_now
from libs.oauth import GitHubOAuth, GoogleOAuth, OAuthUserInfo, WechatOAuth
from libs.token import (
    set_access_token_to_cookie,
    set_csrf_token_to_cookie,
    set_refresh_token_to_cookie,
)
from models.account import Account, AccountStatus
from models.engine import get_db
from services.account_service import AccountService, RegisterService, TenantService
from services.feature_service import FeatureService

logger = logging.getLogger(__name__)


def get_oauth_providers():
    """获取 OAuth 提供商配置（仅从环境变量）"""
    if not app_config.GITHUB_CLIENT_ID or not app_config.GITHUB_CLIENT_SECRET:
        github_oauth = None
    else:
        github_oauth = GitHubOAuth(
            client_id=app_config.GITHUB_CLIENT_ID,
            client_secret=app_config.GITHUB_CLIENT_SECRET,
            redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/github",
        )
    if not app_config.GOOGLE_CLIENT_ID or not app_config.GOOGLE_CLIENT_SECRET:
        google_oauth = None
    else:
        google_oauth = GoogleOAuth(
            client_id=app_config.GOOGLE_CLIENT_ID,
            client_secret=app_config.GOOGLE_CLIENT_SECRET,
            redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/google",
        )

    return {"github": github_oauth, "google": google_oauth}


async def get_oauth_providers_async(db: AsyncSession):
    """获取 OAuth 提供商配置（优先数据库配置）

    优先级：后台配置 > 环境变量
    - 后台有配置且启用 -> 使用后台配置
    - 后台有配置但关闭 -> 返回 None
    - 后台未配置 -> 使用环境变量
    """
    from schemas.settings import GeneralSettingsTarget
    from services.system_settings_service import SystemSettingsService

    settings_service = SystemSettingsService(db)
    general_config = await settings_service.get_general_settings(GeneralSettingsTarget.WEB)

    # GitHub
    db_github = general_config.auth.github
    if db_github.client_id:
        # 后台有配置
        if db_github.enabled and db_github.client_secret:
            github_oauth = GitHubOAuth(
                client_id=db_github.client_id,
                client_secret=db_github.client_secret,
                redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/github",
            )
        else:
            github_oauth = None
    else:
        # 后台未配置，使用环境变量
        if app_config.GITHUB_CLIENT_ID and app_config.GITHUB_CLIENT_SECRET:
            github_oauth = GitHubOAuth(
                client_id=app_config.GITHUB_CLIENT_ID,
                client_secret=app_config.GITHUB_CLIENT_SECRET,
                redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/github",
            )
        else:
            github_oauth = None

    # Google
    db_google = general_config.auth.google
    if db_google.client_id:
        # 后台有配置
        if db_google.enabled and db_google.client_secret:
            google_oauth = GoogleOAuth(
                client_id=db_google.client_id,
                client_secret=db_google.client_secret,
                redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/google",
            )
        else:
            google_oauth = None
    else:
        # 后台未配置，使用环境变量
        if app_config.GOOGLE_CLIENT_ID and app_config.GOOGLE_CLIENT_SECRET:
            google_oauth = GoogleOAuth(
                client_id=app_config.GOOGLE_CLIENT_ID,
                client_secret=app_config.GOOGLE_CLIENT_SECRET,
                redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/google",
            )
        else:
            google_oauth = None

    # WeChat - 优先级：后台配置 > 环境变量
    db_wechat = general_config.auth.wechat
    if db_wechat.app_id:
        # 后台有配置，以后台为准
        if db_wechat.enabled and db_wechat.app_secret:
            wechat_oauth = WechatOAuth(
                app_id=db_wechat.app_id,
                app_secret=db_wechat.app_secret,
                redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/wechat",
            )
        else:
            wechat_oauth = None
    else:
        # 后台未配置，使用环境变量
        if app_config.WECHAT_APP_ID and app_config.WECHAT_APP_SECRET:
            wechat_oauth = WechatOAuth(
                app_id=app_config.WECHAT_APP_ID,
                app_secret=app_config.WECHAT_APP_SECRET,
                redirect_uri=app_config.CONSOLE_API_URL + "/console/api/oauth/authorize/wechat",
            )
        else:
            wechat_oauth = None

    return {"github": github_oauth, "google": google_oauth, "wechat": wechat_oauth}


router = APIRouter()


@router.get("/oauth/login/{provider}")
async def get_provider(
    provider: str,
    invite_token: str = Query(default=None),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    OAUTH_PROVIDERS = await get_oauth_providers_async(db)
    oauth_provider = OAUTH_PROVIDERS.get(provider)
    if not oauth_provider:
        return {"error": "Invalid provider"}, 400

    auth_url = oauth_provider.get_authorization_url(invite_token=invite_token)
    return RedirectResponse(auth_url)


@router.get("/oauth/authorize/{provider}")
async def get(
    request: Request,
    provider: str,
    code: str = Query(default=None),
    state: str = Query(default=None),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    OAUTH_PROVIDERS = await get_oauth_providers_async(db)
    oauth_provider = OAUTH_PROVIDERS.get(provider)
    if not oauth_provider:
        return {"error": "Invalid provider"}, 400

    invite_token = None
    if state and state != "wechat_login":
        invite_token = state

    if not code:
        return {"error": "Authorization code is required"}, 400

    try:
        token = oauth_provider.get_access_token(code)
        user_info = oauth_provider.get_user_info(token)
    except httpx.RequestError as e:
        error_text = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            error_text = e.response.text
        logger.exception(
            "An error occurred during the OAuth process with %s: %s",
            provider,
            error_text,
        )
        return {"error": "OAuth process failed"}, 400

    if invite_token and RegisterService.is_valid_invite_token(invite_token):
        invitation = RegisterService.get_invitation_by_token(token=invite_token)
        if invitation:
            invitation_email = invitation.get("email", None)
            if invitation_email != user_info.email:
                return RedirectResponse(
                    f"{app_config.CONSOLE_WEB_URL}/signin?message=Invalid invitation token."
                )

        return RedirectResponse(
            f"{app_config.CONSOLE_WEB_URL}/signin/invite-settings?invite_token={invite_token}"
        )

    # try:
    account = await _generate_account(db, provider, user_info)
    # except AccountNotFoundError:
    #     return RedirectResponse(
    #         f"{app_config.CONSOLE_WEB_URL}/signin?message=Account not found."
    #     )
    # except (WorkSpaceNotFoundError, WorkSpaceNotAllowedCreateError):
    #     return redirect(
    #         f"{app_config.CONSOLE_WEB_URL}/signin"
    #         "?message=Workspace not found, please contact system admin to invite you to join in a workspace."
    #     )
    # except AccountRegisterError as e:
    #     return redirect(f"{app_config.CONSOLE_WEB_URL}/signin?message={e.description}")

    # Check account status
    if account.status == AccountStatus.BANNED:
        return RedirectResponse(f"{app_config.CONSOLE_WEB_URL}/signin?message=Account is banned.")

    if account.status == AccountStatus.PENDING:
        account.status = AccountStatus.ACTIVE
        account.initialized_at = naive_utc_now()
        await db.commit()

    await TenantService(db).create_owner_tenant_if_not_exist(account)

    token_pair = await AccountService(db).login(
        account=account,
        ip_address=request.client.host if request.client else "",
    )

    response = RedirectResponse(f"{app_config.CONSOLE_WEB_URL}")

    set_access_token_to_cookie(request, response, token_pair.access_token)
    set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
    set_csrf_token_to_cookie(request, response, token_pair.csrf_token)
    return response


async def _get_account_by_openid_or_email(
    db: AsyncSession, provider: str, user_info: OAuthUserInfo
) -> Account | None:
    account: Account | None = await Account.get_by_openid(db, provider, user_info.id)

    if not account:
        account = (
            await db.execute(select(Account).filter_by(email=user_info.email))
        ).scalar_one_or_none()

    return account


async def _generate_account(db: AsyncSession, provider: str, user_info: OAuthUserInfo):
    # Get account by openid or email.
    account = await _get_account_by_openid_or_email(db, provider, user_info)

    if account:
        tenants = await TenantService(db).get_join_tenants(account)
        if not tenants:
            if not FeatureService.get_system_features().is_allow_create_workspace:
                raise WorkspaceCreationDisabledError()
            else:
                new_tenant = await TenantService(db).create_tenant(f"{account.name}'s Workspace")
                await TenantService(db).create_tenant_member(new_tenant, account, role="owner")
                await account.set_current_tenant(db, new_tenant)
                tenant_was_created.send(new_tenant)

    if not account:
        # if not FeatureService.get_system_features().is_allow_register:
        # if app_config.BILLING_ENABLED and BillingService.is_email_in_freeze(
        #     user_info.email
        # ):
        #     raise AccountRegisterError(
        #         description=(
        #             "This email account has been deleted within the past "
        #             "30 days and is temporarily unavailable for new account registration"
        #         )
        #     )
        # else:
        #     raise AccountRegisterError(description=("Invalid email or password"))
        account_name = user_info.name or "Fastapi"
        account = await RegisterService(db).register(
            email=user_info.email,
            name=account_name,
            password=None,
            open_id=user_info.id,
            provider=provider,
        )
        if not account:
            raise AccountNotFoundError()

        # Set interface language
        # preferred_lang = request.accept_languages.best_match(languages)
        # if preferred_lang and preferred_lang in languages:
        #     interface_language = preferred_lang
        # else:
        #     interface_language = languages[0]
        # account.interface_language = interface_language
        await db.commit()

    # Link account
    await AccountService(db).link_account_integrate(provider, user_info.id, account)

    return account


@router.get("/oauth/wechat/qrcode")
async def get_wechat_qrcode_params(
    invite_token: str = Query(default=None),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """获取微信扫码登录二维码参数

    前端可以使用这些参数：
    1. 直接跳转到微信授权页面（redirect_url）
    2. 使用微信 JS SDK 内嵌二维码（qrcode_params）
    """
    from schemas.response import ApiResponse

    OAUTH_PROVIDERS = await get_oauth_providers_async(db)
    wechat_oauth = OAUTH_PROVIDERS.get("wechat")

    if not wechat_oauth:
        raise WeChatLoginDisabledError()

    return ApiResponse(
        data={
            "redirect_url": wechat_oauth.get_authorization_url(invite_token=invite_token),
            "qrcode_params": wechat_oauth.get_qrcode_url(invite_token=invite_token),
        }
    )
