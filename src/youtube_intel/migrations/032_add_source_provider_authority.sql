-- Phase 7: provider-neutral snapshot and locator authority. Rebuild with FK checks before commit.
CREATE TABLE source_subscriptions_v32 (
    provider TEXT NOT NULL DEFAULT 'YOUTUBE' CHECK (provider IN ('YOUTUBE','LOCAL')),
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
        OR (source_type = 'VIDEO_URL' AND provider = 'YOUTUBE' AND video_id IS NOT NULL)
    )
);
INSERT INTO source_subscriptions_v32 (source_id,source_type,canonical_url,channel_id,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,last_error_code,last_error_message,created_at,updated_at) SELECT source_id,source_type,canonical_url,channel_id,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,last_error_code,last_error_message,created_at,updated_at FROM source_subscriptions;
DROP TABLE source_subscriptions;
ALTER TABLE source_subscriptions_v32 RENAME TO source_subscriptions;
CREATE INDEX idx_source_subscriptions_enabled ON source_subscriptions(enabled,updated_at);
CREATE TABLE evidence_v32 (
    evidence_id TEXT PRIMARY KEY CHECK (length(trim(evidence_id)) > 0),
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    locator_type TEXT NOT NULL DEFAULT 'TIMED_MEDIA' CHECK (locator_type IN ('TIMED_MEDIA','TEXT_RANGE')),
    start_offset INTEGER,
    end_offset INTEGER,
    start_ms INTEGER CHECK (start_ms >= 0),
    end_ms INTEGER CHECK (end_ms >= start_ms),
    lineage_kind TEXT NOT NULL CHECK (lineage_kind IN ('ORIGINAL_TRANSCRIPT', 'TRANSLATION', 'EXTRACTION')),
    role TEXT NOT NULL CHECK (role IN ('PRIMARY_ORIGINAL', 'INDEPENDENT_VERIFICATION', 'ANALYSIS_COMMENTARY', 'SECONDARY_RELAY')),
    language TEXT NOT NULL CHECK (length(trim(language)) > 0),
    availability TEXT NOT NULL CHECK (availability IN ('AVAILABLE', 'UNAVAILABLE', 'DELETED')),
    created_at TEXT NOT NULL,
    source_excerpt TEXT CHECK (source_excerpt IS NULL OR (length(trim(source_excerpt)) > 0 AND length(source_excerpt) <= 4000)),
    CHECK ((locator_type='TIMED_MEDIA' AND start_ms IS NOT NULL AND end_ms IS NOT NULL AND start_offset IS NULL AND end_offset IS NULL)
       OR (locator_type='TEXT_RANGE' AND start_ms IS NULL AND end_ms IS NULL AND start_offset IS NOT NULL AND end_offset IS NOT NULL AND start_offset >= 0 AND end_offset > start_offset))
);
INSERT INTO evidence_v32 (evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at,source_excerpt) SELECT evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at,source_excerpt FROM evidence;
DROP TABLE evidence;
ALTER TABLE evidence_v32 RENAME TO evidence;
CREATE INDEX idx_evidence_video_availability ON evidence(video_id, availability, evidence_id);

CREATE TRIGGER evidence_artifact_must_belong_to_video
BEFORE INSERT ON evidence
WHEN NOT EXISTS (
    SELECT 1 FROM artifacts
    WHERE artifact_id = NEW.artifact_id
      AND video_id = NEW.video_id
      AND deleted_at IS NULL
)
BEGIN
    SELECT RAISE(ABORT, 'evidence artifact provenance is unavailable or mismatched');
END;

CREATE TRIGGER evidence_immutable_content
BEFORE UPDATE ON evidence
WHEN NEW.evidence_id IS NOT OLD.evidence_id
  OR NEW.video_id IS NOT OLD.video_id
  OR NEW.artifact_id IS NOT OLD.artifact_id
  OR NEW.locator_type IS NOT OLD.locator_type
  OR NEW.start_offset IS NOT OLD.start_offset
  OR NEW.end_offset IS NOT OLD.end_offset
  OR NEW.start_ms IS NOT OLD.start_ms
  OR NEW.end_ms IS NOT OLD.end_ms
  OR NEW.lineage_kind IS NOT OLD.lineage_kind
  OR NEW.role IS NOT OLD.role
  OR NEW.language IS NOT OLD.language
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'evidence material is immutable');
END;

CREATE TRIGGER evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'evidence deletion requires dependency impact handling');
END;

CREATE UNIQUE INDEX uq_evidence_timed ON evidence(artifact_id,start_ms,end_ms,lineage_kind,role) WHERE locator_type='TIMED_MEDIA';
CREATE UNIQUE INDEX uq_evidence_text ON evidence(artifact_id,start_offset,end_offset,lineage_kind,role) WHERE locator_type='TEXT_RANGE';
CREATE TRIGGER evidence_source_excerpt_immutable BEFORE UPDATE OF source_excerpt ON evidence WHEN NEW.source_excerpt IS NOT OLD.source_excerpt BEGIN SELECT RAISE(ABORT,'evidence source excerpt is immutable'); END;

ALTER TABLE videos ADD COLUMN provider TEXT NOT NULL DEFAULT 'YOUTUBE' CHECK (provider IN ('YOUTUBE','LOCAL'));
CREATE TABLE content_source_snapshots (
    content_id TEXT PRIMARY KEY REFERENCES videos(video_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    provider TEXT NOT NULL CHECK (provider IN ('YOUTUBE','LOCAL')),
    source_identity TEXT NOT NULL,
    source_hash TEXT NOT NULL CHECK (length(source_hash)=64 AND source_hash NOT GLOB '*[^0-9a-f]*'),
    snapshot_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    filename TEXT NOT NULL,
    format TEXT NOT NULL,
    media_kind TEXT NOT NULL CHECK (media_kind IN ('TEXT','AUDIO','VIDEO')),
    byte_count INTEGER NOT NULL CHECK (byte_count>0 AND byte_count<=67108864),
    imported_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('IMPORTED','READY','TRANSCRIPTION_UNAVAILABLE','TRANSCRIPTION_FAILED','FAILED')),
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
CREATE TRIGGER source_snapshot_identity_immutable BEFORE UPDATE ON content_source_snapshots
WHEN NEW.content_id IS NOT OLD.content_id OR NEW.source_id IS NOT OLD.source_id OR NEW.provider IS NOT OLD.provider
 OR NEW.source_identity IS NOT OLD.source_identity OR NEW.source_hash IS NOT OLD.source_hash
 OR NEW.snapshot_artifact_id IS NOT OLD.snapshot_artifact_id OR NEW.filename IS NOT OLD.filename
 OR NEW.format IS NOT OLD.format OR NEW.media_kind IS NOT OLD.media_kind OR NEW.byte_count IS NOT OLD.byte_count
 OR NEW.imported_at IS NOT OLD.imported_at OR OLD.status='READY'
BEGIN SELECT RAISE(ABORT,'source snapshot authority is immutable'); END;
CREATE TRIGGER source_snapshot_no_delete BEFORE DELETE ON content_source_snapshots BEGIN SELECT RAISE(ABORT,'source snapshot deletion requires dependency impact handling'); END;
CREATE TABLE evidence_source_ranges (
    evidence_id TEXT PRIMARY KEY REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    canonical_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    excerpt TEXT NOT NULL,
    excerpt_hash TEXT NOT NULL,
    source_text_hash TEXT NOT NULL,
    source_content_hash TEXT NOT NULL
);
CREATE TRIGGER evidence_source_ranges_immutable_update BEFORE UPDATE ON evidence_source_ranges BEGIN SELECT RAISE(ABORT,'source ranges are immutable'); END;
CREATE TRIGGER evidence_source_ranges_immutable_delete BEFORE DELETE ON evidence_source_ranges BEGIN SELECT RAISE(ABORT,'source ranges are immutable'); END;
CREATE VIEW evidence_search_text AS SELECT evidence_id,excerpt FROM evidence_text_bindings UNION ALL SELECT evidence_id,excerpt FROM evidence_source_ranges;

-- Preserve current-Intelligence dependency protection verbatim from M006.
CREATE TRIGGER evidence_availability_requires_no_current_support
BEFORE UPDATE OF availability ON evidence
WHEN EXISTS (
    SELECT 1
    FROM intelligence_revision_evidence AS link
    JOIN intelligences ON intelligences.current_revision_id = link.revision_id
    WHERE link.evidence_id = OLD.evidence_id
)
BEGIN
    SELECT RAISE(ABORT, 'current intelligence support must be resolved before evidence availability changes');
END;

CREATE TRIGGER video_provider_identity_immutable BEFORE UPDATE OF provider ON videos
WHEN NEW.provider IS NOT OLD.provider BEGIN SELECT RAISE(ABORT,'Content provider identity is immutable'); END;
CREATE TRIGGER following_provider_identity_immutable BEFORE UPDATE OF provider ON source_subscriptions
WHEN NEW.provider IS NOT OLD.provider BEGIN SELECT RAISE(ABORT,'Following provider identity is immutable'); END;
CREATE TRIGGER source_snapshot_ownership BEFORE INSERT ON content_source_snapshots
WHEN NOT EXISTS (SELECT 1 FROM videos v JOIN source_video_links l USING(video_id) JOIN source_subscriptions s USING(source_id) JOIN artifacts a ON a.artifact_id=NEW.snapshot_artifact_id WHERE v.video_id=NEW.content_id AND l.source_id=NEW.source_id AND v.provider=NEW.provider AND s.provider=NEW.provider AND a.video_id=v.video_id AND a.storage_root='DATA' AND a.deleted_at IS NULL AND a.provider=NEW.provider AND a.content_hash=NEW.source_hash)
BEGIN SELECT RAISE(ABORT,'source snapshot ownership is mismatched'); END;
