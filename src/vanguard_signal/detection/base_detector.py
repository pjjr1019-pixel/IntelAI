"""
base_detector.py — Abstract interface for anomaly detectors.

Every detector must:
  1. Accept a 1-D numpy array of time-series values
  2. Return a structured result dataclass with scores and metadata
  3. Be stateless — all parameters come in via __init__ or detect()

This keeps detectors testable in isolation and swappable in the ensemble.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DetectorResult:
    """
    Standard output from any single detector.

    Attributes:
        name:       Detector identifier (e.g. 'stl', 'iforest', 'cusum')
        score:      Primary anomaly score for the LATEST data point.
                    Higher = more anomalous (normalized 0–1 where possible).
        is_anomaly: Whether this detector alone considers it anomalous.
        details:    Detector-specific metadata (for audit / explainability).
        scores_all: Full per-point score array (same length as input series).
    """
    name: str
    score: float
    is_anomaly: bool
    details: dict[str, Any] = field(default_factory=dict)
    scores_all: np.ndarray | None = None

    def __repr__(self) -> str:
        flag = "⚠ ANOMALY" if self.is_anomaly else "  normal"
        return f"[{self.name}] {flag}  score={self.score:.4f}"


class BaseDetector(ABC):
    """Interface that STL, Isolation Forest, and CUSUM all implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for logging and storage."""
        ...

    @abstractmethod
    def detect(self, values: np.ndarray) -> DetectorResult:
        """
        Run anomaly detection on a 1-D time-series array.

        Args:
            values: Ordered numeric observations (oldest → newest).
                    The LAST element is the point being evaluated.

        Returns:
            DetectorResult with the score for the latest point.
        """
        ...

    @staticmethod
    def _validate_input(values: np.ndarray, min_length: int = 3) -> np.ndarray:
        """Ensure input is a clean 1-D float array with enough data."""
        arr = np.asarray(values, dtype=np.float64).ravel()
        if len(arr) < min_length:
            raise ValueError(
                f"Need at least {min_length} data points, got {len(arr)}"
            )
        # Replace NaN / inf with forward-fill then backfill
        mask = ~np.isfinite(arr)
        if mask.any():
            for i in range(1, len(arr)):
                if mask[i]:
                    arr[i] = arr[i - 1]
            # backfill any leading NaNs
            for i in range(len(arr) - 2, -1, -1):
                if mask[i]:
                    arr[i] = arr[i + 1]
        return arr
