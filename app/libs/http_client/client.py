import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .models import Request, Response, StreamChunk
from .pool import PoolLimits, ProxyConfig
from .types import Middleware


class HttpClient:
    def __init__(
        self,
        middlewares: list[Middleware] | None = None,
        pool_limits: PoolLimits | None = None,
        proxy: str | ProxyConfig | None = None,
        default_timeout: float = 30.0,
        default_headers: dict[str, str] | None = None,
    ):
        self._middlewares = middlewares or []
        self._pool_limits = pool_limits or PoolLimits()
        self._proxy = proxy
        self._default_timeout = default_timeout
        self._default_headers = default_headers or {}
        self._client: httpx.AsyncClient | None = None

    def _get_proxy_url(self) -> str | None:
        if self._proxy is None:
            return None
        if isinstance(self._proxy, str):
            return self._proxy
        return self._proxy.to_httpx_proxy()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=self._pool_limits.to_httpx_limits(),
                proxy=self._get_proxy_url(),
                timeout=self._default_timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "HttpClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *_args: Any) -> None:
        await self.close()

    def _prepare_body(self, body: bytes | str | dict | None) -> bytes:
        if body is None:
            return b""
        if isinstance(body, bytes):
            return body
        if isinstance(body, str):
            return body.encode("utf-8")
        return json.dumps(body).encode("utf-8")

    def _merge_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        merged = dict(self._default_headers)
        if headers:
            merged.update(headers)
        return merged

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes | str | dict | None = None,
        timeout: float | None = None,
    ) -> Response:
        req = Request(
            method=method,
            url=url,
            headers=self._merge_headers(headers),
            body=self._prepare_body(body),
            timeout=timeout or self._default_timeout,
        )
        return await self._execute(req)

    async def _execute(self, request: Request) -> Response:
        if self._middlewares:
            return await self._execute_with_middleware(request, 0)
        return await self._do_request(request)

    async def _execute_with_middleware(self, request: Request, index: int) -> Response:
        if index >= len(self._middlewares):
            return await self._do_request(request)

        middleware = self._middlewares[index]

        async def next_fn(req: Request) -> Response:
            return await self._execute_with_middleware(req, index + 1)

        return await middleware(request, next_fn)

    async def _do_request(self, request: Request) -> Response:
        client = await self._ensure_client()
        start_time = time.time()

        http_response = await client.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            content=request.body,
            timeout=request.timeout,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return Response(
            status_code=http_response.status_code,
            headers=dict(http_response.headers),
            body=http_response.content,
            latency_ms=latency_ms,
            request=request,
        )

    async def get(self, url: str, **kwargs: Any) -> Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> Response:
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> Response:
        return await self.request("PATCH", url, **kwargs)

    async def stream(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes | str | dict | None = None,
        timeout: float | None = None,
    ) -> AsyncGenerator[StreamChunk]:
        req = Request(
            method=method,
            url=url,
            headers=self._merge_headers(headers),
            body=self._prepare_body(body),
            timeout=timeout or self._default_timeout,
        )

        client = await self._ensure_client()
        stream_timeout = httpx.Timeout(req.timeout, read=None)

        async with client.stream(
            method=req.method,
            url=req.url,
            headers=req.headers,
            content=req.body,
            timeout=stream_timeout,
        ) as response:
            first = True
            async for chunk in response.aiter_bytes():
                if first:
                    yield StreamChunk(
                        data=chunk,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                    )
                    first = False
                else:
                    yield StreamChunk(data=chunk)

            if first:
                yield StreamChunk(
                    data=b"",
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
