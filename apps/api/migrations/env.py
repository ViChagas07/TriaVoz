"""Alembic environment. Runs as triavoz_owner (sync psycopg driver); the API runtime never does."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config


def _url() -> str:
    url = os.environ.get("TRIAVOZ_DATABASE_URL_OWNER")
    if not url:
        raise RuntimeError(
            "Set TRIAVOZ_DATABASE_URL_OWNER (postgresql+psycopg://triavoz_owner:...)"
        )
    return url


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
