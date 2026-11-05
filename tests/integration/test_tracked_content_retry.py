"""Tracked-only native transcript retry; all provider boundaries are offline."""
from datetime import UTC, datetime, timedelta

import pytest
from conftest import _load_module

from youtube_intel.domain import AppError, ErrorCode, ProcessingStage
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.transcripts import TranscriptError


def _repack_backup(members, metadata):
    """Preserve the real archive's regular-file metadata for semantic probes."""
    import copy
    import io
    import stat
    import zipfile

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, 'w') as target:
        for name, body in members.items():
            info = copy.copy(metadata.get(name))
            if info is None:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o600) << 16
            target.writestr(info, body)
    return payload.getvalue()


def _closed_sqlite_main_bytes(connection, path):
    """Assert the exact staged main bytes contain every intended SQL mutation."""
    import sqlite3
    from contextlib import closing

    intended = tuple(connection.iterdump())
    connection.close()
    # immutable=1 ignores any adjacent WAL: this is exactly what goes in ZIP.
    with closing(sqlite3.connect(path.as_uri() + '?immutable=1', uri=True)) as actual:
        assert tuple(actual.iterdump()) == intended
    return path.read_bytes()


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
    assert repo.initialize(now=datetime(2026, 10, 16, tzinfo=UTC)).version == 44
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
    all_migrations = tuple(m for m in all_migrations if m.version <= 40)
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
    with monkeypatch.context() as patch:
        patch.setattr(repo, '_load_migrations', lambda: all_migrations)
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


def test_worker_completes_only_content_and_preserves_tracking(tmp_path, monkeypatch):
    repo, source, cid, old, adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    with repo._connect() as connection:
        before = {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table}')]
                  for table in ('source_runs', 'source_observations', 'source_video_links', 'source_tracking_state', 'source_subscriptions')}
    receipt = service.request(cid, command_id='worker-success', expected_job_id=old.job_id)
    original = adapter.enumerate_tracks
    calls = []
    def inspect_intent(video_id):
        with repo._connect() as connection:
            execution = connection.execute('SELECT * FROM tracked_content_retry_executions').fetchone()
            dispatch = connection.execute('SELECT status FROM provider_dispatch_states WHERE request_hash=?', (execution['provider_call_hash'],)).fetchone()
            assert execution['state'] == 'ACQUIRING' and dispatch[0] == 'DISPATCH_INTENT_DURABLE'
        calls.append(video_id)
        return original(video_id)
    adapter.enumerate_tracks = inspect_intent
    completed = service.run(receipt['request_id'])
    assert completed['state'] == 'SUCCEEDED'
    assert calls == [cid]
    assert repo.get_video(cid).pipeline_status.value == 'TRANSCRIPT_READY'
    assert repo.current_local_summary_pointer(cid) is not None
    assert service.run(receipt['request_id']) == completed
    assert calls == [cid]
    with repo._connect() as connection:
        assert all([tuple(row) for row in connection.execute(f'SELECT * FROM {table}')] == rows for table, rows in before.items())
        assert connection.execute('SELECT count(*) FROM tracked_content_retry_files').fetchone()[0] >= 6
        assert not connection.execute("SELECT 1 FROM tracked_content_retry_files WHERE state='PLANNED'").fetchone()
        assert not connection.execute("SELECT 1 FROM jobs WHERE video_id=? AND target_stage NOT IN ('METADATA','TRANSCRIPT')", (cid,)).fetchone()


@pytest.mark.parametrize('outcome', ['known', 'unknown', 'paused'])
def test_worker_closed_failures_never_refetch(tmp_path, monkeypatch, outcome):
    repo, source, cid, old, adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id=outcome, expected_job_id=old.job_id)
    calls = []
    def fail(video_id):
        calls.append(video_id)
        if outcome == 'known':
            raise TranscriptError(AppError(code=ErrorCode.INVALID_RESPONSE, message='invalid directory', retryable=False))
        raise TimeoutError('response outcome unknown')
    adapter.enumerate_tracks = fail
    if outcome == 'paused':
        repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
    final = service.run(receipt['request_id'])
    assert final['state'] == ('AMBIGUOUS' if outcome == 'unknown' else 'FAILED')
    assert len(calls) == (0 if outcome == 'paused' else 1)
    assert service.run(receipt['request_id']) == final
    with repo._connect() as connection:
        target = connection.execute('SELECT * FROM jobs WHERE job_id=?', (receipt['target_job_id'],)).fetchone()
        assert target['status'] == 'FAILED_FINAL' and target['lease_owner'] is None
        assert not connection.execute('SELECT 1 FROM job_attempts WHERE job_id=? AND finished_at IS NULL', (target['job_id'],)).fetchone()


@pytest.mark.parametrize('damage', ['event','action','epoch','target','old_attempt'])
def test_reader_rejects_tampered_foundation_evidence(tmp_path, monkeypatch, damage):
    import json

    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_store import canonical, event, read
    repo, _source, cid, old, _adapter, fixture, _runtime, service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id=damage,expected_job_id=old.job_id)
    with repo._connect() as connection:
        row=connection.execute('SELECT * FROM tracked_content_retry_executions').fetchone()
        if damage in {'event','action','epoch'}:
            events=json.loads(row['events_json'])
            final=event('FAILED',prior='QUEUED',revision=1,epoch=0,at=row['updated_at'],name='FAILED')
            if damage=='event':
                final['event']='FUTURE_UNKNOWN_EVENT'
            elif damage=='action':
                final['action']={'arbitrary':'not a receipt'}
            else:
                final['fencing_epoch']=999
            events.append(final)
            connection.execute("UPDATE jobs SET status='FAILED_FINAL',finished_at=? WHERE job_id=?",(row['updated_at'],receipt['target_job_id']))
            connection.execute("UPDATE tracked_content_retry_executions SET state='FAILED',revision=1,error_code='SOURCE_PAUSED',finished_at=updated_at,events_json=?",(canonical(events),))
        elif damage=='target':
            connection.execute("UPDATE jobs SET status='FAILED_FINAL',finished_at=? WHERE job_id=?",(row['updated_at'],receipt['target_job_id']))
        else:
            connection.execute("UPDATE job_attempts SET error_code='UNKNOWN_PROVIDER_STATE' WHERE job_id=?",(old.job_id,))
    with repo._connect(read_only=True) as connection, pytest.raises(RetryIntegrity):
        read(connection,receipt['request_id'])
    with pytest.raises(RetryIntegrity):
        service.request(cid,command_id=damage,expected_job_id=old.job_id)


def test_verified_file_requires_both_observed_values(tmp_path,monkeypatch):
    import sqlite3

    from youtube_intel.tracked_retry_store import canonical, digest
    repo,_source,cid,old,_adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='null-file',expected_job_id=old.job_id)
    with repo._connect() as connection:
        at=connection.execute('SELECT created_at FROM tracked_content_retry_requests').fetchone()[0]
        for checksum,size in [(None,None),('a'*64,None),(None,1)]:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO tracked_content_retry_files(request_id,relative_path,role,expected_sha256,expected_size_bytes,state,observed_sha256,observed_size_bytes,proof_json,proof_sha256,created_at,settled_at) VALUES(?,'test','CAPTURE',?,1,'VERIFIED',?,?,?,?,?,?)",(receipt['request_id'],'a'*64,checksum,size,canonical({}),digest({}),at,at))
        connection.execute("INSERT INTO tracked_content_retry_files(request_id,relative_path,role,expected_sha256,expected_size_bytes,state,proof_json,proof_sha256,created_at) VALUES(?,'test','CAPTURE',?,1,'PLANNED',?,?,?)",(receipt['request_id'],'a'*64,canonical({}),digest({}),at))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE tracked_content_retry_files SET state='VERIFIED',settled_at=?",(at,))


def test_generic_ambiguous_mutator_is_fenced_even_with_real_owner(tmp_path,monkeypatch):
    from youtube_intel.tracked_retry_context import RetryConflict
    repo,_source,cid,old,adapter,fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='generic-ambiguity',expected_job_id=old.job_id)
    def crash(_):
        raise KeyboardInterrupt('simulate owner process loss before receipt')
    adapter.enumerate_tracks=crash
    with pytest.raises(KeyboardInterrupt):
        service.run(receipt['request_id'])
    with repo._connect() as connection:
        execution=connection.execute('SELECT * FROM tracked_content_retry_executions').fetchone()
        before=tuple(connection.iterdump())
    with pytest.raises(RetryConflict):
        repo.mark_provider_dispatch_ambiguous(execution['provider_call_hash'],owner=execution['lease_owner'],now=fixture.now)
    with repo._connect() as connection:
        assert tuple(connection.iterdump())==before
    adapter.enumerate_tracks=lambda _: pytest.fail('unknown acquisition must never refetch')
    result=service.run(receipt['request_id'])
    assert result['state']=='AMBIGUOUS'
    assert repo.get_job(receipt['target_job_id']).attempt_count==1


def test_known_provider_failure_survives_crash_before_execution_receipt_without_becoming_unknown(tmp_path,monkeypatch):
    from youtube_intel.tracked_retry_worker import RetryWorker
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='known-crash-window',expected_job_id=old.job_id)
    def known(_):
        raise TranscriptError(AppError(code=ErrorCode.INVALID_RESPONSE,message='known directory failure',retryable=False))
    adapter.enumerate_tracks=known
    def crash(*args,**kwargs):
        raise KeyboardInterrupt('after provider failure, before execution terminal')
    with monkeypatch.context() as context:
        context.setattr(RetryWorker,'_finish_failure',crash)
        with pytest.raises(KeyboardInterrupt):
            service.run(receipt['request_id'])
    with repo._connect() as connection:
        dispatch=connection.execute('SELECT * FROM provider_dispatch_states WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests)').fetchone()
        call=connection.execute('SELECT * FROM provider_calls WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests)').fetchone()
        assert (call['status'],dispatch['status'])==('FAILED_FINAL','FAILED_KNOWN'),(dict(call),dict(dispatch))
    adapter.enumerate_tracks=lambda _:pytest.fail('known settled failure was dispatched again')
    result=service.run(receipt['request_id'])
    assert result['state']=='FAILED'
    assert service.status(cid)['retry_allowed']
    with repo._connect() as connection:
        assert connection.execute('SELECT last_error_message FROM provider_calls WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests)').fetchone()[0]=='known directory failure'


@pytest.mark.parametrize('window',['before_receipt','after_receipt'])
def test_known_failure_receipt_crash_boundary_keeps_unknown_closed_and_known_recoverable(tmp_path,monkeypatch,window):
    from youtube_intel.tracked_retry_worker import RetryWorker
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='known-receipt-'+window,expected_job_id=old.job_id)
    def known(_):
        raise TranscriptError(AppError(code=ErrorCode.INVALID_RESPONSE,message='typed known failure before restart',retryable=False))
    adapter.enumerate_tracks=known
    original=RetryWorker._record_known_failure
    def crash(self,error):
        if window=='after_receipt':
            original(self,error)
        raise KeyboardInterrupt('actual process interruption '+window)
    with monkeypatch.context() as context:
        context.setattr(RetryWorker,'_record_known_failure',crash)
        with pytest.raises(KeyboardInterrupt):
            service.run(receipt['request_id'])
    with repo._connect() as connection:
        call=connection.execute('SELECT status,last_error_message FROM provider_calls WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests)').fetchone()
        dispatch=connection.execute('SELECT status FROM provider_dispatch_states').fetchone()[0]
        assert (call['status'],dispatch)==(('PENDING','DISPATCH_INTENT_DURABLE') if window=='before_receipt' else ('FAILED_FINAL','FAILED_KNOWN'))
    adapter.enumerate_tracks=lambda _:pytest.fail('recovery dispatched captions again')
    restarted=type(service)(repo,service.data_root,adapter_factory=service.adapter_factory,language_preferences=service.languages,metadata_for_video=service.metadata_for_video,now=service.now)
    result=restarted.run(receipt['request_id'])
    assert result['state']==('AMBIGUOUS' if window=='before_receipt' else 'FAILED')
    assert restarted.status(cid)['retry_allowed']==(window=='after_receipt')


@pytest.mark.parametrize('operation',['RESUME_LOCAL','CLOSE_LOCAL'])
def test_local_attention_has_idempotent_user_exit_without_http(tmp_path,monkeypatch,operation):
    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.tracked_retry_reader import verify_all
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='attention',expected_job_id=old.job_id)
    original=ExtractiveSummaryService.create
    def unavailable(*args,**kwargs):
        raise OSError('isolated local write failure')
    monkeypatch.setattr(ExtractiveSummaryService,'create',unavailable)
    attention=service.run(receipt['request_id'])
    assert attention['state']=='ATTENTION' and attention['can_close_local']
    assert repo.get_job(receipt['target_job_id']).status.value=='SUCCEEDED'
    adapter.enumerate_tracks=lambda _: pytest.fail('local finalization must never request subtitles')
    adapter.read_track=lambda _: pytest.fail('local finalization must never read body')
    monkeypatch.setattr(ExtractiveSummaryService,'create',original)
    inputs=dict(operation=operation,command_id='local-action',expected_revision=attention['revision'])
    action=service.action(receipt['request_id'],**inputs)
    assert action['state']==('FINALIZING' if operation=='RESUME_LOCAL' else 'FAILED')
    assert service.action(receipt['request_id'],**inputs)==action
    if operation=='RESUME_LOCAL':
        assert service.run(receipt['request_id'])['state']=='SUCCEEDED'
    verified=verify_all(repo,service.data_root,settled=True)
    assert len(verified)==1


def test_cancel_queued_is_terminal_and_cannot_dispatch(tmp_path,monkeypatch):
    from youtube_intel.tracked_retry_reader import verify_all
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='cancel',expected_job_id=old.job_id)
    inputs=dict(operation='CANCEL_BEFORE_DISPATCH',command_id='cancel-action',expected_revision=receipt['revision'])
    cancelled=service.action(receipt['request_id'],**inputs)
    assert cancelled['state']=='CANCELLED'
    adapter.enumerate_tracks=lambda _: pytest.fail('cancelled retry dispatched')
    assert service.run(receipt['request_id'])==cancelled
    assert service.action(receipt['request_id'],**inputs)==cancelled
    assert len(verify_all(repo,service.data_root,settled=True))==1


@pytest.mark.parametrize('cause', ['cancel', 'pause', 'adapter'])
def test_zero_dispatch_terminal_allows_new_explicit_command_without_fake_attempt(tmp_path, monkeypatch, cause):
    from youtube_intel.tracked_retry_reader import verify_all
    repo, source, cid, old, adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    initial = service.request(cid, command_id='first', expected_job_id=old.job_id)
    current = initial
    original_factory = service.adapter_factory
    for index in range(3):
        if cause == 'cancel':
            terminal = service.action(current['request_id'], operation='CANCEL_BEFORE_DISPATCH', command_id=f'cancel-{index}', expected_revision=current['revision'])
        else:
            if cause == 'pause':
                repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
            else:
                def unavailable():
                    raise OSError('adapter unavailable before dispatch')
                service.adapter_factory = unavailable
            terminal = service.run(current['request_id'])
            repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
            service.adapter_factory = original_factory
        with repo._connect() as connection:
            target = connection.execute('SELECT * FROM jobs WHERE job_id=?', (current['target_job_id'],)).fetchone()
            assert target['attempt_count'] == 0
            assert connection.execute('SELECT count(*) FROM job_attempts WHERE job_id=?', (target['job_id'],)).fetchone()[0] == 0
        assert service.status(cid)['retry_allowed']
        fixture.now += timedelta(seconds=1)
        following = service.request(cid, command_id=f'new-{index}', expected_job_id=current['target_job_id'])
        assert service.request(cid, command_id=f'new-{index}', expected_job_id=current['target_job_id']) == following
        assert service.run(current['request_id']) == terminal
        with pytest.raises(ValueError):
            service.request(cid, command_id=f'reconsume-{index}', expected_job_id=old.job_id)
        current = following
    assert service.run(current['request_id'])['state'] == 'SUCCEEDED'
    assert len(verify_all(repo, service.data_root, settled=True)) == 4


@pytest.mark.parametrize('damage', ['parent', 'execution', 'receipt', 'epoch', 'marker', 'attempt', 'provider', 'file', 'active_writer', 'cycle', 'source'])
def test_zero_dispatch_parent_proof_is_required_by_admission_reader_and_restore(tmp_path, monkeypatch, damage):
    import json
    import sqlite3
    from contextlib import nullcontext

    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.tracked_retry_context import request_lock
    from youtube_intel.tracked_retry_reader import verify_all
    from youtube_intel.tracked_retry_store import canonical, digest, provider_request
    repo, _source, cid, old, _adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    first = service.request(cid, command_id='parent', expected_job_id=old.job_id)
    service.action(first['request_id'], operation='CANCEL_BEFORE_DISPATCH', command_id='cancel', expected_revision=first['revision'])
    if damage == 'active_writer':
        context = request_lock(repo._database_path, first['request_id'])
    else:
        context = nullcontext()
        with sqlite3.connect(repo._database_path) as connection:
            connection.row_factory = sqlite3.Row
            triggers = list(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'tracked_content_retry_%'"))
            for name, _sql in triggers:
                connection.execute(f'DROP TRIGGER "{name}"')
            row = connection.execute('SELECT * FROM tracked_content_retry_executions').fetchone()
            events = json.loads(row['events_json'])
            if damage == 'parent':
                connection.execute('DELETE FROM tracked_content_retry_executions')
                connection.execute('DELETE FROM tracked_content_retry_requests')
            elif damage == 'execution':
                connection.execute('DELETE FROM tracked_content_retry_executions')
            elif damage == 'cycle':
                connection.execute('UPDATE tracked_content_retry_requests SET expected_old_job_id=target_job_id')
            elif damage == 'source':
                connection.execute("UPDATE tracked_content_retry_requests SET channel_id='UCwrongsource000000000000'")
            elif damage in {'receipt','epoch','marker'}:
                if damage == 'receipt':
                    events[-1]['action'] = None
                elif damage == 'epoch':
                    events[-1]['fencing_epoch'] = 0
                    connection.execute('UPDATE tracked_content_retry_executions SET fencing_epoch=0')
                else:
                    events.pop()
                connection.execute('UPDATE tracked_content_retry_executions SET events_json=?', (canonical(events),))
            elif damage == 'attempt':
                connection.execute('UPDATE jobs SET attempt_count=1 WHERE job_id=?', (first['target_job_id'],))
            elif damage == 'provider':
                request = dict(connection.execute('SELECT * FROM tracked_content_retry_requests').fetchone())
                repo._reserve_provider_call_in_transaction(connection, provider_request(request), owner='unproven', lease_until=fixture.now+timedelta(minutes=1), available_at=fixture.now, now=fixture.now)
            else:
                connection.execute("INSERT INTO tracked_content_retry_files(request_id,relative_path,role,expected_sha256,expected_size_bytes,state,proof_json,proof_sha256,created_at) VALUES(?,'unproven','CAPTURE',?,1,'PLANNED',?,?,?)", (first['request_id'],'a'*64,canonical({}),digest({}),row['updated_at']))
            for _name, sql in triggers:
                connection.execute(sql)
    with context:
        with pytest.raises(ValueError):
            service.request(cid, command_id='new-after-damage', expected_job_id=first['target_job_id'])
        if damage != 'active_writer':
            with pytest.raises(ValueError):
                verify_all(repo, service.data_root, settled=True)
            assert not BackupRestoreService(database=repo._database_path,data_root=service.data_root).readiness()['ready']
        else:
            assert not service.status(cid)['retry_allowed']


def test_long_zero_dispatch_parent_chain_is_iterative_and_checks_middle_ancestors(tmp_path, monkeypatch):
    import json

    from youtube_intel.state import format_utc_datetime
    from youtube_intel.tracked_retry_reader import verify_request
    from youtube_intel.tracked_retry_store import (
        OPERATION,
        PREFIX,
        build_raw_request_hash,
        canonical,
        digest,
        event,
        provider_request,
        request_identity,
        target_identity,
    )
    from youtube_intel.tracked_retry_worker import transition
    repo, source, cid, old, _adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    first = service.request(cid, command_id='chain-root', expected_job_id=old.job_id)
    service.action(first['request_id'], operation='CANCEL_BEFORE_DISPATCH', command_id='cancel-root', expected_revision=first['revision'])
    # Seed 1,050 schema-valid, explicitly cancelled requests in one transaction;
    # no provider calls or job attempts are invented. This exceeds Python's
    # usual recursion limit without making fixture construction quadratic.
    with repo._connect() as connection:
        template = dict(connection.execute('SELECT * FROM tracked_content_retry_requests').fetchone())
        parameters = json.loads(template['parameters_json'])
        old_row = dict(connection.execute('SELECT * FROM jobs WHERE job_id=?', (first['target_job_id'],)).fetchone())
        middle = None
        for index in range(1050):
            command = f'long-chain-{index}'
            request_id = request_identity(source.source_id, command)
            target_id = target_identity(request_id, old_row['job_id'], template['pipeline_version'])
            generation = int(request_id.removeprefix(PREFIX)[:15], 16)
            at = format_utc_datetime(fixture.now + timedelta(seconds=index+1))
            client = dict(contract=template['contract'], operation=OPERATION, video_id=cid, command_id=command, expected_job_id=old_row['job_id'])
            request = dict(template, request_id=request_id, command_id=command,
                client_input_json=canonical(client), client_input_sha256=digest(client),
                expected_old_job_id=old_row['job_id'], old_job_snapshot_json=canonical(old_row), old_job_snapshot_sha256=digest(old_row),
                target_job_id=target_id, refresh_generation=generation, created_at=at,
                raw_request_hash=build_raw_request_hash(video_id=cid, language_preferences=parameters['language_preferences'], provider=parameters['adapter_name'], provider_version=parameters['adapter_version'], refresh_generation=generation))
            request['provider_request_hash'] = provider_request(request).request_hash
            target = dict(old_row, job_id=target_id, status='PENDING', last_error_code=None, last_error_message=None, created_at=at, updated_at=at, finished_at=None)
            connection.execute(f"INSERT INTO jobs({','.join(target)}) VALUES({','.join('?' for _ in target)})", tuple(target.values()))
            connection.execute(f"INSERT INTO tracked_content_retry_requests({','.join(request)}) VALUES({','.join('?' for _ in request)})", tuple(request.values()))
            admission = dict(operation=OPERATION, command_id=command, expected_revision=None, input_json=canonical(client), input_sha256=digest(client), applied_revision=0)
            connection.execute("INSERT INTO tracked_content_retry_executions(request_id,source_id,state,events_json,updated_at) VALUES(?,?,'QUEUED',?,?)", (request_id,source.source_id,canonical([event('QUEUED',prior=None,revision=0,epoch=0,at=at,name='ADMITTED',action=admission)]),at))
            execution = dict(connection.execute('SELECT * FROM tracked_content_retry_executions WHERE request_id=?', (request_id,)).fetchone())
            inputs = dict(request_id=request_id,operation='CANCEL_BEFORE_DISPATCH',command_id='cancel-'+command,expected_revision=0)
            action = dict(operation=inputs['operation'],command_id=inputs['command_id'],expected_revision=0,input_json=canonical(inputs),input_sha256=digest(inputs),applied_revision=1)
            connection.execute("UPDATE jobs SET status='FAILED_FINAL',last_error_code='CAPABILITY_UNAVAILABLE',last_error_message='CANCELLED_BEFORE_DISPATCH',finished_at=? WHERE job_id=?", (at,target_id))
            transition(connection,execution,'CANCELLED',at=at,name='CANCELLED',action=action,fencing_epoch=1,error_code='CANCELLED_BEFORE_DISPATCH')
            old_row = dict(connection.execute('SELECT * FROM jobs WHERE job_id=?', (target_id,)).fetchone())
            if index == 500:
                middle = request_id
    fixture.now += timedelta(seconds=1052)
    assert verify_request(repo,service.data_root,request_id,settled=True)[1]['state'] == 'CANCELLED'
    next_request = service.request(cid, command_id='after-long-chain', expected_job_id=target_id)
    assert service.request(cid, command_id='after-long-chain', expected_job_id=target_id) == next_request
    with repo._connect() as connection:
        assert connection.execute('SELECT count(*) FROM job_attempts WHERE job_id GLOB ?', ('tracked-content-retry-job:*',)).fetchone()[0] == 0
        trigger = connection.execute("SELECT sql FROM sqlite_master WHERE name='tracked_content_retry_execution_update'").fetchone()[0]
        connection.execute('DROP TRIGGER tracked_content_retry_execution_update')
        events = json.loads(connection.execute('SELECT events_json FROM tracked_content_retry_executions WHERE request_id=?',(middle,)).fetchone()[0])
        events[-1]['action'] = None
        connection.execute('UPDATE tracked_content_retry_executions SET events_json=? WHERE request_id=?',(canonical(events),middle))
        connection.execute(trigger)
    with pytest.raises(ValueError, match='receipt'):
        verify_request(repo,service.data_root,next_request['request_id'])


@pytest.mark.parametrize('outcome',['success','known','unknown','cancelled','closed','zerochain'])
def test_retry_terminal_backup_restores_all_tables_and_data(tmp_path,monkeypatch,outcome):
    import hashlib

    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.extractive_summary import ExtractiveSummaryService
    repo,_source,cid,old,adapter,fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='backup-'+outcome,expected_job_id=old.job_id)
    if outcome == 'zerochain':
        service.action(receipt['request_id'], operation='CANCEL_BEFORE_DISPATCH',command_id='cancel-parent',expected_revision=receipt['revision'])
        receipt = service.request(cid,command_id='after-cancel',expected_job_id=receipt['target_job_id'])
    backup=BackupRestoreService(database=repo._database_path,data_root=service.data_root)
    assert not backup.readiness()['ready']
    if outcome=='cancelled':
        service.action(receipt['request_id'],operation='CANCEL_BEFORE_DISPATCH',command_id='cancel',expected_revision=receipt['revision'])
    else:
        if outcome=='known':
            def known(_):
                raise TranscriptError(AppError(code=ErrorCode.INVALID_RESPONSE,message='invalid directory',retryable=False))
            adapter.enumerate_tracks=known
        elif outcome=='unknown':
            def unknown(_):
                raise TimeoutError('unknown')
            adapter.enumerate_tracks=unknown
        elif outcome=='closed':
            def failed(*args,**kwargs):
                raise OSError('local finalization failure')
            monkeypatch.setattr(ExtractiveSummaryService,'create',failed)
        final=service.run(receipt['request_id'])
        if outcome=='closed':
            assert not backup.readiness()['ready']
            final=service.action(receipt['request_id'],operation='CLOSE_LOCAL',command_id='close',expected_revision=final['revision'])
    assert backup.readiness()['ready'],backup.readiness()
    with repo._connect() as connection:
        tables={row[0]:[tuple(r) for r in connection.execute(f'SELECT * FROM "{row[0]}"')] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    files={str(p.relative_to(service.data_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in service.data_root.rglob('*') if p.is_file()}
    result=backup.create_backup()
    archive,_=backup.backup_download(result.backup_id)
    repo.save_global_output_language(output_language='zh-CN',now=fixture.now)
    staged=backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    restarted=SQLiteStateRepository(repo._database_path)
    assert restarted.initialize(now=fixture.now).version==44
    with restarted._connect() as connection:
        assert {row[0]:[tuple(r) for r in connection.execute(f'SELECT * FROM "{row[0]}"')] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}==tables
    assert {str(p.relative_to(service.data_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in service.data_root.rglob('*') if p.is_file()}==files


@pytest.mark.parametrize('damage',['requests','execution','files','completion','future_target','extra_file','missing_file','parent_receipt','parent_epoch','parent_marker','parent_source','parent_cycle'])
def test_rehashed_backup_still_rejects_missing_retry_authority(tmp_path,monkeypatch,damage):
    import hashlib
    import json
    import sqlite3
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    repo,_source,cid,old,_adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='corrupt',expected_job_id=old.job_id)
    parent_id = receipt['request_id']
    if damage.startswith('parent_'):
        service.action(parent_id,operation='CANCEL_BEFORE_DISPATCH',command_id='cancel-parent',expected_revision=receipt['revision'])
        receipt=service.request(cid,command_id='corrupt-child',expected_job_id=receipt['target_job_id'])
    assert service.run(receipt['request_id'])['state']=='SUCCEEDED'
    backup=BackupRestoreService(database=repo._database_path,data_root=service.data_root)
    created=backup.create_backup()
    archive,_=backup.backup_download(created.backup_id)
    with zipfile.ZipFile(archive) as source:
        members={name:source.read(name) for name in source.namelist()}
        metadata={info.filename:info for info in source.infolist()}
    repacked=_repack_backup(members,metadata)
    staged=backup.stage_restore(repacked)
    assert backup.cancel_restore(staged.restore_id)
    manifest=json.loads(members['manifest.json'])
    database=tmp_path/'malicious.sqlite'
    database.write_bytes(members['database/state.sqlite'])
    with sqlite3.connect(database) as connection:
        triggers=list(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'tracked_content_retry_%'"))
        for name,_sql in triggers:
            connection.execute(f'DROP TRIGGER "{name}"')
        if damage=='requests':
            for table in ('tracked_content_retry_files','tracked_content_retry_executions','tracked_content_retry_requests'):
                connection.execute(f'DELETE FROM {table}')
        elif damage=='execution':
            connection.execute('DELETE FROM tracked_content_retry_executions')
        elif damage=='files':
            connection.execute('DELETE FROM tracked_content_retry_files')
        elif damage=='completion':
            connection.execute("UPDATE tracked_content_retry_executions SET completion_json='{}',completion_sha256=?",(hashlib.sha256(b'{}').hexdigest(),))
        elif damage=='future_target':
            connection.execute("UPDATE jobs SET job_id='tracked-content-retry-job:v99:unassociated' WHERE job_id=?",(receipt['target_job_id'],))
        elif damage.startswith('parent_'):
            if damage == 'parent_source':
                connection.execute("UPDATE tracked_content_retry_requests SET channel_id='UCwrongsource000000000000' WHERE request_id=?", (parent_id,))
            elif damage == 'parent_cycle':
                connection.execute('UPDATE tracked_content_retry_requests SET expected_old_job_id=? WHERE request_id=?', (receipt['target_job_id'], parent_id))
            else:
                events=json.loads(connection.execute('SELECT events_json FROM tracked_content_retry_executions WHERE request_id=?',(parent_id,)).fetchone()[0])
                if damage == 'parent_receipt':
                    events[-1]['action']=None
                elif damage == 'parent_epoch':
                    events[-1]['fencing_epoch']=0
                    connection.execute('UPDATE tracked_content_retry_executions SET fencing_epoch=0 WHERE request_id=?',(parent_id,))
                else:
                    events.pop()
                connection.execute('UPDATE tracked_content_retry_executions SET events_json=? WHERE request_id=?',(json.dumps(events,sort_keys=True,separators=(',',':')),parent_id))
        for _name,sql in triggers:
            connection.execute(sql)
    members['database/state.sqlite']=_closed_sqlite_main_bytes(connection,database)
    manifest['database'].update(size_bytes=len(members['database/state.sqlite']),sha256=hashlib.sha256(members['database/state.sqlite']).hexdigest())
    if damage=='extra_file':
        members['data/transcripts/unowned.txt']=b'not an accepted capture'
        manifest['data_files'].append(dict(relative_path='transcripts/unowned.txt',sha256=hashlib.sha256(members['data/transcripts/unowned.txt']).hexdigest(),size_bytes=len(members['data/transcripts/unowned.txt']),artifacts=[],retained_subtitle_derivations=[],tracked_content_retry_files=[]))
    elif damage=='missing_file':
        removed=manifest['data_files'].pop()
        members.pop('data/'+removed['relative_path'])
    members['manifest.json']=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    with pytest.raises(BackupRestoreError) as failure:
        backup.stage_restore(_repack_backup(members,metadata))
    expected = {
        'extra_file': 'Backup DATA artifact identity is missing.',
        'future_target': 'SQLite database has broken foreign-key authority.',
        'missing_file': 'A source Summary failed authority validation.',
    }.get(damage, 'Content retry ownership or file closure failed validation.')
    assert str(failure.value) == expected
    assert backup.readiness()['ready']


def test_api_get_is_read_only_and_strict_command_routes_are_replayable(tmp_path,monkeypatch):
    import json

    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    repo,_source,cid,old,adapter,fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    wakeups=[]
    application=LocalApiApplication(repo,ProductOrchestrationService(repo,now=lambda:fixture.now),
        data_root=service.data_root,tracked_content_retry=service,source_run_wakeup=lambda:wakeups.append(True))
    with repo._connect() as connection:
        before=tuple(connection.iterdump())
    status,payload=application.handle('GET',f'/api/v1/content/{cid}/retry')
    assert status==200 and payload['tracked_content_retry']['retry_allowed']
    with repo._connect() as connection:
        assert tuple(connection.iterdump())==before
    inputs={'command_id':'from-api','expected_job_id':old.job_id}
    status,payload=application.handle('POST',f'/api/v1/content/{cid}/retry',json.dumps(inputs).encode())
    assert status==202 and len(wakeups)==1
    receipt=payload['tracked_content_retry']
    assert application.handle('POST',f'/api/v1/content/{cid}/retry',json.dumps(inputs).encode())[1]==payload
    with pytest.raises(ApiError) as conflict:
        application.handle('POST',f'/api/v1/content/{cid}/retry',json.dumps({**inputs,'expected_job_id':'changed'}).encode())
    assert conflict.value.status==409
    with pytest.raises(ApiError) as invalid:
        application.handle('POST',f'/api/v1/content/{cid}/retry',json.dumps({**inputs,'source_id':'client-authority'}).encode())
    assert invalid.value.status==422
    action={'request_id':receipt['request_id'],'operation':'CANCEL_BEFORE_DISPATCH','command_id':'api-cancel','expected_revision':receipt['revision']}
    assert application.handle('POST',f'/api/v1/content/{cid}/retry/actions',json.dumps(action).encode())[1]['tracked_content_retry']['state']=='CANCELLED'
    assert application.handle('POST',f'/api/v1/content/{cid}/retry/actions',json.dumps(action).encode())[1]['tracked_content_retry']['state']=='CANCELLED'
    adapter.enumerate_tracks=lambda _:pytest.fail('GET or cancelled command started transport')
    assert application.handle('GET',f'/api/v1/videos/{cid}')[1]['video']['tracked_content_retry']['request']['state']=='CANCELLED'
    following={'command_id':'after-api-cancel','expected_job_id':receipt['target_job_id']}
    status,next_payload=application.handle('POST',f'/api/v1/content/{cid}/retry',json.dumps(following).encode())
    assert status==202 and next_payload['tracked_content_retry']['state']=='QUEUED'
    assert application.handle('POST',f'/api/v1/content/{cid}/retry/actions',json.dumps(action).encode())[1]['tracked_content_retry']['state']=='CANCELLED'
    with repo._connect() as connection:
        before_wrong_content=tuple(connection.iterdump())
    with pytest.raises(ApiError) as wrong_content:
        application.handle('POST','/api/v1/content/other-video/retry/actions',json.dumps(action).encode())
    assert wrong_content.value.status==409
    with repo._connect() as connection:
        assert tuple(connection.iterdump())==before_wrong_content


def test_ordinary_runtime_factory_tracked_command_runs_through_dedicated_worker(tmp_path, monkeypatch):
    from youtube_intel.runtime_composition import build_local_source_run_runtime
    repo, _source, cid, old, _adapter, fixture, runtime, _service = failed_tracked(tmp_path, monkeypatch)
    composition=build_local_source_run_runtime(config=runtime._config,project_root=tmp_path,database=repo._database_path,dependencies=runtime._dependencies,now=lambda:fixture.now)
    service=composition.application._tracked_content_retry
    receipt=service.request(cid,command_id='ordinary-factory',expected_job_id=old.job_id)
    composition.worker.run_once()
    assert service.status(cid)['request']['state']=='SUCCEEDED'
    assert composition.repository.get_job(receipt['target_job_id']).attempt_count==1


def _retry_at_history_limit(tmp_path, monkeypatch, dispatch, *, event_count=126):
    import json

    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.tracked_retry_store import read
    from youtube_intel.tracked_retry_worker import RetryWorker, transition
    repo, _source, cid, old, adapter, fixture, _runtime, service = failed_tracked(tmp_path, monkeypatch)
    adapter_factory=service.adapter_factory
    receipt=service.request(cid,command_id='history-limit',expected_job_id=old.job_id)
    if dispatch == 'succeeded':
        original=ExtractiveSummaryService.create
        def local_failure(*args, **kwargs):
            raise OSError('local finalization unavailable')
        monkeypatch.setattr(ExtractiveSummaryService,'create',local_failure)
        attention=service.run(receipt['request_id'])
        monkeypatch.setattr(ExtractiveSummaryService,'create',original)
        service.action(receipt['request_id'],operation='RESUME_LOCAL',command_id='resume',expected_revision=attention['revision'])
    else:
        def crash(*args):
            raise KeyboardInterrupt('crash after claim')
        with monkeypatch.context() as context:
            context.setattr(RetryWorker,'_preflight',crash) if dispatch == 'not-dispatched' else context.setattr(adapter,'enumerate_tracks',crash)
            with pytest.raises(KeyboardInterrupt):
                service.run(receipt['request_id'])
    with repo._connect() as connection:
        _, execution=read(connection,receipt['request_id'])
        while len(json.loads(execution['events_json'])) < event_count:
            execution=transition(connection,execution,execution['state'],at=execution['updated_at'],name='RECOVERED',fencing_epoch=execution['fencing_epoch']+1)
    service.adapter_factory=lambda:pytest.fail('history capacity closure constructed a transport')
    return repo,cid,receipt,service,adapter_factory


@pytest.mark.parametrize('dispatch', ['not-dispatched','intent','succeeded'])
def test_worker_reserves_terminal_history_capacity_without_transport_or_fake_success(tmp_path, monkeypatch, dispatch):
    import json

    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.tracked_retry_reader import verify_all
    repo,cid,receipt,service,adapter_factory=_retry_at_history_limit(tmp_path,monkeypatch,dispatch)
    result=service.run(receipt['request_id'])
    assert result['state'] == {'intent':'AMBIGUOUS','not-dispatched':'FAILED','succeeded':'SUCCEEDED'}[dispatch]
    assert service.run(receipt['request_id'])==result
    assert len(verify_all(repo,service.data_root,settled=True))==1
    assert BackupRestoreService(database=repo._database_path,data_root=service.data_root).readiness()['ready']
    with repo._connect() as connection:
        assert len(json.loads(connection.execute('SELECT events_json FROM tracked_content_retry_executions').fetchone()[0]))==127
    if dispatch=='not-dispatched':
        assert service.status(cid)['retry_allowed']
        service.adapter_factory=adapter_factory
        following=service.request(cid,command_id='after-history-limit',expected_job_id=receipt['target_job_id'])
        assert service.request(cid,command_id='after-history-limit',expected_job_id=receipt['target_job_id'])==following
        assert service.run(following['request_id'])['state']=='SUCCEEDED'
        assert repo.get_job(receipt['target_job_id']).attempt_count==1
    elif dispatch=='intent':
        assert not service.status(cid)['retry_allowed']


@pytest.mark.parametrize('damage',['receipt','marker','epoch','attempt','provider','active_writer'])
def test_prepared_history_limit_successor_requires_full_distinct_parent_receipt(tmp_path,monkeypatch,damage):
    import json
    import sqlite3
    from contextlib import nullcontext

    from youtube_intel.tracked_retry_context import request_lock
    from youtube_intel.tracked_retry_reader import verify_all
    from youtube_intel.tracked_retry_store import canonical, digest
    repo,cid,receipt,service,adapter_factory=_retry_at_history_limit(tmp_path,monkeypatch,'not-dispatched')
    assert service.run(receipt['request_id'])['state']=='FAILED'
    service.adapter_factory=adapter_factory
    context=request_lock(repo._database_path,receipt['request_id']) if damage=='active_writer' else nullcontext()
    if damage!='active_writer':
        with sqlite3.connect(repo._database_path) as connection:
            triggers=list(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'tracked_content_retry_%'"))
            for name,_ in triggers:
                connection.execute(f'DROP TRIGGER "{name}"')
            events=json.loads(connection.execute('SELECT events_json FROM tracked_content_retry_executions').fetchone()[0])
            if damage=='receipt':
                events[-1]['action']=None
            elif damage=='marker':
                events[-2]['event']='DISPATCH_INTENT'
            elif damage=='epoch':
                proof=json.loads(events[-1]['action']['input_json'])
                proof['prior_epoch']+=1
                proof['command_id']='history-limit:'+digest({key:value for key,value in proof.items() if key!='command_id'})
                events[-1]['action'].update(command_id=proof['command_id'],input_json=canonical(proof),input_sha256=digest(proof))
            elif damage=='attempt':
                connection.execute("UPDATE job_attempts SET error_code='INVALID_RESPONSE' WHERE job_id=?",(receipt['target_job_id'],))
            else:
                connection.execute("UPDATE provider_dispatch_states SET status='AMBIGUOUS' WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests)")
            connection.execute('UPDATE tracked_content_retry_executions SET events_json=?',(canonical(events),))
            for _,sql in triggers:
                connection.execute(sql)
    with context:
        with pytest.raises(ValueError):
            service.request(cid,command_id='after-damaged-history',expected_job_id=receipt['target_job_id'])
        if damage!='active_writer':
            with pytest.raises(ValueError):
                verify_all(repo,service.data_root,settled=True)


def test_real_repeated_predispatch_crashes_reserve_capacity_and_allow_a_fresh_command(tmp_path,monkeypatch):
    import json

    from youtube_intel.tracked_retry_worker import RetryWorker
    repo,_source,cid,old,_adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='repeated-preflight-crashes',expected_job_id=old.job_id)
    def crash(*args):
        raise KeyboardInterrupt('actual restart before preflight')
    with monkeypatch.context() as context:
        context.setattr(RetryWorker,'_preflight',crash)
        for _ in range(140):
            try:
                result=service.run(receipt['request_id'])
            except KeyboardInterrupt:
                continue
            break
        else:
            pytest.fail('worker consumed reserved history without closing')
    assert result['state']=='FAILED'
    with repo._connect() as connection:
        row=connection.execute('SELECT * FROM tracked_content_retry_executions').fetchone()
        assert len(json.loads(row['events_json']))==114
        assert row['fencing_epoch']==112
        assert not any(event['event']=='DISPATCH_INTENT' for event in json.loads(row['events_json']))
    following=service.request(cid,command_id='fresh-after-restarts',expected_job_id=receipt['target_job_id'])
    assert service.run(following['request_id'])['state']=='SUCCEEDED'
    assert repo.get_job(receipt['target_job_id']).attempt_count==1


def test_real_local_crash_sequence_preserves_all_three_attempts_and_close_under_128_events(tmp_path,monkeypatch):
    import json

    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.tracked_retry_store import read
    from youtube_intel.tracked_retry_worker import RetryWorker
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='local-restart-budget',expected_job_id=old.job_id)
    def local_failure(*args,**kwargs):
        raise OSError('recoverable isolated local failure')
    monkeypatch.setattr(ExtractiveSummaryService,'create',local_failure)
    current=service.run(receipt['request_id'])
    assert current['state']=='ATTENTION' and current['can_resume_local']
    adapter.enumerate_tracks=lambda _:pytest.fail('local recovery requested another directory')
    adapter.read_track=lambda _:pytest.fail('local recovery requested another body')
    service.action(receipt['request_id'],operation='RESUME_LOCAL',command_id='second-local',expected_revision=current['revision'])
    def crash(*args):
        raise KeyboardInterrupt('actual restart after local claim')
    with monkeypatch.context() as context:
        context.setattr(RetryWorker,'_finalize',crash)
        for _ in range(140):
            try:
                current=service.run(receipt['request_id'])
            except KeyboardInterrupt:
                with repo._connect() as connection:
                    _,execution=read(connection,receipt['request_id'])
                    assert len(json.loads(execution['events_json']))<126
                continue
            break
        else:
            pytest.fail('local recovery consumed its reserved result/action budget')
    assert current['state']=='ATTENTION' and current['can_resume_local']
    service.action(receipt['request_id'],operation='RESUME_LOCAL',command_id='third-local',expected_revision=current['revision'])
    current=service.run(receipt['request_id'])
    assert current['state']=='ATTENTION' and not current['can_resume_local'] and current['can_close_local']
    closed=service.action(receipt['request_id'],operation='CLOSE_LOCAL',command_id='close-after-three',expected_revision=current['revision'])
    assert closed['state']=='FAILED'
    with repo._connect() as connection:
        _,execution=read(connection,receipt['request_id'])
        assert execution['local_attempt_count']==3
        assert len(json.loads(execution['events_json']))<=128
        assert repo.get_job(receipt['target_job_id']).status.value=='SUCCEEDED'


@pytest.mark.parametrize('damage',[None,'receipt','marker','attempt','provider'])
def test_prepared_history_parent_survives_full_backup_and_rehashed_damage_is_rejected(tmp_path,monkeypatch,damage):
    import hashlib
    import json
    import sqlite3
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    from youtube_intel.tracked_retry_store import canonical
    repo,cid,receipt,service,factory=_retry_at_history_limit(tmp_path,monkeypatch,'not-dispatched')
    service.run(receipt['request_id'])
    service.adapter_factory=factory
    child=service.request(cid,command_id='prepared-backup-child',expected_job_id=receipt['target_job_id'])
    assert service.run(child['request_id'])['state']=='SUCCEEDED'
    backup=BackupRestoreService(database=repo._database_path,data_root=service.data_root)
    created=backup.create_backup()
    archive,_=backup.backup_download(created.backup_id)
    with zipfile.ZipFile(archive) as source:
        members={name:source.read(name) for name in source.namelist()}
        metadata={info.filename:info for info in source.infolist()}
    repacked=_repack_backup(members,metadata)
    staged=backup.stage_restore(repacked)
    assert backup.cancel_restore(staged.restore_id)
    if damage is None:
        with repo._connect() as connection:
            before=tuple(connection.iterdump())
        files={str(path.relative_to(service.data_root)):path.read_bytes() for path in service.data_root.rglob('*') if path.is_file()}
        staged=backup.stage_restore(repacked)
        backup.confirm_restore(staged.restore_id)
        backup.recover_and_apply_pending_restore()
        with repo._connect() as connection:
            assert tuple(connection.iterdump())==before
        assert {str(path.relative_to(service.data_root)):path.read_bytes() for path in service.data_root.rglob('*') if path.is_file()}==files
        return
    database=tmp_path/'prepared-corrupt.sqlite'
    database.write_bytes(members['database/state.sqlite'])
    with sqlite3.connect(database) as connection:
        triggers=list(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'tracked_content_retry_%'"))
        for name,_ in triggers:
            connection.execute(f'DROP TRIGGER "{name}"')
        events=json.loads(connection.execute('SELECT events_json FROM tracked_content_retry_executions WHERE request_id=?',(receipt['request_id'],)).fetchone()[0])
        if damage=='receipt':
            events[-1]['action']=None
        elif damage=='marker':
            events[-2]['event']='DISPATCH_INTENT'
        elif damage=='attempt':
            connection.execute("UPDATE job_attempts SET error_code='INVALID_RESPONSE' WHERE job_id=?",(receipt['target_job_id'],))
        else:
            connection.execute("UPDATE provider_dispatch_states SET status='AMBIGUOUS' WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests WHERE request_id=?)",(receipt['request_id'],))
        connection.execute('UPDATE tracked_content_retry_executions SET events_json=? WHERE request_id=?',(canonical(events),receipt['request_id']))
        for _,sql in triggers:
            connection.execute(sql)
    members['database/state.sqlite']=_closed_sqlite_main_bytes(connection,database)
    manifest=json.loads(members['manifest.json'])
    manifest['database'].update(size_bytes=len(members['database/state.sqlite']),sha256=hashlib.sha256(members['database/state.sqlite']).hexdigest())
    members['manifest.json']=canonical(manifest).encode()
    with pytest.raises(BackupRestoreError) as failure:
        backup.stage_restore(_repack_backup(members,metadata))
    expected = ('Backup contains active work: PROVIDER_DISPATCH_UNRESOLVED' if damage == 'provider'
                else 'Content retry ownership or file closure failed validation.')
    assert str(failure.value) == expected


def _blocked_retry_process(database,data_root,request_id,now,entered,release,result):
    import json
    from pathlib import Path

    from conftest import _load_module

    from youtube_intel.domain import VideoMetadata
    from youtube_intel.state import SQLiteStateRepository
    from youtube_intel.tracked_content_retry import TrackedContentRetryService
    from youtube_intel.tracked_retry_store import read
    repo=SQLiteStateRepository(database)
    with repo._connect() as connection:
        request,_=read(connection,request_id)
    parameters=json.loads(request['parameters_json'])
    support=_load_module('test_runtime_composition')
    adapter=support._TimedSubtitleAdapter()
    def blocked(_):
        entered.set()
        assert release.wait(15)
        return support._TimedSubtitleAdapter().enumerate_tracks(support.VIDEO_ID)
    adapter.enumerate_tracks=blocked
    service=TrackedContentRetryService(repo,Path(data_root),adapter_factory=lambda:adapter,
        language_preferences=parameters['language_preferences'],metadata_for_video=lambda _:VideoMetadata.model_validate(parameters['metadata_snapshot']),now=lambda:now)
    try:
        result.put(service.run(request_id)['state'])
    except Exception as error:
        result.put(type(error).__name__)


def test_actual_worker_process_keeps_expired_lease_exclusive_until_exit(tmp_path,monkeypatch):
    import multiprocessing

    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import format_utc_datetime
    from youtube_intel.tracked_retry_context import RetryConflict
    repo,_source,cid,old,adapter,fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='process-owner',expected_job_id=old.job_id)
    context=multiprocessing.get_context('spawn')
    entered,release,result=context.Event(),context.Event(),context.Queue()
    process=context.Process(target=_blocked_retry_process,args=(str(repo._database_path),str(service.data_root),receipt['request_id'],fixture.now,entered,release,result))
    process.start()
    try:
        assert entered.wait(10)
        with repo._connect() as connection:
            expired=format_utc_datetime(fixture.now-timedelta(seconds=1))
            connection.execute('UPDATE tracked_content_retry_executions SET revision=revision+1,lease_until=?',(expired,))
            connection.execute('UPDATE jobs SET lease_until=? WHERE job_id=?',(expired,receipt['target_job_id']))
            connection.execute('UPDATE provider_calls SET lease_until=? WHERE request_hash=(SELECT provider_call_hash FROM tracked_content_retry_executions)',(expired,))
            before=tuple(connection.iterdump())
        with pytest.raises(RetryConflict):
            service.run(receipt['request_id'])
        with pytest.raises(RetryConflict):
            service.action(receipt['request_id'],operation='CLOSE_LOCAL',command_id='late-close',expected_revision=1)
        backup=BackupRestoreService(database=repo._database_path,data_root=service.data_root)
        assert not backup.readiness()['ready']
        with repo._connect() as connection:
            assert tuple(connection.iterdump())==before
    finally:
        release.set()
        process.join(15)
    assert process.exitcode==0
    assert result.get(timeout=2)=='RetryConflict'
    adapter.enumerate_tracks=lambda _:pytest.fail('recovery of durable intent must not refetch')
    final=service.run(receipt['request_id'])
    assert final['state']=='AMBIGUOUS'
    assert repo.get_job(receipt['target_job_id']).attempt_count==1
    assert backup.readiness()['ready']


def test_local_finalization_limit_still_allows_safe_close(tmp_path,monkeypatch):
    from youtube_intel.extractive_summary import ExtractiveSummaryService
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='three-local',expected_job_id=old.job_id)
    calls=[]
    def failed(*args,**kwargs):
        calls.append(1)
        raise OSError('local Summary unavailable')
    monkeypatch.setattr(ExtractiveSummaryService,'create',failed)
    state=service.run(receipt['request_id'])
    adapter.enumerate_tracks=lambda _:pytest.fail('local retries cannot dispatch')
    for attempt in range(2):
        service.action(receipt['request_id'],operation='RESUME_LOCAL',command_id='local-'+str(attempt),expected_revision=state['revision'])
        state=service.run(receipt['request_id'])
    assert len(calls)==3
    assert state['state']=='ATTENTION' and not state['can_resume_local'] and state['can_close_local']
    with pytest.raises(ValueError):
        service.action(receipt['request_id'],operation='RESUME_LOCAL',command_id='over-limit',expected_revision=state['revision'])
    assert service.action(receipt['request_id'],operation='CLOSE_LOCAL',command_id='safe-close',expected_revision=state['revision'])['state']=='FAILED'


@pytest.mark.parametrize('point',['after_intents','after_buffer_fsync','after_publish'])
@pytest.mark.parametrize('operation',['RESUME_LOCAL','CLOSE_LOCAL'])
def test_local_file_failure_windows_can_resume_or_close_without_losing_bytes(tmp_path,monkeypatch,point,operation):
    from youtube_intel.backup_restore import BackupRestoreService
    repo,_source,cid,old,adapter,_fixture,_runtime,service=failed_tracked(tmp_path,monkeypatch)
    receipt=service.request(cid,command_id='file-window',expected_job_id=old.job_id)
    failed=[]
    def inject(name):
        if name=='tracked_retry.file.SUMMARY_DERIVATION.'+point and not failed:
            failed.append(name)
            raise OSError('isolated Summary publication interruption')
    monkeypatch.setattr(repo,'_inject_failure',inject)
    state=service.run(receipt['request_id'])
    assert failed and state['state']=='ATTENTION'
    files_before={str(p.relative_to(service.data_root)):p.read_bytes() for p in service.data_root.rglob('*') if p.is_file()}
    adapter.enumerate_tracks=lambda _:pytest.fail('local file recovery must not request captions')
    adapter.read_track=lambda _:pytest.fail('local file recovery must not read body')
    service.action(receipt['request_id'],operation=operation,command_id='local-file-action',expected_revision=state['revision'])
    if operation=='RESUME_LOCAL':
        assert service.run(receipt['request_id'])['state']=='SUCCEEDED'
    else:
        assert service.status(cid)['request']['state']=='FAILED'
    for path,body in files_before.items():
        assert (service.data_root/path).read_bytes()==body
    backup=BackupRestoreService(database=repo._database_path,data_root=service.data_root)
    assert backup.readiness()['ready'],backup.readiness()
    created=backup.create_backup()
    archive,_=backup.backup_download(created.backup_id)
    backup.stage_restore(archive.read_bytes())


def test_heartbeat_keeps_zero_counter_and_unrecorded_count_blocks_all_work(tmp_path, monkeypatch):
    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_reader import verify_all
    from youtube_intel.tracked_retry_store import read
    from youtube_intel.tracked_retry_worker import RetryWorker

    repo, _, cid, old, _, _, _, service = failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id='counter-heartbeat', expected_job_id=old.job_id)
    def stop(self):
        raise KeyboardInterrupt('before acquisition')
    with monkeypatch.context() as patch:
        patch.setattr(RetryWorker, '_preflight', stop)
        with pytest.raises(KeyboardInterrupt):
            service.run(receipt['request_id'])
    with repo._connect() as connection:
        _, before = read(connection, receipt['request_id'])
        connection.execute('UPDATE tracked_content_retry_executions SET revision=revision+1 WHERE request_id=?', (receipt['request_id'],))
        _, heartbeat = read(connection, receipt['request_id'])
        assert heartbeat['events_json'] == before['events_json'] and heartbeat['local_attempt_count'] == 0
        connection.execute('UPDATE tracked_content_retry_executions SET revision=revision+1,local_attempt_count=1 WHERE request_id=?', (receipt['request_id'],))
    calls = []
    monkeypatch.setattr(ExtractiveSummaryService, 'create', lambda *a, **kw: calls.append('local work'))
    with pytest.raises(RetryIntegrity):
        service.request(cid, command_id='counter-heartbeat', expected_job_id=old.job_id)
    with pytest.raises(RetryIntegrity):
        service.run(receipt['request_id'])
    with pytest.raises(RetryIntegrity):
        verify_all(repo, service.data_root)
    assert calls == []


@pytest.mark.parametrize('outcome', ['SUCCEEDED', 'ATTENTION', 'FAILED', 'CANCELLED', 'AMBIGUOUS'])
def test_counter_replays_uniquely_in_every_observed_phase(tmp_path, monkeypatch, outcome):
    import copy
    import json

    import youtube_intel.tracked_retry_store as store
    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.tracked_retry_context import RetryIntegrity

    repo, _, cid, old, adapter, _, _, service = failed_tracked(tmp_path, monkeypatch)
    snapshots = []
    verify = store._verify_events
    def record(request, execution, events):
        verify(request, execution, events)
        snapshots.append(copy.deepcopy((request, execution, events)))
    monkeypatch.setattr(store, '_verify_events', record)
    receipt = service.request(cid, command_id='phase-counter', expected_job_id=old.job_id)
    if outcome == 'CANCELLED':
        result = service.action(receipt['request_id'], operation='CANCEL_BEFORE_DISPATCH', command_id='cancel', expected_revision=receipt['revision'])
    else:
        if outcome in {'ATTENTION', 'FAILED'}:
            def fail(*a, **kw):
                raise OSError('local failure')
            monkeypatch.setattr(ExtractiveSummaryService, 'create', fail)
        if outcome == 'AMBIGUOUS':
            def unknown(_):
                raise RuntimeError('transport result unknown')
            adapter.enumerate_tracks = unknown
        result = service.run(receipt['request_id'])
        if outcome == 'FAILED':
            result = service.action(receipt['request_id'], operation='CLOSE_LOCAL', command_id='close', expected_revision=result['revision'])
    assert result['state'] == outcome
    with repo._connect() as connection:
        store.read(connection, receipt['request_id'])
    observed = {execution['state'] for _, execution, _ in snapshots}
    assert outcome in observed and 'QUEUED' in observed
    if outcome != 'CANCELLED':
        assert 'ACQUIRING' in observed
    if outcome in {'SUCCEEDED', 'ATTENTION', 'FAILED'}:
        assert 'FINALIZING' in observed
    for request, execution, events in snapshots:
        for delta in (-1, 1):
            changed = dict(execution, local_attempt_count=execution['local_attempt_count'] + delta)
            with pytest.raises(RetryIntegrity):
                verify(request, changed, events)
        legacy = copy.deepcopy(events)
        for item in legacy:
            if item['event'] == 'LOCAL_ATTEMPT_STARTED':
                item['event'] = 'RECOVERED'
                item.pop('local_attempt')
        verify(request, execution, legacy)
        for index, item in enumerate(events):
            if item['event'] != 'LOCAL_ATTEMPT_STARTED':
                continue
            for witness in (None, {}, {'phase': 'START', 'before': False, 'after': 1},
                            {'phase': 'START', 'before': 0, 'after': True},
                            {'phase': 'START', 'before': 0.0, 'after': 1},
                            {'phase': 'START', 'before': 1, 'after': 2},
                            {'phase': 'INLINE_RESULT', 'before': 0, 'after': 1},
                            {'phase': 'START', 'before': 0, 'after': 1, 'extra': 0}):
                bad = copy.deepcopy(events)
                if witness is None:
                    bad[index].pop('local_attempt')
                else:
                    bad[index]['local_attempt'] = witness
                with pytest.raises(RetryIntegrity):
                    verify(request, execution, bad)
            bad = copy.deepcopy(events)
            bad[index]['fencing_epoch'] += 1
            with pytest.raises(RetryIntegrity):
                verify(request, execution, bad)
        # Neither JSON representation nor the current counter participates in
        # determining an inline branch's legality.
        assert json.loads(execution['events_json']) == events


@pytest.mark.parametrize('event_count, phase', [(117, 'START'), (118, 'INLINE_RESULT'), (119, 'INLINE_RESULT')])
def test_inline_capacity_uses_replayed_count_at_threshold_and_neighbors(tmp_path, monkeypatch, event_count, phase):
    import copy
    import json

    from youtube_intel.extractive_summary import ExtractiveSummaryService
    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_store import _verify_events, read

    repo, _, receipt, service, factory = _retry_at_history_limit(tmp_path, monkeypatch, 'succeeded', event_count=event_count)
    service.adapter_factory = factory
    calls = []
    def fail(*a, **kw):
        calls.append('real local failure')
        raise OSError('local failure')
    monkeypatch.setattr(ExtractiveSummaryService, 'create', fail)
    result = service.run(receipt['request_id'])
    with repo._connect() as connection:
        request, execution = read(connection, receipt['request_id'])
    events = json.loads(execution['events_json'])
    index = max(i for i, item in enumerate(events) if 'local_attempt' in item)
    assert events[index]['local_attempt'] == dict(phase=phase, before=1, after=2)
    assert execution['local_attempt_count'] == 2 and calls == ['real local failure']
    if phase == 'START':
        # A structurally valid single result is still forbidden one slot below
        # the inline threshold. Keep the counter fixed; it is not an oracle.
        below = copy.deepcopy(events[:index + 1])
        below[-1].update(event='LOCAL_INLINE_ATTENTION', state='ATTENTION',
                         local_attempt=dict(phase='INLINE_RESULT', before=1, after=2))
        with pytest.raises(RetryIntegrity):
            _verify_events(request, execution, below)
    if phase == 'INLINE_RESULT':
        for witness in (None, {}, {'phase': 'START', 'before': 1, 'after': 2},
                        {'phase': 'INLINE_RESULT', 'before': True, 'after': 2},
                        {'phase': 'INLINE_RESULT', 'before': 1, 'after': 3},
                        {'phase': 'INLINE_RESULT', 'before': 1, 'after': 2, 'extra': 0}):
            bad = copy.deepcopy(events)
            if witness is None:
                bad[index].pop('local_attempt')
            else:
                bad[index]['local_attempt'] = witness
            with pytest.raises(RetryIntegrity):
                _verify_events(request, execution, bad)
        legacy = copy.deepcopy(events)
        legacy[index]['event'] = 'LOCAL_ATTENTION'
        legacy[index].pop('local_attempt')
        with pytest.raises(RetryIntegrity):
            _verify_events(request, execution, legacy)
        with pytest.raises(RetryIntegrity):
            _verify_events(request, dict(execution, local_attempt_count=1), legacy)
    assert result['can_resume_local']
    service.action(receipt['request_id'], operation='RESUME_LOCAL', command_id='third-real-attempt', expected_revision=result['revision'])
    result = service.run(receipt['request_id'])
    assert len(calls) == 2 and not result['can_resume_local'] and result['can_close_local']
    assert service.action(receipt['request_id'], operation='CLOSE_LOCAL', command_id='close', expected_revision=result['revision'])['state'] == 'FAILED'
    with repo._connect() as connection:
        _, execution = read(connection, receipt['request_id'])
        assert execution['local_attempt_count'] == 3 and len(json.loads(execution['events_json'])) <= 128


@pytest.mark.parametrize('counter',[1,0,2])
def test_rehashed_restore_must_reject_counter_not_bound_to_real_events(tmp_path,monkeypatch,counter):
    import hashlib
    import json
    import sqlite3
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    repo,_,cid,old,_,_,_,service=failed_tracked(tmp_path,monkeypatch)
    r=service.request(cid,command_id='backup-counter',expected_job_id=old.job_id)
    assert service.run(r['request_id'])['state']=='SUCCEEDED'
    backup=BackupRestoreService(database=repo._database_path,data_root=service.data_root)
    created=backup.create_backup()
    archive,_=backup.backup_download(created.backup_id)
    with zipfile.ZipFile(archive) as z:
        metadata={i.filename:i for i in z.infolist()}
        members={n:z.read(n) for n in z.namelist()}
    src=tmp_path/'original-snapshot.sqlite'
    src.write_bytes(members['database/state.sqlite'])
    with sqlite3.connect(src) as c:
        snapshot_version=c.execute('PRAGMA user_version').fetchone()[0]
        assert snapshot_version==44
        schema=c.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall()
        columns=[r[1] for r in c.execute('PRAGMA table_info(tracked_content_retry_executions)')]
        row=list(c.execute('SELECT * FROM tracked_content_retry_executions').fetchone())
        assert row[columns.index('local_attempt_count')]==1
        row[columns.index('local_attempt_count')]=counter
        line='INSERT INTO "tracked_content_retry_executions" VALUES('+','.join(c.execute('SELECT quote(?)',(v,)).fetchone()[0] for v in row)+');'
        dump=list(c.iterdump())
        count=sum(s.startswith('INSERT INTO "tracked_content_retry_executions" VALUES(') for s in dump)
        assert count==1
        dump=[line if s.startswith('INSERT INTO "tracked_content_retry_executions" VALUES(') else s for s in dump]
    # New isolated candidate rebuilt from normal SQLite dump. No DROP TRIGGER;
    # final schema includes every original fixed trigger verbatim.
    bad=tmp_path/'repacked-snapshot.sqlite'
    with sqlite3.connect(bad) as c:
        c.executescript('\n'.join(dump))
        assert c.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall()==schema
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
        c.execute(f'PRAGMA user_version={snapshot_version}')
    members['database/state.sqlite']=_closed_sqlite_main_bytes(c,bad)
    manifest=json.loads(members['manifest.json'])
    body=members['database/state.sqlite']
    manifest['database'].update(size_bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
    members['manifest.json']=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    payload=_repack_backup(members,metadata)
    if counter==1:
        staged=backup.stage_restore(payload)
        assert staged.restore_id
        assert backup.cancel_restore(staged.restore_id)
    else:
        with pytest.raises(BackupRestoreError, match='Content retry ownership or file closure failed validation'):
            backup.stage_restore(payload)


@pytest.mark.parametrize('dispatch', ['not-dispatched', 'intent'])
def test_history_closure_receipt_counter_is_bound_even_when_rehashed(tmp_path, monkeypatch, dispatch):
    import copy
    import json

    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_store import (
        _verify_events,
        canonical,
        digest,
        read,
    )

    repo, _, receipt, service, _ = _retry_at_history_limit(tmp_path, monkeypatch, dispatch)
    service.run(receipt['request_id'])
    with repo._connect() as connection:
        request, execution = read(connection, receipt['request_id'])
    events = json.loads(execution['events_json'])
    assert events[-1]['event'] == 'HISTORY_LIMIT_CLOSED' and execution['local_attempt_count'] == 0
    for counter in (-1, 1):
        with pytest.raises(RetryIntegrity):
            _verify_events(request, dict(execution, local_attempt_count=counter), events)
        bad = copy.deepcopy(events)
        action = bad[-1]['action']
        proof = json.loads(action['input_json'])
        proof['local_attempt_count'] = counter
        proof['command_id'] = 'history-limit:' + digest({key: value for key, value in proof.items() if key != 'command_id'})
        action.update(command_id=proof['command_id'], input_json=canonical(proof), input_sha256=digest(proof))
        with pytest.raises(RetryIntegrity):
            _verify_events(request, execution, bad)


@pytest.mark.parametrize('key', ['phase', 'before', 'after'])
def test_duplicate_json_witness_fields_are_not_accepted_as_canonical_history(tmp_path, monkeypatch, key):
    import json

    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_store import read

    repo, _, cid, old, _, _, _, service = failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id='duplicate-witness', expected_job_id=old.job_id)
    assert service.run(receipt['request_id'])['state'] == 'SUCCEEDED'
    with repo._connect() as connection:
        _, execution = read(connection, receipt['request_id'])
        witness = {'phase': 'START', 'before': 0, 'after': 1}
        fragment = json.dumps(witness, sort_keys=True, separators=(',', ':'))
        duplicate = fragment[:-1] + ',' + json.dumps(key) + ':' + json.dumps(witness[key]) + '}'
        assert fragment in execution['events_json']
        damaged = execution['events_json'].replace(fragment, duplicate, 1)
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='tracked_content_retry_executions'").fetchall():
            connection.execute(f'DROP TRIGGER "{row[0]}"')
        connection.execute('UPDATE tracked_content_retry_executions SET events_json=? WHERE request_id=?', (damaged, receipt['request_id']))
        with pytest.raises(RetryIntegrity, match='history changed'):
            read(connection, receipt['request_id'])
