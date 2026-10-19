from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from triavoz.application.agent_config import AgentConfigSchema


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime | None = None


class LoginIn(BaseModel):
    clinic_code: str = Field(min_length=3, max_length=40, pattern="^[a-z0-9-]+$")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=200)


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret
    expires_in: int
    user: UserOut


class MeOut(BaseModel):
    user: UserOut
    clinic_id: UUID
    role: str


class RequestOut(BaseModel):
    id: UUID
    clinic_id: UUID
    type: str
    title: str
    description: str | None
    status: str
    priority: str
    patient_name: str | None
    patient_phone: str | None
    requested_date: date | None
    due_date: date | None
    assigned_to: UUID | None
    assigned_to_name: str | None
    call_id: UUID | None
    created_at: datetime
    updated_at: datetime


class RequestEventOut(BaseModel):
    id: UUID
    event_type: str
    note: str | None
    user_id: UUID | None
    user_name: str | None
    created_at: datetime


class RequestDetailOut(RequestOut):
    timeline: list[RequestEventOut]


class RequestListOut(BaseModel):
    items: list[RequestOut]
    next_cursor: str | None


class RequestPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: Literal["urgent", "normal", "low"] | None = None
    due_date: date | None = None


class AssignIn(BaseModel):
    user_id: UUID


class CallOut(BaseModel):
    id: UUID
    channel: str
    caller_number: str | None
    started_at: datetime
    ended_at: datetime | None
    status: str
    end_reason: str | None
    duration_seconds: int | None
    summary: str | None
    abuse_score: int
    handoff_requested: bool
    handoff_completed: bool
    cost_cents: float


class CallDetailOut(CallOut):
    room_name: str | None
    usage: dict[str, Any]
    latency_ms: dict[str, Any]


class CallListOut(BaseModel):
    items: list[CallOut]
    next_cursor: str | None


class CallTurnOut(BaseModel):
    id: UUID
    seq: int
    speaker: str
    content: str
    tool_name: str | None
    tool_payload: dict[str, Any] | None
    started_at: datetime
    stt_confidence: float | None


class CallEventOut(BaseModel):
    id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class AppointmentOut(BaseModel):
    id: UUID
    clinic_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    customer_name: str
    customer_phone: str
    service_id: UUID
    service_name: str
    professional_id: UUID
    professional_name: str
    created_via: str


class AppointmentCreate(BaseModel):
    service_id: UUID
    professional_id: UUID
    starts_at: AwareDatetime
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")


class AppointmentMove(BaseModel):
    starts_at: AwareDatetime


class AgentConfigIn(AgentConfigSchema):
    pass


class ConfigVersionOut(BaseModel):
    id: UUID
    version: int
    status: str
    config: dict[str, Any]
    created_by: UUID | None
    created_at: datetime
    published_at: datetime | None


class AgentConfigStateOut(BaseModel):
    published: ConfigVersionOut | None
    latest_draft: ConfigVersionOut | None


class TeamUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["admin", "attendant"]
    password: str = Field(min_length=10, max_length=200)


class BlockedCreate(BaseModel):
    e164: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    reason: str | None = Field(default=None, max_length=200)


class BlockedOut(BaseModel):
    id: UUID
    e164: str
    reason: str | None
    source: str
    created_at: datetime
    expires_at: datetime | None


class DashboardOut(BaseModel):
    pending_requests: int
    calls_today: int
    handoffs_today: int
    handoff_rate: float
    cost_today_cents: float
    latency_p50_ms: dict[str, float]
    latency_p95_ms: dict[str, float]


class VoiceSessionIn(BaseModel):
    caller_number: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    clinic_code: str | None = Field(default=None, max_length=40)


class VoiceSessionOut(BaseModel):
    call_id: str
    room_name: str
    token: str
    url: str
