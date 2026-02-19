"""FastAPI dependency injection helpers.

Provides reusable ``Depends``-compatible callables for:
- ``get_db()``        → async database session
- ``get_settings()``  → application settings
- ``get_kb_loader()`` → loaded KBLoader instance (stored on app.state)
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.config import get_settings as _get_settings_impl
from src.database import get_async_db
from src.services.kb_loader import KBLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


async def get_db(
    db: AsyncSession = Depends(get_async_db),
) -> AsyncSession:
    """Provide an async database session to route handlers.

    Thin wrapper around :func:`src.database.get_async_db` that adds a
    typed annotation so handlers can use ``Annotated[AsyncSession, Depends(get_db)]``.

    Yields:
        An async SQLAlchemy session scoped to the current request.
    """
    return db


DBDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def get_settings() -> Settings:
    """Return the cached application settings.

    Returns:
        Application :class:`~src.config.Settings` singleton.
    """
    return _get_settings_impl()


SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# KB Loader (stored on app.state during lifespan startup)
# ---------------------------------------------------------------------------


def get_kb_loader(request: Request) -> KBLoader:
    """Return the application-wide KBLoader instance from ``app.state``.

    The loader is initialised during the FastAPI lifespan startup and stored
    as ``app.state.kb_loader``.  If the startup did not complete (e.g. KB
    files were missing), a 503 is returned to the caller.

    Args:
        request: Injected by FastAPI; provides access to ``app.state``.

    Returns:
        The loaded :class:`~src.services.kb_loader.KBLoader`.

    Raises:
        HTTPException: 503 if the KB loader is not available.
    """
    kb_loader: KBLoader | None = getattr(request.app.state, "kb_loader", None)
    if kb_loader is None:
        logger.error("KB loader not initialised — app.state.kb_loader is None")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base is not loaded. Check server logs for startup errors.",
        )
    return kb_loader


KBLoaderDep = Annotated[KBLoader, Depends(get_kb_loader)]
