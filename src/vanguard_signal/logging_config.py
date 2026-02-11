"""
logging_config.py — Structured JSON logging + Prometheus metrics.

Provides:
  • JSON-formatted structured logging (for CloudWatch / ELK / Grafana Loki)
  • Request/response timing middleware
  • Prometheus metrics endpoint (/metrics)
  • Custom counters for ingestion, detection, and alerts
"""

from __future__ import annotations

import logging
import sys
import time
import json
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from vanguard_signal.config import settings


# ═════════════════════════════════════════════════════════════════════════
# STRUCTURED JSON LOGGING
# ═════════════════════════════════════════════════════════════════════════

class JSONFormatter(logging.Formatter):
    """
    Outputs log records as single-line JSON for machine parsing.
    Compatible with CloudWatch, ELK, Grafana Loki, DataDog, etc.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
            }

        # Include extra fields
        for key in ("request_id", "user_id", "entity", "source", "duration_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry, default=str)


def configure_logging(
    level: str | None = None,
    json_format: bool = True,
) -> None:
    """
    Configure the root logger with structured output.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
            Defaults to VS_LOG_LEVEL env var.
        json_format: If True, use JSON formatter. If False, use simple format.
    """
    # Set UTF-8 encoding for Windows console compatibility
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass  # Ignore if reconfigure is not available

    log_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if json_format and settings.env != "development":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db.echo_sql else logging.WARNING
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured: level=%s json=%s env=%s",
        log_level, json_format, settings.env,
    )


# ═════════════════════════════════════════════════════════════════════════
# PROMETHEUS METRICS (using prometheus_client library)
# ═════════════════════════════════════════════════════════════════════════

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ── HTTP metrics ─────────────────────────────────────────────────────────
http_requests_total = Counter(
    "vanguard_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
http_request_duration_ms = Histogram(
    "vanguard_http_request_duration_ms",
    "HTTP request duration in milliseconds",
    ["method", "path"],
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

# ── Domain metrics ───────────────────────────────────────────────────────
ingestion_events_total = Counter(
    "vanguard_ingestion_events_total",
    "Total events ingested from sources",
    ["source"],
)
ingestion_cycles_total = Counter(
    "vanguard_ingestion_cycles_total",
    "Total ingestion cycles executed",
    ["status"],
)
anomalies_detected_total = Counter(
    "vanguard_anomalies_detected_total",
    "Total anomalies detected by the pipeline",
)
alerts_created_total = Counter(
    "vanguard_alerts_created_total",
    "Total alerts created",
    ["severity"],
)
detection_cycle_duration = Histogram(
    "vanguard_detection_cycle_duration_seconds",
    "Detection cycle duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
ws_connections_active = Gauge(
    "vanguard_ws_connections_active",
    "Number of active WebSocket connections",
)
rl_updates_total = Counter(
    "vanguard_rl_updates_total",
    "Total RL prior updates from feedback",
    ["verdict"],
)
notification_sent_total = Counter(
    "vanguard_notification_sent_total",
    "Total notifications sent",
    ["channel", "status"],
)
semantic_clusters_total = Gauge(
    "vanguard_semantic_clusters_total",
    "Current number of semantic clusters",
)
max_drift_score = Gauge(
    "vanguard_max_drift_score",
    "Maximum semantic drift score observed",
)


# ═════════════════════════════════════════════════════════════════════════
# REQUEST TIMING MIDDLEWARE
# ═════════════════════════════════════════════════════════════════════════

class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Measures request duration and logs structured access log entries.
    Records Prometheus histogram for request latency.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code

        # Record metrics
        http_requests_total.labels(
            method=method, path=path, status=str(status)
        ).inc()
        http_request_duration_ms.labels(
            method=method, path=path
        ).observe(duration_ms)

        # Structured access log
        logger = logging.getLogger("vanguard_signal.access")
        logger.info(
            "%s %s → %d (%.1fms)",
            method, path, status, duration_ms,
            extra={
                "duration_ms": round(duration_ms, 1),
                "request_id": request.headers.get("x-request-id", ""),
            },
        )

        # Add timing header
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        return response


def register_metrics_and_logging(app: FastAPI) -> None:
    """
    Wire up structured logging, request timing, and /metrics endpoint.
    Call this from the app factory.
    """
    configure_logging()
    app.add_middleware(RequestTimingMiddleware)

    @app.get("/metrics", tags=["system"], include_in_schema=False)
    async def prometheus_metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
