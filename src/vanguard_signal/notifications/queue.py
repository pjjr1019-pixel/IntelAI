"""Alert queue service — prioritizes and batches alert notifications."""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from vanguard_signal.notifications.dispatcher import get_dispatcher
from vanguard_signal.schema.enums import Severity

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueuedAlert:
    """Alert queued for batch processing with priority."""
    priority: int  # Lower number = higher priority
    timestamp: float
    alert_id: str
    alert_payload: dict[str, Any] = field(compare=False)
    severity: Severity = field(compare=False)

    def __post_init__(self) -> None:
        # Set priority based on severity (lower number = higher priority)
        priority_map = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        self.priority = priority_map.get(self.severity, 2)


class AlertQueueService:
    """
    Priority queue for alert notifications with batching.

    Features:
    - Priority-based queuing (Critical > High > Medium > Low)
    - Time-based batching (send batches every N seconds)
    - Size-based batching (send when queue reaches M alerts)
    - Background processing
    """

    def __init__(
        self,
        batch_interval: float = 30.0,  # Send batch every 30 seconds
        max_batch_size: int = 10,      # Or when 10 alerts accumulate
        max_queue_size: int = 1000,    # Prevent memory issues
    ) -> None:
        self.batch_interval = batch_interval
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size

        # Priority queue: list of QueuedAlert tuples
        self._queue: list[QueuedAlert] = []
        self._lock = asyncio.Lock()

        # Background task
        self._processing_task: Optional[asyncio.Task[None]] = None
        self._shutdown_event = asyncio.Event()

        # Stats
        self.alerts_queued = 0
        self.batches_sent = 0
        self.alerts_sent = 0

    async def start(self) -> None:
        """Start the background processing task."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_queue())
            logger.info("Alert queue service started")

    async def stop(self) -> None:
        """Stop the background processing and send any remaining alerts."""
        self._shutdown_event.set()
        if self._processing_task:
            await self._processing_task
            self._processing_task = None

        # Send any remaining alerts
        await self._flush_queue()
        logger.info("Alert queue service stopped")

    async def enqueue_alert(
        self,
        alert_id: str,
        alert_payload: dict[str, Any],
        severity: Severity = Severity.MEDIUM
    ) -> bool:
        """
        Add an alert to the priority queue.

        Returns True if queued successfully, False if queue is full.
        """
        async with self._lock:
            if len(self._queue) >= self.max_queue_size:
                logger.warning("Alert queue full (%d), dropping alert %s", self.max_queue_size, alert_id)
                return False

            queued_alert = QueuedAlert(
                priority=0,  # Will be set in __post_init__
                timestamp=time.time(),
                alert_id=alert_id,
                alert_payload=alert_payload,
                severity=severity
            )

            heapq.heappush(self._queue, queued_alert)
            self.alerts_queued += 1
            logger.debug("Queued alert %s (severity: %s, queue size: %d)",
                        alert_id, severity.value, len(self._queue))
            return True

    async def _process_queue(self) -> None:
        """Background task that processes the queue."""
        last_batch_time = time.time()

        while not self._shutdown_event.is_set():
            try:
                current_time = time.time()
                should_batch = (
                    len(self._queue) >= self.max_batch_size or
                    (current_time - last_batch_time) >= self.batch_interval
                )

                if should_batch and self._queue:
                    await self._send_batch()
                    last_batch_time = current_time

                # Wait for next check
                await asyncio.sleep(min(5.0, self.batch_interval))

            except Exception as exc:
                logger.error("Error in alert queue processing: %s", exc)
                await asyncio.sleep(5.0)  # Back off on errors

    async def _send_batch(self) -> None:
        """Send the highest priority alerts as a batch."""
        async with self._lock:
            if not self._queue:
                return

            # Get batch of alerts (up to max_batch_size, highest priority first)
            batch = []
            batch_size = min(self.max_batch_size, len(self._queue))

            for _ in range(batch_size):
                if self._queue:
                    alert = heapq.heappop(self._queue)
                    batch.append(alert)

            if not batch:
                return

        # Send batch outside lock
        try:
            await self._dispatch_batch(batch)
            self.batches_sent += 1
            self.alerts_sent += len(batch)
            logger.info("Sent batch of %d alerts", len(batch))

        except Exception as exc:
            logger.error("Failed to send alert batch: %s", exc)
            # Re-queue failed alerts (with backoff)
            for alert in batch:
                alert.timestamp += 60.0  # Delay retry by 1 minute
                async with self._lock:
                    if len(self._queue) < self.max_queue_size:
                        heapq.heappush(self._queue, alert)

    async def _dispatch_batch(self, batch: list[QueuedAlert]) -> None:
        """Send a batch of alerts via the notification dispatcher."""
        dispatcher = get_dispatcher()

        # Group alerts by channel for efficiency
        # For now, send each alert individually (dispatcher handles batching per channel)
        for queued_alert in batch:
            try:
                if dispatcher.channels:
                    result = await dispatcher.dispatch(queued_alert.alert_payload)
                    sent_count = sum(1 for v in result.values() if v)
                    logger.debug("Alert %s sent to %d/%d channels",
                               queued_alert.alert_id, sent_count, len(result))
            except Exception as exc:
                logger.error("Failed to dispatch alert %s: %s", queued_alert.alert_id, exc)

    async def _flush_queue(self) -> None:
        """Send all remaining alerts in the queue (called during shutdown)."""
        async with self._lock:
            remaining = self._queue.copy()
            self._queue.clear()

        if remaining:
            logger.info("Flushing %d remaining alerts", len(remaining))
            # Sort by priority for final send
            remaining.sort()
            await self._dispatch_batch(remaining)


# Global singleton
_queue_service: Optional[AlertQueueService] = None


def get_alert_queue() -> AlertQueueService:
    """Get the global alert queue service instance."""
    global _queue_service
    if _queue_service is None:
        _queue_service = AlertQueueService()
    return _queue_service
