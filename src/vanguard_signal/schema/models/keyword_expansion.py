"""
Keyword expansion and relationship models.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from ..base import Base


class KeywordRelationship(Base):
    """
    Stores relationships between keywords discovered through various methods.
    Used for keyword expansion and semantic clustering.
    """
    __tablename__ = "keyword_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_keyword_id = Column(Integer, ForeignKey('trend_keywords.id'), nullable=False, index=True)
    target_keyword_id = Column(Integer, ForeignKey('trend_keywords.id'), nullable=False, index=True)

    # Relationship metadata
    relationship_type = Column(String(50), nullable=False, index=True)  # cooccurrence, semantic, category, correlation
    confidence_score = Column(Float, nullable=False)  # 0-1 confidence score
    discovery_method = Column(String(50), nullable=False)  # How this relationship was discovered

    # Context data
    geo = Column(String(5), nullable=False, index=True)  # Geographic context
    time_period_start = Column(DateTime(timezone=True), nullable=True)  # When relationship was observed
    time_period_end = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    cooccurrence_count = Column(Integer, nullable=True)  # How many times they appeared together
    correlation_coefficient = Column(Float, nullable=True)  # For correlation relationships
    shared_words = Column(Text, nullable=True)  # JSON array of shared words for semantic relationships

    # Timestamps
    first_discovered = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    source_keyword = relationship("TrendKeyword", foreign_keys=[source_keyword_id], backref="outgoing_relationships")
    target_keyword = relationship("TrendKeyword", foreign_keys=[target_keyword_id], backref="incoming_relationships")

    __table_args__ = (
        UniqueConstraint('source_keyword_id', 'target_keyword_id', 'relationship_type', name='unique_keyword_relationship'),
        Index('idx_keyword_relationships_type_score', 'relationship_type', 'confidence_score'),
        Index('idx_keyword_relationships_geo_type', 'geo', 'relationship_type'),
        Index('idx_keyword_relationships_updated', 'last_updated'),
    )


class KeywordClusterMembership(Base):
    """
    Many-to-many relationship between keywords and clusters.
    """
    __tablename__ = "keyword_cluster_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword_id = Column(Integer, ForeignKey('trend_keywords.id'), nullable=False, index=True)
    cluster_id = Column(Integer, ForeignKey('keyword_clusters.id'), nullable=False, index=True)

    # Membership metadata
    membership_strength = Column(Float, nullable=False, default=1.0)  # How strongly this keyword belongs to the cluster
    added_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    keyword = relationship("TrendKeyword", backref="cluster_memberships")
    cluster = relationship("KeywordCluster", backref="memberships")

    __table_args__ = (
        UniqueConstraint('keyword_id', 'cluster_id', name='unique_keyword_cluster_membership'),
        Index('idx_keyword_cluster_memberships_keyword', 'keyword_id'),
        Index('idx_keyword_cluster_memberships_cluster', 'cluster_id'),
    )


class KeywordCluster(Base):
    """
    Groups of semantically related keywords.
    Used for topic analysis and keyword organization.
    """
    __tablename__ = "keyword_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)  # Optional human-readable name
    centroid_keyword_id = Column(Integer, ForeignKey('trend_keywords.id'), nullable=False, index=True)

    # Cluster properties
    cluster_size = Column(Integer, nullable=False)
    cohesion_score = Column(Float, nullable=False)  # How tightly related the keywords are
    category = Column(String(100), nullable=True)  # Inferred category for the cluster

    # Metadata
    geo = Column(String(5), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Keywords in this cluster (many-to-many relationship through memberships)
    # keywords = relationship("TrendKeyword", secondary=lambda: KeywordClusterMembership.__table__, backref="clusters")

    __table_args__ = (
        Index('idx_keyword_clusters_geo_category', 'geo', 'category'),
        Index('idx_keyword_clusters_centroid', 'centroid_keyword_id'),
        Index('idx_keyword_clusters_updated', 'last_updated'),
    )


class KeywordExpansionCache(Base):
    """
    Caches keyword expansion results to improve performance.
    """
    __tablename__ = "keyword_expansion_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), nullable=False, unique=True, index=True)  # e.g., "keyword:max_suggestions"

    # Cached data
    suggestions = Column(Text, nullable=False)  # JSON array of suggestions
    cached_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_keyword_expansion_cache_expires', 'expires_at'),
    )