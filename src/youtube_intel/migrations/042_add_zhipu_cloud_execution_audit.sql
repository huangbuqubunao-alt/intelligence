-- Additive BigModel audit only. Historical migrations and rows are unchanged.
CREATE TABLE distillation_zhipu_cloud_authorizations (
    authorization_id TEXT PRIMARY KEY CHECK (length(trim(authorization_id)) BETWEEN 16 AND 160),
    execution_id TEXT NOT NULL UNIQUE REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    provider TEXT NOT NULL CHECK (provider = 'zhipu_bigmodel'),
    model TEXT NOT NULL CHECK (model = 'glm-4.7-flash'),
    verified_input_hash TEXT NOT NULL CHECK (length(verified_input_hash) = 64 AND verified_input_hash NOT GLOB '*[^0-9a-f]*'),
    consent_kind TEXT NOT NULL CHECK (consent_kind IN ('USER_CONFIRMATION', 'OWNER_QUALIFICATION')),
    disclosure_version TEXT NOT NULL CHECK (disclosure_version = 'm12-cloud-intelligence-v1'),
    cost_status TEXT NOT NULL CHECK (cost_status = 'UNKNOWN'),
    authorized_at TEXT NOT NULL CHECK (length(authorized_at) >= 20)
);

CREATE TRIGGER distillation_zhipu_cloud_authorization_bound
BEFORE INSERT ON distillation_zhipu_cloud_authorizations
WHEN NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints AS checkpoint
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.selected_provider = NEW.provider
      AND checkpoint.selected_model = NEW.model
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 0
      AND checkpoint.budget_state IN ('NOT_CHECKED', 'RESERVED_NOT_DISPATCHED')
      AND EXISTS (SELECT 1 FROM videos v WHERE v.video_id=checkpoint.video_id AND v.provider='YOUTUBE')
      AND EXISTS (SELECT 1 FROM source_subscriptions s WHERE s.source_id=checkpoint.source_id AND s.provider='YOUTUBE')
)
BEGIN
    SELECT RAISE(ABORT, 'BigModel consent requires an unclaimed matching execution');
END;

CREATE TRIGGER distillation_zhipu_cloud_authorization_immutable_update
BEFORE UPDATE ON distillation_zhipu_cloud_authorizations
BEGIN
    SELECT RAISE(ABORT, 'BigModel consent is immutable');
END;

CREATE TRIGGER distillation_zhipu_cloud_authorization_immutable_delete
BEFORE DELETE ON distillation_zhipu_cloud_authorizations
BEGIN
    SELECT RAISE(ABORT, 'BigModel consent is immutable');
END;

-- Apply to every BigModel checkpoint so unknown models cannot dispatch around
-- the finite consent table above.
CREATE TRIGGER distillation_zhipu_cloud_dispatch_requires_authorization
BEFORE UPDATE OF invocation_count ON distillation_execution_checkpoints
WHEN NEW.selected_provider = 'zhipu_bigmodel'
  AND NEW.invocation_count = 1
  AND OLD.invocation_count = 0
  AND NOT EXISTS (
      SELECT 1 FROM distillation_zhipu_cloud_authorizations AS consent
      WHERE consent.execution_id = NEW.execution_id
        AND consent.provider = NEW.selected_provider
        AND consent.model = NEW.selected_model
        AND consent.authorized_at <= NEW.updated_at
  )
BEGIN
    SELECT RAISE(ABORT, 'BigModel dispatch requires prior execution authorization');
END;


DROP TRIGGER distillation_no_new_http_status_bound;
CREATE TRIGGER distillation_no_new_http_status_bound
BEFORE INSERT ON distillation_no_new_intelligence_results
WHEN NEW.http_status_code IS NOT NULL
 AND (
     NEW.http_status_code NOT BETWEEN 200 AND 299
     OR NOT EXISTS (
         SELECT 1 FROM distillation_execution_checkpoints AS checkpoint
         WHERE checkpoint.execution_id = NEW.execution_id
           AND checkpoint.status = 'PENDING'
           AND checkpoint.invocation_count = 1
           AND checkpoint.selected_provider = NEW.actual_provider
           AND checkpoint.selected_model = NEW.actual_model
           AND (
               (NEW.actual_provider = 'nvidia_nim' AND NEW.actual_model = 'moonshotai/kimi-k3')
               OR (NEW.actual_provider = 'openai' AND NEW.actual_model = 'gpt-4.1')
               OR (NEW.actual_provider = 'moonshot' AND NEW.actual_model IN ('kimi-k2.6', 'kimi-k3'))
               OR (NEW.actual_provider = 'zhipu_bigmodel' AND NEW.actual_model = 'glm-4.7-flash')
           )
     )
 )
BEGIN
    SELECT RAISE(ABORT, 'no-new HTTP status requires a confirmed supported cloud response');
END;

DROP TRIGGER distillation_resource_usage_http_status_bound;
CREATE TRIGGER distillation_resource_usage_http_status_bound
BEFORE INSERT ON distillation_resource_usage
WHEN NEW.http_status_code IS NOT NULL
 AND NOT (
     (
         NEW.status = 'AMBIGUOUS'
         AND NEW.outcome = 'TRANSPORT_OUTCOME_UNKNOWN'
         AND NEW.invocation_count = 1
         AND NEW.actual_provider IS NULL
         AND NEW.actual_model IS NULL
         AND NEW.http_status_code BETWEEN 200 AND 299
         AND (
             (NEW.selected_provider = 'nvidia_nim' AND NEW.selected_model = 'moonshotai/kimi-k3')
             OR (NEW.selected_provider = 'openai' AND NEW.selected_model = 'gpt-4.1')
             OR (NEW.selected_provider = 'moonshot' AND NEW.selected_model IN ('kimi-k2.6', 'kimi-k3'))
               OR (NEW.selected_provider = 'zhipu_bigmodel' AND NEW.selected_model = 'glm-4.7-flash')
         )
     )
     OR
     (
         NEW.status IN ('SUCCEEDED', 'SUCCEEDED_NO_NEW_INTELLIGENCE', 'REJECTED_OUTPUT')
         AND NEW.actual_provider IS NOT NULL
         AND NEW.actual_model IS NOT NULL
         AND NEW.actual_provider = NEW.selected_provider
         AND NEW.actual_model = NEW.selected_model
         AND NEW.http_status_code BETWEEN 200 AND 299
         AND (
         (NEW.selected_provider = 'nvidia_nim' AND NEW.selected_model = 'moonshotai/kimi-k3')
         OR (NEW.selected_provider = 'openai' AND NEW.selected_model = 'gpt-4.1')
         OR (NEW.selected_provider = 'moonshot' AND NEW.selected_model IN ('kimi-k2.6', 'kimi-k3'))
               OR (NEW.selected_provider = 'zhipu_bigmodel' AND NEW.selected_model = 'glm-4.7-flash')
         )
     )
 )
BEGIN
    SELECT RAISE(ABORT, 'distillation HTTP status requires a confirmed supported cloud response');
END;

DROP TRIGGER distillation_cloud_failure_outcome_finite;
CREATE TRIGGER distillation_cloud_failure_outcome_finite
BEFORE INSERT ON distillation_resource_usage
WHEN NEW.status = 'REJECTED_OUTPUT'
 AND NEW.invocation_count = 1
 AND NEW.actual_provider = NEW.selected_provider
 AND NEW.actual_model = NEW.selected_model
 AND (
     (NEW.selected_provider = 'nvidia_nim' AND NEW.selected_model = 'moonshotai/kimi-k3')
     OR (NEW.selected_provider = 'openai' AND NEW.selected_model = 'gpt-4.1')
     OR (NEW.selected_provider = 'moonshot' AND NEW.selected_model IN ('kimi-k2.6', 'kimi-k3'))
               OR (NEW.selected_provider = 'zhipu_bigmodel' AND NEW.selected_model = 'glm-4.7-flash')
 )
 AND NEW.outcome NOT IN (
     'CLOUD_HTTP_RESPONSE_INVALID',
     'CLOUD_HTTP_RESPONSE_MALFORMED',
     'CLOUD_OUTPUT_TRUNCATED',
     'CLOUD_FINAL_CONTENT_MISSING',
     'STRUCTURED_OR_EVIDENCE_VALIDATION_REJECTED'
 )
BEGIN
    SELECT RAISE(ABORT, 'confirmed cloud failure outcome must use a finite code');
END;

CREATE TABLE distillation_zhipu_cloud_response_failures (
    execution_id TEXT PRIMARY KEY
        REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    actual_provider TEXT NOT NULL
        CHECK (actual_provider = 'zhipu_bigmodel'),
    actual_model TEXT CHECK (actual_model IS NULL),
    status TEXT NOT NULL CHECK (status = 'REJECTED_OUTPUT'),
    outcome TEXT NOT NULL CHECK (outcome IN (
        'CLOUD_HTTP_ERROR',
        'HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN',
        'HTTP_RESPONSE_MODEL_IDENTITY_INVALID',
        'CLOUD_HTTP_RESPONSE_MALFORMED',
        'CLOUD_RESULT_PENDING'
    )),
    http_status_code INTEGER CHECK (
        http_status_code IS NULL
        OR (typeof(http_status_code) = 'integer' AND http_status_code BETWEEN 100 AND 599)
    ),
    input_tokens INTEGER CHECK (input_tokens IS NULL),
    output_tokens INTEGER CHECK (output_tokens IS NULL),
    cost_microunits INTEGER CHECK (cost_microunits IS NULL),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    received_at TEXT NOT NULL CHECK (length(received_at) >= 20),
    CHECK (
        (outcome = 'CLOUD_HTTP_ERROR' AND http_status_code IS NOT NULL AND http_status_code BETWEEN 300 AND 599)
        OR (outcome = 'CLOUD_RESULT_PENDING' AND http_status_code IS NOT NULL AND http_status_code = 202)
        OR (
            outcome IN (
                'HTTP_RESPONSE_MODEL_IDENTITY_UNKNOWN',
                'HTTP_RESPONSE_MODEL_IDENTITY_INVALID',
                'CLOUD_HTTP_RESPONSE_MALFORMED'
            )
            AND http_status_code IS NOT NULL
            AND http_status_code BETWEEN 200 AND 299
        )
    )
);

CREATE TRIGGER distillation_zhipu_cloud_response_failure_bound
BEFORE INSERT ON distillation_zhipu_cloud_response_failures
WHEN NOT EXISTS (
    SELECT 1
    FROM distillation_execution_checkpoints AS checkpoint
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.selected_provider = NEW.actual_provider
      AND NEW.actual_provider = 'zhipu_bigmodel'
      AND checkpoint.selected_model = 'glm-4.7-flash'
      AND EXISTS (SELECT 1 FROM distillation_zhipu_cloud_authorizations AS consent
                  WHERE consent.execution_id=checkpoint.execution_id
                    AND consent.provider=checkpoint.selected_provider AND consent.model=checkpoint.selected_model
                    AND consent.authorized_at <= checkpoint.updated_at)
      AND checkpoint.status = 'REJECTED_OUTPUT'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND checkpoint.budget_state != 'NOT_CHECKED'
      AND NOT EXISTS (SELECT 1 FROM distillation_cloud_response_failures WHERE execution_id=checkpoint.execution_id)
      AND NOT EXISTS (
          SELECT 1 FROM distillation_resource_usage AS usage
          WHERE usage.execution_id = checkpoint.execution_id
      )
      AND NOT EXISTS (
          SELECT 1 FROM distillation_no_new_intelligence_results AS result
          WHERE result.execution_id = checkpoint.execution_id
      )
      AND NOT EXISTS (
          SELECT 1 FROM distillation_unidentified_http_responses AS response
          WHERE response.execution_id = checkpoint.execution_id
      )
      AND NOT EXISTS (
          SELECT 1 FROM distillation_openai_unidentified_http_responses AS response
          WHERE response.execution_id = checkpoint.execution_id
      )
      AND NOT EXISTS (
          SELECT 1 FROM distillation_moonshot_unidentified_http_responses AS response
          WHERE response.execution_id = checkpoint.execution_id
      )
)
BEGIN
    SELECT RAISE(ABORT, 'cloud response failure requires one claimed authorized execution');
END;

CREATE TRIGGER distillation_zhipu_cloud_response_failure_immutable_update
BEFORE UPDATE ON distillation_zhipu_cloud_response_failures
BEGIN
    SELECT RAISE(ABORT, 'cloud response failure accounting is immutable');
END;

CREATE TRIGGER distillation_zhipu_cloud_response_failure_immutable_delete
BEFORE DELETE ON distillation_zhipu_cloud_response_failures
BEGIN
    SELECT RAISE(ABORT, 'cloud response failure accounting is immutable');
END;


-- The new route cannot acquire LOCAL text authority; the v039 contract stays unchanged.
CREATE TRIGGER local_text_input_proofs_zhipu_cloud_denied
BEFORE INSERT ON local_text_input_proofs
WHEN EXISTS (SELECT 1 FROM distillation_execution_checkpoints c
             WHERE c.execution_id=NEW.execution_id AND c.selected_provider='zhipu_bigmodel')
BEGIN SELECT RAISE(ABORT, 'cloud provider cannot acquire local text proof'); END;

CREATE TRIGGER distillation_zhipu_failure_excludes_usage
BEFORE INSERT ON distillation_resource_usage
WHEN EXISTS (SELECT 1 FROM distillation_zhipu_cloud_response_failures WHERE execution_id=NEW.execution_id)
BEGIN SELECT RAISE(ABORT, 'BigModel failure already accounts for this execution'); END;

CREATE TRIGGER distillation_zhipu_failure_excludes_no_new
BEFORE INSERT ON distillation_no_new_intelligence_results
WHEN EXISTS (SELECT 1 FROM distillation_zhipu_cloud_response_failures WHERE execution_id=NEW.execution_id)
BEGIN SELECT RAISE(ABORT, 'BigModel failure cannot coexist with no-new result'); END;

CREATE TRIGGER distillation_zhipu_cloud_insert_requires_zero_invocation
BEFORE INSERT ON distillation_execution_checkpoints
WHEN NEW.selected_provider='zhipu_bigmodel' AND NEW.invocation_count != 0
BEGIN SELECT RAISE(ABORT, 'BigModel execution must precede its dispatch authorization'); END;
