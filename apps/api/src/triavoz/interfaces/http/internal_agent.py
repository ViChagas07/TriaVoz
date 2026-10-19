"""Internal API used ONLY by the voice worker (HMAC-signed). Never exposed to browsers.

Trust model: the worker learns `clinic_id` from LiveKit room metadata written by THIS API when it
creates the session (server-side), so neither the browser nor the LLM can choose the tenant. The
caller's phone used for ownership checks comes from the stored call record, never from tool args.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from triavoz.application.scheduling.use_cases import (
    BookAppointment,
    CancelAppointment,
    ListAvailableSlots,
    ListMyAppointments,
    ListServices,
    RescheduleAppointment,
)
from triavoz.config import get_settings
from triavoz.infrastructure.db.calls_repo import PgCallRepository
from triavoz.infrastructure.db.scheduling_repo import PgSchedulingRepository
from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.security import hmac_auth
from triavoz.shared_kernel.errors import (
    DomainError,
    InvalidRequest,
    NotFound,
    SlotTaken,
    SlotUnavailable,
)


async def verify_internal_signature(request: Request) -> None:
    s = get_settings()
    body = await request.body()
    ok = hmac_auth.verify(
        s.internal_hmac_secret.get_secret_value(),
        request.headers.get(hmac_auth.TIMESTAMP_HEADER),
        request.headers.get(hmac_auth.SIGNATURE_HEADER),
        body,
        s.internal_hmac_tolerance_seconds,
    )
    if not ok:
        raise HTTPException(status_code=401, detail="invalid signature")


router = APIRouter(
    prefix="/internal/agent",
    tags=["internal-agent"],
    dependencies=[Depends(verify_internal_signature)],
)


def _http(exc: DomainError) -> HTTPException:
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
    professional_id: UUID | None = None


class BookIn(Ctx):
    service_id: UUID
    professional_id: UUID
    starts_at: datetime
    customer_name: str = Field(min_length=1, max_length=120)


class AppointmentIn(Ctx):
    appointment_id: UUID


class RescheduleIn(AppointmentIn):
    new_starts_at: datetime


class TurnsIn(Ctx):
    turns: list[dict[str, Any]] = Field(max_length=200)


class EndIn(Ctx):
    status: str = Field(pattern="^(completed|failed|rejected|transferred)$")
    end_reason: str | None = Field(default=None, max_length=200)
    duration_seconds: int | None = Field(default=None, ge=0, le=86_400)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: dict[str, Any] = Field(default_factory=dict)
    cost_cents: float = Field(default=0, ge=0)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise HTTPException(status_code=422, detail="datetime must include a timezone offset")
    return dt


@router.post("/calls/start")
async def start_call(body: StartCall) -> dict[str, str]:
    async with tenant_session(body.clinic_id) as session:
        call_id = await PgCallRepository(session).start(
            clinic_id=body.clinic_id,
            channel=body.channel,
            room_name=body.room_name,
            caller_number=body.caller_number,
        )
    return {"call_id": str(call_id)}


@router.post("/tools/list-services")
async def list_services(body: Ctx) -> list[dict[str, Any]]:
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


@router.post("/tools/list-slots")
async def list_slots(body: SlotsIn) -> list[dict[str, Any]]:
    try:
        async with tenant_session(body.clinic_id) as session:
            slots = await ListAvailableSlots(PgSchedulingRepository(session)).execute(
                clinic_id=body.clinic_id,
                service_id=body.service_id,
                day=body.date,
                now=datetime.now(UTC),
                professional_id=body.professional_id,
            )
    except DomainError as exc:
        raise _http(exc) from exc
    return [
        {
            "professional_id": str(s.professional_id),
            "professional_name": s.professional_name,
            "starts_at": s.starts_at.isoformat(),
        }
        for s in slots
    ]


@router.post("/tools/book")
async def book(body: BookIn) -> dict[str, str]:
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
        raise _http(exc) from exc
    return {"appointment_id": str(appointment_id), "status": "booked"}


@router.post("/tools/my-appointments")
async def my_appointments(body: Ctx) -> list[dict[str, str]]:
    try:
        async with tenant_session(body.clinic_id) as session:
            phone = await PgCallRepository(session).caller_number(body.call_id)
            items = await ListMyAppointments(PgSchedulingRepository(session)).execute(
                caller_phone=phone, now=datetime.now(UTC)
            )
    except DomainError as exc:
        raise _http(exc) from exc
    return [
        {
            "appointment_id": str(i.id),
            "service": i.service_name,
            "professional": i.professional_name,
            "starts_at": i.starts_at.isoformat(),
        }
        for i in items
    ]


@router.post("/tools/cancel")
async def cancel(body: AppointmentIn) -> dict[str, str]:
    try:
        async with tenant_session(body.clinic_id) as session:
            phone = await PgCallRepository(session).caller_number(body.call_id)
            await CancelAppointment(PgSchedulingRepository(session)).execute(
                appointment_id=body.appointment_id, caller_phone=phone, now=datetime.now(UTC)
            )
    except DomainError as exc:
        raise _http(exc) from exc
    return {"status": "canceled"}


@router.post("/tools/reschedule")
async def reschedule(body: RescheduleIn) -> dict[str, str]:
    new_start = _aware(body.new_starts_at)
    try:
        async with tenant_session(body.clinic_id) as session:
            phone = await PgCallRepository(session).caller_number(body.call_id)
            await RescheduleAppointment(PgSchedulingRepository(session)).execute(
                clinic_id=body.clinic_id,
                appointment_id=body.appointment_id,
                caller_phone=phone,
                new_starts_at=new_start,
                now=datetime.now(UTC),
            )
    except DomainError as exc:
        raise _http(exc) from exc
    return {"status": "rescheduled"}


@router.post("/calls/turns")
async def add_turns(body: TurnsIn) -> dict[str, int]:
    turns = []
    for t in body.turns:
        if t.get("speaker") not in {"patient", "agent", "tool", "system"} or "seq" not in t:
            raise HTTPException(status_code=422, detail="invalid turn")
        payload = t.get("tool_payload")
        turns.append(
            {**t, "tool_payload_json": json.dumps(payload) if payload is not None else None}
        )
    async with tenant_session(body.clinic_id) as session:
        await PgCallRepository(session).add_turns(body.clinic_id, body.call_id, turns)
    return {"stored": len(turns)}


@router.post("/calls/end")
async def end_call(body: EndIn) -> dict[str, str]:
    async with tenant_session(body.clinic_id) as session:
        await PgCallRepository(session).end(
            body.call_id,
            status=body.status,
            end_reason=body.end_reason,
            duration_seconds=body.duration_seconds,
            usage_json=json.dumps(body.usage),
            latency_json=json.dumps(body.latency_ms),
            cost_cents=body.cost_cents,
        )
    return {"status": "ok"}
