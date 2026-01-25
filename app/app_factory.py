import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from configs import app_config
from exceptions import exception_handler
from middlewares.http_middleware import CustomMiddleware
from models.engine import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the FastAPI application...")
    yield
    await engine.dispose()


def config_router(app: FastAPI):
    from routers import admin, api, console, files, help, payment, proxy

    app.include_router(help.router)
    app.include_router(console.router)
    app.include_router(files.router)
    app.include_router(admin.router)
    app.include_router(payment.router)
    app.include_router(api.router)
    app.include_router(proxy.router)
    if app_config.DEBUG:
        from routers import tests

        app.include_router(tests.router)


def setup_static_files(app: FastAPI, static_files_dir: Path = Path("static")):
    """
    Setup the static files directory.
    Args:
        app (FastAPI): FastAPI app.
        path (str): Path to the static files directory.
    """
    app.mount(
        "/static",
        StaticFiles(directory=static_files_dir, html=True),
        name="static",
    )


def initialize_extensions(app: FastAPI):
    from extensions import (
        ext_celery,
        ext_code_based_extension,
        ext_es,
        ext_logging,
        ext_mail,
        ext_mongodb,
        ext_redis,
        ext_storage,
    )

    extensions = [
        ext_logging,
        ext_storage,
        ext_celery,
        ext_redis,
        ext_mail,
        ext_es,
        ext_mongodb,
        ext_code_based_extension,
    ]
    for ext in extensions:
        short_name = ext.__name__.split(".")[-1]
        is_enabled = ext.is_enabled() if hasattr(ext, "is_enabled") else True
        if not is_enabled:
            if app_config.DEBUG:
                logger.info("Skipped %s", short_name)
            continue

        start_time = time.perf_counter()
        ext.init_app(app)
        end_time = time.perf_counter()
        if app_config.DEBUG:
            logger.info(
                "Loaded %s (%s ms)",
                short_name,
                round((end_time - start_time) * 1000, 2),
            )


def create_app() -> FastAPI:
    app = FastAPI(
        title=app_config.PROJECT_NAME,
        lifespan=lifespan,
        version="1.0.0",
        openapi_url="/api/openapi.json",
    )
    setup_static_files(app)
    initialize_extensions(app)

    # 设置 CORS 中间件
    cors_origins = [
        origin.strip() for origin in app_config.CORS_ORIGINS.split(",") if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add CSRF protection middleware (if enabled)
    if app_config.CSRF_ENABLED:
        logger.info("CSRF protection middleware enabled")

    app.add_middleware(CustomMiddleware)

    config_router(app)
    exception_handler.set_up(app)

    logger.info(f"FastAPI 应用创建完成: {app_config.PROJECT_NAME}")
    return app
