import logging
from collections.abc import Mapping
from typing import Any
from core.moderation.base import ModerationAction, ModerationError
from core.moderation.factory import ModerationFactory


logger = logging.getLogger(__name__)


class InputModeration:
    async def check(
        self,
        tenant_id: str,
        inputs: Mapping[str, Any],
        query: str,
        moderation_type: str,
        config: dict,
    ) -> tuple[bool, Mapping[str, Any], str]:
        """
        Process sensitive_word_avoidance.
        :param tenant_id: tenant id
        :param app_config: app config
        :param inputs: inputs
        :param query: query
        :param trace_manager: trace manager
        :return:
        """
        inputs = dict(inputs)

        moderation_factory = ModerationFactory(
            name=moderation_type,
            tenant_id=tenant_id,
            config=config,
        )

        moderation_result = await moderation_factory.moderation_for_inputs(inputs, query)

        if not moderation_result.flagged:
            return False, inputs, query

        if moderation_result.action == ModerationAction.DIRECT_OUTPUT:
            raise ModerationError(moderation_result.preset_response)
        elif moderation_result.action == ModerationAction.OVERRIDDEN:
            inputs = moderation_result.inputs
            query = moderation_result.query

        return True, inputs, query
