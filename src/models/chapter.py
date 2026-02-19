"""SQLAlchemy ORM model for the chapters table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.subject import Subject
    from src.models.topic import Topic


class Chapter(Base):
    """Chapters within a subject (e.g. 'Types of Plants').

    Attributes:
        id: Auto-incrementing primary key.
        subject_id: Foreign key to subjects table.
        chapter_number: Chapter number within the subject.
        chapter_name: Human-readable chapter name.
        chapter_description: Optional description text.
        sequence_number: Ordering within subject.
        created_at: Timestamp of record creation.
        subject: Relationship to parent subject.
        topics: Relationship to topics in this chapter.
    """

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("subject_id", "chapter_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chapter_name: Mapped[str] = mapped_column(String(200), nullable=False)
    chapter_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    subject: Mapped[Subject] = relationship("Subject", back_populates="chapters")
    topics: Mapped[List[Topic]] = relationship(
        "Topic", back_populates="chapter", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, name='{self.chapter_name}')>"
