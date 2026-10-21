"""Gatekeeper: cheap checks BEFORE creating a room or spending voice/LLM credits.

Order matters and is deliberate:
  1. emergency hint (never blocked by anything below),
  2. kill switch, hidden-number policy, business hours,
  3. blocklist (clinic + global),
  4. token buckets per caller, per IP and clinic-wide,
  5. daily minute budget, daily cost budget and cost circuit breaker,
  6. concurrent-call cap (slot released on failure/end; also TTL-expired).

Every refusal is a fallback message that still tells the caller how to reach SAMU 192. A blocked
caller is never silently dropped.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from triavoz.application.abuse.alerts import AlertService
from triavoz.application.abuse.breaker import CostCircuitBreaker
from triavoz.application.abuse.policy import (
    ClinicPolicy,
    GateDecision,
    GateReason,
    RateLimitBudget,
    is_hidden_caller,
    within_business_hours,
)
from triavoz.application.abuse.ports import AbuseRepository, GateStore

log = logging.getLogger("triavoz.gatekeeper")

__all__ = ["Gatekeeper"]


def _retry_seconds(refill_per_second: float) -> int:
    return max(1, int(round(1.0 / max(refill_per_second, 1e-9))))


class Gatekeeper:
    def __init__(
        self,
        *,
        clinic_id: UUID,
        policy: ClinicPolicy,
        repo: AbuseRepository,
        store: GateStore,
        rate_limits: RateLimitBudget,
        breaker: CostCircuitBreaker,
        alerts: AlertService | None = None,
    ) -> None:
        self._clinic_id = clinic_id
        self._policy = policy
        self._repo = repo
        self._store = store
        self._limits = rate_limits
        self._breaker = breaker
        self._alerts = alerts

    async def admit(
        self,
        *,
        caller_number: str | None,
        client_ip: str,
        slot_id: str,
        emergency: bool = False,
        now: float | None = None,
        enforce_ip_limit: bool = True,
    ) -> GateDecision:
        policy = self._policy

        # 1. Emergency always wins — before kill switch, blocklist, budgets and breaker.
        if emergency:
            log.info("gate decision clinic=%s reason=emergency", self._clinic_id)
            return policy.emergency()

        # 2. Clinic-level switches.
        if policy.kill_switch:
            return self._deny(GateReason.KILL_SWITCH)
        hidden = is_hidden_caller(caller_number)
        if hidden and policy.hidden_caller_policy == "reject":
            return self._deny(GateReason.HIDDEN_NUMBER)
        if not within_business_hours(policy.business_hours, policy.timezone):
            return self._deny(GateReason.AFTER_HOURS)

        # 3. Blocklist (clinic + global). Expired rows are ignored by the repository.
        if caller_number and not hidden and await self._repo.is_blocked(caller_number):
            return self._deny(GateReason.BLOCKED)

        # 4. Token buckets. Hidden callers are bucketed by IP only.
        caller_key = (
            f"clinic:{self._clinic_id}:rl:caller:{caller_number}"
            if not hidden
            else f"clinic:{self._clinic_id}:rl:hidden:{client_ip}"
        )
        if not await self._store.allow(
            caller_key,
            self._limits.caller_capacity,
            self._limits.caller_refill_per_second,
        ):
            return self._deny(
                GateReason.RATE_LIMITED,
                retry_after_seconds=_retry_seconds(self._limits.caller_refill_per_second),
            )
        # Telephony providers call from a shared address; bucket those by caller, not by proxy IP.
        if enforce_ip_limit and not await self._store.allow(
            f"clinic:{self._clinic_id}:rl:ip:{client_ip}",
            self._limits.ip_capacity,
            self._limits.ip_refill_per_second,
        ):
            return self._deny(
                GateReason.RATE_LIMITED,
                retry_after_seconds=_retry_seconds(self._limits.ip_refill_per_second),
            )
        if not await self._store.allow(
            f"clinic:{self._clinic_id}:rl:global",
            self._limits.global_capacity,
            self._limits.global_refill_per_second,
        ):
            return self._deny(
                GateReason.RATE_LIMITED,
                retry_after_seconds=_retry_seconds(self._limits.global_refill_per_second),
            )

        # 5. Budgets and the cost circuit breaker.
        usage = await self._repo.daily_usage(max_call_seconds=policy.max_call_seconds)
        if usage.seconds >= policy.daily_minute_budget * 60:
            await self._breaker.trip("minute_budget")
            return self._deny(GateReason.MINUTE_BUDGET)
        if usage.cost_cents >= policy.daily_cost_budget_cents:
            await self._breaker.trip("cost_budget")
            return self._deny(GateReason.COST_BUDGET)
        check = await self._breaker.check(now)
        if not check.allowed:
            return self._deny(
                GateReason.COST_BREAKER,
                retry_after_seconds=check.retry_after_seconds,
            )

        # 6. Concurrency slot. The caller already passed the breaker check, so a denial here spends
        # nothing; the slot has a TTL in case the process dies before releasing it.
        acquired = await self._store.acquire_slot(
            clinic_id=self._clinic_id,
            slot_id=slot_id,
            limit=policy.max_concurrent_calls,
            ttl_seconds=policy.max_call_seconds + 60,
        )
        if not acquired:
            return self._deny(GateReason.CONCURRENCY)

        log.info("gate decision clinic=%s reason=ok probe=%s", self._clinic_id, check.half_open)
        return policy.allowed(breaker_probe=check.half_open)

    async def release(self, slot_id: str) -> None:
        await self._store.release_slot(clinic_id=self._clinic_id, slot_id=slot_id)

    async def on_call_ended(self, *, cost_cents: float, duration_seconds: int) -> None:
        """Update the breaker from the real outcome and emit cost alerts."""
        if self._alerts is not None:
            await self._alerts.record_cost(self._clinic_id, cost_cents)
        usage = await self._repo.daily_usage(max_call_seconds=self._policy.max_call_seconds)
        if usage.cost_cents >= self._policy.daily_cost_budget_cents:
            await self._breaker.trip("cost_budget")
            return
        if usage.seconds >= self._policy.daily_minute_budget * 60:
            await self._breaker.trip("minute_budget")
            return
        await self._breaker.record_success()

    def _deny(self, reason: GateReason, *, retry_after_seconds: int | None = None) -> GateDecision:
        log.info("gate decision clinic=%s reason=%s", self._clinic_id, reason.value)
        return self._policy.fallback(reason, retry_after_seconds=retry_after_seconds)


def gatekeeper_for(
    *,
    clinic_id: UUID,
    policy: ClinicPolicy,
    repo: AbuseRepository,
    store: GateStore,
    rate_limits: RateLimitBudget,
    cooldown_seconds: int,
    failure_threshold: int,
    alerts: AlertService | None = None,
) -> Gatekeeper:
    """Small factory so HTTP/worker adapters do not duplicate breaker wiring."""
    breaker = CostCircuitBreaker(
        store,
        clinic_id=clinic_id,
        cooldown_seconds=cooldown_seconds,
        failure_threshold=failure_threshold,
    )
    return Gatekeeper(
        clinic_id=clinic_id,
        policy=policy,
        repo=repo,
        store=store,
        rate_limits=rate_limits,
        breaker=breaker,
        alerts=alerts,
    )


def rate_limits_from_settings(settings: Any) -> RateLimitBudget:
    return RateLimitBudget(
        caller_capacity=settings.voice_caller_capacity,
        caller_refill_per_second=settings.voice_caller_refill_per_second,
        ip_capacity=settings.voice_rate_capacity,
        ip_refill_per_second=settings.voice_rate_refill_per_second,
        global_capacity=settings.voice_global_capacity,
        global_refill_per_second=settings.voice_global_refill_per_second,
    )
