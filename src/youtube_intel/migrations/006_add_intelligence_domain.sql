-- TASK-018 owns only immutable product-domain identity, revisions, and provenance.
-- Execution, dispatch, provider, scoring, Topic, and Brief authority remain elsewhere.

CREATE TABLE intelligences (
    intelligence_id TEXT PRIMARY KEY CHECK (length(trim(intelligence_id)) > 0),
    current_revision_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (intelligence_id, current_revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id)
        ON DELETE RESTRICT
);

CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY CHECK (length(trim(evidence_id)) > 0),
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    start_ms INTEGER NOT NULL CHECK (start_ms >= 0),
    end_ms INTEGER NOT NULL CHECK (end_ms >= start_ms),
    lineage_kind TEXT NOT NULL CHECK (lineage_kind IN ('ORIGINAL_TRANSCRIPT', 'TRANSLATION', 'EXTRACTION')),
    role TEXT NOT NULL CHECK (role IN ('PRIMARY_ORIGINAL', 'INDEPENDENT_VERIFICATION', 'ANALYSIS_COMMENTARY', 'SECONDARY_RELAY')),
    language TEXT NOT NULL CHECK (length(trim(language)) > 0),
    availability TEXT NOT NULL CHECK (availability IN ('AVAILABLE', 'UNAVAILABLE', 'DELETED')),
    created_at TEXT NOT NULL,
    UNIQUE (artifact_id, start_ms, end_ms, lineage_kind, role)
);
CREATE INDEX idx_evidence_video_availability ON evidence(video_id, availability, evidence_id);

CREATE TRIGGER evidence_artifact_must_belong_to_video
BEFORE INSERT ON evidence
WHEN NOT EXISTS (
    SELECT 1 FROM artifacts
    WHERE artifact_id = NEW.artifact_id
      AND video_id = NEW.video_id
      AND deleted_at IS NULL
)
BEGIN
    SELECT RAISE(ABORT, 'evidence artifact provenance is unavailable or mismatched');
END;

CREATE TRIGGER evidence_immutable_content
BEFORE UPDATE ON evidence
WHEN NEW.evidence_id IS NOT OLD.evidence_id
  OR NEW.video_id IS NOT OLD.video_id
  OR NEW.artifact_id IS NOT OLD.artifact_id
  OR NEW.start_ms IS NOT OLD.start_ms
  OR NEW.end_ms IS NOT OLD.end_ms
  OR NEW.lineage_kind IS NOT OLD.lineage_kind
  OR NEW.role IS NOT OLD.role
  OR NEW.language IS NOT OLD.language
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'evidence material is immutable');
END;

CREATE TRIGGER evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'evidence deletion requires dependency impact handling');
END;

CREATE TABLE intelligence_revisions (
    revision_id TEXT PRIMARY KEY CHECK (length(trim(revision_id)) > 0),
    intelligence_id TEXT NOT NULL REFERENCES intelligences(intelligence_id) ON DELETE RESTRICT,
    revision_number INTEGER NOT NULL CHECK (revision_number > 0),
    prior_revision_id TEXT REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    interpretation_kind TEXT NOT NULL CHECK (interpretation_kind IN ('DISTILLATION', 'SYNTHESIS', 'CORRECTION')),
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64 AND content_hash NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL,
    UNIQUE (intelligence_id, revision_id),
    UNIQUE (intelligence_id, revision_number)
);
CREATE INDEX idx_intelligence_revisions_identity ON intelligence_revisions(intelligence_id, revision_number);

CREATE TRIGGER intelligence_revision_must_append
BEFORE INSERT ON intelligence_revisions
WHEN NEW.revision_number != COALESCE((
    SELECT MAX(revision_number) + 1
    FROM intelligence_revisions
    WHERE intelligence_id = NEW.intelligence_id
), 1)
 OR (
    NEW.revision_number = 1 AND NEW.prior_revision_id IS NOT NULL
 )
 OR (
    NEW.revision_number > 1 AND NEW.prior_revision_id IS NOT (
        SELECT current_revision_id FROM intelligences
        WHERE intelligence_id = NEW.intelligence_id
    )
 )
BEGIN
    SELECT RAISE(ABORT, 'intelligence revision must append to its current revision');
END;

CREATE TRIGGER intelligence_revision_prior_same_identity
BEFORE INSERT ON intelligence_revisions
WHEN NEW.prior_revision_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1 FROM intelligence_revisions
    WHERE revision_id = NEW.prior_revision_id
      AND intelligence_id = NEW.intelligence_id
 )
BEGIN
    SELECT RAISE(ABORT, 'prior revision belongs to another intelligence');
END;

CREATE TRIGGER intelligence_revision_immutable
BEFORE UPDATE ON intelligence_revisions
BEGIN
    SELECT RAISE(ABORT, 'intelligence revisions are immutable');
END;

CREATE TRIGGER intelligence_revision_no_delete
BEFORE DELETE ON intelligence_revisions
BEGIN
    SELECT RAISE(ABORT, 'intelligence revisions are immutable');
END;

CREATE TABLE intelligence_revision_evidence (
    revision_id TEXT NOT NULL REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    PRIMARY KEY (revision_id, evidence_id)
);
CREATE INDEX idx_intelligence_revision_evidence_evidence ON intelligence_revision_evidence(evidence_id, revision_id);

CREATE TRIGGER revision_evidence_must_be_available
BEFORE INSERT ON intelligence_revision_evidence
WHEN NOT EXISTS (
    SELECT 1 FROM evidence
    WHERE evidence_id = NEW.evidence_id AND availability = 'AVAILABLE'
)
BEGIN
    SELECT RAISE(ABORT, 'unavailable evidence cannot support an intelligence revision');
END;

CREATE TRIGGER revision_evidence_no_delete
BEFORE DELETE ON intelligence_revision_evidence
BEGIN
    SELECT RAISE(ABORT, 'revision evidence links are immutable');
END;

CREATE TABLE intelligence_state_history (
    state_event_id TEXT PRIMARY KEY CHECK (length(trim(state_event_id)) > 0),
    intelligence_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('NEW', 'PENDING_CONFIRMATION', 'CONFIRMED', 'DISPUTED', 'UPDATED', 'INVALIDATED', 'OVERTURNED')),
    prior_state TEXT CHECK (prior_state IS NULL OR prior_state IN ('NEW', 'PENDING_CONFIRMATION', 'CONFIRMED', 'DISPUTED', 'UPDATED', 'INVALIDATED', 'OVERTURNED')),
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    UNIQUE (revision_id),
    FOREIGN KEY (intelligence_id, revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_intelligence_state_history_identity ON intelligence_state_history(intelligence_id, created_at, state_event_id);

CREATE TRIGGER intelligence_state_history_immutable_update
BEFORE UPDATE ON intelligence_state_history
BEGIN
    SELECT RAISE(ABORT, 'intelligence state history is immutable');
END;

CREATE TRIGGER intelligence_state_history_immutable_delete
BEFORE DELETE ON intelligence_state_history
BEGIN
    SELECT RAISE(ABORT, 'intelligence state history is immutable');
END;

CREATE TRIGGER intelligence_current_revision_must_be_supported
BEFORE UPDATE OF current_revision_id ON intelligences
WHEN NEW.current_revision_id IS NOT NULL
 AND (
    NOT EXISTS (
        SELECT 1 FROM intelligence_revision_evidence
        WHERE revision_id = NEW.current_revision_id
    )
    OR EXISTS (
        SELECT 1
        FROM intelligence_revision_evidence AS link
        JOIN evidence ON evidence.evidence_id = link.evidence_id
        WHERE link.revision_id = NEW.current_revision_id
          AND evidence.availability != 'AVAILABLE'
    )
    OR NOT EXISTS (
        SELECT 1 FROM intelligence_state_history
        WHERE revision_id = NEW.current_revision_id
    )
 )
BEGIN
    SELECT RAISE(ABORT, 'current intelligence revision must have available evidence and state history');
END;

CREATE TRIGGER evidence_availability_requires_no_current_support
BEFORE UPDATE OF availability ON evidence
WHEN EXISTS (
    SELECT 1
    FROM intelligence_revision_evidence AS link
    JOIN intelligences ON intelligences.current_revision_id = link.revision_id
    WHERE link.evidence_id = OLD.evidence_id
)
BEGIN
    SELECT RAISE(ABORT, 'current intelligence support must be resolved before evidence availability changes');
END;

CREATE TABLE dependency_edges (
    edge_id TEXT PRIMARY KEY CHECK (length(trim(edge_id)) > 0),
    dependent_revision_id TEXT NOT NULL REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    relation TEXT NOT NULL CHECK (relation IN ('EVIDENCE_SUPPORT', 'REVISION_SUPERSEDES')),
    input_evidence_id TEXT REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    input_revision_id TEXT REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (
        (relation = 'EVIDENCE_SUPPORT' AND input_evidence_id IS NOT NULL AND input_revision_id IS NULL)
        OR (relation = 'REVISION_SUPERSEDES' AND input_evidence_id IS NULL AND input_revision_id IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_dependency_edge_evidence
    ON dependency_edges(dependent_revision_id, relation, input_evidence_id)
    WHERE input_evidence_id IS NOT NULL;
CREATE UNIQUE INDEX uq_dependency_edge_revision
    ON dependency_edges(dependent_revision_id, relation, input_revision_id)
    WHERE input_revision_id IS NOT NULL;
CREATE INDEX idx_dependency_edges_input_evidence ON dependency_edges(input_evidence_id, dependent_revision_id);
CREATE INDEX idx_dependency_edges_input_revision ON dependency_edges(input_revision_id, dependent_revision_id);

CREATE TRIGGER dependency_edge_revision_must_be_same_intelligence
BEFORE INSERT ON dependency_edges
WHEN NEW.relation = 'REVISION_SUPERSEDES'
 AND NOT EXISTS (
    SELECT 1
    FROM intelligence_revisions AS dependent
    JOIN intelligence_revisions AS input ON input.revision_id = NEW.input_revision_id
    WHERE dependent.revision_id = NEW.dependent_revision_id
      AND dependent.intelligence_id = input.intelligence_id
      AND dependent.revision_id != input.revision_id
 )
BEGIN
    SELECT RAISE(ABORT, 'revision supersession must stay within one intelligence identity');
END;

CREATE TRIGGER dependency_edge_immutable_update
BEFORE UPDATE ON dependency_edges
BEGIN
    SELECT RAISE(ABORT, 'dependency edges are immutable');
END;

CREATE TRIGGER dependency_edge_immutable_delete
BEFORE DELETE ON dependency_edges
BEGIN
    SELECT RAISE(ABORT, 'dependency edges are immutable');
END;
