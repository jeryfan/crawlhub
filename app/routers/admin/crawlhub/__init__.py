from fastapi import APIRouter

from .projects import router as projects_router
from .spiders import router as spiders_router
from .proxies import router as proxies_router
from .coder_workspaces import router as coder_workspaces_router

router = APIRouter(prefix="/crawlhub")
router.include_router(projects_router)
router.include_router(spiders_router)
router.include_router(proxies_router)
router.include_router(coder_workspaces_router)
