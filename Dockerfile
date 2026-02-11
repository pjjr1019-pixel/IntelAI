# ═══════════════════════════════════════════════════════════════════════
# Vanguard Signal — Multi-stage Docker build
# ═══════════════════════════════════════════════════════════════════════
# Stage 1: Build wheel
# Stage 2: Slim runtime image
# ═══════════════════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY data/ data/

# Build the wheel
RUN pip wheel --no-deps --wheel-dir /build/wheels .

# Install all dependencies as wheels
RUN pip wheel --wheel-dir /build/wheels .


# ── Stage 2: Runtime ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: run as non-root
RUN groupadd -r vanguard && useradd -r -g vanguard -d /app -s /sbin/nologin vanguard

WORKDIR /app

# Install runtime system deps (libpq for asyncpg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# Copy non-Python assets
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY data/ /app/data/

# Switch to non-root user
USER vanguard

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Default: run the API server
CMD ["uvicorn", "vanguard_signal.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
