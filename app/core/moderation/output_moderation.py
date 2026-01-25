import logging
import threading
import time
from typing import Any

from pydantic import BaseModel, ConfigDict

from configs import app_config
from core.moderation.base import ModerationAction, ModerationOutputsResult
from core.moderation.factory import ModerationFactory

logger = logging.getLogger(__name__)


class ModerationRule(BaseModel):
    type: str
    config: dict[str, Any]


class OutputModeration(BaseModel):
    tenant_id: str

    rule: ModerationRule

    buffer: str = ""
    is_final_chunk: bool = False
    final_output: str | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def should_direct_output(self) -> bool:
        return self.final_output is not None

    def get_final_output(self) -> str:
        return self.final_output or ""

    def append_new_token(self, token: str):
        self.buffer += token

        if not self.thread:
            self.thread = self.start_thread()

    async def moderation_completion(
        self, completion: str, public_event: bool = False
    ) -> tuple[str, bool]:
        self.buffer = completion
        self.is_final_chunk = True

        result = await self.moderation(tenant_id=self.tenant_id, moderation_buffer=completion)

        if not result or not result.flagged:
            return completion, False

        if result.action == ModerationAction.DIRECT_OUTPUT:
            final_output = result.preset_response
        else:
            final_output = result.text

        # if public_event:
        #     self.queue_manager.publish(
        #         QueueMessageReplaceEvent(
        #             text=final_output,
        #             reason=QueueMessageReplaceEvent.MessageReplaceReason.OUTPUT_MODERATION,
        #         ),
        #         PublishFrom.TASK_PIPELINE,
        #     )

        return final_output, True

    def start_thread(self) -> threading.Thread:
        buffer_size = app_config.MODERATION_BUFFER_SIZE
        thread = threading.Thread(
            target=self.worker,
            kwargs={
                "flask_app": current_app._get_current_object(),  # type: ignore
                "buffer_size": (
                    buffer_size if buffer_size > 0 else app_config.MODERATION_BUFFER_SIZE
                ),
            },
        )

        thread.start()

        return thread

    def stop_thread(self):
        if self.thread and self.thread.is_alive():
            self.thread_running = False

    async def worker(self, buffer_size: int):
        current_length = 0
        while self.thread_running:
            moderation_buffer = self.buffer
            buffer_length = len(moderation_buffer)
            if not self.is_final_chunk:
                chunk_length = buffer_length - current_length
                if 0 <= chunk_length < buffer_size:
                    time.sleep(1)
                    continue

            current_length = buffer_length

            result = await self.moderation(
                tenant_id=self.tenant_id,
                moderation_buffer=moderation_buffer,
            )

            if not result or not result.flagged:
                continue

            if result.action == ModerationAction.DIRECT_OUTPUT:
                final_output = result.preset_response
                self.final_output = final_output
            else:
                final_output = result.text + self.buffer[len(moderation_buffer) :]

            # trigger replace event
            # if self.thread_running:
            #     self.queue_manager.publish(
            #         QueueMessageReplaceEvent(
            #             text=final_output,
            #             reason=QueueMessageReplaceEvent.MessageReplaceReason.OUTPUT_MODERATION,
            #         ),
            #         PublishFrom.TASK_PIPELINE,
            #     )

            # if result.action == ModerationAction.DIRECT_OUTPUT:
            #     break

    async def moderation(
        self, tenant_id: str, moderation_buffer: str
    ) -> ModerationOutputsResult | None:
        try:
            moderation_factory = ModerationFactory(
                name=self.rule.type,
                tenant_id=tenant_id,
                config=self.rule.config,
            )

            result: ModerationOutputsResult = await moderation_factory.moderation_for_outputs(
                moderation_buffer
            )
            return result
        except Exception:
            logger.exception("Moderation Output error")

        return None
