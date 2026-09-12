-- TASK-018B: immutable cue-level time/text authority.  Existing transcript and
-- Evidence rows deliberately remain unbound; this migration never backfills.
CREATE TABLE timed_transcripts (
    timed_transcript_id TEXT PRIMARY KEY CHECK (length(trim(timed_transcript_id)) > 0 AND length(timed_transcript_id) <= 512),
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    canonical_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    timed_transcript_hash TEXT NOT NULL CHECK (length(timed_transcript_hash) = 64 AND timed_transcript_hash GLOB '[0-9a-f]*'),
    created_at TEXT NOT NULL,
    UNIQUE (canonical_artifact_id)
);

CREATE TABLE timed_transcript_cues (
    timed_transcript_id TEXT NOT NULL REFERENCES timed_transcripts(timed_transcript_id) ON DELETE RESTRICT,
    cue_index INTEGER NOT NULL CHECK (cue_index >= 0),
    start_ms INTEGER NOT NULL CHECK (start_ms >= 0),
    end_ms INTEGER NOT NULL CHECK (end_ms > start_ms),
    cue_text TEXT NOT NULL CHECK (length(trim(cue_text)) > 0),
    cue_text_hash TEXT NOT NULL CHECK (length(cue_text_hash) = 64 AND cue_text_hash GLOB '[0-9a-f]*'),
    PRIMARY KEY (timed_transcript_id, cue_index),
    UNIQUE (timed_transcript_id, start_ms, end_ms)
);

CREATE TABLE evidence_text_bindings (
    evidence_id TEXT PRIMARY KEY REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    timed_transcript_id TEXT NOT NULL REFERENCES timed_transcripts(timed_transcript_id) ON DELETE RESTRICT,
    start_cue_index INTEGER NOT NULL CHECK (start_cue_index >= 0),
    end_cue_index INTEGER NOT NULL CHECK (end_cue_index > start_cue_index),
    excerpt TEXT NOT NULL CHECK (length(trim(excerpt)) > 0),
    excerpt_hash TEXT NOT NULL CHECK (length(excerpt_hash) = 64 AND excerpt_hash GLOB '[0-9a-f]*'),
    timed_transcript_hash TEXT NOT NULL CHECK (length(timed_transcript_hash) = 64 AND timed_transcript_hash GLOB '[0-9a-f]*'),
    created_at TEXT NOT NULL
);

CREATE INDEX idx_timed_transcripts_video ON timed_transcripts(video_id, timed_transcript_id);
CREATE INDEX idx_evidence_text_bindings_timed ON evidence_text_bindings(timed_transcript_id, evidence_id);

CREATE TRIGGER timed_transcripts_immutable_update
BEFORE UPDATE ON timed_transcripts
BEGIN
    SELECT RAISE(ABORT, 'timed transcript authority is immutable');
END;
CREATE TRIGGER timed_transcripts_immutable_delete
BEFORE DELETE ON timed_transcripts
BEGIN
    SELECT RAISE(ABORT, 'timed transcript authority cannot be deleted');
END;
CREATE TRIGGER timed_transcript_cues_immutable_update
BEFORE UPDATE ON timed_transcript_cues
BEGIN
    SELECT RAISE(ABORT, 'timed transcript cues are immutable');
END;
CREATE TRIGGER timed_transcript_cues_immutable_delete
BEFORE DELETE ON timed_transcript_cues
BEGIN
    SELECT RAISE(ABORT, 'timed transcript cues cannot be deleted');
END;
CREATE TRIGGER evidence_text_bindings_immutable_update
BEFORE UPDATE ON evidence_text_bindings
BEGIN
    SELECT RAISE(ABORT, 'evidence text binding is immutable');
END;
CREATE TRIGGER evidence_text_bindings_immutable_delete
BEFORE DELETE ON evidence_text_bindings
BEGIN
    SELECT RAISE(ABORT, 'evidence text binding cannot be deleted');
END;
