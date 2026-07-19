"""Deterministic local-scoring sampling, cache, and threshold policy.

This module deliberately owns no network or SQLite implementation.  It produces
the frozen domain contracts and keeps model suggestions distinct from the
application's configured summary threshold.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, NoReturn, Protocol

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    AppError,
    DiagnosticEntry,
    ErrorCode,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringInput,
    ScoringOutcome,
    ScoringProvider,
    TranscriptSample,
    VideoMetadata,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactWrite,
    ProviderCallCompletion,
    ProviderCallRecord,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderReservation,
    RetentionClass,
    ScoringSummaryWrite,
    StorageRoot,
    build_provider_request_hash,
)

PROMPT_VERSION: Final = "scoring-prompt-v1"
SCHEMA_VERSION: Final = "score-result-v1"
SAMPLING_VERSION: Final = "sampling-v1"
_SCORING_OPERATION: Final = "local-scoring"
_RAW_ARTIFACT_PRODUCER_VERSION: Final = "ollama-raw-v1"
_STRUCTURED_ARTIFACT_PRODUCER_VERSION: Final = "scoring-structured-v1"
_RAW_ARTIFACT_RETENTION: Final = timedelta(days=30)
_MAX_PERSISTED_ARTIFACT_BYTES: Final = 1_000_000
_RECOVERY_PRIMARY_ARTIFACT_SUFFIX: Final = "recovery-primary"
_CLOCK = Callable[[], datetime]


class ScoringCache(Protocol):
    """Cache boundary keyed by the canonical primary scoring request hash."""

    def get(self, request_hash: str) -> ScoreResult | None: ...

    def put(self, result: ScoreResult) -> None: ...


class InMemoryScoringCache:
    """Small deterministic cache suitable for offline tests and local composition."""

    def __init__(self) -> None:
        self._results: dict[str, ScoreResult] = {}

    def get(self, request_hash: str) -> ScoreResult | None:
        return self._results.get(request_hash)

    def put(self, result: ScoreResult) -> None:
        self._results[result.request_hash] = result


class _RawResponseScoringProvider(Protocol):
    def score(self, scoring_input: ScoringInput) -> ScoreResult: ...

    def consume_raw_response(self, *, request_hash: str) -> str: ...

    def _repair_saved_primary_response(
        self,
        *,
        primary_raw_response: str,
        scoring_input: ScoringInput,
    ) -> ScoreResult: ...


class _ScoringRepository(Protocol):
    def reserve_provider_call(
        self,
        request: ProviderCallRequest,
        *,
        owner: str,
        lease_until: datetime,
        available_at: datetime,
        now: datetime,
    ) -> ProviderReservation: ...

    def complete_stage(
        self,
        *,
        job_id: str,
        owner: str,
        video_id: str,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        artifacts: tuple[ArtifactWrite, ...],
        provider_call: ProviderCallCompletion | None,
        now: datetime,
        scoring_summary: ScoringSummaryWrite | None = None,
    ) -> object: ...

    def fail_provider_call(
        self,
        request_hash: str,
        *,
        owner: str,
        retryable: bool,
        available_at: datetime,
        error_code: ErrorCode,
        error_message: str,
        now: datetime,
    ) -> object: ...

    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None: ...

    def upsert_artifact(
        self,
        artifact: ArtifactWrite,
        *,
        now: datetime,
    ) -> ArtifactRecord: ...


@dataclass(frozen=True, slots=True)
class ScoringJobContext:
    """Owned SCORING job identity required for repository-backed completion."""

    job_id: str
    owner: str
    pipeline_version: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (self.job_id, self.owner, self.pipeline_version)
        ):
            msg = "scoring job context values must be non-empty"
            raise ValueError(msg)


class ScoringPersistenceError(Exception):
    """Safe application error from repository-backed scoring composition."""

    def __init__(self, error: AppError) -> None:
        super().__init__(error.message)
        self.error = error


def _raise_sanitized_persistence_error(error: AppError) -> NoReturn:
    """Raise only after provider payloads and artifact paths left the traceback."""

    raise ScoringPersistenceError(error)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _normalized_scoring_input_hash(
    *,
    video: VideoMetadata,
    sample: TranscriptSample,
    language: str,
    settings: LocalScoringSettings,
) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "metadata": [
                    video.video_id,
                    video.title,
                    video.channel_name,
                    video.published_at.astimezone(UTC).isoformat(),
                    video.duration_seconds,
                    video.default_language,
                    language,
                    video.description[: settings.max_description_chars],
                ],
                "transcript_content_hash": sample.source_content_hash,
                "sample": {
                    "head": sample.head,
                    "body": sample.body,
                    "tail": sample.tail,
                    "selected_char_count": sample.selected_char_count,
                    "sampling_version": sample.sampling_version,
                },
                "language": language,
                "model": settings.model,
                "temperature": settings.temperature,
                "max_output_tokens": settings.max_output_tokens,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
            }
        )
    )


def sample_transcript(transcript_text: str, *, max_chars: int) -> TranscriptSample:
    """Select the ADR-007 ``sampling-v1`` head/centre/tail transcript sample."""

    if max_chars < 3:
        msg = "max_chars must be at least 3"
        raise ValueError(msg)
    if len(transcript_text) < 3:
        msg = "transcript_text must contain at least 3 characters"
        raise ValueError(msg)

    transcript_length = len(transcript_text)
    if transcript_length <= max_chars:
        head = transcript_text
        body = ""
        tail = ""
    else:
        head_length = (max_chars + 2) // 3
        body_length = (max_chars + 1) // 3
        tail_length = max_chars // 3
        available_body_start = head_length
        available_body_end = transcript_length - tail_length
        available_body_length = available_body_end - available_body_start
        body_start = available_body_start + (available_body_length - body_length) // 2
        head = transcript_text[:head_length]
        body = transcript_text[body_start : body_start + body_length]
        tail = transcript_text[available_body_end:]

    return TranscriptSample(
        head=head,
        body=body,
        tail=tail,
        selected_char_count=len(head) + len(body) + len(tail),
        source_content_hash=_sha256_text(transcript_text),
        sampling_version=SAMPLING_VERSION,
    )


def build_scoring_input(
    *,
    video: VideoMetadata,
    transcript_text: str,
    language: str,
    settings: LocalScoringSettings,
) -> ScoringInput:
    """Build one versioned scoring input and its provider-call cache key."""

    if not language or language != language.strip():
        msg = "language must be a non-empty value without surrounding whitespace"
        raise ValueError(msg)

    sample = sample_transcript(
        transcript_text,
        max_chars=settings.max_transcript_chars,
    )
    normalized_input_hash = _normalized_scoring_input_hash(
        video=video,
        sample=sample,
        language=language,
        settings=settings,
    )
    request_hash = build_provider_request_hash(
        operation=_SCORING_OPERATION,
        normalized_input_hash=normalized_input_hash,
        provider="ollama",
        model=settings.model,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    return ScoringInput(
        video=video,
        sample=sample,
        transcript_content_hash=sample.source_content_hash,
        language=language,
        request_hash=request_hash,
    )


class ScoringService:
    """Apply cache and threshold policy around a structural scoring Provider."""

    def __init__(
        self,
        *,
        provider: ScoringProvider,
        settings: LocalScoringSettings,
        summary_threshold: float,
        cache: ScoringCache,
        clock: _CLOCK = _utcnow,
    ) -> None:
        if not 0 <= summary_threshold <= 10:
            msg = "summary_threshold must be in 0..10"
            raise ValueError(msg)
        self._provider = provider
        self._settings = settings
        self._summary_threshold = summary_threshold
        self._cache = cache
        self._clock = clock

    def score(
        self,
        *,
        video: VideoMetadata,
        transcript_text: str,
        language: str,
    ) -> ScoringOutcome:
        scoring_input = build_scoring_input(
            video=video,
            transcript_text=transcript_text,
            language=language,
            settings=self._settings,
        )
        started_at = self._clock()
        cached = self._cache.get(scoring_input.request_hash)
        diagnostics: list[DiagnosticEntry] = []
        if cached is None:
            result = self._provider.score(scoring_input)
            if result.request_hash != scoring_input.request_hash:
                msg = "scoring provider returned a result for a different request"
                raise ValueError(msg)
            self._cache.put(result)
        else:
            result = cached
            diagnostics.append(
                DiagnosticEntry(
                    code="CACHE_HIT",
                    message="reused cached structured local-scoring result",
                )
            )
        final_should_summarize = result.score >= self._summary_threshold
        model_disagrees = result.should_summarize != final_should_summarize
        if model_disagrees:
            diagnostics.append(
                DiagnosticEntry(
                    code="MODEL_POLICY_DISAGREEMENT",
                    message="configured summary threshold overrides the model suggestion",
                )
            )
        finished_at = self._clock()
        return ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=self._summary_threshold,
                final_should_summarize=final_should_summarize,
                model_disagrees=model_disagrees,
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=started_at,
                finished_at=finished_at,
                diagnostics=tuple(diagnostics),
            ),
        )


class RepositoryBackedScoringService:
    """Persist a verified local score with its SCORING stage in one transaction."""

    def __init__(
        self,
        *,
        provider: _RawResponseScoringProvider,
        settings: LocalScoringSettings,
        summary_threshold: float,
        repository: _ScoringRepository,
        context: ScoringJobContext,
        artifact_root: Path,
        clock: _CLOCK = _utcnow,
        provider_lease_seconds: int = 300,
    ) -> None:
        if not 0 <= summary_threshold <= 10:
            msg = "summary_threshold must be in 0..10"
            raise ValueError(msg)
        if provider_lease_seconds <= 0:
            msg = "provider_lease_seconds must be positive"
            raise ValueError(msg)
        self._provider = provider
        self._settings = settings
        self._summary_threshold = summary_threshold
        self._repository = repository
        self._context = context
        self._artifact_root = artifact_root
        self._clock = clock
        self._provider_lease_seconds = provider_lease_seconds

    def score(
        self,
        *,
        video: VideoMetadata,
        transcript_text: str,
        language: str,
    ) -> ScoringOutcome:
        failure: AppError | None = None
        try:
            return self._score(
                video=video,
                transcript_text=transcript_text,
                language=language,
            )
        except ScoringPersistenceError as error:
            failure = error.error
        except Exception:
            failure = self._error(
                ErrorCode.LOCAL_RESOURCE,
                "local scoring failed before stage completion",
                retryable=True,
                video_id=video.video_id,
            )
        del self
        del video
        del transcript_text
        del language
        _raise_sanitized_persistence_error(
            failure
            if failure is not None
            else AppError(
                code=ErrorCode.LOCAL_RESOURCE,
                message="local scoring failed before stage completion",
                retryable=True,
                stage=ProcessingStage.SCORING,
            )
        )

    def _score(
        self,
        *,
        video: VideoMetadata,
        transcript_text: str,
        language: str,
    ) -> ScoringOutcome:
        scoring_input = build_scoring_input(
            video=video,
            transcript_text=transcript_text,
            language=language,
            settings=self._settings,
        )
        now = self._clock()
        request = self._provider_request(scoring_input)
        reservation = self._reserve(request, now=now, video_id=video.video_id)
        if not reservation.acquired:
            if reservation.record.status is ProviderCallStatus.SUCCEEDED:
                result = self._load_verified_cached_result(
                    request=request,
                    provider_call=reservation.record,
                    video_id=video.video_id,
                )
                outcome = self._outcome(
                    result,
                    started_at=now,
                    finished_at=self._clock(),
                    cache_hit=True,
                )
                self._complete_stage(
                    outcome=outcome,
                    artifacts=(),
                    provider_call=None,
                    now=now,
                    video_id=video.video_id,
                )
                return outcome
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    "local scoring provider call is already reserved or unavailable",
                    retryable=True,
                    video_id=video.video_id,
                )
            )

        try:
            recovery_raw_response = self._load_verified_recovery_raw_response(
                request=request,
                video_id=video.video_id,
                now=now,
            )
        except ScoringPersistenceError as error:
            self._record_failure(
                request_hash=request.request_hash,
                error=error.error,
                now=now,
            )
            raise
        if recovery_raw_response is None:
            result, raw_response = self._call_provider(
                scoring_input=scoring_input,
                request=request,
                now=now,
            )
        else:
            result, raw_response = self._repair_saved_primary_response(
                primary_raw_response=recovery_raw_response,
                scoring_input=scoring_input,
                request=request,
                now=now,
            )
        outcome = self._outcome(
            result,
            started_at=now,
            finished_at=self._clock(),
            cache_hit=False,
        )
        try:
            artifacts, written_paths = self._write_artifacts(
                result=result,
                raw_response=raw_response,
                request=request,
                video_id=video.video_id,
                now=now,
            )
        except ScoringPersistenceError:
            self._record_failure(
                request_hash=request.request_hash,
                error=self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring artifact write failed",
                    retryable=True,
                    video_id=video.video_id,
                ),
                now=now,
            )
            raise
        try:
            self._complete_stage(
                outcome=outcome,
                artifacts=artifacts,
                provider_call=ProviderCallCompletion(
                    request_hash=request.request_hash,
                    response_artifact_id=artifacts[0].artifact_id,
                    input_tokens=None,
                    output_tokens=None,
                    cost_microusd=None,
                ),
                now=now,
                video_id=video.video_id,
            )
        except ScoringPersistenceError:
            self._remove_written_paths(written_paths)
            self._record_failure(
                request_hash=request.request_hash,
                error=self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring persistence failed",
                    retryable=True,
                    video_id=video.video_id,
                ),
                now=now,
            )
            raise
        return outcome

    def _provider_request(self, scoring_input: ScoringInput) -> ProviderCallRequest:
        normalized_input_hash = _normalized_scoring_input_hash(
            video=scoring_input.video,
            sample=scoring_input.sample,
            language=scoring_input.language,
            settings=self._settings,
        )
        request = ProviderCallRequest(
            operation=_SCORING_OPERATION,
            normalized_input_hash=normalized_input_hash,
            provider="ollama",
            model=self._settings.model,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            deterministic_artifact_key=f"scoring/{scoring_input.request_hash}/raw",
        )
        if request.request_hash != scoring_input.request_hash:
            msg = "scoring request hash does not match the frozen provider contract"
            raise ValueError(msg)
        return request

    def _reserve(
        self,
        request: ProviderCallRequest,
        *,
        now: datetime,
        video_id: str,
    ) -> ProviderReservation:
        try:
            return self._repository.reserve_provider_call(
                request,
                owner=self._context.owner,
                lease_until=now + timedelta(seconds=self._provider_lease_seconds),
                available_at=now,
                now=now,
            )
        except Exception:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring provider call reservation failed",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None

    def _call_provider(
        self,
        *,
        scoring_input: ScoringInput,
        request: ProviderCallRequest,
        now: datetime,
    ) -> tuple[ScoreResult, str]:
        failure: AppError | None = None
        result: ScoreResult | None = None
        raw_response: str | None = None
        try:
            result = self._provider.score(scoring_input)
            if result.request_hash != request.request_hash:
                raise ValueError("scoring provider returned a result for a different request")
            raw_response = self._provider.consume_raw_response(
                request_hash=request.request_hash
            )
        except Exception as error:
            candidate = getattr(error, "error", None)
            if isinstance(candidate, AppError):
                failure = candidate
            else:
                failure = self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "local scoring provider returned an invalid result",
                    retryable=True,
                    video_id=scoring_input.video.video_id,
                )
        if failure is not None:
            recovery_raw_response = self._consume_raw_response_if_available(
                request_hash=request.request_hash
            )
            if recovery_raw_response is not None:
                try:
                    self._persist_recovery_primary_response(
                        raw_response=recovery_raw_response,
                        request=request,
                        video_id=scoring_input.video.video_id,
                        now=now,
                    )
                except ScoringPersistenceError as persistence_error:
                    failure = persistence_error.error
            self._record_failure(
                request_hash=request.request_hash,
                error=failure,
                now=now,
            )
            raise ScoringPersistenceError(failure)
        if result is None or raw_response is None:
            fallback = self._error(
                ErrorCode.INVALID_RESPONSE,
                "local scoring provider returned no result",
                retryable=True,
                video_id=scoring_input.video.video_id,
            )
            self._record_failure(
                request_hash=request.request_hash,
                error=fallback,
                now=now,
            )
            raise ScoringPersistenceError(fallback)
        return result, raw_response

    def _repair_saved_primary_response(
        self,
        *,
        primary_raw_response: str,
        scoring_input: ScoringInput,
        request: ProviderCallRequest,
        now: datetime,
    ) -> tuple[ScoreResult, str]:
        failure: AppError | None = None
        result: ScoreResult | None = None
        raw_response: str | None = None
        try:
            result = self._provider._repair_saved_primary_response(
                primary_raw_response=primary_raw_response,
                scoring_input=scoring_input,
            )
            if result.request_hash != request.request_hash:
                raise ValueError("repaired scoring result belongs to a different request")
            raw_response = self._provider.consume_raw_response(
                request_hash=request.request_hash
            )
        except Exception as error:
            candidate = getattr(error, "error", None)
            if isinstance(candidate, AppError):
                failure = candidate
            else:
                failure = self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "saved local scoring response could not be repaired",
                    retryable=True,
                    video_id=scoring_input.video.video_id,
                )
        if failure is not None:
            self._record_failure(
                request_hash=request.request_hash,
                error=failure,
                now=now,
            )
            raise ScoringPersistenceError(failure)
        if result is None or raw_response is None:
            fallback = self._error(
                ErrorCode.INVALID_RESPONSE,
                "saved local scoring response produced no result",
                retryable=True,
                video_id=scoring_input.video.video_id,
            )
            self._record_failure(
                request_hash=request.request_hash,
                error=fallback,
                now=now,
            )
            raise ScoringPersistenceError(fallback)
        return result, raw_response

    def _consume_raw_response_if_available(self, *, request_hash: str) -> str | None:
        try:
            return self._provider.consume_raw_response(request_hash=request_hash)
        except Exception:
            return None

    def _persist_recovery_primary_response(
        self,
        *,
        raw_response: str,
        request: ProviderCallRequest,
        video_id: str,
        now: datetime,
    ) -> None:
        raw_content = raw_response.encode("utf-8")
        if len(raw_content) > _MAX_PERSISTED_ARTIFACT_BYTES:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "local scoring recovery response exceeded its safety limit",
                    retryable=True,
                    video_id=video_id,
                )
            )
        artifact_key = self._recovery_primary_artifact_key(request)
        content_hash = hashlib.sha256(raw_content).hexdigest()
        artifact = ArtifactWrite(
            artifact_id=(
                "scoring-recovery-"
                + _sha256_text(artifact_key + content_hash)
            ),
            artifact_key=artifact_key,
            video_id=video_id,
            job_id=self._context.job_id,
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=self._recovery_primary_relative_path(request),
            content_hash=content_hash,
            provider=request.provider,
            model=request.model,
            producer_version=_RAW_ARTIFACT_PRODUCER_VERSION,
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=now + _RAW_ARTIFACT_RETENTION,
        )
        written_paths: tuple[Path, ...] = ()
        try:
            path, created = self._write_artifact_file(
                relative_path=artifact.relative_path,
                content=raw_content,
                content_hash=content_hash,
            )
            if created:
                written_paths = (path,)
            self._repository.upsert_artifact(artifact, now=now)
        except Exception:
            self._remove_written_paths(written_paths)
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring recovery response could not be persisted",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None

    def _load_verified_recovery_raw_response(
        self,
        *,
        request: ProviderCallRequest,
        video_id: str,
        now: datetime,
    ) -> str | None:
        artifact_key = self._recovery_primary_artifact_key(request)
        artifact = self._repository.get_artifact_by_key(artifact_key)
        if artifact is None:
            return None
        if (
            artifact.artifact_id
            != "scoring-recovery-"
            + _sha256_text(artifact_key + artifact.content_hash)
            or artifact.artifact_key != artifact_key
            or artifact.video_id != video_id
            or artifact.job_id is None
            or artifact.kind is not ArtifactKind.SCORING_RAW
            or artifact.storage_root is not StorageRoot.DATA
            or artifact.relative_path != self._recovery_primary_relative_path(request)
            or artifact.provider != request.provider
            or artifact.model != request.model
            or artifact.producer_version != _RAW_ARTIFACT_PRODUCER_VERSION
            or artifact.retention_class is not RetentionClass.RAW_RESPONSE_30D
            or artifact.expires_at is None
            or artifact.expires_at <= now
        ):
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "local scoring recovery artifact provenance is invalid",
                    retryable=True,
                    video_id=video_id,
                )
            )
        try:
            path = self._artifact_path(artifact.relative_path)
            with path.open("rb") as handle:
                raw_content = handle.read(_MAX_PERSISTED_ARTIFACT_BYTES + 1)
            if (
                len(raw_content) > _MAX_PERSISTED_ARTIFACT_BYTES
                or hashlib.sha256(raw_content).hexdigest() != artifact.content_hash
            ):
                raise ValueError("recovery artifact verification failed")
            return raw_content.decode("utf-8")
        except Exception:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "local scoring recovery artifact is unavailable or invalid",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None

    @staticmethod
    def _recovery_primary_artifact_key(request: ProviderCallRequest) -> str:
        return f"scoring/{request.request_hash}/{_RECOVERY_PRIMARY_ARTIFACT_SUFFIX}"

    @staticmethod
    def _recovery_primary_relative_path(request: ProviderCallRequest) -> str:
        return (
            f"scoring/{request.request_hash}/"
            f"{_RECOVERY_PRIMARY_ARTIFACT_SUFFIX}.json"
        )

    def _write_artifacts(
        self,
        *,
        result: ScoreResult,
        raw_response: str,
        request: ProviderCallRequest,
        video_id: str,
        now: datetime,
    ) -> tuple[tuple[ArtifactWrite, ArtifactWrite], tuple[Path, ...]]:
        raw_content = raw_response.encode("utf-8")
        structured_content = _canonical_json(result.model_dump(mode="json")).encode("utf-8")
        raw_key = request.deterministic_artifact_key
        structured_key = f"scoring/{request.request_hash}/structured"
        raw_relative_path = f"scoring/{request.request_hash}/raw.json"
        structured_relative_path = f"scoring/{request.request_hash}/structured.json"
        raw_hash = hashlib.sha256(raw_content).hexdigest()
        structured_hash = hashlib.sha256(structured_content).hexdigest()
        artifacts = (
            ArtifactWrite(
                artifact_id=f"scoring-raw-{_sha256_text(raw_key + raw_hash)}",
                artifact_key=raw_key,
                video_id=video_id,
                job_id=self._context.job_id,
                kind=ArtifactKind.SCORING_RAW,
                storage_root=StorageRoot.DATA,
                relative_path=raw_relative_path,
                content_hash=raw_hash,
                provider=result.provider,
                model=result.model,
                producer_version=_RAW_ARTIFACT_PRODUCER_VERSION,
                retention_class=RetentionClass.RAW_RESPONSE_30D,
                expires_at=now + _RAW_ARTIFACT_RETENTION,
            ),
            ArtifactWrite(
                artifact_id=(
                    "scoring-structured-"
                    + _sha256_text(structured_key + structured_hash)
                ),
                artifact_key=structured_key,
                video_id=video_id,
                job_id=self._context.job_id,
                kind=ArtifactKind.SCORING_STRUCTURED,
                storage_root=StorageRoot.DATA,
                relative_path=structured_relative_path,
                content_hash=structured_hash,
                provider=result.provider,
                model=result.model,
                producer_version=_STRUCTURED_ARTIFACT_PRODUCER_VERSION,
                retention_class=RetentionClass.LONG_LIVED,
                expires_at=None,
            ),
        )
        written_paths: list[Path] = []
        try:
            for relative_path, content, content_hash in (
                (raw_relative_path, raw_content, raw_hash),
                (structured_relative_path, structured_content, structured_hash),
            ):
                path, created = self._write_artifact_file(
                    relative_path=relative_path,
                    content=content,
                    content_hash=content_hash,
                )
                if created:
                    written_paths.append(path)
        except Exception:
            self._remove_written_paths(tuple(written_paths))
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring artifact write failed",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None
        return artifacts, tuple(written_paths)

    def _write_artifact_file(
        self,
        *,
        relative_path: str,
        content: bytes,
        content_hash: str,
    ) -> tuple[Path, bool]:
        root = self._artifact_root.resolve()
        path = (root / relative_path).resolve()
        if root != path and root not in path.parents:
            msg = "scoring artifact path escapes the configured root"
            raise ValueError(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = path.read_bytes()
            if hashlib.sha256(existing).hexdigest() != content_hash:
                msg = "scoring artifact path already contains different content"
                raise ValueError(msg)
            return path, False
        path.write_bytes(content)
        return path, True

    def _load_verified_cached_result(
        self,
        *,
        request: ProviderCallRequest,
        provider_call: ProviderCallRecord,
        video_id: str,
    ) -> ScoreResult:
        raw = self._repository.get_artifact_by_key(request.deterministic_artifact_key)
        structured = self._repository.get_artifact_by_key(
            f"scoring/{request.request_hash}/structured"
        )
        if raw is None or structured is None:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "verified local scoring artifacts are unavailable",
                    retryable=True,
                    video_id=video_id,
                )
            )
        raw_path = self._artifact_path(raw.relative_path)
        structured_path = self._artifact_path(structured.relative_path)
        try:
            raw_content = raw_path.read_bytes()
            structured_content = structured_path.read_bytes()
            if (
                len(raw_content) > _MAX_PERSISTED_ARTIFACT_BYTES
                or len(structured_content) > _MAX_PERSISTED_ARTIFACT_BYTES
                or hashlib.sha256(raw_content).hexdigest() != raw.content_hash
                or hashlib.sha256(structured_content).hexdigest()
                != structured.content_hash
            ):
                raise ValueError("scoring artifact verification failed")
            result = ScoreResult.model_validate_json(structured_content)
        except Exception:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "verified local scoring artifacts are invalid",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None
        if (
            raw.kind is not ArtifactKind.SCORING_RAW
            or structured.kind is not ArtifactKind.SCORING_STRUCTURED
            or raw.video_id != video_id
            or structured.video_id != video_id
            or raw.artifact_id != provider_call.response_artifact_id
            or result.request_hash != request.request_hash
            or result.provider != request.provider
            or result.model != request.model
        ):
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "verified local scoring artifact provenance is invalid",
                    retryable=True,
                    video_id=video_id,
                )
            )
        return result

    def _artifact_path(self, relative_path: str) -> Path:
        root = self._artifact_root.resolve()
        path = (root / relative_path).resolve()
        if root != path and root not in path.parents:
            msg = "scoring artifact path escapes the configured root"
            raise ValueError(msg)
        return path

    def _complete_stage(
        self,
        *,
        outcome: ScoringOutcome,
        artifacts: tuple[ArtifactWrite, ...],
        provider_call: ProviderCallCompletion | None,
        now: datetime,
        video_id: str,
    ) -> None:
        try:
            self._repository.complete_stage(
                job_id=self._context.job_id,
                owner=self._context.owner,
                video_id=video_id,
                expected_status=PipelineStatus.TRANSCRIPT_READY,
                target_status=PipelineStatus.SCORED,
                pipeline_version=self._context.pipeline_version,
                artifacts=artifacts,
                provider_call=provider_call,
                scoring_summary=ScoringSummaryWrite(
                    score=outcome.result.score,
                    should_summarize=outcome.decision.final_should_summarize,
                ),
                now=now,
            )
        except Exception:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring stage completion failed",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None

    def _record_failure(
        self,
        *,
        request_hash: str,
        error: AppError,
        now: datetime,
    ) -> None:
        try:
            self._repository.fail_provider_call(
                request_hash,
                owner=self._context.owner,
                retryable=error.retryable,
                available_at=now,
                error_code=error.code,
                error_message=error.message,
                now=now,
            )
        except Exception:
            pass

    def _outcome(
        self,
        result: ScoreResult,
        *,
        started_at: datetime,
        finished_at: datetime,
        cache_hit: bool,
    ) -> ScoringOutcome:
        diagnostics: list[DiagnosticEntry] = []
        if cache_hit:
            diagnostics.append(
                DiagnosticEntry(
                    code="PERSISTED_CACHE_HIT",
                    message="reused a verified persisted local-scoring result",
                )
            )
        final_should_summarize = result.score >= self._summary_threshold
        model_disagrees = result.should_summarize != final_should_summarize
        if model_disagrees:
            diagnostics.append(
                DiagnosticEntry(
                    code="MODEL_POLICY_DISAGREEMENT",
                    message="configured summary threshold overrides the model suggestion",
                )
            )
        return ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=self._summary_threshold,
                final_should_summarize=final_should_summarize,
                model_disagrees=model_disagrees,
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=started_at,
                finished_at=finished_at,
                diagnostics=tuple(diagnostics),
            ),
        )

    @staticmethod
    def _error(
        code: ErrorCode,
        message: str,
        *,
        retryable: bool,
        video_id: str | None,
    ) -> AppError:
        return AppError(
            code=code,
            message=message,
            retryable=retryable,
            video_id=video_id,
            stage=ProcessingStage.SCORING,
        )

    @staticmethod
    def _remove_written_paths(paths: tuple[Path, ...]) -> None:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


__all__ = [
    "InMemoryScoringCache",
    "PROMPT_VERSION",
    "RepositoryBackedScoringService",
    "SAMPLING_VERSION",
    "SCHEMA_VERSION",
    "ScoringCache",
    "ScoringJobContext",
    "ScoringPersistenceError",
    "ScoringService",
    "build_scoring_input",
    "sample_transcript",
]
