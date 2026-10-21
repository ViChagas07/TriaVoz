from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, computed_field, field_validator

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
    suspicion_flags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def needs_review(self) -> bool:
        """Dashboard badge data: a human should look at spam or flagged requests."""
        return self.status == "spam" or bool(self.suspicion_flags)


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
    suspicion_flags: list[str] = Field(default_factory=list)
    needs_review: bool = False
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
    call_id: UUID | None = None
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


class BusinessHours(BaseModel):
    days: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    start: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    end: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")

    @field_validator("days")
    @classmethod
    def _valid_days(cls, value: list[int]) -> list[int]:
        if not value or any(day < 1 or day > 7 for day in value):
            raise ValueError("days must contain ISO weekdays 1..7")
        return sorted(set(value))


class ClinicSettingsOut(BaseModel):
    name: str
    slug: str
    timezone: str
    business_hours: BusinessHours | None
    max_call_seconds: int
    max_concurrent_calls: int
    daily_minute_budget: int
    daily_cost_budget_cents: int
    kill_switch: bool
    hidden_caller_policy: str


class ClinicSettingsIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=80)
    business_hours: BusinessHours | None = None
    max_call_seconds: int = Field(ge=30, le=3600)
    max_concurrent_calls: int = Field(ge=1, le=100)
    daily_minute_budget: int = Field(ge=0, le=100_000)
    daily_cost_budget_cents: int = Field(ge=0, le=10_000_000)
    kill_switch: bool
    hidden_caller_policy: Literal["allow", "reject"] = "allow"

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(value)
        except (KeyError, ValueError) as exc:
            raise ValueError("unknown IANA timezone") from exc
        return value


class ServiceOut(BaseModel):
    id: UUID
    name: str
    duration_min: int
    price_cents: int
    is_active: bool


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_min: int = Field(ge=1, le=480)
    price_cents: int = Field(ge=0, le=10_000_000)


class ServicePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    duration_min: int | None = Field(default=None, ge=1, le=480)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    is_active: bool | None = None


class ProfessionalOut(BaseModel):
    id: UUID
    name: str
    specialty: str | None
    is_active: bool
    service_ids: list[UUID] = Field(default_factory=list)


class ProfessionalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    specialty: str | None = Field(default=None, max_length=120)
    service_ids: list[UUID] = Field(default_factory=list)


class ProfessionalPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    specialty: str | None = Field(default=None, max_length=120)
    service_ids: list[UUID] | None = None
    is_active: bool | None = None


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
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class MarkSpamIn(BaseModel):
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


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
    # The caller can declare an emergency before the room exists. This only routes to the SAMU
    # message/handoff; it never bypasses a limit to spend credits.
    emergency_hint: bool = False
    turnstile_token: str | None = Field(default=None, max_length=4096)


class VoiceSessionOut(BaseModel):
    call_id: str | None = None
    room_name: str | None = None
    token: str | None = None
    url: str | None = None
    mode: Literal["session", "fallback", "emergency"] = "session"
    reason: str | None = None
    message: str | None = None
    handoff: bool = False
    max_call_seconds: int | None = None
    timezone: str | None = None
