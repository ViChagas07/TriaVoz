"""Concurrency guarantees for the auth boundary.

Two processes can receive the same refresh cookie (tab duplication, network retry, stolen token).
Rotation must be an atomic compare-and-set: exactly one request may rotate it, and the loser must
invalidate the family. Concurrent logins must also be independent (each gets its own family).
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import asyncpg
import httpx
import pytest

from tests.conftest import OWNER_DSN, set_password
from triavoz.application.auth.service import AuthService
from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.limiter import InMemoryRateLimiter
from triavoz.interfaces.http.deps import get_auth_service, get_password_hasher
from triavoz.main import create_app

pytestmark = pytest.mark.db

PASSWORD = "ConcurrentPass9!"
REFRESH_COOKIE = "triavoz_refresh"


def _app() -> Any:
    app = create_app()
    settings = get_settings()
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        InMemoryRateLimiter(),
        get_password_hasher(),
        refresh_ttl_days=settings.refresh_token_ttl_days,
        account_capacity=settings.login_account_capacity,
        ip_capacity=settings.login_ip_capacity,
    )
    return app


async def _login(client: httpx.AsyncClient, slug: str) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/login",
        json={"clinic_code": slug, "email": "isolated@example.test", "password": PASSWORD},
    )


def _cookie(raw: str) -> dict[str, str]:
    return {"Cookie": f"{REFRESH_COOKIE}={raw}"}


async def _active_tokens(clinic_id: Any, raw: str) -> tuple[int, int]:
    digest = hashlib.sha256(raw.encode()).digest()
    conn = await asyncpg.connect(OWNER_DSN)
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_clinic_id', $1, true)", str(clinic_id)
            )
            family_id = await conn.fetchval(
                "SELECT family_id FROM refresh_tokens WHERE token_hash = $1", digest
            )
            total = await conn.fetchval(
                "SELECT count(*) FROM refresh_tokens WHERE family_id = $1", family_id
            )
            active = await conn.fetchval(
                "SELECT count(*) FROM refresh_tokens WHERE family_id = $1 AND revoked_at IS NULL",
                family_id,
            )
    finally:
        await conn.close()
    return int(total), int(active)


async def test_concurrent_refresh_rotates_once_and_revokes_the_family(
    isolated_clinic: dict[str, Any],
) -> None:
    await set_password(isolated_clinic["clinic"], isolated_clinic["user"], PASSWORD)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()), base_url="http://test"
    ) as first_client:
        login = await _login(first_client, isolated_clinic["slug"])
        assert login.status_code == 200, login.text
        raw = first_client.cookies.get(REFRESH_COOKIE)
    assert raw

    async def attempt() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app()), base_url="http://test"
        ) as c:
            return await c.post("/api/v1/auth/refresh", headers=_cookie(raw))

    responses = await asyncio.gather(attempt(), attempt())
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 401], [r.text for r in responses]

    loser = next(response for response in responses if response.status_code == 401)
    # The public error stays generic (does not reveal reuse vs. unknown token).
    assert loser.json()["detail"] == "invalid_credentials"

    success = next(response for response in responses if response.status_code == 200)
    rotated = success.cookies.get(REFRESH_COOKIE)
    assert rotated and rotated != raw

    total, active = await _active_tokens(isolated_clinic["clinic"], raw)
    assert total >= 2, "rotation must have created the replacement token"
    assert active == 0, "a concurrent refresh must leave no live token in the family"

    # The token handed to the winner is already part of the revoked family.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()), base_url="http://test"
    ) as c:
        replay = await c.post("/api/v1/auth/refresh", headers=_cookie(rotated))
    assert replay.status_code == 401


async def test_concurrent_logins_create_independent_families(
    isolated_clinic: dict[str, Any],
) -> None:
    await set_password(isolated_clinic["clinic"], isolated_clinic["user"], PASSWORD)

    async def login_once() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app()), base_url="http://test"
        ) as c:
            return await _login(c, isolated_clinic["slug"])

    responses = await asyncio.gather(login_once(), login_once())
    assert [r.status_code for r in responses] == [200, 200]
    tokens = [r.cookies.get(REFRESH_COOKIE) for r in responses]
    assert all(tokens) and tokens[0] != tokens[1]
