"""Offline advancing-clock and strictly known retained-capture retry controls."""
from datetime import UTC, datetime, timedelta

import pytest
from conftest import _load_module


@pytest.mark.parametrize('clock', ['microsecond', 'millisecond', 'utc'])
def test_advancing_claim_clock_keeps_provider_reservation_consistent(tmp_path, monkeypatch, clock):
    repo, _, cid, old, _, fixture, _, service = _load_module('test_tracked_content_retry').failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id='advancing-clock', expected_job_id=old.job_id)
    if clock == 'utc':
        service.now = lambda: datetime.now(UTC)
    else:
        step = timedelta(microseconds=1 if clock == 'microsecond' else 5000)
        def advance():
            fixture.now += step
            return fixture.now
        service.now = advance
    result = service.run(receipt['request_id'])
    assert result['state'] == 'SUCCEEDED'
    with repo._connect(read_only=True) as connection:
        call = connection.execute('SELECT * FROM provider_calls WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests WHERE request_id=?)', (receipt['request_id'],)).fetchone()
        assert call['started_at'] <= call['updated_at'] <= call['finished_at']
        assert connection.execute('SELECT local_attempt_count FROM tracked_content_retry_executions WHERE request_id=?', (receipt['request_id'],)).fetchone()[0] == 1
    assert repo.get_verified_timed_transcript(video_id=cid) is not None
    assert repo.current_local_summary_pointer(cid) is not None
    assert repo.list_evidence_for_presentation(cid)


@pytest.mark.parametrize('damage', ['started_after_updated', 'future_updated', 'future_available', 'backward_clock'])
def test_takeover_cannot_rewrite_invalid_reservation_time(tmp_path, monkeypatch, damage):
    from youtube_intel.state import format_utc_datetime
    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_worker import RetryWorker

    repo, _, cid, old, adapter, fixture, _, service = _load_module('test_tracked_content_retry').failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id='invalid-clock', expected_job_id=old.job_id)
    def stop(self):
        raise KeyboardInterrupt('before HTTP')
    with monkeypatch.context() as patch:
        patch.setattr(RetryWorker, '_preflight', stop)
        with pytest.raises(KeyboardInterrupt):
            service.run(receipt['request_id'])
    adapter.enumerate_tracks = lambda _: pytest.fail('invalid clock cannot dispatch')
    with repo._connect() as connection:
        field = {'started_after_updated': 'started_at', 'future_updated': 'updated_at', 'future_available': 'available_at'}.get(damage)
        if field is not None:
            connection.execute(f'UPDATE provider_calls SET {field}=? WHERE request_hash=(SELECT provider_request_hash FROM tracked_content_retry_requests WHERE request_id=?)', (format_utc_datetime(fixture.now + timedelta(seconds=1)), receipt['request_id']))
        else:
            service.now = lambda: fixture.now - timedelta(microseconds=1)
        before = tuple(connection.iterdump())
    with pytest.raises(RetryIntegrity, match='reservation time'):
        service.run(receipt['request_id'])
    with repo._connect() as connection:
        assert tuple(connection.iterdump()) == before


def captured_failure(tmp_path, monkeypatch, *, captures=1, indexed=False):
    """An actual offline body/attempt followed by an injected local index error.

    This builds the legacy terminal shape without rewriting any event/counter.
    It is separate from the real advancing-clock red reproduction above.
    """
    import json
    from dataclasses import replace

    from youtube_intel.domain import SubtitleFormat
    from youtube_intel.state import LeaseConflict
    from youtube_intel.transcripts import SubtitleReadResult, normalize_timed_subtitle

    values = _load_module('test_tracked_content_retry').failed_tracked(tmp_path, monkeypatch)
    repo, _, cid, old, adapter, _, _, service = values
    if captures == 2:
        listing = adapter.enumerate_tracks(cid)
        original_track = listing.tracks[0]
        timed = adapter.read_track(original_track)
        normalized = normalize_timed_subtitle(timed.body, original_track.source_format)
        plain = json.dumps({'events': [{'segs': [{'utf8': normalized.text}]}]}).encode()
        vtt = b'WEBVTT\n\n00:00.000 --> 00:09.000\n' + normalized.text.encode() + b'\n'
        adapter.enumerate_tracks = lambda _: replace(listing, tracks=(original_track, replace(original_track, source_format=SubtitleFormat.VTT, provider_position=1)))
        adapter.read_track = lambda track: SubtitleReadResult(body=plain if track.source_format == SubtitleFormat.JSON3 else vtt, call=timed.call)
    receipt = service.request(cid, command_id='known-capture-parent', expected_job_id=old.job_id)
    register = repo.register_subtitle_source_capture
    calls = []
    def local_failure(**kwargs):
        calls.append(kwargs['artifact'].artifact_id)
        if len(calls) == captures:
            if indexed:
                register(**kwargs)
            raise LeaseConflict('isolated local capture registration failure')
        return register(**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(repo, 'register_subtitle_source_capture', local_failure)
        result = service.run(receipt['request_id'])
    assert result['state'] == 'FAILED' and result['error_code'] == 'LOCAL_FINALIZATION_FAILED'
    assert len(calls) == captures
    return values, receipt


@pytest.mark.parametrize('captures,indexed', [(1, False), (1, True), (2, False), (2, True)])
def test_known_capture_failure_allows_only_new_manual_successor(tmp_path, monkeypatch, captures, indexed):
    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_reader import verify_request
    from youtube_intel.tracked_retry_store import read

    values, parent = captured_failure(tmp_path, monkeypatch, captures=captures, indexed=indexed)
    repo, _, cid, _, _, _, _, service = values
    tables = ('tracked_content_retry_requests', 'tracked_content_retry_executions', 'tracked_content_retry_files')
    with repo._connect(read_only=True) as connection:
        before = {table: [tuple(r) for r in connection.execute(f'SELECT * FROM {table} WHERE request_id=? ORDER BY rowid', (parent['request_id'],))] for table in tables}
        parent_job = tuple(connection.execute('SELECT * FROM jobs WHERE job_id=?', (parent['target_job_id'],)).fetchone())
        request = dict(connection.execute('SELECT * FROM tracked_content_retry_requests WHERE request_id=?', (parent['request_id'],)).fetchone())
        parent_provider = tuple(connection.execute('SELECT * FROM provider_calls WHERE request_hash=?', (request['provider_request_hash'],)).fetchone())
    files = {str(path.relative_to(service.data_root)): path.read_bytes() for path in service.data_root.rglob('*') if path.is_file()}
    child = service.request(cid, command_id='manual-after-capture', expected_job_id=parent['target_job_id'])
    assert child['state'] == 'QUEUED'
    assert service.run(child['request_id'])['state'] == 'SUCCEEDED'
    assert service.request(cid, command_id='manual-after-capture', expected_job_id=parent['target_job_id'])['state'] == 'SUCCEEDED'
    with pytest.raises(ValueError):
        service.request(cid, command_id='competing-after-capture', expected_job_id=parent['target_job_id'])
    verify_request(repo, service.data_root, child['request_id'], settled=True)
    with repo._connect(read_only=True) as connection:
        with pytest.raises(RetryIntegrity, match='bound DATA root'):
            read(connection, child['request_id'])
        assert {table: [tuple(r) for r in connection.execute(f'SELECT * FROM {table} WHERE request_id=? ORDER BY rowid', (parent['request_id'],))] for table in tables} == before
        assert tuple(connection.execute('SELECT * FROM jobs WHERE job_id=?', (parent['target_job_id'],)).fetchone()) == parent_job
        assert tuple(connection.execute('SELECT * FROM provider_calls WHERE request_hash=?', (request['provider_request_hash'],)).fetchone()) == parent_provider
    assert all((service.data_root / path).read_bytes() == body for path, body in files.items())


@pytest.mark.parametrize('damage', [
    'no_capture', 'no_buffer', 'partial_buffer', 'planned_buffer', 'missing_bytes', 'changed_bytes',
    'buffer_exists', 'capture_size', 'capture_proof', 'capture_epoch', 'authoritative_file',
    'authority_artifact', 'authority_timed', 'authority_evidence', 'authority_summary', 'file_time', 'local_counter', 'target_attempt0', 'target_attempt2',
    'provider_attempt0', 'provider_attempt2', 'unknown_dispatch', 'unknown_provider',
    'wrong_error', 'wrong_message', 'terminal_time', 'attempt_message', 'attempt_owner',
    'active_provider', 'active_execution', 'target_changed', 'source_changed', 'generation',
    'event_changed', 'missing_marker', 'missing_parent', 'missing_provider', 'missing_dispatch', 'ordinary_raw_record',
])
def test_capture_successor_rejects_incomplete_or_unknown_parent(tmp_path, monkeypatch, damage):
    import json
    import sqlite3

    from youtube_intel.source_authority import sha256
    from youtube_intel.tracked_retry_context import RetryConflict, RetryIntegrity
    from youtube_intel.tracked_retry_store import canonical, digest

    values, parent = captured_failure(tmp_path, monkeypatch, indexed=damage != 'no_capture')
    repo, _, cid, _, _, fixture, _, service = values
    with sqlite3.connect(repo._database_path) as connection:
        connection.row_factory = sqlite3.Row
        request = dict(connection.execute('SELECT * FROM tracked_content_retry_requests WHERE request_id=?', (parent['request_id'],)).fetchone())
        cap = dict(connection.execute("SELECT * FROM tracked_content_retry_files WHERE request_id=? AND role='CAPTURE'", (parent['request_id'],)).fetchone())
        buffer = dict(connection.execute("SELECT * FROM tracked_content_retry_files WHERE request_id=? AND role='WRITE_BUFFER'", (parent['request_id'],)).fetchone())
        triggers = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'").fetchall()
        for row in triggers:
            connection.execute(f'DROP TRIGGER "{row[0]}"')
        if damage == 'no_capture':
            connection.execute('DELETE FROM tracked_content_retry_files WHERE request_id=?', (parent['request_id'],))
        elif damage == 'no_buffer':
            connection.execute("DELETE FROM tracked_content_retry_files WHERE request_id=? AND role='WRITE_BUFFER'", (parent['request_id'],))
        elif damage == 'partial_buffer':
            (service.data_root / buffer['relative_path']).write_bytes(b'partial')
            connection.execute("UPDATE tracked_content_retry_files SET state='RETAINED_PARTIAL',observed_sha256=?,observed_size_bytes=7 WHERE role='WRITE_BUFFER'", (sha256(b'partial'),))
        elif damage == 'planned_buffer':
            connection.execute("UPDATE tracked_content_retry_files SET state='PLANNED',settled_at=NULL WHERE role='WRITE_BUFFER'")
        elif damage in {'missing_bytes', 'changed_bytes'}:
            path = service.data_root / cap['relative_path']
            path.unlink() if damage == 'missing_bytes' else path.write_bytes(b'changed bytes')
        elif damage == 'buffer_exists':
            (service.data_root / buffer['relative_path']).write_bytes(b'')
        elif damage == 'capture_size':
            connection.execute("UPDATE tracked_content_retry_files SET expected_size_bytes=expected_size_bytes+1,observed_size_bytes=observed_size_bytes+1 WHERE role='CAPTURE'")
        elif damage in {'capture_proof', 'capture_epoch'}:
            proof = json.loads(cap['proof_json'])
            proof['extra'] = 0 if damage == 'capture_proof' else None
            if damage == 'capture_epoch':
                proof.pop('extra')
                proof['fencing_epoch'] += 1
            connection.execute("UPDATE tracked_content_retry_files SET proof_json=?,proof_sha256=? WHERE role='CAPTURE'", (canonical(proof), digest(proof)))
        elif damage == 'authoritative_file':
            connection.execute("UPDATE tracked_content_retry_files SET role='CANONICAL_DERIVATION' WHERE role='CAPTURE'")
        elif damage == 'authority_artifact':
            connection.execute("UPDATE artifacts SET kind='transcript_canonical' WHERE job_id=?", (parent['target_job_id'],))
        elif damage == 'ordinary_raw_record':
            connection.execute("UPDATE artifacts SET artifact_id='ordinary-unproven-raw',artifact_key=? WHERE job_id=?", ('subtitle-source:' + request['raw_request_hash'], parent['target_job_id']))
        elif damage == 'authority_timed':
            artifact = connection.execute('SELECT artifact_id FROM artifacts WHERE job_id=?', (parent['target_job_id'],)).fetchone()[0]
            connection.execute('INSERT INTO timed_transcripts VALUES(?,?,?,?,?)', ('forged-timing', cid, artifact, 'a' * 64, cap['created_at']))
        elif damage in {'authority_evidence', 'authority_summary'}:
            artifact = connection.execute('SELECT artifact_id FROM artifacts WHERE job_id=?', (parent['target_job_id'],)).fetchone()[0]
            if damage == 'authority_evidence':
                connection.execute("INSERT INTO evidence(evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES('unproven-parent-evidence',?,?,0,1000,'ORIGINAL_TRANSCRIPT','PRIMARY_ORIGINAL','en','AVAILABLE',?,'unproven capture text')", (cid, artifact, cap['created_at']))
            else:
                connection.execute("INSERT INTO current_content_summaries(video_id,result_identity,analysis_artifact_id,output_language,updated_at) VALUES(?,NULL,?,'en',?)", (cid, artifact, cap['created_at']))
        elif damage == 'file_time':
            from youtube_intel.state import format_utc_datetime
            connection.execute("UPDATE tracked_content_retry_files SET settled_at=? WHERE role='CAPTURE'", (format_utc_datetime(fixture.now - timedelta(seconds=1)),))
        elif damage == 'local_counter':
            connection.execute('UPDATE tracked_content_retry_executions SET local_attempt_count=1')
        elif damage.startswith('target_attempt'):
            connection.execute('UPDATE jobs SET attempt_count=?,max_attempts=? WHERE job_id=?', (int(damage[-1]), max(1, int(damage[-1])), parent['target_job_id']))
        elif damage.startswith('provider_attempt'):
            connection.execute('UPDATE provider_calls SET attempt_count=? WHERE request_hash=?', (int(damage[-1]), request['provider_request_hash']))
        elif damage == 'unknown_dispatch':
            connection.execute("UPDATE provider_dispatch_states SET status='AMBIGUOUS' WHERE request_hash=?", (request['provider_request_hash'],))
        elif damage == 'unknown_provider':
            connection.execute("UPDATE provider_calls SET status='PENDING',reservation_owner='other-live-writer',lease_until='2026-10-04T00:05:00.000000Z',finished_at=NULL WHERE request_hash=?", (request['provider_request_hash'],))
        elif damage in {'wrong_error', 'wrong_message', 'terminal_time', 'active_provider'}:
            field, value = {'wrong_error': ('last_error_code', 'INVALID_RESPONSE'), 'wrong_message': ('last_error_message', 'different local error'), 'terminal_time': ('finished_at', '2026-10-04T00:00:00.000001Z'), 'active_provider': ('reservation_owner', 'other-live-writer')}[damage]
            if damage == 'active_provider':
                connection.execute("UPDATE provider_calls SET status='PENDING',reservation_owner=?,lease_until='2026-10-04T00:05:00.000000Z',finished_at=NULL WHERE request_hash=?", (value, request['provider_request_hash']))
            else:
                connection.execute(f'UPDATE provider_calls SET {field}=? WHERE request_hash=?', (value, request['provider_request_hash']))
        elif damage in {'attempt_message', 'attempt_owner'}:
            field = 'error_message' if damage == 'attempt_message' else 'lease_owner'
            connection.execute(f'UPDATE job_attempts SET {field}=? WHERE job_id=?', ('foreign', parent['target_job_id']))
        elif damage == 'active_execution':
            connection.execute("UPDATE tracked_content_retry_executions SET state='ACQUIRING',lease_owner='still-live',lease_until='2026-10-04T00:05:00.000000Z',finished_at=NULL,error_code=NULL")
        elif damage == 'target_changed':
            connection.execute("UPDATE jobs SET last_error_message='changed target' WHERE job_id=?", (parent['target_job_id'],))
        elif damage in {'source_changed', 'generation'}:
            field, value = ('channel_id', 'UCwrongsource000000000000') if damage == 'source_changed' else ('refresh_generation', request['refresh_generation'] + 1)
            connection.execute(f'UPDATE tracked_content_retry_requests SET {field}=? WHERE request_id=?', (value, parent['request_id']))
        elif damage in {'event_changed', 'missing_marker'}:
            events = json.loads(connection.execute('SELECT events_json FROM tracked_content_retry_executions').fetchone()[0])
            if damage == 'event_changed':
                events[-1]['event'] = 'RECOVERED'
            else:
                events.pop(-2)
            connection.execute('UPDATE tracked_content_retry_executions SET events_json=?', (canonical(events),))
        elif damage == 'missing_provider':
            connection.execute('DELETE FROM provider_calls WHERE request_hash=?', (request['provider_request_hash'],))
        elif damage == 'missing_dispatch':
            connection.execute('DELETE FROM provider_dispatch_states WHERE request_hash=?', (request['provider_request_hash'],))
        elif damage == 'missing_parent':
            connection.execute('DELETE FROM tracked_content_retry_requests WHERE request_id=?', (parent['request_id'],))
        for row in triggers:
            connection.execute(row[1])
    with repo._connect(read_only=True) as connection:
        before = tuple(connection.iterdump())
    with pytest.raises(ValueError):
        service.request(cid, command_id='must-reject-capture', expected_job_id=parent['target_job_id'])
    try:
        status = service.status(cid)
    except (RetryConflict, RetryIntegrity):
        pass
    else:
        assert not status['retry_allowed']
    with repo._connect(read_only=True) as connection:
        assert tuple(connection.iterdump()) == before
    assert fixture.now is not None


def test_generic_local_resource_still_cannot_admit_a_retry(tmp_path, monkeypatch):
    from youtube_intel.tracked_retry_store import KNOWN_RETRYABLE

    repo, _, cid, old, _, _, _, service = _load_module('test_tracked_content_retry').failed_tracked(tmp_path, monkeypatch)
    assert 'LOCAL_RESOURCE' not in KNOWN_RETRYABLE
    with repo._connect() as connection:
        connection.execute("UPDATE jobs SET last_error_code='LOCAL_RESOURCE' WHERE job_id=?", (old.job_id,))
        connection.execute("UPDATE job_attempts SET error_code='LOCAL_RESOURCE' WHERE job_id=?", (old.job_id,))
        before = tuple(connection.iterdump())
    with pytest.raises(ValueError):
        service.request(cid, command_id='generic-local-resource', expected_job_id=old.job_id)
    with repo._connect() as connection:
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize('captures', [1, 2])
def test_capture_successor_survives_restart_and_exact_full_restore(tmp_path, monkeypatch, captures):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import SQLiteStateRepository
    from youtube_intel.tracked_content_retry import TrackedContentRetryService

    values, parent = captured_failure(tmp_path, monkeypatch, captures=captures)
    repo, _, cid, _, _, fixture, _, service = values
    child = service.request(cid, command_id='restore-capture-child', expected_job_id=parent['target_job_id'])
    assert service.run(child['request_id'])['state'] == 'SUCCEEDED'
    backup = BackupRestoreService(database=repo._database_path, data_root=service.data_root)
    assert backup.readiness()['ready'], backup.readiness()
    with repo._connect(read_only=True) as connection:
        before = tuple(connection.iterdump())
    files = {str(p.relative_to(service.data_root)): p.read_bytes() for p in service.data_root.rglob('*') if p.is_file()}
    result = backup.create_backup()
    archive, _ = backup.backup_download(result.backup_id)
    repo.save_global_output_language(output_language='zh-CN', now=fixture.now)
    preview = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    restarted = SQLiteStateRepository(repo._database_path)
    assert restarted.initialize(now=fixture.now).version == 44
    service = TrackedContentRetryService(restarted, service.data_root, adapter_factory=lambda: pytest.fail('terminal replay constructed transport'), language_preferences=service.languages, metadata_for_video=service.metadata_for_video, now=service.now)
    assert service.run(child['request_id'])['state'] == 'SUCCEEDED'
    assert service.request(cid, command_id='restore-capture-child', expected_job_id=parent['target_job_id'])['state'] == 'SUCCEEDED'
    with restarted._connect(read_only=True) as connection:
        assert tuple(connection.iterdump()) == before
    assert {str(p.relative_to(service.data_root)): p.read_bytes() for p in service.data_root.rglob('*') if p.is_file()} == files


def test_closed_capture_parent_lock_must_be_excluded_before_successor(tmp_path, monkeypatch):
    import multiprocessing

    from youtube_intel.tracked_retry_context import RetryConflict

    support = _load_module('test_tracked_content_retry')
    values, parent = captured_failure(tmp_path, monkeypatch)
    repo, _, cid, _, _, _, _, service = values
    context = multiprocessing.get_context('spawn')
    ready, release = context.Event(), context.Event()
    process = context.Process(target=support._hold_locks, args=(repo._database_path, parent['request_id'], ready, release))
    process.start()
    try:
        assert ready.wait(10)
        assert not service.status(cid)['retry_allowed']
        with pytest.raises(RetryConflict):
            service.request(cid, command_id='locked-parent', expected_job_id=parent['target_job_id'])
    finally:
        release.set()
        process.join(10)
    assert process.exitcode == 0
    assert service.request(cid, command_id='locked-parent', expected_job_id=parent['target_job_id'])['state'] == 'QUEUED'


def test_successor_revalidates_parent_in_all_readers_and_rehashed_backup(tmp_path, monkeypatch):
    import hashlib
    import json
    import sqlite3
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    from youtube_intel.tracked_retry_context import RetryIntegrity
    from youtube_intel.tracked_retry_reader import verify_request

    support = _load_module('test_tracked_content_retry')
    values, parent = captured_failure(tmp_path, monkeypatch)
    repo, _, cid, _, _, _, _, service = values
    child = service.request(cid, command_id='parent-proof-child', expected_job_id=parent['target_job_id'])
    assert service.run(child['request_id'])['state'] == 'SUCCEEDED'
    backup = BackupRestoreService(database=repo._database_path, data_root=service.data_root)
    archive, _ = backup.backup_download(backup.create_backup().backup_id)
    with zipfile.ZipFile(archive) as source:
        members = {name: source.read(name) for name in source.namelist()}
        metadata = {info.filename: info for info in source.infolist()}
    staged = backup.stage_restore(support._repack_backup(members, metadata))
    assert backup.cancel_restore(staged.restore_id)
    with repo._connect() as connection:
        request = dict(connection.execute('SELECT * FROM tracked_content_retry_requests WHERE request_id=?', (parent['request_id'],)).fetchone())
        connection.execute("UPDATE provider_calls SET last_error_code='INVALID_RESPONSE' WHERE request_hash=?", (request['provider_request_hash'],))
    for action in (lambda: verify_request(repo, service.data_root, child['request_id']), lambda: service.status(cid), lambda: service.request(cid, command_id='parent-proof-child', expected_job_id=parent['target_job_id']), lambda: service.run(child['request_id'])):
        with pytest.raises(RetryIntegrity):
            action()
    assert not backup.readiness()['ready']
    database = tmp_path / 'damaged-parent-snapshot.sqlite'
    database.write_bytes(members['database/state.sqlite'])
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE provider_calls SET last_error_code='INVALID_RESPONSE' WHERE request_hash=?", (request['provider_request_hash'],))
    members['database/state.sqlite'] = support._closed_sqlite_main_bytes(connection, database)
    manifest = json.loads(members['manifest.json'])
    manifest['database'].update(size_bytes=len(members['database/state.sqlite']), sha256=hashlib.sha256(members['database/state.sqlite']).hexdigest())
    members['manifest.json'] = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
    with pytest.raises(BackupRestoreError, match='Content retry ownership or file closure failed validation'):
        backup.stage_restore(support._repack_backup(members, metadata))


def test_clock_moving_backwards_after_claim_cannot_dispatch(tmp_path, monkeypatch):
    from youtube_intel.tracked_retry_context import RetryConflict

    repo, _, cid, old, adapter, fixture, _, service = _load_module('test_tracked_content_retry').failed_tracked(tmp_path, monkeypatch)
    receipt = service.request(cid, command_id='clock-backwards-after-claim', expected_job_id=old.job_id)
    adapter.enumerate_tracks = lambda _: pytest.fail('backward clock must not enumerate')
    adapter.read_track = lambda _: pytest.fail('backward clock must not read')
    def factory():
        service.now = lambda: fixture.now - timedelta(seconds=1)
        return adapter
    service.adapter_factory = factory
    with pytest.raises(RetryConflict):
        service.run(receipt['request_id'])
    with repo._connect(read_only=True) as connection:
        execution = connection.execute('SELECT * FROM tracked_content_retry_executions').fetchone()
        assert execution['state'] == 'ACQUIRING' and execution['local_attempt_count'] == 0
        assert connection.execute('SELECT status FROM provider_dispatch_states').fetchone()[0] == 'NOT_DISPATCHED'


@pytest.mark.parametrize('damage', ['third_capture', 'unrelated_alternate', 'two_timed', 'two_plain'])
def test_capture_count_and_native_pair_are_proven_not_guessed(tmp_path, monkeypatch, damage):
    import json
    import sqlite3
    from dataclasses import replace
    from pathlib import Path

    from youtube_intel.domain import SubtitleFormat
    from youtube_intel.source_authority import sha256
    from youtube_intel.tracked_retry_files import provenance
    from youtube_intel.tracked_retry_store import canonical, digest
    from youtube_intel.transcripts import _decode_source_metadata, _source_relative_path

    values, parent = captured_failure(tmp_path, monkeypatch, captures=1 if damage == 'two_timed' else 2)
    repo, _, cid, _, _, fixture, _, service = values
    with sqlite3.connect(repo._database_path) as connection:
        connection.row_factory = sqlite3.Row
        request = dict(connection.execute('SELECT * FROM tracked_content_retry_requests WHERE request_id=?', (parent['request_id'],)).fetchone())
        rows = [dict(row) for row in connection.execute("SELECT * FROM tracked_content_retry_files WHERE role='CAPTURE'")]
        original = _decode_source_metadata(Path(rows[0]['relative_path']).name, video_id=cid)
        triggers = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'").fetchall()
        for row in triggers:
            connection.execute(f'DROP TRIGGER "{row[0]}"')
        if damage in {'unrelated_alternate', 'two_plain'}:
            alternate = next(row for row in rows if json.loads(row['proof_json'])['source_format'] == 'vtt')
            proof = json.loads(alternate['proof_json'])
            buffer = str(Path(alternate['relative_path']).with_name('.tracked-buffer-' + digest(dict(request_id=request['request_id'], relative=alternate['relative_path'], epoch=proof['fencing_epoch']))))
            connection.execute('DELETE FROM tracked_content_retry_files WHERE relative_path IN (?,?)', (alternate['relative_path'], buffer))
            (service.data_root / alternate['relative_path']).unlink()
        text = 'A complete original subtitle provides reliable details about this public lesson.'
        if damage == 'third_capture':
            metadata = replace(original, source_format=SubtitleFormat.SRT)
            body = ('1\n00:00:00,000 --> 00:00:09,000\n' + text + '\n').encode()
        elif damage == 'two_plain':
            metadata = replace(original, actual_language='en-US', source_format=SubtitleFormat.JSON3)
            body = json.dumps({'events': [{'segs': [{'utf8': text}]}]}).encode()
        else:
            metadata = replace(original, actual_language='en-US' if damage == 'unrelated_alternate' else 'en', source_format=SubtitleFormat.VTT)
            body = ('WEBVTT\n\n00:00.000 --> 00:09.000\n' + text + '\n').encode()
        relative = _source_relative_path(video_id=cid, raw_request_hash=request['raw_request_hash'], metadata=metadata)
        (service.data_root / relative).write_bytes(body)
        role, proof = provenance(repo, service.data_root, request, relative, body, epoch=1)
        assert role == 'CAPTURE'
        buffer = str(Path(relative).with_name('.tracked-buffer-' + digest(dict(request_id=request['request_id'], relative=relative, epoch=1))))
        for path, role, state, observed, size in ((relative, 'CAPTURE', 'VERIFIED', sha256(body), len(body)), (buffer, 'WRITE_BUFFER', 'ABSENT', None, None)):
            connection.execute('INSERT INTO tracked_content_retry_files(request_id,relative_path,role,expected_sha256,expected_size_bytes,state,observed_sha256,observed_size_bytes,proof_json,proof_sha256,created_at,settled_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (request['request_id'], path, role, sha256(body), len(body), state, observed, size, canonical(proof), digest(proof), rows[0]['created_at'], rows[0]['settled_at']))
        for row in triggers:
            connection.execute(row[1])
    with pytest.raises(ValueError):
        service.request(cid, command_id='invalid-capture-pair', expected_job_id=parent['target_job_id'])
    assert not service.status(cid)['retry_allowed']
    assert fixture.now is not None
