"""Scheduling against a real PostgreSQL: the DB — not the prompt — prevents double booking."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.conftest import future_monday
from triavoz.application.scheduling.use_cases import (
    BookAppointment,
    CancelAppointment,
    ListAvailableSlots,
    ListMyAppointments,
    RescheduleAppointment,
)
from triavoz.infrastructure.db.scheduling_repo import PgSchedulingRepository
from triavoz.infrastructure.db.session import tenant_session
from triavoz.shared_kernel.errors import NotFound, SlotTaken, SlotUnavailable

pytestmark = pytest.mark.db

TZ = ZoneInfo("America/Bahia")


def local(day_offset_weeks: int, h: int, m: int = 0) -> datetime:
    return datetime.combine(future_monday(day_offset_weeks), time(h, m), tzinfo=TZ)


async def _book(t: dict[str, Any], starts_at: datetime, phone: str, name: str = "Maria") -> Any:
    async with tenant_session(t["clinic"]) as s:
        return await BookAppointment(PgSchedulingRepository(s)).execute(
            clinic_id=t["clinic"],
            call_id=None,
            service_id=t["service"],
            professional_id=t["prof"],
            starts_at=starts_at,
            customer_name=name,
            caller_phone=phone,
            now=datetime.now(UTC),
        )


async def _slots(t: dict[str, Any], starts_at: datetime) -> list[datetime]:
    async with tenant_session(t["clinic"]) as s:
        slots = await ListAvailableSlots(PgSchedulingRepository(s)).execute(
            clinic_id=t["clinic"],
            service_id=t["service"],
            day=starts_at.date(),
            now=datetime.now(UTC),
        )
    return [x.starts_at for x in slots]


async def test_concurrent_bookings_of_the_same_slot_yield_exactly_one_winner(
    tenants: dict[str, dict[str, Any]],
) -> None:
    t = tenants["A"]
    slot = local(2, 9, 0)
    results = await asyncio.gather(
        *(_book(t, slot, f"+55719999{i:05d}", f"Cliente {i}") for i in range(12)),
        return_exceptions=True,
    )
    winners = [r for r in results if not isinstance(r, Exception)]
    losers = [r for r in results if isinstance(r, Exception)]
    assert len(winners) == 1
    assert all(isinstance(e, SlotTaken | SlotUnavailable) for e in losers), losers


async def test_db_constraint_rejects_overlap_even_if_the_use_case_is_bypassed(
    tenants: dict[str, dict[str, Any]],
) -> None:
    t = tenants["A"]
    start = local(3, 10, 0)

    async def raw_insert(s_start: datetime) -> Any:
        async with tenant_session(t["clinic"]) as s:
            return await PgSchedulingRepository(s).insert_appointment(
                clinic_id=t["clinic"],
                call_id=None,
                professional_id=t["prof"],
                service_id=t["service"],
                customer_name="X",
                customer_phone="+5571977776666",
                starts_at=s_start,
                ends_at=s_start + timedelta(minutes=30),
                created_via="staff",
            )

    await raw_insert(start)
    with pytest.raises(SlotTaken):
        await raw_insert(start + timedelta(minutes=15))  # partial overlap
    await raw_insert(start + timedelta(minutes=30))  # back-to-back is fine


async def test_booked_slot_disappears_and_cancel_brings_it_back(
    tenants: dict[str, dict[str, Any]],
) -> None:
    t = tenants["B"]
    slot, phone = local(4, 9, 30), "+5571966665555"
    assert slot in await _slots(t, slot)
    appt = await _book(t, slot, phone)
    assert slot not in await _slots(t, slot)

    async with tenant_session(t["clinic"]) as s:
        mine = await ListMyAppointments(PgSchedulingRepository(s)).execute(
            caller_phone=phone, now=datetime.now(UTC)
        )
    assert [m.id for m in mine] == [appt]

    async with tenant_session(t["clinic"]) as s:
        with pytest.raises(NotFound):  # someone else's phone can neither see nor cancel it
            await CancelAppointment(PgSchedulingRepository(s)).execute(
                appointment_id=appt, caller_phone="+5571900000000", now=datetime.now(UTC)
            )
    async with tenant_session(t["clinic"]) as s:
        await CancelAppointment(PgSchedulingRepository(s)).execute(
            appointment_id=appt, caller_phone=phone, now=datetime.now(UTC)
        )
    assert slot in await _slots(t, slot)


async def test_reschedule_moves_the_booking_and_refuses_taken_or_invalid_times(
    tenants: dict[str, dict[str, Any]],
) -> None:
    t = tenants["B"]
    phone = "+5571955554444"
    first, second = local(5, 9, 0), local(5, 10, 0)
    appt = await _book(t, first, phone)
    await _book(t, second, "+5571944443333", "Outro")

    async def move(to: datetime) -> None:
        async with tenant_session(t["clinic"]) as s:
            await RescheduleAppointment(PgSchedulingRepository(s)).execute(
                clinic_id=t["clinic"],
                appointment_id=appt,
                caller_phone=phone,
                new_starts_at=to,
                now=datetime.now(UTC),
            )

    with pytest.raises(SlotUnavailable):
        await move(second)  # already taken
    with pytest.raises(SlotUnavailable):
        await move(local(5, 3, 0))  # outside working hours
    await move(local(5, 11, 0))
    assert first in await _slots(t, first)  # old slot is free again


async def test_booking_requires_an_offered_slot(tenants: dict[str, dict[str, Any]]) -> None:
    t = tenants["A"]
    with pytest.raises(SlotUnavailable):
        await _book(t, local(2, 23, 0), "+5571933332222")  # LLM-invented time, outside hours
    with pytest.raises(SlotUnavailable):
        await _book(t, local(2, 9, 7), "+5571933332222")  # not on the 15-minute grid


async def test_concurrent_reschedules_to_the_same_target_yield_exactly_one_winner(
    isolated_clinic: dict[str, Any],
) -> None:
    t = isolated_clinic
    target = local(2, 10, 0)
    first = await _book(t, local(2, 9, 0), "+5571911110001", "Paciente A")
    second = await _book(t, local(2, 11, 0), "+5571911110002", "Paciente B")

    async def move(appointment_id: Any, phone: str) -> None:
        async with tenant_session(t["clinic"]) as s:
            await RescheduleAppointment(PgSchedulingRepository(s)).execute(
                clinic_id=t["clinic"],
                appointment_id=appointment_id,
                caller_phone=phone,
                new_starts_at=target,
                now=datetime.now(UTC),
            )

    results = await asyncio.gather(
        move(first, "+5571911110001"),
        move(second, "+5571911110002"),
        return_exceptions=True,
    )
    winners = [r for r in results if not isinstance(r, Exception)]
    losers = [r for r in results if isinstance(r, Exception)]
    assert len(winners) == 1
    assert all(isinstance(e, SlotTaken | SlotUnavailable) for e in losers), losers

    async with tenant_session(t["clinic"]) as s:
        booked_at_target = (
            await s.execute(
                text(
                    "SELECT count(*) FROM appointments "
                    "WHERE starts_at = :target AND status = 'booked'"
                ),
                {"target": target},
            )
        ).scalar_one()
    assert booked_at_target == 1


async def test_reschedule_race_against_a_new_booking_has_one_winner(
    isolated_clinic: dict[str, Any],
) -> None:
    t = isolated_clinic
    target = local(2, 10, 0)
    appt = await _book(t, local(2, 9, 0), "+5571911110003", "Paciente C")

    async def move() -> None:
        async with tenant_session(t["clinic"]) as s:
            await RescheduleAppointment(PgSchedulingRepository(s)).execute(
                clinic_id=t["clinic"],
                appointment_id=appt,
                caller_phone="+5571911110003",
                new_starts_at=target,
                now=datetime.now(UTC),
            )

    results = await asyncio.gather(
        move(),
        _book(t, target, "+5571911110004", "Paciente D"),
        return_exceptions=True,
    )
    winners = [r for r in results if not isinstance(r, Exception)]
    losers = [r for r in results if isinstance(r, Exception)]
    assert len(winners) == 1
    assert all(isinstance(e, SlotTaken | SlotUnavailable) for e in losers), losers
