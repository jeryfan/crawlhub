from sqlalchemy import select

from core.extension.api_based_extension_requestor import APIBasedExtensionRequestor
from core.external_data_tool.base import ExternalDataTool
from core.helper import encrypter
from models.engine import AsyncSessionLocal
from models.api_based_extension import APIBasedExtension, APIBasedExtensionPoint


class ApiExternalDataTool(ExternalDataTool):
    """
    The api external data tool.
    """

    name: str = "api"
    """the unique name of external data tool"""

    @classmethod
    async def validate_config(cls, tenant_id: str, config: dict):
        """
        Validate the incoming form config data.

        :param tenant_id: the id of workspace
        :param config: the form config data
        :return:
        """
        # own validation logic
        api_based_extension_id = config.get("api_based_extension_id")
        if not api_based_extension_id:
            raise ValueError("api_based_extension_id is required")
        # get api_based_extension
        stmt = select(APIBasedExtension).where(
            APIBasedExtension.tenant_id == tenant_id,
            APIBasedExtension.id == api_based_extension_id,
        )
        async with AsyncSessionLocal() as session:
            api_based_extension = await session.scalar(stmt)

        if not api_based_extension:
            raise ValueError("api_based_extension_id is invalid")

    async def query(self, inputs: dict, query: str | None = None) -> str:
        """
        Query the external data tool.

        :param inputs: user inputs
        :param query: the query of chat app
        :return: the tool query result
        """
        # get params from config
        if not self.config:
            raise ValueError(f"config is required, config: {self.config}")
        api_based_extension_id = self.config.get("api_based_extension_id")
        assert api_based_extension_id is not None, "api_based_extension_id is required"
        # get api_based_extension
        stmt = select(APIBasedExtension).where(
            APIBasedExtension.tenant_id == self.tenant_id,
            APIBasedExtension.id == api_based_extension_id,
        )
        async with AsyncSessionLocal() as session:
            api_based_extension = await session.scalar(stmt)

        if not api_based_extension:
            raise ValueError(
                "[External data tool] API query failed, variable: {}, error: api_based_extension_id is invalid".format(
                    self.variable
                )
            )

        # decrypt api_key
        api_key = encrypter.decrypt_token(
            tenant_id=self.tenant_id, token=api_based_extension.api_key
        )

        try:
            # request api
            requestor = APIBasedExtensionRequestor(
                api_endpoint=api_based_extension.api_endpoint, api_key=api_key
            )
        except Exception as e:
            raise ValueError(
                f"[External data tool] API query failed, variable: {self.variable}, error: {e}"
            )

        response_json = await requestor.request(
            point=APIBasedExtensionPoint.APP_EXTERNAL_DATA_TOOL_QUERY,
            params={
                "tool_variable": self.variable,
                "inputs": inputs,
                "query": query,
            },
        )

        if "result" not in response_json:
            raise ValueError(
                "[External data tool] API query failed, variable: {}, error: result not found in response".format(
                    self.variable
                )
            )

        if not isinstance(response_json["result"], str):
            raise ValueError(
                f"[External data tool] API query failed, variable: {self.variable}, error: result is not string"
            )

        return response_json["result"]
