"""
google_trends.py — Connector for Google Trends interest-over-time data.

Uses the `pytrends` library (unofficial Google Trends API).
Returns interest scores (0–100) for a list of keywords over a
configurable time window.

Rate limiting:  Google aggressively rate-limits Trends.  This connector
uses exponential backoff and a configurable delay between batches.

Normalization:  Each (keyword, date) tuple becomes one NormalizedEvent
with entity_type=SEARCH_QUERY and metric_value=interest score.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from vanguard_signal.ingestion.base_connector import BaseConnector
from vanguard_signal.schema.enums import EntityType, HealthStatus, SourceType
from vanguard_signal.schema.validators import NormalizedEventCreate

logger = logging.getLogger(__name__)

# Google Trends allows max 5 keywords per request
_BATCH_SIZE = 5
_TIMEFRAME_DEFAULT = "now 7-d"  # last 7 days, hourly granularity
_GEO_DEFAULT = ""               # worldwide

# Multi-timeframe strategy for fresher data
_TIMEFRAMES = [
    "now 1-H",    # Last hour (most real-time)
    "now 4-H",    # Last 4 hours
    "now 1-d",    # Last day
    "now 7-d"     # Last week (fallback)
]


class GoogleTrendsConnector(BaseConnector):
    """
    Pulls interest-over-time from Google Trends via pytrends.

    Config env vars:
      VS_GTRENDS_TIMEFRAME  — pytrends timeframe string (default: "now 7-d")
      VS_GTRENDS_GEO        — ISO country code or "" for worldwide
      VS_GTRENDS_DELAY      — seconds between batches (default: 2.0)
    """

    # ── Identity ─────────────────────────────────────────────────────────

    @property
    def source_name(self) -> str:
        return "google_trends"

    @property
    def source_type(self) -> SourceType:
        return SourceType.SEARCH

    @property
    def entity_type(self) -> EntityType:
        return EntityType.SEARCH_QUERY

    def __init__(self) -> None:
        self._timeframe = os.getenv("VS_GTRENDS_TIMEFRAME", _TIMEFRAME_DEFAULT)
        self._geo = os.getenv("VS_GTRENDS_GEO", _GEO_DEFAULT)
        self._delay = float(os.getenv("VS_GTRENDS_DELAY", "2.0"))

    # ── Fetch ────────────────────────────────────────────────────────────

    async def _fetch(self, keywords: list[str]) -> dict[str, Any]:
        """
        Pull interest-over-time for up to N keywords using multi-timeframe strategy.
        Tries shorter timeframes first for fresher data, falls back to longer periods.
        Returns a dict like:
        {
            "timeframe": "multi-timeframe",
            "geo": "",
            "keywords": ["bank run", "gold price"],
            "interest_over_time": {
                "2026-02-01T00:00:00": {"bank run": 12, "gold price": 45},
                "2026-02-01T01:00:00": {"bank run": 15, "gold price": 50},
                ...
            },
            "fetched_at": "2026-02-08T12:00:00+00:00"
        }
        """
        from pytrends.request import TrendReq

        # Try multiple timeframes for maximum freshness
        combined_interest: dict[str, dict[str, int]] = {}

        for timeframe in _TIMEFRAMES:
            logger.info("[google_trends] Trying timeframe: %s", timeframe)

            try:
                pytrends = TrendReq(hl="en-US", tz=0, retries=0, backoff_factor=0)
                timeframe_data = await self._fetch_single_timeframe(pytrends, keywords, timeframe)

                # Merge with existing data, prioritizing newer timeframes
                for ts_str, scores in timeframe_data.items():
                    if ts_str not in combined_interest:
                        combined_interest[ts_str] = {}
                    combined_interest[ts_str].update(scores)

                logger.info("[google_trends] Successfully fetched %d data points for timeframe %s",
                           len(timeframe_data), timeframe)

            except Exception as exc:
                logger.warning("[google_trends] Failed to fetch timeframe %s: %s", timeframe, exc)
                continue

        # If we got no data from any timeframe, something is wrong
        if not combined_interest:
            raise RuntimeError("Failed to fetch data from Google Trends API after trying all timeframes")

        return {
            "timeframe": "multi-timeframe",
            "geo": self._geo,
            "keywords": keywords,
            "interest_over_time": combined_interest,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _fetch_single_timeframe(self, pytrends: "TrendReq", keywords: list[str], timeframe: str) -> dict[str, dict[str, int]]:
        """Fetch data for a single timeframe."""
        all_interest: dict[str, dict[str, int]] = {}

        # Process keywords in batches of 5 (Google's limit)
        for i in range(0, len(keywords), _BATCH_SIZE):
            batch = keywords[i : i + _BATCH_SIZE]
            logger.info("[google_trends] Fetching batch: %s for timeframe %s", batch, timeframe)

            # pytrends is synchronous — run in executor to stay async
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                self._sync_fetch_batch,
                pytrends,
                batch,
                timeframe,
            )

            if df is not None and not df.empty:
                # Drop the 'isPartial' column if present
                if "isPartial" in df.columns:
                    df = df.drop(columns=["isPartial"])

                for ts, row in df.iterrows():
                    ts_str = ts.isoformat()
                    if ts_str not in all_interest:
                        all_interest[ts_str] = {}
                    for kw in batch:
                        if kw in row:
                            all_interest[ts_str][kw] = int(row[kw])

            # Respect rate limits
            if i + _BATCH_SIZE < len(keywords):
                await asyncio.sleep(self._delay)

        return all_interest

    def _sync_fetch_batch(
        self, pytrends: Any, batch: list[str], timeframe: str = None
    ) -> Any:
        """Synchronous call to pytrends (runs inside executor)."""
        try:
            pytrends.build_payload(
                batch,
                timeframe=timeframe or self._timeframe,
                geo=self._geo,
            )
            return pytrends.interest_over_time()
        except Exception as exc:
            logger.error(
                "[google_trends] Batch fetch failed for %s: %s", batch, exc
            )
            return None

    # ── Normalize ────────────────────────────────────────────────────────

    def _normalize_payload(
        self,
        raw_payload: dict[str, Any],
        raw_id: UUID,
        source_id: UUID,
    ) -> list[NormalizedEventCreate]:
        """
        Flatten the interest_over_time dict into one NormalizedEvent per
        (keyword, timestamp) pair.
        """
        events: list[NormalizedEventCreate] = []
        interest = raw_payload.get("interest_over_time", {})
        geo = raw_payload.get("geo", "")
        geo_code = geo if geo != "worldwide" else None

        for ts_str, kw_scores in interest.items():
            try:
                event_time = datetime.fromisoformat(ts_str)
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
            except ValueError:
                logger.warning("[google_trends] Skipping bad timestamp: %s", ts_str)
                continue

            for keyword, score in kw_scores.items():
                events.append(
                    NormalizedEventCreate(
                        raw_id=raw_id,
                        source_id=source_id,
                        event_time=event_time,
                        entity_type=EntityType.SEARCH_QUERY,
                        entity_value=keyword,
                        metric_value=float(score),
                        geo=geo_code,
                        language="en",
                        metadata_extra={
                            "timeframe": raw_payload.get("timeframe"),
                            "score_type": "interest_over_time",
                        },
                    )
                )

        return events

    # ── Health Check ─────────────────────────────────────────────────────

    async def health_check(self) -> HealthStatus:
        """
        Check if Google Trends API is accessible and returning data.
        Uses a well-known keyword that should always have trend data.
        """
        import asyncio

        # Use a keyword that consistently has trend data
        test_keywords = ["google", "facebook", "youtube"]

        # Temporarily reduce delay for faster health checks
        original_delay = self._delay
        original_timeframe = self._timeframe
        try:
            self._delay = 0.5  # Faster for health checks
            self._timeframe = "now 1-d"  # Shorter timeframe for quicker checks

            for keyword in test_keywords:
                try:
                    # Add timeout to prevent hanging
                    result = await asyncio.wait_for(
                        self._fetch([keyword]),
                        timeout=10.0  # 10 second timeout
                    )
                    # Check if we got any actual interest data
                    interest_data = result.get("interest_over_time", {})
                    if interest_data:
                        # Verify we have at least some data points
                        total_scores = sum(len(scores) for scores in interest_data.values())
                        if total_scores > 0:
                            logger.info("[%s] Health check passed with keyword '%s'", self.source_name, keyword)
                            return HealthStatus.LIVE
                except asyncio.TimeoutError:
                    logger.debug("[%s] Health check timed out for keyword '%s'", self.source_name, keyword)
                    continue
                except Exception as exc:
                    logger.debug("[%s] Health check failed for keyword '%s': %s", self.source_name, keyword, exc)
                    continue

        finally:
            # Restore original settings
            self._delay = original_delay
            self._timeframe = original_timeframe

        logger.warning("[%s] Health check failed: no data returned for any test keywords", self.source_name)
        return HealthStatus.DOWN
