"""PostgreSQL queries for the staff API and internal service-request tool.

All methods are called inside `tenant_session(clinic_id)`. Explicit clinic filters are defence in
depth; RLS is the isolation mechanism. Dynamic SQL is deliberately avoided: optional predicates
use `:param IS NULL OR ...`, so every value remains a bound parameter.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.shared_kernel.errors import Conflict, NotFound


def _row(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


def _rows(result: Any) -> list[dict[str, Any]]:
    return [dict(r._mapping) for r in result]


class PgStaffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def clinic_timezone(self) -> str:
        value = (
            await self._s.execute(
                text("SELECT timezone FROM clinics WHERE id = app_current_clinic_id()")
            )
        ).scalar_one()
        return str(value)

    async def get_clinic_settings(self) -> dict[str, Any]:
        row = (
            await self._s.execute(
                text(
                    "SELECT c.name, c.slug, c.timezone, "
                    "COALESCE(s.business_hours, NULL) AS business_hours, "
                    "COALESCE(s.max_call_seconds, 300) AS max_call_seconds, "
                    "COALESCE(s.max_concurrent_calls, 3) AS max_concurrent_calls, "
                    "COALESCE(s.daily_minute_budget, 120) AS daily_minute_budget, "
                    "COALESCE(s.daily_cost_budget_cents, 500) AS daily_cost_budget_cents, "
                    "COALESCE(s.kill_switch, false) AS kill_switch, "
                    "COALESCE(s.hidden_caller_policy, 'allow') AS hidden_caller_policy "
                    "FROM clinics c LEFT JOIN clinic_settings s ON s.clinic_id = c.id "
                    "WHERE c.id = app_current_clinic_id()"
                )
            )
        ).first()
        if row is None:
            raise NotFound("clinic")
        return _row(row)

    async def update_clinic_settings(
        self,
        *,
        name: str,
        timezone: str,
        business_hours: dict[str, Any] | None,
        max_call_seconds: int,
        max_concurrent_calls: int,
        daily_minute_budget: int,
        daily_cost_budget_cents: int,
        kill_switch: bool,
        hidden_caller_policy: str,
    ) -> dict[str, Any]:
        await self._s.execute(
            text(
                "UPDATE clinics SET name = :name, timezone = :tz WHERE id = app_current_clinic_id()"
            ),
            {"name": name, "tz": timezone},
        )
        await self._s.execute(
            text(
                "INSERT INTO clinic_settings (clinic_id, business_hours, max_call_seconds, "
                "max_concurrent_calls, daily_minute_budget, daily_cost_budget_cents, kill_switch, "
                "hidden_caller_policy, updated_at) "
                "VALUES (app_current_clinic_id(), CAST(:hours AS jsonb), :max_seconds, "
                ":max_concurrent, :minutes, :cost, :kill, :hidden, now()) "
                "ON CONFLICT (clinic_id) DO UPDATE SET business_hours = EXCLUDED.business_hours, "
                "max_call_seconds = EXCLUDED.max_call_seconds, "
                "max_concurrent_calls = EXCLUDED.max_concurrent_calls, "
                "daily_minute_budget = EXCLUDED.daily_minute_budget, "
                "daily_cost_budget_cents = EXCLUDED.daily_cost_budget_cents, "
                "kill_switch = EXCLUDED.kill_switch, "
                "hidden_caller_policy = EXCLUDED.hidden_caller_policy, updated_at = now()"
            ),
            {
                "hours": json.dumps(business_hours) if business_hours is not None else None,
                "max_seconds": max_call_seconds,
                "max_concurrent": max_concurrent_calls,
                "minutes": daily_minute_budget,
                "cost": daily_cost_budget_cents,
                "kill": kill_switch,
                "hidden": hidden_caller_policy,
            },
        )
        return await self.get_clinic_settings()

    async def list_services(self) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, name, duration_min, price_cents, is_active FROM services "
                "WHERE clinic_id = app_current_clinic_id() ORDER BY is_active DESC, name"
            )
        )
        return _rows(rows)

    async def create_service(
        self, *, name: str, duration_min: int, price_cents: int
    ) -> dict[str, Any]:
        try:
            row = (
                await self._s.execute(
                    text(
                        "INSERT INTO services (clinic_id, name, duration_min, price_cents) "
                        "VALUES (app_current_clinic_id(), :name, :duration, :price) "
                        "RETURNING id, name, duration_min, price_cents, is_active"
                    ),
                    {"name": name, "duration": duration_min, "price": price_cents},
                )
            ).first()
        except IntegrityError as exc:
            raise Conflict("service_name") from exc
        if row is None:
            raise NotFound("service")
        return _row(row)

    async def update_service(
        self,
        service_id: UUID,
        *,
        name: str | None,
        duration_min: int | None,
        price_cents: int | None,
        is_active: bool | None,
    ) -> dict[str, Any] | None:
        try:
            row = (
                await self._s.execute(
                    text(
                        "UPDATE services SET name = COALESCE(:name, name), "
                        "duration_min = COALESCE(:duration, duration_min), "
                        "price_cents = COALESCE(:price, price_cents), "
                        "is_active = COALESCE(:active, is_active) "
                        "WHERE id = :id AND clinic_id = app_current_clinic_id() "
                        "RETURNING id, name, duration_min, price_cents, is_active"
                    ),
                    {
                        "id": service_id,
                        "name": name,
                        "duration": duration_min,
                        "price": price_cents,
                        "active": is_active,
                    },
                )
            ).first()
        except IntegrityError as exc:
            raise Conflict("service_name") from exc
        return _row(row) if row else None

    async def deactivate_service(self, service_id: UUID) -> bool:
        result = await self._s.execute(
            text(
                "UPDATE services SET is_active = false WHERE id = :id "
                "AND clinic_id = app_current_clinic_id()"
            ),
            {"id": service_id},
        )
        return int(getattr(result, "rowcount", 0) or 0) > 0

    async def list_professionals(self) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT p.id, p.name, p.specialty, p.is_active, "
                "COALESCE(array_agg(ps.service_id) FILTER (WHERE ps.service_id IS NOT NULL), "
                "'{}'::uuid[]) AS service_ids "
                "FROM professionals p LEFT JOIN professional_services ps "
                "ON ps.professional_id = p.id "
                "WHERE p.clinic_id = app_current_clinic_id() "
                "GROUP BY p.id ORDER BY p.is_active DESC, p.name"
            )
        )
        return _rows(rows)

    async def _sync_professional_services(
        self, professional_id: UUID, service_ids: list[UUID]
    ) -> None:
        await self._s.execute(
            text("DELETE FROM professional_services WHERE professional_id = :id"),
            {"id": professional_id},
        )
        if service_ids:
            await self._s.execute(
                text(
                    "INSERT INTO professional_services (clinic_id, professional_id, service_id) "
                    "SELECT app_current_clinic_id(), :pid, s.id FROM services s "
                    "WHERE s.id = ANY(CAST(:ids AS uuid[])) "
                    "AND s.clinic_id = app_current_clinic_id() ON CONFLICT DO NOTHING"
                ),
                {"pid": professional_id, "ids": service_ids},
            )

    async def _professional_by_id(self, professional_id: UUID) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT p.id, p.name, p.specialty, p.is_active, "
                    "COALESCE(array_agg(ps.service_id) FILTER "
                    "(WHERE ps.service_id IS NOT NULL), '{}'::uuid[]) AS service_ids "
                    "FROM professionals p LEFT JOIN professional_services ps "
                    "ON ps.professional_id = p.id WHERE p.id = :id "
                    "AND p.clinic_id = app_current_clinic_id() GROUP BY p.id"
                ),
                {"id": professional_id},
            )
        ).first()
        return _row(row) if row else None

    async def create_professional(
        self, *, name: str, specialty: str | None, service_ids: list[UUID]
    ) -> dict[str, Any]:
        professional_id = (
            await self._s.execute(
                text(
                    "INSERT INTO professionals (clinic_id, name, specialty) "
                    "VALUES (app_current_clinic_id(), :name, :specialty) RETURNING id"
                ),
                {"name": name, "specialty": specialty},
            )
        ).scalar_one()
        await self._sync_professional_services(professional_id, service_ids)
        result = await self._professional_by_id(professional_id)
        if result is None:
            raise NotFound("professional")
        return result

    async def update_professional(
        self,
        professional_id: UUID,
        *,
        name: str | None,
        specialty: str | None,
        service_ids: list[UUID] | None,
        is_active: bool | None,
    ) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "UPDATE professionals SET name = COALESCE(:name, name), "
                    "specialty = COALESCE(:specialty, specialty), "
                    "is_active = COALESCE(:active, is_active) "
                    "WHERE id = :id AND clinic_id = app_current_clinic_id() RETURNING id"
                ),
                {"id": professional_id, "name": name, "specialty": specialty, "active": is_active},
            )
        ).first()
        if row is None:
            return None
        if service_ids is not None:
            await self._sync_professional_services(professional_id, service_ids)
        return await self._professional_by_id(professional_id)

    async def deactivate_professional(self, professional_id: UUID) -> bool:
        result = await self._s.execute(
            text(
                "UPDATE professionals SET is_active = false WHERE id = :id "
                "AND clinic_id = app_current_clinic_id()"
            ),
            {"id": professional_id},
        )
        return int(getattr(result, "rowcount", 0) or 0) > 0

    async def list_requests(
        self,
        *,
        status: str | None,
        type_: str | None,
        priority: str | None,
        day: date | None,
        search: str | None,
        cursor_ts: datetime | None,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        q = f"%{search}%" if search else None
        rows = await self._s.execute(
            text(
                "SELECT r.id, r.clinic_id, r.type, r.title, r.description, r.status, "
                "r.priority, r.patient_name, r.patient_phone, r.requested_date, r.due_date, "
                "r.assigned_to, u.full_name AS assigned_to_name, r.call_id, r.suspicion_flags, "
                "r.created_at, r.updated_at FROM service_requests r "
                "LEFT JOIN clinic_users u ON u.id = r.assigned_to "
                "WHERE (CAST(:status AS text) IS NULL OR r.status = CAST(:status AS text)) "
                "AND (CAST(:type AS text) IS NULL OR r.type = CAST(:type AS text)) "
                "AND (CAST(:priority AS text) IS NULL OR r.priority = CAST(:priority AS text)) "
                "AND (CAST(:day AS date) IS NULL OR r.created_at::date = CAST(:day AS date)) "
                "AND (CAST(:q AS text) IS NULL OR r.title ILIKE CAST(:q AS text) "
                "     OR r.description ILIKE CAST(:q AS text) "
                "     OR r.patient_name ILIKE CAST(:q AS text)) "
                "AND (CAST(:cursor_ts AS timestamptz) IS NULL OR (r.created_at, r.id) < "
                "     (CAST(:cursor_ts AS timestamptz), CAST(:cursor_id AS uuid))) "
                "ORDER BY r.created_at DESC, r.id DESC LIMIT :limit"
            ),
            {
                "status": status,
                "type": type_,
                "priority": priority,
                "day": day,
                "q": q,
                "cursor_ts": cursor_ts,
                "cursor_id": cursor_id,
                "limit": limit,
            },
        )
        return _rows(rows)

    async def get_request(self, request_id: UUID) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT r.id, r.clinic_id, r.type, r.title, r.description, r.status, "
                    "r.priority, r.patient_name, r.patient_phone, r.requested_date, r.due_date, "
                    "r.assigned_to, u.full_name AS assigned_to_name, r.call_id, r.suspicion_flags, "
                    "r.created_at, r.updated_at FROM service_requests r "
                    "LEFT JOIN clinic_users u ON u.id = r.assigned_to WHERE r.id = :id"
                ),
                {"id": request_id},
            )
        ).first()
        return _row(row) if row else None

    async def get_request_events(self, request_id: UUID) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT e.id, e.event_type, e.note, e.user_id, u.full_name AS user_name, "
                "e.created_at FROM request_events e "
                "LEFT JOIN clinic_users u ON u.id = e.user_id "
                "WHERE e.request_id = :id ORDER BY e.created_at, e.id"
            ),
            {"id": request_id},
        )
        return _rows(rows)

    async def update_request(
        self,
        request_id: UUID,
        *,
        title: str | None,
        description: str | None,
        priority: str | None,
        due_date: date | None,
    ) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "UPDATE service_requests SET title = COALESCE(:title, title), "
                    "description = COALESCE(:description, description), "
                    "priority = COALESCE(:priority, priority), "
                    "due_date = COALESCE(:due, due_date), updated_at = now() "
                    "WHERE id = :id RETURNING id"
                ),
                {
                    "id": request_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "due": due_date,
                },
            )
        ).first()
        return await self.get_request(request_id) if row else None

    async def assign_request(self, request_id: UUID, user_id: UUID) -> dict[str, Any] | None:
        user = (
            await self._s.execute(
                text("SELECT id FROM clinic_users WHERE id = :uid AND is_active"),
                {"uid": user_id},
            )
        ).first()
        if user is None:
            raise NotFound("user")
        row = (
            await self._s.execute(
                text(
                    "UPDATE service_requests SET assigned_to = :uid, updated_at = now() "
                    "WHERE id = :id RETURNING id"
                ),
                {"id": request_id, "uid": user_id},
            )
        ).first()
        return await self.get_request(request_id) if row else None

    async def complete_request(self, request_id: UUID) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "UPDATE service_requests SET status = 'done', completed_at = now(), "
                    "updated_at = now() WHERE id = :id AND status <> 'spam' RETURNING id"
                ),
                {"id": request_id},
            )
        ).first()
        return await self.get_request(request_id) if row else None

    async def mark_request_spam(
        self, request_id: UUID, *, expires_in_days: int | None = None
    ) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "UPDATE service_requests SET status = 'spam', updated_at = now() "
                    "WHERE id = :id RETURNING id"
                ),
                {"id": request_id},
            )
        ).first()
        if row is None:
            return None
        phone = (
            await self._s.execute(
                text(
                    "SELECT COALESCE(r.patient_phone, c.caller_number) FROM service_requests r "
                    "LEFT JOIN calls c ON c.id = r.call_id WHERE r.id = :id"
                ),
                {"id": request_id},
            )
        ).scalar()
        added = False
        if phone:
            inserted = await self._s.execute(
                text(
                    "INSERT INTO blocked_numbers (clinic_id, e164, reason, source, expires_at) "
                    "VALUES (app_current_clinic_id(), :e164, 'marked_spam', 'auto_spam_flag', "
                    "CASE WHEN CAST(:days AS integer) IS NULL THEN NULL "
                    "ELSE now() + (CAST(:days AS integer) * interval '1 day') END) "
                    "ON CONFLICT (coalesce(clinic_id, "
                    "'00000000-0000-0000-0000-000000000000'::uuid), e164) "
                    "DO UPDATE SET expires_at = EXCLUDED.expires_at RETURNING id"
                ),
                {"e164": str(phone), "days": expires_in_days},
            )
            added = inserted.first() is not None
        request = await self.get_request(request_id)
        if request is not None:
            request["blocked_number_added"] = added
        return request

    async def add_request_event(
        self,
        request_id: UUID,
        event_type: str,
        *,
        user_id: UUID | None = None,
        note: str | None = None,
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO request_events (clinic_id, request_id, user_id, event_type, note) "
                "VALUES (app_current_clinic_id(), :rid, :uid, :type, :note)"
            ),
            {"rid": request_id, "uid": user_id, "type": event_type, "note": note},
        )

    async def add_audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: UUID | None,
        ip: str | None,
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO audit_log "
                "(clinic_id, user_id, action, resource_type, resource_id, ip) "
                "VALUES (app_current_clinic_id(), :uid, :action, :rtype, :rid, CAST(:ip AS inet))"
            ),
            {
                "uid": user_id,
                "action": action,
                "rtype": resource_type,
                "rid": resource_id,
                "ip": ip,
            },
        )

    async def list_calls(
        self,
        *,
        status: str | None,
        day: date | None,
        cursor_ts: datetime | None,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, clinic_id, channel, room_name, caller_number, started_at, ended_at, "
                "status, end_reason, duration_seconds, summary, abuse_score, suspicion_flags, "
                "handoff_requested, handoff_completed, cost_cents FROM calls "
                "WHERE (CAST(:status AS text) IS NULL OR status = CAST(:status AS text)) "
                "AND (CAST(:day AS date) IS NULL OR started_at::date = CAST(:day AS date)) "
                "AND (CAST(:cursor_ts AS timestamptz) IS NULL OR (started_at, id) < "
                "     (CAST(:cursor_ts AS timestamptz), CAST(:cursor_id AS uuid))) "
                "ORDER BY started_at DESC, id DESC LIMIT :limit"
            ),
            {
                "status": status,
                "day": day,
                "cursor_ts": cursor_ts,
                "cursor_id": cursor_id,
                "limit": limit,
            },
        )
        return _rows(rows)

    async def get_call(self, call_id: UUID) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT id, clinic_id, channel, room_name, caller_number, started_at, "
                    "ended_at, status, end_reason, duration_seconds, summary, abuse_score, "
                    "suspicion_flags, handoff_requested, handoff_completed, usage, latency_ms, "
                    "cost_cents FROM calls WHERE id = :id"
                ),
                {"id": call_id},
            )
        ).first()
        return _row(row) if row else None

    async def get_call_turns(self, call_id: UUID) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, seq, speaker, content, tool_name, tool_payload, started_at, ended_at, "
                "stt_confidence FROM call_turns WHERE call_id = :id ORDER BY seq"
            ),
            {"id": call_id},
        )
        return _rows(rows)

    async def get_call_events(self, call_id: UUID) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, event_type, payload, created_at FROM call_events "
                "WHERE call_id = :id ORDER BY created_at, id"
            ),
            {"id": call_id},
        )
        return _rows(rows)

    async def set_call_summary(self, call_id: UUID, summary: str) -> None:
        await self._s.execute(
            text("UPDATE calls SET summary = :summary WHERE id = :id"),
            {"id": call_id, "summary": summary},
        )

    async def list_appointments(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        professional_id: UUID | None,
    ) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT a.id, a.clinic_id, a.call_id, a.starts_at, a.ends_at, a.status, "
                "a.customer_name, a.customer_phone, a.service_id, a.professional_id, "
                "a.created_via, s.name AS service_name, p.name AS professional_name "
                "FROM appointments a JOIN services s ON s.id = a.service_id "
                "JOIN professionals p ON p.id = a.professional_id "
                "WHERE a.starts_at >= :start AND a.starts_at < :end "
                "AND (CAST(:pid AS uuid) IS NULL OR a.professional_id = CAST(:pid AS uuid)) "
                "ORDER BY a.starts_at LIMIT 1000"
            ),
            {"start": date_from, "end": date_to, "pid": professional_id},
        )
        return _rows(rows)

    async def get_appointment(self, appointment_id: UUID) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT a.id, a.clinic_id, a.call_id, a.starts_at, a.ends_at, a.status, "
                    "a.customer_name, a.customer_phone, a.service_id, a.professional_id, "
                    "a.created_via, s.name AS service_name, p.name AS professional_name "
                    "FROM appointments a JOIN services s ON s.id = a.service_id "
                    "JOIN professionals p ON p.id = a.professional_id WHERE a.id = :id"
                ),
                {"id": appointment_id},
            )
        ).first()
        return _row(row) if row else None

    async def get_published_config(self) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT id, clinic_id, version, status, config, created_by, created_at, "
                    "published_at "
                    "FROM agent_configs WHERE status = 'published' ORDER BY version DESC LIMIT 1"
                )
            )
        ).first()
        return _row(row) if row else None

    async def get_config_version(self, version: int) -> dict[str, Any] | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT id, clinic_id, version, status, config, created_by, created_at, "
                    "published_at "
                    "FROM agent_configs WHERE version = :v"
                ),
                {"v": version},
            )
        ).first()
        return _row(row) if row else None

    async def list_config_versions(self) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, clinic_id, version, status, config, created_by, created_at, "
                "published_at "
                "FROM agent_configs ORDER BY version DESC"
            )
        )
        return _rows(rows)

    async def next_config_version(self) -> int:
        value = (
            await self._s.execute(text("SELECT COALESCE(max(version), 0) + 1 FROM agent_configs"))
        ).scalar_one()
        return int(value)

    async def create_config(
        self, *, version: int, config: dict[str, Any], created_by: UUID | None, status: str
    ) -> dict[str, Any]:
        import json

        row = (
            await self._s.execute(
                text(
                    "INSERT INTO agent_configs "
                    "(clinic_id, version, status, config, created_by, published_at) "
                    "VALUES (app_current_clinic_id(), :v, :status, CAST(:config AS jsonb), "
                    ":created, CASE WHEN :status = 'published' THEN now() END) "
                    "RETURNING id, clinic_id, version, status, config, created_by, created_at, "
                    "published_at"
                ),
                {
                    "v": version,
                    "status": status,
                    "config": json.dumps(config, ensure_ascii=False),
                    "created": created_by,
                },
            )
        ).first()
        assert row is not None
        return _row(row)

    async def publish_config(self, version: int) -> dict[str, Any] | None:
        exists = (
            await self._s.execute(
                text("SELECT id FROM agent_configs WHERE version = :v"), {"v": version}
            )
        ).first()
        if exists is None:
            return None
        await self._s.execute(
            text(
                "UPDATE agent_configs SET status = 'draft', published_at = NULL "
                "WHERE status = 'published' AND version <> :v"
            ),
            {"v": version},
        )
        row = (
            await self._s.execute(
                text(
                    "UPDATE agent_configs SET status = 'published', "
                    "published_at = COALESCE(published_at, now()) WHERE version = :v "
                    "RETURNING id, clinic_id, version, status, config, created_by, created_at, "
                    "published_at"
                ),
                {"v": version},
            )
        ).first()
        return _row(row) if row else None

    async def list_users(self) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, email, full_name, role, is_active, created_at "
                "FROM clinic_users ORDER BY created_at"
            )
        )
        return _rows(rows)

    async def create_user(
        self, *, email: str, full_name: str, role: str, password_hash: str
    ) -> dict[str, Any]:
        try:
            row = (
                await self._s.execute(
                    text(
                        "INSERT INTO clinic_users "
                        "(clinic_id, email, password_hash, full_name, role) "
                        "VALUES (app_current_clinic_id(), :email, :hash, :name, :role) "
                        "RETURNING id, email, full_name, role, is_active, created_at"
                    ),
                    {"email": email, "hash": password_hash, "name": full_name, "role": role},
                )
            ).first()
        except IntegrityError as exc:
            raise Conflict("email_exists") from exc
        assert row is not None
        return _row(row)

    async def deactivate_user(self, user_id: UUID) -> dict[str, Any] | None:
        await self._s.execute(
            text(
                "UPDATE refresh_tokens SET revoked_at = now(), revoked_reason = 'admin' "
                "WHERE user_id = :id AND revoked_at IS NULL"
            ),
            {"id": user_id},
        )
        row = (
            await self._s.execute(
                text(
                    "UPDATE clinic_users SET is_active = false WHERE id = :id "
                    "RETURNING id, email, full_name, role, is_active, created_at"
                ),
                {"id": user_id},
            )
        ).first()
        return _row(row) if row else None

    async def list_blocked(self) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            text(
                "SELECT id, e164, reason, source, created_at, expires_at FROM blocked_numbers "
                "WHERE clinic_id IS NOT NULL ORDER BY created_at DESC"
            )
        )
        return _rows(rows)

    async def add_blocked(
        self,
        *,
        e164: str,
        reason: str | None,
        source: str,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        row = (
            await self._s.execute(
                text(
                    "INSERT INTO blocked_numbers (clinic_id, e164, reason, source, expires_at) "
                    "VALUES (app_current_clinic_id(), :e164, :reason, :source, "
                    "CASE WHEN CAST(:days AS integer) IS NULL THEN NULL "
                    "ELSE now() + (CAST(:days AS integer) * interval '1 day') END) "
                    "ON CONFLICT DO NOTHING "
                    "RETURNING id, e164, reason, source, created_at, expires_at"
                ),
                {"e164": e164, "reason": reason, "source": source, "days": expires_in_days},
            )
        ).first()
        if row is None:
            existing = (
                await self._s.execute(
                    text(
                        "SELECT id, e164, reason, source, created_at, expires_at "
                        "FROM blocked_numbers WHERE clinic_id = app_current_clinic_id() "
                        "AND e164 = :e164"
                    ),
                    {"e164": e164},
                )
            ).first()
            if existing is None:
                raise Conflict("blocked_number")
            return _row(existing)
        return _row(row)

    async def delete_blocked(self, blocked_id: UUID) -> bool:
        result = await self._s.execute(
            text("DELETE FROM blocked_numbers WHERE id = :id AND clinic_id IS NOT NULL"),
            {"id": blocked_id},
        )
        return int(getattr(result, "rowcount", 0) or 0) > 0

    async def dashboard(self, *, start: datetime, end: datetime) -> dict[str, Any]:
        counts = (
            await self._s.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM service_requests WHERE status = 'pending') "
                    "AS pending_requests, "
                    "(SELECT count(*) FROM calls WHERE started_at >= :start AND started_at < :end) "
                    "AS calls_today, "
                    "(SELECT count(*) FROM calls WHERE started_at >= :start AND started_at < :end "
                    " AND handoff_requested) AS handoffs, "
                    "(SELECT COALESCE(sum(cost_cents), 0) FROM calls "
                    " WHERE started_at >= :start AND started_at < :end) AS cost_today_cents"
                ),
                {"start": start, "end": end},
            )
        ).one()
        latency_rows = (
            await self._s.execute(
                text(
                    "SELECT latency_ms FROM calls "
                    "WHERE started_at >= :start AND started_at < :end "
                    "AND latency_ms <> '{}'::jsonb"
                ),
                {"start": start, "end": end},
            )
        ).scalars()
        stages: dict[str, list[float]] = {}
        for latency in latency_rows:
            if not isinstance(latency, dict):
                continue
            for stage, values in latency.items():
                if isinstance(values, dict) and isinstance(values.get("p50"), (int, float)):
                    stages.setdefault(stage, []).append(float(values["p50"]))
        calls_today = int(counts.calls_today)
        handoffs = int(counts.handoffs)
        return {
            "pending_requests": int(counts.pending_requests),
            "calls_today": calls_today,
            "handoffs_today": handoffs,
            "handoff_rate": round(handoffs / calls_today, 4) if calls_today else 0.0,
            "cost_today_cents": float(counts.cost_today_cents),
            "latency_p50_ms": {k: _percentile(v, 50) for k, v in stages.items()},
            "latency_p95_ms": {k: _percentile(v, 95) for k, v in stages.items()},
        }

    async def create_service_request(
        self,
        *,
        clinic_id: UUID,
        call_id: UUID,
        type_: str,
        title: str,
        description: str | None,
        patient_name: str | None,
        requested_date: date | None,
        due_date: date | None,
    ) -> UUID:
        caller = (
            await self._s.execute(
                text("SELECT caller_number FROM calls WHERE id = :id"), {"id": call_id}
            )
        ).scalar()
        if not caller:
            raise NotFound("call")
        # Dedupe identical requests from the same number inside a short window. A repeated ask is
        # one piece of work, not two; the action itself is still idempotent by Idempotency-Key.
        existing = (
            await self._s.execute(
                text(
                    "SELECT id FROM service_requests WHERE patient_phone = :phone "
                    "AND type = :type AND lower(btrim(title)) = lower(btrim(:title)) "
                    "AND created_at >= now() - interval '10 minutes' AND status <> 'spam' "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"phone": caller, "type": type_, "title": title},
            )
        ).scalar()
        if existing is not None:
            return UUID(str(existing))
        request_id = (
            await self._s.execute(
                text(
                    "INSERT INTO service_requests "
                    "(clinic_id, call_id, type, title, description, patient_name, patient_phone, "
                    "requested_date, due_date) VALUES (app_current_clinic_id(), :call, :type, "
                    ":title, :description, :name, :phone, :requested, :due) RETURNING id"
                ),
                {
                    "call": call_id,
                    "type": type_,
                    "title": title,
                    "description": description,
                    "name": patient_name,
                    "phone": caller,
                    "requested": requested_date,
                    "due": due_date,
                },
            )
        ).scalar_one()
        rid = UUID(str(request_id))
        await self.add_request_event(rid, "created")
        return rid


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((p / 100) * len(ordered) + 0.5)) - 1))
    return round(ordered[index], 2)
