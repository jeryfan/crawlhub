from urllib import parse

from fastapi import APIRouter, Depends
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from dependencies.auth import get_current_account_with_tenant
from exceptions.common import (
    BadRequestError,
    InvalidRoleError,
    MemberNotFoundError,
)
from models.account import Account, TenantAccountRole
from models.engine import get_db
from schemas.auth import AccountModel, MemberInvitePayload, MemberRoleUpdatePayload
from schemas.response import ApiResponse
from services.account_service import RegisterService, TenantService
from services.feature_service import FeatureService

router = APIRouter()


@router.get("/workspaces/current/members")
async def get_members(
    db: AsyncSession = Depends(get_db),
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    current_user, _ = current_account_with_tenant
    if not current_user.current_tenant:
        raise ValueError("No current tenant")
    members = await TenantService(db).get_tenant_members(current_user.current_tenant)
    members = TypeAdapter(list[AccountModel]).validate_python(members)
    return ApiResponse(data={"accounts": members})


@router.post("/workspaces/current/members/invite-email")
async def invite_email(
    args: MemberInvitePayload,
    db: AsyncSession = Depends(get_db),
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    invitee_emails = args.emails
    invitee_role = args.role
    interface_language = args.language
    if not TenantAccountRole.is_non_owner_role(invitee_role):
        raise InvalidRoleError()
    current_user, _ = current_account_with_tenant
    inviter = current_user
    if not inviter.current_tenant:
        raise ValueError("No current tenant")
    invitation_results = []
    console_web_url = app_config.CONSOLE_WEB_URL

    workspace_members = FeatureService.get_features(
        tenant_id=inviter.current_tenant.id
    ).workspace_members

    if not workspace_members.is_available(len(invitee_emails)):
        raise BadRequestError(f"Maximum workspace members ({workspace_members.limit}) reached.")

    for invitee_email in invitee_emails:
        try:
            if not inviter.current_tenant:
                raise ValueError("No current tenant")
            token = await RegisterService(db).invite_new_member(
                inviter.current_tenant,
                invitee_email,
                interface_language,
                role=invitee_role,
                inviter=inviter,
            )
            encoded_invitee_email = parse.quote(invitee_email)
            invitation_results.append(
                {
                    "status": "success",
                    "email": invitee_email,
                    "url": f"{console_web_url}/activate?email={encoded_invitee_email}&token={token}",
                }
            )
        except Exception as e:
            invitation_results.append(
                {"status": "failed", "email": invitee_email, "message": str(e)}
            )

    return ApiResponse(
        data={
            "invitation_results": invitation_results,
            "tenant_id": (str(inviter.current_tenant.id) if inviter.current_tenant else ""),
        }
    )


@router.put("/workspaces/current/members/{member_id}/update-role")
async def update_role(
    member_id: str,
    args: MemberRoleUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_account_with_tenant=Depends(get_current_account_with_tenant),
):
    new_role = args.role

    if not TenantAccountRole.is_valid_role(new_role):
        raise InvalidRoleError()
    current_user, _ = current_account_with_tenant
    if not current_user.current_tenant:
        raise ValueError("No current tenant")
    member = await db.get(Account, str(member_id))
    if not member:
        raise MemberNotFoundError()

    try:
        assert member is not None, "Member not found"
        await TenantService(db).update_member_role(
            current_user.current_tenant, member, new_role, current_user
        )
    except Exception as e:
        raise ValueError(str(e))

    # todo: 403

    return ApiResponse()
