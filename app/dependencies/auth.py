from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import COOKIE_NAME_ACCESS_TOKEN, COOKIE_NAME_ADMIN_ACCESS_TOKEN
from enums import PlatformEnum
from exceptions.common import AccountNotFoundError, UnauthorizedError
from libs.passport import PassportService
from libs.token import check_csrf_token
from models import Account
from models.account import TenantAccountJoin
from models.admin import Admin
from models.engine import get_db

# 创建安全方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Account | None:
    """获取当前登录用户"""
    auth_token = None
    if credentials:
        auth_token = credentials.credentials

    if not auth_token:
        auth_token = request.cookies.get(COOKIE_NAME_ACCESS_TOKEN)

    if not auth_token:
        raise UnauthorizedError()

    try:
        # 验证 token
        decoded = PassportService().verify(auth_token)
    except Exception:
        raise UnauthorizedError("Token invalid or expired.")

    user_id = decoded.get("user_id")
    if not user_id:
        raise UnauthorizedError("Missing user info in token.")

    check_csrf_token(request, user_id)

    # 查询用户
    result = await db.execute(select(Account).where(Account.id == user_id))
    account = result.scalar_one_or_none()

    if not account:
        raise AccountNotFoundError()

    # 查询并设置用户的当前租户
    tenant_join_query = select(TenantAccountJoin).where(
        TenantAccountJoin.account_id == account.id,
        TenantAccountJoin.current == True,
    )
    result = await db.execute(tenant_join_query)
    current_tenant_join = result.scalar_one_or_none()

    if current_tenant_join:
        await account.set_tenant_id(db, current_tenant_join.tenant_id)

    return account


async def get_current_account_with_tenant(
    current_user: Account = Depends(get_current_user),
) -> tuple[Account, str | None]:
    if not current_user.current_tenant_id:
        raise UnauthorizedError("No current tenant.")
    return current_user, current_user.current_tenant_id


async def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    auth_token = None
    if credentials:
        auth_token = credentials.credentials

    if not auth_token:
        auth_token = request.cookies.get(COOKIE_NAME_ADMIN_ACCESS_TOKEN)

    if not auth_token:
        raise UnauthorizedError()

    try:
        # 验证 token
        decoded = PassportService().verify(auth_token)
    except Exception:
        raise UnauthorizedError("Token invalid or expired.")

    admin_id = decoded.get("user_id")
    if not admin_id:
        raise UnauthorizedError("Missing user info in token.")

    check_csrf_token(request, admin_id, PlatformEnum.ADMIN)

    # 查询用户
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()

    if not admin:
        raise AccountNotFoundError()
    return admin
