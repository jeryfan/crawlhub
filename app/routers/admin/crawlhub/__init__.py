from fastapi import APIRouter

from .projects import router as projects_router
from .spiders import router as spiders_router
from .proxies import router as proxies_router
from .coder_workspaces import router as coder_workspaces_router
from .tasks import router as tasks_router
from .data import router as data_router
from .alerts import router as alerts_router
from .workers import router as workers_router
from .dashboard import router as dashboard_router
from .deployments import router as deployments_router

router = APIRouter(prefix="/crawlhub")
router.include_router(projects_router)
router.include_router(spiders_router)
router.include_router(proxies_router)
router.include_router(coder_workspaces_router)
router.include_router(tasks_router)
router.include_router(data_router)
router.include_router(alerts_router)
router.include_router(workers_router)
router.include_router(dashboard_router)
router.include_router(deployments_router)
