-- =============================================================================
-- KitmeK Lesson Generation — Performance Indices
-- All CREATE INDEX statements use IF NOT EXISTS — fully idempotent.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- generation_requests
-- ---------------------------------------------------------------------------

-- Fast status polling (GET /lessons/{request_id})
CREATE INDEX IF NOT EXISTS idx_generation_requests_status
    ON generation_requests (status);

-- Ordered queue retrieval by priority + creation time
CREATE INDEX IF NOT EXISTS idx_generation_requests_priority_created
    ON generation_requests (priority DESC, created_at ASC)
    WHERE status IN ('pending', 'processing');

-- Lookup all requests for a given topic
CREATE INDEX IF NOT EXISTS idx_generation_requests_topic_id
    ON generation_requests (topic_id);

-- Lookup requests by KB version (cache invalidation, analytics)
CREATE INDEX IF NOT EXISTS idx_generation_requests_kb_version_id
    ON generation_requests (kb_version_id);

-- Time-range analytics and cleanup jobs
CREATE INDEX IF NOT EXISTS idx_generation_requests_created_at
    ON generation_requests (created_at DESC);

-- ---------------------------------------------------------------------------
-- generated_lessons
-- ---------------------------------------------------------------------------

-- 1-to-1 lookup from request_id (GET /lessons/{request_id}/download)
CREATE INDEX IF NOT EXISTS idx_generated_lessons_request_id
    ON generated_lessons (request_id);

-- All lessons for a given topic (history, caching)
CREATE INDEX IF NOT EXISTS idx_generated_lessons_topic_id
    ON generated_lessons (topic_id);

-- Recent lesson retrieval (dashboard, analytics)
CREATE INDEX IF NOT EXISTS idx_generated_lessons_generation_timestamp
    ON generated_lessons (generation_timestamp DESC);

-- JSONB GIN index — fast queries inside lesson_metadata
CREATE INDEX IF NOT EXISTS idx_generated_lessons_metadata_gin
    ON generated_lessons USING GIN (lesson_metadata);

-- JSONB GIN index — fast queries inside validation_report
CREATE INDEX IF NOT EXISTS idx_generated_lessons_validation_gin
    ON generated_lessons USING GIN (validation_report);

-- ---------------------------------------------------------------------------
-- audit_log
-- ---------------------------------------------------------------------------

-- Trace all events for a single request (debug, QA)
CREATE INDEX IF NOT EXISTS idx_audit_log_request_id
    ON audit_log (request_id);

-- Time-based log retrieval and retention cleanup
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
    ON audit_log (created_at DESC);

-- Filter by severity (error monitoring dashboards)
CREATE INDEX IF NOT EXISTS idx_audit_log_severity
    ON audit_log (severity)
    WHERE severity IN ('warning', 'error');

-- Filter by event type (e.g., counting validation_failed events)
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type
    ON audit_log (event_type);

-- JSONB GIN index — search inside event_details
CREATE INDEX IF NOT EXISTS idx_audit_log_event_details_gin
    ON audit_log USING GIN (event_details);

-- ---------------------------------------------------------------------------
-- kb_constraint_cache
-- ---------------------------------------------------------------------------

-- Primary lookup pattern: (kb_version_id, constraint_type, grade_code)
-- Already covered by the UNIQUE constraint; add a supporting index for
-- partial lookups by (kb_version_id, constraint_type) without grade.
CREATE INDEX IF NOT EXISTS idx_kb_constraint_cache_version_type
    ON kb_constraint_cache (kb_version_id, constraint_type);

-- Per-grade constraint lookup (e.g., language ceiling for Grade 3)
CREATE INDEX IF NOT EXISTS idx_kb_constraint_cache_grade_code
    ON kb_constraint_cache (grade_code);

-- JSONB GIN index — allow jsonb_path_query on constraint_json
CREATE INDEX IF NOT EXISTS idx_kb_constraint_cache_json_gin
    ON kb_constraint_cache USING GIN (constraint_json);

-- ---------------------------------------------------------------------------
-- Supporting tables (curriculum hierarchy)
-- ---------------------------------------------------------------------------

-- subjects: quick lookup by grade
CREATE INDEX IF NOT EXISTS idx_subjects_grade_id
    ON subjects (grade_id);

-- chapters: quick lookup by subject
CREATE INDEX IF NOT EXISTS idx_chapters_subject_id
    ON chapters (subject_id);

-- topics: quick lookup by chapter + ordering
CREATE INDEX IF NOT EXISTS idx_topics_chapter_id_seq
    ON topics (chapter_id, sequence_number);

-- Full-text search on topic names (GET /topics?search=...)
CREATE INDEX IF NOT EXISTS idx_topics_name_fts
    ON topics USING GIN (to_tsvector('english', topic_name));

-- Full-text search on chapter names
CREATE INDEX IF NOT EXISTS idx_chapters_name_fts
    ON chapters USING GIN (to_tsvector('english', chapter_name));
