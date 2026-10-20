-- Final additive long protocol storage; no transport or qualification authority.
CREATE TABLE long_distillation_input_proofs (
    execution_id TEXT PRIMARY KEY NOT NULL REFERENCES distillation_execution_checkpoints(execution_id) ON DELETE RESTRICT CHECK(length(execution_id)=91 AND substr(execution_id,1,27)='distillation:long-timed-v1:' AND substr(execution_id,28) NOT GLOB '*[^0-9a-f]*'),
    proof_version TEXT NOT NULL CHECK(proof_version='long-timed-input-proof-v1'),
    wire_version TEXT NOT NULL CHECK(wire_version='long-grounding-lossless-timed-v1'),
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    canonical_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    timed_transcript_id TEXT NOT NULL REFERENCES timed_transcripts(timed_transcript_id) ON DELETE RESTRICT,
    original_summary_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    global_policy_revision_id TEXT NOT NULL REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    source_policy_revision_id TEXT  REFERENCES source_policy_revisions(revision_id) ON DELETE RESTRICT,
    semantic_snapshot_wire TEXT NOT NULL CHECK (semantic_snapshot_wire IS NULL OR (typeof(semantic_snapshot_wire)='text' AND length(CAST(semantic_snapshot_wire AS BLOB)) BETWEEN 1 AND 16000000 AND json_valid(semantic_snapshot_wire) AND json_type(semantic_snapshot_wire)='object')),
    semantic_snapshot_hash TEXT NOT NULL CHECK (semantic_snapshot_hash IS NULL OR (typeof(semantic_snapshot_hash)='text' AND length(semantic_snapshot_hash)=64 AND semantic_snapshot_hash NOT GLOB '*[^0-9a-f]*')),
    profile_wire TEXT NOT NULL CHECK (profile_wire IS NULL OR (typeof(profile_wire)='text' AND length(CAST(profile_wire AS BLOB)) BETWEEN 1 AND 1000000 AND json_valid(profile_wire) AND json_type(profile_wire)='object')),
    profile_hash TEXT NOT NULL CHECK (profile_hash IS NULL OR (typeof(profile_hash)='text' AND length(profile_hash)=64 AND profile_hash NOT GLOB '*[^0-9a-f]*')),
    request_wire TEXT NOT NULL CHECK (request_wire IS NULL OR (typeof(request_wire)='text' AND length(CAST(request_wire AS BLOB)) BETWEEN 1 AND 8000000 AND json_valid(request_wire) AND json_type(request_wire)='object')),
    request_hash TEXT NOT NULL CHECK (request_hash IS NULL OR (typeof(request_hash)='text' AND length(request_hash)=64 AND request_hash NOT GLOB '*[^0-9a-f]*')),
    schema_hash TEXT NOT NULL CHECK (schema_hash IS NULL OR (typeof(schema_hash)='text' AND length(schema_hash)=64 AND schema_hash NOT GLOB '*[^0-9a-f]*')),
    freeze_hash TEXT NOT NULL CHECK (freeze_hash IS NULL OR (typeof(freeze_hash)='text' AND length(freeze_hash)=64 AND freeze_hash NOT GLOB '*[^0-9a-f]*')),
    code_identity_json TEXT NOT NULL CHECK (code_identity_json IS NULL OR (typeof(code_identity_json)='text' AND length(CAST(code_identity_json AS BLOB)) BETWEEN 1 AND 65536 AND json_valid(code_identity_json) AND json_type(code_identity_json)='object')),
    proof_hash TEXT NOT NULL CHECK (proof_hash IS NULL OR (typeof(proof_hash)='text' AND length(proof_hash)=64 AND proof_hash NOT GLOB '*[^0-9a-f]*')),
    created_at TEXT NOT NULL CHECK(typeof(created_at)='text' AND length(created_at)=27 AND created_at GLOB '????-??-??T??:??:??.??????Z')
);
CREATE TABLE long_distillation_completion_receipts (
    execution_id TEXT PRIMARY KEY NOT NULL REFERENCES long_distillation_input_proofs(execution_id) ON DELETE RESTRICT,
    usage_execution_id TEXT REFERENCES distillation_resource_usage(execution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    receipt_version TEXT NOT NULL CHECK(receipt_version='long-timed-completion-receipt-v1'),
    proof_hash TEXT NOT NULL CHECK (proof_hash IS NULL OR (typeof(proof_hash)='text' AND length(proof_hash)=64 AND proof_hash NOT GLOB '*[^0-9a-f]*')),
    public_wire TEXT CHECK (public_wire IS NULL OR (typeof(public_wire)='text' AND length(CAST(public_wire AS BLOB)) BETWEEN 0 AND 1000000)),
    public_hash TEXT CHECK (public_hash IS NULL OR (typeof(public_hash)='text' AND length(public_hash)=64 AND public_hash NOT GLOB '*[^0-9a-f]*')),
    decoded_wire TEXT  CHECK (decoded_wire IS NULL OR (typeof(decoded_wire)='text' AND length(CAST(decoded_wire AS BLOB)) BETWEEN 1 AND 1000000 AND json_valid(decoded_wire) AND json_type(decoded_wire)='object')),
    decoded_hash TEXT  CHECK (decoded_hash IS NULL OR (typeof(decoded_hash)='text' AND length(decoded_hash)=64 AND decoded_hash NOT GLOB '*[^0-9a-f]*')),
    completion_json TEXT NOT NULL CHECK (completion_json IS NULL OR (typeof(completion_json)='text' AND length(CAST(completion_json AS BLOB)) BETWEEN 1 AND 65536 AND json_valid(completion_json) AND json_type(completion_json)='object')),
    completion_hash TEXT NOT NULL CHECK (completion_hash IS NULL OR (typeof(completion_hash)='text' AND length(completion_hash)=64 AND completion_hash NOT GLOB '*[^0-9a-f]*')),
    result_kind TEXT NOT NULL CHECK(result_kind IN ('INTELLIGENCE','NO_NEW_INTELLIGENCE','REJECTED')),
    terminal TEXT NOT NULL CHECK(terminal IN ('SUCCEEDED','SUCCEEDED_NO_NEW_INTELLIGENCE','REJECTED_OUTPUT')),
    intelligence_id TEXT,
    revision_id TEXT REFERENCES distillation_cards(revision_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    admitted_content_hash TEXT  CHECK (admitted_content_hash IS NULL OR (typeof(admitted_content_hash)='text' AND length(admitted_content_hash)=64 AND admitted_content_hash NOT GLOB '*[^0-9a-f]*')),
    no_new_execution_id TEXT REFERENCES distillation_no_new_intelligence_results(execution_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    receipt_hash TEXT NOT NULL CHECK (receipt_hash IS NULL OR (typeof(receipt_hash)='text' AND length(receipt_hash)=64 AND receipt_hash NOT GLOB '*[^0-9a-f]*')),
    created_at TEXT NOT NULL CHECK(typeof(created_at)='text' AND length(created_at)=27 AND created_at GLOB '????-??-??T??:??:??.??????Z'),
    FOREIGN KEY (intelligence_id,revision_id) REFERENCES intelligence_revisions(intelligence_id,revision_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CHECK ((public_wire IS NULL)=(public_hash IS NULL)),
    CHECK ((decoded_wire IS NULL)=(decoded_hash IS NULL)),
    CHECK ((result_kind='INTELLIGENCE' AND usage_execution_id IS execution_id AND terminal='SUCCEEDED' AND decoded_wire IS NOT NULL AND intelligence_id IS NOT NULL AND revision_id IS NOT NULL AND admitted_content_hash IS NOT NULL AND no_new_execution_id IS NULL) OR (result_kind='NO_NEW_INTELLIGENCE' AND usage_execution_id IS NULL AND terminal='SUCCEEDED_NO_NEW_INTELLIGENCE' AND decoded_wire IS NOT NULL AND intelligence_id IS NULL AND revision_id IS NULL AND admitted_content_hash IS NULL AND no_new_execution_id IS execution_id) OR (result_kind='REJECTED' AND usage_execution_id IS execution_id AND terminal='REJECTED_OUTPUT' AND intelligence_id IS NULL AND revision_id IS NULL AND admitted_content_hash IS NULL AND no_new_execution_id IS NULL)),
    CHECK(json_type(completion_json,'$.actual_provider') IS 'text' AND length(json_extract(completion_json,'$.actual_provider')) BETWEEN 1 AND 160
      AND json_type(completion_json,'$.actual_model') IS 'text' AND length(json_extract(completion_json,'$.actual_model')) BETWEEN 1 AND 320
      AND json_type(completion_json,'$.request_hash') IS 'text'
      AND COALESCE(json_type(completion_json,'$.done') IN ('true','false','null'),0)
      AND COALESCE(json_type(completion_json,'$.done_reason') IN ('text','null'),0)
      AND COALESCE(json_extract(completion_json,'$.public_state') IN ('PRESENT','ABSENT','OVERSIZE'),0)),
    CHECK(COALESCE((json_type(completion_json,'$.input_tokens')='null' AND json_type(completion_json,'$.output_tokens')='null')
      OR (json_type(completion_json,'$.input_tokens')='integer' AND json_type(completion_json,'$.output_tokens')='integer'
        AND typeof(json_extract(completion_json,'$.input_tokens'))='integer' AND typeof(json_extract(completion_json,'$.output_tokens'))='integer'
        AND json_extract(completion_json,'$.input_tokens')>=0 AND json_extract(completion_json,'$.output_tokens')>=0),0)),
    CHECK(COALESCE(json_type(completion_json,'$.duration_ms')='null' OR (json_type(completion_json,'$.duration_ms')='integer'
      AND typeof(json_extract(completion_json,'$.duration_ms'))='integer' AND json_extract(completion_json,'$.duration_ms')>=0),0)),
    CHECK(COALESCE(json_type(completion_json,'$.cost_microunits')='null' OR (json_type(completion_json,'$.cost_microunits')='integer'
      AND typeof(json_extract(completion_json,'$.cost_microunits'))='integer' AND json_extract(completion_json,'$.cost_microunits')>=0),0)),
    CHECK((public_wire IS NOT NULL AND json_extract(completion_json,'$.public_state') IS 'PRESENT')
      OR (public_wire IS NULL AND json_extract(completion_json,'$.public_state') IN ('ABSENT','OVERSIZE'))),
    CHECK(result_kind='REJECTED' OR (json_type(completion_json,'$.done') IS 'true'
      AND json_extract(completion_json,'$.done_reason') IS 'stop' AND public_wire IS NOT NULL AND length(public_wire)>0)),
    CHECK(result_kind!='INTELLIGENCE' OR (intelligence_id IS 'intelligence:distillation:'||execution_id AND revision_id IS 'revision:distillation:'||execution_id))
);
CREATE TRIGGER long_distillation_input_proofs_no_update BEFORE UPDATE ON long_distillation_input_proofs
BEGIN SELECT RAISE(ABORT,'long distillation provenance is immutable'); END;
CREATE TRIGGER long_distillation_input_proofs_no_delete BEFORE DELETE ON long_distillation_input_proofs
BEGIN SELECT RAISE(ABORT,'long distillation provenance is immutable'); END;
CREATE TRIGGER long_distillation_completion_receipts_no_update BEFORE UPDATE ON long_distillation_completion_receipts
BEGIN SELECT RAISE(ABORT,'long distillation provenance is immutable'); END;
CREATE TRIGGER long_distillation_completion_receipts_no_delete BEFORE DELETE ON long_distillation_completion_receipts
BEGIN SELECT RAISE(ABORT,'long distillation provenance is immutable'); END;

CREATE TRIGGER long_distillation_input_authority BEFORE INSERT ON long_distillation_input_proofs
WHEN NOT EXISTS (
 SELECT 1 FROM distillation_execution_checkpoints d
 JOIN source_subscriptions s ON s.source_id=d.source_id
 JOIN videos v ON v.video_id=d.video_id
 JOIN source_video_links l ON l.source_id=d.source_id AND l.video_id=d.video_id
 JOIN artifacts a ON a.artifact_id=NEW.canonical_artifact_id
 JOIN timed_transcripts t ON t.timed_transcript_id=NEW.timed_transcript_id
 JOIN current_content_summaries c ON c.video_id=d.video_id
 JOIN artifacts summary ON summary.artifact_id=NEW.original_summary_artifact_id
 JOIN source_policy_revisions policy ON policy.revision_id=NEW.global_policy_revision_id
 WHERE d.execution_id=NEW.execution_id AND d.source_id=NEW.source_id AND d.video_id=NEW.video_id
 AND d.status='PENDING' AND d.invocation_count=0 AND d.budget_state='RESERVED_NOT_DISPATCHED'
 AND d.intelligence_id IS NULL AND d.revision_id IS NULL AND d.selected_provider='ollama'
 AND d.use_case='PERSONALIZED_INTELLIGENCE' AND d.created_at=NEW.created_at
 AND s.provider='YOUTUBE' AND v.provider='YOUTUBE' AND v.availability='public'
 AND a.video_id=d.video_id AND a.kind='transcript_canonical' AND a.deleted_at IS NULL
 AND t.video_id=d.video_id AND t.canonical_artifact_id=a.artifact_id
 AND c.analysis_artifact_id=summary.artifact_id AND summary.video_id=d.video_id
 AND summary.kind='analysis_structured' AND summary.deleted_at IS NULL
 AND policy.policy_scope='GLOBAL' AND policy.source_id IS NULL
)
OR (NEW.source_policy_revision_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM source_policy_revisions WHERE revision_id=NEW.source_policy_revision_id AND policy_scope='SOURCE' AND source_id=NEW.source_id))
OR (SELECT COUNT(DISTINCT a.artifact_id) FROM artifacts a JOIN evidence e USING(artifact_id) WHERE a.video_id=NEW.video_id AND a.kind='transcript_canonical' AND a.deleted_at IS NULL AND e.availability='AVAILABLE' AND e.lineage_kind='ORIGINAL_TRANSCRIPT')!=1
OR EXISTS (SELECT 1 FROM evidence e LEFT JOIN artifacts a USING(artifact_id)
 LEFT JOIN evidence_text_bindings b USING(evidence_id) LEFT JOIN timed_transcripts t ON t.timed_transcript_id=b.timed_transcript_id
 WHERE e.video_id=NEW.video_id AND e.availability='AVAILABLE' AND e.lineage_kind='ORIGINAL_TRANSCRIPT' AND (
 a.artifact_id IS NULL OR a.video_id IS NOT NEW.video_id OR a.kind IS NOT 'transcript_canonical' OR a.deleted_at IS NOT NULL
 OR e.artifact_id IS NOT NEW.canonical_artifact_id OR b.evidence_id IS NULL OR b.timed_transcript_id IS NOT NEW.timed_transcript_id
 OR t.video_id IS NOT NEW.video_id OR t.canonical_artifact_id IS NOT NEW.canonical_artifact_id))
OR json_type(NEW.semantic_snapshot_wire,'$.value.evidence') IS NOT 'array'
OR (SELECT count(*) FROM json_each(NEW.semantic_snapshot_wire,'$.value.evidence')) NOT BETWEEN 1 AND 4102
OR (SELECT count(*) FROM json_each(NEW.semantic_snapshot_wire,'$.value.evidence')) != (
 SELECT count(*) FROM evidence e WHERE e.video_id=NEW.video_id
 AND e.lineage_kind='ORIGINAL_TRANSCRIPT' AND e.availability='AVAILABLE')
OR (SELECT count(*) FROM json_each(NEW.semantic_snapshot_wire,'$.value.evidence')) !=
 (SELECT count(DISTINCT json_extract(j.value,'$.evidence_id')) FROM json_each(NEW.semantic_snapshot_wire,'$.value.evidence') j)
OR EXISTS (SELECT 1 FROM json_each(NEW.semantic_snapshot_wire,'$.value.evidence') j WHERE NOT EXISTS (
 SELECT 1 FROM evidence e JOIN evidence_text_bindings b USING(evidence_id)
 WHERE e.evidence_id=json_extract(j.value,'$.evidence_id') AND e.video_id=NEW.video_id
 AND e.artifact_id=NEW.canonical_artifact_id AND e.lineage_kind='ORIGINAL_TRANSCRIPT' AND e.availability='AVAILABLE'
 AND b.timed_transcript_id=NEW.timed_transcript_id))
BEGIN SELECT RAISE(ABORT,'long proof requires complete reserved timed source'); END;
CREATE TRIGGER long_distillation_checkpoint_insert BEFORE INSERT ON distillation_execution_checkpoints
WHEN NEW.execution_id LIKE 'distillation:long-timed%' AND (
 length(NEW.execution_id)!=91 OR substr(NEW.execution_id,1,27)!='distillation:long-timed-v1:'
 OR substr(NEW.execution_id,28) GLOB '*[^0-9a-f]*' OR NEW.status!='PENDING' OR NEW.invocation_count!=0
 OR NEW.budget_state!='RESERVED_NOT_DISPATCHED' OR NEW.selected_provider!='ollama')
BEGIN SELECT RAISE(ABORT,'invalid long execution reservation'); END;
CREATE TRIGGER long_distillation_checkpoint_no_delete BEFORE DELETE ON distillation_execution_checkpoints
WHEN OLD.execution_id LIKE 'distillation:long-timed%'
BEGIN SELECT RAISE(ABORT,'long execution identity is retained'); END;
CREATE TRIGGER long_distillation_checkpoint_transition BEFORE UPDATE ON distillation_execution_checkpoints
WHEN OLD.execution_id LIKE 'distillation:long-timed%' AND (
 NOT EXISTS (SELECT 1 FROM long_distillation_input_proofs WHERE execution_id=OLD.execution_id)
 OR (NEW.invocation_count=0 AND NEW.status NOT IN ('PENDING','WAITING_MODEL','WAITING_BUDGET','REJECTED_INELIGIBLE','REJECTED_EVIDENCE'))
 OR (NEW.invocation_count=1 AND NEW.status NOT IN ('PENDING','SUCCEEDED','REJECTED_OUTPUT','AMBIGUOUS'))
 OR (NEW.invocation_count=1 AND NEW.status IN ('SUCCEEDED','REJECTED_OUTPUT') AND NOT EXISTS (
 SELECT 1 FROM long_distillation_completion_receipts r WHERE r.execution_id=OLD.execution_id AND r.terminal=NEW.status
 AND r.intelligence_id IS NEW.intelligence_id AND r.revision_id IS NEW.revision_id)))
BEGIN SELECT RAISE(ABORT,'long execution transition lacks provenance'); END;
CREATE TRIGGER long_distillation_receipt_authority BEFORE INSERT ON long_distillation_completion_receipts
WHEN NOT EXISTS (SELECT 1 FROM long_distillation_input_proofs p JOIN distillation_execution_checkpoints d USING(execution_id)
 WHERE p.execution_id=NEW.execution_id AND p.proof_hash=NEW.proof_hash AND d.status='PENDING'
 AND d.invocation_count=1 AND d.budget_state='DISPATCH_CLAIMED'
 AND (NEW.result_kind='REJECTED' OR (json_extract(NEW.completion_json,'$.actual_provider') IS d.selected_provider
 AND json_extract(NEW.completion_json,'$.actual_model') IS d.selected_model))
 AND json_extract(NEW.completion_json,'$.request_hash')=p.request_hash)
 OR EXISTS(SELECT 1 FROM distillation_waiting_model_cancellations WHERE execution_id=NEW.execution_id)
BEGIN SELECT RAISE(ABORT,'long receipt requires its claimed input'); END;
CREATE TRIGGER long_distillation_cancel_authority BEFORE INSERT ON distillation_waiting_model_cancellations
WHEN NEW.execution_id LIKE 'distillation:long-timed%' AND (
 NOT EXISTS(SELECT 1 FROM long_distillation_input_proofs WHERE execution_id=NEW.execution_id)
 OR EXISTS(SELECT 1 FROM long_distillation_completion_receipts WHERE execution_id=NEW.execution_id))
BEGIN SELECT RAISE(ABORT,'long cancellation requires only input provenance'); END;
CREATE TRIGGER long_distillation_zero_authority BEFORE INSERT ON distillation_no_new_intelligence_results
WHEN NEW.execution_id LIKE 'distillation:long-timed%' AND NOT EXISTS (
 SELECT 1 FROM long_distillation_completion_receipts WHERE execution_id=NEW.execution_id AND no_new_execution_id=NEW.execution_id AND result_kind='NO_NEW_INTELLIGENCE')
BEGIN SELECT RAISE(ABORT,'long zero requires completion receipt'); END;
CREATE TRIGGER long_distillation_card_authority BEFORE INSERT ON distillation_cards
WHEN NEW.revision_id LIKE 'revision:distillation:distillation:long-timed%' AND NOT EXISTS (
 SELECT 1 FROM long_distillation_completion_receipts WHERE revision_id=NEW.revision_id AND result_kind='INTELLIGENCE')
BEGIN SELECT RAISE(ABORT,'long card requires completion receipt'); END;
CREATE TRIGGER long_distillation_completion_safe_shape BEFORE INSERT ON long_distillation_completion_receipts
WHEN (SELECT count(*) FROM json_each(NEW.completion_json))!=10
 OR EXISTS(SELECT 1 FROM json_each(NEW.completion_json) WHERE key NOT IN ('done','done_reason','actual_provider','actual_model','request_hash','input_tokens','output_tokens','cost_microunits','duration_ms','public_state'))
BEGIN SELECT RAISE(ABORT,'long completion contains unexpected metadata'); END;
CREATE TRIGGER long_distillation_usage_authority BEFORE INSERT ON distillation_resource_usage
WHEN NEW.execution_id LIKE 'distillation:long-timed%' AND NEW.invocation_count=1 AND NEW.status!='AMBIGUOUS' AND NOT EXISTS (
 SELECT 1 FROM long_distillation_completion_receipts r JOIN distillation_execution_checkpoints d USING(execution_id)
 WHERE r.execution_id=NEW.execution_id AND d.source_id=NEW.source_id AND d.video_id=NEW.video_id
 AND d.reason=NEW.reason AND d.use_case=NEW.use_case AND d.selected_provider=NEW.selected_provider AND d.selected_model=NEW.selected_model
 AND r.intelligence_id IS NEW.intelligence_id AND r.revision_id IS NEW.revision_id AND r.created_at=NEW.created_at
 AND NEW.status=CASE WHEN r.result_kind='NO_NEW_INTELLIGENCE' THEN 'SUCCEEDED' ELSE r.terminal END
 AND NEW.actual_provider IS json_extract(r.completion_json,'$.actual_provider')
 AND NEW.actual_model IS json_extract(r.completion_json,'$.actual_model')
 AND NEW.input_tokens IS json_extract(r.completion_json,'$.input_tokens')
 AND NEW.output_tokens IS json_extract(r.completion_json,'$.output_tokens')
 AND NEW.cost_microunits IS json_extract(r.completion_json,'$.cost_microunits')
 AND NEW.duration_ms IS json_extract(r.completion_json,'$.duration_ms')
 AND (r.result_kind!='NO_NEW_INTELLIGENCE' OR NEW.outcome='NO_NEW_INTELLIGENCE'))
BEGIN SELECT RAISE(ABORT,'long observed usage differs from completion receipt'); END;
CREATE TRIGGER long_distillation_zero_metadata BEFORE INSERT ON distillation_no_new_intelligence_results
WHEN NEW.execution_id LIKE 'distillation:long-timed%' AND NOT EXISTS (
 SELECT 1 FROM long_distillation_completion_receipts r WHERE r.execution_id=NEW.execution_id
 AND r.created_at=NEW.created_at AND NEW.actual_provider IS json_extract(r.completion_json,'$.actual_provider')
 AND NEW.actual_model IS json_extract(r.completion_json,'$.actual_model')
 AND NEW.input_tokens IS json_extract(r.completion_json,'$.input_tokens')
 AND NEW.output_tokens IS json_extract(r.completion_json,'$.output_tokens')
 AND NEW.cost_microunits IS json_extract(r.completion_json,'$.cost_microunits')
 AND NEW.duration_ms IS json_extract(r.completion_json,'$.duration_ms'))
BEGIN SELECT RAISE(ABORT,'long zero metadata differs from completion receipt'); END;
