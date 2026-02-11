"""
Narrative saturation models for detecting oversaturated news narratives.
"""

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from ..base import Base

class NarrativeCluster(Base):
    """Represents a cluster of semantically similar news articles forming a narrative."""

    __tablename__ = "narrative_clusters"

    id = Column(String(100), primary_key=True)  # e.g., "cluster_123"
    representative_title = Column(Text, nullable=False)
    source_distribution = Column(JSON, nullable=False)  # Dict[str, int] of source -> count
    average_tone = Column(Float, nullable=False, default=0.0)
    coverage_intensity = Column(Float, nullable=False)  # articles per hour
    time_span_hours = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to saturation scores
    saturation_scores = relationship("NarrativeSaturation", back_populates="cluster")

    def __init__(self, **kwargs):
        # Extract articles before calling super().__init__
        articles = kwargs.pop('articles', [])
        super().__init__(**kwargs)
        # Store articles as a runtime attribute
        self.articles = articles

class NarrativeClusterArticle(Base):
    """Junction table linking narrative clusters to news articles."""

    __tablename__ = "narrative_cluster_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(100), ForeignKey("narrative_clusters.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("ingestion.news_articles.id"), nullable=False)

    # Relationships
    # cluster = relationship("NarrativeCluster", backref="cluster_articles")
    # article = relationship("NewsArticle", backref="cluster_articles")

class NarrativeSaturation(Base):
    """Saturation analysis for narrative clusters."""

    __tablename__ = "narrative_saturation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(100), ForeignKey("narrative_clusters.id"), nullable=False)
    saturation_score = Column(Float, nullable=False)  # 0.0 to 1.0
    lifecycle_stage = Column(String(20), nullable=False)  # emerging, rising, peak, declining
    coverage_volume = Column(Integer, nullable=False)  # total articles in cluster
    source_concentration = Column(Float, nullable=False)  # 0.0 to 1.0 (echo chamber measure)
    repetition_score = Column(Float, nullable=False)  # semantic similarity within cluster
    temporal_distribution = Column(Float, nullable=False)  # burstiness measure
    is_saturated = Column(Boolean, nullable=False, default=False)
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to cluster
    cluster = relationship("NarrativeCluster", back_populates="saturation_scores")

class NarrativeAlert(Base):
    """Alerts generated based on narrative saturation detection."""

    __tablename__ = "narrative_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(100), ForeignKey("narrative_clusters.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # saturation_warning, echo_chamber, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    saturation_score = Column(Float, nullable=False)
    article_count = Column(Integer, nullable=False)
    source_count = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationship to cluster
    cluster = relationship("NarrativeCluster")

# Add relationship to NewsArticle model (if it exists)
# This would need to be added to the existing NewsArticle model:
# narrative_clusters = relationship("NarrativeClusterArticle", back_populates="article")