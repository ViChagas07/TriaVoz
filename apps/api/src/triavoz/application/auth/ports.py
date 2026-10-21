from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from triavoz.infrastructure.security.tokens import Principal


@dataclass(frozen=True)
class UserRecord:
    id: UUID
    clinic_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    password_hash: str


@dataclass(frozen=True)
class RefreshRecord:
    id: UUID
    clinic_id: UUID
    user_id: UUID
    family_id: UUID
    token_hash: bytes
    expires_at: datetime
    revoked_at: datetime | None
    revoked_reason: str | None


class AuthRepository(Protocol):
    """Tenant-bound repository: every method runs with app.current_clinic_id set."""

    async def find_user_by_email(self, email: str) -> UserRecord | None: ...
    async def get_user(self, user_id: UUID) -> UserRecord | None: ...
    async def create_refresh(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        family_id: UUID,
        token_hash: bytes,
        expires_at: datetime,
        created_ip: str | None,
        user_agent: str | None,
    ) -> UUID: ...
    async def find_refresh(self, token_hash: bytes) -> RefreshRecord | None: ...
    async def revoke_token(
        self, token_id: UUID, reason: str, replaced_by_id: UUID | None = None
    ) -> None: ...
    async def revoke_family(self, family_id: UUID, reason: str) -> int: ...
    async def revoke_by_hash(self, token_hash: bytes, reason: str) -> None: ...


class PasswordHasher(Protocol):
    @property
    def dummy_hash(self) -> str: ...
    def hash(self, plain: str) -> str: ...
    def verify(self, hashed: str, plain: str) -> bool: ...


class RateLimiter(Protocol):
    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool: ...
    async def reset(self, key: str) -> None: ...


class ClinicResolver(Protocol):
    async def by_slug(self, slug: str) -> UUID | None: ...
    async def by_phone(self, e164: str) -> UUID | None: ...


class AccessTokenIssuer(Protocol):
    def issue(self, principal: Principal) -> str: ...
