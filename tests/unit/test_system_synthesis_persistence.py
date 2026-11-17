"""Offline schema44 provenance, not model qualification or fee authorization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis_persistence as p
from youtube_intel import system_synthesis_profile as profile

support = _load_module("test_long_input_wait_lifecycle")
NOW = support.NOW


def setup(tmp_path: Path):
    repo, root, source, video, *_ = support.workspace(tmp_path, 2)
    prepared = p.prepare(
        repo, source_id=source, video_id=video, command_id="synthetic-one", output_language="en", now=NOW
    )
    return repo, root, prepared


def test_finite_profile_has_real_identity_and_never_grants_qualification() -> None:
    descriptor = profile.resolve_profile(profile.PROFILE_ID)
    assert descriptor["model"] == "kimi-k3.1-pro"
    assert descriptor["max_completion_tokens"] == 5888
    assert descriptor["endpoint"] == "https://api.moonshot.cn/v1/chat/completions"
    assert descriptor["retries"] == 0 and descriptor["qualified"] is False
    with pytest.raises(ValueError):
        profile.resolve_profile("kimi-k2.6")


def test_atomic_reserve_contains_exact_replayable_summary_and_wire(tmp_path: Path) -> None:
    repo, root, prepared = setup(tmp_path)
    assert not repo.get_distillation_execution(prepared.execution_id)
    p.reserve(repo, prepared, now=NOW)
    record = repo.get_distillation_execution(prepared.execution_id)
    assert record is not None and record.status == "PENDING" and record.invocation_count == 0
    with repo._connect() as connection:
        rebuilt = p.verify_execution(repo, connection, prepared.execution_id)
        assert rebuilt == prepared
        assert len(json.loads(prepared.proof_json)["request"]["summary_context"]["summary"]) == 10
        assert connection.execute("SELECT count(*) FROM system_synthesis_cloud_authorizations").fetchone()[0] == 0


def claim(repo, prepared, *, scope='synthetic-owner-policy', limit=8_000_000, calls=8, prior=0):
    p.confirm_and_claim(repo, prepared, budget=p.SynthesisBudget(scope, limit, calls, prior),
        consent_kind='OWNER_QUALIFICATION', now=NOW)


def raw_positive():
    return json.dumps({'core_conclusion':"Source reports a constraint; this system suggests checking applicability, not assuming proof.",
        'user_relevant_information':['For reliability, verify whether the reported constraint applies; no measured guarantee.'],
        'important_new_information':[], 'meaningful_details':[], 'filtered_noise':[],
        'evidence':[{'ref':'E02','stance':'supporting'}], 'reference_protocol':'bound-evidence-reference-v1'})


def finish(repo, prepared, branch):
    from youtube_intel.state import (
        DistillationCardWrite,
        EvidenceStance,
        IntelligenceClaimKind,
    )
    proof=json.loads(prepared.proof_json)
    refs=proof['capture']['source_refs']
    if branch=='positive':
        raw=raw_positive()
        request=p.request_from_proof(prepared)
        decoded=p.synthesis.decode_system_synthesis(raw,request,request_origin_sha256=request.origin_sha256)
        value=decoded.candidate_projection()
        content={k:v for k,v in value.items() if k!='reference_protocol'}
        content['evidence']=sorted(content['evidence'],key=lambda e:e['evidence_id'])
        cmd=proof['command']
        return repo.admit_distillation(execution_id=prepared.execution_id,intelligence_id='intelligence:'+prepared.execution_id,
            revision_id='revision:'+prepared.execution_id,claim_kind=IntelligenceClaimKind.SYSTEM_INFERENCE,
            content_hash=profile.sha(json.dumps(content,sort_keys=True,separators=(',',':'))),
            evidence_ids=tuple(e['evidence_id'] for e in content['evidence']),
            evidence_stances=tuple((e['evidence_id'],EvidenceStance(e['stance'])) for e in content['evidence']),
            card=DistillationCardWrite(source_id=cmd['source_id'],video_id=cmd['video_id'],core_conclusion=value['core_conclusion'],
                user_relevant_information=tuple(value['user_relevant_information']),important_new_information=(),meaningful_details=(),filtered_noise=(),
                preference_ids=tuple(cmd['preference_ids']),source_policy_revision_id=cmd['source_policy_revision_id']),
            actual_provider=profile.PAIR[0],actual_model=profile.PAIR[1],input_tokens=100,output_tokens=100,cost_microunits=None,
            duration_ms=1000,http_status_code=200,now=NOW,synthesis_completion=p.Completion(raw))
    if branch=='zero':
        raw=json.dumps({'result':'NO_NEW_INTELLIGENCE','reference_protocol':'bound-evidence-reference-v1',
            'evidence':[{'ref':r['ref']} for r in refs]})
        return repo.record_distillation_no_new_intelligence(execution_id=prepared.execution_id,evidence_ids=tuple(r['evidence_id'] for r in refs),
            budget_state='ADMITTED',actual_provider=profile.PAIR[0],actual_model=profile.PAIR[1],input_tokens=100,output_tokens=20,
            cost_microunits=None,duration_ms=1000,http_status_code=200,now=NOW,synthesis_completion=p.Completion(raw))
    if branch=='http':
        return repo.finish_distillation_cloud_response_failure(execution_id=prepared.execution_id,budget_state='ADMITTED',
            outcome='CLOUD_HTTP_ERROR',http_status_code=429,now=NOW,synthesis_completion=p.Completion())
    return repo.finish_distillation_without_admission(execution_id=prepared.execution_id,status='AMBIGUOUS',budget_state='ADMITTED',
        outcome='TRANSPORT_OUTCOME_UNKNOWN',invocation_count=1,actual_provider=None,actual_model=None,input_tokens=None,
        output_tokens=None,cost_microunits=None,duration_ms=None,now=NOW,synthesis_completion=p.Completion())


@pytest.mark.parametrize('branch',['positive','zero','http','unknown'])
def test_existing_terminal_paths_have_one_authentic_receipt_and_replay(tmp_path, branch):
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    repo, root, prepared=setup(tmp_path)
    p.reserve(repo,prepared,now=NOW)
    claim(repo,prepared)
    result=finish(repo,prepared,branch)
    assert result.invocation_count==1
    with repo._connect() as connection:
        p.verify_database(repo,connection)
        receipt=connection.execute('SELECT * FROM system_synthesis_result_receipts').fetchone()
        assert receipt['raw_text'] is not None if branch in {'positive','zero'} else receipt['raw_text'] is None
    restarted=p.SQLiteStateRepository(repo._database_path)
    restarted.bind_source_storage(root)
    assert restarted.initialize(now=NOW).version==45
    assert restarted.get_distillation_execution(prepared.execution_id)==result
    assert restarted.get_distillation_resource_usage(prepared.execution_id).invocation_count==1
    if branch=='positive':
        card=AuthoritativeIntelligenceReader(restarted).read_recorded_card(result.intelligence_id,result.revision_id)
        assert card.verified.claim_kind.value=='SYSTEM_INFERENCE'
    with pytest.raises((p.StateStoreError, p.sqlite3.Error)):
        claim(repo,prepared)


def test_confirm_requires_explicit_bounded_policy_and_holds_unknown_costs(tmp_path):
    repo, root, prepared=setup(tmp_path)
    p.reserve(repo,prepared,now=NOW)
    reserve=json.loads(prepared.proof_json)['reserve_microunits']
    with pytest.raises(p.sqlite3.IntegrityError):
        claim(repo,prepared,limit=reserve-1)
    assert repo.get_distillation_execution(prepared.execution_id).invocation_count==0
    claim(repo,prepared,limit=reserve,calls=1)
    finish(repo,prepared,'unknown')
    proof=json.loads(prepared.proof_json)
    second=p.prepare(repo,source_id=proof['command']['source_id'],video_id=proof['command']['video_id'],command_id='explicit-new',output_language='en',now=NOW)
    p.reserve(repo,second,now=NOW)
    with pytest.raises(p.sqlite3.IntegrityError):
        claim(repo,second,limit=reserve,calls=1)
    assert repo.get_distillation_execution(second.execution_id).invocation_count==0
    with pytest.raises(p.sqlite3.IntegrityError):
        claim(repo,second,limit=reserve*2,calls=2)


def test_explicit_abandon_is_proof_bound_zero_call_cancel_and_restart_safe(tmp_path):
    from youtube_intel.backup_restore import BackupRestoreService
    repo,root,prepared=setup(tmp_path)
    p.reserve(repo,prepared,now=NOW)
    assert not repo.can_cancel_waiting_model_execution(prepared.execution_id)
    p.abandon_unclaimed(repo,prepared.execution_id,now=NOW)
    assert repo.get_distillation_execution(prepared.execution_id).status=='CANCELLED'
    assert not repo.can_cancel_waiting_model_execution(prepared.execution_id)
    result=repo.cancel_waiting_model_execution(prepared.execution_id,video_id=json.loads(prepared.proof_json)['command']['video_id'],now=NOW)
    assert result.status=='CANCELLED' and result.invocation_count==0
    assert BackupRestoreService(database=repo._database_path,data_root=root).readiness()['ready']
    with pytest.raises((p.StateStoreError,p.sqlite3.Error)):
        claim(repo,prepared)
    with repo._connect() as c:
        assert c.execute('SELECT count(*) FROM system_synthesis_cloud_authorizations').fetchone()[0]==0
        with pytest.raises(p.sqlite3.IntegrityError):
            c.execute("UPDATE distillation_execution_checkpoints SET invocation_count=1 WHERE execution_id=?",(prepared.execution_id,))


@pytest.mark.parametrize('branch',['positive','zero','http','unknown','cancel'])
def test_schema44_backup_restore_preserves_every_row_and_data_file(tmp_path,branch):
    from youtube_intel.backup_restore import BackupRestoreService
    repo,root,prepared=setup(tmp_path)
    p.reserve(repo,prepared,now=NOW)
    if branch=='cancel':
        p.abandon_unclaimed(repo,prepared.execution_id,now=NOW)
    else:
        claim(repo,prepared)
        finish(repo,prepared,branch)
    before=support._inventory(repo,root)
    backup=BackupRestoreService(database=repo._database_path,data_root=root)
    package,_=backup.backup_download(backup.create_backup().backup_id)
    preview=backup.stage_restore(package.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert support._inventory(repo,root)==before
    restarted=p.SQLiteStateRepository(repo._database_path)
    restarted.bind_source_storage(root)
    assert restarted.get_distillation_execution(prepared.execution_id).invocation_count==(0 if branch=='cancel' else 1)


@pytest.mark.parametrize('version', range(34,44))
def test_every_old_backup_verifies_original_schema_then_migrates_preserving_rows_and_files(tmp_path, monkeypatch, version):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.state import SQLiteStateRepository
    migrations=SQLiteStateRepository(tmp_path/'unused')._load_migrations()
    with monkeypatch.context() as patch:
        patch.setattr(SQLiteStateRepository,'_load_migrations',lambda _:tuple(m for m in migrations if m.version<=version))
        repo,root,*_=support.workspace(tmp_path,2)
    before=support._inventory(repo,root)
    backup=BackupRestoreService(database=repo._database_path,data_root=root)
    archive,_=backup.backup_download(backup.create_backup().backup_id)
    preview=backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert support._inventory(repo,root)==before
    assert repo.initialize(now=NOW).version==45
    after, files=support._inventory(repo,root)
    assert {k:v for k,v in after.items() if k in before[0] and k!='schema_migrations'}=={k:v for k,v in before[0].items() if k!='schema_migrations'}
    assert files==before[1] and all(not after[table] for table in p.TABLES)


@pytest.mark.parametrize('point',['synthesis_after_proof','synthesis_after_reservation','synthesis_after_consent','synthesis_after_claim'])
def test_transaction_fault_leaves_no_half_proof_consent_or_claim(tmp_path,monkeypatch,point):
    repo,root,prepared=setup(tmp_path)
    if 'consent' in point or 'claim' in point:
        p.reserve(repo,prepared,now=NOW)
    before=support._inventory(repo,root)
    def fault(name):
        if name==point:
            raise RuntimeError('synthetic injected fault')
    monkeypatch.setattr(repo,'_inject_failure',fault)
    with pytest.raises(RuntimeError,match='synthetic injected fault'):
        if 'consent' in point or 'claim' in point:
            claim(repo,prepared)
        else:
            p.reserve(repo,prepared,now=NOW)
    assert support._inventory(repo,root)==before


@pytest.mark.parametrize('damage',['profile','wire','summary','proof-hash','missing-proof','receipt-raw','receipt-hash','missing-receipt','authorization','guard'])
def test_tampered_provenance_is_rejected_by_read_startup_and_backup(tmp_path,damage):
    from youtube_intel.backup_restore import BackupRestoreService
    repo,root,prepared=setup(tmp_path)
    p.reserve(repo,prepared,now=NOW)
    claim(repo,prepared)
    finish(repo,prepared,'positive')
    with repo._connect() as c:
        if damage=='guard':
            c.execute('DROP TRIGGER distillation_cloud_response_failure_bound')
        else:
            table=p.PROOFS if damage in {'profile','wire','summary','proof-hash','missing-proof'} else p.AUTHORIZATIONS if damage=='authorization' else p.RECEIPTS
            for row in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",(table,)).fetchall():
                c.execute('DROP TRIGGER '+row[0])
            if damage in {'missing-proof','missing-receipt'}:
                c.execute('PRAGMA foreign_keys=OFF')
                c.execute('DELETE FROM '+table)
            elif damage in {'profile','wire','summary'}:
                value=json.loads(prepared.proof_json)
                if damage=='profile':
                    value['transport']['model']='kimi-k2.6'
                elif damage=='wire':
                    value['provider_wire']+=' '
                else:
                    value['capture']['summary_raw']+=' '
                encoded=profile.canonical(value)
                c.execute('UPDATE '+table+' SET proof_json=?,proof_sha256=?',(encoded,profile.sha(encoded)))
            elif damage=='proof-hash':
                c.execute('UPDATE '+table+" SET proof_sha256=?",('0'*64,))
            elif damage=='authorization':
                c.execute('UPDATE '+table+" SET verified_input_hash=?",('0'*64,))
            elif damage=='receipt-raw':
                c.execute('UPDATE '+table+" SET raw_text=?",(raw_positive()+' ',))
            else:
                c.execute('UPDATE '+table+" SET raw_sha256=?",('0'*64,))
    with pytest.raises((p.StateStoreError,ValueError,p.sqlite3.Error)):
        repo.get_distillation_execution(prepared.execution_id)
    with pytest.raises((p.StateStoreError,ValueError,p.sqlite3.Error)):
        repo.initialize(now=NOW)
    assert not BackupRestoreService(database=repo._database_path,data_root=root).readiness()['ready']


def test_claim_rebuilds_current_summary_and_full_input_not_just_digest(tmp_path):
    from dataclasses import replace
    repo,root,prepared=setup(tmp_path)
    with pytest.raises(p.StateStoreError):
        p.reserve(repo,replace(prepared,proof_json=prepared.proof_json+' '),now=NOW)
    p.reserve(repo,prepared,now=NOW)
    with repo._connect() as c:
        c.execute("UPDATE videos SET title='Legitimate changed title' WHERE video_id=?",(json.loads(prepared.proof_json)['command']['video_id'],))
    # Historical proof remains readable; only new confirmation requires exact current identity.
    assert repo.get_distillation_execution(prepared.execution_id).invocation_count==0
    with pytest.raises(p.StateStoreError,match='changed before confirmation'):
        claim(repo,prepared)


def test_unknown_or_legacy_family_cannot_use_abandon_or_impersonate_current_model(tmp_path):
    from youtube_intel.state import DistillationExecutionWrite
    repo,root,prepared=setup(tmp_path)
    proof=json.loads(prepared.proof_json)
    cmd=proof['command']
    with pytest.raises((p.sqlite3.Error,p.StateStoreError)):
        repo.reserve_distillation_execution(DistillationExecutionWrite(execution_id='forged-without-proof',
            source_id=cmd['source_id'],video_id=cmd['video_id'],reason=cmd['reason'],use_case=cmd['use_case'],
            selected_provider=profile.PAIR[0],selected_model=profile.PAIR[1],output_language='en'),now=NOW)
    with pytest.raises((p.StateStoreError,p.sqlite3.Error)):
        p.abandon_unclaimed(repo,'legacy-pending',now=NOW)


def test_concurrent_claim_and_abandon_has_exactly_one_terminal_authority(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    repo,root,prepared=setup(tmp_path)
    p.reserve(repo,prepared,now=NOW)
    barrier=Barrier(2)
    def contender(cancel):
        barrier.wait()
        try:
            if cancel:
                p.abandon_unclaimed(repo,prepared.execution_id,now=NOW)
            else:
                claim(repo,prepared)
            return True
        except (p.StateStoreError,p.sqlite3.Error):
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(contender,cancel) for cancel in [True,False]]
        assert sum(f.result() for f in futures)==1
    result=repo.get_distillation_execution(prepared.execution_id)
    with repo._connect() as c:
        auth=c.execute('SELECT count(*) FROM '+p.AUTHORIZATIONS).fetchone()[0]
        cancel=c.execute('SELECT count(*) FROM '+p.TABLE).fetchone()[0]
    assert (result.invocation_count,auth,cancel) in {(1,1,0),(0,0,1)}
