from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PgVoiceSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def voice_context(self) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT c.id AS clinic_id, c.timezone, c.is_active, "
                    "COALESCE(s.kill_switch, false) AS kill_switch, "
                    "(SELECT config FROM agent_configs WHERE status = 'published' "
                    " ORDER BY version DESC LIMIT 1) AS agent_config "
                    "FROM clinics c LEFT JOIN clinic_settings s ON s.clinic_id = c.id "
                    "WHERE c.id = app_current_clinic_id()"
                )
            )
        ).first()
        if row is None or not row.is_active:
            return None
        return {
            "clinic_id": row.clinic_id,
            "timezone": row.timezone,
            "kill_switch": row.kill_switch,
            "agent_config": row.agent_config or {},
        }

    async def create_call(self, *, room_name: str, caller_number: str) -> UUID:
        call_id = (
            await self._s.execute(
                text(
                    "INSERT INTO calls (clinic_id, channel, room_name, caller_number) "
                    "VALUES (app_current_clinic_id(), 'web', :room, :caller) RETURNING id"
                ),
                {"room": room_name, "caller": caller_number},
            )
        ).scalar_one()
        return UUID(str(call_id))

    async def fail_call(self, call_id: UUID) -> None:
        await self._s.execute(
            text(
                "UPDATE calls SET status = 'failed', end_reason = 'voice_provider_unavailable', "
                "ended_at = now() WHERE id = :id"
            ),
            {"id": call_id},
        )
