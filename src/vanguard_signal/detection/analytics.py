"""Alert rule analytics service — tracks performance metrics for alert rules."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.models.alert import Alert, AlertRuleAnalytics, AlertRule
from vanguard_signal.schema.enums import AlertStatus

logger = logging.getLogger(__name__)


class AlertRuleAnalyticsService:
    """
    Service for tracking and calculating alert rule performance analytics.

    Maintains rolling analytics windows and calculates effectiveness metrics.
    """

    def __init__(self, analytics_window_days: int = 30):
        """
        Initialize analytics service.

        Args:
            analytics_window_days: Number of days to keep analytics data
        """
        self.analytics_window_days = analytics_window_days

    async def record_alert_creation(self, alert: Alert) -> None:
        """
        Record that an alert was created by a rule.

        Updates the current analytics period for the rule.
        """
        if not alert.trigger_rule_id:
            return  # Not created by a rule

        async with get_session() as session:
            try:
                # Get or create current analytics record
                analytics = await self._get_current_analytics(session, alert.trigger_rule_id)
                if not analytics:
                    analytics = await self._create_analytics_record(session, alert.trigger_rule_id)

                # Update counts
                analytics.alerts_generated += 1
                await session.commit()

                logger.debug("Recorded alert creation for rule %s", alert.trigger_rule_id)

            except Exception as exc:
                logger.error("Failed to record alert creation analytics: %s", exc)
                await session.rollback()

    async def record_alert_resolution(
        self,
        alert: Alert,
        was_confirmed: bool,
        response_time_minutes: Optional[float] = None
    ) -> None:
        """
        Record that an alert was resolved.

        Args:
            alert: The resolved alert
            was_confirmed: True if confirmed as true positive, False if dismissed
            response_time_minutes: Time from creation to resolution
        """
        if not alert.trigger_rule_id:
            return

        async with get_session() as session:
            try:
                analytics = await self._get_current_analytics(session, alert.trigger_rule_id)
                if not analytics:
                    analytics = await self._create_analytics_record(session, alert.trigger_rule_id)

                # Update resolution counts
                if was_confirmed:
                    analytics.alerts_confirmed += 1
                else:
                    analytics.alerts_dismissed += 1

                # Update response time (rolling average)
                if response_time_minutes is not None:
                    if analytics.average_response_time_minutes is None:
                        analytics.average_response_time_minutes = response_time_minutes
                    else:
                        # Simple rolling average
                        total_alerts = analytics.alerts_confirmed + analytics.alerts_dismissed
                        analytics.average_response_time_minutes = (
                            (analytics.average_response_time_minutes * (total_alerts - 1) + response_time_minutes)
                            / total_alerts
                        )

                # Recalculate performance metrics
                await self._update_performance_metrics(analytics)

                await session.commit()

                logger.debug("Recorded alert resolution for rule %s", alert.trigger_rule_id)

            except Exception as exc:
                logger.error("Failed to record alert resolution analytics: %s", exc)
                await session.rollback()

    async def record_alert_escalation(self, alert: Alert) -> None:
        """Record that an alert was escalated."""
        if not alert.trigger_rule_id:
            return

        async with get_session() as session:
            try:
                analytics = await self._get_current_analytics(session, alert.trigger_rule_id)
                if analytics:
                    analytics.alerts_escalated += 1
                    await session.commit()

                logger.debug("Recorded alert escalation for rule %s", alert.trigger_rule_id)

            except Exception as exc:
                logger.error("Failed to record alert escalation analytics: %s", exc)
                await session.rollback()

    async def get_rule_analytics(
        self,
        rule_id: str,
        days: int = 30
    ) -> list[AlertRuleAnalytics]:
        """
        Get analytics for a specific rule over the last N days.

        Returns list of analytics records, most recent first.
        """
        async with get_session() as session:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                result = await session.execute(
                    select(AlertRuleAnalytics)
                    .where(
                        AlertRuleAnalytics.rule_id == rule_id,
                        AlertRuleAnalytics.period_end >= cutoff_date
                    )
                    .order_by(AlertRuleAnalytics.period_end.desc())
                )

                return list(result.scalars())

            except Exception as exc:
                logger.error("Failed to get rule analytics: %s", exc)
                return []

    async def get_all_rules_analytics(
        self,
        days: int = 30
    ) -> dict[str, list[AlertRuleAnalytics]]:
        """
        Get analytics for all rules over the last N days.

        Returns dict mapping rule_id to list of analytics records.
        """
        async with get_session() as session:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

                result = await session.execute(
                    select(AlertRuleAnalytics)
                    .where(AlertRuleAnalytics.period_end >= cutoff_date)
                    .order_by(AlertRuleAnalytics.rule_id, AlertRuleAnalytics.period_end.desc())
                )

                analytics = result.scalars()
                rules_data = {}

                for analytic in analytics:
                    rule_id = str(analytic.rule_id)
                    if rule_id not in rules_data:
                        rules_data[rule_id] = []
                    rules_data[rule_id].append(analytic)

                return rules_data

            except Exception as exc:
                logger.error("Failed to get all rules analytics: %s", exc)
                return {}

    async def cleanup_old_analytics(self, max_age_days: int = 90) -> int:
        """
        Remove analytics records older than max_age_days.

        Returns number of records deleted.
        """
        async with get_session() as session:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

                result = await session.execute(
                    select(func.count(AlertRuleAnalytics.id))
                    .where(AlertRuleAnalytics.period_end < cutoff_date)
                )
                count = result.scalar() or 0

                if count > 0:
                    await session.execute(
                        AlertRuleAnalytics.__table__.delete()
                        .where(AlertRuleAnalytics.period_end < cutoff_date)
                    )
                    await session.commit()
                    logger.info("Cleaned up %d old analytics records", count)

                return count

            except Exception as exc:
                logger.error("Failed to cleanup old analytics: %s", exc)
                await session.rollback()
                return 0

    async def _get_current_analytics(
        self,
        session: AsyncSession,
        rule_id: str
    ) -> Optional[AlertRuleAnalytics]:
        """Get the current analytics record for a rule (most recent period)."""
        now = datetime.now(timezone.utc)
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        result = await session.execute(
            select(AlertRuleAnalytics)
            .where(
                AlertRuleAnalytics.rule_id == rule_id,
                AlertRuleAnalytics.period_start == period_start
            )
        )

        return result.scalar_one_or_none()

    async def _create_analytics_record(
        self,
        session: AsyncSession,
        rule_id: str
    ) -> AlertRuleAnalytics:
        """Create a new analytics record for the current period."""
        now = datetime.now(timezone.utc)
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)

        analytics = AlertRuleAnalytics(
            rule_id=rule_id,
            period_start=period_start,
            period_end=period_end,
            alerts_generated=0,
            alerts_confirmed=0,
            alerts_dismissed=0,
            alerts_escalated=0
        )

        session.add(analytics)
        await session.flush()  # Get the ID
        return analytics

    async def _update_performance_metrics(self, analytics: AlertRuleAnalytics) -> None:
        """Calculate and update performance metrics for an analytics record."""
        total_resolved = analytics.alerts_confirmed + analytics.alerts_dismissed

        if total_resolved > 0:
            # Precision: confirmed / (confirmed + dismissed)
            analytics.precision_score = analytics.alerts_confirmed / total_resolved

            # False positive rate: dismissed / total resolved
            analytics.false_positive_rate = analytics.alerts_dismissed / total_resolved

        # Effectiveness score (simple combination of precision and volume)
        # Higher precision and reasonable volume = higher score
        if analytics.precision_score is not None:
            volume_factor = min(1.0, analytics.alerts_generated / 100.0)  # Cap at 100 alerts
            analytics.effectiveness_score = analytics.precision_score * volume_factor


# Global singleton
_analytics_service: Optional[AlertRuleAnalyticsService] = None


def get_analytics_service() -> AlertRuleAnalyticsService:
    """Get the global analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AlertRuleAnalyticsService()
    return _analytics_service
