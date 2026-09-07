-- TASK-018A: durable, revision-specific claim classification.
-- Existing m006 revisions cannot be classified safely; retain UNCLASSIFIED only
-- as a migration sentinel and prohibit it for all future inserts.

ALTER TABLE intelligence_revisions
    ADD COLUMN claim_kind TEXT NOT NULL DEFAULT 'UNCLASSIFIED'
    CHECK (claim_kind IN (
        'UNCLASSIFIED',
        'FACT',
        'EVIDENCE_BACKED_STATEMENT',
        'OPINION',
        'PREDICTION',
        'RUMOR',
        'SYSTEM_INFERENCE'
    ));

CREATE TRIGGER intelligence_revision_new_claim_kind_must_be_classified
BEFORE INSERT ON intelligence_revisions
WHEN NEW.claim_kind = 'UNCLASSIFIED'
BEGIN
    SELECT RAISE(ABORT, 'new intelligence revisions require an explicit claim kind');
END;
