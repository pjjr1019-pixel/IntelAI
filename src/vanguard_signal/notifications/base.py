"""Abstract base for all notification channels."""

from __future__ import annotations

import abc
from typing import Any


class BaseNotifier(abc.ABC):
    """Every notifier implements send() for a single alert payload."""

    @abc.abstractmethod
    async def send(self, alert: dict[str, Any]) -> bool:
        """Send notification for an alert. Returns True on success."""
        ...
