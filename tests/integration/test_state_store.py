"""Integration tests for the TASK-003 SQLite state repository."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from datetime import timedelta as td
from importlib import resources
from pathlib import Path

import pytest

from youtube_intel import state as state_mod
from youtube_intel.config import load_app_config
from youtube_intel.domain import (
    Availability,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    ScoringInput,
    VideoMetadata,
)
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    parse_scoring_candidate,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import (
    PhaseFTrustedScoringSuccess,
    PrimaryScoringAttempt,
    ScoringPersistenceError,
    TrustedPersistenceEntry,
    build_primary_scoring_attempt,
    build_scoring_input,
)
from youtube_intel.scoring_admission import ScoringDispatchAdmission
from youtube_intel.state import (
    CURRENT_SCHEMA_VERSION,
    ArtifactKind,
    ArtifactWrite,
    ConcurrencyConflict,
    IntegrityConflict,
    JobAttemptOutcome,
    JobType,
    LeaseConflict,
    MigrationError,
    ProviderCallCompletion,
    ProviderCallRequest,
    ProviderCallStatus,
    ReportStatus,
    ReportWrite,
    RetentionClass,
    ScoringSummaryWrite,
    SQLiteStateRepository,
    StorageRoot,
    VerifiedArtifact,
    build_provider_request_hash,
)

NOW = datetime(2026, 7, 15, 8, 30, tzinfo=UTC)
HASH_A = "a" * 64
HASH_B = "b" * 64
INPUT_HASH = "c" * 64
REQUEST_HASH = build_provider_request_hash(
    operation="transcribe",
    normalized_input_hash=INPUT_HASH,
    provider="fake-provider",
    model="fake-model",
    prompt_version=None,
    schema_version="v1",
)

EXPECTED_TABLES = {
    "saved_intelligences",
    "artifacts",
    "channel_cursors",
    "deep_analysis_persisted_results",
    "current_content_summaries",
    "distillation_cards",
    "distillation_execution_checkpoints",
    "distillation_resource_usage",
    "job_attempts",
    "jobs",
    "provider_calls",
    "provider_dispatch_states",
    "reports",
    "schema_migrations",
    "source_subscriptions",
    "source_video_links",
    "automation_schedules",
    "automation_runs",
    "weekly_briefs",
    "brief_items",
    "brief_item_evidence",
    "weekly_brief_preference_projections",
    "brief_item_markers",
    "global_model_preferences",
    "global_user_settings",
    "evidence",
    "intelligences",
    "intelligence_revisions",
    "intelligence_state_history",
    "intelligence_revision_evidence",
    "dependency_edges",
    "preferences",
    "preference_state_events",
    "feedback_events",
    "manual_analyze_overrides",
    "source_policy_current",
    "source_policy_revisions",
    "source_run_checkpoint_events",
    "source_run_state_events",
    "source_run_video_execution_events",
    "source_run_video_executions",
    "source_runs",
    "source_video_filter_decisions",
    "topic_memberships",
    "topic_membership_evidence",
    "topic_relations",
    "topic_timeline_event_memberships",
    "topic_timeline_events",
    "topics",
    "videos",
}
EXPECTED_COLUMNS = {
    "saved_intelligences": ("intelligence_id", "saved_at"),
    "global_user_settings": ("settings_key", "output_language", "updated_at"),
    "current_content_summaries": ("video_id", "result_identity", "updated_at"),
    "schema_migrations": ("version", "name", "checksum", "applied_at"),
    "videos": (
        "video_id",
        "channel_id",
        "channel_name",
        "title",
        "description",
        "source_url",
        "published_at",
        "duration_seconds",
        "default_language",
        "available_languages_json",
        "live_status",
        "availability",
        "pipeline_status",
        "pipeline_version",
        "score",
        "should_summarize",
        "discovered_at",
        "updated_at",
        "completed_at",
        "authoritative_scoring_job_id",
    ),
    "channel_cursors": (
        "channel_id",
        "last_checked_at",
        "latest_published_at",
        "latest_video_id",
        "provider_cursor",
        "last_error_code",
        "last_error_message",
        "revision",
        "updated_at",
    ),
    "jobs": (
        "job_id",
        "scope_key",
        "video_id",
        "job_type",
        "target_stage",
        "pipeline_version",
        "status",
        "attempt_count",
        "max_attempts",
        "available_at",
        "lease_owner",
        "lease_until",
        "last_error_code",
        "last_error_message",
        "created_at",
        "updated_at",
        "finished_at",
        "authoritative_scoring_artifact_key",
        "scoring_success_provenance",
        "scoring_lineage_version",
    ),
    "job_attempts": (
        "attempt_id",
        "job_id",
        "attempt_number",
        "lease_owner",
        "started_at",
        "lease_until",
        "finished_at",
        "outcome",
        "error_code",
        "error_message",
    ),
    "artifacts": (
        "artifact_id",
        "artifact_key",
        "video_id",
        "job_id",
        "kind",
        "storage_root",
        "relative_path",
        "content_hash",
        "provider",
        "model",
        "producer_version",
        "retention_class",
        "created_at",
        "expires_at",
        "deleted_at",
    ),
    "provider_calls": (
        "request_hash",
        "operation",
        "provider",
        "model",
        "prompt_version",
        "schema_version",
        "status",
        "reservation_owner",
        "lease_until",
        "available_at",
        "attempt_count",
        "response_artifact_id",
        "input_tokens",
        "output_tokens",
        "cost_microusd",
        "last_error_code",
        "last_error_message",
        "started_at",
        "finished_at",
        "updated_at",
    ),
    "provider_dispatch_states": (
        "request_hash",
        "status",
        "updated_at",
    ),
    "reports": (
        "report_id",
        "timezone",
        "iso_year",
        "iso_week",
        "report_type",
        "relative_path",
        "content_hash",
        "status",
        "created_at",
        "updated_at",
    ),
    "weekly_briefs": (
        "brief_id", "version", "logical_period_id", "timezone", "period_start_utc",
        "period_end_utc", "status", "no_important_information",
        "preference_projection_hash", "generated_at", "finalized_at",
    ),
    "brief_items": (
        "brief_item_id", "brief_id", "membership_id", "topic_id", "topic_name",
        "intelligence_id", "revision_id", "association_kind", "claim_kind",
        "source_state", "summary", "source_content_hash", "position", "created_at",
    ),
    "brief_item_evidence": ("brief_item_id", "evidence_id"),
    "weekly_brief_preference_projections": (
        "brief_id", "preference_id", "horizon", "provenance", "statement_hash",
    ),
    "brief_item_markers": (
        "marker_id", "brief_item_id", "marker_kind", "reason", "current_revision_id",
        "evidence_id", "marked_at",
    ),
    "source_subscriptions": (
        "source_id",
        "source_type",
        "canonical_url",
        "channel_id",
        "video_id",
        "display_name",
        "enabled",
        "processing_policy",
        "last_checked_at",
        "last_success_at",
        "last_error_code",
        "last_error_message",
        "created_at",
        "updated_at",
    ),
    "source_video_links": ("source_id", "video_id", "discovered_at"),
    "automation_schedules": (
        "schedule_id",
        "target_type",
        "target_id",
        "frequency",
        "weekday",
        "local_time",
        "timezone",
        "enabled",
        "created_at",
        "updated_at",
    ),
    "automation_runs": (
        "run_id",
        "schedule_id",
        "target_type",
        "target_id",
        "scheduled_for",
        "claimed_at",
        "started_at",
        "finished_at",
        "status",
        "error_code",
        "error_message",
        "result_summary",
    ),
    "global_model_preferences": (
        "preference_key",
        "desired_provider",
        "desired_model",
        "updated_at",
    ),
    "preferences": (
        "preference_id",
        "horizon",
        "provenance",
        "scope",
        "target_id",
        "statement",
        "starts_at",
        "expires_at",
        "supersedes_preference_id",
        "created_at",
    ),
    "preference_state_events": ("state_event_id", "preference_id", "state", "created_at"),
    "feedback_events": (
        "feedback_id",
        "kind",
        "scope",
        "target_id",
        "content",
        "correction_kind",
        "effect_status",
        "created_at",
    ),
    "source_policy_revisions": (
        "revision_id",
        "policy_scope",
        "source_id",
        "initial_history_count",
        "per_run_max_new_videos",
        "focus_mode",
        "focus_rules_json",
        "ignore_mode",
        "ignore_rules_json",
        "distillation_style_mode",
        "distillation_style",
        "created_at",
    ),
    "source_policy_current": (
        "policy_key",
        "policy_scope",
        "source_id",
        "revision_id",
    ),
    "source_video_filter_decisions": (
        "decision_order",
        "decision_id",
        "source_id",
        "video_id",
        "stage",
        "outcome",
        "reason",
        "global_policy_revision_id",
        "source_policy_revision_id",
        "manual_override_id",
        "prior_decision_id",
        "evaluated_at",
    ),
    "manual_analyze_overrides": (
        "override_id",
        "source_id",
        "video_id",
        "command_id",
        "prior_decision_id",
        "created_at",
    ),
    "source_runs": (
        "run_id",
        "source_id",
        "trigger",
        "trigger_reference",
        "priority",
        "idempotency_key",
        "state",
        "attention_reason",
        "automation_run_id",
        "manual_command_id",
        "manual_analyze_override_id",
        "created_at",
        "updated_at",
    ),
    "source_run_state_events": (
        "event_id",
        "run_id",
        "prior_state",
        "state",
        "attention_reason",
        "occurred_at",
    ),
    "source_run_video_executions": (
        "run_id",
        "video_id",
        "state",
        "distillation_execution_id",
        "created_at",
        "updated_at",
    ),
    "source_run_video_execution_events": (
        "event_id",
        "run_id",
        "video_id",
        "prior_state",
        "state",
        "occurred_at",
    ),
    "source_run_checkpoint_events": (
        "event_id",
        "run_id",
        "checkpoint",
        "checkpoint_position",
        "event_status",
        "created_at",
    ),
}


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "state.sqlite3"


def _raw_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def _call() -> ProviderCallMetadata:
    return ProviderCallMetadata(
        provider="fake-source",
        started_at=NOW,
        finished_at=NOW,
    )


def _cursor(*, provider_cursor: str, latest_video_id: str | None) -> DiscoveryCursor:
    return DiscoveryCursor(
        channel_id="UC_TEST",
        last_checked_at=NOW,
        latest_published_at=NOW,
        latest_video_id=latest_video_id,
        provider_cursor=provider_cursor,
    )


def _batch(
    *video_ids: str,
    provider_cursor: str = "cursor-1",
) -> DiscoveryBatch:
    return DiscoveryBatch(
        channel_id="UC_TEST",
        video_ids=video_ids,
        next_cursor=_cursor(
            provider_cursor=provider_cursor,
            latest_video_id=video_ids[-1] if video_ids else None,
        ),
        call=_call(),
    )


def _metadata(*, title: str = "Initial title") -> VideoMetadata:
    return VideoMetadata(
        video_id="video-1",
        channel_id="UC_TEST",
        channel_name="Test channel",
        title=title,
        description="Description",
        source_url="https://www.youtube.com/watch?v=video-1",
        published_at=NOW,
        duration_seconds=123,
        default_language="en",
        available_languages=("en", "zh", "en"),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _repository_with_video(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    return repository


def _create_video_job(
    repository: SQLiteStateRepository,
    *,
    job_id: str,
    max_attempts: int = 3,
    created_at: datetime = NOW,
) -> None:
    repository.create_job(
        job_id=job_id,
        scope_key="video:video-1:METADATA",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.METADATA,
        pipeline_version="pipeline-v1",
        max_attempts=max_attempts,
        available_at=NOW,
        now=created_at,
    )


def _artifact(
    *,
    artifact_id: str = "artifact-1",
    artifact_key: str = "video:video-1:metadata:v1",
    content_hash: str = HASH_A,
    job_id: str | None = None,
    kind: ArtifactKind = ArtifactKind.TRANSCRIPT_CANONICAL,
    retention_class: RetentionClass = RetentionClass.LONG_LIVED,
    expires_at: datetime | None = None,
) -> ArtifactWrite:
    return ArtifactWrite(
        artifact_id=artifact_id,
        artifact_key=artifact_key,
        video_id="video-1",
        job_id=job_id,
        kind=kind,
        storage_root=StorageRoot.DATA,
        relative_path="transcripts/video-1.txt",
        content_hash=content_hash,
        provider="fake-provider",
        model=None,
        producer_version="v1",
        retention_class=retention_class,
        expires_at=expires_at,
    )


def _provider_request() -> ProviderCallRequest:
    return ProviderCallRequest(
        operation="transcribe",
        normalized_input_hash=INPUT_HASH,
        provider="fake-provider",
        model="fake-model",
        prompt_version=None,
        schema_version="v1",
        deterministic_artifact_key="video:video-1:metadata:v1",
    )


class _QualityResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self, size: int = -1) -> bytes:
        del size
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        pass


class _QualityTransport:
    def __call__(self, request: object, timeout: float) -> _QualityResponse:
        del timeout
        if getattr(request, "method") == "GET":
            return _QualityResponse(
                {"models": [{"name": "qwen3:8b", "digest": "a" * 64}]}
            )
        return _QualityResponse(
            {
                "response": json.dumps(
                    {
                        "status": "PASS",
                        "decision_confidence": "HIGH",
                        "grounding_confidence": "MEDIUM",
                        "usefulness_confidence": "MEDIUM",
                        "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
                        "reason": None,
                        "evidence_ids": ["title-1"],
                    },
                    separators=(",", ":"),
                )
            }
        )


class _TrustedScoringProvider:
    def primary_attempt(self, scoring_input: ScoringInput) -> PrimaryScoringAttempt:
        raw = json.dumps(
            {
                "model": "qwen3:8b",
                "response": json.dumps(
                    {
                        "score": 7.5,
                        "reason": (
                            "This offline fixture explains a concrete product workflow "
                            "with grounded, practical details."
                        ),
                        "topics": ["product"],
                        "should_summarize": True,
                    },
                    separators=(",", ":"),
                ),
            },
            separators=(",", ":"),
        )
        return build_primary_scoring_attempt(
            scoring_input=scoring_input,
            candidate=parse_scoring_candidate(raw),
            final_raw_response=raw,
            provider="ollama",
            model="qwen3:8b",
            model_digest="sha256:" + ("a" * 64),
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=4000,
        )


def _trusted_scoring_runtime(
    tmp_path: Path,
) -> tuple[RuntimeOperations, _TrustedScoringProvider]:
    project_root = tmp_path / "trusted-runtime"
    config_root = project_root / "config"
    config_root.mkdir(parents=True)
    vault_root = project_root / "vault"
    vault_root.mkdir()
    (config_root / "channels.yaml").write_text(
        "channels:\n  - channel_id: UC_TEST\n", encoding="utf-8"
    )
    (config_root / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: qwen3:8b
  expected_model_digest: sha256:{"a" * 64}
  temperature: 0.0
  max_output_tokens: 1200
  max_transcript_chars: 30000
  max_description_chars: 4000
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {vault_root}
  vault_subdir: Knowledge
""",
        encoding="utf-8",
    )
    config = load_app_config(
        channels_path=config_root / "channels.yaml",
        settings_path=config_root / "settings.yaml",
    )
    scoring_provider = _TrustedScoringProvider()
    runtime = RuntimeOperations(
        config=config,
        project_root=project_root,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: scoring_provider,
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
            quality_judge_provider_factory=lambda: OllamaQualityJudgeProvider(
                settings=config.settings.local_scoring,
                transport=_QualityTransport(),
            ),
        ),
    )
    return runtime, scoring_provider


def _trusted_scoring_job(
    runtime: RuntimeOperations,
) -> tuple[ScoringInput, PhaseFTrustedScoringSuccess, datetime]:
    repository = runtime._repository
    now = datetime.now(UTC)
    repository.upsert_video_metadata(
        _metadata(), pipeline_version="pipeline-v1", now=now
    )
    assert repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    assert repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    repository.create_job(
        job_id="scoring-job",
        scope_key="video:video-1:SCORING",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    claimed = repository.claim_next_job(
        owner="worker-1", lease_until=now + td(minutes=10), now=now
    )
    assert claimed is not None
    scoring_input = build_scoring_input(
        video=_metadata(),
        transcript_text="transcript evidence",
        language="en",
        output_language=runtime._config.settings.general.output_language,
        settings=runtime._config.settings.local_scoring,
    )
    provider = runtime._dependencies.scoring_provider_factory()
    success = runtime._run_primary_trusted_scoring(
        attempt=provider.primary_attempt(scoring_input),
        scoring_input=scoring_input,
        admission=ScoringDispatchAdmission(
            repository=repository,
            job_id=claimed.job_id,
            owner=claimed.lease_owner or "",
        ),
    )
    return scoring_input, success, now


def _trusted_persistence_entry(
    runtime: RuntimeOperations, *, now: datetime
) -> TrustedPersistenceEntry:
    entry = runtime._trusted_persistence_entry(
        job_id="scoring-job", owner="worker-1", pipeline_version="pipeline-v1"
    )
    entry._clock = lambda: now  # type: ignore[method-assign]
    return entry


def _assert_no_trusted_scoring_success(runtime: RuntimeOperations) -> None:
    repository = runtime._repository
    assert repository.get_artifact_by_key("scoring/forged/raw") is None
    with _raw_connection(runtime._data_root / "state.sqlite") as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE video_id = 'video-1'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM provider_calls").fetchone()[0] == 0
        )
    video = repository.get_video("video-1")
    assert video is not None
    assert video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    assert video.score is None
    assert video.should_summarize is None
    job = repository.get_job("scoring-job")
    assert job is not None
    assert job.status is JobStatus.RUNNING


def test_initialize_is_repeatable_and_records_packaged_checksum(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)

    first = repository.initialize(now=NOW)
    second = repository.initialize(now=NOW)

    sql = (
        resources.files("youtube_intel")
        .joinpath("migrations", "017_add_evidence_excerpt_stance.sql")
        .read_bytes()
    )
    assert first == second
    assert first.version == CURRENT_SCHEMA_VERSION == 17
    assert first.name == "017_add_evidence_excerpt_stance.sql"
    assert first.checksum == hashlib.sha256(sql).hexdigest()

    with _raw_connection(path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
            if not row["name"].startswith("sqlite_")
        }
        migration_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
    assert tables == EXPECTED_TABLES
    assert migration_count == CURRENT_SCHEMA_VERSION


def test_m017_adds_nullable_immutable_excerpt_and_finite_stance(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)

    with _raw_connection(path) as connection:
        evidence_columns = {
            row["name"] for row in connection.execute('PRAGMA table_info("evidence")')
        }
        relation_columns = {
            row["name"]
            for row in connection.execute(
                'PRAGMA table_info("intelligence_revision_evidence")'
            )
        }
    assert "source_excerpt" in evidence_columns
    assert "stance" in relation_columns


def test_global_output_language_persists_and_rejects_unsupported_values(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)

    assert repository.get_global_user_settings() is None

    saved = repository.save_global_output_language(
        output_language="en", now=NOW
    )
    assert saved.output_language == "en"
    assert repository.get_global_user_settings() == saved

    replaced = repository.save_global_output_language(
        output_language="zh-CN", now=NOW + td(minutes=1)
    )
    assert replaced.output_language == "zh-CN"
    assert repository.get_global_user_settings() == replaced

    with pytest.raises(ValueError, match="output language is unsupported"):
        repository.save_global_output_language(
            output_language="fr", now=NOW + td(minutes=2)
        )


def test_file_database_enforces_required_pragmas_and_wal(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)

    settings = repository.database_settings()

    assert settings.foreign_keys is True
    assert settings.busy_timeout_ms == 5000
    assert settings.synchronous == "NORMAL"
    assert settings.journal_mode == "WAL"
    assert settings.read_uncommitted is False


def test_schema_columns_and_required_indexes_match_adr_003(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)

    with _raw_connection(path) as connection:
        actual_columns = {
            table: tuple(
                row["name"]
                for row in connection.execute(f'PRAGMA table_info("{table}")')
            )
            for table in EXPECTED_COLUMNS
        }
        explicit_indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND sql IS NOT NULL"
            )
        }
        active_job_index = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'index' AND name = 'uq_jobs_active_scope_pipeline'"
        ).fetchone()[0]

    assert actual_columns == EXPECTED_COLUMNS
    assert explicit_indexes == {
        "idx_saved_intelligences_order",
        "idx_current_content_summaries_result",
        "idx_artifacts_retention",
        "idx_artifacts_video_kind_created",
        "idx_brief_item_markers_item",
        "idx_brief_items_membership",
        "idx_brief_items_revision",
        "idx_jobs_schedule",
        "idx_jobs_video_stage_created",
        "idx_provider_calls_recovery",
        "idx_videos_availability_updated",
        "idx_videos_channel_published",
        "idx_videos_pipeline_updated",
        "idx_weekly_briefs_period",
        "uq_job_attempts_active",
        "uq_job_attempts_number",
        "uq_jobs_active_scope_pipeline",
        "uq_jobs_authoritative_scoring_artifact_key",
        "uq_videos_authoritative_scoring_job_id",
        "uq_deep_analysis_persisted_cache_identity",
        "idx_source_subscriptions_enabled",
        "idx_automation_runs_schedule_time",
        "uq_automation_schedule_target",
        "idx_evidence_video_availability",
        "idx_intelligence_revisions_identity",
        "idx_intelligence_revision_evidence_evidence",
        "idx_intelligence_state_history_identity",
        "idx_dependency_edges_input_evidence",
        "idx_dependency_edges_input_revision",
        "uq_dependency_edge_evidence",
        "uq_dependency_edge_revision",
        "uq_brief_marker_evidence",
        "uq_brief_marker_superseded",
        "idx_preferences_scope_created",
        "idx_preference_state_events_preference",
        "idx_feedback_events_created",
        "idx_manual_analyze_overrides_source_video",
        "idx_source_policy_revisions_scope_created",
        "idx_source_run_checkpoint_events_run",
        "idx_source_run_state_events_run",
        "idx_source_run_video_execution_events_child",
        "idx_source_run_video_executions_run_state",
        "idx_source_runs_admission",
        "idx_source_runs_source_created",
        "idx_source_video_filter_decisions_source_video",
        "idx_topic_memberships_revision",
        "idx_topic_memberships_topic",
        "idx_topic_timeline_events_topic",
        "idx_topics_pinned_updated",
    }
    assert "scope_key, pipeline_version" in active_job_index
    assert "PENDING" in active_job_index
    assert "RUNNING" in active_job_index
    assert "RETRY_PENDING" in active_job_index


@pytest.mark.parametrize("corruption", ["name", "checksum", "user_version"])
def test_initialize_rejects_migration_history_mismatch(
    tmp_path: Path, corruption: str
) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)

    with _raw_connection(path) as connection:
        if corruption == "name":
            connection.execute(
                "UPDATE schema_migrations SET name = 'renamed.sql' WHERE version = 1"
            )
        elif corruption == "checksum":
            connection.execute(
                "UPDATE schema_migrations SET checksum = ? WHERE version = 1",
                ("0" * 64,),
            )
        else:
            connection.execute("PRAGMA user_version = 0")

    with pytest.raises(MigrationError, match="migration history mismatch"):
        repository.initialize(now=NOW)


def test_failed_migration_rolls_back_schema_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    broken_sql = "CREATE TABLE half_applied (value TEXT);\nTHIS IS NOT SQL;\n"
    migration = state_mod._Migration(
        version=1,
        name="001_initial.sql",
        sql=broken_sql,
        checksum=hashlib.sha256(broken_sql.encode()).hexdigest(),
    )
    monkeypatch.setattr(repository, "_load_migrations", lambda: (migration,))

    with pytest.raises(MigrationError, match="failed to apply migration"):
        repository.initialize(now=NOW)

    with _raw_connection(path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert "half_applied" not in tables
    assert "schema_migrations" not in tables
    assert version == 0


def test_discovery_batch_and_cursor_are_atomic_with_empty_batch_support(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)

    first = repository.save_discovery_batch(
        _batch("video-1", "video-2"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    empty_batch = _batch(provider_cursor="cursor-2")
    second = repository.save_discovery_batch(
        empty_batch,
        expected_cursor=_cursor(
            provider_cursor="cursor-1",
            latest_video_id="video-2",
        ),
        expected_revision=1,
        pipeline_version="pipeline-v1",
        now=NOW,
    )

    assert first.revision == 1
    assert second.revision == 2
    assert second.provider_cursor == "cursor-2"
    assert repository.get_video("video-1").title is None
    assert repository.get_video("video-2").pipeline_status is PipelineStatus.DISCOVERED


def test_discovery_rejects_stale_cursor_without_partial_candidates(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )

    with pytest.raises(ConcurrencyConflict, match="channel cursor changed"):
        repository.save_discovery_batch(
            _batch("stale-video", provider_cursor="cursor-stale"),
            expected_cursor=None,
            expected_revision=0,
            pipeline_version="pipeline-v1",
            now=NOW,
        )

    assert repository.get_video("stale-video") is None
    assert repository.get_channel_cursor("UC_TEST").revision == 1


def test_discovery_failure_after_candidates_rolls_back_batch_and_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)

    def fail_after_candidates(point: str) -> None:
        if point == "discovery.after_candidates":
            raise RuntimeError("injected failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_after_candidates)

    with pytest.raises(RuntimeError, match="injected failure"):
        repository.save_discovery_batch(
            _batch("rolled-back-video"),
            expected_cursor=None,
            expected_revision=0,
            pipeline_version="pipeline-v1",
            now=NOW,
        )

    assert repository.get_video("rolled-back-video") is None
    assert repository.get_channel_cursor("UC_TEST") is None


def test_metadata_upsert_preserves_discovery_and_pipeline_state(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    discovered = repository.get_video("video-1")

    first = repository.upsert_video_metadata(
        _metadata(), pipeline_version="pipeline-v1", now=NOW
    )
    for expected, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
    ):
        assert repository.advance_pipeline(
            "video-1",
            expected_status=expected,
            target_status=target,
            pipeline_version="pipeline-v1",
            now=NOW,
        )
    updated = repository.upsert_video_metadata(
        _metadata(title="Renamed title"),
        pipeline_version="other-version",
        now=NOW,
    )

    assert first.available_languages == ("en", "zh")
    assert updated.title == "Renamed title"
    assert updated.discovered_at == discovered.discovered_at
    assert updated.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    assert updated.pipeline_version == "pipeline-v1"


def test_mark_unavailable_does_not_fabricate_metadata(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )

    assert repository.mark_video_unavailable(
        "video-1", availability=Availability.PRIVATE, now=NOW
    )
    video = repository.get_video("video-1")

    assert video.availability is Availability.PRIVATE
    assert video.title is None
    assert video.source_url is None


def test_active_job_uniqueness_covers_video_and_global_scopes(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="video-job-1")

    with pytest.raises(IntegrityConflict, match="active job"):
        _create_video_job(repository, job_id="video-job-2")

    repository.create_job(
        job_id="global-job-1",
        scope_key="channel:UC_TEST:discovery",
        video_id=None,
        job_type=JobType.CHANNEL_DISCOVERY,
        target_stage=ProcessingStage.DISCOVERY,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    with pytest.raises(IntegrityConflict, match="active job"):
        repository.create_job(
            job_id="global-job-2",
            scope_key="channel:UC_TEST:discovery",
            video_id=None,
            job_type=JobType.CHANNEL_DISCOVERY,
            target_stage=ProcessingStage.DISCOVERY,
            pipeline_version="pipeline-v1",
            max_attempts=3,
            available_at=NOW,
            now=NOW,
        )


def test_global_job_scope_key_requires_a_non_empty_canonical_scope(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)

    with pytest.raises(ValueError, match="scope_key is not canonical"):
        repository.create_job(
            job_id="invalid-global-job",
            scope_key="channel::discovery",
            video_id=None,
            job_type=JobType.CHANNEL_DISCOVERY,
            target_stage=ProcessingStage.DISCOVERY,
            pipeline_version="pipeline-v1",
            max_attempts=3,
            available_at=NOW,
            now=NOW,
        )


def test_claim_uses_stable_order_and_creates_attempt(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    repository.create_job(
        job_id="job-b",
        scope_key="weekly:Asia-Shanghai:2026-W29:weekly-b",
        video_id=None,
        job_type=JobType.WEEKLY_REPORT,
        target_stage=ProcessingStage.WEEKLY_REPORT,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.create_job(
        job_id="job-a",
        scope_key="weekly:Asia-Shanghai:2026-W29:weekly-a",
        video_id=None,
        job_type=JobType.WEEKLY_REPORT,
        target_stage=ProcessingStage.WEEKLY_REPORT,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )

    claimed = repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=5), now=NOW
    )

    assert claimed.job_id == "job-a"
    assert claimed.status is JobStatus.RUNNING
    assert claimed.attempt_count == 1
    attempts = repository.list_job_attempts("job-a")
    assert [(item.attempt_number, item.lease_owner) for item in attempts] == [
        (1, "worker-1")
    ]
    completed = repository.complete_job("job-a", owner="worker-1", now=NOW)
    assert completed.status is JobStatus.SUCCEEDED
    assert (
        repository.list_job_attempts("job-a")[0].outcome is JobAttemptOutcome.SUCCEEDED
    )


def test_two_connections_cannot_double_claim_one_job(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="single-job")

    def claim(owner: str) -> str | None:
        independent = SQLiteStateRepository(_database_path(tmp_path))
        job = independent.claim_next_job(
            owner=owner,
            lease_until=NOW + td(minutes=5),
            now=NOW,
        )
        return None if job is None else job.lease_owner

    with ThreadPoolExecutor(max_workers=2) as executor:
        owners = list(executor.map(claim, ("worker-a", "worker-b")))

    assert sum(owner is not None for owner in owners) == 1
    assert len(repository.list_job_attempts("single-job")) == 1


def test_renew_requires_current_owner_and_unexpired_lease(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="renew-job")
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=5), now=NOW
    )

    assert not repository.renew_job(
        "renew-job",
        owner="other-worker",
        lease_until=NOW + td(minutes=10),
        now=NOW + td(minutes=1),
    )
    assert repository.renew_job(
        "renew-job",
        owner="worker-1",
        lease_until=NOW + td(minutes=10),
        now=NOW + td(minutes=1),
    )
    assert not repository.renew_job(
        "renew-job",
        owner="worker-1",
        lease_until=NOW + td(minutes=20),
        now=NOW + td(minutes=11),
    )
    assert repository.list_job_attempts("renew-job")[0].lease_until == NOW + td(
        minutes=10
    )


def test_retry_must_be_activated_and_attempt_history_is_preserved(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="retry-job")
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=5), now=NOW
    )

    failed = repository.fail_job(
        "retry-job",
        owner="worker-1",
        error_code=ErrorCode.TRANSIENT_NETWORK,
        error_message="Authorization: Bearer top-secret\nraw response body",
        retry_at=NOW + td(minutes=10),
        now=NOW + td(minutes=1),
    )
    assert failed.status is JobStatus.RETRY_PENDING
    assert (
        repository.claim_next_job(
            owner="worker-2", lease_until=NOW + td(minutes=20), now=NOW + td(minutes=10)
        )
        is None
    )
    assert repository.activate_retry_jobs(now=NOW + td(minutes=9)) == ()
    activated = repository.activate_retry_jobs(now=NOW + td(minutes=10))
    assert [job.job_id for job in activated] == ["retry-job"]

    claimed = repository.claim_next_job(
        owner="worker-2",
        lease_until=NOW + td(minutes=20),
        now=NOW + td(minutes=10),
    )
    assert claimed.attempt_count == 2
    succeeded = repository.complete_stage(
        job_id="retry-job",
        owner="worker-2",
        video_id="video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        artifacts=(),
        provider_call=None,
        now=NOW + td(minutes=11),
    ).job
    assert succeeded.status is JobStatus.SUCCEEDED
    attempts = repository.list_job_attempts("retry-job")
    assert [attempt.outcome for attempt in attempts] == [
        JobAttemptOutcome.RETRY_PENDING,
        JobAttemptOutcome.SUCCEEDED,
    ]

    with _raw_connection(_database_path(tmp_path)) as connection:
        stored = " ".join(
            str(value)
            for row in connection.execute(
                "SELECT last_error_message FROM jobs WHERE job_id = 'retry-job' "
                "UNION ALL SELECT error_message FROM job_attempts "
                "WHERE job_id = 'retry-job'"
            )
            for value in row
            if value is not None
        )
    assert "top-secret" not in stored
    assert "raw response body" not in stored


def test_lease_recovery_requeues_then_stops_at_max_attempts(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="crashed-job", max_attempts=2)
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=1), now=NOW
    )

    recovered = repository.reclaim_expired_jobs(now=NOW + td(minutes=2))
    assert recovered[0].status is JobStatus.RETRY_PENDING
    repository.activate_retry_jobs(now=NOW + td(minutes=2))
    repository.claim_next_job(
        owner="worker-2",
        lease_until=NOW + td(minutes=3),
        now=NOW + td(minutes=2),
    )
    final = repository.reclaim_expired_jobs(now=NOW + td(minutes=4))

    assert final[0].status is JobStatus.FAILED_FINAL
    assert final[0].attempt_count == 2
    assert [
        attempt.outcome for attempt in repository.list_job_attempts("crashed-job")
    ] == [
        JobAttemptOutcome.LEASE_EXPIRED,
        JobAttemptOutcome.LEASE_EXPIRED,
    ]


def test_manual_rerun_creates_new_job_without_rewriting_old_history(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="old-job", max_attempts=1)
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=1), now=NOW
    )
    repository.reclaim_expired_jobs(now=NOW + td(minutes=2))
    before = repository.list_job_attempts("old-job")

    rerun = repository.rerun_job(
        "old-job",
        new_job_id="new-job",
        available_at=NOW + td(minutes=2),
        now=NOW + td(minutes=2),
    )

    assert rerun.job_id == "new-job"
    assert rerun.status is JobStatus.PENDING
    assert rerun.attempt_count == 0
    assert repository.get_job("old-job").status is JobStatus.FAILED_FINAL
    assert repository.list_job_attempts("old-job") == before


def test_artifact_upsert_is_idempotent_and_rejects_key_corruption(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)

    first = repository.upsert_artifact(_artifact(), now=NOW)
    second = repository.upsert_artifact(_artifact(), now=NOW + td(minutes=1))

    assert first == second
    with pytest.raises(IntegrityConflict, match="artifact key"):
        repository.upsert_artifact(
            _artifact(artifact_id="artifact-other", content_hash=HASH_B),
            now=NOW + td(minutes=2),
        )


def test_provider_call_reservation_is_exclusive_and_owner_checked(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    artifact = repository.upsert_artifact(_artifact(), now=NOW)

    first = repository.reserve_provider_call(
        _provider_request(),
        owner="worker-1",
        lease_until=NOW + td(minutes=5),
        available_at=NOW,
        now=NOW,
    )
    concurrent = repository.reserve_provider_call(
        _provider_request(),
        owner="worker-2",
        lease_until=NOW + td(minutes=5),
        available_at=NOW,
        now=NOW,
    )

    assert first.acquired is True
    assert concurrent.acquired is False
    assert first.record.attempt_count == 1
    with pytest.raises(LeaseConflict, match="provider call reservation"):
        repository.complete_provider_call(
            REQUEST_HASH,
            owner="worker-2",
            response_artifact_id=artifact.artifact_id,
            input_tokens=10,
            output_tokens=5,
            cost_microusd=25,
            now=NOW + td(minutes=1),
        )
    completed = repository.complete_provider_call(
        REQUEST_HASH,
        owner="worker-1",
        response_artifact_id=artifact.artifact_id,
        input_tokens=10,
        output_tokens=5,
        cost_microusd=25,
        now=NOW + td(minutes=1),
    )
    assert completed.status is ProviderCallStatus.SUCCEEDED
    assert completed.response_artifact_id == artifact.artifact_id


def test_provider_retry_and_expired_reservation_takeover(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    repository.reserve_provider_call(
        _provider_request(),
        owner="worker-1",
        lease_until=NOW + td(minutes=1),
        available_at=NOW,
        now=NOW,
    )
    failed = repository.fail_provider_call(
        REQUEST_HASH,
        owner="worker-1",
        retryable=True,
        available_at=NOW + td(minutes=5),
        error_code=ErrorCode.PROVIDER_UNAVAILABLE,
        error_message="api_key=very-secret\nprovider raw response",
        now=NOW + td(seconds=30),
    )
    assert failed.status is ProviderCallStatus.FAILED_RETRYABLE

    too_early = repository.reserve_provider_call(
        _provider_request(),
        owner="worker-2",
        lease_until=NOW + td(minutes=10),
        available_at=NOW + td(minutes=5),
        now=NOW + td(minutes=4),
    )
    acquired = repository.reserve_provider_call(
        _provider_request(),
        owner="worker-2",
        lease_until=NOW + td(minutes=10),
        available_at=NOW + td(minutes=5),
        now=NOW + td(minutes=5),
    )
    assert too_early.acquired is False
    assert acquired.acquired is True
    assert acquired.record.attempt_count == 2

    with _raw_connection(_database_path(tmp_path)) as connection:
        message = connection.execute(
            "SELECT last_error_message FROM provider_calls WHERE request_hash = ?",
            (REQUEST_HASH,),
        ).fetchone()[0]
    assert "very-secret" not in (message or "")
    assert "provider raw response" not in (message or "")


def test_expired_provider_reservation_recovers_verified_artifact(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    repository.reserve_provider_call(
        _provider_request(),
        owner="crashed-worker",
        lease_until=NOW + td(minutes=1),
        available_at=NOW,
        now=NOW,
    )
    artifact = repository.upsert_artifact(_artifact(), now=NOW + td(minutes=2))

    recovered = repository.reserve_provider_call(
        _provider_request(),
        owner="recovery-worker",
        lease_until=NOW + td(minutes=10),
        available_at=NOW,
        now=NOW + td(minutes=2),
        verified_artifact=VerifiedArtifact(
            artifact_key=artifact.artifact_key,
            content_hash=artifact.content_hash,
        ),
    )

    assert recovered.acquired is False
    assert recovered.recovered_from_artifact is True
    assert recovered.record.status is ProviderCallStatus.SUCCEEDED
    assert recovered.record.response_artifact_id == artifact.artifact_id


def test_stage_completion_commits_job_artifact_call_and_pipeline_together(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    assert repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    repository.create_job(
        job_id="stage-job",
        scope_key="video:video-1:TRANSCRIPT",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW
    )
    repository.reserve_provider_call(
        _provider_request(),
        owner="worker-1",
        lease_until=NOW + td(minutes=10),
        available_at=NOW,
        now=NOW,
    )
    artifact = _artifact(job_id="stage-job")

    with pytest.raises(IntegrityConflict, match="stage artifacts"):
        repository.complete_stage(
            job_id="stage-job",
            owner="worker-1",
            video_id="video-1",
            expected_status=PipelineStatus.METADATA_READY,
            target_status=PipelineStatus.TRANSCRIPT_READY,
            pipeline_version="pipeline-v1",
            artifacts=(_artifact(job_id=None),),
            provider_call=None,
            now=NOW + td(seconds=30),
        )
    assert repository.get_artifact_by_key(artifact.artifact_key) is None

    result = repository.complete_stage(
        job_id="stage-job",
        owner="worker-1",
        video_id="video-1",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="pipeline-v1",
        artifacts=(artifact,),
        provider_call=ProviderCallCompletion(
            request_hash=REQUEST_HASH,
            response_artifact_id=artifact.artifact_id,
            input_tokens=12,
            output_tokens=4,
            cost_microusd=50,
        ),
        now=NOW + td(minutes=1),
    )

    assert result.job.status is JobStatus.SUCCEEDED
    assert result.video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    assert result.artifacts[0].job_id == "stage-job"
    assert result.provider_call.status is ProviderCallStatus.SUCCEEDED


def test_stage_completion_rejects_a_job_for_another_target_stage(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    assert repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    _create_video_job(repository, job_id="wrong-stage-job")
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW
    )

    with pytest.raises(ConcurrencyConflict, match="target stage"):
        repository.complete_stage(
            job_id="wrong-stage-job",
            owner="worker-1",
            video_id="video-1",
            expected_status=PipelineStatus.METADATA_READY,
            target_status=PipelineStatus.TRANSCRIPT_READY,
            pipeline_version="pipeline-v1",
            artifacts=(),
            provider_call=None,
            now=NOW + td(minutes=1),
        )

    assert repository.get_job("wrong-stage-job").status is JobStatus.RUNNING
    assert (
        repository.get_video("video-1").pipeline_status is PipelineStatus.METADATA_READY
    )


@pytest.mark.parametrize(
    "failure_point",
    [
        "stage.after_artifacts",
        "stage.after_provider_call",
        "stage.after_pipeline",
    ],
)
def test_stage_completion_failure_rolls_back_every_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    repository = _repository_with_video(tmp_path)
    assert repository.advance_pipeline(
        "video-1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    repository.create_job(
        job_id="stage-job",
        scope_key="video:video-1:TRANSCRIPT",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW
    )
    repository.reserve_provider_call(
        _provider_request(),
        owner="worker-1",
        lease_until=NOW + td(minutes=10),
        available_at=NOW,
        now=NOW,
    )
    artifact = _artifact(job_id="stage-job")

    def fail_at_requested_boundary(point: str) -> None:
        if point == failure_point:
            raise RuntimeError("injected stage failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_at_requested_boundary)
    with pytest.raises(RuntimeError, match="injected stage failure"):
        repository.complete_stage(
            job_id="stage-job",
            owner="worker-1",
            video_id="video-1",
            expected_status=PipelineStatus.METADATA_READY,
            target_status=PipelineStatus.TRANSCRIPT_READY,
            pipeline_version="pipeline-v1",
            artifacts=(artifact,),
            provider_call=ProviderCallCompletion(
                request_hash=REQUEST_HASH,
                response_artifact_id=artifact.artifact_id,
                input_tokens=None,
                output_tokens=None,
                cost_microusd=None,
            ),
            now=NOW + td(minutes=1),
        )

    assert repository.get_artifact_by_key(artifact.artifact_key) is None
    assert (
        repository.get_provider_call(REQUEST_HASH).status is ProviderCallStatus.PENDING
    )
    assert (
        repository.get_video("video-1").pipeline_status is PipelineStatus.METADATA_READY
    )
    assert repository.get_job("stage-job").status is JobStatus.RUNNING
    assert repository.list_job_attempts("stage-job")[0].finished_at is None


def test_legacy_scoring_completion_without_summary_fails_before_writes(
    tmp_path: Path,
) -> None:
    runtime, _ = _trusted_scoring_runtime(tmp_path)
    _trusted_scoring_job(runtime)
    before_files = set(runtime._data_root.rglob("*"))

    with pytest.raises(IntegrityConflict, match="runtime trusted persistence entry"):
        runtime._repository.complete_stage(
            job_id="scoring-job",
            owner="worker-1",
            video_id="video-1",
            expected_status=PipelineStatus.TRANSCRIPT_READY,
            target_status=PipelineStatus.SCORED,
            pipeline_version="pipeline-v1",
            artifacts=(),
            provider_call=None,
            now=NOW + td(minutes=1),
        )

    assert set(runtime._data_root.rglob("*")) == before_files
    _assert_no_trusted_scoring_success(runtime)


def test_trusted_scoring_persistence_commits_summary_artifacts_and_calls_atomically(
    tmp_path: Path,
) -> None:
    runtime, _ = _trusted_scoring_runtime(tmp_path)
    scoring_input, success, now = _trusted_scoring_job(runtime)

    result = _trusted_persistence_entry(runtime, now=now).persist_success(success)

    assert result.job.status is JobStatus.SUCCEEDED
    assert result.video.pipeline_status is PipelineStatus.SCORED
    assert result.video.score == 7.5
    assert result.video.should_summarize is True
    assert {artifact.kind for artifact in result.artifacts} == {
        ArtifactKind.SCORING_RAW,
        ArtifactKind.SCORING_STRUCTURED,
    }
    assert result.provider_call is not None
    assert result.provider_call.status is ProviderCallStatus.SUCCEEDED
    with _raw_connection(runtime._data_root / "state.sqlite") as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE video_id = 'video-1'"
            ).fetchone()[0]
            == 2
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM provider_calls WHERE status = 'SUCCEEDED'"
            ).fetchone()[0]
            == 2
        )
    assert (
        runtime._repository.get_artifact_by_key(
            f"scoring/{scoring_input.request_hash}/raw"
        )
        is not None
    )
    assert (
        runtime._repository.get_artifact_by_key(
            f"scoring/{scoring_input.request_hash}/structured"
        )
        is not None
    )


def test_non_scoring_stage_rejects_a_scoring_summary(tmp_path: Path) -> None:
    repository = _repository_with_video(tmp_path)
    _create_video_job(repository, job_id="metadata-job")
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=10), now=NOW
    )

    with pytest.raises(IntegrityConflict, match="scoring summary"):
        repository.complete_stage(
            job_id="metadata-job",
            owner="worker-1",
            video_id="video-1",
            expected_status=PipelineStatus.DISCOVERED,
            target_status=PipelineStatus.METADATA_READY,
            pipeline_version="pipeline-v1",
            artifacts=(),
            provider_call=None,
            now=NOW + td(minutes=1),
            scoring_summary=ScoringSummaryWrite(score=7.5, should_summarize=True),
        )
    assert repository.get_video("video-1").score is None
    assert repository.get_job("metadata-job").status is JobStatus.RUNNING


def test_trusted_scoring_sqlite_rollback_has_no_partial_success(
    tmp_path: Path,
) -> None:
    runtime, _ = _trusted_scoring_runtime(tmp_path)
    _, success, now = _trusted_scoring_job(runtime)

    def fail_after_pipeline(point: str) -> None:
        if point == "atomic_register.after_pipeline":
            raise RuntimeError("injected trusted registration failure")

    runtime._repository._inject_failure = fail_after_pipeline  # type: ignore[method-assign]
    with pytest.raises(
        ScoringPersistenceError, match="injected trusted registration failure"
    ):
        _trusted_persistence_entry(runtime, now=now).persist_success(success)

    _assert_no_trusted_scoring_success(runtime)
    assert tuple((runtime._data_root / "scoring").rglob("*.json"))


def test_trusted_scoring_same_success_is_idempotent_without_duplicate_outputs(
    tmp_path: Path,
) -> None:
    runtime, _ = _trusted_scoring_runtime(tmp_path)
    _, success, now = _trusted_scoring_job(runtime)
    entry = _trusted_persistence_entry(runtime, now=now)

    first = entry.persist_success(success)
    second = entry.persist_success(success)

    assert second == first
    with _raw_connection(runtime._data_root / "state.sqlite") as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE video_id = 'video-1'"
            ).fetchone()[0]
            == 2
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM provider_calls").fetchone()[0] == 2
        )
    assert len(tuple((runtime._data_root / "scoring").rglob("*.json"))) == 2


def test_artifact_deletion_cas_and_expiry_listing_are_index_only(
    tmp_path: Path,
) -> None:
    repository = _repository_with_video(tmp_path)
    earlier = repository.upsert_artifact(
        _artifact(
            artifact_id="expired-z",
            artifact_key="video:video-1:audio:expired-z",
            kind=ArtifactKind.AUDIO,
            retention_class=RetentionClass.EPHEMERAL_AUDIO,
            expires_at=NOW - td(days=2),
        ),
        now=NOW,
    )
    later = repository.upsert_artifact(
        _artifact(
            artifact_id="expired-a",
            artifact_key="video:video-1:audio:expired-a",
            content_hash=HASH_B,
            kind=ArtifactKind.AUDIO,
            retention_class=RetentionClass.EPHEMERAL_AUDIO,
            expires_at=NOW - td(days=1),
        ),
        now=NOW,
    )
    repository.upsert_artifact(
        _artifact(
            artifact_id="unexpired",
            artifact_key="video:video-1:audio:unexpired",
            content_hash="c" * 64,
            kind=ArtifactKind.AUDIO,
            retention_class=RetentionClass.EPHEMERAL_AUDIO,
            expires_at=NOW + td(days=1),
        ),
        now=NOW,
    )

    expired = repository.list_expired_artifacts(
        RetentionClass.EPHEMERAL_AUDIO,
        now=NOW,
        limit=10,
    )
    assert tuple(record.artifact_id for record in expired) == ("expired-z", "expired-a")
    assert repository.list_expired_artifacts(
        RetentionClass.EPHEMERAL_AUDIO,
        now=NOW,
        limit=1,
    ) == (earlier,)
    assert not repository.mark_artifact_deleted(
        earlier.artifact_id,
        expected_content_hash=HASH_B,
        now=NOW,
    )
    assert not repository.mark_artifact_deleted(
        "unknown-artifact",
        expected_content_hash=HASH_A,
        now=NOW,
    )
    assert repository.mark_artifact_deleted(
        earlier.artifact_id,
        expected_content_hash=HASH_A,
        now=NOW,
    )
    assert not repository.mark_artifact_deleted(
        earlier.artifact_id,
        expected_content_hash=HASH_A,
        now=NOW + td(minutes=1),
    )
    assert repository.list_expired_artifacts(
        RetentionClass.EPHEMERAL_AUDIO,
        now=NOW,
        limit=10,
    ) == (later,)


def test_weekly_report_upsert_uses_stable_period_and_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    first = repository.upsert_report(
        ReportWrite(
            report_id="report-1",
            timezone="Asia/Shanghai",
            iso_year=2026,
            iso_week=29,
            relative_path=None,
            content_hash=None,
            status=ReportStatus.PENDING,
        ),
        now=NOW,
    )
    updated = repository.upsert_report(
        ReportWrite(
            report_id="report-duplicate-id",
            timezone="Asia/Shanghai",
            iso_year=2026,
            iso_week=29,
            relative_path="reports/2026-W29.md",
            content_hash=HASH_A,
            status=ReportStatus.WRITTEN,
        ),
        now=NOW + td(minutes=1),
    )
    assert first.report_id == updated.report_id == "report-1"
    assert updated.status is ReportStatus.WRITTEN

    def fail_before_commit(point: str) -> None:
        if point == "report.before_commit":
            raise RuntimeError("injected report failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_before_commit)
    with pytest.raises(RuntimeError, match="injected report failure"):
        repository.upsert_report(
            ReportWrite(
                report_id="report-2",
                timezone="UTC",
                iso_year=2026,
                iso_week=29,
                relative_path=None,
                content_hash=None,
                status=ReportStatus.PENDING,
            ),
            now=NOW,
        )
    assert repository.get_report(timezone="UTC", iso_year=2026, iso_week=29) is None
