"""Tenant isolation — the most important test suite in the project. Blocks merge in CI."""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg
import pytest
from sqlalchemy import text

from tests.conftest import OPS_DSN, OWNER_DSN, app_conn
from triavoz.infrastructure.db.session import get_engine, tenant_session

pytestmark = pytest.mark.db


async def _tenant_tables() -> list[str]:
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name = 'clinic_id' ORDER BY 1"
        )
    finally:
        await conn.close()
    return [r["table_name"] for r in rows] + ["clinics"]


@pytest.mark.parametrize("me,other", [("A", "B"), ("B", "A")])
async def test_each_tenant_sees_only_its_own_rows_in_every_table(
    tenants: dict[str, dict[str, Any]], me: str, other: str
) -> None:
    mine, theirs = tenants[me]["clinic"], tenants[other]["clinic"]
    for table in await _tenant_tables():
        col = "id" if table == "clinics" else "clinic_id"
        async with app_conn(mine) as conn:
            own = await conn.fetchval(f"SELECT count(*) FROM {table} WHERE {col} = $1", mine)  # noqa: S608
            foreign = await conn.fetchval(f"SELECT count(*) FROM {table} WHERE {col} = $1", theirs)  # noqa: S608
            unexpected = await conn.fetchval(
                f"SELECT count(*) FROM {table} WHERE {col} IS NOT NULL AND {col} <> $1",  # noqa: S608
                mine,
            )
        assert own >= 1, f"{table}: seed row not visible to its own tenant"
        assert foreign == 0, f"{table}: LEAK of the other tenant's rows"
        assert unexpected == 0, f"{table}: rows of some other tenant are visible"


async def test_without_tenant_context_nothing_is_visible(
    tenants: dict[str, dict[str, Any]],
) -> None:
    for table in await _tenant_tables():
        async with app_conn(None) as conn:
            if (
                table == "blocked_numbers"
            ):  # global blocks (clinic_id NULL) are intentionally readable
                n = await conn.fetchval(
                    "SELECT count(*) FROM blocked_numbers WHERE clinic_id IS NOT NULL"
                )
            else:
                n = await conn.fetchval(f"SELECT count(*) FROM {table}")  # noqa: S608
        assert n == 0, f"{table}: visible without tenant context"


async def test_cross_tenant_insert_is_rejected_by_rls(tenants: dict[str, dict[str, Any]]) -> None:
    a, b = tenants["A"]["clinic"], tenants["B"]["clinic"]
    async with app_conn(a) as conn:
        with pytest.raises(asyncpg.PostgresError) as exc:
            await conn.execute(
                "INSERT INTO services (clinic_id, name, duration_min) VALUES ($1, 'evil', 10)", b
            )
    assert exc.value.sqlstate == "42501"  # new row violates row-level security policy


async def test_cross_tenant_update_and_delete_touch_zero_rows(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a, b = tenants["A"]["clinic"], tenants["B"]["clinic"]
    async with app_conn(a) as conn:
        assert (
            await conn.execute("UPDATE services SET name = 'hacked' WHERE clinic_id = $1", b)
            == "UPDATE 0"
        )
        assert await conn.execute("DELETE FROM appointments WHERE clinic_id = $1", b) == "DELETE 0"
        # moving a row of mine into another tenant is also refused (WITH CHECK)
        with pytest.raises(asyncpg.PostgresError) as exc:
            await conn.execute("UPDATE services SET clinic_id = $1 WHERE clinic_id = $2", b, a)
        assert exc.value.sqlstate == "42501"


async def test_audit_log_is_append_only_for_the_runtime_role(
    tenants: dict[str, dict[str, Any]],
) -> None:
    async with app_conn(tenants["A"]["clinic"]) as conn:
        with pytest.raises(asyncpg.PostgresError) as exc:
            await conn.execute("UPDATE audit_log SET action = 'tampered'")
    assert exc.value.sqlstate == "42501"


async def test_runtime_role_is_unprivileged(tenants: dict[str, dict[str, Any]]) -> None:
    async with app_conn(tenants["A"]["clinic"]) as conn:
        role = await conn.fetchrow(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        owned = await conn.fetchval(
            "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user"
        )
    assert role["rolsuper"] is False
    assert role["rolbypassrls"] is False
    assert owned == 0, "runtime role must not own tables (owners can bypass non-FORCEd RLS)"


async def test_routing_functions_work_without_context_but_tables_stay_closed(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]
    async with app_conn(None) as conn:
        assert await conn.fetchval("SELECT resolve_clinic_by_phone($1)", a["e164"]) == a["clinic"]
        assert await conn.fetchval("SELECT resolve_clinic_by_slug($1)", a["slug"]) == a["clinic"]
        assert await conn.fetchval("SELECT resolve_clinic_by_phone('+10000000000')") is None
        assert await conn.fetchval("SELECT count(*) FROM phone_numbers") == 0


async def test_global_blocks_are_readable_by_tenants_but_not_writable(
    tenants: dict[str, dict[str, Any]],
) -> None:
    g = tenants["global_e164"]["e164"]
    async with app_conn(tenants["A"]["clinic"]) as conn:
        assert await conn.fetchval("SELECT count(*) FROM blocked_numbers WHERE e164 = $1", g) == 1
        assert await conn.execute("DELETE FROM blocked_numbers WHERE e164 = $1", g) == "DELETE 0"
        with pytest.raises(asyncpg.PostgresError):
            await conn.execute(
                "INSERT INTO blocked_numbers (clinic_id, e164, source) VALUES (NULL, '+5500000000009', 'manual')"
            )


async def test_ops_role_can_only_touch_global_blocks(tenants: dict[str, dict[str, Any]]) -> None:
    ops = await asyncpg.connect(OPS_DSN)
    try:
        with pytest.raises(asyncpg.PostgresError) as exc:
            await ops.fetch("SELECT * FROM services")
        assert exc.value.sqlstate == "42501"
        with pytest.raises(asyncpg.PostgresError):
            await ops.execute(
                "INSERT INTO blocked_numbers (clinic_id, e164, source) VALUES ($1, '+5500000000008', 'manual')",
                tenants["A"]["clinic"],
            )
    finally:
        await ops.close()


async def test_tenant_context_does_not_leak_across_pooled_connections(
    tenants: dict[str, dict[str, Any]],
) -> None:
    async with tenant_session(tenants["A"]["clinic"]) as s:
        assert (await s.execute(text("SELECT count(*) FROM services"))).scalar_one() >= 1
    # A fresh transaction on the same pool has NO context → sees nothing.
    async with get_engine().connect() as c:
        assert (await c.execute(text("SELECT count(*) FROM services"))).scalar_one() == 0


async def test_concurrent_requests_of_different_tenants_never_mix(
    tenants: dict[str, dict[str, Any]],
) -> None:
    async def read(label: str) -> set[Any]:
        async with tenant_session(tenants[label]["clinic"]) as s:
            await asyncio.sleep(0)  # force interleaving
            rows = await s.execute(text("SELECT DISTINCT clinic_id FROM services"))
            return {r[0] for r in rows}

    labels = ["A", "B"] * 25
    results = await asyncio.gather(*(read(label) for label in labels))
    for label, seen in zip(labels, results, strict=True):
        assert seen == {tenants[label]["clinic"]}
