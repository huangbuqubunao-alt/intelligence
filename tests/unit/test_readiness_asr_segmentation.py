"""Frozen deterministic source-time/no-speech guard; never edit decoded text."""
import json

import numpy as np
import pytest

from scripts.readiness_asr_profile import assemble, boundaries, signal_guard


def test_partition_preserves_each_source_frame_and_splits_sustained_silence():
    audio = np.concatenate([np.full(16000, .1), np.zeros(16000), np.full(16000, .1)])
    spans = boundaries(audio)
    assert spans == [(0, 24000), (24000, 48000)]
    assert np.array_equal(np.concatenate([audio[a:b] for a, b in spans]), audio)


def test_continuous_source_keeps_bounded_nonoverlapping_partitions():
    spans = boundaries(np.full(950001, .1))
    assert spans == [(0, 400000), (400000, 800000), (800000, 950001)]


def test_zero_pcm_and_fixed_white_noise_cannot_create_authority():
    assert signal_guard(np.zeros(56000)) == 'NO_SIGNAL'
    assert signal_guard(np.random.default_rng(909).normal(0, .01, 56000)) == 'NOISE_ONLY'


def test_speech_like_tone_is_not_classified_as_silence_or_white_noise():
    t = np.arange(16000) / 16000
    assert signal_guard(.1 * np.sin(t * 2 * np.pi * 440)) == 'DECODE'


def test_native_timestamp_grid_maps_once_to_source_samples_without_float_overlap():
    outputs = [{'language': 'en', 'segments': [
        {'start': 0., 'end': .1 + .2, 'text': ' Again.'},
        {'start': .3, 'end': 1., 'text': ' Again.'}]}]
    result = assemble([(0, 32000)], outputs, 32000)
    assert [s['text'] for s in result['segments']] == [' Again.', ' Again.']
    assert result['segments'][0]['end'] == result['segments'][1]['start'] == .3


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_metadata_invalidates_entire_attempt(bad):
    with pytest.raises(ValueError):
        assemble([(0, 32000)], [{'language': 'en', 'segments': [{'start': 0., 'end': 1., 'text': 'Speech.', 'avg_logprob': bad}]}], 32000)


@pytest.mark.parametrize('start,end', [(1., .5), (-.02, 1.), (0., 2.2), (0., .333)])
def test_real_bad_timestamp_is_not_rounded_clipped_or_repaired(start, end):
    with pytest.raises(ValueError):
        assemble([(0, 32000)], [{'language': 'en', 'segments': [{'start': start, 'end': end, 'text': 'Speech.'}]}], 32000)


def test_late_chunk_failure_never_returns_partial_or_removes_repeated_words():
    good = {'language': 'en', 'segments': [{'start': 0., 'end': 1., 'text': 'Again again.'}]}
    bad = {'language': 'en', 'segments': [{'start': 0., 'end': 3., 'text': 'Again again.'}]}
    with pytest.raises(ValueError):
        assemble([(0, 32000), (32000, 64000)], [good, bad], 64000)
    result = assemble([(0, 32000), (32000, 64000)], [good, good], 64000)
    assert [s['text'] for s in result['segments']] == ['Again again.'] * 2
    assert result['segments'][1]['start'] == 2.
    json.dumps(result, allow_nan=False)
