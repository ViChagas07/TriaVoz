"""LGPD retention/expurgo job.

Runs as `triavoz_ops` and only calls the two narrow SECURITY DEFINER functions; ops never receives
table access. Safe to run from cron/Render job. Transcript batches are bounded per call, and the
script loops until no more rows match.

Environment:
  TRIAVOZ_DATABASE_URL_OPS  postgresql://triavoz_ops:...@host:5432/triavoz
"""

from __future__ import annotations

import argparse
import asyncio
import os

import asyncpg


def _dsn() -> str:
    value = os.environ.get("TRIAVOZ_DATABASE_URL_OPS")
    if not value:
        raise SystemExit("TRIAVOZ_DATABASE_URL_OPS is required")
    return value.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


async def _run(*, batch_size: int, revoked_before_days: int) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        total_transcripts = 0
        while True:
            rows = await conn.fetch(
                "SELECT clinic_id, deleted FROM purge_expired_transcripts($1)", batch_size
            )
            deleted = sum(int(row["deleted"]) for row in rows)
            total_transcripts += deleted
            if deleted == 0:
                break
            print(f"transcripts deleted: {deleted} (batch)")

        tokens = await conn.fetchval(
            "SELECT purge_expired_refresh_tokens(now() - ($1::int * interval '1 day'), $2)",
            revoked_before_days,
            max(batch_size, 5000),
        )
        print(f"transcripts deleted total: {total_transcripts}")
        print(f"refresh tokens deleted: {int(tokens or 0)}")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge expired transcripts and refresh tokens")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--revoked-before-days", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(_run(batch_size=args.batch_size, revoked_before_days=args.revoked_before_days))


if __name__ == "__main__":
    main()
