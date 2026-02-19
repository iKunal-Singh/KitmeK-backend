"""SQLAlchemy ORM model for the subjects table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.chapter import Chapter
    from src.models.grade import Grade


class Subject(Base):
    """Subjects offered per grade (EVS, Math, English, Hindi).

    Attributes:
        id: Auto-incrementing primary key.
        grade_id: Foreign key to grades table.
        subject_name: Full subject name.
        subject_code: Short code (e.g. 'EVS', 'MATH').
        created_at: Timestamp of record creation.
        grade: Relationship to parent grade.
        chapters: Relationship to chapters in this subject.
    """

    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("grade_id", "subject_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="CASCADE"), nullable=False
    )
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_code: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    grade: Mapped[Grade] = relationship("Grade", back_populates="subjects")
    chapters: Mapped[List[Chapter]] = relationship(
        "Chapter", back_populates="subject", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, code='{self.subject_code}')>"
