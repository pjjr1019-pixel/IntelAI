"""Slack webhook notifier."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .base import BaseNotifier

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}


class SlackNotifier(BaseNotifier):
    """Posts alert cards to a Slack incoming webhook."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, alert: dict[str, Any]) -> bool:
        severity = alert.get("severity", "medium")
        emoji = SEVERITY_EMOJI.get(severity, "⚪")
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Vanguard Signal Alert — {severity.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Term:* {alert.get('term', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Score:* {alert.get('anomaly_score', 0):.3f}"},
                    {"type": "mrkdwn", "text": f"*Source:* {alert.get('source', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Time:* {alert.get('detected_at', 'N/A')}"},
                ],
            },
        ]
        summary = alert.get("summary")
        if summary:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": summary[:2000]}}
            )
        payload = {"blocks": blocks}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    ok = resp.status == 200
                    if not ok:
                        logger.warning("Slack webhook returned %s", resp.status)
                    return ok
        except Exception:
            logger.exception("Slack notification failed")
            return False
