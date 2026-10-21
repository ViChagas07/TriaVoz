"""HTTP contract for the staff API + public voice session.

The suite runs against the real PostgreSQL roles; every cross-tenant access must be a 404 (never a
403 that reveals existence). Auth cookies are exercised without an Authorization header so the SSE
path is covered too.
"""

from __future__ import annotations

import json
import secrets
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import asyncpg
import httpx
import pytest

from tests.conftest import OWNER_DSN, app_conn, future_monday
from triavoz.application.auth.service import AuthService
from triavoz.application.voice.ports import VoiceRoom
from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.limiter import InMemoryRateLimiter
from triavoz.infrastructure.security import hmac_auth
from triavoz.infrastructure.security.passwords import hash_password
from triavoz.interfaces.http.deps import (
    get_auth_service,
    get_demo_clinic_slug,
    get_event_stream,
    get_password_hasher,
    get_voice_room_service,
)
from triavoz.main import create_app

pytestmark = pytest.mark.db

PASSWORD = "TestPassw0rd!"
REFRESH_COOKIE = "triavoz_refresh"
ACCESS_COOKIE = "triavoz_access"


@pytest.fixture(scope="session", autouse=True)
async def _passwords(tenants: dict[str, dict[str, Any]]) -> AsyncIterator[None]:
    hashed = hash_password(PASSWORD)
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        for label in ("A", "B"):
            t = tenants[label]
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('app.current_clinic_id', $1, true)", str(t["clinic"])
                )
                await conn.execute(
                    "UPDATE clinic_users SET password_hash = $1 WHERE id = $2",
                    hashed,
                    t["user"],
                )
    finally:
        await conn.close()
    yield


def _app() -> Any:
    """App factory with a per-test limiter so lockout tests never leak into other tests."""
    app = create_app()
    settings = get_settings()
    service = AuthService(
        InMemoryRateLimiter(),
        get_password_hasher(),
        refresh_ttl_days=settings.refresh_token_ttl_days,
        account_capacity=settings.login_account_capacity,
        ip_capacity=settings.login_ip_capacity,
    )
    app.dependency_overrides[get_auth_service] = lambda: service
    return app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _app_client(app: Any, client_host: tuple[str, int] | None = None) -> httpx.AsyncClient:
    if client_host:
        transport = httpx.ASGITransport(app=app, client=client_host)
    else:
        transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _login(
    client: httpx.AsyncClient,
    clinic_code: str,
    email: str,
    password: str = PASSWORD,
) -> dict[str, Any]:
    r = await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": clinic_code, "email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _bearer(login: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}"}


async def _create_attendant(
    client: httpx.AsyncClient, admin: dict[str, Any], clinic_slug: str
) -> tuple[str, dict[str, str]]:
    email = f"att-{uuid.uuid4().hex[:8]}@example.test"
    r = await client.post(
        "/api/v1/team",
        headers=_bearer(admin),
        json={
            "email": email,
            "full_name": "Atendente de Teste",
            "role": "attendant",
            "password": "AttendantPass9!",
        },
    )
    assert r.status_code == 200, r.text
    login = await _login(client, clinic_slug, email, "AttendantPass9!")
    return email, _bearer(login)


def _signed(
    body: dict[str, Any], extra: dict[str, str] | None = None
) -> tuple[bytes, dict[str, str]]:
    raw = json.dumps(body).encode()
    ts = int(time.time())
    nonce = secrets.token_hex(16)
    sig = hmac_auth.sign(get_settings().internal_hmac_secret.get_secret_value(), ts, raw, nonce)
    headers = {
        "Content-Type": "application/json",
        hmac_auth.TIMESTAMP_HEADER: str(ts),
        hmac_auth.NONCE_HEADER: nonce,
        hmac_auth.SIGNATURE_HEADER: sig,
        **(extra or {}),
    }
    return raw, headers


async def _internal(
    client: httpx.AsyncClient,
    path: str,
    body: dict[str, Any],
    extra: dict[str, str] | None = None,
) -> httpx.Response:
    raw, headers = _signed(body, extra)
    return await client.post(path, content=raw, headers=headers)


def _future_slot(tz_name: str, weeks: int = 8, hour: int = 9) -> datetime:
    day = future_monday(weeks)
    return datetime.combine(day, datetime.min.time().replace(hour=hour), tzinfo=ZoneInfo(tz_name))


async def test_login_me_refresh_rotation_and_logout(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": a["slug"], "email": "a@example.test", "password": PASSWORD},
    )
    assert login_response.status_code == 200, login_response.text
    login = login_response.json()
    assert login["token_type"] == "bearer"
    assert login["user"]["role"] == "admin"
    assert client.cookies.get(ACCESS_COOKIE)
    assert client.cookies.get(REFRESH_COOKIE)
    set_cookie = " ".join(login_response.headers.get_list("set-cookie"))
    assert "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["user"]["id"] == str(a["user"])

    old_refresh = client.cookies.get(REFRESH_COOKIE)
    first = await client.post("/api/v1/auth/refresh")
    assert first.status_code == 200, first.text
    new_refresh = client.cookies.get(REFRESH_COOKIE)
    assert new_refresh and new_refresh != old_refresh

    client.cookies.clear()
    reuse = await client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"{REFRESH_COOKIE}={old_refresh}"},
    )
    assert reuse.status_code == 401
    client.cookies.clear()
    revoked_family = await client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"{REFRESH_COOKIE}={new_refresh}"},
    )
    assert revoked_family.status_code == 401, "reuse must revoke the whole family"

    client.cookies.clear()
    logout = await client.post(
        "/api/v1/auth/logout", headers={"Cookie": f"{REFRESH_COOKIE}={new_refresh}"}
    )
    assert logout.status_code == 204


async def test_login_generic_errors_and_progressive_lockout(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    wrong = await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": a["slug"], "email": "wrong@example.test", "password": PASSWORD},
    )
    assert wrong.status_code == 401 and wrong.json()["detail"] == "invalid_credentials"
    unknown = await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": "does-not-exist", "email": "x@example.test", "password": PASSWORD},
    )
    assert unknown.status_code == 401

    app = _app()
    async with _app_client(app, ("198.51.100.77", 1234)) as locked:
        email = f"lock-{uuid.uuid4().hex[:8]}@example.test"
        statuses = []
        for _ in range(6):
            r = await locked.post(
                "/api/v1/auth/login",
                json={"clinic_code": a["slug"], "email": email, "password": PASSWORD},
            )
            statuses.append(r.status_code)
        assert statuses[:5] == [401] * 5, statuses
        assert statuses[5] == 429, statuses


async def test_cross_tenant_resources_are_404_and_transcript_reads_are_audited(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a, b = tenants["A"], tenants["B"]
    admin_a = await _login(client, a["slug"], "a@example.test")
    admin_b = await _login(client, b["slug"], "b@example.test")
    ha, hb = _bearer(admin_a), _bearer(admin_b)

    assert (await client.get(f"/api/v1/requests/{a['req']}", headers=ha)).status_code == 200
    assert (await client.get(f"/api/v1/requests/{a['req']}", headers=hb)).status_code == 404
    assert (
        await client.patch(f"/api/v1/requests/{a['req']}", headers=hb, json={"title": "hijack"})
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/requests/{a['req']}/complete", headers=hb)
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/requests/{a['req']}/mark-spam", headers=hb)
    ).status_code == 404
    assert (await client.get(f"/api/v1/calls/{a['call']}", headers=hb)).status_code == 404
    assert (await client.get(f"/api/v1/calls/{a['call']}/turns", headers=hb)).status_code == 404
    assert (await client.get(f"/api/v1/calls/{a['call']}/events", headers=hb)).status_code == 404
    assert (await client.post(f"/api/v1/calls/{a['call']}/summary", headers=hb)).status_code == 404
    assert (
        await client.post(
            f"/api/v1/agenda/{a['appt']}/move",
            headers=hb,
            json={"starts_at": "2030-01-07T10:00:00-03:00"},
        )
    ).status_code == 404
    assert (await client.post(f"/api/v1/agenda/{a['appt']}/cancel", headers=hb)).status_code == 404
    assert (await client.delete(f"/api/v1/team/{a['user']}", headers=hb)).status_code == 404
    assert (
        await client.delete(f"/api/v1/blocked-numbers/{a['blocked']}", headers=hb)
    ).status_code == 404

    async with app_conn(a["clinic"]) as conn:
        before = await conn.fetchval(
            "SELECT count(*) FROM audit_log WHERE action = 'call.transcript.read'"
        )
    turns = await client.get(f"/api/v1/calls/{a['call']}/turns", headers=ha)
    assert turns.status_code == 200 and turns.json()[0]["content"] == "oi"
    async with app_conn(a["clinic"]) as conn:
        after = await conn.fetchval(
            "SELECT count(*) FROM audit_log WHERE action = 'call.transcript.read'"
        )
    assert after == before + 1


async def test_rbac_admin_only_routes_and_self_deactivation(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "a@example.test")
    email, attendant = await _create_attendant(client, admin, a["slug"])

    assert (await client.get("/api/v1/team", headers=attendant)).status_code == 403
    assert (
        await client.put(
            "/api/v1/agent-config/draft",
            headers=attendant,
            json={
                "clinic_name": "X",
                "greeting": "Olá! Sou a assistente da {clinic_name}.",
                "tone": "calmo",
                "emergency_message": "Ligue 192.",
            },
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/blocked-numbers", headers=attendant, json={"e164": "+5571999900000"}
        )
    ).status_code == 403

    assert (
        await client.delete(f"/api/v1/team/{a['user']}", headers=_bearer(admin))
    ).status_code == 409
    created = await client.get("/api/v1/team", headers=_bearer(admin))
    assert created.status_code == 200
    user_id = next(u["id"] for u in created.json() if u["email"] == email)
    assert (
        await client.delete(f"/api/v1/team/{user_id}", headers=_bearer(admin))
    ).status_code == 200
    denied = await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": a["slug"], "email": email, "password": "AttendantPass9!"},
    )
    assert denied.status_code == 401


async def test_requests_filters_mutations_timeline_and_mark_spam_blocklist(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "a@example.test")
    h = _bearer(admin)

    listed = await client.get("/api/v1/requests", headers=h)
    assert listed.status_code == 200
    assert any(item["id"] == str(a["req"]) for item in listed.json()["items"])
    filtered = await client.get("/api/v1/requests", headers=h, params={"search": "recado"})
    assert [i["id"] for i in filtered.json()["items"]] == [str(a["req"])]

    patched = await client.patch(
        f"/api/v1/requests/{a['req']}", headers=h, json={"priority": "urgent", "title": "Novo"}
    )
    assert patched.status_code == 200 and patched.json()["priority"] == "urgent"
    detail = await client.get(f"/api/v1/requests/{a['req']}", headers=h)
    assert [e["event_type"] for e in detail.json()["timeline"]][-1] == "updated"

    assigned = await client.post(
        f"/api/v1/requests/{a['req']}/assign", headers=h, json={"user_id": str(a["user"])}
    )
    assert assigned.status_code == 200 and assigned.json()["assigned_to"] == str(a["user"])

    marked = await client.post(f"/api/v1/requests/{a['req']}/mark-spam", headers=h)
    assert marked.status_code == 200 and marked.json()["status"] == "spam"
    async with app_conn(a["clinic"]) as conn:
        blocked = await conn.fetchval(
            "SELECT count(*) FROM blocked_numbers WHERE e164 = '+5571988887777'"
        )
    assert blocked == 1

    # cursor pagination: create a second request through the HMAC tool first
    started = await _internal(
        client,
        "/internal/agent/calls/start",
        {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": "+5571999900011"},
    )
    call_id = started.json()["call_id"]
    created = await _internal(
        client,
        "/internal/agent/tools/create-service-request",
        {
            "clinic_id": str(a["clinic"]),
            "call_id": call_id,
            "type": "callback",
            "title": "Retornar ligação",
            "patient_name": "Maria",
        },
    )
    assert created.status_code == 200
    page1 = await client.get("/api/v1/requests", headers=h, params={"limit": 1})
    assert page1.status_code == 200 and page1.json()["next_cursor"]
    page2 = await client.get(
        "/api/v1/requests", headers=h, params={"limit": 1, "cursor": page1.json()["next_cursor"]}
    )
    assert page2.status_code == 200
    assert page2.json()["items"][0]["id"] != page1.json()["items"][0]["id"]


async def test_calls_detail_summary_stub_and_dashboard(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "a@example.test")
    h = _bearer(admin)
    listed = await client.get("/api/v1/calls", headers=h)
    assert listed.status_code == 200 and listed.json()["items"]
    detail = await client.get(f"/api/v1/calls/{a['call']}", headers=h)
    assert detail.status_code == 200 and detail.json()["usage"] == {}
    events = await client.get(f"/api/v1/calls/{a['call']}/events", headers=h)
    assert events.status_code == 200 and events.json()[0]["event_type"] == "call_started"
    summary = await client.post(f"/api/v1/calls/{a['call']}/summary", headers=h)
    assert summary.status_code == 503

    dashboard = await client.get("/api/v1/dashboard", headers=h)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["calls_today"] >= 1
    assert "pending_requests" in body and "handoff_rate" in body


async def test_agenda_create_move_cancel(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "a@example.test")
    h = _bearer(admin)
    async with app_conn(a["clinic"]) as conn:
        tz_name = await conn.fetchval("SELECT timezone FROM clinics WHERE id = $1", a["clinic"])
    starts = _future_slot(tz_name, weeks=8, hour=9)
    created = await client.post(
        "/api/v1/agenda",
        headers=h,
        json={
            "service_id": str(a["service"]),
            "professional_id": str(a["prof"]),
            "starts_at": starts.isoformat(),
            "customer_name": "Paciente Staff",
            "customer_phone": "+5571999912345",
        },
    )
    assert created.status_code == 200, created.text
    appointment_id = created.json()["id"]
    assert created.json()["created_via"] == "staff"

    agenda = await client.get(
        "/api/v1/agenda", headers=h, params={"date_from": starts.date().isoformat()}
    )
    assert any(item["id"] == appointment_id for item in agenda.json())
    moved = await client.post(
        f"/api/v1/agenda/{appointment_id}/move",
        headers=h,
        json={"starts_at": starts.replace(hour=10).isoformat()},
    )
    assert moved.status_code == 200 and moved.json()["starts_at"] != created.json()["starts_at"]
    canceled = await client.post(f"/api/v1/agenda/{appointment_id}/cancel", headers=h)
    assert canceled.status_code == 200 and canceled.json()["status"] == "canceled"


async def test_agent_config_draft_publish_rollback_and_validation(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "a@example.test")
    h = _bearer(admin)
    state = await client.get("/api/v1/agent-config", headers=h)
    assert state.status_code == 200 and state.json()["published"]["version"] == 1

    invalid = await client.put(
        "/api/v1/agent-config/draft",
        headers=h,
        json={"clinic_name": "", "greeting": "", "emergency_message": ""},
    )
    assert invalid.status_code == 422

    draft = await client.put(
        "/api/v1/agent-config/draft",
        headers=h,
        json={
            "clinic_name": "Clínica A",
            "greeting": "Olá! Sou a assistente da {clinic_name}.",
            "tone": "acolhedor",
            "emergency_message": "Se for urgente, ligue 192.",
        },
    )
    assert draft.status_code == 200 and draft.json()["status"] == "draft"
    version = draft.json()["version"]
    published = await client.post(f"/api/v1/agent-config/{version}/publish", headers=h)
    assert published.status_code == 200 and published.json()["status"] == "published"

    rolled = await client.post("/api/v1/agent-config/1/rollback", headers=h)
    assert rolled.status_code == 200 and rolled.json()["status"] == "published"
    assert rolled.json()["version"] > version


async def test_team_and_blocked_crud(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "a@example.test")
    h = _bearer(admin)
    team = await client.get("/api/v1/team", headers=h)
    assert team.status_code == 200 and any(
        u["email"].endswith("@example.test") for u in team.json()
    )

    blocked = await client.post(
        "/api/v1/blocked-numbers",
        headers=h,
        json={"e164": "+5571999988888", "reason": "prank"},
    )
    assert blocked.status_code == 200
    blocked_id = blocked.json()["id"]
    listed = await client.get("/api/v1/blocked-numbers", headers=h)
    assert any(b["id"] == blocked_id for b in listed.json())
    assert (
        await client.delete(f"/api/v1/blocked-numbers/{blocked_id}", headers=h)
    ).status_code == 204
    assert (
        await client.delete(f"/api/v1/blocked-numbers/{blocked_id}", headers=h)
    ).status_code == 404


async def test_sse_requires_auth_and_relays_tenant_events(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    assert (await client.get("/api/v1/events/stream")).status_code == 401

    class OneFrameBus:
        async def publish(self, clinic_id: uuid.UUID, event_type: str, data: dict[str, Any]):
            return None

        async def subscribe(self, clinic_id: uuid.UUID) -> AsyncIterator[str]:
            yield 'event: update\ndata: {"type":"request.created"}\n\n'

    app = _app()
    app.dependency_overrides[get_event_stream] = lambda: OneFrameBus()
    a = tenants["A"]
    async with _app_client(app) as stream_client:
        await _login(stream_client, a["slug"], "a@example.test")
        async with stream_client.stream("GET", "/api/v1/events/stream") as response:
            assert response.status_code == 200
            lines = [line async for line in response.aiter_lines()]
        assert any(line.startswith("retry:") for line in lines)
        assert any("request.created" in line for line in lines)


async def test_voice_session_uses_server_metadata_and_demo_clinic(
    tenants: dict[str, dict[str, Any]],
) -> None:
    class FakeRooms:
        metadata: dict[str, Any] | None = None

        async def create_room(
            self,
            *,
            room_name: str,
            identity: str,
            metadata: dict[str, Any],
            ttl_seconds: int,
        ) -> VoiceRoom:
            self.metadata = metadata
            return VoiceRoom(room_name=room_name, token="short-lived-token", url="ws://test")

    app = _app()
    fake = FakeRooms()
    app.dependency_overrides[get_demo_clinic_slug] = lambda: tenants["A"]["slug"]
    app.dependency_overrides[get_voice_room_service] = lambda: fake
    a = tenants["A"]
    async with _app_client(app) as c:
        r = await c.post(
            "/api/v1/voice/session",
            json={"caller_number": "+5571999922222", "clinic_code": a["slug"]},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token"] == "short-lived-token"
        assert fake.metadata is not None
        assert fake.metadata["clinic_id"] == str(a["clinic"])
        assert fake.metadata["channel"] == "web"
        assert fake.metadata["caller_number"] == "+5571999922222"
        assert "agent_config" in fake.metadata and "timezone" in fake.metadata
        async with app_conn(a["clinic"]) as conn:
            assert (
                await conn.fetchval(
                    "SELECT count(*) FROM calls WHERE id = $1", uuid.UUID(body["call_id"])
                )
                == 1
            )

        bad = await c.post("/api/v1/voice/session", json={"caller_number": "123"})
        assert bad.status_code == 422


async def test_internal_idempotency_returns_same_book_and_request(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    started = await _internal(
        client,
        "/internal/agent/calls/start",
        {"clinic_id": str(a["clinic"]), "channel": "web", "caller_number": "+5571999933333"},
    )
    ctx = {"clinic_id": str(a["clinic"]), "call_id": started.json()["call_id"]}
    slots = await _internal(
        client,
        "/internal/agent/tools/list-slots",
        {**ctx, "service_id": str(a["service"]), "date": future_monday(9).isoformat()},
    )
    assert slots.status_code == 200 and slots.json(), slots.text
    slot = slots.json()[0]
    body = {
        **ctx,
        "service_id": str(a["service"]),
        "professional_id": slot["professional_id"],
        "starts_at": slot["starts_at"],
        "customer_name": "Idem",
    }
    key = str(uuid.uuid4())
    first = await _internal(client, "/internal/agent/tools/book", body, {"Idempotency-Key": key})
    second = await _internal(client, "/internal/agent/tools/book", body, {"Idempotency-Key": key})
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["appointment_id"] == second.json()["appointment_id"]

    cancel_body = {**ctx, "appointment_id": first.json()["appointment_id"]}
    cancel_key = str(uuid.uuid4())
    cancel1 = await _internal(
        client, "/internal/agent/tools/cancel", cancel_body, {"Idempotency-Key": cancel_key}
    )
    cancel2 = await _internal(
        client, "/internal/agent/tools/cancel", cancel_body, {"Idempotency-Key": cancel_key}
    )
    assert cancel1.status_code == 200 and cancel2.status_code == 200
    assert cancel1.json()["status"] == "canceled"

    request_body = {
        **ctx,
        "type": "message",
        "title": "Recado idempotente",
        "description": "x",
    }
    req_key = str(uuid.uuid4())
    req1 = await _internal(
        client,
        "/internal/agent/tools/create-service-request",
        request_body,
        {"Idempotency-Key": req_key},
    )
    req2 = await _internal(
        client,
        "/internal/agent/tools/create-service-request",
        request_body,
        {"Idempotency-Key": req_key},
    )
    assert req1.status_code == 200 and req2.status_code == 200
    assert req1.json()["request_id"] == req2.json()["request_id"]


async def test_openapi_is_available_outside_production(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/v1/auth/login",
        "/api/v1/requests",
        "/api/v1/calls",
        "/api/v1/events/stream",
        "/api/v1/voice/session",
    ):
        assert path in paths


async def test_clinic_settings_and_catalog_crud(
    client: httpx.AsyncClient, tenants: dict[str, dict[str, Any]]
) -> None:
    a = tenants["A"]
    admin = await _login(client, a["slug"], "A@example.test")
    headers = _bearer(admin)

    settings = (await client.get("/api/v1/settings/clinic", headers=headers)).json()
    assert settings["name"].lower() == "clinic a"
    saved = await client.put(
        "/api/v1/settings/clinic",
        headers=headers,
        json={
            "name": settings["name"],
            "timezone": settings["timezone"],
            "business_hours": settings["business_hours"],
            "max_call_seconds": settings["max_call_seconds"],
            "max_concurrent_calls": settings["max_concurrent_calls"],
            "daily_minute_budget": settings["daily_minute_budget"],
            "daily_cost_budget_cents": settings["daily_cost_budget_cents"],
            "kill_switch": settings["kill_switch"],
            "hidden_caller_policy": settings["hidden_caller_policy"],
        },
    )
    assert saved.status_code == 200, saved.text

    suffix = uuid.uuid4().hex[:6]
    service = await client.post(
        "/api/v1/services",
        headers=headers,
        json={"name": f"Servico {suffix}", "duration_min": 30, "price_cents": 12000},
    )
    assert service.status_code == 200, service.text
    service_id = service.json()["id"]
    patched = await client.patch(
        f"/api/v1/services/{service_id}", headers=headers, json={"duration_min": 45}
    )
    assert patched.status_code == 200 and patched.json()["duration_min"] == 45
    assert (
        await client.delete(f"/api/v1/services/{service_id}", headers=headers)
    ).status_code == 204

    professional = await client.post(
        "/api/v1/professionals",
        headers=headers,
        json={
            "name": f"Profissional {suffix}",
            "specialty": "Clinica",
            "service_ids": [service_id],
        },
    )
    assert professional.status_code == 200, professional.text
    professional_id = professional.json()["id"]
    assert service_id in professional.json()["service_ids"]
    assert (
        await client.delete(f"/api/v1/professionals/{professional_id}", headers=headers)
    ).status_code == 204
