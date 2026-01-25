from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from configs import app_config
from constants.languages import get_valid_language
from libs.helper import timezone
from models.engine import get_db
from enums.response_code import ResponseCode
from libs.datetime_utils import naive_utc_now
from models.admin import Admin
from models.common import FastAPISetup
from schemas.auth import SetupInModel
from schemas.response import ApiResponse
from services.account_service import RegisterService, TenantService
from services.setup_service import SetupService
from constants.languages import language_timezone_mapping


router = APIRouter()


@router.get("/setup", response_model=ApiResponse)
async def get_setup(
    db: AsyncSession = Depends(get_db),
):
    setup_status = await SetupService(db).get_setup_status()
    if setup_status:
        return ApiResponse(data={"step": "finished", "setup_at": setup_status.setup_at.isoformat()})
    return ApiResponse(data={"step": "not_started"})


@router.post("/setup", response_model=ApiResponse)
async def post_setup(
    request: Request,
    args: SetupInModel,
    db: AsyncSession = Depends(get_db),
):
    setup_status = await SetupService(db).get_setup_status()
    if setup_status:
        if setup_status and isinstance(setup_status, bool):
            return ApiResponse(data={"step": "finished"})
        raise HTTPException(
            status_code=ResponseCode.FORBIDDEN,
            detail="Setup has been successfully installed. Please refresh the page or return to the dashboard homepage.",
        )

    interface_language = get_valid_language(args.language)
    admin = Admin(
        email=args.email,
        name=args.name,
        password=args.password,
        interface_language=interface_language,
        timezone=language_timezone_mapping.get(interface_language, "UTC"),
    )
    admin.last_login_ip = request.client.host if request.client else ""
    admin.initialized_at = naive_utc_now()
    db.add(admin)
    await db.commit()

    fastapi_setup = FastAPISetup(version=app_config.project.version)
    db.add(fastapi_setup)
    await db.commit()
    return ApiResponse()
