from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from triavoz.application.voice.ports import VoiceRoomService, VoiceSessionRepository
from triavoz.shared_kernel.errors import ServiceUnavailable

__all__ = ["StartVoiceSession", "VoiceSessionResult"]


@dataclass(frozen=True)
class VoiceSessionResult:
    call_id: str
    room_name: str
    token: str
    url: str


class StartVoiceSession:
    """Creates the call (server-side tenant context) and the room, then returns a short token."""

    def __init__(self, repo: VoiceSessionRepository, rooms: VoiceRoomService) -> None:
        self._repo = repo
        self._rooms = rooms

    async def execute(self, *, caller_number: str, ttl_seconds: int) -> VoiceSessionResult:
        ctx = await self._repo.voice_context()
        if ctx is None:
            raise ServiceUnavailable("demo_clinic_unavailable")
        if ctx["kill_switch"]:
            raise ServiceUnavailable("voice_temporarily_unavailable")

        room_name = f"triavoz-{uuid.uuid4().hex[:16]}"
        call_id = await self._repo.create_call(room_name=room_name, caller_number=caller_number)
        metadata = {
            "clinic_id": str(ctx["clinic_id"]),
            "call_id": str(call_id),
            "channel": "web",
            "caller_number": caller_number,
            "timezone": ctx["timezone"],
            "agent_config": ctx["agent_config"],
        }
        try:
            room = await self._rooms.create_room(
                room_name=room_name,
                identity=f"web-{uuid.uuid4().hex[:12]}",
                metadata=metadata,
                ttl_seconds=ttl_seconds,
            )
        except Exception as exc:
            await self._repo.fail_call(call_id)
            raise ServiceUnavailable("voice_provider_unavailable") from exc
        return VoiceSessionResult(str(call_id), room.room_name, room.token, room.url)


def room_metadata_json(metadata: dict[str, object]) -> str:
    return json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
