from fastapi import APIRouter
from constants import SYSTEM_UUID
from core.moderation.factory import ModerationFactory
from schemas.response import ApiResponse

router = APIRouter(prefix="/tests")


@router.get("/code_based")
async def handle_code_based_test():
    factory = ModerationFactory(
        name="keywords",
        tenant_id=SYSTEM_UUID,
        config={
            "keywords": "敏感词1\n敏感词2",
            "inputs_config": {"enabled": True, "preset_response": "包含敏感词"},
            "outputs_config": {"enabled": False},
        },
    )
    result = await factory.moderation_for_inputs({"text": "敏感词1", "text2": "敏感词3"})
    return ApiResponse(data=result)
