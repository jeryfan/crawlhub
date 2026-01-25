from typing import Annotated, ParamSpec, TypeVar

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_account_with_tenant
from exceptions.common import (
    BadRequestError,
    InvalidRedirectUriError,
    OAuthProviderNotFoundError,
    UnauthorizedError,
)
from models import Account
from models.common import OAuthProviderApp
from models.engine import get_db
from schemas.account import OAuthClientPayload, OAuthProviderRequest, OAuthTokenRequest
from services.oauth_server import (
    OAUTH_ACCESS_TOKEN_EXPIRES_IN,
    OAuthGrantType,
    OAuthServerService,
)
from utils.encoders import jsonable_encoder

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


async def get_oauth_provider_app(
    payload: OAuthClientPayload,
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderApp:
    oauth_provider_app = await OAuthServerService(db).get_oauth_provider_app(payload.client_id)
    if not oauth_provider_app:
        raise OAuthProviderNotFoundError()
    return oauth_provider_app


async def get_current_account(
    authorization: Annotated[str | None, Header()] = None,
    oauth_provider_app: OAuthProviderApp = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Account:
    if not authorization:
        raise UnauthorizedError("Authorization header is required.")

    parts = authorization.strip().split(None, 1)
    if len(parts) != 2:
        raise UnauthorizedError("Invalid Authorization header format.")

    token_type = parts[0].strip()
    if token_type.lower() != "bearer":
        raise UnauthorizedError("Invalid token_type.")

    access_token = parts[1].strip()
    if not access_token:
        raise UnauthorizedError("access_token is required.")

    account = await OAuthServerService(db).validate_oauth_access_token(
        oauth_provider_app.client_id, access_token
    )
    if not account:
        raise UnauthorizedError("Invalid access_token or client_id.")
    return account
    return account


router = APIRouter()


@router.post("/oauth/provider")
async def oauth_provider(
    request: Request,
    payload: OAuthProviderRequest,
    oauth_provider_app: OAuthProviderApp = Depends(get_oauth_provider_app),
):
    redirect_uri = payload.redirect_uri

    # check if redirect_uri is valid
    if redirect_uri not in oauth_provider_app.redirect_uris:
        raise InvalidRedirectUriError()

    return jsonable_encoder(
        {
            "app_icon": oauth_provider_app.app_icon,
            "app_label": oauth_provider_app.app_label,
            "scope": oauth_provider_app.scope,
        }
    )


@router.post("/oauth/provider/authorize")
async def authorize(
    oauth_provider_app: OAuthProviderApp = Depends(get_oauth_provider_app),
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    current_user, _ = current_account_with_tenant
    account = current_user
    user_account_id = account.id

    code = OAuthServerService.sign_oauth_authorization_code(
        oauth_provider_app.client_id, user_account_id
    )
    return jsonable_encoder(
        {
            "code": code,
        }
    )


@router.post("/oauth/provider/token")
async def provider_token(
    payload: OAuthTokenRequest,
    oauth_provider_app: OAuthProviderApp = Depends(get_oauth_provider_app),
):
    try:
        grant_type = OAuthGrantType(payload.grant_type)
    except ValueError:
        raise BadRequestError("Invalid grant_type.")

    if grant_type == OAuthGrantType.AUTHORIZATION_CODE:
        if not payload.code:
            raise BadRequestError("code is required.")

        if payload.client_secret != oauth_provider_app.client_secret:
            raise BadRequestError("Invalid client_secret.")

        if payload.redirect_uri not in oauth_provider_app.redirect_uris:
            raise InvalidRedirectUriError()

        access_token, refresh_token = OAuthServerService.sign_oauth_access_token(
            grant_type, code=payload.code, client_id=oauth_provider_app.client_id
        )
        return jsonable_encoder(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": OAUTH_ACCESS_TOKEN_EXPIRES_IN,
                "refresh_token": refresh_token,
            }
        )
    elif grant_type == OAuthGrantType.REFRESH_TOKEN:
        if not payload.refresh_token:
            raise BadRequestError("refresh_token is required.")

        access_token, refresh_token = OAuthServerService.sign_oauth_access_token(
            grant_type,
            refresh_token=payload.refresh_token,
            client_id=oauth_provider_app.client_id,
        )
        return jsonable_encoder(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": OAUTH_ACCESS_TOKEN_EXPIRES_IN,
                "refresh_token": refresh_token,
            }
        )


@router.post("/oauth/provider/account")
async def provider_account(account: Account = Depends(get_current_account)):
    return jsonable_encoder(
        {
            "name": account.name,
            "email": account.email,
            "avatar": account.avatar,
            "interface_language": account.interface_language,
            "timezone": account.timezone,
        }
    )
