"""Unit tests for helper functions in src/api/lessons.py.

These helpers are pure functions or lightweight async helpers that do not require
the full HTTP stack.  Testing them directly maximises coverage of the lessons module
without the complexity of mocking the full generation pipeline.

Functions tested:
- _parse_json_field: JSON list parsing from text column values
- _convert_internal_report_to_schema: DataClass → Pydantic conversion
- _status_to_percentage: status string → completion integer
- _status_to_message: status string → human-readable message
"""

from __future__ import annotations

import pytest

from src.api.lessons import (
    _convert_internal_report_to_schema,
    _parse_json_field,
    _status_to_message,
    _status_to_percentage,
)
from src.services.validator import CheckResult
from src.services.validator import ValidationReport as InternalValidationReport


# ---------------------------------------------------------------------------
# _parse_json_field
# ---------------------------------------------------------------------------


def test_parse_json_field_returns_list_for_valid_json():
    """_parse_json_field returns a list for a valid JSON list string.

    DB text columns store prerequisites/exclusions as JSON arrays.
    The function must deserialise them into Python lists.
    """
    result = _parse_json_field('[1, 2, 3]')

    assert result == [1, 2, 3], f"Expected [1, 2, 3], got {result}"
    assert isinstance(result, list)


def test_parse_json_field_returns_empty_for_none():
    """_parse_json_field returns [] when given None.

    Optional text columns may be NULL in the DB; the helper must
    handle None without raising AttributeError.
    """
    result = _parse_json_field(None)
    assert result == [], f"Expected [], got {result}"


def test_parse_json_field_returns_empty_for_empty_string():
    """_parse_json_field returns [] for an empty string value.

    An empty string column value should behave the same as NULL.
    """
    result = _parse_json_field("")
    assert result == [], f"Expected [], got {result}"


def test_parse_json_field_returns_empty_for_invalid_json():
    """_parse_json_field returns [] silently for malformed JSON.

    The function must not propagate JSONDecodeError to callers.
    """
    result = _parse_json_field("{not: valid json}")
    assert result == [], f"Expected [], got {result}"


def test_parse_json_field_returns_empty_for_non_list_json():
    """_parse_json_field returns [] when the JSON parses to a non-list type.

    The column is expected to hold a JSON array.  A JSON object or scalar
    must be rejected and return the safe default of [].
    """
    result = _parse_json_field('{"key": "value"}')
    assert result == [], (
        f"Non-list JSON must return [], got {result}"
    )


def test_parse_json_field_returns_string_items_as_list():
    """_parse_json_field returns a list of strings for a JSON string array."""
    result = _parse_json_field('["climbers", "creepers"]')
    assert result == ["climbers", "creepers"], f"Expected string list, got {result}"


# ---------------------------------------------------------------------------
# _convert_internal_report_to_schema
# ---------------------------------------------------------------------------


def test_convert_internal_report_all_passed():
    """_convert_internal_report_to_schema converts an all-passed report correctly.

    A ValidationReport with all 'passed' checks must produce a Pydantic schema
    with passed=True, no errors, and the same number of checks.
    """
    internal = InternalValidationReport()
    internal.add_check(CheckResult(name="language_ceiling", status="passed"))
    internal.add_check(CheckResult(name="blooms_distribution", status="passed"))
    internal.compute_score()

    schema = _convert_internal_report_to_schema(internal, grade="3")

    assert schema.passed is True, f"All-passed report must have passed=True"
    assert len(schema.checks) == 2, f"Expected 2 checks in schema, got {len(schema.checks)}"
    assert schema.errors == [], f"All-passed report must have no errors, got {schema.errors}"
    assert schema.overall_score == 1.0, (
        f"All-passed overall_score must be 1.0, got {schema.overall_score}"
    )


def test_convert_internal_report_with_failed_check():
    """_convert_internal_report_to_schema converts a report with a failure correctly.

    A ValidationReport with one 'failed' check must set passed=False and add
    the failure message to the errors list.
    """
    internal = InternalValidationReport()
    internal.add_check(CheckResult(
        name="language_ceiling",
        status="failed",
        message="3 sentences exceed max length",
    ))
    internal.compute_score()

    schema = _convert_internal_report_to_schema(internal, grade="3")

    assert schema.passed is False, f"Report with failure must have passed=False"
    assert len(schema.errors) == 1, (
        f"Expected 1 error in schema, got {len(schema.errors)}: {schema.errors}"
    )
    # Check that grade is propagated to the check
    assert schema.checks[0].grade == "3", (
        f"Grade must be passed through to check, got {schema.checks[0].grade}"
    )


def test_convert_internal_report_with_warning_check():
    """_convert_internal_report_to_schema maps 'warning' checks to passed+warnings.

    Architecture Section 4.3.3: soft-check warnings must NOT set passed=False.
    The check is mapped to 'passed' status in the schema but added to warnings.
    """
    internal = InternalValidationReport()
    internal.add_check(CheckResult(
        name="definition_alignment",
        status="warning",
        message="Some KB concepts not found",
    ))
    internal.compute_score()

    schema = _convert_internal_report_to_schema(internal, grade="3")

    assert schema.passed is True, (
        "Warning-only report must still have passed=True"
    )
    assert len(schema.warnings) == 1, (
        f"Expected 1 warning in schema, got {len(schema.warnings)}"
    )
    assert len(schema.errors) == 0, (
        f"Warnings must not add to errors list"
    )
    # The check itself maps to 'passed' in the schema (not 'warning')
    assert schema.checks[0].status == "passed", (
        f"Warning check must map to 'passed' in Pydantic schema, got {schema.checks[0].status}"
    )


# ---------------------------------------------------------------------------
# _status_to_percentage
# ---------------------------------------------------------------------------


def test_status_to_percentage_maps_all_statuses():
    """_status_to_percentage returns the correct integer for each known status.

    The frontend uses these percentages for a progress bar.  The mapping must
    be exact: pending=0, processing=50, completed=100, failed=100.
    """
    assert _status_to_percentage("pending") == 0
    assert _status_to_percentage("processing") == 50
    assert _status_to_percentage("completed") == 100
    assert _status_to_percentage("failed") == 100


def test_status_to_percentage_returns_zero_for_unknown():
    """_status_to_percentage returns 0 for unrecognised status strings.

    Unknown statuses must not raise — they return the safe default of 0.
    """
    assert _status_to_percentage("unknown_status") == 0


# ---------------------------------------------------------------------------
# _status_to_message
# ---------------------------------------------------------------------------


def test_status_to_message_maps_all_statuses():
    """_status_to_message returns a non-empty string for each known status.

    The message is shown to frontend clients when they poll for status.
    All known statuses must have a non-empty human-readable message.
    """
    for status in ("pending", "processing", "completed", "failed"):
        msg = _status_to_message(status)
        assert isinstance(msg, str) and len(msg) > 0, (
            f"Expected non-empty message for status='{status}', got {msg!r}"
        )


def test_status_to_message_returns_string_for_unknown():
    """_status_to_message returns a non-None value for unknown status strings."""
    result = _status_to_message("zombie_state")
    assert result is not None, "Must not return None for unknown status"


# ---------------------------------------------------------------------------
# _get_active_kb_version (async)
# ---------------------------------------------------------------------------


async def test_get_active_kb_version_returns_none_when_not_found():
    """_get_active_kb_version returns None when no active KB version in DB.

    The helper is called during lesson generation to attach a KB version ID
    to the request.  When no active version exists it must return None (the
    caller uses a fallback ID of 1 in that case).
    """
    from unittest.mock import AsyncMock, MagicMock
    from src.api.lessons import _get_active_kb_version

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await _get_active_kb_version(mock_db)

    assert result is None, (
        f"Expected None when no active KB version, got {result}"
    )


async def test_get_active_kb_version_returns_kb_version_when_found():
    """_get_active_kb_version returns the KnowledgeBaseVersion when one is active.

    When an active KB version exists in the DB, the helper must return it
    so its ID can be attached to the GenerationRequest record.
    """
    from unittest.mock import AsyncMock, MagicMock
    from src.api.lessons import _get_active_kb_version

    mock_kb_version = MagicMock()
    mock_kb_version.id = 1
    mock_kb_version.kb_version = "1.0"
    mock_kb_version.is_active = True

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_kb_version)
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await _get_active_kb_version(mock_db)

    assert result is mock_kb_version, (
        f"Expected the mock KB version object, got {result}"
    )


# ---------------------------------------------------------------------------
# _write_audit_log (async)
# ---------------------------------------------------------------------------


async def test_write_audit_log_adds_to_db():
    """_write_audit_log adds an AuditLog entry to the DB session.

    The function must call db.add() exactly once with an AuditLog object.
    It must not raise even if called with various event types.
    """
    import uuid
    from unittest.mock import AsyncMock, MagicMock
    from src.api.lessons import _write_audit_log

    mock_db = AsyncMock()
    mock_db.add = MagicMock(return_value=None)

    request_id = uuid.uuid4()
    await _write_audit_log(
        mock_db,
        request_id=request_id,
        event_type="lesson_generated",
        event_details={"topic_id": 42},
        severity="info",
    )

    mock_db.add.assert_called_once(), "db.add must be called once with the audit log entry"


async def test_write_audit_log_handles_db_exception_gracefully():
    """_write_audit_log does not propagate exceptions from db.add.

    Audit log failures must never break the main generation pipeline.
    The function must silently swallow any exception from db.add.
    """
    import uuid
    from unittest.mock import MagicMock
    from src.api.lessons import _write_audit_log

    mock_db = MagicMock()
    mock_db.add = MagicMock(side_effect=RuntimeError("DB write failed"))

    # Must not raise
    try:
        await _write_audit_log(
            mock_db,
            request_id=uuid.uuid4(),
            event_type="test",
            event_details={},
        )
    except Exception as exc:
        pytest.fail(f"_write_audit_log must not propagate exceptions, got: {exc}")
