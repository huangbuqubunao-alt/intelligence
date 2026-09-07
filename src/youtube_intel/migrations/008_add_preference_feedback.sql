-- TASK-020: feedback is immutable history; preferences are separately projected.
-- This migration deliberately does not infer intent from existing content.

CREATE TABLE preferences (
    preference_id TEXT PRIMARY KEY CHECK (length(trim(preference_id)) > 0),
    horizon TEXT NOT NULL CHECK (horizon IN ('LONG_TERM', 'RECENT', 'TEMPORARY_FOCUS')),
    provenance TEXT NOT NULL CHECK (provenance IN ('EXPLICIT', 'DERIVED', 'TEMPORARY')),
    scope TEXT NOT NULL CHECK (scope IN ('GLOBAL_CONTENT', 'SOURCE_CONTENT', 'VIDEO_CONTENT', 'INTELLIGENCE_CONTENT', 'DISTILLATION_STYLE')),
    target_id TEXT,
    statement TEXT NOT NULL CHECK (length(trim(statement)) > 0 AND length(statement) <= 2048),
    starts_at TEXT,
    expires_at TEXT,
    supersedes_preference_id TEXT REFERENCES preferences(preference_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    CHECK (
        (scope IN ('GLOBAL_CONTENT', 'DISTILLATION_STYLE') AND target_id IS NULL)
        OR (scope IN ('SOURCE_CONTENT', 'VIDEO_CONTENT', 'INTELLIGENCE_CONTENT') AND target_id IS NOT NULL AND length(trim(target_id)) > 0)
    ),
    CHECK (
        (horizon = 'LONG_TERM' AND provenance = 'EXPLICIT' AND starts_at IS NULL AND expires_at IS NULL)
        OR (horizon = 'RECENT' AND provenance = 'DERIVED' AND starts_at IS NULL AND expires_at IS NULL)
        OR (horizon = 'TEMPORARY_FOCUS' AND provenance = 'TEMPORARY' AND starts_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at > starts_at)
    )
);
CREATE INDEX idx_preferences_scope_created ON preferences(scope, created_at, preference_id);

CREATE TRIGGER preference_source_target_must_exist
BEFORE INSERT ON preferences
WHEN NEW.scope = 'SOURCE_CONTENT'
 AND NOT EXISTS (SELECT 1 FROM source_subscriptions WHERE source_id = NEW.target_id)
BEGIN
    SELECT RAISE(ABORT, 'preference source target does not exist');
END;

CREATE TRIGGER preference_video_target_must_exist
BEFORE INSERT ON preferences
WHEN NEW.scope = 'VIDEO_CONTENT'
 AND NOT EXISTS (SELECT 1 FROM videos WHERE video_id = NEW.target_id)
BEGIN
    SELECT RAISE(ABORT, 'preference video target does not exist');
END;

CREATE TRIGGER preference_intelligence_target_must_exist
BEFORE INSERT ON preferences
WHEN NEW.scope = 'INTELLIGENCE_CONTENT'
 AND NOT EXISTS (SELECT 1 FROM intelligences WHERE intelligence_id = NEW.target_id)
BEGIN
    SELECT RAISE(ABORT, 'preference intelligence target does not exist');
END;

CREATE TRIGGER preference_supersession_preserves_authority_class
BEFORE INSERT ON preferences
WHEN NEW.supersedes_preference_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1 FROM preferences AS prior
    WHERE prior.preference_id = NEW.supersedes_preference_id
      AND prior.horizon = NEW.horizon
      AND prior.provenance = NEW.provenance
      AND prior.scope = NEW.scope
      AND (prior.target_id IS NEW.target_id)
 )
BEGIN
    SELECT RAISE(ABORT, 'preference supersession cannot cross horizon, provenance, or target');
END;

CREATE TRIGGER preferences_immutable_update
BEFORE UPDATE ON preferences
BEGIN
    SELECT RAISE(ABORT, 'preferences are immutable records');
END;

CREATE TRIGGER preferences_immutable_delete
BEFORE DELETE ON preferences
BEGIN
    SELECT RAISE(ABORT, 'preferences are immutable records');
END;

CREATE TABLE preference_state_events (
    state_event_id TEXT PRIMARY KEY CHECK (length(trim(state_event_id)) > 0),
    preference_id TEXT NOT NULL REFERENCES preferences(preference_id) ON DELETE RESTRICT,
    state TEXT NOT NULL CHECK (state IN ('ACTIVATED', 'REPLACED', 'DELETED')),
    created_at TEXT NOT NULL
);
CREATE INDEX idx_preference_state_events_preference ON preference_state_events(preference_id, created_at, state_event_id);

CREATE TRIGGER preference_state_event_must_follow_lifecycle
BEFORE INSERT ON preference_state_events
WHEN (NEW.state = 'ACTIVATED' AND EXISTS (
    SELECT 1 FROM preference_state_events WHERE preference_id = NEW.preference_id
))
 OR (NEW.state IN ('REPLACED', 'DELETED') AND (
    NOT EXISTS (SELECT 1 FROM preference_state_events WHERE preference_id = NEW.preference_id AND state = 'ACTIVATED')
    OR EXISTS (SELECT 1 FROM preference_state_events WHERE preference_id = NEW.preference_id AND state IN ('REPLACED', 'DELETED'))
 ))
BEGIN
    SELECT RAISE(ABORT, 'preference state event violates immutable lifecycle');
END;

CREATE TRIGGER preference_activation_requires_replaced_prior
BEFORE INSERT ON preference_state_events
WHEN NEW.state = 'ACTIVATED'
 AND EXISTS (
    SELECT 1 FROM preferences AS replacement
    WHERE replacement.preference_id = NEW.preference_id
      AND replacement.supersedes_preference_id IS NOT NULL
 )
 AND NOT EXISTS (
    SELECT 1
    FROM preferences AS replacement
    JOIN preference_state_events AS prior_state
      ON prior_state.preference_id = replacement.supersedes_preference_id
    WHERE replacement.preference_id = NEW.preference_id
      AND prior_state.state = 'REPLACED'
 )
BEGIN
    SELECT RAISE(ABORT, 'replacement preference requires immutable prior retirement');
END;

CREATE TRIGGER preference_state_events_immutable_update
BEFORE UPDATE ON preference_state_events
BEGIN
    SELECT RAISE(ABORT, 'preference state events are immutable');
END;

CREATE TRIGGER preference_state_events_immutable_delete
BEFORE DELETE ON preference_state_events
BEGIN
    SELECT RAISE(ABORT, 'preference state events are immutable');
END;

CREATE TABLE feedback_events (
    feedback_id TEXT PRIMARY KEY CHECK (length(trim(feedback_id)) > 0),
    kind TEXT NOT NULL CHECK (kind IN ('MORE_LIKE_THIS', 'LESS_LIKE_THIS', 'IMPORTANT', 'NATURAL_LANGUAGE', 'EXPLICIT_PREFERENCE_STATEMENT', 'FACTUAL_CORRECTION')),
    scope TEXT NOT NULL CHECK (scope IN ('GLOBAL_CONTENT', 'SOURCE_CONTENT', 'VIDEO_CONTENT', 'INTELLIGENCE_CONTENT', 'DISTILLATION_STYLE')),
    target_id TEXT,
    content TEXT CHECK (content IS NULL OR (length(trim(content)) > 0 AND length(content) <= 2048)),
    correction_kind TEXT CHECK (correction_kind IS NULL OR correction_kind IN ('WRONG_INTERPRETATION', 'SOURCE_UNSUPPORTED', 'OUTDATED', 'VIEWPOINTS_MERGED', 'OTHER')),
    effect_status TEXT NOT NULL CHECK (effect_status = 'RECORDED'),
    created_at TEXT NOT NULL,
    CHECK (
        (scope IN ('GLOBAL_CONTENT', 'DISTILLATION_STYLE') AND target_id IS NULL)
        OR (scope IN ('SOURCE_CONTENT', 'VIDEO_CONTENT', 'INTELLIGENCE_CONTENT') AND target_id IS NOT NULL AND length(trim(target_id)) > 0)
    ),
    CHECK (
        (kind IN ('MORE_LIKE_THIS', 'LESS_LIKE_THIS', 'IMPORTANT') AND content IS NULL AND correction_kind IS NULL)
        OR (kind IN ('NATURAL_LANGUAGE', 'EXPLICIT_PREFERENCE_STATEMENT') AND content IS NOT NULL AND correction_kind IS NULL)
        OR (kind = 'FACTUAL_CORRECTION' AND content IS NOT NULL AND correction_kind IS NOT NULL)
    )
);
CREATE INDEX idx_feedback_events_created ON feedback_events(created_at, feedback_id);

CREATE TRIGGER feedback_source_target_must_exist
BEFORE INSERT ON feedback_events
WHEN NEW.scope = 'SOURCE_CONTENT'
 AND NOT EXISTS (SELECT 1 FROM source_subscriptions WHERE source_id = NEW.target_id)
BEGIN
    SELECT RAISE(ABORT, 'feedback source target does not exist');
END;

CREATE TRIGGER feedback_video_target_must_exist
BEFORE INSERT ON feedback_events
WHEN NEW.scope = 'VIDEO_CONTENT'
 AND NOT EXISTS (SELECT 1 FROM videos WHERE video_id = NEW.target_id)
BEGIN
    SELECT RAISE(ABORT, 'feedback video target does not exist');
END;

CREATE TRIGGER feedback_intelligence_target_must_exist
BEFORE INSERT ON feedback_events
WHEN NEW.scope = 'INTELLIGENCE_CONTENT'
 AND NOT EXISTS (SELECT 1 FROM intelligences WHERE intelligence_id = NEW.target_id)
BEGIN
    SELECT RAISE(ABORT, 'feedback intelligence target does not exist');
END;

CREATE TRIGGER feedback_events_immutable_update
BEFORE UPDATE ON feedback_events
BEGIN
    SELECT RAISE(ABORT, 'feedback events are immutable');
END;

CREATE TRIGGER feedback_events_immutable_delete
BEFORE DELETE ON feedback_events
BEGIN
    SELECT RAISE(ABORT, 'feedback events are immutable');
END;
