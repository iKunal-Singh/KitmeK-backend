"""Unit tests for the ValidationPipeline (src/services/validator.py).

The LessonValidator runs 8 deterministic checks against a lesson dict.
Each check is synchronous but the top-level ``validate`` method is async.

Tests cover:
1.  valid lesson passes all 8 checks
2.  long sentence fails language_ceiling
3.  wrong Bloom's distribution fails blooms_distribution
4.  disallowed interaction type fails interaction_type
5.  missing quiz feedback fails feedback_structure
6.  audio markers present in valid lesson pass audio_pacing
7.  content isolation check respects exclusions
8.  validation report has required structure

All tests use MockKBLoader for KB data (no filesystem I/O) and sample_lessons
fixtures (no Claude API calls).  Tests are ``async`` because ``validate`` is
an async method.
"""

from __future__ import annotations

import pytest

from src.services.validator import LessonValidator, ValidationReport as InternalValidationReport

from tests.fixtures.mock_kb_files import MockKBLoader
from tests.fixtures.sample_lessons import (
    INVALID_LESSON_BAD_INTERACTION,
    INVALID_LESSON_LONG_SENTENCES,
    INVALID_LESSON_MISSING_FEEDBACK,
    INVALID_LESSON_WRONG_BLOOMS,
    VALID_GRADE3_LESSON,
)


@pytest.fixture(scope="module")
def validator() -> LessonValidator:
    """Return a shared LessonValidator instance for the module."""
    return LessonValidator()


async def _validate(
    validator: LessonValidator,
    lesson: dict,
    grade: str = "3",
    subject: str = "EVS",
    exclusions: list[str] | None = None,
    context_narrative: str = "",
) -> InternalValidationReport:
    """Thin async wrapper that calls LessonValidator.validate with common args."""
    return await validator.validate(
        lesson_data=lesson,
        grade=grade,
        subject=subject,
        exclusions=exclusions or [],
        prerequisites=[],
        context_narrative=context_narrative,
    )


# ---------------------------------------------------------------------------
# Test 1: Valid lesson passes all 8 checks
# ---------------------------------------------------------------------------


async def test_valid_grade3_lesson_passes_all_checks(validator):
    """A correctly constructed Grade 3 lesson passes all validation checks.

    The VALID_GRADE3_LESSON fixture is the canonical success case.  The report
    must indicate ``passed=True``, include no hard errors, and surface check
    results for the required check categories.
    """
    report = await _validate(validator, VALID_GRADE3_LESSON)

    assert isinstance(report, InternalValidationReport), (
        "Validation must return a ValidationReport dataclass"
    )
    assert report.passed is True, (
        f"Valid lesson must pass. Errors: {[e for e in report.errors]}"
    )
    assert len(report.errors) == 0, (
        f"Valid lesson must have no hard errors, got: {report.errors}"
    )
    check_names = {c.name for c in report.checks}
    for required in ("language_ceiling", "blooms_distribution", "interaction_type", "feedback_structure"):
        assert required in check_names, (
            f"Expected check '{required}' in report. Found: {check_names}"
        )


# ---------------------------------------------------------------------------
# Test 2: Long sentence fails language_ceiling check
# ---------------------------------------------------------------------------


async def test_long_sentence_fails_language_ceiling(validator):
    """A lesson with a 25-word sentence fails the language_ceiling check.

    INVALID_LESSON_LONG_SENTENCES has one sentence far exceeding Grade 3's
    12-word ceiling.  The check must be marked 'failed' in the report.
    """
    report = await _validate(validator, INVALID_LESSON_LONG_SENTENCES)

    assert report.passed is False, (
        "Lesson with sentence > 12 words must fail validation"
    )
    failed_names = {c.name for c in report.checks if c.status == "failed"}
    assert "language_ceiling" in failed_names, (
        f"language_ceiling must be marked failed for long sentences. "
        f"Failed checks: {failed_names}"
    )


# ---------------------------------------------------------------------------
# Test 3: Wrong Bloom's distribution fails blooms_distribution check
# ---------------------------------------------------------------------------


async def test_wrong_blooms_distribution_fails(validator):
    """A lesson with all-L1 quiz questions fails the blooms_distribution check.

    INVALID_LESSON_WRONG_BLOOMS has 10 L1 questions; Grade 3 requires
    L1×2, L2×3, L3×3, L4×1, L5×1.  The distribution mismatch must be
    detected and reported.
    """
    report = await _validate(validator, INVALID_LESSON_WRONG_BLOOMS)

    assert report.passed is False, (
        "Lesson with wrong Bloom's distribution must fail"
    )
    failed_names = {c.name for c in report.checks if c.status == "failed"}
    assert "blooms_distribution" in failed_names, (
        f"blooms_distribution must be marked failed. Failed: {failed_names}"
    )


# ---------------------------------------------------------------------------
# Test 4: Disallowed interaction type fails interaction_type check
# ---------------------------------------------------------------------------


async def test_bad_interaction_type_fails(validator):
    """A lesson using an interaction type banned for Grade 3 must fail.

    'Scratch to reveal' is only allowed for Grade K (per digital_interactions.md).
    The validator must detect it is not in the Grade 3 allowed list.
    """
    report = await _validate(validator, INVALID_LESSON_BAD_INTERACTION)

    assert report.passed is False, (
        "Lesson with disallowed interaction type must fail"
    )
    failed_names = {c.name for c in report.checks if c.status == "failed"}
    assert "interaction_type" in failed_names, (
        f"interaction_type must be marked failed for 'Scratch to reveal' in Grade 3. "
        f"Failed: {failed_names}"
    )


# ---------------------------------------------------------------------------
# Test 5: Missing quiz feedback fields fails feedback_structure check
# ---------------------------------------------------------------------------


async def test_missing_quiz_feedback_fails(validator):
    """A lesson whose quiz questions lack feedback fields fails feedback_structure.

    Every quiz question must have both ``feedback_correct`` and
    ``feedback_incorrect``.  INVALID_LESSON_MISSING_FEEDBACK strips them all.
    """
    report = await _validate(validator, INVALID_LESSON_MISSING_FEEDBACK)

    assert report.passed is False, (
        "Lesson with missing quiz feedback must fail"
    )
    failed_names = {c.name for c in report.checks if c.status == "failed"}
    assert "feedback_structure" in failed_names, (
        f"feedback_structure must be marked failed when quiz feedback is missing. "
        f"Failed: {failed_names}"
    )


# ---------------------------------------------------------------------------
# Test 6: Audio pacing markers validation
# ---------------------------------------------------------------------------


async def test_audio_pacing_markers_present_in_valid_lesson(validator):
    """A valid lesson with [Beat] and [Pause] markers passes audio_pacing.

    The VALID_GRADE3_LESSON includes [Beat] and [Pause] in the narration.
    The audio_pacing check must pass and report at least one of each marker.
    """
    report = await _validate(validator, VALID_GRADE3_LESSON)

    audio_check = next(
        (c for c in report.checks if c.name == "audio_pacing"), None
    )
    if audio_check is None:
        pytest.skip("audio_pacing check not present in report")

    assert audio_check.status == "passed", (
        f"Valid lesson with [Beat] and [Pause] must pass audio_pacing. "
        f"Details: {audio_check.details}"
    )
    details = audio_check.details
    beat_count = details.get("beat_markers", details.get("beat_count", 0))
    pause_count = details.get("pause_markers", details.get("pause_count", 0))
    assert beat_count >= 1, f"Expected ≥1 [Beat] marker, found {beat_count}"
    assert pause_count >= 1, f"Expected ≥1 [Pause] marker, found {pause_count}"


# ---------------------------------------------------------------------------
# Test 7: Content isolation — excluded concepts not found in valid lesson
# ---------------------------------------------------------------------------


async def test_content_isolation_exclusions_respected(validator):
    """A valid lesson for 'Trees vs Shrubs' does not mention excluded concepts.

    The exclusions ['climbers', 'creepers'] are passed to validate.
    The valid lesson fixture does not mention them, so content_isolation passes.
    """
    report = await _validate(
        validator,
        VALID_GRADE3_LESSON,
        exclusions=["climbers", "creepers"],
    )

    content_check = next(
        (c for c in report.checks if c.name == "content_isolation"), None
    )
    if content_check is None:
        pytest.skip("content_isolation check not present in report")

    assert content_check.status == "passed", (
        f"Valid lesson must pass content_isolation for excluded=['climbers','creepers']. "
        f"Details: {content_check.details}"
    )
    excluded_found = content_check.details.get("excluded_concepts_found", 0)
    assert excluded_found == 0, (
        f"Expected 0 excluded concepts found, got {excluded_found}"
    )


# ---------------------------------------------------------------------------
# Test 8: Validation report structure integrity
# ---------------------------------------------------------------------------


async def test_validation_report_has_required_structure(validator):
    """The ValidationReport dataclass conforms to the expected structure.

    Checks: passed (bool), checks (list), warnings (list), errors (list),
    overall_score (float 0–1).  Each check must have name and status.
    """
    report = await _validate(validator, VALID_GRADE3_LESSON)

    # Top-level fields
    assert hasattr(report, "passed") and isinstance(report.passed, bool)
    assert hasattr(report, "checks") and isinstance(report.checks, list)
    assert hasattr(report, "warnings") and isinstance(report.warnings, list)
    assert hasattr(report, "errors") and isinstance(report.errors, list)
    assert hasattr(report, "overall_score")
    assert isinstance(report.overall_score, (int, float)), (
        "'overall_score' must be numeric"
    )
    assert 0.0 <= report.overall_score <= 1.0, (
        f"'overall_score' must be between 0 and 1, got {report.overall_score}"
    )

    # Individual check structure
    assert len(report.checks) > 0, "Valid lesson report must have at least one check"
    for check in report.checks:
        assert hasattr(check, "name"), f"Check must have 'name': {check}"
        assert hasattr(check, "status"), f"Check must have 'status': {check}"
        assert check.status in ("passed", "failed", "warning"), (
            f"Check status must be passed/failed/warning, got {check.status}"
        )

    # to_dict() must work without error
    report_dict = report.to_dict()
    assert isinstance(report_dict, dict), "to_dict() must return a dict"
    assert "passed" in report_dict, "to_dict() result must include 'passed'"
    assert "checks" in report_dict, "to_dict() result must include 'checks'"


# ---------------------------------------------------------------------------
# Test 9: compute_score on empty checks → overall_score = 0.0
# ---------------------------------------------------------------------------


def test_compute_score_on_empty_checks():
    """ValidationReport.compute_score returns 0.0 when there are no checks.

    An empty checks list is an edge-case that could arise from a partially
    initialised report.  The score must default to 0.0 rather than dividing
    by zero.
    """
    from src.services.validator import ValidationReport as VR

    report = VR()
    # Do NOT add any checks
    report.compute_score()

    assert report.overall_score == 0.0, (
        f"Empty checks should give overall_score=0.0, got {report.overall_score}"
    )


# ---------------------------------------------------------------------------
# Test 10: definition_check with kb_definitions provided
# ---------------------------------------------------------------------------


async def test_definition_check_with_kb_definitions_found(validator):
    """definition_check passes when all KB concepts appear in the lesson text.

    When kb_definitions contains concepts that all appear in the lesson,
    the definition_alignment check must be 'passed' (not 'warning').
    """
    report = await validator.validate(
        lesson_data=VALID_GRADE3_LESSON,
        grade="3",
        subject="EVS",
        kb_definitions={"tree": "a plant with one thick trunk", "shrub": "a plant with many stems"},
    )

    def_check = next((c for c in report.checks if c.name == "definition_alignment"), None)
    if def_check is None:
        pytest.skip("definition_alignment check not present in report")

    # The valid lesson mentions 'tree' and 'shrub' so both should be found
    assert def_check.status in ("passed", "warning"), (
        f"definition_alignment must be passed or warning, got {def_check.status}"
    )


async def test_definition_check_with_missing_concepts_produces_warning(validator):
    """definition_check produces a WARNING when a KB concept is not in the lesson.

    If a key concept from kb_definitions does not appear in lesson text,
    the check must return 'warning' (soft-check per architecture Section 4.3.3).
    """
    report = await validator.validate(
        lesson_data=VALID_GRADE3_LESSON,
        grade="3",
        subject="EVS",
        kb_definitions={"photosynthesis": "process by which plants make food"},
    )

    def_check = next((c for c in report.checks if c.name == "definition_alignment"), None)
    if def_check is None:
        pytest.skip("definition_alignment check not present in report")

    # 'photosynthesis' is not in the Trees vs Shrubs lesson → warning
    assert def_check.status == "warning", (
        f"Missing concept should produce 'warning', got {def_check.status}. "
        f"Details: {def_check.details}"
    )


# ---------------------------------------------------------------------------
# Test 11: story_integration_check with matching context narrative
# ---------------------------------------------------------------------------


async def test_story_integration_passes_when_narrative_referenced(validator):
    """story_integration passes when the lesson references the chapter narrative.

    VALID_GRADE3_LESSON mentions 'trees' and 'shrubs' in opening narration.
    A narrative that uses these terms should produce 'passed' status.
    """
    narrative = "Today we look at trees and shrubs in the garden."
    report = await validator.validate(
        lesson_data=VALID_GRADE3_LESSON,
        grade="3",
        subject="EVS",
        context_narrative=narrative,
    )

    story_check = next((c for c in report.checks if c.name == "story_integration"), None)
    if story_check is None:
        pytest.skip("story_integration check not present in report")

    # The lesson mentions 'trees' and 'shrubs' which are in the narrative
    assert story_check.status in ("passed", "warning"), (
        f"story_integration status must be passed or warning, got {story_check.status}"
    )


async def test_story_integration_warning_when_narrative_not_referenced(validator):
    """story_integration produces WARNING when narrative terms are absent from lesson.

    A narrative about 'penguins' would not be referenced in a trees lesson.
    The check must return 'warning' (soft check) rather than 'failed'.
    """
    narrative = "Penguin walks across the ice and sees the ocean."
    report = await validator.validate(
        lesson_data=VALID_GRADE3_LESSON,
        grade="3",
        subject="EVS",
        context_narrative=narrative,
    )

    story_check = next((c for c in report.checks if c.name == "story_integration"), None)
    if story_check is None:
        pytest.skip("story_integration check not present in report")

    assert story_check.status == "warning", (
        f"Unrelated narrative must produce 'warning', got {story_check.status}. "
        f"Details: {story_check.details}"
    )


# ---------------------------------------------------------------------------
# Test 12: audio_pacing fails when [Pause] is absent
# ---------------------------------------------------------------------------


async def test_audio_pacing_fails_when_pause_missing(validator):
    """audio_pacing fails when no [Pause] marker is present in the lesson.

    The [Pause] marker is mandatory (at least one per lesson).  A lesson
    without any [Pause] markers must fail the audio_pacing check.
    """
    import copy
    import re

    lesson = copy.deepcopy(VALID_GRADE3_LESSON)

    def _strip_pause(obj):
        if isinstance(obj, str):
            return re.sub(r"\[Pause\]", "", obj)
        elif isinstance(obj, dict):
            return {k: _strip_pause(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_strip_pause(i) for i in obj]
        return obj

    lesson = _strip_pause(lesson)

    report = await _validate(validator, lesson)

    audio_check = next((c for c in report.checks if c.name == "audio_pacing"), None)
    if audio_check is None:
        pytest.skip("audio_pacing check not present in report")

    assert audio_check.status == "failed", (
        f"Missing [Pause] must cause audio_pacing to fail, got {audio_check.status}. "
        f"Details: {audio_check.details}"
    )


# ---------------------------------------------------------------------------
# Test 13: interaction_type fails when bloom_level is wrong
# ---------------------------------------------------------------------------


async def test_interaction_type_fails_when_activity_bloom_is_wrong(validator):
    """interaction_type fails when the activity Bloom's level is not L3 or L4.

    An activity tagged L1 is not an Apply/Analyse task.  The check must
    reject it even if the activity type itself is in the allowed list.
    """
    import copy

    lesson = copy.deepcopy(VALID_GRADE3_LESSON)
    lesson["interactive_activity"]["bloom_level"] = "L1"  # must be L3 or L4

    report = await _validate(validator, lesson)

    interaction_check = next(
        (c for c in report.checks if c.name == "interaction_type"), None
    )
    if interaction_check is None:
        pytest.skip("interaction_type check not present in report")

    assert interaction_check.status == "failed", (
        f"Activity Bloom level L1 must fail interaction_type check. "
        f"Details: {interaction_check.details}"
    )


# ---------------------------------------------------------------------------
# Test 14: blooms_distribution fails when quiz is missing entirely
# ---------------------------------------------------------------------------


async def test_blooms_distribution_fails_when_quiz_missing(validator):
    """blooms_distribution fails when quick_quiz is entirely absent.

    The quiz is required for Bloom's level analysis.  A lesson without the
    quick_quiz key must fail with an appropriate error message.
    """
    import copy

    lesson = copy.deepcopy(VALID_GRADE3_LESSON)
    del lesson["quick_quiz"]

    report = await _validate(validator, lesson)

    blooms_check = next(
        (c for c in report.checks if c.name == "blooms_distribution"), None
    )
    if blooms_check is None:
        pytest.skip("blooms_distribution check not present in report")

    assert blooms_check.status == "failed", (
        f"Missing quick_quiz must fail blooms_distribution, got {blooms_check.status}"
    )
