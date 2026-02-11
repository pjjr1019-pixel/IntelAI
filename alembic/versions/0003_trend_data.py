"""Add trend data tables for historical storage and analysis.

Revision ID: 0003_trend_data
Revises: 0002_velocity_detector
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_trend_data"
down_revision = "0002_velocity_detector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Trend snapshots table ────────────────────────────────────────
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("geo", sa.String(length=5), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_trends", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("trends_data", sa.JSON(), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("rate_limited", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="signal",
    )

    # ── Trend keywords table ─────────────────────────────────────────
    op.create_table(
        "trend_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("geo", sa.String(length=5), nullable=False),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column("current_traffic", sa.String(length=50), nullable=True),
        sa.Column("current_traffic_value", sa.Integer(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("peak_rank", sa.Integer(), nullable=True),
        sa.Column("total_appearances", sa.Integer(), nullable=False),
        sa.Column("avg_rank", sa.Float(), nullable=True),
        sa.Column("velocity_trend", sa.JSON(), nullable=True),
        sa.Column("direction_changes", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("news_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="signal",
    )

    # ── Trend time series table ──────────────────────────────────────
    op.create_table(
        "trend_time_series",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interest_score", sa.Float(), nullable=False),
        sa.Column("rank_at_time", sa.Integer(), nullable=True),
        sa.Column("velocity", sa.Float(), nullable=True),
        sa.Column("acceleration", sa.Float(), nullable=True),
        sa.Column("geo", sa.String(length=5), nullable=False),
        sa.Column("data_source", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["keyword_id"],
            ["signal.trend_keywords.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="signal",
    )

    # ── Trend alerts table ───────────────────────────────────────────
    op.create_table(
        "trend_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("rank_at_alert", sa.Integer(), nullable=True),
        sa.Column("interest_at_alert", sa.Float(), nullable=True),
        sa.Column("velocity_at_alert", sa.Float(), nullable=True),
        sa.Column("pct_change_24h", sa.Float(), nullable=True),
        sa.Column("geo", sa.String(length=5), nullable=False),
        sa.Column("related_news", sa.JSON(), nullable=True),
        sa.Column("additional_data", sa.JSON(), nullable=True),
        sa.Column("acknowledged", sa.Integer(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["keyword_id"],
            ["signal.trend_keywords.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="signal",
    )

    # ── Indexes for performance ──────────────────────────────────────
    op.create_index(
        "idx_trend_snapshots_geo_captured",
        "trend_snapshots",
        ["geo", "captured_at"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_snapshots_captured",
        "trend_snapshots",
        ["captured_at"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_keywords_keyword_geo",
        "trend_keywords",
        ["keyword", "geo"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_keywords_last_seen",
        "trend_keywords",
        ["last_seen"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_keywords_category",
        "trend_keywords",
        ["category"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_time_series_keyword_timestamp",
        "trend_time_series",
        ["keyword_id", "timestamp"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_time_series_geo_timestamp",
        "trend_time_series",
        ["geo", "timestamp"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_alerts_keyword_triggered",
        "trend_alerts",
        ["keyword_id", "triggered_at"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_alerts_type_triggered",
        "trend_alerts",
        ["alert_type", "triggered_at"],
        schema="signal",
    )
    op.create_index(
        "idx_trend_alerts_severity",
        "trend_alerts",
        ["severity"],
        schema="signal",
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_trend_alerts_severity", schema="signal")
    op.drop_index("idx_trend_alerts_type_triggered", schema="signal")
    op.drop_index("idx_trend_alerts_keyword_triggered", schema="signal")
    op.drop_index("idx_trend_time_series_geo_timestamp", schema="signal")
    op.drop_index("idx_trend_time_series_keyword_timestamp", schema="signal")
    op.drop_index("idx_trend_keywords_category", schema="signal")
    op.drop_index("idx_trend_keywords_last_seen", schema="signal")
    op.drop_index("idx_trend_keywords_keyword_geo", schema="signal")
    op.drop_index("idx_trend_snapshots_captured", schema="signal")
    op.drop_index("idx_trend_snapshots_geo_captured", schema="signal")

    # Drop tables
    op.drop_table("trend_alerts", schema="signal")
    op.drop_table("trend_time_series", schema="signal")
    op.drop_table("trend_keywords", schema="signal")
    op.drop_table("trend_snapshots", schema="signal")