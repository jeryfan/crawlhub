import importlib
from pkgutil import iter_modules

from fastapi import APIRouter

from utils.router import include_router

router = APIRouter(prefix="/platform/api")

module = importlib.import_module(__name__)
include_router(module, router)
