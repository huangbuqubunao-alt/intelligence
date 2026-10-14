-- Explicitly approved immutable historical input; never model eligibility.
CREATE TABLE local_text_input_proofs (
    execution_id TEXT PRIMARY KEY NOT NULL REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT,
    proof_version TEXT NOT NULL CHECK(proof_version='local-text-input-proof-v1'),
    wire_version TEXT NOT NULL CHECK(wire_version='local-text-distillation-v2'),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES content_source_snapshots(content_id) ON DELETE RESTRICT,
    original_summary_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    global_policy_revision_id TEXT NOT NULL REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    source_policy_revision_id TEXT REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    input_json TEXT NOT NULL CHECK(json_valid(input_json) AND json_type(input_json)='object'),
    context_json TEXT NOT NULL CHECK(json_valid(context_json) AND json_type(context_json)='object'),
    input_hash TEXT NOT NULL CHECK(length(input_hash)=64 AND input_hash NOT GLOB '*[^0-9a-f]*'),
    context_hash TEXT NOT NULL CHECK(length(context_hash)=64 AND context_hash NOT GLOB '*[^0-9a-f]*'),
    profile_hash TEXT NOT NULL CHECK(length(profile_hash)=64 AND profile_hash NOT GLOB '*[^0-9a-f]*'),
    proof_hash TEXT NOT NULL CHECK(length(proof_hash)=64 AND proof_hash NOT GLOB '*[^0-9a-f]*'),
    created_at TEXT NOT NULL CHECK(length(created_at)=27 AND created_at GLOB '????-??-??T??:??:??.??????Z'),
    CHECK(length(CAST(input_json AS BLOB))+length(CAST(context_json AS BLOB))<=524288)
);
CREATE INDEX local_text_input_proofs_source ON local_text_input_proofs(source_id);
CREATE INDEX local_text_input_proofs_video ON local_text_input_proofs(video_id);
CREATE TRIGGER local_text_input_proofs_immutable_update BEFORE UPDATE ON local_text_input_proofs
BEGIN SELECT RAISE(ABORT,'local text input proof is immutable'); END;
CREATE TRIGGER local_text_input_proofs_immutable_delete BEFORE DELETE ON local_text_input_proofs
BEGIN SELECT RAISE(ABORT,'local text input proof is immutable'); END;
CREATE TRIGGER local_text_input_proofs_insert_authority BEFORE INSERT ON local_text_input_proofs
WHEN NOT EXISTS (
    SELECT 1 FROM distillation_execution_checkpoints d
    JOIN content_source_snapshots s ON s.content_id=d.video_id
    JOIN source_subscriptions source ON source.source_id=d.source_id
    JOIN current_content_summaries c ON c.video_id=d.video_id
    JOIN artifacts a ON a.artifact_id=c.analysis_artifact_id
    JOIN source_policy_revisions p ON p.revision_id=NEW.global_policy_revision_id
    WHERE d.execution_id=NEW.execution_id AND d.source_id=NEW.source_id AND d.video_id=NEW.video_id
      AND d.status='PENDING' AND d.budget_state='RESERVED_NOT_DISPATCHED' AND d.invocation_count=0
      AND d.reason LIKE 'MANUAL_CONTENT:%' AND d.use_case='PERSONALIZED_INTELLIGENCE'
      AND d.selected_provider NOT IN ('openai','nvidia_nim','moonshot')
      AND s.provider='LOCAL' AND s.media_kind='TEXT' AND s.status='READY' AND s.source_id=NEW.source_id
      AND source.provider='LOCAL' AND source.source_type='LOCAL_LIBRARY' AND source.processing_policy='DISCOVER_ONLY'
      AND a.artifact_id=NEW.original_summary_artifact_id AND a.video_id=NEW.video_id
      AND a.provider='extractive-source' AND a.producer_version='extractive-summary-v1' AND a.deleted_at IS NULL
      AND p.policy_scope='GLOBAL' AND p.source_id IS NULL
      AND EXISTS(SELECT 1 FROM source_video_links WHERE source_id=NEW.source_id AND video_id=NEW.video_id)
)
OR (NEW.source_policy_revision_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM source_policy_revisions WHERE revision_id=NEW.source_policy_revision_id AND policy_scope='SOURCE' AND source_id=NEW.source_id))
OR json_type(NEW.input_json,'$.evidence') IS NOT 'array'
OR (SELECT count(*) FROM json_each(NEW.input_json,'$.evidence')) NOT BETWEEN 1 AND 20
OR EXISTS(SELECT 1 FROM json_each(NEW.input_json,'$.evidence') j WHERE NOT EXISTS(
    SELECT 1 FROM evidence e WHERE e.evidence_id=json_extract(j.value,'$.evidence_id') AND e.video_id=NEW.video_id
    AND e.locator_type='TEXT_RANGE' AND e.start_ms IS NULL AND e.end_ms IS NULL AND e.availability='AVAILABLE'))
OR json_type(NEW.input_json,'$.preferences') IS NOT 'array'
OR EXISTS(SELECT 1 FROM json_each(NEW.input_json,'$.preferences') j WHERE NOT EXISTS(
    SELECT 1 FROM preferences p WHERE p.preference_id=json_extract(j.value,'$.preference_id')))
BEGIN SELECT RAISE(ABORT,'local text proof requires reserved source-bound input'); END;
