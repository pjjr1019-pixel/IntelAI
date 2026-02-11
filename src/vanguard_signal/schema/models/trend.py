"""
Trend data models for historical storage and analysis.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from ..base import Base


class TrendSnapshot(Base):
    """
    Historical snapshot of trending data at a point in time.
    Stores complete trend data for later analysis and comparison.
    """
    __tablename__ = "trend_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geo = Column(String(5), nullable=False, index=True)  # ISO country code
    captured_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    total_trends = Column(Integer, nullable=False, default=0)
    source = Column(String(50), nullable=False, default="rss")  # rss, pytrends, manual

    # JSON storage for complete trend data
    trends_data = Column(JSON, nullable=False)

    # Metadata
    processing_time_ms = Column(Integer, nullable=True)
    rate_limited = Column(Integer, nullable=False, default=0)  # 0=no, 1=yes
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_trend_snapshots_geo_captured', 'geo', 'captured_at'),
        Index('idx_trend_snapshots_captured', 'captured_at'),
    )


class TrendKeyword(Base):
    """
    Individual trend keywords with historical tracking.
    Allows for longitudinal analysis of specific keywords.
    """
    __tablename__ = "trend_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False, index=True)
    geo = Column(String(5), nullable=False, index=True)

    # Current/latest data
    current_rank = Column(Integer, nullable=True)
    current_traffic = Column(String(50), nullable=True)
    current_traffic_value = Column(Integer, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Historical aggregates
    first_seen = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    peak_rank = Column(Integer, nullable=True)  # Best rank ever achieved
    total_appearances = Column(Integer, nullable=False, default=1)
    avg_rank = Column(Float, nullable=True)

    # Velocity tracking
    velocity_trend = Column(JSON, nullable=True)  # Store velocity history as JSON array
    direction_changes = Column(Integer, nullable=False, default=0)

    # Related data
    category = Column(String(100), nullable=True)  # Auto-categorized
    news_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index('idx_trend_keywords_keyword_geo', 'keyword', 'geo'),
        Index('idx_trend_keywords_last_seen', 'last_seen'),
        Index('idx_trend_keywords_category', 'category'),
    )


class TrendTimeSeries(Base):
    """
    Time series data for individual keywords.
    Stores hourly/daily interest scores over time.
    """
    __tablename__ = "trend_time_series"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword_id = Column(Integer, ForeignKey('signal.trend_keywords.id'), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Interest scores
    interest_score = Column(Float, nullable=False)  # 0-100 scale
    rank_at_time = Column(Integer, nullable=True)

    # Computed metrics
    velocity = Column(Float, nullable=True)  # Rate of change
    acceleration = Column(Float, nullable=True)  # Change in velocity

    # Metadata
    geo = Column(String(5), nullable=False, index=True)
    data_source = Column(String(50), nullable=False, default="pytrends")  # pytrends, estimated, manual

    __table_args__ = (
        Index('idx_trend_time_series_keyword_timestamp', 'keyword_id', 'timestamp'),
        Index('idx_trend_time_series_geo_timestamp', 'geo', 'timestamp'),
    )

    # Relationships
    # keyword = relationship("TrendKeyword", primaryjoin="TrendTimeSeries.keyword_id == TrendKeyword.id")


class TrendAlert(Base):
    """
    Alerts generated based on trend analysis.
    Tracks significant changes, spikes, or patterns.
    """
    __tablename__ = "trend_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword_id = Column(Integer, ForeignKey('trend_keywords.id'), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # spike, breakout, crash, seasonal, etc.

    # Alert details
    triggered_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    message = Column(Text, nullable=False)

    # Metrics at time of alert
    rank_at_alert = Column(Integer, nullable=True)
    interest_at_alert = Column(Float, nullable=True)
    velocity_at_alert = Column(Float, nullable=True)
    pct_change_24h = Column(Float, nullable=True)

    # Context
    geo = Column(String(5), nullable=False, index=True)
    related_news = Column(JSON, nullable=True)  # Related news articles
    additional_data = Column(JSON, nullable=True)  # Any extra context

    # Status
    acknowledged = Column(Integer, nullable=False, default=0)  # 0=unacknowledged, 1=acknowledged
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(100), nullable=True)

    __table_args__ = (
        Index('idx_trend_alerts_keyword_triggered', 'keyword_id', 'triggered_at'),
        Index('idx_trend_alerts_type_triggered', 'alert_type', 'triggered_at'),
        Index('idx_trend_alerts_severity', 'severity'),
    )

    # Relationships
    keyword = relationship("TrendKeyword", primaryjoin="TrendAlert.keyword_id == TrendKeyword.id")


class PredictionModel(Base):
    """
    Stored trained prediction models for trend forecasting.
    Persists model parameters, metadata, and performance metrics.
    """
    __tablename__ = "prediction_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword_id = Column(Integer, ForeignKey('signal.trend_keywords.id'), nullable=False, index=True)

    # Model metadata
    model_type = Column(String(50), nullable=False)  # 'arima', 'exponential_smoothing', 'linear_regression', 'naive'
    model_version = Column(String(20), nullable=False, default='1.0')
    is_active = Column(Boolean, nullable=False, default=True)

    # Training information
    trained_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    training_data_start = Column(DateTime(timezone=True), nullable=True)
    training_data_end = Column(DateTime(timezone=True), nullable=True)
    training_samples = Column(Integer, nullable=True)

    # Model parameters (stored as JSON)
    model_parameters = Column(JSON, nullable=False)  # Model coefficients, hyperparameters, etc.

    # Performance metrics
    training_mae = Column(Float, nullable=True)  # Mean Absolute Error
    training_rmse = Column(Float, nullable=True)  # Root Mean Square Error
    training_mape = Column(Float, nullable=True)  # Mean Absolute Percentage Error
    validation_score = Column(Float, nullable=True)  # Cross-validation score

    # Model state
    last_prediction_at = Column(DateTime(timezone=True), nullable=True)
    prediction_count = Column(Integer, nullable=False, default=0)
    retrain_required = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index('idx_prediction_models_keyword_active', 'keyword_id', 'is_active'),
        Index('idx_prediction_models_type_version', 'model_type', 'model_version'),
    )

    # Relationships
    # keyword = relationship("TrendKeyword", primaryjoin="PredictionModel.keyword_id == TrendKeyword.id")

    def __repr__(self):
        return f"<PredictionModel(keyword_id={self.keyword_id}, type='{self.model_type}', active={self.is_active})>"


class PredictionResult(Base):
    """
    Cached prediction results for performance and audit trail.
    Stores predictions with confidence intervals and actual outcomes.
    """
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey('prediction_models.id'), nullable=False, index=True)

    # Prediction details
    prediction_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    horizon_hours = Column(Integer, nullable=False)  # Prediction horizon in hours
    predicted_value = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=True)
    confidence_upper = Column(Float, nullable=True)

    # Actual outcome (filled in after the fact)
    actual_value = Column(Float, nullable=True)
    actual_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Performance tracking
    prediction_error = Column(Float, nullable=True)  # |predicted - actual|
    prediction_accuracy = Column(Float, nullable=True)  # Accuracy score

    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_prediction_results_model_timestamp', 'model_id', 'prediction_timestamp'),
        Index('idx_prediction_results_horizon', 'horizon_hours'),
    )

    # Relationships
    model = relationship("PredictionModel", backref="predictions")

    def __repr__(self):
        return f"<PredictionResult(model_id={self.model_id}, predicted={self.predicted_value}, horizon={self.horizon_hours}h)>"