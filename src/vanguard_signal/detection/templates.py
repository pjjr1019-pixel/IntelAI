"""
alert_templates.py — Template selection and rendering service for alerts.

This service:
  1. Selects the appropriate template for an alert based on severity, category, etc.
  2. Renders templates with alert data using Jinja2
  3. Provides fallback templates when custom ones aren't available
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.enums import Severity
from vanguard_signal.schema.models.alert import Alert, AlertTemplate

logger = logging.getLogger(__name__)


class AlertTemplateService:
    """Service for selecting and rendering alert templates."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_template_for_alert(self, alert: Alert) -> Optional[AlertTemplate]:
        """
        Select the most appropriate template for an alert.

        Priority order:
        1. Default template for this severity
        2. Any default template
        3. System template for this severity
        4. Any system template
        """
        # Try to find a default template that matches severity
        if alert.severity.value in ['low', 'medium', 'high', 'critical']:
            severity_templates = await self._session.execute(
                select(AlertTemplate).where(
                    AlertTemplate.is_default == True,
                    AlertTemplate.enabled == True,
                    AlertTemplate.severity_filter.contains([alert.severity.value])
                )
            )
            template = severity_templates.scalar_one_or_none()
            if template:
                return template

        # Try any default template
        default_templates = await self._session.execute(
            select(AlertTemplate).where(
                AlertTemplate.is_default == True,
                AlertTemplate.enabled == True
            )
        )
        template = default_templates.scalar_one_or_none()
        if template:
            return template

        # Try system template for this severity
        if alert.severity.value in ['low', 'medium', 'high', 'critical']:
            system_templates = await self._session.execute(
                select(AlertTemplate).where(
                    AlertTemplate.is_system == True,
                    AlertTemplate.enabled == True,
                    AlertTemplate.severity_filter.contains([alert.severity.value])
                )
            )
            template = system_templates.scalar_one_or_none()
            if template:
                return template

        # Try any system template
        system_templates = await self._session.execute(
            select(AlertTemplate).where(
                AlertTemplate.is_system == True,
                AlertTemplate.enabled == True
            )
        )
        template = system_templates.scalar_one_or_none()
        if template:
            return template

        return None

    def render_template(self, template: AlertTemplate, alert: Alert) -> dict[str, str]:
        """
        Render a template with alert data.

        Returns dict with 'subject', 'html', 'text' keys.
        """
        # Prepare template context
        context = self._build_template_context(alert)

        try:
            subject = Template(template.subject_template).render(**context)
            html = Template(template.html_template).render(**context)
            text = Template(template.text_template).render(**context)

            return {
                'subject': subject,
                'html': html,
                'text': text
            }
        except Exception as e:
            logger.error("Failed to render template %s: %s", template.name, e)
            # Return fallback content
            return self._get_fallback_content(alert)

    def _build_template_context(self, alert: Alert) -> dict[str, Any]:
        """Build the context dictionary for template rendering."""
        return {
            'alert_id': str(alert.id),
            'primary_entity': alert.primary_entity,
            'related_entities': alert.related_entities or [],
            'severity': alert.severity.value,
            'status': alert.status.value,
            'confidence_score': alert.confidence_score,
            'ensemble_anomaly_score': alert.ensemble_anomaly_score,
            'source_weights': alert.source_weights,
            'semantic_drift_score': alert.semantic_drift_score,
            'reason_code': alert.reason_code,
            'summary_text': alert.summary_text,
            'signal_start': alert.signal_start.isoformat() if alert.signal_start else None,
            'signal_end': alert.signal_end.isoformat() if alert.signal_end else None,
            'created_at': alert.created_at.isoformat() if alert.created_at else None,
            'updated_at': alert.updated_at.isoformat() if alert.updated_at else None,
            # Convenience aliases
            'term': alert.primary_entity,
            'anomaly_score': alert.ensemble_anomaly_score,
            'confidence': f"{alert.confidence_score * 100:.1f}",
            'detected_at': alert.created_at.isoformat() if alert.created_at else None,
            'dashboard_url': f"http://localhost:3000/alerts/{alert.id}",
            'acknowledge_url': f"http://localhost:3000/alerts/{alert.id}/acknowledge",
            'resolve_url': f"http://localhost:3000/alerts/{alert.id}/resolve",
        }

    def _get_fallback_content(self, alert: Alert) -> dict[str, str]:
        """Get fallback content when template rendering fails."""
        severity = alert.severity.value.upper()
        term = alert.primary_entity

        subject = f"[Vanguard Signal] {severity} Alert — {term}"

        html = f"""
        <html>
        <body>
            <h2>Vanguard Signal Alert - {severity} Priority</h2>
            <p><strong>Term:</strong> {term}</p>
            <p><strong>Anomaly Score:</strong> {alert.ensemble_anomaly_score:.3f}</p>
            <p><strong>Confidence:</strong> {alert.confidence_score:.1%}</p>
            <p><strong>Reason:</strong> {alert.reason_code}</p>
            <p><strong>Summary:</strong> {alert.summary_text}</p>
            <p><a href="http://localhost:3000/alerts/{alert.id}">View in Dashboard</a></p>
        </body>
        </html>
        """

        text = f"""Vanguard Signal Alert - {severity} Priority

Term: {term}
Anomaly Score: {alert.ensemble_anomaly_score:.3f}
Confidence: {alert.confidence_score:.1%}
Reason: {alert.reason_code}
Summary: {alert.summary_text}

View in Dashboard: http://localhost:3000/alerts/{alert.id}
"""

        return {
            'subject': subject,
            'html': html,
            'text': text
        }


async def get_template_service(session: AsyncSession) -> AlertTemplateService:
    """Factory function for AlertTemplateService."""
    return AlertTemplateService(session)