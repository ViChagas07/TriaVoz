from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

from triavoz.shared_kernel.emergency import EMERGENCY_MESSAGE

__all__ = [
    "ClinicPolicy",
    "GateAction",
    "GateDecision",
    "GateReason",
    "RateLimitBudget",
    "clinic_policy_from_context",
    "is_hidden_caller",
    "within_business_hours",
]


class GateAction(StrEnum):
    ALLOW = "allow"
    FALLBACK = "fallback"
    EMERGENCY = "emergency"


class GateReason(StrEnum):
    OK = "ok"
    EMERGENCY = "emergency"
    KILL_SWITCH = "kill_switch"
    AFTER_HOURS = "after_hours"
    BLOCKED = "blocked"
    HIDDEN_NUMBER = "hidden_number"
    RATE_LIMITED = "rate_limited"
    CONCURRENCY = "concurrency"
    MINUTE_BUDGET = "minute_budget"
    COST_BUDGET = "cost_budget"
    COST_BREAKER = "cost_breaker"


HIGH_DEMAND_MESSAGE = "Estamos com alta demanda no momento. Tente novamente em alguns minutos."
AFTER_HOURS_MESSAGE = "O atendimento por voz está fora do horário de funcionamento da clínica."
BLOCKED_MESSAGE = "Não é possível iniciar uma ligação para este número."
KILL_SWITCH_MESSAGE = "O atendimento por voz está temporariamente indisponível."
HIDDEN_NUMBER_MESSAGE = "Não foi possível identificar o número de origem desta ligação."


def _with_emergency(text: str, emergency_message: str | None = None) -> str:
    return f"{text} {emergency_message or EMERGENCY_MESSAGE}"


@dataclass(frozen=True)
class ClinicPolicy:
    max_concurrent_calls: int = 3
    max_call_seconds: int = 300
    daily_minute_budget: int = 120
    daily_cost_budget_cents: int = 500
    kill_switch: bool = False
    hidden_caller_policy: str = "allow"
    business_hours: dict[str, Any] | None = None
    timezone: str = "America/Bahia"
    emergency_message: str = EMERGENCY_MESSAGE

    def emergency_text(self) -> str:
        return self.emergency_message or EMERGENCY_MESSAGE

    def fallback(
        self, reason: GateReason, *, retry_after_seconds: int | None = None
    ) -> GateDecision:
        text = {
            GateReason.KILL_SWITCH: KILL_SWITCH_MESSAGE,
            GateReason.AFTER_HOURS: AFTER_HOURS_MESSAGE,
            GateReason.BLOCKED: BLOCKED_MESSAGE,
            GateReason.HIDDEN_NUMBER: HIDDEN_NUMBER_MESSAGE,
            GateReason.RATE_LIMITED: HIGH_DEMAND_MESSAGE,
            GateReason.CONCURRENCY: HIGH_DEMAND_MESSAGE,
            GateReason.MINUTE_BUDGET: HIGH_DEMAND_MESSAGE,
            GateReason.COST_BUDGET: HIGH_DEMAND_MESSAGE,
            GateReason.COST_BREAKER: HIGH_DEMAND_MESSAGE,
        }.get(reason, HIGH_DEMAND_MESSAGE)
        return GateDecision(
            action=GateAction.FALLBACK,
            reason=reason,
            message=_with_emergency(text, self.emergency_text()),
            retry_after_seconds=retry_after_seconds,
            handoff=True,
        )

    def emergency(self) -> GateDecision:
        return GateDecision(
            action=GateAction.EMERGENCY,
            reason=GateReason.EMERGENCY,
            message=self.emergency_text(),
            handoff=True,
        )

    def allowed(self, *, breaker_probe: bool = False) -> GateDecision:
        return GateDecision(
            action=GateAction.ALLOW,
            reason=GateReason.OK,
            breaker_probe=breaker_probe,
        )


@dataclass(frozen=True)
class GateDecision:
    action: GateAction
    reason: GateReason
    message: str | None = None
    retry_after_seconds: int | None = None
    handoff: bool = False
    breaker_probe: bool = False

    @property
    def allowed(self) -> bool:
        return self.action is GateAction.ALLOW


@dataclass(frozen=True)
class RateLimitBudget:
    caller_capacity: float = 3
    caller_refill_per_second: float = 3 / 3600
    ip_capacity: float = 10
    ip_refill_per_second: float = 10 / 3600
    global_capacity: float = 60
    global_refill_per_second: float = 60 / 3600


_HIDDEN = {"", "anonymous", "unknown", "private", "restricted", "hidden", "withheld", "unavailable"}


def is_hidden_caller(number: str | None) -> bool:
    if not number:
        return True
    return number.strip().lower() in _HIDDEN


def within_business_hours(
    hours: dict[str, Any] | None, timezone: str, now: datetime | None = None
) -> bool:
    """Fail-open: missing/invalid configuration or timezone keeps voice available.

    ``hours`` shape: {"days":[1..7], "start":"HH:MM", "end":"HH:MM"} (ISO weekdays).
    An ``end`` earlier than ``start`` means the window crosses midnight.
    """
    if not hours:
        return True
    try:
        days = {int(day) for day in hours.get("days", list(range(1, 8)))}
        start_h, start_m = (int(part) for part in str(hours["start"]).split(":", 1))
        end_h, end_m = (int(part) for part in str(hours["end"]).split(":", 1))
        zone = ZoneInfo(timezone)
        local = now.astimezone(zone) if now else datetime.now(zone)
    except (KeyError, TypeError, ValueError, OSError):
        return True
    current = local.hour * 60 + local.minute
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m
    if start <= end:
        return local.isoweekday() in days and start <= current < end
    # Overnight window: Monday 22:00-02:00 also covers Tuesday 00:00-02:00.
    previous_day = 7 if local.isoweekday() == 1 else local.isoweekday() - 1
    return (local.isoweekday() in days and current >= start) or (
        previous_day in days and current < end
    )


def clinic_policy_from_context(
    ctx: dict[str, Any],
    *,
    demo_hard_max_call_seconds: int | None = None,
    demo_daily_minute_budget: int | None = None,
    demo_daily_cost_budget_cents: int | None = None,
) -> ClinicPolicy:
    """Build the effective policy from tenant settings + demo hard caps (min of both)."""
    max_seconds = int(ctx["max_call_seconds"]) if ctx.get("max_call_seconds") is not None else 300
    minute_budget = (
        int(ctx["daily_minute_budget"]) if ctx.get("daily_minute_budget") is not None else 120
    )
    cost_budget = (
        int(ctx["daily_cost_budget_cents"])
        if ctx.get("daily_cost_budget_cents") is not None
        else 500
    )
    if demo_hard_max_call_seconds is not None:
        max_seconds = min(max_seconds, demo_hard_max_call_seconds)
    if demo_daily_minute_budget is not None:
        minute_budget = min(minute_budget, demo_daily_minute_budget)
    if demo_daily_cost_budget_cents is not None:
        cost_budget = min(cost_budget, demo_daily_cost_budget_cents)
    return ClinicPolicy(
        max_concurrent_calls=(
            int(ctx["max_concurrent_calls"]) if ctx.get("max_concurrent_calls") is not None else 3
        ),
        max_call_seconds=max_seconds,
        daily_minute_budget=minute_budget,
        daily_cost_budget_cents=cost_budget,
        kill_switch=bool(ctx.get("kill_switch")),
        hidden_caller_policy=str(ctx.get("hidden_caller_policy") or "allow"),
        business_hours=ctx.get("business_hours") or None,
        timezone=str(ctx.get("timezone") or "America/Bahia"),
        emergency_message=str(ctx.get("emergency_message") or EMERGENCY_MESSAGE),
    )
