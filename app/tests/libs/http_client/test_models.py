import pytest

from libs.http_client.models import Request, Response, StreamChunk


class TestRequest:
    def test_create_request(self):
        req = Request(method="GET", url="https://example.com")
        assert req.method == "GET"
        assert req.url == "https://example.com"
        assert req.headers == {}
        assert req.body == b""
        assert req.timeout == 30.0

    def test_request_immutable(self):
        req = Request(method="GET", url="https://example.com")
        with pytest.raises(AttributeError):
            req.method = "POST"

    def test_with_headers(self):
        req = Request(method="GET", url="https://example.com")
        new_req = req.with_headers(Authorization="Bearer token")
        assert req.headers == {}
        assert new_req.headers == {"Authorization": "Bearer token"}

    def test_with_timeout(self):
        req = Request(method="GET", url="https://example.com")
        new_req = req.with_timeout(60.0)
        assert req.timeout == 30.0
        assert new_req.timeout == 60.0


class TestResponse:
    def test_create_response(self):
        req = Request(method="GET", url="https://example.com")
        resp = Response(
            status_code=200,
            headers={"content-type": "application/json"},
            body=b'{"ok": true}',
            latency_ms=100,
            request=req,
        )
        assert resp.status_code == 200
        assert resp.latency_ms == 100
        assert resp.request is req

    def test_ok_property(self):
        req = Request(method="GET", url="https://example.com")
        resp_200 = Response(status_code=200, headers={}, body=b"", latency_ms=0, request=req)
        resp_404 = Response(status_code=404, headers={}, body=b"", latency_ms=0, request=req)
        resp_500 = Response(status_code=500, headers={}, body=b"", latency_ms=0, request=req)
        assert resp_200.ok is True
        assert resp_404.ok is False
        assert resp_500.ok is False

    def test_json_method(self):
        req = Request(method="GET", url="https://example.com")
        resp = Response(
            status_code=200,
            headers={},
            body=b'{"name": "test", "value": 123}',
            latency_ms=0,
            request=req,
        )
        data = resp.json()
        assert data == {"name": "test", "value": 123}


class TestStreamChunk:
    def test_create_chunk(self):
        chunk = StreamChunk(data=b"hello")
        assert chunk.data == b"hello"
        assert chunk.status_code is None
        assert chunk.headers is None

    def test_is_first_property(self):
        first = StreamChunk(data=b"", status_code=200, headers={"content-type": "text/plain"})
        subsequent = StreamChunk(data=b"data")
        assert first.is_first is True
        assert subsequent.is_first is False


from libs.http_client.pool import PoolLimits, ProxyConfig


class TestPoolLimits:
    def test_default_values(self):
        limits = PoolLimits()
        assert limits.max_connections == 100
        assert limits.max_keepalive == 20
        assert limits.keepalive_expiry == 30.0

    def test_custom_values(self):
        limits = PoolLimits(max_connections=50, max_keepalive=10, keepalive_expiry=60.0)
        assert limits.max_connections == 50

    def test_to_httpx_limits(self):
        limits = PoolLimits(max_connections=50, max_keepalive=10)
        httpx_limits = limits.to_httpx_limits()
        assert httpx_limits.max_connections == 50
        assert httpx_limits.max_keepalive_connections == 10


class TestProxyConfig:
    def test_simple_proxy(self):
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        assert proxy.url == "http://proxy.example.com:8080"
        assert proxy.auth is None

    def test_proxy_with_auth(self):
        proxy = ProxyConfig(url="http://proxy.example.com:8080", auth=("user", "pass"))
        assert proxy.auth == ("user", "pass")

    def test_to_httpx_proxy(self):
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        assert proxy.to_httpx_proxy() == "http://proxy.example.com:8080"

    def test_to_httpx_proxy_with_auth(self):
        proxy = ProxyConfig(url="http://proxy.example.com:8080", auth=("user", "pass"))
        result = proxy.to_httpx_proxy()
        assert "user:pass@proxy.example.com" in result
