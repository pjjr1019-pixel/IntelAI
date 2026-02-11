"""Initial schema — 15 tables across 4 Postgres schemas.

Revision ID: 0001_initial
Revises: -
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create schemas ───────────────────────────────────────────────
    for schema in ("ingestion", "signal", "alert", "backtest"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ── Postgres enum types ──────────────────────────────────────────
    sa.Enum("search", "wiki", "social", "news", "finance", "health", "alt_data",
            name="sourcetype", schema="ingestion").create(op.get_bind())
    sa.Enum("live", "degraded", "down",
            name="healthstatus", schema="ingestion").create(op.get_bind())
    sa.Enum("search_query", "wiki_page", "social_post", "news_headline",
            "financial_tick", "health_report",
            name="entitytype", schema="ingestion").create(op.get_bind())
    sa.Enum("hour", "day", "week", "month",
            name="timebucket", schema="signal").create(op.get_bind())
    sa.Enum("low", "medium", "high", "critical",
            name="severity", schema="alert").create(op.get_bind())
    sa.Enum("active", "watching", "confirmed", "dismissed", "resolved", "archived",
            name="alertstatus", schema="alert").create(op.get_bind())
    sa.Enum("confirm", "dismiss",
            name="feedbackverdict", schema="alert").create(op.get_bind())
    sa.Enum("true_positive", "false_positive", "inconclusive",
            name="eventoutcome", schema="alert").create(op.get_bind())
    sa.Enum("finance", "geopolitical", "health", "civil_unrest", "cyber",
            "environmental", "other",
            name="impactdomain", schema="alert").create(op.get_bind())
    sa.Enum("pending", "running", "completed", "failed",
            name="backteststatus", schema="backtest").create(op.get_bind())

    # ═══════════════════════════════════════════════════════════════════
    # INGESTION SCHEMA
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        "source_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("source_type", postgresql.ENUM("search", "wiki", "social", "news", "finance", "health", "alt_data", name="sourcetype", schema="ingestion", create_type=False), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("api_endpoint", sa.String(1024), nullable=True),
        sa.Column("auth_method", sa.String(64), nullable=True),
        sa.Column("update_frequency_seconds", sa.Integer, nullable=False, server_default="3600"),
        sa.Column("data_latency_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("health_status", postgresql.ENUM("live", "degraded", "down", name="healthstatus", schema="ingestion", create_type=False), nullable=False, server_default="live"),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("default_weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("updated_by", sa.String(256), nullable=True),
        sa.UniqueConstraint("name", name="uq_source_name"),
        schema="ingestion",
    )

    op.create_table(
        "raw_ingestion",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="'1.0'"),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("validation_errors", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="ingestion",
    )
    op.create_index("ix_raw_source_time", "raw_ingestion", ["source_id", "ingested_at"], schema="ingestion")

    op.create_table(
        "normalized_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("raw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion.raw_ingestion.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entity_type", postgresql.ENUM("search_query", "wiki_page", "social_post", "news_headline", "financial_tick", "health_report", name="entitytype", schema="ingestion", create_type=False), nullable=False),
        sa.Column("entity_value", sa.String(1024), nullable=False),
        sa.Column("metric_value", sa.Float, nullable=False),
        sa.Column("geo", sa.String(8), nullable=True),
        sa.Column("language", sa.String(8), nullable=True),
        sa.Column("metadata_extra", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="ingestion",
    )
    op.create_index("ix_norm_entity_time", "normalized_event", ["entity_type", "event_time"], schema="ingestion")
    op.create_index("ix_norm_source_time", "normalized_event", ["source_id", "event_time"], schema="ingestion")
    op.create_index("ix_norm_entity_value", "normalized_event", ["entity_value"], schema="ingestion")

    # ═══════════════════════════════════════════════════════════════════
    # SIGNAL SCHEMA
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        "signal_time_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("entity_value", sa.String(1024), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bucket_size", postgresql.ENUM("hour", "day", "week", "month", name="timebucket", schema="signal", create_type=False), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("coverage_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("entity_value", "source_id", "bucket_size", "bucket_start", name="uq_signal_entity_bucket"),
        schema="signal",
    )
    op.create_index("ix_signal_entity_time", "signal_time_series", ["entity_value", "bucket_start"], schema="signal")
    op.create_index("ix_signal_source_bucket", "signal_time_series", ["source_id", "bucket_start"], schema="signal")

    op.create_table(
        "anomaly_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signal.signal_time_series.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detection_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stl_trend", sa.Float, nullable=True),
        sa.Column("stl_seasonal", sa.Float, nullable=True),
        sa.Column("stl_residual", sa.Float, nullable=True),
        sa.Column("stl_residual_zscore", sa.Float, nullable=True),
        sa.Column("iforest_score", sa.Float, nullable=True),
        sa.Column("iforest_contamination", sa.Float, nullable=True),
        sa.Column("cusum_score", sa.Float, nullable=True),
        sa.Column("cusum_threshold", sa.Float, nullable=True),
        sa.Column("cusum_drift", sa.Float, nullable=True),
        sa.Column("weight_stl", sa.Float, nullable=False, server_default="0.4"),
        sa.Column("weight_iforest", sa.Float, nullable=False, server_default="0.3"),
        sa.Column("weight_cusum", sa.Float, nullable=False, server_default="0.3"),
        sa.Column("ensemble_score", sa.Float, nullable=False),
        sa.Column("is_anomaly", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ensemble_threshold", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("series_id", "detection_time", name="uq_anomaly_series_time"),
        schema="signal",
    )
    op.create_index("ix_anomaly_flag", "anomaly_result", ["is_anomaly"], schema="signal")
    op.create_index("ix_anomaly_ensemble", "anomaly_result", ["ensemble_score"], schema="signal")

    op.create_table(
        "semantic_cluster",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("label", sa.String(256), nullable=True),
        sa.Column("centroid_vector", postgresql.ARRAY(sa.Float), nullable=False),
        sa.Column("cluster_size", sa.Integer, nullable=False),
        sa.Column("drift_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("drift_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("prior_cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signal.semantic_cluster.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="signal",
    )
    op.create_index("ix_cluster_drift", "semantic_cluster", ["drift_score"], schema="signal")

    op.create_table(
        "semantic_cluster_member",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signal.semantic_cluster.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_value", sa.String(1024), nullable=False),
        sa.Column("embedding_vector", postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column("distance_to_centroid", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("cluster_id", "entity_value", name="uq_cluster_entity"),
        schema="signal",
    )

    # ═══════════════════════════════════════════════════════════════════
    # ALERT SCHEMA
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        "alert",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("primary_entity", sa.String(1024), nullable=False),
        sa.Column("related_entities", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("anomaly_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signal.anomaly_result.id", ondelete="SET NULL"), nullable=True),
        sa.Column("severity", postgresql.ENUM("low", "medium", "high", "critical", name="severity", schema="alert", create_type=False), nullable=False, server_default="medium"),
        sa.Column("status", postgresql.ENUM("active", "watching", "confirmed", "dismissed", "resolved", "archived", name="alertstatus", schema="alert", create_type=False), nullable=False, server_default="active"),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("ensemble_anomaly_score", sa.Float, nullable=False),
        sa.Column("source_weights", postgresql.JSONB, nullable=False),
        sa.Column("semantic_drift_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("signal_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("updated_by", sa.String(256), nullable=True),
        schema="alert",
    )
    op.create_index("ix_alert_status", "alert", ["status"], schema="alert")
    op.create_index("ix_alert_severity", "alert", ["severity"], schema="alert")
    op.create_index("ix_alert_created", "alert", ["created_at"], schema="alert")

    op.create_table(
        "evidence_chain",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_ids", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("normalized_event_ids", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("series_ids", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("anomaly_ids", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("explainability_text", sa.Text, nullable=False),
        sa.Column("evidence_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="alert",
    )
    op.create_index("ix_evidence_alert", "evidence_chain", ["alert_id"], schema="alert")

    op.create_table(
        "historical_analog",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matched_alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=False),
        sa.Column("similarity_method", sa.String(64), nullable=False, server_default="'dtw_cosine'"),
        sa.Column("reference_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analog_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="alert",
    )
    op.create_index("ix_analog_alert", "historical_analog", ["alert_id"], schema="alert")

    op.create_table(
        "post_mortem",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("event_outcome", postgresql.ENUM("true_positive", "false_positive", "inconclusive", name="eventoutcome", schema="alert", create_type=False), nullable=False),
        sa.Column("impact_domain", postgresql.ENUM("finance", "geopolitical", "health", "civil_unrest", "cyber", "environmental", "other", name="impactdomain", schema="alert", create_type=False), nullable=True),
        sa.Column("impact_severity", postgresql.ENUM("low", "medium", "high", "critical", name="severity", schema="alert", create_type=False), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("external_references", postgresql.JSONB, nullable=True),
        sa.Column("event_actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lead_time_hours", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("updated_by", sa.String(256), nullable=True),
        schema="alert",
    )
    op.create_index("ix_pm_outcome", "post_mortem", ["event_outcome"], schema="alert")

    op.create_table(
        "analyst_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(256), nullable=False),
        sa.Column("verdict", postgresql.ENUM("confirm", "dismiss", name="feedbackverdict", schema="alert", create_type=False), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("was_used_for_training", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="alert",
    )
    op.create_index("ix_feedback_alert", "analyst_feedback", ["alert_id"], schema="alert")

    # ═══════════════════════════════════════════════════════════════════
    # BACKTEST SCHEMA
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        "backtest_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "running", "completed", "failed", name="backteststatus", schema="backtest", create_type=False), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("alerts_generated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("true_positives", sa.Integer, nullable=False, server_default="0"),
        sa.Column("false_positives", sa.Integer, nullable=False, server_default="0"),
        sa.Column("missed_events", sa.Integer, nullable=False, server_default="0"),
        sa.Column("results_summary", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.Column("updated_by", sa.String(256), nullable=True),
        schema="backtest",
    )
    op.create_index("ix_backtest_status", "backtest_run", ["status"], schema="backtest")

    op.create_table(
        "backtest_alert",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest.backtest_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("primary_entity", sa.String(1024), nullable=False),
        sa.Column("severity", postgresql.ENUM("low", "medium", "high", "critical", name="severity", schema="alert", create_type=False), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("ensemble_anomaly_score", sa.Float, nullable=False),
        sa.Column("source_weights", postgresql.JSONB, nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("signal_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("matched_real_alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert.alert.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_true_positive", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="backtest",
    )
    op.create_index("ix_bt_alert_run", "backtest_alert", ["backtest_run_id"], schema="backtest")


def downgrade() -> None:
    # Drop tables in reverse dependency order
    for tbl, sch in [
        ("backtest_alert", "backtest"),
        ("backtest_run", "backtest"),
        ("analyst_feedback", "alert"),
        ("post_mortem", "alert"),
        ("historical_analog", "alert"),
        ("evidence_chain", "alert"),
        ("alert", "alert"),
        ("semantic_cluster_member", "signal"),
        ("semantic_cluster", "signal"),
        ("anomaly_result", "signal"),
        ("signal_time_series", "signal"),
        ("normalized_event", "ingestion"),
        ("raw_ingestion", "ingestion"),
        ("source_registry", "ingestion"),
    ]:
        op.drop_table(tbl, schema=sch)

    # Drop enum types
    for name, sch in [
        ("backteststatus", "backtest"),
        ("impactdomain", "alert"),
        ("eventoutcome", "alert"),
        ("feedbackverdict", "alert"),
        ("alertstatus", "alert"),
        ("severity", "alert"),
        ("timebucket", "signal"),
        ("entitytype", "ingestion"),
        ("healthstatus", "ingestion"),
        ("sourcetype", "ingestion"),
    ]:
        sa.Enum(name=name, schema=sch).drop(op.get_bind())

    # Drop schemas
    for schema in ("backtest", "alert", "signal", "ingestion"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
