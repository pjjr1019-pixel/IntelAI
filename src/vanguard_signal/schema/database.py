"""
database.py — Engine creation, session factory, and schema bootstrap.

Usage (application startup):
    from vanguard_signal.schema.database import engine, async_session, init_db
    await init_db()           # creates schemas + tables if they don't exist
    async with async_session() as session:
        ...

The four Postgres schemas keep data physically separated in the
lakehouse pattern:

    ingestion.*   — raw and normalized data (immutable audit layer)
    signal.*      — time-series, anomalies, semantic clusters
    alert.*       — alerts, evidence chains, analyst feedback
    backtest.*    — synthetic replay data (isolated from prod)

When running in SQLite desktop mode (VS_DB_MODE=sqlite), Postgres schemas
are skipped and all tables live in a single local file.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session

from vanguard_signal.config import settings
from vanguard_signal.schema.base import Base

# ── SQLite type compatibility ────────────────────────────────────────────
# PostgreSQL-specific types (ARRAY, JSONB, UUID) don't exist in SQLite.
# We register compile-time overrides so the same models work on both.
if settings.db.is_sqlite:
    import json as _json
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID

    @compiles(ARRAY, "sqlite")
    def _compile_array_sqlite(type_, compiler, **kw):  # noqa: N802
        return "JSON"

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: N802
        return "JSON"

    @compiles(PG_UUID, "sqlite")
    def _compile_uuid_sqlite(type_, compiler, **kw):  # noqa: N802
        return "CHAR(36)"

    # Runtime bind/result processors so Python lists survive the SQLite round-trip
    _orig_array_bp = ARRAY.bind_processor
    _orig_array_rp = ARRAY.result_processor

    def _array_bind_processor(self, dialect):
        def process(value):
            if value is not None:
                return _json.dumps(value)
            return value
        if dialect.name == "sqlite":
            return process
        orig = _orig_array_bp(self, dialect)
        return orig

    def _array_result_processor(self, dialect, coltype):
        def process(value):
            if value is not None and isinstance(value, str):
                return _json.loads(value)
            return value
        if dialect.name == "sqlite":
            return process
        orig = _orig_array_rp(self, dialect, coltype)
        return orig

    ARRAY.bind_processor = _array_bind_processor
    ARRAY.result_processor = _array_result_processor

    # Patch ForeignKey.__init__ to strip schemas for SQLite
    from sqlalchemy import ForeignKey
    original_init = ForeignKey.__init__
    
    def patched_init(self, *args, **kwargs):
        # Call original init first
        result = original_init(self, *args, **kwargs)
        # For SQLite, patch the _colspec to handle schema prefixes
        if settings.db.is_sqlite and hasattr(self, '_colspec') and isinstance(self._colspec, str) and '.' in self._colspec and self._colspec.count('.') > 1:
            parts = self._colspec.split('.')
            if len(parts) == 3:  # schema.table.column
                old_colspec = self._colspec
                table_with_schema = f"{parts[0]}.{parts[1]}"
                table_without_schema = parts[1]
                
                # Check if table exists in metadata
                if table_without_schema in Base.metadata.tables:
                    # Table exists without schema, strip it
                    self._colspec = f"{parts[1]}.{parts[2]}"
                    print(f"Patched ForeignKey (table without schema): {old_colspec} -> {self._colspec}")
                elif table_with_schema in Base.metadata.tables:
                    # Table exists with schema, keep it
                    print(f"Kept ForeignKey with schema: {old_colspec}")
                else:
                    # Table not found yet, assume it will have schema and keep it
                    print(f"Kept ForeignKey (table not found yet): {old_colspec}")
        return result
    
    ForeignKey.__init__ = patched_init
    print("ForeignKey.__init__ has been patched")

# For SQLite, strip schemas from model classes since SQLite doesn't support schemas
if settings.db.is_sqlite:
    # Clear existing metadata to force re-creation without schemas
    Base.metadata.clear()
    
    # Modify model __table_args__ before re-importing
    import vanguard_signal.schema.models as models_module
    import inspect
    
    # First pass: modify __table_args__ to remove schemas
    for name, obj in inspect.getmembers(models_module):
        if (inspect.isclass(obj) and 
            hasattr(obj, '__table_args__') and 
            obj.__table_args__):
            
            # Remove schema from __table_args__
            if isinstance(obj.__table_args__, dict) and 'schema' in obj.__table_args__:
                print(f"Removing schema from {name}.__table_args__")
                del obj.__table_args__['schema']
            elif isinstance(obj.__table_args__, (tuple, list)):
                new_args = []
                for arg in obj.__table_args__:
                    if isinstance(arg, dict) and 'schema' in arg:
                        # Remove schema from dict
                        print(f"Removing schema from {name}.__table_args__ dict")
                        new_arg = {k: v for k, v in arg.items() if k != 'schema'}
                        if new_arg:  # Only add if dict is not empty
                            new_args.append(new_arg)
                    else:
                        new_args.append(arg)
                obj.__table_args__ = tuple(new_args) if new_args else None

# Make sure every model is imported so Base.metadata is complete
import vanguard_signal.schema.models  # noqa: F401

# For SQLite, strip schemas from tables after they are created
if settings.db.is_sqlite:
    # Strip schemas from table objects (but don't try to rename metadata keys)
    for table_name, table in list(Base.metadata.tables.items()):
        original_schema = table.schema
        if original_schema:
            print(f"Stripping schema '{original_schema}' from table '{table_name}'")
            table.schema = None
    
    # Reconfigure mappers after schema changes
    from sqlalchemy.orm import configure_mappers
    configure_mappers()

# For SQLite, add event listener to modify SQL and strip schema prefixes
if settings.db.is_sqlite:
    @event.listens_for(Base.metadata, "before_create")
    def _before_create(target, connection, **kw):
        """Modify table schemas before creation."""
        for table in target.tables.values():
            if table.schema:
                # Temporarily set schema to None for SQLite
                table._original_schema = table.schema
                table.schema = None
    
    @event.listens_for(Base.metadata, "after_create")
    def _after_create(target, connection, **kw):
        """Restore table schemas after creation."""
        for table in target.tables.values():
            if hasattr(table, '_original_schema'):
                table.schema = table._original_schema
                del table._original_schema

logger = logging.getLogger(__name__)

# ── Postgres Schemas (namespaces) ────────────────────────────────────────
SCHEMAS = ["ingestion", "signal", "alert", "backtest"]


# ── Async Engine & Session Factory ───────────────────────────────────────

def _build_engine() -> AsyncEngine:
    if settings.db.is_sqlite:
        # Ensure the sqlite directory exists
        db_path = Path(settings.db.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        eng = create_async_engine(
            settings.db.url,
            echo=settings.db.echo_sql,
            # SQLite doesn't support pool_size/max_overflow the same way
        )
        # Enable WAL mode + foreign keys for SQLite via sync listener
        @event.listens_for(eng.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")  # Better performance than FULL
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")   # Temp tables in memory
            cursor.close()

        return eng

    return create_async_engine(
        settings.db.url,
        echo=settings.db.echo_sql,
        pool_size=20,  # Increased from 10
        max_overflow=30,  # Increased from 20
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections every hour
    )


engine: AsyncEngine = _build_engine()

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency-injectable async session context manager."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Database Bootstrap ───────────────────────────────────────────────────

# ── Global state for init caching ─────────────────────────────────────
_db_initialized = False

async def init_db() -> None:
    """
    Create Postgres schemas and all tables (idempotent).

    In production, use Alembic migrations instead of create_all().
    This function is provided for local development and testing.
    SQLite mode skips schema creation (not supported).
    """
    global _db_initialized
    if _db_initialized:
        logger.info("Database already initialized, skipping.")
        return

    async with engine.begin() as conn:
        if not settings.db.is_sqlite:
            # Ensure Postgres schemas exist
            for schema_name in SCHEMAS:
                await conn.execute(
                    text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                )
                logger.info("Ensured schema: %s", schema_name)
        else:
            # SQLite doesn't support schemas — strip them from all tables
            for table in Base.metadata.tables.values():
                table.schema = None

        # Check if tables already exist to avoid slow recreation
        if settings.env == "development":
            # In dev mode, check if a key table exists first
            try:
                result = await conn.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'users' LIMIT 1"))
                if result.fetchone():
                    logger.info("Tables already exist, skipping creation.")
                    _db_initialized = True
                    return
            except Exception:
                # If check fails, proceed with creation
                pass

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created / verified.")
        _db_initialized = True


async def drop_db() -> None:
    """Drop all tables. USE WITH EXTREME CAUTION — dev/test only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        for schema_name in reversed(SCHEMAS):
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        logger.info("All tables and schemas dropped.")


# ── FastAPI Dependency ──────────────────────────────────────────────────

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
