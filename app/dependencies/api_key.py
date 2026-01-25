import ipaddress
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from enums.response_code import ResponseCode
from exceptions.common import IpNotInWhitelistError
from libs.helper import RateLimiter
from libs.security import hash_text
from models.api_key import ApiKey, ApiKeyStatus
from models.engine import get_db

logger = logging.getLogger(__name__)


class ApiKeyAuthError(HTTPException):
    def __init__(self, detail: str, log_message: str | None = None):
        super().__init__(
            status_code=ResponseCode.UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        if log_message:
            logger.warning(f"API Key auth failed: {log_message}")


class RateLimitExceededError(HTTPException):
    def __init__(
        self,
        detail: str = "Rate limit exceeded, please try again later",
        retry_after: int = 60,
    ):
        super().__init__(
            status_code=429,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


async def get_api_key(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    client_ip = request.client.host if request.client else "unknown"

    if not authorization:
        raise ApiKeyAuthError(
            "Missing Authorization header",
            f"Missing authorization header from {client_ip}",
        )

    api_key_str = authorization
    if authorization.lower().startswith("bearer "):
        api_key_str = authorization[7:].strip()

    if not api_key_str:
        raise ApiKeyAuthError("API Key cannot be empty", f"Empty API key from {client_ip}")

    if not api_key_str.startswith("sk-"):
        raise ApiKeyAuthError("Invalid API Key format", f"Invalid key format from {client_ip}")

    key_hash = hash_text(api_key_str)
    key_prefix = api_key_str[:12]

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise ApiKeyAuthError("Invalid API Key", f"Invalid key {key_prefix}... from {client_ip}")

    if api_key.status == ApiKeyStatus.DISABLED:
        raise ApiKeyAuthError(
            "API Key is disabled", f"Disabled key {key_prefix}... from {client_ip}"
        )

    if api_key.status == ApiKeyStatus.REVOKED:
        raise ApiKeyAuthError(
            "API Key has been revoked", f"Revoked key {key_prefix}... from {client_ip}"
        )

    now = datetime.now(UTC)
    if api_key.expires_at:
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if now > expires_at:
            raise ApiKeyAuthError(
                "API Key has expired", f"Expired key {key_prefix}... from {client_ip}"
            )

    request.state.api_key = api_key
    request.state.api_key_id = api_key.id
    request.state.tenant_id = api_key.tenant_id

    try:
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key.id)
            .values(last_used_at=now.replace(tzinfo=None))
        )
    except Exception as e:
        logger.warning(f"Failed to update last_used_at for key {api_key.id}: {e}")

    return api_key


async def check_rate_limits(
    request: Request,
    api_key: ApiKey = Depends(get_api_key),
) -> ApiKey:
    """
    Check RPM and RPH rate limits.
    """
    rpm = api_key.rpm
    rph = api_key.rph

    # 检查每分钟限制
    if rpm:
        rpm_limiter = RateLimiter(prefix="rpm", max_attempts=rpm, time_window=60)
        is_limited, current_count = rpm_limiter.check_and_increment(api_key.id)
        if is_limited:
            logger.info(
                f"RPM limit exceeded for key {api_key.key_prefix}... "
                f"({current_count}/{rpm} per minute)"
            )
            raise RateLimitExceededError(
                f"Rate limit exceeded ({rpm}/min)",
                retry_after=60,
            )

    # 检查每小时限制
    if rph:
        rph_limiter = RateLimiter(prefix="rph", max_attempts=rph, time_window=3600)
        is_limited, current_count = rph_limiter.check_and_increment(api_key.id)
        if is_limited:
            logger.info(
                f"RPH limit exceeded for key {api_key.key_prefix}... "
                f"({current_count}/{rph} per hour)"
            )
            raise RateLimitExceededError(
                f"Rate limit exceeded ({rph}/hour)",
                retry_after=3600,
            )

    return api_key


def is_ip_allowed(client_ip: str, whitelist: list[str]) -> bool:
    if not whitelist:
        return True

    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in whitelist:
        try:
            if "/" in entry:
                network = ipaddress.ip_network(entry, strict=False)
                if client_addr in network:
                    return True
            else:
                if client_addr == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue

    return False


async def check_ip_whitelist(
    request: Request,
    api_key: ApiKey = Depends(check_rate_limits),
) -> ApiKey:
    client_ip = request.client.host if request.client else "unknown"

    if not api_key.whitelist:
        return api_key

    if not is_ip_allowed(client_ip, api_key.whitelist):
        logger.warning(
            f"IP denied for key {api_key.key_prefix}..., "
            f"client_ip: {client_ip}, whitelist: {api_key.whitelist}"
        )
        raise IpNotInWhitelistError()

    return api_key


async def get_validated_api_key(
    api_key: ApiKey = Depends(check_ip_whitelist),
) -> ApiKey:
    return api_key
