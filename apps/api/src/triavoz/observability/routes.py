from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.limiter import get_limiter
from triavoz.observability.metrics import metrics_content_type, metrics_payload

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    """Prometheus scrape endpoint. Contains aggregate metrics only (no tenant/personal data)."""
    s = get_settings()
    host = request.client.host if request.client else "unknown"
    allowed = await get_limiter().allow(
        f"triavoz:metrics:ip:{host}",
        s.metrics_rate_capacity,
        s.metrics_rate_refill_per_second,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited")
    return Response(content=metrics_payload(), media_type=metrics_content_type())
