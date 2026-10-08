-- Summary EXTRACTION spans are preserved but do not enter canonical Intelligence input.
DROP TRIGGER distillation_no_new_result_requires_claimed_checkpoint;
CREATE TRIGGER distillation_no_new_result_requires_claimed_checkpoint
BEFORE INSERT ON distillation_no_new_intelligence_results
WHEN NOT EXISTS (
    SELECT 1
    FROM distillation_execution_checkpoints AS checkpoint
    WHERE checkpoint.execution_id = NEW.execution_id
      AND checkpoint.source_id = NEW.source_id
      AND checkpoint.video_id = NEW.video_id
      AND checkpoint.reason = NEW.reason
      AND checkpoint.use_case = NEW.use_case
      AND checkpoint.status = 'PENDING'
      AND checkpoint.invocation_count = 1
      AND checkpoint.intelligence_id IS NULL
      AND checkpoint.revision_id IS NULL
      AND checkpoint.selected_provider = NEW.actual_provider
      AND checkpoint.selected_model = NEW.actual_model
)
 OR json_array_length(NEW.evidence_ids_json) = 0
 OR EXISTS (
    SELECT 1 FROM json_each(NEW.evidence_ids_json) AS cited
    WHERE cited.type != 'text'
 )
 OR (SELECT COUNT(*) FROM json_each(NEW.evidence_ids_json)) != (
    SELECT COUNT(DISTINCT cited.value)
    FROM json_each(NEW.evidence_ids_json) AS cited
 )
 OR EXISTS (
    SELECT 1
    FROM json_each(NEW.evidence_ids_json) AS cited
    WHERE NOT EXISTS (
        SELECT 1
        FROM evidence
        JOIN artifacts ON artifacts.artifact_id = evidence.artifact_id
        WHERE evidence.evidence_id = cited.value
          AND evidence.video_id = NEW.video_id
          AND evidence.availability = 'AVAILABLE'
      AND evidence.lineage_kind = 'ORIGINAL_TRANSCRIPT'
          AND artifacts.video_id = NEW.video_id
          AND artifacts.deleted_at IS NULL
          AND artifacts.kind = 'transcript_canonical'
    )
 )
 OR (SELECT COUNT(*) FROM json_each(NEW.evidence_ids_json)) != (
    SELECT COUNT(*)
    FROM evidence
    JOIN artifacts ON artifacts.artifact_id = evidence.artifact_id
    WHERE evidence.video_id = NEW.video_id
      AND evidence.availability = 'AVAILABLE'
      AND evidence.lineage_kind = 'ORIGINAL_TRANSCRIPT'
      AND artifacts.video_id = NEW.video_id
      AND artifacts.deleted_at IS NULL
      AND artifacts.kind = 'transcript_canonical'
 )
BEGIN
    SELECT RAISE(ABORT, 'no-new Intelligence result requires one invocation and the exact canonical Evidence set');
END;
