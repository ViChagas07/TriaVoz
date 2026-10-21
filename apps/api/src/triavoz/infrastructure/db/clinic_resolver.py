from __future__ import annotations

from uuid import UUID

from triavoz.infrastructure.db import routing


class RoutingClinicResolver:
    async def by_slug(self, slug: str) -> UUID | None:
        return await routing.resolve_clinic_by_slug(slug)

    async def by_phone(self, e164: str) -> UUID | None:
        return await routing.resolve_clinic_by_phone(e164)
