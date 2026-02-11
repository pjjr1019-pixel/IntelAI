"""
notifier.py — Windows desktop toast notifications for Vanguard Signal.

Shows native Windows 10/11 toast notifications when high/critical
alerts arrive. Uses winotify (pure-Python, no C deps).

Falls back gracefully if winotify is not installed.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("vanguard.desktop.notifier")

_AVAILABLE = False

try:
    from winotify import Notification, audio
    _AVAILABLE = True
except ImportError:
    logger.debug("winotify not installed — desktop notifications disabled")


def is_available() -> bool:
    """Check if desktop notifications are supported."""
    return _AVAILABLE


def notify_alert(alert_data: dict[str, Any], port: int = 8000) -> None:
    """
    Show a Windows toast notification for a new alert.

    Only fires for 'high' and 'critical' severity alerts.
    Runs in a thread to avoid blocking the event loop.
    """
    if not _AVAILABLE:
        return

    severity = alert_data.get("severity", "medium").lower()
    if severity not in ("high", "critical"):
        return

    entity = alert_data.get("primary_entity", "Unknown Entity")
    confidence = alert_data.get("confidence_score", 0)
    summary = alert_data.get("summary", "New anomaly detected")
    alert_id = alert_data.get("id", "")

    severity_label = severity.upper()
    conf_pct = f"{confidence * 100:.0f}%" if isinstance(confidence, float) else str(confidence)

    title = f"⚠ {severity_label} Alert — {entity}"
    body = f"{summary}\nConfidence: {conf_pct}"

    def _show():
        try:
            toast = Notification(
                app_id="Vanguard Signal",
                title=title,
                msg=body,
                duration="long" if severity == "critical" else "short",
            )

            # Add action to open the alert in browser
            if alert_id:
                toast.add_actions(
                    label="View Alert",
                    launch=f"http://127.0.0.1:{port}/alerts/{alert_id}",
                )

            # Sound
            if severity == "critical":
                toast.set_audio(audio.LoopingAlarm, loop=False)
            else:
                toast.set_audio(audio.Default, loop=False)

            toast.show()
            logger.info("Desktop notification shown: %s", title)
        except Exception as exc:
            logger.debug("Failed to show notification: %s", exc)

    # Run in thread — winotify.show() can block briefly
    threading.Thread(target=_show, daemon=True, name="toast-notify").start()
