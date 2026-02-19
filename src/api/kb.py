"""Knowledge Base management API routes.

Provides:
    GET  /kb/version   — Return active KB version and checksum metadata.
    POST /kb/reload    — (Admin) Reload KB files from disk, invalidating cache.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import KBLoaderDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class KBVersionResponse(BaseModel):
    """Metadata about the currently loaded knowledge base version."""

    kb_version: str
    checksum: str
    files_loaded: list[str]
    total_files: int


class KBReloadResponse(BaseModel):
    """Response for a successful KB reload."""

    status: str
    kb_version: str
    checksum: str
    files_loaded: list[str]
    message: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get(
    "/version",
    response_model=KBVersionResponse,
    summary="Get active KB version and metadata",
    description=(
        "Return the version string, SHA-256 checksum, and list of loaded files"
        " for the currently active knowledge base."
    ),
    responses={
        200: {"description": "KB version metadata"},
        503: {"description": "KB not loaded"},
    },
)
async def get_kb_version(
    kb_loader: KBLoaderDep,
) -> KBVersionResponse:
    """Return metadata for the currently loaded KB.

    Args:
        kb_loader: Injected :class:`~src.services.kb_loader.KBLoader` instance.

    Returns:
        :class:`KBVersionResponse` with version, checksum, and file list.
    """
    meta: dict[str, Any] = kb_loader.get_kb_version()

    if meta.get("kb_version") == "not_loaded":
        logger.warning("GET /kb/version called but KB is not loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base is not yet loaded. Try POST /kb/reload.",
        )

    files: list[str] = meta.get("files_loaded", [])
    return KBVersionResponse(
        kb_version=meta["kb_version"],
        checksum=meta["checksum"],
        files_loaded=files,
        total_files=len(files),
    )


@router.post(
    "/reload",
    response_model=KBReloadResponse,
    summary="(Admin) Reload KB files from disk",
    description=(
        "Invalidates the in-memory KB cache and re-reads all Markdown files from"
        " the configured ``kb_path``. Useful after deploying updated KB files"
        " without restarting the server."
    ),
    responses={
        200: {"description": "KB successfully reloaded"},
        500: {"description": "Reload failed — check KB files on disk"},
        503: {"description": "KB loader not available"},
    },
)
async def reload_kb(
    kb_loader: KBLoaderDep,
) -> KBReloadResponse:
    """Reload the knowledge base from disk.

    Args:
        kb_loader: Injected :class:`~src.services.kb_loader.KBLoader` instance.

    Returns:
        :class:`KBReloadResponse` with new version metadata.

    Raises:
        HTTPException: 500 if required KB files are missing or unparseable.
    """
    from src.exceptions import KBLoadError  # local to avoid circular at top

    logger.info("POST /kb/reload: invalidating KB cache and reloading from disk")
    try:
        kb_data = kb_loader.reload()
    except KBLoadError as exc:
        logger.error("KB reload failed: %s (missing=%s)", exc, exc.missing_files)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "KB reload failed",
                "message": str(exc),
                "missing_files": exc.missing_files,
            },
        )
    except Exception as exc:
        logger.exception("Unexpected error during KB reload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KB reload failed: {exc}",
        )

    logger.info(
        "KB reloaded successfully: version=%s checksum=%s files=%d",
        kb_data.version,
        kb_data.checksum[:16],
        len(kb_data.files_loaded),
    )

    return KBReloadResponse(
        status="success",
        kb_version=kb_data.version,
        checksum=kb_data.checksum,
        files_loaded=kb_data.files_loaded,
        message=(
            f"Knowledge base reloaded successfully. "
            f"{len(kb_data.files_loaded)} files loaded."
        ),
    )
