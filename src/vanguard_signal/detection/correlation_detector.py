"""
correlation_detector.py — Cross-keyword co-movement detection.

PURPOSE:
    Detect when MULTIPLE unrelated keywords suddenly start moving together.
    This is one of the strongest pre-event signals: before a bank run,
    searches for "bank safety", "FDIC insurance", "withdraw savings",
    and "gold price" all spike simultaneously — even though they come
    from different categories.

HOW IT WORKS:
    1. Collect recent time-series for all active entities.
    2. Compute pairwise Pearson correlation over a rolling window.
    3. Build a "correlation graph" — edges where |corr| > threshold.
    4. Detect correlation SPIKES: when current correlation is significantly
       higher than the historical baseline for that pair.
    5. Score based on how many cross-category edges are anomalously high,
       weighted by the magnitude of the correlation change.

OUTPUTS:
    CorrelationResult — per-cycle summary with:
      • List of anomalous pairs (entity_a, entity_b, corr, baseline_corr)
      • Overall "co-movement score" (0–1)
      • The largest cluster of co-moving keywords
      • Narrative summary for the alert system

WHY IT MATTERS:
    Individual keyword spikes may be noise.  But when 5+ unrelated keywords
    from different domains correlate in the same 48-hour window, the
    probability of a real event rises dramatically — because separate
    populations are independently reacting to the same underlying cause.

PARAMETERS:
    min_overlap:       Minimum shared data points for a pair (default 14).
    corr_threshold:    Minimum |correlation| to form an edge (default 0.7).
    baseline_window:   Historical window for baseline correlation (default 30).
    spike_zscore:      Z-score above baseline to flag as anomalous (default 2.0).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────
_DEFAULT_MIN_OVERLAP = 14
_DEFAULT_CORR_THRESHOLD = 0.7
_DEFAULT_BASELINE_WINDOW = 30
_DEFAULT_SPIKE_ZSCORE = 2.0
_DEFAULT_RECENT_WINDOW = 7


@dataclass(frozen=True)
class CorrelatedPair:
    """A single correlated pair of entities."""
    entity_a: str
    entity_b: str
    correlation: float
    baseline_correlation: float
    zscore: float

    @property
    def delta(self) -> float:
        """How much correlation increased over baseline."""
        return self.correlation - self.baseline_correlation


@dataclass(frozen=True)
class CorrelationCluster:
    """A connected component of co-moving entities."""
    entities: frozenset[str]
    mean_correlation: float
    max_correlation: float
    size: int

    @property
    def is_significant(self) -> bool:
        """Clusters of 3+ entities are considered significant."""
        return self.size >= 3


@dataclass(frozen=True)
class CorrelationResult:
    """
    Complete output of cross-keyword correlation analysis.

    This is NOT a DetectorResult because it operates across entities,
    not on a single time series.  It feeds directly into the pipeline
    as a supplementary signal.
    """
    # All anomalous pairs
    pairs: list[CorrelatedPair]
    # Connected clusters of co-moving entities
    clusters: list[CorrelationCluster]
    # Overall co-movement score (0–1)
    co_movement_score: float
    # Number of entity pairs analysed
    pairs_analysed: int
    # Summary
    summary: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to a serialisable dict for storage and WS broadcast."""
        return {
            "co_movement_score": round(self.co_movement_score, 4),
            "pairs_analysed": self.pairs_analysed,
            "anomalous_pairs": [
                {
                    "entity_a": p.entity_a,
                    "entity_b": p.entity_b,
                    "correlation": round(p.correlation, 4),
                    "baseline": round(p.baseline_correlation, 4),
                    "zscore": round(p.zscore, 2),
                }
                for p in self.pairs
            ],
            "clusters": [
                {
                    "entities": sorted(c.entities),
                    "mean_correlation": round(c.mean_correlation, 4),
                    "size": c.size,
                }
                for c in self.clusters
                if c.is_significant
            ],
            "summary": self.summary,
        }


class CrossCorrelationDetector:
    """
    Detects anomalous cross-keyword co-movement.

    Unlike BaseDetector subclasses, this operates on a DICT of entity
    series rather than a single 1-D array.

    Parameters:
        min_overlap:     Minimum shared data points for a valid pair.
        corr_threshold:  Minimum |correlation| to count as co-moving.
        baseline_window: Number of points for historical baseline.
        recent_window:   Number of recent points for current correlation.
        spike_zscore:    Z-score threshold for anomalous correlation increase.
    """

    def __init__(
        self,
        min_overlap: int = _DEFAULT_MIN_OVERLAP,
        corr_threshold: float = _DEFAULT_CORR_THRESHOLD,
        baseline_window: int = _DEFAULT_BASELINE_WINDOW,
        recent_window: int = _DEFAULT_RECENT_WINDOW,
        spike_zscore: float = _DEFAULT_SPIKE_ZSCORE,
    ) -> None:
        self._min_overlap = min_overlap
        self._corr_threshold = corr_threshold
        self._baseline_window = baseline_window
        self._recent_window = recent_window
        self._spike_zscore = spike_zscore

    def detect(
        self,
        entity_series: dict[str, np.ndarray],
    ) -> CorrelationResult:
        """
        Analyse cross-entity correlation.

        Args:
            entity_series: Dict mapping entity_value → 1-D value array
                           (oldest → newest, same time alignment).

        Returns:
            CorrelationResult with all anomalous pairs and clusters.
        """
        entities = list(entity_series.keys())
        n_entities = len(entities)

        if n_entities < 2:
            return CorrelationResult(
                pairs=[],
                clusters=[],
                co_movement_score=0.0,
                pairs_analysed=0,
                summary="Fewer than 2 entities — correlation analysis skipped.",
            )

        # ── Step 1: Compute pairwise correlations ────────────────────────
        anomalous_pairs: list[CorrelatedPair] = []
        pairs_analysed = 0

        for name_a, name_b in combinations(entities, 2):
            series_a = entity_series[name_a]
            series_b = entity_series[name_b]

            # Align to minimum length
            min_len = min(len(series_a), len(series_b))
            if min_len < self._min_overlap:
                continue

            # Trim both to same length (latest points aligned)
            a = series_a[-min_len:]
            b = series_b[-min_len:]
            pairs_analysed += 1

            # Recent correlation (last N points)
            recent_n = min(self._recent_window, min_len)
            recent_corr = self._pearson(a[-recent_n:], b[-recent_n:])

            # Baseline correlation (historical rolling)
            baseline_corr, baseline_std = self._rolling_baseline_corr(
                a, b, self._baseline_window, self._recent_window
            )

            # Z-score of current correlation vs baseline
            if baseline_std < 1e-10:
                zscore = 0.0 if abs(recent_corr - baseline_corr) < 0.1 else 3.0
            else:
                zscore = (recent_corr - baseline_corr) / baseline_std

            # Flag if correlation is both HIGH and ANOMALOUSLY HIGHER than baseline
            if abs(recent_corr) >= self._corr_threshold and zscore >= self._spike_zscore:
                anomalous_pairs.append(CorrelatedPair(
                    entity_a=name_a,
                    entity_b=name_b,
                    correlation=float(recent_corr),
                    baseline_correlation=float(baseline_corr),
                    zscore=float(zscore),
                ))

        # ── Step 2: Build clusters from anomalous pairs ──────────────────
        clusters = self._build_clusters(anomalous_pairs)

        # ── Step 3: Compute overall co-movement score ────────────────────
        if pairs_analysed == 0:
            co_movement_score = 0.0
        else:
            # Score = fraction of pairs that are anomalously correlated,
            # weighted by average correlation magnitude
            frac = len(anomalous_pairs) / pairs_analysed
            avg_corr = (
                np.mean([abs(p.correlation) for p in anomalous_pairs])
                if anomalous_pairs else 0.0
            )
            co_movement_score = min(frac * avg_corr * 5.0, 1.0)  # scale to 0-1

        # ── Step 4: Generate summary ─────────────────────────────────────
        summary = self._generate_summary(
            anomalous_pairs, clusters, co_movement_score, pairs_analysed
        )

        return CorrelationResult(
            pairs=anomalous_pairs,
            clusters=clusters,
            co_movement_score=co_movement_score,
            pairs_analysed=pairs_analysed,
            summary=summary,
        )

    @staticmethod
    def _pearson(a: np.ndarray, b: np.ndarray) -> float:
        """Compute Pearson correlation, returning 0 on degenerate input."""
        if len(a) < 2:
            return 0.0
        std_a, std_b = np.std(a), np.std(b)
        if std_a < 1e-10 or std_b < 1e-10:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])

    def _rolling_baseline_corr(
        self,
        a: np.ndarray,
        b: np.ndarray,
        baseline_window: int,
        recent_window: int,
    ) -> tuple[float, float]:
        """
        Compute rolling correlations over the baseline period, excluding
        the most recent window.  Returns (mean_corr, std_corr).
        """
        # Exclude the recent window from baseline
        n = len(a)
        if n <= recent_window + baseline_window:
            # Not enough history; baseline = correlation of everything minus recent
            hist_a = a[:-recent_window] if n > recent_window else a
            hist_b = b[:-recent_window] if n > recent_window else b
            base_corr = self._pearson(hist_a, hist_b)
            return base_corr, 0.15  # default uncertainty

        # Compute rolling correlations over baseline region
        end_idx = n - recent_window
        start_idx = max(0, end_idx - baseline_window * 3)
        window_size = min(baseline_window, end_idx - start_idx)
        if window_size < self._min_overlap:
            return 0.0, 0.15

        correlations = []
        for i in range(start_idx, end_idx - window_size + 1, max(1, window_size // 3)):
            seg_a = a[i:i + window_size]
            seg_b = b[i:i + window_size]
            correlations.append(self._pearson(seg_a, seg_b))

        if not correlations:
            return 0.0, 0.15

        return float(np.mean(correlations)), float(np.std(correlations))

    @staticmethod
    def _build_clusters(
        pairs: list[CorrelatedPair],
    ) -> list[CorrelationCluster]:
        """
        Build connected components from anomalous pairs using union-find.
        """
        if not pairs:
            return []

        # Union-Find
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent[x], parent[x])
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for p in pairs:
            parent.setdefault(p.entity_a, p.entity_a)
            parent.setdefault(p.entity_b, p.entity_b)
            union(p.entity_a, p.entity_b)

        # Group entities by root
        groups: dict[str, set[str]] = {}
        for entity in parent:
            root = find(entity)
            groups.setdefault(root, set()).add(entity)

        # Build CorrelationCluster for each group
        clusters = []
        for entities in groups.values():
            # Gather correlations for edges within this cluster
            cluster_corrs = [
                abs(p.correlation) for p in pairs
                if p.entity_a in entities and p.entity_b in entities
            ]
            clusters.append(CorrelationCluster(
                entities=frozenset(entities),
                mean_correlation=float(np.mean(cluster_corrs)) if cluster_corrs else 0.0,
                max_correlation=float(np.max(cluster_corrs)) if cluster_corrs else 0.0,
                size=len(entities),
            ))

        # Sort by size descending
        clusters.sort(key=lambda c: c.size, reverse=True)
        return clusters

    @staticmethod
    def _generate_summary(
        pairs: list[CorrelatedPair],
        clusters: list[CorrelationCluster],
        score: float,
        total_pairs: int,
    ) -> str:
        """Generate a human-readable summary of correlation findings."""
        if not pairs:
            return (
                f"No anomalous cross-keyword correlations detected "
                f"({total_pairs} pairs analysed)."
            )

        # Pick the strongest pair
        top = max(pairs, key=lambda p: abs(p.correlation))
        sig_clusters = [c for c in clusters if c.is_significant]

        parts = [
            f"Cross-keyword co-movement detected (score={score:.3f}): "
            f"{len(pairs)} anomalous pair(s) out of {total_pairs} analysed.",
        ]

        parts.append(
            f'Strongest pair: "{top.entity_a}" ↔ "{top.entity_b}" '
            f"(r={top.correlation:+.3f}, baseline={top.baseline_correlation:+.3f}, "
            f"Δ=+{top.delta:.3f})."
        )

        if sig_clusters:
            biggest = sig_clusters[0]
            entity_list = ", ".join(sorted(biggest.entities)[:5])
            parts.append(
                f"Largest co-moving cluster ({biggest.size} entities): "
                f"{entity_list}."
            )

        return " ".join(parts)
