"""Tenant-bound queries for the gatekeeper and post-call scoring."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.application.abuse.ports import DailyUsage, ScoringInputs


class PgAbuseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def is_blocked(self, e164: str) -> bool:
        # RLS exposes the clinic's own rows plus global rows; expired blocks stop applying.
        value = (
            await self._s.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM blocked_numbers WHERE e164 = :e164 "
                    "AND (expires_at IS NULL OR expires_at > now()))"
                ),
                {"e164": e164},
            )
        ).scalar_one()
        return bool(value)

    async def daily_usage(self, *, max_call_seconds: int) -> DailyUsage:
        row = (
            await self._s.execute(
                text(
                    "WITH tz AS (SELECT timezone FROM clinics WHERE id = app_current_clinic_id()), "
                    "day AS (SELECT date_trunc('day', now() AT TIME ZONE tz.timezone) "
                    "        AT TIME ZONE tz.timezone AS start FROM tz) "
                    "SELECT COALESCE(SUM(CASE WHEN ended_at IS NOT NULL "
                    "  THEN COALESCE(duration_seconds, "
                    "       EXTRACT(EPOCH FROM (ended_at - started_at))::int) "
                    "  ELSE LEAST(EXTRACT(EPOCH FROM (now() - started_at)), :max_seconds) "
                    "END), 0) AS seconds, "
                    "COALESCE(SUM(cost_cents), 0) AS cost_cents "
                    "FROM calls, day WHERE started_at >= day.start"
                ),
                {"max_seconds": max_call_seconds},
            )
        ).one()
        return DailyUsage(seconds=float(row.seconds), cost_cents=float(row.cost_cents))

    async def scoring_inputs(
        self, call_id: UUID, *, abusive_language: bool = False
    ) -> ScoringInputs | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT c.id, c.status, "
                    "COALESCE(c.duration_seconds, "
                    "  EXTRACT(EPOCH FROM (COALESCE(c.ended_at, now()) - c.started_at))::int, 0) "
                    "  AS duration_seconds, "
                    "(SELECT count(*) FROM call_turns t WHERE t.call_id = c.id "
                    " AND t.speaker = 'patient' AND btrim(t.content) <> '') AS patient_turns, "
                    "(SELECT count(*) FROM call_turns t WHERE t.call_id = c.id "
                    " AND t.speaker = 'tool' "
                    " AND COALESCE(t.tool_payload->>'is_error', 'false') = 'false') "
                    "  AS successful_tool_calls, "
                    "(SELECT avg(t.stt_confidence) FROM call_turns t WHERE t.call_id = c.id "
                    " AND t.speaker = 'patient' AND t.stt_confidence IS NOT NULL) "
                    "  AS average_stt_confidence, "
                    "EXISTS(SELECT 1 FROM appointments a WHERE a.call_id = c.id) "
                    "  AS appointment_created, "
                    "EXISTS(SELECT 1 FROM service_requests r WHERE r.call_id = c.id) "
                    "  AS request_created, "
                    "(SELECT count(*) FROM calls p WHERE p.clinic_id = c.clinic_id "
                    " AND p.caller_number = c.caller_number AND p.id <> c.id "
                    " AND p.started_at >= c.started_at - interval '24 hours' "
                    " AND p.started_at <= c.started_at) AS previous_calls_24h "
                    "FROM calls c WHERE c.id = :id"
                ),
                {"id": call_id},
            )
        ).first()
        if row is None:
            return None
        confidence = row.average_stt_confidence
        return ScoringInputs(
            call_id=UUID(str(row.id)),
            status=str(row.status),
            duration_seconds=int(row.duration_seconds or 0),
            patient_turns=int(row.patient_turns or 0),
            successful_tool_calls=int(row.successful_tool_calls or 0),
            average_stt_confidence=float(confidence) if confidence is not None else None,
            appointment_created=bool(row.appointment_created),
            request_created=bool(row.request_created),
            previous_calls_24h=int(row.previous_calls_24h or 0),
            abusive_language=abusive_language,
        )

    async def apply_call_score(
        self, call_id: UUID, *, score: int, flags: tuple[str, ...], needs_review: bool
    ) -> None:
        payload = json.dumps(list(flags), ensure_ascii=False)
        await self._s.execute(
            text(
                "UPDATE calls SET abuse_score = :score, "
                "suspicion_flags = CAST(:flags AS jsonb) WHERE id = :id"
            ),
            {"id": call_id, "score": score, "flags": payload},
        )
        # Keep the linked request's badge data in sync with the call that created it.
        await self._s.execute(
            text(
                "UPDATE service_requests SET suspicion_flags = CAST(:flags AS jsonb), "
                "updated_at = now() WHERE call_id = :id"
            ),
            {"id": call_id, "flags": payload},
        )
