"""DoS limits: streamed body caps and SSE connection ceilings."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import HTTPException

from triavoz.config import get_settings
from triavoz.interfaces.http.api_v1.events import _acquire_stream_slot, _release_stream_slot
from triavoz.main import create_app


async def _body() -> AsyncIterator[bytes]:
    yield b"x" * 2048


async def test_oversized_body_is_rejected_with_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "max_request_body_bytes", 1024)
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/auth/login", content=b"x" * 2048)
    assert response.status_code == 413
    assert response.json()["detail"] == "payload_too_large"


async def test_oversized_streamed_body_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "max_request_body_bytes", 1024)
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/auth/login", content=_body())
    assert response.status_code == 413


async def test_sse_stream_slots_are_bounded_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "sse_max_connections_per_user", 1)
    user, clinic = uuid.uuid4(), uuid.uuid4()
    await _acquire_stream_slot(user, clinic)
    try:
        with pytest.raises(HTTPException) as exc:
            await _acquire_stream_slot(user, clinic)
        assert exc.value.status_code == 429
        assert exc.value.detail == "sse_connection_limit"
    finally:
        await _release_stream_slot(user, clinic)
    await _acquire_stream_slot(user, clinic)
    await _release_stream_slot(user, clinic)
