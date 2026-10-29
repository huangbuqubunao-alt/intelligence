-- Additive proof/consent/receipt/cancel authority; no transport or eligibility grant.
CREATE TABLE system_synthesis_input_proofs (
 execution_id TEXT PRIMARY KEY REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
 profile_id TEXT NOT NULL CHECK(length(profile_id) BETWEEN 1 AND 160),
 proof_json TEXT NOT NULL CHECK(json_valid(proof_json) AND json_type(proof_json)='object' AND length(CAST(proof_json AS BLOB))<=524288),
 proof_sha256 TEXT NOT NULL CHECK(length(proof_sha256)=64 AND proof_sha256 NOT GLOB '*[^0-9a-f]*'),
 created_at TEXT NOT NULL
);
CREATE TABLE system_synthesis_cloud_authorizations (
 authorization_id TEXT PRIMARY KEY CHECK(length(authorization_id) BETWEEN 16 AND 160),
 execution_id TEXT NOT NULL UNIQUE REFERENCES system_synthesis_input_proofs(execution_id) ON DELETE RESTRICT,
 provider TEXT NOT NULL CHECK(provider='moonshot'), model TEXT NOT NULL,
 verified_input_hash TEXT NOT NULL CHECK(length(verified_input_hash)=64 AND verified_input_hash NOT GLOB '*[^0-9a-f]*'),
 consent_kind TEXT NOT NULL CHECK(consent_kind IN ('USER_CONFIRMATION','OWNER_QUALIFICATION')),
 disclosure_version TEXT NOT NULL CHECK(disclosure_version='system-synthesis-disclosure-v1'),
 cost_status TEXT NOT NULL CHECK(cost_status='UNKNOWN'), authorized_at TEXT NOT NULL,
 budget_scope TEXT NOT NULL CHECK(length(trim(budget_scope)) BETWEEN 1 AND 160),
 budget_limit_microunits INTEGER NOT NULL CHECK(typeof(budget_limit_microunits)='integer' AND budget_limit_microunits>0),
 max_calls INTEGER NOT NULL CHECK(typeof(max_calls)='integer' AND max_calls>0),
 reserve_microunits INTEGER NOT NULL CHECK(typeof(reserve_microunits)='integer' AND reserve_microunits>0),
 prior_reserved_microunits INTEGER NOT NULL CHECK(typeof(prior_reserved_microunits)='integer' AND prior_reserved_microunits>=0),
 prior_calls INTEGER NOT NULL CHECK(typeof(prior_calls)='integer' AND prior_calls>=0),
 price_sha256 TEXT NOT NULL CHECK(length(price_sha256)=64 AND price_sha256 NOT GLOB '*[^0-9a-f]*')
);
CREATE TABLE system_synthesis_result_receipts (
 execution_id TEXT PRIMARY KEY REFERENCES system_synthesis_cloud_authorizations(execution_id) ON DELETE RESTRICT,
 proof_sha256 TEXT NOT NULL CHECK(length(proof_sha256)=64 AND proof_sha256 NOT GLOB '*[^0-9a-f]*'),
 raw_text TEXT CHECK(raw_text IS NULL OR (typeof(raw_text)='text' AND length(CAST(raw_text AS BLOB))<=2097152)),
 raw_sha256 TEXT CHECK(raw_sha256 IS NULL OR (length(raw_sha256)=64 AND raw_sha256 NOT GLOB '*[^0-9a-f]*')),
 observation_json TEXT NOT NULL CHECK(json_valid(observation_json) AND json_type(observation_json)='object' AND length(observation_json)<=8192),
 revision_id TEXT UNIQUE REFERENCES intelligence_revisions(revision_id) ON DELETE RESTRICT,
 created_at TEXT NOT NULL,
 CHECK(raw_text IS NULL OR raw_sha256 IS NOT NULL)
);
CREATE TABLE system_synthesis_wait_cancellations (
 execution_id TEXT PRIMARY KEY REFERENCES system_synthesis_input_proofs(execution_id) ON DELETE RESTRICT,
 source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
 video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
 reason TEXT NOT NULL, use_case TEXT NOT NULL, selected_provider TEXT NOT NULL, selected_model TEXT NOT NULL,
 output_language TEXT NOT NULL, budget_state TEXT NOT NULL, checkpoint_updated_at TEXT NOT NULL,
 cancelled_at TEXT NOT NULL, outcome TEXT NOT NULL CHECK(outcome='CANCELLED_BEFORE_CLOUD_MODEL_INVOCATION')
);
CREATE TRIGGER system_synthesis_input_proofs_immutable_update BEFORE UPDATE ON system_synthesis_input_proofs BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_input_proofs_immutable_delete BEFORE DELETE ON system_synthesis_input_proofs BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_cloud_authorizations_immutable_update BEFORE UPDATE ON system_synthesis_cloud_authorizations BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_cloud_authorizations_immutable_delete BEFORE DELETE ON system_synthesis_cloud_authorizations BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_result_receipts_immutable_update BEFORE UPDATE ON system_synthesis_result_receipts BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_result_receipts_immutable_delete BEFORE DELETE ON system_synthesis_result_receipts BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_wait_cancellations_immutable_update BEFORE UPDATE ON system_synthesis_wait_cancellations BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;
CREATE TRIGGER system_synthesis_wait_cancellations_immutable_delete BEFORE DELETE ON system_synthesis_wait_cancellations BEGIN SELECT RAISE(ABORT, 'system synthesis proof is immutable'); END;

CREATE TRIGGER synthesis_checkpoint_requires_proof BEFORE INSERT ON distillation_execution_checkpoints
WHEN (lower(NEW.execution_id) LIKE 'distillation:system-synthesis-%' OR (NEW.selected_provider='moonshot' AND NEW.selected_model='kimi-k3.1-pro'))
 AND NOT EXISTS(SELECT 1 FROM system_synthesis_input_proofs p WHERE p.execution_id=NEW.execution_id
  AND p.profile_id=json_extract(p.proof_json,'$.transport.id') AND json_extract(p.proof_json,'$.transport.provider')=NEW.selected_provider
  AND json_extract(p.proof_json,'$.transport.model')=NEW.selected_model
  AND json_extract(p.proof_json,'$.command.source_id')=NEW.source_id AND json_extract(p.proof_json,'$.command.video_id')=NEW.video_id
  AND json_extract(p.proof_json,'$.command.reason')=NEW.reason AND NEW.use_case='PERSONALIZED_INTELLIGENCE'
  AND json_extract(p.proof_json,'$.command.output_language')=NEW.output_language
  AND NEW.status='PENDING' AND NEW.invocation_count=0 AND NEW.budget_state='RESERVED_NOT_DISPATCHED')
BEGIN SELECT RAISE(ABORT,'system synthesis checkpoint requires full matching proof'); END;
CREATE TRIGGER synthesis_consent_bound BEFORE INSERT ON system_synthesis_cloud_authorizations
WHEN NOT EXISTS(SELECT 1 FROM system_synthesis_input_proofs p JOIN distillation_execution_checkpoints c USING(execution_id)
 WHERE p.execution_id=NEW.execution_id AND c.status='PENDING' AND c.invocation_count=0 AND c.budget_state='RESERVED_NOT_DISPATCHED'
 AND NEW.provider=c.selected_provider AND NEW.model=c.selected_model AND NEW.verified_input_hash=p.proof_sha256
 AND NEW.reserve_microunits=json_extract(p.proof_json,'$.reserve_microunits')
 AND NEW.price_sha256=json_extract(p.proof_json,'$.transport_sha256') AND NEW.authorized_at>=c.created_at)
 OR NEW.reserve_microunits+NEW.prior_reserved_microunits+COALESCE((SELECT SUM(reserve_microunits) FROM system_synthesis_cloud_authorizations WHERE budget_scope=NEW.budget_scope),0)>NEW.budget_limit_microunits
 OR NEW.prior_calls+(SELECT COUNT(*) FROM system_synthesis_cloud_authorizations WHERE budget_scope=NEW.budget_scope)+1>NEW.max_calls
 OR EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a WHERE a.budget_scope=NEW.budget_scope AND
  (a.budget_limit_microunits!=NEW.budget_limit_microunits OR a.max_calls!=NEW.max_calls OR a.prior_calls!=NEW.prior_calls OR a.prior_reserved_microunits!=NEW.prior_reserved_microunits))
BEGIN SELECT RAISE(ABORT,'system synthesis affirmative consent or fee reserve differs'); END;
CREATE TRIGGER synthesis_claim_bound BEFORE UPDATE ON distillation_execution_checkpoints
WHEN EXISTS(SELECT 1 FROM system_synthesis_input_proofs WHERE execution_id=OLD.execution_id)
 AND (NEW.invocation_count<OLD.invocation_count OR
  (NEW.invocation_count=1 AND NOT EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id)
    WHERE a.execution_id=NEW.execution_id AND a.verified_input_hash=p.proof_sha256 AND a.authorized_at<=NEW.updated_at))
  OR EXISTS(SELECT 1 FROM system_synthesis_result_receipts WHERE execution_id=OLD.execution_id)
  OR EXISTS(SELECT 1 FROM system_synthesis_wait_cancellations WHERE execution_id=OLD.execution_id))
BEGIN SELECT RAISE(ABORT,'system synthesis cannot dispatch or revive without exact consent'); END;
CREATE TRIGGER synthesis_receipt_bound BEFORE INSERT ON system_synthesis_result_receipts
WHEN NOT EXISTS(SELECT 1 FROM system_synthesis_input_proofs p JOIN distillation_execution_checkpoints c USING(execution_id)
 JOIN system_synthesis_cloud_authorizations a USING(execution_id)
 WHERE p.execution_id=NEW.execution_id AND p.proof_sha256=NEW.proof_sha256 AND a.verified_input_hash=p.proof_sha256
 AND c.invocation_count=1 AND NEW.created_at=c.updated_at AND NEW.revision_id IS c.revision_id
 AND (c.status IN ('SUCCEEDED','REJECTED_OUTPUT','AMBIGUOUS') OR EXISTS(SELECT 1 FROM distillation_no_new_intelligence_results n WHERE n.execution_id=c.execution_id))
 AND NOT EXISTS(SELECT 1 FROM system_synthesis_wait_cancellations WHERE execution_id=c.execution_id))
BEGIN SELECT RAISE(ABORT,'system synthesis receipt requires one terminal authorized attempt'); END;
CREATE TRIGGER synthesis_cancel_bound BEFORE INSERT ON system_synthesis_wait_cancellations
WHEN NOT EXISTS(SELECT 1 FROM system_synthesis_input_proofs p JOIN distillation_execution_checkpoints c USING(execution_id)
 JOIN distillation_resource_usage u USING(execution_id)
 WHERE c.execution_id=NEW.execution_id AND c.status='WAITING_MODEL' AND c.invocation_count=0 AND u.status='WAITING_MODEL' AND u.invocation_count=0
 AND c.source_id=NEW.source_id AND c.video_id=NEW.video_id AND c.reason=NEW.reason AND c.use_case=NEW.use_case
 AND c.selected_provider=NEW.selected_provider AND c.selected_model=NEW.selected_model AND c.output_language=NEW.output_language
 AND c.budget_state=NEW.budget_state AND c.updated_at=NEW.checkpoint_updated_at AND NEW.cancelled_at>=c.updated_at
 AND c.intelligence_id IS NULL AND c.revision_id IS NULL AND u.actual_provider IS NULL AND u.actual_model IS NULL
 AND u.input_tokens IS NULL AND u.output_tokens IS NULL AND u.cost_microunits IS NULL AND u.duration_ms IS NULL AND u.http_status_code IS NULL
 AND u.outcome='MODEL_UNAVAILABLE_BEFORE_TRANSPORT' AND u.created_at=c.updated_at)
 OR EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations WHERE execution_id=NEW.execution_id)
 OR EXISTS(SELECT 1 FROM system_synthesis_result_receipts WHERE execution_id=NEW.execution_id)
 OR EXISTS(SELECT 1 FROM distillation_no_new_intelligence_results WHERE execution_id=NEW.execution_id)
 OR EXISTS(SELECT 1 FROM distillation_cloud_response_failures WHERE execution_id=NEW.execution_id)
BEGIN SELECT RAISE(ABORT,'system synthesis cancel requires proven zero invocation'); END;
CREATE TRIGGER synthesis_cancelled_child_insert BEFORE INSERT ON source_run_video_executions
WHEN EXISTS(SELECT 1 FROM system_synthesis_wait_cancellations WHERE execution_id=NEW.distillation_execution_id)
BEGIN SELECT RAISE(ABORT,'cancelled system synthesis cannot gain child work'); END;
CREATE TRIGGER synthesis_cancelled_child_update BEFORE UPDATE ON source_run_video_executions
WHEN EXISTS(SELECT 1 FROM system_synthesis_wait_cancellations WHERE execution_id=OLD.distillation_execution_id)
BEGIN SELECT RAISE(ABORT,'cancelled system synthesis child cannot resume'); END;

DROP TRIGGER distillation_moonshot_cloud_dispatch_requires_authorization;
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
  AND NOT EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id) WHERE a.execution_id=NEW.execution_id AND a.provider=NEW.selected_provider AND a.model=NEW.selected_model AND a.verified_input_hash=p.proof_sha256 AND a.authorized_at<=NEW.updated_at)
BEGIN
    SELECT RAISE(ABORT, 'Moonshot dispatch requires prior execution authorization');
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
               OR (NEW.actual_provider='moonshot' AND NEW.actual_model='kimi-k3.1-pro' AND EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id) WHERE a.execution_id=NEW.execution_id AND a.verified_input_hash=p.proof_sha256))
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
               OR (NEW.selected_provider='moonshot' AND NEW.selected_model='kimi-k3.1-pro' AND EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id) WHERE a.execution_id=NEW.execution_id AND a.verified_input_hash=p.proof_sha256))
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
               OR (NEW.selected_provider='moonshot' AND NEW.selected_model='kimi-k3.1-pro' AND EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id) WHERE a.execution_id=NEW.execution_id AND a.verified_input_hash=p.proof_sha256))
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
               OR (NEW.selected_provider='moonshot' AND NEW.selected_model='kimi-k3.1-pro' AND EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id) WHERE a.execution_id=NEW.execution_id AND a.verified_input_hash=p.proof_sha256))
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

DROP TRIGGER distillation_cloud_response_failure_bound;
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
          OR (NEW.actual_provider='moonshot' AND checkpoint.selected_model='kimi-k3.1-pro'
              AND EXISTS(SELECT 1 FROM system_synthesis_cloud_authorizations a JOIN system_synthesis_input_proofs p USING(execution_id)
                  WHERE a.execution_id=checkpoint.execution_id AND a.verified_input_hash=p.proof_sha256 AND a.model=checkpoint.selected_model))
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
