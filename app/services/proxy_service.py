"""
Proxy service module.

Contains services for:
- ProxyRouteService: Managing proxy route configurations (CRUD)
- ProxyLogService: Managing proxy request logs in MongoDB
- ProxyForwardService: Forwarding HTTP requests to target URLs
"""

import json
import logging
import time
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime
from typing import Any

import httpx
from bson import ObjectId
from fastapi import Request
from sqlalchemy import func, select

from extensions.ext_mongodb import mongodb_client
from libs.http_client import HttpClient
from models.proxy import ProxyLoadBalanceMode, ProxyRoute, ProxyRouteStatus
from schemas.proxy import ProxyRouteCreate, ProxyRouteUpdate
from services.base_service import BaseService

logger = logging.getLogger(__name__)


# ============ HTTP Forwarding Utilities ============

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


# ============ Round Robin Counter ============


class RoundRobinCounter:
    """Simple round-robin counter for load balancing."""

    def __init__(self):
        self._counters: dict[str, int] = {}

    def get_next_index(self, route_id: str, total: int) -> int:
        """Get next index for round-robin selection."""
        if total <= 0:
            return 0
        current = self._counters.get(route_id, 0)
        self._counters[route_id] = (current + 1) % total
        return current


_round_robin = RoundRobinCounter()


# ============ Proxy Route Service ============


class ProxyRouteService(BaseService):
    """Service for managing proxy route configurations."""

    async def create_route(
        self,
        data: ProxyRouteCreate,
        created_by: str | None = None,
    ) -> ProxyRoute:
        """Create a new proxy route."""
        route = ProxyRoute(
            path=data.path,
            target_urls=data.target_urls,
            load_balance_mode=data.load_balance_mode,
            methods=data.methods,
            description=data.description,
            timeout=data.timeout,
            preserve_host=data.preserve_host,
            enable_logging=data.enable_logging,
            created_by=created_by,
        )
        self.db.add(route)
        await self.db.flush()
        await self.db.refresh(route)
        return route

    async def get_route(self, route_id: str) -> ProxyRoute | None:
        """Get a proxy route by ID."""
        result = await self.db.execute(select(ProxyRoute).where(ProxyRoute.id == route_id))
        return result.scalar_one_or_none()

    async def get_route_by_path(self, path: str) -> ProxyRoute | None:
        """Get a proxy route by path."""
        result = await self.db.execute(select(ProxyRoute).where(ProxyRoute.path == path))
        return result.scalar_one_or_none()

    async def update_route(
        self,
        route_id: str,
        data: ProxyRouteUpdate,
    ) -> ProxyRoute | None:
        """Update a proxy route."""
        route = await self.get_route(route_id)
        if not route:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(route, field, value)

        await self.db.flush()
        await self.db.refresh(route)
        return route

    async def delete_route(self, route_id: str) -> bool:
        """Delete a proxy route."""
        route = await self.get_route(route_id)
        if not route:
            return False

        await self.db.delete(route)
        await self.db.flush()
        return True

    async def list_routes(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[Sequence[ProxyRoute], int]:
        """List proxy routes with pagination."""
        query = select(ProxyRoute)

        if status:
            query = query.where(ProxyRoute.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = query.order_by(ProxyRoute.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        routes = result.scalars().all()

        return routes, total

    async def get_enabled_routes(self) -> Sequence[ProxyRoute]:
        """Get all enabled proxy routes."""
        result = await self.db.execute(
            select(ProxyRoute).where(ProxyRoute.status == ProxyRouteStatus.ENABLED)
        )
        return result.scalars().all()

    async def match_route(self, path: str, method: str) -> ProxyRoute | None:
        """
        Match a request path to an enabled proxy route.

        Args:
            path: The request path to match
            method: The HTTP method

        Returns:
            The matched ProxyRoute or None
        """
        # Normalize path
        normalized_path = path.rstrip("/") or "/"

        # Get all enabled routes
        routes = await self.get_enabled_routes()

        for route in routes:
            route_path = route.path.rstrip("/") or "/"

            # Exact match or prefix match
            if (
                normalized_path == route_path or normalized_path.startswith(route_path + "/")
            ) and route.allows_method(method):
                return route

        return None

    async def toggle_status(self, route_id: str) -> ProxyRoute | None:
        """Toggle the status of a proxy route."""
        route = await self.get_route(route_id)
        if not route:
            return None

        new_status = (
            ProxyRouteStatus.DISABLED
            if route.status == ProxyRouteStatus.ENABLED
            else ProxyRouteStatus.ENABLED
        )
        route.status = new_status

        await self.db.flush()
        await self.db.refresh(route)
        return route


# ============ Proxy Log Service ============

# Headers to mask for security
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "cookie",
    "set-cookie",
    "x-csrf-token",
}

PROXY_LOGS_COLLECTION = "proxy_logs"
PROXY_LOG_TTL_DAYS = 30  # 日志保留天数


class ProxyLogService:
    """Service for managing proxy request logs in MongoDB."""

    def __init__(self):
        self._collection = None
        self._indexes_created = False

    @property
    def collection(self):
        if self._collection is None:
            self._collection = mongodb_client.get_collection(PROXY_LOGS_COLLECTION)
        return self._collection

    async def ensure_indexes(self) -> None:
        """Create indexes for proxy_logs collection (called once on first use)."""
        if self._indexes_created or not mongodb_client.is_enabled():
            return

        try:
            await mongodb_client.ensure_indexes(
                PROXY_LOGS_COLLECTION,
                [
                    {"keys": "route_id"},
                    {"keys": "request.path"},
                    {"keys": "response.status_code"},
                    {"keys": "status"},
                    {"keys": "client_ip"},
                    {"keys": [("created_at", -1)]},
                ],
            )

            # TTL index for automatic cleanup (30 days)
            ttl_seconds = PROXY_LOG_TTL_DAYS * 24 * 60 * 60
            await mongodb_client.create_ttl_index(
                PROXY_LOGS_COLLECTION,
                "created_at",
                expire_seconds=ttl_seconds,
            )

            self._indexes_created = True
            logger.info("MongoDB indexes created for proxy_logs collection")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")

    @staticmethod
    def mask_sensitive_headers(headers: dict[str, str] | None) -> dict[str, str] | None:
        """Mask sensitive header values."""
        if not headers:
            return headers

        masked = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked

    async def create_pending_log(
        self,
        route_id: str,
        route_path: str,
        target_url: str,
        request_method: str,
        request_path: str,
        request_query_params: dict[str, Any] | None,
        request_headers: dict[str, str] | None,
        request_body: Any | None,
        request_body_size: int,
        client_ip: str | None = None,
    ) -> str | None:
        """
        Create a pending proxy log entry before the request is sent.

        Returns the inserted document ID or None if logging is disabled.
        """
        if not mongodb_client.is_enabled():
            logger.debug("MongoDB is disabled, skipping proxy log")
            return None

        # Ensure indexes on first use
        await self.ensure_indexes()

        doc = {
            "route_id": route_id,
            "route_path": route_path,
            "target_url": target_url,
            "request": {
                "method": request_method,
                "path": request_path,
                "query_params": request_query_params,
                "headers": self.mask_sensitive_headers(request_headers),
                "body": request_body,
                "body_size": request_body_size,
            },
            "response": None,
            "status": "pending",
            "latency_ms": 0,
            "client_ip": client_ip,
            "error": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

        try:
            result = await self.collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create pending proxy log: {e}")
            return None

    async def update_log_response(
        self,
        log_id: str,
        response_status_code: int,
        response_headers: dict[str, str] | None,
        response_body: Any | None,
        response_body_size: int,
        latency_ms: int,
        error: str | None = None,
    ) -> bool:
        """
        Update a pending log entry with response data.

        Returns True if update was successful.
        """
        if not mongodb_client.is_enabled() or not log_id:
            return False

        try:
            update_data = {
                "$set": {
                    "response": {
                        "status_code": response_status_code,
                        "headers": self.mask_sensitive_headers(response_headers),
                        "body": response_body,
                        "body_size": response_body_size,
                    },
                    "status": "error" if error else "completed",
                    "latency_ms": latency_ms,
                    "error": error,
                    "completed_at": datetime.utcnow(),
                }
            }
            result = await self.collection.update_one(
                {"_id": ObjectId(log_id)},
                update_data,
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update proxy log: {e}")
            return False

    async def log_request(
        self,
        route_id: str,
        route_path: str,
        target_url: str,
        request_method: str,
        request_path: str,
        request_query_params: dict[str, Any] | None,
        request_headers: dict[str, str] | None,
        request_body: Any | None,
        request_body_size: int,
        response_status_code: int,
        response_headers: dict[str, str] | None,
        response_body: Any | None,
        response_body_size: int,
        latency_ms: int,
        client_ip: str | None = None,
        error: str | None = None,
    ) -> str | None:
        """
        Log a proxy request to MongoDB (legacy single-step method).

        Returns the inserted document ID or None if logging is disabled.
        """
        if not mongodb_client.is_enabled():
            logger.debug("MongoDB is disabled, skipping proxy log")
            return None

        # Ensure indexes on first use
        await self.ensure_indexes()

        doc = {
            "route_id": route_id,
            "route_path": route_path,
            "target_url": target_url,
            "request": {
                "method": request_method,
                "path": request_path,
                "query_params": request_query_params,
                "headers": self.mask_sensitive_headers(request_headers),
                "body": request_body,
                "body_size": request_body_size,
            },
            "response": {
                "status_code": response_status_code,
                "headers": self.mask_sensitive_headers(response_headers),
                "body": response_body,
                "body_size": response_body_size,
            },
            "status": "error" if error else "completed",
            "latency_ms": latency_ms,
            "client_ip": client_ip,
            "error": error,
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        }

        try:
            result = await self.collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to log proxy request: {e}")
            return None

    async def get_log(self, log_id: str) -> dict | None:
        """Get a single log entry by ID."""
        if not mongodb_client.is_enabled():
            return None

        try:
            doc = await self.collection.find_one({"_id": ObjectId(log_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Failed to get proxy log: {e}")
            return None

    async def search_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        route_id: str | None = None,
        route_path: str | None = None,
        status_code: int | None = None,
        client_ip: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        has_error: bool | None = None,
    ) -> tuple[list[dict], int]:
        """
        Search proxy logs with filters.

        Returns a tuple of (logs, total_count).
        """
        if not mongodb_client.is_enabled():
            return [], 0

        # Build query filter
        query: dict[str, Any] = {}

        if route_id:
            query["route_id"] = route_id
        if route_path:
            query["route_path"] = {"$regex": route_path, "$options": "i"}
        if status_code:
            query["response.status_code"] = status_code
        if client_ip:
            query["client_ip"] = client_ip
        if has_error is True:
            query["error"] = {"$ne": None}
        elif has_error is False:
            query["error"] = None

        # Time range filter
        if start_time or end_time:
            query["created_at"] = {}
            if start_time:
                query["created_at"]["$gte"] = start_time
            if end_time:
                query["created_at"]["$lte"] = end_time

        try:
            # Get total count
            total = await self.collection.count_documents(query)

            # Get paginated results
            cursor = (
                self.collection.find(query)
                .sort("created_at", -1)
                .skip((page - 1) * page_size)
                .limit(page_size)
            )

            logs = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                logs.append(doc)

            return logs, total
        except Exception as e:
            logger.error(f"Failed to search proxy logs: {e}")
            return [], 0

    async def get_statistics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        route_id: str | None = None,
    ) -> dict:
        """
        Get statistics for proxy logs.

        Returns aggregated statistics including:
        - Total requests
        - Success/error counts
        - Average latency
        - Requests by route
        - Requests by status code
        """
        if not mongodb_client.is_enabled():
            return {
                "total_requests": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "requests_by_route": {},
                "requests_by_status": {},
            }

        # Build match stage
        match_stage: dict[str, Any] = {}
        if route_id:
            match_stage["route_id"] = route_id
        if start_time or end_time:
            match_stage["created_at"] = {}
            if start_time:
                match_stage["created_at"]["$gte"] = start_time
            if end_time:
                match_stage["created_at"]["$lte"] = end_time

        try:
            pipeline = []
            if match_stage:
                pipeline.append({"$match": match_stage})

            pipeline.extend(
                [
                    {
                        "$facet": {
                            "overview": [
                                {
                                    "$group": {
                                        "_id": None,
                                        "total": {"$sum": 1},
                                        "success_count": {
                                            "$sum": {
                                                "$cond": [
                                                    {
                                                        "$and": [
                                                            {
                                                                "$gte": [
                                                                    "$response.status_code",
                                                                    200,
                                                                ]
                                                            },
                                                            {
                                                                "$lt": [
                                                                    "$response.status_code",
                                                                    400,
                                                                ]
                                                            },
                                                        ]
                                                    },
                                                    1,
                                                    0,
                                                ]
                                            }
                                        },
                                        "error_count": {
                                            "$sum": {"$cond": [{"$ne": ["$error", None]}, 1, 0]}
                                        },
                                        "avg_latency": {"$avg": "$latency_ms"},
                                    }
                                }
                            ],
                            "by_route": [
                                {"$group": {"_id": "$route_path", "count": {"$sum": 1}}},
                                {"$sort": {"count": -1}},
                                {"$limit": 10},
                            ],
                            "by_status": [
                                {
                                    "$group": {
                                        "_id": "$response.status_code",
                                        "count": {"$sum": 1},
                                    }
                                },
                                {"$sort": {"_id": 1}},
                            ],
                        }
                    }
                ]
            )

            cursor = self.collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)

            if not result:
                return {
                    "total_requests": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "success_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "requests_by_route": {},
                    "requests_by_status": {},
                }

            data = result[0]
            overview = data["overview"][0] if data["overview"] else {}

            total = overview.get("total", 0)
            success_count = overview.get("success_count", 0)

            return {
                "total_requests": total,
                "success_count": success_count,
                "error_count": overview.get("error_count", 0),
                "success_rate": (success_count / total * 100) if total > 0 else 0.0,
                "avg_latency_ms": round(overview.get("avg_latency", 0), 2),
                "requests_by_route": {
                    item["_id"]: item["count"] for item in data.get("by_route", [])
                },
                "requests_by_status": {
                    str(item["_id"]): item["count"] for item in data.get("by_status", [])
                },
            }
        except Exception as e:
            logger.error(f"Failed to get proxy log statistics: {e}")
            return {
                "total_requests": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "requests_by_route": {},
                "requests_by_status": {},
            }

    async def delete_logs_by_route(self, route_id: str) -> int:
        """Delete all logs for a specific route."""
        if not mongodb_client.is_enabled():
            return 0

        try:
            result = await self.collection.delete_many({"route_id": route_id})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete proxy logs: {e}")
            return 0

    async def delete_all_logs(self) -> int:
        """Delete all proxy logs."""
        if not mongodb_client.is_enabled():
            return 0

        try:
            result = await self.collection.delete_many({})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete all proxy logs: {e}")
            return 0


# ============ Proxy Forward Service ============


class ProxyForwardService:
    """
    Service for forwarding HTTP requests to target URLs.

    Uses libs.http_client.HttpClient for the actual request forwarding, adding:
    - Load balancing (round-robin, failover)
    - Route-based configuration
    - Request logging
    """

    def __init__(self):
        self.log_service = ProxyLogService()
        self._client: HttpClient | None = None

    async def _get_client(self) -> HttpClient:
        """Get or create the HTTP client instance."""
        if self._client is None:
            self._client = HttpClient()
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.close()
            self._client = None

    def _select_target_url(self, route: ProxyRoute) -> tuple[str, list[str]]:
        """
        Select target URL based on load balance mode.

        Returns:
            Tuple of (selected_url, remaining_urls_for_failover)
        """
        all_urls = route.get_all_target_urls()

        if len(all_urls) == 0:
            raise ValueError("No target URLs configured")

        if len(all_urls) == 1:
            return all_urls[0], []

        if route.load_balance_mode == ProxyLoadBalanceMode.ROUND_ROBIN:
            idx = _round_robin.get_next_index(route.id, len(all_urls))
            selected = all_urls[idx]
            # For round_robin, no failover - just use the selected one
            return selected, []
        else:
            # Failover mode: return first URL and rest as fallbacks
            return all_urls[0], all_urls[1:]

    def _build_target_url(
        self,
        base_url: str,
        path_suffix: str,
        query: str | None,
    ) -> str:
        """Build full target URL with path suffix and query string."""
        full_url = base_url
        if path_suffix:
            full_url = f"{base_url}/{path_suffix.lstrip('/')}"
        if query:
            full_url = f"{full_url}?{query}"
        return full_url

    def _prepare_headers(
        self,
        request: Request,
        route: ProxyRoute,
    ) -> dict[str, str]:
        """Prepare headers for forwarding."""
        headers = prepare_request_headers(
            headers=dict(request.headers),
            preserve_host=route.preserve_host,
            original_host=request.headers.get("host"),
        )
        return headers

    async def _do_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
    ) -> tuple[httpx.Response | None, int, str | None]:
        """
        Execute a single HTTP request.

        Returns:
            Tuple of (response, latency_ms, error_message)
        """
        client = await self._get_client()
        start_time = time.time()

        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                timeout=timeout,
            )

            # Create httpx.Response for backward compatibility
            http_response = httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=response.body,
            )
            return http_response, response.latency_ms, None

        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            return None, latency_ms, f"Request timeout after {timeout}s"

        except httpx.ConnectError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return None, latency_ms, f"Connection error: {e}"

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Forward error for {url}: {e}")
            return None, latency_ms, f"Forward error: {e}"

    async def forward_request(
        self,
        request: Request,
        route: ProxyRoute,
        path_suffix: str = "",
    ) -> tuple[httpx.Response | None, int, str | None, str]:
        """
        Forward a request to the target URL with failover support.

        Args:
            request: The incoming FastAPI request
            route: The matched proxy route
            path_suffix: Additional path after the matched route path

        Returns:
            Tuple of (response, latency_ms, error_message, used_target_url)
        """
        headers = self._prepare_headers(request, route)
        body = await request.body()
        query = request.url.query or None

        # Select target URL
        selected_url, fallback_urls = self._select_target_url(route)
        target_url = self._build_target_url(selected_url, path_suffix, query)
        fallback_target_urls = [
            self._build_target_url(url, path_suffix, query) for url in fallback_urls
        ]

        # Try primary URL first, then failovers
        urls_to_try = [target_url] + fallback_target_urls
        total_latency = 0

        for idx, url in enumerate(urls_to_try):
            response, latency, error = await self._do_request(
                method=request.method,
                url=url,
                headers=headers,
                body=body,
                timeout=route.timeout,
            )
            total_latency += latency

            if error is None:
                # Success
                return response, total_latency, None, url

            # Log failover attempt
            if idx < len(urls_to_try) - 1:
                logger.info(f"Failover: trying {urls_to_try[idx + 1]} after {url} failed")

        # All URLs failed
        return None, total_latency, error, target_url

    async def _do_stream(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
    ) -> AsyncGenerator[tuple[bytes, int, str | None, dict | None, int | None], None]:
        """
        Execute a single streaming HTTP request.

        Yields tuples of (chunk, latency_ms, error, headers, status_code).
        First chunk includes headers and status_code.
        """
        client = await self._get_client()
        start_time = time.time()

        try:
            async for chunk in client.stream(
                method=method,
                url=url,
                headers=headers,
                body=body,
                timeout=timeout,
            ):
                latency_ms = int((time.time() - start_time) * 1000)
                if chunk.is_first:
                    yield chunk.data, latency_ms, None, chunk.headers, chunk.status_code
                else:
                    yield chunk.data, latency_ms, None, None, None

        except httpx.TimeoutException:
            latency_ms = int((time.time() - start_time) * 1000)
            yield b"", latency_ms, f"Request timeout after {timeout}s", None, None

        except httpx.ConnectError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            yield b"", latency_ms, f"Connection error: {e}", None, None

        except httpx.RemoteProtocolError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            yield b"", latency_ms, f"Remote protocol error: {e}", None, None

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Streaming error for {url}: {e}")
            yield b"", latency_ms, f"Forward error: {e}", None, None

    async def forward_streaming_request(
        self,
        request: Request,
        route: ProxyRoute,
        path_suffix: str = "",
    ) -> AsyncGenerator[tuple[bytes, int, str | None, str, dict | None, int | None], None]:
        """
        Forward a streaming request to the target URL.

        Yields tuples of (chunk, latency_ms, error, target_url, response_headers, status_code).
        The first yield includes response_headers and status_code, subsequent yields have None.
        """
        headers = self._prepare_headers(request, route)
        body = await request.body()
        query = request.url.query or None

        # Select target URL
        selected_url, fallback_urls = self._select_target_url(route)
        target_url = self._build_target_url(selected_url, path_suffix, query)
        fallback_target_urls = [
            self._build_target_url(url, path_suffix, query) for url in fallback_urls
        ]

        # Try primary URL first, then failovers
        urls_to_try = [target_url] + fallback_target_urls

        for idx, url in enumerate(urls_to_try):
            started = False
            error_chunk: tuple[bytes, int, str | None, dict | None, int | None] | None = None

            async for chunk_data, latency, error, hdrs, status in self._do_stream(
                method=request.method,
                url=url,
                headers=headers,
                body=body,
                timeout=route.timeout,
            ):
                if error:
                    error_chunk = (chunk_data, latency, error, hdrs, status)
                    break
                started = True
                yield chunk_data, latency, None, url, hdrs, status

            if started:
                # Successfully started streaming - we're done
                return

            # Failed before streaming started - try next URL
            if idx < len(urls_to_try) - 1:
                logger.info(f"Failover streaming: trying {urls_to_try[idx + 1]} after {url} failed")
            else:
                # Last URL also failed - yield the error
                if error_chunk:
                    yield (
                        error_chunk[0],
                        error_chunk[1],
                        error_chunk[2],
                        target_url,
                        error_chunk[3],
                        error_chunk[4],
                    )

    async def create_pending_log(
        self,
        route: ProxyRoute,
        request: Request,
        request_body: bytes,
        target_url: str,
    ) -> str | None:
        """Create a pending log entry before forwarding the request."""
        if not route.enable_logging:
            return None

        # Parse request body
        request_body_parsed: Any = None
        try:
            if request_body:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    request_body_parsed = json.loads(request_body.decode("utf-8"))
                else:
                    request_body_parsed = request_body.decode("utf-8", errors="replace")
        except Exception:
            if request_body:
                request_body_parsed = request_body.decode("utf-8", errors="replace")

        # Get query params
        query_params = dict(request.query_params) if request.query_params else None

        # Get client IP
        client_ip = request.client.host if request.client else None

        return await self.log_service.create_pending_log(
            route_id=route.id,
            route_path=route.path,
            target_url=target_url,
            request_method=request.method,
            request_path=str(request.url.path),
            request_query_params=query_params,
            request_headers=dict(request.headers),
            request_body=request_body_parsed,
            request_body_size=len(request_body) if request_body else 0,
            client_ip=client_ip,
        )

    async def update_log_response(
        self,
        log_id: str | None,
        response: httpx.Response | None,
        response_body: bytes | None,
        latency_ms: int,
        error: str | None = None,
    ) -> bool:
        """Update a pending log entry with response data."""
        if not log_id:
            return False

        # Parse response body
        response_body_parsed: Any = None
        if response_body:
            try:
                response_content_type = response.headers.get("content-type", "") if response else ""
                if "application/json" in response_content_type:
                    response_body_parsed = json.loads(response_body.decode("utf-8"))
                else:
                    response_body_parsed = response_body.decode("utf-8", errors="replace")
            except Exception:
                response_body_parsed = response_body.decode("utf-8", errors="replace")

        return await self.log_service.update_log_response(
            log_id=log_id,
            response_status_code=response.status_code if response else 502,
            response_headers=dict(response.headers) if response else None,
            response_body=response_body_parsed,
            response_body_size=len(response_body) if response_body else 0,
            latency_ms=latency_ms,
            error=error,
        )

    async def log_request(
        self,
        route: ProxyRoute,
        request: Request,
        request_body: bytes,
        response: httpx.Response | None,
        response_body: bytes | None,
        latency_ms: int,
        used_target_url: str,
        error: str | None = None,
    ) -> str | None:
        """Log a proxy request to MongoDB (legacy single-step method)."""
        if not route.enable_logging:
            return None

        # Parse request body
        request_body_parsed: Any = None
        try:
            if request_body:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    request_body_parsed = json.loads(request_body.decode("utf-8"))
                else:
                    request_body_parsed = request_body.decode("utf-8", errors="replace")
        except Exception:
            if request_body:
                request_body_parsed = request_body.decode("utf-8", errors="replace")
            else:
                request_body_parsed = None

        # Parse response body
        response_body_parsed: Any = None
        if response_body:
            try:
                response_content_type = response.headers.get("content-type", "") if response else ""
                if "application/json" in response_content_type:
                    response_body_parsed = json.loads(response_body.decode("utf-8"))
                else:
                    response_body_parsed = response_body.decode("utf-8", errors="replace")
            except Exception:
                response_body_parsed = response_body.decode("utf-8", errors="replace")

        # Get query params
        query_params = dict(request.query_params) if request.query_params else None

        # Get client IP
        client_ip = request.client.host if request.client else None

        return await self.log_service.log_request(
            route_id=route.id,
            route_path=route.path,
            target_url=used_target_url,
            request_method=request.method,
            request_path=str(request.url.path),
            request_query_params=query_params,
            request_headers=dict(request.headers),
            request_body=request_body_parsed,
            request_body_size=len(request_body) if request_body else 0,
            response_status_code=response.status_code if response else 502,
            response_headers=dict(response.headers) if response else None,
            response_body=response_body_parsed,
            response_body_size=len(response_body) if response_body else 0,
            latency_ms=latency_ms,
            client_ip=client_ip,
            error=error,
        )


# ============ Proxy Gateway Service ============


class ProxyGatewayService:
    """
    High-level service for handling proxy gateway requests.

    Orchestrates route matching, request forwarding, response handling,
    and logging. Supports both streaming and buffered modes.
    """

    # Maximum response body size to store for logging (64KB)
    MAX_LOG_BODY_SIZE = 64 * 1024

    def __init__(self, db):
        self.db = db
        self.route_service = ProxyRouteService(db)
        self.forward_service = ProxyForwardService()

    async def match_route(self, path: str, method: str) -> ProxyRoute | None:
        """Match request path to a proxy route."""
        normalized_path = path.rstrip("/") or "/"
        return await self.route_service.match_route(normalized_path, method)

    @staticmethod
    def get_path_suffix(normalized_path: str, route: ProxyRoute) -> str:
        """Calculate path suffix after the matched route path."""
        route_path = route.path.rstrip("/") or "/"
        if normalized_path.startswith(route_path):
            return normalized_path[len(route_path) :]
        return ""

    async def handle_request(
        self,
        request: Request,
        route: ProxyRoute,
        path_suffix: str,
        streaming: bool = True,
    ):
        """
        Handle a proxy request and return appropriate response.

        Args:
            request: FastAPI request object
            route: Matched proxy route
            path_suffix: Path suffix after route match
            streaming: Use streaming mode if True

        Returns:
            FastAPI Response or StreamingResponse
        """
        from fastapi import Response
        from fastapi.responses import StreamingResponse

        if streaming:
            return await self._handle_streaming(
                request, route, path_suffix, Response, StreamingResponse, filter_hop_by_hop_headers
            )
        return await self._handle_buffered(
            request, route, path_suffix, Response, filter_hop_by_hop_headers
        )

    async def _handle_streaming(
        self,
        request: Request,
        route: ProxyRoute,
        path_suffix: str,
        Response,
        StreamingResponse,
        filter_hop_by_hop_headers,
    ):
        """Handle streaming proxy request."""
        import json
        import time

        # State tracking
        log_id: str | None = None
        log_body_chunks: list[bytes] = []
        log_body_size = 0
        total_body_size = 0
        response_headers: dict[str, str] = {}
        status_code = 0
        latency_ms = 0
        error: str | None = None
        response_started = False
        start_time = time.time()
        target_url = route.target_urls[0] if route.target_urls else ""

        # Create pending log
        request_body = await request.body()
        try:
            log_id = await self.forward_service.create_pending_log(
                route=route,
                request=request,
                request_body=request_body,
                target_url=target_url,
            )
        except Exception as e:
            logger.error(f"Failed to create pending log: {e}")

        async def stream_and_collect():
            nonlocal latency_ms, error, response_started, status_code
            nonlocal response_headers, target_url, total_body_size
            nonlocal log_body_chunks, log_body_size

            try:
                async for (
                    chunk,
                    lat,
                    err,
                    url,
                    hdrs,
                    sc,
                ) in self.forward_service.forward_streaming_request(request, route, path_suffix):
                    latency_ms = lat
                    target_url = url

                    if hdrs and not response_started:
                        response_headers.update(hdrs)
                        response_started = True

                    if sc is not None:
                        status_code = sc

                    if err:
                        error = err
                        if not response_started:
                            yield json.dumps({"error": err}).encode()
                        break

                    if chunk:
                        # Collect for logging
                        total_body_size += len(chunk)
                        if log_body_size < self.MAX_LOG_BODY_SIZE:
                            remaining = self.MAX_LOG_BODY_SIZE - log_body_size
                            to_store = chunk[:remaining] if len(chunk) > remaining else chunk
                            log_body_chunks.append(to_store)
                            log_body_size += len(to_store)
                        yield chunk

            except Exception as e:
                error = f"Stream error: {e}"
                logger.exception(f"Unexpected error in stream: {e}")
                if not response_started:
                    yield json.dumps({"error": error}).encode()
            finally:
                # Update log
                if log_id:
                    try:
                        elapsed = latency_ms or int((time.time() - start_time) * 1000)
                        log_body = b"".join(log_body_chunks)
                        body_parsed = self._parse_body(log_body, response_headers)
                        await self.forward_service.log_service.update_log_response(
                            log_id=log_id,
                            response_status_code=status_code or (502 if error else 200),
                            response_headers=response_headers or None,
                            response_body=body_parsed,
                            response_body_size=total_body_size,
                            latency_ms=elapsed,
                            error=error,
                        )
                    except Exception as e:
                        logger.error(f"Failed to update log: {e}")

        # Get first chunk to determine response headers
        generator = stream_and_collect()
        first_chunk = None
        try:
            first_chunk = await generator.__anext__()
        except StopAsyncIteration:
            pass
        except Exception as e:
            error = f"Failed to start stream: {e}"
            logger.exception(f"Error getting first chunk: {e}")
            return self._error_response(Response, 500, error)

        # Check for early errors
        if error and not response_started:
            return self._error_response(Response, self._error_status(error), error)

        async def wrapped():
            if first_chunk:
                yield first_chunk
            async for chunk in generator:
                yield chunk

        return StreamingResponse(
            wrapped(),
            status_code=status_code or 200,
            headers=filter_hop_by_hop_headers(response_headers, {"content-length"}),
            media_type=response_headers.get("content-type"),
        )

    async def _handle_buffered(
        self,
        request: Request,
        route: ProxyRoute,
        path_suffix: str,
        Response,
        filter_hop_by_hop_headers,
    ):
        """Handle buffered proxy request."""
        import time

        target_url = route.target_urls[0] if route.target_urls else ""
        start_time = time.time()

        # Create pending log
        request_body = await request.body()
        log_id: str | None = None
        try:
            log_id = await self.forward_service.create_pending_log(
                route=route,
                request=request,
                request_body=request_body,
                target_url=target_url,
            )
        except Exception as e:
            logger.error(f"Failed to create pending log: {e}")

        try:
            response, latency_ms, error, used_url = await self.forward_service.forward_request(
                request, route, path_suffix
            )

            if error:
                await self._update_log(log_id, None, 0, latency_ms, error, start_time)
                return self._error_response(Response, self._error_status(error), error)

            if response is None:
                error = "No response from upstream"
                await self._update_log(log_id, None, 0, latency_ms, error, start_time)
                return self._error_response(Response, 502, error)

            # Update log
            response_body = response.content
            await self._update_log(
                log_id,
                dict(response.headers),
                response.status_code,
                latency_ms,
                None,
                start_time,
                response_body,
            )

            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=filter_hop_by_hop_headers(dict(response.headers)),
                media_type=response.headers.get("content-type"),
            )

        except Exception as e:
            error = f"Request error: {e}"
            logger.exception(f"Unexpected error in buffered request: {e}")
            elapsed = int((time.time() - start_time) * 1000)
            await self._update_log(log_id, None, 0, elapsed, error, start_time)
            return self._error_response(Response, 500, error)

    async def _update_log(
        self,
        log_id: str | None,
        headers: dict | None,
        status_code: int,
        latency_ms: int,
        error: str | None,
        start_time: float,
        body: bytes = b"",
    ):
        """Update log entry with response data."""
        if not log_id:
            return
        import time

        try:
            elapsed = latency_ms or int((time.time() - start_time) * 1000)
            await self.forward_service.log_service.update_log_response(
                log_id=log_id,
                response_status_code=status_code or (502 if error else 200),
                response_headers=headers,
                response_body=self._parse_body(body, headers) if body else None,
                response_body_size=len(body),
                latency_ms=elapsed,
                error=error,
            )
        except Exception as e:
            logger.error(f"Failed to update log: {e}")

    @staticmethod
    def _parse_body(body: bytes, headers: dict | None):
        """Parse response body based on content type."""
        import json

        if not body:
            return None
        try:
            content_type = headers.get("content-type", "") if headers else ""
            if "application/json" in content_type:
                return json.loads(body.decode("utf-8"))
            return body.decode("utf-8", errors="replace")
        except Exception:
            return body.decode("utf-8", errors="replace")

    @staticmethod
    def _error_response(Response, status_code: int, message: str):
        """Create JSON error response."""
        import json

        return Response(
            content=json.dumps({"code": status_code, "msg": message, "data": None}),
            status_code=status_code,
            media_type="application/json",
        )

    @staticmethod
    def _error_status(error: str) -> int:
        """Determine HTTP status code from error message."""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return 504
        if "connection" in error_lower:
            return 502
        return 500
