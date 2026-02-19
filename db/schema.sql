-- KitmeK Lesson Generation Backend — PostgreSQL Schema
-- Version: 1.0
-- Compatible with: PostgreSQL 14+

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Table: grades
-- Curriculum hierarchy root. Represents NCERT grade levels (K through 5).
-- =============================================================================
CREATE TABLE grades (
    id SERIAL PRIMARY KEY,
    grade_code VARCHAR(5) UNIQUE NOT NULL,       -- 'K', '1', '2', '3', '4', '5'
    grade_name VARCHAR(50) NOT NULL,
    age_range VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE grades IS 'NCERT grade levels K–5. Immutable reference data.';
COMMENT ON COLUMN grades.grade_code IS 'Short code: K, 1, 2, 3, 4, 5';

-- =============================================================================
-- Table: subjects
-- Subjects offered per grade (EVS, Math, English, Hindi).
-- =============================================================================
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    grade_id INTEGER NOT NULL REFERENCES grades(id) ON DELETE CASCADE,
    subject_name VARCHAR(100) NOT NULL,
    subject_code VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(grade_id, subject_code)
);

COMMENT ON TABLE subjects IS 'Subjects per grade. One grade has many subjects.';

CREATE INDEX idx_subjects_grade_id ON subjects(grade_id);

-- =============================================================================
-- Table: chapters
-- Chapters within a subject (e.g., "Types of Plants").
-- =============================================================================
CREATE TABLE chapters (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    chapter_name VARCHAR(200) NOT NULL,
    chapter_description TEXT,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_id, chapter_number)
);

COMMENT ON TABLE chapters IS 'Chapters within a subject. Ordered by sequence_number.';

CREATE INDEX idx_chapters_subject_id ON chapters(subject_id);
CREATE INDEX idx_chapters_sequence ON chapters(subject_id, sequence_number);

-- =============================================================================
-- Table: topics
-- Individual topics within a chapter. Leaf node of curriculum hierarchy.
-- =============================================================================
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    topic_number INTEGER NOT NULL,
    topic_name VARCHAR(200) NOT NULL,
    topic_description TEXT,
    sequence_number INTEGER NOT NULL,
    prerequisites TEXT,              -- JSON array of prerequisite topic IDs
    exclusions TEXT,                 -- JSON array of excluded topic IDs
    context_narrative TEXT,          -- Story frame from chapter
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chapter_id, topic_number)
);

COMMENT ON TABLE topics IS 'Topics within a chapter. Supports prerequisites and exclusions.';
COMMENT ON COLUMN topics.prerequisites IS 'JSON array of topic IDs that must be taught first.';
COMMENT ON COLUMN topics.exclusions IS 'JSON array of topic IDs whose content must not bleed in.';
COMMENT ON COLUMN topics.context_narrative IS 'Story or narrative frame from the chapter context.';

CREATE INDEX idx_topics_chapter_id ON topics(chapter_id);
CREATE INDEX idx_topics_sequence ON topics(chapter_id, sequence_number);

-- =============================================================================
-- Table: knowledge_base_versions
-- Versioned snapshots of KB files. Only one version is active at a time.
-- =============================================================================
CREATE TABLE knowledge_base_versions (
    id SERIAL PRIMARY KEY,
    kb_version VARCHAR(20) UNIQUE NOT NULL,      -- e.g., '1.0', '1.1'
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    language_guidelines BYTEA,                    -- Raw markdown file content
    blooms_taxonomy BYTEA,
    ncert_pedagogy BYTEA,
    digital_interactions BYTEA,
    question_bank BYTEA,
    definitions_examples BYTEA,
    checksum VARCHAR(64),                         -- SHA256 of all KB files combined
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE knowledge_base_versions IS 'Versioned KB file snapshots. One active version at a time.';
COMMENT ON COLUMN knowledge_base_versions.checksum IS 'SHA256 hash of concatenated KB file contents.';

CREATE INDEX idx_kb_versions_active ON knowledge_base_versions(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- Table: generation_requests
-- Tracks each lesson generation request through its lifecycle.
-- =============================================================================
CREATE TABLE generation_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
    kb_version_id INTEGER NOT NULL REFERENCES knowledge_base_versions(id) ON DELETE RESTRICT,
    request_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_by VARCHAR(100),                    -- User or system identifier
    status VARCHAR(20) NOT NULL DEFAULT 'pending',-- pending, processing, completed, failed
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE generation_requests IS 'Lesson generation request lifecycle tracker.';
COMMENT ON COLUMN generation_requests.status IS 'One of: pending, processing, completed, failed.';

CREATE INDEX idx_gen_requests_topic_id ON generation_requests(topic_id);
CREATE INDEX idx_gen_requests_status ON generation_requests(status);
CREATE INDEX idx_gen_requests_created_at ON generation_requests(created_at);
CREATE INDEX idx_gen_requests_kb_version ON generation_requests(kb_version_id);

-- =============================================================================
-- Table: generated_lessons
-- Stores the output of successful lesson generation: DOCX, metadata, report.
-- =============================================================================
CREATE TABLE generated_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES generation_requests(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
    lesson_content_docx BYTEA,                    -- Binary DOCX file
    lesson_metadata JSONB,                        -- Structured lesson data
    validation_report JSONB,                      -- Validation check results
    generation_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generation_time_seconds NUMERIC(5, 2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE generated_lessons IS 'Generated lesson outputs with DOCX, metadata, and validation.';
COMMENT ON COLUMN generated_lessons.lesson_metadata IS 'JSON: {opening, sections, quiz, activity, conclusion}';
COMMENT ON COLUMN generated_lessons.validation_report IS 'JSON: {passed, checks[], warnings[], errors[], overall_score}';

CREATE INDEX idx_gen_lessons_request_id ON generated_lessons(request_id);
CREATE INDEX idx_gen_lessons_topic_id ON generated_lessons(topic_id);

-- =============================================================================
-- Table: kb_constraint_cache
-- Pre-parsed KB constraints for fast per-grade lookups during validation.
-- =============================================================================
CREATE TABLE kb_constraint_cache (
    id SERIAL PRIMARY KEY,
    kb_version_id INTEGER NOT NULL REFERENCES knowledge_base_versions(id) ON DELETE CASCADE,
    constraint_type VARCHAR(50) NOT NULL,         -- language_ceiling, bloom_distribution, etc.
    grade_code VARCHAR(5),
    constraint_json JSONB NOT NULL,               -- Normalized constraint data
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(kb_version_id, constraint_type, grade_code)
);

COMMENT ON TABLE kb_constraint_cache IS 'Pre-parsed KB constraints for fast per-grade lookups.';
COMMENT ON COLUMN kb_constraint_cache.constraint_type IS 'E.g. language_ceiling, bloom_distribution, interaction_types.';

CREATE INDEX idx_kb_cache_version ON kb_constraint_cache(kb_version_id);
CREATE INDEX idx_kb_cache_lookup ON kb_constraint_cache(kb_version_id, constraint_type, grade_code);

-- =============================================================================
-- Table: audit_log
-- Full traceability for lesson generation events.
-- =============================================================================
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID,
    event_type VARCHAR(50) NOT NULL,              -- lesson_generated, validation_passed, etc.
    event_details JSONB,
    severity VARCHAR(20) NOT NULL DEFAULT 'info', -- info, warning, error
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE audit_log IS 'Immutable event log for traceability and debugging.';
COMMENT ON COLUMN audit_log.event_type IS 'E.g. lesson_generated, validation_passed, validation_failed, kb_loaded.';

CREATE INDEX idx_audit_log_request_id ON audit_log(request_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_severity ON audit_log(severity);
