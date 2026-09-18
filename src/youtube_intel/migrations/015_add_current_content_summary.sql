-- V1 M3: explicit current official Summary / Video Notes pointer.
-- A result may become current only after DeepAnalysisPersistenceStore has
-- revalidated the persisted trusted Deep Analysis result.

CREATE TABLE current_content_summaries (
    video_id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(video_id)) > 0),
    result_identity TEXT NOT NULL UNIQUE
        REFERENCES deep_analysis_persisted_results(result_identity) ON DELETE RESTRICT,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_current_content_summaries_result
    ON current_content_summaries(result_identity);
