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
                    "COALESCE(s.max_concurrent_calls, 3) AS max_concurrent_calls, "
                    "COALESCE(s.max_call_seconds, 300) AS max_call_seconds, "
                    "COALESCE(s.daily_minute_budget, 120) AS daily_minute_budget, "
                    "COALESCE(s.daily_cost_budget_cents, 500) AS daily_cost_budget_cents, "
                    "COALESCE(s.hidden_caller_policy, 'allow') AS hidden_caller_policy, "
                    "s.business_hours, "
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
            "max_concurrent_calls": row.max_concurrent_calls,
            "max_call_seconds": row.max_call_seconds,
            "daily_minute_budget": row.daily_minute_budget,
            "daily_cost_budget_cents": row.daily_cost_budget_cents,
            "hidden_caller_policy": row.hidden_caller_policy,
            "business_hours": row.business_hours,
            "agent_config": row.agent_config or {},
        }

    async def create_call(
        self,
        *,
        call_id: UUID,
        room_name: str,
        caller_number: str | None,
        channel: str,
    ) -> UUID:
        result = (
            await self._s.execute(
                text(
                    "INSERT INTO calls (id, clinic_id, channel, room_name, caller_number) "
                    "VALUES (:id, app_current_clinic_id(), :channel, :room, :caller) "
                    "RETURNING id"
                ),
                {
                    "id": call_id,
                    "channel": channel,
                    "room": room_name,
                    "caller": caller_number,
                },
            )
        ).scalar_one()
        return UUID(str(result))

    async def fail_call(self, call_id: UUID) -> None:
        await self._s.execute(
            text(
                "UPDATE calls SET status = 'failed', end_reason = 'voice_provider_unavailable', "
                "ended_at = now() WHERE id = :id"
            ),
            {"id": call_id},
        )
