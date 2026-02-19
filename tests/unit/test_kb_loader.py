"""Unit tests for the KBLoader service (src/services/kb_loader.py).

The KBLoader reads Markdown KB files from disk, normalises their content into
structured Python objects, and exposes query methods used by the validation
pipeline and the lesson generation orchestrator.

These tests verify every public method of KBLoader against the Grade 3
(and multi-grade) constraints defined in the KB Markdown files, using the
actual LanguageCeiling dataclass returned by the service.

Tests use the real KB files from ``kb_files/`` via the production KBLoader
to ensure parsing logic stays in sync with the source-of-truth documents.
"""

from __future__ import annotations

import os
import pytest

# ---------------------------------------------------------------------------
# Conditional import — tests are skipped until the service is implemented
# ---------------------------------------------------------------------------
kb_loader_mod = pytest.importorskip(
    "src.services.kb_loader",
    reason="src/services/kb_loader.py not yet implemented",
)

KBLoader = kb_loader_mod.KBLoader
LanguageCeiling = kb_loader_mod.LanguageCeiling

KB_PATH = os.environ.get("KB_PATH", "/home/kunal/projects/kitmeK-lesson-backend/kb_files")


@pytest.fixture(scope="module")
def kb_loader():
    """Instantiate KBLoader once for the whole test module to save load time.

    The loader reads KB files from KB_PATH.  The fixture is module-scoped
    because KB files are immutable during testing.
    """
    return KBLoader(kb_path=KB_PATH)


# ---------------------------------------------------------------------------
# Test 1: Language ceiling Grade 3
# ---------------------------------------------------------------------------


def test_get_language_ceiling_grade3(kb_loader):
    """KBLoader returns correct language ceiling values for Grade 3.

    According to language_guidelines.md:
        - Maximum sentence length: 10–12 words → ceiling is 12
        - New vocabulary per lesson: 5–6 maximum → ceiling is at most 6

    The return value is a LanguageCeiling dataclass (not a plain dict).
    The test accesses its attributes directly.
    """
    ceiling = kb_loader.get_language_ceiling("3")

    assert isinstance(ceiling, LanguageCeiling), (
        f"get_language_ceiling must return a LanguageCeiling, got {type(ceiling)}"
    )
    # Grade 3 ceiling: sentences must not exceed 12 words
    assert ceiling.max_sentence_length == 12, (
        f"Grade 3 max sentence length should be 12, got {ceiling.max_sentence_length}"
    )
    # Grade 3 ceiling: up to 6 new words
    assert ceiling.max_new_vocab >= 5, (
        f"Grade 3 max_new_vocab should be >= 5, got {ceiling.max_new_vocab}"
    )
    assert ceiling.grade == "3", (
        f"LanguageCeiling.grade should be '3', got {ceiling.grade!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: Language ceiling Kindergarten
# ---------------------------------------------------------------------------


def test_get_language_ceiling_kindergarten(kb_loader):
    """KBLoader returns correct language ceiling values for Kindergarten.

    According to language_guidelines.md:
        - Maximum sentence length: 5–7 words → ceiling is 7
        - New vocabulary per lesson: 2–3 maximum → ceiling is at most 3

    Kindergarten has the most restrictive language constraints in the system.
    The return is a LanguageCeiling dataclass; attributes are accessed directly.
    """
    ceiling = kb_loader.get_language_ceiling("K")

    assert isinstance(ceiling, LanguageCeiling)
    # Kindergarten must have the most restrictive sentence length
    assert ceiling.max_sentence_length <= 7, (
        f"Grade K max_sentence_length should be ≤ 7, got {ceiling.max_sentence_length}"
    )
    # Kindergarten allows fewer new words than Grade 3
    grade3_vocab = kb_loader.get_language_ceiling("3").max_new_vocab
    assert ceiling.max_new_vocab < grade3_vocab, (
        f"Kindergarten max_new_vocab ({ceiling.max_new_vocab}) must be "
        f"stricter than Grade 3 ({grade3_vocab})"
    )


# ---------------------------------------------------------------------------
# Test 3: Bloom's distribution Grade 3
# ---------------------------------------------------------------------------


def test_get_bloom_distribution_grade3(kb_loader):
    """KBLoader returns the required Bloom's level distribution for Grade 3.

    From architecture Section 9.3 (Acceptance Test 1):
        Quiz must have: L1×2, L2×3, L3×3, L4×1, L5×1
    The sum must be 10 (one complete Quick Quiz).
    """
    dist = kb_loader.get_bloom_distribution("3")

    assert isinstance(dist, dict), "get_bloom_distribution must return a dict"
    for level in ("L1", "L2", "L3", "L4", "L5"):
        assert level in dist, f"Distribution must include {level}"
        assert isinstance(dist[level], int), f"Count for {level} must be an integer"

    assert dist["L1"] == 2, f"Grade 3 L1 count should be 2, got {dist['L1']}"
    assert dist["L2"] == 3, f"Grade 3 L2 count should be 3, got {dist['L2']}"
    assert dist["L3"] == 3, f"Grade 3 L3 count should be 3, got {dist['L3']}"
    assert dist["L4"] == 1, f"Grade 3 L4 count should be 1, got {dist['L4']}"
    assert dist["L5"] == 1, f"Grade 3 L5 count should be 1, got {dist['L5']}"
    total = sum(dist.values())
    assert total == 10, f"Grade 3 Bloom's distribution must sum to 10, got {total}"


# ---------------------------------------------------------------------------
# Test 4: Allowed interactions Grade 3
# ---------------------------------------------------------------------------


def test_get_allowed_interactions_grade3(kb_loader):
    """KBLoader returns the correct allowed interactions list for Grade 3.

    From digital_interactions.md (Grade 3 section).
    Specifically:
        - 'Drag to Sort' MUST be in the list (preferred for EVS classification)
        - 'Scratch to reveal' must NOT be in the list (Grade K only)
        - 'Trace with Finger' must NOT be in the list (Grades K–1 only)
    """
    allowed = kb_loader.get_allowed_interactions("3")

    assert isinstance(allowed, list), "get_allowed_interactions must return a list"
    assert len(allowed) >= 12, (
        f"Grade 3 should have at least 12 allowed interaction types, got {len(allowed)}"
    )

    # Must be included for Grade 3 (core EVS interaction)
    assert "Drag to Sort" in allowed, "'Drag to Sort' must be allowed for Grade 3"
    assert "Choose the Odd One Out" in allowed, "'Choose the Odd One Out' must be allowed"
    assert "Match one item to another" in allowed, "'Match one item to another' must be allowed"

    # Must NOT be available at Grade 3 (narrowed from Grade K)
    assert "Scratch to reveal" not in allowed, (
        "'Scratch to reveal' is Grade K only and must not appear in Grade 3"
    )
    assert "Trace with Finger" not in allowed, (
        "'Trace with Finger' is Grades K–1 only and must not appear in Grade 3"
    )


# ---------------------------------------------------------------------------
# Test 5: KB version metadata (returns a dict, not a string)
# ---------------------------------------------------------------------------


def test_get_kb_version(kb_loader):
    """KBLoader.get_kb_version returns a dict with version metadata.

    After loading, the dict must have:
        - 'kb_version': non-empty string (e.g. '1.0')
        - 'checksum': non-empty hex string
        - 'files_loaded': non-empty list of filenames

    The version string is used in generation requests and audit logs to ensure
    deterministic replay of lessons.
    """
    # Trigger a load first so _cache is populated
    kb_loader.load()
    version_info = kb_loader.get_kb_version()

    assert isinstance(version_info, dict), (
        f"get_kb_version must return a dict, got {type(version_info).__name__}"
    )
    assert "kb_version" in version_info, "Result dict must have 'kb_version' key"
    assert isinstance(version_info["kb_version"], str), "kb_version must be a string"
    assert len(version_info["kb_version"]) > 0, "kb_version must not be empty"
    # Sanity check: version looks like a semantic version
    assert any(c.isdigit() for c in version_info["kb_version"]), (
        f"kb_version '{version_info['kb_version']}' must contain at least one digit"
    )
    assert "checksum" in version_info, "Result dict must have 'checksum' key"
    assert len(version_info["checksum"]) > 0, "checksum must not be empty"
    assert "files_loaded" in version_info, "Result dict must have 'files_loaded' key"
    assert isinstance(version_info["files_loaded"], list), "files_loaded must be a list"
    assert len(version_info["files_loaded"]) > 0, "files_loaded must not be empty"


# ---------------------------------------------------------------------------
# Test 6: get_kb_version before load returns 'not_loaded'
# ---------------------------------------------------------------------------


def test_get_kb_version_before_load_returns_not_loaded():
    """KBLoader.get_kb_version before load returns a sentinel dict.

    When no files have been loaded yet (fresh KBLoader), get_kb_version must
    return a dict with kb_version='not_loaded' rather than raising an error.
    This matches the /kb/version endpoint's 503 guard check.
    """
    fresh_loader = KBLoader(kb_path=KB_PATH)
    # Do NOT call .load() first
    version_info = fresh_loader.get_kb_version()

    assert isinstance(version_info, dict)
    assert version_info.get("kb_version") == "not_loaded", (
        f"Expected 'not_loaded' before first load, got {version_info.get('kb_version')!r}"
    )
    assert version_info.get("files_loaded") == [], (
        f"files_loaded should be empty before load, got {version_info.get('files_loaded')}"
    )


# ---------------------------------------------------------------------------
# Test 7: is_loaded() reflects cache state
# ---------------------------------------------------------------------------


def test_is_loaded_reflects_cache_state():
    """KBLoader.is_loaded() returns False before load and True after.

    The is_loaded() predicate is used by the dependency injection layer to
    report KB status in the /health endpoint.
    """
    fresh_loader = KBLoader(kb_path=KB_PATH)
    assert fresh_loader.is_loaded() is False, "is_loaded should be False before load"
    fresh_loader.load()
    assert fresh_loader.is_loaded() is True, "is_loaded should be True after load"


# ---------------------------------------------------------------------------
# Test 8: reload() invalidates cache and re-reads files
# ---------------------------------------------------------------------------


def test_reload_returns_fresh_kb_data(kb_loader):
    """KBLoader.reload() clears cache and returns freshly parsed KBData.

    After reload, is_loaded() must be True and the checksum must match the
    original load checksum (same files on disk).
    """
    from src.services.kb_loader import KBData

    first_data = kb_loader.load()
    first_checksum = first_data.checksum

    reloaded = kb_loader.reload()

    assert isinstance(reloaded, KBData), (
        f"reload() must return KBData, got {type(reloaded).__name__}"
    )
    assert reloaded.checksum == first_checksum, (
        "Checksum must be identical for the same files on disk after reload"
    )
    assert kb_loader.is_loaded() is True, "is_loaded must be True after reload"


# ---------------------------------------------------------------------------
# Test 9: Invalid grade uses fallback (no ValueError)
# ---------------------------------------------------------------------------


def test_invalid_grade_uses_fallback_not_raises(kb_loader):
    """KBLoader falls back to a default grade for unrecognised grade codes.

    Rather than raising ValueError, KBLoader logs a warning and uses a
    fallback grade.  This is intentional for resilience:
        - get_language_ceiling('99') → falls back to Grade 5
        - get_bloom_distribution('99') → falls back to Grade 3
        - get_allowed_interactions('99') → falls back to Grade 5

    The return value must be valid (non-empty) in all cases.
    """
    # No ValueError — just fallback
    ceiling = kb_loader.get_language_ceiling("99")
    assert isinstance(ceiling, LanguageCeiling), (
        "Invalid grade should fall back to a valid LanguageCeiling, not raise"
    )
    assert ceiling.max_sentence_length > 0, "Fallback ceiling must have a valid max_sentence_length"

    dist = kb_loader.get_bloom_distribution("99")
    assert isinstance(dist, dict) and len(dist) > 0, (
        "Invalid grade should fall back to a valid bloom distribution dict"
    )

    interactions = kb_loader.get_allowed_interactions("99")
    assert isinstance(interactions, list) and len(interactions) > 0, (
        "Invalid grade should fall back to a valid interactions list"
    )


# ---------------------------------------------------------------------------
# Test 10: get_full_content returns raw file text
# ---------------------------------------------------------------------------


def test_get_full_content_returns_markdown(kb_loader):
    """KBLoader.get_full_content returns the raw markdown text for a known file.

    The content of 'language_guidelines.md' must be a non-empty string
    containing the word 'Grade' (confirming it was actually parsed).
    """
    kb_loader.load()
    content = kb_loader.get_full_content("language_guidelines.md")

    assert isinstance(content, str), "get_full_content must return a string"
    assert len(content) > 100, "language_guidelines.md must contain substantial text"
    assert "Grade" in content, (
        "language_guidelines.md must contain the word 'Grade' — check file loading"
    )


# ---------------------------------------------------------------------------
# Test 11: get_definition returns snippet or None
# ---------------------------------------------------------------------------


def test_get_definition_returns_none_for_unknown(kb_loader):
    """KBLoader.get_definition returns None for concepts not in definitions_and_examples.md.

    A made-up concept ('ZzZzUnknownConcept') must not be found in any KB file,
    so get_definition must return None rather than raising.
    """
    kb_loader.load()
    result = kb_loader.get_definition("ZzZzUnknownConcept", grade="3")
    assert result is None, (
        f"Expected None for unknown concept, got {result!r}"
    )
