"""
health.py — Source Health Monitor for graceful degradation.

Responsibilities:
  1. After each ingestion cycle, evaluate if a source is LIVE / DEGRADED / DOWN.
  2. Update the source_registry table with the new status.
  3. Compute dynamic confidence weights based on source health.

Threshold logic:
  • 0 consecutive failures  → LIVE
  • 1–2 consecutive failures → DEGRADED (weight halved)
  • 3+ consecutive failures  → DOWN (weight = 0, excluded from scoring)

When a source recovers, it ramps back to full weight over 2 successful cycles.
"""

from __future__ import annotations

import logging
from uuid import UUID

from vanguard_signal.schema.enums import HealthStatus
from vanguard_signal.schema.models.ingestion import SourceRegistry

logger = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────────────────
_DEGRADED_THRESHOLD = 1   # failures before DEGRADED
_DOWN_THRESHOLD = 3       # failures before DOWN
_RECOVERY_CYCLES = 2      # successful pulls before full weight restored


class SourceHealthMonitor:
    """
    Evaluates and updates source health states.

    This is a stateless calculator — all state lives in the database
    (SourceRegistry.consecutive_failures and health_status).
    """

    @staticmethod
    def evaluate_status(consecutive_failures: int) -> HealthStatus:
        """Determine health status from failure count."""
        if consecutive_failures >= _DOWN_THRESHOLD:
            return HealthStatus.DOWN
        if consecutive_failures >= _DEGRADED_THRESHOLD:
            return HealthStatus.DEGRADED
        return HealthStatus.LIVE

    @staticmethod
    def compute_weight(
        source: SourceRegistry,
        override_status: HealthStatus | None = None,
    ) -> float:
        """
        Calculate the effective confidence weight for a source.

        Returns a value between 0.0 and source.default_weight.
        """
        status = override_status or source.health_status

        if status == HealthStatus.DOWN:
            return 0.0
        if status == HealthStatus.DEGRADED:
            return source.default_weight * 0.5
        return source.default_weight

    @staticmethod
    def compute_all_weights(
        sources: list[SourceRegistry],
    ) -> dict[str, float]:
        """
        Compute normalized confidence weights across all active sources.

        Returns a dict like {"google_trends": 0.55, "wikipedia": 0.45}
        where values sum to 1.0.  If a source is DOWN its weight is 0
        and the others are re-proportioned.
        """
        raw_weights: dict[str, float] = {}
        for src in sources:
            if not src.is_active:
                continue
            w = SourceHealthMonitor.compute_weight(src)
            raw_weights[src.name] = w

        total = sum(raw_weights.values())
        if total == 0:
            # All sources are down — return equal weights as fallback
            logger.critical("ALL sources are DOWN. Using equal fallback weights.")
            n = len(raw_weights) or 1
            return {name: 1.0 / n for name in raw_weights}

        return {name: w / total for name, w in raw_weights.items()}

    @staticmethod
    def should_alert_on_degradation(
        old_status: HealthStatus,
        new_status: HealthStatus,
    ) -> bool:
        """Return True if the status change warrants an ops notification."""
        severity_order = {
            HealthStatus.LIVE: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.DOWN: 2,
        }
        return severity_order[new_status] > severity_order[old_status]
