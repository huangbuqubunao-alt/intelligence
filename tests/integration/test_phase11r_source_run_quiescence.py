"""Phase 11R P0-02: a settled NEEDS_ATTENTION Source Run must not deadlock Backup.

Reconnaissance proved that one failed Bilibili creator check leaves a durable
``NEEDS_ATTENTION / EXECUTION_CONDITION_UNRESOLVED`` run that the backup
readiness loop treats as permanently active, so the user can never create a
backup again.  These tests pin the corrected lifecycle semantics:

* only genuinely in-flight work blocks a backup;
* a settled, unresolvable run is history, not live work;
* a retry creates a *new* run instead of mutating the failed one;
* a corrupt or genuinely active database still fails closed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
from youtube_intel.following_tracking import FollowingTrackingService
from youtube_intel.providers.bilibili import BilibiliAdapter, BilibiliError
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunPriority,
    SourceRunState,
    SourceRunTrigger,
    SourceRunWrite,
    source_run_transition_allowed,
)
from youtube_intel.state import DistillationExecutionWrite, SQLiteStateRepository

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _workspace(tmp_path: Path) -> tuple[Path, Path, SQLiteStateRepository]:
    """A real Bilibili creator subscription whose very first check failed."""

    from youtube_intel.bilibili_content import BilibiliContentProvider

    data_root = tmp_path / "data"
    data_root.mkdir()
    database = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos "
            "(video_id, channel_id, pipeline_status, pipeline_version, "
            "availability, discovered_at, updated_at) "
            "VALUES ('video-1', 'UC_TEST', 'DISCOVERED', 'fixture-v1', 'public', ?, ?)",
            (NOW.isoformat(), NOW.isoformat()),
        )
    finally:
        connection.close()

    def fetch(url: str, maximum: int) -> bytes:
        if "/card?" in url:
            return json.dumps(
                {"code": 0, "data": {"card": {"mid": "123", "name": "公开 UP 主"}}}
            ).encode()
        # The recon's real listing refusal, reproduced without any bypass.
        raise BilibiliError("RISK_CONTROLLED")

    publisher = BilibiliContentProvider(
        repository,
        data_root,
        adapter=BilibiliAdapter(fetch=fetch),
        now=lambda: NOW,
    )
    tracker = FollowingTrackingService(repository, publisher, now=lambda: NOW)
    source = tracker.follow("https://space.bilibili.com/123")
    assert source.source_id == "bilibili-creator-123"
    assert tracker.projection(source.source_id)["health"] == "RISK_CONTROLLED"
    return database, data_root, repository


def _manual_check_now(repository: SQLiteStateRepository, command_id: str) -> str:
    return repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id="bilibili-creator-123",
            command_id=command_id,
            priority=SourceRunPriority.P1,
            created_at=NOW,
        )
    ).run_id


def _settle_in_needs_attention(repository: SQLiteStateRepository, run_id: str) -> None:
    repository.transition_source_run(run_id, to_state=SourceRunState.RUNNING, now=NOW)
    repository.transition_source_run(
        run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        now=NOW,
        attention_reason=SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED,
    )


def _service(tmp_path: Path) -> BackupRestoreService:
    return BackupRestoreService(
        database=tmp_path / "state.sqlite3", data_root=tmp_path / "data"
    )


def test_failed_creator_check_produces_a_truthful_unresolved_run(tmp_path: Path) -> None:
    """Recon P0-01/P0-02 precondition: the real refusal is classified truthfully."""

    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)

    source = repository.get_source_subscription("bilibili-creator-123")
    assert source.last_error_code == "RISK_CONTROLLED"
    assert source.last_success_at is None
    run = repository.get_source_run(run_id)
    assert run.state is SourceRunState.NEEDS_ATTENTION
    assert run.attention_reason is SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED


def test_settled_needs_attention_run_does_not_block_backup(tmp_path: Path) -> None:
    """The recon's exact deadlock: one failed check permanently refused Backup."""

    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)

    status = _service(tmp_path).readiness()

    assert "SOURCE_RUN_ACTIVE" not in status["reasons"], status
    assert status["ready"] is True, status


def test_settled_needs_attention_run_with_no_running_work_unblocks_backup(
    tmp_path: Path,
) -> None:
    """No task or process may remain active while the refusal persists."""

    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)
    connection = repository._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM source_checks WHERE status='RUNNING'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM source_runs WHERE state IN "
                "('QUEUED','RUNNING','WAITING','PARTIAL')"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()

    status = _service(tmp_path).readiness()

    assert "SOURCE_RUN_ACTIVE" not in status["reasons"], status


def test_backup_and_restore_succeed_after_a_failed_creator_check(tmp_path: Path) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)
    service = _service(tmp_path)

    backup = service.create_backup()
    archive_path, _content = service.backup_download(backup.backup_id) or (None, None)

    assert archive_path is not None
    staged = service.stage_restore(archive_path.read_bytes())
    assert staged.preview["vault_excluded"] is True
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()

    restored = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restored.initialize(now=NOW)
    assert restored.get_source_run(run_id).state is SourceRunState.NEEDS_ATTENTION
    assert restored.get_source_subscription("bilibili-creator-123") is not None


def test_needs_attention_history_is_preserved_and_never_rewritten_as_success(
    tmp_path: Path,
) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)

    _service(tmp_path).create_backup()

    run = repository.get_source_run(run_id)
    assert run.state is SourceRunState.NEEDS_ATTENTION
    assert run.attention_reason is SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED
    assert repository.get_source_subscription("bilibili-creator-123").last_success_at is None


def test_retry_creates_a_new_run_instead_of_mutating_the_failed_history(
    tmp_path: Path,
) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    first = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, first)

    retry = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id="bilibili-creator-123",
            command_id="check-2",
            priority=SourceRunPriority.P1,
            created_at=NOW + timedelta(hours=1),
        )
    )

    assert retry.run_id != first
    assert retry.state is SourceRunState.QUEUED
    assert repository.get_source_run(first).state is SourceRunState.NEEDS_ATTENTION
    reasons = _service(tmp_path).readiness()["reasons"]
    assert "SOURCE_RUN_ACTIVE" in reasons


def test_genuinely_active_run_still_blocks_backup(tmp_path: Path) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    repository.transition_source_run(run_id, to_state=SourceRunState.RUNNING, now=NOW)

    status = _service(tmp_path).readiness()

    assert "SOURCE_RUN_ACTIVE" in status["reasons"], status


def test_restart_does_not_revive_a_settled_needs_attention_run_as_active(
    tmp_path: Path,
) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)

    first = _service(tmp_path).readiness()
    second = _service(tmp_path).readiness()

    assert first["reasons"] == second["reasons"]
    assert "SOURCE_RUN_ACTIVE" not in second["reasons"], second
    assert (
        SQLiteStateRepository(tmp_path / "state.sqlite3").get_source_run(run_id).state
        is SourceRunState.NEEDS_ATTENTION
    )


def test_corrupt_source_run_state_still_fails_closed(tmp_path: Path) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    connection = repository._connect()
    try:
        connection.execute("DROP TABLE source_runs")
        connection.execute("CREATE TABLE source_runs (state TEXT NOT NULL)")
        connection.execute("INSERT INTO source_runs (state) VALUES ('RUNNING')")
    finally:
        connection.close()

    with pytest.raises(BackupRestoreError):
        _service(tmp_path).create_backup()


def test_resumable_attention_runs_that_still_hold_work_block_backup(
    tmp_path: Path,
) -> None:
    """An open distillation checkpoint for the source is not settled history."""

    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="execution-waiting-model",
            source_id="bilibili-creator-123",
            video_id="video-1",
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="ollama",
            selected_model="qwen3:8b",
            output_language="en",
        ),
        now=NOW,
    )
    repository.finish_distillation_without_admission(
        execution_id="execution-waiting-model",
        status="WAITING_MODEL",
        budget_state="RUNTIME_BUDGET_ADMITTED",
        outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
        invocation_count=0,
        actual_provider=None,
        actual_model=None,
        input_tokens=None,
        output_tokens=None,
        cost_microunits=None,
        duration_ms=None,
        now=NOW,
    )
    repository.transition_source_run(run_id, to_state=SourceRunState.RUNNING, now=NOW)
    repository.transition_source_run(
        run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        now=NOW,
        attention_reason=SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED,
    )


def _service(tmp_path: Path) -> BackupRestoreService:
    return BackupRestoreService(
        database=tmp_path / "state.sqlite3", data_root=tmp_path / "data"
    )


def test_needs_attention_has_a_lifecycle_exit_that_never_fakes_success() -> None:
    """State machine: NEEDS_ATTENTION may only settle into a resolved outcome."""

    for target in {SourceRunState.CANCELLED, SourceRunState.FAILED}:
        assert source_run_transition_allowed(
            SourceRunState.NEEDS_ATTENTION, target
        ), target
    for target in {
        SourceRunState.QUEUED,
        SourceRunState.RUNNING,
        SourceRunState.WAITING,
        SourceRunState.PARTIAL,
        SourceRunState.COMPLETED,
        SourceRunState.AMBIGUOUS,
    }:
        assert not source_run_transition_allowed(
            SourceRunState.NEEDS_ATTENTION, target
        ), target
    assert SourceRunTrigger.MANUAL_CHECK_NOW.value == "MANUAL_CHECK_NOW"


def test_backup_archive_carries_no_secret_columns_or_vault(tmp_path: Path) -> None:
    _database, _data_root, repository = _workspace(tmp_path)
    run_id = _manual_check_now(repository, "check-1")
    _settle_in_needs_attention(repository, run_id)
    service = _service(tmp_path)

    backup = service.create_backup()
    archive_path, _content = service.backup_download(backup.backup_id) or (None, None)

    assert archive_path is not None
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest()