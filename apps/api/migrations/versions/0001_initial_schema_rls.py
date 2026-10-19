"""initial schema with multi-tenant RLS

Revision ID: 0001
Revises:
"""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_SQL = Path(__file__).resolve().parent.parent / "sql" / "0001_initial_schema_rls.sql"


def upgrade() -> None:
    # Plain SQL on purpose: RLS policies, EXCLUDE constraints and SECURITY DEFINER functions are
    # clearer (and reviewable) as SQL than as ORM-generated DDL.
    op.execute(_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Irreversible by design: restore from backup. (No destructive downgrades.)")
