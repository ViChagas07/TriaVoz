from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from triavoz.application.auth.ports import ClinicResolver, RateLimiter
from triavoz.application.events import EventPublisher
from triavoz.application.voice.ports import VoiceRoomService
from triavoz.application.voice.service import StartVoiceSession
from triavoz.config import get_settings
from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.db.voice_repo import PgVoiceSessionRepository
from triavoz.interfaces.http.api_v1.schemas import VoiceSessionIn, VoiceSessionOut
from triavoz.interfaces.http.deps import (
    client_ip,
    get_clinic_resolver,
    get_demo_clinic_slug,
    get_events_dep,
    get_limiter_dep,
    get_voice_room_service,
)
from triavoz.shared_kernel.errors import NotFound, TooManyAttempts

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/session", response_model=VoiceSessionOut)
async def create_voice_session(
    body: VoiceSessionIn,
    request: Request,
    resolver: ClinicResolver = Depends(get_clinic_resolver),
    demo_slug: str = Depends(get_demo_clinic_slug),
    rooms: VoiceRoomService = Depends(get_voice_room_service),
    limiter: RateLimiter = Depends(get_limiter_dep),
    events: EventPublisher = Depends(get_events_dep),
) -> VoiceSessionOut:
    s = get_settings()
    allowed = await limiter.allow(
        f"triavoz:voice:ip:{client_ip(request)}",
        s.voice_rate_capacity,
        s.voice_rate_refill_per_second,
    )
    if not allowed:
        raise TooManyAttempts("voice")
    if body.clinic_code and body.clinic_code != demo_slug:
        raise NotFound("demo_clinic")

    clinic_id = await resolver.by_slug(demo_slug)
    if clinic_id is None:
        raise NotFound("demo_clinic")
    async with tenant_session(clinic_id) as session:
        use_case = StartVoiceSession(PgVoiceSessionRepository(session), rooms)
        result = await use_case.execute(
            caller_number=body.caller_number,
            ttl_seconds=s.livekit_token_ttl_seconds,
        )
    await events.publish(clinic_id, "call.started", {"call_id": result.call_id})
    return VoiceSessionOut(
        call_id=result.call_id,
        room_name=result.room_name,
        token=result.token,
        url=result.url,
    )
