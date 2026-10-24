from __future__ import annotations

import os
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import asyncpg


def owner_dsn() -> str:
    dsn = os.environ.get("TRIAVOZ_TEST_OWNER_DSN") or os.environ.get("TRIAVOZ_DATABASE_URL_OWNER")
    if not dsn:
        raise RuntimeError(
            "set TRIAVOZ_TEST_OWNER_DSN (or TRIAVOZ_DATABASE_URL_OWNER) to a migrated test DB"
        )
    return dsn.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )


@dataclass(frozen=True)
class ClinicFixture:
    clinic_id: uuid.UUID
    service_id: uuid.UUID
    service_name: str
    professional_id: uuid.UUID
    professional_name: str
    timezone: str


def _phone() -> str:
    return "+5571" + "".join(random.choices("0123456789", k=9))


async def seed_eval_clinic() -> ClinicFixture:
    clinic_id, service_id, professional_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    slug = f"eval-{uuid.uuid4().hex[:10]}"
    conn = await asyncpg.connect(owner_dsn())
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id)
            )
            await conn.execute(
                "INSERT INTO clinics (id, name, slug, timezone) VALUES ($1, $2, $3, $4)",
                clinic_id,
                "Clínica Avaliação",
                slug,
                "America/Bahia",
            )
            await conn.execute("INSERT INTO clinic_settings (clinic_id) VALUES ($1)", clinic_id)
            await conn.execute(
                "INSERT INTO services (id, clinic_id, name, duration_min, price_cents) "
                "VALUES ($1, $2, 'Consulta geral', 30, 15000), "
                "($3, $2, 'Retorno', 20, 0)",
                service_id,
                clinic_id,
                uuid.uuid4(),
            )
            await conn.execute(
                "INSERT INTO professionals (id, clinic_id, name) VALUES ($1, $2, $3)",
                professional_id,
                clinic_id,
                "Dra. Avaliação",
            )
            await conn.execute(
                "INSERT INTO professional_services (clinic_id, professional_id, service_id) "
                "SELECT $1, $2, id FROM services WHERE clinic_id = $1",
                clinic_id,
                professional_id,
            )
            await conn.execute(
                "INSERT INTO availability_rules "
                "(clinic_id, professional_id, weekday, start_time, end_time) "
                "SELECT $1, $2, d, '08:00', '18:00' FROM generate_series(1, 7) d",
                clinic_id,
                professional_id,
            )
    finally:
        await conn.close()
    return ClinicFixture(
        clinic_id=clinic_id,
        service_id=service_id,
        service_name="Consulta geral",
        professional_id=professional_id,
        professional_name="Dra. Avaliação",
        timezone="America/Bahia",
    )


async def drop_eval_clinic(clinic_id: uuid.UUID) -> None:
    conn = await asyncpg.connect(owner_dsn())
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id)
            )
            await conn.execute("DELETE FROM clinics WHERE id = $1", clinic_id)
    finally:
        await conn.close()


async def appointment_state(
    clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> dict[str, Any] | None:
    conn = await asyncpg.connect(owner_dsn())
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id)
            )
            row = await conn.fetchrow(
                "SELECT id, status, starts_at, customer_phone FROM appointments WHERE id = $1",
                appointment_id,
            )
        return dict(row) if row else None
    finally:
        await conn.close()


def eval_phone() -> str:
    return _phone()


def eval_day(days_ahead: int = 7) -> date:
    return date.today() + timedelta(days=days_ahead)


def iso(value: datetime) -> str:
    return value.isoformat()
