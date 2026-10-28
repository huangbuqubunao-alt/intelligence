"""Synthetic SQLite/fake-wire proof of narrow cloud zero-call cancellation."""
from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from conftest import _load_module

from youtube_intel import distillation as d
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)

fixtures = _load_module('test_task022_personalized_distillation')
NOW = fixtures.NOW
TABLE = 'distillation_cloud_waiting_model_cancellations'


def setup_wait(tmp_path, *, v2=False, tls=False, budget='ADMITTED', body=None, finish=True, consent_kind='OWNER_QUALIFICATION', reservation_id=None):
    repo = SQLiteStateRepository(tmp_path / 'state.sqlite3')
    repo.initialize(now=NOW)
    source, video = fixtures._source_and_video(repo, 'cloud-cancel-public')
    data = tmp_path / 'DATA'
    data.mkdir()
    raw = b'Fixture canonical evidence.'
    name = f'{video}-1000-1500.txt'
    (data / name).write_bytes(raw)
    repo.upsert_artifact(ArtifactWrite(artifact_id=f'artifact-{video}-1000-1500',
        artifact_key=f'artifact-key-{video}-1000-1500', video_id=video, job_id=None,
        kind=ArtifactKind.TRANSCRIPT_CANONICAL, storage_root=StorageRoot.DATA,
        relative_path=name, content_hash=hashlib.sha256(raw).hexdigest(), provider=None,
        model=None, producer_version='v1', retention_class=RetentionClass.LONG_LIVED,
        expires_at=None), now=NOW)
    evidence = fixtures._evidence(repo, video)
    calls = []
    def credential():
        calls.append('fake-key')
        return 'synthetic-secret' if tls else None
    def wire(*_):
        calls.append('fake-known-no-POST')
        if body is not None:
            return d._BigModelWireResponse(429, body)
        raise d.CloudDistillationPreDispatchError('known synthetic TLS failure before HTTP bytes')
    cls = d.BigModelGlm47FlashGroundingV2DistillationTransport if v2 else d.BigModelGlm47FlashDistillationTransport
    adapter = cls(authorization=d.CloudDistillationAuthorization(), credential_resolver=credential, wire_transport=wire)
    service = fixtures._service(repo, adapter, fixtures._FakeBudget(True, state=budget))
    if reservation_id is not None:
        service._reservation_id = lambda **_: reservation_id
    reserved = service.reserve_distillation_execution(source_id=source, video_id=video, evidence_ids=(evidence,))
    _, value = service._reserved_command_from_record(repo.get_distillation_execution(reserved.execution_id))
    adapter._authorization = d.CloudDistillationAuthorization(cloud_enabled=True, provider='zhipu_bigmodel',
        model='glm-4.7-flash', credential_available=True, provider_available=True,
        qualification_input_hash=value.semantic_hash)
    if consent_kind is not None:
        service.authorize_reserved_cloud_execution(reserved.execution_id, consent_kind=consent_kind)
    if finish:
        result = (service.continue_qualification_reserved_distillation(reserved.execution_id) if consent_kind == 'OWNER_QUALIFICATION'
            else service.continue_reserved_distillation(reserved.execution_id))
        assert (result.status.value, result.invocation_count) == (('WAITING_MODEL', 0) if body is None else ('REJECTED_OUTPUT', 1))
    return repo, service, reserved.execution_id, video, data, calls


@pytest.mark.parametrize('v2', [False, True])
@pytest.mark.parametrize('tls', [False, True])
def test_proven_cloud_wait_cancel_is_append_only_restart_and_backup_safe(tmp_path, v2, tls):
    repo, service, execution_id, video, data, calls = setup_wait(tmp_path, v2=v2, tls=tls)
    with repo._connect() as c:
        names=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!=?",(TABLE,))]
        before = {name: [tuple(row) for row in c.execute('SELECT * FROM '+name)] for name in names}
    files_before={str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}
    backup = BackupRestoreService(database=tmp_path / 'state.sqlite3', data_root=data)
    assert backup.readiness()['reasons'] == ['DISTILLATION_ACTIVE']
    assert repo.can_cancel_waiting_model_execution(execution_id)
    cancelled = repo.cancel_waiting_model_execution(execution_id, video_id=video, now=NOW+timedelta(seconds=1))
    assert cancelled.status == 'CANCELLED' and cancelled.invocation_count == 0
    assert repo.cancel_waiting_model_execution(execution_id, video_id=video, now=NOW+timedelta(seconds=2)) == cancelled
    with repo._connect() as c:
        for name, rows in before.items():
            assert [tuple(row) for row in c.execute('SELECT * FROM '+name)] == rows
        assert c.execute('SELECT count(*) FROM '+TABLE).fetchone()[0] == 1
    assert {str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}==files_before
    count = len(calls)
    assert service.continue_qualification_reserved_distillation(execution_id).status.value == 'CANCELLED'
    assert len(calls) == count
    restarted = SQLiteStateRepository(tmp_path / 'state.sqlite3')
    assert restarted.get_distillation_execution(execution_id) == cancelled
    assert not restarted.can_cancel_waiting_model_execution(execution_id)
    assert restarted.get_distillation_resource_usage(execution_id).cost_microunits is None
    assert backup.readiness()['ready'] is True


def test_new_receipt_is_exactly_twelve_fields_and_schema43(tmp_path):
    repo = SQLiteStateRepository(tmp_path / 'state.sqlite3')
    assert repo.initialize(now=NOW).version == 43
    with repo._connect() as c:
        assert tuple(row[1] for row in c.execute('PRAGMA table_info('+TABLE+')')) == (
            'execution_id','source_id','video_id','reason','use_case','selected_provider',
            'selected_model','output_language','budget_state','checkpoint_updated_at','cancelled_at','outcome')

@pytest.mark.parametrize('code', ['1113','1302','1305','1308','1315'])
def test_bigmodel_429_observation_drops_private_body(code):
    import json
    response = d._BigModelWireResponse(429, json.dumps({'error': {'code': code, 'message': 'PRIVATE-SECRET-REASONING'}}).encode())
    with pytest.raises(d.KnownCloudDistillationResponseError) as caught:
        d.BigModelGlm47FlashDistillationTransport._decode(response, 1)
    assert getattr(caught.value, 'safe_error_code', None) == code
    assert 'PRIVATE' not in repr(vars(caught.value))


@pytest.mark.parametrize('body', [b'{}', b'{"error":{"code":"9999","message":"PRIVATE"}}',
    b'{"error":{"code":true}}', b'{"error":{"code":"1302","code":"1113"}}', b'\xff', b'x'*8193])
def test_unknown_or_malformed_429_stays_generic(body):
    with pytest.raises(d.KnownCloudDistillationResponseError) as caught:
        d.BigModelGlm47FlashDistillationTransport._decode(d._BigModelWireResponse(429,body),1)
    assert type(caught.value) is d.KnownCloudDistillationResponseError


@pytest.mark.parametrize('v2', [False,True])
def test_http429_code_is_atomic_non_authoritative_and_backup_safe(tmp_path,v2):
    import sqlite3
    repo,service,execution_id,video,data,calls=setup_wait(tmp_path,v2=v2,tls=True,
        body=b'{"error":{"code":1308,"message":"PRIVATE-SECRET"},"reasoning_content":"PRIVATE-THINKING"}')
    assert repo.get_bigmodel_http429_code(execution_id)=='1308'
    usage=repo.get_distillation_resource_usage(execution_id)
    assert usage.outcome=='CLOUD_HTTP_ERROR' and usage.http_status_code==429 and usage.invocation_count==1
    assert usage.cost_microunits is None and not repo.can_cancel_waiting_model_execution(execution_id)
    with repo._connect() as c:
        before=tuple(c.iterdump())
        assert 'PRIVATE' not in '\n'.join(before)
        with pytest.raises(sqlite3.IntegrityError,match='immutable'):
            c.execute('UPDATE distillation_zhipu_http429_observations SET error_code=error_code')
        with pytest.raises(sqlite3.IntegrityError,match='immutable'):
            c.execute('DELETE FROM distillation_zhipu_http429_observations')
    count=len(calls)
    assert service.continue_qualification_reserved_distillation(execution_id).invocation_count==1
    assert len(calls)==count
    backup=BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=data)
    archive=backup.create_backup()
    path,_=backup.backup_download(archive.backup_id)
    staged=backup.stage_restore(path.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    restored=SQLiteStateRepository(tmp_path/'state.sqlite3')
    assert restored.get_bigmodel_http429_code(execution_id)=='1308'
    with restored._connect() as c:
        assert tuple(c.iterdump())==before


@pytest.mark.parametrize('consent_kind', ['USER_CONFIRMATION','OWNER_QUALIFICATION'])
def test_only_exact_admitted_budget_and_existing_consent_can_cancel(tmp_path,consent_kind):
    repo,_,eid,video,_,_=setup_wait(tmp_path,consent_kind=consent_kind,budget='PUBLIC_DIAGNOSTIC_ANTICIPATED_FREE_MAX_ONE')
    assert repo.can_cancel_waiting_model_execution(eid)
    assert repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW).status=='CANCELLED'


def test_unknown_budget_stays_closed(tmp_path):
    from youtube_intel.state import StateStoreError
    repo,_,eid,video,data,_=setup_wait(tmp_path,budget='UNPROVED')
    assert not repo.can_cancel_waiting_model_execution(eid)
    with pytest.raises(StateStoreError):
        repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    assert not BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=data).readiness()['ready']


@pytest.mark.parametrize('posture', ['PENDING','CLAIMED','WAITING_BUDGET','AMBIGUOUS'])
def test_unfinished_or_unknown_execution_cannot_cancel(tmp_path,posture):
    from youtube_intel.state import StateStoreError
    repo,_,eid,video,_,_=setup_wait(tmp_path,finish=False)
    record=repo.get_distillation_execution(eid)
    if posture=='CLAIMED':
        assert repo.claim_reserved_distillation_execution(**identity(record),now=NOW)
    elif posture!='PENDING':
        repo.finish_distillation_without_admission(execution_id=eid,status=posture,budget_state='ADMITTED',
            outcome='TRANSPORT_OUTCOME_UNKNOWN' if posture=='AMBIGUOUS' else 'BUDGET_DENIED',
            invocation_count=1 if posture=='AMBIGUOUS' else 0,actual_provider=None,actual_model=None,
            input_tokens=None,output_tokens=None,cost_microunits=None,duration_ms=None,now=NOW)
    assert not repo.can_cancel_waiting_model_execution(eid)
    with pytest.raises(StateStoreError):
        repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)


def identity(record):
    return {key:getattr(record,key) for key in ('execution_id','source_id','video_id','reason','use_case',
        'selected_provider','selected_model','output_language')}


def test_concurrent_cancel_idempotent_and_claim_cannot_reanimate(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    repo,_,eid,video,_,_=setup_wait(tmp_path)
    record=repo.get_distillation_execution(eid)
    barrier=Barrier(2)
    def cancel():
        barrier.wait()
        return SQLiteStateRepository(tmp_path/'state.sqlite3').cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(cancel) for _ in range(2)]
        results=[f.result() for f in futures]
    assert results[0]==results[1] and results[0].status=='CANCELLED'
    assert not repo.claim_reserved_distillation_execution(**identity(record),now=NOW)
    with repo._connect() as c:
        assert c.execute('SELECT count(*) FROM '+TABLE).fetchone()[0]==1


def test_cancel_rechecks_public_authority_after_advisory_snapshot(tmp_path,monkeypatch):
    from youtube_intel.state import StateStoreError
    repo,_,eid,video,_,_=setup_wait(tmp_path)
    reader=SQLiteStateRepository(tmp_path/'state.sqlite3')
    validate=reader._validate_zhipu_execution
    with repo._connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
    def interleave(connection,checkpoint):
        assert connection.in_transaction
        with repo._connect() as writer:
            writer.execute("UPDATE videos SET availability='private' WHERE video_id=?",(video,))
            writer.commit()
        validate(connection,checkpoint)
    monkeypatch.setattr(reader,'_validate_zhipu_execution',interleave)
    assert reader.can_cancel_waiting_model_execution(eid)
    assert not repo.can_cancel_waiting_model_execution(eid)
    with pytest.raises(StateStoreError):
        repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)


def test_receipt_guards_and_schema_tamper_fail_closed(tmp_path):
    import sqlite3

    from youtube_intel.state import StateStoreError
    repo,_,eid,video,data,_=setup_wait(tmp_path)
    repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    with repo._connect() as c:
        for statement in ('UPDATE '+TABLE+' SET cancelled_at=cancelled_at', 'DELETE FROM '+TABLE,
            'UPDATE distillation_execution_checkpoints SET status=status'):
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(statement)
        c.execute('DROP TRIGGER cloud_wait_cancellation_immutable_update')
        c.commit()
    with pytest.raises((ValueError,StateStoreError)):
        repo.get_distillation_execution(eid)
    assert not BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=data).readiness()['ready']


def test_populated42_migrates_all81_tables_and19_data_unchanged(tmp_path):
    from types import SimpleNamespace
    fixture=_load_module('test_bigmodel_public_first_case')
    fixture.unpack_public_stock(SimpleNamespace(sha=lambda raw:hashlib.sha256(raw).hexdigest()),tmp_path)
    repo=SQLiteStateRepository(tmp_path/'state.sqlite3')
    with repo._connect() as c:
        tables={row[0]:[tuple(v) for v in c.execute('SELECT * FROM "'+row[0]+'"')] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert len(tables)==81
    data=tmp_path/'DATA'
    files={str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}
    assert len(files)==19
    assert repo.initialize(now=NOW).version==43
    with repo._connect() as c:
        for table,rows in tables.items():
            if table!='schema_migrations':
                assert [tuple(row) for row in c.execute('SELECT * FROM "'+table+'"')]==rows
        assert [tuple(row) for row in c.execute('SELECT * FROM schema_migrations WHERE version<=42')]==tables['schema_migrations']
        assert c.execute('SELECT count(*) FROM '+TABLE).fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM distillation_zhipu_http429_observations').fetchone()[0]==0
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert {str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}==files


def test_cancelled_wait_full43_backup_restore_preserves_all_rows_and_data(tmp_path):
    repo,_,eid,video,data,_=setup_wait(tmp_path,v2=True)
    cancelled=repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    with repo._connect() as c:
        before=tuple(c.iterdump())
    files={str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}
    backup=BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=data)
    archive=backup.create_backup()
    path,_=backup.backup_download(archive.backup_id)
    staged=backup.stage_restore(path.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    restored=SQLiteStateRepository(tmp_path/'state.sqlite3')
    assert restored.get_distillation_execution(eid)==cancelled
    with restored._connect() as c:
        assert tuple(c.iterdump())==before
    assert {str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}==files


def test_unproven_reservation_id_is_not_cancel_authority(tmp_path):
    from youtube_intel.state import StateStoreError
    repo,_,eid,video,_,_=setup_wait(tmp_path,reservation_id='distillation:reservation:v3:'+'a'*64)
    assert not repo.can_cancel_waiting_model_execution(eid)
    with pytest.raises(StateStoreError):
        repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)


def test_linked_parent_must_be_settled_and_other_work_keeps_backup_blocked(tmp_path):
    import sqlite3

    from youtube_intel.source_run import (
        SourceRunAttentionReason,
        SourceRunChildState,
        SourceRunPriority,
        SourceRunState,
        SourceRunWrite,
    )
    repo,_,eid,video,data,_=setup_wait(tmp_path)
    source=repo.get_distillation_execution(eid).source_id
    run=repo.create_source_run(SourceRunWrite.manual_check_now(source_id=source,command_id='cancel-parent',
        priority=SourceRunPriority.P0,created_at=NOW))
    repo.transition_source_run(run.run_id,to_state=SourceRunState.RUNNING,now=NOW)
    repo.record_source_run_child(run.run_id,video_id=video,state=SourceRunChildState.PENDING,distillation_execution_id=eid,now=NOW)
    assert not repo.can_cancel_waiting_model_execution(eid)
    repo.transition_source_run_child(run.run_id,video_id=video,to_state=SourceRunChildState.WAITING,now=NOW)
    repo.transition_source_run(run.run_id,to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE,now=NOW)
    assert repo.can_cancel_waiting_model_execution(eid)
    repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    backup=BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=data)
    assert backup.readiness()['ready']
    with repo._connect() as c:
        with pytest.raises(sqlite3.IntegrityError,match='cancelled cloud'):
            c.execute('UPDATE source_run_video_executions SET state=state WHERE distillation_execution_id=?',(eid,))
        with pytest.raises(sqlite3.IntegrityError,match='cancelled cloud'):
            c.execute('INSERT INTO source_run_video_executions SELECT * FROM source_run_video_executions WHERE distillation_execution_id=?',(eid,))
    repo.create_source_run(SourceRunWrite.manual_check_now(source_id=source,command_id='unrelated-work',
        priority=SourceRunPriority.P0,created_at=NOW))
    assert 'SOURCE_RUN_ACTIVE' in backup.readiness()['reasons']


@pytest.mark.parametrize('payload', [b'{"error":{"code":"1113","message":"PRIVATE"}}', b'x'*100000])
def test_real_wire_boundary_429_reads_bounded_code_only_once(monkeypatch,payload):
    module=_load_module('test_bigmodel_distillation_adapter')
    connection=module._Connection(payload,429)
    module._fake_connection(monkeypatch,connection)
    with pytest.raises(d.KnownCloudDistillationResponseError) as caught:
        module._send()
    assert len(connection.requests)==1 and connection.closed
    assert connection.reads<=2
    assert len(payload)-len(connection.payload)<=8193
    assert getattr(caught.value,'safe_error_code',None)==('1113' if len(payload)<8193 else None)
    assert 'PRIVATE' not in str(caught.value)


def test_429_sidecar_tamper_blocks_backup_and_api_uses_only_safe_code(tmp_path):
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    repo,_,eid,_,data,_=setup_wait(tmp_path,tls=True,body=b'{"error":{"code":"1315","message":"PRIVATE"}}')
    app=LocalApiApplication(repo,ProductOrchestrationService(repo,now=lambda:NOW),data_root=data,vault_root=tmp_path/'vault',now=lambda:NOW)
    dto=app._distillation_execution_dto(repo.get_distillation_execution(eid))
    assert dto['cloud_http429_code']=='1315' and 'PRIVATE' not in str(dto)
    with repo._connect() as c:
        c.execute('DROP TRIGGER zhipu_http429_observation_immutable_update')
        c.commit()
    with pytest.raises(ValueError,match='schema differs'):
        repo.get_bigmodel_http429_code(eid)
    assert not BackupRestoreService(database=tmp_path/'state.sqlite3',data_root=data).readiness()['ready']


def test_known_zero_without_consent_is_not_cancellable(tmp_path):
    from youtube_intel.state import StateStoreError
    repo,_,eid,video,_,_=setup_wait(tmp_path,finish=False,consent_kind=None)
    repo.finish_distillation_without_admission(execution_id=eid,status='WAITING_MODEL',budget_state='ADMITTED',
        outcome='MODEL_UNAVAILABLE_BEFORE_TRANSPORT',invocation_count=0,actual_provider=None,actual_model=None,
        input_tokens=None,output_tokens=None,cost_microunits=None,duration_ms=None,now=NOW)
    assert not repo.can_cancel_waiting_model_execution(eid)
    with pytest.raises(StateStoreError):
        repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)


def test_changed_current_interest_does_not_rewrite_original_consent(tmp_path):
    repo,_,eid,video,_,_=setup_wait(tmp_path)
    with repo._connect() as c:
        consent=tuple(c.execute('SELECT * FROM distillation_zhipu_cloud_authorizations').fetchone())
    fixtures.SourcePolicyApplicationService(repo,now=lambda:NOW).update_global(command_id='changed-current-focus',
        initial_history_count=5,per_run_max_new_videos=5,focus_rules=('Changed current interest',),ignore_rules=(),
        distillation_style=fixtures.DistillationStyle.BALANCED)
    assert repo.can_cancel_waiting_model_execution(eid)
    repo.cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    with repo._connect() as c:
        assert tuple(c.execute('SELECT * FROM distillation_zhipu_cloud_authorizations').fetchone())==consent


def test_old42_safe_http429_observation_is_optional_generic_compatibility(tmp_path,monkeypatch):
    legacy=_load_module('test_backup_restore')
    load=SQLiteStateRepository._load_migrations
    with monkeypatch.context() as patch:
        patch.setattr(SQLiteStateRepository,'_load_migrations',lambda self:tuple(m for m in load(self) if m.version<=42))
        _,_,_,repo,_=legacy._workspace(tmp_path)
        request=legacy._zhipu_request(repo)
        repo.authorize_cloud_execution(authorization_id='synthetic-old42-consent',execution_id=request['execution_id'],provider='zhipu_bigmodel',
            model='glm-4.7-flash',verified_input_hash='f'*64,consent_kind='OWNER_QUALIFICATION',now=legacy.NOW)
        assert repo.claim_reserved_distillation_execution(**request,now=legacy.NOW)
        repo.finish_distillation_cloud_response_failure(execution_id=request['execution_id'],budget_state='ADMITTED',
            outcome='CLOUD_HTTP_ERROR',http_status_code=429,bigmodel_error_code='1302',now=legacy.NOW)
        assert repo.get_bigmodel_http429_code(request['execution_id']) is None
        assert repo.get_distillation_resource_usage(request['execution_id']).invocation_count==1


def test_pending_claim_race_never_uses_cancellation_as_dispatch_permission(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from youtube_intel.state import StateStoreError
    repo,_,eid,video,_,_=setup_wait(tmp_path,finish=False)
    request=identity(repo.get_distillation_execution(eid))
    barrier=Barrier(2)
    def cancel():
        barrier.wait()
        with pytest.raises(StateStoreError):
            SQLiteStateRepository(tmp_path/'state.sqlite3').cancel_waiting_model_execution(eid,video_id=video,now=NOW)
    def claim():
        barrier.wait()
        return SQLiteStateRepository(tmp_path/'state.sqlite3').claim_reserved_distillation_execution(**request,now=NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=pool.submit(cancel),pool.submit(claim)
        a.result()
        assert b.result()
    assert repo.get_distillation_execution(eid).invocation_count==1
    with repo._connect() as c:
        assert c.execute('SELECT count(*) FROM '+TABLE).fetchone()[0]==0


@pytest.mark.parametrize('mode', ['timeout','truncated','non429'])
def test_error_observation_never_upgrades_incomplete_or_other_http_response(monkeypatch,mode):
    module=_load_module('test_bigmodel_distillation_adapter')
    connection=module._Connection(b'{"error":{"code":"1302","message":"PRIVATE"}}',503 if mode=='non429' else 429)
    if mode=='timeout':
        def timeout(_size):
            raise TimeoutError('PRIVATE')
        connection.read1=timeout
    if mode=='truncated':
        connection.length=1
    module._fake_connection(monkeypatch,connection)
    with pytest.raises(d.KnownCloudDistillationResponseError) as caught:
        module._send()
    assert type(caught.value) is d.KnownCloudDistillationResponseError
    assert caught.value.http_status==(503 if mode=='non429' else 429)
    assert len(connection.requests)==1 and connection.closed
    assert 'PRIVATE' not in repr(vars(caught.value))


def test_m043_failure_rolls_back_both_new_tables_and_all42_rows(tmp_path,monkeypatch):
    from dataclasses import replace

    from youtube_intel.state import MigrationError
    repo=SQLiteStateRepository(tmp_path/'state.sqlite3')
    migrations=repo._load_migrations()
    legacy=tuple(m for m in migrations if m.version<=42)
    monkeypatch.setattr(repo,'_load_migrations',lambda:legacy)
    assert repo.initialize(now=NOW).version==42
    fixtures._source_and_video(repo,'migration-preserved-public')
    with repo._connect() as c:
        before=tuple(c.iterdump())
    m043=next(m for m in migrations if m.version==43)
    broken=replace(m043,sql=m043.sql+'\nSELECT missing_m043_rollback_probe;')
    monkeypatch.setattr(repo,'_load_migrations',lambda:(*legacy,broken))
    with pytest.raises(MigrationError,match='failed to apply migration 43'):
        repo.initialize(now=NOW)
    with repo._connect() as c:
        assert tuple(c.iterdump())==before
        assert c.execute('PRAGMA user_version').fetchone()[0]==42


def test_invalid429_observation_rolls_back_claim_finish_without_replay(tmp_path):
    repo,_,eid,_,_,_=setup_wait(tmp_path,finish=False)
    assert repo.claim_reserved_distillation_execution(**identity(repo.get_distillation_execution(eid)),now=NOW)
    with pytest.raises(ValueError):
        repo.finish_distillation_cloud_response_failure(execution_id=eid,budget_state='ADMITTED',outcome='CLOUD_HTTP_ERROR',
            http_status_code=429,bigmodel_error_code='PRIVATE-UNALLOWLISTED',now=NOW)
    with repo._connect() as c:
        before=tuple(c.iterdump())
        # A broken new guard must roll the whole finalization back, leaving the
        # original claimed/unknown execution blocked rather than silently losing metadata.
        c.execute("CREATE TRIGGER synthetic_observation_failure BEFORE INSERT ON distillation_zhipu_http429_observations BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
        c.commit()
    with pytest.raises(ValueError,match='schema differs'):
        repo.finish_distillation_cloud_response_failure(execution_id=eid,budget_state='ADMITTED',outcome='CLOUD_HTTP_ERROR',
            http_status_code=429,bigmodel_error_code='1302',now=NOW)
    with repo._connect() as c:
        c.execute('DROP TRIGGER synthetic_observation_failure')
        c.commit()
        assert tuple(c.iterdump())==before
    assert repo.get_distillation_execution(eid).invocation_count==1
    assert not repo.can_cancel_waiting_model_execution(eid)
