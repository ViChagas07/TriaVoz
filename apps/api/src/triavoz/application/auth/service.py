"""Authentication rules: generic errors, rotation with reuse detection, rate limits.

The repository passed in is already bound to one tenant transaction; this module never chooses a
clinic from user input for an authenticated request.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from triavoz.application.auth.ports import (
    AuthRepository,
    PasswordHasher,
    RateLimiter,
    UserRecord,
)
from triavoz.infrastructure.security.tokens import Principal
from triavoz.shared_kernel.errors import AuthenticationError, TooManyAttempts

REFRESH_PREFIX = "triavoz-refresh"


@dataclass(frozen=True)
class LoginResult:
    user: UserRecord
    principal: Principal
    refresh_token: str
    refresh_expires_at: datetime


@dataclass(frozen=True)
class RefreshResult:
    user: UserRecord
    principal: Principal
    refresh_token: str
    refresh_expires_at: datetime


@dataclass(frozen=True)
class RefreshRejected:
    """Returned (not raised) so the caller's tenant transaction can COMMIT a family revocation."""

    reason: str


def new_refresh_token(clinic_id: UUID) -> str:
    # The clinic id is only a routing hint. The authoritative lookup is the SHA-256 hash INSIDE
    # that tenant's RLS context, so tampering with the hint cannot cross tenants.
    return f"{clinic_id}.{secrets.token_urlsafe(48)}"


def refresh_hash(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


def parse_refresh_clinic(raw: str) -> UUID | None:
    prefix, _, _ = raw.partition(".")
    try:
        return UUID(prefix)
    except ValueError:
        return None


class AuthService:
    def __init__(
        self,
        limiter: RateLimiter,
        hasher: PasswordHasher,
        *,
        refresh_ttl_days: int = 30,
        account_capacity: int = 5,
        ip_capacity: int = 30,
        refresh_ip_capacity: int = 60,
        refresh_ip_refill_per_second: float = 1.0,
    ) -> None:
        self._limiter = limiter
        self._hasher = hasher
        self._ttl = timedelta(days=refresh_ttl_days)
        self._account_capacity = account_capacity
        self._ip_capacity = ip_capacity
        self._refresh_ip_capacity = refresh_ip_capacity
        self._refresh_ip_refill = refresh_ip_refill_per_second
        # Argon2id uses 64 MiB per verification; cap concurrent verifications so a burst of
        # unauthenticated logins cannot exhaust the process/host memory.
        self._verify_slots = asyncio.Semaphore(4)

    async def enforce_rate(self, *, clinic_code: str, email: str, ip: str) -> None:
        account_key = f"triavoz:auth:acct:{clinic_code.lower()}:{email.lower()}"
        ip_key = f"triavoz:auth:ip:{ip}"
        account_ok = await self._limiter.allow(account_key, self._account_capacity, 1 / 120, cost=1)
        ip_ok = await self._limiter.allow(ip_key, self._ip_capacity, 1 / 10, cost=1)
        if not (account_ok and ip_ok):
            raise TooManyAttempts("login")

    async def verify_dummy(self, password: str) -> None:
        async with self._verify_slots:
            await asyncio.to_thread(self._hasher.verify, self._hasher.dummy_hash, password)

    async def _verify(self, password_hash: str, password: str) -> bool:
        async with self._verify_slots:
            return await asyncio.to_thread(self._hasher.verify, password_hash, password)

    async def enforce_refresh_rate(self, *, ip: str) -> None:
        # Refresh is unauthenticated by design (cookie only): bound it per source address.
        ok = await self._limiter.allow(
            f"triavoz:auth:refresh:ip:{ip}",
            self._refresh_ip_capacity,
            self._refresh_ip_refill,
            cost=1,
        )
        if not ok:
            raise TooManyAttempts("refresh")

    async def login(
        self,
        repo: AuthRepository,
        *,
        clinic_code: str,
        email: str,
        password: str,
        ip: str,
        user_agent: str | None,
    ) -> LoginResult:
        await self.enforce_rate(clinic_code=clinic_code, email=email, ip=ip)
        user = await repo.find_user_by_email(email)
        valid = await asyncio.to_thread(
            self._hasher.verify, user.password_hash if user else self._hasher.dummy_hash, password
        )
        if user is None or not user.is_active or not valid:
            await repo.add_audit(
                action="auth.login_failed",
                resource_type="user",
                resource_id=str(user.id) if user else None,
                user_id=user.id if user else None,
                ip=ip,
            )
            raise AuthenticationError("invalid credentials")
        # A successful login clears the account's failure budget; the IP budget keeps counting.
        await self._limiter.reset(f"triavoz:auth:acct:{clinic_code.lower()}:{email.lower()}")

        principal = Principal(user.id, user.clinic_id, user.role)
        raw = new_refresh_token(user.clinic_id)
        family_id = UUID(bytes=secrets.token_bytes(16), version=4)
        expires = datetime.now(UTC) + self._ttl
        await repo.create_refresh(
            clinic_id=user.clinic_id,
            user_id=user.id,
            family_id=family_id,
            token_hash=refresh_hash(raw),
            expires_at=expires,
            created_ip=ip,
            user_agent=user_agent,
        )
        await repo.add_audit(
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
            ip=ip,
        )
        return LoginResult(user, principal, raw, expires)

    async def refresh(
        self,
        repo: AuthRepository,
        *,
        raw_token: str,
        ip: str,
        user_agent: str | None,
    ) -> RefreshResult | RefreshRejected:
        record = await repo.find_refresh(refresh_hash(raw_token))
        if record is None:
            return RefreshRejected("refresh")
        if record.revoked_at is not None:
            # A revoked token presented again is a compromise signal: kill the whole family.
            await repo.revoke_family(record.family_id, "reuse_detected")
            await repo.add_audit(
                action="auth.refresh_reuse",
                resource_type="user",
                resource_id=str(record.user_id),
                user_id=record.user_id,
                ip=ip,
            )
            return RefreshRejected("refresh_reuse")
        if record.expires_at <= datetime.now(UTC):
            return RefreshRejected("refresh_expired")

        user = await repo.get_user(record.user_id)
        if user is None or not user.is_active:
            await repo.revoke_family(record.family_id, "admin")
            return RefreshRejected("refresh_user_inactive")

        raw = new_refresh_token(user.clinic_id)
        expires = datetime.now(UTC) + self._ttl
        new_id = await repo.create_refresh(
            clinic_id=user.clinic_id,
            user_id=user.id,
            family_id=record.family_id,
            token_hash=refresh_hash(raw),
            expires_at=expires,
            created_ip=ip,
            user_agent=user_agent,
        )
        # Atomic rotation: two concurrent requests carrying the same token both reach this UPDATE,
        # but only one sees an unrevoked row. The loser is treated as token reuse and kills the
        # family, so a captured token can never mint two live sessions.
        if not await repo.revoke_token(record.id, "rotated", replaced_by_id=new_id):
            await repo.revoke_family(record.family_id, "reuse_detected")
            return RefreshRejected("refresh_reuse")
        return RefreshResult(user, Principal(user.id, user.clinic_id, user.role), raw, expires)

    async def logout(self, repo: AuthRepository, *, raw_token: str) -> None:
        record = await repo.find_refresh(refresh_hash(raw_token))
        if record is not None:
            await repo.revoke_family(record.family_id, "logout")
