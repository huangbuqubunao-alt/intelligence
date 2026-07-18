"""Fully offline contract tests for the model-free MLX Whisper adapter."""

from __future__ import annotations

import ast
import hashlib
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from youtube_intel.domain import ErrorCode
from youtube_intel.providers.whisper import (
    MlxWhisperAdapter,
    WhisperAdapterError,
    WhisperDecodePolicy,
    WhisperResponse,
)
from youtube_intel.transcription import (
    AudioArtifact,
    AudioResourceSnapshot,
    DurationDecision,
    InMemoryTranscriptionCache,
    TranscriptionPolicy,
)

FIXED_NOW = datetime(2026, 7, 19, 10, 0, tzinfo=UTC)


class _FakeWhisperExecutor:
    def __init__(self, response: WhisperResponse | BaseException) -> None:
        self.response = response
        self.calls: list[tuple[Path, WhisperDecodePolicy]] = []

    def transcribe(self, audio_path: Path, policy: WhisperDecodePolicy) -> WhisperResponse:
        self.calls.append((audio_path, policy))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def _synthetic_wav(tmp_path: Path) -> tuple[AudioArtifact, Path]:
    path = tmp_path / "silence.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\x00\x00" * 160)
    body = path.read_bytes()
    return (
        AudioArtifact(
            artifact_id="audio-1",
            video_id="video-1",
            relative_path="audio/silence.wav",
            content_hash=hashlib.sha256(body).hexdigest(),
            byte_count=len(body),
            duration_seconds=1,
        ),
        path,
    )


def _adapter(executor: _FakeWhisperExecutor) -> MlxWhisperAdapter:
    return MlxWhisperAdapter(
        executor=executor,
        cache=InMemoryTranscriptionCache(),
        clock=lambda: FIXED_NOW,
    )


def test_fake_executor_is_cached_and_receives_frozen_decode_policy(tmp_path: Path) -> None:
    audio, path = _synthetic_wav(tmp_path)
    executor = _FakeWhisperExecutor(WhisperResponse(text="offline text", language="en"))
    adapter = _adapter(executor)

    first = adapter.transcribe(
        audio,
        audio_path=path,
        resources=AudioResourceSnapshot(100, 100),
    )
    second = adapter.transcribe(
        audio,
        audio_path=path,
        resources=AudioResourceSnapshot(100, 100),
    )

    assert first.text == "offline text"
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert first.cache_key == second.cache_key
    assert len(executor.calls) == 1
    _, policy = executor.calls[0]
    assert policy.task == "transcribe"
    assert policy.temperature == 0.0
    assert policy.word_timestamps is False
    assert policy.fp16 is True
    assert policy.initial_prompt is None


def test_duration_and_resource_rejection_happen_before_fake_execution(tmp_path: Path) -> None:
    audio, path = _synthetic_wav(tmp_path)
    executor = _FakeWhisperExecutor(WhisperResponse(text="never", language="en"))
    adapter = _adapter(executor)

    with pytest.raises(WhisperAdapterError) as duration:
        adapter.transcribe(
            audio,
            audio_path=path,
            resources=AudioResourceSnapshot(100, 100),
            policy=TranscriptionPolicy(
                max_duration_seconds=0,
                max_audio_bytes=audio.byte_count,
                min_free_disk_gib=1,
                min_available_memory_gib=1,
            ),
        )
    assert duration.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert duration.value.decision is DurationDecision.DURATION_LIMIT_EXCEEDED
    assert path.exists()

    with pytest.raises(WhisperAdapterError) as resources:
        adapter.transcribe(
            audio,
            audio_path=path,
            resources=AudioResourceSnapshot(0, 100),
        )
    assert resources.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert len(executor.calls) == 0


def test_fake_errors_are_typed_without_leaking_paths_or_model_output(tmp_path: Path) -> None:
    audio, path = _synthetic_wav(tmp_path)
    executor = _FakeWhisperExecutor(TimeoutError(f"{path} SECRET transcript"))

    with pytest.raises(WhisperAdapterError) as raised:
        _adapter(executor).transcribe(
            audio,
            audio_path=path,
            resources=AudioResourceSnapshot(100, 100),
        )

    assert raised.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert raised.value.error.retryable is True
    assert str(path) not in raised.value.error.message
    assert "SECRET" not in raised.value.error.message
    assert path.exists()


def test_fake_response_must_contain_a_non_empty_transcript(tmp_path: Path) -> None:
    audio, path = _synthetic_wav(tmp_path)
    executor = _FakeWhisperExecutor(WhisperResponse(text="   ", language="en"))

    with pytest.raises(WhisperAdapterError) as raised:
        _adapter(executor).transcribe(
            audio,
            audio_path=path,
            resources=AudioResourceSnapshot(100, 100),
        )

    assert raised.value.error.code is ErrorCode.INVALID_RESPONSE


def test_malformed_executor_result_is_mapped_to_a_typed_error(tmp_path: Path) -> None:
    audio, path = _synthetic_wav(tmp_path)
    executor = _FakeWhisperExecutor(cast(WhisperResponse, object()))

    with pytest.raises(WhisperAdapterError) as raised:
        _adapter(executor).transcribe(
            audio,
            audio_path=path,
            resources=AudioResourceSnapshot(100, 100),
        )

    assert raised.value.error.code is ErrorCode.INVALID_RESPONSE


def test_phase_a_adapter_does_not_import_a_model_or_system_decoder() -> None:
    source_path = Path(__file__).parents[2] / "src" / "youtube_intel" / "providers" / "whisper.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )

    assert "mlx_whisper" not in imported_modules
    assert "subprocess" not in imported_modules
