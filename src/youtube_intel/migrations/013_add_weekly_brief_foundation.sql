-- TASK-025: immutable V1 Weekly Brief snapshots.  Existing reports and
-- Weekly V2 remain separate authorities and are intentionally untouched.

CREATE TABLE weekly_briefs (
    brief_id TEXT PRIMARY KEY CHECK (length(trim(brief_id)) > 0 AND length(brief_id) <= 512),
    version TEXT NOT NULL CHECK (version = 'weekly-v1'),
    logical_period_id TEXT NOT NULL UNIQUE CHECK (length(trim(logical_period_id)) > 0 AND length(logical_period_id) <= 512),
    timezone TEXT NOT NULL CHECK (length(trim(timezone)) > 0 AND length(timezone) <= 128),
    period_start_utc TEXT NOT NULL,
    period_end_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'FINALIZED'),
    no_important_information INTEGER NOT NULL CHECK (no_important_information IN (0, 1)),
    preference_projection_hash TEXT NOT NULL CHECK (length(preference_projection_hash) = 64 AND preference_projection_hash NOT GLOB '*[^0-9a-f]*'),
    generated_at TEXT NOT NULL,
    finalized_at TEXT NOT NULL,
    UNIQUE (version, timezone, period_start_utc, period_end_utc),
    CHECK (period_start_utc < period_end_utc)
);
CREATE INDEX idx_weekly_briefs_period ON weekly_briefs(period_start_utc, period_end_utc, brief_id);

CREATE TRIGGER weekly_briefs_immutable_update
BEFORE UPDATE ON weekly_briefs
BEGIN
    SELECT RAISE(ABORT, 'finalized weekly briefs are immutable');
END;

CREATE TRIGGER weekly_briefs_immutable_delete
BEFORE DELETE ON weekly_briefs
BEGIN
    SELECT RAISE(ABORT, 'finalized weekly briefs are retained for history');
END;

CREATE TABLE brief_items (
    brief_item_id TEXT PRIMARY KEY CHECK (length(trim(brief_item_id)) > 0 AND length(brief_item_id) <= 512),
    brief_id TEXT NOT NULL REFERENCES weekly_briefs(brief_id) ON DELETE RESTRICT,
    membership_id TEXT NOT NULL REFERENCES topic_memberships(membership_id) ON DELETE RESTRICT,
    topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE RESTRICT,
    topic_name TEXT NOT NULL CHECK (length(trim(topic_name)) > 0 AND length(topic_name) <= 240),
    intelligence_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    association_kind TEXT NOT NULL CHECK (association_kind IN ('NEW_INFORMATION', 'NEW_EVIDENCE', 'CONTRADICTORY_INFORMATION')),
    claim_kind TEXT NOT NULL CHECK (claim_kind IN ('FACT', 'EVIDENCE_BACKED_STATEMENT', 'OPINION', 'PREDICTION', 'RUMOR', 'SYSTEM_INFERENCE')),
    source_state TEXT NOT NULL CHECK (source_state IN ('NEW', 'PENDING_CONFIRMATION', 'CONFIRMED', 'DISPUTED', 'UPDATED', 'INVALIDATED', 'OVERTURNED')),
    summary TEXT NOT NULL CHECK (length(trim(summary)) > 0 AND length(summary) <= 4000),
    source_content_hash TEXT NOT NULL CHECK (length(source_content_hash) = 64 AND source_content_hash NOT GLOB '*[^0-9a-f]*'),
    position INTEGER NOT NULL CHECK (position > 0),
    created_at TEXT NOT NULL,
    UNIQUE (brief_id, topic_id),
    UNIQUE (brief_id, intelligence_id, revision_id),
    UNIQUE (brief_id, position),
    FOREIGN KEY (intelligence_id, revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id) ON DELETE RESTRICT
);
CREATE INDEX idx_brief_items_revision ON brief_items(intelligence_id, revision_id, brief_item_id);
CREATE INDEX idx_brief_items_membership ON brief_items(membership_id, brief_item_id);

CREATE TRIGGER brief_item_must_be_current_trusted_topic_membership
BEFORE INSERT ON brief_items
WHEN NOT EXISTS (
    SELECT 1
    FROM weekly_briefs AS brief
    JOIN topic_memberships AS membership ON membership.membership_id = NEW.membership_id
    JOIN intelligences AS intelligence ON intelligence.intelligence_id = NEW.intelligence_id
    JOIN intelligence_revisions AS revision ON revision.revision_id = NEW.revision_id
    JOIN distillation_cards AS card ON card.revision_id = NEW.revision_id
    WHERE brief.brief_id = NEW.brief_id
      AND brief.status = 'FINALIZED'
      AND membership.topic_id = NEW.topic_id
      AND membership.intelligence_id = NEW.intelligence_id
      AND membership.revision_id = NEW.revision_id
      AND membership.association_kind = NEW.association_kind
      AND membership.source_claim_kind = NEW.claim_kind
      AND membership.source_state = NEW.source_state
      AND intelligence.current_revision_id = NEW.revision_id
      AND revision.content_hash = NEW.source_content_hash
      AND card.core_conclusion = NEW.summary
)
BEGIN
    SELECT RAISE(ABORT, 'brief item requires a current trusted topic membership');
END;

CREATE TRIGGER brief_items_immutable_update
BEFORE UPDATE ON brief_items
BEGIN
    SELECT RAISE(ABORT, 'brief items are immutable');
END;

CREATE TRIGGER brief_items_immutable_delete
BEFORE DELETE ON brief_items
BEGIN
    SELECT RAISE(ABORT, 'brief items are retained for history');
END;

CREATE TABLE brief_item_evidence (
    brief_item_id TEXT NOT NULL REFERENCES brief_items(brief_item_id) ON DELETE RESTRICT,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    PRIMARY KEY (brief_item_id, evidence_id)
);

CREATE TRIGGER brief_item_evidence_must_match_snapshot_source
BEFORE INSERT ON brief_item_evidence
WHEN NOT EXISTS (
    SELECT 1
    FROM brief_items AS item
    JOIN topic_membership_evidence AS topic_evidence
      ON topic_evidence.membership_id = item.membership_id
    JOIN intelligence_revision_evidence AS revision_evidence
      ON revision_evidence.revision_id = item.revision_id
    WHERE item.brief_item_id = NEW.brief_item_id
      AND topic_evidence.evidence_id = NEW.evidence_id
      AND revision_evidence.evidence_id = NEW.evidence_id
)
BEGIN
    SELECT RAISE(ABORT, 'brief item evidence must match its topic and intelligence source');
END;

CREATE TRIGGER brief_item_evidence_immutable_update
BEFORE UPDATE ON brief_item_evidence
BEGIN
    SELECT RAISE(ABORT, 'brief item evidence is immutable');
END;

CREATE TRIGGER brief_item_evidence_immutable_delete
BEFORE DELETE ON brief_item_evidence
BEGIN
    SELECT RAISE(ABORT, 'brief item evidence is retained for history');
END;

CREATE TABLE weekly_brief_preference_projections (
    brief_id TEXT NOT NULL REFERENCES weekly_briefs(brief_id) ON DELETE RESTRICT,
    preference_id TEXT NOT NULL REFERENCES preferences(preference_id) ON DELETE RESTRICT,
    horizon TEXT NOT NULL CHECK (horizon IN ('LONG_TERM', 'RECENT', 'TEMPORARY_FOCUS')),
    provenance TEXT NOT NULL CHECK (provenance IN ('EXPLICIT', 'DERIVED', 'TEMPORARY')),
    statement_hash TEXT NOT NULL CHECK (length(statement_hash) = 64 AND statement_hash NOT GLOB '*[^0-9a-f]*'),
    PRIMARY KEY (brief_id, preference_id)
);

CREATE TRIGGER weekly_brief_preference_projection_immutable_update
BEFORE UPDATE ON weekly_brief_preference_projections
BEGIN
    SELECT RAISE(ABORT, 'weekly preference projections are immutable');
END;

CREATE TRIGGER weekly_brief_preference_projection_immutable_delete
BEFORE DELETE ON weekly_brief_preference_projections
BEGIN
    SELECT RAISE(ABORT, 'weekly preference projections are retained for audit');
END;

CREATE TABLE brief_item_markers (
    marker_id TEXT PRIMARY KEY CHECK (length(trim(marker_id)) > 0 AND length(marker_id) <= 512),
    brief_item_id TEXT NOT NULL REFERENCES brief_items(brief_item_id) ON DELETE RESTRICT,
    marker_kind TEXT NOT NULL CHECK (marker_kind IN ('SUPERSEDED', 'EVIDENCE_DELETED', 'SOURCE_INVALIDATED')),
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0 AND length(reason) <= 1000),
    current_revision_id TEXT REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    evidence_id TEXT REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    marked_at TEXT NOT NULL,
    CHECK (
        (marker_kind = 'SUPERSEDED' AND current_revision_id IS NOT NULL AND evidence_id IS NULL)
        OR (marker_kind IN ('EVIDENCE_DELETED', 'SOURCE_INVALIDATED') AND current_revision_id IS NULL AND evidence_id IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_brief_marker_superseded
    ON brief_item_markers(brief_item_id, marker_kind, current_revision_id)
    WHERE current_revision_id IS NOT NULL;
CREATE UNIQUE INDEX uq_brief_marker_evidence
    ON brief_item_markers(brief_item_id, marker_kind, evidence_id)
    WHERE evidence_id IS NOT NULL;
CREATE INDEX idx_brief_item_markers_item ON brief_item_markers(brief_item_id, marked_at, marker_id);

CREATE TRIGGER brief_item_marker_requires_legal_source
BEFORE INSERT ON brief_item_markers
WHEN (
    NEW.marker_kind = 'SUPERSEDED'
    AND NOT EXISTS (
        SELECT 1
        FROM brief_items AS item
        JOIN intelligence_revisions AS current_revision ON current_revision.revision_id = NEW.current_revision_id
        JOIN intelligences AS intelligence ON intelligence.intelligence_id = item.intelligence_id
        WHERE item.brief_item_id = NEW.brief_item_id
          AND current_revision.intelligence_id = item.intelligence_id
          AND current_revision.revision_id != item.revision_id
          AND intelligence.current_revision_id = current_revision.revision_id
    )
) OR (
    NEW.marker_kind IN ('EVIDENCE_DELETED', 'SOURCE_INVALIDATED')
    AND NOT EXISTS (
        SELECT 1
        FROM brief_item_evidence AS item_evidence
        JOIN evidence AS source_evidence ON source_evidence.evidence_id = item_evidence.evidence_id
        WHERE item_evidence.brief_item_id = NEW.brief_item_id
          AND item_evidence.evidence_id = NEW.evidence_id
          AND (
              (NEW.marker_kind = 'EVIDENCE_DELETED' AND source_evidence.availability = 'DELETED')
              OR (NEW.marker_kind = 'SOURCE_INVALIDATED' AND source_evidence.availability = 'UNAVAILABLE')
          )
    )
) OR (
    NEW.marker_kind = 'SUPERSEDED'
    AND NEW.reason != 'A later trusted Intelligence revision supersedes this historical snapshot item.'
) OR (
    NEW.marker_kind = 'EVIDENCE_DELETED'
    AND NEW.reason != 'Historical supporting evidence was later deleted.'
) OR (
    NEW.marker_kind = 'SOURCE_INVALIDATED'
    AND NEW.reason != 'Historical supporting evidence is no longer available.'
)
BEGIN
    SELECT RAISE(ABORT, 'brief marker requires an affected legal source');
END;

CREATE TRIGGER brief_item_markers_immutable_update
BEFORE UPDATE ON brief_item_markers
BEGIN
    SELECT RAISE(ABORT, 'brief item markers are append-only');
END;

CREATE TRIGGER brief_item_markers_immutable_delete
BEFORE DELETE ON brief_item_markers
BEGIN
    SELECT RAISE(ABORT, 'brief item markers are retained for history');
END;
