"""Fixed public capsule offline tests; no Root D/native/provider access."""
import builtins
import importlib.util
import io
import json
import os
import socket
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from conftest import _load_module

stock_support = _load_module('test_bigmodel_public_first_case')


def _module():
    path = Path(__file__).resolve().parents[2] / 'scripts/qualify_bigmodel_grounding_v2_public_case.py'
    spec = importlib.util.spec_from_file_location('grounding_v2_capsule', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def case(tmp_path, monkeypatch):
    module = _module()
    blocked = str(module.SOURCE)
    def deny_external(original):
        def guarded(path, *args, **kwargs):
            if blocked in str(path):
                raise PermissionError('Root public D forbidden in offline tests')
            return original(path, *args, **kwargs)
        return guarded
    for owner, name in [(builtins, 'open'), (io, 'open'), (sqlite3, 'connect'),
            (os, 'open'), (os, 'stat'), (os, 'lstat'), (os, 'listdir'), (os, 'scandir')]:
        monkeypatch.setattr(owner, name, deny_external(getattr(owner, name)))
    monkeypatch.setattr(socket, 'create_connection', lambda *_a, **_kw: pytest.fail('network forbidden'))
    with pytest.raises(PermissionError):
        (module.SOURCE / 'initial.json').read_bytes()
    with pytest.raises(PermissionError):
        sqlite3.connect((module.SOURCE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True)
    stock = tmp_path / 'stock'
    stock.mkdir()
    stock_support.unpack_public_stock(module, stock)
    monkeypatch.setattr(module, 'SOURCE', stock)
    monkeypatch.setattr(module, 'PACKAGE', tmp_path / 'package')
    monkeypatch.setattr(module, 'ATTEMPT', tmp_path / 'attempt.json')
    monkeypatch.setattr(module, 'pricing_day', lambda: '2026-10-28')
    monkeypatch.setattr(module, 'MacOSBigModelQACredentialStore', lambda: pytest.fail('native forbidden'))
    monkeypatch.setattr(module, '_bigmodel_chat_completions_http_transport', lambda *_: pytest.fail('real wire forbidden'))
    return module


def test_prepare_is_pure_and_preserves_full_unseen_source(case):
    before = case.sql_snapshot(case.SOURCE)
    physical = case.sha((case.SOURCE / 'state.sqlite3').read_bytes())
    files = case.data_manifest(case.SOURCE / 'data')
    p = case.prepare()
    assert case.sql_snapshot(case.SOURCE) == before == case.sql_snapshot(case.PACKAGE)
    assert len(p['data']) == 19 and len(before['tables']) == 81
    assert case.sha((case.SOURCE / 'state.sqlite3').read_bytes()) == physical
    assert case.data_manifest(case.SOURCE / 'data') == files == p['data']
    source = case.read(case.PACKAGE / 'source.json')
    assert len(source['timed_segments']) == 104 and len(source['canonical_evidence']) == 5
    assert len(case.read(case.PACKAGE / 'summary.json')['core_points']) == 5
    assert not case.ATTEMPT.exists()
    case.validate()


SECRET = 'synthetic-v2-public-secret-xy98'
PRIVATE = 'PRIVATE_REASONING_MARKER'


class Store:
    calls = 0
    def get(self):
        self.calls += 1
        return SECRET


def approve(case):
    case.write_once(case.PACKAGE / 'review.json', case.canonical({
        'decision': 'APPROVE_ONE_PUBLIC_DIAGNOSTIC',
        'prepared_sha256': case.sha((case.PACKAGE / 'prepared.json').read_bytes()),
        'reviewer': 'offline-independent-reviewer', 'review_commit': 'a' * 40,
        'maximum_calls': 1, 'cost_authorization': 'ANTICIPATED_FREE_EXACT_MODEL_ONLY'}))


def fake_wire(case, calls, mode='positive'):
    def send(request, key, timeout, retries):
        calls.append(request)
        assert (key, timeout, retries) == (SECRET, 300, 0)
        _, _, value, expected = case.validate(allow_case=True)
        assert request == expected == case.Adapter._request(value)
        assert case.CaptureV2._request(value) == case.Adapter._request(value)
        assert 'Preserve modality' in request['messages'][0]['content']
        source = json.loads(request['messages'][2]['content'].split('=', 1)[1])
        assert set(source) == {'video_id', 'video_title', 'source_display_name', 'evidence'}
        assert len(source['evidence']) == 5
        assert SECRET not in str(request) and 'minimum_substantive_judgment' not in str(request)
        if mode == 'timeout':
            raise TimeoutError(SECRET + PRIVATE)
        if mode == 'interrupt':
            raise KeyboardInterrupt()
        refs = [{k: e[k] for k in ('evidence_id', 'start_ms', 'end_ms')} for e in source['evidence']]
        output = {'core_conclusion': 'Offline synthetic retained judgment; not actual model quality.',
            'user_relevant_information': [], 'important_new_information': [], 'meaningful_details': [],
            'filtered_noise': [], 'claim_kind': 'SYSTEM_INFERENCE',
            'evidence': [dict(item, stance='supporting') for item in refs]}
        if mode == 'no-new':
            output = {'result': 'NO_NEW_INTELLIGENCE', 'evidence': refs}
        elif mode == 'bad-schema':
            output = {'invalid_schema': True}
        elif mode in {'thought', 'key-echo'}:
            output['core_conclusion'] = '<think>' + PRIVATE + '</think>' if mode == 'thought' else SECRET
        body = {'model': 'other-model' if mode == 'wrong-model' else 'glm-4.7-flash',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {
                'role': 'assistant', 'content': json.dumps(output), 'reasoning_content': PRIVATE}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10, 'total_tokens': 30}}
        return case._BigModelWireResponse(int(mode) if mode.isdigit() else 200, json.dumps(body).encode())
    return send


@pytest.mark.parametrize('mode', ['positive', 'no-new', 'thought', 'key-echo', '401', '429', '202', 'timeout', 'wrong-model', 'bad-schema'])
def test_one_fixed_v2_dispatch_and_public_only_fail_stop(case, mode):
    prepared = case.prepare()
    approve(case)
    store, calls = Store(), []
    result = case.execute(store=store, wire=fake_wire(case, calls, mode))
    assert store.calls == 1 and len(calls) == 1
    assert result['production_qualified'] is False and result['actual_bill'] == 'UNKNOWN'
    assert result['usage']['cost_microunits'] is None
    assert result['diagnostic'] == ('POSITIVE_AWAITING_INDEPENDENT_REVIEW' if mode == 'positive' else 'FAIL_STOP')
    saved = (case.PACKAGE / 'result.json').read_text()
    with sqlite3.connect(case.PACKAGE / 'state.sqlite3') as db:
        rows = '\n'.join(db.iterdump())
    assert SECRET not in rows + saved and PRIVATE not in rows + saved
    if mode in {'thought', 'key-echo'}:
        assert result['public_final'] is None and result['status'] == 'REJECTED_OUTPUT'
    assert case.data_manifest(case.PACKAGE / 'data') == prepared['data']
    with pytest.raises((case.Refused, FileExistsError)):
        case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 1 and len(calls) == 1


@pytest.mark.parametrize('target', ['case', 'source', 'oracle.json', 'price.txt', 'data', 'request.json', 'request-body.json',
    'verified-input.json', 'summary.json', 'source.json', 'profile', 'code', 'review', 'destination', 'schema-version'])
def test_tamper_refuses_before_key_or_once(case, target):
    case.prepare()
    approve(case)
    if target in {'case', 'source', 'profile', 'code', 'destination'}:
        p = case.read(case.PACKAGE / 'prepared.json')
        p[target] = 'tampered'
        (case.PACKAGE / 'prepared.json').write_bytes(case.canonical(p))
    elif target == 'data':
        next(p for p in (case.PACKAGE / 'data').rglob('*') if p.is_file()).write_bytes(b'tampered')
    elif target == 'schema-version':
        with sqlite3.connect(case.PACKAGE / 'state.sqlite3') as db:
            db.execute('PRAGMA user_version=0')
    elif target == 'review':
        p = case.read(case.PACKAGE / 'review.json')
        p['maximum_calls'] = 2
        (case.PACKAGE / 'review.json').write_bytes(case.canonical(p))
    else:
        (case.PACKAGE / target).write_bytes(b'tampered')
    store, calls = Store(), []
    with pytest.raises((case.Refused, ValueError, TypeError)):
        case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 0 and calls == [] and not case.ATTEMPT.exists()


def test_once_concurrent_and_hard_interrupt_never_replay(case, monkeypatch):
    case.prepare()
    approve(case)
    store, calls = Store(), []
    def run(_):
        try:
            return case.execute(store=store, wire=fake_wire(case, calls, 'interrupt'))
        except (case.Refused, FileExistsError, KeyboardInterrupt):
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, [1, 2]))
    assert case.ATTEMPT.exists() and store.calls == 1 and len(calls) == 1
    with pytest.raises((case.Refused, FileExistsError)):
        case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 1 and len(calls) == 1
    restarted = _module()
    for name in ['SOURCE', 'PACKAGE', 'ATTEMPT', 'pricing_day']:
        monkeypatch.setattr(restarted, name, getattr(case, name))
    fresh = Store()
    with pytest.raises((case.Refused, FileExistsError)):
        restarted.execute(store=fresh, wire=fake_wire(case, calls))
    assert fresh.calls == 0 and len(calls) == 1


def test_post_key_tamper_stops_before_wire(case):
    case.prepare()
    approve(case)
    class TamperingStore(Store):
        def get(self):
            result = super().get()
            p = case.read(case.PACKAGE / 'prepared.json')
            p['profile'] = 'tampered'
            (case.PACKAGE / 'prepared.json').write_bytes(case.canonical(p))
            return result
    store, calls = TamperingStore(), []
    result = case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 1 and calls == [] and case.ATTEMPT.exists()
    assert result['diagnostic'] == 'FAIL_STOP' and result['status'] != 'PENDING'


def test_expiry_and_normal_gates_remain_closed(case, monkeypatch):
    from youtube_intel.runtime_composition import ProductionDistillationBudget
    case.prepare()
    approve(case)
    _, command, value, _ = case.validate()
    assert not ProductionDistillationBudget().check(command).allowed
    assert not case.Adapter(authorization=case.CloudDistillationAuthorization(), credential_resolver=case.never).is_authorized_for_normal_production(value)
    monkeypatch.setattr(case, 'pricing_day', lambda: '2026-10-29')
    store, calls = Store(), []
    with pytest.raises(case.Refused):
        case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 0 and calls == [] and not case.ATTEMPT.exists()


def test_full_backup_restore_preserves_all_history_data_and_once(case):
    from youtube_intel.backup_restore import BackupRestoreService
    case.prepare()
    approve(case)
    store, calls = Store(), []
    backup = BackupRestoreService(database=case.PACKAGE / 'state.sqlite3', data_root=case.PACKAGE / 'data')
    initial_sql = case.sql_snapshot(case.PACKAGE)
    initial_backup = backup.create_backup()
    initial_archive, _ = backup.backup_download(initial_backup.backup_id)
    initial_bytes = initial_archive.read_bytes()
    case.execute(store=store, wire=fake_wire(case, calls))
    before, data = case.sql_snapshot(case.PACKAGE), case.data_manifest(case.PACKAGE / 'data')
    item = backup.create_backup()
    archive, _ = backup.backup_download(item.backup_id)
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert case.sql_snapshot(case.PACKAGE) == before and case.data_manifest(case.PACKAGE / 'data') == data
    assert len(before['tables']) == 81 and len(data) == 19
    assert case.ATTEMPT.exists()
    with pytest.raises((case.Refused, FileExistsError)):
        case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 1 and len(calls) == 1
    # Restoring the genuinely unspent database must not restore the external attempt.
    staged = backup.stage_restore(initial_bytes)
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert case.sql_snapshot(case.PACKAGE) == initial_sql
    assert case.data_manifest(case.PACKAGE / 'data') == data
    with pytest.raises(FileExistsError):
        case.execute(store=store, wire=fake_wire(case, calls))
    assert store.calls == 1 and len(calls) == 1 and case.ATTEMPT.exists()



def test_code_manifest_includes_imported_helper_and_actual_v2_mro(case):
    from scripts import qualify_bigmodel_public_first_case as first
    before = (first.SOURCE, first.PACKAGE, first.ATTEMPT, first.CASE, first.Adapter)
    prepared = case.prepare()
    for name in ['scripts/qualify_bigmodel_public_first_case.py',
            'scripts/qualify_bigmodel_grounding_v2_public_case.py',
            'src/youtube_intel/distillation.py', str(case.ORACLE.relative_to(case.PROJECT))]:
        assert name in prepared['code']
    assert case.CaptureV2.__mro__[1:3] == (first.Capture, case.Adapter)
    assert case.CaptureV2.profile_projection() == case.Adapter.profile_projection()
    assert before == (first.SOURCE, first.PACKAGE, first.ATTEMPT, first.CASE, first.Adapter)


def test_source_change_is_refused_without_application_writes(case):
    with sqlite3.connect(case.SOURCE / 'state.sqlite3') as db:
        db.execute('UPDATE videos SET title=? WHERE video_id=?', ('Changed public title', case.VIDEO))
    before = case.sql_snapshot(case.SOURCE)
    with pytest.raises(case.Refused):
        case.prepare()
    assert case.sql_snapshot(case.SOURCE) == before
    assert not case.PACKAGE.exists() and not case.ATTEMPT.exists()


def test_invalid_cli_never_echoes_secret_arguments():
    run = subprocess.run([sys.executable, '-m', 'scripts.qualify_bigmodel_grounding_v2_public_case',
        'execute', '--key', 'synthetic-cli-secret'], capture_output=True, text=True)
    assert run.returncode == 2
    assert 'synthetic-cli-secret' not in run.stdout + run.stderr
