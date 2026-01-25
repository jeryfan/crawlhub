import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from libs.http_client.client import HttpClient
from libs.http_client.models import Response, StreamChunk


class TestHttpClientRequest:
    @pytest.mark.asyncio
    async def test_simple_get(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = httpx.Headers({"content-type": "application/json"})
        mock_response.content = b'{"ok": true}'

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            async with HttpClient() as client:
                response = await client.get("https://api.example.com/data")
                assert response.status_code == 200
                assert response.json() == {"ok": True}

    @pytest.mark.asyncio
    async def test_post_with_body(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = httpx.Headers({})
        mock_response.content = b""

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            async with HttpClient() as client:
                response = await client.post(
                    "https://api.example.com/users",
                    body={"name": "test"},
                )
                assert response.status_code == 201
                call_args = mock_request.call_args
                assert call_args.kwargs["method"] == "POST"

    @pytest.mark.asyncio
    async def test_custom_headers(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = httpx.Headers({})
        mock_response.content = b""

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            async with HttpClient(default_headers={"X-Api-Key": "secret"}) as client:
                response = await client.get(
                    "https://api.example.com/data",
                    headers={"X-Request-Id": "123"},
                )
                call_args = mock_request.call_args
                headers = call_args.kwargs["headers"]
                assert headers["X-Api-Key"] == "secret"
                assert headers["X-Request-Id"] == "123"


class TestHttpClientStream:
    @pytest.mark.asyncio
    async def test_stream_response(self):
        chunks = [b"chunk1", b"chunk2", b"chunk3"]

        async def mock_aiter_bytes():
            for chunk in chunks:
                yield chunk

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = httpx.Headers({"content-type": "text/plain"})
        mock_response.aiter_bytes = mock_aiter_bytes
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient.stream") as mock_stream:
            mock_stream.return_value = mock_response
            async with HttpClient() as client:
                received = []
                first_chunk = None
                async for chunk in client.stream("GET", "https://api.example.com/stream"):
                    if chunk.is_first:
                        first_chunk = chunk
                    received.append(chunk.data)

                assert first_chunk is not None
                assert first_chunk.status_code == 200
                assert received == chunks
