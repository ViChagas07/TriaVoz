from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class VoiceRoom:
    room_name: str
    token: str
    url: str


class VoiceRoomService(Protocol):
    async def create_room(
        self,
        *,
        room_name: str,
        identity: str,
        metadata: dict[str, Any],
        ttl_seconds: int,
    ) -> VoiceRoom: ...


class VoiceSessionRepository(Protocol):
    async def voice_context(self) -> dict[str, Any] | None: ...
    async def create_call(
        self,
        *,
        call_id: UUID,
        room_name: str,
        caller_number: str | None,
        channel: str,
    ) -> UUID: ...
    async def fail_call(self, call_id: UUID) -> None: ...
