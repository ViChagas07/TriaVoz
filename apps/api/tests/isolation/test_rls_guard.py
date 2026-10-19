"""Guard test: a new table that carries clinic_id but forgot RLS breaks the build."""

from __future__ import annotations

import asyncpg
import pytest

from tests.conftest import OWNER_DSN

pytestmark = pytest.mark.db

QUERY = """
SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND (c.relname = 'clinics' OR EXISTS (
        SELECT 1 FROM pg_attribute a
        WHERE a.attrelid = c.oid AND a.attname = 'clinic_id' AND NOT a.attisdropped))
"""


async def test_every_tenant_table_has_enabled_and_forced_rls_with_a_policy() -> None:
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        rows = await conn.fetch(QUERY)
    finally:
        await conn.close()
    assert len(rows) >= 15, "expected the full tenant table set"
    bad = [
        r["relname"]
        for r in rows
        if not (r["relrowsecurity"] and r["relforcerowsecurity"] and r["policies"] >= 1)
    ]
    assert not bad, f"tables without ENABLE+FORCE RLS and a policy: {bad}"
