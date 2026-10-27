"""Offline public diagnostic package tests; no native store or provider."""

import builtins
import importlib.util
import io
import json
import os
import sqlite3
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/bigmodel_public_first_case'
STOCK_SHA256 = 'f12f59025ef423fb0a3b6b0bd74e33b46846d481879bf8cc431d5c360209065f'


def unpack_public_stock(module, stock):
    """Bounded extraction of the fixed public fixture, never a user archive."""
    archive = FIXTURE / 'stock.zip'
    assert archive.stat().st_size < 1024 * 1024
    assert module.sha(archive.read_bytes()) == STOCK_SHA256
    manifest = json.loads((FIXTURE / 'manifest.json').read_bytes())
    expected = {item['path']: item for item in manifest['files']}
    with ZipFile(archive) as zipped:
        entries = zipped.infolist()
        assert len(entries) == len(expected) == 23
        assert len({entry.filename for entry in entries}) == len(entries)
        assert sum(entry.file_size for entry in entries) <= 8 * 1024 * 1024
        # Validate the whole inventory before creating any extracted file.
        for entry in entries:
            name = PurePosixPath(entry.filename)
            assert not name.is_absolute() and '\\' not in entry.filename
            assert all(part not in {'', '.', '..'} for part in entry.filename.split('/'))
            assert stat.S_ISREG(entry.external_attr >> 16)
            assert entry.filename in expected and entry.file_size <= 6 * 1024 * 1024
            assert entry.file_size == expected[entry.filename]['size']
        for entry in entries:
            raw = zipped.read(entry)
            assert module.sha(raw) == expected[entry.filename]['sha256']
            destination = stock / entry.filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(raw)
    # Standard SQLite dump preserves all original rows/schema without free pages.
    with sqlite3.connect(stock / 'state.sqlite3') as target:
        target.executescript((stock / 'state.sql').read_text())
        assert target.execute('PRAGMA user_version').fetchone() == (42,)
    (stock / 'state.sql').unlink()


@pytest.fixture
def case(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'scripts/qualify_bigmodel_public_first_case.py'
    spec = importlib.util.spec_from_file_location('bigmodel_first_case', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    stock = tmp_path / 'stock'
    stock.mkdir()
    blocked_source = str(module.SOURCE)
    # Actively deny the original absolute location, including in clean checkouts.
    # Guard Path/builtin reads, SQLite URIs, directory traversal and low-level opens.
    def deny_external(original):
        def guarded(path, *args, **kwargs):
            if blocked_source in str(path):
                raise PermissionError('Root-owned runtime stock forbidden in unit tests')
            return original(path, *args, **kwargs)
        return guarded
    for owner, name in [(builtins, 'open'), (io, 'open'), (sqlite3, 'connect'),
            (os, 'open'), (os, 'stat'), (os, 'lstat'), (os, 'listdir'), (os, 'scandir')]:
        monkeypatch.setattr(owner, name, deny_external(getattr(owner, name)))
    with pytest.raises(PermissionError):
        (module.SOURCE / 'initial.json').read_bytes()
    with pytest.raises(PermissionError):
        sqlite3.connect((module.SOURCE / 'state.sqlite3').as_uri() + '?mode=ro', uri=True)
    unpack_public_stock(module, stock)
    monkeypatch.setattr(module, 'SOURCE', stock)
    monkeypatch.setattr(module, 'PACKAGE', tmp_path / 'package')
    monkeypatch.setattr(module, 'ATTEMPT', tmp_path / 'attempt.json')
    monkeypatch.setattr(module, 'pricing_day', lambda: '2026-10-28')
    monkeypatch.setattr(module, 'MacOSBigModelQACredentialStore', lambda: pytest.fail('native forbidden in author tests'))
    monkeypatch.setattr(module, '_bigmodel_chat_completions_http_transport', lambda *a: pytest.fail('real HTTP forbidden'))
    return module


class Store:
    calls = 0
    def get(self):
        self.calls += 1
        return 'synthetic-secret-never-persist-xy98'


def review(case):
    case.write_once(case.PACKAGE / 'review.json', case.canonical({
        'decision': 'APPROVE_ONE_PUBLIC_DIAGNOSTIC',
        'prepared_sha256': case.sha((case.PACKAGE / 'prepared.json').read_bytes()),
        'reviewer': 'offline-independent-reviewer', 'review_commit': 'a' * 40,
        'maximum_calls': 1, 'cost_authorization': 'ANTICIPATED_FREE_EXACT_MODEL_ONLY'}))


def answer(request, *, thought=False, no_new=False):
    evidence = json.loads(request['messages'][2]['content'].split('=', 1)[1])['evidence']
    refs = [{k: item[k] for k in ('evidence_id', 'start_ms', 'end_ms')} for item in evidence]
    if no_new:
        return json.dumps({'result': 'NO_NEW_INTELLIGENCE', 'evidence': refs})
    return json.dumps({'core_conclusion': ('<think>PRIVATE_REASONING_MARKER</think>' if thought else
        'The speakers describe mathematical exploration as a provisional research aid; human mathematical verification remains necessary.'),
        'user_relevant_information': ['Distinguish reported progress from independently verified correctness.'],
        'important_new_information': [], 'meaningful_details': [], 'filtered_noise': [],
        'claim_kind': 'SYSTEM_INFERENCE', 'evidence': [dict(item, stance='supporting') for item in refs]})


def wire(case, calls, *, thought=False, no_new=False, status=200):
    def fake(request, key, timeout, retries):
        calls.append(1)
        assert key == 'synthetic-secret-never-persist-xy98' and (timeout, retries) == (300.0, 0)
        assert key not in str(request)
        body = {'model': 'glm-4.7-flash', 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': answer(request, thought=thought, no_new=no_new),
                'reasoning_content': 'PRIVATE_REASONING_MARKER never retain opaque private channel'}}],
            'usage': {'prompt_tokens': 111, 'completion_tokens': 42, 'total_tokens': 153}}
        return case._BigModelWireResponse(status, json.dumps(body).encode())
    return fake


def test_prepare_is_readonly_and_matches_frozen_public_corpus(case):
    before = case.sql_snapshot(case.SOURCE)
    p = case.prepare()
    assert case.sql_snapshot(case.SOURCE) == before == case.sql_snapshot(case.PACKAGE)
    assert len(p['data']) == 19 and len(before['tables']) == 81
    assert p['input_hash'] == '4d4b30739519803c87fecd23b991b3f221a508512ecf2f63520f45c617c0150e'
    assert len((case.PACKAGE / 'request.json').read_bytes()) == 4224
    assert not case.ATTEMPT.exists()
    case.validate()


@pytest.mark.parametrize('mode', ['positive', 'no-new', 'thought', '429', '202', 'timeout', 'wrong-model', 'bad-schema'])
def test_one_execution_preserves_history_and_redacts_private_content(case, mode):
    p = case.prepare()
    review(case)
    store, calls = Store(), []
    fake = wire(case, calls, thought=mode == 'thought', no_new=mode == 'no-new',
        status=int(mode) if mode in {'429', '202'} else 200)
    if mode == 'timeout':
        def fake(*args):
            calls.append(1)
            raise TimeoutError('synthetic-secret-never-persist-xy98 PRIVATE_REASONING_MARKER')
    if mode in {'wrong-model', 'bad-schema'}:
        original = fake
        def fake(*args):
            response = original(*args)
            body = json.loads(response.body)
            if mode == 'wrong-model':
                body['model'] = 'glm-4.7-flashx'
            else:
                body['choices'][0]['message']['content'] = '{"invalid_schema":true}'
            return case._BigModelWireResponse(200, json.dumps(body).encode())
    result = case.execute(store=store, wire=fake)
    assert store.calls == 1 and calls == [1]
    assert result['production_qualified'] is False and result['actual_bill'] == 'UNKNOWN'
    assert result['usage']['cost_microunits'] is None
    assert result['diagnostic'] == ('POSITIVE_AWAITING_INDEPENDENT_REVIEW' if mode == 'positive' else 'FAIL_STOP')
    saved = (case.PACKAGE / 'result.json').read_text()
    with sqlite3.connect(case.PACKAGE / 'state.sqlite3') as db:
        sql = '\n'.join(db.iterdump())
    assert 'synthetic-secret-never-persist-xy98' not in saved + sql
    assert 'PRIVATE_REASONING_MARKER' not in saved + sql
    if mode == 'thought':
        assert result['status'] == 'REJECTED_OUTPUT' and result['public_final'] is None
    assert case.data_manifest(case.PACKAGE / 'data') == p['data']
    with pytest.raises((case.Refused, FileExistsError)):
        case.execute(store=store, wire=fake)
    assert store.calls == 1 and calls == [1] and case.ATTEMPT.exists()


@pytest.mark.parametrize('target', ['price.txt', 'request.json', 'verified-input.json', 'oracle.json', 'data', 'profile', 'review', 'destination', 'code'])
def test_tampering_refuses_before_key_and_wire(case, target):
    case.prepare()
    review(case)
    if target in {'profile', 'destination', 'code'}:
        p = case.read(case.PACKAGE / 'prepared.json')
        p[target] = 'tampered'
        (case.PACKAGE / 'prepared.json').write_bytes(case.canonical(p))
    elif target == 'data':
        path = next(p for p in (case.PACKAGE / 'data').rglob('*') if p.is_file())
        path.write_bytes(b'tampered')
    elif target == 'review':
        r = case.read(case.PACKAGE / 'review.json')
        r['maximum_calls'] = 2
        (case.PACKAGE / 'review.json').write_bytes(case.canonical(r))
    else:
        (case.PACKAGE / target).write_bytes(b'tampered')
    store, calls = Store(), []
    with pytest.raises((case.Refused, ValueError, TypeError)):
        case.execute(store=store, wire=wire(case, calls))
    assert store.calls == 0 and calls == [] and not case.ATTEMPT.exists()


def test_concurrent_execute_is_at_most_one_attempt(case):
    case.prepare()
    review(case)
    store, calls = Store(), []
    def run(_):
        try:
            return case.execute(store=store, wire=wire(case, calls))
        except (case.Refused, FileExistsError):
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [1, 2]))
    assert sum(r is not None for r in results) == 1
    assert store.calls == 1 and calls == [1]


def test_interrupted_attempt_never_replays_after_restart(case):
    case.prepare()
    review(case)
    store, calls = Store(), []
    def interrupted(*args):
        calls.append(1)
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        case.execute(store=store, wire=interrupted)
    assert case.ATTEMPT.exists()
    with pytest.raises((case.Refused, FileExistsError)):
        case.execute(store=store, wire=wire(case, calls))
    assert store.calls == 1 and calls == [1]


def test_stale_price_day_refuses_before_key_or_attempt(case, monkeypatch):
    case.prepare()
    review(case)
    monkeypatch.setattr(case, 'pricing_day', lambda: '2026-10-29')
    store, calls = Store(), []
    with pytest.raises(case.Refused):
        case.execute(store=store, wire=wire(case, calls))
    assert store.calls == 0 and calls == [] and not case.ATTEMPT.exists()


def test_actual_backup_restore_keeps_all_sql_data_and_consumed_attempt(case):
    from youtube_intel.backup_restore import BackupRestoreService
    case.prepare()
    review(case)
    store, calls = Store(), []
    case.execute(store=store, wire=wire(case, calls))
    before = case.sql_snapshot(case.PACKAGE)
    files = case.data_manifest(case.PACKAGE / 'data')
    service = BackupRestoreService(database=case.PACKAGE / 'state.sqlite3', data_root=case.PACKAGE / 'data')
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    staged = service.stage_restore(archive.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    assert case.sql_snapshot(case.PACKAGE) == before
    assert case.data_manifest(case.PACKAGE / 'data') == files
    with pytest.raises((case.Refused, FileExistsError)):
        case.execute(store=store, wire=wire(case, calls))
    assert store.calls == 1 and calls == [1] and case.ATTEMPT.exists()


def test_invalid_cli_never_echoes_accidental_key():
    path = Path(__file__).resolve().parents[2] / 'scripts/qualify_bigmodel_public_first_case.py'
    result = subprocess.run([sys.executable, str(path), 'execute', '--key', 'synthetic-cli-secret'], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'synthetic-cli-secret' not in result.stdout + result.stderr


def test_normal_production_authority_and_budget_stay_closed(case):
    from youtube_intel.runtime_composition import ProductionDistillationBudget
    case.prepare()
    _, command, value, _ = case.validate()
    adapter = case.Adapter(authorization=case.CloudDistillationAuthorization(), credential_resolver=case.never)
    assert not adapter.is_authorized_for_normal_production(value)
    assert not ProductionDistillationBudget().check(command).allowed
