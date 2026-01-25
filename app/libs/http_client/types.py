from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Request, Response, StreamChunk

NextFn = Callable[["Request"], Awaitable["Response"]]
Middleware = Callable[["Request", NextFn], Awaitable["Response"]]

StreamNextFn = Callable[["Request"], AsyncGenerator["StreamChunk"]]
StreamMiddleware = Callable[["Request", StreamNextFn], AsyncGenerator["StreamChunk"]]
