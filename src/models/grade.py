"""SQLAlchemy ORM model for the grades table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.subject import Subject


class Grade(Base):
    """NCERT grade levels K–5.

    Attributes:
        id: Auto-incrementing primary key.
        grade_code: Short code such as 'K', '1', '2', '3', '4', '5'.
        grade_name: Human-readable name (e.g. 'Kindergarten').
        age_range: Typical age range (e.g. '4-5').
        created_at: Timestamp of record creation.
        subjects: Relationship to subjects offered in this grade.
    """

    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grade_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    grade_name: Mapped[str] = mapped_column(String(50), nullable=False)
    age_range: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    subjects: Mapped[List[Subject]] = relationship(
        "Subject", back_populates="grade", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Grade(id={self.id}, code='{self.grade_code}')>"
