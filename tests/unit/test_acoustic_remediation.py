"""Phase9R authority adversaries; legitimate repetition must remain exact."""
import json

import pytest

from youtube_intel.offline_transcription import OfflineError, validate_result


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
@pytest.mark.parametrize('location', ['segment', 'top', 'nested'])
def test_nonfinite_metadata_cannot_enter_authoritative_raw(value, location):
    data = {'language': 'en', 'segments': [{'start': 0., 'end': 1., 'text': 'Again again.'}]}
    if location == 'segment':
        data['segments'][0]['avg_logprob'] = value
    elif location == 'top':
        data['diagnostic'] = value
    else:
        data['diagnostic'] = {'nested': [value]}
    with pytest.raises(OfflineError, match='TRANSCRIPT_INVALID'):
        validate_result(json.dumps(data).encode(), duration_seconds=2., provenance='test')


def test_legitimate_repeated_speech_is_retained_exactly():
    data = {'language': 'en', 'segments': [
        {'start': 0., 'end': 1., 'text': ' Again again.'},
        {'start': 1., 'end': 2., 'text': ' Again again.'},
        {'start': 2., 'end': 3., 'text': ' Again again.'},
    ]}
    result = validate_result(json.dumps(data).encode(), duration_seconds=3., provenance='test')
    assert [c.text for c in result.cues] == [' Again again.'] * 3


def test_hallucinated_tail_with_invalid_progression_fails_complete_result():
    data = {'language': 'en', 'segments': [
        {'start': 0., 'end': 1., 'text': 'Real speech.'},
        {'start': 1., 'end': 2., 'text': 'Repeated tail.'},
        {'start': 2., 'end': 2., 'text': 'Repeated tail.'},
        {'start': 2., 'end': 6., 'text': 'Repeated tail.'},
    ]}
    with pytest.raises(OfflineError, match='TRANSCRIPT_INVALID'):
        validate_result(json.dumps(data).encode(), duration_seconds=3., provenance='test')


def test_exponent_overflow_in_metadata_is_nonfinite():
    raw = b'{"language":"en","segments":[{"start":0,"end":1,"text":"Speech."}],"metadata":1e999}'
    with pytest.raises(OfflineError, match='TRANSCRIPT_INVALID'):
        validate_result(raw, duration_seconds=2., provenance='test')


def test_contiguous_chunk_boundaries_preserve_every_source_frame():
    from scripts.phase9r_profiles import boundaries
    spans = boundaries(122855 * 16)
    assert spans[0][0] == 0
    assert spans[-1][1] == 122855 * 16
    assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
    assert all(0 < right - left <= 400000 for left, right in spans)


def test_source_offsets_and_repeated_boundary_words_survive_without_dedup():
    import numpy as np

    from scripts.phase9r_profiles import decode_chunks
    audio = np.arange(800000)
    seen = []
    def decode(chunk, previous):
        seen.append(chunk.copy())
        return {'language': 'en', 'segments': [{'start': 0., 'end': 25., 'text': 'Again again.'}]}
    result, records = decode_chunks(audio, decode, False)
    assert np.array_equal(np.concatenate(seen), audio)
    assert len(records) == 2
    assert [(s['start'], s['end'], s['text']) for s in result['segments']] == [
        (0., 25., 'Again again.'), (25., 50., 'Again again.')]


def test_failed_chunk_returns_no_partial_result_and_retry_decodes_from_start():
    import numpy as np

    from scripts.phase9r_profiles import decode_chunks
    starts = []
    def failing(chunk, previous):
        starts.append(int(chunk[0]))
        if chunk[0] == 400000:
            raise ValueError('chunk failed')
        return {'language': 'en', 'segments': [{'start': 0., 'end': 25., 'text': 'Speech.'}]}
    audio = np.arange(1000000)
    for _ in range(2):
        with pytest.raises(ValueError, match='chunk failed'):
            decode_chunks(audio, failing, True)
    assert starts == [0, 400000, 0, 400000]


def test_chunk_cannot_overlap_next_partition_even_with_sdk_tolerance():
    import numpy as np

    from scripts.phase9r_profiles import decode_chunks
    def decode(chunk, previous):
        return {'language': 'en', 'segments': [{'start': 0., 'end': 25.2, 'text': 'Speech.'}]}
    with pytest.raises(ValueError, match='source partition'):
        decode_chunks(np.zeros(800000), decode, False)
