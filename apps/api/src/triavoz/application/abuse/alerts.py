"""Spike alerts for calls, cost and prank flags.

Counters are shared in Redis (hourly windows). Each alert fires at most once per hour and never
includes the caller's phone number: only the clinic id, the counter and the threshold.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from triavoz.application.abuse.ports import AlertNotifier, GateStore

__all__ = ["AlertService", "hour_bucket"]


def hour_bucket(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%d%H")


class AlertService:
    def __init__(
        self,
        store: GateStore,
        notifier: AlertNotifier,
        *,
        calls_per_hour: int,
        cost_cents_per_hour: int,
        prank_flags_per_hour: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._notifier = notifier
        self._calls = max(1, calls_per_hour)
        self._cost = max(1, cost_cents_per_hour)
        self._pranks = max(1, prank_flags_per_hour)
        self._clock = clock or (lambda: datetime.now(UTC))

    async def record_call(self, clinic_id: UUID) -> None:
        await self._bump("calls", clinic_id, 1, self._calls)

    async def record_cost(self, clinic_id: UUID, cost_cents: float) -> None:
        # Integer counters in hundredths of a cent keep small per-call costs visible.
        units = max(1, int(round(cost_cents * 100)))
        await self._bump("cost", clinic_id, units, self._cost * 100)

    async def record_prank_flag(self, clinic_id: UUID) -> None:
        await self._bump("prank", clinic_id, 1, self._pranks)

    async def _bump(self, kind: str, clinic_id: UUID, amount: int, threshold: int) -> None:
        hour = hour_bucket(self._clock())
        counter_key = f"clinic:{clinic_id}:rl:alert:{kind}:{hour}"
        count = await self._store.increment(counter_key, ttl_seconds=7200, amount=amount)
        if count < threshold:
            return
        sent_key = f"clinic:{clinic_id}:rl:alert:sent:{kind}:{hour}"
        first = await self._store.set_if_absent(sent_key, str(count), ttl_seconds=7200)
        if not first:
            return
        await self._notifier.notify(
            kind,
            clinic_id,
            {
                "kind": kind,
                "count": count,
                "threshold": threshold,
                "hour_utc": hour,
            },
        )
