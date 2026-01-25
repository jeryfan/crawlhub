from pydantic import BaseModel, Field
from sqlalchemy import select

from core.extension.api_based_extension_requestor import (
    APIBasedExtensionPoint,
    APIBasedExtensionRequestor,
)
from core.helper.encrypter import decrypt_token
from core.moderation.base import (
    Moderation,
    ModerationAction,
    ModerationInputsResult,
    ModerationOutputsResult,
)
from models.engine import AsyncSessionLocal
from models.api_based_extension import APIBasedExtension


class ModerationInputParams(BaseModel):
    inputs: dict = Field(default_factory=dict)
    query: str = ""


class ModerationOutputParams(BaseModel):
    text: str


class ApiModeration(Moderation):
    name: str = "api"

    @classmethod
    async def validate_config(cls, tenant_id: str, config: dict):
        """
        Validate the incoming form config data.

        :param tenant_id: the id of workspace
        :param config: the form config data
        :return:
        """
        cls._validate_inputs_and_outputs_config(config, False)

        api_based_extension_id = config.get("api_based_extension_id")
        if not api_based_extension_id:
            raise ValueError("api_based_extension_id is required")

        extension = await cls._get_api_based_extension(tenant_id, api_based_extension_id)
        if not extension:
            raise ValueError("API-based Extension not found. Please check it again.")

    async def moderation_for_inputs(self, inputs: dict, query: str = "") -> ModerationInputsResult:
        flagged = False
        preset_response = ""
        if self.config is None:
            raise ValueError("The config is not set.")

        if self.config["inputs_config"]["enabled"]:
            params = ModerationInputParams(inputs=inputs, query=query)

            result = await self._get_config_by_requestor(
                APIBasedExtensionPoint.APP_MODERATION_INPUT, params.model_dump()
            )
            return ModerationInputsResult.model_validate(result)

        return ModerationInputsResult(
            flagged=flagged,
            action=ModerationAction.DIRECT_OUTPUT,
            preset_response=preset_response,
        )

    async def moderation_for_outputs(self, text: str) -> ModerationOutputsResult:
        flagged = False
        preset_response = ""
        if self.config is None:
            raise ValueError("The config is not set.")

        if self.config["outputs_config"]["enabled"]:
            params = ModerationOutputParams(text=text)

            result = await self._get_config_by_requestor(
                APIBasedExtensionPoint.APP_MODERATION_OUTPUT, params.model_dump()
            )
            return ModerationOutputsResult.model_validate(result)

        return ModerationOutputsResult(
            flagged=flagged,
            action=ModerationAction.DIRECT_OUTPUT,
            preset_response=preset_response,
        )

    async def _get_config_by_requestor(self, extension_point: APIBasedExtensionPoint, params: dict):
        if self.config is None:
            raise ValueError("The config is not set.")
        extension = await self._get_api_based_extension(
            self.tenant_id, self.config.get("api_based_extension_id", "")
        )
        if not extension:
            raise ValueError("API-based Extension not found. Please check it again.")
        requestor = APIBasedExtensionRequestor(
            extension.api_endpoint, decrypt_token(self.tenant_id, extension.api_key)
        )

        result = await requestor.request(extension_point, params)
        return result

    @staticmethod
    async def _get_api_based_extension(
        tenant_id: str, api_based_extension_id: str
    ) -> APIBasedExtension | None:
        stmt = select(APIBasedExtension).where(
            APIBasedExtension.tenant_id == tenant_id,
            APIBasedExtension.id == api_based_extension_id,
        )
        async with AsyncSessionLocal() as session:
            extension = await session.scalar(stmt)

        return extension
