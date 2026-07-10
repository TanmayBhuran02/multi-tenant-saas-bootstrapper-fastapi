"""Lazy-initialised async database engine and session factory.

Unlike the original implementation which created the engine at import
time, this module defers engine creation until ``init_db()`` is called
(typically by ``create_app()`` or ``mount_to_app()``).  This ensures
the database URL from the user's config is used rather than a hardcoded
default.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── Module-level singletons ──────────────────────────────────────────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str, *, echo: bool = False) -> None:
    """Initialise the async database engine and session factory.

    This is called automatically by :func:`create_app` and
    :func:`mount_to_app`.  It is safe to call manually if you need
    to set up the database before the app factory.

    Parameters
    ----------
    database_url:
        A SQLAlchemy async database URL
        (e.g. ``postgresql+asyncpg://user:pass@host/db``).
    echo:
        If ``True``, SQL statements are logged to stdout.
    """
    global _engine, _session_factory

    # Normalise the URL to use the async driver
    url = database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    _engine = create_async_engine(url, echo=echo, future=True)
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def get_engine() -> AsyncEngine:
    """Return the current async engine.

    Raises
    ------
    RuntimeError
        If :func:`init_db` has not been called yet.
    """
    if _engine is None:
        raise RuntimeError(
            "Database not initialised. Call init_db() or create_app() first."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the current async session factory.

    Raises
    ------
    RuntimeError
        If :func:`init_db` has not been called yet.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialised. Call init_db() or create_app() first."
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting an async database session.

    Usage::

        from multi_tenant_bootstrapper import get_db

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
