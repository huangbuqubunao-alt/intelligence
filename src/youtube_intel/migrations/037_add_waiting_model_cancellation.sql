-- Owner-approved additive cancellation authority. Original requests and usage stay intact.
CREATE TABLE distillation_waiting_model_cancellations (
    execution_id TEXT PRIMARY KEY REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    use_case TEXT NOT NULL,
    selected_provider TEXT NOT NULL,
    selected_model TEXT NOT NULL,
    output_language TEXT NOT NULL,
    checkpoint_updated_at TEXT NOT NULL,
    budget_state TEXT NOT NULL,
    cancelled_at TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome = 'CANCELLED_BEFORE_MODEL_INVOCATION')
);

CREATE TRIGGER waiting_model_cancellation_requires_zero_invocation
BEFORE INSERT ON distillation_waiting_model_cancellations
WHEN NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints c
    JOIN distillation_resource_usage u USING(execution_id)
    WHERE c.execution_id = NEW.execution_id
      AND c.source_id = NEW.source_id AND c.video_id = NEW.video_id
      AND c.reason = NEW.reason AND c.use_case = NEW.use_case
      AND c.selected_provider = NEW.selected_provider AND c.selected_model = NEW.selected_model
      AND c.output_language = NEW.output_language AND c.updated_at = NEW.checkpoint_updated_at
      AND c.budget_state = NEW.budget_state
      AND c.selected_provider = 'ollama'
      AND c.status = 'WAITING_MODEL' AND c.invocation_count = 0
      AND c.intelligence_id IS NULL AND c.revision_id IS NULL
      AND c.budget_state IN ('RUNTIME_BUDGET_ADMITTED', 'ADMITTED')
      AND u.source_id = c.source_id AND u.video_id = c.video_id
      AND u.reason = c.reason AND u.use_case = c.use_case
      AND u.selected_provider = c.selected_provider AND u.selected_model = c.selected_model
      AND u.budget_state = c.budget_state AND u.created_at = c.updated_at
      AND u.status = 'WAITING_MODEL' AND u.invocation_count = 0
      AND u.outcome = 'MODEL_UNAVAILABLE_BEFORE_TRANSPORT'
      AND u.intelligence_id IS NULL AND u.revision_id IS NULL
      AND u.actual_provider IS NULL AND u.actual_model IS NULL
      AND u.input_tokens IS NULL AND u.output_tokens IS NULL
      AND u.cost_microunits IS NULL AND u.duration_ms IS NULL AND u.http_status_code IS NULL
)
 OR EXISTS (SELECT 1 FROM distillation_no_new_intelligence_results WHERE execution_id = NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_cloud_response_failures WHERE execution_id = NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_unidentified_http_responses WHERE execution_id = NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_openai_unidentified_http_responses WHERE execution_id = NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_moonshot_unidentified_http_responses WHERE execution_id = NEW.execution_id)
 OR EXISTS (
    SELECT 1 FROM source_run_video_executions child JOIN source_runs run USING(run_id)
    WHERE child.distillation_execution_id = NEW.execution_id AND (
        child.video_id != NEW.video_id OR run.source_id != NEW.source_id
        OR child.state != 'WAITING' OR run.state != 'NEEDS_ATTENTION'
        OR run.attention_reason != 'MODEL_UNAVAILABLE'
    )
 )
BEGIN
    SELECT RAISE(ABORT, 'cancellation requires a proven zero-invocation model wait');
END;

CREATE TRIGGER waiting_model_cancellation_immutable_update
BEFORE UPDATE ON distillation_waiting_model_cancellations
BEGIN SELECT RAISE(ABORT, 'model wait cancellation is immutable'); END;

CREATE TRIGGER waiting_model_cancellation_immutable_delete
BEFORE DELETE ON distillation_waiting_model_cancellations
BEGIN SELECT RAISE(ABORT, 'model wait cancellation is immutable'); END;

CREATE TRIGGER waiting_model_cancelled_checkpoint_terminal
BEFORE UPDATE ON distillation_execution_checkpoints
WHEN EXISTS (SELECT 1 FROM distillation_waiting_model_cancellations WHERE execution_id = OLD.execution_id)
BEGIN SELECT RAISE(ABORT, 'cancelled model wait cannot be redispatched'); END;

-- A stale preflight must never erase a concurrent local transport claim.
-- Known cloud pre-dispatch receipts retain their existing accounting contract.
CREATE TRIGGER waiting_model_local_invocation_cannot_decrease
BEFORE UPDATE OF invocation_count ON distillation_execution_checkpoints
WHEN OLD.selected_provider = 'ollama' AND NEW.invocation_count < OLD.invocation_count
BEGIN SELECT RAISE(ABORT, 'local invocation claim cannot be erased'); END;

CREATE TRIGGER waiting_model_cancelled_child_cannot_be_attached
BEFORE INSERT ON source_run_video_executions
WHEN EXISTS (SELECT 1 FROM distillation_waiting_model_cancellations WHERE execution_id = NEW.distillation_execution_id)
BEGIN SELECT RAISE(ABORT, 'cancelled model wait cannot gain new child work'); END;

CREATE TRIGGER waiting_model_cancelled_child_terminal
BEFORE UPDATE ON source_run_video_executions
WHEN EXISTS (SELECT 1 FROM distillation_waiting_model_cancellations WHERE execution_id = OLD.distillation_execution_id)
BEGIN SELECT RAISE(ABORT, 'cancelled model wait child cannot resume'); END;
