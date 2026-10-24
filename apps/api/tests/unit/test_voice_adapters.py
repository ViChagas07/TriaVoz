"""Unit coverage for the voice-session adapters (no LiveKit server required)."""

from __future__ import annotations

import asyncio
from typing import Any

import jwt
import pytest

from triavoz.application.voice.ports import VoiceRoom
from triavoz.application.voice.resilient import ResilientVoiceRoomService
from triavoz.infrastructure.voice import livekit_service
from triavoz.shared_kernel.resilience import (
    Bulkhead,
    CircuitBreaker,
    CircuitOpenError,
    ProviderTimeoutError,
)


class _FakeRoomApi:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def create_room(self, request: Any) -> None:
        self.requests.append(request)


class _FakeLiveKitApi:
    instances: list[_FakeLiveKitApi] = []

    def __init__(self, url: str, key: str, secret: str) -> None:
        self.url, self.key, self.secret = url, key, secret
        self.room = _FakeRoomApi()
        self.closed = False
        _FakeLiveKitApi.instances.append(self)

    async def aclose(self) -> None:
        self.closed = True


async def test_livekit_adapter_creates_the_room_and_signs_a_room_scoped_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeLiveKitApi.instances.clear()
    monkeypatch.setattr(livekit_service.api, "LiveKitAPI", _FakeLiveKitApi)
    service = livekit_service.LiveKitVoiceService(
        http_url="http://livekit.test",
        public_url="ws://livekit.public",
        api_key="key",
        api_secret="unit-test-secret-0123456789abcdef",
    )
    metadata = {"clinic_id": "clinic-1", "call_id": "call-1", "channel": "web"}
    room = await service.create_room(
        room_name="triavoz-room",
        identity="web-abc",
        metadata=metadata,
        ttl_seconds=90,
    )

    assert isinstance(room, VoiceRoom)
    assert room.url == "ws://livekit.public"
    api_instance = _FakeLiveKitApi.instances[0]
    assert api_instance.closed is True
    assert api_instance.room.requests
    created = api_instance.room.requests[0]
    assert created.name == "triavoz-room"
    assert created.empty_timeout == 90
    assert created.max_participants == 2
    assert metadata["clinic_id"] in created.metadata

    claims = jwt.decode(room.token, "unit-test-secret-0123456789abcdef", algorithms=["HS256"])
    assert claims["sub"] == "web-abc"
    assert claims["video"]["room"] == "triavoz-room"
    assert claims["video"]["roomJoin"] is True
    assert claims["exp"] - claims["nbf"] == 90


class _FailingInner:
    def __init__(self) -> None:
        self.calls = 0

    async def create_room(self, **_: Any) -> VoiceRoom:
        self.calls += 1
        raise RuntimeError("provider down")


class _SlowInner:
    async def create_room(self, **_: Any) -> VoiceRoom:
        await asyncio.sleep(0.05)
        return VoiceRoom("room", "token", "ws://x")


async def test_resilient_adapter_opens_the_breaker_and_stops_calling_the_provider() -> None:
    inner = _FailingInner()
    breaker = CircuitBreaker("livekit", failure_threshold=2, recovery_timeout=60)
    service = ResilientVoiceRoomService(
        inner, breaker=breaker, bulkhead=Bulkhead("livekit", max_concurrency=1), timeout_seconds=1
    )
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await service.create_room(room_name="r", identity="i", metadata={}, ttl_seconds=10)
    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        await service.create_room(room_name="r", identity="i", metadata={}, ttl_seconds=10)
    assert inner.calls == 2


async def test_resilient_adapter_times_out_and_records_a_failure() -> None:
    breaker = CircuitBreaker("livekit", failure_threshold=1)
    service = ResilientVoiceRoomService(
        _SlowInner(),
        breaker=breaker,
        bulkhead=Bulkhead("livekit", max_concurrency=1),
        timeout_seconds=0.01,
    )
    with pytest.raises(ProviderTimeoutError):
        await service.create_room(room_name="r", identity="i", metadata={}, ttl_seconds=10)
    assert breaker.state == "open"
