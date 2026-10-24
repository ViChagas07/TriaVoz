from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from triavoz_agent.api_client import ApiError, TriaVozApi

from evals.models import ToolEvent

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")


def _moment(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


@dataclass
class SlotLedger:
    offered: set[datetime] = field(default_factory=set)
    booked: list[datetime] = field(default_factory=list)
    hallucinated: int = 0

    def record_offered(self, slots: list[dict[str, Any]]) -> None:
        for slot in slots:
            starts_at = slot.get("starts_at")
            moment = _moment(str(starts_at)) if starts_at else None
            if moment is not None:
                self.offered.add(moment)

    def record_booking(self, starts_at: str) -> None:
        moment = _moment(starts_at)
        if moment is None or moment not in self.offered:
            self.hallucinated += 1
        else:
            self.booked.append(moment)

    def record_speech(self, text: str) -> None:
        """Every ISO time the agent says out loud must come from a tool response."""
        for raw in _ISO.findall(text):
            moment = _moment(raw)
            if moment is None or moment not in self.offered:
                self.hallucinated += 1


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


class ToolRunner:
    """Thin, instrumented wrapper over the real `/internal/agent/tools/*` endpoints."""

    def __init__(
        self,
        api: TriaVozApi,
        clinic_id: str,
        call_id: str,
        *,
        ledger: SlotLedger,
        events: list[ToolEvent],
    ) -> None:
        self.api = api
        self.clinic_id = clinic_id
        self.call_id = call_id
        self.ledger = ledger
        self.events = events
        self.calls = 0
        self.errors = 0

    async def call(self, name: str, **arguments: Any) -> ToolResult:
        self.calls += 1
        try:
            data = await self.api.tool(name, self.clinic_id, self.call_id, **arguments)
        except ApiError as exc:
            self.errors += 1
            self.events.append(ToolEvent(name=name, ok=False, arguments=arguments, error=exc.code))
            return ToolResult(ok=False, error=exc.code)
        if name == "list-slots" and isinstance(data, list):
            self.ledger.record_offered(data)
        self.events.append(ToolEvent(name=name, ok=True, arguments=arguments, output=data))
        return ToolResult(ok=True, data=data)
