-- M4C: make Evidence excerpts and Intelligence-relative stance explicit without
-- reinterpreting historical rows. Existing rows remain NULL by design.

ALTER TABLE evidence
ADD COLUMN source_excerpt TEXT
CHECK (
    source_excerpt IS NULL
    OR (
        length(trim(source_excerpt)) > 0
        AND length(source_excerpt) <= 4000
    )
);

ALTER TABLE intelligence_revision_evidence
ADD COLUMN stance TEXT
CHECK (
    stance IS NULL
    OR stance IN ('supporting', 'contradicting', 'conditional')
);

CREATE TRIGGER evidence_source_excerpt_immutable
BEFORE UPDATE OF source_excerpt ON evidence
WHEN NEW.source_excerpt IS NOT OLD.source_excerpt
BEGIN
    SELECT RAISE(ABORT, 'evidence source excerpt is immutable');
END;

CREATE TRIGGER revision_evidence_immutable_update
BEFORE UPDATE ON intelligence_revision_evidence
BEGIN
    SELECT RAISE(ABORT, 'revision evidence links are immutable');
END;
