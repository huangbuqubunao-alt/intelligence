-- Seal generation-time output language on each Distillation execution.
-- Historical executions stay NULL because their language was never recorded.

ALTER TABLE distillation_execution_checkpoints
ADD COLUMN output_language TEXT
CHECK (output_language IS NULL OR output_language IN ('zh-CN', 'en'));

CREATE UNIQUE INDEX distillation_one_pending_reservation_per_content
ON distillation_execution_checkpoints
    (source_id, video_id, selected_provider, selected_model)
WHERE status = 'PENDING'
  AND budget_state = 'RESERVED_NOT_DISPATCHED'
  AND invocation_count = 0;

CREATE TRIGGER distillation_checkpoint_language_immutable
BEFORE UPDATE ON distillation_execution_checkpoints
WHEN NEW.output_language IS NOT OLD.output_language
BEGIN
    SELECT RAISE(ABORT, 'distillation output language is immutable');
END;
