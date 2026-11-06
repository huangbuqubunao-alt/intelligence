"""Owned finite v3 continuation tests; synthetic accounting is not live quality."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

import pytest


def controller() -> Any:
    from conftest import _load_module
    return _load_module('test_bounded_synthesis_v2_trial').controller()


def test_finite_v3_has_fresh_purpose_and_full_history() -> None:
    m = controller()
    spec = m.trial_spec('v3-r1')
    assert m.trial_spec()['variant'] == 'v1-r4'
    assert m.trial_spec('v2-r1')['limits'] == m.V2_LIMITS
    assert spec['profile_id'] == m.profile.SOURCE_LEVEL_PROFILE_ID
    assert spec['purpose'] == 'ROOT_RECORDED_SOURCE_LEVEL_V3_CONTINUATION'
    assert spec['limits']['historical_calls'] == 5
    assert spec['limits']['historical_held_microcny'] == 4881252
    assert spec['limits']['prospective_total_microcny'] == 11603148
    assert spec['limits']['total_microcny'] == 12000000
    assert spec['limits']['max_total_calls'] == 14


@pytest.fixture(scope='module')
def template(tmp_path_factory: pytest.TempPathFactory) -> Any:
    from dataclasses import replace

    from conftest import _load_module

    previous = _load_module('test_bounded_synthesis_v2_trial')
    m, old, two, root = previous.template.__wrapped__(tmp_path_factory)
    parent_trial = m.Trial(variant='v2-r1', control=root / 'v2-control', runs=root / 'v2-runs', _spec=two)
    two.update(control=parent_trial.control, runs=parent_trial.runs)
    report = previous.approve(m, parent_trial)
    storage = _load_module('test_system_synthesis_persistence')

    def wire(*args: Any) -> Any:
        response = old.fake_wire(m, [])(*args)
        return replace(response, final_content=storage.raw_positive())

    for decision in ('PASS', 'REJECT'):
        result = parent_trial.execute(credential=lambda: 'synthetic-external-key', wire=wire)
        assert result['execution_status'] == 'SUCCEEDED', result
        previous.semantic(m, parent_trial, result, decision)
    # Freeze physically settled owned SQLite files. The real stopped parent has
    # no live writer. Explicitly close/checkpoint synthetic runtimes here too.
    import gc
    import sqlite3
    from contextlib import closing

    gc.collect()
    for case in two['order'][:2]:
        with closing(sqlite3.connect(parent_trial.runs / case / 'state.sqlite3')) as connection:
            connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    frozen = root / 'frozen-source'
    for name in report['binding']['source_hashes']:
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(m.read(m.REPO / name))
    reviews = frozen / '.var/independent-v2-semantic-20261106'
    m.directory(reviews, create=True)
    review_pins = []
    for case, verdict in zip(two['order'][:2], ('PASS', 'REJECT'), strict=True):
        m.once(reviews / (case + '.json'), {'case': case, 'verdict': verdict, 'identity': 'SYNTHETIC_NOT_REAL_QUALITY'})
        review_pins.append(m.sha(m.read(reviews / (case + '.json'), private=True)))
    restore = root / 'synthetic-restore.json'
    m.once(restore, {'status': 'REAL_PAID_RESULT_RESTORE_PASS_NO_REEXECUTION', 'case': two['order'][1],
        'semantic': 'REJECT', 'all_data_files_equal': True, 'all_table_rows_equal': True,
        'external_controls_hashes_equal': True, 'backup_ready_after_restore': True,
        'new_model_calls_during_backup_restore': 0, 'original_invocation_count': 1,
        'identity': 'SYNTHETIC_RESTORE_ONLY'})
    three = m.trial_spec('v3-r1')
    held = two['limits']['historical_held_microcny'] + sum(a['reserve_microcny']
        for a in m.parsed(parent_trial.control / 'ledger.json', private=True)['attempts'])
    manifest = m.parsed(two['package'] / 'manifest.json')
    estimates = [m.p.loads(m.p._assemble(m.parsed(Path(row['artifacts']) / 'prepared-proof.json')['command'],
        m.parsed(Path(row['artifacts']) / 'prepared-proof.json')['capture'],
        profile_id=m.profile.SOURCE_LEVEL_PROFILE_ID).proof_json)['reserve_microunits'] for row in manifest['cases']]
    three.update(original=two, package=root / 'v3-package', order=two['order'], seed=two['seed'],
        frozen_parent_source=frozen, parent_runs=parent_trial.runs,
        historical_revision=report['binding']['source_revision'],
        historical_binding_sha256=m.sha(m.encoded(report['binding'])),
        historical_manifest_sha256=report['binding']['manifest_sha256'],
        historical_marker_sha256=m.sha(m.read(parent_trial.initialization_marker(), private=True)),
        independent_report_pins=review_pins, restore_report=restore,
        parent_pins={p.name: m.sha(m.read(p, private=True)) for p in parent_trial.control.iterdir()})
    three['limits'].update(historical_held_microcny=held, runner_held_microcny=sum(estimates),
        gui_held_microcny=estimates[1], prospective_total_microcny=held + sum(estimates) + estimates[1])
    patcher = pytest.MonkeyPatch()
    check_output = m.subprocess.check_output

    def revision(command: Any, **kwargs: Any) -> Any:
        if command == ['git', '-C', str(frozen), 'rev-parse', 'HEAD']:
            return report['binding']['source_revision'] + '\n'
        return check_output(command, **kwargs)

    patcher.setattr(m.subprocess, 'check_output', revision)
    path = Path(m.__file__).with_name('materialize_synthesis_v2_inputs.py')
    spec = importlib.util.spec_from_file_location('owned_v3_package_builder', path)
    assert spec and spec.loader
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    proposal = helper.materialize(three)
    assert proposal['approval']['approved'] is False
    yield m, old, previous, three, parent_trial
    patcher.undo()


@pytest.fixture
def owned(tmp_path: Path, template: Any) -> Any:
    m, old, previous, original, parent = template
    spec = copy.deepcopy(original)
    trial = m.Trial(variant='v3-r1', control=tmp_path / 'child', runs=tmp_path / 'runs', _spec=spec)
    # Shared synthetic parent stays immutable across cases, including after a
    # deliberately corrupt-input test. Restore original inodes rather than copy.
    files = {p: (p.read_bytes(), p.stat().st_mode & 0o777) for p in parent.control.iterdir()}
    frozen_files = {p: p.read_bytes() for p in spec['frozen_parent_source'].rglob('*') if p.is_file()}
    yield m, old, previous, trial, parent
    for p in parent.control.iterdir():
        if p not in files:
            p.unlink()
    for p, (raw, mode) in files.items():
        p.write_bytes(raw)
        p.chmod(mode)
    for p, raw in frozen_files.items():
        p.write_bytes(raw)


def test_five_calls_are_held_and_old_rejection_blocks_only_old_batch(owned: Any) -> None:
    m, _, _, trial, parent = owned
    report = trial.prepare()
    history = report['binding']['parent']
    assert history['historical_calls'] == 5
    assert history['historical_held_microcny'] == trial.spec['limits']['historical_held_microcny']
    assert history['nested_v1']['historical_calls'] == 3
    assert [row['decision'] for row in history['terminals']] == ['PASS', 'REJECT']
    assert report['approval']['approved'] is False
    with pytest.raises(ValueError, match='PREVIOUS'):
        binding = m.package_binding('v2-r1', _spec=parent.spec)
        parent.previous(parent.ledger(binding), binding, m.sha(m.read(parent.control / 'grant.json', private=True)))
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('no new paid consent'))
    assert trial.ledger(report['binding'])['attempts'] == []


@pytest.mark.parametrize('kind', ['old-purpose', 'expired', 'binding', 'budget'])
def test_new_exact_grant_precedes_key_and_claim(owned: Any, kind: str) -> None:
    m, _, _, trial, _ = owned
    report = trial.prepare()
    grant = {**report['approval'], 'approved': True, 'decision_id': 'SYNTHETIC_ONLY',
        'expires_at': '2099-01-01T00:00:00+00:00'}
    if kind == 'old-purpose':
        grant['purpose'] = trial.spec['original']['purpose']
    elif kind == 'expired':
        grant['expires_at'] = '2020-01-01T00:00:00+00:00'
    elif kind == 'binding':
        grant['binding_sha256'] = report['binding']['parent']['binding_sha256']
    else:
        grant['limits'] = trial.spec['original']['limits']
    m.once(trial.control / 'grant.json', grant)
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('must refuse before key'))
    assert not trial.runs.exists()


@pytest.mark.parametrize('kind', ['extra-attempt', 'extra-result', 'hash', 'unknown-state', 'false-pass', 'source', 'independent'])
def test_old_parent_tamper_refuses_before_new_control(owned: Any, kind: str) -> None:
    m, _, _, trial, parent = owned
    case = parent.spec['order'][1]
    if kind.startswith('extra'):
        m.once(parent.control / ('attempt-3.json' if kind == 'extra-attempt' else 'unknown.result.json'), {})
    elif kind in {'hash', 'unknown-state', 'false-pass'}:
        path = parent.control / (case + ('.semantic.json' if kind == 'false-pass' else '.result.json'))
        value = m.parsed(path, private=True)
        if kind == 'unknown-state':
            value['execution_status'] = 'UNKNOWN'
        elif kind == 'false-pass':
            value['decision'] = 'PASS'
        else:
            value['reserve_microcny'] += 1
        path.write_bytes(m.encoded(value))
        # Even a new summary pin cannot convert unknown/rejected history.
        trial.spec['parent_pins'][path.name] = m.sha(path.read_bytes())
    else:
        path = trial.spec['frozen_parent_source'] / ('src/youtube_intel/system_synthesis.py'
            if kind == 'source' else '.var/independent-v2-semantic-20261106/' + case + '.json')
        path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='PARENT'):
        trial.prepare()
    assert not trial.control.exists()


def test_every_new_case_needs_new_semantics_and_ninth_is_forbidden(owned: Any) -> None:
    m, old, previous, trial, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    for case in trial.spec['order']:
        result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
        assert result['case'] == case and result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT', result
        assert result['qualification'] == 'CLOSED'
        with pytest.raises(ValueError, match='PREVIOUS'):
            trial.execute(credential=lambda: pytest.fail('new receipt needs new Root PASS'))
        previous.semantic(m, trial, result)
    with pytest.raises(ValueError, match='GUI_SLOT_NOT_EXECUTABLE'):
        trial.execute(credential=lambda: pytest.fail('no automatic ninth'))
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 8
    assert sum(a['reserve_microcny'] for a in trial.ledger(report['binding'])['attempts']) == trial.spec['limits']['runner_held_microcny']


@pytest.mark.parametrize('branch', ['timeout', '429', 'truncated', 'reject'])
def test_unknown_or_failure_retains_once_hold_and_stops(owned: Any, branch: str) -> None:
    m, old, previous, trial, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key',
        wire=old.fake_wire(m, calls, 'zero' if branch == 'reject' else branch))
    if branch == 'reject':
        previous.semantic(m, trial, result, 'REJECT')
    else:
        assert result['status'] in {'TECHNICAL_FAILURE_STOP', 'UNKNOWN_STOP'}
    restarted = m.Trial(variant='v3-r1', control=trial.control, runs=trial.runs, _spec=trial.spec)
    with pytest.raises(ValueError, match='PREVIOUS'):
        restarted.execute(credential=lambda: pytest.fail('failure stays held'))
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 1


@pytest.mark.parametrize('phase', ['before-claim', 'after-key'])
def test_parent_rechecked_at_each_dispatch_boundary(owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    m, old, previous, trial, parent = owned
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

    monkeypatch.setattr(m.PersonalizedDistillationService, 'preview_cloud_execution', preview)

    def key() -> str:
        keys.append(True)
        if phase == 'after-key':
            mutate()
        return 'synthetic-external-key'

    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result['status'] == 'UNKNOWN_STOP' and calls == []
    assert len(keys) == (1 if phase == 'after-key' else 0)


def test_concurrent_call_and_whole_control_loss_keep_consumed_marker(owned: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    m, old, previous, trial, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []

    def invoke() -> Any:
        try:
            return trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invoke(), range(2)))
    assert sum(isinstance(r, dict) and r['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' for r in results) == 1
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 1
    trial.control.rename(trial.control.with_name('preserved-consumed-control'))
    with pytest.raises(ValueError, match='INITIALIZATION'):
        trial.prepare()


def test_old_expired_grant_keeps_only_its_historical_authorization(owned: Any) -> None:
    from datetime import datetime, timedelta

    m, _, _, trial, parent = owned
    grant = m.parsed(parent.control / 'grant.json', private=True)
    ledger = m.parsed(parent.control / 'ledger.json', private=True)
    last = m.parsed(parent.control / (parent.spec['order'][1] + '.result.json'), private=True)
    authorized = datetime.fromisoformat(last['state_trace']['system_synthesis_cloud_authorizations'][0]['authorized_at'])
    grant['expires_at'] = (authorized + timedelta(microseconds=1)).isoformat()
    (parent.control / 'grant.json').write_bytes(m.encoded(grant))
    for index, attempt in enumerate(ledger['attempts']):
        attempt['grant_sha256'] = m.sha(m.encoded(grant))
        (parent.control / f'attempt-{index + 1}.json').write_bytes(m.encoded(attempt))
        case = attempt['case']
        path = parent.control / (case + '.result.json')
        result = m.parsed(path, private=True)
        result['grant_sha256'] = attempt['grant_sha256']
        path.write_bytes(m.encoded(result))
        path = parent.control / (case + '.semantic.json')
        decision = m.parsed(path, private=True)
        decision['result_sha256'] = m.sha(m.encoded(result))
        path.write_bytes(m.encoded(decision))
    (parent.control / 'ledger.json').write_bytes(m.encoded(ledger))
    trial.spec['parent_pins'] = {p.name: m.sha(p.read_bytes()) for p in parent.control.iterdir()}
    # Historical expiry is evaluated against the actual old authorization rows.
    history = m.stopped_v2_parent(trial.spec)
    assert history['historical_calls'] == 5
    with pytest.raises(ValueError, match='GRANT'):
        trial.grant({'parent': history})


def test_crash_after_immutable_hold_cannot_be_reinitialized(owned: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    m, _, previous, trial, _ = owned
    report = previous.approve(m, trial)

    def crash(*args: Any) -> None:
        raise RuntimeError('SYNTHETIC_CRASH_AFTER_RESERVATION')

    monkeypatch.setattr(m, 'replace_ledger', crash)
    with pytest.raises(RuntimeError, match='SYNTHETIC_CRASH'):
        trial.execute(credential=lambda: pytest.fail('crash before key'))
    assert (trial.control / 'attempt-1.json').exists()
    assert m.parsed(trial.control / 'ledger.json', private=True)['attempts'] == []
    with pytest.raises(ValueError, match='LEDGER'):
        trial.ledger(report['binding'])


@pytest.mark.parametrize('kind', ['mode', 'hardlink', 'same-bytes-new-inode'])
def test_parent_files_remain_private_and_identity_bound(owned: Any, kind: str) -> None:
    import os

    m, _, previous, trial, parent = owned
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
            trial.execute(credential=lambda: pytest.fail('parent changed before key'))
    finally:
        if saved.exists():
            path.unlink()
            saved.rename(path)


@pytest.mark.parametrize('phase', ['before-key', 'after-key'])
def test_current_source_is_rechecked_around_credential_resolution(owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    m, old, previous, trial, _ = owned
    previous.approve(m, trial)
    calls: list[object] = []
    keys: list[bool] = []
    changed = [False]
    hashes = m.code_hashes
    confirm = m.PersonalizedDistillationService.confirm_synthesis_qualification

    def code_hashes(**kwargs: Any) -> Any:
        actual = hashes(**kwargs)
        if changed[0] and not kwargs:
            return {**actual, 'synthetic-changed-source.py': 'f' * 64}
        return actual

    def wrapped_confirm(service: Any, **kwargs: Any) -> Any:
        if phase == 'before-key':
            changed[0] = True
        return confirm(service, **kwargs)

    def key() -> str:
        keys.append(True)
        if phase == 'after-key':
            changed[0] = True
        return 'synthetic-external-key'

    monkeypatch.setattr(m, 'code_hashes', code_hashes)
    monkeypatch.setattr(m.PersonalizedDistillationService, 'confirm_synthesis_qualification', wrapped_confirm)
    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result['status'] == 'UNKNOWN_STOP' and calls == []
    assert len(keys) == (1 if phase == 'after-key' else 0)


def test_backup_restore_of_executed_child_preserves_sql_data_and_external_hold(owned: Any) -> None:
    from datetime import UTC, datetime, timedelta

    m, old, previous, trial, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' and result['invocation_count'] == 1
    root = trial.runs / result['case']
    before = m.inputs.inventory(root)
    control_before = {p.name: m.sha(m.read(p, private=True)) for p in trial.control.iterdir()}
    clock = [datetime.now(UTC)]
    with m.inputs.offline():
        active = m.inputs.runtime(root, clock)
        service = active.backup_restore
        assert service.readiness()['ready']
        download = service.backup_download(service.create_backup().backup_id)
        assert download is not None
        staged = service.stage_restore(download[0].read_bytes())
        service.confirm_restore(staged.restore_id)
        clock[0] += timedelta(seconds=3)
        restored = m.inputs.runtime(root, clock)
        assert restored.backup_restore.readiness()['ready']
        assert m.inputs.inventory(root) == before
    assert {p.name: m.sha(m.read(p, private=True)) for p in trial.control.iterdir()} == control_before
    assert len(trial.ledger(report['binding'])['attempts']) == 1
    restarted = m.Trial(variant='v3-r1', control=trial.control, runs=trial.runs, _spec=trial.spec)
    with pytest.raises(ValueError, match='PREVIOUS'):
        restarted.execute(credential=lambda: pytest.fail('restore cannot imply Root semantic PASS'))
    assert len(calls) == 1


def test_old_v2_english_pass_cannot_approve_new_v3_result(owned: Any) -> None:
    m, old, previous, trial, parent = owned
    previous.approve(m, trial)
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, []))
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT'
    old_decision = m.parsed(parent.control / (result['case'] + '.semantic.json'), private=True)
    assert old_decision['decision'] == 'PASS'
    m.once(trial.control / (result['case'] + '.semantic.json'), old_decision)
    with pytest.raises(ValueError, match='PREVIOUS'):
        trial.execute(credential=lambda: pytest.fail('v2 PASS is not v3 semantic evidence'))
