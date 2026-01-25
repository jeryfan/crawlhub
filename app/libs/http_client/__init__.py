"""HTTP Client module."""

from .client import HttpClient
from .middleware import (
    headers_middleware,
    logging_middleware,
    retry_middleware,
    timeout_middleware,
)
from .models import Request, Response, StreamChunk
from .pool import PoolLimits, ProxyConfig
from .types import Middleware, NextFn, StreamMiddleware, StreamNextFn

__all__ = [
    "HttpClient",
    "Request",
    "Response",
    "StreamChunk",
    "PoolLimits",
    "ProxyConfig",
    "Middleware",
    "NextFn",
    "StreamMiddleware",
    "StreamNextFn",
    "retry_middleware",
    "timeout_middleware",
    "logging_middleware",
    "headers_middleware",
]
