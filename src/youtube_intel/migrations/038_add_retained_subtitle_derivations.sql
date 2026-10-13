-- Owner-approved neutral retention; never a Transcript, Evidence or successful output.
CREATE TABLE retained_subtitle_derivations (
    archive_id TEXT PRIMARY KEY NOT NULL CHECK(length(archive_id)=64 AND archive_id NOT GLOB '*[^0-9a-f]*'),
    proof_version TEXT NOT NULL CHECK(proof_version='failed-caption-derivation-v1'),
    request_hash TEXT NOT NULL REFERENCES provider_calls(request_hash) ON DELETE RESTRICT,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE RESTRICT,
    source_run_id TEXT NOT NULL REFERENCES source_runs(run_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    raw_capture_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    raw_sha256 TEXT NOT NULL CHECK(length(raw_sha256)=64 AND raw_sha256 NOT GLOB '*[^0-9a-f]*'),
    relative_path TEXT NOT NULL CHECK(length(relative_path)>0 AND relative_path LIKE 'transcripts/%' AND substr(relative_path,1,1)<>'/' AND instr(relative_path,'..')=0 AND instr(relative_path,char(92))=0),
    derived_sha256 TEXT NOT NULL CHECK(length(derived_sha256)=64 AND derived_sha256 NOT GLOB '*[^0-9a-f]*'),
    size_bytes INTEGER NOT NULL CHECK(typeof(size_bytes)='integer' AND size_bytes BETWEEN 1 AND 4000000),
    normalization_version TEXT NOT NULL CHECK(normalization_version='subtitle-normalization-v1'),
    quality_profile_version TEXT NOT NULL CHECK(quality_profile_version='subtitle-quality-v1'),
    canonical_request_hash TEXT NOT NULL CHECK(length(canonical_request_hash)=64 AND canonical_request_hash NOT GLOB '*[^0-9a-f]*'),
    successor_job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE RESTRICT,
    successor_request_hash TEXT NOT NULL REFERENCES provider_calls(request_hash) ON DELETE RESTRICT,
    successor_canonical_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    successor_summary_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK(reason='COMPLETION_PERSISTENCE_FAILED_WITH_VERIFIED_SUCCESSOR'),
    created_at TEXT NOT NULL CHECK(length(created_at)=27 AND substr(created_at,-1)='Z'),
    proof_json TEXT NOT NULL CHECK(length(proof_json) BETWEEN 1 AND 1000000),
    proof_sha256 TEXT NOT NULL CHECK(length(proof_sha256)=64 AND proof_sha256 NOT GLOB '*[^0-9a-f]*')
);
CREATE UNIQUE INDEX retained_subtitle_derivations_request ON retained_subtitle_derivations(request_hash);
CREATE UNIQUE INDEX retained_subtitle_derivations_job ON retained_subtitle_derivations(job_id);
CREATE UNIQUE INDEX retained_subtitle_derivations_path ON retained_subtitle_derivations(relative_path);
CREATE TRIGGER retained_subtitle_derivations_immutable_update BEFORE UPDATE ON retained_subtitle_derivations
BEGIN SELECT RAISE(ABORT,'retained subtitle derivation is immutable'); END;
CREATE TRIGGER retained_subtitle_derivations_immutable_delete BEFORE DELETE ON retained_subtitle_derivations
BEGIN SELECT RAISE(ABORT,'retained subtitle derivation is immutable'); END;
