-- TASK-023: live Topic identity with immutable source-backed membership and history.
-- Existing Intelligence/Evidence remain the only trust roots.  This migration
-- deliberately creates no Topic projection from historic text or revisions.

CREATE TABLE topics (
    topic_id TEXT PRIMARY KEY CHECK (length(trim(topic_id)) > 0 AND length(topic_id) <= 512),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0 AND length(name) <= 240),
    pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
    lifecycle TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (lifecycle IN ('ACTIVE', 'MERGED')),
    merged_into_topic_id TEXT REFERENCES topics(topic_id) ON DELETE RESTRICT,
    current_event_id TEXT REFERENCES topic_timeline_events(event_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (lifecycle = 'ACTIVE' AND merged_into_topic_id IS NULL)
        OR (lifecycle = 'MERGED' AND merged_into_topic_id IS NOT NULL)
    )
);
CREATE INDEX idx_topics_pinned_updated ON topics(pinned DESC, updated_at DESC, topic_id ASC);

CREATE TRIGGER topic_identity_immutable
BEFORE UPDATE ON topics
WHEN NEW.topic_id IS NOT OLD.topic_id OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'topic identity is immutable');
END;

CREATE TRIGGER topic_merge_target_must_be_active
BEFORE UPDATE OF lifecycle, merged_into_topic_id ON topics
WHEN NEW.lifecycle = 'MERGED' AND (
    NEW.merged_into_topic_id = OLD.topic_id
    OR NOT EXISTS (
        SELECT 1 FROM topics
        WHERE topic_id = NEW.merged_into_topic_id AND lifecycle = 'ACTIVE'
    )
)
BEGIN
    SELECT RAISE(ABORT, 'topic merge target must be an active different topic');
END;

CREATE TABLE topic_memberships (
    membership_id TEXT PRIMARY KEY CHECK (length(trim(membership_id)) > 0 AND length(membership_id) <= 512),
    topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE RESTRICT,
    intelligence_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    association_kind TEXT NOT NULL CHECK (association_kind IN ('NEW_INFORMATION', 'SUPPORTING_REPETITION', 'NEW_EVIDENCE', 'CONTRADICTORY_INFORMATION', 'LOW_VALUE_DUPLICATE')),
    source_claim_kind TEXT NOT NULL CHECK (source_claim_kind IN ('FACT', 'EVIDENCE_BACKED_STATEMENT', 'OPINION', 'PREDICTION', 'RUMOR', 'SYSTEM_INFERENCE')),
    source_state TEXT NOT NULL CHECK (source_state IN ('NEW', 'PENDING_CONFIRMATION', 'CONFIRMED', 'DISPUTED', 'UPDATED', 'INVALIDATED', 'OVERTURNED')),
    created_at TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    UNIQUE(topic_id, intelligence_id, revision_id),
    FOREIGN KEY (intelligence_id, revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id) ON DELETE RESTRICT
);
CREATE INDEX idx_topic_memberships_topic ON topic_memberships(topic_id, created_at, membership_id);
CREATE INDEX idx_topic_memberships_revision ON topic_memberships(intelligence_id, revision_id, topic_id);

CREATE TRIGGER topic_membership_must_match_immutable_intelligence
BEFORE INSERT ON topic_memberships
WHEN NOT EXISTS (
    SELECT 1
    FROM intelligence_revisions AS revision
    JOIN intelligence_state_history AS history ON history.revision_id = revision.revision_id
    WHERE revision.intelligence_id = NEW.intelligence_id
      AND revision.revision_id = NEW.revision_id
      AND revision.claim_kind = NEW.source_claim_kind
      AND history.state = NEW.source_state
)
BEGIN
    SELECT RAISE(ABORT, 'topic membership must cite matching intelligence revision state');
END;

CREATE TRIGGER topic_membership_immutable_update
BEFORE UPDATE ON topic_memberships
BEGIN
    SELECT RAISE(ABORT, 'topic memberships are immutable');
END;

CREATE TRIGGER topic_membership_immutable_delete
BEFORE DELETE ON topic_memberships
BEGIN
    SELECT RAISE(ABORT, 'topic memberships are immutable');
END;

CREATE TABLE topic_membership_evidence (
    membership_id TEXT NOT NULL REFERENCES topic_memberships(membership_id) ON DELETE RESTRICT,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    PRIMARY KEY(membership_id, evidence_id)
);

CREATE TRIGGER topic_membership_evidence_must_match_revision_support
BEFORE INSERT ON topic_membership_evidence
WHEN NOT EXISTS (
    SELECT 1
    FROM topic_memberships AS membership
    JOIN intelligence_revision_evidence AS support
      ON support.revision_id = membership.revision_id
    WHERE membership.membership_id = NEW.membership_id
      AND support.evidence_id = NEW.evidence_id
)
BEGIN
    SELECT RAISE(ABORT, 'topic membership evidence must be exact revision support');
END;

CREATE TRIGGER topic_membership_evidence_immutable_update
BEFORE UPDATE ON topic_membership_evidence
BEGIN
    SELECT RAISE(ABORT, 'topic membership evidence is immutable');
END;

CREATE TRIGGER topic_membership_evidence_immutable_delete
BEFORE DELETE ON topic_membership_evidence
BEGIN
    SELECT RAISE(ABORT, 'topic membership evidence is immutable');
END;

CREATE TABLE topic_timeline_events (
    event_id TEXT PRIMARY KEY CHECK (length(trim(event_id)) > 0 AND length(event_id) <= 512),
    topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE RESTRICT,
    primary_membership_id TEXT NOT NULL REFERENCES topic_memberships(membership_id) ON DELETE RESTRICT,
    event_kind TEXT NOT NULL CHECK (event_kind IN ('NEW_INFORMATION', 'NEW_EVIDENCE', 'CONTRADICTION')),
    state TEXT NOT NULL CHECK (state IN ('UNRESOLVED', 'CONSENSUS', 'DISAGREEMENT', 'DEGRADED')),
    created_at TEXT NOT NULL
);
CREATE INDEX idx_topic_timeline_events_topic ON topic_timeline_events(topic_id, created_at, event_id);

CREATE TRIGGER topic_timeline_event_primary_dependency_must_belong_to_topic
BEFORE INSERT ON topic_timeline_events
WHEN NOT EXISTS (
    SELECT 1 FROM topic_memberships
    WHERE membership_id = NEW.primary_membership_id AND topic_id = NEW.topic_id
)
BEGIN
    SELECT RAISE(ABORT, 'topic timeline event requires an owned membership dependency');
END;

CREATE TRIGGER topic_timeline_event_kind_must_match_primary_membership
BEFORE INSERT ON topic_timeline_events
WHEN NOT EXISTS (
    SELECT 1
    FROM topic_memberships
    WHERE membership_id = NEW.primary_membership_id
      AND topic_id = NEW.topic_id
      AND (
        (NEW.event_kind = 'NEW_INFORMATION' AND association_kind = 'NEW_INFORMATION')
        OR (NEW.event_kind = 'NEW_EVIDENCE' AND association_kind = 'NEW_EVIDENCE')
        OR (NEW.event_kind = 'CONTRADICTION' AND association_kind = 'CONTRADICTORY_INFORMATION')
      )
)
BEGIN
    SELECT RAISE(ABORT, 'topic timeline event kind must match its primary membership');
END;

CREATE TRIGGER topic_timeline_event_state_must_be_supported
BEFORE INSERT ON topic_timeline_events
WHEN (
    NEW.state = 'DISAGREEMENT'
    AND NOT EXISTS (
        SELECT 1 FROM topic_memberships
        WHERE topic_id = NEW.topic_id
          AND association_kind = 'CONTRADICTORY_INFORMATION'
    )
) OR (
    NEW.state = 'CONSENSUS'
    AND (
        (SELECT COUNT(*) FROM topic_memberships WHERE topic_id = NEW.topic_id) < 2
        OR NOT EXISTS (
            SELECT 1
            FROM topic_memberships AS membership
            JOIN topic_membership_evidence AS membership_evidence
              ON membership_evidence.membership_id = membership.membership_id
            JOIN evidence ON evidence.evidence_id = membership_evidence.evidence_id
            WHERE membership.topic_id = NEW.topic_id
              AND membership.association_kind = 'NEW_EVIDENCE'
              AND evidence.role = 'INDEPENDENT_VERIFICATION'
        )
    )
)
BEGIN
    SELECT RAISE(ABORT, 'topic timeline event state is not supported by its memberships');
END;

CREATE TRIGGER topic_timeline_event_immutable_update
BEFORE UPDATE ON topic_timeline_events
BEGIN
    SELECT RAISE(ABORT, 'topic timeline events are immutable');
END;

CREATE TRIGGER topic_timeline_event_immutable_delete
BEFORE DELETE ON topic_timeline_events
BEGIN
    SELECT RAISE(ABORT, 'topic timeline events are immutable');
END;

CREATE TABLE topic_timeline_event_memberships (
    event_id TEXT NOT NULL REFERENCES topic_timeline_events(event_id) ON DELETE RESTRICT,
    membership_id TEXT NOT NULL REFERENCES topic_memberships(membership_id) ON DELETE RESTRICT,
    PRIMARY KEY(event_id, membership_id)
);

CREATE TRIGGER topic_timeline_dependency_must_belong_to_topic
BEFORE INSERT ON topic_timeline_event_memberships
WHEN NOT EXISTS (
    SELECT 1
    FROM topic_timeline_events AS event
    JOIN topic_memberships AS membership ON membership.topic_id = event.topic_id
    WHERE event.event_id = NEW.event_id AND membership.membership_id = NEW.membership_id
)
BEGIN
    SELECT RAISE(ABORT, 'topic timeline dependency must belong to its topic');
END;

CREATE TRIGGER topic_timeline_event_membership_immutable_update
BEFORE UPDATE ON topic_timeline_event_memberships
BEGIN
    SELECT RAISE(ABORT, 'topic timeline dependencies are immutable');
END;

CREATE TRIGGER topic_timeline_event_membership_immutable_delete
BEFORE DELETE ON topic_timeline_event_memberships
BEGIN
    SELECT RAISE(ABORT, 'topic timeline dependencies are immutable');
END;

CREATE TRIGGER topic_current_event_must_be_meaningful_and_owned
BEFORE UPDATE OF current_event_id ON topics
WHEN NEW.current_event_id IS NOT NULL AND NOT EXISTS (
    SELECT 1
    FROM topic_timeline_events AS event
    JOIN topic_timeline_event_memberships AS dependency
      ON dependency.event_id = event.event_id
    JOIN topic_memberships AS membership
      ON membership.membership_id = dependency.membership_id
    WHERE event.event_id = NEW.current_event_id
      AND event.topic_id = NEW.topic_id
      AND (
        (event.event_kind = 'NEW_INFORMATION' AND membership.association_kind = 'NEW_INFORMATION')
        OR (event.event_kind = 'NEW_EVIDENCE' AND membership.association_kind = 'NEW_EVIDENCE')
        OR (event.event_kind = 'CONTRADICTION' AND membership.association_kind = 'CONTRADICTORY_INFORMATION')
      )
)
BEGIN
    SELECT RAISE(ABORT, 'topic current event must cite a meaningful owned dependency');
END;

CREATE TABLE topic_relations (
    topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE RESTRICT,
    related_topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE RESTRICT,
    relation TEXT NOT NULL CHECK (relation = 'RELATED'),
    created_at TEXT NOT NULL,
    PRIMARY KEY(topic_id, related_topic_id),
    CHECK(topic_id < related_topic_id)
);

CREATE TRIGGER topic_relations_immutable_update
BEFORE UPDATE ON topic_relations
BEGIN
    SELECT RAISE(ABORT, 'topic relations are immutable');
END;

CREATE TRIGGER topic_relations_immutable_delete
BEFORE DELETE ON topic_relations
BEGIN
    SELECT RAISE(ABORT, 'topic relations are immutable');
END;
