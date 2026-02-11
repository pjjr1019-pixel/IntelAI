"""
gdelt.py — GDELT Global Event Database connector.

GDELT monitors worldwide news in 100+ languages in near real-time.
This connector queries the GDELT 2.0 GKG (Global Knowledge Graph)
and Event APIs for keyword-related events.

No API key required — GDELT is fully open.
Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-v2-developer-documentation/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from vanguard_signal.ingestion.base_connector import BaseConnector
from vanguard_signal.schema.enums import EntityType, HealthStatus, SourceType
from vanguard_signal.schema.validators import NormalizedEventCreate

logger = logging.getLogger(__name__)

# GDELT DOC 2.0 API endpoint
_GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_GEO_API = "https://api.gdeltproject.org/api/v2/geo/geo"

# Default: articles from last 7 days, English
_TIMESPAN = "7d"
_MAX_RECORDS = 250


class GDELTConnector(BaseConnector):
    """
    Queries GDELT DOC 2.0 API for news article counts and tone analysis
    related to monitored keywords.

    Outputs:
      - Article count per keyword per day (velocity)
      - Average tone score (sentiment proxy: negative = concern)
      - Geographic breakdown (which countries are reporting)
    """

    @property
    def source_name(self) -> str:
        return "gdelt"

    @property
    def source_type(self) -> SourceType:
        return SourceType.NEWS

    @property
    def entity_type(self) -> EntityType:
        return EntityType.NEWS_HEADLINE

    async def _fetch(self, keywords: list[str]) -> dict[str, Any]:
        """
        Query GDELT for each keyword and collect article metadata.
        """
        results: dict[str, Any] = {}

        async with aiohttp.ClientSession() as session:
            for keyword in keywords:
                try:
                    data = await self._query_gdelt(session, keyword)
                    results[keyword] = data
                    logger.info(
                        "GDELT: '%s' → %d articles",
                        keyword,
                        data.get("article_count", 0),
                    )
                except Exception as exc:
                    logger.error("GDELT query failed for '%s': %s", keyword, exc)
                    results[keyword] = {"error": str(exc), "article_count": 0}

        return {
            "source": "gdelt",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "timespan": _TIMESPAN,
            "results": results,
        }

    async def _query_gdelt(
        self,
        session: aiohttp.ClientSession,
        keyword: str,
    ) -> dict[str, Any]:
        """
        Query the GDELT DOC API for article count timeline and tone.

        Uses the 'timelinevol' mode for daily article counts and
        'timelinetone' for sentiment tracking.
        """
        # Timeline volume — daily article count
        vol_params = {
            "query": keyword,
            "mode": "timelinevol",
            "timespan": _TIMESPAN,
            "format": "json",
            "maxrecords": _MAX_RECORDS,
        }

        async with session.get(_GDELT_DOC_API, params=vol_params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"GDELT API returned {resp.status}")
            vol_data = await resp.json(content_type=None)

        # Timeline tone — average sentiment per day
        tone_params = {
            "query": keyword,
            "mode": "timelinetone",
            "timespan": _TIMESPAN,
            "format": "json",
            "maxrecords": _MAX_RECORDS,
        }

        async with session.get(_GDELT_DOC_API, params=tone_params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                tone_data = {}
            else:
                tone_data = await resp.json(content_type=None)

        # Parse timeline data
        timeline = self._parse_timeline(vol_data)
        tone_timeline = self._parse_tone_timeline(tone_data)

        return {
            "keyword": keyword,
            "article_count": sum(d.get("value", 0) for d in timeline),
            "timeline": timeline,
            "tone_timeline": tone_timeline,
        }

    def _parse_timeline(self, data: dict | list) -> list[dict]:
        """Parse GDELT timelinevol response into date→count pairs."""
        entries = []
        try:
            # GDELT returns nested structure: {"timeline": [{"data": [...]}]}
            if isinstance(data, dict):
                series_list = data.get("timeline", [])
                for series in series_list:
                    for point in series.get("data", []):
                        entries.append({
                            "date": point.get("date", ""),
                            "value": float(point.get("value", 0)),
                        })
            elif isinstance(data, list):
                for item in data:
                    entries.append({
                        "date": item.get("date", ""),
                        "value": float(item.get("value", 0)),
                    })
        except Exception as exc:
            logger.warning("Error parsing GDELT timeline: %s", exc)
        return entries

    def _parse_tone_timeline(self, data: dict | list) -> list[dict]:
        """Parse GDELT timelinetone response."""
        entries = []
        try:
            if isinstance(data, dict):
                series_list = data.get("timeline", [])
                for series in series_list:
                    for point in series.get("data", []):
                        entries.append({
                            "date": point.get("date", ""),
                            "tone": float(point.get("value", 0)),
                        })
        except Exception as exc:
            logger.warning("Error parsing GDELT tone timeline: %s", exc)
        return entries

    def _normalize_payload(
        self,
        raw_payload: dict[str, Any],
        raw_id: "UUID",
        source_id: "UUID",
    ) -> list[NormalizedEventCreate]:
        """
        Convert GDELT raw results into NormalizedEventCreate objects.

        Creates one event per keyword per day with article_count as metric
        and tone as metadata.
        """
        from uuid import UUID  # noqa: F811

        events: list[NormalizedEventCreate] = []
        results = raw_payload.get("results", {})

        for keyword, data in results.items():
            if isinstance(data, dict) and "error" in data:
                continue

            timeline = data.get("timeline", [])
            tone_timeline = data.get("tone_timeline", [])

            # Build tone lookup by date
            tone_by_date = {}
            for t in tone_timeline:
                tone_by_date[t["date"]] = t["tone"]

            for point in timeline:
                date_str = point.get("date", "")
                if not date_str:
                    continue

                try:
                    # GDELT dates are typically "YYYYMMDDHHMMSS" or "Month DD, YYYY"
                    if len(date_str) >= 14 and date_str[:8].isdigit():
                        event_time = datetime.strptime(
                            date_str[:8], "%Y%m%d"
                        ).replace(tzinfo=timezone.utc)
                    else:
                        event_time = datetime.strptime(
                            date_str.strip(), "%B %d, %Y"
                        ).replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.debug("Skipping unparseable GDELT date: %s", date_str)
                    continue

                events.append(NormalizedEventCreate(
                    raw_id=raw_id,
                    source_id=source_id,
                    event_time=event_time,
                    entity_type=EntityType.NEWS_HEADLINE,
                    entity_value=keyword.lower().strip(),
                    metric_value=float(point.get("value", 0)),
                    geo=None,
                    language="en",
                    metadata_extra={
                        "platform": "gdelt",
                        "tone": tone_by_date.get(date_str, 0.0),
                        "raw_date": date_str,
                    },
                ))

        return events

    async def health_check(self) -> HealthStatus:
        """Verify GDELT API availability."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "query": "test",
                    "mode": "timelinevol",
                    "timespan": "1d",
                    "format": "json",
                    "maxrecords": 1,
                }
                async with session.get(
                    _GDELT_DOC_API,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return HealthStatus.LIVE if resp.status == 200 else HealthStatus.DEGRADED
        except Exception as exc:
            logger.error("GDELT health check failed: %s", exc)
            return HealthStatus.DOWN
            return False
