"""Finite readable-Summary continuation using owned synthetic history only."""
from __future__ import annotations

import copy
import gc
import importlib.util
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest


def controller() -> Any:
    from conftest import _load_module
    return _load_module('test_bounded_synthesis_v2_trial').controller()


def test_v4_is_finite_new_consent_and_retains_six_historical_holds() -> None:
    m = controller()
    assert m.trial_spec()['variant'] == 'v1-r4'
    assert m.trial_spec('v2-r1')['limits'] == m.V2_LIMITS
    assert m.trial_spec('v3-r1')['limits'] == m.V3_LIMITS
    four = m.trial_spec('v4-r1')
    assert four['original']['variant'] == 'v3-r1'
    assert four['original']['original']['variant'] == 'v2-r1'
    assert four['profile_id'] == m.profile.READABLE_SUMMARY_PROFILE_ID
    assert four['purpose'] == 'ROOT_RECORDED_READABLE_SUMMARY_V4_CONTINUATION'
    assert four['limits']['historical_calls'] == 6
    assert four['limits']['historical_held_microcny'] == 5867962
    assert four['limits']['per_call_microcny'] == 1500000
    assert four['limits']['max_total_calls'] == 15
    assert four['limits']['total_microcny'] == 14000000
    assert four['limits']['prospective_total_microcny'] == 13931926


@pytest.fixture(scope='module')
def template(tmp_path_factory: pytest.TempPathFactory) -> Any:
    from conftest import _load_module

    old_v3 = _load_module('test_bounded_synthesis_v3_trial')
    previous_generator = old_v3.template.__wrapped__(tmp_path_factory)
    m, old, previous, three, two_parent = next(previous_generator)
    three = copy.deepcopy(three)
    root = tmp_path_factory.mktemp('owned-readable-continuation')
    three.update(control=root / 'stopped-v3-control', runs=root / 'stopped-v3-runs')
    parent = m.Trial(variant='v3-r1', _spec=three)
    report = previous.approve(m, parent)
    storage = _load_module('test_system_synthesis_persistence')

    def positive_wire(*args: Any) -> Any:
        return replace(old.fake_wire(m, [])(*args), final_content=storage.raw_positive())

    result = parent.execute(credential=lambda: 'synthetic-external-key', wire=positive_wire)
    assert result['execution_status'] == 'SUCCEEDED', result
    previous.semantic(m, parent, result, 'REJECT')
    gc.collect()
    with closing(sqlite3.connect(parent.runs / result['case'] / 'state.sqlite3')) as connection:
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    frozen = root / 'frozen-v3-source'
    for name in report['binding']['source_hashes']:
        path = frozen / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(m.read(m.REPO / name))
    independent = frozen / '.var/independent-v3-semantic-20261107' / (result['case'] + '.json')
    m.directory(independent.parent, create=True)
    m.once(independent, {'case': result['case'], 'verdict': 'REJECT', 'identity': 'SYNTHETIC_NOT_REAL_QUALITY'})
    restore = root / 'synthetic-v3-restore.json'
    m.once(restore, {'status': 'REAL_V3_PAID_REJECTED_RESULT_RESTORE_PASS_NO_REEXECUTION',
        'case': result['case'], 'semantic': 'REJECT', 'all_data_files_equal': True,
        'all_table_rows_equal': True, 'external_controls_hashes_equal': True,
        'backup_ready_after_restore': True, 'external_control_files': 9,
        'new_model_calls_during_backup_restore': 0, 'original_invocation_count': 1,
        'identity': 'SYNTHETIC_RESTORE_ONLY'})
    held = three['limits']['historical_held_microcny'] + result['reserve_microcny']
    summary = {'actual_bill': 'UNKNOWN', 'binding_sha256': m.sha(m.encoded(report['binding'])),
        'control': str(parent.control), 'historical_calls': 6, 'historical_held_microcny': held,
        'independent_report_sha256': m.sha(m.read(independent, private=True)),
        'manifest_sha256': report['binding']['manifest_sha256'], 'new_fee_authorized': False,
        'parent_source': str(frozen), 'pins': {p.name: m.sha(m.read(p, private=True)) for p in parent.control.iterdir()},
        'semantic': 'REJECT', 'source_revision': report['binding']['source_revision']}
    summary_path = root / 'synthetic-parent-summary.json'
    m.once(summary_path, summary)
    four = m.trial_spec('v4-r1')
    four.update(original=three, package=root / 'v4-package', order=three['order'], seed=three['seed'],
        frozen_parent_source=frozen, parent_runs=parent.runs, stopped_v3_summary=summary_path,
        stopped_v3_summary_sha256=m.sha(m.encoded(summary)), historical_revision=summary['source_revision'],
        historical_binding_sha256=summary['binding_sha256'], historical_manifest_sha256=summary['manifest_sha256'],
        restore_report=restore)
    manifest = m.parsed(three['package'] / 'manifest.json')
    estimates = [m.p.loads(m.p._assemble(m.parsed(Path(row['artifacts']) / 'prepared-proof.json')['command'],
        m.parsed(Path(row['artifacts']) / 'prepared-proof.json')['capture'],
        profile_id=m.profile.READABLE_SUMMARY_PROFILE_ID).proof_json)['reserve_microunits'] for row in manifest['cases']]
    four['limits'].update(historical_held_microcny=held, runner_held_microcny=sum(estimates),
        gui_held_microcny=estimates[1], prospective_total_microcny=held + sum(estimates) + estimates[1])
    patcher = pytest.MonkeyPatch()
    check_output = m.subprocess.check_output

    def revision(command: Any, **kwargs: Any) -> Any:
        if command == ['git', '-C', str(frozen), 'rev-parse', 'HEAD']:
            return summary['source_revision'] + '\n'
        return check_output(command, **kwargs)

    patcher.setattr(m.subprocess, 'check_output', revision)
    path = Path(m.__file__).with_name('materialize_synthesis_v2_inputs.py')
    module_spec = importlib.util.spec_from_file_location('owned_v4_preparation', path)
    assert module_spec and module_spec.loader
    helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    proposal = helper.materialize(four)
    assert proposal['approval']['approved'] is False
    yield m, old, previous, four, parent, two_parent
    patcher.undo()
    next(previous_generator, None)


@pytest.fixture
def owned(tmp_path: Path, template: Any) -> Any:
    m, old, previous, original, parent, two_parent = template
    spec = copy.deepcopy(original)
    trial = m.Trial(variant='v4-r1', control=tmp_path / 'child', runs=tmp_path / 'runs', _spec=spec)
    roots = [parent.control, two_parent.control, spec['frozen_parent_source'], spec['original']['frozen_parent_source']]
    files = {p: (p.read_bytes(), p.stat().st_mode & 0o777) for root in roots for p in root.rglob('*') if p.is_file()}
    summary_path = spec['stopped_v3_summary']
    summary_raw = summary_path.read_bytes()
    yield m, old, previous, trial, parent, two_parent
    for root in roots:
        for path in root.rglob('*'):
            if path.is_file() and path not in files:
                path.unlink()
    for path, (raw, mode) in files.items():
        path.write_bytes(raw)
        path.chmod(mode)
    summary_path.write_bytes(summary_raw)


def test_six_holds_new_permission_and_old_v3_rejection_are_independent(owned: Any) -> None:
    m, _, _, trial, parent, _ = owned
    report = trial.prepare()
    history = report['binding']['parent']
    assert history['historical_calls'] == 6
    assert history['nested_v2']['historical_calls'] == 5
    assert history['nested_v2']['nested_v1']['historical_calls'] == 3
    assert history['historical_held_microcny'] == trial.spec['limits']['historical_held_microcny']
    assert history['parent_semantic'] == 'REJECT' and report['approval']['approved'] is False
    binding = m.package_binding('v3-r1', _spec=parent.spec)
    with pytest.raises(ValueError, match='PREVIOUS'):
        parent.previous(parent.ledger(binding), binding, m.sha(m.read(parent.control / 'grant.json', private=True)))
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('new fee permission required'))
    assert trial.ledger(report['binding'])['attempts'] == []


def test_all_ten_summary_fields_are_literal_and_original_source_is_exact(owned: Any) -> None:
    from youtube_intel.summary_baseline import SEMANTIC_FIELDS

    m, _, _, trial, _, _ = owned
    manifest = m.parsed(trial.spec['package'] / 'manifest.json')
    for row in manifest['cases']:
        artifacts = Path(row['artifacts'])
        proof = m.parsed(artifacts / 'prepared-proof.json')
        body = m.parsed(artifacts / 'provider-body.json')
        raw = m.p.loads(proof['capture']['summary_raw'])
        displayed = m.p.loads(body['messages'][-1]['content'].split('=', 1)[1])
        assert displayed['summary'] == {name: raw[name] for name in SEMANTIC_FIELDS}
        old_artifacts = trial.spec['original']['package'] / 'cases' / row['case'] / 'artifacts'
        old_proof = m.parsed(old_artifacts / 'prepared-proof.json')
        assert proof['capture'] == old_proof['capture'] and proof['command'] == old_proof['command']
        assert body['messages'][:3] == m.parsed(old_artifacts / 'provider-body.json')['messages'][:3]
        assert m.profile.resolve_profile(m.profile.READABLE_SUMMARY_PROFILE_ID)['max_request_bytes'] == 40960


@pytest.mark.parametrize('kind', ['old-purpose', 'expired', 'binding', 'old-budget', 'profile'])
def test_fresh_exact_grant_precedes_credentials(owned: Any, kind: str) -> None:
    m, _, _, trial, _, _ = owned
    report = trial.prepare()
    grant = {**report['approval'], 'approved': True, 'decision_id': 'SYNTHETIC_ONLY', 'expires_at': '2099-01-01T00:00:00+00:00'}
    if kind == 'old-purpose':
        grant['purpose'] = trial.spec['original']['purpose']
    elif kind == 'expired':
        grant['expires_at'] = '2020-01-01T00:00:00+00:00'
    elif kind == 'old-budget':
        grant['limits'] = trial.spec['original']['limits']
    else:
        grant['binding_sha256'] = report['binding']['parent']['binding_sha256']
    m.once(trial.control / 'grant.json', grant)
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('no key before exact current consent'))
    assert not trial.runs.exists()


@pytest.mark.parametrize('kind', ['extra-attempt', 'extra-result', 'raw', 'unknown-state', 'false-pass', 'source', 'nested', 'independent'])
def test_parent_chain_tampering_stops_before_child_creation(owned: Any, kind: str) -> None:
    m, _, _, trial, parent, two_parent = owned
    case = parent.spec['order'][0]
    if kind.startswith('extra'):
        m.once(parent.control / ('attempt-2.json' if kind == 'extra-attempt' else 'unknown.result.json'), {})
    elif kind == 'nested':
        path = two_parent.control / 'ledger.json'
        path.write_bytes(path.read_bytes() + b' ')
    elif kind in {'source', 'independent'}:
        path = trial.spec['frozen_parent_source'] / ('src/youtube_intel/system_synthesis.py' if kind == 'source'
            else '.var/independent-v3-semantic-20261107/' + case + '.json')
        path.write_bytes(path.read_bytes() + b' ')
    else:
        path = parent.control / (case + ('.semantic.json' if kind == 'false-pass' else '.final.json' if kind == 'raw' else '.result.json'))
        value = m.parsed(path, private=True)
        if kind == 'false-pass':
            value['decision'] = 'PASS'
        elif kind == 'raw':
            value['raw_text'] += 'SYNTHETIC_TAMPER'
        else:
            value['execution_status'] = 'UNKNOWN'
        path.write_bytes(m.encoded(value))
        summary_path = trial.spec['stopped_v3_summary']
        summary = m.parsed(summary_path, private=True)
        summary['pins'][path.name] = m.sha(path.read_bytes())
        summary_path.write_bytes(m.encoded(summary))
        trial.spec['stopped_v3_summary_sha256'] = m.sha(m.encoded(summary))
    with pytest.raises(ValueError, match='PARENT'):
        trial.prepare()
    assert not trial.control.exists()


def test_new_eight_require_new_root_semantics_and_refuse_ninth(owned: Any) -> None:
    m, old, previous, trial, _, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    for case in trial.spec['order']:
        result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
        assert result['case'] == case and result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT', result
        assert result['qualification'] == 'CLOSED'
        with pytest.raises(ValueError, match='PREVIOUS'):
            trial.execute(credential=lambda: pytest.fail('each new result needs new Root PASS'))
        previous.semantic(m, trial, result)
    with pytest.raises(ValueError, match='GUI_SLOT_NOT_EXECUTABLE'):
        trial.execute(credential=lambda: pytest.fail('no automatic GUI fee'))
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 8


@pytest.mark.parametrize('branch', ['timeout', '429', 'truncated', 'reject'])
def test_failed_or_unknown_call_keeps_hold_and_stops_after_restart(owned: Any, branch: str) -> None:
    m, old, previous, trial, _, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls, 'zero' if branch == 'reject' else branch))
    if branch == 'reject':
        previous.semantic(m, trial, result, 'REJECT')
    else:
        assert result['status'] in {'TECHNICAL_FAILURE_STOP', 'UNKNOWN_STOP'}
    restarted = m.Trial(variant='v4-r1', control=trial.control, runs=trial.runs, _spec=trial.spec)
    with pytest.raises(ValueError, match='PREVIOUS'):
        restarted.execute(credential=lambda: pytest.fail('held failure cannot be replayed'))
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 1


@pytest.mark.parametrize('phase', ['before-claim', 'after-key'])
def test_parent_is_revalidated_at_dispatch_boundaries(owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    m, old, previous, trial, parent, _ = owned
    previous.approve(m, trial)
    calls: list[object] = []
    keys: list[bool] = []
    original = m.PersonalizedDistillationService.preview_cloud_execution

    def mutate() -> None:
        path = parent.control / 'ledger.json'
        path.write_bytes(path.read_bytes() + b' ')

    def preview(service: Any, **kwargs: Any) -> Any:
        review = original(service, **kwargs)
        if phase == 'before-claim' and (trial.control / 'attempt-1.json').exists():
            mutate()
        return review

    def key() -> str:
        keys.append(True)
        if phase == 'after-key':
            mutate()
        return 'synthetic-external-key'

    monkeypatch.setattr(m.PersonalizedDistillationService, 'preview_cloud_execution', preview)
    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result['status'] == 'UNKNOWN_STOP' and calls == []
    assert len(keys) == (1 if phase == 'after-key' else 0)


def test_concurrent_once_and_consumed_control_loss_are_closed(owned: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    m, old, previous, trial, _, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []

    def execute() -> Any:
        try:
            return trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: execute(), range(2)))
    assert sum(isinstance(row, dict) and row['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' for row in results) == 1
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 1
    trial.control.rename(trial.control.with_name('preserved-used-control'))
    with pytest.raises(ValueError, match='INITIALIZATION'):
        trial.prepare()


def test_orphan_hold_stays_closed_before_credentials(owned: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    m, _, previous, trial, _, _ = owned
    report = previous.approve(m, trial)

    def crash(*args: Any) -> None:
        raise RuntimeError('SYNTHETIC_CRASH_AFTER_HOLD')

    monkeypatch.setattr(m, 'replace_ledger', crash)
    with pytest.raises(RuntimeError, match='SYNTHETIC_CRASH'):
        trial.execute(credential=lambda: pytest.fail('crash before key'))
    assert (trial.control / 'attempt-1.json').exists()
    with pytest.raises(ValueError, match='LEDGER'):
        trial.ledger(report['binding'])


@pytest.mark.parametrize('phase', ['before-key', 'after-key'])
def test_current_source_is_rechecked_before_and_after_key(owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    m, old, previous, trial, _, _ = owned
    previous.approve(m, trial)
    changed = [False]
    keys: list[bool] = []
    calls: list[object] = []
    hashes = m.code_hashes
    confirm = m.PersonalizedDistillationService.confirm_synthesis_qualification

    def code_hashes(**kwargs: Any) -> Any:
        original = hashes(**kwargs)
        return {**original, 'synthetic-change.py': 'f' * 64} if changed[0] and not kwargs else original

    def wrapped(service: Any, **kwargs: Any) -> Any:
        if phase == 'before-key':
            changed[0] = True
        return confirm(service, **kwargs)

    def key() -> str:
        keys.append(True)
        changed[0] = True
        return 'synthetic-external-key'

    monkeypatch.setattr(m, 'code_hashes', code_hashes)
    monkeypatch.setattr(m.PersonalizedDistillationService, 'confirm_synthesis_qualification', wrapped)
    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result['status'] == 'UNKNOWN_STOP' and calls == []
    assert len(keys) == (1 if phase == 'after-key' else 0)


def test_child_backup_restore_keeps_all_sql_data_and_external_hold(owned: Any) -> None:
    from datetime import UTC, datetime, timedelta

    m, old, previous, trial, _, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT'
    root = trial.runs / result['case']
    before = m.inputs.inventory(root)
    controls = {p.name: m.sha(m.read(p, private=True)) for p in trial.control.iterdir()}
    clock = [datetime.now(UTC)]
    with m.inputs.offline():
        active = m.inputs.runtime(root, clock)
        assert active.backup_restore.readiness()['ready']
        download = active.backup_restore.backup_download(active.backup_restore.create_backup().backup_id)
        assert download is not None
        staged = active.backup_restore.stage_restore(download[0].read_bytes())
        active.backup_restore.confirm_restore(staged.restore_id)
        clock[0] += timedelta(seconds=3)
        restored = m.inputs.runtime(root, clock)
        assert restored.backup_restore.readiness()['ready']
        assert m.inputs.inventory(root) == before
    assert {p.name: m.sha(m.read(p, private=True)) for p in trial.control.iterdir()} == controls
    assert len(trial.ledger(report['binding'])['attempts']) == len(calls) == 1
    with pytest.raises(ValueError, match='PREVIOUS'):
        trial.execute(credential=lambda: pytest.fail('Restore cannot create semantic PASS'))


def test_v3_decision_cannot_approve_new_v4_receipt(owned: Any) -> None:
    m, old, previous, trial, parent, _ = owned
    previous.approve(m, trial)
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, []))
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT'
    decision = m.parsed(parent.control / (result['case'] + '.semantic.json'), private=True)
    decision['decision'] = 'PASS'
    m.once(trial.control / (result['case'] + '.semantic.json'), decision)
    with pytest.raises(ValueError, match='PREVIOUS'):
        trial.execute(credential=lambda: pytest.fail('old proof/receipt cannot approve new output'))


def test_expired_v3_grant_retains_only_its_historical_hold(owned: Any) -> None:
    from datetime import datetime, timedelta

    m, _, _, trial, parent, _ = owned
    case = parent.spec['order'][0]
    result_path = parent.control / (case + '.result.json')
    result = m.parsed(result_path, private=True)
    authorized = datetime.fromisoformat(result['state_trace']['system_synthesis_cloud_authorizations'][0]['authorized_at'])
    grant = m.parsed(parent.control / 'grant.json', private=True)
    grant['expires_at'] = (authorized + timedelta(microseconds=1)).isoformat()
    (parent.control / 'grant.json').write_bytes(m.encoded(grant))
    attempt = m.parsed(parent.control / 'attempt-1.json', private=True)
    attempt['grant_sha256'] = m.sha(m.encoded(grant))
    (parent.control / 'attempt-1.json').write_bytes(m.encoded(attempt))
    ledger = m.parsed(parent.control / 'ledger.json', private=True)
    ledger['attempts'] = [attempt]
    (parent.control / 'ledger.json').write_bytes(m.encoded(ledger))
    result['grant_sha256'] = attempt['grant_sha256']
    result_path.write_bytes(m.encoded(result))
    decision_path = parent.control / (case + '.semantic.json')
    decision = m.parsed(decision_path, private=True)
    decision['result_sha256'] = m.sha(m.encoded(result))
    decision_path.write_bytes(m.encoded(decision))
    summary_path = trial.spec['stopped_v3_summary']
    summary = m.parsed(summary_path, private=True)
    summary['pins'] = {p.name: m.sha(p.read_bytes()) for p in parent.control.iterdir()}
    summary_path.write_bytes(m.encoded(summary))
    trial.spec['stopped_v3_summary_sha256'] = m.sha(m.encoded(summary))
    history = m.stopped_v3_parent(trial.spec)
    assert history['historical_calls'] == 6
    with pytest.raises(ValueError, match='GRANT'):
        trial.grant({'parent': history})


@pytest.mark.parametrize('kind', ['mode', 'hardlink', 'same-bytes-new-inode'])
def test_parent_private_file_and_identity_precede_credentials(owned: Any, kind: str) -> None:
    import os

    m, _, previous, trial, parent, _ = owned
    previous.approve(m, trial)
    path = parent.control / 'ledger.json'
    saved = parent.control.parent / ('preserved-ledger-' + kind + '.json')
    if kind == 'mode':
        path.chmod(0o644)
    else:
        path.rename(saved)
        if kind == 'hardlink':
            os.link(saved, path)
        else:
            m.once(path, m.parsed(saved, private=True))
    try:
        with pytest.raises(ValueError, match='PARENT|GRANT'):
            trial.execute(credential=lambda: pytest.fail('identity mismatch before key'))
    finally:
        if saved.exists():
            path.unlink()
            saved.rename(path)


def test_restored_preexecution_parent_database_cannot_erase_old_invocation(owned: Any) -> None:
    m, _, _, trial, parent, _ = owned
    case = parent.spec['order'][0]
    database = parent.runs / case / 'state.sqlite3'
    gc.collect()
    original_raw = database.read_bytes()
    source = parent.spec['package'] / 'cases' / case / 'project/state.sqlite3'
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as before:
            with closing(sqlite3.connect(database)) as restored:
                before.backup(restored)
        with pytest.raises(ValueError, match='PARENT'):
            trial.prepare()
        assert not trial.control.exists()
    finally:
        gc.collect()
        database.write_bytes(original_raw)
