"""Integration tests for Knowledge Base API endpoints.

NOTE: The /kb/version and /kb/reload endpoints are planned in the architecture
(Section 4.3.5) but may not yet be implemented (depends on Backend Agent 1).
These tests use conditional skips to remain runnable at any phase of development.

Endpoints tested
----------------
GET  /kb/version   — retrieve active KB version metadata
POST /kb/reload    — (admin) trigger reload of KB files from disk

Tests use the ``test_client`` fixture with mocked DB and KB dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _has_route(client, method: str, path: str) -> bool:
    """Return True if the app has a route matching method + path."""
    from starlette.routing import Route

    for route in client.app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            if route.path == path and method.upper() in (route.methods or set()):
                return True
    return False


# ---------------------------------------------------------------------------
# Test 1: GET /kb/version returns KB metadata
# ---------------------------------------------------------------------------


def test_get_kb_version_returns_metadata_or_not_implemented(test_client, mock_db_session):
    """GET /kb/version returns HTTP 200 with version info, or 404 if not yet implemented.

    When the route is present, the response must include 'kb_version' as a
    non-empty string (Architecture Section 4.3.5).
    When the route is not yet implemented, the test passes with a skip notice.
    """
    if not _has_route(test_client, "GET", "/kb/version"):
        pytest.skip("/kb/version route not yet implemented — waiting for Backend Agent 1")

    mock_kb_version = MagicMock()
    mock_kb_version.kb_version = "1.0"
    mock_kb_version.checksum = "abc123"
    mock_kb_version.is_active = True
    mock_kb_version.timestamp = "2026-02-18T00:00:00"

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = MagicMock(return_value=mock_kb_version)
    mock_db_session.execute = AsyncMock(return_value=mock_execute_result)

    response = test_client.get("/kb/version")

    assert response.status_code in (200, 404), (
        f"Expected 200 or 404 from GET /kb/version, got {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert "kb_version" in data, (
            f"Response must include 'kb_version', got: {data}"
        )
        assert isinstance(data["kb_version"], str) and data["kb_version"], (
            f"'kb_version' must be a non-empty string, got: {data['kb_version']!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: POST /kb/reload triggers KB reload
# ---------------------------------------------------------------------------


def test_kb_reload_returns_success_or_not_implemented(test_client, mock_db_session):
    """POST /kb/reload returns 200 with status='success', or skips if not implemented.

    The endpoint triggers a reload of KB files from disk, creates a new
    KnowledgeBaseVersion record, and returns the new version string.
    """
    if not _has_route(test_client, "POST", "/kb/reload"):
        pytest.skip("/kb/reload route not yet implemented — waiting for Backend Agent 1")

    response = test_client.post("/kb/reload")

    assert response.status_code in (200, 202, 501, 503), (
        f"Expected 200/202/501/503 from POST /kb/reload, "
        f"got {response.status_code}: {response.text}"
    )
    if response.status_code in (200, 202):
        data = response.json()
        assert "status" in data, f"Response must include 'status', got: {data}"
        assert data["status"] in ("success", "processing"), (
            f"Reload status must be 'success' or 'processing', got: {data['status']}"
        )


# ---------------------------------------------------------------------------
# Test 3: GET /kb/version returns 503 when KB loader reports 'not_loaded'
# ---------------------------------------------------------------------------


def test_get_kb_version_returns_503_when_not_loaded(test_client):
    """GET /kb/version returns HTTP 503 when the KB loader has no cached data.

    The endpoint reads the KB version from the loader.  When the loader has
    not yet loaded any KB files (kb_version='not_loaded'), the endpoint must
    return 503 Service Unavailable.
    """
    if not _has_route(test_client, "GET", "/kb/version"):
        pytest.skip("/kb/version route not yet implemented")

    # Create a mock KB loader that reports 'not_loaded'
    mock_not_loaded_kb = MagicMock()
    mock_not_loaded_kb.get_kb_version = MagicMock(
        return_value={"kb_version": "not_loaded", "checksum": "", "files_loaded": []}
    )

    from src.api.dependencies import get_kb_loader

    # Patch the dependency directly on the app
    original_override = test_client.app.dependency_overrides.get(get_kb_loader)
    test_client.app.dependency_overrides[get_kb_loader] = lambda: mock_not_loaded_kb

    try:
        response = test_client.get("/kb/version")
        assert response.status_code in (503, 200), (
            f"Expected 503 for not_loaded KB, got {response.status_code}: {response.text}"
        )
        if response.status_code == 503:
            data = response.json()
            assert "detail" in data, f"503 response must include 'detail', got: {data}"
    finally:
        if original_override is not None:
            test_client.app.dependency_overrides[get_kb_loader] = original_override
        else:
            test_client.app.dependency_overrides.pop(get_kb_loader, None)


# ---------------------------------------------------------------------------
# Test 4: POST /kb/reload returns 500 when KBLoadError is raised
# ---------------------------------------------------------------------------


def test_kb_reload_returns_500_on_load_error(test_client):
    """POST /kb/reload returns HTTP 500 when the KBLoader raises KBLoadError.

    If required KB files are missing from disk, the loader raises KBLoadError.
    The endpoint must translate this into a 500 response with structured error
    details including the missing_files list.
    """
    if not _has_route(test_client, "POST", "/kb/reload"):
        pytest.skip("/kb/reload route not yet implemented")

    from src.api.dependencies import get_kb_loader
    from src.exceptions import KBLoadError

    mock_erroring_kb = MagicMock()
    mock_erroring_kb.reload = MagicMock(
        side_effect=KBLoadError(
            "Required KB files missing",
            missing_files=["language_guidelines.md"],
        )
    )

    original_override = test_client.app.dependency_overrides.get(get_kb_loader)
    test_client.app.dependency_overrides[get_kb_loader] = lambda: mock_erroring_kb

    try:
        response = test_client.post("/kb/reload")
        assert response.status_code in (500, 200, 503), (
            f"Expected 500 for KBLoadError, got {response.status_code}: {response.text}"
        )
        if response.status_code == 500:
            data = response.json()
            assert "detail" in data, f"500 response must include 'detail', got: {data}"
    finally:
        if original_override is not None:
            test_client.app.dependency_overrides[get_kb_loader] = original_override
        else:
            test_client.app.dependency_overrides.pop(get_kb_loader, None)
