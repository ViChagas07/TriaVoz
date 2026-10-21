from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class DailyUsage:
    seconds: float = 0.0
    cost_cents: float = 0.0


@dataclass(frozen=True)
class ScoringInputs:
    """Everything the pure scorer needs; already tenant-scoped by the repository."""

    call_id: UUID
    status: str
    duration_seconds: int
    patient_turns: int
    successful_tool_calls: int
    average_stt_confidence: float | None
    appointment_created: bool
    request_created: bool
    previous_calls_24h: int
    abusive_language: bool


class GateStore(Protocol):
    """Shared (Redis) state for limits; implementations fall back locally when Redis is down."""

    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool: ...
    async def acquire_slot(
        self, *, clinic_id: UUID, slot_id: str, limit: int, ttl_seconds: int
    ) -> bool: ...
    async def release_slot(self, *, clinic_id: UUID, slot_id: str) -> None: ...
    async def get_json(self, key: str) -> dict[str, Any] | None: ...
    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...
    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool: ...
    async def increment(self, key: str, ttl_seconds: int, amount: int = 1) -> int: ...
    async def delete(self, key: str) -> None: ...


class AbuseRepository(Protocol):
    """Tenant-bound reads/writes; every call runs inside tenant_session(clinic_id)."""

    async def is_blocked(self, e164: str) -> bool: ...
    async def daily_usage(self, *, max_call_seconds: int) -> DailyUsage: ...
    async def scoring_inputs(
        self, call_id: UUID, *, abusive_language: bool = False
    ) -> ScoringInputs | None: ...
    async def apply_call_score(
        self, call_id: UUID, *, score: int, flags: tuple[str, ...], needs_review: bool
    ) -> None:
        """Persist the score/flags and mirror the flags onto the request created by the call."""
        ...


class AlertNotifier(Protocol):
    async def notify(self, kind: str, clinic_id: UUID, payload: dict[str, Any]) -> None: ...
