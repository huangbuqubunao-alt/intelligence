-- V1 translations are immutable presentation metadata tied to one canonical
-- Evidence excerpt. No historical Evidence is backfilled by this migration.
CREATE TABLE evidence_translation_presentations (
    translation_id TEXT PRIMARY KEY
        CHECK (length(trim(translation_id)) > 0),
    evidence_id TEXT NOT NULL
        REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    source_excerpt_hash TEXT NOT NULL
        CHECK (length(source_excerpt_hash) = 64 AND source_excerpt_hash NOT GLOB '*[^0-9a-f]*'),
    source_language TEXT NOT NULL
        CHECK (length(trim(source_language)) BETWEEN 1 AND 64),
    target_language TEXT NOT NULL
        CHECK (target_language IN ('zh-CN', 'en')),
    translated_excerpt TEXT NOT NULL
        CHECK (length(trim(translated_excerpt)) > 0 AND length(translated_excerpt) <= 4000),
    translated_excerpt_hash TEXT NOT NULL
        CHECK (length(translated_excerpt_hash) = 64 AND translated_excerpt_hash NOT GLOB '*[^0-9a-f]*'),
    provider TEXT NOT NULL CHECK (provider = 'ollama'),
    model TEXT NOT NULL CHECK (model = 'qwen3:8b'),
    model_digest TEXT NOT NULL
        CHECK (
            length(model_digest) = 71
            AND substr(model_digest, 1, 7) = 'sha256:'
            AND substr(model_digest, 8) NOT GLOB '*[^0-9a-f]*'
        ),
    prompt_version TEXT NOT NULL CHECK (prompt_version = 'evidence-translation-v1'),
    schema_version TEXT NOT NULL CHECK (schema_version = 'evidence-translation-schema-v1'),
    created_at TEXT NOT NULL,
    UNIQUE (evidence_id, target_language)
);

CREATE INDEX idx_evidence_translation_evidence_target
    ON evidence_translation_presentations(evidence_id, target_language);

CREATE TRIGGER evidence_translation_presentation_immutable_update
BEFORE UPDATE ON evidence_translation_presentations
BEGIN
    SELECT RAISE(ABORT, 'Evidence translation presentation is immutable');
END;

CREATE TRIGGER evidence_translation_presentation_immutable_delete
BEFORE DELETE ON evidence_translation_presentations
BEGIN
    SELECT RAISE(ABORT, 'Evidence translation presentation cannot be deleted');
END;
