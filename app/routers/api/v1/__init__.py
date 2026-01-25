import importlib
from fastapi import APIRouter
from utils.router import include_router


router = APIRouter(prefix="/v1")

module = importlib.import_module(__name__)
include_router(module, router)
