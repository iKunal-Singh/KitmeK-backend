"""Pydantic v2 schemas for validation report structures."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidationCheck(BaseModel):
    """A single validation check result.

    Attributes:
        name: Check identifier (e.g. 'language_ceiling').
        status: One of 'passed', 'failed', 'skipped'.
        grade: Grade code this check was run for.
        details: Arbitrary detail data for the check.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    name: str = Field(..., description="Check identifier")
    status: str = Field(..., pattern=r"^(passed|failed|skipped)$")
    grade: str | None = Field(default=None, description="Grade code")
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationWarning(BaseModel):
    """A validation warning (non-blocking).

    Attributes:
        type: Warning category.
        message: Human-readable warning message.
        severity: One of 'low', 'medium', 'high'.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    type: str
    message: str
    severity: str = Field(..., pattern=r"^(low|medium|high)$")


class ValidationReport(BaseModel):
    """Complete validation report for a generated lesson.

    Attributes:
        passed: Whether all checks passed.
        checks: List of individual check results.
        warnings: Non-blocking validation warnings.
        errors: List of error messages.
        overall_score: Aggregate score from 0.0 to 1.0.
    """

    model_config = ConfigDict(strict=False, populate_by_name=True)

    passed: bool
    checks: list[ValidationCheck] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
