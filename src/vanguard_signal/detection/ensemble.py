"""
ensemble.py — Weighted combination of STL, Isolation Forest, CUSUM, and Velocity.

PURPOSE:
    No single detector catches everything.  The ensemble combines their
    strengths:
      • STL      → great at removing seasonality noise
      • IForest  → great at catching isolated weird points
      • CUSUM    → great at catching slow, creeping mean shifts
      • Velocity → great at catching sudden accelerations / inflection points

    The final ensemble_score = w_stl * norm(stl) + w_if * iforest
                             + w_cusum * cusum + w_vel * velocity

EXPLAINABILITY CONTRACT:
    Every score is stored DECOMPOSED in the AnomalyResult table.
    Auditors can verify:  ensemble = sum(weight_i × score_i).

WEIGHT ADAPTATION:
    Default weights are [0.30, 0.25, 0.25, 0.20].  Over time, the RL
    feedback loop adjusts these based on analyst Confirm/Dismiss verdicts.
    That logic lives in a separate module; this ensemble always accepts
    weights as parameters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from vanguard_signal.detection.base_detector import DetectorResult
from vanguard_signal.detection.stl_detector import STLDetector
from vanguard_signal.detection.iforest_detector import IsolationForestDetector
from vanguard_signal.detection.cusum_detector import CUSUMDetector
from vanguard_signal.detection.velocity_detector import VelocityDetector

logger = logging.getLogger(__name__)

# ── Default Weights & Threshold ──────────────────────────────────────────
_DEFAULT_WEIGHT_STL = 0.30
_DEFAULT_WEIGHT_IFOREST = 0.25
_DEFAULT_WEIGHT_CUSUM = 0.25
_DEFAULT_WEIGHT_VELOCITY = 0.20
_DEFAULT_ENSEMBLE_THRESHOLD = 0.6


@dataclass(frozen=True)
class EnsembleResult:
    """
    Complete output of the ensemble detector — contains everything
    needed to populate one AnomalyResult row.

    All sub-detector results are preserved for full explainability.
    """
    # Sub-detector outputs
    stl: DetectorResult
    iforest: DetectorResult
    cusum: DetectorResult
    velocity: DetectorResult

    # Ensemble calculation
    weight_stl: float
    weight_iforest: float
    weight_cusum: float
    weight_velocity: float
    ensemble_score: float
    ensemble_threshold: float
    is_anomaly: bool

    # Human-readable
    reason_code: str
    summary: str

    def to_anomaly_dict(self) -> dict[str, Any]:
        """
        Convert to a flat dict matching AnomalyResultCreate fields.
        This is the bridge between detection and storage.
        """
        stl_d = self.stl.details
        cusum_d = self.cusum.details
        vel_d = self.velocity.details
        return {
            # STL
            "stl_trend": stl_d.get("trend_latest"),
            "stl_seasonal": stl_d.get("seasonal_latest"),
            "stl_residual": stl_d.get("residual_latest"),
            "stl_residual_zscore": self.stl.score,
            # Isolation Forest
            "iforest_score": self.iforest.score,
            "iforest_contamination": self.iforest.details.get("contamination"),
            # CUSUM
            "cusum_score": self.cusum.score,
            "cusum_threshold": cusum_d.get("threshold_h"),
            "cusum_drift": cusum_d.get("drift_k"),
            # Velocity
            "velocity_score": self.velocity.score,
            "velocity_acceleration": vel_d.get("acceleration_latest"),
            # Ensemble
            "weight_stl": self.weight_stl,
            "weight_iforest": self.weight_iforest,
            "weight_cusum": self.weight_cusum,
            "weight_velocity": self.weight_velocity,
            "ensemble_score": self.ensemble_score,
            "is_anomaly": self.is_anomaly,
            "ensemble_threshold": self.ensemble_threshold,
        }


class EnsembleDetector:
    """
    Runs all four detectors and computes the weighted ensemble score.

    Parameters:
        weight_stl:           Weight for STL detector (default 0.30)
        weight_iforest:       Weight for Isolation Forest (default 0.25)
        weight_cusum:         Weight for CUSUM (default 0.25)
        weight_velocity:      Weight for Velocity (default 0.20)
        ensemble_threshold:   Score above this = anomaly flag (default 0.6)
        stl_period:           Seasonal period for STL (default 7)
        iforest_contamination: Expected anomaly ratio for IForest
        cusum_drift:          CUSUM drift parameter k
        cusum_threshold:      CUSUM decision boundary h
        velocity_window:      Rolling window for velocity Z-scores
        velocity_threshold:   Combined Z-score threshold for velocity
    """

    def __init__(
        self,
        weight_stl: float = _DEFAULT_WEIGHT_STL,
        weight_iforest: float = _DEFAULT_WEIGHT_IFOREST,
        weight_cusum: float = _DEFAULT_WEIGHT_CUSUM,
        weight_velocity: float = _DEFAULT_WEIGHT_VELOCITY,
        ensemble_threshold: float = _DEFAULT_ENSEMBLE_THRESHOLD,
        stl_period: int = 7,
        stl_zscore_threshold: float = 3.0,
        iforest_contamination: float = 0.05,
        iforest_threshold: float = 0.65,
        cusum_drift: float = 0.5,
        cusum_h: float = 4.0,
        velocity_window: int = 14,
        velocity_threshold: float = 2.5,
    ) -> None:
        # Normalize weights to sum to 1.0
        total = weight_stl + weight_iforest + weight_cusum + weight_velocity
        self._w_stl = weight_stl / total
        self._w_if = weight_iforest / total
        self._w_cusum = weight_cusum / total
        self._w_vel = weight_velocity / total
        self._threshold = ensemble_threshold

        # Instantiate sub-detectors
        self._stl = STLDetector(
            period=stl_period,
            threshold=stl_zscore_threshold,
        )
        self._iforest = IsolationForestDetector(
            contamination=iforest_contamination,
            threshold=iforest_threshold,
        )
        self._cusum = CUSUMDetector(
            drift=cusum_drift,
            threshold=cusum_h,
        )
        self._velocity = VelocityDetector(
            window=velocity_window,
            threshold=velocity_threshold,
        )

    def detect(self, values: np.ndarray, entity_name: str = "") -> EnsembleResult:
        """
        Run all four detectors and combine their scores.

        Args:
            values:      1-D array of time-series values (oldest → newest).
            entity_name: For logging / summary text generation.

        Returns:
            EnsembleResult with full decomposition.
        """
        arr = np.asarray(values, dtype=np.float64).ravel()

        # ── Run each detector ────────────────────────────────────────────
        stl_result = self._stl.detect(arr)
        iforest_result = self._iforest.detect(arr)
        cusum_result = self._cusum.detect(arr)
        velocity_result = self._velocity.detect(arr)

        # ── Normalize STL score to 0–1 range ────────────────────────────
        # STL score is a Z-score (can be negative or >1).
        # Normalize using: score = min(|z| / threshold, 1.0)
        stl_threshold = self._stl._threshold
        stl_normalized = min(abs(stl_result.score) / stl_threshold, 1.0) if stl_threshold > 0 else 0.0

        # IForest, CUSUM, and Velocity are already 0–1
        iforest_normalized = max(0.0, min(iforest_result.score, 1.0))
        cusum_normalized = max(0.0, min(cusum_result.score, 1.0))
        velocity_normalized = max(0.0, min(velocity_result.score, 1.0))

        # ── Weighted ensemble ────────────────────────────────────────────
        ensemble_score = (
            self._w_stl * stl_normalized
            + self._w_if * iforest_normalized
            + self._w_cusum * cusum_normalized
            + self._w_vel * velocity_normalized
        )
        ensemble_score = round(float(ensemble_score), 6)
        is_anomaly = bool(ensemble_score > self._threshold)

        # ── Determine reason code and summary ────────────────────────────
        reason_code, summary = self._generate_explanation(
            entity_name,
            stl_result,
            iforest_result,
            cusum_result,
            velocity_result,
            stl_normalized,
            iforest_normalized,
            cusum_normalized,
            velocity_normalized,
            ensemble_score,
        )

        if is_anomaly:
            logger.warning(
                "⚠ ANOMALY: %s | ensemble=%.3f [stl=%.3f if=%.3f cusum=%.3f vel=%.3f] | %s",
                entity_name,
                ensemble_score,
                stl_normalized,
                iforest_normalized,
                cusum_normalized,
                velocity_normalized,
                reason_code,
            )
        else:
            logger.debug(
                "  normal: %s | ensemble=%.3f",
                entity_name,
                ensemble_score,
            )

        return EnsembleResult(
            stl=stl_result,
            iforest=iforest_result,
            cusum=cusum_result,
            velocity=velocity_result,
            weight_stl=self._w_stl,
            weight_iforest=self._w_if,
            weight_cusum=self._w_cusum,
            weight_velocity=self._w_vel,
            ensemble_score=ensemble_score,
            ensemble_threshold=self._threshold,
            is_anomaly=is_anomaly,
            reason_code=reason_code,
            summary=summary,
        )

    def _generate_explanation(
        self,
        entity: str,
        stl: DetectorResult,
        iforest: DetectorResult,
        cusum: DetectorResult,
        velocity: DetectorResult,
        stl_norm: float,
        if_norm: float,
        cusum_norm: float,
        vel_norm: float,
        ensemble: float,
    ) -> tuple[str, str]:
        """
        Generate a machine-readable reason_code and a human-readable
        plain-English summary for the alert.
        """
        # Pick the dominant detector
        scores = {
            "STL_SPIKE": stl_norm,
            "IFOREST_OUTLIER": if_norm,
            "CUSUM_SHIFT": cusum_norm,
            "VELOCITY_ACCEL": vel_norm,
        }
        dominant = max(scores, key=scores.get)  # type: ignore[arg-type]

        # Build contributing detectors list
        contributors = []
        if stl.is_anomaly:
            direction = "spike" if stl.score > 0 else "drop"
            contributors.append(
                f"STL detected a {direction} (Z={stl.score:+.2f}, "
                f"{abs(stl.score):.1f}σ from normal)"
            )
        if iforest.is_anomaly:
            contributors.append(
                f"Isolation Forest flagged this as an outlier "
                f"(score={iforest.score:.3f})"
            )
        if cusum.is_anomaly:
            direction = cusum.details.get("shift_direction", "up")
            contributors.append(
                f"CUSUM detected a sustained {direction}ward mean shift "
                f"(score={cusum.score:.3f})"
            )
        if velocity.is_anomaly:
            vel_direction = velocity.details.get("direction", "accelerating_up")
            contributors.append(
                f"Velocity detector flagged rapid {vel_direction.replace('_', ' ')} "
                f"(score={velocity.score:.3f}, "
                f"accel={velocity.details.get('acceleration_latest', 0):.2f})"
            )

        if not contributors:
            contributors.append(
                "Multiple detectors show elevated but sub-threshold scores"
            )

        entity_str = f'"{entity}"' if entity else "this entity"
        summary = (
            f"Anomaly detected for {entity_str} with ensemble score "
            f"{ensemble:.3f} (threshold {self._threshold}). "
            + "; ".join(contributors)
            + "."
        )

        # Compound reason codes when multiple detectors fire
        firing = [code for code, s in scores.items() if s > 0.5]
        reason_code = "+".join(firing) if firing else dominant

        return reason_code, summary
