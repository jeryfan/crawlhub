import logging
from time import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from libs.helper import extract_remote_ip
from extensions.ext_logging import trace_id_generator, trace_id_var

logger = logging.getLogger(__name__)


class CustomMiddleware(BaseHTTPMiddleware):
    """切面程序"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # You can modify the request before passing it to the next middleware or endpoint
        if request.headers.get("x-trace-id"):
            trace_id = request.headers.get("x-trace-id")
        else:
            trace_id = trace_id_generator()

        ip = extract_remote_ip(request)
        path = request.url
        trace_id_var.set(trace_id)
        logger.info(f"| {ip} | {request.method} {path}")
        start_time = time()
        response = await call_next(request)
        process_time = round(time() - start_time, 4)
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Trace-ID"] = trace_id or ""
        logger.info(f"| {ip} | {request.method} {path} | process_time={process_time}s")
        return response


class WebSocketLoggingMiddleware:
    """WebSocket 日志中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            trace_id = trace_id_generator()
            trace_id_var.set(trace_id)
        await self.app(scope, receive, send)
