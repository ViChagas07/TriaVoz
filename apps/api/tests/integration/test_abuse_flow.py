"""End-to-end gatekeeper, scoring, dedupe and feedback-loop tests on the real database."""

from __future__ import annotations

import json
import secrets
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import asyncpg
import httpx
import pytest

from tests.conftest import OWNER_DSN, app_conn
from triavoz.application.voice.ports import VoiceRoom
from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.gate_store import InMemoryGateStore
from triavoz.infrastructure.security import hmac_auth
from triavoz.infrastructure.security.passwords import hash_password
from triavoz.interfaces.http.deps import (
    get_demo_clinic_slug,
    get_gate_store_dep,
    get_voice_room_service,
)
from triavoz.main import create_app

pytestmark = pytest.mark.db

PASSWORD = "PwnedPassw0rd!"


class FakeRooms:
    def __init__(self) -> None:
        self.metadata: dict[str, Any] | None = None
        self.rooms: list[str] = []

    async def create_room(
        self,
        *,
        room_name: str,
        identity: str,
        metadata: dict[str, Any],
        ttl_seconds: int,
    ) -> VoiceRoom:
        self.metadata = metadata
        self.rooms.append(room_name)
        return VoiceRoom(room_name=room_name, token="short-lived-token", url="ws://test")


@pytest.fixture(scope="session", autouse=True)
async def _passwords(tenants: dict[str, dict[str, Any]]) -> AsyncIterator[None]:
    hashed = hash_password(PASSWORD)
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        for label in ("A", "B"):
            cluster = tenants[label]
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('app.current_clinic_id', $1, true)",
                    str(cluster["clinic"]),
                )
                await conn.execute(
                    "UPDATE clinic_users SET password_hash = $1 WHERE id = $2",
                    hashed,
                    cluster["user"],
                )
    finally:
        await conn.close()
    yield


async def _owner_update(clinic_id: uuid.UUID, sql: str, *args: Any) -> None:
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id)
            )
            await conn.execute(sql, *args)
    finally:
        await conn.close()


def _signed(body: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    raw = json.dumps(body).encode()
    ts = int(time.time())
    nonce = secrets.token_hex(16)
    sig = hmac_auth.sign(get_settings().internal_hmac_secret.get_secret_value(), ts, raw, nonce)
    return raw, {
        "Content-Type": "application/json",
        hmac_auth.TIMESTAMP_HEADER: str(ts),
        hmac_auth.NONCE_HEADER: nonce,
        hmac_auth.SIGNATURE_HEADER: sig,
    }


async def _internal(client: httpx.AsyncClient, path: str, body: dict[str, Any]) -> httpx.Response:
    raw, headers = _signed(body)
    return await client.post(path, content=raw, headers=headers)


def _voice_app(slug: str, store: InMemoryGateStore, rooms: FakeRooms) -> Any:
    app = create_app()
    app.dependency_overrides[get_demo_clinic_slug] = lambda: slug
    app.dependency_overrides[get_voice_room_service] = lambda: rooms
    app.dependency_overrides[get_gate_store_dep] = lambda: store
    return app


def _client(app: Any, ip: str) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(ip, 4321))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _login(client: httpx.AsyncClient, slug: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": slug, "email": "a@example.test", "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_blocklist_kill_switch_budget_and_emergency_override(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a, b = tenants["A"], tenants["B"]
    store = InMemoryGateStore()

    # 1. A manually blocked number is refused, but an emergency hint still gets SAMU guidance.
    rooms = FakeRooms()
    async with _client(_voice_app(a["slug"], store, rooms), "203.0.113.50") as client:
        blocked = await client.post(
            "/api/v1/voice/session",
            json={"caller_number": "+5571000000001"},
        )
        assert blocked.status_code == 200, blocked.text
        assert blocked.json()["mode"] == "fallback"
        assert blocked.json()["reason"] == "blocked"
        assert "192" in blocked.json()["message"]
        assert rooms.metadata is None

        emergency = await client.post(
            "/api/v1/voice/session",
            json={"caller_number": "+5571000000001", "emergency_hint": True},
        )
        assert emergency.status_code == 200
        assert emergency.json()["mode"] == "emergency"
        assert "192" in emergency.json()["message"]
        assert rooms.metadata is None

        # Global blocklist row (managed outside the tenant) is visible and enforced too.
        global_block = await client.post(
            "/api/v1/voice/session",
            json={"caller_number": tenants["global_e164"]["e164"]},
        )
        assert global_block.json()["reason"] == "blocked"

    # 2. Kill switch. Emergency bypasses it; normal calls get a fixed fallback.
    await _owner_update(a["clinic"], "UPDATE clinic_settings SET kill_switch = true")
    try:
        rooms = FakeRooms()
        async with _client(_voice_app(a["slug"], store, rooms), "203.0.113.51") as client:
            killed = await client.post(
                "/api/v1/voice/session", json={"caller_number": "+5571999900100"}
            )
            assert killed.json()["reason"] == "kill_switch"
            assert rooms.metadata is None

            emergency = await client.post(
                "/api/v1/voice/session",
                json={"caller_number": "+5571999900101", "emergency_hint": True},
            )
            assert emergency.json()["mode"] == "emergency"
    finally:
        await _owner_update(a["clinic"], "UPDATE clinic_settings SET kill_switch = false")

    # 3. Daily cost budget on clinic B: 0 means exhausted; emergency still passes.
    await _owner_update(b["clinic"], "UPDATE clinic_settings SET daily_cost_budget_cents = 0")
    try:
        rooms = FakeRooms()
        async with _client(_voice_app(b["slug"], store, rooms), "203.0.113.52") as client:
            exhausted = await client.post(
                "/api/v1/voice/session", json={"caller_number": "+5571999900200"}
            )
            assert exhausted.json()["reason"] == "cost_budget"
            assert "192" in exhausted.json()["message"]

            emergency = await client.post(
                "/api/v1/voice/session",
                json={"caller_number": "+5571999900201", "emergency_hint": True},
            )
            assert emergency.json()["mode"] == "emergency"
    finally:
        await _owner_update(b["clinic"], "UPDATE clinic_settings SET daily_cost_budget_cents = 500")


async def test_concurrency_cap_and_metadata_limits(tenants: dict[str, dict[str, Any]]) -> None:
    b = tenants["B"]
    await _owner_update(b["clinic"], "UPDATE clinic_settings SET max_concurrent_calls = 1")
    store = InMemoryGateStore()
    rooms = FakeRooms()
    try:
        async with _client(_voice_app(b["slug"], store, rooms), "203.0.113.60") as client:
            first = await client.post(
                "/api/v1/voice/session", json={"caller_number": "+5571999900300"}
            )
            assert first.status_code == 200 and first.json()["mode"] == "session", first.text
            assert rooms.metadata is not None
            assert rooms.metadata["max_call_seconds"] <= get_settings().demo_hard_max_call_seconds
            assert rooms.metadata["max_turns"] > 0
            assert rooms.metadata["silence_timeout_seconds"] > 0

            second = await client.post(
                "/api/v1/voice/session", json={"caller_number": "+5571999900301"}
            )
            assert second.json()["reason"] == "concurrency"
            assert second.json()["token"] is None
    finally:
        await _owner_update(b["clinic"], "UPDATE clinic_settings SET max_concurrent_calls = 3")


async def test_telephony_webhook_runs_gatekeeper_and_emergency(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    store = InMemoryGateStore()
    rooms = FakeRooms()
    async with _client(_voice_app(a["slug"], store, rooms), "203.0.113.80") as client:
        normal = await _internal(
            client,
            "/internal/agent/telephony/incoming",
            {"to": a["e164"], "from": "+5571999900700"},
        )
        assert normal.status_code == 200, normal.text
        assert normal.json()["mode"] == "session"
        assert normal.json()["token"] == "short-lived-token"

        emergency = await _internal(
            client,
            "/internal/agent/telephony/incoming",
            {
                "to": a["e164"],
                "from": "+5571000000001",  # blocked number on purpose
                "emergency": True,
            },
        )
        assert emergency.status_code == 200
        assert emergency.json()["mode"] == "emergency"
        assert "192" in str(emergency.json()["message"])


async def test_post_call_scoring_flags_and_request_badge(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    store = InMemoryGateStore()
    phone = "+5571999900400"
    async with _client(_voice_app(a["slug"], store, FakeRooms()), "203.0.113.70") as client:
        # Very short, silent call -> high score + review flag.
        first = await _internal(
            client,
            "/internal/agent/calls/start",
            {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": phone},
        )
        call_one = first.json()["call_id"]
        ended = await _internal(
            client,
            "/internal/agent/calls/end",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": call_one,
                "status": "completed",
                "duration_seconds": 5,
                "usage": {},
                "cost_cents": 0,
            },
        )
        assert ended.status_code == 200, ended.text

        # Two earlier calls make the next one a repeat caller (>= 2 previous calls in 24h).
        extra = await _internal(
            client,
            "/internal/agent/calls/start",
            {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": phone},
        )
        await _internal(
            client,
            "/internal/agent/calls/end",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": extra.json()["call_id"],
                "status": "completed",
                "duration_seconds": 5,
                "cost_cents": 0,
            },
        )

        # Second short call from the same number, with a request -> repeat-caller + request flags.
        second = await _internal(
            client,
            "/internal/agent/calls/start",
            {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": phone},
        )
        call_two = second.json()["call_id"]
        created = await _internal(
            client,
            "/internal/agent/tools/create-service-request",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": call_two,
                "type": "message",
                "title": f"Teste de abuso {uuid.uuid4().hex[:6]}",
            },
        )
        assert created.status_code == 200, created.text
        request_id = created.json()["request_id"]
        await _internal(
            client,
            "/internal/agent/calls/end",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": call_two,
                "status": "completed",
                "duration_seconds": 5,
                "cost_cents": 0,
            },
        )

    async with app_conn(a["clinic"]) as conn:
        first_score = await conn.fetchrow(
            "SELECT abuse_score, suspicion_flags FROM calls WHERE id = $1",
            uuid.UUID(call_one),
        )
        second_score = await conn.fetchrow(
            "SELECT abuse_score, suspicion_flags FROM calls WHERE id = $1",
            uuid.UUID(call_two),
        )
        request_flags = await conn.fetchval(
            "SELECT suspicion_flags FROM service_requests WHERE id = $1",
            uuid.UUID(request_id),
        )
    assert first_score is not None and first_score["abuse_score"] >= 50
    assert "very_short" in first_score["suspicion_flags"]
    assert second_score is not None and "repeat_caller" in second_score["suspicion_flags"]
    assert request_flags and "very_short" in request_flags


async def test_identical_requests_from_same_number_are_deduplicated(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    store = InMemoryGateStore()
    title = f"Retorno duplicado {uuid.uuid4().hex[:6]}"
    phone = "+5571999900500"
    async with _client(_voice_app(a["slug"], store, FakeRooms()), "203.0.113.71") as client:
        request_ids = []
        for _ in range(2):
            started = await _internal(
                client,
                "/internal/agent/calls/start",
                {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": phone},
            )
            call_id = started.json()["call_id"]
            response = await _internal(
                client,
                "/internal/agent/tools/create-service-request",
                {
                    "clinic_id": str(a["clinic"]),
                    "call_id": call_id,
                    "type": "callback",
                    "title": title,
                },
            )
            assert response.status_code == 200, response.text
            request_ids.append(response.json()["request_id"])
    assert request_ids[0] == request_ids[1]


async def test_mark_spam_expiry_and_unblock(tenants: dict[str, dict[str, Any]]) -> None:
    a = tenants["A"]
    store = InMemoryGateStore()
    app = _voice_app(a["slug"], store, FakeRooms())
    async with _client(app, "203.0.113.72") as client:
        started = await _internal(
            client,
            "/internal/agent/calls/start",
            {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": "+5571999900600"},
        )
        call_id = started.json()["call_id"]
        created = await _internal(
            client,
            "/internal/agent/tools/create-service-request",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": call_id,
                "type": "message",
                "title": "Ligação de teste para spam",
            },
        )
        request_id = created.json()["request_id"]
        headers = await _login(client, a["slug"])

        marked = await client.post(
            f"/api/v1/requests/{request_id}/mark-spam",
            headers=headers,
            json={"expires_in_days": 7},
        )
        assert marked.status_code == 200, marked.text
        assert marked.json()["status"] == "spam"
        assert marked.json()["needs_review"] is True

        async with app_conn(a["clinic"]) as conn:
            blocked = await conn.fetchrow(
                "SELECT id, expires_at FROM blocked_numbers WHERE e164 = $1",
                "+5571999900600",
            )
        assert blocked is not None and blocked["expires_at"] is not None

        unblocked = await client.post(
            f"/api/v1/blocked-numbers/{blocked['id']}/unblock", headers=headers
        )
        assert unblocked.status_code == 204
        async with app_conn(a["clinic"]) as conn:
            remaining = await conn.fetchval(
                "SELECT count(*) FROM blocked_numbers WHERE id = $1", blocked["id"]
            )
        assert remaining == 0
