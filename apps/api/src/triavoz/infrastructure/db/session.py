"""Database access with mandatory tenant context.

There is deliberately NO helper that returns a session without a clinic id: the only way to talk to
tenant tables is `tenant_session(clinic_id)`, which sets `app.current_clinic_id` for the current
TRANSACTION only (`set_config(..., true)` == SET LOCAL). The value never leaks across pooled
connections because it disappears at COMMIT/ROLLBACK.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from triavoz.config import get_settings

_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _factory
    if _engine is None:
        _engine = create_async_engine(
            get_settings().database_url_app, pool_pre_ping=True, pool_size=10, max_overflow=10
        )
        _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def _session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _factory is not None
    return _factory


async def dispose_engine() -> None:
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
    _engine, _factory = None, None


@asynccontextmanager
async def tenant_session(clinic_id: UUID) -> AsyncIterator[AsyncSession]:
    """One transaction, scoped to one clinic. Commits on success, rolls back on error."""
    async with _session_factory()() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_clinic_id', :cid, true)"),
            {"cid": str(clinic_id)},
        )
        yield session
