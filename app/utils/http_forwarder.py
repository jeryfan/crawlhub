"""
Generic HTTP request forwarder.

A standalone utility for forwarding HTTP requests to target URLs,
supporting both streaming and buffered modes with full response passthrough.
"""

import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# Hop-by-hop headers that must be removed by proxies (RFC 2616)
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
    }
)


@dataclass
class ForwardRequest:
    """Request data for forwarding."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    timeout: float = 30.0
    follow_redirects: bool = True


@dataclass
class ForwardResponse:
    """Response data from forwarded request."""

    status_code: int
    headers: dict[str, str]
    body: bytes
    latency_ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400


@dataclass
class StreamChunk:
    """A chunk from streaming response."""

    data: bytes
    latency_ms: int
    error: str | None = None
    # Only set on first chunk
    status_code: int | None = None
    headers: dict[str, str] | None = None

    @property
    def is_first(self) -> bool:
        return self.headers is not None


def filter_hop_by_hop_headers(
    headers: dict[str, str],
    extra_exclude: set[str] | None = None,
) -> dict[str, str]:
    """
    Filter out hop-by-hop headers from response.

    Args:
        headers: Original headers
        extra_exclude: Additional headers to exclude (e.g., {"content-length"} for streaming)

    Returns:
        Filtered headers dict
    """
    excluded = HOP_BY_HOP_HEADERS
    if extra_exclude:
        excluded = excluded | extra_exclude
    return {k: v for k, v in headers.items() if k.lower() not in excluded}


def prepare_request_headers(
    headers: dict[str, str],
    preserve_host: bool = False,
    original_host: str | None = None,
) -> dict[str, str]:
    """
    Prepare headers for forwarding request.

    Args:
        headers: Original request headers
        preserve_host: Whether to preserve the original Host header
        original_host: The original Host header value (used if preserve_host=True)

    Returns:
        Filtered headers dict ready for forwarding
    """
    filtered = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    if preserve_host and original_host:
        filtered["host"] = original_host
    return filtered


class HttpForwarder:
    """
    Generic HTTP request forwarder.

    Supports both buffered and streaming modes for forwarding HTTP requests
    to target URLs with full response passthrough.

    Example usage:
        forwarder = HttpForwarder()

        # Buffered mode
        response = await forwarder.forward(ForwardRequest(
            method="GET",
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"},
        ))
        print(response.status_code, response.body)

        # Streaming mode
        async for chunk in forwarder.forward_stream(request):
            if chunk.is_first:
                print(f"Status: {chunk.status_code}")
            print(chunk.data)
    """

    async def forward(self, request: ForwardRequest) -> ForwardResponse:
        """
        Forward a request in buffered mode.

        Args:
            request: The request to forward

        Returns:
            ForwardResponse with complete response data
        """
        start_time = time.time()
        error_message = None
        status_code = 502
        headers: dict[str, str] = {}
        body = b""

        try:
            async with httpx.AsyncClient(timeout=request.timeout) as client:
                response = await client.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    content=request.body,
                    follow_redirects=request.follow_redirects,
                )
                status_code = response.status_code
                headers = dict(response.headers)
                body = response.content

        except httpx.TimeoutException:
            error_message = f"Request timeout after {request.timeout}s"
            logger.warning(f"Forward timeout for {request.url}: {error_message}")
            status_code = 504
        except httpx.ConnectError as e:
            error_message = f"Connection error: {e}"
            logger.warning(f"Forward connection error for {request.url}: {error_message}")
            status_code = 502
        except Exception as e:
            error_message = f"Forward error: {e}"
            logger.exception(f"Forward error for {request.url}: {error_message}")
            status_code = 500

        latency_ms = int((time.time() - start_time) * 1000)
        return ForwardResponse(
            status_code=status_code,
            headers=headers,
            body=body,
            latency_ms=latency_ms,
            error=error_message,
        )

    async def forward_stream(
        self,
        request: ForwardRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Forward a request in streaming mode.

        Args:
            request: The request to forward

        Yields:
            StreamChunk objects. The first chunk contains status_code and headers.
        """
        start_time = time.time()

        try:
            # Use separate timeout for connection vs read
            timeout = httpx.Timeout(request.timeout, read=None)
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    content=request.body,
                    follow_redirects=request.follow_redirects,
                ) as response,
            ):
                first_chunk = True
                async for chunk in response.aiter_bytes():
                    latency_ms = int((time.time() - start_time) * 1000)
                    if first_chunk:
                        yield StreamChunk(
                            data=chunk,
                            latency_ms=latency_ms,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                        )
                        first_chunk = False
                    else:
                        yield StreamChunk(data=chunk, latency_ms=latency_ms)

                # If no chunks were yielded, yield empty with headers
                if first_chunk:
                    latency_ms = int((time.time() - start_time) * 1000)
                    yield StreamChunk(
                        data=b"",
                        latency_ms=latency_ms,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                    )

        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            yield StreamChunk(
                data=b"",
                latency_ms=latency_ms,
                error=f"Request timeout after {request.timeout}s",
            )
        except httpx.ConnectError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            yield StreamChunk(
                data=b"",
                latency_ms=latency_ms,
                error=f"Connection error: {e}",
            )
        except httpx.RemoteProtocolError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            yield StreamChunk(
                data=b"",
                latency_ms=latency_ms,
                error=f"Remote protocol error: {e}",
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Streaming error for {request.url}: {e}")
            yield StreamChunk(
                data=b"",
                latency_ms=latency_ms,
                error=f"Forward error: {e}",
            )

    async def forward_with_failover(
        self,
        request: ForwardRequest,
        fallback_urls: list[str],
    ) -> ForwardResponse:
        """
        Forward a request with failover support.

        Tries the primary URL first, then falls back to alternative URLs on failure.

        Args:
            request: The request to forward (url is the primary target)
            fallback_urls: List of fallback URLs to try on failure

        Returns:
            ForwardResponse from the first successful target
        """
        urls = [request.url] + fallback_urls
        total_latency = 0
        last_response: ForwardResponse | None = None

        for idx, url in enumerate(urls):
            req = ForwardRequest(
                method=request.method,
                url=url,
                headers=request.headers,
                body=request.body,
                timeout=request.timeout,
                follow_redirects=request.follow_redirects,
            )
            response = await self.forward(req)
            total_latency += response.latency_ms
            last_response = response

            if response.error is None:
                # Success - return with cumulative latency
                return ForwardResponse(
                    status_code=response.status_code,
                    headers=response.headers,
                    body=response.body,
                    latency_ms=total_latency,
                    error=None,
                )

            if idx < len(urls) - 1:
                logger.info(f"Failover: trying {urls[idx + 1]} after {url} failed")

        # All failed - return last response with total latency
        assert last_response is not None
        return ForwardResponse(
            status_code=last_response.status_code,
            headers=last_response.headers,
            body=last_response.body,
            latency_ms=total_latency,
            error=last_response.error,
        )

    async def forward_stream_with_failover(
        self,
        request: ForwardRequest,
        fallback_urls: list[str],
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Forward a streaming request with failover support.

        Tries the primary URL first, then falls back to alternative URLs on connection failure.
        Once streaming starts successfully, no failover occurs.

        Args:
            request: The request to forward (url is the primary target)
            fallback_urls: List of fallback URLs to try on failure

        Yields:
            StreamChunk objects from the first successful connection
        """
        urls = [request.url] + fallback_urls

        for idx, url in enumerate(urls):
            req = ForwardRequest(
                method=request.method,
                url=url,
                headers=request.headers,
                body=request.body,
                timeout=request.timeout,
                follow_redirects=request.follow_redirects,
            )

            started = False
            error_chunk: StreamChunk | None = None

            async for chunk in self.forward_stream(req):
                if chunk.error:
                    error_chunk = chunk
                    break
                started = True
                yield chunk

            if started:
                # Successfully streamed - we're done
                return

            # Failed before streaming started
            if idx < len(urls) - 1:
                logger.info(f"Failover streaming: trying {urls[idx + 1]} after {url} failed")
            else:
                # Last URL also failed - yield the error
                if error_chunk:
                    yield error_chunk


# Singleton instance for convenience
http_forwarder = HttpForwarder()
