"""Initial schema — all 9 tables for KitmeK lesson generation.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-02-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable uuid-ossp extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # -- grades --
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grade_code", sa.String(5), nullable=False),
        sa.Column("grade_name", sa.String(50), nullable=False),
        sa.Column("age_range", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grade_code"),
    )

    # -- subjects --
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("subject_name", sa.String(100), nullable=False),
        sa.Column("subject_code", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grade_id", "subject_code"),
    )
    op.create_index("idx_subjects_grade_id", "subjects", ["grade_id"])

    # -- chapters --
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("chapter_name", sa.String(200), nullable=False),
        sa.Column("chapter_description", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "chapter_number"),
    )
    op.create_index("idx_chapters_subject_id", "chapters", ["subject_id"])
    op.create_index(
        "idx_chapters_sequence", "chapters", ["subject_id", "sequence_number"]
    )

    # -- topics --
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("topic_number", sa.Integer(), nullable=False),
        sa.Column("topic_name", sa.String(200), nullable=False),
        sa.Column("topic_description", sa.Text(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("prerequisites", sa.Text(), nullable=True),
        sa.Column("exclusions", sa.Text(), nullable=True),
        sa.Column("context_narrative", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "topic_number"),
    )
    op.create_index("idx_topics_chapter_id", "topics", ["chapter_id"])
    op.create_index(
        "idx_topics_sequence", "topics", ["chapter_id", "sequence_number"]
    )

    # -- knowledge_base_versions --
    op.create_table(
        "knowledge_base_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kb_version", sa.String(20), nullable=False),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("language_guidelines", sa.LargeBinary(), nullable=True),
        sa.Column("blooms_taxonomy", sa.LargeBinary(), nullable=True),
        sa.Column("ncert_pedagogy", sa.LargeBinary(), nullable=True),
        sa.Column("digital_interactions", sa.LargeBinary(), nullable=True),
        sa.Column("question_bank", sa.LargeBinary(), nullable=True),
        sa.Column("definitions_examples", sa.LargeBinary(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kb_version"),
    )
    op.create_index(
        "idx_kb_versions_active",
        "knowledge_base_versions",
        ["is_active"],
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # -- generation_requests --
    op.create_table(
        "generation_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("kb_version_id", sa.Integer(), nullable=False),
        sa.Column(
            "request_timestamp",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["kb_version_id"],
            ["knowledge_base_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_gen_requests_topic_id", "generation_requests", ["topic_id"]
    )
    op.create_index(
        "idx_gen_requests_status", "generation_requests", ["status"]
    )
    op.create_index(
        "idx_gen_requests_created_at", "generation_requests", ["created_at"]
    )
    op.create_index(
        "idx_gen_requests_kb_version", "generation_requests", ["kb_version_id"]
    )

    # -- generated_lessons --
    op.create_table(
        "generated_lessons",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("lesson_content_docx", sa.LargeBinary(), nullable=True),
        sa.Column("lesson_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("validation_report", postgresql.JSONB(), nullable=True),
        sa.Column(
            "generation_timestamp",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("generation_time_seconds", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["generation_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_gen_lessons_request_id", "generated_lessons", ["request_id"]
    )
    op.create_index(
        "idx_gen_lessons_topic_id", "generated_lessons", ["topic_id"]
    )

    # -- kb_constraint_cache --
    op.create_table(
        "kb_constraint_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kb_version_id", sa.Integer(), nullable=False),
        sa.Column("constraint_type", sa.String(50), nullable=False),
        sa.Column("grade_code", sa.String(5), nullable=True),
        sa.Column("constraint_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["kb_version_id"],
            ["knowledge_base_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kb_version_id", "constraint_type", "grade_code"),
    )
    op.create_index(
        "idx_kb_cache_version", "kb_constraint_cache", ["kb_version_id"]
    )
    op.create_index(
        "idx_kb_cache_lookup",
        "kb_constraint_cache",
        ["kb_version_id", "constraint_type", "grade_code"],
    )

    # -- audit_log --
    op.create_table(
        "audit_log",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column(
            "request_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default="info",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_log_request_id", "audit_log", ["request_id"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("idx_audit_log_event_type", "audit_log", ["event_type"])
    op.create_index("idx_audit_log_severity", "audit_log", ["severity"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("kb_constraint_cache")
    op.drop_table("generated_lessons")
    op.drop_table("generation_requests")
    op.drop_table("knowledge_base_versions")
    op.drop_table("topics")
    op.drop_table("chapters")
    op.drop_table("subjects")
    op.drop_table("grades")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
