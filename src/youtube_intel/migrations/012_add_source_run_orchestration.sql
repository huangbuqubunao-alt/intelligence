-- TASK-023A: durable top-level Source Run persistence for TASK-024 to consume.
-- Source Runs are deliberately distinct from m005 schedule occurrences and m010
-- protected per-video distillation checkpoints. Existing history is not inferred.

CREATE TABLE source_runs (
    run_id TEXT PRIMARY KEY CHECK (length(trim(run_id)) > 0 AND length(run_id) <= 512),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    trigger TEXT NOT NULL CHECK (trigger IN ('MANUAL_CHECK_NOW', 'SCHEDULED_SOURCE_RUN', 'MANUAL_ANALYZE_VIDEO')),
    trigger_reference TEXT NOT NULL CHECK (length(trim(trigger_reference)) > 0 AND length(trigger_reference) <= 512),
    priority TEXT NOT NULL CHECK (priority IN ('P0', 'P1', 'P2', 'P3')),
    idempotency_key TEXT NOT NULL CHECK (length(trim(idempotency_key)) > 0 AND length(idempotency_key) <= 512),
    state TEXT NOT NULL CHECK (state IN ('QUEUED', 'RUNNING', 'WAITING', 'PARTIAL', 'NEEDS_ATTENTION', 'COMPLETED', 'FAILED', 'AMBIGUOUS', 'CANCELLED')),
    attention_reason TEXT CHECK (attention_reason IS NULL OR attention_reason IN ('AMBIGUOUS_EXTERNAL_OUTCOME', 'MODEL_UNAVAILABLE', 'BUDGET_BLOCKED', 'USER_DECISION_REQUIRED', 'EXECUTION_CONDITION_UNRESOLVED')),
    automation_run_id TEXT REFERENCES automation_runs(run_id) ON DELETE RESTRICT,
    manual_command_id TEXT CHECK (manual_command_id IS NULL OR (length(trim(manual_command_id)) > 0 AND length(manual_command_id) <= 512)),
    manual_analyze_override_id TEXT REFERENCES manual_analyze_overrides(override_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, idempotency_key),
    CHECK (
        (trigger = 'MANUAL_CHECK_NOW'
            AND automation_run_id IS NULL
            AND manual_command_id IS NOT NULL
            AND manual_analyze_override_id IS NULL
            AND trigger_reference = manual_command_id)
        OR
        (trigger = 'SCHEDULED_SOURCE_RUN'
            AND automation_run_id IS NOT NULL
            AND manual_command_id IS NULL
            AND manual_analyze_override_id IS NULL
            AND trigger_reference = automation_run_id)
        OR
        (trigger = 'MANUAL_ANALYZE_VIDEO'
            AND automation_run_id IS NULL
            AND manual_command_id IS NOT NULL
            AND manual_analyze_override_id IS NOT NULL
            AND trigger_reference = manual_analyze_override_id)
    ),
    CHECK (
        (state IN ('NEEDS_ATTENTION', 'AMBIGUOUS') AND attention_reason IS NOT NULL)
        OR (state NOT IN ('NEEDS_ATTENTION', 'AMBIGUOUS') AND attention_reason IS NULL)
    ),
    CHECK (state != 'AMBIGUOUS' OR attention_reason = 'AMBIGUOUS_EXTERNAL_OUTCOME')
);
CREATE INDEX idx_source_runs_admission
    ON source_runs(state, priority, created_at, run_id);
CREATE INDEX idx_source_runs_source_created
    ON source_runs(source_id, created_at, run_id);

CREATE TRIGGER source_run_schedule_context_must_match_source
BEFORE INSERT ON source_runs
WHEN NEW.trigger = 'SCHEDULED_SOURCE_RUN' AND NOT EXISTS (
    SELECT 1
    FROM automation_runs AS occurrence
    JOIN automation_schedules AS schedule ON schedule.schedule_id = occurrence.schedule_id
    WHERE occurrence.run_id = NEW.automation_run_id
      AND occurrence.target_type = 'SOURCE_CHECK'
      AND occurrence.target_id = NEW.source_id
      AND schedule.target_type = 'SOURCE_CHECK'
      AND schedule.target_id = NEW.source_id
)
BEGIN
    SELECT RAISE(ABORT, 'scheduled Source Run must reference its Source occurrence');
END;

CREATE TRIGGER source_run_manual_analyze_context_must_match_source
BEFORE INSERT ON source_runs
WHEN NEW.trigger = 'MANUAL_ANALYZE_VIDEO' AND NOT EXISTS (
    SELECT 1
    FROM manual_analyze_overrides AS override
    WHERE override.override_id = NEW.manual_analyze_override_id
      AND override.source_id = NEW.source_id
      AND override.command_id = NEW.manual_command_id
)
BEGIN
    SELECT RAISE(ABORT, 'manual analyze Source Run must reference its exact override');
END;

CREATE TRIGGER source_run_identity_immutable
BEFORE UPDATE ON source_runs
WHEN NEW.run_id IS NOT OLD.run_id
  OR NEW.source_id IS NOT OLD.source_id
  OR NEW.trigger IS NOT OLD.trigger
  OR NEW.trigger_reference IS NOT OLD.trigger_reference
  OR NEW.priority IS NOT OLD.priority
  OR NEW.idempotency_key IS NOT OLD.idempotency_key
  OR NEW.automation_run_id IS NOT OLD.automation_run_id
  OR NEW.manual_command_id IS NOT OLD.manual_command_id
  OR NEW.manual_analyze_override_id IS NOT OLD.manual_analyze_override_id
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'Source Run identity and admission context are immutable');
END;

CREATE TRIGGER source_run_state_transition_must_be_legal
BEFORE UPDATE OF state ON source_runs
WHEN NEW.state IS NOT OLD.state AND NOT (
    (OLD.state = 'QUEUED' AND NEW.state IN ('RUNNING', 'WAITING', 'PARTIAL', 'NEEDS_ATTENTION', 'FAILED', 'CANCELLED'))
    OR (OLD.state = 'RUNNING' AND NEW.state IN ('WAITING', 'PARTIAL', 'NEEDS_ATTENTION', 'COMPLETED', 'FAILED', 'AMBIGUOUS', 'CANCELLED'))
    OR (OLD.state = 'WAITING' AND NEW.state IN ('QUEUED', 'NEEDS_ATTENTION', 'FAILED', 'CANCELLED'))
    OR (OLD.state = 'PARTIAL' AND NEW.state IN ('QUEUED', 'RUNNING', 'WAITING', 'NEEDS_ATTENTION', 'COMPLETED', 'FAILED', 'CANCELLED'))
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run state transition is not legal');
END;

CREATE TRIGGER source_runs_immutable_delete
BEFORE DELETE ON source_runs
BEGIN
    SELECT RAISE(ABORT, 'Source Runs are retained for audit');
END;

CREATE TABLE source_run_state_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES source_runs(run_id) ON DELETE RESTRICT,
    prior_state TEXT CHECK (prior_state IS NULL OR prior_state IN ('QUEUED', 'RUNNING', 'WAITING', 'PARTIAL', 'NEEDS_ATTENTION', 'COMPLETED', 'FAILED', 'AMBIGUOUS', 'CANCELLED')),
    state TEXT NOT NULL CHECK (state IN ('QUEUED', 'RUNNING', 'WAITING', 'PARTIAL', 'NEEDS_ATTENTION', 'COMPLETED', 'FAILED', 'AMBIGUOUS', 'CANCELLED')),
    attention_reason TEXT CHECK (attention_reason IS NULL OR attention_reason IN ('AMBIGUOUS_EXTERNAL_OUTCOME', 'MODEL_UNAVAILABLE', 'BUDGET_BLOCKED', 'USER_DECISION_REQUIRED', 'EXECUTION_CONDITION_UNRESOLVED')),
    occurred_at TEXT NOT NULL
);
CREATE INDEX idx_source_run_state_events_run
    ON source_run_state_events(run_id, event_id);

CREATE TRIGGER source_run_state_events_immutable_update
BEFORE UPDATE ON source_run_state_events
BEGIN
    SELECT RAISE(ABORT, 'Source Run state history is immutable');
END;

CREATE TRIGGER source_run_state_events_immutable_delete
BEFORE DELETE ON source_run_state_events
BEGIN
    SELECT RAISE(ABORT, 'Source Run state history is immutable');
END;

CREATE TRIGGER source_run_initial_state_event
AFTER INSERT ON source_runs
BEGIN
    INSERT INTO source_run_state_events (run_id, prior_state, state, attention_reason, occurred_at)
    VALUES (NEW.run_id, NULL, NEW.state, NEW.attention_reason, NEW.created_at);
END;

CREATE TRIGGER source_run_state_event_on_transition
AFTER UPDATE OF state ON source_runs
WHEN NEW.state IS NOT OLD.state
BEGIN
    INSERT INTO source_run_state_events (run_id, prior_state, state, attention_reason, occurred_at)
    VALUES (NEW.run_id, OLD.state, NEW.state, NEW.attention_reason, NEW.updated_at);
END;

CREATE TABLE source_run_video_executions (
    run_id TEXT NOT NULL REFERENCES source_runs(run_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    state TEXT NOT NULL CHECK (state IN ('PENDING', 'WAITING', 'DEFERRED', 'SKIPPED', 'COMPLETED', 'NEEDS_ATTENTION', 'AMBIGUOUS', 'FAILED')),
    distillation_execution_id TEXT REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(run_id, video_id),
    CHECK ((state IN ('COMPLETED', 'AMBIGUOUS') AND distillation_execution_id IS NOT NULL) OR state NOT IN ('COMPLETED', 'AMBIGUOUS'))
);
CREATE INDEX idx_source_run_video_executions_run_state
    ON source_run_video_executions(run_id, state, video_id);

CREATE TRIGGER source_run_video_execution_context_must_match
BEFORE INSERT ON source_run_video_executions
WHEN NOT EXISTS (
    SELECT 1
    FROM source_runs AS run
    JOIN source_video_links AS link ON link.source_id = run.source_id
    WHERE run.run_id = NEW.run_id AND link.video_id = NEW.video_id
)
 OR (NEW.distillation_execution_id IS NOT NULL AND NOT EXISTS (
    SELECT 1
    FROM source_runs AS run
    JOIN distillation_execution_checkpoints AS checkpoint
      ON checkpoint.source_id = run.source_id
    WHERE run.run_id = NEW.run_id
      AND checkpoint.execution_id = NEW.distillation_execution_id
      AND checkpoint.video_id = NEW.video_id
))
 OR (NEW.state = 'COMPLETED' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'SUCCEEDED'
))
 OR (NEW.state = 'AMBIGUOUS' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'AMBIGUOUS'
))
BEGIN
    SELECT RAISE(ABORT, 'Source Run child must cite matching legal execution state');
END;

CREATE TRIGGER source_run_video_execution_identity_immutable
BEFORE UPDATE ON source_run_video_executions
WHEN NEW.run_id IS NOT OLD.run_id
  OR NEW.video_id IS NOT OLD.video_id
  OR NEW.distillation_execution_id IS NOT OLD.distillation_execution_id
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'Source Run child identity is immutable');
END;

CREATE TRIGGER source_run_video_execution_state_transition_must_be_legal
BEFORE UPDATE OF state ON source_run_video_executions
WHEN NEW.state IS NOT OLD.state AND NOT (
    (OLD.state = 'PENDING' AND NEW.state IN ('WAITING', 'DEFERRED', 'SKIPPED', 'COMPLETED', 'NEEDS_ATTENTION', 'AMBIGUOUS', 'FAILED'))
    OR (OLD.state = 'WAITING' AND NEW.state IN ('PENDING', 'DEFERRED', 'NEEDS_ATTENTION', 'FAILED'))
    OR (OLD.state = 'DEFERRED' AND NEW.state = 'PENDING')
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run child state transition is not legal');
END;

CREATE TRIGGER source_run_video_execution_state_must_match_protected_execution
BEFORE UPDATE OF state ON source_run_video_executions
WHEN (NEW.state = 'COMPLETED' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'SUCCEEDED'
)) OR (NEW.state = 'AMBIGUOUS' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'AMBIGUOUS'
))
BEGIN
    SELECT RAISE(ABORT, 'Source Run child must cite matching legal execution state');
END;

CREATE TRIGGER source_run_video_executions_immutable_delete
BEFORE DELETE ON source_run_video_executions
BEGIN
    SELECT RAISE(ABORT, 'Source Run child executions are retained for audit');
END;

CREATE TABLE source_run_video_execution_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    prior_state TEXT CHECK (prior_state IS NULL OR prior_state IN ('PENDING', 'WAITING', 'DEFERRED', 'SKIPPED', 'COMPLETED', 'NEEDS_ATTENTION', 'AMBIGUOUS', 'FAILED')),
    state TEXT NOT NULL CHECK (state IN ('PENDING', 'WAITING', 'DEFERRED', 'SKIPPED', 'COMPLETED', 'NEEDS_ATTENTION', 'AMBIGUOUS', 'FAILED')),
    occurred_at TEXT NOT NULL,
    FOREIGN KEY(run_id, video_id)
        REFERENCES source_run_video_executions(run_id, video_id) ON DELETE RESTRICT
);
CREATE INDEX idx_source_run_video_execution_events_child
    ON source_run_video_execution_events(run_id, video_id, event_id);

CREATE TRIGGER source_run_video_execution_events_immutable_update
BEFORE UPDATE ON source_run_video_execution_events
BEGIN
    SELECT RAISE(ABORT, 'Source Run child state history is immutable');
END;

CREATE TRIGGER source_run_video_execution_events_immutable_delete
BEFORE DELETE ON source_run_video_execution_events
BEGIN
    SELECT RAISE(ABORT, 'Source Run child state history is immutable');
END;

CREATE TRIGGER source_run_child_initial_state_event
AFTER INSERT ON source_run_video_executions
BEGIN
    INSERT INTO source_run_video_execution_events (run_id, video_id, prior_state, state, occurred_at)
    VALUES (NEW.run_id, NEW.video_id, NULL, NEW.state, NEW.created_at);
END;

CREATE TRIGGER source_run_child_state_event_on_transition
AFTER UPDATE OF state ON source_run_video_executions
WHEN NEW.state IS NOT OLD.state
BEGIN
    INSERT INTO source_run_video_execution_events (run_id, video_id, prior_state, state, occurred_at)
    VALUES (NEW.run_id, NEW.video_id, OLD.state, NEW.state, NEW.updated_at);
END;

CREATE TABLE source_run_checkpoint_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES source_runs(run_id) ON DELETE RESTRICT,
    checkpoint TEXT NOT NULL CHECK (checkpoint IN ('DISCOVERY', 'SELECTION', 'FILTERING', 'SOURCE_PREPARATION', 'DISTILLATION', 'INTELLIGENCE_ADMISSION', 'TOPIC_UPDATE', 'FINALIZATION')),
    checkpoint_position INTEGER NOT NULL CHECK (
        (checkpoint = 'DISCOVERY' AND checkpoint_position = 1)
        OR (checkpoint = 'SELECTION' AND checkpoint_position = 2)
        OR (checkpoint = 'FILTERING' AND checkpoint_position = 3)
        OR (checkpoint = 'SOURCE_PREPARATION' AND checkpoint_position = 4)
        OR (checkpoint = 'DISTILLATION' AND checkpoint_position = 5)
        OR (checkpoint = 'INTELLIGENCE_ADMISSION' AND checkpoint_position = 6)
        OR (checkpoint = 'TOPIC_UPDATE' AND checkpoint_position = 7)
        OR (checkpoint = 'FINALIZATION' AND checkpoint_position = 8)
    ),
    event_status TEXT NOT NULL CHECK (event_status IN ('COMPLETED', 'BLOCKED')),
    created_at TEXT NOT NULL
);
CREATE INDEX idx_source_run_checkpoint_events_run
    ON source_run_checkpoint_events(run_id, checkpoint_position, event_id);

CREATE TRIGGER source_run_checkpoint_events_immutable_update
BEFORE UPDATE ON source_run_checkpoint_events
BEGIN
    SELECT RAISE(ABORT, 'Source Run checkpoint history is immutable');
END;

CREATE TRIGGER source_run_checkpoint_events_immutable_delete
BEFORE DELETE ON source_run_checkpoint_events
BEGIN
    SELECT RAISE(ABORT, 'Source Run checkpoint history is immutable');
END;

CREATE TRIGGER source_run_checkpoint_completion_must_be_ordered
BEFORE INSERT ON source_run_checkpoint_events
WHEN NEW.event_status = 'COMPLETED' AND (
    EXISTS (
        SELECT 1
        FROM (
            SELECT 1 AS checkpoint_position UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
            UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
        ) AS required
        WHERE required.checkpoint_position < NEW.checkpoint_position
          AND NOT EXISTS (
              SELECT 1 FROM source_run_checkpoint_events AS completed
              WHERE completed.run_id = NEW.run_id
                AND completed.checkpoint_position = required.checkpoint_position
                AND completed.event_status = 'COMPLETED'
          )
    )
    OR EXISTS (
        SELECT 1 FROM source_run_checkpoint_events AS completed
        WHERE completed.run_id = NEW.run_id
          AND completed.checkpoint_position = NEW.checkpoint_position
          AND completed.event_status = 'COMPLETED'
    )
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run checkpoint completion is not the safe next step');
END;

CREATE TRIGGER source_run_distillation_checkpoint_requires_legal_children
BEFORE INSERT ON source_run_checkpoint_events
WHEN NEW.checkpoint = 'DISTILLATION' AND NEW.event_status = 'COMPLETED' AND (
    EXISTS (
        SELECT 1 FROM source_run_video_executions AS child
        WHERE child.run_id = NEW.run_id
          AND child.state NOT IN ('COMPLETED', 'SKIPPED')
    )
    OR EXISTS (
        SELECT 1
        FROM source_run_video_executions AS child
        LEFT JOIN distillation_execution_checkpoints AS checkpoint
          ON checkpoint.execution_id = child.distillation_execution_id
        WHERE child.run_id = NEW.run_id
          AND child.state = 'COMPLETED'
          AND (
              child.distillation_execution_id IS NULL
              OR checkpoint.status != 'SUCCEEDED'
          )
    )
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run checkpoint cannot claim protected child success');
END;

CREATE TRIGGER source_run_checkpoint_block_requires_active_context
BEFORE INSERT ON source_run_checkpoint_events
WHEN NEW.event_status = 'BLOCKED' AND NOT EXISTS (
    SELECT 1 FROM source_runs
    WHERE run_id = NEW.run_id
      AND state IN ('RUNNING', 'WAITING', 'PARTIAL', 'NEEDS_ATTENTION')
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run checkpoint block requires active execution context');
END;

CREATE TRIGGER source_run_completion_requires_finalization
BEFORE UPDATE OF state ON source_runs
WHEN NEW.state = 'COMPLETED' AND NEW.state IS NOT OLD.state AND NOT EXISTS (
    SELECT 1 FROM source_run_checkpoint_events
    WHERE run_id = NEW.run_id
      AND checkpoint = 'FINALIZATION'
      AND event_status = 'COMPLETED'
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run completion requires finalization checkpoint');
END;
