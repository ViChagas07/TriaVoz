"""Test fixtures.

DB tests need a PostgreSQL database migrated with Alembic and these env vars (asyncpg-style DSNs):
  TRIAVOZ_TEST_OWNER_DSN  postgresql://triavoz_owner:...@host:5432/triavoz   (seeding/cleanup only)
  TRIAVOZ_TEST_APP_DSN    postgresql://triavoz_app:...@host:5432/triavoz     (what the API uses)
  TRIAVOZ_TEST_OPS_DSN    postgresql://triavoz_ops:...@host:5432/triavoz     (global-block checks)
Without them, tests marked `db` are skipped (unit tests still run).
"""

from __future__ import annotations

import os
import random
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest

OWNER_DSN = os.environ.get("TRIAVOZ_TEST_OWNER_DSN")
APP_DSN = os.environ.get("TRIAVOZ_TEST_APP_DSN")
OPS_DSN = os.environ.get("TRIAVOZ_TEST_OPS_DSN")
HAVE_DB = bool(OWNER_DSN and APP_DSN and OPS_DSN)

if APP_DSN:  # must happen before triavoz.config is first imported/cached
    os.environ["TRIAVOZ_DATABASE_URL_APP"] = APP_DSN.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

# Integration tests share the tenant stores in a dedicated Redis DB when one is provided.
if os.environ.get("TRIAVOZ_TEST_REDIS_URL"):
    os.environ["TRIAVOZ_REDIS_URL"] = os.environ["TRIAVOZ_TEST_REDIS_URL"]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if HAVE_DB:
        return
    skip = pytest.mark.skip(reason="TRIAVOZ_TEST_*_DSN not set (see tests/conftest.py)")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


def future_monday(weeks_ahead: int = 2) -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7) + timedelta(weeks=weeks_ahead)


async def _set_ctx(conn: asyncpg.Connection, clinic_id: uuid.UUID | None) -> None:
    await conn.execute("SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id or ""))


async def seed_clinic(label: str) -> dict[str, Any]:
    ids = {
        k: uuid.uuid4()
        for k in (
            "clinic",
            "user",
            "phone",
            "service",
            "prof",
            "avail",
            "off",
            "call",
            "turn",
            "event",
            "appt",
            "req",
            "reqev",
            "cfg",
            "blocked",
            "settings",
            "refresh",
        )
    }
    e164 = "+5571" + "".join(random.choices("0123456789", k=9))
    slug = f"t-{label}-{uuid.uuid4().hex[:8]}"
    c = ids["clinic"]
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await _set_ctx(conn, c)
            await conn.execute(f"""
              INSERT INTO clinics (id, name, slug) VALUES ('{c}', 'Clinic {label}', '{slug}');
              INSERT INTO clinic_users (id, clinic_id, email, password_hash, full_name, role)
                VALUES ('{ids["user"]}', '{c}', '{label}@example.test', 'x', 'User {label}', 'admin');
              INSERT INTO clinic_settings (clinic_id) VALUES ('{c}');
              INSERT INTO refresh_tokens (id, clinic_id, user_id, family_id, token_hash, expires_at,
                  created_ip, user_agent)
                VALUES ('{ids["refresh"]}', '{c}', '{ids["user"]}', '{ids["refresh"]}',
                  sha256('{ids["refresh"]}'::bytea), now() + interval '30 days',
                  '203.0.113.10', 'seed-test');
              INSERT INTO phone_numbers (id, clinic_id, e164) VALUES ('{ids["phone"]}', '{c}', '{e164}');
              INSERT INTO services (id, clinic_id, name, duration_min, price_cents)
                VALUES ('{ids["service"]}', '{c}', 'Consulta {label}', 30, 10000);
              INSERT INTO professionals (id, clinic_id, name) VALUES ('{ids["prof"]}', '{c}', 'Dra. {label}');
              INSERT INTO professional_services (clinic_id, professional_id, service_id)
                VALUES ('{c}', '{ids["prof"]}', '{ids["service"]}');
              INSERT INTO availability_rules (id, clinic_id, professional_id, weekday, start_time, end_time)
                SELECT gen_random_uuid(), '{c}', '{ids["prof"]}', d, '09:00', '12:00' FROM generate_series(1,7) d;
              INSERT INTO time_off (id, clinic_id, professional_id, starts_at, ends_at)
                VALUES ('{ids["off"]}', '{c}', '{ids["prof"]}', now() + interval '400 days', now() + interval '401 days');
              INSERT INTO calls (id, clinic_id, channel, caller_number)
                VALUES ('{ids["call"]}', '{c}', 'web', '+5571988887777');
              INSERT INTO call_turns (id, clinic_id, call_id, seq, speaker, content)
                VALUES ('{ids["turn"]}', '{c}', '{ids["call"]}', 0, 'patient', 'oi');
              INSERT INTO call_events (id, clinic_id, call_id, event_type)
                VALUES ('{ids["event"]}', '{c}', '{ids["call"]}', 'call_started');
              INSERT INTO appointments (id, clinic_id, call_id, professional_id, service_id,
                  customer_name, customer_phone, starts_at, ends_at)
                VALUES ('{ids["appt"]}', '{c}', '{ids["call"]}', '{ids["prof"]}', '{ids["service"]}',
                  'Fulano', '+5571988887777', now() + interval '300 days', now() + interval '300 days 30 minutes');
              INSERT INTO service_requests (id, clinic_id, call_id, type, title)
                VALUES ('{ids["req"]}', '{c}', '{ids["call"]}', 'message', 'recado');
              INSERT INTO request_events (id, clinic_id, request_id, event_type)
                VALUES ('{ids["reqev"]}', '{c}', '{ids["req"]}', 'created');
              INSERT INTO agent_configs (id, clinic_id, version, status, config)
                VALUES ('{ids["cfg"]}', '{c}', 1, 'published', '{{}}'::jsonb);
              INSERT INTO blocked_numbers (id, clinic_id, e164, source)
                VALUES ('{ids["blocked"]}', '{c}', '+5571000000001', 'manual');
              INSERT INTO audit_log (clinic_id, action, resource_type) VALUES ('{c}', 'seed', 'test');
              INSERT INTO gatekeeper_block_stats (clinic_id, day, reason, count)
                VALUES ('{c}', (now() AT TIME ZONE 'America/Bahia')::date, 'rate_limited', 1);
            """)
    finally:
        await conn.close()
    return {**ids, "slug": slug, "e164": e164}


async def drop_clinic(clinic_id: uuid.UUID) -> None:
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await _set_ctx(conn, clinic_id)
            await conn.execute("DELETE FROM clinics WHERE id = $1", clinic_id)
    finally:
        await conn.close()


async def set_password(clinic_id: uuid.UUID, user_id: uuid.UUID, password: str) -> None:
    """Set a login password through the owner role; used by tests that need a real login."""
    from triavoz.infrastructure.security.passwords import hash_password

    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await _set_ctx(conn, clinic_id)
            await conn.execute(
                "UPDATE clinic_users SET password_hash = $1 WHERE id = $2",
                hash_password(password),
                user_id,
            )
    finally:
        await conn.close()


@pytest.fixture
async def isolated_clinic() -> AsyncIterator[dict[str, Any]]:
    """A fresh clinic per test, removed after it. Prevents cross-test slot/login interference."""
    if not HAVE_DB:
        pytest.skip("no test database")
    clinic = await seed_clinic("isolated")
    try:
        yield clinic
    finally:
        await drop_clinic(clinic["clinic"])


@pytest.fixture(scope="session")
async def tenants() -> AsyncIterator[dict[str, dict[str, Any]]]:
    if not HAVE_DB:
        pytest.skip("no test database")
    a, b = await seed_clinic("a"), await seed_clinic("b")
    ops = await asyncpg.connect(OPS_DSN)
    global_e164 = "+5599" + "".join(random.choices("0123456789", k=9))
    await ops.execute(
        "INSERT INTO blocked_numbers (clinic_id, e164, source) VALUES (NULL, $1, 'rate_limit')",
        global_e164,
    )
    try:
        yield {"A": a, "B": b, "global_e164": {"e164": global_e164}}
    finally:
        await ops.execute(
            "DELETE FROM blocked_numbers WHERE clinic_id IS NULL AND e164 = $1", global_e164
        )
        await ops.close()
        await drop_clinic(a["clinic"])
        await drop_clinic(b["clinic"])


@asynccontextmanager
async def app_conn(clinic_id: uuid.UUID | None) -> AsyncIterator[asyncpg.Connection]:
    """A connection as the RUNTIME role, inside a transaction, with (optional) tenant context."""
    conn = await asyncpg.connect(APP_DSN)
    tr = conn.transaction()
    await tr.start()
    try:
        if clinic_id is not None:
            await _set_ctx(conn, clinic_id)
        yield conn
    finally:
        await tr.rollback()
        await conn.close()
