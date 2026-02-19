"""Lesson generation orchestrator for KitmeK.

Assembles the master prompt from knowledge base context and the topic
specification (Section 5.1 of the architecture document), calls the
Anthropic Claude API, and returns the raw lesson JSON.

Retry policy: 3 attempts with exponential back-off (1 s → 2 s → 4 s).
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

import anthropic

from src.config import get_settings
from src.exceptions import KBLoadError, LessonGenerationError
from src.services.kb_loader import KBLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8000
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1  # wait = _BACKOFF_BASE_SECONDS * 2^(attempt-1)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class LessonGenerationOrchestrator:
    """Coordinate KB loading, prompt assembly, Claude API calls, and retries.

    Args:
        kb_loader: An initialised (and loaded) :class:`KBLoader` instance.
        anthropic_api_key: Override the key from settings (useful for testing).
    """

    def __init__(
        self,
        kb_loader: KBLoader,
        anthropic_api_key: str | None = None,
    ) -> None:
        self.kb_loader = kb_loader
        settings = get_settings()
        self._api_key = anthropic_api_key or settings.anthropic_api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_lesson(
        self,
        topic_data: dict[str, Any],
        grade: str,
        subject: str,
        chapter_name: str,
        chapter_narrative: str = "",
        prerequisites: list[str] | None = None,
        exclusions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a complete lesson JSON for the given topic.

        Args:
            topic_data: Dict with at minimum ``topic_name`` key.
            grade: Grade code (``K``, ``1``–``5``).
            subject: Subject name (e.g. ``"EVS"``, ``"Maths"``).
            chapter_name: Human-readable chapter name.
            chapter_narrative: Optional story/context framing from the chapter.
            prerequisites: List of prerequisite topic names (assumed known).
            exclusions: List of concept names that must NOT appear in the lesson.

        Returns:
            Parsed lesson structure as a Python dict (the JSON returned by Claude).

        Raises:
            LessonGenerationError: If all retry attempts fail.
            KBLoadError: If the KB has not been loaded yet.
        """
        start_time = time.monotonic()
        logger.info(
            "Starting lesson generation for topic=%r grade=%s subject=%s",
            topic_data.get("topic_name"),
            grade,
            subject,
        )

        try:
            kb_data = self.kb_loader.load()
        except KBLoadError:
            raise
        except Exception as exc:
            raise LessonGenerationError(f"KB load failed: {exc}") from exc

        prompt = self._assemble_prompt(
            topic_data=topic_data,
            grade=grade,
            subject=subject,
            chapter_name=chapter_name,
            chapter_narrative=chapter_narrative,
            prerequisites=prerequisites or [],
            exclusions=exclusions or [],
            kb_data_dict={
                "pedagogy": kb_data.raw_content.get(
                    "NCERT_Pedagogical_Style_Knowledge.md", ""
                ),
                "language_guidelines": kb_data.raw_content.get(
                    "language_guidelines.md", ""
                ),
                "bloom_taxonomy": kb_data.raw_content.get(
                    "NCERT_Pedagogical_Style_Knowledge.md", ""
                ),
                "interactions": kb_data.raw_content.get("digital_interactions.md", ""),
                "question_bank": kb_data.raw_content.get("question_bank.md", ""),
                "definitions": kb_data.raw_content.get(
                    "definitions_and_examples.md", ""
                ),
            },
        )

        lesson_dict = await self._call_claude_with_retry(prompt)
        elapsed = time.monotonic() - start_time
        logger.info(
            "Lesson generation completed in %.2f seconds for topic=%r",
            elapsed,
            topic_data.get("topic_name"),
        )
        return lesson_dict

    # ------------------------------------------------------------------
    # Prompt assembly
    # ------------------------------------------------------------------

    def _assemble_prompt(
        self,
        topic_data: dict[str, Any],
        grade: str,
        subject: str,
        chapter_name: str,
        chapter_narrative: str,
        prerequisites: list[str],
        exclusions: list[str],
        kb_data_dict: dict[str, str],
    ) -> str:
        """Assemble the master prompt from KB context and topic spec (Section 5.1).

        Args:
            topic_data: Must contain ``topic_name``.
            grade: Grade code.
            subject: Subject name.
            chapter_name: Chapter title.
            chapter_narrative: Optional story context.
            prerequisites: Prerequisite concept names.
            exclusions: Concept names to exclude.
            kb_data_dict: Mapping of KB section name → raw markdown content.

        Returns:
            Complete prompt string ready for the Claude API.
        """
        topic_name = topic_data.get("topic_name", "Unknown Topic")
        ceiling = self.kb_loader.get_language_ceiling(grade)
        bloom_dist = self.kb_loader.get_bloom_distribution(grade)
        allowed_interactions = self.kb_loader.get_allowed_interactions(grade)

        bloom_table = ", ".join(f"{k}: {v}" for k, v in sorted(bloom_dist.items()))
        interactions_str = "\n".join(f"  - {t}" for t in allowed_interactions)
        prereq_str = ", ".join(prerequisites) if prerequisites else "None"
        exclusions_str = ", ".join(exclusions) if exclusions else "None"

        parts: list[str] = [
            "# LESSON GENERATION PROMPT — NCERT-ALIGNED, AUDIO-FIRST",
            "",
            "## GLOBAL CONTEXT",
            (
                "You are Claude, an expert educational content designer for NCERT-aligned"
                " lessons for Indian primary school students (Grades K–5)."
            ),
            "",
            "## KNOWLEDGE BASE (Loaded Dynamically)",
            "",
            "[KB SECTION 1: PEDAGOGICAL PRINCIPLES]",
            kb_data_dict.get("pedagogy", "(not loaded)"),
            "",
            f"[KB SECTION 2: LANGUAGE GUIDELINES FOR GRADE {grade}]",
            kb_data_dict.get("language_guidelines", "(not loaded)"),
            "",
            "[KB SECTION 3: BLOOM'S TAXONOMY FRAMEWORK]",
            kb_data_dict.get("bloom_taxonomy", "(not loaded)"),
            "",
            f"[KB SECTION 4: DIGITAL INTERACTIONS FOR GRADE {grade}]",
            kb_data_dict.get("interactions", "(not loaded)"),
            "",
            "[KB SECTION 5: QUESTION BANK & FEEDBACK TEMPLATES]",
            kb_data_dict.get("question_bank", "(not loaded)"),
            "",
            f"[KB SECTION 6: DEFINITIONS & EXAMPLES FOR {subject}]",
            kb_data_dict.get("definitions", "(not loaded)"),
            "",
            "---",
            "",
            "## LESSON SPECIFICATION",
            "",
            f"**Topic:** {topic_name}",
            f"**Grade:** {grade}",
            f"**Subject:** {subject}",
            f"**Chapter:** {chapter_name}",
            f"**Chapter Context:** {chapter_narrative or 'None provided'}",
            "",
            f"**Topic Prerequisites:** {prereq_str}",
            f"**Content to EXCLUDE:** {exclusions_str}",
            "",
            "---",
            "",
            "## INSTRUCTION: GENERATE LESSON STRUCTURE",
            "",
            "Your task is to generate a complete, production-ready lesson for this topic.",
            "",
            "### PHASE 1: PLANNING (Internal, not in output)",
            "1. Identify 3–5 core concepts to teach",
            "2. Map each concept to Bloom's level (L1–L4 for this grade)",
            "3. Select an interactive activity type (must be from the allowed list below)",
            "4. Plan 6–10 quiz checkpoints aligned to Bloom's progression",
            "5. Identify any narrative/story context to weave in",
            "",
            "### PHASE 2: WRITING",
            "Output a JSON structure with the following schema:",
            "",
            "```json",
            "{",
            '  "learning_objective": "Students will be able to...",',
            '  "opening_narration": {',
            '    "line_1": "Good morning, children.",',
            '    "line_2": "Have you ever... [Beat]",',
            '    "line_3": "Today we will learn...",',
            '    "line_4": "Let us begin..."',
            "  },",
            '  "on_screen_opening": {',
            '    "layout": "...",',
            '    "static_elements": [],',
            '    "interactive_elements": [],',
            '    "animation": "..."',
            "  },",
            '  "narrated_explanation": [',
            "    {",
            '      "concept_name": "...",',
            '      "teacher_explains": "...",',
            '      "bloom_level": "L2",',
            '      "on_screen": {},',
            '      "transition": "..."',
            "    }",
            "  ],",
            '  "interactive_activity": {',
            '    "type": "...",',
            '    "bloom_level": "L3",',
            '    "instructions": "...",',
            '    "on_screen": {},',
            '    "feedback_hint_1": "...",',
            '    "feedback_hint_2": "...",',
            '    "feedback_reveal": "..."',
            "  },",
            '  "doubts_discussion": [',
            "    {",
            '      "question": "...",',
            '      "bloom_level": "L2",',
            '      "answer": "...",',
            '      "teacher_clarification": "..."',
            "    }",
            "  ],",
            '  "quick_quiz": [',
            "    {",
            '      "question_number": 1,',
            '      "type": "MCQ",',
            '      "bloom_level": "L1",',
            '      "prompt": "...",',
            '      "options": [],',
            '      "answer": "...",',
            '      "feedback_correct": "...",',
            '      "feedback_incorrect": "..."',
            "    }",
            "  ],",
            '  "conclusion": {',
            '    "recap": "...",',
            '    "real_life_connection": "...",',
            '    "reflection_prompt": "..."',
            "  }",
            "}",
            "```",
            "",
            "---",
            "",
            "## CONSTRAINTS & RULES",
            "",
            "### Audio-First Design",
            "- Every 'Teacher says' line will be spoken aloud by ElevenLabs",
            "- Use [Beat] for 1-second pauses after questions (let child think)",
            "- Use [Pause] for 2-second reflection pauses (once per section)",
            "- Use [Emphasis: word] to mark key vocabulary for vocal stress",
            f"- Keep spoken sentences short ({ceiling.max_sentence_length} words max for this grade)",  # noqa: E501
            "",
            f"### Language Ceiling (Grade {grade})",
            f"- Max sentence length: {ceiling.max_sentence_length} words",
            f"- New vocabulary per lesson: {ceiling.max_new_vocab} maximum",
            f"- Allowed connectors: {', '.join(ceiling.allowed_connectors) or 'simple only'}",
            "",
            "### Bloom's Requirements",
            f"- Quiz must have: {bloom_table}",
            "- Questions must progress L1 → L5 from Q1 → Q10",
            "- Activity must be L3 (Apply) or L4 (Analyze)",
            "",
            f"### Interaction Types — MUST select from this list for Grade {grade}:",
            interactions_str,
            "- Activity type determines visualization method",
            "",
            "### Content Isolation",
            f"- Do NOT teach concepts in: {exclusions_str}",
            f"- Assume prerequisites are met: {prereq_str}",
        ]

        if chapter_narrative:
            parts.append(
                f'- Reference chapter narrative if provided: "{chapter_narrative}"'
            )

        parts.extend(
            [
                "",
                "### Feedback Design",
                "- Correct feedback: Affirm warmly + restate reasoning",
                "- Incorrect feedback (Activities): Provide 3-tier hints (nudge → explicit → reveal)",  # noqa: E501
                "- Incorrect feedback (Quiz): Restate the correct answer + explain why",
                "",
                "---",
                "",
                "## VALIDATION CHECKLIST (System Will Verify)",
                "",
                f"- [ ] No sentence exceeds {ceiling.max_sentence_length} words for Grade {grade}",
                f"- [ ] All new vocabulary ≤ {ceiling.max_new_vocab} for this lesson",
                "- [ ] Bloom's distribution matches grade table",
                f"- [ ] Interaction type in allowed list for Grade {grade}",
                "- [ ] Activity has multi-tier feedback",
                "- [ ] Audio markers ([Beat], [Pause], [Emphasis]) present",
                "- [ ] Quiz progresses L1 → L5",
                "",
                "---",
                "",
                "## OUTPUT FORMAT",
                "",
                (
                    "Return ONLY valid JSON (no markdown fences, no explanation)."
                    " The system will parse, validate, and convert to DOCX."
                ),
            ]
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Claude API calls with retry
    # ------------------------------------------------------------------

    async def _call_claude_with_retry(self, prompt: str) -> dict[str, Any]:
        """Call the Claude API up to _MAX_RETRIES times with exponential back-off.

        Args:
            prompt: Fully assembled lesson generation prompt.

        Returns:
            Parsed lesson dict from Claude's JSON response.

        Raises:
            LessonGenerationError: After all retries are exhausted.
        """
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await self._call_claude(prompt, attempt)
            except (LessonGenerationError, anthropic.APIError) as exc:
                last_exc = exc
                logger.warning(
                    "Claude API attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc
                )
                if attempt < _MAX_RETRIES:
                    wait = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                    logger.info("Retrying in %.1f seconds…", wait)
                    await asyncio.sleep(wait)

        msg = str(last_exc) if last_exc else "Unknown error"
        raise LessonGenerationError(
            f"Lesson generation failed after {_MAX_RETRIES} attempts: {msg}",
            attempt=_MAX_RETRIES,
        )

    async def _call_claude(self, prompt: str, attempt: int = 1) -> dict[str, Any]:
        """Make a single Claude API call and parse the JSON response.

        Args:
            prompt: Assembled lesson generation prompt.
            attempt: Current retry attempt number (for logging).

        Returns:
            Parsed lesson structure dict.

        Raises:
            LessonGenerationError: If the API key is missing, the API call fails,
                or the response cannot be parsed as valid JSON.
        """
        if not self._api_key:
            raise LessonGenerationError(
                "ANTHROPIC_API_KEY is not configured. "
                "Set it via environment variable or .env file."
            )

        logger.debug("Calling Claude API (attempt %d, model=%s)", attempt, _MODEL)

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        try:
            message = await client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIStatusError as exc:
            raise LessonGenerationError(
                f"Claude API status error: {exc.status_code} — {exc.message}"
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LessonGenerationError(f"Claude API connection error: {exc}") from exc

        raw_text: str = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text = block.text
                break

        if not raw_text:
            raise LessonGenerationError("Claude returned an empty response")

        return self._parse_json_response(raw_text)

    def _parse_json_response(self, raw_text: str) -> dict[str, Any]:
        """Extract and parse the JSON payload from Claude's response text.

        Handles responses that may be wrapped in markdown code fences
        (```json ... ```) despite the prompt asking for raw JSON.

        Args:
            raw_text: Raw text content from Claude's response block.

        Returns:
            Parsed lesson structure dict.

        Raises:
            LessonGenerationError: If valid JSON cannot be extracted.
        """
        text = raw_text.strip()

        # Strip optional markdown code fence wrappers
        text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text, flags=re.IGNORECASE)
        text = text.strip()

        try:
            lesson: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse Claude JSON response (first 500 chars): %s",
                text[:500],
            )
            raise LessonGenerationError(
                f"Claude response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(lesson, dict):
            raise LessonGenerationError(
                f"Expected a JSON object from Claude, got {type(lesson).__name__}"
            )

        return lesson
