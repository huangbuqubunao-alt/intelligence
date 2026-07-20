"""Model-free MLX Whisper adapter boundary for Phase A.

The official ``mlx_whisper.transcribe`` API may load or download a model. This
phase therefore accepts only an injected executor, allowing the adapter's policy,
cache, and error semantics to be verified without importing or invoking MLX.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Protocol

from youtube_intel.domain import (
    AppError,
    ErrorCode,
    ProcessingStage,
    ProviderCallMetadata,
)
from youtube_intel.transcription import (
    AudioArtifact,
    AudioResourceSnapshot,
    DurationDecision,
    InMemoryTranscriptionCache,
    TranscriptionCache,
    TranscriptionPolicy,
    build_transcription_cache_key,
)

_PROVIDER_NAME = "mlx-whisper"
_DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
_DEFAULT_REVISION = "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"
_DEFAULT_POLICY_VERSION = "mlx-whisper-v1"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _provider_version() -> str:
    try:
        return version("mlx-whisper")
    except PackageNotFoundError:
        return "unknown"


@dataclass(frozen=True, slots=True)
class WhisperDecodePolicy:
    """The frozen L-10 decode policy without free-form SDK kwargs."""

    model: str = _DEFAULT_MODEL
    model_revision: str = _DEFAULT_REVISION
    parameter_policy_version: str = _DEFAULT_POLICY_VERSION
    task: str = "transcribe"
    language_hint: str | None = None
    temperature: float = 0.0
    compression_ratio_threshold: float = 2.4
    logprob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    condition_on_previous_text: bool = True
    word_timestamps: bool = False
    initial_prompt: None = None
    fp16: bool = True

    def __post_init__(self) -> None:
        if (
            not self.model
            or not self.model_revision
            or not self.parameter_policy_version
            or self.task != "transcribe"
            or self.temperature != 0.0
            or self.compression_ratio_threshold != 2.4
            or self.logprob_threshold != -1.0
            or self.no_speech_threshold != 0.6
            or not self.condition_on_previous_text
            or self.word_timestamps
            or self.initial_prompt is not None
            or not self.fp16
        ):
            raise ValueError("Whisper decode policy must match mlx-whisper-v1")
        if self.language_hint is not None and not self.language_hint.strip():
            raise ValueError("language_hint must be None or a non-empty language tag")


@dataclass(frozen=True, slots=True)
class WhisperResponse:
    """Narrow, typed result expected from the injected executor."""

    text: str
    language: str


class WhisperExecutor(Protocol):
    def transcribe(self, audio_path: Path, policy: WhisperDecodePolicy) -> WhisperResponse: ...


@dataclass(frozen=True, slots=True)
class WhisperTranscription:
    text: str
    language: str
    cache_key: str
    cache_hit: bool
    call: ProviderCallMetadata


class WhisperAdapterError(Exception):
    def __init__(self, error: AppError, decision: DurationDecision) -> None:
        super().__init__(error.message)
        self.error = error
        self.decision = decision


class MlxWhisperAdapter:
    """A cache-aware Adapter that does not own model loading in Phase A."""

    def __init__(
        self,
        *,
        executor: WhisperExecutor,
        cache: TranscriptionCache[WhisperTranscription] | None = None,
        decode_policy: WhisperDecodePolicy | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._executor = executor
        self._cache = cache if cache is not None else InMemoryTranscriptionCache()
        self._decode_policy = (
            decode_policy if decode_policy is not None else WhisperDecodePolicy()
        )
        self._clock = clock

    def transcribe(
        self,
        audio: AudioArtifact,
        *,
        audio_path: Path,
        resources: AudioResourceSnapshot,
        policy: TranscriptionPolicy | None = None,
    ) -> WhisperTranscription:
        effective_policy = policy if policy is not None else TranscriptionPolicy()
        decision = effective_policy.evaluate(audio, resources)
        if decision is not DurationDecision.PERMITTED:
            raise self._policy_error(audio.video_id, decision)

        cache_key = build_transcription_cache_key(
            audio_content_hash=audio.content_hash,
            language_hint=self._decode_policy.language_hint,
            model=self._decode_policy.model,
            model_revision=self._decode_policy.model_revision,
            parameter_policy_version=self._decode_policy.parameter_policy_version,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return WhisperTranscription(
                text=cached.text,
                language=cached.language,
                cache_key=cache_key,
                cache_hit=True,
                call=cached.call,
            )

        started = self._clock().astimezone(UTC)
        try:
            response = self._executor.transcribe(audio_path, self._decode_policy)
        except TimeoutError as exc:
            raise self._execution_error(
                ErrorCode.LOCAL_RESOURCE,
                "local Whisper execution timed out",
                retryable=True,
                video_id=audio.video_id,
                decision=decision,
            ) from exc
        except (MemoryError, OSError) as exc:
            raise self._execution_error(
                ErrorCode.LOCAL_RESOURCE,
                "local Whisper resource is unavailable",
                retryable=True,
                video_id=audio.video_id,
                decision=decision,
            ) from exc
        except ValueError as exc:
            raise self._execution_error(
                ErrorCode.INVALID_RESPONSE,
                "local Whisper response is invalid",
                retryable=False,
                video_id=audio.video_id,
                decision=decision,
            ) from exc
        except Exception as exc:  # noqa: BLE001 - adapter maps unknown SDK failures.
            raise self._execution_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "local Whisper provider is unavailable",
                retryable=True,
                video_id=audio.video_id,
                decision=decision,
            ) from exc
        finished = self._clock().astimezone(UTC)

        if (
            not isinstance(response, WhisperResponse)
            or not response.text.strip()
            or not response.language.strip()
        ):
            raise self._execution_error(
                ErrorCode.INVALID_RESPONSE,
                "local Whisper response is invalid",
                retryable=False,
                video_id=audio.video_id,
                decision=decision,
            )

        result = WhisperTranscription(
            text=response.text,
            language=response.language,
            cache_key=cache_key,
            cache_hit=False,
            call=ProviderCallMetadata(
                provider=_PROVIDER_NAME,
                provider_version=_provider_version(),
                model=self._decode_policy.model,
                started_at=started,
                finished_at=finished,
            ),
        )
        self._cache.put(cache_key, result)
        return result

    @staticmethod
    def _policy_error(video_id: str, decision: DurationDecision) -> WhisperAdapterError:
        if decision is DurationDecision.DURATION_LIMIT_EXCEEDED:
            return MlxWhisperAdapter._execution_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                "audio exceeds the local transcription duration policy",
                retryable=False,
                video_id=video_id,
                decision=decision,
            )
        return MlxWhisperAdapter._execution_error(
            ErrorCode.LOCAL_RESOURCE,
            "audio exceeds the local transcription resource policy",
            retryable=False,
            video_id=video_id,
            decision=decision,
        )

    @staticmethod
    def _execution_error(
        code: ErrorCode,
        message: str,
        *,
        retryable: bool,
        video_id: str,
        decision: DurationDecision,
    ) -> WhisperAdapterError:
        return WhisperAdapterError(
            AppError(
                code=code,
                message=message,
                retryable=retryable,
                video_id=video_id,
                stage=ProcessingStage.TRANSCRIPT,
            ),
            decision,
        )


__all__ = [
    "MlxWhisperAdapter",
    "WhisperAdapterError",
    "WhisperDecodePolicy",
    "WhisperExecutor",
    "WhisperResponse",
    "WhisperTranscription",
]
