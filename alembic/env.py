# Alembic environment configuration for Vanguard Signal.
# This file tells Alembic where to find the models and the database.

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection

from alembic import context

# Import ALL models so metadata is populated
from vanguard_signal.schema.base import Base
import vanguard_signal.schema.models  # noqa: F401
from vanguard_signal.config import settings

config = context.config

# Set the database URL dynamically from app config
config.set_main_option("sqlalchemy.url", settings.db.sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    """Only manage our four schemas; skip public and pg_catalog."""
    if type_ == "schema":
        return name in {"ingestion", "signal", "alert", "backtest"}
    return True


def run_migrations_offline() -> None:
    """Run migrations in --sql mode (no live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="ingestion",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""
    from sqlalchemy import engine_from_config

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
