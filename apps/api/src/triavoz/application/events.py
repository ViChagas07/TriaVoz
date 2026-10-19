from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class EventPublisher(Protocol):
    """Best-effort operational events. A failed publish must never fail the business operation."""

    async def publish(self, clinic_id: UUID, event_type: str, data: dict[str, Any]) -> None: ...
