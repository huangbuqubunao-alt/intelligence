-- Independent Content-only requests. No historical Source Run or success is inferred.
CREATE TABLE tracked_content_retry_requests (
 request_id TEXT PRIMARY KEY NOT NULL CHECK(length(request_id) BETWEEN 1 AND 512),
 contract TEXT NOT NULL CHECK(contract='tracked-content-retry-v1'),
 operation TEXT NOT NULL CHECK(operation='RETRY_NATIVE_TRANSCRIPT'),
 command_id TEXT NOT NULL CHECK(length(trim(command_id)) BETWEEN 1 AND 512),
 client_input_json TEXT NOT NULL CHECK(json_valid(client_input_json) AND json_type(client_input_json)='object' AND length(CAST(client_input_json AS BLOB))<=8192),
 client_input_sha256 TEXT NOT NULL CHECK(length(client_input_sha256)=64 AND client_input_sha256 NOT GLOB '*[^0-9a-f]*'),
 source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
 video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
 observation_identity TEXT NOT NULL CHECK(length(observation_identity) BETWEEN 1 AND 100),
 provider TEXT NOT NULL CHECK(provider='YOUTUBE'),
 channel_id TEXT NOT NULL CHECK(length(trim(channel_id)) BETWEEN 1 AND 512),
 expected_old_job_id TEXT NOT NULL UNIQUE REFERENCES jobs(job_id) ON DELETE RESTRICT,
 old_job_snapshot_json TEXT NOT NULL CHECK(json_valid(old_job_snapshot_json) AND length(CAST(old_job_snapshot_json AS BLOB))<=16384),
 old_job_snapshot_sha256 TEXT NOT NULL CHECK(length(old_job_snapshot_sha256)=64 AND old_job_snapshot_sha256 NOT GLOB '*[^0-9a-f]*'),
 target_job_id TEXT NOT NULL UNIQUE REFERENCES jobs(job_id) ON DELETE RESTRICT,
 pipeline_version TEXT NOT NULL CHECK(length(trim(pipeline_version)) BETWEEN 1 AND 512),
 target_stage TEXT NOT NULL CHECK(target_stage='TRANSCRIPT'),
 parameters_json TEXT NOT NULL CHECK(json_valid(parameters_json) AND json_type(parameters_json)='object' AND length(CAST(parameters_json AS BLOB))<=65536),
 parameters_sha256 TEXT NOT NULL CHECK(length(parameters_sha256)=64 AND parameters_sha256 NOT GLOB '*[^0-9a-f]*'),
 refresh_generation INTEGER NOT NULL CHECK(typeof(refresh_generation)='integer' AND refresh_generation BETWEEN 0 AND 1152921504606846975),
 raw_request_hash TEXT NOT NULL UNIQUE CHECK(length(raw_request_hash)=64 AND raw_request_hash NOT GLOB '*[^0-9a-f]*'),
 provider_request_hash TEXT NOT NULL UNIQUE CHECK(length(provider_request_hash)=64 AND provider_request_hash NOT GLOB '*[^0-9a-f]*'),
 created_at TEXT NOT NULL CHECK(length(created_at)=27 AND substr(created_at,-1)='Z'),
 FOREIGN KEY(source_id,observation_identity) REFERENCES source_observations(source_id,canonical_identity) ON DELETE RESTRICT,
 UNIQUE(source_id,operation,command_id), UNIQUE(video_id,refresh_generation)
);
CREATE INDEX tracked_content_retry_video ON tracked_content_retry_requests(video_id,created_at);
CREATE INDEX tracked_content_retry_source ON tracked_content_retry_requests(source_id,created_at);
CREATE TRIGGER tracked_content_retry_request_no_update BEFORE UPDATE ON tracked_content_retry_requests
BEGIN SELECT RAISE(ABORT,'Content retry request is immutable'); END;
CREATE TRIGGER tracked_content_retry_request_no_delete BEFORE DELETE ON tracked_content_retry_requests
BEGIN SELECT RAISE(ABORT,'Content retry request is retained'); END;
CREATE TRIGGER tracked_content_retry_request_authority BEFORE INSERT ON tracked_content_retry_requests
WHEN NOT EXISTS (
 SELECT 1 FROM source_subscriptions s JOIN source_tracking_state t ON t.source_id=s.source_id
 JOIN source_observations o ON o.source_id=s.source_id JOIN source_video_links l ON l.source_id=s.source_id AND l.video_id=o.content_id
 JOIN videos v ON v.video_id=o.content_id JOIN jobs old ON old.video_id=v.video_id JOIN jobs target ON target.video_id=v.video_id
 WHERE s.source_id=NEW.source_id AND s.provider='YOUTUBE' AND s.source_type='CHANNEL' AND s.enabled=1
 AND s.channel_id=NEW.channel_id AND v.channel_id=NEW.channel_id AND v.provider='YOUTUBE'
 AND v.video_id=NEW.video_id AND v.pipeline_status='METADATA_READY' AND v.pipeline_version=NEW.pipeline_version
 AND o.canonical_identity=NEW.observation_identity AND o.baseline=0 AND o.enrollment='ENROLLED'
 AND old.job_id=NEW.expected_old_job_id AND old.job_type='VIDEO_STAGE' AND old.target_stage='TRANSCRIPT' AND old.status='FAILED_FINAL'
 AND old.lease_owner IS NULL AND old.lease_until IS NULL AND old.finished_at IS NOT NULL
 AND target.job_id=NEW.target_job_id AND target.job_type='VIDEO_STAGE' AND target.target_stage='TRANSCRIPT'
 AND target.status='PENDING' AND target.attempt_count=0 AND target.max_attempts=1 AND target.pipeline_version=NEW.pipeline_version
) BEGIN SELECT RAISE(ABORT,'Content retry requires exact tracked terminal Content'); END;

CREATE TABLE tracked_content_retry_executions (
 request_id TEXT PRIMARY KEY NOT NULL REFERENCES tracked_content_retry_requests(request_id) ON DELETE RESTRICT,
 source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
 revision INTEGER NOT NULL DEFAULT 0 CHECK(typeof(revision)='integer' AND revision>=0),
 state TEXT NOT NULL CHECK(state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION','SUCCEEDED','FAILED','CANCELLED','AMBIGUOUS')),
 fencing_epoch INTEGER NOT NULL DEFAULT 0 CHECK(typeof(fencing_epoch)='integer' AND fencing_epoch>=0),
 lease_owner TEXT CHECK(lease_owner IS NULL OR length(trim(lease_owner)) BETWEEN 1 AND 512),
 lease_until TEXT CHECK(lease_until IS NULL OR (length(lease_until)=27 AND substr(lease_until,-1)='Z')),
 provider_call_hash TEXT UNIQUE REFERENCES provider_calls(request_hash) ON DELETE RESTRICT,
 local_attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(typeof(local_attempt_count)='integer' AND local_attempt_count BETWEEN 0 AND 3),
 error_code TEXT,
 canonical_artifact_id TEXT REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
 timed_transcript_id TEXT REFERENCES timed_transcripts(timed_transcript_id) ON DELETE RESTRICT,
 summary_artifact_id TEXT REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
 completion_json TEXT CHECK(completion_json IS NULL OR (json_valid(completion_json) AND length(CAST(completion_json AS BLOB))<=1048576)),
 completion_sha256 TEXT CHECK(completion_sha256 IS NULL OR (length(completion_sha256)=64 AND completion_sha256 NOT GLOB '*[^0-9a-f]*')),
 events_json TEXT NOT NULL CHECK(json_valid(events_json) AND json_type(events_json)='array' AND json_array_length(events_json) BETWEEN 1 AND 128 AND length(CAST(events_json AS BLOB))<=1048576),
 updated_at TEXT NOT NULL CHECK(length(updated_at)=27 AND substr(updated_at,-1)='Z'),
 finished_at TEXT CHECK(finished_at IS NULL OR (length(finished_at)=27 AND substr(finished_at,-1)='Z')),
 CHECK((state IN ('ACQUIRING','FINALIZING') AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR (state NOT IN ('ACQUIRING','FINALIZING') AND lease_owner IS NULL AND lease_until IS NULL)),
 CHECK((state IN ('SUCCEEDED','FAILED','CANCELLED','AMBIGUOUS') AND finished_at IS NOT NULL) OR (state NOT IN ('SUCCEEDED','FAILED','CANCELLED','AMBIGUOUS') AND finished_at IS NULL)),
 CHECK((state='SUCCEEDED' AND canonical_artifact_id IS NOT NULL AND timed_transcript_id IS NOT NULL AND summary_artifact_id IS NOT NULL AND completion_json IS NOT NULL AND completion_sha256 IS NOT NULL) OR (state!='SUCCEEDED' AND canonical_artifact_id IS NULL AND timed_transcript_id IS NULL AND summary_artifact_id IS NULL AND completion_json IS NULL AND completion_sha256 IS NULL)),
 CHECK((state IN ('ATTENTION','FAILED','CANCELLED','AMBIGUOUS') AND error_code IS NOT NULL) OR (state NOT IN ('ATTENTION','FAILED','CANCELLED','AMBIGUOUS') AND error_code IS NULL))
);
CREATE UNIQUE INDEX tracked_content_retry_one_live_source ON tracked_content_retry_executions(source_id) WHERE state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION');
CREATE TRIGGER tracked_content_retry_execution_insert BEFORE INSERT ON tracked_content_retry_executions
WHEN NEW.revision!=0 OR NEW.state!='QUEUED' OR NEW.fencing_epoch!=0 OR NEW.local_attempt_count!=0 OR NEW.provider_call_hash IS NOT NULL OR NOT EXISTS(SELECT 1 FROM tracked_content_retry_requests r WHERE r.request_id=NEW.request_id AND r.source_id=NEW.source_id)
BEGIN SELECT RAISE(ABORT,'Content retry execution must begin at its exact request'); END;
CREATE TRIGGER tracked_content_retry_execution_update BEFORE UPDATE ON tracked_content_retry_executions
WHEN OLD.state IN ('SUCCEEDED','FAILED','CANCELLED','AMBIGUOUS') OR NEW.request_id IS NOT OLD.request_id OR NEW.source_id IS NOT OLD.source_id
 OR NEW.revision!=OLD.revision+1 OR NEW.fencing_epoch NOT BETWEEN OLD.fencing_epoch AND OLD.fencing_epoch+1
 OR NEW.local_attempt_count NOT BETWEEN OLD.local_attempt_count AND OLD.local_attempt_count+1
 OR (OLD.provider_call_hash IS NOT NULL AND NEW.provider_call_hash IS NOT OLD.provider_call_hash)
 OR (NEW.provider_call_hash IS NOT NULL AND NEW.provider_call_hash IS NOT (SELECT provider_request_hash FROM tracked_content_retry_requests WHERE request_id=NEW.request_id))
 OR NOT ((OLD.state='QUEUED' AND NEW.state IN ('ACQUIRING','CANCELLED','FAILED'))
 OR (OLD.state='ACQUIRING' AND NEW.state IN ('ACQUIRING','FINALIZING','FAILED','AMBIGUOUS'))
 OR (OLD.state='FINALIZING' AND NEW.state IN ('FINALIZING','SUCCEEDED','ATTENTION','FAILED'))
 OR (OLD.state='ATTENTION' AND NEW.state IN ('FINALIZING','FAILED')))
 OR json_array_length(NEW.events_json) NOT BETWEEN json_array_length(OLD.events_json) AND json_array_length(OLD.events_json)+1
 OR EXISTS(SELECT 1 FROM json_each(OLD.events_json) o WHERE json_extract(NEW.events_json,'$['||o.key||']') IS NOT o.value)
 OR ((NEW.state IS NOT OLD.state OR NEW.fencing_epoch!=OLD.fencing_epoch) AND json_array_length(NEW.events_json)!=json_array_length(OLD.events_json)+1)
BEGIN SELECT RAISE(ABORT,'Content retry execution transition violates CAS/history'); END;
CREATE TRIGGER tracked_content_retry_execution_no_delete BEFORE DELETE ON tracked_content_retry_executions
BEGIN SELECT RAISE(ABORT,'Content retry execution is retained'); END;

CREATE TABLE tracked_content_retry_files (
 request_id TEXT NOT NULL REFERENCES tracked_content_retry_requests(request_id) ON DELETE RESTRICT,
 relative_path TEXT NOT NULL UNIQUE CHECK(length(relative_path) BETWEEN 1 AND 4096 AND substr(relative_path,1,1)!='/' AND instr(relative_path,'..')=0 AND instr(relative_path,char(92))=0),
 role TEXT NOT NULL CHECK(role IN ('CAPTURE','RAW_SOURCE','CANONICAL_DERIVATION','SUMMARY_DERIVATION','WRITE_BUFFER')),
 expected_sha256 TEXT NOT NULL CHECK(length(expected_sha256)=64 AND expected_sha256 NOT GLOB '*[^0-9a-f]*'),
 expected_size_bytes INTEGER NOT NULL CHECK(typeof(expected_size_bytes)='integer' AND expected_size_bytes>=0),
 state TEXT NOT NULL CHECK(state IN ('PLANNED','VERIFIED','RETAINED_PARTIAL','ABSENT')),
 observed_sha256 TEXT CHECK(observed_sha256 IS NULL OR (length(observed_sha256)=64 AND observed_sha256 NOT GLOB '*[^0-9a-f]*')),
 observed_size_bytes INTEGER CHECK(observed_size_bytes IS NULL OR (typeof(observed_size_bytes)='integer' AND observed_size_bytes>=0)),
 proof_json TEXT NOT NULL CHECK(json_valid(proof_json) AND json_type(proof_json)='object' AND length(CAST(proof_json AS BLOB))<=65536),
 proof_sha256 TEXT NOT NULL CHECK(length(proof_sha256)=64 AND proof_sha256 NOT GLOB '*[^0-9a-f]*'),
 created_at TEXT NOT NULL CHECK(length(created_at)=27 AND substr(created_at,-1)='Z'),
 settled_at TEXT CHECK(settled_at IS NULL OR (length(settled_at)=27 AND substr(settled_at,-1)='Z')),
 PRIMARY KEY(request_id,relative_path),
 CHECK((state='PLANNED' AND settled_at IS NULL AND observed_sha256 IS NULL AND observed_size_bytes IS NULL)
 OR (state='VERIFIED' AND settled_at IS NOT NULL AND observed_sha256=expected_sha256 AND observed_size_bytes=expected_size_bytes)
 OR (state='RETAINED_PARTIAL' AND role='WRITE_BUFFER' AND settled_at IS NOT NULL AND observed_sha256 IS NOT NULL AND observed_size_bytes IS NOT NULL)
 OR (state='ABSENT' AND settled_at IS NOT NULL AND observed_sha256 IS NULL AND observed_size_bytes IS NULL))
);
CREATE TRIGGER tracked_content_retry_file_update BEFORE UPDATE ON tracked_content_retry_files
WHEN OLD.state!='PLANNED' OR NEW.state NOT IN ('VERIFIED','RETAINED_PARTIAL','ABSENT')
 OR NEW.request_id IS NOT OLD.request_id OR NEW.relative_path IS NOT OLD.relative_path OR NEW.role IS NOT OLD.role
 OR NEW.expected_sha256 IS NOT OLD.expected_sha256 OR NEW.expected_size_bytes IS NOT OLD.expected_size_bytes
 OR NEW.proof_json IS NOT OLD.proof_json OR NEW.proof_sha256 IS NOT OLD.proof_sha256 OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT,'Content retry file identity is immutable'); END;
CREATE TRIGGER tracked_content_retry_file_no_delete BEFORE DELETE ON tracked_content_retry_files
BEGIN SELECT RAISE(ABORT,'Content retry file history is retained'); END;

CREATE TRIGGER tracked_content_retry_old_job_no_update BEFORE UPDATE ON jobs
WHEN EXISTS(SELECT 1 FROM tracked_content_retry_requests WHERE expected_old_job_id=OLD.job_id)
BEGIN SELECT RAISE(ABORT,'Consumed Content retry failure is immutable'); END;
CREATE TRIGGER tracked_content_retry_job_identity BEFORE UPDATE ON jobs
WHEN EXISTS(SELECT 1 FROM tracked_content_retry_requests WHERE target_job_id=OLD.job_id) AND
 (NEW.job_id IS NOT OLD.job_id OR NEW.scope_key IS NOT OLD.scope_key OR NEW.video_id IS NOT OLD.video_id OR NEW.job_type IS NOT OLD.job_type OR NEW.target_stage IS NOT OLD.target_stage OR NEW.pipeline_version IS NOT OLD.pipeline_version OR NEW.max_attempts IS NOT OLD.max_attempts OR NEW.scoring_lineage_version IS NOT OLD.scoring_lineage_version OR NEW.created_at IS NOT OLD.created_at)
BEGIN SELECT RAISE(ABORT,'Content retry target identity is immutable'); END;
CREATE TRIGGER tracked_content_retry_source_run_insert BEFORE INSERT ON source_runs
WHEN EXISTS(SELECT 1 FROM tracked_content_retry_executions WHERE source_id=NEW.source_id AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION'))
BEGIN SELECT RAISE(ABORT,'Content retry holds this Source'); END;
CREATE TRIGGER tracked_content_retry_source_run_update BEFORE UPDATE OF state ON source_runs
WHEN NEW.state IN ('QUEUED','RUNNING','WAITING','PARTIAL','NEEDS_ATTENTION') AND EXISTS(SELECT 1 FROM tracked_content_retry_executions WHERE source_id=NEW.source_id AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION'))
BEGIN SELECT RAISE(ABORT,'Content retry holds this Source'); END;
CREATE TRIGGER tracked_content_retry_source_check_insert BEFORE INSERT ON source_checks
WHEN NEW.status='RUNNING' AND EXISTS(SELECT 1 FROM tracked_content_retry_executions WHERE source_id=NEW.source_id AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION'))
BEGIN SELECT RAISE(ABORT,'Content retry holds this Source'); END;
CREATE TRIGGER tracked_content_retry_execution_source_idle BEFORE INSERT ON tracked_content_retry_executions
WHEN EXISTS(SELECT 1 FROM source_runs WHERE source_id=NEW.source_id AND state IN ('QUEUED','RUNNING','WAITING','PARTIAL','NEEDS_ATTENTION'))
 OR EXISTS(SELECT 1 FROM source_checks WHERE source_id=NEW.source_id AND status='RUNNING')
BEGIN SELECT RAISE(ABORT,'Source work excludes Content retry'); END;
CREATE TRIGGER tracked_content_retry_source_check_update BEFORE UPDATE OF status ON source_checks
WHEN NEW.status='RUNNING' AND EXISTS(SELECT 1 FROM tracked_content_retry_executions WHERE source_id=NEW.source_id AND state IN ('QUEUED','ACQUIRING','FINALIZING','ATTENTION'))
BEGIN SELECT RAISE(ABORT,'Content retry holds this Source'); END;
