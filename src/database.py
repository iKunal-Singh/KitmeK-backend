"""
Async SQLAlchemy engine and session factory for KitmeK Lesson Generation.

Configured for asyncpg driver.  DATABASE_URL must use the
``postgresql+asyncpg://`` scheme, e.g.:

    postgresql+asyncpg://kitmeK:dev_password@localhost:5432/lesson_generation

FastAPI dependency: inject ``get_async_db()`` via ``Depends``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------

_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://kitmeK:password@localhost:5432/lesson_generation"
)


def _get_database_url() -> str:
    """Return the DATABASE_URL from environment, config, or a safe default.

    Priority:
    1. DATABASE_URL environment variable (raw or plain ``postgresql://``)
    2. Settings class default (from .env or hardcoded default)
    3. Hardcoded fallback (allows import-time safety for the verify command)

    In production, DATABASE_URL *must* be provided explicitly.
    """
    url: str | None = os.getenv("DATABASE_URL")
    if not url:
        # Try loading from pydantic settings (reads .env if present)
        try:
            from src.config import get_settings  # local to avoid circular import

            url = get_settings().database_url
        except Exception:  # noqa: BLE001
            url = _DEFAULT_DATABASE_URL
    # Normalise plain postgresql:// to use the asyncpg driver.
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _build_engine() -> AsyncEngine:
    """Create the shared async engine with production-grade pool settings."""
    return create_async_engine(
        _get_database_url(),
        # Connection pool
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,  # recycle connections after 1 hour
        pool_pre_ping=True,  # validate connections before use
        # Echo SQL only in debug mode
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    )


# Module-level singletons – created once on first import.
engine: AsyncEngine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Declarative base (shared by all ORM models)
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async generator yielding a database session for FastAPI ``Depends``.

    Usage::

        @app.get("/example")
        async def example(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(MyModel))
            ...

    The session is committed on clean exit and rolled back on any exception,
    then closed in both cases.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Low-level connection helper (migrations, health checks)
# ---------------------------------------------------------------------------


async def get_async_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Yield a raw ``AsyncConnection`` from the engine.

    Useful for DDL operations (migrations, schema inspection) where the ORM
    session abstraction is not needed.
    """
    async with engine.begin() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Startup / shutdown helpers (call from FastAPI lifespan)
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables declared on ``Base`` metadata.

    In production, prefer Alembic migrations.  This helper is useful for
    integration tests and local bootstrapping.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose the engine and close all pooled connections.

    Call this from the FastAPI ``lifespan`` shutdown handler to allow
    graceful container shutdown without connection leaks.
    """
    await engine.dispose()


# ---------------------------------------------------------------------------
# Type alias (convenience re-export for DI annotations)
# ---------------------------------------------------------------------------

DBSession = AsyncSession


async def check_db_connection() -> dict[str, Any]:
    """Probe the database and return a health-status dict.

    Returns:
        dict with key ``"status"`` set to ``"ok"`` or ``"error"``.
        On error, ``"detail"`` contains the exception message.
    """
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("DB health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


__all__: list[str] = [
    "Base",
    "DBSession",
    "AsyncSessionLocal",
    "engine",
    "get_async_db",
    "get_async_connection",
    "init_db",
    "dispose_engine",
    "check_db_connection",
]
