from datetime import datetime, timedelta, UTC
import secrets
from typing import Literal
import app
from configs import app_config
from constants import (
    COOKIE_NAME_ACCESS_TOKEN,
    COOKIE_NAME_CSRF_TOKEN,
    COOKIE_NAME_REFRESH_TOKEN,
    COOKIE_NAME_ADMIN_ACCESS_TOKEN,
    COOKIE_NAME_ADMIN_CSRF_TOKEN,
    COOKIE_NAME_ADMIN_REFRESH_TOKEN,
)
from enums import PlatformEnum
from exceptions.common import Unauthorized
from libs.passport import PassportService
from fastapi import Request, Response
from constants import HEADER_NAME_CSRF_TOKEN
import re

CSRF_WHITE_LIST = []


# server is behind a reverse proxy, so we need to check the url
def is_secure() -> bool:
    return app_config.CONSOLE_WEB_URL.startswith("https") and app_config.CONSOLE_API_URL.startswith(
        "https"
    )


def extract_csrf_token(request: Request) -> str | None:
    return request.headers.get(HEADER_NAME_CSRF_TOKEN)


def extract_csrf_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME_CSRF_TOKEN)


def extract_admin_csrf_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME_ADMIN_CSRF_TOKEN)


def check_csrf_token(request: Request, user_id: str, platform: PlatformEnum = PlatformEnum.USER):
    def _unauthorized():
        raise Unauthorized("CSRF token is missing or invalid.")

    for pattern in CSRF_WHITE_LIST:
        if pattern.match(request.url.path):
            return

    csrf_token = extract_csrf_token(request)
    if platform == PlatformEnum.USER:
        csrf_token_from_cookie = extract_csrf_token_from_cookie(request)
    else:
        csrf_token_from_cookie = extract_admin_csrf_token_from_cookie(request)

    if csrf_token != csrf_token_from_cookie:
        _unauthorized()

    if not csrf_token:
        _unauthorized()
    verified = {}
    try:
        verified = PassportService().verify(csrf_token)
    except:
        _unauthorized()

    if verified.get("sub") != user_id:
        _unauthorized()

    exp: int | None = verified.get("exp")
    if not exp:
        _unauthorized()
    else:
        time_now = int(datetime.now().timestamp())
        if exp < time_now:
            _unauthorized()


def generate_csrf_token(user_id: str) -> str:
    exp_dt = datetime.now(UTC) + timedelta(minutes=app_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "exp": int(exp_dt.timestamp()),
        "sub": user_id,
    }
    return PassportService().issue(payload)


def _cookie_domain() -> str | None:
    """
    Returns the normalized cookie domain.

    Leading dots are stripped from the configured domain. Historically, a leading dot
    indicated that a cookie should be sent to all subdomains, but modern browsers treat
    'example.com' and '.example.com' identically. This normalization ensures consistent
    behavior and avoids confusion.
    """
    domain = app_config.COOKIE_DOMAIN.strip()
    domain = domain.removeprefix(".")
    return domain or None


def _real_cookie_name(cookie_name: str) -> str:
    if is_secure() and _cookie_domain() is None:
        return "__Host-" + cookie_name
    else:
        return cookie_name


def set_access_token_to_cookie(
    request: Request,
    response: Response,
    token: str,
    samesite: Literal["lax", "strict", "none"] | None = "lax",
):
    # response.set_cookie(
    #     key=_real_cookie_name(COOKIE_NAME_ACCESS_TOKEN),
    # )
    response.set_cookie(
        COOKIE_NAME_ACCESS_TOKEN,
        value=token,
        httponly=True,
        domain=_cookie_domain(),
        secure=is_secure(),
        samesite=samesite,
        max_age=int(app_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        path="/",
    )


def set_refresh_token_to_cookie(request: Request, response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME_REFRESH_TOKEN,
        value=token,
        httponly=True,
        domain=_cookie_domain(),
        secure=is_secure(),
        samesite="lax",
        max_age=int(60 * 60 * 24 * app_config.REFRESH_TOKEN_EXPIRE_DAYS),
        path="/",
    )


def set_csrf_token_to_cookie(request: Request, response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME_CSRF_TOKEN,
        value=token,
        httponly=False,
        domain=_cookie_domain(),
        secure=is_secure(),
        samesite="lax",
        max_age=int(60 * app_config.ACCESS_TOKEN_EXPIRE_MINUTES),
        path="/",
    )


def _clear_cookie(
    response: Response,
    cookie_name: str,
    samesite: Literal["lax", "strict", "none"] | None = "lax",
    http_only: bool = True,
):
    response.set_cookie(
        cookie_name,
        "",
        expires=0,
        path="/",
        domain=_cookie_domain(),
        secure=is_secure(),
        httponly=http_only,
        samesite=samesite,
    )


def clear_access_token_from_cookie(response: Response, samesite: str = "Lax"):
    _clear_cookie(response, COOKIE_NAME_ACCESS_TOKEN, samesite)


def clear_refresh_token_from_cookie(response: Response):
    _clear_cookie(response, COOKIE_NAME_REFRESH_TOKEN)


def clear_csrf_token_from_cookie(response: Response):
    _clear_cookie(response, COOKIE_NAME_CSRF_TOKEN, http_only=False)


def _generate_token(length: int = 64):
    token = secrets.token_hex(length)
    return token


# ==================== Admin Cookie Functions ====================
# 以下函数用于管理端，使用独立的cookie名称，避免与用户端冲突


def set_admin_access_token_to_cookie(
    request: Request,
    response: Response,
    token: str,
    samesite: Literal["lax", "strict", "none"] | None = "lax",
):
    response.set_cookie(
        COOKIE_NAME_ADMIN_ACCESS_TOKEN,
        value=token,
        httponly=True,
        domain=_cookie_domain(),
        secure=is_secure(),
        samesite=samesite,
        max_age=int(app_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        path="/",
    )


def set_admin_refresh_token_to_cookie(request: Request, response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME_ADMIN_REFRESH_TOKEN,
        value=token,
        httponly=True,
        domain=_cookie_domain(),
        secure=is_secure(),
        samesite="lax",
        max_age=int(60 * 60 * 24 * app_config.REFRESH_TOKEN_EXPIRE_DAYS),
        path="/",
    )


def set_admin_csrf_token_to_cookie(request: Request, response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME_ADMIN_CSRF_TOKEN,
        value=token,
        httponly=False,
        domain=_cookie_domain(),
        secure=is_secure(),
        samesite="lax",
        max_age=int(60 * app_config.ACCESS_TOKEN_EXPIRE_MINUTES),
        path="/",
    )


def clear_admin_access_token_from_cookie(response: Response, samesite: str = "Lax"):
    _clear_cookie(response, COOKIE_NAME_ADMIN_ACCESS_TOKEN, samesite)


def clear_admin_refresh_token_from_cookie(response: Response):
    _clear_cookie(response, COOKIE_NAME_ADMIN_REFRESH_TOKEN)


def clear_admin_csrf_token_from_cookie(response: Response):
    _clear_cookie(response, COOKIE_NAME_ADMIN_CSRF_TOKEN, http_only=False)
