"""gatekeeper block aggregates for observability

Revision ID: 0004
Revises: 0003
"""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_SQL = Path(__file__).resolve().parent.parent / "sql" / "0004_observability_stats.sql"


def upgrade() -> None:
    op.execute(_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Irreversible by design: restore from backup. (No destructive downgrades.)")
