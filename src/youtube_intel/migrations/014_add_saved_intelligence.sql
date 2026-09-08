-- TASK-025A: local organization only. No copied content, history or trust flag.
CREATE TABLE saved_intelligences (
    intelligence_id TEXT PRIMARY KEY NOT NULL
        REFERENCES intelligences(intelligence_id) ON DELETE RESTRICT,
    saved_at TEXT NOT NULL CHECK (
        length(saved_at) = 27
        AND saved_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z'
        AND julianday(saved_at) IS NOT NULL
    )
);
CREATE INDEX idx_saved_intelligences_order
    ON saved_intelligences(saved_at DESC, intelligence_id ASC);

CREATE TRIGGER saved_intelligences_no_update
BEFORE UPDATE ON saved_intelligences
BEGIN
    SELECT RAISE(ABORT, 'saved relation must be removed before saving again');
END;
