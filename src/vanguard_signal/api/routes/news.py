"""
news.py — Live news feed from GDELT (free, no API key).

Endpoints:
  GET  /api/news/feed   — Latest headlines related to watched keywords
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.deps import get_db
from vanguard_signal.api.cache import cached

router = APIRouter(prefix="/api/news", tags=["news"])
logger = logging.getLogger(__name__)

# ── In-memory 3-minute cache (avoids hammering GDELT) ────────────────
_cache: dict[str, Any] = {"data": [], "ts": 0}
_CACHE_TTL = 180  # seconds

_GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Default queries when no watchlist keywords are loaded
_DEFAULT_QUERIES = [
    "geopolitical risk",
    "financial crisis",
    "cybersecurity breach",
    "natural disaster",
    "supply chain disruption",
]


async def _fetch_gdelt_articles(
    query: str,
    max_records: int = 10,
    timespan: str = "24h",
) -> list[dict]:
    """Query GDELT DOC 2.0 Article List API."""
    params = {
        "query": f"{query} sourcelang:english",
        "mode": "artlist",
        "maxrecords": str(max_records),
        "timespan": timespan,
        "format": "json",
        "sort": "datedesc",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _GDELT_API, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    logger.warning("GDELT returned %s for query=%s", resp.status, query)
                    return []
                data = await resp.json(content_type=None)
                return data.get("articles", [])
    except Exception as exc:
        logger.warning("GDELT fetch error for %r: %s", query, exc)
        return []


def _parse_article(raw: dict, query: str) -> dict:
    """Normalise a GDELT article object to our lightweight schema."""
    seen = raw.get("seendate", "")
    try:
        dt = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        iso = dt.isoformat()
    except Exception:
        iso = datetime.now(timezone.utc).isoformat()

    return {
        "title": raw.get("title", "").strip(),
        "url": raw.get("url", ""),
        "source": raw.get("domain", "unknown"),
        "image": raw.get("socialimage", ""),
        "published_at": iso,
        "tone": round(raw.get("tone", 0.0), 2),
        "language": raw.get("language", "English"),
        "country": raw.get("sourcecountry", ""),
        "query": query,
    }


async def _load_watchlist_keywords(db: AsyncSession | None) -> list[str]:
    """Pull keywords from the user's watchlist, fallback to defaults."""
    try:
        from vanguard_signal.ingestion.watchlist import get_flat_keywords
        keywords = get_flat_keywords()
        logger.info("Loaded %d keywords from watchlist", len(keywords))
        if keywords:
            # Sample up to 8 keywords to avoid too many GDELT requests
            import random
            sampled = random.sample(keywords, min(8, len(keywords)))
            logger.debug("News feed using %d watchlist keywords", len(sampled))
            return sampled
    except Exception as exc:
        logger.warning("Could not load watchlist keywords: %s", exc)

    logger.info("Using default queries: %s", _DEFAULT_QUERIES)
    return _DEFAULT_QUERIES


@router.get("/feed")
async def news_feed(
    limit: int = Query(25, ge=5, le=100, description="Max articles to return"),
    query: str | None = Query(None, description="Custom search query (overrides defaults)"),
    timespan: str = Query("24h", description="GDELT timespan: 15min, 60min, 24h, 7d"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Fetch the latest news headlines from GDELT's free global news index.

    Returns a deduplicated, tone-sorted list of articles from the last 24h
    (or custom timespan). Results are cached for 3 minutes.
    """
    logger.info("News feed requested: limit=%d, query=%s, timespan=%s", limit, query, timespan)
    now = time.time()
    cache_key = f"{query or 'default'}:{timespan}:{limit}"

    # Return cache if fresh
    if _cache.get("key") == cache_key and (now - _cache["ts"]) < _CACHE_TTL:
        return {"articles": _cache["data"][:limit], "cached": True}

    # Determine queries
    if query:
        queries = [query]
    else:
        queries = await _load_watchlist_keywords(db)

    logger.info("Using queries: %s", queries)

    # Fetch from GDELT in parallel (one request per query)
    per_query = max(5, limit // len(queries))
    tasks = [
        _fetch_gdelt_articles(q, max_records=per_query, timespan=timespan)
        for q in queries
    ]
    results = await asyncio.gather(*tasks)

    # Check if all queries failed (no articles returned)
    total_raw_articles = sum(len(batch) for batch in results)
    if total_raw_articles == 0:
        logger.warning("All GDELT queries returned no articles - API may be unavailable")
        raise HTTPException(
            status_code=503,
            detail="News service temporarily unavailable - GDELT API returned no results"
        )

    # Flatten + parse
    articles: list[dict] = []
    seen_titles: set[str] = set()
    for q, batch in zip(queries, results):
        logger.info("Query '%s' returned %d articles", q, len(batch))
        for raw in batch:
            title = raw.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            articles.append(_parse_article(raw, q))

    logger.info("Total articles after deduplication: %d", len(articles))

    # Sort by date descending
    articles.sort(key=lambda a: a["published_at"], reverse=True)
    articles = articles[:limit]

    # Update cache
    _cache.update({"data": articles, "ts": now, "key": cache_key})

    return {"articles": articles, "cached": False}
