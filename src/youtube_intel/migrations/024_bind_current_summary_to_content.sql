-- An authoritative Summary pointer is scoped to an existing Content row.
-- Triggers keep the invariant without rewriting verified pointer history.
CREATE TABLE m024_current_summary_validation (
    valid INTEGER NOT NULL CHECK (valid = 1)
);
INSERT INTO m024_current_summary_validation (valid)
SELECT CASE WHEN EXISTS (
    SELECT 1 FROM current_content_summaries c
    LEFT JOIN videos v ON v.video_id = c.video_id
    WHERE v.video_id IS NULL
) THEN 0 ELSE 1 END;
DROP TABLE m024_current_summary_validation;

CREATE TRIGGER current_summary_requires_content_insert
BEFORE INSERT ON current_content_summaries
WHEN NOT EXISTS (
    SELECT 1 FROM videos WHERE video_id = NEW.video_id
)
BEGIN
    SELECT RAISE(ABORT, 'current Summary requires existing Content');
END;

CREATE TRIGGER current_summary_requires_content_update
BEFORE UPDATE OF video_id ON current_content_summaries
WHEN NOT EXISTS (
    SELECT 1 FROM videos WHERE video_id = NEW.video_id
)
BEGIN
    SELECT RAISE(ABORT, 'current Summary requires existing Content');
END;

CREATE TRIGGER content_with_current_summary_restrict_delete
BEFORE DELETE ON videos
WHEN EXISTS (
    SELECT 1 FROM current_content_summaries WHERE video_id = OLD.video_id
)
BEGIN
    SELECT RAISE(ABORT, 'Content has an authoritative current Summary');
END;
