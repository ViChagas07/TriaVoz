"""Resilience decorator around the LiveKit room/token adapter.

Fallback: when LiveKit times out or the circuit is open, the API rejects the session with
`voice_provider_unavailable` (503) and releases the concurrency slot; the browser can retry later.
"""

from __future__ import annotations

from typing import Any

from triavoz.application.voice.ports import VoiceRoom, VoiceRoomService
from triavoz.shared_kernel.resilience import Bulkhead, CircuitBreaker, guarded_call


class ResilientVoiceRoomService:
    def __init__(
        self,
        inner: VoiceRoomService,
        *,
        breaker: CircuitBreaker,
        bulkhead: Bulkhead,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._inner = inner
        self._breaker = breaker
        self._bulkhead = bulkhead
        self._timeout = timeout_seconds

    async def create_room(
        self,
        *,
        room_name: str,
        identity: str,
        metadata: dict[str, Any],
        ttl_seconds: int,
    ) -> VoiceRoom:
        return await guarded_call(
            lambda: self._inner.create_room(
                room_name=room_name,
                identity=identity,
                metadata=metadata,
                ttl_seconds=ttl_seconds,
            ),
            breaker=self._breaker,
            bulkhead=self._bulkhead,
            timeout_seconds=self._timeout,
        )
