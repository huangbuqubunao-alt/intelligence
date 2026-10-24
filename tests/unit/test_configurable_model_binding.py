"""Exact configurable identity never grants execution or borrows qualifications."""
import pytest


def test_actual0409_binding_is_finite_immutable_and_not_0406():
    from youtube_intel.local_distillation_profile import resolve_model_binding
    value=resolve_model_binding('ollama','qwen3.5:9b-q4_K_M','sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90','0.40.9')
    assert value.runtime == '0.40.9' and value.executable is True
    assert '0.40.9' in value.short_profile_id and '0.40.9' in value.long_profile_id
    assert dict(value.binary_hashes)['ollama']=='be4b054f8ebf8b3b185daa30671849a80f22c2b2ef45e064de562f69aba46a96'
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        value.runtime='0.40.6'


@pytest.mark.parametrize('provider,model,digest,runtime',[
    ('cloud','qwen3.5:9b-q4_K_M','sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90','0.40.9'),
    ('ollama','qwen3.5:4b-q4_K_M','sha256:d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04','0.40.9'),
    ('ollama','qwen3.5:9b-q4_K_M','wrong','0.40.9'),
    ('ollama','qwen3.5:9b-q4_K_M','sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90','0.40.10'),
])
def test_unknown_or_failed_model_cannot_resolve_execution_binding(provider,model,digest,runtime):
    from youtube_intel.local_distillation_profile import resolve_model_binding
    with pytest.raises(ValueError):
        resolve_model_binding(provider,model,digest,runtime)


def test_nominal0406_binding_is_history_only_and_native_host_must_deny():
    from youtube_intel.local_distillation_profile import (
        CURRENT_RUNTIME_PROFILE_ID,
        binding_for_profile,
    )
    from youtube_intel.local_model_capacity import runtime_binary_hashes
    assert binding_for_profile(CURRENT_RUNTIME_PROFILE_ID).executable is False
    with pytest.raises(OSError):
        runtime_binary_hashes(CURRENT_RUNTIME_PROFILE_ID)


def test_active_native_and_qualification_projections_have_distinct_runtime_binding():
    from youtube_intel.local_distillation_profile import (
        ACTUAL_RUNTIME_PROFILE_ID,
        CURRENT_RUNTIME_PROFILE_ID,
    )
    from youtube_intel.local_distillation_qualification import qualification_projection
    from youtube_intel.local_native_capacity import current_descriptor
    current = qualification_projection(ACTUAL_RUNTIME_PROFILE_ID, 'YT_TIMED')
    old = qualification_projection(CURRENT_RUNTIME_PROFILE_ID, 'YT_TIMED')
    assert current['runtime'] == current_descriptor(ACTUAL_RUNTIME_PROFILE_ID)['runtime'] == '0.40.9'
    assert current['local_profile_id'] != old['local_profile_id'] and old['runtime'] == '0.40.6'
    assert current['options'] == old['options'] and current['schema'] == old['schema']


def test_unrelated_qualification_never_replaces_user_configured_model(monkeypatch):
    import youtube_intel.local_distillation_qualification as q
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.runtime_composition import (
        build_production_local_distillation_transport,
    )
    class OtherModelAuthority:
        def permits(self, *args, **kwargs):
            return True
    monkeypatch.setattr(q, 'read_reviewed_qualifications', lambda: OtherModelAuthority())
    transport = build_production_local_distillation_transport(LocalScoringSettings(model='qwen3:8b', expected_model_digest='sha256:' + 'a'*64))
    assert transport.actual_model == 'qwen3:8b' and transport.local_profile_id is None


@pytest.mark.parametrize('damage', ['none', 'old-version', 'wrong-port', 'server-inode', 'runner-inode', 'library-inode', 'changed-host', 'updated-after-start', 'missing-library', 'unknown-library', 'daemon-only-library', 'cold'])
def test_api_version_and_mapped_bytes_belong_to_same_observed_processes(tmp_path, monkeypatch, damage):
    from types import SimpleNamespace

    from youtube_intel import local_model_capacity as c
    paths = {name: tmp_path/name for name in ('ollama','llama-server','libllama-server-impl.dylib')}
    import os
    for p in paths.values():
        p.write_bytes(b'isolated actual mapped file')
        os.utime(p, (1,1))
    if damage == 'updated-after-start':
        os.utime(paths['ollama'], (1800000000,1800000000))
    monkeypatch.setattr(c, 'ROOT', tmp_path)
    server = f'10 Sat Oct 24 00:00:00 2026 {paths["ollama"]} serve'
    runner = '' if damage=='cold' else f'20 Sat Oct 24 00:00:00 2026 {paths["llama-server"]} --offline'
    monkeypatch.setattr(c, 'processes', lambda binary: server if binary=='ollama' else runner)
    host = c.HostObservation(tuple((p,c.file_identity(p)) for p in paths.values()),server,runner)
    calls=[]
    def cmd(argv, **kwargs):
        pid=argv[argv.index('-p')+1]
        assert '-nP' in argv
        if '-iTCP:11434' in argv:
            return SimpleNamespace(stdout='p10\nn127.0.0.1:'+('11435' if damage=='wrong-port' else '11434')+'\n')
        names=['ollama'] if pid=='10' else ['llama-server','libllama-server-impl.dylib']
        if damage in {'missing-library','unknown-library','daemon-only-library'} and pid=='20':
            names=['llama-server']
        if damage=='daemon-only-library' and pid=='10':
            names.append('libllama-server-impl.dylib')
        chunks=['p'+pid]
        for name in names:
            st=paths[name].stat()
            altered=(damage=='server-inode' and name=='ollama' or damage=='runner-inode' and name=='llama-server' or damage=='library-inode' and name=='libllama-server-impl.dylib')
            chunks += ['ftxt','D'+hex(st.st_dev),'i'+str(st.st_ino+int(altered)),'n'+str(paths[name])]
        if damage=='unknown-library' and pid=='20':
            chunks += ['ftxt','n'+str(paths['libllama-server-impl.dylib'])]
        return SimpleNamespace(stdout='\n'.join(chunks)+'\n')
    monkeypatch.setattr(c.subprocess,'run',cmd)
    def send(path, **kwargs):
        calls.append(path)
        if damage=='changed-host':
            monkeypatch.setattr(c.HostObservation,'is_current',lambda self:False)
        return {'version':'0.40.6' if damage=='old-version' else '0.40.9'}
    if damage in {'none','cold'}:
        c.verify_runtime_api(host,'http://127.0.0.1:11434',send,'0.40.9')
        assert calls==['/api/version']
    else:
        with pytest.raises(OSError):
            c.verify_runtime_api(host,'http://127.0.0.1:11434',send,'0.40.9')
    assert all(path=='/api/version' for path in calls)


@pytest.mark.parametrize('profile,expected', [
    ('local-grounding-qwen35-9b-thinking-v1','e66d503614d6d7ebfc59efd0178d7aa2b6da7fbc0ce0d0382d85389169dced49'),
    ('local-grounding-qwen35-9b-fixed-runtime-v2','c4b15b5950308a41b384dc07fb9079755823fb472acd67bc5f8ee744d494322e'),
    ('local-grounding-qwen35-9b-runtime-0.40.6-v3','1f21239397b6072f5cd3aa3b04f93554dcdb028532cf4198c801e95ca4233523'),
])
def test_all_old_profile_projection_bytes_stay_frozen(profile, expected):
    from youtube_intel.local_distillation_profile import digest, resolve_profile
    assert digest(resolve_profile(profile).projection('YT_TIMED',{})) == expected


@pytest.mark.parametrize('candidate,expected', [
    ('local-grounding-qwen35-9b-fixed-runtime-v2','92b37a8d2c2dbfe8e41946fb88e11fda55f9517f2fe023e9eea76395d968559a'),
    ('local-intelligence-qwen35-9b-ollama-0.40.6-v1','06ceaa109cc4cb05f40612c3e41235789191188ec7220be22421a7d924048da3'),
])
def test_historical_catalog_identity_and_serialized_shape_are_unchanged(candidate, expected):
    from dataclasses import asdict

    from youtube_intel.local_intelligence_catalog import resolve_candidate
    resolved = resolve_candidate(candidate)
    assert resolved.catalog_hash == expected
    assert set(asdict(resolved)) == {'candidate_id','model','model_digest','runtime'}


def test_new_long_profile_native_request_same_but_frozen_identity_independent():
    import json

    from youtube_intel.long_distillation_profile import (
        ACTUAL_RUNTIME_PROFILE_ID,
        CURRENT_RUNTIME_PROFILE_ID,
        resolve_long_profile,
    )
    old = resolve_long_profile(CURRENT_RUNTIME_PROFILE_ID)
    new = resolve_long_profile(ACTUAL_RUNTIME_PROFILE_ID)
    old_fields, new_fields = json.loads(old.profile_wire), json.loads(new.profile_wire)
    assert old.profile_hash == '4ea6bf0aca53584afd0bb2ad47d2d356abf43b0d6bb4b8110e5821cebe6b12f9'
    assert new_fields == dict(old_fields,profile_id=ACTUAL_RUNTIME_PROFILE_ID,runtime='0.40.9')
    assert new.profile_hash != old.profile_hash


def test_old_runtime_qualification_cannot_grant_new_transport_or_long_pair(monkeypatch):
    import youtube_intel.local_distillation_qualification as q
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.local_distillation_profile import (
        ACTUAL_RUNTIME_PROFILE_ID,
        CURRENT_RUNTIME_PROFILE_ID,
        resolve_profile,
    )
    from youtube_intel.runtime_composition import (
        build_production_local_distillation_transport,
    )
    class OldOnly:
        def permits(self, projection, *args, **kwargs):
            return projection['runtime'] == '0.40.6'
    monkeypatch.setattr(q,'read_reviewed_qualifications',lambda:OldOnly())
    p = resolve_profile(ACTUAL_RUNTIME_PROFILE_ID)
    t = build_production_local_distillation_transport(LocalScoringSettings(model=p.model,expected_model_digest=p.model_digest))
    assert t.local_profile_id == ACTUAL_RUNTIME_PROFILE_ID
    assert t.long_profile_qualified(q.LONG_ACTUAL,'en',__import__('datetime').datetime.now(__import__('datetime').UTC)) is False
    assert t.long_profile_qualified(q.LONG_CURRENT,'en',__import__('datetime').datetime.now(__import__('datetime').UTC)) is False
    old = build_production_local_distillation_transport(LocalScoringSettings(model=p.model,expected_model_digest=p.model_digest),runtime='0.40.6')
    assert old.local_profile_id is None and old.local_profile_id != CURRENT_RUNTIME_PROFILE_ID


@pytest.mark.parametrize('long',[False,True])
def test_actual0409_harness_uses_same_original_cases_without_execution_authority(long):
    from conftest import _load_module

    from youtube_intel.local_distillation_profile import (
        ACTUAL_LONG_PROFILE_ID,
        ACTUAL_RUNTIME_PROFILE_ID,
    )
    harness = _load_module('test_local_grounding_harness')._harness()
    profile = ACTUAL_LONG_PROFILE_ID if long else ACTUAL_RUNTIME_PROFILE_ID
    value = harness.describe(profile)
    assert value['real_model_calls'] == 0 and value['production_qualified'] is False
    assert all(p['runtime']=='0.40.9' for p in value['profiles'].values())
    assert list(value['case_order']['YT_TIMED'])[:10] == list(harness.CASE_LANGUAGES['YT_TIMED'])
    assert len(value['case_order']['YT_TIMED']) == (12 if long else 10)


@pytest.mark.parametrize('long',[False,True])
def test_history_only_harness_does_not_allow_new_generation(tmp_path, monkeypatch,long):
    from types import SimpleNamespace

    from conftest import _load_module

    from youtube_intel.local_distillation_profile import (
        CURRENT_LONG_PROFILE_ID,
        CURRENT_RUNTIME_PROFILE_ID,
    )
    harness = _load_module('test_local_grounding_harness')._harness()
    profile = CURRENT_LONG_PROFILE_ID if long else CURRENT_RUNTIME_PROFILE_ID
    monkeypatch.setattr(harness,'validate_execution_package',lambda *a:({},SimpleNamespace(binding={'profile_id':profile}),{}))
    with pytest.raises(ValueError,match='historical runtime profile cannot generate'):
        harness.execute_case(tmp_path,tmp_path/'unused-permit',tmp_path/'unused-freeze')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('long,scope',[(False,'YT_TIMED'),(False,'LOCAL_TIMED'),(False,'LOCAL_TEXT'),(True,'YT_TIMED')])
def test_actual_runtime_structural_records_never_borrow_older_scope_or_grant_package_authority(long,scope):
    import copy

    from conftest import _load_module

    from youtube_intel import local_distillation_qualification as q
    from youtube_intel.local_distillation_profile import (
        ACTUAL_LONG_PROFILE_ID,
        ACTUAL_RUNTIME_PROFILE_ID,
        CURRENT_RUNTIME_PROFILE_ID,
    )
    fixture = _load_module('test_current_local_qualification').fixture
    profile = ACTUAL_LONG_PROFILE_ID if long else ACTUAL_RUNTIME_PROFILE_ID
    raw_record, projection = fixture(profile,scope)
    record = q.QualificationRecord.model_validate(raw_record)
    now = _load_module('test_local_grounding_qualification').NOW
    assert record.permits(projection,'en',now)
    old = q.qualification_projection(q.LONG_CURRENT if long else CURRENT_RUNTIME_PROFILE_ID,scope)
    assert not record.permits(old,'en',now)
    from youtube_intel.local_distillation_profile import canonical
    raw = canonical({'version':q.VERSION,'records':[raw_record]})
    assert not q.read_reviewed_qualifications(raw).permits(projection,'en',now=now)
    changed=copy.deepcopy(record)
    changed.binding['runtime']='0.40.6'
    assert not changed.permits(projection,'en',now)
