import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field
from core.external_data_tool.factory import ExternalDataToolFactory

logger = logging.getLogger(__name__)


class ExternalDataVariableEntity(BaseModel):
    """
    External Data Variable Entity.
    """

    variable: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class ExternalDataFetch:
    async def fetch(
        self,
        tenant_id: str,
        external_data_tools: list[ExternalDataVariableEntity],
        inputs: Mapping[str, Any],
        query: str,
    ) -> Mapping[str, Any]:
        """
        Fill in variable inputs from external data tools if exists.

        :param tenant_id: workspace id
        :param external_data_tools: external data tools configs
        :param inputs: the inputs
        :param query: the query
        :return: the filled inputs
        """
        results: dict[str, Any] = {}
        inputs = dict(inputs)
        for tool in external_data_tools:
            tool_variable, result = await self._query_external_data_tool(
                tenant_id,
                tool,
                inputs,
                query,
            )

            if tool_variable is not None:
                results[tool_variable] = result

        inputs.update(results)
        return inputs

    async def _query_external_data_tool(
        self,
        tenant_id: str,
        external_data_tool: ExternalDataVariableEntity,
        inputs: Mapping[str, Any],
        query: str,
    ) -> tuple[str | None, str | None]:
        """
        Query external data tool.
        :param tenant_id: tenant id
        :param external_data_tool: external data tool
        :param inputs: inputs
        :param query: query
        :return:
        """
        tool_variable = external_data_tool.variable
        tool_type = external_data_tool.type
        tool_config = external_data_tool.config

        external_data_tool_factory = ExternalDataToolFactory(
            name=tool_type,
            tenant_id=tenant_id,
            variable=tool_variable,
            config=tool_config,
        )

        # query external data tool
        result = await external_data_tool_factory.query(inputs=inputs, query=query)

        return tool_variable, result
