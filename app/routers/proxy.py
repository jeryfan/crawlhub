"""
Proxy gateway router.

Provides a catch-all endpoint that forwards requests to configured upstream targets.
"""

import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from models.engine import get_db
from services.proxy_service import ProxyGatewayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy")


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None,
)
async def proxy_gateway(
    request: Request,
    path: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Proxy gateway endpoint.

    Matches incoming requests against configured proxy routes and forwards
    them to the target URL. Supports both streaming and buffered modes.
    """
    normalized_path = "/" + path.lstrip("/")

    gateway = ProxyGatewayService(db)

    # Find matching route
    route = await gateway.match_route(normalized_path, request.method)
    if not route:
        from fastapi import Response
        import json

        return Response(
            content=json.dumps(
                {
                    "code": 404,
                    "msg": f"No proxy route found for path: {normalized_path}",
                    "data": None,
                }
            ),
            status_code=404,
            media_type="application/json",
        )

    # Calculate path suffix and execute
    path_suffix = gateway.get_path_suffix(normalized_path, route)
    streaming = getattr(route, "streaming", True)

    return await gateway.handle_request(
        request=request,
        route=route,
        path_suffix=path_suffix,
        streaming=streaming,
    )
