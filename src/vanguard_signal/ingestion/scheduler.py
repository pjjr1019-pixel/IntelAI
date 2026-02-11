"""
scheduler.py — Ingestion orchestrator that runs on a timer.

This is the "main loop" of the ingestion engine.  It:

  1. Loads the keyword watchlist
  2. For each active source connector:
     a. Calls fetch_raw() to pull data from the external API
     b. Stores the immutable raw payload via IngestionStore
     c. Normalizes the payload into clean events
     d. Stores the normalized events
     e. Updates source health (success → LIVE, failure → DEGRADED/DOWN)
  3. Sleeps for the configured interval and repeats

The scheduler is designed to be run as a long-lived asyncio task,
either standalone (via __main__.py) or inside a FastAPI lifespan.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from vanguard_signal.ingestion.base_connector import BaseConnector
from vanguard_signal.ingestion.connectors.google_trends import GoogleTrendsConnector
from vanguard_signal.ingestion.connectors.wikipedia import WikipediaConnector
from vanguard_signal.ingestion.connectors.reddit import RedditConnector
from vanguard_signal.ingestion.connectors.gdelt import GDELTConnector
from vanguard_signal.ingestion.health import SourceHealthMonitor
from vanguard_signal.ingestion.storage import IngestionStore
from vanguard_signal.ingestion.watchlist import get_flat_keywords
from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.enums import HealthStatus, SourceType
from vanguard_signal.schema.validators import SourceRegistryCreate

logger = logging.getLogger(__name__)

_CYCLE_INTERVAL = int(os.getenv("VS_INGEST_INTERVAL", "3600"))  # seconds


# ── Source Definitions ───────────────────────────────────────────────────

_SOURCE_DEFS: list[SourceRegistryCreate] = [
    SourceRegistryCreate(
        name="google_trends",
        source_type=SourceType.SEARCH,
        description="Google Trends interest-over-time via pytrends",
        update_frequency_seconds=3600,
        data_latency_seconds=300,
        default_weight=1.0,
    ),
    SourceRegistryCreate(
        name="wikipedia",
        source_type=SourceType.WIKI,
        description="Wikipedia daily pageviews via Wikimedia REST API",
        update_frequency_seconds=3600,
        data_latency_seconds=86400,  # ~1 day lag
        default_weight=1.0,
    ),
    SourceRegistryCreate(
        name="reddit",
        source_type=SourceType.SOCIAL,
        description="Reddit keyword mentions via async PRAW",
        update_frequency_seconds=3600,
        data_latency_seconds=60,
        default_weight=0.8,
    ),
    SourceRegistryCreate(
        name="gdelt",
        source_type=SourceType.NEWS,
        description="GDELT global news article counts and tone",
        update_frequency_seconds=3600,
        data_latency_seconds=900,
        default_weight=0.9,
    ),
]

_CONNECTOR_MAP: dict[str, type[BaseConnector]] = {
    "google_trends": GoogleTrendsConnector,
    "wikipedia": WikipediaConnector,
    "reddit": RedditConnector,
    "gdelt": GDELTConnector,
}


# ═════════════════════════════════════════════════════════════════════════
# Pipeline: one pull cycle for a single source
# ═════════════════════════════════════════════════════════════════════════

_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2  # seconds: 2, 4, 8


async def _run_source_cycle(
    connector: BaseConnector,
    store: IngestionStore,
    source_id: Any,
    keywords: list[str],
) -> dict[str, Any]:
    """
    Execute one full ingest → store → normalize → store cycle
    with exponential-backoff retry on transient failures.

    Returns a summary dict for logging / monitoring.
    """
    summary: dict[str, Any] = {
        "source": connector.source_name,
        "status": "success",
        "events": 0,
        "elapsed_s": 0.0,
        "error": None,
    }

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            # 1. Fetch raw data
            raw_payload, elapsed = await connector.fetch_raw(keywords)
            summary["elapsed_s"] = round(elapsed, 2)

            # 2. Store immutable raw payload
            raw_create = connector.build_raw_ingestion(source_id, raw_payload)
            raw_row = await store.store_raw(raw_create)

            # 3. Normalize into clean events
            events = connector.normalize(raw_payload, raw_row.id, source_id)

            # 4. Store normalized events
            if events:
                await store.store_events(events)
            summary["events"] = len(events)

            # 5. Mark source as healthy
            await store.update_source_health(
                source_id, HealthStatus.LIVE, reset_failures=True
            )

            logger.info(
                "[%s] Cycle complete: %d events in %.2fs (attempt %d)",
                connector.source_name,
                len(events),
                elapsed,
                attempt,
            )
            last_exc = None
            break  # success — exit retry loop

        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "[%s] Attempt %d/%d failed: %s — retrying in %ds",
                    connector.source_name, attempt, _MAX_RETRIES, exc, delay,
                )
                await asyncio.sleep(delay)
            # else: fall through to failure handling below

    if last_exc is not None:
        summary["status"] = "error"
        summary["error"] = str(last_exc)
        logger.error(
            "[%s] All %d attempts FAILED: %s",
            connector.source_name, _MAX_RETRIES, last_exc, exc_info=True,
        )

        # Increment failure count and re-evaluate health
        try:
            source = await store.get_source_by_name(connector.source_name)
            if source:
                new_failures = source.consecutive_failures + 1
                new_status = SourceHealthMonitor.evaluate_status(new_failures)

                if SourceHealthMonitor.should_alert_on_degradation(
                    source.health_status, new_status
                ):
                    logger.warning(
                        "[%s] DEGRADATION: %s → %s (%d failures)",
                        connector.source_name,
                        source.health_status.value,
                        new_status.value,
                        new_failures,
                    )

                await store.update_source_health(
                    source_id, new_status, increment_failures=True
                )
        except Exception as inner_exc:
            logger.error("Failed to update health: %s", inner_exc)

    return summary


# ═════════════════════════════════════════════════════════════════════════
# Full Ingestion Cycle (all sources)
# ═════════════════════════════════════════════════════════════════════════

async def run_ingestion_cycle(
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Run a single ingestion cycle across ALL active sources.

    This is the function you call once to pull fresh data.
    The scheduler calls it in a loop.
    """
    kw_list = keywords or get_flat_keywords()
    summaries: list[dict[str, Any]] = []

    async with get_session() as session:
        store = IngestionStore(session)

        # Ensure all source definitions exist in the registry
        source_map: dict[str, Any] = {}
        for src_def in _SOURCE_DEFS:
            source = await store.get_or_create_source(src_def)
            source_map[src_def.name] = source

        # Run each active source
        for src_name, connector_cls in _CONNECTOR_MAP.items():
            source = source_map.get(src_name)
            if source is None or not source.is_active:
                logger.info("[%s] Skipped (inactive or missing)", src_name)
                continue

            connector = connector_cls()
            summary = await _run_source_cycle(
                connector, store, source.id, kw_list
            )
            summaries.append(summary)

    # Log overall cycle results
    ok = sum(1 for s in summaries if s["status"] == "success")
    total_events = sum(s["events"] for s in summaries)
    logger.info(
        "=== Ingestion cycle complete: %d/%d sources OK, %d total events ===",
        ok,
        len(summaries),
        total_events,
    )

    return summaries


# ═════════════════════════════════════════════════════════════════════════
# Long-running Scheduler Loop
# ═════════════════════════════════════════════════════════════════════════

async def start_scheduler(
    keywords: list[str] | None = None,
    interval_seconds: int | None = None,
    max_cycles: int | None = None,
) -> None:
    """
    Run the ingestion cycle on a repeating timer.

    Args:
        keywords:         Override the default watchlist.
        interval_seconds: Seconds between cycles (default: VS_INGEST_INTERVAL or 3600).
        max_cycles:       Stop after N cycles (None = run forever).
    """
    interval = interval_seconds or _CYCLE_INTERVAL
    cycle = 0

    logger.info(
        "Ingestion scheduler starting — interval=%ds, keywords=%d, max_cycles=%s",
        interval,
        len(keywords or get_flat_keywords()),
        max_cycles or "∞",
    )

    while True:
        cycle += 1
        logger.info("── Cycle %d starting at %s ──", cycle, datetime.now(timezone.utc))

        try:
            await run_ingestion_cycle(keywords)
        except Exception as exc:
            logger.critical("Unhandled error in cycle %d: %s", cycle, exc, exc_info=True)

        if max_cycles and cycle >= max_cycles:
            logger.info("Reached max_cycles=%d. Stopping.", max_cycles)
            break

        logger.info("Sleeping %ds until next cycle…", interval)
        await asyncio.sleep(interval)
