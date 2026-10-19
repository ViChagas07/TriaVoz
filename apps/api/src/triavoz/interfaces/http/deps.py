from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.application.auth.ports import AuthRepository, ClinicResolver, RateLimiter
from triavoz.application.auth.service import AuthService
from triavoz.application.events import EventPublisher
from triavoz.application.staff.ports import CallSummaryGenerator, StaffRepository
from triavoz.application.staff.service import StaffService
from triavoz.application.voice.ports import VoiceRoomService
from triavoz.config import get_settings
from triavoz.infrastructure.db.auth_repo import PgAuthRepository
from triavoz.infrastructure.db.clinic_resolver import RoutingClinicResolver
from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.db.staff_repo import PgStaffRepository
from triavoz.infrastructure.events.redis_events import RedisEventBus, get_event_bus
from triavoz.infrastructure.rate_limit.limiter import get_limiter
from triavoz.infrastructure.security.adapters import Argon2PasswordHasher, decode_principal
from triavoz.infrastructure.security.tokens import Principal
from triavoz.infrastructure.summary import UnconfiguredCallSummaryGenerator
from triavoz.infrastructure.voice.livekit_service import LiveKitVoiceService


def client_ip(request: Request) -> str:
    # Do not trust X-Forwarded-For until the proxy configuration is explicitly validated (P09).
    return request.client.host if request.client else "unknown"


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    # SSE/EventSource and same-origin navigation use the short-lived httpOnly access cookie.
    return request.cookies.get(get_settings().access_cookie_name)


async def current_principal(request: Request) -> Principal:
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="authentication_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_principal(token)
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=401,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_admin(principal: Principal = Depends(current_principal)) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return principal


async def tenant_db(
    principal: Principal = Depends(current_principal),
) -> AsyncIterator[AsyncSession]:
    async with tenant_session(principal.clinic_id) as session:
        yield session


def get_auth_repo(session: AsyncSession = Depends(tenant_db)) -> AuthRepository:
    return PgAuthRepository(session)


def get_staff_repo(session: AsyncSession = Depends(tenant_db)) -> StaffRepository:
    return PgStaffRepository(session)


@lru_cache
def get_password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache
def get_auth_service() -> AuthService:
    s = get_settings()
    return AuthService(
        get_limiter(),
        get_password_hasher(),
        refresh_ttl_days=s.refresh_token_ttl_days,
        account_capacity=s.login_account_capacity,
        ip_capacity=s.login_ip_capacity,
    )


@lru_cache
def get_clinic_resolver() -> ClinicResolver:
    return RoutingClinicResolver()


def get_limiter_dep() -> RateLimiter:
    return get_limiter()


def get_events_dep() -> EventPublisher:
    return get_event_bus()


def get_event_stream() -> RedisEventBus:
    return get_event_bus()


@lru_cache
def get_summary_generator() -> CallSummaryGenerator:
    return UnconfiguredCallSummaryGenerator()


def get_staff_service(
    repo: StaffRepository = Depends(get_staff_repo),
    events: EventPublisher = Depends(get_events_dep),
) -> StaffService:
    return StaffService(repo, events, get_password_hasher(), get_summary_generator())


@lru_cache
def get_voice_room_service() -> VoiceRoomService:
    s = get_settings()
    return LiveKitVoiceService(
        http_url=s.livekit_http_url,
        public_url=s.livekit_public_url,
        api_key=s.livekit_api_key,
        api_secret=s.livekit_api_secret.get_secret_value(),
    )


def get_demo_clinic_slug() -> str:
    return get_settings().demo_clinic_slug
