"""SYNTHETIC signed fixtures only. These tests do not qualify a real model."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import socket
import time
from pathlib import Path

import pytest

from youtube_intel import acoustic_qualification as q
from youtube_intel import offline_transcription as offline
from youtube_intel.acoustic_scoring import coverage, score, utterance_recalls


def load_tool():
    path = Path(__file__).resolve().parents[2] / 'scripts/validation/adopt_verified_asr.py'
    spec = importlib.util.spec_from_file_location('asr_verified_adoption', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino)
        for p in root.rglob('*') if p.is_file()}


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    tool = load_tool()
    monkeypatch.setattr(offline, 'run_bounded', lambda *args, **kwargs: pytest.fail('model/subprocess execution forbidden in adoption fixtures'))
    monkeypatch.setattr(socket.socket, 'connect', lambda *args, **kwargs: pytest.fail('network forbidden in adoption fixtures'))
    donor = tmp_path / 'SYNTHETIC_DONOR_NOT_REAL_QUALIFICATION'
    donor.mkdir()
    model = tmp_path / 'SYNTHETIC_MODEL_NOT_WEIGHTS'
    model.mkdir()
    (model / 'model-origin.json').write_text('{}')
    corpus = json.loads(tool.CORPUS.read_bytes())['samples']
    samples = []
    for case in corpus:
        source = donor / (case['id'] + '.synthetic-media')
        source.write_bytes(('SYNTHETIC_NOT_ACOUSTIC_MEDIA:' + case['id']).encode())
        case['source'] = str(source)
        case['sha256'] = tool.digest(source.read_bytes())
        negative = case.get('negative', False)
        guard = ('NOISE_ONLY' if 'noise' in case['id'] else 'NO_SIGNAL') if negative else 'DECODE'
        raw = {'language': 'en', 'segments': [] if negative else [{'start': r['start'], 'end': r['end'], 'text': r['text']} for r in case['speech_regions']],
            'native_chunks': [{'guard': guard}], 'acoustic_guard': guard}
        raw_bytes = q.canonical(raw)
        (donor / (case['id'] + '.raw.json')).write_bytes(raw_bytes)
        measured = {'id': case['id'], 'source_sha256': case['sha256'], 'passed': True, 'raw_sha256': tool.digest(raw_bytes),
            'product_wall_seconds': 1., 'status': {'status': 'FAILED' if negative else 'READY'},
            'trusted_timed_transcript': not negative, 'summary': not negative, 'evidence_resolves': not negative,
            'decoder_invocations': 0 if negative else 1, 'acoustic_guard': guard}
        if negative:
            measured['no_authority'] = True
        else:
            transcript = offline.validate_result(raw_bytes, duration_seconds=case['duration_seconds'], provenance='SYNTHETIC')
            text = ' '.join(s['text'] for s in raw['segments'])
            measured.update(score=score(case['expected'], text, case['language']),
                recalls=utterance_recalls([r['text'] for r in case['speech_regions']], text, case['language']),
                coverage=coverage([(r['start'],r['end']) for r in case['speech_regions']], [(r['start'],r['end']) for r in raw['segments']]),
                cues=[{'start_ms': c.start_ms, 'end_ms': c.end_ms, 'text': c.text} for c in transcript.cues])
        samples.append(measured)
    frozen = donor / 'SYNTHETIC_FROZEN_CORPUS.json'
    frozen.write_bytes(q.canonical({'samples': corpus}))
    identity = {'model_digest': tool.MODEL_IDENTITY, 'runtime': 'SYNTHETIC_RUNTIME', 'profile': 'SYNTHETIC_PROFILE'}
    monkeypatch.setattr(q, 'current_tuple', lambda *args: copy.deepcopy(identity))
    monkeypatch.setattr(q, 'machine_binding', lambda key: tool.digest(b'SYNTHETIC_MACHINE:' + key))
    monkeypatch.setattr(offline, 'model_identity', lambda path: identity['model_digest'])
    report = {'verdict': 'PASSED', 'qualification_tuple': copy.deepcopy(identity), 'profile': offline.PROFILE,
        'samples': samples, 'offline': True, 'owner_data_access': False, 'cloud_dispatches': 0, 'source_uploads': 0}
    evidence = tool._replay_product(report, corpus, frozen.read_bytes())
    assert q.evaluate(evidence) == 'PASSED'
    report['evidence'] = evidence.model_dump(mode='json')
    audit = q.canonical(report)
    machine = donor / '.local-transcription'
    q.seal_record(machine, identity, evidence=evidence, audit=audit)
    monkeypatch.setattr(tool, 'DONOR', donor)
    monkeypatch.setattr(tool, 'MODEL', model)
    monkeypatch.setattr(tool, 'CORPUS', frozen)
    monkeypatch.setattr(tool, 'AUDIT_SHA256', tool.digest(audit))
    monkeypatch.setattr(tool, 'DONOR_IDENTITY', q.qualification_status(machine, identity)['identity'])
    destination = tmp_path / 'fresh-owned-destination'
    destination.mkdir()
    return tool, donor, model, destination, identity


def test_proposal_reads_only_and_requires_exact_explicit_approval(fixture):
    tool, donor, model, destination, _ = fixture
    before = inventory(donor)
    proposal = tool.propose(destination)
    assert proposal == tool.propose(destination)
    assert proposal['new_model_invocations'] == 0
    assert proposal['operation'] == 'ADOPT_EXISTING_REAL_17_CASE_EVIDENCE'
    assert not list(destination.iterdir()) and inventory(donor) == before
    with pytest.raises(ValueError, match='approval'):
        tool.apply(destination, 'caller-qualified-true')
    assert not list(destination.iterdir())


def test_same_tuple_adoption_uses_new_seal_preserves_sources_and_is_idempotent(fixture):
    tool, donor, _, destination, identity = fixture
    before = inventory(donor)
    proposal = tool.propose(destination)
    result = tool.apply(destination, proposal['proposal_sha256'])
    root = destination / '.local-transcription'
    assert q.qualification_status(root, identity)['production_eligible']
    assert result['qualification']['identity'] != tool.DONOR_IDENTITY
    assert (root / 'qualification.seal').read_bytes() != (donor / '.local-transcription/qualification.seal').read_bytes()
    assert (root / ('qualification/' + tool.AUDIT_SHA256 + '.json')).read_bytes() == (donor / ('.local-transcription/qualification/' + tool.AUDIT_SHA256 + '.json')).read_bytes()
    adoption = json.loads((root / 'adoption.json').read_bytes())
    assert adoption['is_new_model_run'] is False and adoption['new_model_invocations'] == 0
    assert adoption['proposal']['source']['qualification_identity'] == tool.DONOR_IDENTITY
    installed = inventory(destination)
    directories = {str(p.relative_to(destination)): (p.stat().st_ino, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
        for p in destination.rglob('*') if p.is_dir()}
    assert tool.apply(destination, proposal['proposal_sha256']) == result
    assert {str(p.relative_to(destination)): (p.stat().st_ino, p.stat().st_mtime_ns, p.stat().st_ctime_ns)
        for p in destination.rglob('*') if p.is_dir()} == directories
    assert inventory(destination) == installed and inventory(donor) == before
    assert not (destination / 'data').exists() and not (destination / 'state.sqlite3').exists()


@pytest.mark.parametrize('dimension', ['model_digest', 'runtime', 'profile'])
def test_material_tuple_changes_are_refused_without_destination_writes(fixture, dimension):
    tool, _, _, destination, identity = fixture
    identity[dimension] = 'CHANGED_SYNTHETIC_TUPLE'
    with pytest.raises(ValueError):
        tool.propose(destination)
    assert not list(destination.iterdir())


@pytest.mark.parametrize('damage', ['missing-raw', 'raw', 'audit', 'signature', 'partial', 'frozen', 'source'])
def test_missing_tampered_and_partial_chains_remain_closed(fixture, damage):
    tool, donor, _, destination, _ = fixture
    raw = donor / 'english-clean.raw.json'
    record = donor / '.local-transcription/qualification.json'
    if damage == 'missing-raw':
        raw.unlink()
    elif damage == 'raw':
        raw.write_bytes(b'{}')
    elif damage == 'audit':
        (donor / ('.local-transcription/qualification/' + tool.AUDIT_SHA256 + '.json')).write_bytes(b'{}')
    elif damage in {'signature', 'partial'}:
        value = json.loads(record.read_bytes())
        if damage == 'signature':
            value['signature'] = '0' * 64
        else:
            value['body']['evidence']['samples'].pop()
        record.write_bytes(q.canonical(value))
    elif damage == 'frozen':
        tool.CORPUS.write_bytes(b'{"samples":[]}')
    else:
        (donor / 'english-clean.synthetic-media').write_bytes(b'tamper')
    with pytest.raises((ValueError, OSError)):
        tool.propose(destination)
    assert not list(destination.iterdir())


@pytest.mark.parametrize('target', ['raw', 'audit', 'seal', 'destination'])
@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_linked_evidence_and_destination_are_refused(fixture, tmp_path, target, kind):
    tool, donor, _, destination, _ = fixture
    paths = {'raw': donor / 'english-clean.raw.json', 'audit': donor / ('.local-transcription/qualification/' + tool.AUDIT_SHA256 + '.json'),
        'seal': donor / '.local-transcription/qualification.seal', 'destination': destination / '.local-transcription'}
    path = paths[target]
    if target == 'destination':
        if kind == 'hardlink':
            root = path
            root.mkdir()
            source = tmp_path / 'lock-file'
            source.write_bytes(b'lock')
            source.chmod(0o600)
            os.link(source, root / 'worker.lock')
        else:
            path.symlink_to(donor / '.local-transcription', target_is_directory=True)
    else:
        other = path.with_suffix(path.suffix + '.original')
        path.rename(other)
        if kind == 'symlink':
            path.symlink_to(other)
        else:
            os.link(other, path)
    with pytest.raises((ValueError, OSError)):
        proposal = tool.propose(destination)
        tool.apply(destination, proposal['proposal_sha256'])


@pytest.mark.parametrize('damage', ['unknown-record', 'model-selection', 'unknown-directory', 'empty-qualification', 'empty-evidence', 'other-owner', 'writable-parent', 'relative-parent'])
def test_unsafe_or_unknown_destination_is_preserved(fixture, monkeypatch, damage):
    tool, donor, _, destination, _ = fixture
    root = destination / '.local-transcription'
    root.mkdir()
    if damage == 'unknown-record':
        (root / 'qualification.json').write_bytes(b'{"state":"PASSED"}')
    elif damage == 'model-selection':
        (root / 'model.json').write_bytes(b'{}')
    elif damage == 'unknown-directory':
        (root / 'unrecognized-empty').mkdir()
    elif damage in {'empty-qualification', 'empty-evidence'}:
        (root / damage.removeprefix('empty-')).mkdir()
    elif damage == 'other-owner':
        monkeypatch.setattr(tool.os, 'getuid', lambda: -1)
    elif damage == 'writable-parent':
        destination.chmod(0o777)
    before = inventory(destination)
    with pytest.raises((ValueError, OSError)):
        proposal = tool.propose(Path('relative') if damage == 'relative-parent' else destination)
        tool.apply(destination, proposal['proposal_sha256'])
    assert inventory(destination) == before


@pytest.mark.parametrize('interrupted_file', ['evidence/english-clean.raw.json', 'model.json', 'qualification.json'])
def test_interrupted_publication_is_closed_then_resumes_exact_same_proposal(fixture, monkeypatch, interrupted_file):
    tool, _, _, destination, identity = fixture
    proposal = tool.propose(destination)
    original = tool.write_managed
    writes = []
    def fail_before_qualification(root, name, raw):
        if root == destination / '.local-transcription':
            writes.append(name)
            if name == interrupted_file:
                raise OSError('SYNTHETIC interruption before final admission receipt')
        return original(root, name, raw)
    monkeypatch.setattr(tool, 'write_managed', fail_before_qualification)
    with pytest.raises(OSError, match='interruption'):
        tool.apply(destination, proposal['proposal_sha256'])
    root = destination / '.local-transcription'
    assert q.qualification_status(root, identity)['state'] == 'NOT_TESTED'
    assert writes[-1] == interrupted_file
    before = inventory(root)
    monkeypatch.setattr(tool, 'write_managed', original)
    result = tool.apply(destination, proposal['proposal_sha256'])
    assert result['qualification']['production_eligible']
    assert all(inventory(root)[name] == value for name, value in before.items())


def test_conflicting_partial_file_and_incomplete_stage_are_retained(fixture, monkeypatch):
    tool, _, _, destination, _ = fixture
    proposal = tool.propose(destination)
    stage = destination / ('.asr-adoption-' + proposal['proposal_sha256'])
    stage.mkdir()
    (stage / 'diagnostic.txt').write_bytes(b'SYNTHETIC interrupted issuer before complete staging')
    before = inventory(destination)
    with pytest.raises((ValueError, OSError)):
        tool.apply(destination, proposal['proposal_sha256'])
    assert inventory(destination) == before


def test_runtime_baseline_worker_lock_and_empty_temporary_directory_are_preserved(fixture):
    tool, _, _, destination, _ = fixture
    root = destination / '.local-transcription'
    root.mkdir()
    (root / 'worker.lock').touch(mode=0o600)
    (root / 'temporary').mkdir()
    before = (root / 'worker.lock').stat()
    result = tool.apply(destination, tool.propose(destination)['proposal_sha256'])
    assert result['qualification']['production_eligible']
    assert (root / 'worker.lock').stat().st_ino == before.st_ino
    assert (root / 'temporary').is_dir()


def test_ordinary_product_reads_installed_receipt_without_executor_injection(fixture, monkeypatch):
    tool, _, model, destination, identity = fixture
    tool.apply(destination, tool.propose(destination)['proposal_sha256'])
    def capability(executor):
        assert executor.model_path == model
        return executor.qualified_capability(offline.TranscriptionCapability('READY', True, True, True, True,
            model_identity=identity['model_digest'], execution_identity='SYNTHETIC_COMPATIBILITY_ONLY'))
    monkeypatch.setattr(offline.MlxTimedExecutor, 'capability', capability)
    from conftest import _load_module

    from youtube_intel.config import AppConfig, AppSettings, load_settings
    from youtube_intel.local_api import ApiError
    from youtube_intel.runtime_composition import build_local_source_run_runtime

    monkeypatch.setattr('youtube_intel.runtime_composition.local_models', lambda *args: {'models': []})
    monkeypatch.setattr('youtube_intel.runtime_composition.local_runtime_version', lambda *args: {})
    monkeypatch.setattr('youtube_intel.deep_analysis_activation._local_probe', lambda *args: 'MODEL_UNAVAILABLE')
    def unrelated_local_discovery(transport, path, **kwargs):
        assert kwargs.get('method') == 'GET' and path in {'/api/tags', '/api/version'}
        return {'models': []} if path == '/api/tags' else {}
    monkeypatch.setattr('youtube_intel.distillation.OllamaLocalDistillationTransport._request', unrelated_local_discovery)
    for name in ('owned-vault', 'logs', 'templates'):
        (destination / name).mkdir()
    values = load_settings(tool.REPO / 'config/settings.example.yaml').model_dump()
    values['storage']['vault_root'] = str(destination / 'owned-vault')
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    store = _load_module('test_qa_launch_isolation').FakeStore
    runtime = build_local_source_run_runtime(config=config, project_root=destination,
        database=destination / 'owned-test.sqlite3', credential_store=store(), bigmodel_credential_store=store(),
        allow_environment_credentials=False, allow_cloud_execution=False)
    app = runtime.application
    app.handle('GET', '/api/v1/local/transcription/capability')
    jobs = app._transcription_jobs
    assert jobs._injected is False
    deadline = time.monotonic() + 5
    while jobs.capability()['checking']:
        assert time.monotonic() < deadline
        time.sleep(.01)
    assert jobs.capability()['qualification_state'] == 'PASSED'
    assert jobs.capability()['production_eligible'] is True
    with pytest.raises(ApiError):
        app.handle('PUT', '/api/v1/local/transcription/model', b'{"model_path":"/fake","qualified":true}')


def test_live_worker_slot_refuses_installation_without_changing_existing_files(fixture):
    import fcntl
    tool, _, _, destination, _ = fixture
    root = destination / '.local-transcription'
    root.mkdir()
    lock = root / 'worker.lock'
    lock.touch(mode=0o600)
    proposal = tool.propose(destination)
    before = inventory(destination)
    with lock.open('rb') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            tool.apply(destination, proposal['proposal_sha256'])
    assert inventory(destination) == before


@pytest.mark.parametrize('damage', ['raw', 'raw-and-manifest', 'qualification', 'seal', 'extra-file', 'partial-conflict'])
def test_staged_or_partial_destination_tampering_refuses_before_any_further_write(fixture, monkeypatch, damage):
    tool, _, _, destination, _ = fixture
    proposal = tool.propose(destination)
    original = tool.write_managed
    def stop_publish(root, name, raw):
        if root == destination / '.local-transcription' and name == 'qualification.json':
            raise OSError('synthetic final-publication stop')
        return original(root, name, raw)
    monkeypatch.setattr(tool, 'write_managed', stop_publish)
    with pytest.raises(OSError):
        tool.apply(destination, proposal['proposal_sha256'])
    monkeypatch.setattr(tool, 'write_managed', original)
    stage = destination / ('.asr-adoption-' + proposal['proposal_sha256'])
    if damage in {'raw', 'raw-and-manifest'}:
        path = stage / 'evidence/english-clean.raw.json'
        path.write_bytes(b'{}')
        if damage == 'raw-and-manifest':
            manifest = json.loads((stage / 'adoption.json').read_bytes())
            manifest['files']['evidence/english-clean.raw.json'] = tool.digest(b'{}')
            (stage / 'adoption.json').write_bytes(q.canonical(manifest))
    elif damage == 'qualification':
        (stage / 'qualification.json').write_bytes(b'{}')
    elif damage == 'seal':
        (stage / 'qualification.seal').write_bytes(b'x' * 32)
    elif damage == 'extra-file':
        (stage / 'unknown-file').write_bytes(b'unknown')
    else:
        (destination / '.local-transcription/model.json').write_bytes(b'{}')
    before = inventory(destination)
    with pytest.raises((ValueError, OSError, KeyError)):
        tool.apply(destination, proposal['proposal_sha256'])
    assert inventory(destination) == before


def test_other_machine_and_raw_caller_report_cannot_grant_qualification(fixture, monkeypatch):
    tool, _, _, destination, _ = fixture
    with pytest.raises(TypeError):
        tool.propose(destination, report={'verdict': 'PASSED'})
    monkeypatch.setattr(q, 'machine_binding', lambda key: 'other-machine')
    with pytest.raises(ValueError, match='signature'):
        tool.propose(destination)
    assert not list(destination.iterdir())


@pytest.mark.parametrize('changed_field', ['st_dev', 'st_ino'])
def test_remount_number_is_transient_but_inode_changes_remain_conflicts(fixture, monkeypatch, changed_field):
    tool, _, _, destination, _ = fixture
    proposal = tool.propose(destination)
    installed = tool.apply(destination, proposal['proposal_sha256'])
    before = inventory(destination)
    original_lstat = Path.lstat
    class ChangedMountMetadata:
        def __init__(self, original):
            self.original = original
        def __getattr__(self, name):
            value = getattr(self.original, name)
            return value + 17 if name == changed_field else value
    monkeypatch.setattr(Path, 'lstat', lambda path: ChangedMountMetadata(original_lstat(path)))
    if changed_field == 'st_dev':
        assert tool.propose(destination) == proposal
        assert tool.apply(destination, proposal['proposal_sha256']) == installed
    else:
        with pytest.raises(ValueError):
            tool.apply(destination, proposal['proposal_sha256'])
    assert inventory(destination) == before
