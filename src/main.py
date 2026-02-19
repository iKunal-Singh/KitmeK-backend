"""KitmeK Lesson Generation API — FastAPI application entry point.

Architecture reference: Section 4.3.5 (API Gateway).

Features:
- Lifespan context manager: loads KB files on startup, disposes DB on shutdown
- Structured exception handlers for all domain exceptions
- Request/response logging middleware with request-ID tracing
- Enhanced /health endpoint: checks DB connectivity + KB version
- OpenAPI tags and descriptions for all routers
"""

from __future__ import annotations

import datetime
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.exceptions import (
    DatabaseConnectionError,
    KBLoadError,
    LessonGenerationError,
    TopicNotFoundError,
)
from src.exceptions import ValidationError as DomainValidationError

# ---------------------------------------------------------------------------
# Logging setup  (must happen before routers are imported)
# ---------------------------------------------------------------------------

_settings = get_settings()
logging.basicConfig(
    level=getattr(logging, _settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router and service imports
# ---------------------------------------------------------------------------

from src.api import kb as _kb_module  # noqa: E402
from src.api import lessons as _lessons_module  # noqa: E402
from src.api import topics as _topics_module  # noqa: E402
from src.database import check_db_connection, dispose_engine  # noqa: E402
from src.services.kb_loader import KBLoader  # noqa: E402

# Register all ORM models with the declarative base (required for metadata)
import src.models  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    Startup sequence:
    1. Load KB files from disk; raise if required files are absent.
    2. Store the loaded KBLoader on ``app.state.kb_loader`` for DI.
    3. Probe DB connectivity and log the result (non-fatal at startup).

    Shutdown:
    1. Dispose the SQLAlchemy connection pool gracefully.
    """
    # --- Startup -----------------------------------------------------------
    logger.info(
        "KitmeK Lesson Generation API — starting up (v%s)", _settings.app_version
    )

    kb_loader = KBLoader(kb_path=_settings.kb_path)
    try:
        kb_data = kb_loader.load()
        app.state.kb_loader = kb_loader
        logger.info(
            "KB loaded: version=%s  files=%d  checksum=%s…",
            kb_data.version,
            len(kb_data.files_loaded),
            kb_data.checksum[:16],
        )
    except KBLoadError as exc:
        logger.critical("FATAL — required KB files missing: %s", exc.missing_files)
        app.state.kb_loader = None
        raise RuntimeError(
            f"Cannot start: required KB files missing: {exc.missing_files}"
        ) from exc
    except Exception as exc:
        logger.critical("FATAL — unexpected KB load error: %s", exc)
        app.state.kb_loader = None
        raise RuntimeError(f"Cannot start: KB load error: {exc}") from exc

    db_health = await check_db_connection()
    if db_health["status"] == "ok":
        logger.info("Database: OK")
    else:
        logger.warning("Database: DEGRADED — %s", db_health.get("detail", "unknown"))

    logger.info("Startup complete — serving requests")
    yield

    # --- Shutdown ----------------------------------------------------------
    logger.info("KitmeK API — shutting down")
    try:
        await dispose_engine()
    except Exception as exc:
        logger.warning("Error during engine disposal: %s", exc)
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KitmeK Lesson Generation API",
    description=(
        "Real-time NCERT-aligned lesson generation for Indian primary school "
        "students (Grades K–5). Accepts a topic specification and generates a "
        "complete validated lesson (audio script + visual directions + quiz)."
    ),
    version=_settings.app_version,
    debug=_settings.debug,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "health",
            "description": "System health and readiness checks.",
        },
        {
            "name": "lessons",
            "description": (
                "Lesson generation endpoints. POST to generate; GET to poll"
                " status or download the produced DOCX."
            ),
        },
        {
            "name": "topics",
            "description": (
                "Curriculum topic discovery. List and filter topics by grade,"
                " subject, and chapter."
            ),
        },
        {
            "name": "knowledge-base",
            "description": "KB version metadata and hot-reload (admin operations).",
        },
    ],
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response logging middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Any) -> Response:
    """Log every HTTP request with method, path, status, and duration.

    A short UUID-derived ``request_id`` is attached to each log line and
    returned as the ``X-Request-ID`` response header.
    """
    request_id = str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    logger.info("[%s] → %s %s", request_id, request.method, request.url.path)

    try:
        response: Response = await call_next(request)
    except Exception as exc:
        elapsed = (time.monotonic() - t0) * 1000
        logger.error(
            "[%s] ✗ %s %s — unhandled after %.1f ms: %s",
            request_id,
            request.method,
            request.url.path,
            elapsed,
            exc,
        )
        raise

    elapsed = (time.monotonic() - t0) * 1000
    logger.info(
        "[%s] ← %s %s — %d (%.1f ms)",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Structured exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(KBLoadError)
async def kb_load_error_handler(request: Request, exc: KBLoadError) -> JSONResponse:
    """503 for knowledge-base load failures."""
    logger.error("KBLoadError: %s  missing=%s", exc, exc.missing_files)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "knowledge_base_error",
            "message": str(exc),
            "missing_files": exc.missing_files,
        },
    )


@app.exception_handler(TopicNotFoundError)
async def topic_not_found_handler(
    request: Request, exc: TopicNotFoundError
) -> JSONResponse:
    """404 for missing topics."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "topic_not_found",
            "message": str(exc),
            "topic_id": exc.topic_id,
        },
    )


@app.exception_handler(LessonGenerationError)
async def lesson_generation_error_handler(
    request: Request, exc: LessonGenerationError
) -> JSONResponse:
    """500 for Claude API / orchestrator failures."""
    logger.error("LessonGenerationError attempt=%d: %s", exc.attempt, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "lesson_generation_failed",
            "message": str(exc),
            "attempt": exc.attempt,
        },
    )


@app.exception_handler(DomainValidationError)
async def validation_error_handler(
    request: Request, exc: DomainValidationError
) -> JSONResponse:
    """422 for lesson validation failures."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_failed",
            "message": str(exc),
            "validation_report": exc.validation_report,
        },
    )


@app.exception_handler(DatabaseConnectionError)
async def database_connection_error_handler(
    request: Request, exc: DatabaseConnectionError
) -> JSONResponse:
    """503 for database connectivity failures."""
    logger.error("DatabaseConnectionError: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "database_unavailable", "message": str(exc)},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Render FastAPI HTTPExceptions as structured JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )


# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------


@app.get("/", tags=["health"], summary="API root / service info")
async def root() -> dict[str, str]:
    """Return basic service metadata and navigation links."""
    return {
        "service": "KitmeK Lesson Generation API",
        "version": _settings.app_version,
        "documentation": "/docs",
        "health": "/health",
        "openapi": "/openapi.json",
    }


@app.get(
    "/health",
    tags=["health"],
    summary="Enhanced system health check",
    description=(
        "Probes database connectivity and reports the active knowledge-base version."
        " A ``status: ok`` response means all subsystems are healthy."
        " ``status: degraded`` means the API is responding but at least one"
        " dependency (DB or KB) is unavailable."
    ),
)
async def health_check(request: Request) -> dict[str, Any]:
    """Return current system health including DB + KB status.

    Args:
        request: Used to access ``app.state.kb_loader``.

    Returns:
        Health summary dict with ``status``, ``database``, and ``knowledge_base``.
    """
    db_health = await check_db_connection()

    kb_loader: KBLoader | None = getattr(request.app.state, "kb_loader", None)
    if kb_loader is not None and kb_loader.is_loaded():
        meta = kb_loader.get_kb_version()
        kb_health: dict[str, Any] = {
            "status": "ok",
            "version": meta.get("kb_version", "unknown"),
            "checksum_prefix": meta.get("checksum", "")[:16] + "…",
            "files_loaded": len(meta.get("files_loaded", [])),
        }
    else:
        kb_health = {"status": "not_loaded"}

    overall = (
        "ok"
        if db_health["status"] == "ok" and kb_health["status"] == "ok"
        else "degraded"
    )

    return {
        "status": overall,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "version": _settings.app_version,
        "database": db_health,
        "knowledge_base": kb_health,
    }


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(_lessons_module.router)
app.include_router(_topics_module.router)
app.include_router(_kb_module.router)


# ---------------------------------------------------------------------------
# Development entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=_settings.log_level.lower(),
    )
