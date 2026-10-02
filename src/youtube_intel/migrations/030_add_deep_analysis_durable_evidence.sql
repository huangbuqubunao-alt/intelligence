-- V1.x Phase 1B. Ordinal 029 is reserved for M13's in-flight model settings.
-- Legacy rows are deliberately not backfilled or upgraded to citation authority.
ALTER TABLE deep_analysis_persisted_results ADD COLUMN persistence_version TEXT
    NOT NULL DEFAULT 'deep-analysis-persistence-v1';
ALTER TABLE deep_analysis_persisted_results ADD COLUMN durable_authority_identity TEXT;

CREATE TABLE deep_analysis_evidence (
    result_identity TEXT NOT NULL REFERENCES deep_analysis_persisted_results(result_identity),
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (result_identity, evidence_id)
);
CREATE INDEX idx_deep_analysis_evidence_evidence_id
    ON deep_analysis_evidence(evidence_id);
