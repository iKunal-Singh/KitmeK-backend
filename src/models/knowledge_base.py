"""SQLAlchemy ORM models for knowledge base tables."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class KnowledgeBaseVersion(Base):
    """Versioned snapshots of KB files. One active version at a time.

    Attributes:
        id: Auto-incrementing primary key.
        kb_version: Version string (e.g. '1.0', '1.1').
        timestamp: When this version was created.
        language_guidelines: Raw markdown bytes for language guidelines.
        blooms_taxonomy: Raw markdown bytes for Bloom's taxonomy.
        ncert_pedagogy: Raw markdown bytes for NCERT pedagogy.
        digital_interactions: Raw markdown bytes for digital interactions.
        question_bank: Raw markdown bytes for question bank.
        definitions_examples: Raw markdown bytes for definitions (optional).
        checksum: SHA256 of all KB files combined.
        is_active: Whether this is the currently active version.
        created_at: Timestamp of record creation.
        generation_requests: Requests that used this KB version.
        constraint_caches: Pre-parsed constraint lookups.
    """

    __tablename__ = "knowledge_base_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kb_version: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )
    language_guidelines: Mapped[bytes | None] = mapped_column(nullable=True)
    blooms_taxonomy: Mapped[bytes | None] = mapped_column(nullable=True)
    ncert_pedagogy: Mapped[bytes | None] = mapped_column(nullable=True)
    digital_interactions: Mapped[bytes | None] = mapped_column(nullable=True)
    question_bank: Mapped[bytes | None] = mapped_column(nullable=True)
    definitions_examples: Mapped[bytes | None] = mapped_column(nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    generation_requests: Mapped[List["GenerationRequest"]] = relationship(  # noqa: F821
        "GenerationRequest", back_populates="kb_version_rel"
    )
    constraint_caches: Mapped[List[KBConstraintCache]] = relationship(
        "KBConstraintCache",
        back_populates="kb_version_rel",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBaseVersion(id={self.id}, version='{self.kb_version}', active={self.is_active})>"


class KBConstraintCache(Base):
    """Pre-parsed KB constraints for fast per-grade lookups during validation.

    Attributes:
        id: Auto-incrementing primary key.
        kb_version_id: Foreign key to knowledge_base_versions.
        constraint_type: Type of constraint (e.g. 'language_ceiling').
        grade_code: Grade this constraint applies to.
        constraint_json: Normalized constraint data as JSONB.
        created_at: Timestamp of record creation.
        kb_version_rel: Relationship to parent KB version.
    """

    __tablename__ = "kb_constraint_cache"
    __table_args__ = (
        UniqueConstraint("kb_version_id", "constraint_type", "grade_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kb_version_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_base_versions.id", ondelete="CASCADE"), nullable=False
    )
    constraint_type: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    constraint_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    kb_version_rel: Mapped[KnowledgeBaseVersion] = relationship(
        "KnowledgeBaseVersion", back_populates="constraint_caches"
    )

    def __repr__(self) -> str:
        return (
            f"<KBConstraintCache(id={self.id}, type='{self.constraint_type}', "
            f"grade='{self.grade_code}')>"
        )
