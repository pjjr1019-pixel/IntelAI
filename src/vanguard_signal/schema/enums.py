"""
enums.py — Controlled vocabularies for Vanguard Signal.

Every categorical column in the database maps to one of these enums.
Using Python enums + Postgres ENUMs gives us:
  • Type safety in application code
  • Database-level constraint enforcement
  • A single place to extend allowed values
"""

from __future__ import annotations

import enum


# ── Data Source Classification ───────────────────────────────────────────

class SourceType(str, enum.Enum):
    """What kind of data source a connector pulls from."""
    SEARCH   = "search"        # Google Trends, Bing, etc.
    WIKI     = "wiki"          # Wikipedia pageviews / edits
    SOCIAL   = "social"        # Reddit, X / Twitter, Telegram
    NEWS     = "news"          # RSS, GDELT, NewsAPI
    FINANCE  = "finance"       # Market feeds (Phase 3)
    HEALTH   = "health"        # CDC, WHO feeds (Phase 3)
    ALT_DATA = "alt_data"      # Satellite, shipping, etc. (Phase 3)


class HealthStatus(str, enum.Enum):
    """Current operational state of a data source."""
    LIVE     = "live"          # Nominal; last pull succeeded
    DEGRADED = "degraded"      # Partial data or high latency
    DOWN     = "down"          # No data returned; confidence re-weighted


# ── Normalized Event Types ───────────────────────────────────────────────

class EntityType(str, enum.Enum):
    """The kind of 'thing' an ingested event describes."""
    SEARCH_QUERY   = "search_query"
    WIKI_PAGE      = "wiki_page"
    SOCIAL_POST    = "social_post"
    NEWS_HEADLINE  = "news_headline"
    FINANCIAL_TICK = "financial_tick"   # Phase 3
    HEALTH_REPORT  = "health_report"   # Phase 3


# ── Time Bucketing ───────────────────────────────────────────────────────

class TimeBucket(str, enum.Enum):
    """Granularity level for aggregated time-series data."""
    HOUR  = "hour"
    DAY   = "day"
    WEEK  = "week"
    MONTH = "month"


# ── Anomaly / Alert Severity ────────────────────────────────────────────

class Severity(str, enum.Enum):
    """How 'loud' an alert is for analysts."""
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    """Lifecycle state of an alert."""
    ACTIVE    = "active"       # Newly created; needs analyst attention
    WATCHING  = "watching"     # Analyst is monitoring; not yet resolved
    CONFIRMED = "confirmed"    # Analyst verified as real signal
    DISMISSED = "dismissed"    # Analyst rejected as noise
    RESOLVED  = "resolved"     # Post-event; outcome recorded
    ARCHIVED  = "archived"     # Historical; used for backtesting


# ── Analyst Feedback ─────────────────────────────────────────────────────

class FeedbackVerdict(str, enum.Enum):
    """Binary analyst judgment on an alert."""
    CONFIRM = "confirm"
    DISMISS = "dismiss"


# ── Post-Mortem Outcomes ─────────────────────────────────────────────────

class EventOutcome(str, enum.Enum):
    """Did the alert correspond to a real-world event?"""
    TRUE_POSITIVE  = "true_positive"
    FALSE_POSITIVE = "false_positive"
    INCONCLUSIVE   = "inconclusive"


class ImpactDomain(str, enum.Enum):
    """Which domain was affected by the real-world event."""
    FINANCE      = "finance"
    GEOPOLITICAL = "geopolitical"
    HEALTH       = "health"
    CIVIL_UNREST = "civil_unrest"
    CYBER        = "cyber"
    ENVIRONMENTAL = "environmental"
    OTHER        = "other"


# ── Backtest Status ──────────────────────────────────────────────────────

class BacktestStatus(str, enum.Enum):
    """Lifecycle of a synthetic backtest run."""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
