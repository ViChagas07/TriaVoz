from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from triavoz.domain.scheduling.slots import Interval, WorkWindow


@dataclass(frozen=True)
class ServiceInfo:
    id: UUID
    name: str
    duration_min: int
    price_cents: int


@dataclass(frozen=True)
class ProfessionalInfo:
    id: UUID
    name: str


@dataclass(frozen=True)
class AppointmentView:
    """Deliberately minimal: what the voice agent may know about an appointment."""

    id: UUID
    service_name: str
    professional_name: str
    starts_at: datetime


class SchedulingRepository(Protocol):
    """All methods run inside ONE tenant transaction (RLS context already set)."""

    async def clinic_timezone(self, clinic_id: UUID) -> str: ...
    async def list_services(self) -> list[ServiceInfo]: ...
    async def get_service(self, service_id: UUID) -> ServiceInfo | None: ...
    async def professionals_for_service(
        self, service_id: UUID, professional_id: UUID | None = None
    ) -> list[ProfessionalInfo]: ...
    async def work_windows(self, professional_id: UUID, iso_weekday: int) -> list[WorkWindow]: ...
    async def busy_intervals(self, professional_id: UUID, day: date, tz: str) -> list[Interval]: ...
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
        """Raises SlotTaken when the DB exclusion constraint rejects an overlap."""
        ...

    async def upcoming_for_phone(self, phone: str, now: datetime) -> list[AppointmentView]: ...
    async def get_owned_appointment(
        self, appointment_id: UUID, phone: str
    ) -> tuple[UUID, UUID, UUID, datetime] | None:
        """(id, professional_id, service_id, starts_at) if booked and owned by `phone`."""
        ...

    async def cancel(self, appointment_id: UUID, now: datetime) -> None: ...
    async def move(self, appointment_id: UUID, starts_at: datetime, ends_at: datetime) -> None:
        """Raises SlotTaken on overlap."""
        ...
