-- M3A: one explicit current official Summary / Video Notes binding per Content.
-- A binding may target only an already-persisted Deep Analysis trusted result.
-- Historical Deep Analysis rows remain append-only; this table only selects the
-- current product reading result.

CREATE TABLE current_content_summaries (
    video_id TEXT PRIMARY KEY
        REFERENCES videos(video_id) ON DELETE RESTRICT,
    result_identity TEXT NOT NULL UNIQUE
        REFERENCES deep_analysis_persisted_results(result_identity) ON DELETE RESTRICT,
    note_identity TEXT NOT NULL CHECK (
        length(note_identity) = 64
        AND note_identity NOT GLOB '*[^0-9a-f]*'
    ),
    output_language TEXT NOT NULL CHECK (length(trim(output_language)) > 0),
    promoted_at TEXT NOT NULL
);

CREATE INDEX idx_current_content_summaries_result
    ON current_content_summaries(result_identity);
