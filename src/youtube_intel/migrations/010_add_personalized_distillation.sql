-- TASK-022: bounded personalized distillation execution, immutable ledger, and card data.
-- This migration references existing Video/Source/Intelligence authority without replacing it.

CREATE TABLE distillation_execution_checkpoints (
    execution_id TEXT PRIMARY KEY CHECK (length(trim(execution_id)) > 0 AND length(execution_id) <= 512),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0 AND length(reason) <= 160),
    use_case TEXT NOT NULL CHECK (length(trim(use_case)) > 0 AND length(use_case) <= 160),
    selected_provider TEXT NOT NULL CHECK (length(trim(selected_provider)) > 0 AND length(selected_provider) <= 160),
    selected_model TEXT NOT NULL CHECK (length(trim(selected_model)) > 0 AND length(selected_model) <= 320),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'WAITING_BUDGET', 'WAITING_MODEL', 'REJECTED_INELIGIBLE', 'REJECTED_EVIDENCE', 'REJECTED_OUTPUT', 'AMBIGUOUS', 'SUCCEEDED')),
    budget_state TEXT NOT NULL CHECK (length(trim(budget_state)) > 0 AND length(budget_state) <= 160),
    invocation_count INTEGER NOT NULL CHECK (invocation_count >= 0 AND invocation_count <= 1),
    intelligence_id TEXT REFERENCES intelligences(intelligence_id) ON DELETE RESTRICT,
    revision_id TEXT REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK ((status = 'SUCCEEDED' AND intelligence_id IS NOT NULL AND revision_id IS NOT NULL AND invocation_count = 1) OR (status != 'SUCCEEDED' AND intelligence_id IS NULL AND revision_id IS NULL)),
    FOREIGN KEY (intelligence_id, revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id) ON DELETE RESTRICT
);

CREATE TRIGGER distillation_checkpoint_request_immutable
BEFORE UPDATE ON distillation_execution_checkpoints
WHEN NEW.execution_id IS NOT OLD.execution_id
  OR NEW.source_id IS NOT OLD.source_id
  OR NEW.video_id IS NOT OLD.video_id
  OR NEW.reason IS NOT OLD.reason
  OR NEW.use_case IS NOT OLD.use_case
  OR NEW.selected_provider IS NOT OLD.selected_provider
  OR NEW.selected_model IS NOT OLD.selected_model
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'distillation request identity is immutable');
END;

CREATE TRIGGER distillation_checkpoint_terminal_immutable
BEFORE UPDATE ON distillation_execution_checkpoints
WHEN OLD.status IN ('WAITING_BUDGET', 'WAITING_MODEL', 'REJECTED_INELIGIBLE', 'REJECTED_EVIDENCE', 'REJECTED_OUTPUT', 'AMBIGUOUS', 'SUCCEEDED')
BEGIN
    SELECT RAISE(ABORT, 'terminal distillation checkpoint cannot be redispatched');
END;

CREATE TABLE distillation_resource_usage (
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
    CHECK ((invocation_count = 0 AND actual_provider IS NULL AND actual_model IS NULL) OR (invocation_count = 1 AND actual_provider IS NOT NULL AND actual_model IS NOT NULL)),
    FOREIGN KEY (intelligence_id, revision_id)
        REFERENCES intelligence_revisions(intelligence_id, revision_id) ON DELETE RESTRICT
);

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

CREATE TABLE distillation_cards (
    revision_id TEXT PRIMARY KEY REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    core_conclusion TEXT NOT NULL CHECK (length(trim(core_conclusion)) > 0 AND length(core_conclusion) <= 4000),
    user_relevant_information_json TEXT NOT NULL CHECK (json_valid(user_relevant_information_json) AND json_type(user_relevant_information_json) = 'array'),
    important_new_information_json TEXT NOT NULL CHECK (json_valid(important_new_information_json) AND json_type(important_new_information_json) = 'array'),
    meaningful_details_json TEXT NOT NULL CHECK (json_valid(meaningful_details_json) AND json_type(meaningful_details_json) = 'array'),
    filtered_noise_json TEXT NOT NULL CHECK (json_valid(filtered_noise_json) AND json_type(filtered_noise_json) = 'array'),
    preference_ids_json TEXT NOT NULL CHECK (json_valid(preference_ids_json) AND json_type(preference_ids_json) = 'array'),
    source_policy_revision_id TEXT REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL
);

CREATE TRIGGER distillation_card_immutable_update
BEFORE UPDATE ON distillation_cards
BEGIN
    SELECT RAISE(ABORT, 'distillation cards are immutable');
END;

CREATE TRIGGER distillation_card_immutable_delete
BEFORE DELETE ON distillation_cards
BEGIN
    SELECT RAISE(ABORT, 'distillation cards are immutable');
END;
