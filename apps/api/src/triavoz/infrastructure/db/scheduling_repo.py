"""PostgreSQL implementation of SchedulingRepository (SQLAlchemy Core, parameterised SQL only).

Every statement runs on a session created by `tenant_session`, so RLS scopes it to one clinic. The
explicit `clinic_id` filters below are defence in depth, not the isolation mechanism."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.application.scheduling.ports import (
    AppointmentView,
    ProfessionalInfo,
    ServiceInfo,
)
from triavoz.domain.scheduling.slots import Interval, WorkWindow
from triavoz.shared_kernel.errors import NotFound, SlotTaken

EXCLUSION_VIOLATION = "23P01"


def _is_overlap(exc: DBAPIError) -> bool:
    orig = exc.orig
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return code == EXCLUSION_VIOLATION or "appointments_no_overlap" in str(exc)


class PgSchedulingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def clinic_timezone(self, clinic_id: UUID) -> str:
        row = (
            await self._s.execute(
                text("SELECT timezone FROM clinics WHERE id = :id"), {"id": clinic_id}
            )
        ).scalar()
        if row is None:
            raise NotFound("clinic")
        return str(row)

    async def list_services(self) -> list[ServiceInfo]:
        rows = await self._s.execute(
            text(
                "SELECT id, name, duration_min, price_cents FROM services "
                "WHERE is_active ORDER BY name"
            )
        )
        return [ServiceInfo(r.id, r.name, r.duration_min, r.price_cents) for r in rows]

    async def get_service(self, service_id: UUID) -> ServiceInfo | None:
        r = (
            await self._s.execute(
                text(
                    "SELECT id, name, duration_min, price_cents FROM services "
                    "WHERE id = :id AND is_active"
                ),
                {"id": service_id},
            )
        ).first()
        return ServiceInfo(r.id, r.name, r.duration_min, r.price_cents) if r else None

    async def professionals_for_service(
        self, service_id: UUID, professional_id: UUID | None = None
    ) -> list[ProfessionalInfo]:
        rows = await self._s.execute(
            text(
                "SELECT p.id, p.name FROM professionals p "
                "JOIN professional_services ps ON ps.professional_id = p.id "
                "WHERE ps.service_id = :sid AND p.is_active "
                "AND (CAST(:pid AS uuid) IS NULL OR p.id = CAST(:pid AS uuid)) ORDER BY p.name"
            ),
            {"sid": service_id, "pid": professional_id},
        )
        return [ProfessionalInfo(r.id, r.name) for r in rows]

    async def work_windows(self, professional_id: UUID, iso_weekday: int) -> list[WorkWindow]:
        rows = await self._s.execute(
            text(
                "SELECT start_time, end_time FROM availability_rules "
                "WHERE professional_id = :pid AND weekday = :wd ORDER BY start_time"
            ),
            {"pid": professional_id, "wd": iso_weekday},
        )
        return [WorkWindow(r.start_time, r.end_time) for r in rows]

    async def busy_intervals(self, professional_id: UUID, day: date, tz: str) -> list[Interval]:
        zone = ZoneInfo(tz)
        day_start = datetime.combine(day, time.min, tzinfo=zone)
        day_end = datetime.combine(day, time.max, tzinfo=zone)
        rows = await self._s.execute(
            text(
                "SELECT starts_at, ends_at FROM appointments "
                "WHERE professional_id = :pid AND status = 'booked' "
                "AND starts_at < :de AND ends_at > :ds "
                "UNION ALL "
                "SELECT starts_at, ends_at FROM time_off "
                "WHERE professional_id = :pid AND starts_at < :de AND ends_at > :ds"
            ),
            {"pid": professional_id, "ds": day_start, "de": day_end},
        )
        return [Interval(r.starts_at, r.ends_at) for r in rows]

    async def insert_appointment(
        self,
        *,
        clinic_id: UUID,
        call_id: UUID | None,
        professional_id: UUID,
        service_id: UUID,
        customer_name: str,
        customer_phone: str,
        starts_at: datetime,
        ends_at: datetime,
        created_via: str,
    ) -> UUID:
        try:
            # SAVEPOINT: a constraint violation must not poison the surrounding transaction.
            async with self._s.begin_nested():
                new_id = (
                    await self._s.execute(
                        text(
                            "INSERT INTO appointments (clinic_id, call_id, professional_id, "
                            "service_id, customer_name, customer_phone, starts_at, ends_at, "
                            "created_via) VALUES (:cid, :call, :pid, :sid, :name, :phone, "
                            ":s, :e, :via) RETURNING id"
                        ),
                        {
                            "cid": clinic_id,
                            "call": call_id,
                            "pid": professional_id,
                            "sid": service_id,
                            "name": customer_name,
                            "phone": customer_phone,
                            "s": starts_at,
                            "e": ends_at,
                            "via": created_via,
                        },
                    )
                ).scalar_one()
        except (IntegrityError, DBAPIError) as exc:
            if _is_overlap(exc):
                raise SlotTaken("slot already booked") from exc
            raise
        return UUID(str(new_id))

    async def upcoming_for_phone(self, phone: str, now: datetime) -> list[AppointmentView]:
        rows = await self._s.execute(
            text(
                "SELECT a.id, s.name AS service_name, p.name AS professional_name, a.starts_at "
                "FROM appointments a JOIN services s ON s.id = a.service_id "
                "JOIN professionals p ON p.id = a.professional_id "
                "WHERE a.customer_phone = :phone AND a.status = 'booked' AND a.starts_at > :now "
                "ORDER BY a.starts_at LIMIT 10"
            ),
            {"phone": phone, "now": now},
        )
        return [
            AppointmentView(r.id, r.service_name, r.professional_name, r.starts_at) for r in rows
        ]

    async def get_owned_appointment(
        self, appointment_id: UUID, phone: str
    ) -> tuple[UUID, UUID, UUID, datetime] | None:
        r = (
            await self._s.execute(
                text(
                    "SELECT id, professional_id, service_id, starts_at FROM appointments "
                    "WHERE id = :id AND customer_phone = :phone AND status = 'booked' "
                    "AND starts_at > now() FOR UPDATE"
                ),
                {"id": appointment_id, "phone": phone},
            )
        ).first()
        return (r.id, r.professional_id, r.service_id, r.starts_at) if r else None

    async def cancel(self, appointment_id: UUID, now: datetime) -> None:
        await self._s.execute(
            text(
                "UPDATE appointments SET status = 'canceled', canceled_at = :now "
                "WHERE id = :id AND status = 'booked'"
            ),
            {"id": appointment_id, "now": now},
        )

    async def move(self, appointment_id: UUID, starts_at: datetime, ends_at: datetime) -> None:
        try:
            async with self._s.begin_nested():
                await self._s.execute(
                    text(
                        "UPDATE appointments SET starts_at = :s, ends_at = :e "
                        "WHERE id = :id AND status = 'booked'"
                    ),
                    {"id": appointment_id, "s": starts_at, "e": ends_at},
                )
        except (IntegrityError, DBAPIError) as exc:
            if _is_overlap(exc):
                raise SlotTaken("slot already booked") from exc
            raise
