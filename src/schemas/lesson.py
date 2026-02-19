"""Pydantic v2 schemas for lesson status, topic, KB, and health responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.validation import ValidationReport


class LessonStatusResponse(BaseModel):
    """Response for GET /lessons/{request_id} polling endpoint.

    Attributes:
        request_id: UUID of the generation request.
        status: Current status.
        completion_percentage: Progress from 0 to 100.
        message: Human-readable status message.
        validation_report: Validation results (when completed).
        generation_time_seconds: Time taken (when completed).
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    request_id: str
    status: str = Field(..., pattern=r"^(pending|processing|completed|failed)$")
    completion_percentage: int = Field(default=0, ge=0, le=100)
    message: str = Field(default="")
    validation_report: ValidationReport | None = None
    generation_time_seconds: float | None = None


class TopicSummary(BaseModel):
    """Summary of a topic for list responses.

    Attributes:
        id: Topic primary key.
        topic_name: Topic name.
        topic_number: Number within chapter.
        chapter_name: Parent chapter name.
        grade: Grade code.
        subject: Subject code.
        prerequisites: List of prerequisite topic IDs.
        exclusions: List of excluded concept names.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    id: int
    topic_name: str
    topic_number: int
    chapter_name: str
    grade: str
    subject: str
    prerequisites: list[int] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class TopicListResponse(BaseModel):
    """Response for GET /topics.

    Attributes:
        topics: List of topic summaries.
        count: Total number of topics returned.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    topics: list[TopicSummary]
    count: int


class TopicDetailResponse(BaseModel):
    """Response for GET /topics/{topic_id}.

    Attributes:
        id: Topic primary key.
        topic_name: Topic name.
        topic_number: Number within chapter.
        topic_description: Optional description.
        chapter_name: Parent chapter name.
        chapter_number: Chapter number.
        grade: Grade code.
        subject: Subject code.
        sequence_number: Ordering within chapter.
        prerequisites: List of prerequisite topic IDs.
        exclusions: List of excluded concept names.
        context_narrative: Story frame from chapter.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    id: int
    topic_name: str
    topic_number: int
    topic_description: str | None = None
    chapter_name: str
    chapter_number: int
    grade: str
    subject: str
    sequence_number: int
    prerequisites: list[int] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    context_narrative: str | None = None


class HealthResponse(BaseModel):
    """Response for GET /health.

    Attributes:
        status: Service status.
        uptime_seconds: Seconds since service start.
        kb_version: Active KB version string.
        database: Database connection status.
        timestamp: Current server time.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    status: str = Field(..., pattern=r"^(ok|degraded|error)$")
    uptime_seconds: float | None = None
    kb_version: str | None = None
    database: str = Field(default="disconnected", pattern=r"^(connected|disconnected)$")
    timestamp: datetime


class KBVersionResponse(BaseModel):
    """Response for GET /kb/version.

    Attributes:
        kb_version: Version string.
        timestamp: When this version was created.
        files_checksum: SHA256 checksum of KB files.
        is_active: Whether this is the active version.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    kb_version: str
    timestamp: datetime
    files_checksum: str | None = None
    is_active: bool = True


class KBReloadResponse(BaseModel):
    """Response for POST /kb/reload.

    Attributes:
        status: Always 'success' on success.
        new_version: Newly created version string.
        previous_version: Previously active version.
        timestamp: When the reload occurred.
        files_loaded: List of KB file names loaded.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    status: str = Field(default="success")
    new_version: str
    previous_version: str | None = None
    timestamp: datetime
    files_loaded: list[str] = Field(default_factory=list)
