"""Alert escalation service — automatically increases alert severity based on rules."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.database import get_async_session
from vanguard_signal.schema.models.alert import Alert, AlertEscalation
from vanguard_signal.schema.enums import Severity

logger = logging.getLogger(__name__)


class AlertEscalationService:
    """
    Handles automatic alert escalation based on configurable rules.

    Escalation triggers:
    - Time-based: Low → Medium after X hours, Medium → High after Y hours
    - Score-based: Severity increases when anomaly score exceeds thresholds
    - Frequency-based: Severity increases with repeated similar alerts
    """

    def __init__(self) -> None:
        # Default escalation rules (configurable via env/config later)
        self.time_thresholds = {
            Severity.LOW: timedelta(hours=2),      # Low → Medium after 2 hours
            Severity.MEDIUM: timedelta(hours=6),   # Medium → High after 6 hours
            Severity.HIGH: timedelta(hours=24),    # High → Critical after 24 hours
        }

        self.score_thresholds = {
            Severity.LOW: 0.3,      # Score > 0.3 → Low
            Severity.MEDIUM: 0.6,   # Score > 0.6 → Medium
            Severity.HIGH: 0.8,     # Score > 0.8 → High
            Severity.CRITICAL: 0.95 # Score > 0.95 → Critical
        }

    async def check_and_escalate_alerts(self) -> int:
        """
        Check all active alerts for escalation opportunities.
        Returns the number of alerts that were escalated.
        """
        async with get_async_session() as session:
            escalated_count = 0

            # Check time-based escalations
            time_escalated = await self._check_time_based_escalations(session)
            escalated_count += time_escalated

            # Check score-based escalations
            score_escalated = await self._check_score_based_escalations(session)
            escalated_count += score_escalated

            # Check frequency-based escalations
            freq_escalated = await self._check_frequency_based_escalations(session)
            escalated_count += freq_escalated

            if escalated_count > 0:
                await session.commit()
                logger.info(f"Escalated {escalated_count} alerts")

            return escalated_count

    async def _check_time_based_escalations(self, session: AsyncSession) -> int:
        """Escalate alerts based on how long they've been active."""
        escalated_count = 0
        now = datetime.utcnow()

        for current_severity, time_threshold in self.time_thresholds.items():
            # Find alerts that have been at this severity level for too long
            cutoff_time = now - time_threshold

            stmt = select(Alert).where(
                Alert.status == "active",
                Alert.severity == current_severity,
                Alert.created_at < cutoff_time
            )

            result = await session.execute(stmt)
            alerts_to_escalate = result.scalars().all()

            for alert in alerts_to_escalate:
                next_severity = self._get_next_severity(current_severity)
                if next_severity:
                    await self._escalate_alert(
                        session, alert, next_severity, "time_based",
                        f"Alert escalated due to {time_threshold} timeout",
                        {"time_threshold_hours": time_threshold.total_seconds() / 3600}
                    )
                    escalated_count += 1

        return escalated_count

    async def _check_score_based_escalations(self, session: AsyncSession) -> int:
        """Escalate alerts based on anomaly score increases."""
        escalated_count = 0

        # Find alerts where current score exceeds threshold for higher severity
        stmt = select(Alert).where(Alert.status == "active")
        result = await session.execute(stmt)
        alerts = result.scalars().all()

        for alert in alerts:
            current_score = alert.ensemble_anomaly_score
            current_severity = alert.severity

            # Check if score warrants higher severity
            for severity, threshold in self.score_thresholds.items():
                if current_score > threshold and severity > current_severity:
                    await self._escalate_alert(
                        session, alert, severity, "score_increase",
                        f"Anomaly score {current_score:.3f} exceeds threshold {threshold} for {severity.value}",
                        {"score": current_score, "threshold": threshold}
                    )
                    escalated_count += 1
                    break  # Only escalate to the highest warranted severity

        return escalated_count

    async def _check_frequency_based_escalations(self, session: AsyncSession) -> int:
        """Escalate alerts based on frequency of similar alerts."""
        escalated_count = 0
        now = datetime.utcnow()
        window = timedelta(hours=24)  # Look at last 24 hours

        # Group alerts by primary entity and count occurrences
        stmt = select(Alert.primary_entity, Alert.severity).where(
            Alert.status == "active",
            Alert.created_at > (now - window)
        )

        result = await session.execute(stmt)
        entity_counts = {}
        for primary_entity, severity in result:
            if primary_entity not in entity_counts:
                entity_counts[primary_entity] = {"count": 0, "severities": set()}
            entity_counts[primary_entity]["count"] += 1
            entity_counts[primary_entity]["severities"].add(severity)

        # Escalate if we have 3+ alerts for the same entity in 24 hours
        for entity, data in entity_counts.items():
            if data["count"] >= 3:
                # Find the most severe alert for this entity
                stmt = select(Alert).where(
                    Alert.primary_entity == entity,
                    Alert.status == "active",
                    Alert.created_at > (now - window)
                ).order_by(Alert.severity.desc())

                result = await session.execute(stmt)
                most_severe_alert = result.scalars().first()

                if most_severe_alert:
                    next_severity = self._get_next_severity(most_severe_alert.severity)
                    if next_severity:
                        await self._escalate_alert(
                            session, most_severe_alert, next_severity, "repeated",
                            f"Escalated due to {data['count']} similar alerts in 24 hours",
                            {"similar_alerts_count": data["count"], "time_window_hours": 24}
                        )
                        escalated_count += 1

        return escalated_count

    async def _escalate_alert(
        self,
        session: AsyncSession,
        alert: Alert,
        new_severity: Severity,
        trigger: str,
        reason: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Perform the actual escalation of an alert."""
        old_severity = alert.severity

        # Update alert severity
        alert.severity = new_severity
        alert.updated_at = datetime.utcnow()

        # Create escalation record
        escalation = AlertEscalation(
            alert_id=alert.id,
            previous_severity=old_severity.value,
            new_severity=new_severity.value,
            escalation_reason=reason,
            escalation_trigger=trigger,
            escalation_metadata=metadata,
            escalated_at=datetime.utcnow()
        )

        session.add(escalation)

        logger.warning(
            f"ALERT ESCALATED: {alert.primary_entity} | {old_severity.value} → {new_severity.value} | Trigger: {trigger}"
        )

        # Record escalation analytics
        try:
            from vanguard_signal.detection.analytics import get_analytics_service
            analytics_service = get_analytics_service()
            await analytics_service.record_alert_escalation(alert)
        except Exception as analytics_exc:
            logger.debug("Escalation analytics recording failed: %s", analytics_exc)

    def _get_next_severity(self, current_severity: Severity) -> Severity | None:
        """Get the next higher severity level."""
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        try:
            current_index = severity_order.index(current_severity)
            if current_index < len(severity_order) - 1:
                return severity_order[current_index + 1]
        except ValueError:
            pass
        return None


# Global service instance
_escalation_service: AlertEscalationService | None = None


def get_escalation_service() -> AlertEscalationService:
    """Get the global alert escalation service instance."""
    global _escalation_service
    if _escalation_service is None:
        _escalation_service = AlertEscalationService()
    return _escalation_service


async def run_escalation_check() -> int:
    """Convenience function to run escalation checks. Returns number of escalated alerts."""
    service = get_escalation_service()
    return await service.check_and_escalate_alerts()