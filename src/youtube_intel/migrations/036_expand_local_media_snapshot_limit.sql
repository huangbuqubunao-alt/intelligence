-- D2-02 owner-approved narrow migration. Copy every authority field unchanged.
CREATE TABLE content_source_snapshots_v36 (
    content_id TEXT PRIMARY KEY REFERENCES videos(video_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    provider TEXT NOT NULL CHECK (provider IN ('YOUTUBE','LOCAL','BILIBILI')),
    source_identity TEXT NOT NULL,
    source_hash TEXT NOT NULL CHECK (length(source_hash)=64 AND source_hash NOT GLOB '*[^0-9a-f]*'),
    snapshot_artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE RESTRICT,
    filename TEXT NOT NULL,
    format TEXT NOT NULL,
    media_kind TEXT NOT NULL CHECK (media_kind IN ('TEXT','AUDIO','VIDEO')),
    byte_count INTEGER NOT NULL CHECK (byte_count>0 AND byte_count<=CASE WHEN provider='LOCAL' AND media_kind IN ('AUDIO','VIDEO') THEN 2147483648 ELSE 67108864 END),
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

INSERT INTO content_source_snapshots_v36 (content_id,source_id,provider,source_identity,source_hash,snapshot_artifact_id,filename,format,media_kind,byte_count,imported_at,status,canonical_artifact_id,canonical_text,canonical_text_hash,language,duration_seconds,transcript_provenance,provenance_artifact_id) SELECT content_id,source_id,provider,source_identity,source_hash,snapshot_artifact_id,filename,format,media_kind,byte_count,imported_at,status,canonical_artifact_id,canonical_text,canonical_text_hash,language,duration_seconds,transcript_provenance,provenance_artifact_id FROM content_source_snapshots;

DROP TABLE content_source_snapshots;

ALTER TABLE content_source_snapshots_v36 RENAME TO content_source_snapshots;

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
