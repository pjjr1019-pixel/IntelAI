"""
settings.py — Admin settings & system info endpoint.

Provides:
  GET /api/settings  — System configuration overview + notification channel status
"""

from __future__ import annotations

from fastapi import APIRouter

from vanguard_signal.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=dict)
async def get_system_settings() -> dict:
    """Return non-secret system configuration and feature flag status."""
    notif = settings.notifications
    slack_on = bool(notif.slack_url)
    email_on = bool(notif.email_host and notif.email_to)
    webhook_on = bool(notif.webhook_url)

    return {
        "env": settings.env,
        "semantic_enabled": settings.enable_semantic_engine,
        "backtest_enabled": settings.enable_backtest,
        "rl_feedback_enabled": settings.enable_rl_feedback,
        "ingest_interval_seconds": settings.ingest_interval_seconds,
        "notification": {
            "slack_enabled": slack_on,
            "email_enabled": email_on,
            "webhook_enabled": webhook_on,
            "channels_active": sum([slack_on, email_on, webhook_on]),
        },
    }
