import logging

from .models import Request, Response
from .types import Middleware, NextFn


def retry_middleware(
    max_retries: int = 3,
    retry_on: tuple[int, ...] = (502, 503, 504),
) -> Middleware:
    async def middleware(request: Request, next: NextFn) -> Response:
        last_response: Response | None = None
        for _ in range(max_retries + 1):
            response = await next(request)
            if response.status_code not in retry_on:
                return response
            last_response = response
        assert last_response is not None
        return last_response

    return middleware


def timeout_middleware(timeout: float) -> Middleware:
    async def middleware(request: Request, next: NextFn) -> Response:
        return await next(request.with_timeout(timeout))

    return middleware


def logging_middleware(logger: logging.Logger | None = None) -> Middleware:
    log = logger or logging.getLogger(__name__)

    async def middleware(request: Request, next: NextFn) -> Response:
        log.info(f"-> {request.method} {request.url}")
        response = await next(request)
        log.info(f"<- {response.status_code} ({response.latency_ms}ms)")
        return response

    return middleware


def headers_middleware(**headers: str) -> Middleware:
    async def middleware(request: Request, next: NextFn) -> Response:
        return await next(request.with_headers(**headers))

    return middleware
