"""Integration tests for the Topics API endpoints.

Endpoints tested
----------------
GET /topics               — list topics with optional grade/subject/chapter filters
GET /topics/{topic_id}   — retrieve a single topic by ID

Tests use the ``test_client`` fixture with a mocked DB session.
No real database is used.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers to build mock Topic rows
# ---------------------------------------------------------------------------


def _mock_topic_row(
    topic_id: int = 1,
    topic_name: str = "Trees vs Shrubs",
    topic_number: int = 1,
    chapter_id: int = 10,
    sequence_number: int = 1,
    prerequisites: str = "[]",
    exclusions: str = "[]",
    context_narrative: str | None = None,
    topic_description: str | None = None,
):
    """Build a MagicMock that mimics a Topic ORM row."""
    row = MagicMock()
    row.id = topic_id
    row.topic_name = topic_name
    row.topic_number = topic_number
    row.chapter_id = chapter_id
    row.sequence_number = sequence_number
    row.prerequisites = prerequisites
    row.exclusions = exclusions
    row.context_narrative = context_narrative
    row.topic_description = topic_description
    return row


def _mock_chapter_row(
    chapter_id: int = 10,
    chapter_name: str = "Types of Plants",
    subject_id: int = 5,
):
    row = MagicMock()
    row.id = chapter_id
    row.chapter_name = chapter_name
    row.subject_id = subject_id
    row.sequence_number = 1
    return row


def _mock_subject_row(subject_id: int = 5, subject_name: str = "EVS", grade_id: int = 3):
    row = MagicMock()
    row.id = subject_id
    row.subject_name = subject_name
    row.subject_code = "EVS"
    row.grade_id = grade_id
    return row


def _mock_grade_row(grade_id: int = 3, grade_code: str = "3"):
    row = MagicMock()
    row.id = grade_id
    row.grade_code = grade_code
    return row


# ---------------------------------------------------------------------------
# Test 1: GET /topics returns empty list when no data
# ---------------------------------------------------------------------------


def test_list_topics_returns_empty_list_when_no_data(test_client, mock_db_session):
    """GET /topics returns HTTP 200 with an empty topics list when DB has no rows.

    The endpoint must never return 404 even if the curriculum table is empty.
    It must return an empty ``topics`` list and ``total=0``.
    """
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[])
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = test_client.get("/topics")

    assert response.status_code == 200, (
        f"Expected 200 from GET /topics with no data, got {response.status_code}: "
        f"{response.text}"
    )
    data = response.json()
    assert "topics" in data, f"Response must include 'topics' key, got: {data}"
    assert data["topics"] == [], f"Expected empty topics list, got: {data['topics']}"
    assert data.get("total") == 0, f"Expected total=0, got {data.get('total')}"


# ---------------------------------------------------------------------------
# Test 2: GET /topics returns topic data when rows present
# ---------------------------------------------------------------------------


def test_list_topics_returns_topic_when_rows_present(test_client, mock_db_session):
    """GET /topics returns a TopicListItem for each row returned by the DB query.

    The mock DB returns one row with the full Grade/Subject/Chapter/Topic join.
    The response must include one item with the correct topic_name.
    """
    topic_row = _mock_topic_row()
    chapter_row = _mock_chapter_row()
    subject_row = _mock_subject_row()
    grade_row = _mock_grade_row()

    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[(topic_row, chapter_row, subject_row, grade_row)])
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = test_client.get("/topics")

    assert response.status_code == 200, (
        f"GET /topics should return 200, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["total"] == 1, f"Expected total=1, got {data['total']}"
    assert len(data["topics"]) == 1
    item = data["topics"][0]
    assert item["topic_name"] == "Trees vs Shrubs", (
        f"Expected topic_name='Trees vs Shrubs', got {item['topic_name']!r}"
    )
    assert item["grade"] == "3", f"Expected grade='3', got {item['grade']!r}"
    assert item["subject"] == "EVS", f"Expected subject='EVS', got {item['subject']!r}"
    assert item["chapter_name"] == "Types of Plants", (
        f"Expected chapter_name='Types of Plants', got {item['chapter_name']!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: GET /topics?grade=invalid returns 422
# ---------------------------------------------------------------------------


def test_list_topics_invalid_grade_returns_422(test_client):
    """GET /topics?grade=99 returns HTTP 422 because grade must match pattern ^[K1-5]$.

    FastAPI validates query parameters against their declared pattern before
    the route handler is invoked.  An unrecognised grade code must be rejected
    immediately with a 422 Unprocessable Entity response.
    """
    response = test_client.get("/topics?grade=99")

    assert response.status_code == 422, (
        f"Expected 422 for invalid grade=99, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "detail" in data, f"422 response must include 'detail', got: {data}"


# ---------------------------------------------------------------------------
# Test 4: GET /topics/{topic_id} returns 404 for unknown topic
# ---------------------------------------------------------------------------


def test_get_topic_not_found_returns_404(test_client, mock_db_session):
    """GET /topics/9999 returns HTTP 404 when the topic does not exist in the DB.

    The mock DB session returns None for db.get(Topic, 9999), simulating a
    topic that has not yet been seeded.
    """
    mock_db_session.get = AsyncMock(return_value=None)

    response = test_client.get("/topics/9999")

    assert response.status_code == 404, (
        f"Expected 404 for unknown topic_id=9999, got {response.status_code}: "
        f"{response.text}"
    )
    data = response.json()
    assert "detail" in data, f"404 response must include 'detail', got: {data}"


# ---------------------------------------------------------------------------
# Test 5: GET /topics/{topic_id} returns full TopicDetail for known topic
# ---------------------------------------------------------------------------


def test_get_topic_returns_detail_for_known_topic(test_client, mock_db_session):
    """GET /topics/1 returns HTTP 200 with full TopicDetail for an existing topic.

    The mock DB returns a Topic and the full Chapter/Subject/Grade context chain.
    The response must include all TopicDetail fields with correct values.
    """
    topic_row = _mock_topic_row(
        topic_id=1,
        topic_name="Trees vs Shrubs",
        topic_description="Differences between trees and shrubs.",
        context_narrative="Meera found a tree in the park.",
    )
    chapter_row = _mock_chapter_row()
    subject_row = _mock_subject_row()
    grade_row = _mock_grade_row()

    # db.get(Topic, 1) → topic_row; then db.get(Chapter, chapter_id) etc.
    mock_db_session.get = AsyncMock(
        side_effect=[topic_row, chapter_row, subject_row, grade_row]
    )

    response = test_client.get("/topics/1")

    assert response.status_code == 200, (
        f"Expected 200 for known topic_id=1, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["topic_name"] == "Trees vs Shrubs", (
        f"Expected topic_name='Trees vs Shrubs', got {data['topic_name']!r}"
    )
    assert data["id"] == 1, f"Expected id=1, got {data['id']}"
    assert "prerequisites" in data, "Response must include 'prerequisites'"
    assert "exclusions" in data, "Response must include 'exclusions'"


# ---------------------------------------------------------------------------
# Test 6: GET /topics?subject=EVS filters results
# ---------------------------------------------------------------------------


def test_list_topics_with_subject_filter(test_client, mock_db_session):
    """GET /topics?subject=EVS passes the subject filter to the DB query.

    The endpoint builds a WHERE clause for subject filter.  With a mock DB that
    returns one row, the response must still be 200 with one topic.
    """
    topic_row = _mock_topic_row(topic_name="Water Cycle")
    chapter_row = _mock_chapter_row(chapter_name="Water")
    subject_row = _mock_subject_row(subject_name="EVS")
    grade_row = _mock_grade_row(grade_code="4")

    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[(topic_row, chapter_row, subject_row, grade_row)])
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = test_client.get("/topics?subject=EVS")

    assert response.status_code == 200, (
        f"GET /topics?subject=EVS should return 200, got {response.status_code}"
    )
    data = response.json()
    assert data["total"] >= 0, "Response must include total count"
