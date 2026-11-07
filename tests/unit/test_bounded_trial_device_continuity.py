"""Owned metadata-only recovery; synthetic witnesses never authorize a call."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

import pytest
from conftest import _load_module


@pytest.fixture
def metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    m = _load_module('test_bounded_synthesis_v4_r2_trial').controller()
    original_identity = m.physical_identity

    def identity(path: Path, **kwargs: Any) -> Any:
        assert path.is_relative_to(tmp_path), 'portable test must not read operational paths'
        return {**original_identity(path, **kwargs), 'current_device': 16777232}

    monkeypatch.setattr(m, 'physical_identity', identity)
    controls = [tmp_path / f'owned-control-{i}' for i in range(4)]
    files = {}
    dirs = {}
    original: dict[str, Any] = {}
    for i, root in enumerate(controls):
        m.directory(root, create=True)
        anchor_device = 16777234 if i == 0 else 16777231
        m.once(root / 'anchor.json', {'control_device': anchor_device, 'control_inode': root.stat().st_ino})
        files[str(root / 'anchor.json')] = {**identity(root / 'anchor.json'), 'historical_device': 16777231}
        dirs[str(root)] = {**identity(root, directory_only=True), 'historical_device': 16777231,
            'anchor_device': anchor_device}
        original = {'control': root, 'original': original}
    supports = {}
    for key in ('baseline_snapshot', 'comparison_report'):
        path = tmp_path / (key + '.json')
        m.once(path, {'identity': 'OWNED_SYNTHETIC_NOT_ROOT_EVIDENCE'})
        supports[key] = {'path': str(path), 'sha256': m.sha(path.read_bytes())}
    witness = {**supports, 'controls': dirs, 'files': files, 'decision_id': 'SYNTHETIC_DEVICE_ONLY',
        'new_fee_authorized': False, 'purpose': 'HISTORICAL_METADATA_ONLY_NOT_FEE_AUTHORIZATION',
        'transition': {'historical_device': 16777231, 'current_device': 16777232},
        'version': 'bounded-trial-apfs-device-continuity-v1'}
    path = tmp_path / 'owned-witness.json'
    m.once(path, witness)
    spec = {'variant': 'v4-r2', 'original': original, 'device_continuity': {'path': path,
        'sha256': m.sha(path.read_bytes()), **witness['transition'], 'decision_id': witness['decision_id']}}
    return m, spec, witness, controls


def test_exact_context_has_immutable_history_and_separate_current_identity(metadata: Any) -> None:
    m, spec, _, controls = metadata
    context = m.historical_metadata(spec)
    assert context.device(controls[0]) == 16777231
    assert m.historical_device(controls[0], None) == 16777232
    assert context.evidence()['current_controls'][str(controls[0])]['current_device'] == 16777232
    assert context.evidence()['sha256'] == spec['device_continuity']['sha256']
    assert context.evidence()['new_fee_authorized'] is False
    with pytest.raises(AttributeError):
        context.raw = b'changed'
    with pytest.raises(ValueError, match='UNPINNED'):
        context.device(spec['device_continuity']['path'])
    with pytest.raises(ValueError, match='UNPINNED'):
        context.device(Path(m.parsed(spec['device_continuity']['path'])['comparison_report']['path']))
    with pytest.raises(ValueError, match='R2_ONLY'):
        m.historical_metadata({**spec, 'variant': 'v4-r1'})
    assert m.historical_metadata({'variant': 'v4-r1'}) is None


@pytest.mark.parametrize('field', ['current_device', 'inode', 'owner_uid', 'mode', 'nlink', 'mtime_ns', 'bytes', 'sha256'])
def test_every_pinned_identity_component_is_enforced(metadata: Any, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    m, spec, _, controls = metadata
    original = m.physical_identity
    target = controls[0] / 'anchor.json'

    def changed(path: Path, **kwargs: Any) -> Any:
        value = original(path, **kwargs)
        if path == target:
            value[field] = '0' * 64 if field == 'sha256' else value[field] + 1
        return value

    monkeypatch.setattr(m, 'physical_identity', changed)
    with pytest.raises(ValueError, match='CONTINUITY'):
        m.historical_metadata(spec)


def test_witness_itself_must_remain_on_the_current_device(metadata: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    m, spec, _, _ = metadata
    identity = m.physical_identity

    def wrong_device(path: Path, **kwargs: Any) -> Any:
        value = identity(path, **kwargs)
        if path == spec['device_continuity']['path']:
            value['current_device'] += 1
        return value

    monkeypatch.setattr(m, 'physical_identity', wrong_device)
    with pytest.raises(ValueError, match='WITNESS_DEVICE'):
        m.historical_metadata(spec)


@pytest.mark.parametrize('damage', ['missing', 'hash', 'extra', 'wrong-path', 'wrong-transition', 'fee-true', 'support', 'marker'])
def test_unknown_or_changed_witness_never_becomes_authority(metadata: Any, damage: str) -> None:
    m, spec, witness, controls = metadata
    path = spec['device_continuity']['path']
    if damage == 'missing':
        path.rename(path.with_name('preserved-witness'))
    elif damage == 'hash':
        path.write_bytes(path.read_bytes() + b' ')
    elif damage == 'extra':
        m.once(controls[0] / 'unknown.json', {})
    elif damage == 'support':
        Path(witness['comparison_report']['path']).write_bytes(b'changed')
    elif damage == 'marker':
        (controls[1] / 'anchor.json').write_bytes(b'{}')
    else:
        value = copy.deepcopy(witness)
        if damage == 'wrong-path':
            value['files'][str(path.parent / 'unpinned.json')] = value['files'].pop(str(controls[0] / 'anchor.json'))
        elif damage == 'wrong-transition':
            value['transition']['current_device'] += 1
        else:
            value['new_fee_authorized'] = True
        path.write_bytes(m.encoded(value))
        spec['device_continuity']['sha256'] = m.sha(path.read_bytes())
    with pytest.raises(ValueError):
        m.historical_metadata(spec)


@pytest.fixture(scope='module')
def continued_template(tmp_path_factory: pytest.TempPathFactory) -> Any:
    prior = _load_module('test_bounded_synthesis_v4_r2_trial')
    generator = prior.template.__wrapped__(tmp_path_factory)
    m, old, previous, original, parent, _, _ = next(generator)
    root = tmp_path_factory.mktemp('owned-device-continuity')
    saved_parent = m.parsed(original['package'] / 'proposal-not-authorized.json')['binding']['parent']
    specs = []
    item = original['original']
    while item:
        specs.append(item)
        item = item.get('original')
    controls = {item['control'] for item in specs}
    paths = {path for control in controls for path in control.iterdir()}
    for control in controls:
        marker = control.with_name(control.name + '-initialized.json')
        if marker.exists():
            paths.add(marker)
    for item in specs:
        for key in ('parent_summary', 'stopped_v3_summary'):
            if key in item:
                paths.add(item[key])
        if item.get('parent_location_proof', root / 'absent').exists():
            paths.add(item['parent_location_proof'])
        for case in item['order']:
            run = item['runs'] / case
            if run.exists():
                paths.add(run / 'state.sqlite3')
                paths.update(path for path in (run / 'data').rglob('*') if path.is_file())
    paths.add(original['preclaim_parent_witness'])
    old_witness = m.parsed(original['preclaim_parent_witness'])
    paths.update(Path(old_witness[key]) for key in ('approved_grant_record', 'root_stop_report', 'restore_report'))
    # Only this module's explicit identity boundary simulates the remount.
    # No Path/os/sqlite API is replaced; all bytes and inodes remain genuine.
    actual = parent.control.stat().st_dev
    current = actual + 1
    witness_path = root / 'owned-device-witness.json'
    supports = {key: root / (key + '.json') for key in ('baseline_snapshot', 'comparison_report')}
    for path in supports.values():
        m.once(path, {'identity': 'SYNTHETIC_OWNED_CONTINUITY_NOT_REAL_RESTART_EVIDENCE'})
    observed = m.physical_identity

    def identity(path: Path, **kwargs: Any) -> Any:
        value = observed(path, **kwargs)
        if path in paths | controls | {witness_path, *supports.values()}:
            value['current_device'] = current
        return value

    patcher = pytest.MonkeyPatch()
    patcher.setattr(m, 'physical_identity', identity)
    witness = {key: {'path': str(path), 'sha256': m.sha(path.read_bytes())} for key, path in supports.items()}
    witness.update(controls={str(path): {**identity(path, directory_only=True), 'historical_device': actual,
        'anchor_device': m.parsed(path / 'anchor.json')['control_device']} for path in controls},
        files={str(path): {**identity(path), 'historical_device': actual} for path in paths},
        version='bounded-trial-apfs-device-continuity-v1', purpose='HISTORICAL_METADATA_ONLY_NOT_FEE_AUTHORIZATION',
        decision_id='SYNTHETIC_OWNED_DEVICE_TRANSITION', new_fee_authorized=False,
        transition={'historical_device': actual, 'current_device': current})
    m.once(witness_path, witness)
    spec = copy.deepcopy(original)
    spec.update(package=root / 'new-r2-package', device_continuity={'path': witness_path,
        'sha256': m.sha(witness_path.read_bytes()), 'historical_device': actual, 'current_device': current,
        'decision_id': witness['decision_id']})
    helper_path = Path(m.__file__).with_name('materialize_synthesis_v2_inputs.py')
    loader = importlib.util.spec_from_file_location('owned_continuity_materializer', helper_path)
    assert loader and loader.loader
    helper = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(helper)
    helper.trial = m
    proposal = helper.materialize(spec)
    assert proposal['approval']['approved'] is False
    yield m, old, previous, spec, parent, saved_parent, current
    patcher.undo()
    next(generator, None)


@pytest.fixture
def continued(continued_template: Any, tmp_path: Path) -> Any:
    m, old, previous, spec, parent, saved, current = continued_template
    trial = m.Trial(variant='v4-r2', control=tmp_path / 'new-control', runs=tmp_path / 'new-runs',
        _spec=copy.deepcopy(spec))
    return m, old, previous, trial, parent, saved, current


def test_saved_history_stays_exact_new_parent_binds_current_and_needs_new_grant(continued: Any) -> None:
    m, _, _, trial, parent, saved, current = continued
    report = trial.prepare()
    history = report['binding']['parent']
    assert m.encoded(history['nested_v4']) == m.encoded(saved['nested_v4'])
    assert history['binding_sha256'] == saved['binding_sha256']
    assert history['control_device'] == current
    assert history['device_continuity']['sha256'] == trial.spec['device_continuity']['sha256']
    assert history['historical_calls'] == 7 and history['known_real_invocations'] == 6 and history['preclaim_stop_slots'] == 1
    assert history['historical_held_microcny'] == saved['historical_held_microcny']
    anchor = m.parsed(trial.control / 'anchor.json', private=True)
    assert anchor['control_device'] == trial.control.stat().st_dev
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('device continuity cannot authorize a new key read'))
    with pytest.raises(ValueError, match='PARENT'):
        m.stopped_v3_parent(parent.spec)
    unchanged = copy.deepcopy(trial.spec)
    unchanged['device_continuity'] = None
    with pytest.raises(ValueError, match='PRECLAIM'):
        m.stopped_preclaim_parent(unchanged)


def test_owned_new_receipt_keeps_current_control_and_original_unknown_parent(continued: Any) -> None:
    m, old, previous, trial, parent, _, current = continued
    previous.approve(m, trial)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls))
    assert result['status'] == 'TECHNICAL_PASS_AWAITING_ROOT' and len(calls) == 1
    assert m.parsed(parent.control / (result['case'] + '.result.json'))['status'] == 'UNKNOWN_STOP'
    assert m.stopped_preclaim_parent(trial.spec)['control_device'] == current
    with pytest.raises(ValueError, match='PREVIOUS'):
        trial.execute(credential=lambda: pytest.fail('new receipt needs its own Root semantic approval'))


@pytest.mark.parametrize('phase', ['before-claim', 'after-key'])
def test_continuity_drift_rechecked_before_claim_and_after_key(continued: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    m, old, previous, trial, parent, _, _ = continued
    previous.approve(m, trial)
    changed = [False]
    calls: list[object] = []
    keys: list[bool] = []
    identity = m.physical_identity
    preview = m.PersonalizedDistillationService.preview_cloud_execution
    target = parent.control / 'ledger.json'

    def drift(path: Path, **kwargs: Any) -> Any:
        value = identity(path, **kwargs)
        if changed[0] and path == target:
            value['mtime_ns'] += 1
        return value

    def wrapped(service: Any, **kwargs: Any) -> Any:
        result = preview(service, **kwargs)
        if phase == 'before-claim' and (trial.control / 'attempt-1.json').exists():
            changed[0] = True
        return result

    def key() -> str:
        keys.append(True)
        changed[0] = True
        return 'synthetic-external-key'

    monkeypatch.setattr(m, 'physical_identity', drift)
    monkeypatch.setattr(m.PersonalizedDistillationService, 'preview_cloud_execution', wrapped)
    result = trial.execute(credential=key, wire=old.fake_wire(m, calls))
    assert result['status'] == 'UNKNOWN_STOP' and result['send_attempted'] is False and calls == []
    assert len(keys) == (1 if phase == 'after-key' else 0)


def test_missing_continuity_witness_blocks_before_child_control(continued: Any, tmp_path: Path) -> None:
    m, _, _, trial, _, _, _ = continued
    trial.spec['device_continuity']['path'] = tmp_path / 'missing-witness.json'
    with pytest.raises(ValueError, match='PRECLAIM'):
        trial.prepare()
    assert not trial.control.exists()
