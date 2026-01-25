import base64
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from core.file.helpers import get_signed_file_url
from dependencies.auth import get_current_admin
from libs.password import hash_password, valid_password
from models.account import (
    Account,
    AccountStatus,
    Tenant,
    TenantAccountJoin,
    TenantAccountRole,
)
from schemas.platform import (
    AccountCreate,
    AccountDetail,
    AccountListItem,
    AccountPasswordUpdate,
    AccountStatusUpdate,
    AccountUpdate,
    PaginatedResponse,
)
from schemas.response import ApiResponse
from services.account_service import AccountService, TenantService

router = APIRouter(tags=["Platform - Accounts"])


@router.get("/accounts", response_model=ApiResponse[PaginatedResponse[AccountListItem]])
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取用户列表"""
    query = select(Account)

    # 关键词搜索
    if keyword:
        query = query.where(
            or_(
                Account.name.ilike(f"%{keyword}%"),
                Account.email.ilike(f"%{keyword}%"),
            )
        )

    # 状态筛选
    if status:
        query = query.where(Account.status == status)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(Account.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    accounts = result.scalars().all()

    # 转换为列表项并生成 avatar_url
    items = []
    for acc in accounts:
        item = AccountListItem.model_validate(acc)
        if acc.avatar:
            item.avatar_url = get_signed_file_url(acc.avatar)
        items.append(item)

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/accounts/{account_id}", response_model=ApiResponse[AccountDetail])
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取用户详情"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    detail = AccountDetail.model_validate(account)
    if account.avatar:
        detail.avatar_url = get_signed_file_url(account.avatar)

    return ApiResponse(data=detail)


@router.post("/accounts", response_model=ApiResponse[AccountDetail])
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """创建用户"""
    # 检查邮箱是否已存在
    existing = await Account.get_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 如果指定了工作区，验证工作区是否存在
    tenant = None
    if data.tenant_id:
        tenant = await db.get(Tenant, data.tenant_id)
        if not tenant:
            raise HTTPException(status_code=400, detail="工作区不存在")

        # 如果指定了工作区，则必须指定角色
        if not data.role:
            raise HTTPException(status_code=400, detail="选择工作区时必须指定角色")

        # 验证角色是否有效（不允许指定 owner 角色）
        valid_roles = [
            TenantAccountRole.ADMIN,
            TenantAccountRole.EDITOR,
            TenantAccountRole.NORMAL,
        ]
        if data.role not in [r.value for r in valid_roles]:
            raise HTTPException(status_code=400, detail="无效的角色，可选值: admin, editor, normal")

    account = await AccountService(db).create_account(
        email=data.email,
        name=data.name,
        interface_language="zh-Hans",
        password=data.password,
    )

    if data.status:
        account.status = data.status

    if data.avatar:
        account.avatar = data.avatar

    # 如果指定了工作区，创建用户与工作区的关联
    if tenant and data.role:
        await TenantService(db).create_tenant_member(
            tenant=tenant,
            account=account,
            role=data.role,
        )
    else:
        # 如果未指定工作区，创建默认工作区
        await TenantService(db).create_owner_tenant_if_not_exist(account=account)

    await db.commit()
    await db.refresh(account)

    detail = AccountDetail.model_validate(account)
    if account.avatar:
        detail.avatar_url = get_signed_file_url(account.avatar)

    return ApiResponse(data=detail)


@router.put("/accounts/{account_id}", response_model=ApiResponse[AccountDetail])
async def update_account(
    account_id: str,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """更新用户"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 如果更新邮箱，检查是否已存在
    if data.email and data.email != account.email:
        existing = await Account.get_by_email(db, data.email)
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被使用")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    detail = AccountDetail.model_validate(account)
    if account.avatar:
        detail.avatar_url = get_signed_file_url(account.avatar)

    return ApiResponse(data=detail)


@router.patch("/accounts/{account_id}/status", response_model=ApiResponse[AccountDetail])
async def update_account_status(
    account_id: str,
    data: AccountStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """更新用户状态"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    if data.status not in [s.value for s in AccountStatus]:
        raise HTTPException(status_code=400, detail="无效的状态值")

    account.status = data.status
    await db.commit()
    await db.refresh(account)

    detail = AccountDetail.model_validate(account)
    if account.avatar:
        detail.avatar_url = get_signed_file_url(account.avatar)

    return ApiResponse(data=detail)


@router.patch("/accounts/{account_id}/password", response_model=ApiResponse[dict])
async def update_account_password(
    account_id: str,
    data: AccountPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """更新用户密码"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 验证密码
    valid_password(data.password)

    # 生成新密码
    salt = secrets.token_bytes(16)
    base64_salt = base64.b64encode(salt).decode()
    password_hashed = hash_password(data.password, salt)
    base64_password_hashed = base64.b64encode(password_hashed).decode()

    account.password = base64_password_hashed
    account.password_salt = base64_salt

    await db.commit()

    return ApiResponse()


@router.get(
    "/accounts/{account_id}/owned-tenants",
    response_model=ApiResponse[list[dict]],
)
async def get_account_owned_tenants(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取用户拥有的租户列表（role=owner）"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    query = (
        select(Tenant, TenantAccountJoin)
        .join(TenantAccountJoin, Tenant.id == TenantAccountJoin.tenant_id)
        .where(
            TenantAccountJoin.account_id == account_id,
            TenantAccountJoin.role == TenantAccountRole.OWNER.value,
        )
    )

    result = await db.execute(query)
    rows = result.all()

    # 获取每个租户的成员数
    tenants = []
    for tenant, join in rows:
        member_count_query = select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id)
        member_count = await db.scalar(member_count_query) or 0

        tenants.append(
            {
                "id": tenant.id,
                "name": tenant.name,
                "member_count": member_count,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            }
        )

    return ApiResponse(data=tenants)


@router.delete("/accounts/{account_id}", response_model=ApiResponse)
async def delete_account(
    account_id: str,
    delete_owned_tenants: bool = Query(False, description="是否同时删除用户拥有的租户"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """删除用户

    如果用户是某些租户的所有者（owner），需要先处理这些租户：
    - 设置 delete_owned_tenants=true 可以同时删除这些租户
    - 或者先转让租户所有权，再删除用户
    """
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 查询用户拥有的租户
    owned_tenants_query = (
        select(Tenant, TenantAccountJoin)
        .join(TenantAccountJoin, Tenant.id == TenantAccountJoin.tenant_id)
        .where(
            TenantAccountJoin.account_id == account_id,
            TenantAccountJoin.role == TenantAccountRole.OWNER.value,
        )
    )
    result = await db.execute(owned_tenants_query)
    owned_tenants = result.all()

    if owned_tenants and not delete_owned_tenants:
        # 用户拥有租户但未确认删除，返回错误并附带租户信息
        tenant_list = []
        for tenant, join in owned_tenants:
            member_count_query = select(func.count()).where(
                TenantAccountJoin.tenant_id == tenant.id
            )
            member_count = await db.scalar(member_count_query) or 0
            tenant_list.append(
                {
                    "id": tenant.id,
                    "name": tenant.name,
                    "member_count": member_count,
                }
            )

        raise HTTPException(
            status_code=400,
            detail={
                "code": "HAS_OWNED_TENANTS",
                "message": "用户拥有租户，请先处理这些租户或确认删除",
                "owned_tenants": tenant_list,
            },
        )

    # 如果确认删除用户拥有的租户
    if owned_tenants and delete_owned_tenants:
        for tenant, _ in owned_tenants:
            # 删除租户的所有成员关联
            await db.execute(
                delete(TenantAccountJoin).where(TenantAccountJoin.tenant_id == tenant.id)
            )
            # 删除租户
            await db.delete(tenant)

    # 删除用户的其他租户关联（非 owner 的）
    await db.execute(delete(TenantAccountJoin).where(TenantAccountJoin.account_id == account_id))

    await db.delete(account)
    await db.commit()

    return ApiResponse()


@router.get(
    "/accounts/{account_id}/tenants",
    response_model=ApiResponse[list[dict]],
)
async def get_account_tenants(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取用户关联的租户"""
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    query = (
        select(Tenant, TenantAccountJoin)
        .join(TenantAccountJoin, Tenant.id == TenantAccountJoin.tenant_id)
        .where(TenantAccountJoin.account_id == account_id)
    )

    result = await db.execute(query)
    rows = result.all()

    tenants = []
    for tenant, join in rows:
        tenants.append(
            {
                "id": tenant.id,
                "name": tenant.name,
                "role": join.role,
                "current": join.current,
                "joined_at": join.created_at.isoformat() if join.created_at else None,
                "member_id": join.id,  # 用于更新和删除操作
            }
        )

    return ApiResponse(data=tenants)
