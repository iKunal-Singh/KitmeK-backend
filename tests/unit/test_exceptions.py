"""Unit tests for custom exception classes (src/exceptions.py).

Tests verify that each exception class:
1. Stores its constructor arguments as instance attributes.
2. Inherits from the standard Exception hierarchy.
3. Has a useful string representation that includes the message.

No database or external services are used.
"""

from __future__ import annotations

import pytest

from src.exceptions import (
    DatabaseConnectionError,
    KBLoadError,
    LessonGenerationError,
    TopicNotFoundError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# KBLoadError
# ---------------------------------------------------------------------------


def test_kb_load_error_stores_message_and_missing_files():
    """KBLoadError stores the message and missing_files list as attributes.

    The orchestrator and KB loader raise this error when required KB markdown
    files cannot be found on disk.  Callers check exc.missing_files to surface
    the exact filenames in error responses.
    """
    exc = KBLoadError(
        "Required KB files missing",
        missing_files=["language_guidelines.md", "digital_interactions.md"],
    )

    assert isinstance(exc, Exception), "KBLoadError must inherit from Exception"
    assert str(exc) == "Required KB files missing", (
        f"str(exc) must equal the message, got {str(exc)!r}"
    )
    assert exc.missing_files == ["language_guidelines.md", "digital_interactions.md"], (
        f"missing_files not stored correctly: {exc.missing_files}"
    )


def test_kb_load_error_defaults_missing_files_to_empty_list():
    """KBLoadError.missing_files defaults to [] when not provided.

    Some callers may not know which specific files are absent.  The default
    prevents AttributeError in exception handlers that iterate exc.missing_files.
    """
    exc = KBLoadError("KB directory not found")

    assert exc.missing_files == [], (
        f"Default missing_files must be [], got {exc.missing_files}"
    )


# ---------------------------------------------------------------------------
# TopicNotFoundError
# ---------------------------------------------------------------------------


def test_topic_not_found_error_stores_topic_id():
    """TopicNotFoundError stores the integer topic_id as an attribute.

    The API layer raises this to distinguish a missing topic from a generic
    database error.  Callers log exc.topic_id in 404 responses.
    """
    exc = TopicNotFoundError(topic_id=42)

    assert isinstance(exc, Exception)
    assert exc.topic_id == 42, f"topic_id must be stored as 42, got {exc.topic_id}"
    assert "42" in str(exc), (
        f"str(exc) must mention the topic_id, got {str(exc)!r}"
    )


# ---------------------------------------------------------------------------
# LessonGenerationError
# ---------------------------------------------------------------------------


def test_lesson_generation_error_stores_attempt():
    """LessonGenerationError stores the attempt number as an attribute.

    After the orchestrator exhausts its retry budget, it raises this error
    with the final attempt count so callers can log how many retries occurred.
    """
    exc = LessonGenerationError("Claude API unavailable", attempt=3)

    assert isinstance(exc, Exception)
    assert exc.attempt == 3, f"attempt must be 3, got {exc.attempt}"
    assert "Claude API unavailable" in str(exc), (
        f"str(exc) must contain the message, got {str(exc)!r}"
    )


def test_lesson_generation_error_default_attempt_is_one():
    """LessonGenerationError.attempt defaults to 1 when not provided."""
    exc = LessonGenerationError("API key missing")

    assert exc.attempt == 1, (
        f"Default attempt should be 1, got {exc.attempt}"
    )


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------


def test_validation_error_stores_report():
    """ValidationError stores the full validation_report dict as an attribute.

    When the validation pipeline returns failures, the API layer wraps the
    report in this exception so it can be serialised into the 422 response.
    """
    report = {"passed": False, "checks": [], "errors": ["language_ceiling failed"]}
    exc = ValidationError("Lesson failed validation", validation_report=report)

    assert isinstance(exc, Exception)
    assert exc.validation_report == report, (
        f"validation_report not stored correctly: {exc.validation_report}"
    )
    assert "Lesson failed validation" in str(exc)


def test_validation_error_defaults_report_to_empty_dict():
    """ValidationError.validation_report defaults to {} when not supplied."""
    exc = ValidationError("Validation error")

    assert exc.validation_report == {}, (
        f"Default validation_report must be {{}}, got {exc.validation_report}"
    )


# ---------------------------------------------------------------------------
# DatabaseConnectionError
# ---------------------------------------------------------------------------


def test_database_connection_error_stores_message():
    """DatabaseConnectionError stores the DB connection detail as str(exc).

    The message typically comes from the underlying asyncpg driver and is
    surfaced in the /health endpoint to help operators diagnose DB issues.
    """
    msg = "Connection refused on port 5432"
    exc = DatabaseConnectionError(msg)

    assert isinstance(exc, Exception)
    assert str(exc) == msg, (
        f"str(exc) must equal the message, got {str(exc)!r}"
    )
