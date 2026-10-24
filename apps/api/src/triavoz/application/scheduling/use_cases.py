"""Scheduling use cases. Minimum privilege: cancel/reschedule/list only touch appointments whose
customer_phone equals the CALLER's phone, which comes from the server-side call record — never
from tool arguments produced by the LLM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from triavoz.application.scheduling.ports import (
    AppointmentView,
    SchedulingRepository,
    ServiceInfo,
)
from triavoz.domain.scheduling.slots import free_slots
from triavoz.shared_kernel.errors import InvalidRequest, NotFound, SlotUnavailable

MIN_NOTICE = timedelta(minutes=30)
SLOT_STEP = timedelta(minutes=15)


@dataclass(frozen=True)
class Slot:
    professional_id: UUID
    professional_name: str
    starts_at: datetime


async def _slots_for(
    repo: SchedulingRepository,
    *,
    clinic_id: UUID,
    service: ServiceInfo,
    day: date,
    now: datetime,
    professional_id: UUID | None,
) -> list[Slot]:
    tz_name = await repo.clinic_timezone(clinic_id)
    tz = ZoneInfo(tz_name)
    out: list[Slot] = []
    for prof in await repo.professionals_for_service(service.id, professional_id):
        windows = await repo.work_windows(prof.id, day.isoweekday())
        busy = await repo.busy_intervals(prof.id, day, tz_name)
        for start in free_slots(
            day=day,
            tz=tz,
            windows=windows,
            busy=busy,
            duration=timedelta(minutes=service.duration_min),
            now=now,
            step=SLOT_STEP,
            min_notice=MIN_NOTICE,
        ):
            out.append(Slot(prof.id, prof.name, start))
    return sorted(out, key=lambda s: (s.starts_at, s.professional_name))


class ListServices:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(self) -> list[ServiceInfo]:
        return await self._repo.list_services()


class ListAvailableSlots:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        clinic_id: UUID,
        service_id: UUID,
        day: date,
        now: datetime,
        professional_id: UUID | None = None,
        limit: int = 12,
    ) -> list[Slot]:
        service = await self._repo.get_service(service_id)
        if service is None:
            raise NotFound("service")
        slots = await _slots_for(
            self._repo,
            clinic_id=clinic_id,
            service=service,
            day=day,
            now=now,
            professional_id=professional_id,
        )
        return slots[:limit]


class BookAppointment:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        clinic_id: UUID,
        call_id: UUID | None,
        service_id: UUID,
        professional_id: UUID,
        starts_at: datetime,
        customer_name: str,
        caller_phone: str,
        now: datetime,
        created_via: str = "voice",
    ) -> UUID:
        name = customer_name.strip()
        if not name or len(name) > 120:
            raise InvalidRequest("customer_name")
        service = await self._repo.get_service(service_id)
        if service is None:
            raise NotFound("service")
        # Serialise writers for this professional before reading availability. See port docstring.
        await self._repo.lock_professional(professional_id)
        tz = ZoneInfo(await self._repo.clinic_timezone(clinic_id))
        local_start = starts_at.astimezone(tz)
        # Re-validate against the real availability: the time MUST be an offered slot.
        offered = await _slots_for(
            self._repo,
            clinic_id=clinic_id,
            service=service,
            day=local_start.date(),
            now=now,
            professional_id=professional_id,
        )
        if not any(s.starts_at == starts_at for s in offered):
            raise SlotUnavailable("not an available slot")
        # Final arbiter: the DB exclusion constraint (raises SlotTaken on a race).
        return await self._repo.insert_appointment(
            clinic_id=clinic_id,
            call_id=call_id,
            professional_id=professional_id,
            service_id=service_id,
            customer_name=name,
            customer_phone=caller_phone,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=service.duration_min),
            created_via=created_via,
        )


class ListMyAppointments:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        caller_phone: str | None,
        now: datetime,
        phone_verified: bool = True,
        identity_hash: bytes | None = None,
    ) -> list[AppointmentView]:
        return await self._repo.upcoming_for_owner(
            caller_phone,
            phone_verified=phone_verified,
            identity_hash=identity_hash,
            now=now,
        )


class CancelAppointment:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        appointment_id: UUID,
        caller_phone: str | None,
        now: datetime,
        phone_verified: bool = True,
        identity_hash: bytes | None = None,
    ) -> None:
        owned = await self._repo.get_owned_appointment(
            appointment_id,
            caller_phone,
            phone_verified=phone_verified,
            identity_hash=identity_hash,
        )
        if owned is None:
            raise NotFound("appointment")  # never reveal whether it exists for someone else
        await self._repo.cancel(appointment_id, now)


class MoveStaffAppointment:
    """Staff reschedule: same slot validation, but no caller-phone ownership check."""

    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        clinic_id: UUID,
        appointment_id: UUID,
        new_starts_at: datetime,
        now: datetime,
    ) -> None:
        owned = await self._repo.get_appointment_for_staff(appointment_id)
        if owned is None or owned[4] != "booked":
            raise NotFound("appointment")
        _, professional_id, service_id, _old, _status = owned
        service = await self._repo.get_service(service_id)
        if service is None:
            raise NotFound("service")
        await self._repo.lock_professional(professional_id)
        tz = ZoneInfo(await self._repo.clinic_timezone(clinic_id))
        offered = await _slots_for(
            self._repo,
            clinic_id=clinic_id,
            service=service,
            day=new_starts_at.astimezone(tz).date(),
            now=now,
            professional_id=professional_id,
        )
        if not any(s.starts_at == new_starts_at for s in offered):
            raise SlotUnavailable("not an available slot")
        await self._repo.move(
            appointment_id, new_starts_at, new_starts_at + timedelta(minutes=service.duration_min)
        )


class CancelStaffAppointment:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(self, *, appointment_id: UUID, now: datetime) -> None:
        owned = await self._repo.get_appointment_for_staff(appointment_id)
        if owned is None or owned[4] != "booked":
            raise NotFound("appointment")
        await self._repo.cancel(appointment_id, now)


class RescheduleAppointment:
    def __init__(self, repo: SchedulingRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        *,
        clinic_id: UUID,
        appointment_id: UUID,
        caller_phone: str | None,
        new_starts_at: datetime,
        now: datetime,
        phone_verified: bool = True,
        identity_hash: bytes | None = None,
    ) -> None:
        owned = await self._repo.get_owned_appointment(
            appointment_id,
            caller_phone,
            phone_verified=phone_verified,
            identity_hash=identity_hash,
        )
        if owned is None:
            raise NotFound("appointment")
        _, professional_id, service_id, _old = owned
        service = await self._repo.get_service(service_id)
        if service is None:
            raise NotFound("service")
        await self._repo.lock_professional(professional_id)
        tz = ZoneInfo(await self._repo.clinic_timezone(clinic_id))
        offered = await _slots_for(
            self._repo,
            clinic_id=clinic_id,
            service=service,
            day=new_starts_at.astimezone(tz).date(),
            now=now,
            professional_id=professional_id,
        )
        if not any(s.starts_at == new_starts_at for s in offered):
            raise SlotUnavailable("not an available slot")
        await self._repo.move(
            appointment_id, new_starts_at, new_starts_at + timedelta(minutes=service.duration_min)
        )
