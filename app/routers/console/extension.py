from fastapi import APIRouter, Depends, Query
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from constants import HIDDEN_VALUE
from dependencies.auth import get_current_account_with_tenant
from models import Account
from models.api_based_extension import APIBasedExtension
from models.engine import get_db
from schemas.extension import (
    APIBasedExtensionPayload,
    APIBasedExtensionResponse,
    CodeBasedExtensionQuery,
    CodeBasedExtensionResponse,
)
from schemas.response import ApiResponse, MessageResponse
from services.api_based_extension_service import APIBasedExtensionService
from services.code_based_extension_service import CodeBasedExtensionService

router = APIRouter(prefix="")


@router.get("/code-based-extension")
async def handle_get_code_based_extension(args: CodeBasedExtensionQuery):
    return ApiResponse(
        data={
            "module": args.module,
            "data": CodeBasedExtensionService.get_code_based_extension(args.module),
        }
    )


@router.get("/api-based-extension")
async def handle_get_all_api_based_extension(
    current_account_with_tenant=Depends(get_current_account_with_tenant),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[APIBasedExtensionResponse]]:
    _, tenant_id = current_account_with_tenant
    result = await APIBasedExtensionService(session).get_all_by_tenant_id(tenant_id)
    result = TypeAdapter(list[APIBasedExtensionResponse]).validate_python(result)
    return ApiResponse(data=result)


@router.post("/api-based-extension")
async def handle_add_api_based_extension(
    payload: APIBasedExtensionPayload,
    current_account_with_tenant: tuple[Account, str] = Depends(get_current_account_with_tenant),
    session: AsyncSession = Depends(get_db),
):
    _, current_tenant_id = current_account_with_tenant
    extension_data = APIBasedExtension(
        tenant_id=current_tenant_id,
        name=payload.name,
        api_endpoint=payload.api_endpoint,
        api_key=payload.api_key,
    )

    result = await APIBasedExtensionService(session).save(extension_data)
    return ApiResponse(data=result)


@router.get("/api-based-extension/{extension_id}")
async def handle_get_api_based_extension(
    extension_id: str,
    current_account_with_tenant: tuple[Account, str] = Depends(get_current_account_with_tenant),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[APIBasedExtensionResponse]:
    api_based_extension_id = str(extension_id)
    _, tenant_id = current_account_with_tenant

    result = await APIBasedExtensionService(session).get_with_tenant_id(
        tenant_id, api_based_extension_id
    )
    result = TypeAdapter(APIBasedExtensionResponse).validate_python(result)
    return ApiResponse(data=result)


@router.post("/api-based-extension/{extension_id}")
async def handle_update_api_based_extension(
    extension_id: str,
    payload: APIBasedExtensionPayload,
    current_account_with_tenant: tuple[Account, str] = Depends(get_current_account_with_tenant),
    session: AsyncSession = Depends(get_db),
):
    api_based_extension_id = str(extension_id)
    _, current_tenant_id = current_account_with_tenant

    extension_data_from_db = await APIBasedExtensionService(session).get_with_tenant_id(
        current_tenant_id, api_based_extension_id
    )

    extension_data_from_db.name = payload.name
    extension_data_from_db.api_endpoint = payload.api_endpoint

    if payload.api_key != HIDDEN_VALUE:
        extension_data_from_db.api_key = payload.api_key

    result = await APIBasedExtensionService(session).save(extension_data_from_db)
    return ApiResponse(data=result)


@router.delete("/api-based-extension/{extension_id}")
async def handle_delete_api_based_extension(
    extension_id: str,
    current_account_with_tenant: tuple[Account, str] = Depends(get_current_account_with_tenant),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[MessageResponse]:
    _, current_tenant_id = current_account_with_tenant

    extension_data_from_db = await APIBasedExtensionService(session).get_with_tenant_id(
        current_tenant_id, extension_id
    )

    await APIBasedExtensionService(session).delete(extension_data_from_db)

    return ApiResponse()
