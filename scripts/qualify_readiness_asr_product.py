"""Real isolated Local job qualification; no model simulation or owner state."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel import offline_transcription as boundary
from youtube_intel.acoustic_qualification import (
    NegativeControlResult,
    QualificationEvidence,
    SampleResult,
    canonical,
    current_tuple,
    evaluate,
    qualification_status,
    seal_record,
)
from youtube_intel.acoustic_scoring import coverage, score, utterance_recalls
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository

MODEL = Path('/Users/hua/Documents/yia-worktrees/v1x-acoustic-qualification/.var/phase9/models/whisper-large-v3-turbo/a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb')
FROZEN = Path('docs/validation/readiness-asr/run03')


def product_evidence(report, samples, frozen_bytes):
    """Bind every real product authority requirement to qualification."""
    positive = tuple(SampleResult(name=s['id'],source_sha256=s['source_sha256'],expected_sha256=next(x['expected_sha256'] for x in samples if x['id']==s['id']),error_rate=s.get('score',{}).get('error_rate'),duration_seconds=next(x['duration_seconds'] for x in samples if x['id']==s['id']),processing_seconds=s['product_wall_seconds'],completed=bool(s['passed'] and s['status']['status'] == 'READY' and s['trusted_timed_transcript'] and s['summary'] and s['evidence_resolves']),timestamps_valid=s['trusted_timed_transcript'],coverage_passed=s.get('coverage',{}).get('passed',False),no_omission=bool(s.get('recalls')) and all(r >= .5 for r in s.get('recalls',[]))) for s in report['samples'] if not s['id'].startswith('negative-'))
    negative = tuple(NegativeControlResult(name=s['id'],source_sha256=s['source_sha256'],processing_seconds=s['product_wall_seconds'],observed_outcome=s['acoustic_guard'],decoder_invocations=s['decoder_invocations'],no_authority=bool(s['passed'] and s['status']['status'] == 'FAILED' and s['no_authority'])) for s in report['samples'] if s['id'].startswith('negative-'))
    return QualificationEvidence(corpus_sha256=hashlib.sha256(frozen_bytes).hexdigest(),samples=positive,negative_controls=negative,offline=True,cloud_dispatches=0,source_uploads=0)


def seal_product_result(machine, identity, result, report, audit):
    """Refuse inconsistent evidence before any receipt can be written."""
    if evaluate(result) != report['verdict']:
        raise ValueError('product verdict and complete evidence differ before sealing')
    seal_record(machine, identity, evidence=result, audit=audit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--freeze', type=Path, default=Path('docs/validation/readiness-asr/product-freeze-review-p1.json'))
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    policy = json.loads(args.freeze.read_text())
    for filename, digest in policy['implementation_sha256'].items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, 'frozen product code changed'
    frozen_bytes = (FROZEN/'FROZEN_CORPUS.json').read_bytes()
    samples = json.loads(frozen_bytes)['samples']
    original_run = boundary.run_bounded
    active = {'id':'capability'}
    observations = []
    def measured(command, **kwargs):
        t = time.monotonic()
        raw = original_run(command, **kwargs)
        if '--transcribe' in command:
            (root/(active['id']+'.raw.json')).write_bytes(raw)
            observations.append({'id': active['id'], 'wall_seconds': time.monotonic()-t})
        return raw
    boundary.run_bounded = measured
    machine = root/'.local-transcription'
    executor = boundary.MlxTimedExecutor(model_path=MODEL, temporary_root=machine/'temporary')
    repo = SQLiteStateRepository(root/'state.sqlite3')
    repo.initialize(now=datetime.now(UTC))
    provider = LocalContentProvider(repo, root/'data')
    jobs = LocalTranscriptionJobs(repo, root/'data', executor=executor)  # explicit existing engineering seam
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=root/'data', transcription_jobs=jobs)
    deadline = time.monotonic()+90
    while jobs.capability()['checking']:
        assert time.monotonic() < deadline
        time.sleep(.1)
    cap = jobs.capability()
    assert cap['state'] == 'READY' and not cap['production_eligible']
    report = {'profile': boundary.PROFILE, 'capability_before':cap, 'engineering_seam':True, 'owner_data_access':False, 'offline':True, 'cloud_dispatches':0, 'source_uploads':0, 'samples':[], 'worker_observations':observations}
    for sample in samples:
        source = Path(sample['source'])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == sample['sha256']
        active['id'] = sample['id']
        imported = provider.import_bytes(sample['id']+source.suffix, source.read_bytes())
        start = time.monotonic()
        jobs.start(imported.content_id, cap['execution_identity'])
        deadline = time.monotonic()+1950
        responsive = []
        while True:
            read_start = time.monotonic()
            code, _ = app.handle('GET','/api/v1/local/transcription/capability')
            responsive.append(time.monotonic()-read_start)
            assert code == 200
            status = jobs.status(imported.content_id)
            if status['status'] not in {'PENDING','RUNNING'}:
                break
            assert time.monotonic() < deadline
            time.sleep(.25)
        raw_path = root/(sample['id']+'.raw.json')
        raw = json.loads(raw_path.read_text()) if raw_path.exists() else None
        timed = repo.get_verified_timed_transcript(video_id=imported.content_id)
        summary = repo.current_local_summary_pointer(imported.content_id)
        evidence = repo.list_evidence_for_presentation(imported.content_id)
        elapsed = time.monotonic()-start
        entry = {'id':sample['id'],'content_id':imported.content_id,'source_sha256':sample['sha256'],'status':status,'product_wall_seconds':elapsed,'max_API_read_seconds':max(responsive),'trusted_timed_transcript':timed is not None,'summary':summary is not None,'evidence_ids':list(evidence)}
        if raw:
            entry['decoder_invocations'] = sum(c['guard'] == 'DECODE' for c in raw['native_chunks'])
            entry['acoustic_guard'] = raw['acoustic_guard']
            entry['raw_sha256'] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if sample.get('negative'):
            entry['no_authority'] = timed is None and summary is None and not evidence
            entry['passed'] = status['status'] == 'FAILED' and entry['no_authority'] and entry.get('decoder_invocations') == 0 and entry.get('acoustic_guard') in {'NO_SIGNAL','NOISE_ONLY'}
        else:
            if raw:
                text = ' '.join(s['text'] for s in raw['segments'])
                entry['score'] = score(sample['expected'],text,sample['language'])
                entry['recalls'] = utterance_recalls([r['text'] for r in sample['speech_regions']],text,sample['language'])
                entry['coverage'] = coverage([(r['start'],r['end']) for r in sample['speech_regions']],[(s['start'],s['end']) for s in raw['segments']])
            entry['evidence_resolves'] = bool(evidence) and all(repo.resolve_verified_evidence_text(e) is not None for e in evidence)
            entry['passed'] = bool(timed and summary and entry['evidence_resolves'] and entry.get('coverage',{}).get('passed') and all(r >= .5 for r in entry.get('recalls',[])) and entry.get('score',{}).get('error_rate',1) <= (.2 if sample['language']=='mixed' else .15) and elapsed < 1800)
            if timed:
                entry['cues'] = [{'start_ms':c.start_ms,'end_ms':c.end_ms,'text':c.text} for c in timed.cues]
        report['samples'].append(entry)
        (root/'report.json').write_bytes(canonical(report))
        print(json.dumps({k:entry.get(k) for k in ('id','passed','score','status','no_authority','decoder_invocations')}),flush=True)
    report['verdict'] = 'PASSED' if all(s['passed'] for s in report['samples']) else 'FAILED'
    result = product_evidence(report, samples, frozen_bytes)
    origin = json.loads((MODEL/'model-origin.json').read_text())
    identity = current_tuple(MODEL,boundary.model_identity(MODEL),origin)
    report['qualification_tuple'] = identity
    report['evidence'] = result.model_dump(mode='json')
    audit = canonical(report)
    (root/'report.json').write_bytes(audit)
    seal_product_result(machine, identity, result, report, audit)
    state = qualification_status(machine,identity)
    (root/'qualification-status.json').write_bytes(canonical(state))
    assert (state['state'] == 'PASSED') == (report['verdict'] == 'PASSED')
    if state['state'] == 'PASSED':
        (machine/'model.json').write_bytes(canonical({'model_path':str(MODEL)}))
    print(json.dumps({'verdict':report['verdict'],'qualification':state}),flush=True)


if __name__ == '__main__':
    main()
