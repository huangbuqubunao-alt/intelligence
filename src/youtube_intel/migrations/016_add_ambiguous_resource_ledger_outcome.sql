-- TASK-022C: preserve the immutable m010 ledger while allowing an invoked
-- AMBIGUOUS outcome to truthfully retain an unknown actual provider/model.
CREATE TABLE distillation_resource_usage_v016 (
    execution_id TEXT PRIMARY KEY REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0 AND length(reason) <= 160),
    use_case TEXT NOT NULL CHECK (length(trim(use_case)) > 0 AND length(use_case) <= 160),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    intelligence_id TEXT REFERENCES intelligences(intelligence_id) ON DELETE RESTRICT,
    revision_id TEXT REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    selected_provider TEXT NOT NULL CHECK (length(trim(selected_provider)) > 0 AND length(selected_provider) <= 160),
    selected_model TEXT NOT NULL CHECK (length(trim(selected_model)) > 0 AND length(selected_model) <= 320),
    actual_provider TEXT CHECK (actual_provider IS NULL OR (length(trim(actual_provider)) > 0 AND length(actual_provider) <= 160)),
    actual_model TEXT CHECK (actual_model IS NULL OR (length(trim(actual_model)) > 0 AND length(actual_model) <= 320)),
    status TEXT NOT NULL CHECK (status IN ('WAITING_BUDGET', 'WAITING_MODEL', 'REJECTED_INELIGIBLE', 'REJECTED_EVIDENCE', 'REJECTED_OUTPUT', 'AMBIGUOUS', 'SUCCEEDED')),
    invocation_count INTEGER NOT NULL CHECK (invocation_count >= 0 AND invocation_count <= 1),
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    cost_microunits INTEGER CHECK (cost_microunits IS NULL OR cost_microunits >= 0),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    budget_state TEXT NOT NULL CHECK (length(trim(budget_state)) > 0 AND length(budget_state) <= 160),
    outcome TEXT NOT NULL CHECK (length(trim(outcome)) > 0 AND length(outcome) <= 160),
    created_at TEXT NOT NULL,
    CHECK ((input_tokens IS NULL AND output_tokens IS NULL) OR (input_tokens IS NOT NULL AND output_tokens IS NOT NULL)),
    CHECK (
        (invocation_count = 0 AND actual_provider IS NULL AND actual_model IS NULL)
        OR
        (invocation_count = 1 AND actual_provider IS NOT NULL AND actual_model IS NOT NULL)
        OR
        (invocation_count = 1 AND status = 'AMBIGUOUS' AND actual_provider IS NULL AND actual_model IS NULL)
    ),
    FOREIGN KEY (intelligence_id, revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id) ON DELETE RESTRICT
);

INSERT INTO distillation_resource_usage_v016 (
    execution_id, reason, use_case, source_id, video_id, intelligence_id,
    revision_id, selected_provider, selected_model, actual_provider,
    actual_model, status, invocation_count, input_tokens, output_tokens,
    cost_microunits, duration_ms, budget_state, outcome, created_at
)
SELECT
    execution_id, reason, use_case, source_id, video_id, intelligence_id,
    revision_id, selected_provider, selected_model, actual_provider,
    actual_model, status, invocation_count, input_tokens, output_tokens,
    cost_microunits, duration_ms, budget_state, outcome, created_at
FROM distillation_resource_usage;

DROP TABLE distillation_resource_usage;
ALTER TABLE distillation_resource_usage_v016 RENAME TO distillation_resource_usage;

CREATE TRIGGER distillation_resource_usage_immutable_update
BEFORE UPDATE ON distillation_resource_usage
BEGIN
    SELECT RAISE(ABORT, 'distillation resource usage is immutable');
END;

CREATE TRIGGER distillation_resource_usage_immutable_delete
BEFORE DELETE ON distillation_resource_usage
BEGIN
    SELECT RAISE(ABORT, 'distillation resource usage is immutable');
END;
