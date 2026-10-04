"""Adversarial job/persistence proof with explicit test-only typed executor."""
from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path


def main():
    path = Path('tests/integration/test_offline_transcription_jobs.py')
    spec = importlib.util.spec_from_file_location('phase9r_job_fixtures', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = Path('.var/phase9r/persistence-adversaries')
    root.mkdir(exist_ok=False)
    results = []
    for name, value in [('nan', float('nan')), ('inf', float('inf')), ('negative-inf', -float('inf'))]:
        task = root / name
        task.mkdir()
        setup = module.setup.__wrapped__(task)

        class UntrustedTypedExecutor(module.Executor):
            bad_metadata = True

            def transcribe(self, snapshot, *, duration_seconds):
                transcript = super().transcribe(snapshot, duration_seconds=duration_seconds)
                if not self.bad_metadata:
                    return transcript
                raw = json.loads(transcript.raw_output)
                raw['diagnostic'] = {'nested': [value]}
                return replace(transcript, raw_output=json.dumps(raw).encode())

        executor = UntrustedTypedExecutor()
        jobs = module.service(setup, executor)
        first = jobs.start(setup[2], module.IDENTITY)['attempt_id']
        module.wait_for(lambda: jobs.status(setup[2])['status'] == 'FAILED')
        assert jobs.status(setup[2])['last_failure_category'] == 'TRANSCRIPT_INVALID'
        repo, provider, cid = setup
        assert repo.get_verified_timed_transcript(video_id=cid) is None
        assert repo.current_local_summary_pointer(cid) is None
        assert not repo.list_evidence_for_presentation(cid)
        assert not list(provider.data_root.rglob('executor-output-*'))
        executor.bad_metadata = False
        second = jobs.start(cid, module.IDENTITY)['attempt_id']
        assert first != second
        module.wait_for(lambda: jobs.status(cid)['status'] == 'READY')
        assert executor.calls == 2
        assert repo.get_verified_timed_transcript(video_id=cid) is not None
        results.append({'value': name, 'typed_result_failed_closed': True, 'no_raw_artifact_or_partial_authority': True, 'new_complete_retry_succeeded': True, 'model': 'explicit test-only fixture, no acoustic qualification claim'})
    Path('.var/phase9r/persistence-adversaries.json').write_text(json.dumps(results, indent=2) + '\n')
    print('3 nonfinite typed-result persistence adversaries and complete retries passed.')


if __name__ == '__main__':
    main()
