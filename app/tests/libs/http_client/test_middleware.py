import pytest
from unittest.mock import AsyncMock

from libs.http_client.models import Request, Response
from libs.http_client.middleware import retry_middleware, timeout_middleware, logging_middleware


class TestRetryMiddleware:
    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        req = Request(method="GET", url="https://example.com")
        success_resp = Response(status_code=200, headers={}, body=b"", latency_ms=0, request=req)

        call_count = 0

        async def next_fn(r: Request) -> Response:
            nonlocal call_count
            call_count += 1
            return success_resp

        middleware = retry_middleware(max_retries=3)
        result = await middleware(req, next_fn)

        assert result.status_code == 200
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_502(self):
        req = Request(method="GET", url="https://example.com")
        fail_resp = Response(status_code=502, headers={}, body=b"", latency_ms=0, request=req)
        success_resp = Response(status_code=200, headers={}, body=b"", latency_ms=0, request=req)

        call_count = 0

        async def next_fn(r: Request) -> Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return fail_resp
            return success_resp

        middleware = retry_middleware(max_retries=3)
        result = await middleware(req, next_fn)

        assert result.status_code == 200
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        req = Request(method="GET", url="https://example.com")
        fail_resp = Response(status_code=503, headers={}, body=b"", latency_ms=0, request=req)

        call_count = 0

        async def next_fn(r: Request) -> Response:
            nonlocal call_count
            call_count += 1
            return fail_resp

        middleware = retry_middleware(max_retries=2)
        result = await middleware(req, next_fn)

        assert result.status_code == 503
        assert call_count == 3  # 1 initial + 2 retries


class TestTimeoutMiddleware:
    @pytest.mark.asyncio
    async def test_timeout_override(self):
        req = Request(method="GET", url="https://example.com", timeout=30.0)
        resp = Response(status_code=200, headers={}, body=b"", latency_ms=0, request=req)

        received_request = None

        async def next_fn(r: Request) -> Response:
            nonlocal received_request
            received_request = r
            return resp

        middleware = timeout_middleware(60.0)
        await middleware(req, next_fn)

        assert received_request is not None
        assert received_request.timeout == 60.0
