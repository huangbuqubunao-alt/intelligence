-- Append-only BigModel zero-call cancellation; all earlier authority stays intact.
CREATE TABLE distillation_cloud_waiting_model_cancellations (
    execution_id TEXT NOT NULL PRIMARY KEY CHECK (typeof(execution_id)='text' AND length(execution_id)=92 AND substr(execution_id,1,28)='distillation:reservation:v3:' AND substr(execution_id,29) NOT GLOB '*[^0-9a-f]*') REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL CHECK (typeof(source_id)='text' AND length(source_id) BETWEEN 1 AND 512 AND source_id=trim(source_id)) REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL CHECK (typeof(video_id)='text' AND length(video_id) BETWEEN 1 AND 512 AND video_id=trim(video_id)) REFERENCES videos(video_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK (typeof(reason)='text' AND length(trim(reason)) BETWEEN 1 AND 512),
    use_case TEXT NOT NULL CHECK (use_case='PERSONALIZED_INTELLIGENCE'),
    selected_provider TEXT NOT NULL CHECK (selected_provider='zhipu_bigmodel'),
    selected_model TEXT NOT NULL CHECK (selected_model='glm-4.7-flash'),
    output_language TEXT NOT NULL CHECK (output_language IN ('en','zh-CN')),
    budget_state TEXT NOT NULL CHECK (budget_state IN ('ADMITTED','PUBLIC_DIAGNOSTIC_ANTICIPATED_FREE_MAX_ONE')),
    checkpoint_updated_at TEXT NOT NULL CHECK (typeof(checkpoint_updated_at)='text' AND (length(checkpoint_updated_at)=20 AND checkpoint_updated_at GLOB '????-??-??T??:??:??Z' OR length(checkpoint_updated_at)=27 AND checkpoint_updated_at GLOB '????-??-??T??:??:??.??????Z' AND substr(checkpoint_updated_at,21,6) NOT GLOB '*[^0-9]*') AND substr(checkpoint_updated_at,1,4) BETWEEN '0001' AND '9999' AND strftime('%Y-%m-%dT%H:%M:%S',substr(checkpoint_updated_at,1,19)||'Z','+0 seconds') IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%S',substr(checkpoint_updated_at,1,19)||'Z','+0 seconds')=substr(checkpoint_updated_at,1,19)),
    cancelled_at TEXT NOT NULL CHECK (typeof(cancelled_at)='text' AND (length(cancelled_at)=20 AND cancelled_at GLOB '????-??-??T??:??:??Z' OR length(cancelled_at)=27 AND cancelled_at GLOB '????-??-??T??:??:??.??????Z' AND substr(cancelled_at,21,6) NOT GLOB '*[^0-9]*') AND substr(cancelled_at,1,4) BETWEEN '0001' AND '9999' AND strftime('%Y-%m-%dT%H:%M:%S',substr(cancelled_at,1,19)||'Z','+0 seconds') IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%S',substr(cancelled_at,1,19)||'Z','+0 seconds')=substr(cancelled_at,1,19)),
    outcome TEXT NOT NULL CHECK (outcome='CANCELLED_BEFORE_CLOUD_MODEL_INVOCATION')
);

CREATE TRIGGER cloud_wait_cancellation_requires_proven_zero
BEFORE INSERT ON distillation_cloud_waiting_model_cancellations
WHEN NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints c
    JOIN distillation_resource_usage u USING(execution_id)
    JOIN distillation_zhipu_cloud_authorizations a USING(execution_id)
    JOIN videos v ON v.video_id=c.video_id
    JOIN source_subscriptions s ON s.source_id=c.source_id
    JOIN source_video_links link ON link.source_id=c.source_id AND link.video_id=c.video_id
    WHERE c.execution_id=NEW.execution_id AND c.source_id=NEW.source_id AND c.video_id=NEW.video_id
      AND c.reason=NEW.reason AND c.use_case=NEW.use_case
      AND c.selected_provider=NEW.selected_provider AND c.selected_model=NEW.selected_model
      AND c.output_language=NEW.output_language AND c.budget_state=NEW.budget_state
      AND c.updated_at=NEW.checkpoint_updated_at AND c.status='WAITING_MODEL'
      AND typeof(c.invocation_count)='integer' AND c.invocation_count=0
      AND c.intelligence_id IS NULL AND c.revision_id IS NULL
      AND v.provider='YOUTUBE' AND v.availability='public' AND s.provider='YOUTUBE'
      AND u.source_id=c.source_id AND u.video_id=c.video_id AND u.reason=c.reason AND u.use_case=c.use_case
      AND u.selected_provider=c.selected_provider AND u.selected_model=c.selected_model
      AND u.budget_state=c.budget_state AND u.created_at=c.updated_at
      AND u.status='WAITING_MODEL' AND typeof(u.invocation_count)='integer' AND u.invocation_count=0
      AND u.outcome IN ('MODEL_UNAVAILABLE_BEFORE_TRANSPORT','CLOUD_CREDENTIAL_REQUIRED_BEFORE_DISPATCH')
      AND u.intelligence_id IS NULL AND u.revision_id IS NULL AND u.actual_provider IS NULL AND u.actual_model IS NULL
      AND u.input_tokens IS NULL AND u.output_tokens IS NULL AND u.cost_microunits IS NULL
      AND u.duration_ms IS NULL AND u.http_status_code IS NULL
      AND a.provider=c.selected_provider AND a.model=c.selected_model
      AND a.consent_kind IN ('USER_CONFIRMATION','OWNER_QUALIFICATION') AND a.cost_status='UNKNOWN'
      AND a.authorized_at <= (CASE WHEN length(c.updated_at)=20 THEN substr(c.updated_at,1,19)||'.000000Z' ELSE c.updated_at END)
      AND (CASE WHEN length(NEW.cancelled_at)=20 THEN substr(NEW.cancelled_at,1,19)||'.000000Z' ELSE NEW.cancelled_at END) >= (CASE WHEN length(c.updated_at)=20 THEN substr(c.updated_at,1,19)||'.000000Z' ELSE c.updated_at END)
)
 OR EXISTS (SELECT 1 FROM distillation_no_new_intelligence_results WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_cloud_response_failures WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_unidentified_http_responses WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_openai_unidentified_http_responses WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_moonshot_unidentified_http_responses WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_zhipu_cloud_response_failures WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_waiting_model_cancellations WHERE execution_id=NEW.execution_id)
 OR EXISTS (SELECT 1 FROM intelligences WHERE intelligence_id='intelligence:distillation:'||NEW.execution_id)
 OR EXISTS (SELECT 1 FROM intelligence_revisions WHERE revision_id='revision:distillation:'||NEW.execution_id)
 OR EXISTS (SELECT 1 FROM distillation_cards WHERE revision_id='revision:distillation:'||NEW.execution_id)
 OR EXISTS (SELECT 1 FROM source_run_video_executions child LEFT JOIN source_runs run USING(run_id)
    WHERE child.distillation_execution_id=NEW.execution_id AND (run.run_id IS NULL
      OR child.video_id!=NEW.video_id OR run.source_id!=NEW.source_id OR child.state!='WAITING'
      OR run.state!='NEEDS_ATTENTION' OR run.attention_reason!='MODEL_UNAVAILABLE'))
BEGIN SELECT RAISE(ABORT, 'cloud cancellation requires proven zero-call wait'); END;

CREATE TRIGGER cloud_wait_cancellation_immutable_update
BEFORE UPDATE ON distillation_cloud_waiting_model_cancellations
BEGIN SELECT RAISE(ABORT, 'cloud wait cancellation is immutable'); END;
CREATE TRIGGER cloud_wait_cancellation_immutable_delete
BEFORE DELETE ON distillation_cloud_waiting_model_cancellations
BEGIN SELECT RAISE(ABORT, 'cloud wait cancellation is immutable'); END;
CREATE TRIGGER cloud_wait_cancelled_checkpoint_terminal
BEFORE UPDATE ON distillation_execution_checkpoints
WHEN EXISTS (SELECT 1 FROM distillation_cloud_waiting_model_cancellations WHERE execution_id=OLD.execution_id)
BEGIN SELECT RAISE(ABORT, 'cancelled cloud wait cannot be redispatched'); END;
CREATE TRIGGER cloud_wait_cancelled_child_insert
BEFORE INSERT ON source_run_video_executions
WHEN EXISTS (SELECT 1 FROM distillation_cloud_waiting_model_cancellations WHERE execution_id=NEW.distillation_execution_id)
BEGIN SELECT RAISE(ABORT, 'cancelled cloud wait cannot gain child work'); END;
CREATE TRIGGER cloud_wait_cancelled_child_update
BEFORE UPDATE ON source_run_video_executions
WHEN EXISTS (SELECT 1 FROM distillation_cloud_waiting_model_cancellations WHERE execution_id=OLD.distillation_execution_id OR execution_id=NEW.distillation_execution_id)
BEGIN SELECT RAISE(ABORT, 'cancelled cloud wait child cannot resume'); END;


-- Non-authoritative, bounded provider error-code observation; never an admission.
CREATE TABLE distillation_zhipu_http429_observations (
 execution_id TEXT NOT NULL PRIMARY KEY REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
 selected_provider TEXT NOT NULL CHECK(selected_provider='zhipu_bigmodel'),
 selected_model TEXT NOT NULL CHECK(selected_model='glm-4.7-flash'),
 http_status_code INTEGER NOT NULL CHECK(typeof(http_status_code)='integer' AND http_status_code=429),
 error_code TEXT NOT NULL CHECK(typeof(error_code)='text' AND error_code IN ('1113','1302','1305','1308','1315')),
 observed_at TEXT NOT NULL CHECK(typeof(observed_at)='text' AND length(observed_at)=27 AND observed_at GLOB '????-??-??T??:??:??.??????Z' AND substr(observed_at,21,6) NOT GLOB '*[^0-9]*' AND substr(observed_at,1,4) BETWEEN '0001' AND '9999' AND strftime('%Y-%m-%dT%H:%M:%S',substr(observed_at,1,19)||'Z','+0 seconds') IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%S',substr(observed_at,1,19)||'Z','+0 seconds')=substr(observed_at,1,19))
);
CREATE TRIGGER zhipu_http429_observation_requires_failure
BEFORE INSERT ON distillation_zhipu_http429_observations
WHEN NOT EXISTS (
 SELECT 1 FROM distillation_execution_checkpoints c
 JOIN distillation_zhipu_cloud_response_failures f USING(execution_id)
 JOIN distillation_zhipu_cloud_authorizations a USING(execution_id)
 WHERE c.execution_id=NEW.execution_id AND c.selected_provider=NEW.selected_provider AND c.selected_model=NEW.selected_model
 AND c.status='REJECTED_OUTPUT' AND typeof(c.invocation_count)='integer' AND c.invocation_count=1
 AND c.intelligence_id IS NULL AND c.revision_id IS NULL
 AND f.status=c.status AND f.outcome='CLOUD_HTTP_ERROR' AND typeof(f.http_status_code)='integer' AND f.http_status_code=429
 AND f.actual_provider=c.selected_provider AND f.actual_model IS NULL
 AND f.input_tokens IS NULL AND f.output_tokens IS NULL AND f.cost_microunits IS NULL AND f.duration_ms IS NULL
 AND NEW.observed_at=c.updated_at AND NEW.observed_at=f.received_at
 AND a.provider=c.selected_provider AND a.model=c.selected_model
 AND a.consent_kind IN ('USER_CONFIRMATION','OWNER_QUALIFICATION') AND a.cost_status='UNKNOWN'
 AND a.authorized_at<=NEW.observed_at
 AND NOT EXISTS (SELECT 1 FROM distillation_resource_usage WHERE execution_id=c.execution_id)
 AND NOT EXISTS (SELECT 1 FROM distillation_no_new_intelligence_results WHERE execution_id=c.execution_id)
)
BEGIN SELECT RAISE(ABORT, 'HTTP429 observation requires settled authorized failure'); END;
CREATE TRIGGER zhipu_http429_observation_immutable_update
BEFORE UPDATE ON distillation_zhipu_http429_observations
BEGIN SELECT RAISE(ABORT, 'HTTP429 observation is immutable'); END;
CREATE TRIGGER zhipu_http429_observation_immutable_delete
BEFORE DELETE ON distillation_zhipu_http429_observations
BEGIN SELECT RAISE(ABORT, 'HTTP429 observation is immutable'); END;
