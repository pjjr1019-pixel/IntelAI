"""
rl_feedback.py — Reinforcement Learning weight tuner.

Uses analyst feedback (confirm/dismiss verdicts) to automatically
adjust the ensemble detector weights over time.

Algorithm: Contextual Bandit with Thompson Sampling
  - Each detector (STL, IForest, CUSUM) has a Beta(α, β) distribution
  - CONFIRM verdicts increase α for detectors that fired
  - DISMISS verdicts increase β for detectors that fired
  - Weights are sampled from these distributions each cycle

This means the system learns which detectors are most reliable for
different entity types, WITHOUT needing labeled training data upfront.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.enums import FeedbackVerdict
from vanguard_signal.schema.models.alert import Alert, AnalystFeedback
from vanguard_signal.schema.models.signal import AnomalyResult

logger = logging.getLogger(__name__)

# Where to persist the learned priors
_PRIORS_PATH = Path(
    os.getenv("VS_RL_PRIORS_PATH", "data/rl_priors.json")
)

# Default prior: Beta(2, 2) — slightly informative, centered at 0.5
_DEFAULT_ALPHA = 2.0
_DEFAULT_BETA = 2.0

# Learning rate: how much each feedback updates the prior
_LEARNING_RATE = float(os.getenv("VS_RL_LEARNING_RATE", "1.0"))

# Minimum weight for any detector (prevents total suppression)
_MIN_WEIGHT = 0.05


@dataclass
class DetectorPrior:
    """Beta distribution parameters for one detector."""
    alpha: float = _DEFAULT_ALPHA
    beta: float = _DEFAULT_BETA

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        ab = self.alpha + self.beta
        return (self.alpha * self.beta) / (ab * ab * (ab + 1))

    def sample(self, rng: np.random.Generator | None = None) -> float:
        """Sample from Beta(α, β) — Thompson Sampling."""
        rng = rng or np.random.default_rng()
        return float(rng.beta(self.alpha, self.beta))

    def update_confirm(self, strength: float = 1.0) -> None:
        """Detector contributed to a TRUE POSITIVE → reward."""
        self.alpha += _LEARNING_RATE * strength

    def update_dismiss(self, strength: float = 1.0) -> None:
        """Detector contributed to a FALSE POSITIVE → penalize."""
        self.beta += _LEARNING_RATE * strength


@dataclass
class EnsemblePriors:
    """Priors for all four ensemble detectors."""
    stl: DetectorPrior = field(default_factory=DetectorPrior)
    iforest: DetectorPrior = field(default_factory=DetectorPrior)
    cusum: DetectorPrior = field(default_factory=DetectorPrior)
    velocity: DetectorPrior = field(default_factory=DetectorPrior)

    def sample_weights(self) -> dict[str, float]:
        """
        Sample weights from Thompson Sampling and normalize.
        Returns dict with keys: weight_stl, weight_iforest, weight_cusum, weight_velocity.
        """
        rng = np.random.default_rng()
        raw = {
            "stl": max(_MIN_WEIGHT, self.stl.sample(rng)),
            "iforest": max(_MIN_WEIGHT, self.iforest.sample(rng)),
            "cusum": max(_MIN_WEIGHT, self.cusum.sample(rng)),
            "velocity": max(_MIN_WEIGHT, self.velocity.sample(rng)),
        }
        total = sum(raw.values())
        return {
            "weight_stl": round(raw["stl"] / total, 4),
            "weight_iforest": round(raw["iforest"] / total, 4),
            "weight_cusum": round(raw["cusum"] / total, 4),
            "weight_velocity": round(raw["velocity"] / total, 4),
        }

    def mean_weights(self) -> dict[str, float]:
        """Deterministic weights using prior means (for backtesting)."""
        raw = {
            "stl": max(_MIN_WEIGHT, self.stl.mean),
            "iforest": max(_MIN_WEIGHT, self.iforest.mean),
            "cusum": max(_MIN_WEIGHT, self.cusum.mean),
            "velocity": max(_MIN_WEIGHT, self.velocity.mean),
        }
        total = sum(raw.values())
        return {
            "weight_stl": round(raw["stl"] / total, 4),
            "weight_iforest": round(raw["iforest"] / total, 4),
            "weight_cusum": round(raw["cusum"] / total, 4),
            "weight_velocity": round(raw["velocity"] / total, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "stl": {"alpha": self.stl.alpha, "beta": self.stl.beta},
            "iforest": {"alpha": self.iforest.alpha, "beta": self.iforest.beta},
            "cusum": {"alpha": self.cusum.alpha, "beta": self.cusum.beta},
            "velocity": {"alpha": self.velocity.alpha, "beta": self.velocity.beta},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnsemblePriors":
        return cls(
            stl=DetectorPrior(
                alpha=data.get("stl", {}).get("alpha", _DEFAULT_ALPHA),
                beta=data.get("stl", {}).get("beta", _DEFAULT_BETA),
            ),
            iforest=DetectorPrior(
                alpha=data.get("iforest", {}).get("alpha", _DEFAULT_ALPHA),
                beta=data.get("iforest", {}).get("beta", _DEFAULT_BETA),
            ),
            cusum=DetectorPrior(
                alpha=data.get("cusum", {}).get("alpha", _DEFAULT_ALPHA),
                beta=data.get("cusum", {}).get("beta", _DEFAULT_BETA),
            ),
            velocity=DetectorPrior(
                alpha=data.get("velocity", {}).get("alpha", _DEFAULT_ALPHA),
                beta=data.get("velocity", {}).get("beta", _DEFAULT_BETA),
            ),
        )


def load_priors() -> EnsemblePriors:
    """Load priors from disk. Returns defaults if file doesn't exist."""
    if _PRIORS_PATH.exists():
        try:
            data = json.loads(_PRIORS_PATH.read_text())
            priors = EnsemblePriors.from_dict(data)
            logger.info(
                "Loaded RL priors: STL=%.2f, IF=%.2f, CUSUM=%.2f (means)",
                priors.stl.mean, priors.iforest.mean, priors.cusum.mean,
            )
            return priors
        except Exception as exc:
            logger.warning("Failed to load RL priors: %s — using defaults", exc)

    return EnsemblePriors()


def save_priors(priors: EnsemblePriors) -> None:
    """Persist priors to disk."""
    _PRIORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PRIORS_PATH.write_text(json.dumps(priors.to_dict(), indent=2))
    logger.info("Saved RL priors to %s", _PRIORS_PATH)


def _detector_fired(anomaly: AnomalyResult, detector: str) -> bool:
    """Check if a detector contributed significantly to the anomaly."""
    if detector == "stl":
        return (anomaly.stl_residual_zscore or 0) > 2.0
    elif detector == "iforest":
        return (anomaly.iforest_score or 0) > 0.5
    elif detector == "cusum":
        return (anomaly.cusum_score or 0) > 0.5
    elif detector == "velocity":
        return (anomaly.velocity_score or 0) > 0.5
    return False


async def process_feedback(
    feedback: AnalystFeedback,
    session: AsyncSession,
) -> dict[str, Any]:
    """
    Process a single analyst verdict and update ensemble priors.

    Returns a summary of the weight adjustments made.
    """
    priors = load_priors()

    # Get the alert and its anomaly result
    alert = await session.get(Alert, feedback.alert_id)
    if not alert or not alert.anomaly_result_id:
        return {"status": "skipped", "reason": "no_anomaly_result"}

    anomaly = await session.get(AnomalyResult, alert.anomaly_result_id)
    if not anomaly:
        return {"status": "skipped", "reason": "anomaly_not_found"}

    # Confidence-weighted learning: analyst confidence scales the update
    strength = feedback.confidence if feedback.confidence else 0.5

    adjustments = {}

    if feedback.verdict == FeedbackVerdict.CONFIRM:
        # Reward detectors that fired
        for det in ["stl", "iforest", "cusum", "velocity"]:
            if _detector_fired(anomaly, det):
                getattr(priors, det).update_confirm(strength)
                adjustments[det] = f"+confirm({strength:.2f})"
    elif feedback.verdict == FeedbackVerdict.DISMISS:
        # Penalize detectors that fired (they produced a false positive)
        for det in ["stl", "iforest", "cusum", "velocity"]:
            if _detector_fired(anomaly, det):
                getattr(priors, det).update_dismiss(strength)
                adjustments[det] = f"+dismiss({strength:.2f})"

    # Persist updated priors
    save_priors(priors)

    # Mark feedback as used for training
    feedback.was_used_for_training = True
    await session.flush()

    new_weights = priors.mean_weights()

    logger.info(
        "RL update: verdict=%s alert=%s adjustments=%s → weights=%s",
        feedback.verdict.value, alert.id, adjustments, new_weights,
    )

    return {
        "status": "updated",
        "verdict": feedback.verdict.value,
        "adjustments": adjustments,
        "new_weights": new_weights,
        "priors": priors.to_dict(),
    }


async def process_all_pending_feedback(session: AsyncSession) -> dict[str, Any]:
    """
    Process all unprocessed feedback records.
    Called by the scheduler or manually.
    """
    stmt = (
        select(AnalystFeedback)
        .where(AnalystFeedback.was_used_for_training == False)
        .order_by(AnalystFeedback.created_at.asc())
    )
    result = await session.execute(stmt)
    pending = result.scalars().all()

    processed = 0
    skipped = 0

    for fb in pending:
        outcome = await process_feedback(fb, session)
        if outcome["status"] == "updated":
            processed += 1
        else:
            skipped += 1

    return {
        "total_pending": len(pending),
        "processed": processed,
        "skipped": skipped,
        "current_weights": load_priors().mean_weights(),
    }
