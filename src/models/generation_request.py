"""SQLAlchemy ORM model for the generation_requests table."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.generated_lesson import GeneratedLesson
    from src.models.knowledge_base import KnowledgeBaseVersion
    from src.models.topic import Topic


class GenerationRequest(Base):
    """Lesson generation request lifecycle tracker.

    Attributes:
        id: UUID primary key, auto-generated.
        topic_id: Foreign key to topics table.
        kb_version_id: Foreign key to knowledge_base_versions table.
        request_timestamp: When the request was received.
        requested_by: User or system identifier.
        status: One of pending, processing, completed, failed.
        priority: Priority level (higher = more urgent).
        created_at: Timestamp of record creation.
        updated_at: Timestamp of last update.
        topic: Relationship to the requested topic.
        kb_version_rel: Relationship to the KB version used.
        generated_lessons: Relationship to generated lesson outputs.
    """

    __tablename__ = "generation_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    kb_version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base_versions.id", ondelete="RESTRICT"), nullable=False
    )
    request_timestamp: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )
    requested_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    topic: Mapped[Topic] = relationship("Topic", back_populates="generation_requests")
    kb_version_rel: Mapped[KnowledgeBaseVersion] = relationship(
        "KnowledgeBaseVersion", back_populates="generation_requests"
    )
    generated_lessons: Mapped[List[GeneratedLesson]] = relationship(
        "GeneratedLesson", back_populates="request", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GenerationRequest(id={self.id}, status='{self.status}')>"
