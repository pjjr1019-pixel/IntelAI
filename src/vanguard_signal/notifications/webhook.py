"""Generic webhook notifier."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .base import BaseNotifier

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    """POSTs alert JSON to a custom webhook URL with optional headers."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}

    async def send(self, alert: dict[str, Any]) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url, json=alert, headers=self.headers
                ) as resp:
                    ok = 200 <= resp.status < 300
                    if not ok:
                        logger.warning("Webhook %s returned %s", self.url, resp.status)
                    return ok
        except Exception:
            logger.exception("Webhook notification failed for %s", self.url)
            return False
