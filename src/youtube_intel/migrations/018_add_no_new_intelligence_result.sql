-- M5B: durable positive-zero Intelligence result authority.
--
-- This deliberately avoids rewriting the existing m010 checkpoint/resource tables.
-- A successful "no new Intelligence" result is persisted in a dedicated immutable
-- sidecar table, while the protected checkpoint stays structurally PENDING but is
-- treated as terminal by repository reads once this sidecar exists.
--
-- The sidecar stores the exact canonical Evidence set that was checked and the
-- observed resource usage for the completed invocation. It creates no
-- Intelligence/revision/card and carries no Evidence stance.

CREATE TABLE distillation_no_new_intelligence_results (
    execution_id TEXT PRIMARY KEY
        REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL
        REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL
        REFERENCES videos(video_id) ON DELETE RESTRICT,
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
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
)
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence result requires one claimed successful invocation');
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
    SELECT 1
    FROM distillation_no_new_intelligence_results
    WHERE execution_id = OLD.execution_id
)
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence execution is terminal');
END;
