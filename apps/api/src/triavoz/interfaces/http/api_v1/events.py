from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from triavoz.config import get_settings
from triavoz.infrastructure.events.redis_events import RedisEventBus
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.deps import current_principal, get_event_stream

router = APIRouter(prefix="/events", tags=["events"])

# Process-local stream caps. They stop one authenticated account (or one tenant) from holding an
# unbounded number of Redis pub/sub connections; a multi-replica deployment should also cap at the
# ingress (documented residual risk in docs/security/AUDIT.md).
_SSE_LOCK = asyncio.Lock()
_SSE_PER_USER: dict[str, int] = {}
_SSE_PER_CLINIC: dict[str, int] = {}


async def _acquire_stream_slot(user_id: UUID, clinic_id: UUID) -> None:
    settings = get_settings()
    user_key, clinic_key = str(user_id), str(clinic_id)
    async with _SSE_LOCK:
        if _SSE_PER_USER.get(user_key, 0) >= settings.sse_max_connections_per_user:
            raise HTTPException(
                status_code=429, detail="sse_connection_limit", headers={"Retry-After": "5"}
            )
        if _SSE_PER_CLINIC.get(clinic_key, 0) >= settings.sse_max_connections_per_clinic:
            raise HTTPException(
                status_code=429, detail="sse_clinic_limit", headers={"Retry-After": "5"}
            )
        _SSE_PER_USER[user_key] = _SSE_PER_USER.get(user_key, 0) + 1
        _SSE_PER_CLINIC[clinic_key] = _SSE_PER_CLINIC.get(clinic_key, 0) + 1


async def _release_stream_slot(user_id: UUID, clinic_id: UUID) -> None:
    user_key, clinic_key = str(user_id), str(clinic_id)
    async with _SSE_LOCK:
        if _SSE_PER_USER.get(user_key, 0) <= 1:
            _SSE_PER_USER.pop(user_key, None)
        else:
            _SSE_PER_USER[user_key] -= 1
        if _SSE_PER_CLINIC.get(clinic_key, 0) <= 1:
            _SSE_PER_CLINIC.pop(clinic_key, None)
        else:
            _SSE_PER_CLINIC[clinic_key] -= 1


@router.get("/stream")
async def stream_events(
    request: Request,
    principal: Principal = Depends(current_principal),
    bus: RedisEventBus = Depends(get_event_stream),
) -> StreamingResponse:
    await _acquire_stream_slot(principal.user_id, principal.clinic_id)

    async def generator() -> AsyncIterator[str]:
        try:
            yield "retry: 5000\n\n"
            async for frame in bus.subscribe(principal.clinic_id):
                if await request.is_disconnected():
                    break
                yield frame
        finally:
            await _release_stream_slot(principal.user_id, principal.clinic_id)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
