from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from triavoz.application.abuse.alerts import AlertService
from triavoz.application.abuse.policy import GateAction
from triavoz.application.abuse.ports import GateStore
from triavoz.application.auth.ports import ClinicResolver
from triavoz.application.events import EventPublisher
from triavoz.application.voice.ports import VoiceRoomService
from triavoz.application.voice.service import StartVoiceSession, VoiceSessionOutcome
from triavoz.config import get_settings
from triavoz.infrastructure.db.abuse_repo import PgAbuseRepository
from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.db.voice_repo import PgVoiceSessionRepository
from triavoz.infrastructure.security.turnstile import TurnstileVerifier
from triavoz.interfaces.http.api_v1.schemas import VoiceSessionIn, VoiceSessionOut
from triavoz.interfaces.http.deps import (
    client_ip,
    get_alert_service,
    get_clinic_resolver,
    get_demo_clinic_slug,
    get_events_dep,
    get_gate_store_dep,
    get_turnstile_verifier,
    get_voice_room_service,
)
from triavoz.shared_kernel.errors import Forbidden, NotFound

router = APIRouter(prefix="/voice", tags=["voice"])


def _fallback_response(outcome: VoiceSessionOutcome) -> VoiceSessionOut:
    decision = outcome.decision
    return VoiceSessionOut(
        mode="emergency" if decision.action is GateAction.EMERGENCY else "fallback",
        reason=decision.reason.value,
        message=decision.message,
        handoff=decision.handoff,
    )


@router.post("/session", response_model=VoiceSessionOut)
async def create_voice_session(
    body: VoiceSessionIn,
    request: Request,
    resolver: ClinicResolver = Depends(get_clinic_resolver),
    demo_slug: str = Depends(get_demo_clinic_slug),
    rooms: VoiceRoomService = Depends(get_voice_room_service),
    store: GateStore = Depends(get_gate_store_dep),
    alerts: AlertService = Depends(get_alert_service),
    turnstile: TurnstileVerifier = Depends(get_turnstile_verifier),
    events: EventPublisher = Depends(get_events_dep),
) -> VoiceSessionOut:
    s = get_settings()
    ip = client_ip(request)
    if turnstile.enabled and not await turnstile.verify(body.turnstile_token, ip):
        raise Forbidden("turnstile_failed")
    if body.clinic_code and body.clinic_code != demo_slug:
        raise NotFound("demo_clinic")

    clinic_id = await resolver.by_slug(demo_slug)
    if clinic_id is None:
        raise NotFound("demo_clinic")
    async with tenant_session(clinic_id) as session:
        use_case = StartVoiceSession(
            PgVoiceSessionRepository(session),
            rooms,
            PgAbuseRepository(session),
            store,
            s,
            alert_service=alerts,
        )
        outcome = await use_case.execute(
            caller_number=body.caller_number,
            client_ip=ip,
            ttl_seconds=s.livekit_token_ttl_seconds,
            channel="web",
            emergency=body.emergency_hint,
            demo_caps=True,
        )
    if outcome.session is None:
        return _fallback_response(outcome)
    result = outcome.session
    await events.publish(clinic_id, "call.started", {"call_id": result.call_id})
    return VoiceSessionOut(
        call_id=result.call_id,
        room_name=result.room_name,
        token=result.token,
        url=result.url,
        mode="session",
        reason=outcome.decision.reason.value,
    )
