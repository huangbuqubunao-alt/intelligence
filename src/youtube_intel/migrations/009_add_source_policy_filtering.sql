-- TASK-021: explicit source policy, deterministic relevance screening, and
-- append-only filter history. Existing data is deliberately not rewritten.

CREATE TABLE source_policy_revisions (
    revision_id TEXT PRIMARY KEY CHECK (length(trim(revision_id)) > 0 AND length(revision_id) <= 512),
    policy_scope TEXT NOT NULL CHECK (policy_scope IN ('GLOBAL', 'SOURCE')),
    source_id TEXT REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    initial_history_count INTEGER CHECK (initial_history_count IS NULL OR initial_history_count IN (0, 1, 3, 5, 10)),
    per_run_max_new_videos INTEGER CHECK (per_run_max_new_videos IS NULL OR per_run_max_new_videos IN (1, 3, 5, 10)),
    focus_mode TEXT NOT NULL CHECK (focus_mode IN ('INHERIT', 'OVERRIDE')),
    focus_rules_json TEXT NOT NULL CHECK (json_valid(focus_rules_json) AND json_type(focus_rules_json) = 'array'),
    ignore_mode TEXT NOT NULL CHECK (ignore_mode IN ('INHERIT', 'OVERRIDE')),
    ignore_rules_json TEXT NOT NULL CHECK (json_valid(ignore_rules_json) AND json_type(ignore_rules_json) = 'array'),
    distillation_style_mode TEXT NOT NULL CHECK (distillation_style_mode IN ('INHERIT', 'OVERRIDE')),
    distillation_style TEXT CHECK (distillation_style IS NULL OR distillation_style IN ('BALANCED', 'TECHNICAL_DETAIL_FIRST', 'PRODUCT_CASE_FIRST', 'TREND_OPINION_FIRST')),
    created_at TEXT NOT NULL,
    CHECK (
        (policy_scope = 'GLOBAL'
            AND source_id IS NULL
            AND initial_history_count IS NOT NULL
            AND per_run_max_new_videos IS NOT NULL
            AND focus_mode = 'OVERRIDE'
            AND ignore_mode = 'OVERRIDE'
            AND distillation_style_mode = 'OVERRIDE'
            AND distillation_style IS NOT NULL)
        OR
        (policy_scope = 'SOURCE'
            AND source_id IS NOT NULL
            AND (focus_mode = 'OVERRIDE' OR focus_rules_json = '[]')
            AND (ignore_mode = 'OVERRIDE' OR ignore_rules_json = '[]')
            AND (distillation_style_mode = 'OVERRIDE' OR distillation_style IS NULL)
            AND (distillation_style_mode = 'INHERIT' OR distillation_style IS NOT NULL))
    )
);
CREATE INDEX idx_source_policy_revisions_scope_created
    ON source_policy_revisions(policy_scope, source_id, created_at, revision_id);

CREATE TRIGGER source_policy_revisions_immutable_update
BEFORE UPDATE ON source_policy_revisions
BEGIN
    SELECT RAISE(ABORT, 'source policy revisions are immutable');
END;

CREATE TRIGGER source_policy_revisions_immutable_delete
BEFORE DELETE ON source_policy_revisions
BEGIN
    SELECT RAISE(ABORT, 'source policy revisions are immutable');
END;

CREATE TRIGGER source_policy_rules_must_be_finite_text
BEFORE INSERT ON source_policy_revisions
WHEN (SELECT COUNT(*) FROM json_each(NEW.focus_rules_json)) > 20
 OR (SELECT COUNT(*) FROM json_each(NEW.ignore_rules_json)) > 20
 OR EXISTS (
    SELECT 1 FROM json_each(NEW.focus_rules_json)
    WHERE type != 'text' OR length(trim(value)) = 0 OR value != trim(value) OR length(value) > 160
)
 OR EXISTS (
    SELECT 1 FROM json_each(NEW.ignore_rules_json)
    WHERE type != 'text' OR length(trim(value)) = 0 OR value != trim(value) OR length(value) > 160
)
 OR EXISTS (
    SELECT 1 FROM json_each(NEW.focus_rules_json) GROUP BY lower(value) HAVING COUNT(*) > 1
)
 OR EXISTS (
    SELECT 1 FROM json_each(NEW.ignore_rules_json) GROUP BY lower(value) HAVING COUNT(*) > 1
)
BEGIN
    SELECT RAISE(ABORT, 'source policy rules must be finite text');
END;

CREATE TABLE source_policy_current (
    policy_key TEXT PRIMARY KEY CHECK (length(trim(policy_key)) > 0 AND length(policy_key) <= 768),
    policy_scope TEXT NOT NULL CHECK (policy_scope IN ('GLOBAL', 'SOURCE')),
    source_id TEXT UNIQUE REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    revision_id TEXT NOT NULL REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    CHECK (
        (policy_scope = 'GLOBAL' AND policy_key = 'GLOBAL' AND source_id IS NULL)
        OR
        (policy_scope = 'SOURCE' AND source_id IS NOT NULL AND policy_key = 'SOURCE:' || source_id)
    )
);

CREATE TRIGGER source_policy_current_matches_revision
BEFORE INSERT ON source_policy_current
WHEN NOT EXISTS (
    SELECT 1 FROM source_policy_revisions AS revision
    WHERE revision.revision_id = NEW.revision_id
      AND revision.policy_scope = NEW.policy_scope
      AND (revision.source_id IS NEW.source_id)
)
BEGIN
    SELECT RAISE(ABORT, 'source policy pointer must match revision scope');
END;

CREATE TRIGGER source_policy_current_update_matches_revision
BEFORE UPDATE OF revision_id, policy_scope, source_id ON source_policy_current
WHEN NOT EXISTS (
    SELECT 1 FROM source_policy_revisions AS revision
    WHERE revision.revision_id = NEW.revision_id
      AND revision.policy_scope = NEW.policy_scope
      AND (revision.source_id IS NEW.source_id)
)
BEGIN
    SELECT RAISE(ABORT, 'source policy pointer must match revision scope');
END;

INSERT INTO source_policy_revisions (
    revision_id, policy_scope, source_id, initial_history_count,
    per_run_max_new_videos, focus_mode, focus_rules_json, ignore_mode,
    ignore_rules_json, distillation_style_mode, distillation_style, created_at
) VALUES (
    'source-policy:global:bootstrap', 'GLOBAL', NULL, 5, 5,
    'OVERRIDE', '[]', 'OVERRIDE', '[]', 'OVERRIDE', 'BALANCED',
    '1970-01-01T00:00:00.000000Z'
);
INSERT INTO source_policy_current (policy_key, policy_scope, source_id, revision_id)
VALUES ('GLOBAL', 'GLOBAL', NULL, 'source-policy:global:bootstrap');

CREATE TABLE source_video_filter_decisions (
    decision_order INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE CHECK (length(trim(decision_id)) > 0 AND length(decision_id) <= 512),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    stage TEXT NOT NULL CHECK (stage IN ('STAGE_1', 'STAGE_2', 'MANUAL_OVERRIDE')),
    outcome TEXT NOT NULL CHECK (outcome IN ('RELEVANT', 'NOT_RELEVANT', 'UNCERTAIN')),
    reason TEXT NOT NULL CHECK (reason IN ('FOCUS_MATCH', 'IGNORE_RULE_MATCH', 'SHORT_VIDEO', 'NO_FOCUS_MATCH', 'NO_FOCUS_RULES', 'INSUFFICIENT_METADATA', 'STAGE_TWO_REVIEW', 'MANUAL_ANALYZE')),
    global_policy_revision_id TEXT NOT NULL REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    source_policy_revision_id TEXT REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    manual_override_id TEXT,
    prior_decision_id TEXT REFERENCES source_video_filter_decisions(decision_id) ON DELETE RESTRICT,
    evaluated_at TEXT NOT NULL,
    CHECK (
        (stage = 'STAGE_1' AND manual_override_id IS NULL AND prior_decision_id IS NULL AND (
            (outcome = 'RELEVANT' AND reason = 'FOCUS_MATCH')
            OR (outcome = 'NOT_RELEVANT' AND reason IN ('IGNORE_RULE_MATCH', 'SHORT_VIDEO', 'NO_FOCUS_MATCH'))
            OR (outcome = 'UNCERTAIN' AND reason IN ('INSUFFICIENT_METADATA', 'NO_FOCUS_RULES'))
        ))
        OR (stage = 'STAGE_2' AND manual_override_id IS NULL AND prior_decision_id IS NULL AND outcome IN ('RELEVANT', 'NOT_RELEVANT') AND reason = 'STAGE_TWO_REVIEW')
        OR (stage = 'MANUAL_OVERRIDE' AND outcome = 'RELEVANT' AND reason = 'MANUAL_ANALYZE' AND manual_override_id IS NOT NULL AND prior_decision_id IS NOT NULL)
    )
);
CREATE INDEX idx_source_video_filter_decisions_source_video
    ON source_video_filter_decisions(source_id, video_id, decision_order);

CREATE TRIGGER source_video_filter_decisions_immutable_update
BEFORE UPDATE ON source_video_filter_decisions
BEGIN
    SELECT RAISE(ABORT, 'filter decisions are immutable');
END;

CREATE TRIGGER source_video_filter_decisions_immutable_delete
BEFORE DELETE ON source_video_filter_decisions
BEGIN
    SELECT RAISE(ABORT, 'filter decisions are immutable');
END;

CREATE TABLE manual_analyze_overrides (
    override_id TEXT PRIMARY KEY CHECK (length(trim(override_id)) > 0 AND length(override_id) <= 512),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    command_id TEXT NOT NULL CHECK (length(trim(command_id)) > 0 AND length(command_id) <= 512),
    prior_decision_id TEXT NOT NULL REFERENCES source_video_filter_decisions(decision_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    UNIQUE(source_id, video_id, command_id)
);
CREATE INDEX idx_manual_analyze_overrides_source_video
    ON manual_analyze_overrides(source_id, video_id, created_at, override_id);

CREATE TRIGGER manual_analyze_overrides_immutable_update
BEFORE UPDATE ON manual_analyze_overrides
BEGIN
    SELECT RAISE(ABORT, 'manual analyze overrides are immutable');
END;

CREATE TRIGGER manual_analyze_overrides_immutable_delete
BEFORE DELETE ON manual_analyze_overrides
BEGIN
    SELECT RAISE(ABORT, 'manual analyze overrides are immutable');
END;

CREATE TRIGGER source_video_filter_decision_context_must_be_authoritative
BEFORE INSERT ON source_video_filter_decisions
WHEN NOT EXISTS (
    SELECT 1 FROM source_video_links AS link
    WHERE link.source_id = NEW.source_id AND link.video_id = NEW.video_id
)
 OR NOT EXISTS (
    SELECT 1 FROM source_policy_revisions AS global_revision
    WHERE global_revision.revision_id = NEW.global_policy_revision_id
      AND global_revision.policy_scope = 'GLOBAL'
)
 OR (NEW.source_policy_revision_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM source_policy_revisions AS source_revision
    WHERE source_revision.revision_id = NEW.source_policy_revision_id
      AND source_revision.policy_scope = 'SOURCE'
      AND source_revision.source_id = NEW.source_id
))
 OR (NEW.stage = 'MANUAL_OVERRIDE' AND NOT EXISTS (
    SELECT 1
    FROM manual_analyze_overrides AS override
    JOIN source_video_filter_decisions AS prior
      ON prior.decision_id = NEW.prior_decision_id
    WHERE override.override_id = NEW.manual_override_id
      AND override.source_id = NEW.source_id
      AND override.video_id = NEW.video_id
      AND override.prior_decision_id = NEW.prior_decision_id
      AND prior.source_id = NEW.source_id
      AND prior.video_id = NEW.video_id
      AND prior.outcome = 'NOT_RELEVANT'
))
BEGIN
    SELECT RAISE(ABORT, 'filter decision context is not authoritative');
END;
