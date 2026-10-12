"""Frozen engineering profile. No production configuration or receipt writer.

Uses only actual source PCM, never expected text. No model text is deleted,
trimmed, deduplicated or repaired; every decoded chunk must validate as a whole.
"""
from __future__ import annotations

import json
import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from youtube_intel.offline_transcription import validate_result

RATE = 16000
WINDOW = 320
MAX_CHUNK = 400000
SILENCE_AMPLITUDE = 10 ** (-45 / 20)


def _frames(audio: np.ndarray) -> np.ndarray:
    if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
        raise ValueError('finite nonempty mono PCM required')
    return np.pad(audio, (0, (-len(audio)) % WINDOW)).reshape(-1, WINDOW)


def signal_guard(audio: np.ndarray) -> str:
    """Acoustic refusal only; NO_SIGNAL/NOISE_ONLY are not trusted transcripts.

    A fixed spectral-flatness guard rejects uniform white-noise frames. This
    is not proof of human speech and may refuse poor-quality/weak recordings.
    """
    frames = _frames(audio)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    active = frames[rms > SILENCE_AMPLITUDE]
    if not len(active):
        return 'NO_SIGNAL'
    noise_frames = 0
    for offset in range(0, len(active), 1024):
        power = np.abs(np.fft.rfft(active[offset:offset+1024] * np.hanning(WINDOW), axis=1)[:, 1:]) ** 2
        power = np.maximum(power, 1e-20)
        flatness = np.exp(np.mean(np.log(power), axis=1)) / np.mean(power, axis=1)
        noise_frames += int(np.count_nonzero(flatness >= .4))
    return 'NOISE_ONLY' if noise_frames / len(active) >= .95 else 'DECODE'


def boundaries(audio: np.ndarray) -> list[tuple[int, int]]:
    """Partition every byte once at sustained-silence midpoints, at most 25s.

    Silence has at least fifteen 20ms RMS frames. Continuous speech falls back
    to a hard 25s boundary and must still earn the unchanged acoustic gates.
    """
    quiet = np.sqrt(np.mean(_frames(audio) ** 2, axis=1)) <= SILENCE_AMPLITUDE
    candidate = []
    run_start = None
    for index, silent in enumerate([*quiet, False]):
        if silent and run_start is None:
            run_start = index
        elif not silent and run_start is not None:
            if index - run_start >= 15:
                point = (run_start + index) * WINDOW // 2
                if 0 < point < len(audio):
                    candidate.append(point)
            run_start = None
    cuts = [0]
    for point in [*candidate, len(audio)]:
        while point - cuts[-1] > MAX_CHUNK:
            cuts.append(cuts[-1] + MAX_CHUNK)
        if point != cuts[-1]:
            cuts.append(point)
    return list(zip(cuts, cuts[1:]))


def _tick(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('nonfinite timestamp')
    tick = round(value / .02)
    if abs(value - tick * .02) > 1e-9:
        raise ValueError('timestamp is not on the SDK 20ms token grid')
    return tick * WINDOW


def assemble(spans: Sequence[tuple[int, int]], outputs: Sequence[dict[str, Any]], frames: int) -> dict[str, Any]:
    if len(spans) != len(outputs):
        raise ValueError('incomplete attempt')
    merged = []
    languages = []
    for (start, end), raw in zip(spans, outputs, strict=True):
        # All metadata remains mandatory finite, including non-time fields.
        json.dumps(raw, ensure_ascii=False, allow_nan=False)
        mapped = []
        previous = 0
        for segment in raw['segments']:
            local_start, local_end = _tick(segment['start']), _tick(segment['end'])
            if local_start < previous or local_end <= local_start or local_end > end - start:
                raise ValueError('invalid source-window timestamp')
            previous = local_end
            mapped.append({**segment, 'start': local_start / RATE, 'end': local_end / RATE})
        if mapped:
            validate_result(json.dumps({**raw, 'segments': mapped}, allow_nan=False).encode(), duration_seconds=(end-start)/RATE, provenance='research-chunk')
            languages.append(raw.get('language', 'und'))
            merged.extend({**s, 'start': (start + _tick(s['start'])) / RATE, 'end': (start + _tick(s['end'])) / RATE} for s in mapped)
    response = {'language': languages[0] if languages and len(set(languages)) == 1 else 'mul', 'segments': merged}
    if merged:
        validate_result(json.dumps(response, ensure_ascii=False, allow_nan=False).encode(), duration_seconds=frames/RATE, provenance='research-source-merged')
    return response


def source_windows(audio: np.ndarray) -> list[tuple[int, int]]:
    """Remove only pre-detected quiet padding before inference, on source frames.

    Speech windows retain up to 200ms of surrounding PCM and cannot extend
    beyond their original partition. No model output enters this decision.
    Unvoiced partitions remain recorded for the explicit refusal guard.
    """
    windows = []
    for start, end in boundaries(audio):
        rms = np.sqrt(np.mean(_frames(audio[start:end]) ** 2, axis=1))
        active = np.flatnonzero(rms > SILENCE_AMPLITUDE)
        if not len(active):
            windows.append((start, end))
            continue
        left = max(start, start + int(active[0]) * WINDOW - 3200)
        right = min(end, start + (int(active[-1]) + 1) * WINDOW + 3200)
        windows.append((left, right))
    return windows
