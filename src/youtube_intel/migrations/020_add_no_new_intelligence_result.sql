-- M5B: durable positive-zero Intelligence result authority.
--
-- The m010 checkpoint remains PENDING because its SUCCEEDED value continues to
-- mean that an Intelligence revision was admitted.  This immutable sidecar is
-- the sole authority for the distinct successful zero-admission terminal.

CREATE TABLE distillation_no_new_intelligence_results (
    execution_id TEXT PRIMARY KEY
        REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL
        REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL
        REFERENCES videos(video_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL
        CHECK (length(trim(reason)) > 0 AND length(reason) <= 160),
    use_case TEXT NOT NULL
        CHECK (length(trim(use_case)) > 0 AND length(use_case) <= 160),
    evidence_ids_json TEXT NOT NULL
        CHECK (json_valid(evidence_ids_json) AND json_type(evidence_ids_json) = 'array'),
    evidence_set_hash TEXT NOT NULL
        CHECK (length(evidence_set_hash) = 64 AND evidence_set_hash NOT GLOB '*[^0-9a-f]*'),
    actual_provider TEXT NOT NULL
        CHECK (length(trim(actual_provider)) > 0 AND length(actual_provider) <= 160),
    actual_model TEXT NOT NULL
        CHECK (length(trim(actual_model)) > 0 AND length(actual_model) <= 320),
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    cost_microunits INTEGER CHECK (cost_microunits IS NULL OR cost_microunits >= 0),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    budget_state TEXT NOT NULL
        CHECK (length(trim(budget_state)) > 0 AND length(budget_state) <= 160),
    outcome TEXT NOT NULL CHECK (outcome = 'NO_NEW_INTELLIGENCE'),
    created_at TEXT NOT NULL,
    CHECK ((input_tokens IS NULL AND output_tokens IS NULL)
        OR (input_tokens IS NOT NULL AND output_tokens IS NOT NULL))
);

CREATE TRIGGER distillation_no_new_result_requires_claimed_checkpoint
BEFORE INSERT ON distillation_no_new_intelligence_results
WHEN NOT EXISTS (
    SELECT 1
    FROM distillation_execution_checkpoints AS checkpoint
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.source_id = NEW.source_id
      AND checkpoint.video_id = NEW.video_id
      AND checkpoint.reason = NEW.reason
      AND checkpoint.use_case = NEW.use_case
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND checkpoint.selected_provider = NEW.actual_provider
      AND checkpoint.selected_model = NEW.actual_model
)
 OR json_array_length(NEW.evidence_ids_json) = 0
 OR EXISTS (
    SELECT 1 FROM json_each(NEW.evidence_ids_json) AS cited
    WHERE cited.type != 'text'
 )
 OR (SELECT COUNT(*) FROM json_each(NEW.evidence_ids_json)) != (
    SELECT COUNT(DISTINCT cited.value)
    FROM json_each(NEW.evidence_ids_json) AS cited
 )
 OR EXISTS (
    SELECT 1
    FROM json_each(NEW.evidence_ids_json) AS cited
    WHERE NOT EXISTS (
        SELECT 1
        FROM evidence
        JOIN artifacts ON artifacts.artifact_id = evidence.artifact_id
        WHERE evidence.evidence_id = cited.value
          AND evidence.video_id = NEW.video_id
          AND evidence.availability = 'AVAILABLE'
          AND artifacts.video_id = NEW.video_id
          AND artifacts.deleted_at IS NULL
          AND artifacts.kind = 'transcript_canonical'
    )
 )
 OR (SELECT COUNT(*) FROM json_each(NEW.evidence_ids_json)) != (
    SELECT COUNT(*)
    FROM evidence
    JOIN artifacts ON artifacts.artifact_id = evidence.artifact_id
    WHERE evidence.video_id = NEW.video_id
      AND evidence.availability = 'AVAILABLE'
      AND artifacts.video_id = NEW.video_id
      AND artifacts.deleted_at IS NULL
      AND artifacts.kind = 'transcript_canonical'
 )
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence result requires one invocation and the exact canonical Evidence set');
END;

CREATE TRIGGER distillation_no_new_result_immutable_update
BEFORE UPDATE ON distillation_no_new_intelligence_results
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence result is immutable');
END;

CREATE TRIGGER distillation_no_new_result_immutable_delete
BEFORE DELETE ON distillation_no_new_intelligence_results
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence result is immutable');
END;

CREATE TRIGGER distillation_no_new_checkpoint_terminal
BEFORE UPDATE ON distillation_execution_checkpoints
WHEN EXISTS (
    SELECT 1 FROM distillation_no_new_intelligence_results
    WHERE execution_id = OLD.execution_id
)
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence execution is terminal');
END;

-- Source Run completion accepts the existing admitted success or this exact
-- zero-admission authority.  The historical checkpoint label remains intact.
DROP TRIGGER source_run_video_execution_context_must_match;
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
 ) AND NOT EXISTS (
    SELECT 1
    FROM distillation_no_new_intelligence_results AS result
    JOIN distillation_execution_checkpoints AS checkpoint
      ON checkpoint.execution_id = result.execution_id
    WHERE result.execution_id = NEW.distillation_execution_id
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND result.source_id = checkpoint.source_id
      AND result.video_id = checkpoint.video_id
      AND result.reason = checkpoint.reason
      AND result.use_case = checkpoint.use_case
      AND result.actual_provider = checkpoint.selected_provider
      AND result.actual_model = checkpoint.selected_model
      AND result.outcome = 'NO_NEW_INTELLIGENCE'
 ))
 OR (NEW.state = 'AMBIGUOUS' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'AMBIGUOUS'
))
BEGIN
    SELECT RAISE(ABORT, 'Source Run child must cite matching legal execution state');
END;

DROP TRIGGER source_run_video_execution_state_must_match_protected_execution;
CREATE TRIGGER source_run_video_execution_state_must_match_protected_execution
BEFORE UPDATE OF state ON source_run_video_executions
WHEN (NEW.state = 'COMPLETED' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'SUCCEEDED'
 ) AND NOT EXISTS (
    SELECT 1
    FROM distillation_no_new_intelligence_results AS result
    JOIN distillation_execution_checkpoints AS checkpoint
      ON checkpoint.execution_id = result.execution_id
    WHERE result.execution_id = NEW.distillation_execution_id
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND result.source_id = checkpoint.source_id
      AND result.video_id = checkpoint.video_id
      AND result.reason = checkpoint.reason
      AND result.use_case = checkpoint.use_case
      AND result.actual_provider = checkpoint.selected_provider
      AND result.actual_model = checkpoint.selected_model
      AND result.outcome = 'NO_NEW_INTELLIGENCE'
 )) OR (NEW.state = 'AMBIGUOUS' AND NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints
    WHERE execution_id = NEW.distillation_execution_id AND status = 'AMBIGUOUS'
))
BEGIN
    SELECT RAISE(ABORT, 'Source Run child must cite matching legal execution state');
END;

DROP TRIGGER source_run_distillation_checkpoint_requires_legal_children;
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
              OR (
                  checkpoint.status != 'SUCCEEDED'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM distillation_no_new_intelligence_results AS result
                      WHERE result.execution_id = child.distillation_execution_id
                        AND checkpoint.status = 'PENDING'
                        AND checkpoint.invocation_count = 1
                        AND checkpoint.intelligence_id IS NULL
                        AND checkpoint.revision_id IS NULL
                        AND result.source_id = checkpoint.source_id
                        AND result.video_id = checkpoint.video_id
                        AND result.reason = checkpoint.reason
                        AND result.use_case = checkpoint.use_case
                        AND result.actual_provider = checkpoint.selected_provider
                        AND result.actual_model = checkpoint.selected_model
                        AND result.outcome = 'NO_NEW_INTELLIGENCE'
                  )
              )
          )
    )
)
BEGIN
    SELECT RAISE(ABORT, 'Source Run checkpoint cannot claim protected child success');
END;
