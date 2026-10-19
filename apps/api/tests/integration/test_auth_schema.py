"""Schema-level tests for P03 auth: rotating refresh tokens and per-clinic limits."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import asyncpg
import pytest

from tests.conftest import app_conn

pytestmark = pytest.mark.db


def _hash(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


async def test_refresh_token_can_be_inserted_and_revoked_for_own_tenant(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    token_id, family_id = uuid.uuid4(), uuid.uuid4()
    async with app_conn(a["clinic"]) as conn:
        await conn.execute(
            "INSERT INTO refresh_tokens (id, clinic_id, user_id, family_id, token_hash, expires_at) "
            "VALUES ($1, $2, $3, $4, $5, now() + interval '30 days')",
            token_id,
            a["clinic"],
            a["user"],
            family_id,
            _hash("rotation-token-1"),
        )
        await conn.execute(
            "UPDATE refresh_tokens SET revoked_at = now(), revoked_reason = 'rotated' "
            "WHERE id = $1",
            token_id,
        )
        row = await conn.fetchrow(
            "SELECT revoked_at, revoked_reason FROM refresh_tokens WHERE id = $1", token_id
        )
    assert row is not None
    assert row["revoked_at"] is not None
    assert row["revoked_reason"] == "rotated"


async def test_refresh_token_rejects_a_user_from_another_clinic(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a, b = tenants["A"], tenants["B"]
    async with app_conn(a["clinic"]) as conn:
        with pytest.raises(asyncpg.PostgresError) as exc:
            await conn.execute(
                "INSERT INTO refresh_tokens (clinic_id, user_id, family_id, token_hash, expires_at) "
                "VALUES ($1, $2, $3, $4, now() + interval '30 days')",
                a["clinic"],
                b["user"],
                uuid.uuid4(),
                _hash("cross-tenant-user"),
            )
    assert exc.value.sqlstate == "23503"  # composite FK: (clinic_id, user_id) must match


async def test_refresh_token_hash_is_unique_and_exactly_32_bytes(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    token_hash = _hash("duplicate-hash")
    async with app_conn(a["clinic"]) as conn:
        await conn.execute(
            "INSERT INTO refresh_tokens (clinic_id, user_id, family_id, token_hash, expires_at) "
            "VALUES ($1, $2, $3, $4, now() + interval '30 days')",
            a["clinic"],
            a["user"],
            uuid.uuid4(),
            token_hash,
        )
        with pytest.raises(asyncpg.PostgresError) as exc:
            async with conn.transaction():  # savepoint: failed insert must not poison the test tx
                await conn.execute(
                    "INSERT INTO refresh_tokens (clinic_id, user_id, family_id, token_hash, expires_at) "
                    "VALUES ($1, $2, $3, $4, now() + interval '30 days')",
                    a["clinic"],
                    a["user"],
                    uuid.uuid4(),
                    token_hash,
                )
        assert exc.value.sqlstate == "23505"

        with pytest.raises(asyncpg.PostgresError) as exc:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO refresh_tokens (clinic_id, user_id, family_id, token_hash, expires_at) "
                    "VALUES ($1, $2, $3, $4, now() + interval '30 days')",
                    a["clinic"],
                    a["user"],
                    uuid.uuid4(),
                    b"too-short",
                )
        assert exc.value.sqlstate == "23514"


async def test_refresh_token_revocation_fields_move_together(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    async with app_conn(a["clinic"]) as conn:
        with pytest.raises(asyncpg.PostgresError) as exc:
            await conn.execute(
                "INSERT INTO refresh_tokens (clinic_id, user_id, family_id, token_hash, expires_at, "
                "revoked_at) VALUES ($1, $2, $3, $4, now() + interval '30 days', now())",
                a["clinic"],
                a["user"],
                uuid.uuid4(),
                _hash("revoked-without-reason"),
            )
    assert exc.value.sqlstate == "23514"


async def test_clinic_settings_defaults_and_kill_switch_are_tenant_scoped(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a, b = tenants["A"], tenants["B"]
    async with app_conn(a["clinic"]) as conn:
        row = await conn.fetchrow(
            "SELECT daily_minute_budget, max_concurrent_calls, kill_switch "
            "FROM clinic_settings WHERE clinic_id = $1",
            a["clinic"],
        )
        assert row is not None
        assert row["daily_minute_budget"] == 120
        assert row["max_concurrent_calls"] == 3
        assert row["kill_switch"] is False
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM clinic_settings WHERE clinic_id = $1", b["clinic"]
            )
            == 0
        )
        await conn.execute(
            "UPDATE clinic_settings SET kill_switch = true WHERE clinic_id = $1", a["clinic"]
        )
        assert (
            await conn.fetchval(
                "SELECT kill_switch FROM clinic_settings WHERE clinic_id = $1", a["clinic"]
            )
            is True
        )
