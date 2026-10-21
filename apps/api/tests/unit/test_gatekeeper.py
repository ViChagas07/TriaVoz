from __future__ import annotations

import time
import uuid
from dataclasses import replace

import pytest

from triavoz.application.abuse.breaker import CostCircuitBreaker
from triavoz.application.abuse.gatekeeper import Gatekeeper
from triavoz.application.abuse.policy import (
    ClinicPolicy,
    GateAction,
    GateReason,
    RateLimitBudget,
    clinic_policy_from_context,
    is_hidden_caller,
    within_business_hours,
)
from triavoz.application.abuse.ports import DailyUsage, ScoringInputs
from triavoz.infrastructure.rate_limit.gate_store import InMemoryGateStore


class FakeRepo:
    def __init__(
        self,
        *,
        blocked: bool = False,
        usage: DailyUsage | None = None,
    ) -> None:
        self.blocked = blocked
        self.usage = usage or DailyUsage()

    async def is_blocked(self, e164: str) -> bool:
        return self.blocked

    async def daily_usage(self, *, max_call_seconds: int) -> DailyUsage:
        return self.usage

    async def scoring_inputs(
        self, call_id: uuid.UUID, *, abusive_language: bool = False
    ) -> ScoringInputs | None:
        return None

    async def apply_call_score(
        self,
        call_id: uuid.UUID,
        *,
        score: int,
        flags: tuple[str, ...],
        needs_review: bool,
    ) -> None:
        return None


class DenyingStore(InMemoryGateStore):
    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool:
        return False

    async def acquire_slot(
        self, *, clinic_id: uuid.UUID, slot_id: str, limit: int, ttl_seconds: int
    ) -> bool:
        return False


def _gatekeeper(
    *,
    clinic_id: uuid.UUID | None = None,
    policy: ClinicPolicy | None = None,
    repo: FakeRepo | None = None,
    store: InMemoryGateStore | None = None,
    limits: RateLimitBudget | None = None,
    cooldown: int = 60,
) -> tuple[Gatekeeper, CostCircuitBreaker, uuid.UUID]:
    cid = clinic_id or uuid.uuid4()
    store = store or InMemoryGateStore()
    breaker = CostCircuitBreaker(store, clinic_id=cid, cooldown_seconds=cooldown)
    gate = Gatekeeper(
        clinic_id=cid,
        policy=policy or ClinicPolicy(),
        repo=repo or FakeRepo(),
        store=store,
        rate_limits=limits
        or RateLimitBudget(
            caller_capacity=100,
            caller_refill_per_second=100,
            ip_capacity=100,
            ip_refill_per_second=100,
            global_capacity=100,
            global_refill_per_second=100,
        ),
        breaker=breaker,
    )
    return gate, breaker, cid


async def test_emergency_is_never_blocked_in_any_protection_state() -> None:
    now = time.time()
    cases: list[tuple[str, dict[str, object]]] = [
        ("kill_switch", {"policy": ClinicPolicy(kill_switch=True)}),
        (
            "after_hours",
            {
                "policy": ClinicPolicy(
                    timezone="UTC",
                    business_hours={"days": [7], "start": "09:00", "end": "10:00"},
                )
            },
        ),
        (
            "hidden_reject",
            {"policy": ClinicPolicy(hidden_caller_policy="reject")},
        ),
        ("blocked", {"repo": FakeRepo(blocked=True)}),
        (
            "minute_budget",
            {
                "policy": ClinicPolicy(daily_minute_budget=1),
                "repo": FakeRepo(usage=DailyUsage(seconds=600)),
            },
        ),
        (
            "cost_budget",
            {
                "policy": ClinicPolicy(daily_cost_budget_cents=1),
                "repo": FakeRepo(usage=DailyUsage(cost_cents=100)),
            },
        ),
        ("rate_limited", {"store": DenyingStore()}),
        ("concurrency", {"store": DenyingStore()}),
    ]
    for label, kwargs in cases:
        gate, _, _ = _gatekeeper(**kwargs)  # type: ignore[arg-type]
        decision = await gate.admit(
            caller_number="+5571999990000",
            client_ip="203.0.113.9",
            slot_id=f"slot-{label}",
            emergency=True,
            now=now + 10_000,
        )
        assert decision.action is GateAction.EMERGENCY, label
        assert decision.reason is GateReason.EMERGENCY, label
        assert decision.message and "192" in decision.message, label


async def test_open_breaker_denies_then_allows_one_half_open_probe() -> None:
    gate, breaker, _ = _gatekeeper(cooldown=60)
    now = 10_000.0
    await breaker.trip("cost_budget", now=now)

    denied = await gate.admit(
        caller_number="+5571999990001",
        client_ip="203.0.113.10",
        slot_id="slot-1",
        now=now + 10,
    )
    assert denied.reason is GateReason.COST_BREAKER
    assert denied.retry_after_seconds and denied.retry_after_seconds > 0

    probe = await gate.admit(
        caller_number="+5571999990002",
        client_ip="203.0.113.10",
        slot_id="slot-2",
        now=now + 61,
    )
    assert probe.allowed is True and probe.breaker_probe is True
    # Only one probe is elected; a second concurrent admission is denied.
    second = await gate.admit(
        caller_number="+5571999990003",
        client_ip="203.0.113.10",
        slot_id="slot-3",
        now=now + 61,
    )
    assert second.reason is GateReason.COST_BREAKER

    await breaker.record_success()
    assert (await breaker.snapshot()).status == "closed"


async def test_budget_exhaustion_trips_breaker_and_recovery_closes_it() -> None:
    repo = FakeRepo(usage=DailyUsage(seconds=9999))
    gate, breaker, _ = _gatekeeper(policy=ClinicPolicy(daily_minute_budget=1), repo=repo)
    now = time.time()

    decision = await gate.admit(
        caller_number="+5571999990004",
        client_ip="203.0.113.11",
        slot_id="slot-budget",
        now=now,
    )
    assert decision.reason is GateReason.MINUTE_BUDGET
    assert (await breaker.snapshot()).status == "open"

    # Ops frees capacity; the cooldown makes the circuit half-open for one probe.
    repo.usage = DailyUsage()
    recovered = await gate.admit(
        caller_number="+5571999990005",
        client_ip="203.0.113.11",
        slot_id="slot-recovered",
        now=now + 61,
    )
    assert recovered.allowed is True and recovered.breaker_probe is True
    await breaker.record_success()
    assert (await breaker.snapshot()).status == "closed"


async def test_concurrency_cap_and_slot_release() -> None:
    gate, _, _ = _gatekeeper(policy=ClinicPolicy(max_concurrent_calls=1))

    first = await gate.admit(
        caller_number="+5571999990010", client_ip="203.0.113.20", slot_id="slot-a"
    )
    blocked = await gate.admit(
        caller_number="+5571999990011", client_ip="203.0.113.20", slot_id="slot-b"
    )
    assert first.allowed is True
    assert blocked.reason is GateReason.CONCURRENCY

    await gate.release("slot-a")
    after = await gate.admit(
        caller_number="+5571999990012", client_ip="203.0.113.20", slot_id="slot-c"
    )
    assert after.allowed is True


async def test_caller_token_bucket_limits_then_refills() -> None:
    limits = RateLimitBudget(
        caller_capacity=2,
        caller_refill_per_second=0.0,
        ip_capacity=100,
        ip_refill_per_second=100,
        global_capacity=100,
        global_refill_per_second=100,
    )
    gate, _, _ = _gatekeeper(limits=limits)
    for index in range(2):
        slot = f"slot-{index}"
        decision = await gate.admit(
            caller_number="+5571999990020", client_ip="203.0.113.30", slot_id=slot
        )
        assert decision.allowed is True
        await gate.release(slot)
    limited = await gate.admit(
        caller_number="+5571999990020", client_ip="203.0.113.30", slot_id="slot-3"
    )
    assert limited.reason is GateReason.RATE_LIMITED
    assert limited.retry_after_seconds is not None


async def test_blocklist_kill_switch_hidden_and_business_hours() -> None:
    blocked_gate, _, _ = _gatekeeper(repo=FakeRepo(blocked=True))
    decision = await blocked_gate.admit(
        caller_number="+5571999990030", client_ip="203.0.113.40", slot_id="s"
    )
    assert decision.reason is GateReason.BLOCKED

    kill_gate, _, _ = _gatekeeper(policy=ClinicPolicy(kill_switch=True))
    decision = await kill_gate.admit(
        caller_number="+5571999990031", client_ip="203.0.113.40", slot_id="s"
    )
    assert decision.reason is GateReason.KILL_SWITCH

    hidden_gate, _, _ = _gatekeeper(policy=ClinicPolicy(hidden_caller_policy="reject"))
    decision = await hidden_gate.admit(caller_number=None, client_ip="203.0.113.40", slot_id="s")
    assert decision.reason is GateReason.HIDDEN_NUMBER

    # Default is allow: never block based on unverifiable data alone.
    allowed_gate, _, _ = _gatekeeper(policy=ClinicPolicy(hidden_caller_policy="allow"))
    decision = await allowed_gate.admit(
        caller_number=None, client_ip="203.0.113.40", slot_id="s-hidden"
    )
    assert decision.allowed is True

    assert is_hidden_caller("anonymous") is True
    assert is_hidden_caller("+5571999990032") is False
    assert within_business_hours(None, "UTC") is True


def test_clinic_policy_applies_demo_caps() -> None:
    policy = clinic_policy_from_context(
        {
            "max_call_seconds": 900,
            "daily_minute_budget": 500,
            "daily_cost_budget_cents": 900,
            "max_concurrent_calls": 5,
            "timezone": "America/Bahia",
        },
        demo_hard_max_call_seconds=300,
        demo_daily_minute_budget=120,
        demo_daily_cost_budget_cents=500,
    )
    assert policy.max_call_seconds == 300
    assert policy.daily_minute_budget == 120
    assert policy.daily_cost_budget_cents == 500


def test_fallback_messages_always_include_emergency_guidance() -> None:
    policy = ClinicPolicy()
    for reason in (
        GateReason.KILL_SWITCH,
        GateReason.AFTER_HOURS,
        GateReason.BLOCKED,
        GateReason.HIDDEN_NUMBER,
        GateReason.RATE_LIMITED,
        GateReason.CONCURRENCY,
        GateReason.MINUTE_BUDGET,
        GateReason.COST_BUDGET,
        GateReason.COST_BREAKER,
    ):
        decision = policy.fallback(reason)
        assert decision.message and "192" in decision.message


@pytest.mark.parametrize(
    ("day", "hour", "expected"),
    [(0, 10, True), (0, 8, False), (5, 10, False)],
)
def test_business_hours_weekday_window(day: int, hour: int, expected: bool) -> None:
    from datetime import UTC, datetime, timedelta

    monday = datetime(2030, 1, 7, hour, 0, tzinfo=UTC)  # Monday
    now = monday + timedelta(days=day)
    assert (
        within_business_hours(
            {"days": [1, 2, 3, 4, 5], "start": "09:00", "end": "18:00"}, "UTC", now
        )
        is expected
    )


def test_half_open_flags_are_visible_on_policy_decision() -> None:
    policy = replace(ClinicPolicy(), max_concurrent_calls=2)
    decision = policy.allowed(breaker_probe=True)
    assert decision.allowed is True and decision.breaker_probe is True
