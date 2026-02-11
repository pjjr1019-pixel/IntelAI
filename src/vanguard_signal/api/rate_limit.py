"""Rate limiting and API security hardening middleware."""

from __future__ import annotations

import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ── In-memory sliding window rate limiter ────────────────────────────
import time
from collections import defaultdict


class _TokenBucket:
    """Simple per-key token bucket rate limiter (in-memory)."""

    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(self.capacity), now))
        elapsed = now - last
        tokens = min(self.capacity, tokens + elapsed * self.rate)
        if tokens >= 1:
            self._buckets[key] = (tokens - 1, now)
            return True
        self._buckets[key] = (tokens, now)
        return False


# Default: 60 requests/min for API, 5 requests/min for auth
_api_limiter = _TokenBucket(rate=1.0, capacity=60)  # 60/min
_auth_limiter = _TokenBucket(rate=5 / 60, capacity=5)  # 5/min


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies rate limiting based on client IP + path category."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Auth endpoints get stricter limits
        if path.startswith("/api/auth"):
            if not _auth_limiter.allow(client_ip):
                logger.warning("Auth rate limit hit for %s", client_ip)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many authentication attempts. Retry later."},
                    headers={"Retry-After": "60"},
                )
        # All other API endpoints
        elif path.startswith("/api/"):
            if not _api_limiter.allow(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Retry later."},
                    headers={"Retry-After": "10"},
                )

        return await call_next(request)


# ── Security headers middleware ──────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if os.getenv("VS_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def install_security(app: FastAPI) -> None:
    """Attach rate limiting and security headers to a FastAPI app."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting and security headers installed")
