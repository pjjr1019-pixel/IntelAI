"""add_alert_silence

Revision ID: baeb1bd008f1
Revises: cdd3eed01368
Create Date: 2026-02-09 00:41:24.593398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'baeb1bd008f1'
down_revision: Union[str, None] = 'cdd3eed01368'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Alert silence/snooze tracking ─────────────────────────────
    op.create_table(
        "alert_silence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=True),
        sa.Column("entity_pattern", sa.String(1024), nullable=True),  # For silencing by entity pattern
        sa.Column("silenced_by", sa.String(256), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("silence_type", sa.String(50), nullable=False),  # 'alert', 'entity', 'global'
        sa.Column("duration_minutes", sa.Integer(), nullable=True),  # For time-based silences
        sa.Column("silenced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        comment="Tracks alert silencing/snoozing rules",
    )

    # Add indexes
    op.create_index("ix_alert_silence_alert_id", "alert_silence", ["alert_id"])
    op.create_index("ix_alert_silence_entity_pattern", "alert_silence", ["entity_pattern"])
    op.create_index("ix_alert_silence_expires_at", "alert_silence", ["expires_at"])
    op.create_index("ix_alert_silence_is_active", "alert_silence", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_alert_silence_is_active")
    op.drop_index("ix_alert_silence_expires_at")
    op.drop_index("ix_alert_silence_entity_pattern")
    op.drop_index("ix_alert_silence_alert_id")
    op.drop_table("alert_silence")
