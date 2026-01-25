from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_account_with_tenant
from exceptions.common import AccountNotLinkedError, WorkspaceArchivedError
from models.account import Account, Tenant, TenantStatus
from models.engine import get_db
from schemas.account import SwitchWorkspacePayload, WorkspaceInfoPayload
from schemas.response import ApiResponse
from services.account_service import TenantService
from services.workspace_service import WorkspaceService

router = APIRouter()


@router.get("/workspaces")
async def get_workspaces(
    current_account_with_tenant: tuple[Account, str | None] = Depends(
        get_current_account_with_tenant
    ),
    db: AsyncSession = Depends(get_db),
):
    from models.billing import SubscriptionPlan

    current_user, current_tenant_id = current_account_with_tenant
    tenants = await TenantService(db).get_join_tenants(current_user)
    tenant_dicts = []

    for tenant in tenants:
        plan_id = tenant.plan or "basic"
        plan_name = plan_id  # 默认使用 plan_id

        # 从数据库获取计划名称
        plan = await db.get(SubscriptionPlan, plan_id)
        if plan:
            plan_name = plan.name

        tenant_dict = {
            "id": tenant.id,
            "name": tenant.name,
            "status": tenant.status,
            "created_at": tenant.created_at,
            "plan": plan_name,  # 直接返回计划名称
            "current": tenant.id == current_tenant_id if current_tenant_id else False,
        }

        tenant_dicts.append(tenant_dict)

    return ApiResponse(data={"workspaces": tenant_dicts})


@router.post("/workspaces/current", response_model=ApiResponse)
async def current_workspace(
    current_account_with_tenant: tuple[Account, str | None] = Depends(
        get_current_account_with_tenant
    ),
    db=Depends(get_db),
):
    current_user, _ = current_account_with_tenant
    tenant = current_user.current_tenant
    if not tenant:
        raise ValueError("No current tenant")
    tenant_service = TenantService(db)
    if tenant.status == TenantStatus.ARCHIVE:
        tenants = await tenant_service.get_join_tenants(current_user)
        if len(tenants) > 0:
            await tenant_service.switch_tenant(current_user, tenants[0].id)
            tenant = tenants[0]
        else:
            raise WorkspaceArchivedError()

    return ApiResponse(data=await WorkspaceService(db).get_tenant_info(current_user, tenant))


@router.post("/workspaces/info")
async def handle_info_edit(
    args: WorkspaceInfoPayload,
    current_account_with_tenant: tuple[Account, str | None] = Depends(
        get_current_account_with_tenant
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_account_with_tenant
    tenant = current_user.current_tenant
    if not tenant:
        raise ValueError("No current tenant")

    tenant.name = args.name
    await db.commit()

    return ApiResponse(
        data={
            "tenant": await WorkspaceService(db).get_tenant_info(current_user, tenant),
        }
    )


@router.post("/workspaces/switch")
async def handle_workspace_switch(
    args: SwitchWorkspacePayload,
    db: AsyncSession = Depends(get_db),
    current_account_with_tenant: tuple[Account, str | None] = Depends(
        get_current_account_with_tenant
    ),
):
    current_user, _ = current_account_with_tenant
    try:
        await TenantService(db).switch_tenant(current_user, args.tenant_id)
    except Exception:
        raise AccountNotLinkedError()

    new_tenant = await db.get(Tenant, args.tenant_id)
    if new_tenant is None:
        raise ValueError("Tenant not found")

    new_tenant = await WorkspaceService(db).get_tenant_info(current_user, new_tenant)
    return ApiResponse(
        data={
            "new_tenant": new_tenant,
        }
    )
