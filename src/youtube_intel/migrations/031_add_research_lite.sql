-- Phase 4: separate Research identity and append-only executions. No History UX.
-- Deferred composite pointer permits atomic first creation and forbids cross-item pointers.
CREATE TABLE research_items (
    research_id TEXT PRIMARY KEY CHECK (length(research_id) = 64),
    question TEXT NOT NULL CHECK (length(trim(question)) BETWEEN 1 AND 2000),
    scope_json TEXT NOT NULL CHECK (json_valid(scope_json) AND json_type(scope_json) = 'array'),
    output_language TEXT NOT NULL CHECK (output_language IN ('zh-CN', 'en')),
    contract TEXT NOT NULL CHECK (contract = 'research-lite-v1'),
    current_result_identity TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (research_id, current_result_identity)
        REFERENCES research_results(research_id, result_identity) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE research_results (
    result_identity TEXT PRIMARY KEY CHECK (length(result_identity) = 64),
    research_id TEXT NOT NULL REFERENCES research_items(research_id),
    execution_id TEXT NOT NULL UNIQUE CHECK (length(execution_id) = 32),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64),
    assembled_at TEXT NOT NULL,
    execution_number INTEGER NOT NULL CHECK (execution_number > 0),
    UNIQUE (research_id, execution_number),
    UNIQUE (research_id, result_identity)
);
CREATE INDEX idx_research_results_item ON research_results(research_id, result_identity);
CREATE INDEX idx_research_items_created ON research_items(created_at DESC, research_id);

CREATE TRIGGER research_results_immutable_update BEFORE UPDATE ON research_results
BEGIN SELECT RAISE(ABORT, 'Research execution is immutable'); END;
CREATE TRIGGER research_results_immutable_delete BEFORE DELETE ON research_results
BEGIN SELECT RAISE(ABORT, 'Research execution is immutable'); END;
CREATE TRIGGER research_items_identity_immutable BEFORE UPDATE ON research_items
WHEN NEW.research_id IS NOT OLD.research_id OR NEW.question IS NOT OLD.question
    OR NEW.scope_json IS NOT OLD.scope_json OR NEW.output_language IS NOT OLD.output_language
    OR NEW.contract IS NOT OLD.contract OR NEW.created_at IS NOT OLD.created_at
BEGIN SELECT RAISE(ABORT, 'Research semantic identity is immutable'); END;
CREATE TRIGGER research_items_immutable_delete BEFORE DELETE ON research_items
BEGIN SELECT RAISE(ABORT, 'Research identity is immutable'); END;
