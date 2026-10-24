"""verified caller identity + retention functions

Revision ID: 0005
Revises: 0004
"""

from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_SQL = Path(__file__).resolve().parent.parent / "sql" / "0005_caller_identity_retention.sql"


def upgrade() -> None:
    op.execute(_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Irreversible by design: restore from backup. (No destructive downgrades.)")
