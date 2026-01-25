from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from dependencies.auth import get_current_admin
from models.account import Account, Tenant
from models.api_key import ApiKey, ApiKeyStatus
from schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyDetail,
    ApiKeyItem,
    ApiKeyListResponse,
    ApiKeyRegenerateResponse,
    ApiKeyUpdate,
)
from schemas.response import ApiResponse
from services.api_key_service import ApiKeyService

router = APIRouter(tags=["Platform - API Keys"])


@router.get("/api-keys", response_model=ApiResponse[ApiKeyListResponse])
async def list_api_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取API Key列表"""
    service = ApiKeyService(db)
    api_keys, total = await service.list_api_keys(
        tenant_id=tenant_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )

    # 获取租户名称
    tenant_ids = list(set(key.tenant_id for key in api_keys))
    tenants = {}
    if tenant_ids:
        result = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        for tenant in result.scalars():
            tenants[tenant.id] = tenant.name

    items = []
    for key in api_keys:
        item = ApiKeyItem(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            tenant_id=key.tenant_id,
            tenant_name=tenants.get(key.tenant_id),
            whitelist=key.whitelist,
            status=key.status,
            rpm=key.rpm,
            rph=key.rph,
            balance=float(key.balance) if key.balance else None,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
            updated_at=key.updated_at,
        )
        items.append(item)

    return ApiResponse(
        data=ApiKeyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/api-keys/{key_id}", response_model=ApiResponse[ApiKeyDetail])
async def get_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """获取API Key详情"""
    service = ApiKeyService(db)
    api_key = await service.get_api_key(key_id)

    if not api_key:
        raise HTTPException(status_code=404, detail="API Key不存在")

    # 获取租户名称
    tenant = await db.get(Tenant, api_key.tenant_id)
    tenant_name = tenant.name if tenant else None

    # 获取创建者名称
    creator = await db.get(Account, api_key.created_by)
    created_by_name = creator.name if creator else None

    detail = ApiKeyDetail(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        tenant_id=api_key.tenant_id,
        tenant_name=tenant_name,
        whitelist=api_key.whitelist,
        status=api_key.status,
        rpm=api_key.rpm,
        rph=api_key.rph,
        balance=float(api_key.balance) if api_key.balance else None,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        created_by=api_key.created_by,
        created_by_name=created_by_name,
    )

    return ApiResponse(data=detail)


@router.post("/api-keys", response_model=ApiResponse[ApiKeyCreateResponse])
async def create_api_key(
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """创建API Key"""
    # 验证租户是否存在（如果提供了tenant_id）
    if data.tenant_id:
        tenant = await db.get(Tenant, data.tenant_id)
        if not tenant:
            raise HTTPException(status_code=400, detail="租户不存在")

    service = ApiKeyService(db)
    api_key, full_key = await service.create_api_key(
        name=data.name,
        tenant_id=data.tenant_id,
        created_by=admin.id,
        whitelist=data.whitelist,
        rpm=data.rpm,
        rph=data.rph,
        balance=data.balance,
        expires_at=data.expires_at,
    )

    await db.commit()
    await db.refresh(api_key)

    return ApiResponse(
        data=ApiKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,
            key_prefix=api_key.key_prefix,
            tenant_id=api_key.tenant_id,
            whitelist=api_key.whitelist,
            status=api_key.status,
            rpm=api_key.rpm,
            rph=api_key.rph,
            balance=float(api_key.balance) if api_key.balance else None,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        )
    )


@router.put("/api-keys/{key_id}", response_model=ApiResponse[ApiKeyDetail])
async def update_api_key(
    key_id: str,
    data: ApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """更新API Key"""
    service = ApiKeyService(db)
    api_key = await service.get_api_key(key_id)

    if not api_key:
        raise HTTPException(status_code=404, detail="API Key不存在")

    # 验证状态值
    if data.status and data.status not in [s.value for s in ApiKeyStatus]:
        raise HTTPException(status_code=400, detail="无效的状态值")

    # 不允许通过此接口将已吊销的key改为其他状态
    if api_key.status == ApiKeyStatus.REVOKED and data.status != ApiKeyStatus.REVOKED:
        raise HTTPException(status_code=400, detail="已吊销的API Key无法更改状态")

    api_key = await service.update_api_key(
        key_id=key_id,
        name=data.name,
        whitelist=data.whitelist,
        rpm=data.rpm,
        rph=data.rph,
        balance=data.balance,
        expires_at=data.expires_at,
        status=data.status,
    )

    await db.commit()
    await db.refresh(api_key)

    # 获取租户和创建者信息
    tenant = await db.get(Tenant, api_key.tenant_id)
    creator = await db.get(Account, api_key.created_by)

    detail = ApiKeyDetail(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        tenant_id=api_key.tenant_id,
        tenant_name=tenant.name if tenant else None,
        whitelist=api_key.whitelist,
        status=api_key.status,
        rpm=api_key.rpm,
        rph=api_key.rph,
        balance=float(api_key.balance) if api_key.balance else None,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        created_by=api_key.created_by,
        created_by_name=creator.name if creator else None,
    )

    return ApiResponse(data=detail)


@router.post(
    "/api-keys/{key_id}/regenerate",
    response_model=ApiResponse[ApiKeyRegenerateResponse],
)
async def regenerate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """重新生成API Key"""
    service = ApiKeyService(db)
    result = await service.regenerate_api_key(key_id)

    if not result:
        raise HTTPException(status_code=404, detail="API Key不存在")

    api_key, full_key = result
    await db.commit()
    await db.refresh(api_key)

    return ApiResponse(
        data=ApiKeyRegenerateResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,
            key_prefix=api_key.key_prefix,
        )
    )


@router.patch("/api-keys/{key_id}/revoke", response_model=ApiResponse[ApiKeyDetail])
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """吊销API Key"""
    service = ApiKeyService(db)
    api_key = await service.revoke_api_key(key_id)

    if not api_key:
        raise HTTPException(status_code=404, detail="API Key不存在")

    await db.commit()
    await db.refresh(api_key)

    # 获取租户和创建者信息
    tenant = await db.get(Tenant, api_key.tenant_id)
    creator = await db.get(Account, api_key.created_by)

    detail = ApiKeyDetail(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        tenant_id=api_key.tenant_id,
        tenant_name=tenant.name if tenant else None,
        whitelist=api_key.whitelist,
        status=api_key.status,
        rpm=api_key.rpm,
        rph=api_key.rph,
        balance=float(api_key.balance) if api_key.balance else None,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        created_by=api_key.created_by,
        created_by_name=creator.name if creator else None,
    )

    return ApiResponse(data=detail)


@router.delete("/api-keys/{key_id}", response_model=ApiResponse)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """删除API Key"""
    service = ApiKeyService(db)
    deleted = await service.delete_api_key(key_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="API Key不存在")

    await db.commit()

    return ApiResponse()
