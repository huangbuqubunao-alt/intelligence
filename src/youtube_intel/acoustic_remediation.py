"""Deterministic pre-inference acoustic boundaries and native source-time mapping.

Uses only actual source PCM, never expected text. No model text is deleted,
trimmed, deduplicated or repaired; every decoded chunk must validate as a whole.
"""
from __future__ import annotations

import json
import math
import wave
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import JsonValue

from youtube_intel.offline_transcription import validate_result

RATE = 16000
WINDOW = 320
MAX_CHUNK = 400000
SILENCE_AMPLITUDE = 10 ** (-45 / 20)


def _frames(audio: NDArray[np.float32]) -> NDArray[np.float32]:
    if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
        raise ValueError('finite nonempty mono PCM required')
    return np.pad(audio, (0, (-len(audio)) % WINDOW)).reshape(-1, WINDOW)


def signal_guard(audio: NDArray[np.float32]) -> str:
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


def boundaries(audio: NDArray[np.float32]) -> list[tuple[int, int]]:
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


def _tick(value: Any, *, word_alignment: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('nonfinite timestamp')
    quantum = 1 / RATE if word_alignment else .02
    tick = round(value / quantum)
    if abs(value - tick * quantum) > 1e-9:
        raise ValueError('timestamp is not on the native source-sample grid')
    return tick if word_alignment else tick * WINDOW


def assemble(spans: Sequence[tuple[int, int]], outputs: Sequence[dict[str, Any]], frames: int, *, word_alignment: bool = False) -> dict[str, Any]:
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
            local_start, local_end = _tick(segment['start'], word_alignment=word_alignment), _tick(segment['end'], word_alignment=word_alignment)
            if local_start < previous or local_end <= local_start or local_end > end - start:
                raise ValueError('invalid source-window timestamp')
            previous = local_end
            mapped_segment = {**segment, 'start': local_start / RATE, 'end': local_end / RATE}
            if word_alignment:
                words = segment.get('words')
                if not isinstance(words, list) or not words:
                    raise ValueError('native alignment words required')
                mapped_words = []
                previous_word = 0
                for word in words:
                    word_start = _tick(word['start'], word_alignment=True)
                    word_end = _tick(word['end'], word_alignment=True)
                    if word_start < previous_word or word_end < word_start or word_end > end-start:
                        raise ValueError('invalid native word source-window timestamp')
                    previous_word = word_end
                    mapped_words.append({**word, 'start': word_start/RATE, 'end': word_end/RATE})
                mapped_segment['words'] = mapped_words
            mapped.append(mapped_segment)
        if mapped:
            validate_result(json.dumps({**raw, 'segments': mapped}, allow_nan=False).encode(), duration_seconds=(end-start)/RATE, provenance='research-chunk')
            languages.append(raw.get('language', 'und'))
            for segment in mapped:
                source_segment = {**segment, 'start': (start + _tick(segment['start'], word_alignment=word_alignment)) / RATE, 'end': (start + _tick(segment['end'], word_alignment=word_alignment)) / RATE}
                if word_alignment:
                    source_segment['words'] = [{**word, 'start': (start+_tick(word['start'], word_alignment=True))/RATE, 'end': (start+_tick(word['end'], word_alignment=True))/RATE} for word in segment['words']]
                merged.append(source_segment)
    response = {'language': languages[0] if languages and len(set(languages)) == 1 else 'mul', 'segments': merged}
    if merged:
        validate_result(json.dumps(response, ensure_ascii=False, allow_nan=False).encode(), duration_seconds=frames/RATE, provenance='research-source-merged')
    return response


DECODING_POLICY: dict[str, JsonValue] = {"task": "transcribe", "language": None, "temperature": 0.0,
    "compression_ratio_threshold": 2.4, "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6, "initial_prompt": None, "word_timestamps": True,
    "condition_on_previous_text": False, "fp16": True, "beam_size": None, "best_of": None}
SEGMENTATION_POLICY: dict[str, JsonValue] = {"sample_rate": RATE, "window_frames": WINDOW,
    "silence_rms_dbfs": -45, "minimum_silence_frames": 4800,
    "cut": "silence midpoint", "max_chunk_frames": MAX_CHUNK,
    "overlap_frames": 0, "dropped_source_frames": 0,
    "spectral_flatness_threshold": 0.4, "noise_frame_fraction": 0.95,
    "time_mapping": "native integer PCM frames; representation error <=1e-9s; no clipping"}


def transcribe_pcm(path: Path, decode: Callable[[NDArray[np.float32]], dict[str, Any]]) -> dict[str, Any]:
    """One complete attempt. Refusal is an empty *untrusted* worker response.

    Read only the already bounded, locally preprocessed PCM. Native SDK output
    remains in the raw authority envelope alongside global source-time segments.
    No reference text, semantic noise oracle or model text filtering is used.
    """
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, RATE):
            raise ValueError('bounded mono16k PCM required')
        frames = wav.getnframes()
        if not 0 < frames <= 7200 * RATE:
            raise ValueError('PCM duration bounds')
        source = wav.readframes(frames)
        if len(source) != frames * 2:
            raise ValueError('truncated PCM')
    audio = (np.frombuffer(source, dtype='<i2').astype(np.float32) / 32768).astype(np.float32)
    spans = boundaries(audio)
    global_guard = signal_guard(audio)
    outputs = []
    native = []
    for start, end in spans:
        guard = signal_guard(audio[start:end]) if global_guard == 'DECODE' else global_guard
        raw = decode(audio[start:end]) if guard == 'DECODE' else {'language': 'und', 'segments': []}
        outputs.append(raw)
        native.append({'start_frame': start, 'end_frame': end, 'guard': guard, 'output': raw})
    result = assemble(spans, outputs, len(audio), word_alignment=True)
    result['acoustic_guard'] = global_guard
    result['native_chunks'] = native
    # Reject nonfinite *all* native metadata even outside trusted cue fields.
    json.dumps(result, ensure_ascii=False, allow_nan=False)
    return result
