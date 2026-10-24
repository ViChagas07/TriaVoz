"""Retention/expurgo: bounded transcript deletion through the narrow definer functions."""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg
import pytest

from tests.conftest import OPS_DSN, OWNER_DSN

pytestmark = pytest.mark.db


async def _seed_call(
    clinic: uuid.UUID,
    *,
    status: str,
    ended_days_ago: int | None,
    phone: str,
    summary: str,
    with_turn: bool = True,
) -> tuple[uuid.UUID, uuid.UUID]:
    call_id, turn_id = uuid.uuid4(), uuid.uuid4()
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_clinic_id', $1, true)", str(clinic))
            await conn.execute(
                "INSERT INTO calls (id, clinic_id, channel, caller_number, status, summary, "
                "started_at, ended_at) VALUES ($1, $2, 'web', $3, $4, $5, "
                "CASE WHEN $6::int IS NULL THEN now() "
                "ELSE now() - ($6::int * interval '1 day') END, "
                "CASE WHEN $6::int IS NULL THEN NULL "
                "ELSE now() - ($6::int * interval '1 day') + interval '5 minutes' END)",
                call_id,
                clinic,
                phone,
                status,
                summary,
                ended_days_ago,
            )
            if with_turn:
                await conn.execute(
                    "INSERT INTO call_turns (id, clinic_id, call_id, seq, speaker, content) "
                    "VALUES ($1, $2, $3, 0, 'patient', 'conteudo sensivel')",
                    turn_id,
                    clinic,
                    call_id,
                )
    finally:
        await conn.close()
    return call_id, turn_id


async def test_purge_deletes_only_expired_transcripts_and_audits(
    isolated_clinic: dict[str, Any],
) -> None:
    clinic = isolated_clinic["clinic"]
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_clinic_id', $1, true)", str(clinic))
            await conn.execute(
                "UPDATE clinic_settings SET transcript_retention_days = 1 WHERE clinic_id = $1",
                clinic,
            )
    finally:
        await conn.close()

    old_call, old_turn = await _seed_call(
        clinic, status="completed", ended_days_ago=3, phone="+5571900011111", summary="resumo"
    )
    active_call, active_turn = await _seed_call(
        clinic, status="in_progress", ended_days_ago=None, phone="+5571900022222", summary="ativo"
    )
    empty_call, _ = await _seed_call(
        clinic,
        status="completed",
        ended_days_ago=5,
        phone="+5571900033333",
        summary="sem turnos",
        with_turn=False,
    )

    ops = await asyncpg.connect(OPS_DSN)
    try:
        rows = await ops.fetch("SELECT clinic_id, deleted FROM purge_expired_transcripts(1000)")
        assert any(row["clinic_id"] == clinic and int(row["deleted"]) >= 1 for row in rows)

        # Ops still cannot read tenant tables directly (only EXECUTE on the functions).
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await ops.fetch("SELECT * FROM call_turns LIMIT 1")
    finally:
        await ops.close()

    check = await asyncpg.connect(OWNER_DSN)
    try:
        async with check.transaction():
            await check.execute("SELECT set_config('app.current_clinic_id', $1, true)", str(clinic))
            old_row = await check.fetchrow(
                "SELECT caller_number, summary FROM calls WHERE id = $1", old_call
            )
            empty_row = await check.fetchrow(
                "SELECT caller_number, summary FROM calls WHERE id = $1", empty_call
            )
            active_row = await check.fetchrow(
                "SELECT caller_number, summary FROM calls WHERE id = $1", active_call
            )
            old_turns = await check.fetchval(
                "SELECT count(*) FROM call_turns WHERE id = $1", old_turn
            )
            active_turns = await check.fetchval(
                "SELECT count(*) FROM call_turns WHERE id = $1", active_turn
            )
            audit = await check.fetchval(
                "SELECT count(*) FROM audit_log WHERE clinic_id = $1 "
                "AND action = 'retention.transcripts'",
                clinic,
            )
    finally:
        await check.close()
    assert old_turns == 0
    assert active_turns == 1
    assert old_row is not None and old_row["caller_number"] is None
    assert old_row is not None and old_row["summary"] is None
    assert empty_row is not None and empty_row["caller_number"] is None
    assert empty_row is not None and empty_row["summary"] is None
    assert active_row is not None and active_row["caller_number"] == "+5571900022222"
    assert active_row is not None and active_row["summary"] == "ativo"
    assert audit and audit >= 1
