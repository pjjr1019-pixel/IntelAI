"""
velocity_detector.py — Rate-of-change anomaly detector.

PURPOSE:
    Detect sudden ACCELERATIONS in a time series — not just high values,
    but rapid increases in the *speed* of change.  This catches the
    critical "inflection point" where a trend transitions from linear
    growth to exponential growth, which often precedes major events.

HOW IT WORKS:
    1. First derivative (velocity):  v[i] = x[i] - x[i-1]
       Measures how fast the value is changing each period.

    2. Second derivative (acceleration):  a[i] = v[i] - v[i-1]
       Measures how fast the *velocity itself* is changing.
       A large positive acceleration means the series is curving upward.

    3. Scoring: Combine recent velocity magnitude and acceleration
       magnitude using Z-scores relative to each series' own history.
       The final score emphasises acceleration because it is the
       earliest signal of exponential takeoff.

    4. Lookback window: Only the last `window` points of the derivatives
       are used for scoring, so the detector adapts to recent baseline.

WHY IT MATTERS:
    Traditional detectors (STL, IForest, CUSUM) react to absolute levels
    or slow shifts.  The velocity detector fires *before* those detectors
    because it responds to the SHAPE of the curve, not its height.
    A search term going 10 → 12 → 16 → 24 → 40 per day may have a low
    absolute level, but its acceleration is explosive.

PARAMETERS:
    window:       Number of recent points for Z-score baseline (default 14).
    vel_weight:   Relative weight of velocity Z-score (default 0.3).
    acc_weight:   Relative weight of acceleration Z-score (default 0.7).
    threshold:    Combined Z-score above which an anomaly is flagged (default 2.5).
"""

from __future__ import annotations

import logging

import numpy as np

from vanguard_signal.detection.base_detector import BaseDetector, DetectorResult

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────
_DEFAULT_WINDOW = 14        # Rolling window for baseline stats
_DEFAULT_VEL_WEIGHT = 0.3   # Contribution of velocity to combined score
_DEFAULT_ACC_WEIGHT = 0.7   # Contribution of acceleration to combined score
_DEFAULT_THRESHOLD = 2.5    # Combined Z-score threshold


class VelocityDetector(BaseDetector):
    """
    First- and second-derivative detector for rate-of-change anomalies.

    Parameters:
        window:      Rolling window size for Z-score computation.
        vel_weight:  Relative weight of velocity Z-score in the combined score.
        acc_weight:  Relative weight of acceleration Z-score in the combined score.
        threshold:   Combined Z-score threshold for anomaly flagging.
    """

    @property
    def name(self) -> str:
        return "velocity"

    def __init__(
        self,
        window: int = _DEFAULT_WINDOW,
        vel_weight: float = _DEFAULT_VEL_WEIGHT,
        acc_weight: float = _DEFAULT_ACC_WEIGHT,
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        self._window = max(window, 5)  # minimum 5 for meaningful stats
        self._vel_weight = vel_weight
        self._acc_weight = acc_weight
        self._threshold = threshold

    def detect(self, values: np.ndarray) -> DetectorResult:
        """
        Compute velocity and acceleration, then score using Z-scores.

        Returns a DetectorResult with a 0–1 normalised score suitable
        for the ensemble, plus rich details for explainability.
        """
        arr = self._validate_input(values, min_length=5)

        # ── First derivative (velocity) ──────────────────────────────────
        velocity = np.diff(arr)  # length = n-1

        # ── Second derivative (acceleration) ─────────────────────────────
        acceleration = np.diff(velocity)  # length = n-2

        if len(acceleration) < 3:
            # Not enough data for meaningful acceleration analysis
            return DetectorResult(
                name=self.name,
                score=0.0,
                is_anomaly=False,
                details={
                    "method": "velocity_fallback",
                    "reason": "insufficient_data",
                    "series_length": len(arr),
                },
                scores_all=np.zeros(len(arr)),
            )

        # ── Z-score of latest velocity ───────────────────────────────────
        vel_window = velocity[-self._window:]
        vel_mu = np.mean(vel_window[:-1]) if len(vel_window) > 1 else 0.0
        vel_sigma = np.std(vel_window[:-1]) if len(vel_window) > 1 else 1.0
        if vel_sigma < 1e-10:
            vel_sigma = 1.0
        vel_latest = velocity[-1]
        vel_zscore = (vel_latest - vel_mu) / vel_sigma

        # ── Z-score of latest acceleration ───────────────────────────────
        acc_window = acceleration[-self._window:]
        acc_mu = np.mean(acc_window[:-1]) if len(acc_window) > 1 else 0.0
        acc_sigma = np.std(acc_window[:-1]) if len(acc_window) > 1 else 1.0
        if acc_sigma < 1e-10:
            acc_sigma = 1.0
        acc_latest = acceleration[-1]
        acc_zscore = (acc_latest - acc_mu) / acc_sigma

        # ── Combined score (weighted absolute Z-scores) ──────────────────
        total_weight = self._vel_weight + self._acc_weight
        combined_zscore = (
            self._vel_weight * abs(vel_zscore)
            + self._acc_weight * abs(acc_zscore)
        ) / total_weight

        # ── Normalise to 0–1 for ensemble ────────────────────────────────
        # Use threshold as the reference: score = min(combined / threshold, 1.0)
        normalized_score = float(min(combined_zscore / self._threshold, 1.0)) if self._threshold > 0 else 0.0

        is_anomaly = bool(combined_zscore > self._threshold)

        # ── Direction of acceleration ────────────────────────────────────
        if acc_latest > 0 and vel_latest > 0:
            direction = "accelerating_up"
        elif acc_latest > 0 and vel_latest <= 0:
            direction = "decelerating_down"
        elif acc_latest <= 0 and vel_latest > 0:
            direction = "decelerating_up"
        else:
            direction = "accelerating_down"

        # ── Per-point scores (for charts / audit) ────────────────────────
        # Compute rolling combined score for each acceleration point
        scores_all = np.zeros(len(arr))
        for i in range(len(acceleration)):
            # Use a sliding window ending at i for local Z-scores
            start = max(0, i - self._window + 1)
            v_slice = velocity[start:i + 1]
            a_slice = acceleration[start:i + 1]

            if len(v_slice) > 1:
                v_z = abs((velocity[min(i + 1, len(velocity) - 1)] - np.mean(v_slice)) / max(np.std(v_slice), 1e-10))
            else:
                v_z = 0.0
            if len(a_slice) > 1:
                a_z = abs((acceleration[i] - np.mean(a_slice)) / max(np.std(a_slice), 1e-10))
            else:
                a_z = 0.0

            raw = (self._vel_weight * v_z + self._acc_weight * a_z) / total_weight
            # Map to index in original array (acceleration starts at index 2)
            scores_all[i + 2] = min(raw / self._threshold, 1.0) if self._threshold > 0 else 0.0

        return DetectorResult(
            name=self.name,
            score=normalized_score,
            is_anomaly=is_anomaly,
            details={
                "velocity_latest": float(vel_latest),
                "velocity_zscore": float(vel_zscore),
                "velocity_mean": float(vel_mu),
                "velocity_std": float(vel_sigma),
                "acceleration_latest": float(acc_latest),
                "acceleration_zscore": float(acc_zscore),
                "acceleration_mean": float(acc_mu),
                "acceleration_std": float(acc_sigma),
                "combined_zscore": float(combined_zscore),
                "normalized_score": float(normalized_score),
                "direction": direction,
                "window": self._window,
                "vel_weight": self._vel_weight,
                "acc_weight": self._acc_weight,
                "threshold": self._threshold,
                "method": "velocity_acceleration",
                "series_length": len(arr),
            },
            scores_all=scores_all,
        )
