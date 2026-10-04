-- Generalized portable source tracking; no historical migration changes.
CREATE TABLE source_subscriptions_v34 (
    provider TEXT NOT NULL DEFAULT 'YOUTUBE' CHECK (provider IN ('YOUTUBE','LOCAL','BILIBILI')),
    source_id TEXT PRIMARY KEY CHECK (length(trim(source_id)) > 0),
    source_type TEXT NOT NULL CHECK (source_type IN ('CHANNEL', 'VIDEO_URL', 'LOCAL_LIBRARY', 'CREATOR')),
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
        OR (source_type = 'CREATOR' AND provider = 'BILIBILI' AND channel_id IS NOT NULL AND video_id IS NULL AND source_id = 'bilibili-creator-' || channel_id AND canonical_url = 'https://space.bilibili.com/' || channel_id)
        OR (source_type = 'CHANNEL' AND provider = 'YOUTUBE' AND video_id IS NULL)
        OR (source_type = 'VIDEO_URL' AND provider IN ('YOUTUBE','BILIBILI') AND video_id IS NOT NULL)
    )
);

INSERT INTO source_subscriptions_v34 (provider,source_id,source_type,canonical_url,channel_id,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,last_error_code,last_error_message,created_at,updated_at) SELECT provider,source_id,source_type,canonical_url,channel_id,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,last_error_code,last_error_message,created_at,updated_at FROM source_subscriptions;

DROP TABLE source_subscriptions;

ALTER TABLE source_subscriptions_v34 RENAME TO source_subscriptions;

CREATE INDEX idx_source_subscriptions_enabled ON source_subscriptions(enabled,updated_at);

CREATE TRIGGER following_provider_identity_immutable BEFORE UPDATE OF provider ON source_subscriptions
WHEN NEW.provider IS NOT OLD.provider BEGIN SELECT RAISE(ABORT,'Following provider identity is immutable'); END;


CREATE TRIGGER following_creator_identity_immutable BEFORE UPDATE ON source_subscriptions
WHEN OLD.source_type='CREATOR' AND (NEW.source_type IS NOT OLD.source_type OR NEW.channel_id IS NOT OLD.channel_id OR NEW.canonical_url IS NOT OLD.canonical_url OR NEW.source_id IS NOT OLD.source_id)
BEGIN SELECT RAISE(ABORT,'Creator Following identity is immutable'); END;

CREATE TABLE source_tracking_state (
 source_id TEXT PRIMARY KEY REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
 contract TEXT NOT NULL CHECK(contract='source-tracking-v1'),
 followed_at TEXT NOT NULL,
 baseline_at TEXT,
 verified_at TEXT,
 latest_published_at TEXT,
 next_page INTEGER NOT NULL DEFAULT 1 CHECK(next_page BETWEEN 1 AND 33334),
 coverage TEXT NOT NULL DEFAULT 'BASELINE_PENDING' CHECK(coverage IN ('BASELINE_PENDING','COMPLETE','CHECK_INCOMPLETE','UPDATE_GAP')),
 health TEXT NOT NULL DEFAULT 'BASELINE_PENDING' CHECK(health IN ('BASELINE_PENDING','HEALTHY','OFFLINE','RATE_LIMITED','RISK_CONTROLLED','ACCESS_DENIED','PROVIDER_ERROR','NOT_FOUND','STATE_INVALID','CHECK_INCOMPLETE','UPDATE_GAP')),
 next_check_at TEXT NOT NULL,
 CHECK((baseline_at IS NULL AND verified_at IS NULL AND latest_published_at IS NULL) OR baseline_at IS NOT NULL)
);
CREATE TRIGGER source_tracking_identity_immutable BEFORE UPDATE ON source_tracking_state
WHEN NEW.source_id IS NOT OLD.source_id OR NEW.followed_at IS NOT OLD.followed_at OR NEW.contract IS NOT OLD.contract
BEGIN SELECT RAISE(ABORT,'Tracking identity is immutable'); END;
CREATE TRIGGER source_tracking_no_delete BEFORE DELETE ON source_tracking_state
BEGIN SELECT RAISE(ABORT,'Tracking cannot be reset through deletion'); END;

CREATE TABLE source_observations (
 source_id TEXT NOT NULL REFERENCES source_tracking_state(source_id) ON DELETE RESTRICT,
 canonical_identity TEXT NOT NULL CHECK(length(canonical_identity) BETWEEN 1 AND 100),
 published_at TEXT NOT NULL,
 observed_at TEXT NOT NULL,
 baseline INTEGER NOT NULL CHECK(baseline IN (0,1)),
 enrollment TEXT NOT NULL CHECK(enrollment IN ('BASELINE','PENDING','ENROLLED','UNSUPPORTED','UNAVAILABLE')),
 content_id TEXT REFERENCES videos(video_id) ON DELETE RESTRICT,
 error_code TEXT,
 PRIMARY KEY(source_id,canonical_identity),
 CHECK((baseline=1 AND enrollment='BASELINE' AND content_id IS NULL) OR (baseline=0 AND enrollment!='BASELINE')),
 CHECK((enrollment='ENROLLED' AND content_id IS NOT NULL) OR (enrollment!='ENROLLED' AND content_id IS NULL))
);
CREATE TRIGGER source_observation_identity_immutable BEFORE UPDATE ON source_observations
WHEN NEW.source_id IS NOT OLD.source_id OR NEW.canonical_identity IS NOT OLD.canonical_identity OR NEW.published_at IS NOT OLD.published_at OR NEW.observed_at IS NOT OLD.observed_at OR NEW.baseline IS NOT OLD.baseline OR OLD.enrollment='ENROLLED'
BEGIN SELECT RAISE(ABORT,'Observed source identity is immutable'); END;
CREATE TRIGGER source_observation_no_delete BEFORE DELETE ON source_observations
BEGIN SELECT RAISE(ABORT,'Observed source identity cannot be forgotten'); END;

CREATE TABLE source_checks (
 check_id TEXT PRIMARY KEY,
 source_id TEXT NOT NULL REFERENCES source_tracking_state(source_id) ON DELETE RESTRICT,
 started_at TEXT NOT NULL,
 finished_at TEXT,
 status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCEEDED','FAILED','INTERRUPTED','PAUSED')),
 result_category TEXT,
 discovered_identities_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(discovered_identities_json)),
 complete INTEGER NOT NULL DEFAULT 0 CHECK(complete IN (0,1)),
 CHECK((status='RUNNING' AND finished_at IS NULL) OR (status!='RUNNING' AND finished_at IS NOT NULL))
);
CREATE UNIQUE INDEX one_active_source_check ON source_checks(source_id) WHERE status='RUNNING';
CREATE INDEX source_check_history ON source_checks(source_id,started_at);
