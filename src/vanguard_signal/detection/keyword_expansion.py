"""Keyword expansion and discovery service — automatically finds related terms and expands keyword coverage."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.models.trend import TrendKeyword, TrendTimeSeries
from vanguard_signal.schema.models.keyword_expansion import (
    KeywordRelationship,
    KeywordCluster,
    KeywordClusterMembership,
    KeywordExpansionCache
)
from vanguard_signal.config import settings

logger = logging.getLogger(__name__)


class KeywordExpansionService:
    """
    Service for discovering and expanding keyword coverage through semantic analysis,
    co-occurrence patterns, and trend correlation.
    """

    def __init__(self):
        self.min_cooccurrence_threshold = 0.3  # Minimum correlation for related terms
        self.max_suggestions_per_keyword = 10
        self.cache_expiry_hours = 24

    async def get_related_keywords(
        self,
        keyword: str,
        max_suggestions: int = 10,
        include_scores: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get related keywords for a given term using multiple discovery methods.

        Returns list of dicts with keys: keyword, score, method, category
        """
        # Check database cache first
        cache_key = f"{keyword}:{max_suggestions}"
        cached_result = await self._get_cached_suggestions(cache_key)
        if cached_result:
            return cached_result

        async with get_session() as session:
            try:
                suggestions = await self._discover_related_keywords(
                    session, keyword, max_suggestions
                )

                # Cache the result in database
                await self._cache_suggestions(cache_key, suggestions)

                # Store relationships in database (fire and forget)
                asyncio.create_task(
                    self.store_keyword_relationships(keyword, suggestions)
                )

                return suggestions

            except Exception as exc:
                logger.error(f"Failed to get related keywords for '{keyword}': {exc}")
                return []

    async def _discover_related_keywords(
        self,
        session: AsyncSession,
        keyword: str,
        max_suggestions: int
    ) -> List[Dict[str, Any]]:
        """Discover related keywords using multiple methods."""
        all_suggestions = []

        # Method 1: Co-occurrence analysis
        cooccurrence_suggestions = await self._find_cooccurring_keywords(
            session, keyword, max_suggestions // 3
        )
        all_suggestions.extend(cooccurrence_suggestions)

        # Method 2: Semantic similarity (placeholder for future ML implementation)
        semantic_suggestions = await self._find_semantic_similar_keywords(
            session, keyword, max_suggestions // 3
        )
        all_suggestions.extend(semantic_suggestions)

        # Method 3: Category-based expansion
        category_suggestions = await self._find_category_related_keywords(
            session, keyword, max_suggestions // 3
        )
        all_suggestions.extend(category_suggestions)

        # Method 4: Trend correlation
        correlation_suggestions = await self._find_correlated_trend_keywords(
            session, keyword, max_suggestions // 3
        )
        all_suggestions.extend(correlation_suggestions)

        # Remove duplicates and sort by score
        seen = set()
        unique_suggestions = []
        for suggestion in sorted(all_suggestions, key=lambda x: x["score"], reverse=True):
            if suggestion["keyword"] not in seen and suggestion["keyword"] != keyword:
                unique_suggestions.append(suggestion)
                seen.add(suggestion["keyword"])
                if len(unique_suggestions) >= max_suggestions:
                    break

        return unique_suggestions

    async def _find_cooccurring_keywords(
        self,
        session: AsyncSession,
        keyword: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find keywords that frequently appear in the same time periods."""
        try:
            # Get time periods where the target keyword trended
            target_periods = await session.execute(
                select(TrendTimeSeries.bucket_start, TrendTimeSeries.bucket_end)
                .join(TrendKeyword, TrendTimeSeries.keyword_id == TrendKeyword.id)
                .where(
                    TrendKeyword.keyword == keyword,
                    TrendTimeSeries.value > 0,  # Only periods with activity
                    TrendTimeSeries.bucket_start >= datetime.now(timezone.utc) - timedelta(days=90)
                )
                .distinct()
            )

            period_ranges = [(row.bucket_start, row.bucket_end) for row in target_periods]

            if not period_ranges:
                return []

            # Find other keywords that appeared in these same periods
            cooccurring = defaultdict(int)
            total_periods = len(period_ranges)

            for start_time, end_time in period_ranges:
                other_keywords = await session.execute(
                    select(TrendKeyword.keyword, func.count(TrendTimeSeries.id))
                    .join(TrendTimeSeries, TrendKeyword.id == TrendTimeSeries.keyword_id)
                    .where(
                        TrendTimeSeries.bucket_start == start_time,
                        TrendTimeSeries.bucket_end == end_time,
                        TrendKeyword.keyword != keyword,
                        TrendTimeSeries.value > 0
                    )
                    .group_by(TrendKeyword.keyword)
                )

                for row in other_keywords:
                    cooccurring[row.keyword] += 1

            # Calculate co-occurrence scores
            suggestions = []
            for other_keyword, count in cooccurring.items():
                score = count / total_periods  # Percentage of periods they co-occurred
                if score >= self.min_cooccurrence_threshold:
                    suggestions.append({
                        "keyword": other_keyword,
                        "score": score,
                        "method": "cooccurrence",
                        "category": "temporal"
                    })

            return sorted(suggestions, key=lambda x: x["score"], reverse=True)[:limit]

        except Exception as exc:
            logger.error(f"Co-occurrence analysis failed for '{keyword}': {exc}")
            return []

    async def _find_semantic_similar_keywords(
        self,
        session: AsyncSession,
        keyword: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find semantically similar keywords (placeholder for future ML implementation)."""
        # For now, use simple string similarity and common prefixes/suffixes
        try:
            # Get all keywords from recent trends
            recent_keywords = await session.execute(
                select(TrendKeyword.keyword)
                .join(TrendTimeSeries, TrendKeyword.id == TrendTimeSeries.keyword_id)
                .where(
                    TrendTimeSeries.bucket_start >= datetime.now(timezone.utc) - timedelta(days=30),
                    TrendTimeSeries.value > 0
                )
                .distinct()
            )

            keywords = [row.keyword for row in recent_keywords]
            suggestions = []

            target_lower = keyword.lower()
            target_words = set(target_lower.split())

            for candidate in keywords:
                if candidate == keyword:
                    continue

                candidate_lower = candidate.lower()
                candidate_words = set(candidate_lower.split())

                # Calculate word overlap
                overlap = len(target_words & candidate_words)
                if overlap > 0:
                    score = overlap / max(len(target_words), len(candidate_words))
                    if score > 0.3:  # At least 30% word overlap
                        suggestions.append({
                            "keyword": candidate,
                            "score": score,
                            "method": "semantic",
                            "category": "lexical"
                        })

            return sorted(suggestions, key=lambda x: x["score"], reverse=True)[:limit]

        except Exception as exc:
            logger.error(f"Semantic similarity analysis failed for '{keyword}': {exc}")
            return []

    async def _find_category_related_keywords(
        self,
        session: AsyncSession,
        keyword: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find keywords in the same category or with similar categories."""
        try:
            # Get the category of the target keyword
            target_category = await session.execute(
                select(TrendKeyword.category)
                .where(TrendKeyword.keyword == keyword)
                .limit(1)
            )

            target_row = target_category.first()
            if not target_row or not target_row.category:
                return []

            category = target_row.category

            # Find other keywords in the same category
            related_keywords = await session.execute(
                select(TrendKeyword.keyword, TrendKeyword.last_seen)
                .where(
                    TrendKeyword.category == category,
                    TrendKeyword.keyword != keyword,
                    TrendKeyword.last_seen >= datetime.now(timezone.utc) - timedelta(days=30)
                )
                .order_by(TrendKeyword.last_seen.desc())
                .limit(limit * 2)  # Get more to filter
            )

            suggestions = []
            for row in related_keywords:
                # Score based on recency (newer = higher score)
                days_since_seen = (datetime.now(timezone.utc) - row.last_seen).days
                recency_score = max(0, 1 - (days_since_seen / 30))  # Decay over 30 days

                suggestions.append({
                    "keyword": row.keyword,
                    "score": recency_score,
                    "method": "category",
                    "category": category
                })

            return sorted(suggestions, key=lambda x: x["score"], reverse=True)[:limit]

        except Exception as exc:
            logger.error(f"Category-based analysis failed for '{keyword}': {exc}")
            return []

    async def _find_correlated_trend_keywords(
        self,
        session: AsyncSession,
        keyword: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find keywords with correlated trend patterns."""
        try:
            # Get trend data for the target keyword
            target_trends = await session.execute(
                select(TrendTimeSeries.bucket_start, TrendTimeSeries.value)
                .join(TrendKeyword, TrendTimeSeries.keyword_id == TrendKeyword.id)
                .where(
                    TrendKeyword.keyword == keyword,
                    TrendTimeSeries.bucket_start >= datetime.now(timezone.utc) - timedelta(days=30)
                )
                .order_by(TrendTimeSeries.bucket_start)
            )

            target_data = {row.bucket_start: row.value for row in target_trends}
            if len(target_data) < 7:  # Need at least a week of data
                return []

            # Get other keywords with trend data in the same periods
            correlated_keywords = await session.execute(
                select(
                    TrendKeyword.keyword,
                    func.array_agg(TrendTimeSeries.value).label('values'),
                    func.array_agg(TrendTimeSeries.bucket_start).label('timestamps')
                )
                .join(TrendTimeSeries, TrendKeyword.id == TrendTimeSeries.keyword_id)
                .where(
                    TrendKeyword.keyword != keyword,
                    TrendTimeSeries.bucket_start.in_(target_data.keys())
                )
                .group_by(TrendKeyword.keyword)
                .having(func.count(TrendTimeSeries.id) >= 7)  # At least 7 data points
            )

            suggestions = []
            target_values = list(target_data.values())

            for row in correlated_keywords:
                if len(row.values) != len(target_values):
                    continue

                try:
                    # Calculate Pearson correlation coefficient
                    correlation = np.corrcoef(target_values, row.values)[0, 1]
                    if not np.isnan(correlation) and abs(correlation) > 0.5:  # Strong correlation
                        suggestions.append({
                            "keyword": row.keyword,
                            "score": abs(correlation),
                            "method": "correlation",
                            "category": "trend"
                        })
                except:
                    continue

            return sorted(suggestions, key=lambda x: x["score"], reverse=True)[:limit]

        except Exception as exc:
            logger.error(f"Trend correlation analysis failed for '{keyword}': {exc}")
            return []

    async def _get_cached_suggestions(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached suggestions from database."""
        async with get_session() as session:
            cache_entry = await session.execute(
                select(KeywordExpansionCache)
                .where(
                    KeywordExpansionCache.cache_key == cache_key,
                    KeywordExpansionCache.expires_at > datetime.now(timezone.utc)
                )
            )
            entry = cache_entry.scalar_one_or_none()
            if entry:
                try:
                    return json.loads(entry.suggestions)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cache for key {cache_key}")
                    # Clean up invalid cache entry
                    await session.execute(
                        delete(KeywordExpansionCache).where(KeywordExpansionCache.id == entry.id)
                    )
                    await session.commit()
            return None

    async def _cache_suggestions(self, cache_key: str, suggestions: List[Dict[str, Any]]) -> None:
        """Cache suggestions in database."""
        async with get_session() as session:
            try:
                # Remove existing cache entry
                await session.execute(
                    delete(KeywordExpansionCache).where(KeywordExpansionCache.cache_key == cache_key)
                )

                # Add new cache entry
                expires_at = datetime.now(timezone.utc) + timedelta(hours=self.cache_expiry_hours)
                cache_entry = KeywordExpansionCache(
                    cache_key=cache_key,
                    suggestions=json.dumps(suggestions),
                    expires_at=expires_at
                )
                session.add(cache_entry)
                await session.commit()
            except Exception as exc:
                logger.error(f"Failed to cache suggestions for key {cache_key}: {exc}")
                await session.rollback()

    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        """Check if cached result is still valid."""
        if "timestamp" not in cached_result:
            return False

        cache_age = datetime.now(timezone.utc) - cached_result["timestamp"]
        return cache_age < timedelta(hours=self.cache_expiry_hours)

    async def expand_watchlist_keywords(
        self,
        existing_keywords: List[str],
        expansion_factor: float = 0.5
    ) -> List[str]:
        """
        Expand a watchlist by suggesting related keywords.

        Args:
            existing_keywords: Current keywords in watchlist
            expansion_factor: How many suggestions per existing keyword (0.5 = half as many)

        Returns:
            List of suggested keywords to add
        """
        suggestions = set()

        for keyword in existing_keywords:
            related = await self.get_related_keywords(
                keyword,
                max_suggestions=int(expansion_factor * self.max_suggestions_per_keyword)
            )

            # Only add high-confidence suggestions
            for suggestion in related:
                if suggestion["score"] > 0.6:  # High confidence threshold
                    suggestions.add(suggestion["keyword"])

        # Remove any that are already in the watchlist
        suggestions -= set(existing_keywords)

        return list(suggestions)

    async def store_keyword_relationships(
        self,
        source_keyword: str,
        relationships: List[Dict[str, Any]],
        geo: str = "US"
    ) -> None:
        """
        Store discovered keyword relationships in the database.

        Args:
            source_keyword: The keyword that was analyzed
            relationships: List of relationship dictionaries from discovery methods
            geo: Geographic region for the relationships
        """
        async with get_session() as session:
            try:
                # Get source keyword ID
                source_result = await session.execute(
                    select(TrendKeyword.id).where(TrendKeyword.keyword == source_keyword)
                )
                source_id = source_result.scalar_one_or_none()
                if not source_id:
                    logger.warning(f"Source keyword '{source_keyword}' not found in database")
                    return

                for relationship in relationships:
                    target_keyword = relationship["keyword"]

                    # Get target keyword ID
                    target_result = await session.execute(
                        select(TrendKeyword.id).where(TrendKeyword.keyword == target_keyword)
                    )
                    target_id = target_result.scalar_one_or_none()
                    if not target_id:
                        logger.debug(f"Target keyword '{target_keyword}' not found, skipping relationship")
                        continue

                    # Check if relationship already exists
                    existing = await session.execute(
                        select(KeywordRelationship.id)
                        .where(
                            KeywordRelationship.source_keyword_id == source_id,
                            KeywordRelationship.target_keyword_id == target_id,
                            KeywordRelationship.relationship_type == relationship["method"]
                        )
                    )

                    if existing.scalar_one_or_none():
                        # Update existing relationship
                        await session.execute(
                            KeywordRelationship.__table__.update()
                            .where(
                                KeywordRelationship.source_keyword_id == source_id,
                                KeywordRelationship.target_keyword_id == target_id,
                                KeywordRelationship.relationship_type == relationship["method"]
                            )
                            .values(
                                confidence_score=relationship["score"],
                                last_updated=datetime.now(timezone.utc),
                                geo=geo
                            )
                        )
                    else:
                        # Create new relationship
                        relationship_data = {
                            "source_keyword_id": source_id,
                            "target_keyword_id": target_id,
                            "relationship_type": relationship["method"],
                            "confidence_score": relationship["score"],
                            "discovery_method": relationship["method"],
                            "geo": geo,
                            "last_updated": datetime.now(timezone.utc)
                        }

                        # Add method-specific data
                        if relationship["method"] == "cooccurrence":
                            relationship_data["cooccurrence_count"] = int(relationship["score"] * 10)
                        elif relationship["method"] == "correlation":
                            relationship_data["correlation_coefficient"] = relationship["score"]

                        new_relationship = KeywordRelationship(**relationship_data)
                        session.add(new_relationship)

                await session.commit()
                logger.debug(f"Stored {len(relationships)} relationships for keyword '{source_keyword}'")

            except Exception as exc:
                logger.error(f"Failed to store relationships for '{source_keyword}': {exc}")
                await session.rollback()

    async def get_keyword_clusters(
        self,
        keywords: List[str],
        min_cluster_size: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Group keywords into semantic clusters based on relationships.

        Returns list of clusters, each with: keywords, centroid_keyword, score
        """
        if len(keywords) < min_cluster_size:
            return []

        # Build relationship graph
        relationships = {}
        for keyword in keywords:
            related = await self.get_related_keywords(keyword, max_suggestions=20)
            relationships[keyword] = {s["keyword"]: s["score"] for s in related}

        # Simple clustering: group keywords that share many relationships
        clusters = []
        processed = set()

        for keyword in keywords:
            if keyword in processed:
                continue

            cluster = {keyword}
            cluster_score = 0

            # Find strongly connected keywords
            for other_keyword in keywords:
                if other_keyword == keyword or other_keyword in processed:
                    continue

                # Check bidirectional relationship strength
                score1 = relationships.get(keyword, {}).get(other_keyword, 0)
                score2 = relationships.get(other_keyword, {}).get(keyword, 0)
                avg_score = (score1 + score2) / 2

                if avg_score > 0.4:  # Strong relationship
                    cluster.add(other_keyword)
                    cluster_score += avg_score

            if len(cluster) >= min_cluster_size:
                clusters.append({
                    "keywords": list(cluster),
                    "centroid_keyword": keyword,
                    "score": cluster_score / len(cluster),
                    "size": len(cluster)
                })

                processed.update(cluster)

        return sorted(clusters, key=lambda x: x["score"], reverse=True)


# Global singleton
_keyword_expansion_service = None


def get_keyword_expansion_service():
    """Get the global keyword expansion service instance."""
    global _keyword_expansion_service
    if _keyword_expansion_service is None:
        _keyword_expansion_service = KeywordExpansionService()
    return _keyword_expansion_service
