"""add_user_preferences

Revision ID: 463115f954c2
Revises: 397545b67c77
Create Date: 2026-02-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '463115f954c2'
down_revision: Union[str, None] = '397545b67c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add preferences column to user table ─────────────────────────
    bind = op.get_bind()
    # Use a Text fallback on SQLite (no schemas) and JSON for other dialects
    col = sa.Column(
        "preferences",
        sa.JSON() if bind.dialect.name != "sqlite" else sa.Text(),
        nullable=True,
        comment="User preferences and settings stored as JSON",
    )
    if bind.dialect.name == "sqlite":
        op.add_column("user", col)
    else:
        op.add_column("user", col, schema="alert")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.drop_column("user", "preferences")
    else:
        op.drop_column("user", "preferences", schema="alert")