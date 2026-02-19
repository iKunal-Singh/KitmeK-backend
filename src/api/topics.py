"""Topics API routes — full implementation.

Provides:
    GET /topics               — List topics, filterable by grade, subject, chapter.
    GET /topics/{topic_id}    — Retrieve full details of a single topic.

Topics are the leaf nodes of the NCERT curriculum hierarchy:
Grade → Subject → Chapter → Topic
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import DBDep
from src.models.chapter import Chapter
from src.models.grade import Grade
from src.models.subject import Subject
from src.models.topic import Topic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TopicListItem(BaseModel):
    """Compact topic representation for list responses."""

    id: int
    topic_name: str
    topic_number: int
    chapter_id: int
    chapter_name: str
    grade: str
    subject: str
    prerequisites: list[int]
    exclusions: list[int]
    sequence_number: int


class TopicDetail(BaseModel):
    """Full topic representation including narrative and description."""

    id: int
    topic_name: str
    topic_number: int
    topic_description: str | None
    chapter_id: int
    chapter_name: str
    grade: str
    subject: str
    prerequisites: list[int]
    exclusions: list[int]
    context_narrative: str | None
    sequence_number: int


class TopicListResponse(BaseModel):
    """Paginated list of topics."""

    topics: list[TopicListItem]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json_ids(value: str | None) -> list[int]:
    """Parse a JSON-encoded list of ints stored in a text column.

    Args:
        value: Raw JSON string from the DB (e.g. ``"[1, 2, 3]"``).

    Returns:
        List of integer IDs, or empty list on any parse error.
    """
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [int(x) for x in parsed if isinstance(x, (int, float, str))]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return []


async def _load_topic_context(db: AsyncSession, topic: Topic) -> dict[str, Any]:
    """Fetch the grade, subject, and chapter context for a topic.

    Args:
        db: Async database session.
        topic: The ``Topic`` ORM instance.

    Returns:
        dict with keys ``grade``, ``subject``, ``chapter_name``.
    """
    chapter = await db.get(Chapter, topic.chapter_id)
    grade_code = ""
    subject_name = ""
    chapter_name = ""

    if chapter:
        chapter_name = chapter.chapter_name
        subject = await db.get(Subject, chapter.subject_id)
        if subject:
            subject_name = subject.subject_name
            grade = await db.get(Grade, subject.grade_id)
            if grade:
                grade_code = grade.grade_code

    return {"grade": grade_code, "subject": subject_name, "chapter_name": chapter_name}


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=TopicListResponse,
    summary="List available topics",
    description=(
        "Return all topics in the curriculum, with optional filters by grade, "
        "subject name (or code), and chapter name. Results are ordered by "
        "grade → subject → chapter → sequence_number."
    ),
    responses={
        200: {"description": "Topic list (may be empty if no data seeded)"},
        500: {"description": "Database error"},
    },
)
async def list_topics(
    db: DBDep,
    grade: str | None = Query(
        default=None,
        description="Filter by grade code (K, 1, 2, 3, 4, 5)",
        pattern=r"^[K1-5]$",
    ),
    subject: str | None = Query(
        default=None,
        description="Filter by subject name or code (case-insensitive)",
    ),
    chapter: str | None = Query(
        default=None,
        description="Filter by chapter name (partial match, case-insensitive)",
    ),
) -> TopicListResponse:
    """Retrieve a list of topics with optional filtering.

    Args:
        db: Injected async database session.
        grade: Optional grade-code filter (e.g. ``"3"``).
        subject: Optional subject name/code filter.
        chapter: Optional chapter name substring filter.

    Returns:
        :class:`TopicListResponse` with matching topics.
    """
    try:
        # Build the base query: topics ⊲ chapters ⊲ subjects ⊲ grades
        stmt = (
            select(Topic, Chapter, Subject, Grade)
            .join(Chapter, Topic.chapter_id == Chapter.id)
            .join(Subject, Chapter.subject_id == Subject.id)
            .join(Grade, Subject.grade_id == Grade.id)
        )

        # Apply filters
        if grade is not None:
            stmt = stmt.where(Grade.grade_code == grade)
        if subject is not None:
            upper_subject = subject.upper()
            stmt = stmt.where(
                (Subject.subject_name.ilike(f"%{subject}%"))
                | (Subject.subject_code.ilike(f"%{subject}%"))
                | (Subject.subject_code == upper_subject)
            )
        if chapter is not None:
            stmt = stmt.where(Chapter.chapter_name.ilike(f"%{chapter}%"))

        # Order: grade asc → subject asc → chapter asc → sequence_number asc
        stmt = stmt.order_by(
            Grade.grade_code,
            Subject.subject_name,
            Chapter.sequence_number,
            Topic.sequence_number,
        )

        result = await db.execute(stmt)
        rows = result.all()

        items: list[TopicListItem] = []
        for topic_row, chapter_row, subject_row, grade_row in rows:
            items.append(
                TopicListItem(
                    id=topic_row.id,
                    topic_name=topic_row.topic_name,
                    topic_number=topic_row.topic_number,
                    chapter_id=topic_row.chapter_id,
                    chapter_name=chapter_row.chapter_name,
                    grade=grade_row.grade_code,
                    subject=subject_row.subject_name,
                    prerequisites=_parse_json_ids(topic_row.prerequisites),
                    exclusions=_parse_json_ids(topic_row.exclusions),
                    sequence_number=topic_row.sequence_number,
                )
            )

        return TopicListResponse(topics=items, total=len(items))

    except Exception as exc:
        logger.exception("Error fetching topic list: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error fetching topics: {exc}",
        )


@router.get(
    "/{topic_id}",
    response_model=TopicDetail,
    summary="Get topic details",
    description=(
        "Return full details of a specific topic by its integer ID, including "
        "the context narrative, prerequisites, and exclusion list."
    ),
    responses={
        200: {"description": "Topic details"},
        404: {"description": "Topic not found"},
        500: {"description": "Database error"},
    },
)
async def get_topic(
    topic_id: int,
    db: DBDep,
) -> TopicDetail:
    """Retrieve a single topic by primary key.

    Args:
        topic_id: Integer primary key from the ``topics`` table.
        db: Injected async database session.

    Returns:
        :class:`TopicDetail` with full topic information.

    Raises:
        HTTPException: 404 if the topic is not found, 500 on DB error.
    """
    try:
        topic = await db.get(Topic, topic_id)
    except Exception as exc:
        logger.exception("Database error fetching topic %d: %s", topic_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with id={topic_id} not found",
        )

    ctx = await _load_topic_context(db, topic)

    return TopicDetail(
        id=topic.id,
        topic_name=topic.topic_name,
        topic_number=topic.topic_number,
        topic_description=topic.topic_description,
        chapter_id=topic.chapter_id,
        chapter_name=ctx["chapter_name"],
        grade=ctx["grade"],
        subject=ctx["subject"],
        prerequisites=_parse_json_ids(topic.prerequisites),
        exclusions=_parse_json_ids(topic.exclusions),
        context_narrative=topic.context_narrative,
        sequence_number=topic.sequence_number,
    )
