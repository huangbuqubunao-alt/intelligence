-- Phase 10B: extend existing provider authority; no parallel Bilibili domain.
-- Applied atomically with foreign keys disabled outside BEGIN, then fully checked.

CREATE TABLE videos_v33 (
    video_id TEXT PRIMARY KEY CHECK (length(trim(video_id)) > 0),
    channel_id TEXT NOT NULL CHECK (length(trim(channel_id)) > 0),
    channel_name TEXT,
    title TEXT,
    description TEXT,
    source_url TEXT,
    published_at TEXT,
    duration_seconds INTEGER CHECK (
        duration_seconds IS NULL OR duration_seconds >= 0
    ),
    default_language TEXT,
    available_languages_json TEXT NOT NULL DEFAULT '[]',
    live_status TEXT CHECK (
        live_status IS NULL OR live_status IN ('none', 'upcoming', 'live', 'ended')
    ),
    availability TEXT CHECK (
        availability IS NULL
        OR availability IN ('public', 'unavailable', 'private', 'deleted', 'restricted')
    ),
    pipeline_status TEXT NOT NULL CHECK (
        pipeline_status IN (
            'DISCOVERED',
            'METADATA_READY',
            'DEFERRED',
            'TRANSCRIPT_READY',
            'SCORED',
            'LOW_VALUE_READY',
            'ANALYSIS_READY',
            'NOTE_WRITTEN',
            'COMPLETE',
            'SKIPPED_DURATION_LIMIT'
        )
    ),
    pipeline_version TEXT NOT NULL CHECK (length(trim(pipeline_version)) > 0),
    score REAL CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
    should_summarize INTEGER CHECK (should_summarize IS NULL OR should_summarize IN (0, 1)),
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
, authoritative_scoring_job_id TEXT NULL
    REFERENCES jobs(job_id) ON DELETE RESTRICT, provider TEXT NOT NULL DEFAULT 'YOUTUBE' CHECK (provider IN ('YOUTUBE','LOCAL','BILIBILI')));

INSERT INTO videos_v33 (video_id,channel_id,channel_name,title,description,source_url,published_at,duration_seconds,default_language,available_languages_json,live_status,availability,pipeline_status,pipeline_version,score,should_summarize,discovered_at,updated_at,completed_at,authoritative_scoring_job_id,provider) SELECT video_id,channel_id,channel_name,title,description,source_url,published_at,duration_seconds,default_language,available_languages_json,live_status,availability,pipeline_status,pipeline_version,score,should_summarize,discovered_at,updated_at,completed_at,authoritative_scoring_job_id,provider FROM videos;

DROP TABLE videos;

ALTER TABLE videos_v33 RENAME TO videos;

CREATE INDEX idx_videos_availability_updated
    ON videos(availability, updated_at);

CREATE INDEX idx_videos_channel_published
    ON videos(channel_id, published_at, video_id);

CREATE INDEX idx_videos_pipeline_updated
    ON videos(pipeline_status, updated_at);

CREATE UNIQUE INDEX uq_videos_authoritative_scoring_job_id
    ON videos(authoritative_scoring_job_id)
    WHERE authoritative_scoring_job_id IS NOT NULL;

CREATE TRIGGER content_with_current_summary_restrict_delete
BEFORE DELETE ON videos
WHEN EXISTS (
    SELECT 1 FROM current_content_summaries WHERE video_id = OLD.video_id
)
BEGIN
    SELECT RAISE(ABORT, 'Content has an authoritative current Summary');
END;

CREATE TRIGGER video_provider_identity_immutable BEFORE UPDATE OF provider ON videos
WHEN NEW.provider IS NOT OLD.provider BEGIN SELECT RAISE(ABORT,'Content provider identity is immutable'); END;

CREATE TRIGGER video_unavailability_requires_no_current_evidence
BEFORE UPDATE OF availability ON videos
WHEN NEW.availability IN ('unavailable', 'private', 'deleted', 'restricted')
 AND EXISTS (
    SELECT 1
    FROM evidence
    JOIN intelligence_revision_evidence AS link ON link.evidence_id = evidence.evidence_id
    JOIN intelligences ON intelligences.current_revision_id = link.revision_id
    WHERE evidence.video_id = OLD.video_id
 )
BEGIN
    SELECT RAISE(ABORT, 'video availability requires current intelligence impact handling');
END;

CREATE TABLE source_subscriptions_v33 (
    provider TEXT NOT NULL DEFAULT 'YOUTUBE' CHECK (provider IN ('YOUTUBE','LOCAL','BILIBILI')),
    source_id TEXT PRIMARY KEY CHECK (length(trim(source_id)) > 0),
    source_type TEXT NOT NULL CHECK (source_type IN ('CHANNEL', 'VIDEO_URL', 'LOCAL_LIBRARY')),
    canonical_url TEXT NOT NULL UNIQUE CHECK (length(trim(canonical_url)) > 0),
    channel_id TEXT CHECK (channel_id IS NULL OR length(trim(channel_id)) > 0),
    video_id TEXT CHECK (video_id IS NULL OR length(trim(video_id)) > 0),
    display_name TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    processing_policy TEXT NOT NULL CHECK (
        processing_policy IN ('DISCOVER_ONLY', 'STANDARD_INTELLIGENCE', 'FULL_INTELLIGENCE')
    ),
    last_checked_at TEXT,
    last_success_at TEXT,
    last_error_code TEXT,
    last_error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (source_type = 'LOCAL_LIBRARY' AND provider = 'LOCAL' AND channel_id IS NULL AND video_id IS NULL AND canonical_url = 'local:library')
        OR (source_type = 'CHANNEL' AND provider = 'YOUTUBE' AND video_id IS NULL)
        OR (source_type = 'VIDEO_URL' AND provider IN ('YOUTUBE','BILIBILI') AND video_id IS NOT NULL)
    )
);

INSERT INTO source_subscriptions_v33 (provider,source_id,source_type,canonical_url,channel_id,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,last_error_code,last_error_message,created_at,updated_at) SELECT provider,source_id,source_type,canonical_url,channel_id,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,last_error_code,last_error_message,created_at,updated_at FROM source_subscriptions;

DROP TABLE source_subscriptions;

ALTER TABLE source_subscriptions_v33 RENAME TO source_subscriptions;

CREATE INDEX idx_source_subscriptions_enabled ON source_subscriptions(enabled,updated_at);

CREATE TRIGGER following_provider_identity_immutable BEFORE UPDATE OF provider ON source_subscriptions
WHEN NEW.provider IS NOT OLD.provider BEGIN SELECT RAISE(ABORT,'Following provider identity is immutable'); END;

CREATE TABLE content_source_snapshots_v33 (
    content_id TEXT PRIMARY KEY REFERENCES videos(video_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    provider TEXT NOT NULL CHECK (provider IN ('YOUTUBE','LOCAL','BILIBILI')),
    source_identity TEXT NOT NULL,
    source_hash TEXT NOT NULL CHECK (length(source_hash)=64 AND source_hash NOT GLOB '*[^0-9a-f]*'),
    snapshot_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    filename TEXT NOT NULL,
    format TEXT NOT NULL,
    media_kind TEXT NOT NULL CHECK (media_kind IN ('TEXT','AUDIO','VIDEO')),
    byte_count INTEGER NOT NULL CHECK (byte_count>0 AND byte_count<=67108864),
    imported_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('IMPORTED','READY','TRANSCRIPTION_UNAVAILABLE','TRANSCRIPTION_FAILED','FAILED','CAPTION_UNAVAILABLE','CAPTION_INVALID','NETWORK_UNAVAILABLE','ACCESS_DENIED','RATE_LIMITED','NOT_FOUND')),
    canonical_artifact_id TEXT REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    canonical_text TEXT,
    canonical_text_hash TEXT,
    language TEXT,
    duration_seconds REAL,
    transcript_provenance TEXT,
    provenance_artifact_id TEXT REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    CHECK ((status!='READY') OR (canonical_artifact_id IS NOT NULL AND canonical_text IS NOT NULL AND canonical_text_hash IS NOT NULL AND language IS NOT NULL AND transcript_provenance IS NOT NULL)),
    CHECK (status!='READY' OR media_kind='TEXT' OR provenance_artifact_id IS NOT NULL),
    CHECK (media_kind!='TEXT' OR byte_count<=2097152),
    CHECK (duration_seconds IS NULL OR (duration_seconds>0 AND duration_seconds<=7200)),
    UNIQUE(provider,source_identity)
);

INSERT INTO content_source_snapshots_v33 (content_id,source_id,provider,source_identity,source_hash,snapshot_artifact_id,filename,format,media_kind,byte_count,imported_at,status,canonical_artifact_id,canonical_text,canonical_text_hash,language,duration_seconds,transcript_provenance,provenance_artifact_id) SELECT content_id,source_id,provider,source_identity,source_hash,snapshot_artifact_id,filename,format,media_kind,byte_count,imported_at,status,canonical_artifact_id,canonical_text,canonical_text_hash,language,duration_seconds,transcript_provenance,provenance_artifact_id FROM content_source_snapshots;

DROP TABLE content_source_snapshots;

ALTER TABLE content_source_snapshots_v33 RENAME TO content_source_snapshots;

CREATE TRIGGER source_snapshot_identity_immutable BEFORE UPDATE ON content_source_snapshots
WHEN NEW.content_id IS NOT OLD.content_id OR NEW.source_id IS NOT OLD.source_id OR NEW.provider IS NOT OLD.provider
 OR NEW.source_identity IS NOT OLD.source_identity OR NEW.source_hash IS NOT OLD.source_hash
 OR NEW.snapshot_artifact_id IS NOT OLD.snapshot_artifact_id OR NEW.filename IS NOT OLD.filename
 OR NEW.format IS NOT OLD.format OR NEW.media_kind IS NOT OLD.media_kind OR NEW.byte_count IS NOT OLD.byte_count
 OR NEW.imported_at IS NOT OLD.imported_at OR OLD.status='READY'
BEGIN SELECT RAISE(ABORT,'source snapshot authority is immutable'); END;

CREATE TRIGGER source_snapshot_no_delete BEFORE DELETE ON content_source_snapshots BEGIN SELECT RAISE(ABORT,'source snapshot deletion requires dependency impact handling'); END;

CREATE TRIGGER source_snapshot_ownership BEFORE INSERT ON content_source_snapshots
WHEN NOT EXISTS (SELECT 1 FROM videos v JOIN source_video_links l USING(video_id) JOIN source_subscriptions s USING(source_id) JOIN artifacts a ON a.artifact_id=NEW.snapshot_artifact_id WHERE v.video_id=NEW.content_id AND l.source_id=NEW.source_id AND v.provider=NEW.provider AND s.provider=NEW.provider AND a.video_id=v.video_id AND a.storage_root='DATA' AND a.deleted_at IS NULL AND a.provider=NEW.provider AND a.content_hash=NEW.source_hash)
BEGIN SELECT RAISE(ABORT,'source snapshot ownership is mismatched'); END;
