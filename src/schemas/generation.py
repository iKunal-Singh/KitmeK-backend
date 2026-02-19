"""Pydantic v2 schemas for lesson generation request/response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.validation import ValidationReport


class GenerationRequest(BaseModel):
    """Request payload for POST /lessons/generate.

    Attributes:
        topic_id: ID of the topic to generate a lesson for.
        kb_version: KB version to use (defaults to active version).
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    topic_id: int = Field(..., gt=0, description="ID of the topic to generate a lesson for")
    kb_version: str | None = Field(
        default=None, description="KB version to use (defaults to active version)"
    )


class GenerationResponse(BaseModel):
    """Response payload for POST /lessons/generate.

    Attributes:
        request_id: UUID of the generation request.
        status: Current status of the request.
        docx_url: Download URL for the DOCX (when completed).
        validation_report: Validation results (when available).
        generation_time_seconds: Time taken in seconds (when completed).
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    request_id: str = Field(..., description="UUID of the generation request")
    status: str = Field(
        ...,
        pattern=r"^(pending|processing|completed|failed)$",
        description="Current request status",
    )
    docx_url: str | None = Field(
        default=None, description="Download URL for DOCX"
    )
    validation_report: ValidationReport | None = Field(
        default=None, description="Validation results"
    )
    generation_time_seconds: float | None = Field(
        default=None, description="Generation time in seconds"
    )
