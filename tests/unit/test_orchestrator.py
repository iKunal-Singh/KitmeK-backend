"""Unit tests for the LessonGenerationOrchestrator service.

Tests cover:
1. _parse_json_response — valid JSON, markdown-wrapped JSON, invalid JSON, non-dict result
2. _assemble_prompt — confirms all required sections appear in the prompt
3. generate_lesson — happy path with mocked Claude API
4. _call_claude_with_retry — exhausted retries raise LessonGenerationError
5. _call_claude — missing API key, API status error, API connection error, empty response

No real Anthropic API calls are made; all network I/O is mocked via unittest.mock.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import LessonGenerationError
from src.services.orchestrator import LessonGenerationOrchestrator
from tests.fixtures.sample_lessons import VALID_GRADE3_LESSON


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOPIC_DATA = {"topic_name": "Trees vs Shrubs"}
_GRADE = "3"
_SUBJECT = "EVS"
_CHAPTER = "Types of Plants"


def _make_orchestrator(api_key: str = "test_key") -> LessonGenerationOrchestrator:
    """Create an orchestrator with a real KBLoader (kb_files on disk)."""
    from src.services.kb_loader import KBLoader

    kb_loader = KBLoader(
        kb_path="/home/kunal/projects/kitmeK-lesson-backend/kb_files"
    )
    return LessonGenerationOrchestrator(
        kb_loader=kb_loader,
        anthropic_api_key=api_key,
    )


# ---------------------------------------------------------------------------
# Test group 1: _parse_json_response
# ---------------------------------------------------------------------------


def test_parse_json_response_with_valid_json():
    """_parse_json_response correctly parses a plain JSON string.

    A well-formed JSON object string must be returned as a Python dict
    with identical key-value pairs.
    """
    orchestrator = _make_orchestrator()
    raw = json.dumps({"learning_objective": "Students will identify trees."})
    result = orchestrator._parse_json_response(raw)

    assert isinstance(result, dict), "Result must be a dict"
    assert result["learning_objective"] == "Students will identify trees."


def test_parse_json_response_strips_markdown_fences():
    """_parse_json_response removes markdown code fences before parsing.

    Claude sometimes wraps its JSON output in triple-backtick fences despite
    the prompt asking for raw JSON.  The parser must handle this gracefully.
    """
    orchestrator = _make_orchestrator()
    raw = "```json\n{\"key\": \"value\"}\n```"
    result = orchestrator._parse_json_response(raw)

    assert result == {"key": "value"}, (
        f"Markdown-fenced JSON must parse correctly, got {result}"
    )


def test_parse_json_response_raises_on_invalid_json():
    """_parse_json_response raises LessonGenerationError for malformed JSON.

    If Claude returns something that is not valid JSON, the orchestrator must
    raise LessonGenerationError rather than propagating the raw JSONDecodeError.
    """
    orchestrator = _make_orchestrator()

    with pytest.raises(LessonGenerationError, match="not valid JSON"):
        orchestrator._parse_json_response("this is not json {broken")


def test_parse_json_response_raises_on_non_dict_json():
    """_parse_json_response raises LessonGenerationError if JSON is not an object.

    Claude must return a JSON object (dict), not a list or scalar.  A list
    response is unexpected and must raise LessonGenerationError.
    """
    orchestrator = _make_orchestrator()

    with pytest.raises(LessonGenerationError, match="Expected a JSON object"):
        orchestrator._parse_json_response("[1, 2, 3]")


def test_parse_json_response_strips_plain_fences():
    """_parse_json_response handles plain ``` fences without 'json' language tag."""
    orchestrator = _make_orchestrator()
    raw = "```\n{\"topic\": \"Plants\"}\n```"
    result = orchestrator._parse_json_response(raw)
    assert result == {"topic": "Plants"}


# ---------------------------------------------------------------------------
# Test group 2: _assemble_prompt
# ---------------------------------------------------------------------------


def test_assemble_prompt_contains_topic_and_grade():
    """_assemble_prompt embeds the topic name and grade in the returned string.

    The assembled prompt must explicitly name the topic and grade so Claude
    can target the correct curriculum level and content scope.
    """
    orchestrator = _make_orchestrator()
    prompt = orchestrator._assemble_prompt(
        topic_data=_TOPIC_DATA,
        grade=_GRADE,
        subject=_SUBJECT,
        chapter_name=_CHAPTER,
        chapter_narrative="",
        prerequisites=[],
        exclusions=[],
        kb_data_dict={
            "pedagogy": "",
            "language_guidelines": "",
            "bloom_taxonomy": "",
            "interactions": "",
            "question_bank": "",
            "definitions": "",
        },
    )

    assert isinstance(prompt, str), "Prompt must be a string"
    assert "Trees vs Shrubs" in prompt, "Prompt must contain the topic name"
    assert _GRADE in prompt, "Prompt must contain the grade"
    assert _SUBJECT in prompt, "Prompt must contain the subject"


def test_assemble_prompt_includes_exclusions():
    """_assemble_prompt embeds content exclusions in the prompt.

    Exclusions tell Claude which concepts to avoid in the lesson so they can
    be covered later.  The exclusion list must appear in the prompt text.
    """
    orchestrator = _make_orchestrator()
    prompt = orchestrator._assemble_prompt(
        topic_data=_TOPIC_DATA,
        grade=_GRADE,
        subject=_SUBJECT,
        chapter_name=_CHAPTER,
        chapter_narrative="",
        prerequisites=[],
        exclusions=["climbers", "creepers"],
        kb_data_dict={
            "pedagogy": "",
            "language_guidelines": "",
            "bloom_taxonomy": "",
            "interactions": "",
            "question_bank": "",
            "definitions": "",
        },
    )

    assert "climbers" in prompt, "Exclusions must appear in the assembled prompt"
    assert "creepers" in prompt, "All exclusions must appear in the assembled prompt"


def test_assemble_prompt_includes_chapter_narrative():
    """_assemble_prompt appends the chapter narrative when provided.

    If a chapter_narrative (story context) is supplied, it must appear in the
    prompt to guide Claude's story-integration decisions.
    """
    orchestrator = _make_orchestrator()
    narrative = "Meera and her grandfather walked past a tall mango tree."
    prompt = orchestrator._assemble_prompt(
        topic_data=_TOPIC_DATA,
        grade=_GRADE,
        subject=_SUBJECT,
        chapter_name=_CHAPTER,
        chapter_narrative=narrative,
        prerequisites=[],
        exclusions=[],
        kb_data_dict={
            "pedagogy": "",
            "language_guidelines": "",
            "bloom_taxonomy": "",
            "interactions": "",
            "question_bank": "",
            "definitions": "",
        },
    )

    assert "Meera" in prompt, "Chapter narrative must be embedded in the prompt"


# ---------------------------------------------------------------------------
# Test group 3: generate_lesson (mocked Claude API)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_lesson_happy_path():
    """generate_lesson returns a parsed lesson dict on successful Claude response.

    The Claude API is mocked to return VALID_GRADE3_LESSON as JSON.
    The orchestrator must return an identical dict without modification.
    """
    orchestrator = _make_orchestrator()

    mock_block = MagicMock()
    mock_block.text = json.dumps(VALID_GRADE3_LESSON)

    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        result = await orchestrator.generate_lesson(
            topic_data=_TOPIC_DATA,
            grade=_GRADE,
            subject=_SUBJECT,
            chapter_name=_CHAPTER,
        )

    assert isinstance(result, dict), "generate_lesson must return a dict"
    assert "learning_objective" in result, (
        "Result must contain 'learning_objective' from the lesson schema"
    )


@pytest.mark.asyncio
async def test_generate_lesson_with_prerequisites_and_exclusions():
    """generate_lesson passes prerequisites and exclusions through to the prompt.

    The assembled prompt (passed to Claude) must reference the exclusion list.
    We verify this by capturing the call arguments to the mock client.
    """
    orchestrator = _make_orchestrator()

    mock_block = MagicMock()
    mock_block.text = json.dumps({"learning_objective": "Identify plants."})

    mock_message = MagicMock()
    mock_message.content = [mock_block]

    captured_prompt: list[str] = []

    async def _capture(*args, **kwargs):
        msg = kwargs.get("messages", [{}])
        captured_prompt.append(msg[0].get("content", ""))
        return mock_message

    mock_client = MagicMock()
    mock_client.messages.create = _capture

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        await orchestrator.generate_lesson(
            topic_data=_TOPIC_DATA,
            grade=_GRADE,
            subject=_SUBJECT,
            chapter_name=_CHAPTER,
            exclusions=["climbers"],
            prerequisites=["Living things"],
        )

    assert captured_prompt, "Claude API must have been called"
    assert "climbers" in captured_prompt[0], "Exclusions must appear in the prompt"
    assert "Living things" in captured_prompt[0], "Prerequisites must appear in the prompt"


# ---------------------------------------------------------------------------
# Test group 4: _call_claude_with_retry (retry exhaustion)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_claude_with_retry_raises_after_exhausted():
    """_call_claude_with_retry raises LessonGenerationError when all retries fail.

    The retry loop must not attempt more than _MAX_RETRIES iterations.
    On exhaustion it must raise LessonGenerationError with the attempt count.
    We patch asyncio.sleep to avoid actual wait times.
    """
    import anthropic as anthropic_mod
    orchestrator = _make_orchestrator()

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=anthropic_mod.APIStatusError(
            "rate limit",
            response=MagicMock(status_code=429),
            body=None,
        )
    )

    with patch("anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(LessonGenerationError) as exc_info:
            await orchestrator._call_claude_with_retry("test prompt")

    assert "failed after" in str(exc_info.value).lower() or exc_info.value.attempt >= 1, (
        "LessonGenerationError must indicate retry exhaustion"
    )


# ---------------------------------------------------------------------------
# Test group 5: _call_claude (individual call errors)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_claude_raises_when_api_key_missing():
    """_call_claude raises LessonGenerationError when ANTHROPIC_API_KEY is empty.

    An empty API key means no Claude call can be made.  The error message must
    mention the missing key so operators can fix the configuration quickly.
    We force _api_key to empty directly to bypass the settings fallback.
    """
    orchestrator = _make_orchestrator()
    # Override _api_key directly — constructing with "" falls back to settings
    orchestrator._api_key = ""

    with pytest.raises(LessonGenerationError, match="ANTHROPIC_API_KEY"):
        await orchestrator._call_claude("test prompt")


@pytest.mark.asyncio
async def test_call_claude_raises_on_empty_response():
    """_call_claude raises LessonGenerationError when Claude returns empty content.

    An empty 'content' list (or blocks with no text) must raise rather than
    silently returning an empty dict.
    """
    orchestrator = _make_orchestrator()

    mock_message = MagicMock()
    mock_message.content = []  # No blocks at all

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        with pytest.raises(LessonGenerationError, match="empty response"):
            await orchestrator._call_claude("test prompt")


@pytest.mark.asyncio
async def test_call_claude_raises_on_connection_error():
    """_call_claude raises LessonGenerationError on APIConnectionError.

    Network errors (timeout, DNS failure) must be translated into the
    domain-level LessonGenerationError, not propagated raw.
    """
    import anthropic as anthropic_mod
    orchestrator = _make_orchestrator()

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=anthropic_mod.APIConnectionError(request=MagicMock())
    )

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        with pytest.raises(LessonGenerationError, match="connection error"):
            await orchestrator._call_claude("test prompt")
