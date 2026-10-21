"""Cost circuit breaker: closed -> open -> half-open, shared through Redis.

A breach of the daily cost/minute budget calls ``trip``. While open, the gatekeeper answers with a
fixed "high demand" message (plus SAMU guidance) instead of spending credits. After the cooldown, a
single probe call is allowed; its outcome closes or reopens the circuit.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from triavoz.application.abuse.ports import GateStore


def breaker_key(clinic_id: UUID) -> str:
    return f"clinic:{clinic_id}:rl:breaker:cost"


def probe_key(clinic_id: UUID) -> str:
    return f"clinic:{clinic_id}:rl:breaker:probe"


@dataclass(frozen=True)
class BreakerCheck:
    allowed: bool
    half_open: bool = False
    retry_after_seconds: int = 0
    reason: str = "closed"


@dataclass(frozen=True)
class BreakerSnapshot:
    status: str = "closed"
    failures: int = 0
    opened_at: float = 0.0
    last_reason: str = ""


class CostCircuitBreaker:
    def __init__(
        self,
        store: GateStore,
        *,
        clinic_id: UUID,
        cooldown_seconds: int = 300,
        failure_threshold: int = 1,
        probe_ttl_seconds: int = 120,
    ) -> None:
        self._store = store
        self._clinic_id = clinic_id
        self._cooldown = max(1, cooldown_seconds)
        self._threshold = max(1, failure_threshold)
        self._probe_ttl = max(10, probe_ttl_seconds)

    async def snapshot(self) -> BreakerSnapshot:
        raw = await self._store.get_json(breaker_key(self._clinic_id))
        if not raw:
            return BreakerSnapshot()
        return BreakerSnapshot(
            status=str(raw.get("status", "closed")),
            failures=int(raw.get("failures", 0)),
            opened_at=float(raw.get("opened_at", 0.0)),
            last_reason=str(raw.get("last_reason", "")),
        )

    async def check(self, now: float | None = None) -> BreakerCheck:
        current = time.time() if now is None else now
        snap = await self.snapshot()
        if snap.status not in {"open", "half_open"}:
            return BreakerCheck(allowed=True)
        if snap.status == "open":
            remaining = self._cooldown - (current - snap.opened_at)
            if remaining > 0:
                return BreakerCheck(
                    allowed=False,
                    retry_after_seconds=max(1, int(remaining)),
                    reason=snap.last_reason or "open",
                )
        # Either the cooldown elapsed or we are already half-open: elect one probe.
        probe = await self._store.set_if_absent(
            probe_key(self._clinic_id), str(current), self._probe_ttl
        )
        if probe is False:
            return BreakerCheck(
                allowed=False,
                retry_after_seconds=self._probe_ttl,
                reason=snap.last_reason or "probe_in_flight",
            )
        await self._save(
            status="half_open",
            failures=snap.failures,
            opened_at=snap.opened_at,
            last_reason=snap.last_reason or "cooldown_elapsed",
        )
        return BreakerCheck(allowed=True, half_open=True, reason="half_open")

    async def trip(self, reason: str, now: float | None = None) -> None:
        current = time.time() if now is None else now
        snap = await self.snapshot()
        await self._save(
            status="open",
            failures=max(self._threshold, snap.failures + 1),
            opened_at=current,
            last_reason=reason,
        )
        await self._store.delete(probe_key(self._clinic_id))

    async def record_success(self) -> None:
        await self._save(status="closed", failures=0, opened_at=0.0, last_reason="")
        await self._store.delete(probe_key(self._clinic_id))

    async def record_failure(self, reason: str, now: float | None = None) -> None:
        snap = await self.snapshot()
        if snap.status == "half_open" or snap.failures + 1 >= self._threshold:
            await self.trip(reason, now=now)
            return
        await self._save(
            status=snap.status,
            failures=snap.failures + 1,
            opened_at=snap.opened_at,
            last_reason=reason,
        )

    async def _save(
        self, *, status: str, failures: int, opened_at: float, last_reason: str
    ) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "failures": failures,
            "opened_at": opened_at,
            "last_reason": last_reason,
        }
        # Keep the state well past the cooldown so a restart cannot silently forget an open circuit.
        await self._store.set_json(
            breaker_key(self._clinic_id), payload, ttl_seconds=self._cooldown * 4 + 60
        )


def parse_breaker_state(raw: str | None) -> BreakerSnapshot:
    """Kept for callers that already hold the raw JSON (tests/diagnostics)."""
    if not raw:
        return BreakerSnapshot()
    try:
        data = json.loads(raw)
    except ValueError:
        return BreakerSnapshot()
    return BreakerSnapshot(
        status=str(data.get("status", "closed")),
        failures=int(data.get("failures", 0)),
        opened_at=float(data.get("opened_at", 0.0)),
        last_reason=str(data.get("last_reason", "")),
    )
