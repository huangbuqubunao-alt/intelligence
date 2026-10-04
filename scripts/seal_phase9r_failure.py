"""Seal the measured FAILED adapter tuple; never select an ineligible profile."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from youtube_intel.acoustic_qualification import (
    QualificationEvidence,
    SampleResult,
    canonical,
    current_tuple,
    qualification_status,
    seal_record,
)


def main():
    root = Path('.var/phase9r')
    report = json.loads((root / 'matrix-results.json').read_text())
    assert report['eligible_profiles'] == []
    model_root = Path('.var/phase9')
    origin = json.loads((model_root / 'model-manifest.json').read_text())
    model = model_root / 'models/whisper-large-v3-turbo' / origin['revision']
    identity = current_tuple(model, origin['phase8_model_identity'], origin)
    old = json.loads(Path('docs/validation/phase9/acoustic-evidence.json').read_text())['qualification_tuple']
    assert identity != old
    rows = [s for s in report['samples'] if s['profile'] == 'A']
    samples = tuple(SampleResult(name=s['id'], source_sha256=s['source_sha256'], expected_sha256=s['expected_sha256'], error_rate=s['score']['error_rate'], duration_seconds=s['duration_seconds'], processing_seconds=s['model_wall_seconds'], completed=s['passed'], timestamps_valid=s['validation_error'] is None and not s['nonfinite'], coverage_passed=s['coverage']['passed'], no_omission=all(r >= .5 for r in s['utterance_recalls'])) for s in rows)
    digest = hashlib.sha256(canonical({'original': json.loads((root / 'frozen-corpus/corpus-manifest.json').read_text()), 'independent': json.loads((root / 'independent-corpus/corpus-manifest.json').read_text())})).hexdigest()
    evidence = QualificationEvidence(corpus_sha256=digest, samples=samples, offline=True, cloud_dispatches=0, source_uploads=0)
    audit = {'qualification_tuple': identity, 'historical_tuple': old, 'selected_profile': None, 'matrix': report, 'verdict': 'ACOUSTIC_QUALIFICATION_FAILED', 'reason': 'Every bounded candidate fails at least one required authority or accuracy gate; default decoding remains frozen A, adapter now rejects nonfinite JSON.'}
    payload = canonical(audit)
    (root / 'failure-audit.json').write_bytes(payload)
    machine = model_root / 'real-product-corrected-v1/.local-transcription'
    assert not (machine / 'qualification.json').exists()
    seal_record(machine, identity, evidence=evidence, audit=payload)
    (machine / 'model.json').write_text(json.dumps({'model_path': str(model.absolute())}))
    status = qualification_status(machine, identity)
    assert status['state'] == 'FAILED' and not status['production_eligible']
    candidate_tuples = {}
    for p, (chunked, previous) in report['matrix'].items():
        candidate = json.loads(canonical(identity))
        candidate['decoding_profile']['condition_on_previous_text'] = previous
        candidate['research_segmentation_policy'] = {'chunk_frames': 400000 if chunked else None, 'sample_rate': 16000, 'overlap_frames': 0, 'merge': 'strict-local-then-source-offset-then-global-v1' if chunked else None, 'cross_chunk_prompt': False, 'adapter_semantics': 'reject-all-nonfinite-json-v1'}
        candidate_tuples[p] = {'tuple': candidate, 'sha256': hashlib.sha256(canonical(candidate)).hexdigest(), 'qualified': False}
    assert len({v['sha256'] for v in candidate_tuples.values()}) == 4
    out = {'new_status': status, 'old_tuple_sha256': hashlib.sha256(canonical(old)).hexdigest(), 'new_tuple_sha256': hashlib.sha256(canonical(identity)).hexdigest(), 'adapter_hash_before': old['implementation']['validate_result'], 'adapter_hash_after': identity['implementation']['validate_result'], 'historical_state': json.loads((root / 'historical-qualification-state.json').read_text())['state'], 'research_tuples': candidate_tuples}
    assert out['historical_state'] == 'FAILED'
    (root / 'qualification-state.json').write_bytes(canonical(out))
    print(json.dumps({k:v for k,v in out.items() if k != 'research_tuples'}, indent=2))


if __name__ == '__main__':
    main()
