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
        caller_verified: bool = False,
        caller_identity_hash: bytes | None = None,
    ) -> UUID:
        result = (
            await self._s.execute(
                text(
                    "INSERT INTO calls (id, clinic_id, channel, room_name, caller_number, "
                    "caller_verified, caller_identity_hash) "
                    "VALUES (:id, app_current_clinic_id(), :channel, :room, :caller, "
                    ":verified, :identity) RETURNING id"
                ),
                {
                    "id": call_id,
                    "channel": channel,
                    "room": room_name,
                    "caller": caller_number,
                    "verified": caller_verified,
                    "identity": caller_identity_hash,
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

    async def record_gatekeeper_block(self, reason: str) -> None:
        """Aggregate refusals per clinic/day/reason (no caller identifier is stored).

        Uses a savepoint: an observability write must never turn a safe refusal into a 500.
        """
        try:
            async with self._s.begin_nested():
                await self._s.execute(
                    text(
                        "INSERT INTO gatekeeper_block_stats (clinic_id, day, reason, count) "
                        "SELECT app_current_clinic_id(), "
                        "(now() AT TIME ZONE timezone)::date, :reason, 1 "
                        "FROM clinics WHERE id = app_current_clinic_id() "
                        "ON CONFLICT (clinic_id, day, reason) DO UPDATE "
                        "SET count = gatekeeper_block_stats.count + 1, updated_at = now()"
                    ),
                    {"reason": reason[:80]},
                )
        except Exception:  # pragma: no cover - best effort by design
            import logging

            logging.getLogger("triavoz.voice").warning("gatekeeper block metric skipped")
