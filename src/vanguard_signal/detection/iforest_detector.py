"""
iforest_detector.py — Isolation Forest for point anomaly detection.

PURPOSE:
    Detect data points that are "easy to isolate" from the rest of
    the distribution.  Unlike STL, this doesn't care about seasonality —
    it purely asks "is this point UNUSUAL in the context of recent history?"

HOW IT WORKS:
    1. Build random decision trees on the recent time-series values
    2. Anomalies are points that require FEWER splits to isolate
    3. Score range: negative = more anomalous, near 0 = normal
    4. We normalize to 0–1 for the ensemble (1 = most anomalous)

WHY IT MATTERS:
    Catches isolated spikes that STL might miss if they happen to
    coincide with a seasonal component.  Also works well with very
    short series where STL can't decompose.
"""

from __future__ import annotations

import logging

import numpy as np
from sklearn.ensemble import IsolationForest

from vanguard_signal.detection.base_detector import BaseDetector, DetectorResult

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────
_DEFAULT_CONTAMINATION = 0.05   # expect 5% of points to be anomalous
_DEFAULT_N_ESTIMATORS = 100
_DEFAULT_THRESHOLD = 0.65       # normalized score above this = anomaly


class IsolationForestDetector(BaseDetector):
    """
    Isolation Forest anomaly detector.

    Parameters:
        contamination: Expected proportion of anomalies (0.01 – 0.5).
        n_estimators:  Number of trees in the forest.
        threshold:     Normalized score threshold for flagging (0–1).
        random_state:  For reproducibility.
    """

    @property
    def name(self) -> str:
        return "iforest"

    def __init__(
        self,
        contamination: float = _DEFAULT_CONTAMINATION,
        n_estimators: int = _DEFAULT_N_ESTIMATORS,
        threshold: float = _DEFAULT_THRESHOLD,
        random_state: int = 42,
    ) -> None:
        self._contamination = contamination
        self._n_estimators = n_estimators
        self._threshold = threshold
        self._random_state = random_state

    def detect(self, values: np.ndarray) -> DetectorResult:
        """
        Fit Isolation Forest on the series and score the latest point.

        The raw sklearn score_samples() returns negative values where
        more negative = more anomalous.  We normalize to 0–1 where
        1 = most anomalous for consistency with the ensemble.
        """
        arr = self._validate_input(values, min_length=5)

        # ── Feature engineering: use value + rolling stats ───────────────
        # This gives the forest context about the local neighborhood,
        # not just the raw value.
        features = self._build_features(arr)

        # ── Fit & Score ──────────────────────────────────────────────────
        model = IsolationForest(
            contamination=self._contamination,
            n_estimators=self._n_estimators,
            random_state=self._random_state,
            n_jobs=1,
        )
        model.fit(features)

        raw_scores = model.score_samples(features)  # negative = anomalous
        predictions = model.predict(features)        # -1 = anomaly, 1 = normal

        # ── Normalize to 0–1 (1 = most anomalous) ───────────────────────
        # sklearn scores are typically in [-0.5, 0.5] range
        # We map: most negative → 1.0, most positive → 0.0
        s_min = raw_scores.min()
        s_max = raw_scores.max()
        if abs(s_max - s_min) < 1e-10:
            norm_scores = np.zeros_like(raw_scores)
        else:
            norm_scores = (s_max - raw_scores) / (s_max - s_min)

        latest_score = float(norm_scores[-1])
        latest_raw = float(raw_scores[-1])
        is_anomaly = latest_score > self._threshold

        return DetectorResult(
            name=self.name,
            score=latest_score,
            is_anomaly=is_anomaly,
            details={
                "raw_score": latest_raw,
                "normalized_score": latest_score,
                "sklearn_prediction": int(predictions[-1]),
                "contamination": self._contamination,
                "n_estimators": self._n_estimators,
                "threshold": self._threshold,
                "method": "isolation_forest",
                "series_length": len(arr),
                "n_features": features.shape[1],
            },
            scores_all=norm_scores,
        )

    @staticmethod
    def _build_features(arr: np.ndarray) -> np.ndarray:
        """
        Create a feature matrix from the 1-D series.

        Features per point:
          1. Raw value
          2. Difference from previous point (velocity)
          3. Rolling mean (window=3)
          4. Rolling std  (window=3)
          5. Deviation from rolling mean

        This gives the Isolation Forest richer context than raw values alone.
        """
        n = len(arr)
        feats = np.zeros((n, 5))

        # 1. Raw value
        feats[:, 0] = arr

        # 2. First difference (velocity)
        feats[1:, 1] = np.diff(arr)
        feats[0, 1] = 0.0

        # 3–4. Rolling mean and std (window=3, padded at edges)
        window = min(3, n)
        for i in range(n):
            start = max(0, i - window + 1)
            segment = arr[start : i + 1]
            feats[i, 2] = np.mean(segment)
            feats[i, 3] = np.std(segment) if len(segment) > 1 else 0.0

        # 5. Deviation from rolling mean
        feats[:, 4] = arr - feats[:, 2]

        return feats
