"""Purpose-bound owner entry uses existing dispatch; only external boundaries fake."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis_persistence as p
from youtube_intel.distillation import (
    CloudDistillationAuthorization,
    PersonalizedDistillationService,
)
from youtube_intel.synthesis_runtime import MoonshotSystemSynthesisTransport

runtime = _load_module('test_synthesis_runtime')


def setup(tmp_path: Path, kind: str = 'exact') -> Any:
    repo, root, source, video, original, app_for, calls, _, clock = runtime.setup(tmp_path, qualified=False)
    normal = runtime.review(app_for(), video)
    auth = CloudDistillationAuthorization(cloud_enabled=True, provider='moonshot', model='kimi-k3.1-pro',
        credential_available=True, provider_available=True,
        qualification_input_hash=normal['verified_input_hash'] if kind != 'wrong-hash' else 'a' * 64,
        qualification_max_calls=2 if kind == 'two-calls' else 1)
    if kind == 'normal-only':
        auth = original._transport._authorization
    transport = MoonshotSystemSynthesisTransport(authorization=auth, credential_resolver=lambda: 'synthetic-external-boundary-only',
        wire_transport=original._transport._wire_transport)
    service = PersonalizedDistillationService(repo, original._source_policy, transport, original._budget,
        now=lambda: clock[0], output_language_for_video=lambda _: 'en')
    value = service.preview_cloud_execution(source_id=source, video_id=video, evidence_ids=tuple(normal['evidence_ids']),
        manual_command_id='synthetic-one', qualified=False, credential_available=False)
    proof_hash = value['verified_input_hash']
    assert isinstance(proof_hash, str)
    budget = p.SynthesisBudget('owner-offline:' + proof_hash, 1000000, 1)
    return repo, root, video, original, service, value, budget, calls, clock


def confirm(service: Any, video: str, value: Any, budget: Any) -> Any:
    return service.confirm_synthesis_qualification(video_id=video, execution_id=value['execution_id'],
        review_hash=value['review_hash'], budget=budget)


def test_exact_owner_positive_receipt_retains_normal_closed_and_rejects_replay(tmp_path: Path) -> None:
    repo, root, video, normal, service, value, budget, calls, clock = setup(tmp_path)
    assert value['readiness']['can_confirm'] is False
    before = runtime.support._inventory(repo, root)
    clock[0] += timedelta(seconds=3)
    result = confirm(service, video, value, budget)
    assert result.status.value == 'SUCCEEDED' and result.invocation_count == 1 and len(calls) == 1
    with repo._connect() as c:
        p.verify_database(repo, c)
        auth = dict(c.execute('SELECT * FROM system_synthesis_cloud_authorizations').fetchone())
        receipt = dict(c.execute('SELECT * FROM system_synthesis_result_receipts').fetchone())
    assert auth['consent_kind'] == 'OWNER_QUALIFICATION'
    assert receipt['raw_text'] == runtime.storage.raw_positive()
    assert before[1] == runtime.support._inventory(repo, root)[1]
    assert service._transport._authorization.production_eligible is False
    with pytest.raises(Exception, match='already exists|conflicts'):
        confirm(service, video, value, budget)
    assert len(calls) == 1


@pytest.mark.parametrize('kind', ['normal-only', 'wrong-hash', 'two-calls', 'budget-two', 'over-budget', 'expired', 'wrong-video', 'source-drift'])
def test_unbound_stale_or_unbounded_owner_requests_do_not_claim(tmp_path: Path, kind: str) -> None:
    repo, root, video, normal, service, value, budget, calls, clock = setup(tmp_path, kind)
    if kind == 'budget-two':
        budget = p.SynthesisBudget('owner-test', 1000000, 2)
    if kind == 'over-budget':
        budget = p.SynthesisBudget('owner-test', 1000001, 1)
    if kind == 'expired':
        clock[0] += timedelta(minutes=6)
    if kind == 'wrong-video':
        video = 'other-video'
    if kind == 'source-drift':
        service._output_language_for_video = lambda _: 'zh-CN'
    with pytest.raises(ValueError):
        confirm(service, video, value, budget)
    assert calls == [] and repo.get_distillation_execution(value['execution_id']) is None
    with repo._connect() as c:
        assert c.execute('SELECT count(*) FROM system_synthesis_cloud_authorizations').fetchone()[0] == 0


def test_two_concurrent_exact_owner_confirmations_claim_once(tmp_path: Path) -> None:
    repo, root, video, normal, service, value, budget, calls, clock = setup(tmp_path)
    def invoke() -> Any:
        try:
            return confirm(service, video, value, budget)
        except Exception as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invoke(), range(2)))
    assert sum(not isinstance(r, str) and r.status.value == 'SUCCEEDED' for r in results) == 1
    assert len(calls) == 1 and repo.get_distillation_execution(value['execution_id']).invocation_count == 1


def public_setup(tmp_path: Path, profile_id: str | None = None, *, unknown: bool = False) -> Any:
    """Use the checked-in public AIRC archive through the normal factory and API."""
    import json

    from youtube_intel import system_synthesis_profile as profile
    from youtube_intel.synthesis_runtime import (
        MoonshotAttributionSynthesisTransport,
        MoonshotReadableSummarySynthesisTransport,
        MoonshotSourceLevelSynthesisTransport,
    )

    inputs = _load_module('test_synthesis_reviewed_authority').materializer()
    stock = _load_module('test_bigmodel_public_first_case')
    root = tmp_path / 'owned-public'
    root.mkdir()
    stock.unpack_public_stock(inputs, root)
    clock = [inputs.FIXTURE_TIME]
    selected = profile_id or profile.READABLE_SUMMARY_PROFILE_ID
    with inputs.offline():
        active = inputs.runtime(root, clock)
        active.application.handle('PUT', '/api/v1/settings/output-language', b'{"output_language":"en"}')
        normal, verified = inputs.ordinary_review(active, 'aircAruvnKk', 'qualification-budget', profile_id=selected)
    original = {profile.PROFILE_ID: active.application._cloud_synthesis_service,
        profile.ATTRIBUTION_PROFILE_ID: active.application._cloud_synthesis_v2_service,
        profile.SOURCE_LEVEL_PROFILE_ID: active.application._cloud_synthesis_v3_service,
        profile.READABLE_SUMMARY_PROFILE_ID: active.application._cloud_synthesis_v4_service}[selected]
    adapter = {profile.PROFILE_ID: MoonshotSystemSynthesisTransport,
        profile.ATTRIBUTION_PROFILE_ID: MoonshotAttributionSynthesisTransport,
        profile.SOURCE_LEVEL_PROFILE_ID: MoonshotSourceLevelSynthesisTransport,
        profile.READABLE_SUMMARY_PROFILE_ID: MoonshotReadableSummarySynthesisTransport}[selected]
    activity = {'credentials': 0, 'wire': 0}
    def credential() -> str:
        activity['credentials'] += 1
        return 'synthetic-public-budget-key'
    def wire(request: Any, key: str, timeout: float, retries: int) -> Any:
        activity['wire'] += 1
        assert key == 'synthetic-public-budget-key' and timeout == 300 and retries == 0
        if unknown:
            raise TimeoutError('synthetic possibly-sent request')
        refs = json.loads(request['messages'][2]['content'].split('=', 1)[1])['evidence']
        raw = profile.canonical({'result': 'NO_NEW_INTELLIGENCE', 'reference_protocol': 'bound-evidence-reference-v1',
            'evidence': [{'ref': row['ref']} for row in refs]})
        return runtime.moonshot._response(content=raw, model=profile.PAIR[1])
    transport = adapter(authorization=CloudDistillationAuthorization(cloud_enabled=True, provider=profile.PAIR[0],
        model=profile.PAIR[1], credential_available=True, provider_available=True,
        qualification_input_hash=normal['verified_input_hash'], qualification_max_calls=1),
        credential_resolver=credential, wire_transport=wire)
    service = PersonalizedDistillationService(active.repository, original._source_policy, transport, original._budget,
        now=lambda: clock[0], output_language_for_video=original._output_language_for_video)
    value = service.preview_cloud_execution(source_id=normal['source_id'], video_id='aircAruvnKk',
        evidence_ids=tuple(normal['evidence_ids']), manual_command_id='materialize-qualification-budget',
        qualified=False, credential_available=False)
    assert value['verified_input_hash'] == normal['verified_input_hash']
    prepared = inputs.prepared_input(verified)
    proof = p.loads(prepared.proof_json)
    assert inputs.sha(proof['capture']['summary_raw'].encode()) == inputs.PUBLIC_SUMMARY_SHA['aircAruvnKk']
    return inputs, root, active, service, value, proof['reserve_microunits'], activity, clock


def test_v4_public_request_over_one_cny_uses_explicit_one_and_half_budget(tmp_path: Path) -> None:
    inputs, root, active, service, value, reserve, activity, clock = public_setup(tmp_path)
    assert 1_000_000 < reserve <= 1_500_000
    assert not value['readiness']['can_confirm'] and not service.reviewed_synthesis_qualified()
    before = inputs.inventory(root)
    budget = p.SynthesisBudget('owned-public-v4-budget', 1_500_000, 1)
    with inputs.offline():
        result = confirm(service, 'aircAruvnKk', value, budget)
    assert result.status.value == 'SUCCEEDED_NO_NEW_INTELLIGENCE'
    assert result.invocation_count == 1 and activity['wire'] == 1
    after = inputs.inventory(root)
    assert after['data'] == before['data']
    changed = {name for name in before['tables'] if before['tables'][name] != after['tables'][name]}
    assert changed == {'distillation_execution_checkpoints', 'system_synthesis_input_proofs',
        'system_synthesis_cloud_authorizations', 'system_synthesis_result_receipts',
        'distillation_no_new_intelligence_results'}
    with active.repository._connect() as connection:
        p.verify_database(active.repository, connection)
        auth = dict(connection.execute('SELECT * FROM system_synthesis_cloud_authorizations WHERE execution_id=?',
            (value['execution_id'],)).fetchone())
        receipt = connection.execute('SELECT raw_text FROM system_synthesis_result_receipts WHERE execution_id=?',
            (value['execution_id'],)).fetchone()
    assert auth['consent_kind'] == 'OWNER_QUALIFICATION' and auth['reserve_microunits'] == reserve
    assert auth['budget_limit_microunits'] == 1_500_000 and receipt['raw_text']
    activity_before = dict(activity)
    with pytest.raises(Exception, match='already exists|conflicts'):
        confirm(service, 'aircAruvnKk', value, budget)
    assert activity['wire'] == activity_before['wire'] == 1
    assert not service._transport._authorization.production_eligible and not service.reviewed_synthesis_qualified()


@pytest.mark.parametrize('limit', [1_500_001, 1_000_000, 0, None])
def test_v4_public_budget_refusal_precedes_credentials_and_reservation(tmp_path: Path, limit: int | None) -> None:
    inputs, root, active, service, value, reserve, activity, clock = public_setup(tmp_path)
    assert reserve > 1_000_000
    before = inputs.inventory(root)
    budget = None if limit is None else p.SynthesisBudget('owned-invalid-v4-budget', limit, 1)
    with inputs.offline(), pytest.raises(ValueError, match='qualification authority'):
        confirm(service, 'aircAruvnKk', value, budget)
    assert activity == {'credentials': 0, 'wire': 0} and inputs.inventory(root) == before
    assert active.repository.get_distillation_execution(value['execution_id']) is None


@pytest.mark.parametrize('profile_id', [
    'moonshot-k31-system-synthesis-v1-20261029',
    'moonshot-k31-system-synthesis-v2-attribution-20261105',
    'moonshot-k31-system-synthesis-v3-source-level-20261106',
])
def test_old_public_profiles_retain_one_cny_maximum(tmp_path: Path, profile_id: str) -> None:
    inputs, root, active, service, value, reserve, activity, clock = public_setup(tmp_path, profile_id)
    assert reserve < 1_000_000
    before = inputs.inventory(root)
    with inputs.offline(), pytest.raises(ValueError, match='qualification authority or budget differs'):
        confirm(service, 'aircAruvnKk', value, p.SynthesisBudget('owned-old-budget', 1_000_001, 1))
    assert activity == {'credentials': 0, 'wire': 0} and inputs.inventory(root) == before


@pytest.mark.parametrize(('field', 'invalid'), [
    ('limit_microunits', True), ('limit_microunits', 1_000_000.0), ('max_calls', True),
    ('prior_calls', False), ('prior_calls', 0.0), ('prior_calls', 1),
    ('prior_reserved_microunits', False), ('prior_reserved_microunits', 0.0), ('prior_reserved_microunits', 1),
])
def test_malformed_budget_counters_refuse_before_key_or_reservation(tmp_path: Path, monkeypatch: Any, field: str, invalid: Any) -> None:
    from dataclasses import replace

    repo, root, video, normal, service, value, budget, calls, clock = setup(tmp_path)
    monkeypatch.setattr(service._transport, '_credential_resolver', lambda: pytest.fail('Malformed budget read credentials'))
    before = runtime.support._inventory(repo, root)
    with pytest.raises(ValueError, match='qualification authority or budget differs'):
        confirm(service, video, value, replace(budget, **{field: invalid}))
    assert calls == [] and runtime.support._inventory(repo, root) == before


@pytest.mark.parametrize('count', [True, 1.0])
def test_malformed_authority_call_limit_refuses_before_key(tmp_path: Path, monkeypatch: Any, count: Any) -> None:
    repo, root, video, normal, service, value, budget, calls, clock = setup(tmp_path)
    service._transport._authorization = CloudDistillationAuthorization(cloud_enabled=True, provider='moonshot',
        model='kimi-k3.1-pro', credential_available=True, provider_available=True,
        qualification_input_hash=value['verified_input_hash'], qualification_max_calls=count)
    monkeypatch.setattr(service._transport, '_credential_resolver', lambda: pytest.fail('Malformed authority read credentials'))
    before = runtime.support._inventory(repo, root)
    with pytest.raises(ValueError, match='qualification authority or budget differs'):
        confirm(service, video, value, budget)
    assert calls == [] and runtime.support._inventory(repo, root) == before


@pytest.mark.parametrize('damage', ['unknown-profile', 'source-change'])
def test_v4_current_public_proof_is_required_before_key(tmp_path: Path, damage: str) -> None:
    from dataclasses import replace

    inputs, root, active, service, value, reserve, activity, clock = public_setup(tmp_path)
    if damage == 'unknown-profile':
        command, verified, expires = service._cloud_previews[value['review_hash']]
        service._cloud_previews[value['review_hash']] = (command, replace(verified, wire_version='unknown-v4'), expires)
    else:
        with active.repository._connect() as connection:
            connection.execute('UPDATE videos SET title=? WHERE video_id=?', ('Changed owned public title', 'aircAruvnKk'))
    before = inputs.inventory(root)
    with inputs.offline(), pytest.raises(ValueError):
        confirm(service, 'aircAruvnKk', value, p.SynthesisBudget('owned-stale-v4', 1_500_000, 1))
    assert activity == {'credentials': 0, 'wire': 0} and inputs.inventory(root) == before


def test_v4_unknown_sent_result_keeps_claim_and_rejects_another_wire(tmp_path: Path) -> None:
    inputs, root, active, service, value, reserve, activity, clock = public_setup(tmp_path, unknown=True)
    budget = p.SynthesisBudget('owned-unknown-v4', 1_500_000, 1)
    with inputs.offline():
        result = confirm(service, 'aircAruvnKk', value, budget)
        assert result.status.value == 'AMBIGUOUS' and result.invocation_count == activity['wire'] == 1
        with pytest.raises(Exception, match='already exists|conflicts'):
            confirm(service, 'aircAruvnKk', value, budget)
    assert activity['wire'] == 1
    assert active.repository.get_distillation_execution(value['execution_id']).invocation_count == 1
