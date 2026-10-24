"""Observability persistence: tenant-scoped, PII-free gatekeeper aggregates."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.db.voice_repo import PgVoiceSessionRepository

pytestmark = pytest.mark.db


async def test_gatekeeper_blocks_are_aggregated_per_clinic_day_and_reason(
    tenants: dict[str, dict[str, Any]],
) -> None:
    a = tenants["A"]["clinic"]
    async with tenant_session(a) as session:
        repo = PgVoiceSessionRepository(session)
        await repo.record_gatekeeper_block("rate_limited")
        await repo.record_gatekeeper_block("rate_limited")
        await repo.record_gatekeeper_block("kill_switch")

    async with tenant_session(a) as session:
        rows = (
            await session.execute(
                text(
                    "SELECT reason, sum(count)::int AS total FROM gatekeeper_block_stats "
                    "GROUP BY reason ORDER BY reason"
                )
            )
        ).all()
    totals = {row.reason: row.total for row in rows}
    assert totals["rate_limited"] >= 2
    assert totals["kill_switch"] >= 1
    # No caller number or free-text column exists by design.
    async with tenant_session(a) as session:
        columns = (
            await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'gatekeeper_block_stats'"
                )
            )
        ).scalars()
    assert set(columns) == {"clinic_id", "day", "reason", "count", "updated_at"}
