CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    checksum TEXT NOT NULL CHECK (
        length(checksum) = 64 AND checksum NOT GLOB '*[^0-9a-f]*'
    ),
    applied_at TEXT NOT NULL
);

CREATE TABLE videos (
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
);

CREATE INDEX idx_videos_channel_published
    ON videos(channel_id, published_at, video_id);
CREATE INDEX idx_videos_pipeline_updated
    ON videos(pipeline_status, updated_at);
CREATE INDEX idx_videos_availability_updated
    ON videos(availability, updated_at);

CREATE TABLE channel_cursors (
    channel_id TEXT PRIMARY KEY CHECK (length(trim(channel_id)) > 0),
    last_checked_at TEXT,
    latest_published_at TEXT,
    latest_video_id TEXT CHECK (
        latest_video_id IS NULL OR length(trim(latest_video_id)) > 0
    ),
    provider_cursor TEXT,
    last_error_code TEXT,
    last_error_message TEXT,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    updated_at TEXT NOT NULL
);

CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY CHECK (length(trim(job_id)) > 0),
    scope_key TEXT NOT NULL CHECK (length(trim(scope_key)) > 0),
    video_id TEXT REFERENCES videos(video_id) ON DELETE RESTRICT
        CHECK (video_id IS NULL OR length(trim(video_id)) > 0),
    job_type TEXT NOT NULL CHECK (
        job_type IN ('CHANNEL_DISCOVERY', 'VIDEO_STAGE', 'WEEKLY_REPORT')
    ),
    target_stage TEXT NOT NULL CHECK (
        target_stage IN (
            'DISCOVERY',
            'METADATA',
            'TRANSCRIPT',
            'SCORING',
            'ANALYSIS',
            'NOTE_WRITE',
            'WEEKLY_REPORT'
        )
    ),
    pipeline_version TEXT NOT NULL CHECK (length(trim(pipeline_version)) > 0),
    status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'RUNNING', 'RETRY_PENDING', 'SUCCEEDED', 'FAILED_FINAL')
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL CHECK (max_attempts > 0),
    available_at TEXT NOT NULL,
    lease_owner TEXT CHECK (
        lease_owner IS NULL OR length(trim(lease_owner)) > 0
    ),
    lease_until TEXT,
    last_error_code TEXT,
    last_error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT,
    CHECK (attempt_count <= max_attempts),
    CHECK (
        (job_type = 'VIDEO_STAGE' AND video_id IS NOT NULL)
        OR (job_type IN ('CHANNEL_DISCOVERY', 'WEEKLY_REPORT') AND video_id IS NULL)
    ),
    CHECK (
        (status = 'RUNNING' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL)
        OR (status <> 'RUNNING' AND lease_owner IS NULL AND lease_until IS NULL)
    ),
    CHECK (
        (status IN ('SUCCEEDED', 'FAILED_FINAL') AND finished_at IS NOT NULL)
        OR (status NOT IN ('SUCCEEDED', 'FAILED_FINAL') AND finished_at IS NULL)
    )
);

CREATE UNIQUE INDEX uq_jobs_active_scope_pipeline
    ON jobs(scope_key, pipeline_version)
    WHERE status IN ('PENDING', 'RUNNING', 'RETRY_PENDING');
CREATE INDEX idx_jobs_schedule
    ON jobs(status, available_at, created_at, job_id);
CREATE INDEX idx_jobs_video_stage_created
    ON jobs(video_id, target_stage, created_at);

CREATE TABLE job_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE RESTRICT
        CHECK (length(trim(job_id)) > 0),
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    lease_owner TEXT NOT NULL CHECK (length(trim(lease_owner)) > 0),
    started_at TEXT NOT NULL,
    lease_until TEXT NOT NULL,
    finished_at TEXT,
    outcome TEXT CHECK (
        outcome IS NULL
        OR outcome IN ('SUCCEEDED', 'RETRY_PENDING', 'FAILED_FINAL', 'LEASE_EXPIRED')
    ),
    error_code TEXT,
    error_message TEXT,
    CHECK (
        (finished_at IS NULL AND outcome IS NULL)
        OR (finished_at IS NOT NULL AND outcome IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_job_attempts_number
    ON job_attempts(job_id, attempt_number);
CREATE UNIQUE INDEX uq_job_attempts_active
    ON job_attempts(job_id)
    WHERE finished_at IS NULL;

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY CHECK (length(trim(artifact_id)) > 0),
    artifact_key TEXT NOT NULL UNIQUE CHECK (length(trim(artifact_key)) > 0),
    video_id TEXT REFERENCES videos(video_id) ON DELETE RESTRICT
        CHECK (video_id IS NULL OR length(trim(video_id)) > 0),
    job_id TEXT REFERENCES jobs(job_id) ON DELETE RESTRICT
        CHECK (job_id IS NULL OR length(trim(job_id)) > 0),
    kind TEXT NOT NULL CHECK (
        kind IN (
            'subtitle_source',
            'transcript_canonical',
            'audio',
            'scoring_raw',
            'scoring_structured',
            'analysis_raw',
            'analysis_structured',
            'video_note',
            'weekly_report'
        )
    ),
    storage_root TEXT NOT NULL CHECK (storage_root IN ('DATA', 'VAULT')),
    relative_path TEXT NOT NULL CHECK (length(trim(relative_path)) > 0),
    content_hash TEXT NOT NULL CHECK (
        length(content_hash) = 64 AND content_hash NOT GLOB '*[^0-9a-f]*'
    ),
    provider TEXT,
    model TEXT,
    producer_version TEXT NOT NULL CHECK (length(trim(producer_version)) > 0),
    retention_class TEXT NOT NULL CHECK (
        retention_class IN ('EPHEMERAL_AUDIO', 'RAW_RESPONSE_30D', 'LONG_LIVED')
    ),
    created_at TEXT NOT NULL,
    expires_at TEXT,
    deleted_at TEXT
);

CREATE INDEX idx_artifacts_video_kind_created
    ON artifacts(video_id, kind, created_at);
CREATE INDEX idx_artifacts_retention
    ON artifacts(retention_class, expires_at, deleted_at);

CREATE TABLE provider_calls (
    request_hash TEXT PRIMARY KEY CHECK (
        length(request_hash) = 64 AND request_hash NOT GLOB '*[^0-9a-f]*'
    ),
    operation TEXT NOT NULL CHECK (length(trim(operation)) > 0),
    provider TEXT NOT NULL CHECK (length(trim(provider)) > 0),
    model TEXT,
    prompt_version TEXT,
    schema_version TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'SUCCEEDED', 'FAILED_RETRYABLE', 'FAILED_FINAL')
    ),
    reservation_owner TEXT CHECK (
        reservation_owner IS NULL OR length(trim(reservation_owner)) > 0
    ),
    lease_until TEXT,
    available_at TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    response_artifact_id TEXT REFERENCES artifacts(artifact_id) ON DELETE RESTRICT
        CHECK (
            response_artifact_id IS NULL OR length(trim(response_artifact_id)) > 0
        ),
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    cost_microusd INTEGER CHECK (cost_microusd IS NULL OR cost_microusd >= 0),
    last_error_code TEXT,
    last_error_message TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    updated_at TEXT NOT NULL,
    CHECK (
        (status = 'PENDING' AND reservation_owner IS NOT NULL AND lease_until IS NOT NULL)
        OR (status <> 'PENDING' AND reservation_owner IS NULL AND lease_until IS NULL)
    ),
    CHECK (
        (status IN ('SUCCEEDED', 'FAILED_FINAL') AND finished_at IS NOT NULL)
        OR (status IN ('PENDING', 'FAILED_RETRYABLE') AND finished_at IS NULL)
    )
);

CREATE INDEX idx_provider_calls_recovery
    ON provider_calls(status, available_at, lease_until);

CREATE TABLE reports (
    report_id TEXT PRIMARY KEY CHECK (length(trim(report_id)) > 0),
    timezone TEXT NOT NULL CHECK (length(trim(timezone)) > 0),
    iso_year INTEGER NOT NULL CHECK (iso_year >= 1),
    iso_week INTEGER NOT NULL CHECK (iso_week BETWEEN 1 AND 53),
    report_type TEXT NOT NULL CHECK (report_type = 'weekly'),
    relative_path TEXT,
    content_hash TEXT CHECK (
        content_hash IS NULL
        OR (length(content_hash) = 64 AND content_hash NOT GLOB '*[^0-9a-f]*')
    ),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'WRITTEN')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(timezone, iso_year, iso_week, report_type)
);
