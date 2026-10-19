"""Tenant routing BEFORE a tenant context exists (session start, webhooks, login).

Uses SECURITY DEFINER functions that return ONLY a clinic id — the runtime role has no broad read
access to `phone_numbers` or `clinics` outside its own tenant.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from triavoz.infrastructure.db.session import get_engine


async def resolve_clinic_by_phone(e164: str) -> UUID | None:
    async with get_engine().connect() as conn:
        row = (await conn.execute(text("SELECT resolve_clinic_by_phone(:p)"), {"p": e164})).scalar()
    return UUID(str(row)) if row else None


async def resolve_clinic_by_slug(slug: str) -> UUID | None:
    async with get_engine().connect() as conn:
        row = (await conn.execute(text("SELECT resolve_clinic_by_slug(:s)"), {"s": slug})).scalar()
    return UUID(str(row)) if row else None
