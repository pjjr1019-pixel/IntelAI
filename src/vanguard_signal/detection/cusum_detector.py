"""
cusum_detector.py — Cumulative Sum Control Chart for mean-shift detection.

PURPOSE:
    Detect SMALL, SUSTAINED shifts in the mean of a low-volume data stream.
    This is critical for the "Quiet Before the Storm" pattern — where a
    niche topic's baseline slowly rises before an explosive event.

HOW IT WORKS:
    1. Compute the running mean of the series as the "target"
    2. Track cumulative positive and negative deviations from target
    3. Apply an allowable "drift" (slack) parameter — small noise is ignored
    4. When cumulative sum exceeds the threshold → mean shift detected

    The two-sided CUSUM tracks both UPWARD shifts (S_high) and
    DOWNWARD shifts (S_low) simultaneously.

WHY IT MATTERS:
    STL catches big spikes.  Isolation Forest catches weird points.
    CUSUM catches the slow, creeping rise that neither would flag —
    the exact pattern that precedes real-world crises.

PARAMETERS:
    drift (k):     Allowable deviation before accumulating.
                   Typically 0.5 × the shift you want to detect.
    threshold (h): Decision boundary for the cumulative sum.
                   Higher = fewer alerts, lower = more sensitive.
"""

from __future__ import annotations

import logging

import numpy as np

from vanguard_signal.detection.base_detector import BaseDetector, DetectorResult

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────
_DEFAULT_DRIFT = 0.5        # k: allowable slack (in σ units)
_DEFAULT_THRESHOLD = 4.0    # h: decision boundary (in σ units)


class CUSUMDetector(BaseDetector):
    """
    Two-sided CUSUM detector for sustained mean shifts.

    Parameters:
        drift:     Slack parameter k (in standard-deviation units).
        threshold: Decision boundary h (in standard-deviation units).
    """

    @property
    def name(self) -> str:
        return "cusum"

    def __init__(
        self,
        drift: float = _DEFAULT_DRIFT,
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        self._drift = drift
        self._threshold = threshold

    def detect(self, values: np.ndarray) -> DetectorResult:
        """
        Run two-sided CUSUM on the series.

        Returns the max of (S_high, |S_low|) at the latest point as
        the score.  Higher score = stronger evidence of a mean shift.
        """
        arr = self._validate_input(values, min_length=5)

        # ── Standardize: express values in σ units ───────────────────────
        mu = np.mean(arr)
        sigma = np.std(arr)
        if sigma < 1e-10:
            sigma = 1.0  # flat series; no anomaly possible

        z = (arr - mu) / sigma

        # ── Two-sided CUSUM ──────────────────────────────────────────────
        n = len(z)
        s_high = np.zeros(n)  # upper CUSUM: detects upward shifts
        s_low = np.zeros(n)   # lower CUSUM: detects downward shifts

        for i in range(1, n):
            s_high[i] = max(0.0, s_high[i - 1] + z[i] - self._drift)
            s_low[i] = max(0.0, s_low[i - 1] - z[i] - self._drift)

        # ── Score: max of the two CUSUM branches at the latest point ────
        latest_high = float(s_high[-1])
        latest_low = float(s_low[-1])
        latest_score = max(latest_high, latest_low)

        # Normalize to 0–1 for ensemble (score / threshold, capped at 1)
        normalized_score = min(latest_score / self._threshold, 1.0) if self._threshold > 0 else 0.0

        is_anomaly = latest_score > self._threshold
        shift_direction = "up" if latest_high >= latest_low else "down"

        # ── Full per-point scores (normalized) ───────────────────────────
        combined = np.maximum(s_high, s_low)
        norm_all = np.minimum(combined / self._threshold, 1.0) if self._threshold > 0 else np.zeros(n)

        return DetectorResult(
            name=self.name,
            score=normalized_score,
            is_anomaly=is_anomaly,
            details={
                "cusum_high": latest_high,
                "cusum_low": latest_low,
                "cusum_max": latest_score,
                "normalized_score": normalized_score,
                "shift_direction": shift_direction,
                "series_mean": float(mu),
                "series_std": float(sigma),
                "drift_k": self._drift,
                "threshold_h": self._threshold,
                "method": "two_sided_cusum",
                "series_length": len(arr),
            },
            scores_all=norm_all,
        )
