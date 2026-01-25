from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from libs.datetime_utils import naive_utc_now
from models.account import AccountStatus
from schemas.auth import ActivateCheckQuery, ActivatePayload
from schemas.response import ApiResponse
from services.account_service import AccountService, RegisterService

router = APIRouter(prefix="/activate")


@router.post("")
async def activate(
    request: Request,
    args: ActivatePayload,
    db: AsyncSession = Depends(get_db),
):
    invitation = await RegisterService(db).get_invitation_if_token_valid(
        args.workspace_id, args.email, args.token
    )
    if invitation is None:
        raise HTTPException(
            status_code=403,
            detail="Auth Token is invalid or account already activated, please check again.",
        )

    RegisterService.revoke_token(args.workspace_id, args.email, args.token)

    account = invitation["account"]
    account.name = args.name

    account.interface_language = args.interface_language
    account.timezone = args.timezone
    account.interface_theme = "light"
    account.status = AccountStatus.ACTIVE
    account.initialized_at = naive_utc_now()
    await db.commit()

    token_pair = await AccountService(db).login(
        account, ip_address=request.client.host if request.client else ""
    )

    return ApiResponse(data={"token_pair": token_pair.model_dump()})


@router.get("/check")
async def check(
    args: ActivateCheckQuery = Depends(),
    db: AsyncSession = Depends(get_db),
):
    workspaceId = args.workspace_id
    reg_email = args.email
    token = args.token

    invitation = await RegisterService(db).get_invitation_if_token_valid(
        workspaceId, reg_email, token
    )
    if invitation:
        data = invitation.get("data", {})
        tenant = invitation.get("tenant", None)
        workspace_name = tenant.name if tenant else None
        workspace_id = tenant.id if tenant else None
        invitee_email = data.get("email") if data else None
        return ApiResponse(
            data={
                "is_valid": invitation is not None,
                "data": {
                    "workspace_name": workspace_name,
                    "workspace_id": workspace_id,
                    "email": invitee_email,
                },
            }
        )
    else:
        return ApiResponse(data={"is_valid": False})
