"""Only synthetic external credential/wire boundaries; no real qualification."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

_bundle: dict[str, Any] | None = None


def load_runner() -> Any:
    path = Path(__file__).resolve().parents[2] / 'scripts/validation/bounded_synthesis_trial.py'
    spec = importlib.util.spec_from_file_location('bounded_synthesis_trial', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runner() -> Any:
    module = load_runner()
    assert _bundle is not None
    module.production_limits = dict(module.LIMITS)
    module.PACKAGE = _bundle['package']
    module.MANIFEST_SHA = _bundle['manifest_sha256']
    module.ORDER = _bundle['order']
    module.LIMITS = {**module.LIMITS, **_bundle['reserve_totals']}
    module.inputs.SEED = _bundle['seed']
    # Any accidental dependency on the original owner's untracked package/seed
    # is a failure, even on this machine where those paths happen to exist.
    real_read, real_inventory = module.read, module.inputs.inventory
    def read(path: Path, *, private: bool = False) -> bytes:
        assert '/.var/' not in str(path), 'UNIT_MUST_NOT_READ_OWNER_VAR'
        raw: bytes = real_read(path, private=private)
        return raw
    def inventory(path: Path) -> Any:
        assert '/.var/' not in str(path), 'UNIT_MUST_NOT_READ_OWNER_VAR'
        return real_inventory(path)
    module.read, module.inputs.inventory = read, inventory
    return module


def seed_synthetic_history(module: Any, root: Path, video: str, language: str) -> None:
    """Real state APIs, three cancelled WAIT0 and two explicitly fake-wire NO_NEW."""
    active = module.inputs.runtime(root, [module.inputs.FIXTURE_TIME])
    assert active.application.handle('PUT', '/api/v1/settings/output-language',
        module.encoded({'output_language': language}))[0] == 200
    original = active.application._cloud_synthesis_service
    assert original is not None
    with active.repository._connect() as connection:
        source = connection.execute('SELECT source_id FROM source_video_links WHERE video_id=?', (video,)).fetchone()[0]
    for i in range(3):
        prepared = module.p.prepare(active.repository, source_id=source, video_id=video,
            command_id=f'owned-unit-history-wait-{i}', output_language=language, now=module.inputs.FIXTURE_TIME)
        module.p.reserve(active.repository, prepared, now=module.inputs.FIXTURE_TIME)
        module.p.abandon_unclaimed(active.repository, prepared.execution_id, now=module.inputs.FIXTURE_TIME)
    for i in range(2):
        command = f'owned-unit-history-fake-wire-{i}'
        prepared = module.p.prepare(active.repository, source_id=source, video_id=video,
            command_id=command, output_language=language, now=module.inputs.FIXTURE_TIME)
        transport = module.MoonshotSystemSynthesisTransport(authorization=module.CloudDistillationAuthorization(
            cloud_enabled=True, provider='moonshot', model='kimi-k3.1-pro', credential_available=True,
            provider_available=True, qualification_input_hash=prepared.proof_sha256),
            credential_resolver=lambda: 'synthetic-external-key', wire_transport=fake_wire(module, []))
        service = module.PersonalizedDistillationService(active.repository, original._source_policy, transport,
            original._budget, now=lambda: module.inputs.FIXTURE_TIME, output_language_for_video=lambda _: language)
        review = service.preview_cloud_execution(source_id=source, video_id=video,
            evidence_ids=tuple(r['evidence_id'] for r in module.p.loads(prepared.proof_json)['capture']['source_refs']),
            manual_command_id=command, qualified=False, credential_available=False)
        result = service.confirm_synthesis_qualification(video_id=video, execution_id=prepared.execution_id,
            review_hash=review['review_hash'], budget=module.p.SynthesisBudget('owned-unit-history:' + str(i), 1000000, 1))
        assert result.status.value == 'SUCCEEDED_NO_NEW_INTELLIGENCE'


@pytest.fixture(scope='module', autouse=True)
def owned_synthetic_package(tmp_path_factory: pytest.TempPathFactory) -> None:
    global _bundle
    module = load_runner()
    base = tmp_path_factory.mktemp('owned-bounded-trial-package')
    package, seed = base / 'prepared', base / 'seed'
    package.mkdir()
    order = tuple(f'owned-unit-{kind}-{language}' for kind in ('pair-a', 'pair-b', 'no-new', 'injection')
        for language in ('en', 'zh-CN'))
    rows = []
    with module.inputs.offline():
        module.inputs.seed_synthetic(seed, 'owned-unit-seed', 'en', False)
        for index, case in enumerate(order):
            language = 'en' if index % 2 == 0 else 'zh-CN'
            root = package / 'cases' / case / 'project'
            video = module.inputs.seed_synthetic(root, case, language, index >= 6)
            if index == 0:
                seed_synthetic_history(module, root, video, language)
            rows.append(module.inputs.materialize_case(root, root.parent / 'artifacts', case, video, language,
                synthetic=True, injection=index >= 6, clock=[module.inputs.FIXTURE_TIME]))
    inventory = module.inputs.inventory(seed)
    for name, value in {'source-before.json': inventory, 'source-after.json': inventory,
        'immutable-profile.json': module.profile.resolve_profile(module.profile.PROFILE_ID),
        'source-code-inventory.json': {'identity': 'OWNED_SYNTHETIC_UNIT_ONLY_NOT_REAL_SOURCE_REPLAY'}}.items():
        (package / name).write_bytes(module.encoded(value))
    oracle = b'OWNED SYNTHETIC UNIT ORACLE ONLY; no model quality or real acquisition claim.'
    (package / 'input-only-oracle.md').write_bytes(oracle)
    documents = package / 'official-supplement'
    documents.mkdir()
    fake_price = b'SYNTHETIC TEST PRICE DOCUMENT; NOT OFFICIAL PRICING EVIDENCE.'
    (documents / 'intelligence-kimi-pricing-20261104.txt').write_bytes(fake_price)
    manifest = {'status': 'PREPARED_NOT_AUTHORIZED', 'qualification': 'CLOSED', 'case_count': 8, 'cases': rows,
        'oracle_sha256': module.sha(oracle), 'source_code_inventory_sha256': module.sha((package / 'source-code-inventory.json').read_bytes()),
        'official_supplement': {'document_hashes': {'/owned-synthetic/intelligence-kimi-pricing-20261104.txt': module.sha(fake_price)},
            'identity': 'SYNTHETIC_UNIT_NOT_OFFICIAL_PRICE_CHECK'}}
    raw = module.encoded(manifest)
    (package / 'manifest.json').write_bytes(raw)
    reserves, gui = sum(row['reserve_microcny'] for row in rows), rows[1]['reserve_microcny']
    _bundle = {'package': package, 'seed': seed, 'manifest_sha256': module.sha(raw), 'order': order,
        'reserve_totals': {'runner_held_microcny': reserves, 'gui_held_microcny': gui,
            'prospective_total_microcny': 1943326 + reserves + gui}}


def test_frozen_package_prepare_never_authorizes_or_reads_credentials(tmp_path: Path) -> None:
    m = runner()
    trial = m.Trial(control=tmp_path / 'control', runs=tmp_path / 'runs')
    report = trial.prepare()
    assert report['status'] == 'NOT_AUTHORIZED'
    assert report['approval']['approved'] is False
    assert len(report['binding']['cases']) == 8
    assert report['limits']['prospective_total_microcny'] == m.LIMITS['prospective_total_microcny']
    assert {key: m.production_limits[key] for key in ('max_new_calls', 'max_total_calls', 'total_microcny',
        'runner_held_microcny', 'gui_held_microcny', 'prospective_total_microcny')} == {
        'max_new_calls': 9, 'max_total_calls': 11, 'total_microcny': 9000000,
        'runner_held_microcny': 5599830, 'gui_held_microcny': 969966, 'prospective_total_microcny': 8513122}
    assert report['limits']['runner_new_calls'] == 8
    assert report['limits']['optional_gui_calls'] == 1
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('credential must not be read'))


def authorized_trial(tmp_path: Path) -> tuple[Any, Any]:
    from datetime import UTC, datetime, timedelta
    m = runner()
    trial = m.Trial(control=tmp_path / 'control', runs=tmp_path / 'runs')
    report = trial.prepare()
    approval = {**report['approval'], 'approved': True, 'decision_id': 'SYNTHETIC_OFFLINE_TEST_ONLY',
        'expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat()}
    m.once(trial.control / 'grant.json', approval)
    return m, trial


def fake_wire(m: Any, calls: list[object], branch: str = 'zero') -> Any:
    from conftest import _load_module
    moonshot = _load_module('test_moonshot_distillation_adapter')
    def wire(request: Any, credential: str, timeout_seconds: float, max_retries: int) -> Any:
        from dataclasses import replace
        calls.append(request)
        assert credential == 'synthetic-external-key' and max_retries == 0 and timeout_seconds == 300
        if branch == 'timeout':
            raise TimeoutError('NEVER_SERIALIZE_PRIVATE_REMOTE_ERROR')
        if branch == '429':
            return moonshot._response(http_status=429, model=m.profile.PAIR[1])
        task = json.loads(request['messages'][2]['content'].removeprefix('UNTRUSTED_SOURCE_EVIDENCE='))
        # Actual refs are supplied by the frozen proof. Do not fabricate a result receipt.
        refs = task['evidence'] if isinstance(task, dict) and 'evidence' in task else task
        raw = json.dumps({'result': 'NO_NEW_INTELLIGENCE', 'reference_protocol': 'bound-evidence-reference-v1',
            'evidence': [{'ref': r['ref']} for r in refs]})
        if branch == 'old-fields':
            raw = json.dumps({'claim_kind': 'SYSTEM_INFERENCE', 'core_conclusion': 'old output'})
        response = moonshot._response(content=raw, model=m.profile.PAIR[1])
        return replace(response, finish_reason='length') if branch == 'truncated' else response
    return wire


def test_actual_qualification_claim_dispatch_receipt_and_restart_no_replay(tmp_path: Path) -> None:
    m, trial = authorized_trial(tmp_path)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls))
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT', result
    assert result['execution_status'] == 'SUCCEEDED_NO_NEW_INTELLIGENCE'
    assert result['invocation_count'] == 1 and len(calls) == 1
    assert result['qualification'] == 'CLOSED' and result['normal_execution_enabled'] is False
    assert result['source_parents_unchanged'] and result['backup_readiness']['ready']
    assert result['actual_bill'] == 'UNKNOWN'
    final = m.parsed(trial.control / (m.ORDER[0] + '.final.json'), private=True)
    assert result['receipt']['raw_text'] == final['raw_text']
    assert 'private reasoning' not in m.encoded(result).decode()
    restarted = m.Trial(control=trial.control, runs=tmp_path / 'restored-runs')
    with pytest.raises(ValueError, match='PREVIOUS'):
        restarted.execute(credential=lambda: pytest.fail('no repeat credential'))
    assert len(calls) == 1


@pytest.mark.parametrize('branch', ['429', 'timeout', 'truncated', 'old-fields'])
def test_failure_stops_remaining_without_freeing_attempt(tmp_path: Path, branch: str) -> None:
    m, trial = authorized_trial(tmp_path)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls, branch))
    assert result['status'] in {'TECHNICAL_FAILURE_STOP', 'UNKNOWN_STOP'}
    assert result['actual_bill'] == 'UNKNOWN' and len(calls) == 1
    ledger = trial.ledger(m.package_binding())
    assert len(ledger['attempts']) == 1 and ledger['attempts'][0]['reserve_microcny'] == m.package_binding()['cases'][0]['reserve_microcny']
    assert 'NEVER_SERIALIZE' not in m.encoded(result).decode()
    with pytest.raises(ValueError, match='PREVIOUS'):
        trial.execute(credential=lambda: pytest.fail('failure cannot advance'))


@pytest.mark.parametrize('kind', ['missing', 'corrupt', 'rollback', 'orphan'])
def test_external_ledger_fail_closed(tmp_path: Path, kind: str) -> None:
    m, trial = authorized_trial(tmp_path)
    path = trial.control / 'ledger.json'
    if kind == 'missing':
        path.rename(path.with_name('preserved-ledger.json'))
    elif kind == 'corrupt':
        path.write_text('INVALID')
    elif kind == 'rollback':
        attempt = {k: m.package_binding()['cases'][0][k] for k in
            ('case', 'execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny')}
        attempt['grant_sha256'] = 'a' * 64
        m.once(trial.control / 'attempt-1.json', attempt)
    else:
        m.once(trial.control / 'attempt-9.json', {'unknown': True})
    with pytest.raises(ValueError, match='LEDGER'):
        trial.execute(credential=lambda: pytest.fail('ledger before key'))
    with pytest.raises(ValueError, match='LEDGER'):
        trial.prepare()  # existing initialization can NEVER recreate a missing empty journal


@pytest.mark.parametrize('kind', ['not-approved', 'binding', 'price', 'expires', 'max-calls'])
def test_changed_or_missing_authority_precedes_claim_and_credential(tmp_path: Path, kind: str) -> None:
    m, trial = authorized_trial(tmp_path)
    grant = m.parsed(trial.control / 'grant.json', private=True)
    if kind == 'not-approved':
        grant['approved'] = False
    elif kind == 'binding':
        grant['binding_sha256'] = 'a' * 64
    elif kind == 'expires':
        grant['expires_at'] = '2020-01-01T00:00:00+00:00'
    else:
        grant['limits']['total_microcny' if kind == 'price' else 'max_new_calls'] += 1
    (trial.control / 'grant.json').write_bytes(m.encoded(grant))
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('grant before key'))
    assert trial.ledger(m.package_binding())['attempts'] == []
    assert not trial.runs.exists()


def root_pass(m: Any, trial: Any, result: Any, **changes: Any) -> None:
    m.once(trial.control / (result['case'] + '.semantic.json'), {
        'case': result['case'], 'decision': 'PASS', 'reviewer': 'ROOT',
        'decision_id': 'SYNTHETIC_SEMANTIC_DECISION_NOT_REAL_QUALITY',
        'result_sha256': m.sha(m.encoded(result)), 'receipt_sha256': result['receipt_sha256'],
        'oracle_sha256': m.package_binding()['oracle_sha256'], **changes})


def test_second_case_only_after_hash_bound_root_decision(tmp_path: Path) -> None:
    m, trial = authorized_trial(tmp_path)
    calls: list[object] = []
    first = trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls))
    root_pass(m, trial, first)
    second = trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls))
    assert second['case'] == m.ORDER[1] and second['status'] == 'TECHNICAL_PASS_AWAITING_ROOT'
    assert len(calls) == 2
    assert len(trial.ledger(m.package_binding())['attempts']) == 2
    assert second['actual_bill'] == first['actual_bill'] == 'UNKNOWN'


@pytest.mark.parametrize('kind', ['reject', 'wrong-receipt', 'wrong-oracle', 'restored-old-db', 'changed-final'])
def test_semantic_or_storage_drift_stops_before_next_key(tmp_path: Path, kind: str) -> None:
    m, trial = authorized_trial(tmp_path)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls))
    changes = {'decision': 'REJECT'} if kind == 'reject' else {'receipt_sha256': 'b' * 64} if kind == 'wrong-receipt' else {'oracle_sha256': 'c' * 64} if kind == 'wrong-oracle' else {}
    root_pass(m, trial, result, **changes)
    if kind == 'restored-old-db':
        import sqlite3
        target = trial.runs / m.ORDER[0] / 'state.sqlite3'
        with sqlite3.connect(str(m.PACKAGE / 'cases' / m.ORDER[0] / 'project/state.sqlite3')) as src:
            with sqlite3.connect(target) as dst:
                src.backup(dst)
    if kind == 'changed-final':
        path = trial.control / (m.ORDER[0] + '.final.json')
        path.write_bytes(m.encoded({'raw_text': 'changed', 'sha256': m.sha(b'changed')}))
    with pytest.raises(ValueError, match='PREVIOUS'):
        trial.execute(credential=lambda: pytest.fail('semantic/restore check before next key'))
    assert len(calls) == 1
    assert len(trial.ledger(m.package_binding())['attempts']) == 1


def test_concurrent_controllers_dispatch_once(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    m, trial = authorized_trial(tmp_path)
    calls: list[object] = []
    def invoke() -> Any:
        try:
            return trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls))
        except ValueError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invoke(), range(2)))
    assert sum(isinstance(r, dict) and r['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' for r in results) == 1
    assert any(isinstance(r, str) and 'PREVIOUS' in r for r in results)
    assert len(calls) == 1


@pytest.mark.parametrize('kind', ['manifest', 'body', 'proof', 'profile', 'official-price', 'code'])
def test_mutated_frozen_inputs_or_code_fail_before_credential(tmp_path: Path, monkeypatch: Any, kind: str) -> None:
    m, trial = authorized_trial(tmp_path)
    read = m.read
    def changed(path: Path, **kwargs: Any) -> bytes:
        raw: bytes = read(path, **kwargs)
        match = {'manifest': 'manifest.json', 'body': 'provider-body.json', 'proof': 'prepared-proof.json',
            'profile': 'immutable-profile.json', 'official-price': 'intelligence-kimi-pricing-20261104.txt',
            'code': 'system_synthesis_profile.py'}[kind]
        return raw + b'\nCHANGED' if path.name == match else raw
    monkeypatch.setattr(m, 'read', changed)
    with pytest.raises((ValueError, KeyError), match='CHANGED|JSON|GRANT'):
        trial.execute(credential=lambda: pytest.fail('changed source before key'))
    assert not trial.runs.exists()


def test_old_schema_clone_is_not_migrated_into_an_authorized_trial(tmp_path: Path, monkeypatch: Any) -> None:
    import sqlite3
    m, trial = authorized_trial(tmp_path)
    clone = m.inputs.clone
    def old(source: Path, target: Path) -> None:
        clone(source, target)
        with sqlite3.connect(target / 'state.sqlite3') as c:
            c.execute('PRAGMA user_version=43')
    monkeypatch.setattr(m.inputs, 'clone', old)
    with pytest.raises(ValueError, match='REQUIRES_SCHEMA44'):
        trial.execute(credential=lambda: pytest.fail('old schema before key'))
    assert trial.ledger(m.package_binding())['attempts'] == []


def test_eight_fake_cases_cannot_spend_gui_slot_or_qualify_model(tmp_path: Path) -> None:
    m, trial = authorized_trial(tmp_path)
    calls: list[object] = []
    for case in m.ORDER:
        result = trial.execute(credential=lambda: 'synthetic-external-key', wire=fake_wire(m, calls))
        assert result['case'] == case and result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT'
        assert result['qualification'] == 'CLOSED' and result['normal_execution_enabled'] is False
        root_pass(m, trial, result)  # explicitly synthetic; cannot assert semantic quality
    with pytest.raises(ValueError, match='GUI_SLOT_NOT_EXECUTABLE'):
        trial.execute(credential=lambda: pytest.fail('no ninth credential or GUI spend'))
    ledger = trial.ledger(m.package_binding())
    assert len(calls) == len(ledger['attempts']) == 8
    assert sum(a['reserve_microcny'] for a in ledger['attempts']) == m.LIMITS['runner_held_microcny']


@pytest.mark.parametrize('kind', ['permissions', 'symlink', 'hardlink'])
def test_redirected_or_public_ledger_is_not_trusted(tmp_path: Path, kind: str) -> None:
    import os
    m, trial = authorized_trial(tmp_path)
    path = trial.control / 'ledger.json'
    if kind == 'permissions':
        path.chmod(0o644)
    else:
        preserved = path.with_name('preserved-ledger.json')
        path.rename(preserved)
        if kind == 'symlink':
            path.symlink_to(preserved)
        else:
            os.link(preserved, path)
    with pytest.raises(ValueError, match='LEDGER'):
        trial.execute(credential=lambda: pytest.fail('unsafe ledger before key'))


def test_reservation_precedes_key_and_claim_precedes_wire(tmp_path: Path) -> None:
    import sqlite3
    m, trial = authorized_trial(tmp_path)
    row = m.package_binding()['cases'][0]
    source = m.PACKAGE / 'cases' / row['case'] / 'project/state.sqlite3'
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as connection:
        prior_checkpoints = connection.execute('SELECT * FROM distillation_execution_checkpoints ORDER BY execution_id').fetchall()
        prior_authorizations = connection.execute('SELECT * FROM system_synthesis_cloud_authorizations ORDER BY execution_id').fetchall()
        assert len(prior_checkpoints) == 5 and len(prior_authorizations) == 2
        assert connection.execute('SELECT count(*) FROM distillation_execution_checkpoints WHERE execution_id=?',
            (row['execution_id'],)).fetchone() == (0,)
    calls: list[object] = []
    resolved = []
    def key() -> str:
        ledger = trial.ledger(m.package_binding())
        assert len(ledger['attempts']) == 1
        resolved.append(True)
        return 'synthetic-external-key'
    external = fake_wire(m, calls)
    def wire(request: Any, credential: str, timeout_seconds: float, max_retries: int) -> Any:
        with sqlite3.connect(trial.runs / m.ORDER[0] / 'state.sqlite3') as c:
            assert c.execute('SELECT invocation_count FROM distillation_execution_checkpoints WHERE execution_id=?',
                (row['execution_id'],)).fetchall() == [(1,)]
            assert c.execute('SELECT consent_kind,verified_input_hash FROM system_synthesis_cloud_authorizations WHERE execution_id=?',
                (row['execution_id'],)).fetchall() == [('OWNER_QUALIFICATION', row['proof_sha256'])]
            assert c.execute('SELECT * FROM distillation_execution_checkpoints WHERE execution_id<>? ORDER BY execution_id',
                (row['execution_id'],)).fetchall() == prior_checkpoints
            assert c.execute('SELECT * FROM system_synthesis_cloud_authorizations WHERE execution_id<>? ORDER BY execution_id',
                (row['execution_id'],)).fetchall() == prior_authorizations
        return external(request, credential, timeout_seconds, max_retries)
    result = trial.execute(credential=key, wire=wire)
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' and resolved and len(calls) == 1


def test_crash_after_external_hold_cannot_retry_even_without_db_claim(tmp_path: Path) -> None:
    m, trial = authorized_trial(tmp_path)
    def missing() -> str:
        raise RuntimeError('PRIVATE_CREDENTIAL_EXCEPTION_NEVER_STORE')
    result = trial.execute(credential=missing)
    assert result['status'] == 'UNKNOWN_STOP' and result['send_attempted'] is False
    assert len(trial.ledger(m.package_binding())['attempts']) == 1
    assert 'PRIVATE_CREDENTIAL' not in m.encoded(result).decode()
    restarted = m.Trial(control=trial.control, runs=trial.runs)
    with pytest.raises(ValueError, match='PREVIOUS'):
        restarted.execute(credential=lambda: pytest.fail('hold stays counted'))
