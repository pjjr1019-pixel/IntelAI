"""
alert.py — Alert lifecycle, evidence chains, feedback, and backtesting.

Tables
------
Alert             – The primary output: a flagged anomaly for analyst review.
EvidenceChain     – Unbreakable audit trail linking an alert to raw data.
HistoricalAnalog  – The 3 most similar past patterns (Phase 2).
PostMortem        – Outcome tagging after the real-world event resolves.
AnalystFeedback   – Confirm / Dismiss verdicts that feed the RL layer.
BacktestRun       – Metadata for a synthetic backtest execution.
BacktestAlert     – Alerts that would have been generated during a backtest.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vanguard_signal.schema.base import AuditMixin, Base, TimestampMixin
from vanguard_signal.schema.enums import (
    AlertStatus,
    BacktestStatus,
    EventOutcome,
    FeedbackVerdict,
    ImpactDomain,
    Severity,
)


# ═════════════════════════════════════════════════════════════════════════
# 7. ALERT — Core analyst-facing output
# ═════════════════════════════════════════════════════════════════════════

class Alert(Base, TimestampMixin, AuditMixin):
    """
    The fundamental output of Vanguard Signal: a flagged anomaly that
    demands analyst attention.

    Confidence is NOT a black box.  It is composed of:
      • `ensemble_anomaly_score` — from the anomaly engine
      • `source_weights`         — which sources contributed, and how much
      • `semantic_drift_score`   — Phase 2 semantic signal (0.0 in Phase 1)

    Together these let auditors reproduce the exact reasoning.
    """

    __tablename__ = "alert"
    __table_args__ = (
        Index("ix_alert_status", "status"),
        Index("ix_alert_severity", "severity"),
        Index("ix_alert_created", "created_at"),
        Index("ix_alert_updated", "updated_at"),
        Index("ix_alert_confidence", "confidence_score"),
        {"schema": "alert", "comment": "Flagged anomalies for analyst review"},
    )

    # ── What triggered the alert ─────────────────────────────────────────
    primary_entity: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="The entity (search term, page, …) at the center of the anomaly",
    )
    related_entities: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True,
        comment="Other entities co-occurring in the same anomaly window",
    )
    anomaly_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signal.anomaly_result.id", ondelete="SET NULL"),
        nullable=True,
        comment="The specific anomaly row that spawned this alert",
    )
    trigger_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert_rule.id", ondelete="SET NULL"),
        nullable=True,
        comment="The alert rule that triggered this alert (if rule-based)",
    )

    # ── Severity & Status ────────────────────────────────────────────────
    severity: Mapped[Severity] = mapped_column(
        nullable=False, default=Severity.MEDIUM,
        comment="low / medium / high / critical",
    )
    status: Mapped[AlertStatus] = mapped_column(
        nullable=False, default=AlertStatus.ACTIVE,
        comment="Lifecycle: active → watching → confirmed/dismissed → resolved",
    )

    # ── Confidence — FULLY DECOMPOSED for audit ──────────────────────────
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Final confidence (0.0 – 1.0)",
    )
    ensemble_anomaly_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Anomaly engine's ensemble output",
    )
    source_weights: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment='Per-source weight snapshot, e.g. {"google_trends": 0.6, "wikipedia": 0.4}',
    )
    semantic_drift_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Semantic drift contribution (0.0 until Phase 2)",
    )

    # ── Human-Readable Explanation ───────────────────────────────────────
    reason_code: Mapped[str] = mapped_column(
        String(128), nullable=False,
        comment="Machine-readable reason, e.g. CUSUM_SHIFT, STL_SPIKE, DRIFT",
    )
    summary_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Auto-generated plain-English explanation for the analyst",
    )

    # ── Time Context ─────────────────────────────────────────────────────
    signal_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Earliest timestamp of the contributing anomaly window",
    )
    signal_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Latest timestamp of the contributing anomaly window",
    )

    # ── Relationships ────────────────────────────────────────────────────
    evidence_chains: Mapped[list["EvidenceChain"]] = relationship(
        back_populates="alert", lazy="selectin",
    )
    historical_analogs: Mapped[list["HistoricalAnalog"]] = relationship(
        back_populates="alert",
        foreign_keys="HistoricalAnalog.alert_id",
        lazy="selectin",
    )
    postmortem: Mapped["PostMortem | None"] = relationship(
        back_populates="alert", uselist=False,
    )
    feedbacks: Mapped[list["AnalystFeedback"]] = relationship(
        back_populates="alert", lazy="selectin",
    )
    escalations: Mapped[list["AlertEscalation"]] = relationship(
        back_populates="alert", lazy="selectin",
    )
    trigger_rule: Mapped["AlertRule | None"] = relationship(
        back_populates="created_alerts",
    )
    rule_trigger: Mapped["AlertRuleTrigger | None"] = relationship(
        back_populates="alert",
    )


# ═════════════════════════════════════════════════════════════════════════
# 8. EVIDENCE CHAIN — Full audit trail from alert to raw bytes
# ═════════════════════════════════════════════════════════════════════════

class EvidenceChain(Base, TimestampMixin):
    """
    Each row is one "hop" in the evidence trail.  To reconstruct the
    complete lineage for an auditor, collect all EvidenceChain rows for
    a given alert_id.

    Fields store arrays of UUIDs pointing to:
      raw_ids → normalized_event_ids → series_ids → anomaly_ids

    Plus `explainability_text`: a plain-English narrative auto-generated
    by the explanation engine.
    """

    __tablename__ = "evidence_chain"
    __table_args__ = (
        Index("ix_evidence_alert", "alert_id"),
        {"schema": "alert", "comment": "Audit trail linking alerts to raw data"},
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Lineage References (arrays of UUIDs) ─────────────────────────────
    raw_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False,
        comment="UUIDs of RawIngestion rows that contributed",
    )
    normalized_event_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False,
        comment="UUIDs of NormalizedEvent rows",
    )
    series_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False,
        comment="UUIDs of SignalTimeSeries rows",
    )
    anomaly_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False,
        comment="UUIDs of AnomalyResult rows",
    )

    # ── Explanation ──────────────────────────────────────────────────────
    explainability_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Auto-generated narrative explaining how evidence connects",
    )
    evidence_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional structured data for the evidence visualization",
    )

    # ── Relationships ────────────────────────────────────────────────────
    alert: Mapped["Alert"] = relationship(
        back_populates="evidence_chains",
    )


# ═════════════════════════════════════════════════════════════════════════
# 9. HISTORICAL ANALOG — "We've seen this pattern before"
# ═════════════════════════════════════════════════════════════════════════

class HistoricalAnalog(Base, TimestampMixin):
    """
    Links a new alert to the top-N most similar historical alerts.
    Similarity is computed from the time-series shape + semantic
    cluster proximity.  Phase 2+ only.
    """

    __tablename__ = "historical_analog"
    __table_args__ = (
        Index("ix_analog_alert", "alert_id"),
        {"schema": "alert", "comment": "Similar historical patterns for context"},
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=False,
        comment="The NEW alert we are providing context for",
    )
    matched_alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=False,
        comment="The HISTORICAL alert that looks similar",
    )

    # ── Similarity ───────────────────────────────────────────────────────
    similarity_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="0.0 (no match) – 1.0 (identical pattern)",
    )
    similarity_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="dtw_cosine",
        comment="Algorithm used: dtw_cosine / euclidean / …",
    )

    # ── Context ──────────────────────────────────────────────────────────
    reference_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Start of the historical reference window",
    )
    reference_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="End of the historical reference window",
    )
    analog_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Plain-English description of the historical event",
    )

    # ── Relationships ────────────────────────────────────────────────────
    alert: Mapped["Alert"] = relationship(
        back_populates="historical_analogs",
        foreign_keys=[alert_id],
    )
    matched_alert: Mapped["Alert"] = relationship(
        foreign_keys=[matched_alert_id],
    )


# ═════════════════════════════════════════════════════════════════════════
# 10. POST-MORTEM — "What actually happened?"
# ═════════════════════════════════════════════════════════════════════════

class PostMortem(Base, TimestampMixin, AuditMixin):
    """
    Retrospective label applied after the real-world situation resolves.
    This is the ground-truth dataset that the backtesting engine and
    the RL feedback loop learn from.
    """

    __tablename__ = "post_mortem"
    __table_args__ = (
        Index("ix_pm_outcome", "event_outcome"),
        {"schema": "alert", "comment": "Retrospective outcome labels for alerts"},
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="One post-mortem per alert",
    )

    # ── Outcome ──────────────────────────────────────────────────────────
    event_outcome: Mapped[EventOutcome] = mapped_column(
        nullable=False,
        comment="true_positive / false_positive / inconclusive",
    )
    impact_domain: Mapped[ImpactDomain | None] = mapped_column(
        nullable=True,
        comment="finance / geopolitical / health / civil_unrest / …",
    )
    impact_severity: Mapped[Severity | None] = mapped_column(
        nullable=True,
        comment="Retrospective severity of the actual event",
    )

    # ── Narrative ────────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Free-text analyst notes on what happened",
    )
    external_references: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Links to news articles, government reports, etc.",
    )

    # ── Timing ───────────────────────────────────────────────────────────
    event_actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When the real-world event actually began",
    )
    event_actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When the real-world event resolved",
    )
    lead_time_hours: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Hours between alert creation and real-world event start",
    )

    # ── Relationships ────────────────────────────────────────────────────
    alert: Mapped["Alert"] = relationship(
        back_populates="postmortem",
    )


# ═════════════════════════════════════════════════════════════════════════
# 11. ANALYST FEEDBACK — Human-in-the-loop for RL
# ═════════════════════════════════════════════════════════════════════════

class AnalystFeedback(Base, TimestampMixin):
    """
    Simple Confirm / Dismiss verdict from analysts.
    Multiple analysts can vote on the same alert (majority rules).
    Over time these labels train the Reinforcement Learning layer
    that tunes ensemble weights.
    """

    __tablename__ = "analyst_feedback"
    __table_args__ = (
        Index("ix_feedback_alert", "alert_id"),
        {"schema": "alert", "comment": "Analyst confirm/dismiss verdicts"},
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Analyst's identity (from auth provider)",
    )

    # ── Verdict ──────────────────────────────────────────────────────────
    verdict: Mapped[FeedbackVerdict] = mapped_column(
        nullable=False,
        comment="confirm or dismiss",
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Analyst's self-reported confidence in the verdict (0–1)",
    )
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional free-text reasoning",
    )

    # ── RL Metadata ──────────────────────────────────────────────────────
    was_used_for_training: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True once the RL training loop has consumed this row",
    )

    # ── Relationships ────────────────────────────────────────────────────
    alert: Mapped["Alert"] = relationship(
        back_populates="feedbacks",
    )


# ═════════════════════════════════════════════════════════════════════════
# 12. ALERT ESCALATION — Automatic severity increases
# ═════════════════════════════════════════════════════════════════════════

class AlertEscalation(Base, TimestampMixin):
    """
    Tracks automatic severity escalations for alerts based on time thresholds,
    score increases, or repeated occurrences. Enables audit trails for
    escalation decisions and prevents duplicate notifications.
    """

    __tablename__ = "alert_escalation"
    __table_args__ = (
        Index("ix_alert_escalation_alert_id", "alert_id"),
        Index("ix_alert_escalation_escalated_at", "escalated_at"),
        Index("ix_alert_escalation_trigger", "escalation_trigger"),
        {"comment": "Tracks automatic severity escalations for alerts"},
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=False,
        comment="The alert that was escalated",
    )

    # ── Escalation Details ───────────────────────────────────────────────
    previous_severity: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Severity before escalation (low/medium/high/critical)",
    )
    new_severity: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Severity after escalation (low/medium/high/critical)",
    )
    escalation_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Human-readable explanation of why escalation occurred",
    )

    # ── Timing ───────────────────────────────────────────────────────────
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow,
        comment="When the escalation occurred",
    )

    # ── Trigger Information ──────────────────────────────────────────────
    escalation_trigger: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="What triggered escalation: 'time_based', 'score_increase', 'repeated'",
    )
    escalation_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional context (thresholds, time windows, etc.)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    alert: Mapped["Alert"] = relationship(
        back_populates="escalations",
    )


# ═════════════════════════════════════════════════════════════════════════# 13. ALERT SILENCE — Temporary alert suppression
# ═════════════════════════════════════════════════════════════════════════

class AlertSilence(Base, TimestampMixin):
    """
    Temporarily silence alerts to reduce noise during known events or maintenance.
    Supports silencing individual alerts, entity patterns, or global silencing.
    """

    __tablename__ = "alert_silence"
    __table_args__ = (
        Index("ix_alert_silence_alert_id", "alert_id"),
        Index("ix_alert_silence_entity_pattern", "entity_pattern"),
        Index("ix_alert_silence_expires_at", "expires_at"),
        Index("ix_alert_silence_is_active", "is_active"),
        {"comment": "Tracks alert silencing/snoozing rules"},
    )

    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="CASCADE"),
        nullable=True,
        comment="Specific alert to silence (null for pattern/global silences)",
    )

    # ── Silence Scope ─────────────────────────────────────────────────────
    entity_pattern: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
        comment="Regex pattern to match entity names (for entity-based silencing)",
    )

    # ── Silence Metadata ──────────────────────────────────────────────────
    silenced_by: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="User who created the silence rule",
    )
    reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Reason for silencing",
    )
    silence_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Type of silence: 'alert', 'entity', 'global'",
    )

    # ── Timing ───────────────────────────────────────────────────────────
    silenced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow,
        comment="When the silence was created",
    )
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Duration in minutes (null for indefinite)",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When the silence expires",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Whether this silence rule is currently active",
    )

    # ── Relationships ────────────────────────────────────────────────────
    alert: Mapped["Alert | None"] = relationship(
        backref="silences",
    )


# ═════════════════════════════════════════════════════════════════════════# 12. BACKTEST RUN / BACKTEST ALERT — Synthetic replays
# ═════════════════════════════════════════════════════════════════════════

class BacktestRun(Base, TimestampMixin, AuditMixin):
    """
    Metadata for a single synthetic backtest execution.

    The analyst selects a historical window and a set of detection
    parameters, then the backtest engine replays data through the
    anomaly pipeline and records what alerts WOULD have been generated.
    """

    __tablename__ = "backtest_run"
    __table_args__ = (
        Index("ix_backtest_status", "status"),
        {"schema": "backtest", "comment": "Synthetic backtest execution records"},
    )

    # ── Configuration ────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Human-readable name, e.g. '2023 Banking Stress replay'",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Historical replay starts here",
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Historical replay ends here",
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Full parameter snapshot (thresholds, weights, etc.)",
    )

    # ── Execution ────────────────────────────────────────────────────────
    status: Mapped[BacktestStatus] = mapped_column(
        nullable=False, default=BacktestStatus.PENDING,
        comment="pending → running → completed / failed",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )

    # ── Results Summary ──────────────────────────────────────────────────
    alerts_generated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Total alerts produced during replay",
    )
    true_positives: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    false_positives: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    missed_events: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Known real events that were NOT flagged",
    )
    results_summary: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Extended metrics: precision, recall, F1, lead-time dist",
    )

    # ── Relationships ────────────────────────────────────────────────────
    reconstructed_alerts: Mapped[list["BacktestAlert"]] = relationship(
        back_populates="backtest_run", lazy="selectin",
    )


class BacktestAlert(Base, TimestampMixin):
    """
    An alert that WOULD have been generated during the backtest window.
    Mirrors the structure of Alert but is isolated in the backtest
    schema so it never pollutes real operational data.
    """

    __tablename__ = "backtest_alert"
    __table_args__ = (
        Index("ix_bt_alert_run", "backtest_run_id"),
        {"schema": "backtest", "comment": "Hypothetical alerts from a backtest"},
    )

    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtest.backtest_run.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Mirrored Alert Fields ────────────────────────────────────────────
    primary_entity: Mapped[str] = mapped_column(
        String(1024), nullable=False,
    )
    severity: Mapped[Severity] = mapped_column(
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    ensemble_anomaly_score: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    source_weights: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(
        String(128), nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    signal_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    signal_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    # ── Ground-Truth Comparison ──────────────────────────────────────────
    matched_real_alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="SET NULL"),
        nullable=True,
        comment="If this backtest alert matches a real historical alert",
    )
    is_true_positive: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True,
        comment="Did this correspond to a real event? (from PostMortem)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    backtest_run: Mapped["BacktestRun"] = relationship(
        back_populates="reconstructed_alerts",
    )


# ═════════════════════════════════════════════════════════════════════════
# 14. ALERT RULE — User-defined conditions for alert generation
# ═════════════════════════════════════════════════════════════════════════

class AlertRule(Base, TimestampMixin, AuditMixin):
    """
    User-defined rules for generating alerts based on trend conditions.
    Defines when and how alerts should be created from trend data.
    """

    __tablename__ = "alert_rule"
    __table_args__ = (
        Index("ix_alert_rule_condition_type", "condition_type"),
        Index("ix_alert_rule_enabled", "enabled"),
        {"schema": "alert", "comment": "User-defined rules for alert generation"},
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Human-readable name for the rule",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Detailed description of what this rule detects",
    )

    # ── Rule Conditions ───────────────────────────────────────────────
    condition_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Type of condition: velocity_threshold, rank_change, interest_spike, correlation, etc.",
    )
    threshold_value: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Threshold value for the condition",
    )
    comparison_operator: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="Comparison operator: >, <, >=, <=, ==",
    )

    # ── Target Scope ───────────────────────────────────────────────────
    target_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True,
        comment="Specific keywords to monitor (empty = all keywords)",
    )
    target_categories: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True,
        comment="Categories to monitor (empty = all categories)",
    )
    geo_scope: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True,
        comment="Geographic regions to monitor (empty = all regions)",
    )

    # ── Alert Configuration ─────────────────────────────────────────────
    severity: Mapped[Severity] = mapped_column(
        nullable=False, default=Severity.MEDIUM,
        comment="Default severity for alerts created by this rule",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Whether this rule is active",
    )

    # ── Notification Settings ───────────────────────────────────────────
    notify_email: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Send email notifications for alerts from this rule",
    )
    notify_desktop: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Send desktop notifications for alerts from this rule",
    )
    email_recipients: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True,
        comment="Email addresses to notify",
    )

    # ── Cooldown Settings ───────────────────────────────────────────────
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60,
        comment="Minimum time between alerts for the same entity",
    )

    # ── Rule Metadata ───────────────────────────────────────────────────
    rule_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional rule configuration (time windows, patterns, etc.)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    triggers: Mapped[list["AlertRuleTrigger"]] = relationship(
        back_populates="rule", lazy="selectin",
    )
    created_alerts: Mapped[list["Alert"]] = relationship(
        back_populates="trigger_rule", lazy="selectin",
    )
    analytics: Mapped[list["AlertRuleAnalytics"]] = relationship(
        back_populates="rule", lazy="selectin",
    )


class AlertRuleTrigger(Base, TimestampMixin):
    """
    Tracks when alert rules were triggered to implement cooldowns and analytics.
    """

    __tablename__ = "alert_rule_trigger"
    __table_args__ = (
        Index("ix_alert_rule_trigger_rule_triggered", "rule_id", "created_at"),
        Index("ix_alert_rule_trigger_cooldown", "rule_id", "entity_value", "geo"),
        {"schema": "alert", "comment": "Tracks alert rule trigger history"},
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert_rule.id", ondelete="CASCADE"),
        nullable=False,
        comment="The rule that was triggered",
    )

    # ── Trigger Context ─────────────────────────────────────────────────
    entity_value: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="The entity (keyword, term) that triggered the rule",
    )
    geo: Mapped[str] = mapped_column(
        String(5), nullable=False,
        comment="Geographic region where trigger occurred",
    )

    # ── Trigger Values ──────────────────────────────────────────────────
    actual_value: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="The actual measured value that triggered the rule",
    )
    threshold_value: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="The threshold value that was exceeded",
    )

    # ── Result ──────────────────────────────────────────────────────────
    alert_created: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Whether an alert was actually created from this trigger",
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="SET NULL"),
        nullable=True,
        comment="The alert that was created (if any)",
    )

    # ── Trigger Metadata ────────────────────────────────────────────────
    trigger_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional context about the trigger (time series data, etc.)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    rule: Mapped["AlertRule"] = relationship(
        back_populates="triggers",
    )
    alert: Mapped["Alert | None"] = relationship(
        back_populates="rule_trigger",
    )


# ═════════════════════════════════════════════════════════════════════════
# 15. ALERT TEMPLATE — Customizable alert notification templates
# ═════════════════════════════════════════════════════════════════════════

class AlertTemplate(Base, TimestampMixin, AuditMixin):
    """
    Customizable templates for alert notifications with dynamic content.
    Supports HTML and plain text templates with Jinja2 variable substitution.
    """

    __tablename__ = "alert_template"
    __table_args__ = (
        Index("ix_alert_template_name", "name"),
        Index("ix_alert_template_is_default", "is_default"),
        {"comment": "Customizable alert notification templates"},
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Human-readable name for the template",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Description of when to use this template",
    )

    # ── Template Content ────────────────────────────────────────────────
    subject_template: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Jinja2 template for email subject line",
    )
    html_template: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Jinja2 template for HTML email body",
    )
    text_template: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Jinja2 template for plain text email body",
    )

    # ── Template Scope ──────────────────────────────────────────────────
    severity_filter: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True,
        comment="Severities this template applies to (empty = all severities)",
    )
    category_filter: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True,
        comment="Categories this template applies to (empty = all categories)",
    )

    # ── Template Settings ───────────────────────────────────────────────
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Whether this is the default template for matching alerts",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Whether this is a system template (cannot be deleted)",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Whether this template is active",
    )

    # ── Template Metadata ───────────────────────────────────────────────
    template_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional template configuration (CSS, images, etc.)",
    )

    def __repr__(self) -> str:
        return f"<AlertTemplate(id={self.id}, name='{self.name}', is_default={self.is_default})>"


# ═════════════════════════════════════════════════════════════════════════
# 12. ALERT RULE ANALYTICS — Performance tracking for alert rules
# ═════════════════════════════════════════════════════════════════════════

class AlertRuleAnalytics(Base, TimestampMixin):
    """
    Analytics and performance metrics for alert rules.

    Tracks effectiveness, false positive rates, and response times
    to help optimize alert rule configurations.
    """

    __tablename__ = "alert_rule_analytics"
    __table_args__ = (
        Index("ix_alert_rule_analytics_rule_id", "rule_id"),
        Index("ix_alert_rule_analytics_period", "period_start", "period_end"),
        {"schema": "alert", "comment": "Performance analytics for alert rules"},
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert_rule.id", ondelete="CASCADE"),
        nullable=False,
        comment="The alert rule being analyzed",
    )

    # ── Time Period ─────────────────────────────────────────────────────
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Start of the analytics period",
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="End of the analytics period",
    )

    # ── Alert Counts ────────────────────────────────────────────────────
    alerts_generated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Total alerts generated by this rule in the period",
    )
    alerts_confirmed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Alerts confirmed as true positives",
    )
    alerts_dismissed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Alerts dismissed as false positives",
    )
    alerts_escalated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Alerts that were escalated",
    )

    # ── Performance Metrics ─────────────────────────────────────────────
    average_response_time_minutes: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Average time from alert creation to resolution (minutes)",
    )
    precision_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Precision: confirmed / (confirmed + dismissed)",
    )
    recall_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Recall: confirmed / total relevant events (if available)",
    )
    effectiveness_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Overall effectiveness score (0-1)",
    )

    # ── Additional Metrics ──────────────────────────────────────────────
    false_positive_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="False positive rate: dismissed / total alerts",
    )
    alert_volume_trend: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Trend in alert volume (+/- percentage change)",
    )

    # ── Metadata ────────────────────────────────────────────────────────
    analytics_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional analytics data (severity distribution, etc.)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    rule: Mapped["AlertRule"] = relationship(back_populates="analytics")

    def __repr__(self) -> str:
        return f"<AlertRuleAnalytics(rule_id={self.rule_id}, period={self.period_start.date()}-{self.period_end.date()}, alerts={self.alerts_generated})>"


# ═════════════════════════════════════════════════════════════════════════
# 15. REPLAY MODE — Post-mortem simulator for debugging & training
# ═════════════════════════════════════════════════════════════════════════

class ReplaySession(Base, TimestampMixin, AuditMixin):
    """
    A replay session allows rewinding system state to analyze past decisions,
    test different parameters, and train analysts. Each session captures a
    time range and set of parameters for reproducible analysis.
    """

    __tablename__ = "replay_session"
    __table_args__ = (
        Index("ix_replay_user", "user_id"),
        Index("ix_replay_status", "status"),
        Index("ix_replay_time_range", "start_time", "end_time"),
        {"schema": "alert", "comment": "Replay sessions for post-mortem analysis"},
    )

    user_id: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="User who created this replay session",
    )
    name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Descriptive name for the replay session",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional description of replay purpose",
    )

    # ── Time Range ───────────────────────────────────────────────────────
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Start of replay time window",
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="End of replay time window",
    )

    # ── Replay Parameters ────────────────────────────────────────────────
    parameters: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Replay parameters: confidence_thresholds, detector_weights, etc.",
    )

    # ── Status & Progress ────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created",
        comment="Status: created, running, completed, failed",
    )
    progress_percentage: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Progress through the replay (0.0-1.0)",
    )

    # ── Results Summary ──────────────────────────────────────────────────
    alerts_generated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Number of alerts that would have been generated",
    )
    trades_simulated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Number of trades that would have been executed",
    )
    key_insights: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Key insights from the replay analysis",
    )

    # ── Relationships ────────────────────────────────────────────────────
    snapshots: Mapped[list["ReplaySnapshot"]] = relationship(
        back_populates="session", lazy="selectin", cascade="all, delete-orphan",
    )
    decisions: Mapped[list["ReplayDecision"]] = relationship(
        back_populates="session", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ReplaySession(id={self.id}, name='{self.name}', status='{self.status}')>"


class ReplaySnapshot(Base, TimestampMixin):
    """
    A snapshot of system state at a specific point in time during replay.
    Captures active signals, current positions, and system parameters.
    """

    __tablename__ = "replay_snapshot"
    __table_args__ = (
        Index("ix_snapshot_session_time", "session_id", "snapshot_time"),
        {"schema": "alert", "comment": "System state snapshots during replay"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.replay_session.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Timing ───────────────────────────────────────────────────────────
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Point in time this snapshot represents",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Sequential order within the replay session",
    )

    # ── System State ─────────────────────────────────────────────────────
    active_signals: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False,
        comment="Active signals at this point: [{'entity': str, 'score': float, ...}]",
    )
    system_parameters: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="System parameters at this time (thresholds, weights, etc.)",
    )
    market_conditions: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Market conditions snapshot (volatility, trends, etc.)",
    )

    # ── Portfolio State (if applicable) ───────────────────────────────────
    portfolio_state: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Portfolio state: positions, cash, P&L, etc.",
    )

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped["ReplaySession"] = relationship(back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<ReplaySnapshot(session_id={self.session_id}, time={self.snapshot_time}, seq={self.sequence_number})>"


class ReplayDecision(Base, TimestampMixin):
    """
    A decision point during replay: alert generation, trade execution, or
    parameter changes. Links to original alerts/trades for comparison.
    """

    __tablename__ = "replay_decision"
    __table_args__ = (
        Index("ix_decision_session_time", "session_id", "decision_time"),
        Index("ix_decision_type", "decision_type"),
        {"schema": "alert", "comment": "Decisions made during replay sessions"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.replay_session.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Decision Metadata ────────────────────────────────────────────────
    decision_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When this decision was made in replay time",
    )
    decision_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="Type: alert_generated, trade_executed, parameter_changed, etc.",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Sequential order within the replay session",
    )

    # ── Decision Details ─────────────────────────────────────────────────
    decision_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Decision-specific data (alert details, trade parameters, etc.)",
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Confidence score associated with this decision",
    )

    # ── Comparison to Reality ────────────────────────────────────────────
    original_alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.alert.id", ondelete="SET NULL"),
        nullable=True,
        comment="Original alert this decision relates to (for comparison)",
    )
    original_trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading.order.id", ondelete="SET NULL"),
        nullable=True,
        comment="Original trade this decision relates to (for comparison)",
    )

    # ── Outcome Analysis ─────────────────────────────────────────────────
    would_have_occurred: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True,
        comment="Whether this decision would have occurred in reality",
    )
    impact_analysis: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Analysis of decision impact (P&L, risk, etc.)",
    )

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped["ReplaySession"] = relationship(back_populates="decisions")
    original_alert: Mapped["Alert | None"] = relationship()
    original_trade: Mapped["Order | None"] = relationship()

    def __repr__(self) -> str:
        return f"<ReplayDecision(session_id={self.session_id}, type='{self.decision_type}', seq={self.sequence_number})>"


class ReplaySignal(Base, TimestampMixin):
    """
    Signals that were active during a replay session. Allows analysis of
    how different parameters affect signal detection and processing.
    """

    __tablename__ = "replay_signal"
    __table_args__ = (
        Index("ix_replay_signal_session", "session_id"),
        Index("ix_replay_signal_entity", "entity_value"),
        Index("ix_replay_signal_time", "signal_time"),
        {"schema": "alert", "comment": "Signals processed during replay sessions"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.replay_session.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Signal Identity ──────────────────────────────────────────────────
    entity_value: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="The entity this signal is about",
    )
    signal_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When this signal occurred",
    )

    # ── Signal Scores ────────────────────────────────────────────────────
    original_scores: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Original anomaly scores from detectors",
    )
    adjusted_scores: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Scores after applying replay parameters",
    )

    # ── Processing Results ───────────────────────────────────────────────
    would_trigger_alert: Mapped[bool] = mapped_column(
        Boolean, nullable=False,
        comment="Whether this signal would trigger an alert with current parameters",
    )
    confidence_level: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Final confidence score (0.0-1.0)",
    )

    # ── Analysis Data ────────────────────────────────────────────────────
    signal_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Additional signal metadata (source, trend data, etc.)",
    )
    parameter_sensitivity: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="How sensitive this signal is to parameter changes",
    )

    # ── Relationships ────────────────────────────────────────────────────
    session: Mapped["ReplaySession"] = relationship()

    def __repr__(self) -> str:
        return f"<ReplaySignal(session_id={self.session_id}, entity='{self.entity_value}', confidence={self.confidence_level:.2f})>"
