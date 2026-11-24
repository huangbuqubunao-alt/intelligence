"""Bounded exact-model investigation. Child receives audio, never reference text."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import re
import socket
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
from phase9r_profiles import MATRIX, boundaries, decode_chunks

from youtube_intel.acoustic_scoring import coverage, score, utterance_recalls
from youtube_intel.offline_transcription import validate_result

MODEL = Path('/Users/developer/Documents/yia-worktrees/v1x-acoustic-qualification/.var/phase9/models/whisper-large-v3-turbo/a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb')


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
    import mlx_whisper
    import mlx_whisper.load_models as loader
    loader.snapshot_download = offline
    runtime = importlib.import_module('mlx_whisper.transcribe')
    loads = []
    original_load = runtime.load_model
    def counted(*a, **kw):
        loads.append(time.monotonic())
        return original_load(*a, **kw)
    runtime.load_model = counted
    with wave.open(str(args.audio)) as wav:
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768
    chunked, previous = MATRIX[args.profile]
    spans = boundaries(len(audio)) if chunked else [(0, len(audio))]
    outputs, times = [], []
    for start, end in spans:
        t = time.monotonic()
        raw = mlx_whisper.transcribe(audio[start:end], path_or_hf_repo=str(MODEL), task='transcribe', language=None, temperature=0., compression_ratio_threshold=2.4, logprob_threshold=-1., no_speech_threshold=.6, initial_prompt=None, verbose=None, word_timestamps=False, condition_on_previous_text=previous)
        times.append(time.monotonic() - t)
        outputs.append(raw)
    # Explicitly untrusted raw SDK diagnostics retain NaN/inf verbatim.
    args.output.with_suffix('.NONAUTHORITATIVE.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2))
    merged = {'language': outputs[0].get('language'), 'segments': [dict(s, start=s['start'] + start / 16000, end=s['end'] + start / 16000) for (start, end), raw in zip(spans, outputs) for s in raw['segments']]}
    error = None
    try:
        if chunked:
            iterator = iter(outputs)
            decode_chunks(audio, lambda a, b: next(iterator), previous)
        elif merged['segments']:
            validate_result(json.dumps(merged, allow_nan=False).encode(), duration_seconds=len(audio) / 16000, provenance='research')
        else:
            json.dumps(outputs, allow_nan=False)
    except (ValueError, TypeError) as exc:
        error = str(exc)
    # Strict diagnostic projection omits metadata only for scoring; never persistence.
    result = {'profile': args.profile, 'chunked': chunked, 'previous_text': previous, 'boundaries': spans, 'nonfinite': nonfinite(outputs), 'validation_error': error, 'segments': [{k: s[k] for k in ('start', 'end', 'text')} for s in merged['segments']], 'model_seconds': sum(times), 'invocations': len(outputs), 'disk_model_loads': len(loads), 'call_seconds': times}
    args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


def main(args):
    root = args.root
    out = root / 'matrix'
    out.mkdir(exist_ok=True)
    samples = []
    for folder in ('frozen-corpus', 'independent-corpus'):
        manifest = json.loads((root / folder / 'corpus-manifest.json').read_text())
        samples += [(root / folder / s['file'], s) for s in manifest['samples']]
    english = next(s for _, s in samples if s['id'] == 'english-clean')
    video = root / 'english-video.mp4'
    if not video.exists():
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', f"color=c=black:s=64x64:r=5:d={english['duration_seconds']}", '-i', str(root / 'frozen-corpus' / english['file']), '-shortest', '-c:v', 'mpeg4', '-c:a', 'aac', str(video)], check=True, timeout=30)
    samples.append((video, {**english, 'id': 'english-video', 'sha256': hashlib.sha256(video.read_bytes()).hexdigest()}))
    report = {'matrix': MATRIX, 'chunk_frames': 400000, 'overlap_frames': 0, 'model': str(MODEL), 'samples': []}
    for profile in MATRIX:
        for source, sample in samples:
            destination = out / (profile + '-' + sample['id'] + '.json')
            if destination.exists():
                raise ValueError('retain evidence; distinct run directory required')
            assert hashlib.sha256(source.read_bytes()).hexdigest() == sample['sha256']
            started = time.monotonic()
            audio = out / 'preprocessed.wav'
            t = time.monotonic()
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file,pipe', '-i', str(source), '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(audio)], check=True, timeout=120)
            preprocessing = time.monotonic() - t
            resource = destination.with_suffix('.resource.txt')
            env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'HOME': str(Path.home()), 'PYTHONPATH': str(Path('src').absolute()), 'PYTHONDONTWRITEBYTECODE': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'OMP_NUM_THREADS': '2'}
            t = time.monotonic()
            proc = subprocess.run(['/usr/bin/time', '-l', '-o', str(resource), '/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)', sys.executable, str(Path(__file__).absolute()), '--child', '--profile', profile, '--audio', str(audio), '--output', str(destination)], capture_output=True, env=env, timeout=1800)
            wall = time.monotonic() - t
            destination.with_suffix('.stderr.txt').write_bytes(proc.stderr)
            if proc.returncode:
                raise RuntimeError(f'child failed {profile}/{sample["id"]}: {proc.stderr.decode()[-1500:]}')
            result = json.loads(destination.read_text())
            text = ' '.join(s['text'] for s in result['segments'])
            metric = score(sample['expected'], text, sample['language'])
            recalls = utterance_recalls([r['text'] for r in sample['speech_regions']], text, sample['language'])
            cov = coverage([(r['start'], r['end']) for r in sample['speech_regions']], [(s['start'], s['end']) for s in result['segments']])
            stats = resource.read_text()
            def measured(label):
                m = re.search(r'(\d+)\s+' + label, stats)
                return int(m[1]) if m else None
            entry = {**result, 'id': sample['id'], 'source_sha256': sample['sha256'], 'expected_sha256': sample['expected_sha256'], 'duration_seconds': sample['duration_seconds'], 'language_scorer': sample['language'], 'score': metric, 'utterance_recalls': recalls, 'coverage': cov, 'preprocessing_seconds': preprocessing, 'model_wall_seconds': wall, 'total_wall_seconds': time.monotonic() - started, 'rtf': wall / sample['duration_seconds'], 'peak_rss_bytes': measured('maximum resident set size'), 'peak_footprint_bytes': measured('peak memory footprint')}
            entry['passed'] = result['validation_error'] is None and not result['nonfinite'] and metric['error_rate'] <= (.20 if sample['language'] == 'mixed' else .15) and all(r >= .5 for r in recalls) and cov['passed'] and wall < 1800
            report['samples'].append(entry)
            (root / 'matrix-results.json').write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
            print(json.dumps({k: entry[k] for k in ('profile', 'id', 'score', 'validation_error', 'passed', 'rtf', 'invocations', 'disk_model_loads')}), flush=True)
    report['eligible_profiles'] = [p for p in MATRIX if all(s['passed'] for s in report['samples'] if s['profile'] == p)]
    (root / 'matrix-results.json').write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path, nargs='?', default=Path('.var/phase9r'))
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--profile', choices=list(MATRIX))
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    child(args) if args.child else main(args)
