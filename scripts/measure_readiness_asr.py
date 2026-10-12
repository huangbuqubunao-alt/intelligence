"""Frozen whole-corpus offline research run; expected words never reach child."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import socket
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
from readiness_asr_profile import assemble, boundaries, signal_guard

from youtube_intel.acoustic_scoring import coverage, score, utterance_recalls

MODEL = Path('/Users/hua/Documents/yia-worktrees/v1x-acoustic-qualification/.var/phase9/models/whisper-large-v3-turbo/a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb')
FROZEN = Path('docs/validation/readiness-asr/run03')


def nonfinite(value, path='$'):
    if isinstance(value, float) and not math.isfinite(value):
        return [{'path': path, 'value': str(value)}]
    if isinstance(value, dict):
        return [r for k, v in value.items() for r in nonfinite(v, path + '.' + k)]
    if isinstance(value, list):
        return [r for i, v in enumerate(value) for r in nonfinite(v, path + f'[{i}]')]
    return []


def child(args):
    def offline(*a, **kw):
        raise RuntimeError('network forbidden')
    socket.socket.connect = offline
    socket.create_connection = offline
    with wave.open(str(args.audio)) as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
            raise ValueError('actual mono16k PCM required')
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768
    partitions = boundaries(audio)
    spans = partitions
    global_guard = signal_guard(audio)
    outputs, times, guards, loads = [], [], [], []
    decoder = None
    for start, end in spans:
        guard = signal_guard(audio[start:end]) if global_guard == 'DECODE' else global_guard
        guards.append(guard)
        if guard != 'DECODE':
            outputs.append({'language': 'und', 'segments': []})
            continue
        if decoder is None:
            import mlx_whisper
            import mlx_whisper.load_models as loader
            loader.snapshot_download = offline
            runtime = importlib.import_module('mlx_whisper.transcribe')
            original_load = runtime.load_model
            def counted(*a, **kw):
                loads.append(time.monotonic())
                return original_load(*a, **kw)
            runtime.load_model = counted
            decoder = mlx_whisper.transcribe
        t = time.monotonic()
        raw = decoder(audio[start:end], path_or_hf_repo=str(MODEL), task='transcribe', language=None, temperature=0., compression_ratio_threshold=2.4, logprob_threshold=-1., no_speech_threshold=.6, initial_prompt=None, verbose=None, word_timestamps=True, condition_on_previous_text=False)
        times.append(time.monotonic() - t)
        outputs.append(raw)
    # Explicit untrusted diagnostics retain all model metadata and failures.
    args.output.with_suffix('.NONAUTHORITATIVE.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2))
    error = None
    try:
        merged = assemble(spans, outputs, len(audio), word_alignment=True)
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        merged = {'segments': [{**s, 'start': s['start'] + start/16000, 'end': s['end'] + start/16000} for (start, end), raw in zip(spans, outputs, strict=True) for s in raw['segments']]}
    result = {'source_partitions': partitions, 'boundaries': spans, 'guards': guards, 'global_guard': global_guard, 'nonfinite': nonfinite(outputs), 'validation_error': error, 'segments': [{k: s[k] for k in ('start','end','text')} for s in merged['segments']], 'model_seconds': sum(times), 'invocations': len(times), 'disk_model_loads': len(loads), 'call_seconds': times, 'authoritative': False}
    args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


def main(args):
    root = args.root
    root.mkdir(exist_ok=False, parents=True)
    frozen = json.loads((FROZEN/'FROZEN_HASHES.json').read_text())
    for filename, digest in frozen.items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, 'frozen policy/input/harness changed'
    with (MODEL/'weights.safetensors').open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == '951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6'
    samples = json.loads((FROZEN/'FROZEN_CORPUS.json').read_text())['samples']
    report = {'frozen_hashes': frozen, 'model': str(MODEL), 'samples': [], 'production_eligible': False, 'offline': True}
    for sample in samples:
        source = Path(sample['source'])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == sample['sha256']
        destination = root/(sample['id']+'.json')
        audio = root/(sample['id']+'.pcm.wav')
        t = time.monotonic()
        subprocess.run(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-i',str(source),'-map','0:a:0','-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(audio)], check=True, timeout=120)
        preprocessing = time.monotonic()-t
        resource = destination.with_suffix('.resource.txt')
        env = {'PATH':'/opt/homebrew/bin:/usr/bin:/bin','HOME':str(Path.home()),'PYTHONPATH':str(Path('src').absolute()),'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','OMP_NUM_THREADS':'2'}
        t = time.monotonic()
        proc = subprocess.run(['/usr/bin/time','-l','-o',str(resource),'/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)',sys.executable,str(Path(__file__).absolute()),'--child','--audio',str(audio),'--output',str(destination)], capture_output=True,env=env,timeout=1800)
        wall = time.monotonic()-t
        destination.with_suffix('.stderr.txt').write_bytes(proc.stderr)
        if proc.returncode:
            entry = {'id':sample['id'],'failed_worker':proc.returncode,'passed':False,'stderr':proc.stderr.decode()[-1000:]}
        else:
            result = json.loads(destination.read_text())
            text = ' '.join(s['text'] for s in result['segments'])
            entry = {**result,'id':sample['id'],'source_sha256':sample['sha256'],'preprocessing_seconds':preprocessing,'child_wall_seconds':wall,'resource':resource.name}
            if sample.get('negative'):
                entry['passed'] = not result['segments'] and not result['invocations'] and not result['nonfinite'] and result['validation_error'] is None
                entry['safe_no_authority'] = not result['segments']
            else:
                metric = score(sample['expected'], text, sample['language'])
                recalls = utterance_recalls([r['text'] for r in sample['speech_regions']],text,sample['language'])
                cov = coverage([(r['start'],r['end']) for r in sample['speech_regions']],[(s['start'],s['end']) for s in result['segments']])
                entry.update(score=metric,utterance_recalls=recalls,coverage=cov,rtf=wall/sample['duration_seconds'])
                entry['passed'] = result['validation_error'] is None and not result['nonfinite'] and metric['error_rate'] <= (.2 if sample['language']=='mixed' else .15) and all(r >= .5 for r in recalls) and cov['passed'] and wall < 1800
        report['samples'].append(entry)
        (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2))
        print(json.dumps({k:entry.get(k) for k in ('id','passed','score','validation_error','invocations','global_guard','failed_worker')}),flush=True)
    report['verdict'] = 'PASSED' if all(s['passed'] for s in report['samples']) else 'FAILED'
    (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2))
    print(report['verdict'],flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root',nargs='?',type=Path)
    parser.add_argument('--child',action='store_true')
    parser.add_argument('--audio',type=Path)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    child(args) if args.child else main(args)
