from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.application.events import EventPublisher
from triavoz.application.scheduling.use_cases import (
    BookAppointment,
    CancelStaffAppointment,
    MoveStaffAppointment,
)
from triavoz.application.staff.ports import StaffRepository
from triavoz.infrastructure.db.scheduling_repo import PgSchedulingRepository
from triavoz.infrastructure.security.tokens import Principal
from triavoz.interfaces.http.api_v1.schemas import (
    AppointmentCreate,
    AppointmentMove,
    AppointmentOut,
)
from triavoz.interfaces.http.deps import (
    current_principal,
    get_events_dep,
    get_staff_repo,
    tenant_db,
)

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("", response_model=list[AppointmentOut])
async def list_agenda(
    date_from: date | None = None,
    date_to: date | None = None,
    professional_id: UUID | None = None,
    repo: StaffRepository = Depends(get_staff_repo),
) -> list[AppointmentOut]:
    tz = ZoneInfo(await repo.clinic_timezone())
    today = datetime.now(tz).date()
    start_day = date_from or today
    end_day = date_to or (start_day + timedelta(days=7))
    start = datetime.combine(start_day, time.min, tzinfo=tz)
    end = datetime.combine(end_day, time.min, tzinfo=tz)
    rows = await repo.list_appointments(
        date_from=start, date_to=end, professional_id=professional_id
    )
    return [AppointmentOut.model_validate(r) for r in rows]


@router.post("", response_model=AppointmentOut)
async def create_appointment(
    body: AppointmentCreate,
    session: AsyncSession = Depends(tenant_db),
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(current_principal),
    events: EventPublisher = Depends(get_events_dep),
) -> AppointmentOut:
    appointment_id = await BookAppointment(PgSchedulingRepository(session)).execute(
        clinic_id=principal.clinic_id,
        call_id=None,
        service_id=body.service_id,
        professional_id=body.professional_id,
        starts_at=body.starts_at,
        customer_name=body.customer_name,
        caller_phone=body.customer_phone,
        now=datetime.now(UTC),
        created_via="staff",
    )
    appointment = await repo.get_appointment(appointment_id)
    assert appointment is not None
    await events.publish(
        principal.clinic_id,
        "appointment.created",
        {"appointment_id": str(appointment_id)},
    )
    return AppointmentOut.model_validate(appointment)


@router.post("/{appointment_id}/move", response_model=AppointmentOut)
async def move_appointment(
    appointment_id: UUID,
    body: AppointmentMove,
    session: AsyncSession = Depends(tenant_db),
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(current_principal),
    events: EventPublisher = Depends(get_events_dep),
) -> AppointmentOut:
    await MoveStaffAppointment(PgSchedulingRepository(session)).execute(
        clinic_id=principal.clinic_id,
        appointment_id=appointment_id,
        new_starts_at=body.starts_at,
        now=datetime.now(UTC),
    )
    appointment = await repo.get_appointment(appointment_id)
    assert appointment is not None
    await events.publish(
        principal.clinic_id,
        "appointment.moved",
        {"appointment_id": str(appointment_id)},
    )
    return AppointmentOut.model_validate(appointment)


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
    appointment_id: UUID,
    session: AsyncSession = Depends(tenant_db),
    repo: StaffRepository = Depends(get_staff_repo),
    principal: Principal = Depends(current_principal),
    events: EventPublisher = Depends(get_events_dep),
) -> AppointmentOut:
    await CancelStaffAppointment(PgSchedulingRepository(session)).execute(
        appointment_id=appointment_id, now=datetime.now(UTC)
    )
    appointment = await repo.get_appointment(appointment_id)
    assert appointment is not None
    await events.publish(
        principal.clinic_id,
        "appointment.canceled",
        {"appointment_id": str(appointment_id)},
    )
    return AppointmentOut.model_validate(appointment)
