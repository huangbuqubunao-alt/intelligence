"""Retired known public subtitle failures settle without bypassing Backup."""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier, Event

import pytest
from conftest import _load_module

from youtube_intel.domain import ErrorCode, ProcessingStage
from youtube_intel.processing_orchestrator import DurableProcessingOrchestrator
from youtube_intel.runtime_composition import DurableSourceRunWorker
from youtube_intel.state import (
    DistillationExecutionWrite,
    JobType,
    ProviderCallRequest,
    ProviderCallStatus,
    SQLiteStateRepository,
    format_utc_datetime,
)

support = _load_module("test_backup_restore")
NOW = support.NOW
LATER = NOW + timedelta(minutes=1)


def _failure(repository, **overrides):
    request = ProviderCallRequest(
        operation="subtitle.fetch", normalized_input_hash=hashlib.sha256(b"old public subtitle").hexdigest(),
        provider="yt-dlp", model=None, prompt_version="subtitle-selection-v1",
        schema_version="subtitle-format-v1", deterministic_artifact_key="unused-original-response",
    )
    request = replace(request, **overrides)
    repository.reserve_provider_call(request, owner="subtitle-worker", lease_until=LATER, available_at=NOW, now=NOW)
    repository.fail_provider_call(request.request_hash, owner="subtitle-worker", retryable=True,
        available_at=NOW, error_code=ErrorCode.RATE_LIMITED, error_message="Public caption HTTP 429.", now=NOW)
    return request


def _workspace(tmp_path):
    _database, _data, _vault, repository, _artifact = support._workspace(tmp_path)
    return repository, support._service(tmp_path)


def _tables(repository):
    with repository._connect() as connection:
        names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name: tuple(tuple(row) for row in connection.execute(f'SELECT * FROM "{name}" ORDER BY rowid')) for name in names}


def test_retired_known_failure_releases_backup_and_preserves_all_other_history(tmp_path):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    old = repository.get_provider_call(request.request_hash)
    before = _tables(repository)
    assert backup.readiness()["reasons"] == ["PROVIDER_CALL_UNRESOLVED"]
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == (request.request_hash,)
    terminal = repository.get_provider_call(request.request_hash)
    assert terminal.status is ProviderCallStatus.FAILED_FINAL
    assert terminal.last_error_code == old.last_error_code
    assert terminal.last_error_message.startswith(old.last_error_message + "\n")
    assert "POLICY_RETIRED" in terminal.last_error_message
    assert replace(terminal, status=old.status, last_error_message=old.last_error_message,
        finished_at=old.finished_at, updated_at=old.updated_at) == old
    after = _tables(repository)
    assert {k: v for k, v in after.items() if k != "provider_calls"} == {k: v for k, v in before.items() if k != "provider_calls"}
    assert backup.readiness()["ready"] is True
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER + timedelta(days=1)) == ()
    assert repository.get_provider_call(request.request_hash) == terminal
    restarted = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert restarted.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert restarted.get_provider_call(request.request_hash) == terminal
    assert restarted.reserve_provider_call(request, owner="again", lease_until=LATER + timedelta(minutes=1), available_at=LATER, now=LATER).acquired is False
    result = backup.create_backup()
    archive, _ = backup.backup_download(result.backup_id)
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert _tables(restored) == after
    assert restored.get_provider_call(request.request_hash) == terminal
    assert restored.retire_known_failed_subtitle_calls(backup_restore=support._service(tmp_path), now=LATER) == ()


@pytest.mark.parametrize("column,value", [
    ("operation", "scoring"), ("provider", "openai"), ("model", "qwen3:8b"),
    ("prompt_version", "subtitle-selection-v2-original-tracks"), ("schema_version", "subtitle-format-v2-native-timing"),
    ("prompt_version", "unknown"), ("schema_version", "unknown"),
    ("last_error_code", "TRANSIENT_NETWORK"),
    ("last_error_message", None), ("response_artifact_id", "artifact-1"),
    ("input_tokens", 0), ("output_tokens", 0), ("cost_microusd", 0),
])
def test_non_exact_or_uncertain_provider_rows_remain_blocked(tmp_path, column, value):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        connection.execute(f"UPDATE provider_calls SET {column}=? WHERE request_hash=?", (value, request.request_hash))
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert backup.readiness()["ready"] is False


@pytest.mark.parametrize("dispatch", ["NOT_DISPATCHED", "DISPATCH_INTENT_DURABLE", "DISPATCHED_RESULT_UNKNOWN", "AMBIGUOUS", "SUCCESS_DURABLY_RECORDED"])
def test_unknown_or_inconsistent_dispatch_is_not_retired(tmp_path, dispatch):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        connection.execute("INSERT INTO provider_dispatch_states VALUES (?,?,?)", (request.request_hash, dispatch, format_utc_datetime(NOW)))
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before


def test_any_other_unfinished_provider_blocks_the_entire_retirement(tmp_path):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    _failure(repository, provider="other-provider")
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before


@pytest.mark.parametrize("state", ["PENDING", "WAITING_BUDGET", "WAITING_MODEL"])
def test_open_checkpoint_keeps_known_failure_unresolved(tmp_path, state):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    support._add_source(repository)
    execution = "waiting-model"
    repository.reserve_distillation_execution(DistillationExecutionWrite(
        execution_id=execution, source_id="source-1", video_id="video-1",
        reason="MANUAL_CONTENT:cancel-test", use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="ollama", selected_model="qwen3:8b", output_language="en",
    ), now=NOW)
    if state != "PENDING":
        repository.finish_distillation_without_admission(
            execution_id=execution, status=state, budget_state="ADMITTED", outcome="BLOCKED",
            invocation_count=0, actual_provider=None, actual_model=None, input_tokens=None,
            output_tokens=None, cost_microunits=None, duration_ms=None, now=NOW,
        )
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert repository.get_distillation_execution(execution).invocation_count == 0


def test_cancelled_wait_checkpoint_is_valid_terminal_authority(tmp_path):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    support._add_source(repository)
    execution = support._waiting_model(repository)
    repository.cancel_waiting_model_execution(execution, video_id="video-1", now=NOW)
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == (request.request_hash,)
    assert _tables(repository)["distillation_execution_checkpoints"] == before["distillation_execution_checkpoints"]
    assert repository.get_distillation_execution(execution).status == "CANCELLED"
    assert backup.readiness()["ready"] is True


def test_retirement_and_same_request_start_have_only_one_winner(tmp_path):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    barrier = Barrier(2)

    def retire():
        barrier.wait()
        return repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER)

    def start():
        barrier.wait()
        return repository.reserve_provider_call(request, owner="retry", lease_until=LATER + timedelta(minutes=1), available_at=LATER, now=LATER).acquired

    with ThreadPoolExecutor(max_workers=2) as pool:
        retired = pool.submit(retire)
        started = pool.submit(start)
        settled, acquired = retired.result(timeout=10), started.result(timeout=10)
    assert bool(settled) != acquired
    record = repository.get_provider_call(request.request_hash)
    assert record.status is (ProviderCallStatus.PENDING if acquired else ProviderCallStatus.FAILED_FINAL)
    if acquired:
        assert record.reservation_owner == "retry" and record.attempt_count == 2


def test_background_work_and_pending_restore_block_maintenance(tmp_path):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    before = _tables(repository)
    with backup.background_work() as allowed:
        assert allowed
        assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    backup.marker_path.write_text('{}')
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before


@pytest.mark.parametrize("expired", [False, True])
def test_owned_or_unknown_expired_request_is_not_a_known_failure(tmp_path, expired):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    repository.reserve_provider_call(request, owner="active", lease_until=LATER, available_at=NOW, now=NOW)
    before = _tables(repository)
    at = LATER + timedelta(minutes=1) if expired else NOW
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=at) == ()
    assert _tables(repository) == before
    assert backup.readiness()["ready"] is False


@pytest.mark.parametrize("running", [False, True])
def test_pending_or_running_job_keeps_retired_provider_blocked(tmp_path, running):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    repository.create_job(job_id="live-job", scope_key="video:video-1:TRANSCRIPT", video_id="video-1",
        job_type=JobType.VIDEO_STAGE, target_stage=ProcessingStage.TRANSCRIPT, pipeline_version="v1",
        max_attempts=3, available_at=NOW, now=NOW)
    if running:
        assert repository.claim_next_job(owner="worker", lease_until=LATER, now=NOW).job_id == "live-job"
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert "JOBS_ACTIVE" in backup.readiness()["reasons"]


def test_new_policy_success_does_not_erase_old_known_failure(tmp_path):
    repository, backup = _workspace(tmp_path)
    old = _failure(repository)
    new = replace(old, prompt_version="subtitle-selection-v2-original-tracks",
        schema_version="subtitle-format-v2-native-timing", deterministic_artifact_key="artifact-key-1")
    repository.reserve_provider_call(new, owner="new", lease_until=LATER, available_at=NOW, now=NOW)
    repository.complete_provider_call(new.request_hash, response_artifact_id="artifact-1", input_tokens=None,
        output_tokens=None, cost_microusd=None, owner="new", now=NOW)
    assert backup.readiness()["ready"] is False
    new_before = repository.get_provider_call(new.request_hash)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == (old.request_hash,)
    assert repository.get_provider_call(new.request_hash) == new_before
    assert backup.readiness()["ready"] is True


def test_normal_idle_worker_runs_maintenance_without_self_wakeup(tmp_path):
    repository, backup = _workspace(tmp_path)
    old = _failure(repository)
    orchestrator = DurableProcessingOrchestrator(repository, source_policy=None, distillation=None, now=lambda: LATER)
    worker = DurableSourceRunWorker(orchestrator, backup_restore=backup)
    backup.bind_background_wakeup(worker.notify_backup_window_closed)
    assert worker.run_once() is None
    assert repository.get_provider_call(old.request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert worker._wake.is_set() is False
    # An unrelated protected window and direct user notification still wake.
    with backup._protect_background():
        pass
    assert worker._wake.is_set() is True
    worker._wake.clear()
    worker.notify()
    assert worker._wake.is_set() is True


def test_concurrent_external_backup_notification_is_not_lost(tmp_path):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    orchestrator = DurableProcessingOrchestrator(repository, source_policy=None, distillation=None, now=lambda: LATER)
    worker = DurableSourceRunWorker(orchestrator, backup_restore=backup)
    entered, notified = Event(), Event()

    def external():
        assert entered.wait(5)
        worker.notify_backup_window_closed()
        notified.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(external)
        worker._maintenance_context.active = True
        entered.set()
        assert notified.wait(5)
        worker.notify_backup_window_closed()
        future.result(timeout=5)
        worker._maintenance_context.active = False
    assert worker._wake.is_set() is True


@pytest.mark.parametrize("active", ["source-run", "source-check"])
def test_other_live_source_authority_blocks_retirement(tmp_path, active):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    if active == "source-run":
        support._add_source(repository)
        orchestrator = DurableProcessingOrchestrator(repository, source_policy=None, distillation=None, now=lambda: NOW)
        orchestrator.enqueue_manual_check_now(source_id="source-1", command_id="live-check")
    else:
        channel = "UC" + "a" * 22
        repository.create_source_subscription(support.SourceSubscriptionRecord(
            source_id="source-1", source_type=support.SourceType.CHANNEL,
            canonical_url=f"https://www.youtube.com/channel/{channel}", channel_id=channel,
            video_id=None, display_name="Public source", enabled=True,
            processing_policy=support.ProcessingPolicy.STANDARD_INTELLIGENCE,
            last_checked_at=None, last_success_at=None, last_error_code=None, last_error_message=None,
            created_at=NOW, updated_at=NOW,
        ))
        with repository._connect() as connection:
            connection.execute("INSERT INTO source_tracking_state(source_id,contract,followed_at,next_check_at) VALUES('source-1','source-tracking-v1',?,?)", (format_utc_datetime(NOW), format_utc_datetime(NOW)))
            connection.execute("INSERT INTO source_checks(check_id,source_id,started_at,status) VALUES('live-check','source-1',?,'RUNNING')", (format_utc_datetime(NOW),))
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert "SOURCE_RUN_ACTIVE" in backup.readiness()["reasons"]


def test_known_failed_dispatch_is_preserved_and_settled(tmp_path):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        connection.execute("INSERT INTO provider_dispatch_states VALUES (?,?,?)", (request.request_hash, "FAILED_KNOWN", format_utc_datetime(NOW)))
    before = _tables(repository)["provider_dispatch_states"]
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == (request.request_hash,)
    assert _tables(repository)["provider_dispatch_states"] == before
    assert backup.readiness()["ready"] is True


def test_indexed_raw_response_prevents_retirement_even_if_not_attached(tmp_path):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        connection.execute("UPDATE artifacts SET artifact_key=? WHERE artifact_id='artifact-1'", (f"subtitle-source:{request.request_hash}",))
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert backup.readiness()["ready"] is False


def test_new_request_waits_for_transaction_and_remains_active(tmp_path, monkeypatch):
    repository, backup = _workspace(tmp_path)
    old = _failure(repository)
    new = replace(old, prompt_version="subtitle-selection-v2-original-tracks", schema_version="subtitle-format-v2-native-timing")
    inside, starting, started, release = Event(), Event(), Event(), Event()
    real_reasons = backup._quiescence_reasons

    def pause(connection, *, repository):
        result = real_reasons(connection, repository=repository)
        inside.set()
        assert release.wait(5)
        return result

    def start():
        assert inside.wait(5)
        starting.set()
        result = repository.reserve_provider_call(new, owner="new", lease_until=LATER + timedelta(minutes=1), available_at=LATER, now=LATER)
        started.set()
        return result

    monkeypatch.setattr(backup, "_quiescence_reasons", pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        retired = pool.submit(repository.retire_known_failed_subtitle_calls, backup_restore=backup, now=LATER)
        current = pool.submit(start)
        assert starting.wait(5)
        assert started.is_set() is False
        release.set()
        assert retired.result(timeout=10) == (old.request_hash,)
        assert current.result(timeout=10).acquired is True
    monkeypatch.setattr(backup, "_quiescence_reasons", real_reasons)
    assert repository.get_provider_call(new.request_hash).status is ProviderCallStatus.PENDING
    assert backup.readiness()["ready"] is False


def test_other_backup_window_or_database_authority_cannot_settle(tmp_path):
    repository, backup = _workspace(tmp_path)
    _failure(repository)
    before = _tables(repository)
    with backup._protect_background():
        assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    other = tmp_path / "other"
    other.mkdir()
    _, other_backup = _workspace(other)
    with pytest.raises(ValueError, match="matching Backup authority"):
        repository.retire_known_failed_subtitle_calls(backup_restore=other_backup, now=LATER)
    assert _tables(repository) == before


@pytest.mark.parametrize("column", ["started_at", "updated_at", "available_at", "dispatch_updated_at"])
@pytest.mark.parametrize("mixed_batch", [False, True])
def test_unreadable_retirement_history_keeps_every_row_and_backup_blocked(tmp_path, column, mixed_batch):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    if mixed_batch:
        _failure(repository, normalized_input_hash=hashlib.sha256(b"another valid public subtitle").hexdigest())
    with repository._connect() as connection:
        if column == "dispatch_updated_at":
            connection.execute("INSERT INTO provider_dispatch_states VALUES (?,?,?)", (request.request_hash, "FAILED_KNOWN", "0"))
        else:
            connection.execute(f"UPDATE provider_calls SET {column}='0' WHERE request_hash=?", (request.request_hash,))
    with pytest.raises(ValueError, match="Invalid isoformat"):
        if column == "dispatch_updated_at":
            with repository._connect() as connection:
                repository._dispatch_state_in_transaction(connection, request.request_hash)
        else:
            repository.get_provider_call(request.request_hash)
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert backup.readiness()["ready"] is False


@pytest.mark.parametrize("column,value", [
    ("started_at", format_utc_datetime(NOW + timedelta(seconds=1))),
    ("updated_at", format_utc_datetime(NOW - timedelta(seconds=1))),
    ("available_at", format_utc_datetime(NOW - timedelta(seconds=1))),
    ("dispatch_updated_at", format_utc_datetime(NOW - timedelta(seconds=1))),
    ("dispatch_updated_at", format_utc_datetime(NOW + timedelta(seconds=1))),
    ("attempt_count", 0), ("attempt_count", 1.5), ("attempt_count", "unknown"),
])
def test_inconsistent_retirement_times_or_counts_are_not_reinterpreted(tmp_path, column, value):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        if column == "dispatch_updated_at":
            connection.execute("INSERT INTO provider_dispatch_states VALUES (?,?,?)", (request.request_hash, "FAILED_KNOWN", value))
        else:
            connection.execute(f"UPDATE provider_calls SET {column}=? WHERE request_hash=?", (value, request.request_hash))
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert backup.readiness()["ready"] is False


@pytest.mark.parametrize("column", ["started_at", "updated_at", "available_at", "dispatch_updated_at"])
def test_date_without_utc_execution_time_is_not_retired(tmp_path, column):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        if column == "dispatch_updated_at":
            connection.execute("INSERT INTO provider_dispatch_states VALUES (?,?,?)", (request.request_hash, "FAILED_KNOWN", "2026-09-23"))
        else:
            connection.execute(f"UPDATE provider_calls SET {column}='2026-09-23' WHERE request_hash=?", (request.request_hash,))
    before = _tables(repository)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == ()
    assert _tables(repository) == before
    assert backup.readiness()["ready"] is False


def test_valid_future_retry_backoff_is_not_mistaken_for_unknown_history(tmp_path):
    repository, backup = _workspace(tmp_path)
    request = _failure(repository)
    with repository._connect() as connection:
        connection.execute("UPDATE provider_calls SET available_at=? WHERE request_hash=?", (format_utc_datetime(LATER + timedelta(minutes=5)), request.request_hash))
    before = repository.get_provider_call(request.request_hash)
    assert repository.retire_known_failed_subtitle_calls(backup_restore=backup, now=LATER) == (request.request_hash,)
    assert repository.get_provider_call(request.request_hash).available_at == before.available_at
    assert backup.readiness()["ready"] is True
