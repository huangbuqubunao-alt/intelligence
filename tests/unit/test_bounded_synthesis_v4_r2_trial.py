"""Owned r2 continuation tests, distinguishing a held slot from a model call."""
from __future__ import annotations

import copy
import gc
import importlib.util
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import _load_module


def controller() -> Any:
    return _load_module('test_bounded_synthesis_v2_trial').controller()


def test_finite_r2_has_separate_consent_and_compatible_fee_slot_limits() -> None:
    m = controller()
    spec = m.trial_spec('v4-r2')
    assert m.trial_spec()['variant'] == 'v1-r4'
    assert spec['original']['variant'] == 'v4-r1'
    assert spec['original']['original']['variant'] == 'v3-r1'
    assert m.trial_spec('v4-r1')['limits'] == m.V4_LIMITS
    assert spec['profile_id'] == spec['original']['profile_id'] == m.profile.READABLE_SUMMARY_PROFILE_ID
    assert spec['purpose'] != spec['original']['purpose']
    assert spec['limits']['historical_calls'] == 7
    assert spec['limits']['historical_held_microcny'] == 7238380
    assert spec['limits']['max_total_calls'] == 16 and spec['limits']['total_microcny'] == 16000000
    assert spec['limits']['per_call_microcny'] == 1500000
    assert spec['limits']['prospective_total_microcny'] == 15302344


@pytest.fixture(scope='module')
def template(tmp_path_factory: pytest.TempPathFactory) -> Any:
    old_v4 = _load_module('test_bounded_synthesis_v4_trial')
    generator = old_v4.template.__wrapped__(tmp_path_factory)
    m, old, previous, four, parent3, parent2 = next(generator)
    four = copy.deepcopy(four)
    root = tmp_path_factory.mktemp('owned-preclaim-r2')
    four.update(control=root / 'stopped-r1-control', runs=root / 'stopped-r1-runs')
    parent = m.Trial(variant='v4-r1', _spec=four)
    proposal = previous.approve(m, parent)
    with pytest.MonkeyPatch.context() as patcher:
        def preclaim_stop(*args: Any, **kwargs: Any) -> Any:
            raise ValueError('SYNTHETIC_PRECLAIM_GUARD_NO_MODEL_EXECUTION')
        patcher.setattr(m.PersonalizedDistillationService, 'confirm_synthesis_qualification', preclaim_stop)
        result = parent.execute(credential=lambda: pytest.fail('owned preclaim stop must not read a key'))
    assert result['status'] == 'UNKNOWN_STOP' and result['send_attempted'] is False
    assert all(rows == [] for rows in result['state_trace'].values())
    case = result['case']
    run = parent.runs / case
    before = m.inputs.inventory(run)
    clock = [datetime.now(UTC)]
    controls = {p.name: m.sha(m.read(p, private=True)) for p in parent.control.iterdir()}
    with m.inputs.offline():
        active = m.inputs.runtime(run, clock)
        assert active.backup_restore.readiness()['ready']
        download = active.backup_restore.backup_download(active.backup_restore.create_backup().backup_id)
        assert download is not None
        staged = active.backup_restore.stage_restore(download[0].read_bytes())
        active.backup_restore.confirm_restore(staged.restore_id)
        clock[0] += timedelta(seconds=3)
        assert m.inputs.runtime(run, clock).backup_restore.readiness()['ready']
    assert m.inputs.inventory(run) == before
    assert {p.name: m.sha(m.read(p, private=True)) for p in parent.control.iterdir()} == controls
    gc.collect()
    with closing(sqlite3.connect(run / 'state.sqlite3')) as connection:
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    frozen = root / 'frozen-r1-source'
    for name in proposal['binding']['source_hashes']:
        path = frozen / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(m.read(m.REPO / name))
    reports = frozen / '.var/final-checks/v4-real-20261107'
    m.directory(reports, create=True)
    grant = m.parsed(parent.control / 'grant.json', private=True)
    approval = {'status': 'USER_EXPLICITLY_APPROVED_BOUNDED_V4', 'decision_id': grant['decision_id'],
        'expires_at': grant['expires_at'], 'grant_sha256': m.sha(m.read(parent.control / 'grant.json', private=True)),
        'binding_sha256': m.sha(m.encoded(proposal['binding'])), 'limits': four['limits'],
        'source_revision': proposal['binding']['source_revision'], 'new_attempts_before_dispatch': 0,
        'qualification': 'CLOSED', 'actual_bill': 'UNKNOWN', 'identity': 'SYNTHETIC_NOT_REAL_FEE_CONSENT'}
    stop = {'status': 'V4_BATCH_STOPPED_PRECLAIM_QUALIFICATION_CAP_MISMATCH', 'case': case,
        'binding_sha256': approval['binding_sha256'], 'source_revision': approval['source_revision'],
        'actual_result_sha256': m.sha(m.encoded(result)), 'result_status': 'UNKNOWN_STOP', 'send_attempted': False,
        'new_real_model_invocations': 0, 'raw_final_or_receipt_exists': False, 'target_execution_trace_rows':
            {name: 0 for name in result['state_trace']}, 'new_reserve_microcny': result['reserve_microcny'],
        'qualification': 'CLOSED', 'identity': 'SYNTHETIC_PRECLAIM_SEAM_SIMULATION_NOT_ACTUAL_INCIDENT'}
    restore = {'status': 'REAL_V4_PRECLAIM_STOPPED_RESULT_RESTORE_PASS_NO_REEXECUTION', 'case': case,
        'result_status': 'UNKNOWN_STOP', 'all_data_files_equal': True, 'all_table_rows_equal': True,
        'external_controls_hashes_equal': True, 'backup_ready_after_restore': True, 'backup_ready_before': True,
        'external_control_files': 7, 'new_fee_attempts_during_backup_restore': 0, 'new_model_calls_during_backup_restore': 0,
        'target_invocation_count': 0, 'original_stopped_fee_hold_microcny': result['reserve_microcny'],
        'sql_tables': len(before['tables']), 'data_files': len(before['data']), 'identity': 'OWNED_REAL_RESTORE_FAKE_STOP'}
    paths = {'approved_grant_record': reports / 'approved.json', 'root_stop_report': reports / 'stop.json',
        'restore_report': reports / 'restore.json'}
    for name, body in [('approved_grant_record', approval), ('root_stop_report', stop), ('restore_report', restore)]:
        m.once(paths[name], body)
    held = four['limits']['historical_held_microcny'] + result['reserve_microcny']
    witness = {'actual_bill': 'UNKNOWN', 'binding_sha256': approval['binding_sha256'], 'control': str(parent.control),
        'historical_calls': 7, 'historical_held_microcny': held, 'known_real_invocations': 6,
        'manifest_sha256': proposal['binding']['manifest_sha256'], 'marker_sha256': m.sha(m.read(parent.initialization_marker(), private=True)),
        'new_fee_authorized': False, 'note': 'SYNTHETIC_OWNED_HISTORY_NOT_REAL_INVOCATIONS_OR_FEES',
        'parent_source': str(frozen), 'pins': controls, 'postrestore_database_sha256': m.sha(m.read(run / 'state.sqlite3')),
        'postrestore_inventory_sha256': m.sha(m.encoded(m.inputs.inventory(run))), 'preclaim_stop_slots': 1,
        'source_revision': proposal['binding']['source_revision'], 'version': 'v4-r1-preclaim-stopped-parent-v1'}
    for name, path in paths.items():
        witness[name] = str(path)
        witness[name + '_sha256'] = m.sha(m.read(path, private=True))
    witness_path = root / 'synthetic-preclaim-witness.json'
    m.once(witness_path, witness)
    r2 = m.trial_spec('v4-r2')
    r2.update(original=four, package=root / 'r2-package', order=four['order'], seed=four['seed'], device_continuity=None,
        frozen_parent_source=frozen, parent_runs=parent.runs, preclaim_parent_witness=witness_path,
        preclaim_parent_witness_sha256=m.sha(m.encoded(witness)), historical_revision=approval['source_revision'],
        historical_binding_sha256=approval['binding_sha256'], historical_manifest_sha256=witness['manifest_sha256'])
    r2['limits'].update(historical_held_microcny=held, runner_held_microcny=four['limits']['runner_held_microcny'],
        gui_held_microcny=four['limits']['gui_held_microcny'], prospective_total_microcny=held
            + four['limits']['runner_held_microcny'] + four['limits']['gui_held_microcny'])
    patcher = pytest.MonkeyPatch()
    check_output = m.subprocess.check_output
    def revision(command: Any, **kwargs: Any) -> Any:
        if command == ['git', '-C', str(frozen), 'rev-parse', 'HEAD']:
            return approval['source_revision'] + '\n'
        return check_output(command, **kwargs)
    patcher.setattr(m.subprocess, 'check_output', revision)
    path = Path(m.__file__).with_name('materialize_synthesis_v2_inputs.py')
    spec = importlib.util.spec_from_file_location('owned_r2_materializer', path)
    assert spec and spec.loader
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    prepared = helper.materialize(r2)
    assert prepared['approval']['approved'] is False
    yield m, old, previous, r2, parent, parent3, parent2
    patcher.undo()
    next(generator, None)


@pytest.fixture
def owned(tmp_path: Path, template: Any) -> Any:
    m, old, previous, original, parent, parent3, parent2 = template
    spec = copy.deepcopy(original)
    trial = m.Trial(variant='v4-r2', control=tmp_path / 'child', runs=tmp_path / 'runs', _spec=spec)
    roots = [parent.control, parent3.control, parent2.control, spec['frozen_parent_source']]
    files = {p: (p.read_bytes(), p.stat().st_mode & 0o777) for root in roots for p in root.rglob('*') if p.is_file()}
    for path in [spec['preclaim_parent_witness'], parent.initialization_marker()]:
        files[path] = (path.read_bytes(), path.stat().st_mode & 0o777)
    yield m, old, previous, trial, parent, parent3
    for root in roots:
        for path in root.rglob('*'):
            if path.is_file() and path not in files:
                path.unlink()
    for path, (raw, mode) in files.items():
        path.write_bytes(raw)
        path.chmod(mode)


def test_old_preclaim_slot_is_not_an_invocation_or_new_consent(owned: Any) -> None:
    m, _, _, trial, parent, _ = owned
    report = trial.prepare()
    history = report['binding']['parent']
    assert history['historical_calls'] == 7 and history['known_real_invocations'] == 6
    assert history['preclaim_stop_slots'] == 1 and history['nested_v4']['historical_calls'] == 6
    assert report['binding']['known_real_invocations'] == 6
    assert m.parsed(trial.spec['package'] / 'manifest.json')['preclaim_stop_slots'] == 1
    assert history['historical_held_microcny'] == trial.spec['limits']['historical_held_microcny']
    assert report['approval']['approved'] is False
    old_binding = m.parsed(parent.spec['package'] / 'proposal-not-authorized.json')['binding']
    with pytest.raises(ValueError, match='PREVIOUS'):
        parent.previous(parent.ledger(old_binding), old_binding, m.sha(m.read(parent.control / 'grant.json', private=True)))
    assert not any(parent.control.glob('*.semantic.json')) and not any(parent.control.glob('*.final.json'))
    with pytest.raises(ValueError, match='GRANT'):
        trial.execute(credential=lambda: pytest.fail('new explicit grant required'))


def test_r2_proofs_wires_and_source_match_r1_exactly(owned: Any) -> None:
    m, _, _, trial, _, _ = owned
    before = m.parsed(trial.spec['original']['package'] / 'manifest.json')
    after = m.parsed(trial.spec['package'] / 'manifest.json')
    for old, new in zip(before['cases'], after['cases'], strict=True):
        for key in ['execution_id', 'proof_sha256', 'wire_sha256', 'reserve_microcny', 'summary_sha256', 'source_refs_sha256']:
            assert old[key] == new[key]
        assert m.read(Path(old['artifacts']) / 'prepared-proof.json') == m.read(Path(new['artifacts']) / 'prepared-proof.json')
        assert m.read(Path(old['artifacts']) / 'provider-body.json') == m.read(Path(new['artifacts']) / 'provider-body.json')


@pytest.mark.parametrize('kind', ['send-true', 'trace', 'extra', 'missing', 'orphan', 'marker', 'restore', 'source', 'nested'])
def test_unproven_parent_closes_before_child_or_key(owned: Any, kind: str) -> None:
    m, _, _, trial, parent, parent3 = owned
    witness_path = trial.spec['preclaim_parent_witness']
    witness = m.parsed(witness_path, private=True)
    saved = None
    try:
        if kind in {'send-true', 'trace'}:
            path = parent.control / (parent.spec['order'][0] + '.result.json')
            result = m.parsed(path, private=True)
            if kind == 'send-true':
                result['send_attempted'] = True
            else:
                result['state_trace']['distillation_execution_checkpoints'] = [{'unknown': True}]
            path.write_bytes(m.encoded(result))
            witness['pins'][path.name] = m.sha(path.read_bytes())
            witness_path.write_bytes(m.encoded(witness))
            trial.spec['preclaim_parent_witness_sha256'] = m.sha(m.encoded(witness))
        elif kind in {'extra', 'orphan'}:
            m.once(parent.control / ('fabricated.semantic.json' if kind == 'extra' else 'attempt-2.json'), {})
        elif kind == 'missing':
            path = parent.control / 'attempt-1.json'
            saved = path.with_name('preserved-attempt')
            path.rename(saved)
        elif kind == 'marker':
            path = parent.initialization_marker()
            path.write_bytes(path.read_bytes() + b' ')
        elif kind == 'restore':
            path = Path(witness['restore_report'])
            path.write_bytes(path.read_bytes() + b' ')
        elif kind == 'source':
            path = trial.spec['frozen_parent_source'] / 'src/youtube_intel/distillation.py'
            path.write_bytes(path.read_bytes() + b' ')
        else:
            path = parent3.control / 'ledger.json'
            path.write_bytes(path.read_bytes() + b' ')
        with pytest.raises(ValueError, match='PRECLAIM|PARENT'):
            trial.prepare()
        assert not trial.control.exists()
    finally:
        if saved is not None:
            saved.rename(parent.control / 'attempt-1.json')


@pytest.mark.parametrize('kind', ['old-purpose', 'expired', 'binding', 'old-budget', 'profile'])
def test_fresh_grant_precedes_key(owned: Any, kind: str) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_fresh_exact_grant_precedes_credentials(owned, kind)


def test_eight_new_receipts_need_new_root_semantics_and_no_ninth(owned: Any) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_new_eight_require_new_root_semantics_and_refuse_ninth(owned)


@pytest.mark.parametrize('branch', ['timeout', '429', 'truncated', 'reject'])
def test_new_failure_holds_after_restart(owned: Any, branch: str) -> None:
    m, old, previous, trial, _, _ = owned
    report = previous.approve(m, trial)
    calls: list[object] = []
    result = trial.execute(credential=lambda: 'synthetic-external-key', wire=old.fake_wire(m, calls, 'zero' if branch == 'reject' else branch))
    if branch == 'reject':
        previous.semantic(m, trial, result, 'REJECT')
    else:
        assert result['status'] in {'TECHNICAL_FAILURE_STOP', 'UNKNOWN_STOP'}
    restarted = m.Trial(variant='v4-r2', control=trial.control, runs=trial.runs, _spec=trial.spec)
    with pytest.raises(ValueError, match='PREVIOUS'):
        restarted.execute(credential=lambda: pytest.fail('failure keeps hold'))
    assert len(calls) == len(trial.ledger(report['binding'])['attempts']) == 1


@pytest.mark.parametrize('phase', ['before-claim', 'after-key'])
def test_parent_revalidated_at_claim_and_key(owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_parent_is_revalidated_at_dispatch_boundaries(owned, monkeypatch, phase)


@pytest.mark.parametrize('phase', ['before-key', 'after-key'])
def test_current_source_revalidated_around_key(owned: Any, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_current_source_is_rechecked_before_and_after_key(owned, monkeypatch, phase)


def test_concurrent_once_and_lost_control(owned: Any) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_concurrent_once_and_consumed_control_loss_are_closed(owned)


def test_orphan_hold(owned: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_orphan_hold_stays_closed_before_credentials(owned, monkeypatch)


def test_child_restore_keeps_data_and_outside_hold(owned: Any) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_child_backup_restore_keeps_all_sql_data_and_external_hold(owned)


@pytest.mark.parametrize('kind', ['mode', 'hardlink', 'same-bytes-new-inode'])
def test_parent_identity_is_private_and_bound(owned: Any, kind: str) -> None:
    _load_module('test_bounded_synthesis_v4_trial').test_parent_private_file_and_identity_precede_credentials(owned, kind)


def test_actual_public_request_above_one_cny_reaches_normal_claim_and_fake_wire(tmp_path: Path) -> None:
    _load_module('test_synthesis_qualification_entry').test_v4_public_request_over_one_cny_uses_explicit_one_and_half_budget(tmp_path)


def test_expired_historical_preclaim_grant_does_not_become_new_permission(owned: Any) -> None:
    m, _, _, trial, parent, _ = owned
    witness_path = trial.spec['preclaim_parent_witness']
    witness = m.parsed(witness_path, private=True)
    grant_path = parent.control / 'grant.json'
    grant = m.parsed(grant_path, private=True)
    grant['expires_at'] = '2020-01-01T00:00:00+00:00'
    grant_path.write_bytes(m.encoded(grant))
    attempt_path = parent.control / 'attempt-1.json'
    attempt = m.parsed(attempt_path, private=True)
    attempt['grant_sha256'] = m.sha(grant_path.read_bytes())
    attempt_path.write_bytes(m.encoded(attempt))
    ledger = m.parsed(parent.control / 'ledger.json', private=True)
    ledger['attempts'] = [attempt]
    (parent.control / 'ledger.json').write_bytes(m.encoded(ledger))
    case = parent.spec['order'][0]
    result_path = parent.control / (case + '.result.json')
    result = m.parsed(result_path, private=True)
    result['grant_sha256'] = attempt['grant_sha256']
    result_path.write_bytes(m.encoded(result))
    approval_path = Path(witness['approved_grant_record'])
    approval = m.parsed(approval_path, private=True)
    approval.update(expires_at=grant['expires_at'], grant_sha256=attempt['grant_sha256'])
    approval_path.write_bytes(m.encoded(approval))
    stop_path = Path(witness['root_stop_report'])
    stop = m.parsed(stop_path, private=True)
    stop['actual_result_sha256'] = m.sha(result_path.read_bytes())
    stop_path.write_bytes(m.encoded(stop))
    witness['pins'] = {p.name: m.sha(p.read_bytes()) for p in parent.control.iterdir()}
    for name in ['approved_grant_record', 'root_stop_report']:
        witness[name + '_sha256'] = m.sha(m.read(Path(witness[name]), private=True))
    witness_path.write_bytes(m.encoded(witness))
    trial.spec['preclaim_parent_witness_sha256'] = m.sha(m.encoded(witness))
    history = m.stopped_preclaim_parent(trial.spec)
    assert history['known_real_invocations'] == 6 and history['preclaim_stop_slots'] == 1
    assert 'authorized_at' not in history
    with pytest.raises(ValueError, match='GRANT'):
        trial.grant({'parent': history})


@pytest.mark.parametrize('damage', ['changed-db', 'nonempty-claim'])
def test_parent_database_identity_and_absent_claim_are_independent_guards(owned: Any, damage: str) -> None:
    m, _, _, trial, parent, _ = owned
    case = parent.spec['order'][0]
    root = parent.runs / case
    database = root / 'state.sqlite3'
    gc.collect()
    original_raw = database.read_bytes()
    witness_path = trial.spec['preclaim_parent_witness']
    witness = m.parsed(witness_path, private=True)
    try:
        if damage == 'changed-db':
            with closing(sqlite3.connect(database)) as connection:
                connection.execute('PRAGMA user_version=99')
        else:
            row = m.parsed(parent.spec['package'] / 'manifest.json')['cases'][0]
            proof_raw = m.read(Path(row['artifacts']) / 'prepared-proof.json').decode()
            prepared = m.p.PreparedSynthesis(row['execution_id'], proof_raw, row['proof_sha256'])
            repository = m.SQLiteStateRepository(database)
            repository.bind_source_storage(root / 'data')
            now = datetime.now(UTC)
            m.p.reserve(repository, prepared, now=now)
            m.p.confirm_and_claim(repository, prepared, budget=m.p.SynthesisBudget('synthetic-unknown-parent', 1500000, 1),
                consent_kind='OWNER_QUALIFICATION', now=now)
            gc.collect()
            with closing(sqlite3.connect(database)) as connection:
                connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            witness['postrestore_database_sha256'] = m.sha(database.read_bytes())
            witness_path.write_bytes(m.encoded(witness))
            trial.spec['preclaim_parent_witness_sha256'] = m.sha(m.encoded(witness))
        with pytest.raises(ValueError, match='PRECLAIM'):
            trial.prepare()
        assert not trial.control.exists()
    finally:
        gc.collect()
        database.write_bytes(original_raw)
