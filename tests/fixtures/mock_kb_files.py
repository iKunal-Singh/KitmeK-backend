"""MockKBLoader — hardcoded Grade 3 (and multi-grade) KB responses for unit tests.

This module provides a drop-in replacement for the real ``KBLoader`` service so
that tests never touch the filesystem or database.  Every method returns values
consistent with the KB Markdown files in ``kb_files/``.

Grade 3 constraints are taken directly from:
- ``language_guidelines.md`` (sentence length 10–12 words → ceiling 12; vocab 5–6)
- ``digital_interactions.md`` (15 types allowed for Grade 3)
- Section 9.3 of the architecture doc (Bloom's distribution per quiz)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Reference data extracted from KB files
# ---------------------------------------------------------------------------

_LANGUAGE_CEILINGS: dict[str, dict[str, Any]] = {
    "K": {"max_sentence_length": 7, "new_vocab": 3},
    "1": {"max_sentence_length": 8, "new_vocab": 4},
    "2": {"max_sentence_length": 10, "new_vocab": 5},
    "3": {"max_sentence_length": 12, "new_vocab": 5},
    "4": {"max_sentence_length": 15, "new_vocab": 8},
    "5": {"max_sentence_length": 18, "new_vocab": 10},
}

_BLOOM_DISTRIBUTIONS: dict[str, dict[str, int]] = {
    "K": {"L1": 6, "L2": 2, "L3": 1, "L4": 0, "L5": 0},
    "1": {"L1": 5, "L2": 3, "L3": 2, "L4": 0, "L5": 0},
    "2": {"L1": 4, "L2": 3, "L3": 2, "L4": 1, "L5": 0},
    "3": {"L1": 2, "L2": 3, "L3": 3, "L4": 1, "L5": 1},
    "4": {"L1": 1, "L2": 2, "L3": 3, "L4": 2, "L5": 2},
    "5": {"L1": 1, "L2": 1, "L3": 3, "L4": 3, "L5": 2},
}

# Grade 3 allowed interactions per digital_interactions.md (Grade 3 section)
_ALLOWED_INTERACTIONS: dict[str, list[str]] = {
    "K": [
        "Tap to Select", "Tap All That Apply", "Tap to Count", "Tap in Sequence",
        "Tap Yes / No", "Reveal on Tap", "Tap to Build",
        "Drag and Drop", "Drag to Sort", "Drag to Complete", "Follow the Path",
        "Drag to reorder items", "Drag along a path",
        "Match one item to another", "Flip to find a pair", "Choose the Odd One Out",
        "Match item to placeholder",
        "Trace with Finger", "Swipe to Move", "Slide to adjust size or value",
        "Scratch to reveal",
        "Listen and Respond", "Listen and respond", "Listen and act",
    ],
    "1": [
        "Tap to Select", "Tap All That Apply", "Tap to Count", "Tap in Sequence",
        "Tap Yes / No", "Reveal on Tap", "Tap to Build",
        "Drag and Drop", "Drag to Sort", "Drag to Complete", "Follow the Path",
        "Drag to reorder items",
        "Match one item to another", "Flip to find a pair", "Choose the Odd One Out",
        "Match item to placeholder",
        "Trace with Finger", "Swipe to Move", "Slide to adjust size or value",
        "Listen and Respond", "Listen and respond",
    ],
    "2": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence",
        "Tap Yes / No", "Reveal on Tap",
        "Drag and Drop", "Drag to Sort", "Drag to Complete", "Drag to reorder items",
        "Match one item to another", "Flip to find a pair", "Choose the Odd One Out",
        "Match item to placeholder",
        "Slide to adjust size or value",
        "Listen and Respond", "Listen and respond",
    ],
    "3": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence", "Tap Yes / No",
        "Drag and Drop", "Drag to Sort", "Drag to Complete", "Drag to reorder items",
        "Match one item to another", "Choose the Odd One Out", "Match item to placeholder",
        "Listen and Respond",
    ],
    "4": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence", "Tap Yes / No",
        "Drag and Drop", "Drag to Sort", "Drag to Complete", "Drag to reorder items",
        "Match one item to another", "Choose the Odd One Out", "Match item to placeholder",
        "Listen and Respond",
    ],
    "5": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence", "Tap Yes / No",
        "Drag and Drop", "Drag to Sort", "Drag to Complete", "Drag to reorder items",
        "Match one item to another", "Choose the Odd One Out", "Match item to placeholder",
        "Listen and Respond",
    ],
}

_VALID_GRADES = frozenset({"K", "1", "2", "3", "4", "5"})
_KB_VERSION = "1.0-test"


# ---------------------------------------------------------------------------
# MockKBData
# ---------------------------------------------------------------------------


@dataclass
class MockKBData:
    """Mock KB data object for testing (mimics real KBData)."""

    version: str = _KB_VERSION
    checksum: str = "mock-checksum-1234567890abcdef"
    files_loaded: list[str] = None
    raw_content: dict[str, str] = None

    def __post_init__(self) -> None:
        if self.files_loaded is None:
            self.files_loaded = [
                "NCERT_Pedagogical_Style_Knowledge.md",
                "language_guidelines.md",
                "digital_interactions.md",
                "question_bank.md",
                "definitions_and_examples.md",
            ]
        if self.raw_content is None:
            self.raw_content = {
                "NCERT_Pedagogical_Style_Knowledge.md": "# Pedagogical Style\n## Grade 3\n...",
                "language_guidelines.md": "# Language Guidelines\n## Grade 3\n...",
                "digital_interactions.md": "# Digital Interactions\n## Grade 3\n...",
                "question_bank.md": "# Question Bank\n...",
                "definitions_and_examples.md": "# Definitions and Examples\n...",
            }


# ---------------------------------------------------------------------------
# MockKBLoader
# ---------------------------------------------------------------------------

class MockKBLoader:
    """In-memory Knowledge Base Loader for unit and integration tests.

    Mirrors the public interface of the production ``KBLoader`` service
    without touching the filesystem or PostgreSQL.  All return values are
    sourced from the real KB files and the architecture specification.
    """

    def load(self) -> MockKBData:
        """Load the KB (mocked for testing).

        Returns:
            MockKBData object with KB metadata.
        """
        return MockKBData()

    def get_language_ceiling(self, grade: str) -> dict[str, Any]:
        """Return maximum sentence length and new-vocabulary cap for *grade*.

        Args:
            grade: Grade code string — one of 'K', '1', '2', '3', '4', '5'.

        Returns:
            Dict with keys ``max_sentence_length`` (int) and ``new_vocab`` (int).

        Raises:
            ValueError: If *grade* is not a recognised grade code.
        """
        if grade not in _VALID_GRADES:
            raise ValueError(f"Unknown grade '{grade}'. Valid grades: {sorted(_VALID_GRADES)}")
        return dict(_LANGUAGE_CEILINGS[grade])

    def get_bloom_distribution(self, grade: str) -> dict[str, int]:
        """Return required Bloom's level distribution for the Quick Quiz.

        The distribution governs how many questions at each Bloom's level
        (L1–L5) must appear in a 10-question quiz.  Total always sums to 10.

        Args:
            grade: Grade code string.

        Returns:
            Dict mapping ``'L1'``–``'L5'`` to required question counts.

        Raises:
            ValueError: If *grade* is not a recognised grade code.
        """
        if grade not in _VALID_GRADES:
            raise ValueError(f"Unknown grade '{grade}'. Valid grades: {sorted(_VALID_GRADES)}")
        return dict(_BLOOM_DISTRIBUTIONS[grade])

    def get_allowed_interactions(self, grade: str) -> list[str]:
        """Return the list of interaction type names permitted for *grade*.

        Each string corresponds to a canonical interaction type defined in
        ``digital_interactions.md``.  The list shrinks as the grade increases
        (e.g. 'Scratch to reveal' is only allowed for Grade K).

        Args:
            grade: Grade code string.

        Returns:
            List of allowed interaction type name strings.

        Raises:
            ValueError: If *grade* is not a recognised grade code.
        """
        if grade not in _VALID_GRADES:
            raise ValueError(f"Unknown grade '{grade}'. Valid grades: {sorted(_VALID_GRADES)}")
        return list(_ALLOWED_INTERACTIONS[grade])

    def get_kb_version(self) -> dict[str, Any]:
        """Return version metadata for the KB.

        Returns:
            Dict with keys ``kb_version``, ``checksum``, and ``files_loaded``.
        """
        return {
            "kb_version": _KB_VERSION,
            "checksum": "test-checksum-mock",
            "files_loaded": [
                "NCERT_Pedagogical_Style_Knowledge.md",
                "language_guidelines.md",
                "digital_interactions.md",
                "question_bank.md",
                "definitions_and_examples.md",
            ],
        }

    def reload(self) -> MockKBData:
        """Reload the KB from source files (mocked for testing).

        Returns:
            MockKBData object with version, checksum, and files_loaded.
        """
        return MockKBData()

    def is_interaction_allowed(self, interaction_type: str, grade: str) -> bool:
        """Convenience check: return True iff *interaction_type* is allowed for *grade*.

        Args:
            interaction_type: Canonical interaction type name string.
            grade: Grade code string.

        Returns:
            ``True`` if allowed, ``False`` otherwise.
        """
        return interaction_type in self.get_allowed_interactions(grade)
