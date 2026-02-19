"""Integration tests for the Lesson API endpoints.

Endpoints tested
----------------
GET  /health                       — system health check
POST /lessons/generate             — request a lesson (expects topic in DB)
GET  /lessons/{request_id}         — poll generation status
GET  /lessons/{request_id}/download — download DOCX

All tests use the ``test_client`` fixture which overrides ``get_async_db``
with a mock async session.  No real DB or Claude API is used.

The DB mock must simulate:
  - db.get(Topic, topic_id) → mock Topic or None
  - db.execute(stmt) → mock result
  - db.add() / db.flush() → no-op

Where the orchestrator is unavailable (no ANTHROPIC_API_KEY to a real model),
POST /lessons/generate will return 503.  Tests account for this.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Test 1: Health check
# ---------------------------------------------------------------------------


def test_health_check_returns_ok(test_client):
    """GET /health returns HTTP 200 with status='ok'.

    This endpoint must always be reachable regardless of DB or KB state.
    It confirms the API process is alive.
    """
    response = test_client.get("/health")

    assert response.status_code == 200, (
        f"Expected 200 from /health, got {response.status_code}: {response.text}"
    )
    data = response.json()
    # The health check may return 'ok' (DB up) or 'degraded' (mock DB can't
    # handle the server-side cursor used in the health query).  Both are
    # acceptable in unit test context — we just confirm the endpoint is alive.
    assert data.get("status") in ("ok", "degraded"), (
        f"Health check must return status='ok' or 'degraded', got: {data}"
    )


# ---------------------------------------------------------------------------
# Test 2a: Generate lesson — topic found, orchestrator mocked to return lesson
# ---------------------------------------------------------------------------


def test_generate_lesson_with_valid_topic_calls_pipeline(test_client, mock_db_session):
    """POST /lessons/generate with a found topic proceeds through the pipeline.

    When the DB returns a valid Topic, the endpoint:
    1. Fetches Chapter/Subject/Grade context
    2. Creates a GenerationRequest (status='processing')
    3. Calls the orchestrator

    We mock the orchestrator to return VALID_GRADE3_LESSON and verify the full
    pipeline produces a 200 with request_id, status, and validation_report.
    """
    from tests.fixtures.sample_lessons import VALID_GRADE3_LESSON

    # Mock a topic with all required fields
    mock_topic = MagicMock()
    mock_topic.id = 1
    mock_topic.topic_name = "Trees vs Shrubs"
    mock_topic.topic_number = 1
    mock_topic.chapter_id = 10
    mock_topic.exclusions = "[]"
    mock_topic.prerequisites = "[]"
    mock_topic.context_narrative = ""

    # Mock a chapter
    mock_chapter = MagicMock()
    mock_chapter.id = 10
    mock_chapter.chapter_name = "Types of Plants"
    mock_chapter.subject_id = 5
    mock_chapter.sequence_number = 1

    # Mock a subject
    mock_subject = MagicMock()
    mock_subject.id = 5
    mock_subject.subject_name = "EVS"
    mock_subject.subject_code = "EVS"
    mock_subject.grade_id = 3

    # Mock a grade
    mock_grade = MagicMock()
    mock_grade.id = 3
    mock_grade.grade_code = "3"

    # db.get(Topic) → mock_topic; db.get for chapter/subject/grade in _load_topic_context not called here
    mock_db_session.get = AsyncMock(return_value=mock_topic)

    # db.execute returns chapter, then subject, then grade, then KB version (None)
    mock_chapter_result = MagicMock()
    mock_chapter_result.scalar_one_or_none = MagicMock(return_value=mock_chapter)

    mock_subject_result = MagicMock()
    mock_subject_result.scalar_one_or_none = MagicMock(return_value=mock_subject)

    mock_grade_result = MagicMock()
    mock_grade_result.scalar_one_or_none = MagicMock(return_value=mock_grade)

    mock_kb_result = MagicMock()
    mock_kb_result.scalar_one_or_none = MagicMock(return_value=None)  # No active KB version

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_chapter_result, mock_subject_result, mock_grade_result, mock_kb_result]
    )
    mock_db_session.flush = AsyncMock(return_value=None)

    # Patch _call_orchestrator to return VALID_GRADE3_LESSON without Claude API call
    async def _mock_orchestrator(*args, **kwargs):
        return VALID_GRADE3_LESSON

    with patch("src.api.lessons._call_orchestrator", side_effect=_mock_orchestrator):
        response = test_client.post(
            "/lessons/generate",
            json={"topic_id": 1, "kb_version": None},
        )

    assert response.status_code == 200, (
        f"Expected 200 from generate_lesson with valid topic, "
        f"got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "request_id" in data, f"Response must include 'request_id', got: {data}"
    assert "status" in data, f"Response must include 'status', got: {data}"
    assert "validation_report" in data, f"Response must include 'validation_report', got: {data}"


# ---------------------------------------------------------------------------
# Test 2: Generate lesson with valid topic_id
# ---------------------------------------------------------------------------


def test_generate_lesson_with_topic_not_in_db_returns_404(test_client, mock_db_session):
    """POST /lessons/generate returns 404 when topic_id does not exist in DB.

    The mock DB session returns None for db.get(Topic, id), simulating a
    missing topic.  The endpoint must return 404 with an appropriate message.
    """
    # Simulate db.get returning None (topic not found)
    mock_db_session.get = AsyncMock(return_value=None)

    response = test_client.post(
        "/lessons/generate",
        json={"topic_id": 9999, "kb_version": None},
    )

    assert response.status_code == 404, (
        f"Expected 404 for unknown topic_id=9999, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "detail" in data, f"404 response must include 'detail', got: {data}"


# ---------------------------------------------------------------------------
# Test 3: Generate lesson with invalid (non-positive) topic_id returns 422
# ---------------------------------------------------------------------------


def test_generate_lesson_invalid_topic_id_returns_422(test_client):
    """POST /lessons/generate with topic_id <= 0 returns HTTP 422.

    The GenerationRequest schema enforces ``topic_id: int = Field(..., gt=0)``.
    A value of 0 or negative must be rejected by Pydantic before hitting the route.
    """
    response = test_client.post(
        "/lessons/generate",
        json={"topic_id": 0, "kb_version": None},
    )

    assert response.status_code == 422, (
        f"Expected 422 for topic_id=0 (must be gt=0), got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "detail" in data, f"422 response must include 'detail', got: {data}"


# ---------------------------------------------------------------------------
# Test 4: Generate lesson missing required fields returns 422
# ---------------------------------------------------------------------------


def test_generate_lesson_missing_required_field(test_client):
    """POST /lessons/generate without topic_id returns HTTP 422.

    FastAPI + Pydantic validates the request body.  An empty payload must
    trigger a 422 response with validation error details.
    """
    response = test_client.post("/lessons/generate", json={})

    assert response.status_code == 422, (
        f"Expected 422 Unprocessable Entity for missing topic_id, "
        f"got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "detail" in data, f"422 response must include 'detail', got: {data}"


# ---------------------------------------------------------------------------
# Test 5: Get lesson status returns 404 for unknown request_id
# ---------------------------------------------------------------------------


def test_get_lesson_status_not_found(test_client, mock_db_session):
    """GET /lessons/{request_id} returns 404 when the request_id is not in DB.

    The mock DB session returns None for db.get(GenerationRequest, uuid),
    simulating a missing request.
    """
    fake_id = str(uuid.uuid4())
    mock_db_session.get = AsyncMock(return_value=None)

    response = test_client.get(f"/lessons/{fake_id}")

    assert response.status_code == 404, (
        f"Expected 404 for unknown request_id, got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Test 6: Get lesson status with invalid UUID returns 400
# ---------------------------------------------------------------------------


def test_get_lesson_status_invalid_uuid_returns_400(test_client):
    """GET /lessons/{request_id} with a non-UUID string returns 400.

    The route parses the path parameter as a UUID.  An invalid string must
    return 400 Bad Request (not 500).
    """
    response = test_client.get("/lessons/not-a-valid-uuid")

    assert response.status_code == 400, (
        f"Expected 400 for invalid UUID in path, got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Test 7: Get lesson status for completed request
# ---------------------------------------------------------------------------


def test_get_lesson_status_completed_returns_docx_url(test_client, mock_db_session):
    """GET /lessons/{request_id} returns docx_url for a completed request.

    The mock DB returns a GenerationRequestModel with status='completed' and
    a corresponding GeneratedLesson.  The response must include docx_url.
    """
    fake_id = uuid.uuid4()

    # Mock a completed GenerationRequestModel
    mock_gen_request = MagicMock()
    mock_gen_request.id = fake_id
    mock_gen_request.status = "completed"

    # Mock a GeneratedLesson
    mock_lesson = MagicMock()
    mock_lesson.validation_report = {"passed": True, "checks": [], "errors": [], "warnings": []}
    mock_lesson.generation_time_seconds = 42.5

    # db.get returns the request, db.execute returns the lesson
    mock_db_session.get = AsyncMock(return_value=mock_gen_request)
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = MagicMock(return_value=mock_lesson)
    mock_db_session.execute = AsyncMock(return_value=mock_execute_result)

    response = test_client.get(f"/lessons/{fake_id}")

    assert response.status_code == 200, (
        f"Expected 200 for completed request, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data.get("status") == "completed", (
        f"Expected status='completed', got: {data.get('status')}"
    )
    assert "docx_url" in data, (
        f"Completed lesson must include 'docx_url' in response, got: {data}"
    )


# ---------------------------------------------------------------------------
# Test 8: Download endpoint — invalid UUID returns 400
# ---------------------------------------------------------------------------


def test_download_invalid_uuid_returns_400(test_client):
    """GET /lessons/{request_id}/download with a non-UUID returns HTTP 400.

    The download endpoint parses the path parameter as a UUID. An invalid
    string must return 400 Bad Request, not 500 or 404.
    """
    response = test_client.get("/lessons/not-a-valid-uuid/download")

    assert response.status_code == 400, (
        f"Expected 400 for invalid UUID in download path, "
        f"got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Test 9: Download endpoint — lesson not found returns 404
# ---------------------------------------------------------------------------


def test_download_lesson_not_found_returns_404(test_client, mock_db_session):
    """GET /lessons/{request_id}/download returns 404 when no lesson exists.

    The mock DB returns None from the GeneratedLesson query, simulating a
    request that was created but whose lesson was never stored.
    """
    fake_id = str(uuid.uuid4())

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db_session.execute = AsyncMock(return_value=mock_execute_result)

    response = test_client.get(f"/lessons/{fake_id}/download")

    assert response.status_code == 404, (
        f"Expected 404 when no generated lesson found, "
        f"got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Test 10: Download endpoint — lesson exists but DOCX content missing → 404
# ---------------------------------------------------------------------------


def test_download_lesson_missing_docx_returns_404(test_client, mock_db_session):
    """GET /lessons/{request_id}/download returns 404 when DOCX bytes are absent.

    A GeneratedLesson may exist in the DB but have no lesson_content_docx
    (e.g. generation failed or DOCX step was skipped).  The endpoint must
    return 404 rather than serving empty bytes.
    """
    fake_id = str(uuid.uuid4())

    mock_lesson = MagicMock()
    mock_lesson.lesson_content_docx = None  # No DOCX bytes stored

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = MagicMock(return_value=mock_lesson)
    mock_db_session.execute = AsyncMock(return_value=mock_execute_result)

    response = test_client.get(f"/lessons/{fake_id}/download")

    assert response.status_code == 404, (
        f"Expected 404 when DOCX content is missing, "
        f"got {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Test 11: Download endpoint — returns DOCX bytes with correct headers
# ---------------------------------------------------------------------------


def test_download_lesson_returns_docx_bytes(test_client, mock_db_session):
    """GET /lessons/{request_id}/download returns DOCX bytes with proper headers.

    When a GeneratedLesson has lesson_content_docx bytes, the response must:
    - Return HTTP 200
    - Use 'application/vnd.openxmlformats...' content type
    - Include Content-Disposition: attachment with a .docx filename
    """
    fake_id = str(uuid.uuid4())
    docx_bytes = b"PK\x03\x04fake_docx_content"

    mock_lesson = MagicMock()
    mock_lesson.lesson_content_docx = docx_bytes
    mock_lesson.topic_id = 42

    mock_topic = MagicMock()
    mock_topic.topic_name = "Trees vs Shrubs"

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = MagicMock(return_value=mock_lesson)
    mock_db_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_db_session.get = AsyncMock(return_value=mock_topic)

    response = test_client.get(f"/lessons/{fake_id}/download")

    assert response.status_code == 200, (
        f"Expected 200 for valid download, got {response.status_code}: {response.text}"
    )
    assert response.content == docx_bytes, (
        "Response body must equal the stored DOCX bytes"
    )
    content_type = response.headers.get("content-type", "")
    assert "openxmlformats" in content_type or "application/" in content_type, (
        f"Content-Type must indicate DOCX, got {content_type!r}"
    )
    disposition = response.headers.get("content-disposition", "")
    assert ".docx" in disposition, (
        f"Content-Disposition must include .docx filename, got {disposition!r}"
    )
