#!/usr/bin/env python
"""Seed three fictional clinics for the public demo. Idempotent: safe to run twice.

DEV ONLY password for every seeded user: ``Demo!TriaVoz2026``.
No real personal data is used (phone numbers are fictional; no CPF/document is seeded).

Run from ``apps/api`` with an OWNER DSN (migrations/seed only, never at API runtime):

    $env:TRIAVOZ_DATABASE_URL_OWNER="postgresql+psycopg://triavoz_owner:...@localhost:5432/triavoz"
    poetry run python scripts/seed_demo.py

The script sets ``app.current_clinic_id`` per transaction because FORCE RLS also applies to the
owner. Every UUID is deterministic (uuid5), so re-running updates rows instead of duplicating them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import time
from pathlib import Path

import asyncpg

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from triavoz.infrastructure.security.passwords import hash_password  # noqa: E402

DEMO_PASSWORD = "Demo!TriaVoz2026"  # noqa: S105 - documented DEV-ONLY demo password
_NAMESPACE = uuid.UUID("b5b48b39-6f3a-4d8f-9f66-3f20c8d0f0a1")


def _id(key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, key)


@dataclass(frozen=True)
class ServiceSeed:
    key: str
    name: str
    duration_min: int
    price_cents: int


@dataclass(frozen=True)
class ProfessionalSeed:
    key: str
    name: str
    specialty: str
    service_keys: tuple[str, ...]


@dataclass(frozen=True)
class UserSeed:
    key: str
    email: str
    full_name: str
    role: str


@dataclass(frozen=True)
class ClinicSeed:
    key: str
    name: str
    slug: str
    timezone: str
    phone: str
    services: tuple[ServiceSeed, ...]
    professionals: tuple[ProfessionalSeed, ...]
    users: tuple[UserSeed, ...]


CLINICS = (
    ClinicSeed(
        key="horizonte",
        name="Clínica Horizonte",
        slug="clinica-horizonte",
        timezone="America/Bahia",
        phone="+557140020001",
        services=(
            ServiceSeed("consulta", "Consulta clínica", 30, 25000),
            ServiceSeed("retorno", "Retorno", 20, 0),
            ServiceSeed("curativo", "Curativo", 15, 8000),
        ),
        professionals=(
            ProfessionalSeed("ana", "Dra. Ana Ribeiro", "Clínica geral", ("consulta", "retorno")),
            ProfessionalSeed(
                "bruno", "Dr. Bruno Matos", "Cardiologia", ("consulta", "retorno", "curativo")
            ),
        ),
        users=(
            UserSeed("admin", "admin@horizonte.demo", "Ana Administradora", "admin"),
            UserSeed("recepcao", "recepcao@horizonte.demo", "Rita Recepção", "attendant"),
        ),
    ),
    ClinicSeed(
        key="vida-leve",
        name="Clínica Vida Leve",
        slug="clinica-vida-leve",
        timezone="America/Sao_Paulo",
        phone="+551140020002",
        services=(
            ServiceSeed("nutri", "Consulta nutricional", 45, 30000),
            ServiceSeed("avaliacao", "Avaliação corporal", 30, 15000),
        ),
        professionals=(
            ProfessionalSeed("clara", "Dra. Clara Nunes", "Nutrição", ("nutri", "avaliacao")),
            ProfessionalSeed("diego", "Dr. Diego Alves", "Educação física", ("avaliacao",)),
        ),
        users=(
            UserSeed("admin", "admin@vida-leve.demo", "Clara Administradora", "admin"),
            UserSeed("recepcao", "recepcao@vida-leve.demo", "Rui Recepção", "attendant"),
        ),
    ),
    ClinicSeed(
        key="sol-nascente",
        name="Clínica Sol Nascente",
        slug="clinica-sol-nascente",
        timezone="America/Recife",
        phone="+558140020003",
        services=(
            ServiceSeed("pediatria", "Consulta pediátrica", 30, 28000),
            ServiceSeed("vacina", "Vacinação", 15, 12000),
            ServiceSeed("acuidade", "Teste de acuidade visual", 20, 9000),
        ),
        professionals=(
            ProfessionalSeed("helena", "Dra. Helena Castro", "Pediatria", ("pediatria", "vacina")),
            ProfessionalSeed("joao", "Dr. João Freitas", "Oftalmologia", ("acuidade",)),
        ),
        users=(
            UserSeed("admin", "admin@sol-nascente.demo", "Helena Administradora", "admin"),
            UserSeed("recepcao", "recepcao@sol-nascente.demo", "Jana Recepção", "attendant"),
        ),
    ),
)

_WINDOWS = ((time(8, 0), time(12, 0)), (time(14, 0), time(18, 0)))


def _agent_config(clinic: ClinicSeed) -> dict[str, str]:
    return {
        "clinic_name": clinic.name,
        "greeting": (
            "Olá! Sou a assistente virtual da {clinic_name}. Posso ajudar a marcar, "
            "remarcar ou cancelar uma consulta. Como posso ajudar?"
        ),
        "tone": "acolhedor, claro e objetivo",
        "emergency_message": "Se for uma emergência, ligue agora para o SAMU, no 192.",
    }


async def _seed_clinic(conn: asyncpg.Connection, clinic: ClinicSeed, password_hash: str) -> None:
    clinic_id = _id(f"clinic/{clinic.key}")
    async with conn.transaction():
        # FORCE RLS applies to the owner too: set the tenant before touching clinics.
        await conn.execute("SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id))
        await conn.execute(
            """
            INSERT INTO clinics (id, name, slug, timezone)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE
              SET name = EXCLUDED.name, slug = EXCLUDED.slug,
                  timezone = EXCLUDED.timezone, is_active = true
            """,
            clinic_id,
            clinic.name,
            clinic.slug,
            clinic.timezone,
        )

        user_ids: dict[str, uuid.UUID] = {}
        for user in clinic.users:
            user_ids[user.key] = await conn.fetchval(
                """
                INSERT INTO clinic_users (id, clinic_id, email, password_hash, full_name, role)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (clinic_id, email) DO UPDATE
                  SET password_hash = EXCLUDED.password_hash,
                      full_name = EXCLUDED.full_name,
                      role = EXCLUDED.role,
                      is_active = true
                RETURNING id
                """,
                _id(f"user/{clinic.key}/{user.key}"),
                clinic_id,
                user.email,
                password_hash,
                user.full_name,
                user.role,
            )

        await conn.execute(
            """
            INSERT INTO phone_numbers (id, clinic_id, e164, label)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE
              SET clinic_id = EXCLUDED.clinic_id, e164 = EXCLUDED.e164,
                  label = EXCLUDED.label, is_active = true
            """,
            _id(f"phone/{clinic.key}"),
            clinic_id,
            clinic.phone,
            "Demo",
        )

        service_ids: dict[str, uuid.UUID] = {}
        for service in clinic.services:
            service_ids[service.key] = await conn.fetchval(
                """
                INSERT INTO services (id, clinic_id, name, duration_min, price_cents)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (clinic_id, name) DO UPDATE
                  SET duration_min = EXCLUDED.duration_min,
                      price_cents = EXCLUDED.price_cents,
                      is_active = true
                RETURNING id
                """,
                _id(f"service/{clinic.key}/{service.key}"),
                clinic_id,
                service.name,
                service.duration_min,
                service.price_cents,
            )

        professional_ids: dict[str, uuid.UUID] = {}
        for professional in clinic.professionals:
            professional_ids[professional.key] = await conn.fetchval(
                """
                INSERT INTO professionals (id, clinic_id, name, specialty)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE
                  SET name = EXCLUDED.name, specialty = EXCLUDED.specialty,
                      is_active = true
                RETURNING id
                """,
                _id(f"professional/{clinic.key}/{professional.key}"),
                clinic_id,
                professional.name,
                professional.specialty,
            )
            for service_key in professional.service_keys:
                await conn.execute(
                    """
                    INSERT INTO professional_services (clinic_id, professional_id, service_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    clinic_id,
                    professional_ids[professional.key],
                    service_ids[service_key],
                )
            for weekday in range(1, 6):
                for index, (start, end) in enumerate(_WINDOWS):
                    await conn.execute(
                        """
                        INSERT INTO availability_rules
                          (id, clinic_id, professional_id, weekday, start_time, end_time)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (id) DO UPDATE
                          SET professional_id = EXCLUDED.professional_id,
                              weekday = EXCLUDED.weekday,
                              start_time = EXCLUDED.start_time,
                              end_time = EXCLUDED.end_time
                        """,
                        _id(f"availability/{clinic.key}/{professional.key}/{weekday}/{index}"),
                        clinic_id,
                        professional_ids[professional.key],
                        weekday,
                        start,
                        end,
                    )

        admin_id = user_ids["admin"]
        await conn.execute(
            """
            INSERT INTO agent_configs
              (id, clinic_id, version, status, config, created_by, published_at)
            VALUES ($1, $2, 1, 'published', $3::jsonb, $4, now())
            ON CONFLICT (clinic_id, version) DO UPDATE
              SET status = 'published',
                  config = EXCLUDED.config,
                  created_by = EXCLUDED.created_by,
                  published_at = COALESCE(agent_configs.published_at, now())
            """,
            _id(f"agent-config/{clinic.key}"),
            clinic_id,
            json.dumps(_agent_config(clinic), ensure_ascii=False),
            admin_id,
        )

        await conn.execute(
            """
            INSERT INTO clinic_settings
              (clinic_id, daily_minute_budget, daily_cost_budget_cents,
               max_concurrent_calls, max_call_seconds, kill_switch, transcript_retention_days)
            VALUES ($1, 120, 500, 3, 300, false, 365)
            ON CONFLICT (clinic_id) DO UPDATE
              SET daily_minute_budget = EXCLUDED.daily_minute_budget,
                  daily_cost_budget_cents = EXCLUDED.daily_cost_budget_cents,
                  max_concurrent_calls = EXCLUDED.max_concurrent_calls,
                  max_call_seconds = EXCLUDED.max_call_seconds,
                  kill_switch = EXCLUDED.kill_switch,
                  transcript_retention_days = EXCLUDED.transcript_retention_days,
                  updated_at = now()
            """,
            clinic_id,
        )

        print(
            f"  {clinic.name}: {len(clinic.users)} users, {len(clinic.services)} services, "
            f"{len(clinic.professionals)} professionals"
        )


def _dsn() -> str:
    raw = os.environ.get("TRIAVOZ_DATABASE_URL_OWNER")
    if not raw:
        raise SystemExit(
            "Set TRIAVOZ_DATABASE_URL_OWNER (owner DSN; see .env.example) or pass --dsn."
        )
    return raw.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", help="owner DSN; defaults to TRIAVOZ_DATABASE_URL_OWNER")
    args = parser.parse_args()
    dsn = (
        (args.dsn or _dsn())
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )
    password_hash = hash_password(DEMO_PASSWORD)
    conn = await asyncpg.connect(dsn)
    try:
        print(f"Seeding {len(CLINICS)} fictional clinics (password: {DEMO_PASSWORD})")
        for clinic in CLINICS:
            await _seed_clinic(conn, clinic, password_hash)
    finally:
        await conn.close()
    print("Done. Safe to run again.")


if __name__ == "__main__":
    asyncio.run(main())
