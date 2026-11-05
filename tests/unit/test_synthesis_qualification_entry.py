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
