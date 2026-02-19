"""
Lesson generation API endpoints — POST /lessons/generate and GET /lessons/{id}/download.

Implements the full 10-step generation pipeline from Architecture Doc Section 4.3.5.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chapter import Chapter
from src.models.grade import Grade
from src.models.subject import Subject

from src.api.dependencies import KBLoaderDep
from src.database import get_async_db
from src.models.audit_log import AuditLog
from src.models.generated_lesson import GeneratedLesson
from src.models.generation_request import GenerationRequest as GenerationRequestModel
from src.models.knowledge_base import KnowledgeBaseVersion
from src.models.topic import Topic
from src.schemas.generation import (
    GenerationRequest as GenerationRequestSchema,
    GenerationResponse,
)
from src.schemas.validation import ValidationCheck, ValidationReport, ValidationWarning
from src.services.docx_generator import DocxGenerator
from src.services.kb_loader import KBLoader
from src.services.validator import LessonValidator
from src.services.validator import ValidationReport as InternalValidationReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lessons", tags=["lessons"])

# Singleton service instances
_validator = LessonValidator()
_docx_generator = DocxGenerator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_field(value: str | None) -> list[Any]:
    """Parse a JSON string stored in a text column, returning a list."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _convert_internal_report_to_schema(
    internal: InternalValidationReport,
    grade: str = "",
) -> ValidationReport:
    """Convert the validator's dataclass report to the Pydantic schema."""
    checks: list[ValidationCheck] = []
    warnings: list[ValidationWarning] = []
    errors: list[str] = []

    for c in internal.checks:
        # Map internal "warning" status to schema-compatible "passed"
        # and add to warnings list
        if c.status == "warning":
            checks.append(ValidationCheck(
                name=c.name,
                status="passed",
                grade=grade,
                details=c.details,
            ))
            warnings.append(ValidationWarning(
                type=c.name,
                message=c.message or f"Warning in {c.name}",
                severity="low",
            ))
        else:
            checks.append(ValidationCheck(
                name=c.name,
                status=c.status,
                grade=grade,
                details=c.details,
            ))
            if c.status == "failed":
                errors.append(c.message or f"Check {c.name} failed")

    return ValidationReport(
        passed=internal.passed,
        checks=checks,
        warnings=warnings,
        errors=errors,
        overall_score=internal.overall_score,
    )


async def _get_active_kb_version(db: AsyncSession) -> KnowledgeBaseVersion | None:
    """Get the currently active KB version."""
    stmt = select(KnowledgeBaseVersion).where(KnowledgeBaseVersion.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _write_audit_log(
    db: AsyncSession,
    request_id: uuid.UUID,
    event_type: str,
    event_details: dict[str, Any],
    severity: str = "info",
) -> None:
    """Write an entry to the audit log."""
    try:
        log = AuditLog(
            request_id=request_id,
            event_type=event_type,
            event_details=event_details,
            severity=severity,
        )
        db.add(log)
    except Exception as exc:
        logger.error("Failed to write audit log: %s", exc)


async def _call_orchestrator(
    topic: Topic,
    grade: str,
    subject: str,
    chapter_name: str,
    kb_loader: KBLoader,
    chapter_narrative: str = "",
    prerequisites: list[str] | None = None,
    exclusions: list[str] | None = None,
) -> dict[str, Any]:
    """
    Call the lesson generation orchestrator.

    Args:
        topic: Topic model instance.
        grade: Grade code (K, 1-5).
        subject: Subject name (e.g. "EVS").
        chapter_name: Chapter title.
        kb_loader: Loaded KBLoader instance.
        chapter_narrative: Optional story context.
        prerequisites: Prerequisite concepts (if any).
        exclusions: Concepts to exclude (if any).

    Returns:
        Generated lesson dict from Claude.

    Raises:
        HTTPException: If orchestrator is unavailable or generation fails.
    """
    try:
        from src.services.orchestrator import LessonGenerationOrchestrator

        orchestrator = LessonGenerationOrchestrator(kb_loader=kb_loader)
        topic_data = {
            "topic_name": topic.topic_name,
        }
        lesson_data = await orchestrator.generate_lesson(
            topic_data=topic_data,
            grade=grade,
            subject=subject,
            chapter_name=chapter_name,
            chapter_narrative=chapter_narrative,
            prerequisites=prerequisites,
            exclusions=exclusions,
        )
        return lesson_data
    except ImportError:
        logger.error(
            "Orchestrator service not available. "
            "Ensure src/services/orchestrator.py is implemented."
        )
        raise HTTPException(
            status_code=503,
            detail="Lesson generation orchestrator is not yet configured. "
                   "The orchestrator service must be implemented.",
        )
    except Exception as exc:
        logger.error("Orchestrator error: %s", exc)
        raise


# ---------------------------------------------------------------------------
# POST /lessons/generate
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=200,
    summary="Generate a lesson for a topic",
    responses={
        404: {"description": "Topic not found"},
        422: {"description": "Validation failed"},
        503: {"description": "Orchestrator unavailable"},
    },
)
async def generate_lesson(
    payload: GenerationRequestSchema,
    db: AsyncSession = Depends(get_async_db),
    kb_loader: KBLoaderDep = ...,
) -> GenerationResponse:
    """
    Generate a complete NCERT-aligned lesson.

    Pipeline steps:
    1. Validate topic_id exists -> 404 if not
    2. Create GenerationRequest (status='processing')
    3. orchestrator.generate_lesson(topic, kb_loader)
    4. validator.validate(lesson_data, grade, subject)
    5. If validation fails -> status='failed', return 422
    6. docx_generator.generate(lesson_data) -> bytes
    7. Store GeneratedLesson in DB
    8. Update GenerationRequest status='completed'
    9. Write AuditLog entry
    10. Return: request_id, status, docx_url, validation_report, generation_time_seconds
    """
    start_time = time.time()

    # ----------------------------------------------------------------
    # Step 1: Validate topic_id exists
    # ----------------------------------------------------------------
    topic = await db.get(Topic, payload.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {payload.topic_id} not found")

    # Eagerly load the hierarchy for grade/subject info
    chapter_stmt = select(Chapter).where(Chapter.id == topic.chapter_id)
    chapter_result = await db.execute(chapter_stmt)
    chapter = chapter_result.scalar_one_or_none()

    grade_code = ""
    subject_code = ""
    chapter_name = ""

    if chapter:
        chapter_name = chapter.chapter_name
        subject_stmt = select(Subject).where(Subject.id == chapter.subject_id)
        subject_result = await db.execute(subject_stmt)
        subject_obj = subject_result.scalar_one_or_none()
        if subject_obj:
            subject_code = subject_obj.subject_code
            grade_stmt = select(Grade).where(Grade.id == subject_obj.grade_id)
            grade_result = await db.execute(grade_stmt)
            grade_obj = grade_result.scalar_one_or_none()
            if grade_obj:
                grade_code = grade_obj.grade_code

    # Get active KB version
    kb_version = None
    if payload.kb_version:
        kb_stmt = select(KnowledgeBaseVersion).where(
            KnowledgeBaseVersion.kb_version == payload.kb_version
        )
        kb_result = await db.execute(kb_stmt)
        kb_version = kb_result.scalar_one_or_none()
    else:
        kb_version = await _get_active_kb_version(db)

    # Use a fallback KB version ID if none found (for early development)
    kb_version_id = kb_version.id if kb_version else 1

    # ----------------------------------------------------------------
    # Step 2: Create GenerationRequest (status='processing')
    # ----------------------------------------------------------------
    gen_request = GenerationRequestModel(
        topic_id=payload.topic_id,
        kb_version_id=kb_version_id,
        status="processing",
    )
    db.add(gen_request)
    await db.flush()  # Persist to get the UUID

    request_id = gen_request.id
    logger.info("Generation request %s created for topic %s", request_id, payload.topic_id)

    try:
        # ----------------------------------------------------------------
        # Step 3: Call orchestrator
        # ----------------------------------------------------------------
        exclusions = _parse_json_field(topic.exclusions)
        prerequisites = _parse_json_field(topic.prerequisites)
        chapter_narrative = topic.context_narrative or ""

        lesson_data = await _call_orchestrator(
            topic=topic,
            grade=grade_code,
            subject=subject_code,
            chapter_name=chapter_name,
            kb_loader=kb_loader,
            chapter_narrative=chapter_narrative,
            prerequisites=prerequisites,
            exclusions=exclusions,
        )

        # ----------------------------------------------------------------
        # Step 4: Validate lesson data
        # ----------------------------------------------------------------
        internal_report = await _validator.validate(
            lesson_data=lesson_data,
            grade=grade_code,
            subject=subject_code,
            exclusions=exclusions,
            prerequisites=prerequisites,
            context_narrative=chapter_narrative,
        )

        schema_report = _convert_internal_report_to_schema(internal_report, grade=grade_code)

        # ----------------------------------------------------------------
        # Step 5: If validation fails -> status='failed', return 422
        # ----------------------------------------------------------------
        if not internal_report.passed:
            gen_request.status = "failed"
            gen_request.updated_at = datetime.utcnow()

            generation_time = round(time.time() - start_time, 2)

            # Store failed lesson for debugging
            failed_lesson = GeneratedLesson(
                request_id=request_id,
                topic_id=payload.topic_id,
                lesson_metadata=lesson_data,
                validation_report=schema_report.model_dump(),
                generation_time_seconds=Decimal(str(generation_time)),
            )
            db.add(failed_lesson)

            await _write_audit_log(
                db,
                request_id=request_id,
                event_type="validation_failed",
                event_details={
                    "topic_id": payload.topic_id,
                    "grade": grade_code,
                    "errors": schema_report.errors,
                    "generation_time_seconds": generation_time,
                },
                severity="warning",
            )

            await db.flush()

            raise HTTPException(
                status_code=422,
                detail={
                    "request_id": str(request_id),
                    "status": "failed",
                    "validation_report": schema_report.model_dump(),
                    "generation_time_seconds": generation_time,
                    "message": "Lesson failed validation checks",
                },
            )

        # ----------------------------------------------------------------
        # Step 6: Generate DOCX
        # ----------------------------------------------------------------
        docx_bytes = _docx_generator.generate(
            lesson_data=lesson_data,
            grade=grade_code,
            subject=subject_code,
            topic_name=topic.topic_name,
            chapter_name=chapter_name,
            validation_report=schema_report.model_dump(),
        )

        generation_time = round(time.time() - start_time, 2)

        # ----------------------------------------------------------------
        # Step 7: Store GeneratedLesson in DB
        # ----------------------------------------------------------------
        generated_lesson = GeneratedLesson(
            request_id=request_id,
            topic_id=payload.topic_id,
            lesson_content_docx=docx_bytes,
            lesson_metadata=lesson_data,
            validation_report=schema_report.model_dump(),
            generation_time_seconds=Decimal(str(generation_time)),
        )
        db.add(generated_lesson)

        # ----------------------------------------------------------------
        # Step 8: Update GenerationRequest status='completed'
        # ----------------------------------------------------------------
        gen_request.status = "completed"
        gen_request.updated_at = datetime.utcnow()

        # ----------------------------------------------------------------
        # Step 9: Write AuditLog entry
        # ----------------------------------------------------------------
        await _write_audit_log(
            db,
            request_id=request_id,
            event_type="lesson_generated",
            event_details={
                "topic_id": payload.topic_id,
                "topic_name": topic.topic_name,
                "grade": grade_code,
                "subject": subject_code,
                "generation_time_seconds": generation_time,
                "validation_passed": True,
                "overall_score": schema_report.overall_score,
            },
            severity="info",
        )

        await db.flush()

        # ----------------------------------------------------------------
        # Step 10: Return response
        # ----------------------------------------------------------------
        docx_url = f"/lessons/{request_id}/download"

        return GenerationResponse(
            request_id=str(request_id),
            status="completed",
            docx_url=docx_url,
            validation_report=schema_report,
            generation_time_seconds=generation_time,
        )

    except HTTPException:
        raise
    except Exception as exc:
        # Catch-all: mark request as failed, log, and return 500
        logger.exception("Unhandled error during lesson generation: %s", exc)

        gen_request.status = "failed"
        gen_request.updated_at = datetime.utcnow()

        await _write_audit_log(
            db,
            request_id=request_id,
            event_type="generation_error",
            event_details={
                "topic_id": payload.topic_id,
                "error": str(exc),
            },
            severity="error",
        )

        try:
            await db.flush()
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail={
                "request_id": str(request_id),
                "status": "failed",
                "message": f"Internal error during lesson generation: {exc}",
            },
        )


# ---------------------------------------------------------------------------
# GET /lessons/{request_id}/download
# ---------------------------------------------------------------------------

@router.get(
    "/{request_id}/download",
    summary="Download generated DOCX",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            },
            "description": "DOCX file download",
        },
        404: {"description": "Lesson not found or not yet completed"},
    },
)
async def download_lesson(
    request_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Download the generated DOCX for a completed lesson.

    Returns DOCX bytes with proper Content-Disposition header.
    """
    try:
        req_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request_id format")

    # Find the generated lesson by request_id
    stmt = select(GeneratedLesson).where(GeneratedLesson.request_id == req_uuid)
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail=f"No generated lesson found for request {request_id}",
        )

    if not lesson.lesson_content_docx:
        raise HTTPException(
            status_code=404,
            detail="DOCX content not available (generation may have failed)",
        )

    # Get topic name for filename
    topic = await db.get(Topic, lesson.topic_id)
    topic_name = topic.topic_name if topic else "lesson"
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic_name)
    filename = f"{safe_name}.docx"

    return Response(
        content=lesson.lesson_content_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# GET /lessons/{request_id} — Status polling
# ---------------------------------------------------------------------------

@router.get(
    "/{request_id}",
    summary="Poll lesson generation status",
    responses={
        404: {"description": "Request not found"},
    },
)
async def get_lesson_status(
    request_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Poll the status of a generation request."""
    try:
        req_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request_id format")

    gen_request = await db.get(GenerationRequestModel, req_uuid)
    if not gen_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    response: dict[str, Any] = {
        "request_id": str(gen_request.id),
        "status": gen_request.status,
        "completion_percentage": _status_to_percentage(gen_request.status),
        "message": _status_to_message(gen_request.status),
    }

    # If completed, include validation report and generation time
    if gen_request.status == "completed":
        stmt = select(GeneratedLesson).where(GeneratedLesson.request_id == req_uuid)
        result = await db.execute(stmt)
        lesson = result.scalar_one_or_none()
        if lesson:
            response["validation_report"] = lesson.validation_report
            response["generation_time_seconds"] = (
                float(lesson.generation_time_seconds)
                if lesson.generation_time_seconds
                else None
            )
            response["docx_url"] = f"/lessons/{request_id}/download"

    return response


def _status_to_percentage(status: str) -> int:
    mapping = {
        "pending": 0,
        "processing": 50,
        "completed": 100,
        "failed": 100,
    }
    return mapping.get(status, 0)


def _status_to_message(status: str) -> str:
    mapping = {
        "pending": "Request queued for processing",
        "processing": "Lesson is being generated",
        "completed": "Lesson generated successfully",
        "failed": "Lesson generation failed",
    }
    return mapping.get(status, "Unknown status")
