from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from triavoz.application.abuse.alerts import AlertService
from triavoz.infrastructure.rate_limit.gate_store import InMemoryGateStore


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, uuid.UUID, dict[str, Any]]] = []

    async def notify(self, kind: str, clinic_id: uuid.UUID, payload: dict[str, Any]) -> None:
        self.calls.append((kind, clinic_id, payload))


def _service(notifier: RecordingNotifier) -> AlertService:
    return AlertService(
        InMemoryGateStore(),
        notifier,
        calls_per_hour=2,
        cost_cents_per_hour=100,
        prank_flags_per_hour=1,
        clock=lambda: datetime(2030, 1, 7, 12, tzinfo=UTC),
    )


async def test_alerts_fire_once_per_hour_at_threshold() -> None:
    notifier = RecordingNotifier()
    service = _service(notifier)
    clinic = uuid.uuid4()
    await service.record_call(clinic)
    assert notifier.calls == []
    await service.record_call(clinic)
    await service.record_call(clinic)
    assert [c[0] for c in notifier.calls] == ["calls"]
    assert notifier.calls[0][2]["count"] == 2


async def test_cost_and_prank_alerts_use_integer_counters() -> None:
    notifier = RecordingNotifier()
    service = _service(notifier)
    clinic = uuid.uuid4()
    await service.record_cost(clinic, 60.0)
    await service.record_cost(clinic, 60.0)  # 120 cents > 100 threshold
    await service.record_prank_flag(clinic)
    assert sorted(kind for kind, _, _ in notifier.calls) == ["cost", "prank"]
    cost_payload = next(p for k, _, p in notifier.calls if k == "cost")
    assert cost_payload["count"] >= 10000  # stored in hundredths of a cent
