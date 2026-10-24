"""retention: pseudonymise old calls without transcripts

Revision ID: 0006
Revises: 0005
"""

from pathlib import Path

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_SQL = Path(__file__).resolve().parent.parent / "sql" / "0006_retention_pseudonymise.sql"


def upgrade() -> None:
    op.execute(_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Irreversible by design: restore from backup. (No destructive downgrades.)")
