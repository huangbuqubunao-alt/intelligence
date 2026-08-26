-- TASK-016C Phase H2-C: authoritative scoring lineage (schema v2).
--
-- Adds the durable Video -> scoring Job -> structured Artifact authority
-- chain plus the immutable scoring-lineage generation discriminator.
-- Migration performs no data UPDATE: every existing row remains the
-- pre-lineage generation (NULL) forever.

ALTER TABLE videos ADD COLUMN authoritative_scoring_job_id TEXT NULL
    REFERENCES jobs(job_id) ON DELETE RESTRICT;

ALTER TABLE jobs ADD COLUMN authoritative_scoring_artifact_key TEXT NULL
    REFERENCES artifacts(artifact_key) ON DELETE RESTRICT;
ALTER TABLE jobs ADD COLUMN scoring_success_provenance TEXT NULL
    CHECK (scoring_success_provenance IS NULL
           OR scoring_success_provenance IN ('PRIMARY', 'REPAIR_H2C'));
ALTER TABLE jobs ADD COLUMN scoring_lineage_version TEXT NULL
    CHECK (scoring_lineage_version IS NULL
           OR scoring_lineage_version = 'task016c-scoring-lineage-v1');

CREATE UNIQUE INDEX uq_jobs_authoritative_scoring_artifact_key
    ON jobs(authoritative_scoring_artifact_key)
    WHERE authoritative_scoring_artifact_key IS NOT NULL;
CREATE UNIQUE INDEX uq_videos_authoritative_scoring_job_id
    ON videos(authoritative_scoring_job_id)
    WHERE authoritative_scoring_job_id IS NOT NULL;
