"""Fixed research-only profile matrix; no product configuration or admission path."""
from __future__ import annotations

import json
from collections.abc import Callable

from youtube_intel.offline_transcription import validate_result

CHUNK_FRAMES = 25 * 16000
MATRIX = {'A': (False, True), 'B': (False, False), 'C': (True, True), 'D': (True, False)}


def boundaries(frames: int) -> list[tuple[int, int]]:
    if frames <= 0:
        raise ValueError('nonempty audio required')
    return [(start, min(start + CHUNK_FRAMES, frames)) for start in range(0, frames, CHUNK_FRAMES)]


def decode_chunks(audio, decode: Callable, previous_text: bool) -> tuple[dict, list[dict]]:
    """All chunks must validate; return no partial authority on any failure.

    Raw research outputs are collected by the caller even on failure. Empty
    SDK segments represent no detected speech; never fabricate a silent cue.
    No overlap, text removal, prompts, deduplication or timeline clipping.
    """
    merged, languages, records = [], [], []
    for start, end in boundaries(len(audio)):
        raw = decode(audio[start:end], previous_text)
        record = {'start_frame': start, 'end_frame': end, 'raw': raw}
        records.append(record)
        encoded = json.dumps(raw, ensure_ascii=False, allow_nan=False).encode()
        if raw.get('segments'):
            validate_result(encoded, duration_seconds=(end - start) / 16000, provenance='research-chunk')
            # The existing validator permits 1s SDK tolerance; chunk reconstruction
            # cannot use that tolerance to overlap neighboring source partitions.
            if any(s['end'] > (end - start) / 16000 for s in raw['segments']):
                raise ValueError('chunk cue exceeds its source partition')
            for s in raw['segments']:
                merged.append({**s, 'start': start / 16000 + s['start'], 'end': start / 16000 + s['end']})
        languages.append(raw.get('language', 'und'))
    response = {'language': languages[0], 'segments': merged}
    validate_result(json.dumps(response, ensure_ascii=False, allow_nan=False).encode(), duration_seconds=len(audio) / 16000, provenance='research-merged')
    return response, records
