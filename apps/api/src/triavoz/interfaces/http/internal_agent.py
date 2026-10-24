"""Internal API used ONLY by the voice worker (HMAC-signed). Never exposed to browsers.

Trust model: the worker learns `clinic_id` from LiveKit room metadata written by THIS API when it
creates the session (server-side), so neither the browser nor the LLM can choose the tenant. The
caller's phone used for ownership checks comes from the stored call record, never from tool args.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from triavoz.application.abuse.alerts import AlertService
from triavoz.application.abuse.gatekeeper import gatekeeper_for, rate_limits_from_settings
from triavoz.application.abuse.policy import clinic_policy_from_context
from triavoz.application.abuse.ports import GateStore
from triavoz.application.abuse.scoring import score_call
from triavoz.application.events import EventPublisher
from triavoz.application.scheduling.use_cases import (
    BookAppointment,
    CancelAppointment,
    ListAvailableSlots,
    ListMyAppointments,
    ListServices,
    RescheduleAppointment,
)
from triavoz.application.voice.ports import VoiceRoomService
from triavoz.application.voice.service import StartVoiceSession
from triavoz.config import get_settings
from triavoz.infrastructure.db.abuse_repo import PgAbuseRepository
from triavoz.infrastructure.db.calls_repo import PgCallRepository
from triavoz.infrastructure.db.clinic_resolver import RoutingClinicResolver
from triavoz.infrastructure.db.scheduling_repo import PgSchedulingRepository
from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.db.staff_repo import PgStaffRepository
from triavoz.infrastructure.db.voice_repo import PgVoiceSessionRepository
from triavoz.infrastructure.events.redis_events import get_event_bus
from triavoz.infrastructure.idempotency import IdempotencyStore, get_idempotency_store
from triavoz.infrastructure.rate_limit.limiter import get_limiter
from triavoz.infrastructure.security import hmac_auth
from triavoz.infrastructure.security.replay_guard import get_replay_guard
from triavoz.interfaces.http.deps import (
    get_alert_service,
    get_events_dep,
    get_gate_store_dep,
    get_voice_room_service,
)
from triavoz.observability.metrics import (
    observe_call_ended,
    observe_call_started,
    observe_tool_call,
    observe_tool_error,
)
from triavoz.shared_kernel.context import bind_log_ids
from triavoz.shared_kernel.errors import (
    DomainError,
    InvalidRequest,
    NotFound,
    SlotTaken,
    SlotUnavailable,
)


async def guard_internal_request(request: Request) -> None:
    """Network allow-list (optional) + a cheap bucket before the HMAC/body work.

    The HMAC is the authentication boundary; this is defence-in-depth against scanning/flooding
    of the internal surface if it is ever accidentally exposed by a proxy.
    """
    s = get_settings()
    host = request.client.host if request.client else "unknown"
    if s.internal_allowed_cidrs:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            raise HTTPException(status_code=403, detail="internal_forbidden") from None
        if not any(
            address in ipaddress.ip_network(network, strict=False)
            for network in s.internal_allowed_cidrs
        ):
            raise HTTPException(status_code=403, detail="internal_forbidden")
    allowed = await get_limiter().allow(
        f"triavoz:internal:ip:{host}",
        s.internal_rate_capacity,
        s.internal_rate_refill_per_second,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited")


async def verify_internal_signature(request: Request) -> None:
    s = get_settings()
    body = await request.body()
    nonce = request.headers.get(hmac_auth.NONCE_HEADER)
    signature = request.headers.get(hmac_auth.SIGNATURE_HEADER)
    secrets = [s.internal_hmac_secret.get_secret_value()]
    if s.internal_hmac_secret_previous is not None:
        secrets.append(s.internal_hmac_secret_previous.get_secret_value())
    ok = hmac_auth.verify_any(
        secrets,
        request.headers.get(hmac_auth.TIMESTAMP_HEADER),
        signature,
        body,
        s.internal_hmac_tolerance_seconds,
        nonce_header=nonce,
    )
    if not ok or not nonce or not signature:
        raise HTTPException(status_code=401, detail="invalid_signature")
    # The nonce is signed and single-use: a captured request cannot be replayed inside the window.
    ttl = max(2, s.internal_hmac_tolerance_seconds * 2)
    if not await get_replay_guard().claim(hmac_auth.replay_key(nonce, signature), ttl):
        raise HTTPException(status_code=401, detail="replayed_request")


async def bind_internal_log_context(request: Request) -> None:
    """Put the server-side identifiers on the request log without trusting anything for authz."""
    try:
        payload = json.loads(await request.body() or b"{}")
    except (TypeError, ValueError):
        return
    if isinstance(payload, dict):
        bind_log_ids(clinic_id=payload.get("clinic_id"), call_id=payload.get("call_id"))


router = APIRouter(
    prefix="/internal/agent",
    tags=["internal-agent"],
    dependencies=[
        Depends(guard_internal_request),
        Depends(verify_internal_signature),
        Depends(bind_internal_log_context),
    ],
)


def _http(exc: DomainError, tool: str) -> HTTPException:
    observe_tool_error(tool, exc.code)
    status = {
        NotFound: 404,
        SlotTaken: 409,
        SlotUnavailable: 409,
        InvalidRequest: 422,
    }.get(type(exc), 400)
    return HTTPException(status_code=status, detail=exc.code)


class Ctx(BaseModel):
    clinic_id: UUID
    call_id: UUID


class StartCall(BaseModel):
    clinic_id: UUID
    channel: str = Field(pattern="^(web|phone)$")
    room_name: str | None = Field(default=None, max_length=200)
    caller_number: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")


class SlotsIn(Ctx):
    service_id: UUID
    date: date
    # ID preferred; a name is accepted because the LLM may repeat the professional it heard.
    professional_id: str | None = Field(default=None, max_length=120)


class BookIn(Ctx):
    service_id: UUID
    professional_id: UUID
    starts_at: datetime
    customer_name: str = Field(min_length=1, max_length=120)


class AppointmentIn(Ctx):
    appointment_id: UUID


class RescheduleIn(AppointmentIn):
    new_starts_at: datetime


class ServiceRequestIn(Ctx):
    type: Literal["appointment", "exam_pickup", "message", "callback", "other"]
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    patient_name: str | None = Field(default=None, max_length=120)
    requested_date: date | None = None
    due_date: date | None = None


class TurnIn(BaseModel):
    # The worker is trusted, but the payload is still bounded: an oversized or malformed turn must
    # not reach the DB or blow up a request log. Unknown keys are ignored for forward compatibility.
    model_config = ConfigDict(extra="ignore")

    seq: int = Field(ge=0, le=1_000_000)
    speaker: Literal["patient", "agent", "tool", "system"]
    content: str = Field(default="", max_length=8000)
    tool_name: str | None = Field(default=None, max_length=120)
    tool_payload: dict[str, Any] | None = None
    started_at: datetime | None = None
    stt_confidence: float | None = Field(default=None, ge=0, le=1)


class TurnsIn(Ctx):
    turns: list[TurnIn] = Field(max_length=200)


class EndIn(Ctx):
    status: str = Field(pattern="^(completed|failed|rejected|transferred)$")
    end_reason: str | None = Field(default=None, max_length=200)
    duration_seconds: int | None = Field(default=None, ge=0, le=86_400)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: dict[str, Any] = Field(default_factory=dict)
    cost_cents: float = Field(default=0, ge=0)
    handoff_requested: bool = False
    handoff_completed: bool = False
    abusive_language_detected: bool = False


class TelephonyIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    to: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    from_number: str | None = Field(default=None, alias="from", max_length=32)
    emergency: bool = False


# Response models are part of the worker/API contract. `tests/contracts` snapshots them so a
# rename or a changed field type cannot silently drift away from the worker's expectations.
class StartCallOut(BaseModel):
    call_id: str


class ServiceOut(BaseModel):
    id: str
    name: str
    duration_min: int
    price_cents: int


class SlotOut(BaseModel):
    professional_id: str
    professional_name: str
    starts_at: str


class BookOut(BaseModel):
    appointment_id: str
    status: Literal["booked"]


class MyAppointmentOut(BaseModel):
    appointment_id: str
    service: str
    professional: str
    starts_at: str


class StatusOut(BaseModel):
    status: str


class RequestOut(BaseModel):
    request_id: str
    status: Literal["pending"]


class TurnsStoredOut(BaseModel):
    stored: int


class TelephonyOut(BaseModel):
    mode: Literal["session", "fallback", "emergency"]
    reason: str
    message: str | None
    handoff: bool
    call_id: str | None
    room_name: str | None
    token: str | None
    url: str | None


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise HTTPException(status_code=422, detail="datetime must include a timezone offset")
    return dt


def _idem_key(
    *, clinic_id: UUID, call_id: UUID, endpoint: str, header: str | None, body: dict[str, Any]
) -> tuple[str, str] | None:
    if not header:
        return None
    if len(header) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", header):
        raise HTTPException(status_code=422, detail="invalid_idempotency_key")
    body_hash = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    return f"{clinic_id}:{call_id}:{endpoint}:{header}", body_hash


@router.post("/calls/start", response_model=StartCallOut)
async def start_call(
    body: StartCall, events: EventPublisher = Depends(get_events_dep)
) -> dict[str, str]:
    async with tenant_session(body.clinic_id) as session:
        call_id = await PgCallRepository(session).start(
            clinic_id=body.clinic_id,
            channel=body.channel,
            room_name=body.room_name,
            caller_number=body.caller_number,
        )
    observe_call_started(channel=body.channel)
    await events.publish(body.clinic_id, "call.started", {"call_id": str(call_id)})
    return {"call_id": str(call_id)}


@router.post("/tools/list-services", response_model=list[ServiceOut])
async def list_services(body: Ctx) -> list[dict[str, Any]]:
    observe_tool_call("list_services")
    async with tenant_session(body.clinic_id) as session:
        items = await ListServices(PgSchedulingRepository(session)).execute()
    return [
        {
            "id": str(i.id),
            "name": i.name,
            "duration_min": i.duration_min,
            "price_cents": i.price_cents,
        }
        for i in items
    ]


@router.post("/tools/list-slots", response_model=list[SlotOut])
async def list_slots(body: SlotsIn) -> list[dict[str, Any]]:
    observe_tool_call("list_available_slots")
    try:
        async with tenant_session(body.clinic_id) as session:
            repo = PgSchedulingRepository(session)
            zone = ZoneInfo(await repo.clinic_timezone(body.clinic_id))
            professional_id = body.professional_id
            if professional_id:
                try:
                    UUID(professional_id)
                except ValueError:
                    # The LLM may pass the name it just heard; resolve it server-side.
                    resolved = await repo.find_professional_by_name(professional_id)
                    if resolved is None:
                        raise InvalidRequest("professional_not_found") from None
                    professional_id = str(resolved)
            slots = await ListAvailableSlots(repo).execute(
                clinic_id=body.clinic_id,
                service_id=body.service_id,
                day=body.date,
                now=datetime.now(UTC),
                professional_id=UUID(professional_id) if professional_id else None,
            )
    except DomainError as exc:
        raise _http(exc, "list_available_slots") from exc
    return [
        {
            "professional_id": str(s.professional_id),
            "professional_name": s.professional_name,
            # Always speak/localize in the clinic timezone; timestamptz from PostgreSQL is UTC.
            "starts_at": s.starts_at.astimezone(zone).isoformat(),
        }
        for s in slots
    ]


@router.post("/tools/book", response_model=BookOut)
async def book(
    body: BookIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: IdempotencyStore = Depends(get_idempotency_store),
    events: EventPublisher = Depends(get_events_dep),
) -> dict[str, str]:
    observe_tool_call("book_appointment")
    key = _idem_key(
        clinic_id=body.clinic_id,
        call_id=body.call_id,
        endpoint="book",
        header=idempotency_key,
        body=body.model_dump(mode="json"),
    )
    if key is not None:
        cached = await store.get(key[0])
        if cached is not None:
            if cached.get("request_hash") != key[1]:
                raise HTTPException(status_code=409, detail="idempotency_conflict")
            return dict(cached["response"])
    starts_at = _aware(body.starts_at)
    try:
        async with tenant_session(body.clinic_id) as session:
            phone = await PgCallRepository(session).caller_number(body.call_id)
            appointment_id = await BookAppointment(PgSchedulingRepository(session)).execute(
                clinic_id=body.clinic_id,
                call_id=body.call_id,
                service_id=body.service_id,
                professional_id=body.professional_id,
                starts_at=starts_at,
                customer_name=body.customer_name,
                caller_phone=phone,
                now=datetime.now(UTC),
            )
    except DomainError as exc:
        raise _http(exc, "book_appointment") from exc
    result = {"appointment_id": str(appointment_id), "status": "booked"}
    if key is not None:
        await store.set(key[0], {"request_hash": key[1], "response": result})
    await events.publish(
        body.clinic_id,
        "appointment.created",
        {"appointment_id": str(appointment_id), "call_id": str(body.call_id)},
    )
    return result


@router.post("/tools/my-appointments", response_model=list[MyAppointmentOut])
async def my_appointments(body: Ctx) -> list[dict[str, str]]:
    observe_tool_call("list_my_appointments")
    try:
        async with tenant_session(body.clinic_id) as session:
            repo = PgSchedulingRepository(session)
            zone = ZoneInfo(await repo.clinic_timezone(body.clinic_id))
            phone, verified, identity = await PgCallRepository(session).caller_ownership(
                body.call_id
            )
            items = await ListMyAppointments(repo).execute(
                caller_phone=phone,
                now=datetime.now(UTC),
                phone_verified=verified,
                identity_hash=identity,
            )
    except DomainError as exc:
        raise _http(exc, "list_my_appointments") from exc
    return [
        {
            "appointment_id": str(i.id),
            "service": i.service_name,
            "professional": i.professional_name,
            "starts_at": i.starts_at.astimezone(zone).isoformat(),
        }
        for i in items
    ]


@router.post("/tools/cancel", response_model=StatusOut)
async def cancel(
    body: AppointmentIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: IdempotencyStore = Depends(get_idempotency_store),
    events: EventPublisher = Depends(get_events_dep),
) -> dict[str, str]:
    observe_tool_call("cancel_appointment")
    key = _idem_key(
        clinic_id=body.clinic_id,
        call_id=body.call_id,
        endpoint="cancel",
        header=idempotency_key,
        body=body.model_dump(mode="json"),
    )
    if key is not None:
        cached = await store.get(key[0])
        if cached is not None:
            if cached.get("request_hash") != key[1]:
                raise HTTPException(status_code=409, detail="idempotency_conflict")
            return dict(cached["response"])
    try:
        async with tenant_session(body.clinic_id) as session:
            phone, verified, identity = await PgCallRepository(session).caller_ownership(
                body.call_id
            )
            await CancelAppointment(PgSchedulingRepository(session)).execute(
                appointment_id=body.appointment_id,
                caller_phone=phone,
                now=datetime.now(UTC),
                phone_verified=verified,
                identity_hash=identity,
            )
    except DomainError as exc:
        raise _http(exc, "cancel_appointment") from exc
    result = {"status": "canceled"}
    if key is not None:
        await store.set(key[0], {"request_hash": key[1], "response": result})
    await events.publish(
        body.clinic_id,
        "appointment.canceled",
        {"appointment_id": str(body.appointment_id), "call_id": str(body.call_id)},
    )
    return result


@router.post("/tools/reschedule", response_model=StatusOut)
async def reschedule(
    body: RescheduleIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: IdempotencyStore = Depends(get_idempotency_store),
    events: EventPublisher = Depends(get_events_dep),
) -> dict[str, str]:
    observe_tool_call("reschedule_appointment")
    key = _idem_key(
        clinic_id=body.clinic_id,
        call_id=body.call_id,
        endpoint="reschedule",
        header=idempotency_key,
        body=body.model_dump(mode="json"),
    )
    if key is not None:
        cached = await store.get(key[0])
        if cached is not None:
            if cached.get("request_hash") != key[1]:
                raise HTTPException(status_code=409, detail="idempotency_conflict")
            return dict(cached["response"])
    new_start = _aware(body.new_starts_at)
    try:
        async with tenant_session(body.clinic_id) as session:
            phone, verified, identity = await PgCallRepository(session).caller_ownership(
                body.call_id
            )
            await RescheduleAppointment(PgSchedulingRepository(session)).execute(
                clinic_id=body.clinic_id,
                appointment_id=body.appointment_id,
                caller_phone=phone,
                new_starts_at=new_start,
                now=datetime.now(UTC),
                phone_verified=verified,
                identity_hash=identity,
            )
    except DomainError as exc:
        raise _http(exc, "reschedule_appointment") from exc
    result = {"status": "rescheduled"}
    if key is not None:
        await store.set(key[0], {"request_hash": key[1], "response": result})
    await events.publish(
        body.clinic_id,
        "appointment.moved",
        {"appointment_id": str(body.appointment_id), "call_id": str(body.call_id)},
    )
    return result


@router.post("/telephony/incoming", response_model=TelephonyOut)
async def telephony_incoming(
    body: TelephonyIn,
    request: Request,
    store: GateStore = Depends(get_gate_store_dep),
    alerts: AlertService = Depends(get_alert_service),
    rooms: VoiceRoomService = Depends(get_voice_room_service),
) -> dict[str, str | bool | None]:
    """Optional telephony webhook: resolve the dialed number, run the same gatekeeper.

    A real provider adapter (Twilio signature validation + TwiML) stays behind this endpoint; the
    internal HMAC keeps it closed until that adapter exists. Emergencies get SAMU guidance even
    when the number is blocked or the breaker is open.
    """
    clinic_id = await RoutingClinicResolver().by_phone(body.to)
    if clinic_id is None:
        raise HTTPException(status_code=404, detail="unknown_number")
    ip = request.client.host if request.client else "telephony"
    s = get_settings()
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
            caller_number=body.from_number,
            client_ip=ip,
            ttl_seconds=s.livekit_token_ttl_seconds,
            channel="phone",
            emergency=body.emergency,
            demo_caps=False,
            caller_verified=bool(body.from_number),
        )
    if outcome.provider_error:
        raise HTTPException(status_code=503, detail="voice_provider_unavailable")
    decision = outcome.decision
    if outcome.session is None:
        return {
            "mode": "emergency" if decision.reason.value == "emergency" else "fallback",
            "reason": decision.reason.value,
            "message": decision.message,
            "handoff": decision.handoff,
            "call_id": None,
            "room_name": None,
            "token": None,
            "url": None,
        }
    result = outcome.session
    observe_call_started(channel="phone")
    await get_event_bus().publish(clinic_id, "call.started", {"call_id": result.call_id})
    return {
        "mode": "session",
        "reason": decision.reason.value,
        "message": None,
        "handoff": False,
        "call_id": result.call_id,
        "room_name": result.room_name,
        "token": result.token,
        "url": result.url,
    }


@router.post("/calls/turns", response_model=TurnsStoredOut)
async def add_turns(body: TurnsIn) -> dict[str, int]:
    turns = []
    for turn in body.turns:
        data = turn.model_dump()
        payload = data.pop("tool_payload")
        turns.append(
            {**data, "tool_payload_json": json.dumps(payload) if payload is not None else None}
        )
    async with tenant_session(body.clinic_id) as session:
        await PgCallRepository(session).add_turns(body.clinic_id, body.call_id, turns)
    return {"stored": len(turns)}


@router.post("/calls/end", response_model=StatusOut)
async def end_call(
    body: EndIn,
    events: EventPublisher = Depends(get_events_dep),
    store: GateStore = Depends(get_gate_store_dep),
    alerts: AlertService = Depends(get_alert_service),
) -> dict[str, str]:
    s = get_settings()
    async with tenant_session(body.clinic_id) as session:
        await PgCallRepository(session).end(
            body.call_id,
            status=body.status,
            end_reason=body.end_reason,
            duration_seconds=body.duration_seconds,
            usage_json=json.dumps(body.usage),
            latency_json=json.dumps(body.latency_ms),
            cost_cents=body.cost_cents,
            handoff_requested=body.handoff_requested,
            handoff_completed=body.handoff_completed,
        )
        abuse = PgAbuseRepository(session)
        inputs = await abuse.scoring_inputs(
            body.call_id, abusive_language=body.abusive_language_detected
        )
        if inputs is not None:
            result = score_call(inputs, review_threshold=s.abuse_review_threshold)
            await abuse.apply_call_score(
                body.call_id,
                score=result.score,
                flags=result.flags,
                needs_review=result.needs_review,
            )
        ctx = await PgVoiceSessionRepository(session).voice_context()
        if ctx is not None:
            channel = await PgCallRepository(session).channel(body.call_id)
            policy = clinic_policy_from_context(
                ctx,
                demo_hard_max_call_seconds=(
                    s.demo_hard_max_call_seconds if channel == "web" else None
                ),
                demo_daily_minute_budget=(s.demo_daily_minute_budget if channel == "web" else None),
                demo_daily_cost_budget_cents=(
                    s.demo_daily_cost_budget_cents if channel == "web" else None
                ),
            )
            gate = gatekeeper_for(
                clinic_id=ctx["clinic_id"],
                policy=policy,
                repo=abuse,
                store=store,
                rate_limits=rate_limits_from_settings(s),
                cooldown_seconds=s.cost_breaker_cooldown_seconds,
                failure_threshold=s.cost_breaker_failure_threshold,
                alerts=alerts,
            )
            await gate.release(str(body.call_id))
            await gate.on_call_ended(
                cost_cents=body.cost_cents,
                duration_seconds=body.duration_seconds or 0,
            )
    observe_call_ended(
        status=body.status,
        reason=body.end_reason,
        duration_seconds=body.duration_seconds,
        cost_cents=body.cost_cents,
        handoff_requested=body.handoff_requested,
        handoff_completed=body.handoff_completed,
        latency_ms=body.latency_ms,
    )
    await events.publish(body.clinic_id, "call.ended", {"call_id": str(body.call_id)})
    return {"status": "ok"}


@router.post("/tools/create-service-request", response_model=RequestOut)
async def create_service_request(
    body: ServiceRequestIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: IdempotencyStore = Depends(get_idempotency_store),
    events: EventPublisher = Depends(get_events_dep),
) -> dict[str, str]:
    observe_tool_call("create_service_request")
    key = _idem_key(
        clinic_id=body.clinic_id,
        call_id=body.call_id,
        endpoint="create-service-request",
        header=idempotency_key,
        body=body.model_dump(mode="json"),
    )
    if key is not None:
        cached = await store.get(key[0])
        if cached is not None:
            if cached.get("request_hash") != key[1]:
                raise HTTPException(status_code=409, detail="idempotency_conflict")
            return dict(cached["response"])
    try:
        async with tenant_session(body.clinic_id) as session:
            request_id = await PgStaffRepository(session).create_service_request(
                clinic_id=body.clinic_id,
                call_id=body.call_id,
                type_=body.type,
                title=body.title,
                description=body.description,
                patient_name=body.patient_name,
                requested_date=body.requested_date,
                due_date=body.due_date,
            )
    except DomainError as exc:
        raise _http(exc, "create_service_request") from exc
    result = {"request_id": str(request_id), "status": "pending"}
    if key is not None:
        await store.set(key[0], {"request_hash": key[1], "response": result})
    await events.publish(body.clinic_id, "request.created", {"request_id": str(request_id)})
    return result
