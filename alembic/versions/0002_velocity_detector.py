"""Add velocity detector columns to anomaly_result.

Revision ID: 0002_velocity_detector
Revises: 0001_initial
Create Date: 2025-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_velocity_detector"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Velocity detector score columns ──────────────────────────────
    op.add_column(
        "anomaly_result",
        sa.Column(
            "velocity_score", sa.Float(), nullable=True,
            comment="Velocity detector normalised score (0-1); high = rapid acceleration",
        ),
        schema="signal",
    )
    op.add_column(
        "anomaly_result",
        sa.Column(
            "velocity_acceleration", sa.Float(), nullable=True,
            comment="Raw second derivative (acceleration) at the latest point",
        ),
        schema="signal",
    )

    # ── Velocity weight column ───────────────────────────────────────
    op.add_column(
        "anomaly_result",
        sa.Column(
            "weight_velocity", sa.Float(), nullable=False,
            server_default="0.2",
            comment="Weight assigned to Velocity detector score",
        ),
        schema="signal",
    )


def downgrade() -> None:
    op.drop_column("anomaly_result", "weight_velocity", schema="signal")
    op.drop_column("anomaly_result", "velocity_acceleration", schema="signal")
    op.drop_column("anomaly_result", "velocity_score", schema="signal")
