"""
Narrative Saturation Detector

Detects when news narratives become oversaturated by analyzing:
- Topic clustering using BERT-based semantic similarity
- Coverage volume and repetition patterns
- Narrative lifecycle tracking (emergence → peak → decline)
- Saturation scoring and echo chamber detection
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any, Union
import logging
from collections import defaultdict, Counter
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import re

from sentence_transformers import SentenceTransformer
from ..schema.models import NewsArticle, NarrativeCluster, NarrativeSaturation

logger = logging.getLogger(__name__)

class NarrativeSaturationDetector:
    """
    Detects narrative saturation through topic clustering and coverage analysis.
    """

    def __init__(self):
        # Initialize BERT model for semantic similarity
        try:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded BERT model for narrative clustering")
        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")
            self.encoder = None

        # Clustering parameters
        self.eps = 0.3  # DBSCAN epsilon for semantic similarity
        self.min_samples = 3  # Minimum articles per cluster
        self.saturation_threshold = 0.7  # Saturation score threshold

    def detect_narratives(self, articles: List[Any], time_window_hours: int = 24) -> List[NarrativeCluster]:
        """
        Cluster articles into narrative groups using semantic similarity.

        Args:
            articles: List of news articles
            time_window_hours: Time window for analysis

        Returns:
            List of narrative clusters
        """
        if not articles or not self.encoder:
            return []

        # Filter articles by time window
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_articles = [a for a in articles if a.published_at >= cutoff_time]

        if len(recent_articles) < self.min_samples:
            return []

        try:
            # Extract titles and content for clustering
            texts = []
            for article in recent_articles:
                # Combine title and summary for better semantic representation
                text = f"{article.title} {getattr(article, 'summary', '')}"
                texts.append(text)

            # Generate embeddings
            embeddings = self.encoder.encode(texts, show_progress_bar=False)

            # Perform clustering
            clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric='cosine')
            cluster_labels = clustering.fit_predict(embeddings)

            # Group articles by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                if label != -1:  # -1 indicates noise/outlier
                    clusters[label].append(recent_articles[i])

            # Convert to NarrativeCluster objects
            narrative_clusters = []
            for cluster_id, cluster_articles in clusters.items():
                if len(cluster_articles) >= self.min_samples:
                    cluster = self._create_narrative_cluster(cluster_id, cluster_articles)
                    narrative_clusters.append(cluster)

            logger.info(f"Detected {len(narrative_clusters)} narrative clusters from {len(recent_articles)} articles")
            return narrative_clusters

        except Exception as e:
            logger.error(f"Error in narrative detection: {e}")
            return []

    def _create_narrative_cluster(self, cluster_id: int, articles: List[Any]) -> NarrativeCluster:
        """Create a narrative cluster from grouped articles."""
        # Find representative title (most central article)
        titles = [a.title for a in articles]
        title_embeddings = self.encoder.encode(titles, show_progress_bar=False)

        # Calculate centroid
        centroid = np.mean(title_embeddings, axis=0)

        # Find article closest to centroid
        distances = cosine_similarity([centroid], title_embeddings)[0]
        representative_idx = np.argmax(distances)
        representative_article = articles[representative_idx]

        # Calculate cluster statistics
        sources = Counter(a.source for a in articles)
        tones = [a.tone for a in articles if a.tone is not None]
        avg_tone = np.mean(tones) if tones else 0.0

        # Calculate temporal distribution
        timestamps = [a.published_at for a in articles]
        time_span = max(timestamps) - min(timestamps)
        hours_span = time_span.total_seconds() / 3600

        # Calculate coverage intensity (articles per hour)
        coverage_intensity = len(articles) / max(hours_span, 1)

        return NarrativeCluster(
            id=f"cluster_{cluster_id}",
            representative_title=representative_article.title,
            articles=articles,
            source_distribution=dict(sources),
            average_tone=avg_tone,
            coverage_intensity=coverage_intensity,
            time_span_hours=hours_span,
            created_at=datetime.utcnow()
        )

    def calculate_saturation_scores(self, clusters: List[NarrativeCluster]) -> List[NarrativeSaturation]:
        """
        Calculate saturation scores for narrative clusters.

        Saturation factors:
        - Coverage volume (articles per hour)
        - Source diversity (concentration in few sources)
        - Repetition score (semantic similarity within cluster)
        - Temporal distribution (burst vs sustained coverage)
        """
        saturation_scores = []

        for cluster in clusters:
            try:
                saturation_score = self._calculate_cluster_saturation(cluster)
                lifecycle_stage = self._determine_lifecycle_stage(cluster)

                saturation = NarrativeSaturation(
                    cluster_id=cluster.id,
                    saturation_score=saturation_score,
                    lifecycle_stage=lifecycle_stage,
                    coverage_volume=len(cluster.articles),
                    source_concentration=self._calculate_source_concentration(cluster),
                    repetition_score=self._calculate_repetition_score(cluster),
                    temporal_distribution=self._analyze_temporal_distribution(cluster),
                    is_saturated=saturation_score >= self.saturation_threshold,
                    calculated_at=datetime.utcnow()
                )

                saturation_scores.append(saturation)

            except Exception as e:
                logger.error(f"Error calculating saturation for cluster {cluster.id}: {e}")
                continue

        return saturation_scores

    def _calculate_cluster_saturation(self, cluster: NarrativeCluster) -> float:
        """Calculate overall saturation score for a cluster."""
        # Weight different saturation factors
        weights = {
            'coverage_volume': 0.3,
            'source_concentration': 0.25,
            'repetition': 0.25,
            'temporal_burst': 0.2
        }

        # Coverage volume score (normalized)
        coverage_score = min(cluster.coverage_intensity / 10.0, 1.0)  # Cap at 10 articles/hour

        # Source concentration score
        source_concentration = self._calculate_source_concentration(cluster)

        # Repetition score
        repetition_score = self._calculate_repetition_score(cluster)

        # Temporal burst score
        temporal_score = self._analyze_temporal_distribution(cluster)

        # Combine scores
        saturation_score = (
            weights['coverage_volume'] * coverage_score +
            weights['source_concentration'] * source_concentration +
            weights['repetition'] * repetition_score +
            weights['temporal_burst'] * temporal_score
        )

        return min(saturation_score, 1.0)  # Cap at 1.0

    def _calculate_source_concentration(self, cluster: NarrativeCluster) -> float:
        """Calculate how concentrated coverage is in few sources (echo chamber effect)."""
        if not cluster.source_distribution:
            return 0.0

        total_articles = sum(cluster.source_distribution.values())
        if total_articles == 0:
            return 0.0

        # Calculate Herfindahl-Hirschman Index for source concentration
        hhi = sum((count / total_articles) ** 2 for count in cluster.source_distribution.values())

        # Normalize: HHI ranges from 1/n to 1, we want 0-1 scale where 1 = most concentrated
        max_hhi = 1.0
        min_hhi = 1.0 / len(cluster.source_distribution)
        normalized_hhi = (hhi - min_hhi) / (max_hhi - min_hhi)

        return max(0.0, min(1.0, normalized_hhi))

    def _calculate_repetition_score(self, cluster: NarrativeCluster) -> float:
        """Calculate semantic repetition within the cluster."""
        if len(cluster.articles) < 2:
            return 0.0

        try:
            # Get embeddings for all articles in cluster
            texts = [f"{a.title} {getattr(a, 'summary', '')}" for a in cluster.articles]
            embeddings = self.encoder.encode(texts, show_progress_bar=False)

            # Calculate average pairwise similarity
            similarities = cosine_similarity(embeddings)
            # Remove self-similarities
            np.fill_diagonal(similarities, 0)

            # Average similarity score
            avg_similarity = np.mean(similarities)

            return min(avg_similarity, 1.0)

        except Exception as e:
            logger.error(f"Error calculating repetition score: {e}")
            return 0.0

    def _analyze_temporal_distribution(self, cluster: NarrativeCluster) -> float:
        """Analyze if coverage is bursty vs sustained (higher score = more bursty)."""
        if len(cluster.articles) < 3:
            return 0.0

        # Sort timestamps
        timestamps = sorted([a.published_at for a in cluster.articles])

        # Calculate time intervals between articles
        intervals = []
        for i in range(1, len(timestamps)):
            interval_hours = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
            intervals.append(interval_hours)

        if not intervals:
            return 0.0

        # Calculate coefficient of variation (burstiness measure)
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)

        if mean_interval == 0:
            return 1.0  # All articles at same time = maximum burstiness

        cv = std_interval / mean_interval  # Coefficient of variation

        # Normalize CV to 0-1 scale (higher CV = more bursty)
        # Typical CV values: 0.5-2.0, normalize to 0-1
        normalized_burstiness = min(cv / 2.0, 1.0)

        return normalized_burstiness

    def _determine_lifecycle_stage(self, cluster: NarrativeCluster) -> str:
        """Determine the lifecycle stage of the narrative."""
        hours_old = cluster.time_span_hours

        if hours_old < 2:
            return "emerging"
        elif hours_old < 12:
            return "rising"
        elif hours_old < 48:
            return "peak"
        else:
            return "declining"

    def get_saturated_narratives(self, articles: List[Any],
                                time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get narratives that are currently saturated/overhyped.

        Returns:
            List of saturated narratives with metadata
        """
        # Detect narrative clusters
        clusters = self.detect_narratives(articles, time_window_hours)

        # Calculate saturation scores
        saturation_scores = self.calculate_saturation_scores(clusters)

        # Filter to saturated narratives
        saturated = [s for s in saturation_scores if s.is_saturated]

        # Enrich with cluster data
        results = []
        for saturation in saturated:
            cluster = next((c for c in clusters if c.id == saturation.cluster_id), None)
            if cluster:
                result = {
                    'narrative_id': saturation.cluster_id,
                    'title': cluster.representative_title,
                    'saturation_score': saturation.saturation_score,
                    'lifecycle_stage': saturation.lifecycle_stage,
                    'article_count': saturation.coverage_volume,
                    'source_count': len(cluster.source_distribution),
                    'time_span_hours': cluster.time_span_hours,
                    'average_tone': cluster.average_tone,
                    'coverage_intensity': cluster.coverage_intensity,
                    'source_concentration': saturation.source_concentration,
                    'repetition_score': saturation.repetition_score,
                    'temporal_burstiness': saturation.temporal_distribution,
                    'articles': [
                        {
                            'title': a.title,
                            'source': a.source,
                            'published_at': a.published_at.isoformat(),
                            'tone': a.tone,
                            'url': a.url
                        }
                        for a in cluster.articles[:5]  # Top 5 articles
                    ]
                }
                results.append(result)

        # Sort by saturation score (highest first)
        results.sort(key=lambda x: x['saturation_score'], reverse=True)

        logger.info(f"Found {len(results)} saturated narratives")
        return results