"""Adopt the accepted same-machine October 20 ASR evidence, with zero decoding.

Fixed donor/model/audit only. Proposal is read-only. Explicit apply issues a new
machine seal through the existing issuer and publishes qualification last.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.qualify_readiness_asr_product import product_evidence
from youtube_intel import acoustic_qualification as qualification
from youtube_intel import offline_transcription as offline
from youtube_intel.acoustic_scoring import coverage, score, utterance_recalls
from youtube_intel.source_authority import read_managed, write_managed

REPO = Path(__file__).resolve().parents[2]
DONOR = Path('/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/asr-requal-20261020')
MODEL = Path('/Users/developer/Documents/yia-worktrees/v1x-acoustic-qualification/.var/phase9/models/whisper-large-v3-turbo/a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb')
CORPUS = REPO / 'docs/validation/readiness-asr/run03/FROZEN_CORPUS.json'
DONOR_IDENTITY = 'ab0c9eab7749bb2d344bb2db134b8859390e6e5aadcbbe68e6d9391d970cc576'
AUDIT_SHA256 = '694f9e89b73479d2fec6452f21cd9d90ceb2aff66ebfe5089fcb96e65a66805c'
MODEL_IDENTITY = 'sha256:627ea4bff5510683c5919ac35d290ec3cfca957ef74a301ca46e24ec71d34751'
VERSION = 'same-machine-reviewed-asr-adoption-v1'
ROOT_DECISION = 'TASK-READINESS-ASR-VERIFIED-ADOPTION approved 2026-11-05'
_replay_product: Callable[[dict[str, Any], list[dict[str, Any]], bytes], qualification.QualificationEvidence] = product_evidence


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def directory(path: Path) -> os.stat_result:
    if not path.is_absolute() or path.absolute() != path.resolve(strict=True):
        raise ValueError('absolute non-symlink directory required')
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('owned non-writable-by-others directory required')
    return info


def checked_read(path: Path, maximum: int) -> bytes:
    directory(path.parent)
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
        or before.st_uid != os.getuid() or before.st_mode & 0o022):
        raise ValueError('owned single-link regular evidence required')
    raw = read_managed(path.parent, path.name, maximum=maximum)
    if before != path.lstat():
        # Access-time updates are deliberately excluded from the equality below.
        after = path.lstat()
        if (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('evidence changed during read')
    return raw


def file_record(path: Path, raw: bytes) -> dict[str, Any]:
    info = path.lstat()
    # Mount device numbers can change across a normal OS/session restart.
    # Same-read race checks retain them, durable evidence uses path/inode/hash.
    return {'path': str(path), 'sha256': digest(raw), 'size': len(raw),
        'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns, 'inode': info.st_ino}


def verify_source() -> tuple[dict[str, Any], qualification.QualificationEvidence, dict[str, bytes]]:
    directory(DONOR)
    machine = DONOR / '.local-transcription'
    directory(machine)
    origin = json.loads(checked_read(MODEL / 'model-origin.json', 16384))
    identity = qualification.current_tuple(MODEL, offline.model_identity(MODEL), origin)
    if identity['model_digest'] != MODEL_IDENTITY:
        raise ValueError('accepted model identity differs')
    # Read no signing bytes here. Only the original verifier reads the donor key.
    seal_info = (machine / 'qualification.seal').lstat()
    if not stat.S_ISREG(seal_info.st_mode) or seal_info.st_nlink != 1:
        raise ValueError('donor seal must be a single-link regular file')
    record_raw = checked_read(machine / 'qualification.json', 1024 * 1024)
    status = qualification.qualification_status(machine, identity)
    if status != {'state': 'PASSED', 'production_eligible': True, 'identity': DONOR_IDENTITY}:
        raise ValueError('accepted donor current-tuple signature is not valid')
    body = json.loads(record_raw)['body']
    if body['audit_sha256'] != AUDIT_SHA256 or body['tuple'] != identity:
        raise ValueError('accepted donor audit or tuple differs')
    audit_path = machine / 'qualification' / (AUDIT_SHA256 + '.json')
    audit = checked_read(audit_path, 4 * 1024 * 1024)
    report = json.loads(audit)
    corpus_raw = checked_read(CORPUS, 4 * 1024 * 1024)
    corpus = json.loads(corpus_raw)['samples']
    evidence = qualification.QualificationEvidence.model_validate_json(qualification.canonical(body['evidence']))
    if (digest(audit) != AUDIT_SHA256 or report['qualification_tuple'] != identity
        or report['verdict'] != 'PASSED' or report['profile'] != offline.PROFILE
        or report['offline'] is not True or report['owner_data_access'] is not False
        or report['cloud_dispatches'] != 0 or report['source_uploads'] != 0
        or report['evidence'] != evidence.model_dump(mode='json')
        or evidence.corpus_sha256 != digest(corpus_raw)
        or len(corpus) != 17 or len(report['samples']) != 17
        or [s['id'] for s in report['samples']] != [s['id'] for s in corpus]
        or set(s['id'] for s in corpus) != qualification.REQUIRED | qualification.NEGATIVE_REQUIRED
        or _replay_product(report, corpus, corpus_raw) != evidence
        or qualification.evaluate(evidence) != 'PASSED'):
        raise ValueError('complete accepted product evidence differs')
    blobs = {'qualification/' + AUDIT_SHA256 + '.json': audit, 'evidence/FROZEN_CORPUS.json': corpus_raw}
    sources = [file_record(machine / 'qualification.json', record_raw), file_record(audit_path, audit), file_record(CORPUS, corpus_raw)]
    for sample, measured in zip(corpus, report['samples'], strict=True):
        name = sample['id']
        if measured['passed'] is not True or measured['source_sha256'] != sample['sha256']:
            raise ValueError('sample source or verdict differs')
        source_path = Path(sample['source'])
        source = checked_read(source_path, 128 * 1024 * 1024)
        raw_path = DONOR / (name + '.raw.json')
        raw = checked_read(raw_path, offline.MAX_RESULT)
        response = json.loads(raw)
        if (digest(source) != sample['sha256'] or digest(raw) != measured['raw_sha256']
            or sum(c['guard'] == 'DECODE' for c in response['native_chunks']) != measured['decoder_invocations']
            or response['acoustic_guard'] != measured['acoustic_guard']):
            raise ValueError('original source/raw/decoder receipt differs')
        if sample.get('negative'):
            if response['segments'] or measured['decoder_invocations'] != 0:
                raise ValueError('negative control has decoder output')
        else:
            transcript = offline.validate_result(raw, duration_seconds=sample['duration_seconds'], provenance='original-audit-replay')
            text = ' '.join(s['text'] for s in response['segments'])
            if (digest(sample['expected'].encode()) != sample['expected_sha256']
                or score(sample['expected'], text, sample['language']) != measured['score']
                or utterance_recalls([r['text'] for r in sample['speech_regions']], text, sample['language']) != measured['recalls']
                or coverage([(r['start'], r['end']) for r in sample['speech_regions']],
                    [(s['start'], s['end']) for s in response['segments']]) != measured['coverage']
                or [{'start_ms': c.start_ms, 'end_ms': c.end_ms, 'text': c.text} for c in transcript.cues] != measured['cues']):
                raise ValueError('original timing/accuracy/coverage replay differs')
        blobs['evidence/' + name + '.raw.json'] = raw
        sources.extend((file_record(source_path, source), file_record(raw_path, raw)))
    if qualification.qualification_status(machine, identity) != status:
        raise ValueError('donor changed while verifying evidence')
    return {'donor': str(DONOR), 'qualification_identity': DONOR_IDENTITY,
        'audit_sha256': AUDIT_SHA256, 'tuple': identity, 'source_files': sources}, evidence, blobs


def propose(destination_parent: Path) -> dict[str, Any]:
    parent = directory(destination_parent)
    if destination_parent == DONOR or DONOR.is_relative_to(destination_parent) or destination_parent.is_relative_to(DONOR):
        raise ValueError('destination must be separate from donor')
    source, _, blobs = verify_source()
    proposal: dict[str, Any] = {'version': VERSION, 'root_decision': ROOT_DECISION, 'source': source,
        'destination': str(destination_parent / '.local-transcription'),
        'parent': {'inode': parent.st_ino, 'uid': parent.st_uid},
        'files': {name: digest(raw) for name, raw in blobs.items()},
        'model_path': str(MODEL), 'new_model_invocations': 0,
        'operation': 'ADOPT_EXISTING_REAL_17_CASE_EVIDENCE'}
    proposal['proposal_sha256'] = digest(qualification.canonical(proposal))
    root = destination_parent / '.local-transcription'
    stage = destination_parent / ('.asr-adoption-' + proposal['proposal_sha256'])
    baseline = tree_files(root) - {'worker.lock'} if root.exists() or root.is_symlink() else set()
    if stage.exists() or stage.is_symlink():
        validate_stage(stage, proposal, root)
    elif baseline or (root.exists() and any(p.is_dir() and p.name != 'temporary' for p in root.iterdir())):
        raise ValueError('unknown destination state cannot be adopted')
    return proposal


def tree_files(root: Path) -> set[str]:
    directory(root)
    files: set[str] = set()
    for current, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            child = Path(current) / name
            directory(child)
            if str(child.relative_to(root)) not in {'qualification', 'evidence', 'temporary'}:
                raise ValueError('unknown machine-state directory')
            if name == 'temporary' and any(child.iterdir()):
                raise ValueError('temporary work is still present')
        for name in names:
            path = Path(current) / name
            if path == root / 'worker.lock':
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise ValueError('private single-link worker lock required')
            else:
                checked_read(path, 4 * 1024 * 1024)
            files.add(str(path.relative_to(root)))
    return files


def stage_install(stage: Path, proposal: dict[str, Any], evidence: qualification.QualificationEvidence,
    blobs: dict[str, bytes]) -> dict[str, Any]:
    stage.mkdir(mode=0o700)
    for name, raw in blobs.items():
        write_managed(stage, name, raw)
    qualification.seal_record(stage, proposal['source']['tuple'], evidence=evidence,
        audit=blobs['qualification/' + AUDIT_SHA256 + '.json'])
    write_managed(stage, 'model.json', qualification.canonical({'model_path': str(MODEL)}))
    status = qualification.qualification_status(stage, proposal['source']['tuple'])
    if status['state'] != 'PASSED':
        raise ValueError('new independent machine issuer did not verify')
    files = {name: digest(checked_read(stage / name, 4 * 1024 * 1024)) for name in sorted(tree_files(stage))}
    manifest = {'version': VERSION, 'proposal': proposal, 'root_decision': ROOT_DECISION,
        'adopted_at': datetime.now(UTC).isoformat(), 'original_experiment': str(DONOR),
        'is_new_model_run': False, 'new_model_invocations': 0, 'files': files,
        'destination_qualification_identity': status['identity']}
    write_managed(stage, 'adoption.json', qualification.canonical(manifest))
    return manifest


def validate_stage(stage: Path, proposal: dict[str, Any], root: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(checked_read(stage / 'adoption.json', 1024 * 1024))
    if (manifest['version'] != VERSION or manifest['proposal'] != proposal
        or manifest['root_decision'] != ROOT_DECISION or manifest['original_experiment'] != str(DONOR)
        or manifest['is_new_model_run'] is not False or manifest['new_model_invocations'] != 0
        or manifest['destination_qualification_identity'] == DONOR_IDENTITY):
        raise ValueError('staging proposal conflict; evidence retained')
    expected = manifest['files']
    source_files = proposal['files']
    if (set(expected) != set(source_files) | {'qualification.seal', 'qualification.json', 'model.json'}
        or any(expected[name] != wanted for name, wanted in source_files.items())
        or expected['model.json'] != digest(qualification.canonical({'model_path': str(MODEL)}))
        or tree_files(stage) != set(expected) | {'adoption.json'}):
        raise ValueError('staging file set or source digests differ')
    for name, wanted in expected.items():
        if digest(checked_read(stage / name, 4 * 1024 * 1024)) != wanted:
            raise ValueError('staging evidence changed')
    baseline = tree_files(root) - {'worker.lock'} if root.exists() else set()
    if not baseline <= set(expected) | {'adoption.json'}:
        raise ValueError('unknown destination files')
    for name in baseline:
        if checked_read(root / name, 4 * 1024 * 1024) != checked_read(stage / name, 4 * 1024 * 1024):
            raise ValueError('destination conflict; existing files retained')
    original = json.loads(checked_read(DONOR / '.local-transcription/qualification.json', 1024 * 1024))['body']
    installed = json.loads(checked_read(stage / 'qualification.json', 1024 * 1024))['body']
    if any(installed[key] != original[key] for key in ('version', 'tuple', 'state', 'evidence', 'audit_sha256')):
        raise ValueError('staged measured evidence differs from donor')
    if qualification.qualification_status(stage, proposal['source']['tuple']) != {
        'state': 'PASSED', 'production_eligible': True, 'identity': manifest['destination_qualification_identity']}:
        raise ValueError('staged independent qualification is invalid')
    return manifest


def apply(destination_parent: Path, approved_proposal: str) -> dict[str, Any]:
    proposal = propose(destination_parent)
    if approved_proposal != proposal['proposal_sha256']:
        raise ValueError('explicit approval of the current proposal is required')
    root = destination_parent / '.local-transcription'
    root.mkdir(mode=0o700, exist_ok=True)
    directory(root)
    lock = root / 'worker.lock'
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('private owned single-link worker lock required')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage = destination_parent / ('.asr-adoption-' + approved_proposal)
        baseline = tree_files(root) - {'worker.lock'}
        if not stage.exists():
            if baseline or any(p.name != 'temporary' or any(p.iterdir()) for p in root.iterdir() if p.is_dir()):
                raise ValueError('unknown destination state cannot be adopted')
            source, evidence, blobs = verify_source()
            if source != proposal['source']:
                raise ValueError('source changed after proposal')
            stage_install(stage, proposal, evidence, blobs)
        manifest = validate_stage(stage, proposal, root)
        expected = manifest['files']
        if propose(destination_parent) != proposal:
            raise ValueError('current binding changed before publication')
        # The immutable manifest/raw/audit/new seal/model selection arrive first.
        # Until the final complete qualification.json is visible, admission closes.
        missing = (set(expected) | {'adoption.json'}) - baseline
        for name in sorted(missing - {'qualification.json'}):
            write_managed(root, name, checked_read(stage / name, 4 * 1024 * 1024))
        if 'qualification.json' in missing:
            write_managed(root, 'qualification.json', checked_read(stage / 'qualification.json', 1024 * 1024))
        status = qualification.qualification_status(root, proposal['source']['tuple'])
        if status['identity'] != manifest['destination_qualification_identity'] or not status['production_eligible']:
            raise ValueError('published qualification did not verify')
        return {'operation': proposal['operation'], 'destination': str(root), 'proposal_sha256': approved_proposal,
            'qualification': status, 'new_model_invocations': 0, 'adopted_at': manifest['adopted_at']}
    finally:
        os.close(fd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest='command', required=True)
    for command in ('proposal', 'apply'):
        command_parser = subcommands.add_parser(command)
        command_parser.add_argument('--destination-parent', type=Path, required=True)
        if command == 'apply':
            command_parser.add_argument('--approve-proposal', required=True)
    args = parser.parse_args()
    try:
        result = propose(args.destination_parent) if args.command == 'proposal' else apply(args.destination_parent, args.approve_proposal)
    except (OSError, ValueError, KeyError, TypeError, RecursionError, subprocess.SubprocessError) as error:
        raise SystemExit('ASR adoption refused: ' + str(error)) from None
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))


if __name__ == '__main__':
    main()
