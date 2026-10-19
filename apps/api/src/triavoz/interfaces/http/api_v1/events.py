from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from triavoz.infrastructure.events.redis_events import RedisEventBus
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.deps import current_principal, get_event_stream

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def stream_events(
    request: Request,
    principal: Principal = Depends(current_principal),
    bus: RedisEventBus = Depends(get_event_stream),
) -> StreamingResponse:
    async def generator() -> AsyncIterator[str]:
        yield "retry: 5000\n\n"
        async for frame in bus.subscribe(principal.clinic_id):
            if await request.is_disconnected():
                break
            yield frame

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
