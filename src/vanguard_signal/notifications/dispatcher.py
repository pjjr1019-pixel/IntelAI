"""Notification dispatcher — fans out alerts to all configured channels."""

from __future__ import annotations

import logging
import os
from typing import Any

from .base import BaseNotifier
from .slack import SlackNotifier
from .email import EmailNotifier
from .webhook import WebhookNotifier

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """
    Reads env vars to configure notification channels, then dispatches
    alert payloads to all active channels.

    Env vars:
        VS_NOTIFY_SLACK_URL          — Slack incoming webhook URL
        VS_NOTIFY_EMAIL_HOST         — SMTP host
        VS_NOTIFY_EMAIL_PORT         — SMTP port (default 587)
        VS_NOTIFY_EMAIL_USER         — SMTP username
        VS_NOTIFY_EMAIL_PASS         — SMTP password
        VS_NOTIFY_EMAIL_FROM         — Sender address
        VS_NOTIFY_EMAIL_TO           — Comma-separated recipient list
        VS_NOTIFY_WEBHOOK_URL        — Custom webhook URL
        VS_NOTIFY_WEBHOOK_SECRET     — Optional Bearer token for webhook
    """

    def __init__(self) -> None:
        self.channels: list[BaseNotifier] = []
        self._configure()

    def _configure(self) -> None:
        # Slack
        slack_url = os.getenv("VS_NOTIFY_SLACK_URL")
        if slack_url:
            self.channels.append(SlackNotifier(slack_url))
            logger.info("Slack notifier enabled")

        # Email
        email_host = os.getenv("VS_NOTIFY_EMAIL_HOST")
        email_to = os.getenv("VS_NOTIFY_EMAIL_TO")
        if email_host and email_to:
            self.channels.append(
                EmailNotifier(
                    smtp_host=email_host,
                    smtp_port=int(os.getenv("VS_NOTIFY_EMAIL_PORT", "587")),
                    username=os.getenv("VS_NOTIFY_EMAIL_USER", ""),
                    password=os.getenv("VS_NOTIFY_EMAIL_PASS", ""),
                    from_addr=os.getenv("VS_NOTIFY_EMAIL_FROM", "alerts@vanguard-signal.local"),
                    to_addrs=[a.strip() for a in email_to.split(",")],
                )
            )
            logger.info("Email notifier enabled")

        # Webhook
        webhook_url = os.getenv("VS_NOTIFY_WEBHOOK_URL")
        if webhook_url:
            headers: dict[str, str] = {}
            secret = os.getenv("VS_NOTIFY_WEBHOOK_SECRET")
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            self.channels.append(WebhookNotifier(webhook_url, headers))
            logger.info("Webhook notifier enabled")

        if not self.channels:
            logger.info("No notification channels configured")

    async def dispatch(self, alert: dict[str, Any]) -> dict[str, bool]:
        """Send to all channels. Returns {channel_name: success}."""
        results: dict[str, bool] = {}
        for ch in self.channels:
            name = type(ch).__name__
            results[name] = await ch.send(alert)
        return results


# Module-level singleton
_dispatcher: NotificationDispatcher | None = None


def get_dispatcher() -> NotificationDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = NotificationDispatcher()
    return _dispatcher
