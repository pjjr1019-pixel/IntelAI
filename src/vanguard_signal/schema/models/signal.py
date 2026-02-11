"""
signal.py — Time-series, anomaly detection, and semantic models.

Tables
------
SignalTimeSeries      – Aggregated time-bucketed metrics per entity.
AnomalyResult        – Per-bucket output of the three ensemble detectors.
SemanticCluster       – Phase 2: SBERT-based topic clusters.
SemanticClusterMember – Phase 2: Many-to-many entity↔cluster mapping.

Design note:  Anomaly scores are stored DECOMPOSED (one column per
detector) so every confidence number is fully explainable for audit.
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vanguard_signal.schema.base import AuditMixin, Base, TimestampMixin
from vanguard_signal.schema.enums import TimeBucket


# ═════════════════════════════════════════════════════════════════════════
# 4. SIGNAL TIME SERIES — Aggregated observation windows
# ═════════════════════════════════════════════════════════════════════════

class SignalTimeSeries(Base, TimestampMixin):
    """
    One row = one (entity, time_bucket) aggregation.

    Example: entity_value='bank run', bucket_size=DAY,
             bucket_start='2023-03-10'  →  value = 84.2

    `coverage_score` captures data completeness: 1.0 = every expected
    data point arrived; <1.0 = partial (e.g. source was degraded).
    """

    __tablename__ = "signal_time_series"
    __table_args__ = (
        UniqueConstraint(
            "entity_value", "source_id", "bucket_size", "bucket_start",
            name="uq_signal_entity_bucket",
        ),
        Index("ix_signal_entity_time", "entity_value", "bucket_start"),
        Index("ix_signal_source_bucket", "source_id", "bucket_start"),
        Index("ix_signal_bucket_start", "bucket_start"),
        Index("ix_signal_bucket_size", "bucket_size"),
        {"schema": "signal", "comment": "Aggregated time-series per entity"},
    )

    # ── Identity ─────────────────────────────────────────────────────────
    entity_value: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="Search term, page title, etc.",
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion.source_registry.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Which source produced this series",
    )

    # ── Time Window ──────────────────────────────────────────────────────
    bucket_size: Mapped[TimeBucket] = mapped_column(
        nullable=False,
        comment="Aggregation granularity: hour / day / week / month",
    )
    bucket_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Inclusive start of this time bucket",
    )
    bucket_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Exclusive end of this time bucket",
    )

    # ── Value ────────────────────────────────────────────────────────────
    value: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Aggregated metric (mean interest, total views, …)",
    )
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Number of NormalizedEvents that were aggregated",
    )
    coverage_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0,
        comment="1.0 = full data; <1.0 = degraded coverage",
    )

    # ── Relationships ────────────────────────────────────────────────────
    anomaly_results: Mapped[list["AnomalyResult"]] = relationship(
        back_populates="series", lazy="selectin",
    )


# ═════════════════════════════════════════════════════════════════════════
# 5. ANOMALY RESULT — Ensemble detector outputs
# ═════════════════════════════════════════════════════════════════════════

class AnomalyResult(Base, TimestampMixin):
    """
    Stores the output of ALL three anomaly detectors for one time-series
    bucket plus the final ensemble score.

    Explainability contract:
      ensemble_score = w_stl * stl_residual_zscore
                     + w_if  * iforest_score
                     + w_cusum * cusum_score

    Weights are stored so auditors can reproduce the math exactly.
    """

    __tablename__ = "anomaly_result"
    __table_args__ = (
        UniqueConstraint(
            "series_id", "detection_time",
            name="uq_anomaly_series_time",
        ),
        Index("ix_anomaly_flag", "is_anomaly"),
        Index("ix_anomaly_ensemble", "ensemble_score"),
        {"schema": "signal", "comment": "Per-bucket ensemble anomaly scores"},
    )

    # ── Foreign Keys ─────────────────────────────────────────────────────
    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signal.signal_time_series.id", ondelete="CASCADE"),
        nullable=False,
        comment="The time-series bucket that was evaluated",
    )

    detection_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When this detection pass ran",
    )

    # ── STL Decomposition (Seasonality Removal) ─────────────────────────
    stl_trend: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Trend component from STL decomposition",
    )
    stl_seasonal: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Seasonal component from STL decomposition",
    )
    stl_residual: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Residual after removing trend + seasonality",
    )
    stl_residual_zscore: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Z-score of the residual (how many σ from mean)",
    )

    # ── Isolation Forest (Point Anomaly) ─────────────────────────────────
    iforest_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Isolation Forest anomaly score (−1 to 0 range typical)",
    )
    iforest_contamination: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Contamination parameter used for this run",
    )

    # ── CUSUM (Mean-Shift Detection) ─────────────────────────────────────
    cusum_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="CUSUM statistic; large values → sustained mean shift",
    )
    cusum_threshold: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="The threshold that was in effect for CUSUM",
    )
    cusum_drift: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Allowable drift parameter used for this run",
    )

    # ── Velocity (Rate-of-Change Detection) ──────────────────────────────
    velocity_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Velocity detector normalised score (0–1); high = rapid acceleration",
    )
    velocity_acceleration: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Raw second derivative (acceleration) at the latest point",
    )

    # ── Ensemble (Combined Decision) ─────────────────────────────────────
    weight_stl: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.4,
        comment="Weight assigned to STL Z-score in the ensemble",
    )
    weight_iforest: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.3,
        comment="Weight assigned to Isolation Forest score",
    )
    weight_cusum: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.3,
        comment="Weight assigned to CUSUM score",
    )
    weight_velocity: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.2,
        comment="Weight assigned to Velocity detector score",
    )
    ensemble_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Final combined anomaly score",
    )
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True when ensemble_score exceeds alert threshold",
    )
    ensemble_threshold: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="The threshold that was in effect for this decision",
    )

    # ── Relationships ────────────────────────────────────────────────────
    series: Mapped["SignalTimeSeries"] = relationship(
        back_populates="anomaly_results",
    )


# ═════════════════════════════════════════════════════════════════════════
# 6. SEMANTIC CLUSTER — Phase 2: Transformer-based topic groups
# ═════════════════════════════════════════════════════════════════════════

class SemanticCluster(Base, TimestampMixin):
    """
    Represents a cluster of semantically similar entities at a point
    in time.  The `drift_score` quantifies how fast the cluster centroid
    is moving in embedding space — a proxy for "Semantic Drift."

    A high drift_score means people are rapidly changing HOW they talk
    about a topic (curiosity → intent), which is a key pre-event signal.
    """

    __tablename__ = "semantic_cluster"
    __table_args__ = (
        Index("ix_cluster_drift", "drift_score"),
        {"schema": "signal", "comment": "SBERT topic clusters with drift tracking"},
    )

    # ── Time Window ──────────────────────────────────────────────────────
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Start of the observation window",
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="End of the observation window",
    )

    # ── Cluster Attributes ───────────────────────────────────────────────
    label: Mapped[str | None] = mapped_column(
        String(256), nullable=True,
        comment="Auto-generated or analyst-assigned cluster label",
    )
    centroid_vector: Mapped[list[float]] = mapped_column(
        ARRAY(Float), nullable=False,
        comment="Mean SBERT embedding vector (768-d or 384-d)",
    )
    cluster_size: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Number of unique entities in this cluster",
    )

    # ── Drift Tracking ───────────────────────────────────────────────────
    drift_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Cosine distance the centroid moved since the prior window",
    )
    drift_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True when drift exceeds threshold (rapid semantic shift)",
    )
    prior_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signal.semantic_cluster.id", ondelete="SET NULL"),
        nullable=True,
        comment="The same logical cluster from the previous time window",
    )

    # ── Relationships ────────────────────────────────────────────────────
    members: Mapped[list["SemanticClusterMember"]] = relationship(
        back_populates="cluster", lazy="selectin",
    )


class SemanticClusterMember(Base, TimestampMixin):
    """
    Association table: which entities belong to which cluster,
    along with their individual embedding and distance from centroid.
    """

    __tablename__ = "semantic_cluster_member"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id", "entity_value",
            name="uq_cluster_entity",
        ),
        {"schema": "signal", "comment": "Entity membership in semantic clusters"},
    )

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signal.semantic_cluster.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_value: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        comment="The search term, page title, etc.",
    )
    embedding_vector: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float), nullable=True,
        comment="This entity's individual SBERT embedding",
    )
    distance_to_centroid: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Cosine distance from entity embedding to cluster centroid",
    )

    # ── Relationships ────────────────────────────────────────────────────
    cluster: Mapped["SemanticCluster"] = relationship(
        back_populates="members",
    )
