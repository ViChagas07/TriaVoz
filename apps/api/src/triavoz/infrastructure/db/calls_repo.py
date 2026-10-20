"""Conversation log persistence (calls, turns). Runs inside a tenant transaction."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.shared_kernel.errors import NotFound


class PgCallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def start(
        self, *, clinic_id: UUID, channel: str, room_name: str | None, caller_number: str | None
    ) -> UUID:
        new_id = (
            await self._s.execute(
                text(
                    "INSERT INTO calls (clinic_id, channel, room_name, caller_number) "
                    "VALUES (:cid, :ch, :room, :caller) RETURNING id"
                ),
                {"cid": clinic_id, "ch": channel, "room": room_name, "caller": caller_number},
            )
        ).scalar_one()
        return UUID(str(new_id))

    async def caller_number(self, call_id: UUID) -> str:
        row = (
            await self._s.execute(
                text("SELECT caller_number FROM calls WHERE id = :id"), {"id": call_id}
            )
        ).scalar()
        if not row:
            raise NotFound("call")
        return str(row)

    async def add_turns(self, clinic_id: UUID, call_id: UUID, turns: list[dict[str, Any]]) -> None:
        for t in turns:
            await self._s.execute(
                text(
                    "INSERT INTO call_turns (clinic_id, call_id, seq, speaker, content, tool_name, "
                    "tool_payload, started_at, stt_confidence) VALUES (:cid, :call, :seq, :sp, "
                    ":content, :tool, CAST(:payload AS jsonb), :started, :conf) "
                    "ON CONFLICT (call_id, seq) DO NOTHING"
                ),
                {
                    "cid": clinic_id,
                    "call": call_id,
                    "seq": t["seq"],
                    "sp": t["speaker"],
                    "content": t.get("content", ""),
                    "tool": t.get("tool_name"),
                    "payload": t.get("tool_payload_json"),
                    "started": t.get("started_at") or datetime.now().astimezone(),
                    "conf": t.get("stt_confidence"),
                },
            )

    async def end(
        self,
        call_id: UUID,
        *,
        status: str,
        end_reason: str | None,
        duration_seconds: int | None,
        usage_json: str,
        latency_json: str,
        cost_cents: float,
        handoff_requested: bool = False,
        handoff_completed: bool = False,
    ) -> None:
        await self._s.execute(
            text(
                "UPDATE calls SET ended_at = now(), status = :status, end_reason = :reason, "
                "duration_seconds = :dur, usage = CAST(:usage AS jsonb), "
                "latency_ms = CAST(:lat AS jsonb), cost_cents = :cost, "
                "handoff_requested = :handoff, handoff_completed = :handoff_done "
                "WHERE id = :id"
            ),
            {
                "id": call_id,
                "status": status,
                "reason": end_reason,
                "dur": duration_seconds,
                "usage": usage_json,
                "lat": latency_json,
                "cost": cost_cents,
                "handoff": handoff_requested,
                "handoff_done": handoff_completed,
            },
        )
