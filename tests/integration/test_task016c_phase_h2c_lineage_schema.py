"""TASK-016C Phase H2-C — scoring lineage schema v2 (migration/cutover/reclaim).

RED tests for the approved migration ``002_add_scoring_lineage.sql``, the
repository-derived immutable lineage generation, the transaction-local CAS
readers, and the frozen pre-v2 cutover / generic reclaim contract.
"""

from __future__ import annotations

import inspect
import sqlite3
from datetime import UTC, datetime
from datetime import timedelta as td
from importlib import resources
from pathlib import Path

import pytest

from youtube_intel import state as state_mod
from youtube_intel.domain import JobStatus, ProcessingStage
from youtube_intel.runtime import _database_check
from youtube_intel.state import (
    JobAttemptOutcome,
    JobType,
    MigrationError,
    SQLiteStateRepository,
)

NOW = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
LINEAGE_V1 = "task016c-scoring-lineage-v1"


def _database_path(tmp_path: Path) -> Path:
    return tmp_path / "state.sqlite3"


def _raw_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _migration_001_only() -> tuple[state_mod._Migration, ...]:
    name = "001_initial.sql"
    sql_bytes = (
        resources.files("youtube_intel").joinpath("migrations", name).read_bytes()
    )
    import hashlib

    return (
        state_mod._Migration(
            version=1,
            name=name,
            sql=sql_bytes.decode("utf-8"),
            checksum=hashlib.sha256(sql_bytes).hexdigest(),
        ),
    )


def _initialized_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> SQLiteStateRepository:
    """Initialize a v1 database using only migration 001."""

    repository = SQLiteStateRepository(_database_path(tmp_path))
    monkeypatch.setattr(repository, "_load_migrations", _migration_001_only)
    repository.initialize(now=NOW)
    monkeypatch.undo()
    return repository


def _seed_video(connection: sqlite3.Connection, video_id: str = "video-1") -> None:
    now_text = state_mod.format_utc_datetime(NOW)
    connection.execute(
        "INSERT INTO videos (video_id, channel_id, pipeline_status, "
        "pipeline_version, discovered_at, updated_at) "
        "VALUES (?, ?, 'DISCOVERED', 'pipeline-v1', ?, ?)",
        (video_id, "UC_TEST", now_text, now_text),
    )


def _seed_job(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    status: str = "SUCCEEDED",
    target_stage: str = "SCORING",
    video_id: str | None = "video-1",
    lease_owner: str | None = None,
    lease_until: datetime | None = None,
) -> None:
    now_text = state_mod.format_utc_datetime(NOW)
    lease_text = (
        None if lease_until is None else state_mod.format_utc_datetime(lease_until)
    )
    finished = now_text if status in {"SUCCEEDED", "FAILED_FINAL"} else None
    connection.execute(
        "INSERT INTO jobs (job_id, scope_key, video_id, job_type, target_stage, "
        "pipeline_version, status, attempt_count, max_attempts, available_at, "
        "lease_owner, lease_until, created_at, updated_at, finished_at) "
        "VALUES (:job_id, :scope_key, :video_id, :job_type, :target_stage, "
        "'pipeline-v1', :status, 1, 3, :available_at, :lease_owner, :lease_until, "
        ":created_at, :updated_at, :finished_at)",
        {
            "job_id": job_id,
            "scope_key": f"video:{video_id}:{target_stage}",
            "video_id": video_id,
            "job_type": "VIDEO_STAGE" if video_id is not None else "WEEKLY_REPORT",
            "target_stage": target_stage,
            "status": status,
            "available_at": now_text,
            "lease_owner": lease_owner,
            "lease_until": lease_text,
            "created_at": now_text,
            "updated_at": now_text,
            "finished_at": finished,
        },
    )
    if status in {"RUNNING"}:
        connection.execute(
            "INSERT INTO job_attempts (job_id, attempt_number, lease_owner, "
            "started_at, lease_until) VALUES (?, 1, ?, ?, ?)",
            (job_id, lease_owner, now_text, lease_text),
        )


# ---------------------------------------------------------------------------
# Migration 002: upgrade, columns, FKs, CHECKs, indexes, user_version
# ---------------------------------------------------------------------------


def test_v1_database_upgrades_through_v11_with_exact_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = _initialized_repository(tmp_path, monkeypatch)
    with _raw_connection(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        _seed_video(connection)
        _seed_job(connection, job_id="legacy-job")

    version = repository.initialize(now=NOW + td(hours=1))

    assert version.version == 11
    assert version.name == "011_add_topic_timeline.sql"
    with _raw_connection(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 11
        history = tuple(
            connection.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            )
        )
    assert [(row["version"], row["name"]) for row in history] == [
        (1, "001_initial.sql"),
        (2, "002_add_scoring_lineage.sql"),
        (3, "003_add_deep_analysis_persistence.sql"),
        (4, "004_add_provider_dispatch_state.sql"),
        (5, "005_add_product_orchestration.sql"),
        (6, "006_add_intelligence_domain.sql"),
        (7, "007_add_intelligence_claim_classification.sql"),
        (8, "008_add_preference_feedback.sql"),
        (9, "009_add_source_policy_filtering.sql"),
        (10, "010_add_personalized_distillation.sql"),
        (11, "011_add_topic_timeline.sql"),
    ]


def test_fresh_database_applies_all_migrations_to_v11(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    version = repository.initialize(now=NOW)
    assert version.version == 11
    assert repository.schema_version().version == 11


def test_migration_002_adds_exact_columns(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    with _raw_connection(_database_path(tmp_path)) as connection:
        job_columns = tuple(
            row["name"] for row in connection.execute('PRAGMA table_info("jobs")')
        )
        video_columns = tuple(
            row["name"] for row in connection.execute('PRAGMA table_info("videos")')
        )
    assert job_columns[-3:] == (
        "authoritative_scoring_artifact_key",
        "scoring_success_provenance",
        "scoring_lineage_version",
    )
    assert video_columns[-1] == "authoritative_scoring_job_id"
    # No unauthorized column exists.
    assert "expected_authoritative_scoring_job_id" not in job_columns


def test_migration_002_adds_exact_foreign_keys(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    with _raw_connection(_database_path(tmp_path)) as connection:
        jobs_fks = {
            (row["from"], row["table"], row["to"], row["on_delete"])
            for row in connection.execute('PRAGMA foreign_key_list("jobs")')
        }
        videos_fks = {
            (row["from"], row["table"], row["to"], row["on_delete"])
            for row in connection.execute('PRAGMA foreign_key_list("videos")')
        }
    assert (
        "authoritative_scoring_artifact_key",
        "artifacts",
        "artifact_key",
        "RESTRICT",
    ) in jobs_fks
    assert (
        "authoritative_scoring_job_id",
        "jobs",
        "job_id",
        "RESTRICT",
    ) in videos_fks


def test_migration_002_check_constraints_reject_unknown_literals(
    tmp_path: Path,
) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    with _raw_connection(path) as connection:
        _seed_video(connection)
        _seed_job(connection, job_id="job-check")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE jobs SET scoring_success_provenance = 'OTHER' "
                "WHERE job_id = 'job-check'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE jobs SET scoring_lineage_version = 'bogus' "
                "WHERE job_id = 'job-check'"
            )
        connection.execute(
            "UPDATE jobs SET scoring_success_provenance = 'PRIMARY', "
            "scoring_lineage_version = ? WHERE job_id = 'job-check'",
            (LINEAGE_V1,),
        )
        row = connection.execute(
            "SELECT scoring_success_provenance, scoring_lineage_version "
            "FROM jobs WHERE job_id = 'job-check'"
        ).fetchone()
    assert row["scoring_success_provenance"] == "PRIMARY"
    assert row["scoring_lineage_version"] == LINEAGE_V1


def test_migration_002_partial_unique_indexes_forbid_shared_pointers(
    tmp_path: Path,
) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    with _raw_connection(path) as connection:
        index_names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND sql IS NOT NULL"
            )
        }
        assert "uq_jobs_authoritative_scoring_artifact_key" in index_names
        assert "uq_videos_authoritative_scoring_job_id" in index_names

        _seed_video(connection)
        _seed_video(connection, "video-2")
        _seed_job(connection, job_id="job-a", status="FAILED_FINAL")
        _seed_job(connection, job_id="job-b", status="FAILED_FINAL")
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, "
            "kind, storage_root, relative_path, content_hash, producer_version, "
            "retention_class, created_at) VALUES "
            "('artifact-a', 'scoring/x/structured', 'video-1', 'job-a', "
            "'scoring_structured', 'DATA', 'scoring/x/structured.json', ?, "
            "'scoring-structured-content-quality-v1', 'LONG_LIVED', ?)",
            ("a" * 64, state_mod.format_utc_datetime(NOW)),
        )
        connection.execute(
            "UPDATE jobs SET authoritative_scoring_artifact_key = "
            "'scoring/x/structured' WHERE job_id = 'job-a'"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE jobs SET authoritative_scoring_artifact_key = "
                "'scoring/x/structured' WHERE job_id = 'job-b'"
            )
        connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = 'job-a' "
            "WHERE video_id = 'video-1'"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE videos SET authoritative_scoring_job_id = 'job-a' "
                "WHERE video_id = 'video-2'"
            )
        # NULL pointers are exempt from the partial unique indexes.
        connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = NULL "
            "WHERE video_id = 'video-1'"
        )


def test_migration_002_foreign_keys_restrict_pointer_deletes(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    with _raw_connection(path) as connection:
        _seed_video(connection)
        _seed_job(connection, job_id="job-fk", status="FAILED_FINAL")
        connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = 'job-fk' "
            "WHERE video_id = 'video-1'"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM jobs WHERE job_id = 'job-fk'")
        connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = NULL "
            "WHERE video_id = 'video-1'"
        )
        connection.execute("DELETE FROM jobs WHERE job_id = 'job-fk'")


def test_migration_002_does_not_backfill_historical_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = _initialized_repository(tmp_path, monkeypatch)
    with _raw_connection(path) as connection:
        _seed_video(connection)
        _seed_job(connection, job_id="old-succeeded")
        _seed_job(connection, job_id="old-final", status="FAILED_FINAL")

    repository.initialize(now=NOW + td(hours=1))

    with _raw_connection(path) as connection:
        rows = {
            row["job_id"]: row
            for row in connection.execute(
                "SELECT job_id, scoring_lineage_version, "
                "scoring_success_provenance, authoritative_scoring_artifact_key "
                "FROM jobs"
            )
        }
        video_row = connection.execute(
            "SELECT authoritative_scoring_job_id FROM videos WHERE video_id = 'video-1'"
        ).fetchone()
    for row in rows.values():
        assert row["scoring_lineage_version"] is None
        assert row["scoring_success_provenance"] is None
        assert row["authoritative_scoring_artifact_key"] is None
    assert video_row["authoritative_scoring_job_id"] is None


def test_unsupported_schema_versions_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)

    # A database claiming an unknown newer migration fails closed.
    with _raw_connection(path) as connection:
        connection.execute(
            "INSERT INTO schema_migrations (version, name, checksum, applied_at) "
            "VALUES (12, '012_future.sql', ?, ?)",
            ("f" * 64, NOW.isoformat()),
        )
        connection.execute("PRAGMA user_version = 12")
    with pytest.raises(MigrationError, match="unsupported"):
        repository.initialize(now=NOW)
    with _raw_connection(path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version = 12")
        connection.execute("PRAGMA user_version = 11")

    # A malformed history (missing user_version agreement) fails closed.
    with _raw_connection(path) as connection:
        connection.execute("PRAGMA user_version = 0")
    with pytest.raises(MigrationError, match="migration history mismatch"):
        repository.initialize(now=NOW)


def test_doctor_database_check_accepts_exactly_version_11(tmp_path: Path) -> None:
    path = _database_path(tmp_path)
    repository = SQLiteStateRepository(path)
    repository.initialize(now=NOW)
    assert _database_check(path).status == "PASS"

    with _raw_connection(path) as connection:
        connection.execute("PRAGMA user_version = 1")
    assert _database_check(path).status == "FAIL"
    with _raw_connection(path) as connection:
        connection.execute("PRAGMA user_version = 12")
    assert _database_check(path).status == "FAIL"
    with _raw_connection(path) as connection:
        connection.execute("PRAGMA user_version = 11")
    assert _database_check(path).status == "PASS"


# ---------------------------------------------------------------------------
# Job creation: repository-derived immutable lineage generation
# ---------------------------------------------------------------------------


def _create_scoring_job(
    repository: SQLiteStateRepository, *, job_id: str, stage: str = "SCORING"
) -> None:
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:video-1:{stage}",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage(stage),
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )


def test_new_scoring_job_receives_lineage_v1(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _discovery_batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    _create_scoring_job(repository, job_id="scoring-job")
    job = repository.get_job("scoring-job")
    assert job.scoring_lineage_version == LINEAGE_V1
    assert job.scoring_success_provenance is None
    assert job.authoritative_scoring_artifact_key is None
    video = repository.get_video("video-1")
    assert video.authoritative_scoring_job_id is None


def _discovery_batch(video_id: str):
    from youtube_intel.domain import (
        DiscoveryBatch,
        DiscoveryCursor,
        ProviderCallMetadata,
    )

    return DiscoveryBatch(
        channel_id="UC_TEST",
        video_ids=(video_id,),
        next_cursor=DiscoveryCursor(
            channel_id="UC_TEST",
            last_checked_at=NOW,
            latest_published_at=NOW,
            latest_video_id=video_id,
            provider_cursor="cursor-1",
        ),
        call=ProviderCallMetadata(
            provider="fake-source", started_at=NOW, finished_at=NOW
        ),
    )


def test_non_scoring_jobs_receive_null_lineage(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _discovery_batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    for stage in ("METADATA", "TRANSCRIPT", "ANALYSIS", "NOTE_WRITE"):
        _create_scoring_job(repository, job_id=f"job-{stage}", stage=stage)
        assert repository.get_job(f"job-{stage}").scoring_lineage_version is None
    repository.create_job(
        job_id="weekly-job",
        scope_key="weekly:UC_TEST:2026-W34:report",
        video_id=None,
        job_type=JobType.WEEKLY_REPORT,
        target_stage=ProcessingStage.WEEKLY_REPORT,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    assert repository.get_job("weekly-job").scoring_lineage_version is None


def test_caller_cannot_control_lineage_version(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    signature = inspect.signature(repository.create_job)
    assert not any("lineage" in name for name in signature.parameters)
    with pytest.raises(TypeError):
        repository.create_job(
            job_id="forged",
            scope_key="video:video-1:SCORING",
            video_id="video-1",
            job_type=JobType.VIDEO_STAGE,
            target_stage=ProcessingStage.SCORING,
            pipeline_version="pipeline-v1",
            max_attempts=3,
            available_at=NOW,
            now=NOW,
            scoring_lineage_version=None,  # type: ignore[call-arg]
        )


def test_lineage_version_is_immutable_through_terminal_paths(
    tmp_path: Path,
) -> None:
    from youtube_intel.domain import ErrorCode

    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _discovery_batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    _create_scoring_job(repository, job_id="scoring-job")
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=5), now=NOW
    )
    repository.fail_job(
        "scoring-job",
        owner="worker-1",
        error_code=ErrorCode.LOCAL_RESOURCE,
        error_message="boom",
        retry_at=None,
        now=NOW + td(minutes=1),
    )
    assert repository.get_job("scoring-job").scoring_lineage_version == LINEAGE_V1


# ---------------------------------------------------------------------------
# Transaction-local readers
# ---------------------------------------------------------------------------


def test_transaction_local_readers_use_given_connection(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _discovery_batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    _create_scoring_job(repository, job_id="scoring-job")

    connection = repository._connect()
    try:
        job = repository._read_job_in_transaction(connection, "scoring-job")
        assert job is not None
        assert job.job_id == "scoring-job"
        assert job.scoring_lineage_version == LINEAGE_V1
        assert repository._read_job_in_transaction(connection, "missing") is None
        video = repository._read_video_in_transaction(connection, "video-1")
        assert video is not None
        assert video.video_id == "video-1"
        assert video.authoritative_scoring_job_id is None
        assert repository._read_video_in_transaction(connection, "missing") is None

        # The reader observes the transaction snapshot, not a separate commit.
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE jobs SET scoring_success_provenance = 'PRIMARY' "
            "WHERE job_id = 'scoring-job'"
        )
        inside = repository._read_job_in_transaction(connection, "scoring-job")
        assert inside.scoring_success_provenance == "PRIMARY"
        connection.rollback()
        rolled_back = repository._read_job_in_transaction(connection, "scoring-job")
        assert rolled_back.scoring_success_provenance is None
    finally:
        connection.close()

    # The public surface still shows the committed state.
    assert repository.get_job("scoring-job").scoring_success_provenance is None


# ---------------------------------------------------------------------------
# Pre-v2 cutover and generic reclaim contract
# ---------------------------------------------------------------------------


def test_expired_pre_v2_scoring_reclaim_terminal_keeps_null_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = _initialized_repository(tmp_path, monkeypatch)
    with _raw_connection(path) as connection:
        _seed_video(connection)
        _seed_job(
            connection,
            job_id="expired-scoring",
            status="RUNNING",
            lease_owner="worker-1",
            lease_until=NOW - td(minutes=1),
        )

    # Normal business bootstrap migrates the old valid v1 database to v2
    # before operation; the H1 reclaim then runs under schema v2 with every
    # historical lineage column still NULL.
    repository.initialize(now=NOW)

    recovered = repository.reclaim_expired_jobs(now=NOW)

    assert len(recovered) == 1
    job = recovered[0]
    assert job.status is JobStatus.FAILED_FINAL
    assert job.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert job.last_error_message == (
        "scoring provider outcome is unknown after lease expiry"
    )
    assert job.lease_owner is None
    assert job.lease_until is None
    stored = repository.get_job("expired-scoring")
    assert stored.scoring_lineage_version is None
    assert stored.scoring_success_provenance is None
    assert stored.authoritative_scoring_artifact_key is None
    attempts = repository.list_job_attempts("expired-scoring")
    assert attempts[0].outcome is JobAttemptOutcome.FAILED_FINAL


def test_reclaim_tuple_is_ordered_heterogeneous_and_committed(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        _discovery_batch("video-1"),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=NOW,
    )
    repository.create_job(
        job_id="scoring-expired",
        scope_key="video:video-1:SCORING",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    repository.claim_next_job(
        owner="worker-1", lease_until=NOW + td(minutes=1), now=NOW
    )
    repository.create_job(
        job_id="metadata-expired",
        scope_key="video:video-1:METADATA",
        video_id="video-1",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.METADATA,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    with _raw_connection(_database_path(tmp_path)) as connection:
        connection.execute(
            "UPDATE jobs SET status = 'RUNNING', attempt_count = 1, "
            "lease_owner = 'worker-1', lease_until = ? "
            "WHERE job_id = 'metadata-expired'",
            (state_mod.format_utc_datetime(NOW + td(minutes=2)),),
        )
        connection.execute(
            "INSERT INTO job_attempts (job_id, attempt_number, lease_owner, "
            "started_at, lease_until) VALUES "
            "('metadata-expired', 1, 'worker-1', ?, ?)",
            (
                state_mod.format_utc_datetime(NOW),
                state_mod.format_utc_datetime(NOW + td(minutes=2)),
            ),
        )
    recovered = repository.reclaim_expired_jobs(now=NOW + td(minutes=3))

    assert isinstance(recovered, tuple)
    assert [job.job_id for job in recovered] == [
        "scoring-expired",
        "metadata-expired",
    ]
    scoring, metadata = recovered
    assert scoring.status is JobStatus.FAILED_FINAL
    assert scoring.last_error_code == "UNKNOWN_PROVIDER_STATE"
    assert metadata.status is JobStatus.RETRY_PENDING
    assert metadata.last_error_code == "LEASE_EXPIRED"
    # Committed state is observable through a fresh public read.
    assert repository.get_job("scoring-expired").status is JobStatus.FAILED_FINAL
    assert repository.get_job("metadata-expired").status is JobStatus.RETRY_PENDING


def test_reclaim_with_no_expired_rows_returns_empty_tuple(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(_database_path(tmp_path))
    repository.initialize(now=NOW)
    assert repository.reclaim_expired_jobs(now=NOW) == ()


def test_live_pre_v2_running_job_keeps_null_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _database_path(tmp_path)
    repository = _initialized_repository(tmp_path, monkeypatch)
    with _raw_connection(path) as connection:
        _seed_video(connection)
        _seed_job(
            connection,
            job_id="live-scoring",
            status="RUNNING",
            lease_owner="worker-1",
            lease_until=NOW + td(minutes=5),
        )

    repository.initialize(now=NOW)

    job = repository.get_job("live-scoring")
    assert job.status is JobStatus.RUNNING
    assert job.scoring_lineage_version is None
    # No reclamation happens while the lease is valid.
    assert repository.reclaim_expired_jobs(now=NOW) == ()
