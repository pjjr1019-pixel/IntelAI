"""
stl_detector.py — Seasonal-Trend Decomposition using LOESS (STL).

PURPOSE:
    Strip away predictable seasonality and trend from a time series,
    leaving only the "residual."  A large residual Z-score means
    something genuinely unusual is happening — not just the normal
    weekly or monthly cycle.

HOW IT WORKS:
    1. STL splits the series into: Trend + Seasonal + Residual
    2. We compute the Z-score of the LATEST residual value
    3. If |Z| > threshold → anomaly flag

WHY IT MATTERS:
    Without STL, a normal Friday traffic spike on Wikipedia would
    look like an anomaly.  STL removes that noise so only TRUE
    deviations are flagged.

MINIMUM DATA:  Needs at least 2 full seasonal periods.  For daily
data with weekly seasonality that means ≥14 data points.
"""

from __future__ import annotations

import logging

import numpy as np
from statsmodels.tsa.seasonal import STL as _STL

from vanguard_signal.detection.base_detector import BaseDetector, DetectorResult

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────
_DEFAULT_PERIOD = 7          # weekly seasonality for daily data
_DEFAULT_ZSCORE_THRESHOLD = 3.0
_MIN_LENGTH_MULTIPLIER = 2   # need 2× period of data minimum


class STLDetector(BaseDetector):
    """
    Anomaly detector based on STL decomposition residual Z-scores.

    Parameters:
        period:    Seasonal period length (7 = weekly for daily data).
        threshold: Z-score threshold for flagging anomalies.
        robust:    Use robust fitting (downweight outliers in STL itself).
    """

    @property
    def name(self) -> str:
        return "stl"

    def __init__(
        self,
        period: int = _DEFAULT_PERIOD,
        threshold: float = _DEFAULT_ZSCORE_THRESHOLD,
        robust: bool = True,
    ) -> None:
        self._period = period
        self._threshold = threshold
        self._robust = robust
        self._min_length = period * _MIN_LENGTH_MULTIPLIER

    def detect(self, values: np.ndarray) -> DetectorResult:
        """
        Run STL decomposition and score the latest residual.

        If the series is too short for STL, falls back to a simple
        Z-score of the raw values (graceful degradation).
        """
        arr = self._validate_input(values, min_length=3)

        # ── Fallback: too short for seasonal decomposition ───────────────
        if len(arr) < self._min_length:
            logger.debug(
                "STL: only %d points (need %d) — using raw Z-score fallback",
                len(arr),
                self._min_length,
            )
            return self._fallback_zscore(arr)

        # ── Full STL decomposition ───────────────────────────────────────
        try:
            stl = _STL(
                arr,
                period=self._period,
                robust=self._robust,
            )
            result = stl.fit()

            trend = result.trend
            seasonal = result.seasonal
            residual = result.resid

            # Z-score of the residuals
            res_mean = np.nanmean(residual)
            res_std = np.nanstd(residual)
            if res_std < 1e-10:
                res_std = 1.0  # prevent division by zero for flat series

            zscores = (residual - res_mean) / res_std
            latest_z = float(zscores[-1])
            is_anomaly = abs(latest_z) > self._threshold

            return DetectorResult(
                name=self.name,
                score=latest_z,
                is_anomaly=is_anomaly,
                details={
                    "trend_latest": float(trend[-1]),
                    "seasonal_latest": float(seasonal[-1]),
                    "residual_latest": float(residual[-1]),
                    "residual_mean": float(res_mean),
                    "residual_std": float(res_std),
                    "zscore": latest_z,
                    "threshold": self._threshold,
                    "period": self._period,
                    "method": "stl_full",
                    "series_length": len(arr),
                },
                scores_all=zscores,
            )

        except Exception as exc:
            logger.warning("STL decomposition failed: %s — using fallback", exc)
            return self._fallback_zscore(arr)

    def _fallback_zscore(self, arr: np.ndarray) -> DetectorResult:
        """Simple Z-score when STL can't run (not enough data)."""
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-10:
            std = 1.0

        zscores = (arr - mean) / std
        latest_z = float(zscores[-1])

        return DetectorResult(
            name=self.name,
            score=latest_z,
            is_anomaly=abs(latest_z) > self._threshold,
            details={
                "trend_latest": None,
                "seasonal_latest": None,
                "residual_latest": float(arr[-1] - mean),
                "residual_mean": float(mean),
                "residual_std": float(std),
                "zscore": latest_z,
                "threshold": self._threshold,
                "period": self._period,
                "method": "zscore_fallback",
                "series_length": len(arr),
            },
            scores_all=zscores,
        )
