import os

from fastapi import APIRouter

from schemas.response import ApiResponse

router = APIRouter()


@router.get("/health")
async def health():
    return ApiResponse(
        data={
            "pid": os.getpid(),
            "status": "ok",
        }
    )
