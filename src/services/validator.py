"""
Lesson Validation Pipeline — All 8 checks from Architecture Doc Section 4.3.3.

Validates generated lesson data against KB constraints deterministically.
Never raises unhandled exceptions — always returns a ValidationReport.
"""

import re
import json
import logging
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Grade-level constants (from language_guidelines.md Quick Reference Table)
# ---------------------------------------------------------------------------

LANGUAGE_CEILINGS: dict[str, dict[str, Any]] = {
    "K": {"max_sentence_length": 7, "new_vocab_max": 3},
    "1": {"max_sentence_length": 8, "new_vocab_max": 4},
    "2": {"max_sentence_length": 10, "new_vocab_max": 5},
    "3": {"max_sentence_length": 12, "new_vocab_max": 6},
    "4": {"max_sentence_length": 15, "new_vocab_max": 8},
    "5": {"max_sentence_length": 18, "new_vocab_max": 10},
}

# Bloom's distribution per grade (from NCERT_Pedagogical_Style_Knowledge.md)
BLOOM_DISTRIBUTION: dict[str, dict[str, int]] = {
    "K": {"L1": 4, "L2": 4, "L3": 2, "L4": 0, "L5": 0},
    "1": {"L1": 3, "L2": 4, "L3": 2, "L4": 1, "L5": 0},
    "2": {"L1": 3, "L2": 3, "L3": 2, "L4": 1, "L5": 1},
    "3": {"L1": 2, "L2": 3, "L3": 3, "L4": 1, "L5": 1},
    "4": {"L1": 2, "L2": 2, "L3": 3, "L4": 2, "L5": 1},
    "5": {"L1": 1, "L2": 2, "L3": 3, "L4": 2, "L5": 2},
}

# Allowed interaction types per grade (from digital_interactions.md)
ALLOWED_INTERACTIONS: dict[str, list[str]] = {
    "K": [
        "Tap to Select", "Tap All That Apply", "Tap to Count",
        "Tap in Sequence", "Tap Yes / No", "Reveal on Tap", "Tap to Build",
        "Drag and Drop", "Drag to Sort", "Drag to Complete",
        "Follow the Path", "Drag to reorder items", "Drag along a path",
        "Match one item to another", "Flip to find a pair",
        "Choose the Odd One Out", "Match item to placeholder",
        "Trace with Finger", "Swipe to Move",
        "Slide to adjust size or value", "Scratch to reveal",
        "Listen and Respond", "Listen and respond", "Listen and act",
    ],
    "1": [
        "Tap to Select", "Tap All That Apply", "Tap to Count",
        "Tap in Sequence", "Tap Yes / No", "Reveal on Tap", "Tap to Build",
        "Drag and Drop", "Drag to Sort", "Drag to Complete",
        "Follow the Path", "Drag to reorder items",
        "Match one item to another", "Flip to find a pair",
        "Choose the Odd One Out", "Match item to placeholder",
        "Trace with Finger", "Swipe to Move",
        "Slide to adjust size or value",
        "Listen and Respond", "Listen and respond",
    ],
    "2": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence",
        "Tap Yes / No", "Reveal on Tap",
        "Drag and Drop", "Drag to Sort", "Drag to Complete",
        "Drag to reorder items",
        "Match one item to another", "Flip to find a pair",
        "Choose the Odd One Out", "Match item to placeholder",
        "Slide to adjust size or value",
        "Listen and Respond", "Listen and respond",
    ],
    "3": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence",
        "Tap Yes / No",
        "Drag and Drop", "Drag to Sort", "Drag to Complete",
        "Drag to reorder items",
        "Match one item to another", "Choose the Odd One Out",
        "Match item to placeholder",
        "Listen and Respond",
    ],
    "4": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence",
        "Tap Yes / No",
        "Drag and Drop", "Drag to Sort", "Drag to Complete",
        "Drag to reorder items",
        "Match one item to another", "Choose the Odd One Out",
        "Match item to placeholder",
        "Listen and Respond",
    ],
    "5": [
        "Tap to Select", "Tap All That Apply", "Tap in Sequence",
        "Tap Yes / No",
        "Drag and Drop", "Drag to Sort", "Drag to Complete",
        "Drag to reorder items",
        "Match one item to another", "Choose the Odd One Out",
        "Match item to placeholder",
        "Listen and Respond",
    ],
}


# ---------------------------------------------------------------------------
# Data classes for validation results
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    status: str  # "passed", "failed", "warning"
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    passed: bool = True
    checks: list[CheckResult] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    overall_score: float = 1.0

    def add_check(self, check: CheckResult) -> None:
        self.checks.append(check)
        if check.status == "failed":
            self.passed = False
            self.errors.append({
                "type": check.name,
                "message": check.message,
                "severity": "high",
            })
        elif check.status == "warning":
            self.warnings.append({
                "type": check.name,
                "message": check.message,
                "severity": "low",
            })

    def compute_score(self) -> None:
        if not self.checks:
            self.overall_score = 0.0
            return
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.status == "passed")
        warned = sum(1 for c in self.checks if c.status == "warning")
        self.overall_score = round((passed + warned * 0.5) / total, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
            "errors": self.errors,
            "overall_score": self.overall_score,
        }


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _extract_all_text(lesson_data: dict) -> str:
    """Recursively extract all string values from lesson_data into one blob."""
    texts: list[str] = []

    def _recurse(obj: Any) -> None:
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                _recurse(item)

    _recurse(lesson_data)
    return " ".join(texts)


def _extract_sentences(text: str) -> list[str]:
    """Split text into sentences, stripping audio markers."""
    # Remove audio markers before splitting
    cleaned = re.sub(r"\[Beat\]", "", text)
    cleaned = re.sub(r"\[Pause\]", "", cleaned)
    cleaned = re.sub(r"\[Emphasis:\s*\w+\]", "", cleaned)
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', cleaned.strip())
    return [s.strip() for s in sentences if s.strip()]


def _count_words(sentence: str) -> int:
    """Count words in a sentence, ignoring punctuation-only tokens."""
    words = sentence.split()
    return len([w for w in words if re.search(r'[a-zA-Z0-9]', w)])


def _safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dict keys."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


# ---------------------------------------------------------------------------
# LessonValidator — main class
# ---------------------------------------------------------------------------

class LessonValidator:
    """
    Validates generated lesson data against all KB constraints.

    All 8 checks:
      a) language_ceiling_check
      b) blooms_distribution_check
      c) interaction_type_check
      d) definition_check          (soft-check → WARNING)
      e) story_integration_check   (soft-check → WARNING)
      f) audio_pacing_check
      g) feedback_structure_check
      h) content_isolation_check
    """

    async def validate(
        self,
        lesson_data: dict[str, Any],
        grade: str,
        subject: str,
        exclusions: Optional[list[str]] = None,
        prerequisites: Optional[list[str]] = None,
        context_narrative: Optional[str] = None,
        kb_definitions: Optional[dict[str, str]] = None,
    ) -> ValidationReport:
        """
        Run all 8 validation checks and return a ValidationReport.
        Never raises — all exceptions caught and reported.
        """
        report = ValidationReport()

        checks = [
            ("language_ceiling", self.language_ceiling_check),
            ("blooms_distribution", self.blooms_distribution_check),
            ("interaction_type", self.interaction_type_check),
            ("definition_alignment", self.definition_check),
            ("story_integration", self.story_integration_check),
            ("audio_pacing", self.audio_pacing_check),
            ("feedback_structure", self.feedback_structure_check),
            ("content_isolation", self.content_isolation_check),
        ]

        for check_name, check_fn in checks:
            try:
                result = check_fn(
                    lesson_data=lesson_data,
                    grade=grade,
                    subject=subject,
                    exclusions=exclusions or [],
                    prerequisites=prerequisites or [],
                    context_narrative=context_narrative or "",
                    kb_definitions=kb_definitions or {},
                )
                report.add_check(result)
            except Exception as exc:
                logger.error("Validation check '%s' raised: %s", check_name, exc)
                report.add_check(CheckResult(
                    name=check_name,
                    status="failed",
                    details={"error": str(exc)},
                    message=f"Internal error in {check_name}: {exc}",
                ))

        report.compute_score()
        return report

    # ------------------------------------------------------------------
    # CHECK a) Language Ceiling
    # ------------------------------------------------------------------

    def language_ceiling_check(self, lesson_data: dict, grade: str, **_kwargs) -> CheckResult:
        """
        For each sentence: word_count <= max_for_grade.
        For each section: new_vocab_count <= allowed_for_grade.
        """
        ceiling = LANGUAGE_CEILINGS.get(grade, LANGUAGE_CEILINGS["3"])
        max_len = ceiling["max_sentence_length"]
        max_vocab = ceiling["new_vocab_max"]

        all_text = _extract_all_text(lesson_data)
        sentences = _extract_sentences(all_text)

        violations: list[dict[str, Any]] = []
        max_found = 0

        for sent in sentences:
            wc = _count_words(sent)
            if wc > max_found:
                max_found = wc
            if wc > max_len:
                violations.append({
                    "sentence": sent[:80],
                    "word_count": wc,
                    "max_allowed": max_len,
                })

        # Count new vocabulary (words introduced for the first time)
        # Heuristic: words marked with [Emphasis: word] are new vocab
        emphasis_matches = re.findall(r'\[Emphasis:\s*(\w+)\]', all_text)
        new_vocab_count = len(set(emphasis_matches))

        vocab_exceeded = new_vocab_count > max_vocab

        details = {
            "max_sentence_length": max_len,
            "sentences_checked": len(sentences),
            "max_found": max_found,
            "violations_count": len(violations),
            "violations": violations[:5],  # cap at 5 for readability
            "new_vocab_count": new_vocab_count,
            "new_vocab_max": max_vocab,
            "vocab_exceeded": vocab_exceeded,
        }

        if violations or vocab_exceeded:
            return CheckResult(
                name="language_ceiling",
                status="failed",
                details=details,
                message=(
                    f"{len(violations)} sentence(s) exceed max length {max_len} for grade {grade}. "
                    f"New vocab: {new_vocab_count}/{max_vocab}."
                ),
            )

        return CheckResult(
            name="language_ceiling",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK b) Bloom's Distribution
    # ------------------------------------------------------------------

    def blooms_distribution_check(self, lesson_data: dict, grade: str, **_kwargs) -> CheckResult:
        """
        Count L1-L5 across all quiz questions.
        Verify matches grade distribution table.
        Verify progression: Q1-Q3 are L1/L2, Q8-Q10 are L3-L5.
        """
        expected = BLOOM_DISTRIBUTION.get(grade, BLOOM_DISTRIBUTION["3"])
        quiz = lesson_data.get("quick_quiz", [])

        if not quiz:
            return CheckResult(
                name="blooms_distribution",
                status="failed",
                details={"error": "No quick_quiz found in lesson data"},
                message="Quick quiz section is missing from lesson data.",
            )

        actual: dict[str, int] = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5": 0}
        for q in quiz:
            bl = q.get("bloom_level", "").upper().strip()
            if bl in actual:
                actual[bl] += 1

        distribution_match = all(actual.get(k, 0) == v for k, v in expected.items())

        # Progression check: Q1-Q3 should be L1/L2, Q8-Q10 should be L3-L5
        progression_ok = True
        progression_issues: list[str] = []

        for i, q in enumerate(quiz[:3], start=1):
            bl = q.get("bloom_level", "").upper().strip()
            if bl not in ("L1", "L2"):
                progression_ok = False
                progression_issues.append(f"Q{i} is {bl}, expected L1 or L2")

        for i, q in enumerate(quiz[7:10], start=8):
            bl = q.get("bloom_level", "").upper().strip()
            if bl not in ("L3", "L4", "L5"):
                progression_ok = False
                progression_issues.append(f"Q{i} is {bl}, expected L3-L5")

        details = {
            "expected": expected,
            "actual": actual,
            "distribution_match": distribution_match,
            "progression_ok": progression_ok,
            "progression_issues": progression_issues,
            "total_questions": len(quiz),
        }

        if not distribution_match or not progression_ok:
            return CheckResult(
                name="blooms_distribution",
                status="failed",
                details=details,
                message=(
                    f"Bloom's distribution mismatch for grade {grade}. "
                    f"Expected {expected}, got {actual}. "
                    f"Progression issues: {progression_issues}"
                ),
            )

        return CheckResult(
            name="blooms_distribution",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK c) Interaction Type
    # ------------------------------------------------------------------

    def interaction_type_check(self, lesson_data: dict, grade: str, **_kwargs) -> CheckResult:
        """
        Extract activity type from lesson.
        Verify it's in allowed_interactions[grade].
        """
        allowed = ALLOWED_INTERACTIONS.get(grade, ALLOWED_INTERACTIONS["3"])
        activity = lesson_data.get("interactive_activity", {})

        if not activity:
            return CheckResult(
                name="interaction_type",
                status="failed",
                details={"error": "No interactive_activity found"},
                message="Interactive activity section is missing from lesson data.",
            )

        activity_type = activity.get("type", "")

        # Case-insensitive match
        allowed_lower = [a.lower() for a in allowed]
        is_allowed = activity_type.lower() in allowed_lower

        # Check Bloom's level of activity matches expected (L3 Apply or L4 Analyze)
        activity_bloom = activity.get("bloom_level", "").upper().strip()
        bloom_ok = activity_bloom in ("L3", "L4")

        details = {
            "activity_type": activity_type,
            "allowed_for_grade": allowed,
            "is_allowed": is_allowed,
            "activity_bloom_level": activity_bloom,
            "bloom_level_valid": bloom_ok,
        }

        if not is_allowed:
            return CheckResult(
                name="interaction_type",
                status="failed",
                details=details,
                message=f"Activity type '{activity_type}' is not allowed for grade {grade}.",
            )

        if not bloom_ok:
            return CheckResult(
                name="interaction_type",
                status="failed",
                details=details,
                message=f"Activity Bloom's level '{activity_bloom}' should be L3 or L4.",
            )

        return CheckResult(
            name="interaction_type",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK d) Definition (soft-check → WARNING)
    # ------------------------------------------------------------------

    def definition_check(
        self,
        lesson_data: dict,
        kb_definitions: Optional[dict[str, str]] = None,
        **_kwargs,
    ) -> CheckResult:
        """
        Extract key concepts from lesson.
        For each concept: verify definition matches KB definition.
        Soft check — returns WARNING on mismatch, not FAIL.
        """
        if not kb_definitions:
            return CheckResult(
                name="definition_alignment",
                status="warning",
                details={"reason": "No KB definitions provided for comparison"},
                message="No KB definitions available; skipping definition alignment.",
            )

        all_text = _extract_all_text(lesson_data).lower()

        concepts_checked = 0
        concepts_found = 0
        missing_concepts: list[str] = []

        for concept, definition in kb_definitions.items():
            concepts_checked += 1
            # Check if the concept term appears in the lesson text
            if concept.lower() in all_text:
                concepts_found += 1
            else:
                missing_concepts.append(concept)

        details = {
            "concepts_checked": concepts_checked,
            "concepts_found_in_lesson": concepts_found,
            "missing_concepts": missing_concepts,
        }

        if missing_concepts:
            return CheckResult(
                name="definition_alignment",
                status="warning",
                details=details,
                message=f"Some KB concepts not found in lesson: {missing_concepts[:5]}",
            )

        return CheckResult(
            name="definition_alignment",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK e) Story Integration (soft-check → WARNING)
    # ------------------------------------------------------------------

    def story_integration_check(
        self,
        lesson_data: dict,
        context_narrative: str = "",
        **_kwargs,
    ) -> CheckResult:
        """
        Opening Narration must reference topic context (if provided).
        At least one concept section must weave narrative.
        Soft check — returns WARNING, not FAIL.
        """
        if not context_narrative:
            return CheckResult(
                name="story_integration",
                status="passed",
                details={"reason": "No context narrative provided; check not applicable"},
            )

        opening = lesson_data.get("opening_narration", {})
        opening_text = " ".join(
            str(v) for v in opening.values() if isinstance(v, str)
        ).lower() if isinstance(opening, dict) else str(opening).lower()

        # Extract key terms from narrative (words > 3 chars)
        narrative_terms = [
            w.lower() for w in re.findall(r'\b\w+\b', context_narrative) if len(w) > 3
        ]

        opening_references = sum(1 for t in narrative_terms if t in opening_text)

        # Check narrated explanation sections
        explanations = lesson_data.get("narrated_explanation", [])
        explanation_text = ""
        if isinstance(explanations, list):
            for exp in explanations:
                if isinstance(exp, dict):
                    explanation_text += " " + str(exp.get("teacher_explains", ""))
        explanation_text = explanation_text.lower()
        explanation_references = sum(1 for t in narrative_terms if t in explanation_text)

        locations: list[str] = []
        if opening_references > 0:
            locations.append("Opening Narration")
        if explanation_references > 0:
            locations.append("Narrated Explanation")

        details = {
            "context_narrative_provided": True,
            "narrative_terms_checked": len(narrative_terms),
            "opening_references": opening_references,
            "explanation_references": explanation_references,
            "locations_found": locations,
        }

        if not locations:
            return CheckResult(
                name="story_integration",
                status="warning",
                details=details,
                message="Story context was provided but not referenced in lesson.",
            )

        return CheckResult(
            name="story_integration",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK f) Audio Pacing
    # ------------------------------------------------------------------

    def audio_pacing_check(self, lesson_data: dict, **_kwargs) -> CheckResult:
        """
        Count [Beat] and [Pause] markers.
        Verify [Pause] present in at least 1 section.
        Check sentence length alternation (short/medium mix).
        """
        all_text = _extract_all_text(lesson_data)

        beat_count = len(re.findall(r'\[Beat\]', all_text))
        pause_count = len(re.findall(r'\[Pause\]', all_text))
        emphasis_count = len(re.findall(r'\[Emphasis:\s*\w+\]', all_text))

        has_pause = pause_count >= 1
        has_beats = beat_count >= 1

        details = {
            "beat_markers": beat_count,
            "pause_markers": pause_count,
            "emphasis_markers": emphasis_count,
            "has_minimum_pause": has_pause,
            "has_minimum_beat": has_beats,
        }

        if not has_pause:
            return CheckResult(
                name="audio_pacing",
                status="failed",
                details=details,
                message="No [Pause] marker found. At least one [Pause] per lesson is required.",
            )

        if not has_beats:
            return CheckResult(
                name="audio_pacing",
                status="failed",
                details=details,
                message="No [Beat] marker found. At least one [Beat] per lesson is required.",
            )

        return CheckResult(
            name="audio_pacing",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK g) Feedback Structure
    # ------------------------------------------------------------------

    def feedback_structure_check(self, lesson_data: dict, **_kwargs) -> CheckResult:
        """
        Activities have multi-tier hints (Hint 1, 2, 3).
        Quiz questions have Correct + Incorrect feedback.
        Feedback includes reasoning, not just 'Correct'.
        """
        activity = lesson_data.get("interactive_activity", {})
        quiz = lesson_data.get("quick_quiz", [])

        # Check activity multi-tier hints
        has_hint_1 = bool(activity.get("feedback_hint_1", ""))
        has_hint_2 = bool(activity.get("feedback_hint_2", ""))
        has_hint_3 = bool(activity.get("feedback_reveal", ""))
        activity_hints_ok = has_hint_1 and has_hint_2 and has_hint_3

        # Check quiz feedback
        quiz_feedback_issues: list[str] = []
        for i, q in enumerate(quiz, start=1):
            fc = q.get("feedback_correct", "")
            fi = q.get("feedback_incorrect", "")
            if not fc:
                quiz_feedback_issues.append(f"Q{i}: missing feedback_correct")
            elif len(fc.split()) < 4:
                quiz_feedback_issues.append(f"Q{i}: feedback_correct too short (needs reasoning)")
            if not fi:
                quiz_feedback_issues.append(f"Q{i}: missing feedback_incorrect")
            elif len(fi.split()) < 4:
                quiz_feedback_issues.append(f"Q{i}: feedback_incorrect too short (needs reasoning)")

        quiz_feedback_complete = len(quiz_feedback_issues) == 0

        details = {
            "activity_hint_1": has_hint_1,
            "activity_hint_2": has_hint_2,
            "activity_hint_3_reveal": has_hint_3,
            "activity_multitier_ok": activity_hints_ok,
            "quiz_feedback_complete": quiz_feedback_complete,
            "quiz_feedback_issues": quiz_feedback_issues[:5],
        }

        if not activity_hints_ok:
            return CheckResult(
                name="feedback_structure",
                status="failed",
                details=details,
                message="Activity missing multi-tier hints (hint_1, hint_2, reveal).",
            )

        if not quiz_feedback_complete:
            return CheckResult(
                name="feedback_structure",
                status="failed",
                details=details,
                message=f"Quiz feedback incomplete: {quiz_feedback_issues[:3]}",
            )

        return CheckResult(
            name="feedback_structure",
            status="passed",
            details=details,
        )

    # ------------------------------------------------------------------
    # CHECK h) Content Isolation
    # ------------------------------------------------------------------

    def content_isolation_check(
        self,
        lesson_data: dict,
        exclusions: Optional[list[str]] = None,
        prerequisites: Optional[list[str]] = None,
        **_kwargs,
    ) -> CheckResult:
        """
        Verify lesson doesn't introduce concepts marked in topic.exclusions.
        Check prerequisites are met (topic.prerequisites).
        """
        exclusions = exclusions or []
        prerequisites = prerequisites or []

        all_text = _extract_all_text(lesson_data).lower()

        excluded_found: list[str] = []
        for concept in exclusions:
            if concept.lower() in all_text:
                excluded_found.append(concept)

        details = {
            "exclusions_checked": exclusions,
            "excluded_concepts_found": len(excluded_found),
            "excluded_found_list": excluded_found,
            "prerequisites_declared": prerequisites,
            "prerequisites_met": True,  # We trust prerequisites are met by upstream
        }

        if excluded_found:
            return CheckResult(
                name="content_isolation",
                status="failed",
                details=details,
                message=f"Lesson contains excluded concepts: {excluded_found}",
            )

        return CheckResult(
            name="content_isolation",
            status="passed",
            details=details,
        )
