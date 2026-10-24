"""HTTP-level flow of the voice worker's internal API (HMAC-signed), end to end on a real DB."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

import httpx
import pytest

from tests.conftest import future_monday
from triavoz.config import get_settings
from triavoz.infrastructure.security import hmac_auth
from triavoz.main import create_app

pytestmark = pytest.mark.db


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


@pytest.fixture
async def client() -> Any:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _post(client: httpx.AsyncClient, path: str, body: dict[str, Any]) -> httpx.Response:
    raw, headers = _signed(body)
    return await client.post(path, content=raw, headers=headers)


async def test_health_is_public(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).json() == {"status": "ok"}


async def test_prometheus_endpoint_is_public_and_exposes_business_metrics(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "triavoz_http_requests_total" in response.text
    assert "triavoz_calls_started_total" in response.text
    assert "triavoz_gatekeeper_blocks_total" in response.text


async def test_internal_routes_reject_missing_or_bad_signature(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    body = {"clinic_id": str(tenants["A"]["clinic"]), "call_id": str(tenants["A"]["call"])}
    assert (await client.post("/internal/agent/tools/list-services", json=body)).status_code == 401
    raw, headers = _signed(body)
    headers[hmac_auth.SIGNATURE_HEADER] = "0" * 64
    assert (
        await client.post("/internal/agent/tools/list-services", content=raw, headers=headers)
    ).status_code == 401


async def test_replayed_signed_request_is_rejected(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    body = {"clinic_id": str(tenants["A"]["clinic"]), "call_id": str(tenants["A"]["call"])}
    raw, headers = _signed(body)
    first = await client.post("/internal/agent/tools/list-services", content=raw, headers=headers)
    assert first.status_code == 200
    replay = await client.post("/internal/agent/tools/list-services", content=raw, headers=headers)
    assert replay.status_code == 401
    assert replay.json()["detail"] == "replayed_request"


async def test_full_voice_booking_flow_over_http(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    t = tenants["A"]
    clinic = str(t["clinic"])
    phone = "+5571912345678"

    r = await _post(
        client,
        "/internal/agent/calls/start",
        {"clinic_id": clinic, "channel": "phone", "caller_number": phone},
    )
    assert r.status_code == 200
    ctx = {"clinic_id": clinic, "call_id": r.json()["call_id"]}

    services = (await _post(client, "/internal/agent/tools/list-services", ctx)).json()
    assert str(t["service"]) in [s["id"] for s in services]

    day = future_monday(6)
    slots = (
        await _post(
            client,
            "/internal/agent/tools/list-slots",
            {**ctx, "service_id": str(t["service"]), "date": day.isoformat()},
        )
    ).json()
    assert slots, "expected free slots on a future Monday"
    chosen = slots[0]

    book_body = {
        **ctx,
        "service_id": str(t["service"]),
        "professional_id": chosen["professional_id"],
        "starts_at": chosen["starts_at"],
        "customer_name": "Joana",
    }
    booked = await _post(client, "/internal/agent/tools/book", book_body)
    assert booked.status_code == 200 and booked.json()["status"] == "booked"

    again = await _post(client, "/internal/agent/tools/book", book_body)
    assert again.status_code == 409  # the same slot can never be confirmed twice

    mine = (await _post(client, "/internal/agent/tools/my-appointments", ctx)).json()
    assert [m["appointment_id"] for m in mine] == [booked.json()["appointment_id"]]

    # a DIFFERENT call (different caller phone) cannot cancel it — and gets 404, not 403
    other = await _post(
        client,
        "/internal/agent/calls/start",
        {"clinic_id": clinic, "channel": "web", "caller_number": "+5571900001111"},
    )
    other_ctx = {"clinic_id": clinic, "call_id": other.json()["call_id"]}
    denied = await _post(
        client,
        "/internal/agent/tools/cancel",
        {**other_ctx, "appointment_id": booked.json()["appointment_id"]},
    )
    assert denied.status_code == 404

    ok = await _post(
        client,
        "/internal/agent/tools/cancel",
        {**ctx, "appointment_id": booked.json()["appointment_id"]},
    )
    assert ok.status_code == 200

    stored = await _post(
        client,
        "/internal/agent/calls/turns",
        {
            **ctx,
            "turns": [
                {"seq": 0, "speaker": "patient", "content": "quero marcar uma consulta"},
                {"seq": 1, "speaker": "agent", "content": "claro!"},
                {
                    "seq": 2,
                    "speaker": "tool",
                    "tool_name": "list_available_slots",
                    "tool_payload": {"n": 3},
                },
            ],
        },
    )
    assert stored.json() == {"stored": 3}
    end = await _post(
        client,
        "/internal/agent/calls/end",
        {
            **ctx,
            "status": "completed",
            "duration_seconds": 42,
            "usage": {"llm_tokens": 1234},
            "cost_cents": 1.5,
        },
    )
    assert end.status_code == 200


async def test_naive_datetimes_are_rejected(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    t = tenants["A"]
    call = await _post(
        client,
        "/internal/agent/calls/start",
        {"clinic_id": str(t["clinic"]), "channel": "web", "caller_number": "+5571911112222"},
    )
    naive = f"{future_monday(7).isoformat()}T09:00:00"
    r = await _post(
        client,
        "/internal/agent/tools/book",
        {
            "clinic_id": str(t["clinic"]),
            "call_id": call.json()["call_id"],
            "service_id": str(t["service"]),
            "professional_id": str(t["prof"]),
            "starts_at": naive,
            "customer_name": "X",
        },
    )
    assert r.status_code == 422
