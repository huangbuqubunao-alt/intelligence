"""Tracked-only native transcript retry; all provider boundaries are offline."""
from datetime import UTC, datetime, timedelta

import pytest
from conftest import _load_module

from youtube_intel.domain import AppError, ErrorCode, ProcessingStage
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.transcripts import TranscriptError


def failed_tracked(tmp_path, monkeypatch):
    support = _load_module("test_youtube_following")
    repo, tracker, fixture, runtime = support.youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(support.CHANNEL, provider="YOUTUBE")
    fixture.publish(support.NEW)
    adapter = runtime._dependencies.subtitle_adapter_factory()
    good = adapter.enumerate_tracks
    def broken(_video_id):
        raise TranscriptError(AppError(code=ErrorCode.INVALID_RESPONSE,
            message="subtitle adapter response invalid during track enumeration", retryable=False,
            stage=ProcessingStage.TRANSCRIPT, video_id=support.NEW))
    adapter.enumerate_tracks = broken
    tracker.check(source.source_id)
    adapter.enumerate_tracks = good
    with repo._connect() as connection:
        connection.execute("UPDATE source_subscriptions SET last_error_code='OFFLINE' WHERE source_id=?", (source.source_id,))
    old = repo.latest_content_job(support.NEW)
    assert old.status.value == "FAILED_FINAL" and old.last_error_code == "INVALID_RESPONSE"
    from youtube_intel.tracked_content_retry import TrackedContentRetryService
    service = TrackedContentRetryService(repo, runtime._data_root,
        adapter_factory=runtime._dependencies.subtitle_adapter_factory,
        language_preferences=runtime._config.settings.general.transcript_languages,
        metadata_for_video=runtime._video_metadata, now=lambda: fixture.now)
    return repo, source, support.NEW, old, adapter, fixture, runtime, service


def test_schema40_adds_only_empty_protocol_tables(tmp_path):
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    assert repo.initialize(now=datetime(2026, 10, 16, tzinfo=UTC)).version == 40
    with repo._connect() as connection:
        for table in ("tracked_content_retry_requests", "tracked_content_retry_executions", "tracked_content_retry_files"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_admission_is_durable_idempotent_and_preserves_old_history(tmp_path, monkeypatch):
    repo, source, cid, old, _adapter, _fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    with repo._connect() as connection:
        source_before = tuple(connection.execute("SELECT * FROM source_subscriptions WHERE source_id=?", (source.source_id,)).fetchone())
        old_before = tuple(connection.execute("SELECT * FROM jobs WHERE job_id=?", (old.job_id,)).fetchone())
        runs = connection.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0]
    first = service.request(cid, command_id="explicit-retry", expected_job_id=old.job_id)
    assert first["state"] == "QUEUED"
    assert service.request(cid, command_id="explicit-retry", expected_job_id=old.job_id) == first
    with pytest.raises(ValueError):
        service.request(cid, command_id="different", expected_job_id=old.job_id)
    with repo._connect() as connection:
        assert tuple(connection.execute("SELECT * FROM jobs WHERE job_id=?", (old.job_id,)).fetchone()) == old_before
        assert tuple(connection.execute("SELECT * FROM source_subscriptions WHERE source_id=?", (source.source_id,)).fetchone()) == source_before
        assert connection.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == runs
    assert repo.claim_next_job(owner="generic", lease_until=_fixture.now + timedelta(minutes=1), now=_fixture.now) is None


def test_request_history_replay_needs_no_current_adapter_or_enabled_source(tmp_path, monkeypatch):
    repo, source, cid, old, _adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id="original", expected_job_id=old.job_id)
    repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
    def unavailable():
        raise AssertionError("history replay must not construct an adapter")
    service.adapter_factory = unavailable
    assert service.request(cid, command_id="original", expected_job_id=old.job_id) == receipt
    with pytest.raises(ValueError):
        service.request(cid, command_id="original", expected_job_id="changed")


@pytest.mark.parametrize("damage", ["paused", "untrusted", "unknown_call", "active_run", "active_check", "wrong_stage", "unknown_error"])
def test_new_admission_is_closed_before_target_creation(tmp_path, monkeypatch, damage):
    repo, source, cid, old, _adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    with repo._connect() as connection:
        if damage == "paused":
            connection.execute("UPDATE source_subscriptions SET enabled=0 WHERE source_id=?", (source.source_id,))
        elif damage == "untrusted":
            connection.execute("UPDATE source_tracking_state SET health='STATE_INVALID' WHERE source_id=?", (source.source_id,))
        elif damage == "unknown_call":
            connection.execute("INSERT INTO provider_dispatch_states(request_hash,status,updated_at) SELECT request_hash,'AMBIGUOUS',updated_at FROM provider_calls LIMIT 1 ON CONFLICT(request_hash) DO UPDATE SET status='AMBIGUOUS'")
            assert connection.execute("SELECT COUNT(*) FROM provider_dispatch_states WHERE status='AMBIGUOUS'").fetchone()[0] == 1
        elif damage == "active_run":
            from youtube_intel.source_run import SourceRunPriority, SourceRunWrite
            repo.create_source_run(SourceRunWrite.manual_check_now(source_id=source.source_id, command_id="existing", priority=SourceRunPriority.P0, created_at=fixture.now))
        elif damage == "active_check":
            connection.execute("INSERT INTO source_checks(check_id,source_id,started_at,status) VALUES('active',?,?,'RUNNING')", (source.source_id, fixture.now.isoformat()))
        elif damage == "wrong_stage":
            connection.execute("UPDATE videos SET pipeline_status='TRANSCRIPT_READY' WHERE video_id=?", (cid,))
        elif damage == "unknown_error":
            connection.execute("UPDATE jobs SET last_error_code='UNKNOWN_PROVIDER_STATE' WHERE job_id=?", (old.job_id,))
        before = tuple(connection.iterdump())
    with pytest.raises(ValueError):
        service.request(cid, command_id="blocked", expected_job_id=old.job_id)
    with repo._connect() as connection:
        assert tuple(connection.iterdump()) == before


def test_request_and_consumed_history_are_immutable_and_source_check_is_excluded(tmp_path, monkeypatch):
    import sqlite3

    from youtube_intel.source_run import SourceRunPriority, SourceRunWrite
    from youtube_intel.state import IntegrityConflict
    repo, source, cid, old, _adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id="protected", expected_job_id=old.job_id)
    with repo._connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE tracked_content_retry_requests SET command_id='changed'")
        with pytest.raises(sqlite3.IntegrityError, match="retained"):
            connection.execute("DELETE FROM tracked_content_retry_requests")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE jobs SET updated_at=updated_at WHERE job_id=?", (old.job_id,))
        with pytest.raises(sqlite3.IntegrityError, match="holds"):
            connection.execute("INSERT INTO source_checks(check_id,source_id,started_at,status) VALUES('blocked',?,?,'RUNNING')", (source.source_id, fixture.now.isoformat()))
    with pytest.raises(IntegrityConflict):
        repo.create_source_run(SourceRunWrite.manual_check_now(source_id=source.source_id, command_id="blocked", priority=SourceRunPriority.P0, created_at=fixture.now))
    with pytest.raises(ValueError):
        repo.rerun_job(old.job_id, new_job_id="generic-rerun", now=fixture.now, available_at=fixture.now)
    assert repo.claim_next_job(owner="generic", lease_until=fixture.now+timedelta(minutes=1), now=fixture.now, job_id=receipt["target_job_id"]) is None


def test_two_commands_can_consume_a_failure_only_once(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    repo, _source, cid, old, _adapter, _fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    def submit(command):
        try:
            return service.request(cid, command_id=command, expected_job_id=old.job_id)
        except ValueError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, ["first", "second"]))
    assert sum(result is not None for result in results) == 1
    with repo._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM tracked_content_retry_requests").fetchone()[0] == 1


def _hold_locks(database, request_id, ready, release):
    from pathlib import Path

    from youtube_intel.tracked_retry_context import request_lock, store_lock
    with store_lock(Path(database)), request_lock(Path(database), request_id):
        ready.set()
        assert release.wait(15)


def test_real_process_lock_cannot_be_stolen_by_new_owner_or_backup(tmp_path):
    import multiprocessing

    from youtube_intel.tracked_retry_context import (
        RetryConflict,
        request_lock,
        store_lock,
    )
    context = multiprocessing.get_context("spawn")
    ready, release = context.Event(), context.Event()
    database = tmp_path / "state.sqlite"
    process = context.Process(target=_hold_locks, args=(str(database), "request", ready, release))
    process.start()
    try:
        assert ready.wait(10)
        with pytest.raises(RetryConflict):
            with request_lock(database, "request"):
                raise AssertionError("live writer lock stolen")
        with pytest.raises(RetryConflict):
            with store_lock(database, exclusive=True):
                raise AssertionError("Backup crossed live writer")
    finally:
        release.set()
        process.join(10)
    assert process.exitcode == 0
    with request_lock(database, "request"), store_lock(database, exclusive=True):
        pass


def test_migration40_failure_rolls_back_and_success_preserves39_domain_rows(tmp_path, monkeypatch):
    from dataclasses import replace

    from youtube_intel.state import MigrationError
    now = datetime(2026, 10, 16, tzinfo=UTC)
    all_migrations = SQLiteStateRepository(tmp_path / 'unused.sqlite')._load_migrations()
    repo = SQLiteStateRepository(tmp_path / 'state.sqlite')
    with monkeypatch.context() as patch:
        patch.setattr(repo, '_load_migrations', lambda: all_migrations[:-1])
        assert repo.initialize(now=now).version == 39
    repo.save_global_output_language(output_language='en', now=now)
    with repo._connect() as connection:
        before = tuple(connection.iterdump())
        rows_before = {row[0]: connection.execute(f'SELECT * FROM "{row[0]}"').fetchall()
                       for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('schema_migrations','sqlite_sequence')")}
    broken = replace(all_migrations[-1], sql=all_migrations[-1].sql+'\nSELECT injected_migration_failure();')
    with monkeypatch.context() as patch:
        patch.setattr(repo, '_load_migrations', lambda: (*all_migrations[:-1], broken))
        with pytest.raises(MigrationError):
            repo.initialize(now=now)
    with repo._connect() as connection:
        assert tuple(connection.iterdump()) == before
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 39
    assert repo.initialize(now=now).version == 40
    with repo._connect() as connection:
        assert all(connection.execute(f'SELECT * FROM "{name}"').fetchall() == values for name, values in rows_before.items())
        targets = connection.execute('PRAGMA foreign_key_list(tracked_content_retry_requests)').fetchall()
        assert any(row[2] == 'source_observations' and row[3] == 'observation_identity' and row[4] == 'canonical_identity' for row in targets)
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []


def test_contended_initial_lock_creation_keeps_one_stable_inode(tmp_path):
    import os
    from concurrent.futures import ThreadPoolExecutor

    from youtube_intel.tracked_retry_context import store_lock
    database = tmp_path / 'state.sqlite'
    def open_shared(_):
        with store_lock(database):
            return os.stat(tmp_path / '.tracked-content-retry-locks/store.lock').st_ino
    with ThreadPoolExecutor(max_workers=8) as pool:
        identities = list(pool.map(open_shared, range(1000)))
    assert len(set(identities)) == 1
