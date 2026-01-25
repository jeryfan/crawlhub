from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import delete, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from core.file.helpers import get_signed_file_url
from dependencies.auth import get_current_admin
from models.account import (
    Account,
    Tenant,
    TenantAccountJoin,
    TenantAccountRole,
    TenantStatus,
)
from schemas.platform import (
    PaginatedResponse,
    TenantCreate,
    TenantDetail,
    TenantListItem,
    TenantMember,
    TenantUpdate,
)
from schemas.response import ApiResponse

router = APIRouter()


@router.get(
    "/tenants/{tenant_id}/search-users",
    response_model=ApiResponse[dict],
)
async def search_users_for_tenant(
    tenant_id: str,
    keyword: str = Query(..., min_length=1, description="搜索关键词（邮箱或用户名）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """搜索可添加到租户的用户

    根据邮箱或用户名搜索用户，排除已是该租户成员的用户
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取已是成员的用户ID
    existing_members_query = select(TenantAccountJoin.account_id).where(
        TenantAccountJoin.tenant_id == tenant_id
    )
    existing_result = await db.execute(existing_members_query)
    existing_member_ids = {row[0] for row in existing_result.all()}

    # 搜索用户（邮箱或用户名模糊匹配）
    base_query = select(Account).where(
        or_(
            Account.email.ilike(f"%{keyword}%"),
            Account.name.ilike(f"%{keyword}%"),
        )
    )

    # 统计总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页查询
    search_query = base_query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(search_query)
    users = result.scalars().all()

    # 构建结果
    items = []
    for user in users:
        is_member = user.id in existing_member_ids
        avatar_url = get_signed_file_url(user.avatar) if user.avatar else None
        items.append(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "avatar_url": avatar_url,
                "is_member": is_member,
            }
        )

    return ApiResponse(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total,
        }
    )


@router.post(
    "/tenants/{tenant_id}/members/batch",
    response_model=ApiResponse[dict],
)
async def batch_add_tenant_members(
    tenant_id: str,
    account_ids: list[str] = Body(..., embed=True, description="用户ID列表"),
    role: str = Body(default="normal", embed=True, description="角色"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """批量添加租户成员"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    if not TenantAccountRole.is_valid_role(role):
        raise HTTPException(status_code=400, detail="无效的角色")

    # 获取已是成员的用户ID
    existing_query = select(TenantAccountJoin.account_id).where(
        TenantAccountJoin.tenant_id == tenant_id,
        TenantAccountJoin.account_id.in_(account_ids),
    )
    existing_result = await db.execute(existing_query)
    existing_ids = {row[0] for row in existing_result.all()}

    # 验证用户是否存在
    accounts_query = select(Account.id).where(Account.id.in_(account_ids))
    accounts_result = await db.execute(accounts_query)
    valid_ids = {row[0] for row in accounts_result.all()}

    added_count = 0
    skipped_count = 0
    invalid_count = 0

    for account_id in account_ids:
        if account_id not in valid_ids:
            invalid_count += 1
            continue
        if account_id in existing_ids:
            skipped_count += 1
            continue

        join = TenantAccountJoin(
            tenant_id=tenant_id,
            account_id=account_id,
            role=role,
        )
        db.add(join)
        added_count += 1

    await db.commit()

    return ApiResponse(
        data={
            "added": added_count,
            "skipped": skipped_count,
            "invalid": invalid_count,
        }
    )


@router.get("/tenants", response_model=ApiResponse[PaginatedResponse[TenantListItem]])
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    plan: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    query = select(Tenant)

    # 关键词搜索
    if keyword:
        query = query.where(Tenant.name.ilike(f"%{keyword}%"))

    # 状态筛选
    if status:
        query = query.where(Tenant.status == status)

    # 计划筛选
    if plan:
        query = query.where(Tenant.plan == plan)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(Tenant.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tenants = result.scalars().all()

    # 获取每个租户的成员数
    items = []
    for tenant in tenants:
        member_count = await db.scalar(
            select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id)
        )
        item = TenantListItem(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan,
            status=tenant.status,
            created_at=tenant.created_at,
            member_count=member_count or 0,
        )
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


@router.get("/tenants/{tenant_id}", response_model=ApiResponse[TenantDetail])
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    member_count = await db.scalar(
        select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id)
    )

    return ApiResponse(
        data=TenantDetail(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan,
            status=tenant.status,
            created_at=tenant.created_at,
            member_count=member_count or 0,
            encrypt_public_key=tenant.encrypt_public_key,
            custom_config=tenant.custom_config_dict,
            updated_at=tenant.updated_at,
        )
    )


@router.post("/tenants", response_model=ApiResponse[TenantDetail])
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    tenant = Tenant(
        name=data.name,
        plan=data.plan,
        status=TenantStatus.NORMAL,
    )

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return ApiResponse(
        data=TenantDetail(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan,
            status=tenant.status,
            created_at=tenant.created_at,
            member_count=0,
            encrypt_public_key=tenant.encrypt_public_key,
            custom_config=tenant.custom_config_dict,
            updated_at=tenant.updated_at,
        )
    )


@router.put("/tenants/{tenant_id}", response_model=ApiResponse[TenantDetail])
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 处理 custom_config
    if "custom_config" in update_data:
        tenant.custom_config_dict = update_data.pop("custom_config")

    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    member_count = await db.scalar(
        select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id)
    )

    return ApiResponse(
        data=TenantDetail(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan,
            status=tenant.status,
            created_at=tenant.created_at,
            member_count=member_count or 0,
            encrypt_public_key=tenant.encrypt_public_key,
            custom_config=tenant.custom_config_dict,
            updated_at=tenant.updated_at,
        )
    )


@router.patch("/tenants/{tenant_id}/status", response_model=ApiResponse[TenantDetail])
async def update_tenant_status(
    tenant_id: str,
    status: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    if status not in [s.value for s in TenantStatus]:
        raise HTTPException(status_code=400, detail="无效的状态值")

    tenant.status = status
    await db.commit()
    await db.refresh(tenant)

    member_count = await db.scalar(
        select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id)
    )

    return ApiResponse(
        data=TenantDetail(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan,
            status=tenant.status,
            created_at=tenant.created_at,
            member_count=member_count or 0,
            encrypt_public_key=tenant.encrypt_public_key,
            custom_config=tenant.custom_config_dict,
            updated_at=tenant.updated_at,
        )
    )


@router.get(
    "/tenants/{tenant_id}/deletion-impact",
    response_model=ApiResponse[dict],
)
async def get_tenant_deletion_impact(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取删除租户的影响范围

    返回：
    - member_count: 成员总数
    - owner: 租户所有者信息
    - orphan_users: 只属于该租户的用户列表（删除后将没有任何工作区）
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取所有成员
    members_query = (
        select(Account, TenantAccountJoin)
        .join(TenantAccountJoin, Account.id == TenantAccountJoin.account_id)
        .where(TenantAccountJoin.tenant_id == tenant_id)
    )
    result = await db.execute(members_query)
    members = result.all()

    member_count = len(members)
    owner = None
    orphan_users = []

    for account, join in members:
        # 找到所有者
        if join.role == TenantAccountRole.OWNER.value:
            owner = {
                "id": account.id,
                "name": account.name,
                "email": account.email,
            }

        # 检查该用户是否只属于这一个租户
        user_tenant_count = await db.scalar(
            select(func.count()).where(TenantAccountJoin.account_id == account.id)
        )
        if user_tenant_count == 1:
            orphan_users.append(
                {
                    "id": account.id,
                    "name": account.name,
                    "email": account.email,
                    "role": join.role,
                }
            )

    return ApiResponse(
        data={
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "member_count": member_count,
            "owner": owner,
            "orphan_users": orphan_users,
            "orphan_user_count": len(orphan_users),
        }
    )


@router.delete("/tenants/{tenant_id}", response_model=ApiResponse)
async def delete_tenant(
    tenant_id: str,
    delete_orphan_users: bool = Query(
        False, description="是否同时删除孤儿用户（只属于该租户的用户）"
    ),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """删除租户

    如果租户中有只属于该租户的用户（孤儿用户），需要选择处理方式：
    - delete_orphan_users=false: 仅移除用户与租户的关联，用户账户保留但将没有任何工作区
    - delete_orphan_users=true: 同时删除这些孤儿用户账户
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取所有成员
    members_query = (
        select(Account, TenantAccountJoin)
        .join(TenantAccountJoin, Account.id == TenantAccountJoin.account_id)
        .where(TenantAccountJoin.tenant_id == tenant_id)
    )
    result = await db.execute(members_query)
    members = result.all()

    # 找出孤儿用户
    orphan_user_ids = []
    for account, _ in members:
        user_tenant_count = await db.scalar(
            select(func.count()).where(TenantAccountJoin.account_id == account.id)
        )
        if user_tenant_count == 1:
            orphan_user_ids.append(account.id)

    # 删除租户成员关联
    await db.execute(delete(TenantAccountJoin).where(TenantAccountJoin.tenant_id == tenant_id))

    # 如果需要删除孤儿用户
    if delete_orphan_users and orphan_user_ids:
        for user_id in orphan_user_ids:
            account = await db.get(Account, user_id)
            if account:
                await db.delete(account)

    # 删除租户
    await db.delete(tenant)
    await db.commit()

    return ApiResponse(
        data={
            "deleted_orphan_users": len(orphan_user_ids) if delete_orphan_users else 0,
        }
    )


@router.get(
    "/tenants/{tenant_id}/members",
    response_model=ApiResponse[list[TenantMember]],
)
async def get_tenant_members(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    query = (
        select(Account, TenantAccountJoin)
        .join(TenantAccountJoin, Account.id == TenantAccountJoin.account_id)
        .where(TenantAccountJoin.tenant_id == tenant_id)
    )

    result = await db.execute(query)
    rows = result.all()

    members = []
    for account, join in rows:
        members.append(
            TenantMember(
                id=join.id,
                account_id=account.id,
                account_name=account.name,
                account_email=account.email,
                role=join.role,
                created_at=join.created_at,
            )
        )

    return ApiResponse(data=members)


@router.post(
    "/tenants/{tenant_id}/members",
    response_model=ApiResponse[TenantMember],
)
async def add_tenant_member(
    tenant_id: str,
    account_id: str = Query(...),
    role: str = Query(default="normal"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否已是成员
    existing = await db.scalar(
        select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id,
            TenantAccountJoin.account_id == account_id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="用户已是该租户成员")

    if not TenantAccountRole.is_valid_role(role):
        raise HTTPException(status_code=400, detail="无效的角色")

    join = TenantAccountJoin(
        tenant_id=tenant_id,
        account_id=account_id,
        role=role,
    )

    db.add(join)
    await db.commit()
    await db.refresh(join)

    return ApiResponse(
        data=TenantMember(
            id=join.id,
            account_id=account.id,
            account_name=account.name,
            account_email=account.email,
            role=join.role,
            created_at=join.created_at,
        )
    )


@router.patch(
    "/tenants/{tenant_id}/members/{member_id}",
    response_model=ApiResponse[TenantMember],
)
async def update_tenant_member_role(
    tenant_id: str,
    member_id: str,
    role: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    join = await db.get(TenantAccountJoin, member_id)
    if not join or join.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="成员不存在")

    if not TenantAccountRole.is_valid_role(role):
        raise HTTPException(status_code=400, detail="无效的角色")

    join.role = role
    await db.commit()
    await db.refresh(join)

    account = await db.get(Account, join.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="成员不存在")
    return ApiResponse(
        data=TenantMember(
            id=join.id,
            account_id=account.id,
            account_name=account.name,
            account_email=account.email,
            role=join.role,
            created_at=join.created_at,
        )
    )


@router.delete(
    "/tenants/{tenant_id}/members/{member_id}",
    response_model=ApiResponse,
)
async def remove_tenant_member(
    tenant_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    join = await db.get(TenantAccountJoin, member_id)
    if not join or join.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="成员不存在")

    await db.delete(join)
    await db.commit()

    return ApiResponse()


@router.post(
    "/tenants/{tenant_id}/transfer-ownership",
    response_model=ApiResponse,
)
async def transfer_tenant_ownership(
    tenant_id: str,
    new_owner_id: str = Query(..., description="新所有者的用户ID"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """转让租户所有权

    将租户的所有权从当前 owner 转让给指定的用户。
    新所有者必须已经是该租户的成员。
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 查找当前所有者
    current_owner_join = await db.scalar(
        select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id,
            TenantAccountJoin.role == TenantAccountRole.OWNER.value,
        )
    )

    # 查找新所有者的成员记录
    new_owner_join = await db.scalar(
        select(TenantAccountJoin).where(
            TenantAccountJoin.tenant_id == tenant_id,
            TenantAccountJoin.account_id == new_owner_id,
        )
    )

    if not new_owner_join:
        # 新所有者不是成员，检查用户是否存在
        new_owner_account = await db.get(Account, new_owner_id)
        if not new_owner_account:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 创建新的成员记录并设置为 owner
        new_owner_join = TenantAccountJoin(
            tenant_id=tenant_id,
            account_id=new_owner_id,
            role=TenantAccountRole.OWNER.value,
        )
        db.add(new_owner_join)
    else:
        # 新所有者已是成员，更新为 owner
        new_owner_join.role = TenantAccountRole.OWNER.value

    # 将原所有者降级为 admin
    if current_owner_join:
        if current_owner_join.account_id != new_owner_id:
            current_owner_join.role = TenantAccountRole.ADMIN.value

    await db.commit()

    return ApiResponse()
