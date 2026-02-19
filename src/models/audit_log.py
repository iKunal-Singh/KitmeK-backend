"""SQLAlchemy ORM model for the audit_log table."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class AuditLog(Base):
    """Immutable event log for traceability and debugging.

    Attributes:
        id: Auto-incrementing bigint primary key.
        request_id: Optional UUID linking to a generation request.
        event_type: Event identifier (e.g. 'lesson_generated').
        event_details: Structured event data as JSONB.
        severity: One of info, warning, error.
        created_at: Timestamp of record creation.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="CURRENT_TIMESTAMP", index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, type='{self.event_type}', "
            f"severity='{self.severity}')>"
        )
