"""Freeze independent nonpersonal fixtures before any candidate output is seen."""
import hashlib
import json
import sys
import wave
from pathlib import Path

import generate_phase9_corpus as generator
from generate_phase9_corpus import ENGLISH, MEDIUM, MIXED, main

INDEPENDENT = [
    'A weather station measures the temperature beside a public walking trail.',
    'The brass instrument records air pressure at regular intervals each morning.',
    'A wooden shelter protects the thermometer from direct afternoon sunlight.',
    'Several glass containers collect rainwater for a simple measurement exercise.',
    'The observer writes each reading in a notebook with the date and time.',
    'A blue arrow on the roof shows which direction the wind is blowing.',
    'The lesson explains why nearby buildings can change the measured wind speed.',
    'Students compare observations from the hill and from the open playing field.',
    'The next activity uses a paper chart to display temperature changes.',
    'Each colored line represents a different day of the same teaching week.',
    'A small ruler helps the class draw straight lines across the chart.',
    'The instructor asks everyone to check the units before comparing numbers.',
    'Warm air can hold more moisture than cold air under similar conditions.',
    'Clouds form when moist air rises and cools above the surrounding landscape.',
    'A simple experiment places a cool metal lid over a container of warm water.',
    'Drops appear on the lid after the water vapor touches the cooler surface.',
    'The class discusses the difference between an observation and an explanation.',
    'Careful records help another observer repeat the same measurement tomorrow.',
    'All spoken material in this exercise was generated locally for software testing.',
    'The recording ends after the final explanation without any private information.',
]


def specification():
    def sample(name, lines, gap):
        return {'id': name, 'language': 'en', 'utterances': [{'voice': 'Samantha', 'text': t} for t in lines], 'gap_seconds': gap, 'rate': 145, 'noise_snr_db': None}
    return [
        sample('independent-medium', INDEPENDENT, 1.5),
        sample('boundary-medium', INDEPENDENT + ENGLISH + MEDIUM[:5], 0.0),
        sample('silence-medium', INDEPENDENT[:12], 7.0),
        {**sample('mixed-medium', [], 1.0), 'language': 'mixed', 'utterances': [{'voice': v, 'text': t} for v, t in MIXED * 5]},
    ]


if __name__ == '__main__':
    generator.specification = specification
    main()
    # Declared before decoding: add a fixed seven-second terminal silence to
    # the independent fixture, also exercising the original failure trigger.
    root = Path(sys.argv[1])
    path = root / 'independent-medium.wav'
    with wave.open(str(path)) as wav:
        data = wav.readframes(wav.getnframes())
    data += bytes(7 * 16000 * 2)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(data)
    manifest_path = root / 'corpus-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['postprocess'] = {'independent-medium': {'terminal_silence_seconds': 7.0}}
    for sample in manifest['samples']:
        if sample['id'] == 'independent-medium':
            sample['duration_seconds'] += 7.0
            sample['bytes'] = path.stat().st_size
            sample['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.pop('corpus_sha256')
    manifest['corpus_sha256'] = hashlib.sha256(generator.canonical(manifest)).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
