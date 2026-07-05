from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import get_settings

# ---------------------------------------------------------------------------
# Engine + session factory (created lazily on first use)
# ---------------------------------------------------------------------------

_engine = None
_session_factory = None


def get_engine():
    """
    Return the async SQLAlchemy engine, creating it on first call.

    The engine is a connection pool — it maintains a set of DB connections
    ready to use so we don't open a new TCP connection on every request.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,      # logs every SQL statement when debug=True
            pool_pre_ping=True,       # test connections before using them
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Return the async session factory, creating it on first call.

    ``expire_on_commit=False`` keeps model attributes accessible after
    a commit without re-querying the database.
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an open AsyncSession and closes it when done.

    Usage in route handlers:
        async def my_route(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
