"""
validators.py — Pydantic schemas for API request/response validation.

These are the "gatekeepers" that sit between the outside world and the
database.  Every piece of data entering or leaving the system is
validated here BEFORE it touches the ORM.

Naming convention:
  • *Create  — inbound payloads for creating new rows
  • *Read    — outbound responses (includes id + timestamps)
  • *Update  — partial updates (all fields optional)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


from vanguard_signal.schema.enums import (
    AlertStatus,
    BacktestStatus,
    EntityType,
    EventOutcome,
    FeedbackVerdict,
    HealthStatus,
    ImpactDomain,
    Severity,
    SourceType,
    TimeBucket,
)


# ── Shared Bases ─────────────────────────────────────────────────────────

class _ReadBase(BaseModel):
    """Common fields present on every Read schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ═════════════════════════════════════════════════════════════════════════
# SOURCE REGISTRY
# ═════════════════════════════════════════════════════════════════════════

class SourceRegistryCreate(BaseModel):
    name: str = Field(..., max_length=128, examples=["google_trends"])
    source_type: SourceType
    description: str | None = None
    api_endpoint: str | None = None
    auth_method: str | None = Field(None, pattern=r"^(oauth2|api_key|iam_role|none)$")
    update_frequency_seconds: int = Field(3600, ge=60)
    data_latency_seconds: int = Field(0, ge=0)
    default_weight: float = Field(1.0, ge=0.0, le=10.0)
    is_active: bool = True


class SourceRegistryRead(_ReadBase):
    name: str
    source_type: SourceType
    description: str | None
    api_endpoint: str | None
    auth_method: str | None
    update_frequency_seconds: int
    data_latency_seconds: int
    health_status: HealthStatus
    last_ingested_at: datetime | None
    consecutive_failures: int
    default_weight: float
    is_active: bool


class SourceRegistryUpdate(BaseModel):
    description: str | None = None
    api_endpoint: str | None = None
    auth_method: str | None = None
    update_frequency_seconds: int | None = Field(None, ge=60)
    data_latency_seconds: int | None = None
    default_weight: float | None = Field(None, ge=0.0, le=10.0)
    is_active: bool | None = None
    health_status: HealthStatus | None = None


# ═════════════════════════════════════════════════════════════════════════
# RAW INGESTION
# ═════════════════════════════════════════════════════════════════════════

class RawIngestionCreate(BaseModel):
    source_id: UUID
    ingested_at: datetime
    payload: dict[str, Any]
    payload_hash: str = Field(..., min_length=64, max_length=64)
    payload_size_bytes: int = Field(..., ge=0)
    schema_version: str = "1.0"

    @field_validator("payload_hash")
    @classmethod
    def hash_must_be_hex(cls, v: str) -> str:
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("payload_hash must be a valid hex string")
        return v.lower()


class RawIngestionRead(_ReadBase):
    source_id: UUID
    ingested_at: datetime
    payload: dict[str, Any]
    payload_hash: str
    payload_size_bytes: int
    schema_version: str
    is_valid: bool
    validation_errors: dict[str, Any] | None


# ═════════════════════════════════════════════════════════════════════════
# NORMALIZED EVENT
# ═════════════════════════════════════════════════════════════════════════

class NormalizedEventCreate(BaseModel):
    raw_id: UUID
    source_id: UUID
    event_time: datetime
    entity_type: EntityType
    entity_value: str = Field(..., max_length=1024)
    metric_value: float
    geo: str | None = Field(None, max_length=8)
    language: str | None = Field(None, max_length=8)
    metadata_extra: dict[str, Any] | None = None


class NormalizedEventRead(_ReadBase):
    raw_id: UUID
    source_id: UUID
    event_time: datetime
    entity_type: EntityType
    entity_value: str
    metric_value: float
    geo: str | None
    language: str | None
    metadata_extra: dict[str, Any] | None


# ═════════════════════════════════════════════════════════════════════════
# SIGNAL TIME SERIES
# ═════════════════════════════════════════════════════════════════════════

class SignalTimeSeriesCreate(BaseModel):
    entity_value: str = Field(..., max_length=1024)
    source_id: UUID
    bucket_size: TimeBucket
    bucket_start: datetime
    bucket_end: datetime
    value: float
    sample_count: int = Field(0, ge=0)
    coverage_score: float = Field(1.0, ge=0.0, le=1.0)


class SignalTimeSeriesRead(_ReadBase):
    entity_value: str
    source_id: UUID
    bucket_size: TimeBucket
    bucket_start: datetime
    bucket_end: datetime
    value: float
    sample_count: int
    coverage_score: float


# ═════════════════════════════════════════════════════════════════════════
# ANOMALY RESULT
# ═════════════════════════════════════════════════════════════════════════

class AnomalyResultCreate(BaseModel):
    series_id: UUID
    detection_time: datetime
    # STL
    stl_trend: float | None = None
    stl_seasonal: float | None = None
    stl_residual: float | None = None
    stl_residual_zscore: float | None = None
    # Isolation Forest
    iforest_score: float | None = None
    iforest_contamination: float | None = None
    # CUSUM
    cusum_score: float | None = None
    cusum_threshold: float | None = None
    cusum_drift: float | None = None
    # Velocity
    velocity_score: float | None = None
    velocity_acceleration: float | None = None
    # Ensemble
    weight_stl: float = 0.30
    weight_iforest: float = 0.25
    weight_cusum: float = 0.25
    weight_velocity: float = 0.20
    ensemble_score: float
    is_anomaly: bool = False
    ensemble_threshold: float


class AnomalyResultRead(_ReadBase):
    series_id: UUID
    detection_time: datetime
    stl_trend: float | None
    stl_seasonal: float | None
    stl_residual: float | None
    stl_residual_zscore: float | None
    iforest_score: float | None
    iforest_contamination: float | None
    cusum_score: float | None
    cusum_threshold: float | None
    cusum_drift: float | None
    velocity_score: float | None
    velocity_acceleration: float | None
    weight_stl: float
    weight_iforest: float
    weight_cusum: float
    weight_velocity: float
    ensemble_score: float
    is_anomaly: bool
    ensemble_threshold: float


# ═════════════════════════════════════════════════════════════════════════
# ALERT
# ═════════════════════════════════════════════════════════════════════════

class AlertCreate(BaseModel):
    primary_entity: str = Field(..., max_length=1024)
    related_entities: list[str] | None = None
    anomaly_result_id: UUID | None = None
    severity: Severity = Severity.MEDIUM
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    ensemble_anomaly_score: float
    source_weights: dict[str, float]
    semantic_drift_score: float = 0.0
    reason_code: str = Field(..., max_length=128)
    summary_text: str
    signal_start: datetime
    signal_end: datetime


class AlertRead(_ReadBase):
    primary_entity: str
    related_entities: list[str] | None
    anomaly_result_id: UUID | None
    severity: Severity
    status: AlertStatus
    confidence_score: float
    ensemble_anomaly_score: float
    source_weights: dict[str, float]
    semantic_drift_score: float
    reason_code: str
    summary_text: str
    signal_start: datetime
    signal_end: datetime


class AlertUpdate(BaseModel):
    severity: Severity | None = None
    status: AlertStatus | None = None


# ═════════════════════════════════════════════════════════════════════════
# EVIDENCE CHAIN
# ═════════════════════════════════════════════════════════════════════════

class EvidenceChainCreate(BaseModel):
    alert_id: UUID
    raw_ids: list[str]
    normalized_event_ids: list[str]
    series_ids: list[str]
    anomaly_ids: list[str]
    explainability_text: str
    evidence_metadata: dict[str, Any] | None = None


class EvidenceChainRead(_ReadBase):
    alert_id: UUID
    raw_ids: list[str]
    normalized_event_ids: list[str]
    series_ids: list[str]
    anomaly_ids: list[str]
    explainability_text: str
    evidence_metadata: dict[str, Any] | None


# ═════════════════════════════════════════════════════════════════════════
# HISTORICAL ANALOG
# ═════════════════════════════════════════════════════════════════════════

class HistoricalAnalogCreate(BaseModel):
    alert_id: UUID
    matched_alert_id: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    similarity_method: str = "dtw_cosine"
    reference_period_start: datetime
    reference_period_end: datetime
    analog_summary: str | None = None


class HistoricalAnalogRead(_ReadBase):
    alert_id: UUID
    matched_alert_id: UUID
    similarity_score: float
    similarity_method: str
    reference_period_start: datetime
    reference_period_end: datetime
    analog_summary: str | None


# ═════════════════════════════════════════════════════════════════════════
# POST-MORTEM
# ═════════════════════════════════════════════════════════════════════════

class PostMortemCreate(BaseModel):
    alert_id: UUID
    event_outcome: EventOutcome
    impact_domain: ImpactDomain | None = None
    impact_severity: Severity | None = None
    notes: str | None = None
    external_references: dict[str, Any] | None = None
    event_actual_start: datetime | None = None
    event_actual_end: datetime | None = None
    lead_time_hours: float | None = None


class PostMortemRead(_ReadBase):
    alert_id: UUID
    event_outcome: EventOutcome
    impact_domain: ImpactDomain | None
    impact_severity: Severity | None
    notes: str | None
    external_references: dict[str, Any] | None
    event_actual_start: datetime | None
    event_actual_end: datetime | None
    lead_time_hours: float | None


# ═════════════════════════════════════════════════════════════════════════
# ANALYST FEEDBACK
# ═════════════════════════════════════════════════════════════════════════

class AnalystFeedbackCreate(BaseModel):
    alert_id: UUID
    user_id: str = Field(..., max_length=256)
    verdict: FeedbackVerdict
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    comment: str | None = None


class AnalystFeedbackRead(_ReadBase):
    alert_id: UUID
    user_id: str
    verdict: FeedbackVerdict
    confidence: float | None
    comment: str | None
    was_used_for_training: bool


# ═════════════════════════════════════════════════════════════════════════
# BACKTEST
# ═════════════════════════════════════════════════════════════════════════

class BacktestRunCreate(BaseModel):
    name: str = Field(..., max_length=256)
    description: str | None = None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any]


class BacktestRunRead(_ReadBase):
    name: str
    description: str | None
    window_start: datetime
    window_end: datetime
    parameters: dict[str, Any]
    status: BacktestStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    alerts_generated: int
    true_positives: int
    false_positives: int
    missed_events: int
    results_summary: dict[str, Any] | None


class BacktestAlertRead(_ReadBase):
    backtest_run_id: UUID
    primary_entity: str
    severity: Severity
    confidence_score: float
    ensemble_anomaly_score: float
    source_weights: dict[str, float]
    reason_code: str
    summary_text: str
    signal_start: datetime
    signal_end: datetime
    matched_real_alert_id: UUID | None
    is_true_positive: bool | None


# ═════════════════════════════════════════════════════════════════════════
# ALERT TEMPLATES
# ═════════════════════════════════════════════════════════════════════════

class AlertTemplateCreate(BaseModel):
    """Schema for creating new alert templates."""
    name: str = Field(..., max_length=100, description="Human-readable name for the template")
    description: str | None = Field(None, description="Description of when to use this template")
    subject_template: str = Field(..., max_length=255, description="Jinja2 template for email subject line")
    html_template: str = Field(..., description="Jinja2 template for HTML email body")
    text_template: str = Field(..., description="Jinja2 template for plain text email body")
    severity_filter: list[str] | None = Field(None, description="Severities this template applies to")
    category_filter: list[str] | None = Field(None, description="Categories this template applies to")
    is_default: bool = Field(False, description="Whether this is the default template")
    enabled: bool = Field(True, description="Whether this template is active")


class AlertTemplateUpdate(BaseModel):
    """Schema for updating alert templates."""
    name: str | None = Field(None, max_length=100, description="Human-readable name for the template")
    description: str | None = Field(None, description="Description of when to use this template")
    subject_template: str | None = Field(None, max_length=255, description="Jinja2 template for email subject line")
    html_template: str | None = Field(None, description="Jinja2 template for HTML email body")
    text_template: str | None = Field(None, description="Jinja2 template for plain text email body")
    severity_filter: list[str] | None = Field(None, description="Severities this template applies to")
    category_filter: list[str] | None = Field(None, description="Categories this template applies to")
    is_default: bool | None = Field(None, description="Whether this is the default template")
    enabled: bool | None = Field(None, description="Whether this template is active")


class AlertTemplateRead(_ReadBase):
    """Schema for reading alert templates."""
    name: str
    description: str | None
    subject_template: str
    html_template: str
    text_template: str
    severity_filter: list[str] | None
    category_filter: list[str] | None
    is_default: bool
    is_system: bool
    enabled: bool
    template_metadata: dict[str, Any] | None
    created_by: str | None
    updated_by: str | None
