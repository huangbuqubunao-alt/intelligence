-- One explicit current Summary selection for either verified Deep Analysis or
-- the existing M1 Analysis artifact. Preserve historical Deep Analysis pointers.
CREATE TABLE current_content_summaries_v2 (
    video_id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(video_id)) > 0),
    result_identity TEXT UNIQUE
        REFERENCES deep_analysis_persisted_results(result_identity) ON DELETE RESTRICT,
    analysis_artifact_id TEXT UNIQUE
        REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    output_language TEXT CHECK (output_language IN ('zh-CN', 'en')),
    updated_at TEXT NOT NULL,
    CHECK (
        (result_identity IS NOT NULL AND analysis_artifact_id IS NULL AND output_language IS NULL)
        OR (result_identity IS NULL AND analysis_artifact_id IS NOT NULL AND output_language IS NOT NULL)
    )
);

INSERT INTO current_content_summaries_v2 (video_id, result_identity, updated_at)
SELECT video_id, result_identity, updated_at FROM current_content_summaries;

DROP TABLE current_content_summaries;
ALTER TABLE current_content_summaries_v2 RENAME TO current_content_summaries;

CREATE INDEX idx_current_content_summaries_result
    ON current_content_summaries(result_identity);
CREATE INDEX idx_current_content_summaries_analysis
    ON current_content_summaries(analysis_artifact_id);

CREATE TRIGGER current_local_summary_language_immutable
BEFORE UPDATE ON current_content_summaries
WHEN OLD.analysis_artifact_id IS NOT NULL
  AND NEW.analysis_artifact_id IS OLD.analysis_artifact_id
  AND NEW.output_language IS NOT OLD.output_language
BEGIN
    SELECT RAISE(ABORT, 'current Summary language is immutable for an artifact');
END;
