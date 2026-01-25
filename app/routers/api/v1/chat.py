import asyncio
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.api_key import get_api_key, get_validated_api_key
from models.engine import get_db
from schemas.response import ApiResponse

router = APIRouter(prefix="/chat", dependencies=[Depends(get_validated_api_key)])


@router.post("/completions")
async def completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    async def stream():
        for i in range(5):
            yield f"data: Chunk {i}\n\n"
            await asyncio.sleep(1)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
