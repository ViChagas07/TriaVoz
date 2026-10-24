"""Public web demo: a browser-supplied phone must never grant access to that phone's bookings."""

from __future__ import annotations

import json
import secrets
import time
import uuid
from typing import Any

import httpx
import pytest

from tests.conftest import app_conn, future_monday
from triavoz.application.voice.ports import VoiceRoom
from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.gate_store import InMemoryGateStore
from triavoz.infrastructure.security import hmac_auth
from triavoz.interfaces.http.deps import (
    get_demo_clinic_slug,
    get_gate_store_dep,
    get_voice_room_service,
)
from triavoz.main import create_app

pytestmark = pytest.mark.db


class FakeRooms:
    async def create_room(
        self, *, room_name: str, identity: str, metadata: dict[str, Any], ttl_seconds: int
    ) -> VoiceRoom:
        return VoiceRoom(room_name=room_name, token="short-lived-token", url="ws://test")


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


def _app(slug: str) -> Any:
    app = create_app()
    app.dependency_overrides[get_demo_clinic_slug] = lambda: slug
    app.dependency_overrides[get_voice_room_service] = lambda: FakeRooms()
    app.dependency_overrides[get_gate_store_dep] = lambda: InMemoryGateStore()
    return app


async def test_web_caller_cannot_manage_another_phones_appointments(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    phone = f"+5571{uuid.uuid4().int % 10**9:09d}"
    app = _app(a["slug"])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as first:
        session = await first.post(
            "/api/v1/voice/session", json={"caller_number": phone, "clinic_code": a["slug"]}
        )
        assert session.status_code == 200, session.text
        assert session.json()["mode"] == "session"
        call_one = session.json()["call_id"]
        assert first.cookies.get("triavoz_caller")

        slots = await _internal(
            first,
            "/internal/agent/tools/list-slots",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": call_one,
                "service_id": str(a["service"]),
                "date": future_monday(30 + (uuid.uuid4().int % 20)).isoformat(),
            },
        )
        assert slots.status_code == 200 and slots.json(), slots.text
        chosen = slots.json()[0]
        booked = await _internal(
            first,
            "/internal/agent/tools/book",
            {
                "clinic_id": str(a["clinic"]),
                "call_id": call_one,
                "service_id": str(a["service"]),
                "professional_id": chosen["professional_id"],
                "starts_at": chosen["starts_at"],
                "customer_name": "Titular",
            },
        )
        assert booked.status_code == 200, booked.text
        appointment_id = booked.json()["appointment_id"]

    # A different browser that merely types the same phone number gets a different identity.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as attacker:
        hijack = await attacker.post(
            "/api/v1/voice/session", json={"caller_number": phone, "clinic_code": a["slug"]}
        )
        assert hijack.status_code == 200, hijack.text
        call_two = hijack.json()["call_id"]
        ctx = {"clinic_id": str(a["clinic"]), "call_id": call_two}

        mine = await _internal(attacker, "/internal/agent/tools/my-appointments", ctx)
        assert mine.status_code == 200 and mine.json() == []

        denied = await _internal(
            attacker,
            "/internal/agent/tools/cancel",
            {**ctx, "appointment_id": appointment_id},
        )
        assert denied.status_code == 404

    async with app_conn(a["clinic"]) as conn:
        status = await conn.fetchval(
            "SELECT status FROM appointments WHERE id = $1", uuid.UUID(appointment_id)
        )
    assert status == "booked"

    # The original browser identity can still manage its own booking across sessions.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as owner:
        owner.cookies.set("triavoz_caller", session.cookies.get("triavoz_caller") or "")
        resumed = await owner.post(
            "/api/v1/voice/session", json={"caller_number": phone, "clinic_code": a["slug"]}
        )
        assert resumed.status_code == 200, resumed.text
        ctx = {"clinic_id": str(a["clinic"]), "call_id": resumed.json()["call_id"]}
        mine = await _internal(owner, "/internal/agent/tools/my-appointments", ctx)
        assert [item["appointment_id"] for item in mine.json()] == [appointment_id]
        canceled = await _internal(
            owner, "/internal/agent/tools/cancel", {**ctx, "appointment_id": appointment_id}
        )
        assert canceled.status_code == 200, canceled.text
