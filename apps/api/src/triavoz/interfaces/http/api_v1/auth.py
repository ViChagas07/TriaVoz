from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Request, Response, status

from triavoz.application.auth.ports import AuthRepository, ClinicResolver
from triavoz.application.auth.service import (
    AuthService,
    RefreshRejected,
    RefreshResult,
    parse_refresh_clinic,
)
from triavoz.config import get_settings
from triavoz.infrastructure.db.auth_repo import PgAuthRepository
from triavoz.infrastructure.db.session import tenant_session
from triavoz.infrastructure.security.tokens import Principal, create_access_token
from triavoz.interfaces.http.api_v1.cookies import clear_auth_cookies, set_auth_cookies
from triavoz.interfaces.http.api_v1.schemas import LoginIn, LoginOut, MeOut, UserOut
from triavoz.interfaces.http.deps import (
    client_ip,
    current_principal,
    get_auth_service,
    get_clinic_resolver,
    get_staff_repo,  # noqa: F401  (dependency export)
)
from triavoz.shared_kernel.errors import AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: object) -> UserOut:
    u = user
    return UserOut(
        id=u.id,  # type: ignore[attr-defined]
        email=str(u.email),  # type: ignore[attr-defined]
        full_name=u.full_name,  # type: ignore[attr-defined]
        role=u.role,  # type: ignore[attr-defined]
        is_active=u.is_active,  # type: ignore[attr-defined]
        created_at=getattr(u, "created_at", None),
    )


@router.post("/login", response_model=LoginOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    resolver: ClinicResolver = Depends(get_clinic_resolver),
) -> LoginOut:
    started = time.monotonic()
    try:
        clinic_id = await resolver.by_slug(body.clinic_code)
        ip = client_ip(request)
        if clinic_id is None:
            await service.enforce_rate(clinic_code=body.clinic_code, email=body.email, ip=ip)
            await service.verify_dummy(body.password)
            raise AuthenticationError("invalid credentials")

        async with tenant_session(clinic_id) as session:
            repo: AuthRepository = PgAuthRepository(session)
            result = await service.login(
                repo,
                clinic_code=body.clinic_code,
                email=body.email,
                password=body.password,
                ip=ip,
                user_agent=request.headers.get("User-Agent"),
            )
        access = create_access_token(result.principal)
        set_auth_cookies(
            response,
            access_token=access,
            refresh_token=result.refresh_token,
            refresh_expires=result.refresh_expires_at,
        )
        return LoginOut(
            access_token=access,
            expires_in=get_settings().jwt_access_ttl_seconds,
            user=_user_out(result.user),
        )
    finally:
        # Constant-time floor: an unknown clinic must not answer measurably faster than a real one.
        remaining = get_settings().login_min_seconds - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)


@router.post("/refresh", response_model=LoginOut)
async def refresh(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> LoginOut:
    await service.enforce_refresh_rate(ip=client_ip(request))
    raw = request.cookies.get(get_settings().refresh_cookie)
    clinic_id = parse_refresh_clinic(raw) if raw else None
    if raw is None or clinic_id is None:
        raise AuthenticationError("refresh")
    async with tenant_session(clinic_id) as session:
        repo: AuthRepository = PgAuthRepository(session)
        outcome = await service.refresh(
            repo, raw_token=raw, ip=client_ip(request), user_agent=request.headers.get("User-Agent")
        )
    if isinstance(outcome, RefreshRejected):
        # The session above committed any family revocation before this 401 is returned.
        raise AuthenticationError(outcome.reason)
    result: RefreshResult = outcome
    access = create_access_token(result.principal)
    set_auth_cookies(
        response,
        access_token=access,
        refresh_token=result.refresh_token,
        refresh_expires=result.refresh_expires_at,
    )
    return LoginOut(
        access_token=access,
        expires_in=get_settings().jwt_access_ttl_seconds,
        user=_user_out(result.user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request) -> Response:
    raw = request.cookies.get(get_settings().refresh_cookie)
    clinic_id = parse_refresh_clinic(raw) if raw else None
    if raw and clinic_id:
        async with tenant_session(clinic_id) as session:
            repo: AuthRepository = PgAuthRepository(session)
            await get_auth_service().logout(repo, raw_token=raw)
    out = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(out)
    return out


@router.get("/me", response_model=MeOut)
async def me(
    principal: Principal = Depends(current_principal),
) -> MeOut:
    async with tenant_session(principal.clinic_id) as session:
        repo: AuthRepository = PgAuthRepository(session)
        user = await repo.get_user(principal.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("inactive")
    return MeOut(user=_user_out(user), clinic_id=principal.clinic_id, role=user.role)
