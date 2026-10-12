"""Product worker pre-inference refusals and complete source-bound authority."""
import wave
from pathlib import Path

import numpy as np
import pytest

from youtube_intel.acoustic_remediation import transcribe_pcm


def pcm(path: Path, samples: np.ndarray) -> Path:
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(np.rint(samples * 32768).astype('<i2').tobytes())
    return path


@pytest.mark.parametrize('noise', [False, True])
def test_refusal_never_calls_decoder_or_creates_empty_trusted_transcript(tmp_path, noise):
    samples = np.random.default_rng(909).normal(0, .01, 56000) if noise else np.zeros(56000)
    calls = []
    result = transcribe_pcm(pcm(tmp_path/'input.wav', samples), lambda audio: calls.append(audio))
    assert calls == []
    assert result['segments'] == []
    assert result['acoustic_guard'] == ('NOISE_ONLY' if noise else 'NO_SIGNAL')


def test_complete_source_offsets_preserve_exact_words_and_all_native_output(tmp_path):
    audio = np.concatenate([np.full(16000, .1), np.zeros(16000), np.full(16000, .1)])
    calls = []
    def decode(chunk):
        calls.append(chunk.copy())
        return {'language': 'en', 'text': ' Again.', 'segments': [{'start': 0., 'end': 1., 'text': ' Again.', 'words': [{'start': 0., 'end': 1., 'word': ' Again.', 'probability': .9}]}]}
    result = transcribe_pcm(pcm(tmp_path/'input.wav', audio), decode)
    assert len(calls) == 2
    assert [s['text'] for s in result['segments']] == [' Again.'] * 2
    assert result['segments'][1]['start'] == 1.5
    assert result['segments'][1]['words'][0]['start'] == 1.5
    assert result['native_chunks'][1]['output']['segments'][0]['start'] == 0.
    assert result['native_chunks'][1]['output']['text'] == ' Again.'


def test_late_nonfinite_native_metadata_invalidates_entire_attempt(tmp_path):
    count = 0
    def decode(audio):
        nonlocal count
        count += 1
        return {'language': 'en', 'segments': [{'start': 0., 'end': 1., 'text': ' Again.', 'words': [{'start': 0., 'end': 1., 'word': ' Again.', 'probability': .9 if count == 1 else float('nan')}]}]}
    audio = np.concatenate([np.full(16000, .1), np.zeros(16000), np.full(16000, .1)])
    with pytest.raises(ValueError):
        transcribe_pcm(pcm(tmp_path/'input.wav', audio), decode)
    assert count == 2
