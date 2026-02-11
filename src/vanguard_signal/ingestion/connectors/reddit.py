"""
reddit.py — Reddit connector via async PRAW or Pushshift.

Monitors subreddits for keyword mentions, tracks post velocity and
sentiment as normalized events for anomaly detection.

Requires: asyncpraw  (pip install asyncpraw)
Env vars:
    VS_REDDIT_CLIENT_ID
    VS_REDDIT_CLIENT_SECRET
    VS_REDDIT_USER_AGENT
    VS_REDDIT_SUBREDDITS  (comma-separated, default: "all")
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from vanguard_signal.ingestion.base_connector import BaseConnector
from vanguard_signal.schema.enums import EntityType, HealthStatus, SourceType
from vanguard_signal.schema.validators import NormalizedEventCreate

logger = logging.getLogger(__name__)

_CLIENT_ID = os.getenv("VS_REDDIT_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("VS_REDDIT_CLIENT_SECRET", "")
_USER_AGENT = os.getenv("VS_REDDIT_USER_AGENT", "vanguard_signal:v0.1 (by /u/vanguard)")
_SUBREDDITS = os.getenv("VS_REDDIT_SUBREDDITS", "all").split(",")
_SEARCH_LIMIT = int(os.getenv("VS_REDDIT_SEARCH_LIMIT", "100"))


class RedditConnector(BaseConnector):
    """
    Searches Reddit for keyword mentions across configured subreddits.

    Collects: post title, score, num_comments, created_utc, subreddit.
    Normalizes: keyword mention count + engagement score per time bucket.
    """

    def __init__(self) -> None:
        super().__init__()
        self._reddit = None

    @property
    def source_name(self) -> str:
        return "reddit"

    @property
    def source_type(self) -> SourceType:
        return SourceType.SOCIAL

    @property
    def entity_type(self) -> EntityType:
        return EntityType.SOCIAL_POST

    async def _get_reddit(self):
        """Lazy-init the async Reddit client."""
        if self._reddit is None:
            try:
                import asyncpraw
            except ImportError:
                raise ImportError(
                    "asyncpraw is required for Reddit connector. "
                    "Install with: pip install asyncpraw"
                )

            if not _CLIENT_ID or not _CLIENT_SECRET:
                raise ValueError(
                    "Reddit API credentials not configured. "
                    "Set VS_REDDIT_CLIENT_ID and VS_REDDIT_CLIENT_SECRET."
                )

            self._reddit = asyncpraw.Reddit(
                client_id=_CLIENT_ID,
                client_secret=_CLIENT_SECRET,
                user_agent=_USER_AGENT,
            )
        return self._reddit

    async def _fetch(self, keywords: list[str]) -> dict[str, Any]:
        """
        Search Reddit for all keywords. Returns raw search results
        grouped by keyword.
        """
        reddit = await self._get_reddit()
        results: dict[str, list[dict]] = {}

        for keyword in keywords:
            keyword_results = []
            try:
                subreddit_str = "+".join(s.strip() for s in _SUBREDDITS)
                subreddit = await reddit.subreddit(subreddit_str)

                async for submission in subreddit.search(
                    keyword,
                    sort="new",
                    time_filter="week",
                    limit=_SEARCH_LIMIT,
                ):
                    keyword_results.append({
                        "id": submission.id,
                        "title": submission.title,
                        "subreddit": str(submission.subreddit),
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": submission.created_utc,
                        "upvote_ratio": submission.upvote_ratio,
                        "selftext_length": len(submission.selftext or ""),
                        "url": f"https://reddit.com{submission.permalink}",
                    })

                logger.info(
                    "Reddit: '%s' → %d posts found",
                    keyword, len(keyword_results),
                )
            except Exception as exc:
                logger.error("Reddit search failed for '%s': %s", keyword, exc)

            results[keyword] = keyword_results

        await self._close_reddit()

        return {
            "source": "reddit",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "subreddits": _SUBREDDITS,
            "results": results,
        }

    async def _close_reddit(self):
        """Close the Reddit session."""
        if self._reddit:
            await self._reddit.close()
            self._reddit = None

    def _normalize_payload(
        self,
        raw_payload: dict[str, Any],
        raw_id: "UUID",
        source_id: "UUID",
    ) -> list[NormalizedEventCreate]:
        """
        Convert raw Reddit search results into NormalizedEventCreate objects.

        Metrics:
          - mention_count: number of posts containing the keyword
          - engagement_score: sum(score + num_comments) / mention_count
        """
        from uuid import UUID  # noqa: F811

        events: list[NormalizedEventCreate] = []
        results = raw_payload.get("results", {})

        for keyword, posts in results.items():
            if not posts:
                continue

            # Group by day
            days: dict[str, list[dict]] = {}
            for post in posts:
                dt = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)
                day_key = dt.strftime("%Y-%m-%d")
                days.setdefault(day_key, []).append(post)

            for day_key, day_posts in days.items():
                mention_count = len(day_posts)
                total_engagement = sum(
                    p["score"] + p["num_comments"] for p in day_posts
                )
                avg_engagement = total_engagement / mention_count if mention_count else 0

                event_time = datetime.strptime(day_key, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )

                events.append(NormalizedEventCreate(
                    raw_id=raw_id,
                    source_id=source_id,
                    event_time=event_time,
                    entity_type=EntityType.SOCIAL_POST,
                    entity_value=keyword.lower().strip(),
                    metric_value=float(mention_count),
                    geo=None,
                    language="en",
                    metadata_extra={
                        "platform": "reddit",
                        "avg_engagement": round(avg_engagement, 2),
                        "total_engagement": total_engagement,
                        "subreddits": list(set(p["subreddit"] for p in day_posts)),
                        "top_post_url": max(day_posts, key=lambda p: p["score"])["url"],
                    },
                ))

        return events

    async def health_check(self) -> HealthStatus:
        """Verify Reddit API connectivity."""
        try:
            reddit = await self._get_reddit()
            subreddit = await reddit.subreddit("test")
            # Just verify we can access it
            _ = subreddit.display_name
            await self._close_reddit()
            return HealthStatus.LIVE
        except Exception as exc:
            logger.error("Reddit health check failed: %s", exc)
            return HealthStatus.DOWN
