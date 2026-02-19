"""SQLAlchemy ORM model for the generated_lessons table."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.generation_request import GenerationRequest
    from src.models.topic import Topic


class GeneratedLesson(Base):
    """Generated lesson output with DOCX, metadata, and validation report.

    Attributes:
        id: UUID primary key, auto-generated.
        request_id: Foreign key to generation_requests table.
        topic_id: Foreign key to topics table.
        lesson_content_docx: Binary DOCX file content.
        lesson_metadata: Structured lesson data as JSONB.
        validation_report: Validation check results as JSONB.
        generation_timestamp: When the lesson was generated.
        generation_time_seconds: How long generation took.
        created_at: Timestamp of record creation.
        request: Relationship to the parent generation request.
        topic: Relationship to the topic this lesson covers.
    """

    __tablename__ = "generated_lessons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    lesson_content_docx: Mapped[bytes | None] = mapped_column(nullable=True)
    lesson_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    generation_timestamp: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )
    generation_time_seconds: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    request: Mapped[GenerationRequest] = relationship(
        "GenerationRequest", back_populates="generated_lessons"
    )
    topic: Mapped[Topic] = relationship("Topic", back_populates="generated_lessons")

    def __repr__(self) -> str:
        return f"<GeneratedLesson(id={self.id}, request_id={self.request_id})>"
