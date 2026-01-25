from sqlalchemy import select
from core.extension.api_based_extension_requestor import APIBasedExtensionRequestor
from core.helper.encrypter import decrypt_token, encrypt_token
from models.api_based_extension import APIBasedExtension, APIBasedExtensionPoint
from services.base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession


class APIBasedExtensionService(BaseService):
    async def get_all_by_tenant_id(self, tenant_id: str) -> list[APIBasedExtension]:
        extension_list = (
            await self.db.scalars(
                select(APIBasedExtension)
                .where(APIBasedExtension.tenant_id == tenant_id)
                .order_by(APIBasedExtension.created_at.desc())
            )
        ).all()

        for extension in extension_list:
            extension.api_key = decrypt_token(extension.tenant_id, extension.api_key)

        return list(extension_list)

    async def save(self, extension_data: APIBasedExtension) -> APIBasedExtension:
        await self._validation(extension_data)

        extension_data.api_key = await encrypt_token(
            extension_data.tenant_id, extension_data.api_key
        )

        self.db.add(extension_data)
        await self.db.commit()
        return extension_data

    async def delete(self, extension_data: APIBasedExtension):
        await self.db.delete(extension_data)
        await self.db.commit()

    async def get_with_tenant_id(
        self, tenant_id: str, api_based_extension_id: str
    ) -> APIBasedExtension:
        extension = await self.db.scalar(
            select(APIBasedExtension)
            .where(APIBasedExtension.tenant_id == tenant_id)
            .where(APIBasedExtension.id == api_based_extension_id)
        )

        if not extension:
            raise ValueError("API based extension is not found")

        extension.api_key = decrypt_token(extension.tenant_id, extension.api_key)

        return extension

    async def _validation(self, extension_data: APIBasedExtension):
        # name
        if not extension_data.name:
            raise ValueError("name must not be empty")

        if not extension_data.id:
            # case one: check new data, name must be unique
            is_name_existed = await self.db.scalar(
                select(APIBasedExtension).where(
                    APIBasedExtension.tenant_id == extension_data.tenant_id,
                    APIBasedExtension.name == extension_data.name,
                )
            )

            if is_name_existed:
                raise ValueError("name must be unique, it is already existed")
        else:
            # case two: check existing data, name must be unique
            is_name_existed = await self.db.scalar(
                select(APIBasedExtension).where(
                    APIBasedExtension.tenant_id == extension_data.tenant_id,
                    APIBasedExtension.name == extension_data.name,
                    APIBasedExtension.id != extension_data.id,
                )
            )

            if is_name_existed:
                raise ValueError("name must be unique, it is already existed")

        # api_endpoint
        if not extension_data.api_endpoint:
            raise ValueError("api_endpoint must not be empty")

        # api_key
        if not extension_data.api_key:
            raise ValueError("api_key must not be empty")

        if len(extension_data.api_key) < 5:
            raise ValueError("api_key must be at least 5 characters")

        # check endpoint
        await self._ping_connection(extension_data)

    async def _ping_connection(self, extension_data: APIBasedExtension):
        try:
            client = APIBasedExtensionRequestor(extension_data.api_endpoint, extension_data.api_key)
            resp = client.request(point=APIBasedExtensionPoint.PING, params={})
            if resp.get("result") != "pong":
                raise ValueError(resp)
        except Exception as e:
            raise ValueError(f"connection error: {e}")
