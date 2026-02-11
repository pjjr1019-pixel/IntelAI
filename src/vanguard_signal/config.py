"""
Central configuration loaded from environment variables.
Secrets are NEVER hard-coded; they come from AWS Secrets Manager
or a local .env file during development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Load .env file if present (python-dotenv is a listed dependency)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[2] / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass


@dataclass(frozen=True)
class DatabaseConfig:
    """Postgres connection parameters (GovCloud RDS).
    
    When VS_DB_MODE=sqlite, uses a local SQLite file instead of Postgres.
    This enables the desktop exe to run without any external database.
    """

    mode: str = os.getenv("VS_DB_MODE", "postgres")            # postgres | sqlite
    host: str = os.getenv("VS_DB_HOST", "localhost")
    port: int = int(os.getenv("VS_DB_PORT", "5432"))
    name: str = os.getenv("VS_DB_NAME", "vanguard_signal")
    user: str = os.getenv("VS_DB_USER", "vanguard")
    password: str = os.getenv("VS_DB_PASSWORD", "changeme")
    echo_sql: bool = os.getenv("VS_DB_ECHO", "false").lower() == "true"
    sqlite_path: str = os.getenv(
        "VS_SQLITE_PATH",
        str(Path(__file__).resolve().parents[2] / "data" / "vanguard.db"),
    )

    @property
    def is_sqlite(self) -> bool:
        return self.mode.lower() == "sqlite"

    @property
    def url(self) -> str:
        if self.is_sqlite:
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        if self.is_sqlite:
            return f"sqlite:///{self.sqlite_path}"
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class JWTConfig:
    """JWT authentication settings."""

    secret: str = os.getenv("VS_JWT_SECRET", "vanguard-dev-secret-change-me")
    algorithm: str = "HS256"
    expire_minutes: int = int(os.getenv("VS_JWT_EXPIRE_MINUTES", "480"))


@dataclass(frozen=True)
class NotificationConfig:
    """Notification channel settings (all optional)."""

    slack_url: str = os.getenv("VS_NOTIFY_SLACK_URL", "")
    email_host: str = os.getenv("VS_NOTIFY_EMAIL_HOST", "")
    email_port: int = int(os.getenv("VS_NOTIFY_EMAIL_PORT", "587"))
    email_user: str = os.getenv("VS_NOTIFY_EMAIL_USER", "")
    email_pass: str = os.getenv("VS_NOTIFY_EMAIL_PASS", "")
    email_from: str = os.getenv("VS_NOTIFY_EMAIL_FROM", "alerts@vanguard-signal.local")
    email_to: str = os.getenv("VS_NOTIFY_EMAIL_TO", "")  # comma-separated
    webhook_url: str = os.getenv("VS_NOTIFY_WEBHOOK_URL", "")
    webhook_secret: str = os.getenv("VS_NOTIFY_WEBHOOK_SECRET", "")


@dataclass(frozen=True)
class RedditConfig:
    """Reddit API credentials."""

    client_id: str = os.getenv("VS_REDDIT_CLIENT_ID", os.getenv("REDDIT_CLIENT_ID", ""))
    client_secret: str = os.getenv("VS_REDDIT_CLIENT_SECRET", os.getenv("REDDIT_CLIENT_SECRET", ""))
    user_agent: str = os.getenv("VS_REDDIT_USER_AGENT", os.getenv("REDDIT_USER_AGENT", "vanguard-signal/0.1"))


@dataclass(frozen=True)
class AppConfig:
    """Top-level application settings."""

    env: str = os.getenv("VS_ENV", "development")
    log_level: str = os.getenv("VS_LOG_LEVEL", "INFO")
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    jwt: JWTConfig = field(default_factory=JWTConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    reddit: RedditConfig = field(default_factory=RedditConfig)

    # Phase flags — toggle features without redeploying
    enable_semantic_engine: bool = os.getenv("VS_SEMANTIC", "false").lower() == "true"
    enable_backtest: bool = os.getenv("VS_BACKTEST", "false").lower() == "true"
    enable_rl_feedback: bool = os.getenv("VS_RL_FEEDBACK", "false").lower() == "true"

    # Ingestion settings
    ingest_interval_seconds: int = int(os.getenv("VS_INGEST_INTERVAL", "3600"))
    gtrends_timeframe: str = os.getenv("VS_GTRENDS_TIMEFRAME", "now 7-d")
    gtrends_geo: str = os.getenv("VS_GTRENDS_GEO", "")
    wiki_lookback_days: int = int(os.getenv("VS_WIKI_LOOKBACK_DAYS", "30"))
    wiki_granularity: str = os.getenv("VS_WIKI_GRANULARITY", "daily")
    # Safety flag: enable live external Google Trends calls by default in dev
    enable_live_trends: bool = os.getenv("VS_ENABLE_LIVE_TRENDS", "true").lower() == "true"

    @property
    def DATABASE_URL(self) -> str:
        """Database URL for compatibility with existing code."""
        return self.db.url


settings = AppConfig()
