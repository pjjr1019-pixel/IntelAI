"""
live_trending.py — Live worldwide trending searches with velocity metrics.

Fetches real-time trending searches from Google Trends RSS feed,
then pulls interest-over-time data to compute velocity and sparklines.

Endpoints:
  GET /api/trending/live — Live trending searches with velocity/volume data
"""

from __future__ import annotations

import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Any

import numpy as np
import pandas as pd
import requests
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel, Field
from sqlalchemy import select

from vanguard_signal.api.deps import get_user_id
from vanguard_signal.api.deps import get_db
from vanguard_signal.schema.database import async_session
from vanguard_signal.schema.models.trend import TrendSnapshot, TrendKeyword, TrendTimeSeries, TrendAlert
from vanguard_signal.schema.models.alert import AlertRule, AlertRuleTrigger


def categorize_trend(keyword: str) -> str:
    """Categorize a trend keyword into predefined categories."""
    lower_keyword = keyword.lower()
    
    # Entertainment & Media
    if any(word in lower_keyword for word in ['movie', 'film', 'actor', 'actress', 'celebrity', 'tv', 'netflix', 'spotify', 'music', 'song', 'album', 'artist']):
        return 'Entertainment'
    
    # Sports
    if any(word in lower_keyword for word in ['football', 'soccer', 'basketball', 'baseball', 'tennis', 'golf', 'nfl', 'nba', 'mlb', 'championship', 'tournament', 'olympics', 'world cup', 'super bowl']):
        return 'Sports'
    
    # Technology
    if any(word in lower_keyword for word in ['apple', 'google', 'microsoft', 'facebook', 'twitter', 'instagram', 'tiktok', 'youtube', 'ai', 'crypto', 'bitcoin', 'ethereum', 'blockchain', 'software', 'app', 'phone', 'computer', 'internet']):
        return 'Technology'
    
    # Politics & News
    if any(word in lower_keyword for word in ['election', 'president', 'government', 'politics', 'trump', 'biden', 'congress', 'senate', 'vote', 'law', 'court', 'supreme']):
        return 'Politics'
    
    # Business & Finance
    if any(word in lower_keyword for word in ['stock', 'market', 'economy', 'business', 'company', 'ceo', 'money', 'bank', 'investment', 'trading', 'finance']):
        return 'Business'
    
    # Health & Science
    if any(word in lower_keyword for word in ['health', 'medical', 'doctor', 'hospital', 'vaccine', 'virus', 'disease', 'cancer', 'science', 'research', 'study', 'nasa', 'space']):
        return 'Health & Science'
    
    return 'General'

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/trending",
    tags=["trending"],
)

# ── Constants ────────────────────────────────────────────────────────────

_RSS_URL = "https://trends.google.com/trending/rss"
_NS = {"ht": "https://trends.google.com/trending/rss"}
_BATCH_SIZE = 5  # Google Trends max per request
_FETCH_DELAY = 3.0  # seconds between batches

# In-memory cache (live trends don't change every second)
_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_CACHE_TTL = 300  # seconds (5 minutes - reduced API calls)
_RSS_UPDATE_INTERVAL = 600  # seconds (10 minutes - reduced API calls)

# Lock to prevent multiple simultaneous fetches
_cache_lock = asyncio.Lock()

# ── Geo code mapping ────────────────────────────────────────────────────

_GEO_MAP: dict[str, str] = {
    "US": "united_states",
    "GB": "united_kingdom",
    "DE": "germany",
    "FR": "france",
    "JP": "japan",
    "CA": "canada",
    "AU": "australia",
    "IN": "india",
    "BR": "brazil",
    "IT": "italy",
    "ES": "spain",
    "MX": "mexico",
    "KR": "south_korea",
    "RU": "russia",
}


# ── Response Models ──────────────────────────────────────────────────────

class TrendingNewsItem(BaseModel):
    title: str
    url: str
    source: str
    snippet: str = ""


class LiveTrendingEntity(BaseModel):
    """One trending search with volume, velocity, and context."""
    rank: int
    keyword: str
    approx_traffic: str = Field(description="Approximate daily search volume string, e.g. '500,000+'")
    traffic_value: int = Field(description="Numeric traffic estimate for sorting")
    sparkline: list[float] = Field(default_factory=list, description="Hourly interest scores (last 7 days)")
    current_interest: float = Field(0.0, description="Latest hourly interest score (0-100)")
    peak_interest: float = Field(0.0, description="Peak interest in the window")
    velocity: float = Field(0.0, description="Rate of change (first derivative)")
    acceleration: float = Field(0.0, description="Change in velocity (second derivative)")
    pct_change_24h: float = Field(0.0, description="% change in last 24 hours")
    direction: str = Field("unknown", description="up / down / flat / accelerating_up / spike")
    news: list[TrendingNewsItem] = Field(default_factory=list, description="Related news articles")
    published_at: str = ""
    geo: str = Field("", description="Geographic region this trend is from")


class LiveTrendingResponse(BaseModel):
    trends: list[LiveTrendingEntity]
    total: int
    geo: str
    generated_at: str
    cached: bool = False


# ── RSS Parsing ──────────────────────────────────────────────────────────

def _parse_traffic(traffic_str: str) -> int:
    """Convert '500,000+' or '5000+' to an integer."""
    try:
        cleaned = traffic_str.replace(",", "").replace("+", "").strip()
        return int(cleaned)
    except (ValueError, AttributeError):
        return 0


def _fetch_rss(geo: str = "US") -> list[dict]:
    """Fetch and parse the Google Trends RSS feed with rate limiting avoidance."""
    import random
    import time

    # Fetch from a few key regions to get more comprehensive trending data
    # Include the requested geo first, then add a couple more major markets
    major_markets = [geo]  # Start with requested geo

    # Add a few more major markets for broader coverage (keep it minimal for speed)
    additional_markets = ["US", "GB", "CA", "AU", "DE", "FR", "JP", "IN", "BR"]
    for market in additional_markets:
        if market not in major_markets and market != geo:
            major_markets.append(market)
            if len(major_markets) >= 8:  # Increased to 8 regions for more comprehensive results
                break

    all_items: list[dict] = []
    seen_keywords = set()  # Track keywords we've already seen to avoid duplicates

    # Fetch from each market with conservative rate limiting
    for market_geo in major_markets:
        url = f"{_RSS_URL}?geo={market_geo}"

        # Use different user agents to avoid detection
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                resp = requests.get(url, timeout=5, headers=headers)
                resp.raise_for_status()

                # Check if we got a rate limit response
                if "Too Many Requests" in resp.text or resp.status_code == 429:
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        delay = (2 ** attempt) * 5 + random.uniform(1, 3)
                        logger.warning(f"Rate limited for {market_geo}, attempt {attempt + 1}, waiting {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limited for {market_geo} after {max_retries} attempts")
                        break

                root = ET.fromstring(resp.text)
                break  # Success, exit retry loop

            except requests.exceptions.RequestException as exc:
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) * 2 + random.uniform(1, 2)
                    logger.warning(f"Request failed for {market_geo}, attempt {attempt + 1}, waiting {delay:.1f}s: {exc}")
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to fetch RSS for {market_geo} after {max_retries} attempts: {exc}")
                    continue
        else:
            # All retries failed
            continue

        try:
            market_items = []
            for idx, item in enumerate(root.findall(".//item")):
                title = item.findtext("title", "").strip()
                if not title:
                    continue

                # Skip if we've already seen this keyword (case-insensitive)
                title_lower = title.lower()
                if title_lower in seen_keywords:
                    continue

                traffic = item.findtext("ht:approx_traffic", "0+", _NS)
                pub_date = item.findtext("pubDate", "")

                # Parse news items
                news_items: list[dict] = []
                for ni in item.findall("ht:news_item", _NS):
                    news_items.append({
                        "title": ni.findtext("ht:news_item_title", "", _NS).strip(),
                        "url": ni.findtext("ht:news_item_url", "", _NS).strip(),
                        "source": ni.findtext("ht:news_item_source", "", _NS).strip(),
                        "snippet": ni.findtext("ht:news_item_snippet", "", _NS).strip(),
                    })

                market_items.append({
                    "rank": len(all_items) + len(market_items) + 1,
                    "keyword": title,
                    "approx_traffic": traffic,
                    "traffic_value": _parse_traffic(traffic),
                    "published_at": pub_date,
                    "news": news_items,
                    "geo": market_geo,
                })

                # Mark this keyword as seen
                seen_keywords.add(title_lower)

            all_items.extend(market_items)

            # Conservative delay between requests (increased for rate limiting)
            if market_geo != major_markets[-1]:
                time.sleep(2 + random.uniform(1.0, 2.0))

        except ET.ParseError as exc:
            logger.debug("Failed to parse RSS XML for %s: %s", market_geo, exc)
            continue

    # Sort by traffic value (highest first)
    all_items.sort(key=lambda x: x["traffic_value"], reverse=True)

    logger.info(f"Fetched {len(all_items)} real trending items from {geo}")
    return all_items


# ── Interest-over-time fetch ────────────────────────────────────────────

async def _fetch_interest(keywords: list[str]) -> tuple[dict[str, list[float]], bool]:
    """
    Fetch interest-over-time for a list of keywords.
    Returns ({keyword: [hourly_scores...]}, rate_limited: bool) for each keyword.
    """
    from pytrends.request import TrendReq

    result: dict[str, list[float]] = {kw: [] for kw in keywords}
    loop = asyncio.get_event_loop()
    rate_limited = False

    for i in range(0, len(keywords), _BATCH_SIZE):
        batch = keywords[i: i + _BATCH_SIZE]
        logger.info("[live_trending] Fetching interest for: %s", batch)

        try:
            def _sync_fetch(kws=batch):
                pt = TrendReq(hl="en-US", tz=0, retries=0, backoff_factor=0)
                pt.build_payload(kws, timeframe="now 7-d", geo="")
                df = pt.interest_over_time()
                if df is not None and not df.empty:
                    if "isPartial" in df.columns:
                        df = df.drop(columns=["isPartial"])
                    return {col: df[col].tolist() for col in df.columns}
                return {}

            data = await loop.run_in_executor(None, _sync_fetch)
            for kw, scores in data.items():
                if kw in result:
                    result[kw] = scores
        except Exception as exc:
            logger.warning("[live_trending] Interest fetch failed for %s: %s", batch, exc)
            # If we get rate limited, stop trying for this request
            if "429" in str(exc) or "rate limit" in str(exc).lower():
                logger.warning("[live_trending] Rate limited, skipping remaining batches")
                rate_limited = True
                break

        if i + _BATCH_SIZE < len(keywords):
            await asyncio.sleep(_FETCH_DELAY)

    return result, rate_limited


# ── Velocity computation ────────────────────────────────────────────────

def _compute_velocity(scores: list[float]) -> dict[str, float]:
    """Compute velocity/acceleration/direction from an interest-over-time series."""
    if len(scores) < 3:
        return {
            "current_interest": scores[-1] if scores else 0.0,
            "peak_interest": max(scores) if scores else 0.0,
            "velocity": 0.0,
            "acceleration": 0.0,
            "pct_change_24h": 0.0,
            "direction": "unknown",
        }

    arr = np.array(scores, dtype=np.float64)
    current = float(arr[-1])
    peak = float(arr.max())

    # Velocity = first derivative at the end
    diffs = np.diff(arr)
    vel = float(diffs[-1]) if len(diffs) > 0 else 0.0

    # Acceleration = second derivative at the end
    accel_arr = np.diff(diffs) if len(diffs) >= 2 else np.array([0.0])
    accel = float(accel_arr[-1]) if len(accel_arr) > 0 else 0.0

    # % change over last 24h (hourly data → 24 points back)
    lookback = min(24, len(arr) - 1)
    prev_val = float(arr[-(lookback + 1)])
    pct_24h = ((current - prev_val) / max(abs(prev_val), 0.01)) * 100

    # Direction
    if current > 0.8 * peak and vel > 5:
        direction = "spike"
    elif accel > 0 and vel > 0:
        direction = "accelerating_up"
    elif accel < 0 and vel > 0:
        direction = "decelerating_up"
    elif vel > 0:
        direction = "up"
    elif vel < -1:
        direction = "down"
    else:
        direction = "flat"

    return {
        "current_interest": round(current, 1),
        "peak_interest": round(peak, 1),
        "velocity": round(vel, 2),
        "acceleration": round(accel, 2),
        "pct_change_24h": round(pct_24h, 1),
        "direction": direction,
    }


# ── Endpoint ─────────────────────────────────────────────────────────────

@router.get("/live", response_model=LiveTrendingResponse)
async def _get_live_trending_internal(
    geo: str = "US",
    enrich: bool = False,  # Temporarily disabled to avoid rate limiting
) -> LiveTrendingResponse:
    """
    Internal function to fetch live trending searches (used by both API and WebSocket).
    """
    cache_key = f"{geo}:{enrich}"
    now = time.time()

    # Return cached data if fresh
    if (_cache.get("key") == cache_key
            and _cache["data"] is not None
            and (now - _cache["ts"]) < _CACHE_TTL):
        resp = _cache["data"]
        resp.cached = True
        logger.info("Returning cached trends data for geo=%s", geo)
        return resp

    # Use lock to prevent multiple simultaneous fetches
    async with _cache_lock:
        # Double-check cache after acquiring lock
        if (_cache.get("key") == cache_key
                and _cache["data"] is not None
                and (now - _cache["ts"]) < _CACHE_TTL):
            resp = _cache["data"]
            resp.cached = True
            return resp

        logger.info("Fetching fresh trends data for geo=%s", geo)
        
        # 1. Fetch trending keywords from RSS
        logger.info(f"Starting RSS fetch for geo={geo}")
        rss_items = await asyncio.get_event_loop().run_in_executor(None, _fetch_rss, geo)
        logger.info(f"RSS fetch completed, got {len(rss_items) if rss_items else 0} items")

        if not rss_items:
            return LiveTrendingResponse(
                trends=[],
                total=0,
                geo=geo,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # 2. Optionally enrich with interest-over-time data
        interest_data: dict[str, list[float]] = {}
        rate_limited = False
        if enrich and rss_items:
            keywords = [item["keyword"] for item in rss_items]
            interest_data, rate_limited = await _fetch_interest(keywords)
            if rate_limited:
                logger.warning("Google Trends API rate limited, using empty interest data")

        # 3. Build response
    trends: list[LiveTrendingEntity] = []
    for item in rss_items:
        kw = item["keyword"]
        scores = interest_data.get(kw, [])

        vel_data = _compute_velocity(scores)

        # Sparkline: last 48h of hourly data (or whatever we have)
        sparkline = scores[-48:] if scores else []

        trends.append(LiveTrendingEntity(
            rank=item["rank"],
            keyword=kw,
            approx_traffic=item["approx_traffic"],
            traffic_value=item["traffic_value"],
            sparkline=[float(s) for s in sparkline],
            current_interest=vel_data["current_interest"],
            peak_interest=vel_data["peak_interest"],
            velocity=vel_data["velocity"],
            acceleration=vel_data["acceleration"],
            pct_change_24h=vel_data["pct_change_24h"],
            direction=vel_data["direction"],
            news=[TrendingNewsItem(**n) for n in item.get("news", [])],
            published_at=item.get("published_at", ""),
            geo=item.get("geo", geo),  # Use item geo if available, otherwise fallback to requested geo
        ))

    response = LiveTrendingResponse(
        trends=trends,
        total=len(trends),
        geo=geo,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Cache
    _cache["data"] = response
    _cache["ts"] = now
    _cache["key"] = cache_key

    return response


# ── Internal helper function ──────────────────────────────────────────

async def _get_live_trending_internal(
    geo: str = "US",
    enrich: bool = True,
) -> LiveTrendingResponse:
    """
    Internal function to fetch live trending searches (used by both API and WebSocket).
    """
    cache_key = f"{geo}:{enrich}"
    now = time.time()

    # Return cached data if fresh
    if (_cache.get("key") == cache_key
            and _cache["data"] is not None
            and (now - _cache["ts"]) < _CACHE_TTL):
        resp = _cache["data"]
        resp.cached = True
        return resp

    # 1. Fetch trending keywords from RSS
    rss_items = await asyncio.get_event_loop().run_in_executor(None, _fetch_rss, geo)

    if not rss_items:
        return LiveTrendingResponse(
            trends=[],
            total=0,
            geo=geo,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # 2. Optionally enrich with interest-over-time data
    interest_data: dict[str, list[float]] = {}
    if enrich and rss_items:
        keywords = [item["keyword"] for item in rss_items]
        interest_data, _ = await _fetch_interest(keywords)

    # 3. Build response
    trends: list[LiveTrendingEntity] = []
    for item in rss_items:
        kw = item["keyword"]
        scores = interest_data.get(kw, [])

        vel_data = _compute_velocity(scores)

        # Sparkline: last 48h of hourly data (or whatever we have)
        sparkline = scores[-48:] if scores else []

        trends.append(LiveTrendingEntity(
            rank=item["rank"],
            keyword=kw,
            approx_traffic=item["approx_traffic"],
            traffic_value=item["traffic_value"],
            sparkline=[float(s) for s in sparkline],
            current_interest=vel_data["current_interest"],
            peak_interest=vel_data["peak_interest"],
            velocity=vel_data["velocity"],
            acceleration=vel_data["acceleration"],
            pct_change_24h=vel_data["pct_change_24h"],
            direction=vel_data["direction"],
            news=[TrendingNewsItem(**n) for n in item.get("news", [])],
            published_at=item.get("published_at", ""),
        ))

    response = LiveTrendingResponse(
        trends=trends,
        total=len(trends),
        geo=geo,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Persist data to database (run in background to not block response)
    asyncio.create_task(_persist_trend_data(trends, geo, rss_items))

    # Cache
    _cache["data"] = response
    _cache["ts"] = now
    _cache["key"] = cache_key

    return response


async def _persist_trend_data(trends: list[LiveTrendingEntity], geo: str, rss_items: list[dict]):
    """
    Persist trend data to database in the background.
    """
    try:
        async with async_session() as db:
            # Store trend snapshot
            snapshot = TrendSnapshot(
                geo=geo,
                total_trends=len(trends),
                source="rss",
                trends_data=[trend.dict() for trend in trends],
                processing_time_ms=0,  # Could be calculated if needed
                rate_limited=0,
            )
            db.add(snapshot)
            
            # Update keyword tracking
            for trend in trends:
                # Find existing keyword or create new one
                result = await db.execute(
                    select(TrendKeyword).where(
                        TrendKeyword.keyword == trend.keyword,
                        TrendKeyword.geo == trend.geo
                    )
                )
                keyword = result.scalar_one_or_none()
                
                if not keyword:
                    keyword = TrendKeyword(
                        keyword=trend.keyword,
                        geo=trend.geo,
                        current_rank=trend.rank,
                        current_traffic=trend.approx_traffic,
                        current_traffic_value=trend.traffic_value,
                        category=categorize_trend(trend.keyword),
                        news_count=len(trend.news),
                    )
                else:
                    # Update existing keyword
                    keyword.current_rank = trend.rank
                    keyword.current_traffic = trend.approx_traffic
                    keyword.current_traffic_value = trend.traffic_value
                    keyword.last_seen = datetime.now(timezone.utc)
                    keyword.total_appearances += 1
                    keyword.news_count = len(trend.news)
                    
                    # Update peak rank if this is better
                    if keyword.peak_rank is None or trend.rank < keyword.peak_rank:
                        keyword.peak_rank = trend.rank
                
                db.add(keyword)
                
                # Store time series data if available
                if trend.sparkline:
                    for i, interest_score in enumerate(trend.sparkline[-24:]):  # Last 24 hours
                        timestamp = datetime.now(timezone.utc)
                        # Could adjust timestamp based on data frequency
                        
                        time_series = TrendTimeSeries(
                            keyword_id=keyword.id,
                            timestamp=timestamp,
                            interest_score=interest_score,
                            rank_at_time=trend.rank,
                            velocity=trend.velocity,
                            geo=trend.geo,
                            data_source="rss",
                        )
                        db.add(time_series)
            
            # Check for alerts (spikes, significant changes)
            # await _check_and_create_alerts(db, trends, geo)  # Temporarily disabled
            
            await db.commit()
            logger.info(f"Successfully persisted {len(trends)} trends for geo {geo}")
        
    except Exception as e:
        logger.error(f"Failed to persist trend data: {e}")
        # No rollback needed with async context manager


async def _check_and_create_alerts(db, trends: list[LiveTrendingEntity], geo: str):
    """
    Check for trend alerts and create them if conditions are met.
    """
    for trend in trends:
        # Spike alert: high velocity + high current interest
        if (trend.velocity > 2.0 and trend.current_interest > 70 and 
            trend.direction in ['spike', 'accelerating_up']):
            
            alert = TrendAlert(
                keyword_id=db.query(TrendKeyword.id).filter_by(
                    keyword=trend.keyword, geo=geo
                ).first()[0],
                alert_type="spike",
                severity="high",
                message=f"Spike detected: {trend.keyword} showing rapid upward trend",
                rank_at_alert=trend.rank,
                interest_at_alert=trend.current_interest,
                velocity_at_alert=trend.velocity,
                pct_change_24h=trend.pct_change_24h,
                geo=geo,
            )
            db.add(alert)
        
        # Breakout alert: sudden rank improvement
        elif trend.velocity > 1.5 and trend.pct_change_24h > 50:
            alert = TrendAlert(
                keyword_id=db.query(TrendKeyword.id).filter_by(
                    keyword=trend.keyword, geo=geo
                ).first()[0],
                alert_type="breakout",
                severity="medium",
                message=f"Breakout: {trend.keyword} gaining significant traction",
                rank_at_alert=trend.rank,
                interest_at_alert=trend.current_interest,
                velocity_at_alert=trend.velocity,
                pct_change_24h=trend.pct_change_24h,
                geo=geo,
            )
            db.add(alert)


# ── Endpoint ─────────────────────────────────────────────────────────────

@router.get("/live", response_model=LiveTrendingResponse)
async def get_live_trending(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    enrich: bool = Query(False, description="Fetch interest-over-time for velocity data (slower but richer)"),
    _user: dict = Depends(get_user_id),
) -> LiveTrendingResponse:
    """
    Fetch live trending searches from Google Trends with velocity metrics.

    Returns what's trending RIGHT NOW worldwide or in a specific country,
    enriched with interest-over-time sparklines and velocity/acceleration data.
    Results are cached for 5 minutes to avoid rate-limiting.
    """
    return await _get_live_trending_internal(geo=geo, enrich=enrich)


@router.get("/search", response_model=LiveTrendingResponse)
async def search_google_trends(
    q: str = Query(..., min_length=1, max_length=100, description="Search query for Google Trends"),
    geo: str = Query("US", max_length=5, description="ISO country code"),
    _user: dict = Depends(get_user_id),
) -> LiveTrendingResponse:
    """
    Search Google Trends for a specific keyword and get its trending data.

    Returns interest-over-time data, velocity metrics, and trend analysis
    for the specified search query from Google Trends.
    """
    return await _search_google_trends_internal(query=q, geo=geo)


async def _search_google_trends_internal(query: str, geo: str = "US") -> LiveTrendingResponse:
    """
    Internal function to search Google Trends for a specific keyword.
    """
    import random
    import time
    from pytrends.request import TrendReq
    from pytrends.exceptions import TooManyRequestsError, ResponseError

    # Create a single-item response for the searched keyword
    try:
        # Initialize pytrends with rate limiting considerations
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]

        # Implement exponential backoff for rate limiting
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                pytrends = TrendReq(
                    hl="en-US",
                    tz=0,
                    timeout=(10, 25),
                    retries=1,
                    backoff_factor=0.5,
                    requests_args={"headers": {"User-Agent": random.choice(user_agents)}}
                )

                # Build payload for the search query
                pytrends.build_payload([query], cat=0, timeframe="now 7-d", geo=geo, gprop="")

                # Get interest over time data
                interest_df = pytrends.interest_over_time()

                if interest_df.empty:
                    # Return empty response if no data found
                    return LiveTrendingResponse(
                        trends=[],
                        total=0,
                        geo=geo,
                        generated_at=datetime.now(timezone.utc).isoformat(),
                    )

                # Extract the interest scores
                scores = interest_df[query].tolist()
                scores = [float(s) for s in scores]

                # Calculate velocity metrics
                vel_data = _compute_velocity(scores)

                # Sparkline: last 48h of hourly data (or whatever we have)
                sparkline = scores[-48:] if scores else []

                # Create the trending entity
                trend = LiveTrendingEntity(
                    rank=1,
                    keyword=query,
                    approx_traffic="N/A",  # Not available from pytrends
                    traffic_value=0,  # Not available from pytrends
                    sparkline=[float(s) for s in sparkline],
                    current_interest=vel_data["current_interest"],
                    peak_interest=vel_data["peak_interest"],
                    velocity=vel_data["velocity"],
                    acceleration=vel_data["acceleration"],
                    pct_change_24h=vel_data["pct_change_24h"],
                    direction=vel_data["direction"],
                    news=[],  # Not available from pytrends
                    published_at=datetime.now(timezone.utc).isoformat(),
                    geo=geo,
                )

                response = LiveTrendingResponse(
                    trends=[trend],
                    total=1,
                    geo=geo,
                    generated_at=datetime.now(timezone.utc).isoformat(),
                )

                return response

            except TooManyRequestsError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Rate limited by Google Trends for '{query}'. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limited by Google Trends for '{query}' after {max_retries} attempts")
                    raise e
            except ResponseError as e:
                logger.error(f"Response error from Google Trends for '{query}': {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error searching Google Trends for '{query}': {e}")
                break

        # If we get here, all attempts failed
        return LiveTrendingResponse(
            trends=[],
            total=0,
            geo=geo,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.error(f"Failed to search Google Trends for '{query}': {exc}")
        # Return empty response on error
        return LiveTrendingResponse(
            trends=[],
            total=0,
            geo=geo,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


# ── Historical Analysis Endpoints ──────────────────────────────────────

@router.get("/history/{keyword}")
async def get_keyword_history(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    _user: dict = Depends(get_user_id),
):
    """
    Get historical trend data for a specific keyword.
    Returns time series data, velocity trends, and appearance statistics.
    """
    try:
        db = next(get_db())
        
        # Get keyword info
        keyword_record = db.query(TrendKeyword).filter_by(
            keyword=keyword, geo=geo
        ).first()
        
        if not keyword_record:
            return {
                "keyword": keyword,
                "geo": geo,
                "found": False,
                "message": "Keyword not found in historical data"
            }
        
        # Get time series data
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        time_series = db.query(TrendTimeSeries).filter(
            TrendTimeSeries.keyword_id == keyword_record.id,
            TrendTimeSeries.timestamp >= cutoff_date
        ).order_by(TrendTimeSeries.timestamp).all()
        
        # Get recent alerts
        recent_alerts = db.query(TrendAlert).filter(
            TrendAlert.keyword_id == keyword_record.id,
            TrendAlert.triggered_at >= cutoff_date
        ).order_by(TrendAlert.triggered_at.desc()).limit(10).all()
        
        return {
            "keyword": keyword,
            "geo": geo,
            "found": True,
            "stats": {
                "first_seen": keyword_record.first_seen.isoformat(),
                "last_seen": keyword_record.last_seen.isoformat(),
                "total_appearances": keyword_record.total_appearances,
                "peak_rank": keyword_record.peak_rank,
                "current_rank": keyword_record.current_rank,
                "category": keyword_record.category,
                "avg_rank": keyword_record.avg_rank,
            },
            "time_series": [
                {
                    "timestamp": ts.timestamp.isoformat(),
                    "interest_score": ts.interest_score,
                    "rank": ts.rank_at_time,
                    "velocity": ts.velocity,
                }
                for ts in time_series
            ],
            "recent_alerts": [
                {
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "rank_at_alert": alert.rank_at_alert,
                    "interest_at_alert": alert.interest_at_alert,
                    "velocity_at_alert": alert.velocity_at_alert,
                }
                for alert in recent_alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get keyword history for '{keyword}': {e}")
        return {
            "keyword": keyword,
            "geo": geo,
            "found": False,
            "error": str(e)
        }
    finally:
        db.close()


@router.get("/alerts")
async def get_trend_alerts(
    geo: str = Query(None, description="Filter by geo region"),
    severity: str = Query(None, description="Filter by severity (low, medium, high, critical)"),
    alert_type: str = Query(None, description="Filter by alert type (spike, breakout, etc.)"),
    hours: int = Query(24, ge=1, le=168, description="Hours of alerts to retrieve"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
    _user: dict = Depends(get_user_id),
):
    """
    Get recent trend alerts with filtering options.
    """
    try:
        db = next(get_db())
        
        # Build query
        query = db.query(TrendAlert).join(TrendKeyword)
        
        # Apply filters
        if geo:
            query = query.filter(TrendAlert.geo == geo)
        if severity:
            query = query.filter(TrendAlert.severity == severity)
        if alert_type:
            query = query.filter(TrendAlert.alert_type == alert_type)
        
        # Time filter
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = query.filter(TrendAlert.triggered_at >= cutoff_time)
        
        # Get results
        alerts = query.order_by(TrendAlert.triggered_at.desc()).limit(limit).all()
        
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "keyword": alert.keyword.keyword,
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "rank_at_alert": alert.rank_at_alert,
                    "interest_at_alert": alert.interest_at_alert,
                    "velocity_at_alert": alert.velocity_at_alert,
                    "pct_change_24h": alert.pct_change_24h,
                    "geo": alert.geo,
                    "acknowledged": bool(alert.acknowledged),
                }
                for alert in alerts
            ],
            "total": len(alerts),
            "filters": {
                "geo": geo,
                "severity": severity,
                "alert_type": alert_type,
                "hours": hours,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get trend alerts: {e}")
        return {
            "alerts": [],
            "total": 0,
            "error": str(e)
        }
    finally:
        db.close()


@router.get("/stats")
async def get_trend_stats(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    days: int = Query(7, ge=1, le=90, description="Days to analyze"),
    _user: dict = Depends(get_user_id),
):
    """
    Get trend statistics and analytics for a region.
    """
    try:
        db = next(get_db())
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get keyword statistics
        keywords = db.query(TrendKeyword).filter(
            TrendKeyword.geo == geo,
            TrendKeyword.last_seen >= cutoff_date
        ).all()
        
        # Category breakdown
        category_stats = {}
        for keyword in keywords:
            cat = keyword.category or "Uncategorized"
            if cat not in category_stats:
                category_stats[cat] = 0
            category_stats[cat] += 1
        
        # Get recent snapshots
        snapshots = db.query(TrendSnapshot).filter(
            TrendSnapshot.geo == geo,
            TrendSnapshot.captured_at >= cutoff_date
        ).order_by(TrendSnapshot.captured_at.desc()).limit(10).all()
        
        # Alert summary
        alerts = db.query(TrendAlert).filter(
            TrendAlert.geo == geo,
            TrendAlert.triggered_at >= cutoff_date
        ).all()
        
        alert_summary = {}
        for alert in alerts:
            if alert.alert_type not in alert_summary:
                alert_summary[alert.alert_type] = 0
            alert_summary[alert.alert_type] += 1
        
        return {
            "geo": geo,
            "period_days": days,
            "overview": {
                "total_keywords_tracked": len(keywords),
                "total_snapshots": len(snapshots),
                "total_alerts": len(alerts),
                "avg_trends_per_snapshot": sum(s.total_trends for s in snapshots) / max(len(snapshots), 1),
            },
            "categories": category_stats,
            "alerts_by_type": alert_summary,
            "recent_activity": [
                {
                    "timestamp": s.captured_at.isoformat(),
                    "trends_count": s.total_trends,
                    "source": s.source,
                }
                for s in snapshots
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get trend stats: {e}")
        return {
            "geo": geo,
            "period_days": days,
            "error": str(e)
        }
    finally:
        db.close()


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query(..., description="Name/email of person acknowledging"),
    _user: dict = Depends(get_user_id),
):
    """
    Acknowledge a trend alert.
    """
    try:
        db = next(get_db())
        
        alert = db.query(TrendAlert).filter(TrendAlert.id == alert_id).first()
        if not alert:
            return {"success": False, "message": "Alert not found"}
        
        if alert.acknowledged:
            return {"success": False, "message": "Alert already acknowledged"}
        
        alert.acknowledged = 1
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Alert {alert_id} acknowledged by {acknowledged_by}"
        }
        
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        return {"success": False, "message": str(e)}
    finally:
        db.close()


# ── Alert Rules Management Endpoints ─────────────────────────────────────

@router.get("/alert-rules")
async def get_alert_rules(
    geo: str = Query("US", max_length=5, description="Filter by geo"),
    enabled_only: bool = Query(True, description="Only return enabled rules"),
    _user: dict = Depends(get_user_id),
):
    """
    Get all alert rules, optionally filtered by geo and enabled status.
    """
    try:
        db = next(get_db())
        
        query = db.query(AlertRule)
        if enabled_only:
            query = query.filter(AlertRule.enabled == 1)
        if geo != "all":
            query = query.filter(AlertRule.geo_scope.contains([geo]) | (AlertRule.geo_scope == None))
        
        rules = query.order_by(AlertRule.created_at.desc()).all()
        
        return {
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "condition_type": rule.condition_type,
                    "threshold_value": rule.threshold_value,
                    "comparison_operator": rule.comparison_operator,
                    "target_keywords": rule.target_keywords,
                    "target_categories": rule.target_categories,
                    "geo_scope": rule.geo_scope,
                    "severity": rule.severity,
                    "enabled": rule.enabled,
                    "notify_email": rule.notify_email,
                    "notify_desktop": rule.notify_desktop,
                    "email_recipients": rule.email_recipients,
                    "cooldown_minutes": rule.cooldown_minutes,
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": rule.updated_at.isoformat(),
                    "created_by": rule.created_by,
                }
                for rule in rules
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get alert rules: {e}")
        return {"rules": [], "error": str(e)}


@router.post("/alert-rules")
async def create_alert_rule(
    rule_data: dict,
    _user: dict = Depends(get_user_id),
):
    """
    Create a new alert rule.
    """
    try:
        db = next(get_db())
        
        # Validate required fields
        required_fields = ["name", "condition_type", "threshold_value", "comparison_operator", "severity"]
        for field in required_fields:
            if field not in rule_data:
                return {"success": False, "message": f"Missing required field: {field}"}
        
        # Create the rule
        new_rule = AlertRule(
            name=rule_data["name"],
            description=rule_data.get("description"),
            condition_type=rule_data["condition_type"],
            threshold_value=rule_data["threshold_value"],
            comparison_operator=rule_data["comparison_operator"],
            target_keywords=rule_data.get("target_keywords"),
            target_categories=rule_data.get("target_categories"),
            geo_scope=rule_data.get("geo_scope"),
            severity=rule_data["severity"],
            enabled=rule_data.get("enabled", 1),
            notify_email=rule_data.get("notify_email", 0),
            notify_desktop=rule_data.get("notify_desktop", 1),
            email_recipients=rule_data.get("email_recipients"),
            cooldown_minutes=rule_data.get("cooldown_minutes", 60),
            created_by=_user.get("username", "system"),
        )
        
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "success": True,
            "message": "Alert rule created successfully",
            "rule_id": new_rule.id
        }
        
    except Exception as e:
        logger.error(f"Failed to create alert rule: {e}")
        db.rollback()
        return {"success": False, "message": str(e)}


@router.put("/alert-rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    rule_data: dict,
    _user: dict = Depends(get_user_id),
):
    """
    Update an existing alert rule.
    """
    try:
        db = next(get_db())
        
        rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return {"success": False, "message": "Alert rule not found"}
        
        # Update fields
        for key, value in rule_data.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {"success": True, "message": "Alert rule updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update alert rule {rule_id}: {e}")
        db.rollback()
        return {"success": False, "message": str(e)}


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    _user: dict = Depends(get_user_id),
):
    """
    Delete an alert rule.
    """
    try:
        db = next(get_db())
        
        rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return {"success": False, "message": "Alert rule not found"}
        
        db.delete(rule)
        db.commit()
        
        return {"success": True, "message": "Alert rule deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete alert rule {rule_id}: {e}")
        db.rollback()
        return {"success": False, "message": str(e)}


@router.post("/alert-rules/{rule_id}/test")
async def test_alert_rule(
    rule_id: int,
    _user: dict = Depends(get_user_id),
):
    """
    Test an alert rule by running it against current data.
    """
    try:
        db = next(get_db())
        
        rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            return {"success": False, "message": "Alert rule not found"}
        
        # Get recent trend data to test against
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Build query based on rule conditions
        query = db.query(TrendTimeSeries).join(TrendKeyword).filter(
            TrendTimeSeries.timestamp >= cutoff_date
        )
        
        if rule.target_keywords:
            query = query.filter(TrendKeyword.keyword.in_(rule.target_keywords))
        
        if rule.geo_scope:
            query = query.filter(TrendKeyword.geo.in_(rule.geo_scope))
        
        recent_data = query.limit(100).all()
        
        # Test the rule condition
        matches = []
        for data_point in recent_data:
            value = None
            if rule.condition_type == "velocity_threshold":
                value = data_point.velocity
            elif rule.condition_type == "interest_threshold":
                value = data_point.interest_score
            elif rule.condition_type == "rank_change":
                # Would need to calculate rank change
                value = 0  # Placeholder
            
            if value is not None:
                # Check condition
                if rule.comparison_operator == ">" and value > rule.threshold_value:
                    matches.append({
                        "keyword": data_point.keyword.keyword,
                        "value": value,
                        "threshold": rule.threshold_value,
                        "timestamp": data_point.timestamp.isoformat()
                    })
                elif rule.comparison_operator == "<" and value < rule.threshold_value:
                    matches.append({
                        "keyword": data_point.keyword.keyword,
                        "value": value,
                        "threshold": rule.threshold_value,
                        "timestamp": data_point.timestamp.isoformat()
                    })
        
        return {
            "success": True,
            "rule_name": rule.name,
            "matches_found": len(matches),
            "matches": matches[:10]  # Limit to first 10 matches
        }
        
    except Exception as e:
        logger.error(f"Failed to test alert rule {rule_id}: {e}")
        return {"success": False, "message": str(e)}


# ── Correlation Analysis Endpoints ─────────────────────────────────────

@router.get("/correlation/matrix")
async def get_correlation_matrix(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    days: int = Query(7, ge=1, le=90, description="Number of days for analysis"),
    keywords: str = Query(None, description="Comma-separated list of keywords to analyze"),
    limit: int = Query(10, ge=2, le=20, description="Number of top keywords to include in matrix"),
    _user: dict = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get correlation matrix for top trending keywords or specified keywords.
    Returns a correlation matrix suitable for heatmap visualization.
    """
    try:
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get keywords to analyze
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",")]
            target_keywords_result = await db.execute(
                select(TrendKeyword).filter(
                    TrendKeyword.keyword.in_(keyword_list),
                    TrendKeyword.geo == geo
                )
            )
            target_keywords = target_keywords_result.scalars().all()
        else:
            # Get top trending keywords
            target_keywords_result = await db.execute(
                select(TrendKeyword).filter(
                    TrendKeyword.geo == geo,
                    TrendKeyword.total_appearances >= 3
                ).order_by(TrendKeyword.avg_rank).limit(limit)
            )
            target_keywords = target_keywords_result.scalars().all()
        
        if len(target_keywords) < 2:
            return {
                "matrix": [],
                "keywords": [],
                "message": "Need at least 2 keywords for correlation analysis"
            }
        
        # Get time series for all keywords
        keyword_series = {}
        for kw in target_keywords:
            series_result = await db.execute(
                select(TrendTimeSeries).filter(
                    TrendTimeSeries.keyword_id == kw.id,
                    TrendTimeSeries.timestamp >= cutoff_date
                ).order_by(TrendTimeSeries.timestamp)
            )
            series = series_result.scalars().all()
            
            if len(series) >= 3:  # Minimum data points
                keyword_series[kw.keyword] = {
                    "series": series,
                    "category": kw.category
                }
        
        if len(keyword_series) < 2:
            return {
                "matrix": [],
                "keywords": [],
                "message": "Insufficient data for correlation matrix"
            }
        
        keywords_list = list(keyword_series.keys())
        matrix_size = len(keywords_list)
        correlation_matrix = [[0.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
        
        # Calculate correlations
        for i in range(matrix_size):
            for j in range(matrix_size):
                if i == j:
                    correlation_matrix[i][j] = 1.0  # Perfect self-correlation
                elif i < j:  # Calculate only upper triangle
                    kw1 = keywords_list[i]
                    kw2 = keywords_list[j]
                    
                    series1 = keyword_series[kw1]["series"]
                    series2 = keyword_series[kw2]["series"]
                    
                    # Align time series by timestamp
                    timestamps1 = {ts.timestamp: ts.interest_score for ts in series1}
                    timestamps2 = {ts.timestamp: ts.interest_score for ts in series2}
                    
                    aligned_values1 = []
                    aligned_values2 = []
                    
                    for ts in timestamps1:
                        if ts in timestamps2:
                            aligned_values1.append(timestamps1[ts])
                            aligned_values2.append(timestamps2[ts])
                    
                    if len(aligned_values1) >= 3:
                        try:
                            correlation = np.corrcoef(aligned_values1, aligned_values2)[0, 1]
                            correlation_matrix[i][j] = round(correlation, 3)
                            correlation_matrix[j][i] = round(correlation, 3)  # Symmetric
                        except:
                            correlation_matrix[i][j] = 0.0
                            correlation_matrix[j][i] = 0.0
                    else:
                        correlation_matrix[i][j] = 0.0
                        correlation_matrix[j][i] = 0.0
        
        return {
            "matrix": correlation_matrix,
            "keywords": keywords_list,
            "categories": [keyword_series[kw]["category"] for kw in keywords_list],
            "analysis_period_days": days,
            "geo": geo
        }
        
    except Exception as e:
        logger.error(f"Failed to generate correlation matrix: {e}")
        return {
            "matrix": [],
            "keywords": [],
            "error": str(e)
        }


# ── Export & Reporting Endpoints ─────────────────────────────────────

@router.get("/export/trends")
async def export_trends(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    format: str = Query("csv", description="Export format: csv or excel"),
    days: int = Query(7, ge=1, le=90, description="Number of days of historical data"),
    _user: dict = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Export trending data to CSV or Excel format.
    Includes current trends and historical time series data.
    """
    try:
        # Get current trends
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get trend keywords with their time series
        keywords_result = await db.execute(
            select(TrendKeyword).filter(
                TrendKeyword.geo == geo,
                TrendKeyword.total_appearances >= 1
            ).order_by(TrendKeyword.avg_rank).limit(100)
        )
        keywords = keywords_result.scalars().all()
        
        # If no data for specified geo, try empty geo (worldwide data)
        if not keywords and geo != "":
            keywords_result = await db.execute(
                select(TrendKeyword).filter(
                    TrendKeyword.geo == "",
                    TrendKeyword.total_appearances >= 1
                ).order_by(TrendKeyword.avg_rank).limit(100)
            )
            keywords = keywords_result.scalars().all()
        
        export_data = []
        
        for keyword in keywords:
            # Get time series for this keyword
            series_result = await db.execute(
                select(TrendTimeSeries).filter(
                    TrendTimeSeries.keyword_id == keyword.id,
                    TrendTimeSeries.timestamp >= cutoff_date
                ).order_by(TrendTimeSeries.timestamp)
            )
            series = series_result.scalars().all()
            
            # Create base record
            base_record = {
                "Keyword": keyword.keyword,
                "Category": keyword.category,
                "Geo": keyword.geo or "Worldwide",
                "Total_Appearances": keyword.total_appearances,
                "Avg_Rank": round(keyword.avg_rank, 2),
                "Current_Rank": keyword.current_rank,
                "Data_Points": len(series),
            }
            
            if series:
                # Add time series data
                for ts in series:
                    record = base_record.copy()
                    record.update({
                        "Date": ts.timestamp.date().isoformat(),
                        "Timestamp": ts.timestamp.isoformat(),
                        "Interest_Score": ts.interest_score,
                        "Rank": ts.rank_at_time,
                        "Velocity": ts.velocity,
                    })
                    export_data.append(record)
            else:
                # No time series data, just add the keyword info
                record = base_record.copy()
                record.update({
                    "Date": None,
                    "Timestamp": None,
                    "Interest_Score": None,
                    "Rank": None,
                    "Velocity": None,
                })
                export_data.append(record)
        
        if not export_data:
            raise HTTPException(status_code=404, detail="No trend data available for export")
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Generate file
        if format.lower() == "excel":
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Trends_Data', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Trends_Data']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename=trends_export_{geo}_{datetime.now().strftime('%Y%m%d')}.xlsx"}
            )
        
        else:  # CSV format
            buffer = BytesIO()
            df.to_csv(buffer, index=False, encoding='utf-8')
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type='text/csv',
                headers={"Content-Disposition": f"attachment; filename=trends_export_{geo}_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
            
    except Exception as e:
        logger.error(f"Failed to export trends data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/alerts")
async def export_alerts(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    format: str = Query("csv", description="Export format: csv or excel"),
    days: int = Query(30, ge=1, le=365, description="Number of days of alert history"),
    _user: dict = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Export alert history to CSV or Excel format.
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get alerts
        alerts_result = await db.execute(
            select(TrendAlert).filter(
                TrendAlert.geo == geo,
                TrendAlert.triggered_at >= cutoff_date
            ).order_by(TrendAlert.triggered_at.desc())
        )
        alerts = alerts_result.scalars().all()
        
        export_data = []
        for alert in alerts:
            export_data.append({
                "Alert_ID": alert.id,
                "Keyword": alert.keyword,
                "Severity": alert.severity,
                "Type": alert.type,
                "Message": alert.message,
                "Triggered_At": alert.triggered_at.isoformat(),
                "Rank_At_Alert": alert.rank_at_alert,
                "Interest_At_Alert": alert.interest_at_alert,
                "Geo": alert.geo,
                "Rule_ID": alert.rule_id,
            })
        
        if not export_data:
            raise HTTPException(status_code=404, detail="No alert data available for export")
        
        df = pd.DataFrame(export_data)
        
        if format.lower() == "excel":
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Alerts_Data', index=False)
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename=alerts_export_{geo}_{datetime.now().strftime('%Y%m%d')}.xlsx"}
            )
        else:
            buffer = BytesIO()
            df.to_csv(buffer, index=False, encoding='utf-8')
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type='text/csv',
                headers={"Content-Disposition": f"attachment; filename=alerts_export_{geo}_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
            
    except Exception as e:
        logger.error(f"Failed to export alerts data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/correlation")
async def export_correlation_matrix(
    geo: str = Query("US", max_length=5, description="ISO country code"),
    format: str = Query("csv", description="Export format: csv or excel"),
    days: int = Query(7, ge=1, le=90, description="Number of days for analysis"),
    limit: int = Query(20, ge=2, le=50, description="Number of top keywords to include"),
    _user: dict = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Export correlation matrix to CSV or Excel format.
    """
    try:
        # Get correlation matrix data (reuse the logic from correlation endpoint)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get top trending keywords
        target_keywords_result = await db.execute(
            select(TrendKeyword).filter(
                TrendKeyword.geo == geo,
                TrendKeyword.total_appearances >= 3
            ).order_by(TrendKeyword.avg_rank).limit(limit)
        )
        target_keywords = target_keywords_result.scalars().all()
        
        if len(target_keywords) < 2:
            raise HTTPException(status_code=404, detail="Insufficient data for correlation analysis")
        
        # Get time series for all keywords
        keyword_series = {}
        for kw in target_keywords:
            series_result = await db.execute(
                select(TrendTimeSeries).filter(
                    TrendTimeSeries.keyword_id == kw.id,
                    TrendTimeSeries.timestamp >= cutoff_date
                ).order_by(TrendTimeSeries.timestamp)
            )
            series = series_result.scalars().all()
            
            if len(series) >= 3:
                keyword_series[kw.keyword] = {
                    "series": series,
                    "category": kw.category
                }
        
        if len(keyword_series) < 2:
            raise HTTPException(status_code=404, detail="Insufficient time series data for correlation")
        
        keywords_list = list(keyword_series.keys())
        matrix_size = len(keywords_list)
        correlation_matrix = [[0.0 for _ in range(matrix_size)] for _ in range(matrix_size)]
        
        # Calculate correlations
        for i in range(matrix_size):
            for j in range(matrix_size):
                if i == j:
                    correlation_matrix[i][j] = 1.0
                elif i < j:
                    kw1 = keywords_list[i]
                    kw2 = keywords_list[j]
                    
                    series1 = keyword_series[kw1]["series"]
                    series2 = keyword_series[kw2]["series"]
                    
                    # Align time series by timestamp
                    timestamps1 = {ts.timestamp: ts.interest_score for ts in series1}
                    timestamps2 = {ts.timestamp: ts.interest_score for ts in series2}
                    
                    aligned_values1 = []
                    aligned_values2 = []
                    
                    for ts in timestamps1:
                        if ts in timestamps2:
                            aligned_values1.append(timestamps1[ts])
                            aligned_values2.append(timestamps2[ts])
                    
                    if len(aligned_values1) >= 3:
                        try:
                            correlation = np.corrcoef(aligned_values1, aligned_values2)[0, 1]
                            correlation_matrix[i][j] = round(correlation, 3)
                            correlation_matrix[j][i] = round(correlation, 3)
                        except:
                            correlation_matrix[i][j] = 0.0
                            correlation_matrix[j][i] = 0.0
                    else:
                        correlation_matrix[i][j] = 0.0
                        correlation_matrix[j][i] = 0.0
        
        # Create export data
        export_data = []
        
        # Add correlation matrix
        for i, keyword1 in enumerate(keywords_list):
            row_data = {"Keyword": keyword1, "Category": keyword_series[keyword1]["category"]}
            for j, keyword2 in enumerate(keywords_list):
                row_data[f"Corr_{keyword2}"] = correlation_matrix[i][j]
            export_data.append(row_data)
        
        df = pd.DataFrame(export_data)
        
        if format.lower() == "excel":
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Correlation_Matrix', index=False)
                
                # Add a summary sheet
                summary_data = []
                for i in range(len(keywords_list)):
                    for j in range(i+1, len(keywords_list)):
                        if abs(correlation_matrix[i][j]) >= 0.3:
                            summary_data.append({
                                "Keyword_1": keywords_list[i],
                                "Keyword_2": keywords_list[j],
                                "Correlation": correlation_matrix[i][j],
                                "Strength": "Strong" if abs(correlation_matrix[i][j]) > 0.7 else "Moderate" if abs(correlation_matrix[i][j]) > 0.5 else "Weak",
                                "Direction": "Positive" if correlation_matrix[i][j] > 0 else "Negative"
                            })
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Significant_Correlations', index=False)
            
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename=correlation_export_{geo}_{datetime.now().strftime('%Y%m%d')}.xlsx"}
            )
        else:
            buffer = BytesIO()
            df.to_csv(buffer, index=False, encoding='utf-8')
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type='text/csv',
                headers={"Content-Disposition": f"attachment; filename=correlation_export_{geo}_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
            
    except Exception as e:
        logger.error(f"Failed to export correlation data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/correlation/{keyword}")
async def get_keyword_correlations(
    keyword: str,
    geo: str = Query("US", max_length=5, description="ISO country code"),
    days: int = Query(30, ge=1, le=365, description="Number of days for correlation analysis"),
    min_correlation: float = Query(0.3, ge=0, le=1, description="Minimum correlation threshold"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of correlated keywords to return"),
    _user: dict = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get correlation analysis for a keyword against other trending topics.
    Returns correlated keywords with correlation coefficients and time series.
    """
    try:
        
        # Get the target keyword's time series
        target_keyword = await db.execute(
            select(TrendKeyword).filter_by(keyword=keyword, geo=geo)
        )
        target_keyword = target_keyword.scalar_one_or_none()
        
        if not target_keyword:
            return {
                "keyword": keyword,
                "geo": geo,
                "found": False,
                "message": "Keyword not found in database"
            }
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        target_series_result = await db.execute(
            select(TrendTimeSeries).filter(
                TrendTimeSeries.keyword_id == target_keyword.id,
                TrendTimeSeries.timestamp >= cutoff_date
            ).order_by(TrendTimeSeries.timestamp)
        )
        target_series = target_series_result.scalars().all()
        
        if len(target_series) < 7:  # Need minimum data points
            return {
                "keyword": keyword,
                "geo": geo,
                "found": True,
                "correlations": [],
                "message": "Insufficient data for correlation analysis"
            }
        
        # Get other keywords with sufficient data
        other_keywords_result = await db.execute(
            select(TrendKeyword).filter(
                TrendKeyword.geo == geo,
                TrendKeyword.keyword != keyword,
                TrendKeyword.total_appearances >= 5  # Minimum appearances
            ).limit(200)  # Limit for performance
        )
        other_keywords = other_keywords_result.scalars().all()
        
        correlations = []
        
        # Extract target time series values
        target_timestamps = [ts.timestamp for ts in target_series]
        target_values = [ts.interest_score for ts in target_series]
        
        for other_keyword in other_keywords:
            # Get time series for this keyword
            other_series_result = await db.execute(
                select(TrendTimeSeries).filter(
                    TrendTimeSeries.keyword_id == other_keyword.id,
                    TrendTimeSeries.timestamp >= cutoff_date
                ).order_by(TrendTimeSeries.timestamp)
            )
            other_series = other_series_result.scalars().all()
            
            if len(other_series) < 7:
                continue
            
            # Align time series by timestamp
            aligned_target = []
            aligned_other = []
            
            other_dict = {ts.timestamp: ts.interest_score for ts in other_series}
            
            for i, timestamp in enumerate(target_timestamps):
                if timestamp in other_dict:
                    aligned_target.append(target_values[i])
                    aligned_other.append(other_dict[timestamp])
            
            if len(aligned_target) < 7:
                continue
            
            # Calculate Pearson correlation
            try:
                correlation = np.corrcoef(aligned_target, aligned_other)[0, 1]
                
                if abs(correlation) >= min_correlation:
                    correlations.append({
                        "keyword": other_keyword.keyword,
                        "correlation": round(correlation, 3),
                        "strength": "strong" if abs(correlation) > 0.7 else "moderate" if abs(correlation) > 0.5 else "weak",
                        "direction": "positive" if correlation > 0 else "negative",
                        "data_points": len(aligned_target),
                        "category": other_keyword.category,
                        "avg_rank": round(other_keyword.avg_rank, 1),
                    })
            except:
                continue
        
        # Sort by absolute correlation strength
        correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        correlations = correlations[:limit]
        
        return {
            "keyword": keyword,
            "geo": geo,
            "found": True,
            "analysis_period_days": days,
            "correlations": correlations,
            "total_analyzed": len(other_keywords),
            "significant_correlations": len(correlations)
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze correlations for '{keyword}': {e}")
        return {
            "keyword": keyword,
            "geo": geo,
            "found": False,
            "error": str(e)
        }
