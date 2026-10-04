"""Sequential negative controls and uncontended repeats; fixed matrix unchanged."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
from phase9r_profiles import MATRIX


def main():
    root = Path('.var/phase9r')
    out = root / 'controls'
    out.mkdir(exist_ok=False)
    specification = {'silence-short': {'seconds': 3.5, 'amplitude': 0}, 'silence-medium': {'seconds': 125, 'amplitude': 0}, 'noise-short': {'seconds': 3.5, 'seed': 909, 'standard_deviation': .01}}
    (out / 'spec.json').write_text(json.dumps(specification, indent=2))
    negative = []
    for name, spec in specification.items():
        frames = round(spec['seconds'] * 16000)
        audio = np.zeros(frames, dtype='<i2') if 'amplitude' in spec else np.clip(np.rint(np.random.default_rng(909).normal(0, .01 * 32768, frames)), -32768, 32767).astype('<i2')
        source = out / (name + '.wav')
        with wave.open(str(source), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(audio.tobytes())
        negative.append((name, source))
    runs = [('B', name, root / 'independent-corpus' / (name + '.wav'), False) for name in ['independent-medium', 'boundary-medium']]
    runs += [(p, name, source, True) for p in MATRIX for name, source in negative]
    report = []
    for profile, name, source, is_negative in runs:
        destination = out / (profile + '-' + name + '.json')
        audio = out / 'preprocessed.wav'
        t = time.monotonic()
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(source), '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(audio)], check=True, timeout=30)
        preprocessing = time.monotonic() - t
        t = time.monotonic()
        resource = destination.with_suffix('.resource.txt')
        subprocess.run(['/usr/bin/time', '-l', '-o', str(resource), '/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)', sys.executable, 'scripts/measure_phase9r_profiles.py', '--child', '--profile', profile, '--audio', str(audio), '--output', str(destination)], check=True, timeout=1800)
        seconds = time.monotonic() - t
        data = json.loads(destination.read_text())
        record = {'profile': profile, 'sample': name, 'negative': is_negative, 'preprocessing_seconds': preprocessing, 'model_wall_seconds': seconds, 'result': data}
        if is_negative:
            record['meaningful_speech_emitted'] = any(s['text'].strip() for s in data['segments'])
            record['safe_no_transcript'] = not record['meaningful_speech_emitted']
        else:
            original = json.loads((root / 'matrix' / destination.name).read_text())
            record['same_text_and_source_times'] = data['segments'] == original['segments']
            assert record['same_text_and_source_times']
        report.append(record)
        (root / 'controls-results.json').write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
        print(json.dumps({k: v for k, v in record.items() if k != 'result'}), flush=True)


if __name__ == '__main__':
    main()
