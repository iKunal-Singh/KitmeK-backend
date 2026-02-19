"""SQLAlchemy ORM model for the topics table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.chapter import Chapter
    from src.models.generated_lesson import GeneratedLesson
    from src.models.generation_request import GenerationRequest


class Topic(Base):
    """Individual topics within a chapter. Leaf node of curriculum hierarchy.

    Attributes:
        id: Auto-incrementing primary key.
        chapter_id: Foreign key to chapters table.
        topic_number: Topic number within the chapter.
        topic_name: Human-readable topic name.
        topic_description: Optional description text.
        sequence_number: Ordering within chapter.
        prerequisites: JSON string of prerequisite topic IDs.
        exclusions: JSON string of excluded topic IDs.
        context_narrative: Story or narrative frame from chapter.
        created_at: Timestamp of record creation.
        chapter: Relationship to parent chapter.
        generation_requests: Relationship to lesson generation requests.
        generated_lessons: Relationship to generated lessons.
    """

    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("chapter_id", "topic_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    topic_number: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    topic_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusions: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    chapter: Mapped[Chapter] = relationship("Chapter", back_populates="topics")
    generation_requests: Mapped[List[GenerationRequest]] = relationship(
        "GenerationRequest", back_populates="topic"
    )
    generated_lessons: Mapped[List[GeneratedLesson]] = relationship(
        "GeneratedLesson", back_populates="topic"
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name='{self.topic_name}')>"
