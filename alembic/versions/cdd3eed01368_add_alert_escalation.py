"""add_alert_escalation

Revision ID: cdd3eed01368
Revises: 2de993a9edc5
Create Date: 2026-02-09 00:39:17.340656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'cdd3eed01368'
down_revision: Union[str, None] = '2de993a9edc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Alert escalation tracking ─────────────────────────────
    op.create_table(
        "alert_escalation",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_severity", sa.String(20), nullable=False),
        sa.Column("new_severity", sa.String(20), nullable=False),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escalation_trigger", sa.String(50), nullable=True),  # 'time_based', 'score_increase', 'repeated'
        sa.Column("escalation_metadata", sa.JSON(), nullable=True),
        comment="Tracks automatic severity escalations for alerts",
    )

    # Add indexes
    op.create_index("ix_alert_escalation_alert_id", "alert_escalation", ["alert_id"])
    op.create_index("ix_alert_escalation_escalated_at", "alert_escalation", ["escalated_at"])
    op.create_index("ix_alert_escalation_trigger", "alert_escalation", ["escalation_trigger"])


def downgrade() -> None:
    op.drop_index("ix_alert_escalation_trigger")
    op.drop_index("ix_alert_escalation_escalated_at")
    op.drop_index("ix_alert_escalation_alert_id")
    op.drop_table("alert_escalation")
