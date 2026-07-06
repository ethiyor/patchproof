import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Make sure the project root is on sys.path so our modules import ──────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# ── Import all models so Alembic can see them in Base.metadata ───────────────
from backend.db.models import Base          # noqa: E402
from backend.config import get_settings     # noqa: E402

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata Alembic will compare against the current DB state
target_metadata = Base.metadata


# ── Offline mode: generate SQL without connecting to a real DB ───────────────

def run_migrations_offline() -> None:
    """
    Offline mode — prints SQL to stdout instead of running it.
    Used with:  alembic upgrade --sql head
    Useful for reviewing what will be run before touching the real DB.
    """
    url = get_settings().database_url or "postgresql+asyncpg://user:pass@localhost/db"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode: connect to a real DB and run migrations ─────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect to the async PostgreSQL engine and run all pending migrations."""
    settings = get_settings()
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
