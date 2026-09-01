-- Product-orchestration state is intentionally separate from trusted video,
-- scoring, note, weekly, and provider dispatch authority.

CREATE TABLE source_subscriptions (
    source_id TEXT PRIMARY KEY CHECK (length(trim(source_id)) > 0),
    source_type TEXT NOT NULL CHECK (source_type IN ('CHANNEL', 'VIDEO_URL')),
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
        (source_type = 'CHANNEL' AND video_id IS NULL)
        OR (source_type = 'VIDEO_URL' AND video_id IS NOT NULL)
    )
);
CREATE INDEX idx_source_subscriptions_enabled ON source_subscriptions(enabled, updated_at);

CREATE TABLE source_video_links (
    source_id TEXT NOT NULL REFERENCES source_subscriptions(source_id) ON DELETE RESTRICT,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE RESTRICT,
    discovered_at TEXT NOT NULL,
    PRIMARY KEY (source_id, video_id)
);

CREATE TABLE automation_schedules (
    schedule_id TEXT PRIMARY KEY CHECK (length(trim(schedule_id)) > 0),
    target_type TEXT NOT NULL CHECK (target_type IN ('SOURCE_CHECK', 'WEEKLY_GENERATION')),
    target_id TEXT,
    frequency TEXT NOT NULL CHECK (frequency IN ('MANUAL', 'DAILY', 'WEEKLY')),
    weekday INTEGER CHECK (weekday IS NULL OR weekday BETWEEN 0 AND 6),
    local_time TEXT CHECK (local_time IS NULL OR local_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    timezone TEXT NOT NULL CHECK (length(trim(timezone)) > 0),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (target_type = 'SOURCE_CHECK' AND target_id IS NOT NULL)
        OR (target_type = 'WEEKLY_GENERATION' AND target_id IS NULL)
    ),
    CHECK (
        (frequency = 'MANUAL' AND weekday IS NULL AND local_time IS NULL)
        OR (frequency = 'DAILY' AND weekday IS NULL AND local_time IS NOT NULL)
        OR (frequency = 'WEEKLY' AND weekday IS NOT NULL AND local_time IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_automation_schedule_target
    ON automation_schedules(target_type, target_id);

CREATE TABLE automation_runs (
    run_id TEXT PRIMARY KEY CHECK (length(trim(run_id)) > 0),
    schedule_id TEXT NOT NULL REFERENCES automation_schedules(schedule_id) ON DELETE RESTRICT,
    target_type TEXT NOT NULL CHECK (target_type IN ('SOURCE_CHECK', 'WEEKLY_GENERATION')),
    target_id TEXT,
    scheduled_for TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('CLAIMED', 'RUNNING', 'SUCCEEDED', 'FAILED_FINAL', 'BLOCKED')),
    error_code TEXT,
    error_message TEXT,
    result_summary TEXT,
    UNIQUE(schedule_id, scheduled_for),
    CHECK (
        (status IN ('CLAIMED', 'RUNNING') AND finished_at IS NULL)
        OR (status IN ('SUCCEEDED', 'FAILED_FINAL', 'BLOCKED') AND finished_at IS NOT NULL)
    )
);
CREATE INDEX idx_automation_runs_schedule_time ON automation_runs(schedule_id, scheduled_for DESC);

CREATE TABLE global_model_preferences (
    preference_key TEXT PRIMARY KEY CHECK (preference_key = 'deep_analysis'),
    desired_provider TEXT,
    desired_model TEXT,
    updated_at TEXT NOT NULL,
    CHECK ((desired_provider IS NULL AND desired_model IS NULL) OR (desired_provider IS NOT NULL))
);
