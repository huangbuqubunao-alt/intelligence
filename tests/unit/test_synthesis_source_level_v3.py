"""Finite v3 structural policy/gate tests, never actual model qualification."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis as synthesis
from youtube_intel import system_synthesis_persistence as persistence
from youtube_intel import system_synthesis_profile as profile
from youtube_intel import system_synthesis_qualification as qualification
from youtube_intel.cloud_spending_policy import price_disclosure
from youtube_intel.distillation import CloudDistillationPreDispatchError
from youtube_intel.local_api import ApiError

pure = _load_module('test_system_synthesis')
V3 = 'moonshot-k31-system-synthesis-v3-source-level-20261106'
POLICY = 'system-synthesis-v3-source-level'


def test_v3_is_distinct_generic_source_level_policy_with_original_full_context():
    previous = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=synthesis.ATTRIBUTION_PROFILE_ID)
    request = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=POLICY)
    old_messages = json.loads(previous.wire_json)['messages']
    messages = json.loads(request.wire_json)['messages']
    assert messages[1:] == old_messages[1:]
    assert 'even when an original speaker label is explicit' in messages[0]['content']
    assert 'Do not merge differing viewpoints into consensus' in messages[0]['content']
    assert 'supported subject-matter entities' in messages[0]['content']
    assert 'Lisha' not in messages[0]['content'] and 'ReLU' not in messages[0]['content']
    assert request.origin_sha256 != previous.origin_sha256
    assert profile.provider_wire(request, V3)


def test_normal_factory_lists_distinct_closed_v3_without_calling_any_wire(tmp_path, monkeypatch):
    authority = _load_module('test_synthesis_reviewed_authority')
    module, root, video, runtime, old_service, calls = authority.actual_factory(tmp_path, monkeypatch, qualified=False)
    with module.offline():
        rows = runtime.application.handle('GET', '/api/v1/cloud-intelligence/profiles')[1]['profiles']
        assert V3 in {row['profile_id'] for row in rows}
        assert not next(row for row in rows if row['profile_id'] == V3)['qualified']
    assert calls == []

authority_tests = _load_module('test_synthesis_reviewed_authority')
runtime_tests = _load_module('test_synthesis_runtime')


def v3_record():
    record = authority_tests.record_fixture()
    binding = qualification.qualification_binding(V3)
    record.update(version=qualification.SOURCE_LEVEL_VERSION, binding=binding)
    for case in record['cases']:
        case.update(profile_sha256=binding['profile_sha256'], code_sha256=binding['code_sha256'])
    return authority_tests.seal_record(record)


def package_fixture(tmp_path, monkeypatch, record):
    raw = profile.canonical({'version': qualification.SOURCE_LEVEL_VERSION, 'records': [record]}).encode()
    resource = tmp_path / 'STRUCTURAL_FAKE_V3_PACKAGE.json'
    resource.write_bytes(raw)
    package = Path(qualification.__file__).parent
    class Package:
        def joinpath(self, name):
            return resource if name == 'resources/system_synthesis_source_level_qualification_v1.json' else package / name
    monkeypatch.setattr(qualification, 'resources', SimpleNamespace(files=lambda name: Package()))
    return raw


def factory(tmp_path, monkeypatch, *, qualified=True, credential=True, enabled=True):
    if qualified:
        package_fixture(tmp_path, monkeypatch, v3_record())
    module, root, video, runtime, old_service, calls = authority_tests.actual_factory(
        tmp_path, monkeypatch, qualified=False, credential=credential, enabled=enabled)
    service = runtime.application._cloud_synthesis_v3_service
    def wire(request, secret, timeout, retries):
        assert secret == 'STRUCTURAL_FAKE_KEY' and retries == 0
        calls.append(request)
        return runtime_tests.moonshot._response(content=runtime_tests.storage.raw_positive(), model=profile.PAIR[1])
    monkeypatch.setattr(service._transport, '_wire_transport', wire)
    return module, root, video, runtime, service, calls


def configure(app, *, profile_id=V3, amount='1'):
    return app.handle('PUT', '/api/v1/settings/cloud-spending-policy', json.dumps({'expected_revision': 0,
        'enabled': True, 'total_cny': '8', 'per_request_cny': amount, 'max_calls': 8,
        'accept_price_hash': price_disclosure(profile_id)['price_hash'], 'acknowledge': True}).encode())


def review(app, video, **extra):
    return authority_tests.review(app, video, V3, **extra)


def confirm(app, video, value, **extra):
    return authority_tests.confirm(app, video, value, profile_id=V3, **extra)


def test_v2_golden_projection_descriptor_wire_and_origin_replay_exactly():
    request = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=synthesis.ATTRIBUTION_PROFILE_ID)
    wire, reserve = profile.provider_wire(request, profile.ATTRIBUTION_PROFILE_ID)
    assert profile.sha(request.projection_json) == '8b3b3f4dfab13f519d59a2bbcef81eed9a7dd393d871b19447b9ecf707760d4f'
    assert profile.sha(request.wire_json) == '0fde23afa8c8e3a7f9b00d36947bfbdda60ab9737c7d2763f8553a13a6c9f34f'
    assert request.origin_sha256 == 'fefd53f017dcb7a39bf31c7bda756cf9b44a623a9e10f52a382ed8467a6a063a'
    assert profile.sha(profile.canonical(profile.resolve_profile(profile.ATTRIBUTION_PROFILE_ID))) == '910d8f085d0c6122b34640536288dc6fdeb5105786f77e67312ca1770cd3f67c'
    assert profile.sha(wire) == 'a0bd331d05fc8f8bc8d68e86ab77d4f39800659e1f3537d5ba0831b845a9138a'
    assert reserve == 583710
    descriptor = profile.resolve_profile(V3)
    assert descriptor == {**profile.resolve_profile(profile.PROFILE_ID), 'id': V3,
        'policy_id': POLICY, 'policy_sha256': profile.sha(profile.canonical(synthesis.profile_projection(POLICY)))}
    assert len(synthesis._SOURCE_LEVEL_POLICY.encode()) == 649


def test_v3_schema_preserves_entities_and_raw_text_but_does_not_claim_semantic_enforcement():
    request = synthesis.build_system_synthesis_request(**pure.inputs(), profile_id=POLICY)
    candidate = pure.positive()
    candidate['important_new_information'] = ['The excerpt discusses Curie and Acme as research subjects.']
    raw = pure.canonical(candidate)
    decoded = synthesis.decode_system_synthesis(raw, request, request_origin_sha256=request.origin_sha256)
    assert decoded.raw_text == raw and decoded.raw_sha256 == profile.sha(raw)
    assert decoded.candidate_projection()['important_new_information'] == candidate['important_new_information']
    # Free strings also structurally decode a speaker claim. No sealed quality
    # or semantic PASS is inferred from JSON validity, and no output is repaired.
    candidate['important_new_information'] = ['The presenter asserts a definite view.']
    raw = pure.canonical(candidate)
    assert synthesis.decode_system_synthesis(raw, request, request_origin_sha256=request.origin_sha256).raw_text == raw
    assert not qualification.read_reviewed_qualifications(profile_id=V3).permits(V3, 'en')


def test_v3_full_evidence_summary_and_proofs_remain_exact_and_versions_do_not_mix(tmp_path):
    support = _load_module('test_synthesis_attribution_v2').runtime.support
    source = '[Ada] uncertain view. Unmarked different view. Curie is the discussion topic.'
    repo, root, subscription, video, *_ = support.workspace(tmp_path, 2, texts=[source, 'A distinct supported conditional observation.'])
    old = persistence.prepare(repo, source_id=subscription, video_id=video, command_id='same-command',
        output_language='en', now=support.NOW, profile_id=profile.ATTRIBUTION_PROFILE_ID)
    new = persistence.prepare(repo, source_id=subscription, video_id=video, command_id='same-command',
        output_language='en', now=support.NOW, profile_id=V3)
    a, b = json.loads(old.proof_json), json.loads(new.proof_json)
    assert a['capture'] == b['capture'] and a['command'] == b['command']
    assert old.proof_sha256 != new.proof_sha256
    previous, request = persistence.request_from_proof(old), persistence.request_from_proof(new)
    assert json.loads(previous.wire_json)['messages'][1:] == json.loads(request.wire_json)['messages'][1:]
    assert source in json.loads(request.wire_json)['messages'][2]['content']
    with pytest.raises(ValueError):
        profile.provider_wire(request, profile.ATTRIBUTION_PROFILE_ID)
    with pytest.raises(ValueError):
        synthesis.decode_system_synthesis(pure.canonical(pure.positive()), request, request_origin_sha256=previous.origin_sha256)


def test_trusted_resources_raw_bytes_and_constructor_flags_cannot_cross_qualify(tmp_path, monkeypatch):
    raw = package_fixture(tmp_path, monkeypatch, v3_record())
    loaded = qualification.read_reviewed_qualifications(profile_id=V3)
    assert loaded.permits(V3, 'en') and loaded.permits(V3, 'zh-CN')
    assert not loaded.permits(profile.ATTRIBUTION_PROFILE_ID, 'en')
    assert not qualification.read_reviewed_qualifications().permits(V3, 'en')
    assert not qualification.read_reviewed_qualifications(raw, profile_id=V3).permits(V3, 'en')
    with pytest.raises(TypeError):
        qualification.SynthesisQualificationAuthority(qualified=True)
    old = authority_tests.record_fixture()
    package_fixture(tmp_path, monkeypatch, old)
    assert not qualification.read_reviewed_qualifications(profile_id=V3).permits(V3, 'en')


@pytest.mark.parametrize('damage', ['missing', 'language', 'version', 'profile', 'fixture', 'failed', 'positive-en', 'positive-zh-CN', 'control'])
def test_v3_rehashed_incomplete_or_false_evidence_cannot_qualify(tmp_path, monkeypatch, damage):
    record = v3_record()
    if damage == 'missing':
        record['cases'].pop()
    elif damage == 'language':
        record['cases'][0]['output_language'] = 'zh-CN'
    elif damage == 'version':
        record['version'] = qualification.VERSION
    elif damage == 'profile':
        record['binding'] = qualification.qualification_binding()
    elif damage == 'fixture':
        record['cases'][0]['mode'] = 'FIXTURE_CONTRACT'
    elif damage == 'failed':
        record['cases'][0]['review']['verdict'] = 'FAIL'
    elif damage.startswith('positive-'):
        for case in record['cases'][:4]:
            if case['output_language'] == damage.removeprefix('positive-'):
                case['outcome'] = case['review']['outcome'] = 'NO_NEW_INTELLIGENCE'
    else:
        record['cases'][4]['outcome'] = record['cases'][4]['review']['outcome'] = 'INTELLIGENCE'
    package_fixture(tmp_path, monkeypatch, authority_tests.seal_record(record))
    assert not qualification.read_reviewed_qualifications(profile_id=V3).permits(V3, 'en')


@pytest.mark.parametrize('gate', ['qualification', 'credential', 'execution', 'budget', 'insufficient', 'price', 'consent'])
def test_v3_normal_factory_independent_gates_remain_zero_claim_zero_send(tmp_path, monkeypatch, gate):
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch,
        qualified=gate != 'qualification', credential=gate != 'credential', enabled=gate != 'execution')
    app = runtime.application
    if gate != 'budget':
        configure(app, profile_id=profile.ATTRIBUTION_PROFILE_ID if gate == 'price' else V3,
            amount='0.000001' if gate == 'insufficient' else '1')
    before = module.inventory(root)
    with module.offline():
        value = review(app, video)
        assert value['readiness']['can_confirm'] is (gate == 'consent')
        with pytest.raises(ApiError):
            confirm(app, video, value, **({'authorize': False} if gate == 'consent' else {}))
    assert calls == [] and runtime.repository.get_distillation_execution(value['execution_id']) is None
    assert module.inventory(root) == before


def test_v3_normal_confirm_receipt_save_topic_restore_and_held_cost(tmp_path, monkeypatch):
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch)
    app = runtime.application
    configure(app)
    with module.offline():
        rows = {r['profile_id']: r for r in app.handle('GET', '/api/v1/cloud-intelligence/profiles')[1]['profiles']}
        assert rows[V3]['qualified'] and not rows[profile.ATTRIBUTION_PROFILE_ID]['qualified']
        value = review(app, video)
        assert value['readiness']['can_confirm']
        assert value['spending']['price']['profile_id'] == V3
        before = module.inventory(root)
        assert review(app, video)['verified_input_hash'] == value['verified_input_hash']
        assert module.inventory(root) == before and calls == []
        status, result = confirm(app, video, value)
        assert status == 202 and result['execution']['status'] == 'SUCCEEDED' and len(calls) == 1
        identity = result['execution']['intelligence_id']
        assert app.handle('GET', f'/api/v1/intelligence/{identity}')[1]['intelligence']['trusted']
        app.handle('POST', '/api/v1/saved-intelligence/save', json.dumps({'intelligence_id': identity}).encode())
        topic = app.handle('POST', '/api/v1/topics', b'{"command_id":"fake-v3","name":"Fake v3 topic"}')[1]['topic']['topic_id']
        app.handle('POST', f'/api/v1/topics/{topic}/associations', json.dumps({'intelligence_id': identity, 'association_kind': 'NEW_INFORMATION'}).encode())
        with pytest.raises(ApiError):
            confirm(app, video, value)
    original = module.inventory(root)
    journal = service._spending_policy.path.read_bytes()
    assert service._spending_policy.status()['held_requests'] == 1
    archive = runtime.backup_restore.backup_download(runtime.backup_restore.create_backup().backup_id)[0]
    staged = runtime.backup_restore.stage_restore(archive.read_bytes())
    runtime.backup_restore.confirm_restore(staged.restore_id)
    runtime.backup_restore.recover_and_apply_pending_restore()
    assert module.inventory(root) == original and service._spending_policy.path.read_bytes() == journal
    assert runtime.repository.get_distillation_execution(value['execution_id']).invocation_count == 1 and len(calls) == 1
    with module.offline():
        assert app.handle('GET', f'/api/v1/topics/{topic}')[0] == 200


def test_v3_exact_scope_pair_permits_and_after_credential_binding_recheck(tmp_path, monkeypatch):
    from youtube_intel.distillation import CloudDistillationAuthorization
    from youtube_intel.synthesis_runtime import MoonshotSourceLevelSynthesisTransport
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch)
    value = review(runtime.application, video)
    verified = service._cloud_previews[value['review_hash']][1]
    assert service._transport.is_authorized_for_normal_production(verified)
    pair = runtime_tests.SimulatedFutureQualification.resolve(provider=profile.PAIR[0], model=profile.PAIR[1],
        capability_scope=runtime_tests.DistillationCapabilityScope.V1_VIDEO_DISTILLATION, available=True)
    adapter = MoonshotSourceLevelSynthesisTransport(authorization=CloudDistillationAuthorization.for_normal_production(
        eligibility=pair, cloud_enabled=True, credential_available=True), credential_resolver=lambda: pytest.fail('pair permit read credentials'))
    assert not adapter.is_authorized_for_normal_production(verified)
    before = module.inventory(root)
    with pytest.raises(ValueError):
        replace(verified, output_language='fr')
    for altered in (replace(verified, wire_version=profile.PROFILE_ID),
        replace(verified, wire_version=profile.ATTRIBUTION_PROFILE_ID), replace(verified, content_provider='LOCAL'),
        replace(verified, output_language='zh-CN')):
        with pytest.raises(CloudDistillationPreDispatchError):
            service._transport.generate(altered)
    for field in ('scope', 'source-provider', 'private', 'capture'):
        proof = copy.deepcopy(json.loads(verified.input_json))
        if field == 'scope':
            proof['source_scope'] = 'LOCAL_TIMED'
        elif field == 'source-provider':
            proof['capture']['source']['provider'] = 'BILIBILI'
        elif field == 'private':
            proof['capture']['video']['availability'] = 'private'
        else:
            proof['capture']['video']['title'] = 'Unbound owned capture'
        wire = profile.canonical(proof)
        with pytest.raises(CloudDistillationPreDispatchError):
            service._transport.generate(replace(verified, input_json=wire, semantic_hash=profile.sha(wire)))
    binding = qualification.qualification_binding(V3)
    def invalidate():
        monkeypatch.setattr(qualification, 'qualification_binding', lambda *args, **kwargs: {**binding, 'code_sha256': '0' * 64})
        return 'STRUCTURAL_FAKE_KEY'
    monkeypatch.setattr(service._transport, '_credential_resolver', invalidate)
    with pytest.raises(CloudDistillationPreDispatchError, match='changed before dispatch'):
        service._transport.generate(verified)
    assert calls == [] and module.inventory(root) == before


def test_v3_caller_flags_mixed_tickets_and_changed_current_input_do_not_claim(tmp_path, monkeypatch):
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch)
    app = runtime.application
    configure(app)
    value = review(app, video)
    for extra in ({'qualified': True}, {'authority': v3_record()}, {'qualification_path': '/tmp/foreign'}):
        with pytest.raises(ApiError):
            review(app, video, **extra)
    with pytest.raises(ApiError):
        authority_tests.confirm(app, video, value)
    app.handle('PUT', '/api/v1/settings/output-language', b'{"output_language":"zh-CN"}')
    before = module.inventory(root)
    with pytest.raises(ApiError):
        confirm(app, video, value)
    assert calls == [] and runtime.repository.get_distillation_execution(value['execution_id']) is None
    assert module.inventory(root) == before


@pytest.mark.parametrize('branch', ['no-new', 'unknown'])
def test_v3_no_new_and_ambiguous_lifecycle_keep_once_only_execution_and_hold(tmp_path, monkeypatch, branch):
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch)
    app = runtime.application
    configure(app)
    value = review(app, video)
    proof = json.loads(service._cloud_previews[value['review_hash']][1].input_json)
    raw = profile.canonical({'result': 'NO_NEW_INTELLIGENCE', 'reference_protocol': 'bound-evidence-reference-v1',
        'evidence': [{'ref': r['ref']} for r in proof['capture']['source_refs']]})
    def wire(request, *args):
        calls.append(request)
        if branch == 'unknown':
            raise RuntimeError('STRUCTURAL_FAKE possibly sent request')
        return runtime_tests.moonshot._response(content=raw, model=profile.PAIR[1])
    monkeypatch.setattr(service._transport, '_wire_transport', wire)
    with module.offline():
        result = confirm(app, video, value)[1]['execution']
    assert result['status'] == ('SUCCEEDED_NO_NEW_INTELLIGENCE' if branch == 'no-new' else 'AMBIGUOUS')
    assert runtime.repository.get_distillation_execution(value['execution_id']).invocation_count == 1
    assert service._spending_policy.status()['held_requests'] == 1 and len(calls) == 1
    with pytest.raises(ApiError):
        confirm(app, video, value)
    assert len(calls) == 1


@pytest.mark.parametrize('terminal', ['CANCELLED', 'REJECTED_OUTPUT'])
def test_v3_terminal_history_prepares_a_distinct_manual_review_without_reexecuting(tmp_path, monkeypatch, terminal):
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch)
    app = runtime.application
    configure(app)
    previous = review(app, video)
    if terminal == 'CANCELLED':
        from youtube_intel.synthesis_runtime import prepared_input
        prepared = prepared_input(service._cloud_previews[previous['review_hash']][1])
        persistence.reserve(runtime.repository, prepared, now=authority_tests.NOW)
        persistence.abandon_unclaimed(runtime.repository, prepared.execution_id, now=authority_tests.NOW)
    else:
        def wire(request, *args):
            calls.append(request)
            return runtime_tests.moonshot._response(content='{}', model=profile.PAIR[1])
        monkeypatch.setattr(service._transport, '_wire_transport', wire)
        assert confirm(app, video, previous)[1]['execution']['status'] == terminal
    retained = runtime.repository.get_distillation_execution(previous['execution_id'])
    count = len(calls)
    before = module.inventory(root)
    with module.offline():
        detail = app.handle('GET', f'/api/v1/videos/{video}')[1]
        assert detail['intelligence_result']['status'] == terminal and detail['manual_intelligence_eligible']
        fresh = review(app, video, command_id='fresh-v3-' + terminal)
    assert fresh['readiness']['can_confirm'] and fresh['execution_id'] != previous['execution_id']
    assert runtime.repository.get_distillation_execution(fresh['execution_id']) is None
    assert runtime.repository.get_distillation_execution(previous['execution_id']) == retained
    assert module.inventory(root) == before and len(calls) == count


def test_v3_price_reacknowledgement_preserves_all_old_unknown_holds(tmp_path):
    from youtube_intel.cloud_spending_policy import SpendingPolicyRejected
    spending = _load_module('test_cloud_spending_policy')
    repo, root, source, video, service, app, policy, backup, calls, clock = spending.setup(tmp_path)
    spending.configure(app)
    runtime_tests.confirm(app, video, runtime_tests.review(app, video))
    original = policy.status()
    old_events = copy.deepcopy(json.loads(policy.path.read_bytes())['events'])
    prepared = persistence.prepare(repo, source_id=source, video_id=video, command_id='v3-reack',
        output_language='en', now=clock[0], profile_id=V3)
    assert policy.preview(prepared)['blocker'] == 'CLOUD_PRICE_ACCEPTANCE_REQUIRED'
    with pytest.raises(SpendingPolicyRejected):
        policy.claim(prepared, validate_current=lambda: pytest.fail('old policy cannot claim v3'),
            now=clock[0], expected_policy_revision=original['policy_revision'])
    new = policy.update(expected_revision=original['revision'], enabled=True, total_cny='8', per_request_cny='1',
        max_calls=8, accept_price_hash=price_disclosure(V3)['price_hash'], acknowledge=True)
    assert new['price']['profile_id'] == V3 and policy.status()['price']['profile_id'] == V3
    assert new['held_requests'] == original['held_requests'] == 1
    assert new['held_microunits'] == original['held_microunits']
    assert json.loads(policy.path.read_bytes())['events'][:len(old_events)] == old_events
    assert policy.preview(prepared)['blocker'] is None and len(calls) == 1


def test_v3_actual_local_content_review_refuses_cloud_without_a_claim(tmp_path, monkeypatch):
    from youtube_intel.local_content import LocalContentProvider
    module, root, video, runtime, service, calls = factory(tmp_path, monkeypatch)
    configure(runtime.application)
    with module.offline():
        local = LocalContentProvider(runtime.repository, root / 'data').import_bytes(
            'STRUCTURAL_FAKE_LOCAL.txt', b'Owned local source. No cloud upload is authorized.')
        before = module.inventory(root)
        with pytest.raises(ApiError):
            review(runtime.application, local.content_id)
    assert module.inventory(root) == before and calls == []
    assert service._spending_policy.status()['held_requests'] == 0
