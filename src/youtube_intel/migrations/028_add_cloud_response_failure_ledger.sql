-- M12: retain confirmed HTTP response status and classify provider failures
-- without storing response bodies, headers, credentials, or reasoning text.
-- Existing v025-v027 response rows and migration history remain untouched.

ALTER TABLE distillation_resource_usage
ADD COLUMN http_status_code INTEGER
CHECK (
    http_status_code IS NULL
    OR (typeof(http_status_code) = 'integer' AND http_status_code BETWEEN 100 AND 599)
);

ALTER TABLE distillation_no_new_intelligence_results
ADD COLUMN http_status_code INTEGER
CHECK (
    http_status_code IS NULL
    OR (typeof(http_status_code) = 'integer' AND http_status_code BETWEEN 100 AND 599)
);

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
           )
     )
 )
BEGIN
    SELECT RAISE(ABORT, 'no-new HTTP status requires a confirmed supported cloud response');
END;

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
         )
     )
 )
BEGIN
    SELECT RAISE(ABORT, 'distillation HTTP status requires a confirmed supported cloud response');
END;

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

CREATE TRIGGER distillation_resource_usage_http_status_immutable
BEFORE UPDATE OF http_status_code ON distillation_resource_usage
WHEN OLD.http_status_code IS NOT NEW.http_status_code
BEGIN
    SELECT RAISE(ABORT, 'distillation HTTP status accounting is immutable');
END;

CREATE TRIGGER distillation_resource_usage_ambiguous_outcome_finite
BEFORE INSERT ON distillation_resource_usage
WHEN NEW.status = 'AMBIGUOUS'
 AND NOT (
     (NEW.outcome = 'TRANSPORT_OUTCOME_UNKNOWN' AND NEW.invocation_count = 1)
     OR (NEW.outcome = 'RESERVED_DISPATCH_OUTCOME_UNKNOWN' AND NEW.invocation_count = 1)
     OR (NEW.outcome = 'DISPATCH_CLAIM_STATE_UNKNOWN' AND NEW.invocation_count IN (0, 1))
     OR (NEW.outcome = 'PRIOR_ATTEMPT_STATE_UNKNOWN' AND NEW.invocation_count IN (0, 1))
 )
BEGIN
    SELECT RAISE(ABORT, 'ambiguous distillation outcome must use a finite code');
END;

CREATE TRIGGER distillation_resource_usage_ambiguous_outcome_immutable
BEFORE UPDATE ON distillation_resource_usage
WHEN NEW.status = 'AMBIGUOUS'
 AND NOT (
     (NEW.outcome = 'TRANSPORT_OUTCOME_UNKNOWN' AND NEW.invocation_count = 1)
     OR (NEW.outcome = 'RESERVED_DISPATCH_OUTCOME_UNKNOWN' AND NEW.invocation_count = 1)
     OR (NEW.outcome = 'DISPATCH_CLAIM_STATE_UNKNOWN' AND NEW.invocation_count IN (0, 1))
     OR (NEW.outcome = 'PRIOR_ATTEMPT_STATE_UNKNOWN' AND NEW.invocation_count IN (0, 1))
 )
BEGIN
    SELECT RAISE(ABORT, 'ambiguous distillation outcome must use a finite code');
END;

CREATE TABLE distillation_cloud_response_failures (
    execution_id TEXT PRIMARY KEY
        REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    actual_provider TEXT NOT NULL
        CHECK (actual_provider IN ('nvidia_nim', 'openai', 'moonshot')),
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

CREATE TRIGGER distillation_cloud_response_failure_bound
BEFORE INSERT ON distillation_cloud_response_failures
WHEN NOT EXISTS (
    SELECT 1
    FROM distillation_execution_checkpoints AS checkpoint
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.selected_provider = NEW.actual_provider
      AND (
          (NEW.actual_provider = 'nvidia_nim'
           AND checkpoint.selected_model = 'moonshotai/kimi-k3'
           AND EXISTS (
               SELECT 1 FROM distillation_cloud_authorizations AS consent
               WHERE consent.execution_id = checkpoint.execution_id
                 AND consent.authorized_at <= checkpoint.updated_at
           ))
          OR (NEW.actual_provider = 'openai'
              AND checkpoint.selected_model = 'gpt-4.1'
              AND EXISTS (
                  SELECT 1 FROM distillation_openai_cloud_authorizations AS consent
                  WHERE consent.execution_id = checkpoint.execution_id
                    AND consent.authorized_at <= checkpoint.updated_at
              ))
          OR (NEW.actual_provider = 'moonshot'
              AND checkpoint.selected_model IN ('kimi-k2.6', 'kimi-k3')
              AND EXISTS (
                  SELECT 1 FROM distillation_moonshot_cloud_authorizations AS consent
                  WHERE consent.execution_id = checkpoint.execution_id
                    AND consent.authorized_at <= checkpoint.updated_at
              ))
      )
      AND checkpoint.status = 'REJECTED_OUTPUT'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND checkpoint.budget_state != 'NOT_CHECKED'
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

CREATE TRIGGER distillation_cloud_response_failure_immutable_update
BEFORE UPDATE ON distillation_cloud_response_failures
BEGIN
    SELECT RAISE(ABORT, 'cloud response failure accounting is immutable');
END;

CREATE TRIGGER distillation_cloud_response_failure_immutable_delete
BEFORE DELETE ON distillation_cloud_response_failures
BEGIN
    SELECT RAISE(ABORT, 'cloud response failure accounting is immutable');
END;
