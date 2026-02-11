"""
wikipedia.py — Connector for Wikipedia pageview statistics.

Uses the Wikimedia REST API (no authentication required):
  https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/
      {project}/{access}/{agent}/{article}/{granularity}/{start}/{end}

This is a fully public, high-reliability API — perfect as the "always-on"
baseline source for graceful degradation when other APIs fail.

Normalization:  Each (article, date) tuple becomes one NormalizedEvent
with entity_type=WIKI_PAGE and metric_value=view count.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import aiohttp

from vanguard_signal.ingestion.base_connector import BaseConnector
from vanguard_signal.schema.enums import EntityType, SourceType
from vanguard_signal.schema.validators import NormalizedEventCreate

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
)
_PROJECT = "en.wikipedia"
_ACCESS = "all-access"
_AGENT = "user"
_GRANULARITY_DEFAULT = "daily"
_LOOKBACK_DAYS = 30
_CONCURRENT_LIMIT = 10  # max parallel requests


class WikipediaConnector(BaseConnector):
    """
    Pulls per-article view counts from the Wikimedia REST API.

    Config env vars:
      VS_WIKI_GRANULARITY   — daily | hourly (default: daily)
      VS_WIKI_LOOKBACK_DAYS — how far back to pull (default: 30)
    """

    @property
    def source_name(self) -> str:
        return "wikipedia"

    @property
    def source_type(self) -> SourceType:
        return SourceType.WIKI

    @property
    def entity_type(self) -> EntityType:
        return EntityType.WIKI_PAGE

    def __init__(self) -> None:
        self._granularity = os.getenv(
            "VS_WIKI_GRANULARITY", _GRANULARITY_DEFAULT
        )
        self._lookback_days = int(
            os.getenv("VS_WIKI_LOOKBACK_DAYS", str(_LOOKBACK_DAYS))
        )

    # ── Fetch ────────────────────────────────────────────────────────────

    async def _fetch(self, keywords: list[str]) -> dict[str, Any]:
        """
        Pull pageview data for a list of Wikipedia article titles.

        Returns a dict like:
        {
            "project": "en.wikipedia",
            "granularity": "daily",
            "start": "20260109",
            "end": "20260208",
            "articles": {
                "Bank_run": [
                    {"timestamp": "2026010900", "views": 1234},
                    ...
                ],
                "Gold_standard": [ ... ],
            },
            "fetched_at": "2026-02-08T12:00:00+00:00"
        }
        """
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=self._lookback_days)
        start_str = start_dt.strftime("%Y%m%d")
        end_str = end_dt.strftime("%Y%m%d")

        articles_data: dict[str, list[dict[str, Any]]] = {}
        semaphore = asyncio.Semaphore(_CONCURRENT_LIMIT)

        async with aiohttp.ClientSession(
            headers={
                "User-Agent": "VanguardSignal/0.1 (OSINT research tool)",
                "Accept": "application/json",
            }
        ) as session:
            tasks = [
                self._fetch_article(
                    session, semaphore, kw, start_str, end_str
                )
                for kw in keywords
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for kw, result in zip(keywords, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "[wikipedia] Failed to fetch '%s': %s", kw, result
                    )
                    articles_data[kw] = []
                else:
                    articles_data[kw] = result

        return {
            "project": _PROJECT,
            "granularity": self._granularity,
            "start": start_str,
            "end": end_str,
            "articles": articles_data,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _fetch_article(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        article: str,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Fetch pageviews for a single article with concurrency limit."""
        # Wikipedia API expects underscores in article titles
        safe_title = article.replace(" ", "_")
        url = (
            f"{_BASE_URL}/{_PROJECT}/{_ACCESS}/{_AGENT}"
            f"/{safe_title}/{self._granularity}/{start}/{end}"
        )

        async with semaphore:
            async with session.get(url) as resp:
                if resp.status == 404:
                    logger.info(
                        "[wikipedia] Article not found: %s", article
                    )
                    return []
                resp.raise_for_status()
                data = await resp.json()

        items = data.get("items", [])
        return [
            {"timestamp": item["timestamp"], "views": item["views"]}
            for item in items
        ]

    # ── Normalize ────────────────────────────────────────────────────────

    def _normalize_payload(
        self,
        raw_payload: dict[str, Any],
        raw_id: UUID,
        source_id: UUID,
    ) -> list[NormalizedEventCreate]:
        """
        Flatten the per-article pageview data into one NormalizedEvent
        per (article, day/hour) pair.
        """
        events: list[NormalizedEventCreate] = []
        articles = raw_payload.get("articles", {})

        for article_title, datapoints in articles.items():
            for dp in datapoints:
                ts_raw = dp.get("timestamp", "")
                views = dp.get("views", 0)

                event_time = self._parse_wiki_timestamp(ts_raw)
                if event_time is None:
                    continue

                events.append(
                    NormalizedEventCreate(
                        raw_id=raw_id,
                        source_id=source_id,
                        event_time=event_time,
                        entity_type=EntityType.WIKI_PAGE,
                        entity_value=article_title.replace("_", " "),
                        metric_value=float(views),
                        geo=None,  # Wikipedia views aren't geo-tagged
                        language="en",
                        metadata_extra={
                            "project": raw_payload.get("project"),
                            "granularity": raw_payload.get("granularity"),
                        },
                    )
                )

        return events

    @staticmethod
    def _parse_wiki_timestamp(ts: str) -> datetime | None:
        """
        Parse Wikimedia timestamps like '2026010900' (YYYYMMDDHH).
        Returns timezone-aware UTC datetime or None on failure.
        """
        ts = ts.strip()
        try:
            if len(ts) == 10:
                # YYYYMMDDHH
                return datetime.strptime(ts, "%Y%m%d%H").replace(
                    tzinfo=timezone.utc
                )
            elif len(ts) == 8:
                # YYYYMMDD
                return datetime.strptime(ts, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            else:
                return None
        except ValueError:
            return None
