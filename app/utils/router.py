import importlib
from pkgutil import iter_modules

from fastapi import APIRouter


def include_router(package, parent_router: APIRouter):
    for module_info in iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue

        module_path = f"{package.__name__}.{module_info.name}"
        module = importlib.import_module(module_path)

        if hasattr(module, "router"):
            parent_router.include_router(module.router)

        if module_info.ispkg:
            include_router(module, parent_router)
