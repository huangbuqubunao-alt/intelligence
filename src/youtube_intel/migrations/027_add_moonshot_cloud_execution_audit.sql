-- M12: add finite Moonshot Kimi K2.6/K3 execution consent and response audit.
-- v025 NVIDIA and v026 OpenAI history remain unchanged and append-only.
CREATE TABLE distillation_moonshot_cloud_authorizations (
    authorization_id TEXT PRIMARY KEY CHECK (length(trim(authorization_id)) BETWEEN 16 AND 160),
    execution_id TEXT NOT NULL UNIQUE REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    provider TEXT NOT NULL CHECK (provider = 'moonshot'),
    model TEXT NOT NULL CHECK (model IN ('kimi-k2.6', 'kimi-k3')),
    verified_input_hash TEXT NOT NULL CHECK (length(verified_input_hash) = 64 AND verified_input_hash NOT GLOB '*[^0-9a-f]*'),
    consent_kind TEXT NOT NULL CHECK (consent_kind IN ('USER_CONFIRMATION', 'OWNER_QUALIFICATION')),
    disclosure_version TEXT NOT NULL CHECK (disclosure_version = 'm12-cloud-intelligence-v1'),
    cost_status TEXT NOT NULL CHECK (cost_status = 'UNKNOWN'),
    authorized_at TEXT NOT NULL CHECK (length(authorized_at) >= 20)
);

CREATE TRIGGER distillation_moonshot_cloud_authorization_bound
BEFORE INSERT ON distillation_moonshot_cloud_authorizations
WHEN NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints AS checkpoint
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.selected_provider = NEW.provider
      AND checkpoint.selected_model = NEW.model
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 0
      AND checkpoint.budget_state IN ('NOT_CHECKED', 'RESERVED_NOT_DISPATCHED')
)
BEGIN
    SELECT RAISE(ABORT, 'Moonshot consent requires an unclaimed matching execution');
END;

CREATE TRIGGER distillation_moonshot_cloud_authorization_immutable_update
BEFORE UPDATE ON distillation_moonshot_cloud_authorizations
BEGIN
    SELECT RAISE(ABORT, 'Moonshot consent is immutable');
END;

CREATE TRIGGER distillation_moonshot_cloud_authorization_immutable_delete
BEFORE DELETE ON distillation_moonshot_cloud_authorizations
BEGIN
    SELECT RAISE(ABORT, 'Moonshot consent is immutable');
END;

-- Apply to every Moonshot checkpoint so unknown models cannot dispatch around
-- the finite consent table above.
CREATE TRIGGER distillation_moonshot_cloud_dispatch_requires_authorization
BEFORE UPDATE OF invocation_count ON distillation_execution_checkpoints
WHEN NEW.selected_provider = 'moonshot'
  AND NEW.invocation_count = 1
  AND OLD.invocation_count = 0
  AND NOT EXISTS (
      SELECT 1 FROM distillation_moonshot_cloud_authorizations AS consent
      WHERE consent.execution_id = NEW.execution_id
        AND consent.provider = NEW.selected_provider
        AND consent.model = NEW.selected_model
        AND consent.authorized_at <= NEW.updated_at
  )
BEGIN
    SELECT RAISE(ABORT, 'Moonshot dispatch requires prior execution authorization');
END;

CREATE TABLE distillation_moonshot_unidentified_http_responses (
    execution_id TEXT PRIMARY KEY REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    actual_provider TEXT NOT NULL CHECK (actual_provider = 'moonshot'),
    actual_model TEXT CHECK (actual_model IS NULL),
    status TEXT NOT NULL CHECK (status = 'REJECTED_OUTPUT'),
    outcome TEXT NOT NULL CHECK (outcome = 'HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN'),
    input_tokens INTEGER CHECK (input_tokens IS NULL),
    output_tokens INTEGER CHECK (output_tokens IS NULL),
    cost_microunits INTEGER CHECK (cost_microunits IS NULL),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    received_at TEXT NOT NULL CHECK (length(received_at) >= 20)
);

CREATE TRIGGER distillation_moonshot_unidentified_http_response_bound
BEFORE INSERT ON distillation_moonshot_unidentified_http_responses
WHEN NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints AS checkpoint
    JOIN distillation_moonshot_cloud_authorizations AS consent
      ON consent.execution_id = checkpoint.execution_id
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.selected_provider = 'moonshot'
      AND checkpoint.selected_model IN ('kimi-k2.6', 'kimi-k3')
      AND NEW.actual_provider = checkpoint.selected_provider
      AND consent.model = checkpoint.selected_model
      AND checkpoint.status = 'REJECTED_OUTPUT'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND checkpoint.budget_state != 'NOT_CHECKED'
)
BEGIN
    SELECT RAISE(ABORT, 'Moonshot unidentified HTTP response requires a claimed authorized execution');
END;

CREATE TRIGGER distillation_moonshot_unidentified_http_response_immutable_update
BEFORE UPDATE ON distillation_moonshot_unidentified_http_responses
BEGIN
    SELECT RAISE(ABORT, 'Moonshot HTTP response accounting is immutable');
END;

CREATE TRIGGER distillation_moonshot_unidentified_http_response_immutable_delete
BEFORE DELETE ON distillation_moonshot_unidentified_http_responses
BEGIN
    SELECT RAISE(ABORT, 'Moonshot HTTP response accounting is immutable');
END;
