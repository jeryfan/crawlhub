from sqlalchemy import select
from configs import app_config
from models.account import Tenant, TenantAccountJoin, TenantAccountRole
from services.account_service import TenantService
from services.base_service import BaseService


class WorkspaceService(BaseService):
    async def get_tenant_info(self, current_user, tenant: Tenant):
        if not tenant:
            return None
        tenant_info: dict[str, object] = {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan,
            "status": tenant.status,
            "created_at": tenant.created_at,
            "trial_end_reason": None,
            "role": "normal",
        }

        # Get role of user
        tenant_account_join = await self.db.scalar(
            select(TenantAccountJoin)
            .where(
                TenantAccountJoin.tenant_id == tenant.id,
                TenantAccountJoin.account_id == current_user.id,
            )
            .limit(1)
        )
        assert tenant_account_join is not None, "TenantAccountJoin not found"
        tenant_info["role"] = tenant_account_join.role

        # 允许管理员自定义 logo
        if await TenantService(self.db).has_roles(
            tenant, [TenantAccountRole.OWNER, TenantAccountRole.ADMIN]
        ):
            base_url = app_config.FILES_URL
            replace_webapp_logo = (
                f"{base_url}/files/workspaces/{tenant.id}/webapp-logo"
                if tenant.custom_config_dict.get("replace_webapp_logo")
                else None
            )
            remove_webapp_brand = tenant.custom_config_dict.get("remove_webapp_brand", False)

            tenant_info["custom_config"] = {
                "remove_webapp_brand": remove_webapp_brand,
                "replace_webapp_logo": replace_webapp_logo,
            }

        return tenant_info
