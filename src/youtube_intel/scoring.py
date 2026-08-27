"""Deterministic local-scoring sampling, cache, and threshold policy.

This module deliberately owns no network or SQLite implementation.  It produces
the frozen domain contracts and keeps model suggestions distinct from the
application's configured summary threshold.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Final, NoReturn, Protocol, cast

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    AppError,
    ContentQualityInput,
    ContentQualityResult,
    DiagnosticEntry,
    ErrorCode,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    QualityJudgeOperationInput,
    QualityPassAttestation,
    ScoreResult,
    ScoringCandidate,
    ScoringDecision,
    ScoringInput,
    ScoringOutcome,
    ScoringOutputLanguage,
    ScoringProvider,
    TranscriptSample,
    VideoMetadata,
    validate_score_result,
    validate_score_result_json,
)

if TYPE_CHECKING:
    from youtube_intel.quality import (
        QualityProvenanceAuthority,
        TrustedScoreResult,
        TrustedScoringContext,
    )
    from youtube_intel.state import (
        JobRecord,
        VideoRecord,
    )
from youtube_intel.state import (
    SCORING_LINEAGE_VERSION_V1,
    ArtifactKind,
    ArtifactRecord,
    ArtifactWrite,
    ConcurrencyConflict,
    IntegrityConflict,
    JobType,
    LeaseConflict,
    ProviderCallCompletion,
    ProviderCallRecord,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderReservation,
    RetentionClass,
    ScoringSummaryWrite,
    StageCompletionResult,
    StateStoreError,
    StorageRoot,
    _immediate_transaction,
    build_provider_request_hash,
    format_utc_datetime,
)

PROMPT_VERSION: Final = "scoring-prompt-v2"
SCHEMA_VERSION: Final = "score-result-v2"
SAMPLING_VERSION: Final = "sampling-v1"
_SCORING_OPERATION: Final = "local-scoring"
_RAW_ARTIFACT_PRODUCER_VERSION: Final = "ollama-raw-v2"
_STRUCTURED_ARTIFACT_PRODUCER_VERSION: Final = "scoring-structured-v2"
_RAW_ARTIFACT_RETENTION: Final = timedelta(days=30)
_MAX_PERSISTED_ARTIFACT_BYTES: Final = 1_000_000
_RECOVERY_PRIMARY_ARTIFACT_SUFFIX: Final = "recovery-primary"
_RECOVERY_REQUIRED_MARKER_PREFIX: Final = "SCORING_RECOVERY_REQUIRED:"
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
        result = self._results.get(request_hash)
        return None if result is None else validate_score_result(result)

    def put(self, result: ScoreResult) -> None:
        trusted = validate_score_result(result)
        self._results[trusted.request_hash] = trusted


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

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None: ...

    def get_video(self, video_id: str) -> VideoRecord | None: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...

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


class _ScoringCacheMiss(Exception):
    """A verified cache entry is stale and must not be returned."""


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
    output_language: ScoringOutputLanguage,
    model: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
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
                    video.description[:max_description_chars],
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
                "output_language": output_language,
                "model": model,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class ScoringRequestIdentity:
    """Canonical, pure scoring request identity with no authority semantics."""

    normalized_input_hash: str
    request_hash: str


def build_scoring_request_identity(
    *,
    scoring_input: ScoringInput,
    model: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
) -> ScoringRequestIdentity:
    """Rebuild the frozen provider identity from validated scoring material.

    This function deliberately accepts ordinary identity material: authority is
    established by the caller's boundary, not by this canonical hash builder.
    """

    if type(scoring_input) is not ScoringInput:
        msg = (
            "scoring_input must be an exact validated ScoringInput; "
            f"got {type(scoring_input).__name__}"
        )
        raise ValueError(msg)
    validated = ScoringInput.model_validate(dict(scoring_input.__dict__))
    normalized_input_hash = _normalized_scoring_input_hash(
        video=validated.video,
        sample=validated.sample,
        language=validated.language,
        output_language=validated.output_language,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_description_chars=max_description_chars,
    )
    return ScoringRequestIdentity(
        normalized_input_hash=normalized_input_hash,
        request_hash=build_provider_request_hash(
            operation=_SCORING_OPERATION,
            normalized_input_hash=normalized_input_hash,
            provider="ollama",
            model=model,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
        ),
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
    output_language: ScoringOutputLanguage,
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
    provisional = ScoringInput(
        video=video,
        sample=sample,
        transcript_content_hash=sample.source_content_hash,
        language=language,
        output_language=output_language,
        request_hash="0" * 64,
    )
    identity = build_scoring_request_identity(
        scoring_input=provisional,
        model=settings.model,
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens,
        max_description_chars=settings.max_description_chars,
    )
    return ScoringInput(
        video=video,
        sample=sample,
        transcript_content_hash=sample.source_content_hash,
        language=language,
        output_language=output_language,
        request_hash=identity.request_hash,
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
        output_language: ScoringOutputLanguage,
    ) -> ScoringOutcome:
        scoring_input = build_scoring_input(
            video=video,
            transcript_text=transcript_text,
            language=language,
            output_language=output_language,
            settings=self._settings,
        )
        started_at = self._clock()
        cached = self._cache.get(scoring_input.request_hash)
        diagnostics: list[DiagnosticEntry] = []
        if cached is None:
            result = validate_score_result(self._provider.score(scoring_input))
            if result.request_hash != scoring_input.request_hash:
                msg = "scoring provider returned a result for a different request"
                raise ValueError(msg)
            if result.output_language != scoring_input.output_language:
                msg = "scoring provider returned a result for a different output language"
                raise ValueError(msg)
            self._cache.put(result)
        else:
            result = validate_score_result(cached)
            if result.request_hash != scoring_input.request_hash:
                msg = "cached scoring result belongs to a different request"
                raise ValueError(msg)
            if result.output_language != scoring_input.output_language:
                msg = "cached scoring result has a different output language"
                raise ValueError(msg)
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
        output_language: ScoringOutputLanguage,
    ) -> ScoringOutcome:
        failure: AppError | None = None
        try:
            return self._score(
                video=video,
                transcript_text=transcript_text,
                language=language,
                output_language=output_language,
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
        del output_language
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
        output_language: ScoringOutputLanguage,
    ) -> ScoringOutcome:
        scoring_input = build_scoring_input(
            video=video,
            transcript_text=transcript_text,
            language=language,
            output_language=output_language,
            settings=self._settings,
        )
        now = self._clock()
        request = self._provider_request(scoring_input)
        previous_call = self._get_provider_call(
            request_hash=request.request_hash,
            video_id=video.video_id,
        )
        if self._provider_call_version_mismatch(previous_call, request):
            assert previous_call is not None
            return self._recompute_stale_cache(
                scoring_input=scoring_input,
                original_request=request,
                stale_call=previous_call,
                now=now,
                video_id=video.video_id,
            )
        recovery_required = self._is_recovery_required(previous_call, request)
        reservation = self._reserve(request, now=now, video_id=video.video_id)
        if not reservation.acquired:
            if reservation.record.status is ProviderCallStatus.SUCCEEDED:
                try:
                    result = self._load_verified_cached_result(
                        request=request,
                        provider_call=reservation.record,
                        video_id=video.video_id,
                        output_language=scoring_input.output_language,
                    )
                except _ScoringCacheMiss:
                    return self._recompute_stale_cache(
                        scoring_input=scoring_input,
                        original_request=request,
                        stale_call=reservation.record,
                        now=now,
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
                recovery_required=recovery_required,
            )
        except ScoringPersistenceError as error:
            self._record_failure(
                request_hash=request.request_hash,
                error=error.error,
                now=now,
                recovery_required=recovery_required,
            )
            raise
        recovery_input_used = recovery_raw_response is not None
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
                recovery_required=recovery_input_used,
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
                recovery_required=recovery_input_used,
            )
            raise
        return outcome

    @staticmethod
    def _provider_call_version_mismatch(
        provider_call: ProviderCallRecord | None,
        request: ProviderCallRequest,
    ) -> bool:
        return (
            provider_call is not None
            and provider_call.status is ProviderCallStatus.SUCCEEDED
            and provider_call.request_hash == request.request_hash
            and provider_call.operation == request.operation
            and provider_call.provider == request.provider
            and provider_call.model == request.model
            and (
                provider_call.prompt_version != request.prompt_version
                or provider_call.schema_version != request.schema_version
            )
        )

    def _recompute_stale_cache(
        self,
        *,
        scoring_input: ScoringInput,
        original_request: ProviderCallRequest,
        stale_call: ProviderCallRecord,
        now: datetime,
        video_id: str,
    ) -> ScoringOutcome:
        """Treat stale provenance as a miss while retaining its audit records."""

        raw = self._repository.get_artifact_by_key(
            original_request.deterministic_artifact_key
        )
        structured = self._repository.get_artifact_by_key(
            f"scoring/{original_request.request_hash}/structured"
        )
        if raw is None or structured is None:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "stale local scoring cache cannot be audited",
                    retryable=True,
                    video_id=video_id,
                )
            )
        recompute_seed = _canonical_json(
            {
                "policy": "scoring-cache-recompute-v1",
                "original_request_hash": original_request.request_hash,
                "raw_content_hash": raw.content_hash,
                "structured_content_hash": structured.content_hash,
                "stored_prompt_version": stale_call.prompt_version,
                "stored_schema_version": stale_call.schema_version,
            }
        )
        request_without_key = ProviderCallRequest(
            operation=original_request.operation,
            normalized_input_hash=_sha256_text(recompute_seed),
            provider=original_request.provider,
            model=original_request.model,
            prompt_version=original_request.prompt_version,
            schema_version=original_request.schema_version,
            deterministic_artifact_key="pending",
        )
        request = ProviderCallRequest(
            operation=request_without_key.operation,
            normalized_input_hash=request_without_key.normalized_input_hash,
            provider=request_without_key.provider,
            model=request_without_key.model,
            prompt_version=request_without_key.prompt_version,
            schema_version=request_without_key.schema_version,
            deterministic_artifact_key=(
                f"scoring/{request_without_key.request_hash}/raw"
            ),
        )
        recompute_input = ScoringInput.model_validate(
            {
                **scoring_input.model_dump(mode="python"),
                "request_hash": request.request_hash,
            }
        )
        reservation = self._reserve(request, now=now, video_id=video_id)
        if not reservation.acquired:
            if reservation.record.status is ProviderCallStatus.SUCCEEDED:
                result = self._load_verified_cached_result(
                    request=request,
                    provider_call=reservation.record,
                    video_id=video_id,
                    output_language=recompute_input.output_language,
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
                    video_id=video_id,
                )
                return outcome
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    "local scoring recompute is already reserved or unavailable",
                    retryable=True,
                    video_id=video_id,
                )
            )

        result, raw_response = self._call_provider(
            scoring_input=recompute_input,
            request=request,
            now=now,
        )
        outcome = self._outcome(
            result,
            started_at=now,
            finished_at=self._clock(),
            cache_hit=False,
        )
        written_paths: tuple[Path, ...] = ()
        try:
            artifacts, written_paths = self._write_artifacts(
                result=result,
                raw_response=raw_response,
                request=request,
                video_id=video_id,
                now=now,
            )
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
                video_id=video_id,
            )
        except ScoringPersistenceError:
            self._remove_written_paths(written_paths)
            self._record_failure(
                request_hash=request.request_hash,
                error=self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring recompute persistence failed",
                    retryable=True,
                    video_id=video_id,
                ),
                now=now,
            )
            raise
        return outcome

    def _provider_request(self, scoring_input: ScoringInput) -> ProviderCallRequest:
        identity = build_scoring_request_identity(
            scoring_input=scoring_input,
            model=self._settings.model,
            temperature=self._settings.temperature,
            max_output_tokens=self._settings.max_output_tokens,
            max_description_chars=self._settings.max_description_chars,
        )
        request = ProviderCallRequest(
            operation=_SCORING_OPERATION,
            normalized_input_hash=identity.normalized_input_hash,
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

    def _get_provider_call(
        self,
        *,
        request_hash: str,
        video_id: str,
    ) -> ProviderCallRecord | None:
        try:
            return self._repository.get_provider_call(request_hash)
        except Exception:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.LOCAL_RESOURCE,
                    "local scoring provider call lookup failed",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None

    @staticmethod
    def _is_recovery_required(
        provider_call: ProviderCallRecord | None,
        request: ProviderCallRequest,
    ) -> bool:
        return (
            provider_call is not None
            and provider_call.status is ProviderCallStatus.FAILED_RETRYABLE
            and provider_call.last_error_message
            == _RECOVERY_REQUIRED_MARKER_PREFIX + request.request_hash
        )

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
        recovery_required = False
        try:
            result = validate_score_result(self._provider.score(scoring_input))
            self._validate_result_provenance(
                result=result,
                request=request,
                output_language=scoring_input.output_language,
            )
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
                    recovery_required = True
                except ScoringPersistenceError as persistence_error:
                    failure = persistence_error.error
            self._record_failure(
                request_hash=request.request_hash,
                error=failure,
                now=now,
                recovery_required=recovery_required,
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
            result = validate_score_result(
                self._provider._repair_saved_primary_response(
                    primary_raw_response=primary_raw_response,
                    scoring_input=scoring_input,
                )
            )
            self._validate_result_provenance(
                result=result,
                request=request,
                output_language=scoring_input.output_language,
            )
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
                recovery_required=True,
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
                recovery_required=True,
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
        recovery_required: bool,
    ) -> str | None:
        artifact_key = self._recovery_primary_artifact_key(request)
        artifact = self._repository.get_artifact_by_key(artifact_key)
        if artifact is None:
            if recovery_required:
                raise ScoringPersistenceError(
                    self._error(
                        ErrorCode.INVALID_RESPONSE,
                        "local scoring recovery artifact is unavailable or invalid",
                        retryable=True,
                        video_id=video_id,
                    )
                )
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
        result = validate_score_result(result)
        self._validate_result_provenance(
            result=result,
            request=request,
            output_language=result.output_language,
        )
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
        output_language: ScoringOutputLanguage,
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
            result = validate_score_result_json(structured_content)
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
            or provider_call.request_hash != request.request_hash
            or provider_call.operation != request.operation
            or provider_call.provider != request.provider
            or provider_call.model != request.model
            or provider_call.prompt_version != request.prompt_version
            or provider_call.schema_version != request.schema_version
        ):
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "verified local scoring artifact provenance is invalid",
                    retryable=True,
                    video_id=video_id,
                )
            )
        if (
            result.prompt_version != request.prompt_version
            or result.schema_version != request.schema_version
        ):
            raise _ScoringCacheMiss
        try:
            self._validate_result_provenance(
                result=result,
                request=request,
                output_language=output_language,
            )
        except ValueError:
            raise ScoringPersistenceError(
                self._error(
                    ErrorCode.INVALID_RESPONSE,
                    "verified local scoring artifact provenance is invalid",
                    retryable=True,
                    video_id=video_id,
                )
            ) from None
        return result

    @staticmethod
    def _validate_result_provenance(
        *,
        result: ScoreResult,
        request: ProviderCallRequest,
        output_language: ScoringOutputLanguage,
    ) -> None:
        if (
            result.request_hash != request.request_hash
            or result.provider != request.provider
            or result.model != request.model
            or result.output_language != output_language
            or result.prompt_version != request.prompt_version
            or result.schema_version != request.schema_version
        ):
            msg = "local scoring result provenance does not match the current request"
            raise ValueError(msg)

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
        trusted_result = validate_score_result(outcome.result)
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
                    score=trusted_result.score,
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
        recovery_required: bool = False,
    ) -> None:
        try:
            self._repository.fail_provider_call(
                request_hash,
                owner=self._context.owner,
                retryable=error.retryable,
                available_at=now,
                error_code=error.code,
                error_message=(
                    _RECOVERY_REQUIRED_MARKER_PREFIX + request_hash
                    if recovery_required
                    else error.message
                ),
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


# ---------------------------------------------------------------------------
# Phase F: PRIMARY-only in-memory trusted scoring seam (memory only)
# ---------------------------------------------------------------------------
#
# The seam is deliberately non-production and isolated: it accepts only an
# exact ``PrimaryScoringAttempt`` whose candidate was derived by the single
# canonical parser from the exact bounded raw response bytes, re-verifies
# every binding in memory, finalizes through ``TrustedScoringFinalizer``, and
# seals the memory-only ``PhaseFTrustedScoringSuccess`` aggregate.  It never
# touches persistence, artifacts, caches, provider recall, or the legacy
# ``RepositoryBackedScoringService`` path.


@dataclass(frozen=True, slots=True)
class PrimaryScoringAttempt:
    """Frozen candidate-only PRIMARY continuation (Phase F).

    The attempt binds one canonical ``ScoringCandidate`` derived from the
    exact bounded ``final_raw_response`` body to the scoring request identity,
    with ``attempt_role`` fixed to ``"PRIMARY"``.  It is not a Pydantic DTO,
    not restorable from JSON, and not a persistence/cache/artifact type.
    """

    scoring_input_normalized_hash: str
    scoring_request_hash: str
    candidate: ScoringCandidate
    candidate_hash: str
    raw_response_hash: str
    provider: str
    model: str
    model_digest: str
    attempt_role: str
    final_raw_response: str


def build_primary_scoring_attempt(
    *,
    scoring_input: ScoringInput,
    candidate: ScoringCandidate,
    final_raw_response: str,
    provider: str,
    model: str,
    model_digest: str,
    temperature: float,
    max_output_tokens: int,
    max_description_chars: int,
) -> PrimaryScoringAttempt:
    """Bind a canonical candidate to the exact raw response and request identity.

    The candidate is accepted only when it is an exact ``ScoringCandidate``
    whose value equals the canonical re-parse of ``final_raw_response`` (raw A
    + candidate B fails closed).  The raw body must be a bounded strict-UTF-8
    string; the hash is computed over the exact response-body bytes.
    """

    if type(scoring_input) is not ScoringInput:
        msg = (
            "scoring_input must be an exact validated ScoringInput; "
            f"got {type(scoring_input).__name__}"
        )
        raise ValueError(msg)
    if type(candidate) is not ScoringCandidate:
        msg = (
            "candidate must be an exact ScoringCandidate; "
            f"got {type(candidate).__name__}"
        )
        raise ValueError(msg)

    from youtube_intel.providers.ollama import parse_scoring_candidate

    parsed_candidate = parse_scoring_candidate(final_raw_response)
    if parsed_candidate != candidate:
        msg = "candidate does not match the canonical parse of the raw response"
        raise ValueError(msg)

    identity = build_scoring_request_identity(
        scoring_input=scoring_input,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_description_chars=max_description_chars,
    )
    from youtube_intel.quality import build_scoring_candidate_hash

    candidate_hash = build_scoring_candidate_hash(parsed_candidate)
    raw_response_hash = hashlib.sha256(
        final_raw_response.encode("utf-8")
    ).hexdigest()
    return PrimaryScoringAttempt(
        scoring_input_normalized_hash=identity.normalized_input_hash,
        scoring_request_hash=identity.request_hash,
        candidate=parsed_candidate,
        candidate_hash=candidate_hash,
        raw_response_hash=raw_response_hash,
        provider=provider,
        model=model,
        model_digest=model_digest,
        attempt_role="PRIMARY",
        final_raw_response=final_raw_response,
    )


class _PhaseFTrustedScoringSuccessSentinel:
    """Private sentinel; only the Phase F seam can mint the aggregate."""

    __slots__ = ()


_PHASE_F_TRUSTED_SCORING_SUCCESS_SENTINEL = _PhaseFTrustedScoringSuccessSentinel()


@dataclass(frozen=True, slots=True)
class _EnrichedQualityEvidence:
    """Phase G continuation evidence sealed inside the success aggregate.

    Each field is the canonical JSON bytes of the corresponding validated
    domain object and its SHA-256 hash.  The structured result bytes are
    produced by the sealed serializer and are distinct from a bare ScoreResult
    JSON serialization.
    """

    canonical_scoring_input_bytes: bytes
    canonical_scoring_input_hash: str
    canonical_quality_input_bytes: bytes
    canonical_quality_input_hash: str
    canonical_quality_result_bytes: bytes
    canonical_quality_result_hash: str
    canonical_quality_operation_bytes: bytes
    canonical_quality_operation_hash: str
    canonical_attestation_bytes: bytes
    canonical_attestation_hash: str
    canonical_structured_result_bytes: bytes
    canonical_structured_result_hash: str


class PhaseFTrustedScoringSuccess:
    """Opaque memory-only Phase F success aggregate.

    The aggregate is not a Pydantic DTO and cannot be constructed, copied,
    serialized, subclassed, or mutated by callers.  It seals the trusted
    result together with its primary attempt through the three canonical
    hashes so a later phase can verify the complete binding in memory.

    In Phase G the same opaque aggregate is backwards-compatibly enriched with
    canonical scoring/quality evidence and sealed structured-result bytes.
    A Phase F aggregate that lacks this evidence cannot be used as a Phase G
    ingress and must fail-closed.
    """

    __slots__ = (
        "_trusted_result",
        "_primary_attempt",
        "_scoring_request_hash",
        "_candidate_hash",
        "_raw_response_hash",
        "_enriched_evidence",
        "_sealed",
    )

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("PhaseFTrustedScoringSuccess cannot be subclassed")

    def __init__(
        self,
        *,
        sentinel: object,
        trusted_result: TrustedScoreResult,
        primary_attempt: PrimaryScoringAttempt,
        scoring_request_hash: str,
        candidate_hash: str,
        raw_response_hash: str,
        enriched_evidence: _EnrichedQualityEvidence | None = None,
    ) -> None:
        if sentinel is not _PHASE_F_TRUSTED_SCORING_SUCCESS_SENTINEL:
            msg = "PhaseFTrustedScoringSuccess can only be minted by the trusted seam"
            raise ValueError(msg)
        self._trusted_result = trusted_result
        self._primary_attempt = primary_attempt
        self._scoring_request_hash = scoring_request_hash
        self._candidate_hash = candidate_hash
        self._raw_response_hash = raw_response_hash
        self._enriched_evidence = enriched_evidence
        self._sealed = True

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("PhaseFTrustedScoringSuccess is immutable")
        object.__setattr__(self, name, value)

    @property
    def trusted_result(self) -> TrustedScoreResult:
        return self._trusted_result

    @property
    def primary_attempt(self) -> PrimaryScoringAttempt:
        return self._primary_attempt

    @property
    def scoring_request_hash(self) -> str:
        return self._scoring_request_hash

    @property
    def candidate_hash(self) -> str:
        return self._candidate_hash

    @property
    def raw_response_hash(self) -> str:
        return self._raw_response_hash

    @property
    def canonical_scoring_input_bytes(self) -> bytes | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_scoring_input_bytes

    @property
    def canonical_scoring_input_hash(self) -> str | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_scoring_input_hash

    @property
    def canonical_quality_input_bytes(self) -> bytes | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_quality_input_bytes

    @property
    def canonical_quality_input_hash(self) -> str | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_quality_input_hash

    @property
    def canonical_quality_result_bytes(self) -> bytes | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_quality_result_bytes

    @property
    def canonical_quality_result_hash(self) -> str | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_quality_result_hash

    @property
    def canonical_quality_operation_bytes(self) -> bytes | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_quality_operation_bytes

    @property
    def canonical_quality_operation_hash(self) -> str | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_quality_operation_hash

    @property
    def canonical_attestation_bytes(self) -> bytes | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_attestation_bytes

    @property
    def canonical_attestation_hash(self) -> str | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_attestation_hash

    @property
    def canonical_structured_result_bytes(self) -> bytes | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_structured_result_bytes

    @property
    def canonical_structured_result_hash(self) -> str | None:
        return None if self._enriched_evidence is None else self._enriched_evidence.canonical_structured_result_hash

    def __copy__(self) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be serialized")


def _canonical_json_bytes(value: object) -> bytes:
    """Return canonical deterministic JSON bytes for validated domain objects."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _verify_canonical_bytes_hash(
    canonical_bytes: bytes,
    expected_hash: str,
    field_name: str,
) -> None:
    """Fail-closed helper: canonical bytes must match the sealed hash."""

    if hashlib.sha256(canonical_bytes).hexdigest() != expected_hash:
        msg = f"{field_name} canonical bytes do not match the sealed hash"
        raise ValueError(msg)


def _sealed_trusted_score_result_serializer(
    trusted_result: TrustedScoreResult,
) -> bytes:
    """Sealed serializer: exact ``TrustedScoreResult`` -> canonical bytes.

    The serializer is the only Phase G surface that unwraps the trusted result
    into structured bytes.  It never accepts a bare ``ScoreResult`` and never
    re-serializes from an untrusted source.
    """

    from youtube_intel.quality import TrustedScoreResult

    if type(trusted_result) is not TrustedScoreResult:
        msg = (
            "sealed serializer requires an exact TrustedScoreResult; "
            f"got {type(trusted_result).__name__}"
        )
        raise ValueError(msg)
    return _canonical_json_bytes(trusted_result.result.model_dump(mode="json"))


def _mint_phase_f_trusted_scoring_success(
    *,
    trusted_result: TrustedScoreResult,
    primary_attempt: PrimaryScoringAttempt,
    enriched_evidence: _EnrichedQualityEvidence | None = None,
) -> PhaseFTrustedScoringSuccess:
    """Seal the only Phase F success aggregate with self-verifying hashes.

    A bare ``TrustedScoreResult`` is not a Phase F success; the aggregate is
    minted only with the exact primary attempt and re-verified in memory.  The
    mint is private to the seam: it independently re-parses the bounded raw
    body and binds every business field between the trusted result and the
    attempt's candidate, closing the direct-construction bypass.
    """

    from youtube_intel.providers.ollama import parse_scoring_candidate
    from youtube_intel.quality import (
        TrustedScoreResult,
        build_scoring_candidate_hash,
    )

    if type(trusted_result) is not TrustedScoreResult:
        msg = (
            "trusted result must be an exact TrustedScoreResult; "
            f"got {type(trusted_result).__name__}"
        )
        raise ValueError(msg)
    if type(primary_attempt) is not PrimaryScoringAttempt:
        msg = (
            "primary attempt must be an exact PrimaryScoringAttempt; "
            f"got {type(primary_attempt).__name__}"
        )
        raise ValueError(msg)

    try:
        raw_bytes = primary_attempt.final_raw_response.encode("utf-8")
    except UnicodeEncodeError:
        msg = "raw response is not valid strict UTF-8"
        raise ValueError(msg) from None
    raw_response_hash = hashlib.sha256(raw_bytes).hexdigest()
    if raw_response_hash != primary_attempt.raw_response_hash:
        msg = "raw response hash mismatches the primary attempt binding"
        raise ValueError(msg)
    candidate_hash = build_scoring_candidate_hash(primary_attempt.candidate)
    if candidate_hash != primary_attempt.candidate_hash:
        msg = "candidate hash mismatches the primary attempt binding"
        raise ValueError(msg)
    if trusted_result.result.request_hash != primary_attempt.scoring_request_hash:
        msg = "trusted result request hash mismatches the primary attempt binding"
        raise ValueError(msg)

    # Independent raw re-parse: a forged attempt with raw A + candidate B must
    # fail even when all hashes are self-consistent.
    reparsed_candidate = parse_scoring_candidate(primary_attempt.final_raw_response)
    if reparsed_candidate != primary_attempt.candidate:
        msg = "candidate does not match the canonical parse of the raw response"
        raise ValueError(msg)

    # Business-field binding: the trusted result must describe exactly the
    # attempt's candidate, not merely a self-consistent request hash.
    result = trusted_result.result
    candidate = primary_attempt.candidate
    if (
        result.score != candidate.score
        or result.reason != candidate.reason
        or result.topics != candidate.topics
        or result.should_summarize != candidate.should_summarize
        or result.dimensions != candidate.dimensions
    ):
        msg = "trusted result business fields mismatch the primary attempt candidate"
        raise ValueError(msg)

    return PhaseFTrustedScoringSuccess(
        sentinel=_PHASE_F_TRUSTED_SCORING_SUCCESS_SENTINEL,
        trusted_result=trusted_result,
        primary_attempt=primary_attempt,
        scoring_request_hash=primary_attempt.scoring_request_hash,
        candidate_hash=primary_attempt.candidate_hash,
        raw_response_hash=primary_attempt.raw_response_hash,
        enriched_evidence=enriched_evidence,
    )


def _run_primary_trusted_scoring_seam(
    *,
    attempt: PrimaryScoringAttempt,
    scoring_input: ScoringInput,
    quality_input: ContentQualityInput,
    quality_result: ContentQualityResult,
    quality_operation: QualityJudgeOperationInput,
    attestation: QualityPassAttestation,
    quality_authority: QualityProvenanceAuthority,
    scoring_context: TrustedScoringContext,
) -> PhaseFTrustedScoringSuccess:
    """Finalize one PRIMARY attempt into the memory-only trusted success.

    The seam holds no provider handle and cannot recall the provider: it
    re-verifies the raw, candidate, and request bindings entirely from the
    attempt plus the runtime-minted scoring context, then delegates business
    finalization to ``TrustedScoringFinalizer`` with the parser-derived
    candidate.  Legacy ``ScoreResult``, mappings, and JSON are rejected at the
    entrance by exact-type guard.
    """

    # Legacy isolation guard: exact type before any attempt field is read.
    if type(attempt) is not PrimaryScoringAttempt:
        msg = (
            "trusted seam requires an exact PrimaryScoringAttempt; "
            f"got {type(attempt).__name__}"
        )
        raise ValueError(msg)
    if attempt.attempt_role != "PRIMARY":
        msg = "trusted seam accepts only PRIMARY attempts"
        raise ValueError(msg)

    if type(scoring_input) is not ScoringInput:
        msg = (
            "scoring_input must be an exact validated ScoringInput; "
            f"got {type(scoring_input).__name__}"
        )
        raise ValueError(msg)

    # Provider provenance binds the attempt to the current runtime context.
    if attempt.provider != scoring_context.scoring_provider:
        msg = "attempt provider mismatches the trusted scoring context"
        raise ValueError(msg)
    if attempt.model != scoring_context.scoring_model:
        msg = "attempt provider model mismatches the trusted scoring context"
        raise ValueError(msg)
    if attempt.model_digest != scoring_context.scoring_model_digest:
        msg = "attempt provider model digest mismatches the trusted scoring context"
        raise ValueError(msg)

    # Raw binding: the hash is over the exact response-body bytes.
    try:
        raw_bytes = attempt.final_raw_response.encode("utf-8")
    except UnicodeEncodeError:
        msg = "raw response is not valid strict UTF-8"
        raise ValueError(msg) from None
    raw_response_hash = hashlib.sha256(raw_bytes).hexdigest()
    if raw_response_hash != attempt.raw_response_hash:
        msg = "raw response hash mismatches the primary attempt binding"
        raise ValueError(msg)

    # Candidate binding: canonical hash, then a fresh canonical re-parse.
    from youtube_intel.quality import build_scoring_candidate_hash

    candidate_hash = build_scoring_candidate_hash(attempt.candidate)
    if candidate_hash != attempt.candidate_hash:
        msg = "candidate hash mismatches the primary attempt binding"
        raise ValueError(msg)

    from youtube_intel.providers.ollama import parse_scoring_candidate

    reparsed_candidate = parse_scoring_candidate(attempt.final_raw_response)
    if reparsed_candidate != attempt.candidate:
        msg = "candidate does not match the canonical parse of the raw response"
        raise ValueError(msg)

    # Request identity: rebuilt from the runtime context, not trusted by name.
    identity = build_scoring_request_identity(
        scoring_input=scoring_input,
        model=scoring_context.scoring_model,
        temperature=scoring_context.temperature,
        max_output_tokens=scoring_context.max_output_tokens,
        max_description_chars=scoring_context.max_description_chars,
    )
    if attempt.scoring_request_hash != identity.request_hash:
        msg = "scoring request hash mismatches the canonical identity"
        raise ValueError(msg)
    if attempt.scoring_input_normalized_hash != identity.normalized_input_hash:
        msg = "scoring input identity mismatches the canonical identity"
        raise ValueError(msg)
    if scoring_input.request_hash != identity.request_hash:
        msg = "scoring request hash mismatches the trusted scoring input"
        raise ValueError(msg)

    from youtube_intel.quality import TrustedScoringFinalizer

    trusted_result = TrustedScoringFinalizer().finalize(
        candidate=attempt.candidate,
        scoring_input=scoring_input,
        quality_input=quality_input,
        quality_result=quality_result,
        quality_operation=quality_operation,
        attestation=attestation,
        quality_authority=quality_authority,
        scoring_context=scoring_context,
    )

    # Phase G continuation enrichment: seal canonical bytes/hashes of every
    # validated domain object so PREWRITE_VALIDATE can re-verify without caller
    # reconstruction and without touching persistence.
    scoring_input_bytes = _canonical_json_bytes(scoring_input.model_dump(mode="json"))
    quality_input_bytes = _canonical_json_bytes(quality_input.model_dump(mode="json"))
    quality_result_bytes = _canonical_json_bytes(quality_result.model_dump(mode="json"))
    quality_operation_bytes = _canonical_json_bytes(
        quality_operation.model_dump(mode="json")
    )
    attestation_bytes = _canonical_json_bytes(attestation.model_dump(mode="json"))
    structured_bytes = _sealed_trusted_score_result_serializer(trusted_result)
    enriched_evidence = _EnrichedQualityEvidence(
        canonical_scoring_input_bytes=scoring_input_bytes,
        canonical_scoring_input_hash=hashlib.sha256(scoring_input_bytes).hexdigest(),
        canonical_quality_input_bytes=quality_input_bytes,
        canonical_quality_input_hash=hashlib.sha256(quality_input_bytes).hexdigest(),
        canonical_quality_result_bytes=quality_result_bytes,
        canonical_quality_result_hash=hashlib.sha256(quality_result_bytes).hexdigest(),
        canonical_quality_operation_bytes=quality_operation_bytes,
        canonical_quality_operation_hash=hashlib.sha256(
            quality_operation_bytes
        ).hexdigest(),
        canonical_attestation_bytes=attestation_bytes,
        canonical_attestation_hash=hashlib.sha256(attestation_bytes).hexdigest(),
        canonical_structured_result_bytes=structured_bytes,
        canonical_structured_result_hash=hashlib.sha256(structured_bytes).hexdigest(),
    )

    return _mint_phase_f_trusted_scoring_success(
        trusted_result=trusted_result,
        primary_attempt=attempt,
        enriched_evidence=enriched_evidence,
    )


# ---------------------------------------------------------------------------
# Phase G: trusted prewrite persistence committer
# ---------------------------------------------------------------------------

_G_RAW_ENVELOPE_SCHEMA: Final = "scoring-raw-envelope-v1"
_G_RAW_ARTIFACT_PRODUCER_VERSION: Final = "scoring-raw-content-quality-v1"
_G_STRUCTURED_ARTIFACT_PRODUCER_VERSION: Final = "scoring-structured-content-quality-v1"
_G_ARTIFACT_RETENTION: Final = timedelta(days=30)


class _ValidatedScoringWritePlanSentinel:
    """Private sentinel; only PREWRITE_VALIDATE can mint a plan."""

    __slots__ = ()


_VALIDATED_SCORING_WRITE_PLAN_SENTINEL = _ValidatedScoringWritePlanSentinel()


class _ValidatedScoringWritePlan:
    """Opaque, runtime-minted Phase G write capability.

    A plan is not a DTO, cache identity, authority, or persistence record.  It
    is strictly internal to ``TrustedPersistenceEntry.persist_success``.
    and it freezes every byte, hash, Artifact identity and ProviderCall identity
    required for the subsequent trusted filesystem + SQLite registration.
    """

    __slots__ = (
        "_success",
        "_raw_envelope_bytes",
        "_raw_envelope_hash",
        "_raw_envelope_length",
        "_structured_bytes",
        "_structured_hash",
        "_structured_length",
        "_raw_artifact",
        "_structured_artifact",
        "_scoring_call_request",
        "_judge_call_request",
        "_scoring_call_completion",
        "_judge_call_completion",
        "_scoring_summary",
        "_video_id",
        "_sealed",
    )

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("_ValidatedScoringWritePlan cannot be subclassed")

    def __init__(
        self,
        *,
        sentinel: object,
        success: PhaseFTrustedScoringSuccess,
        raw_envelope_bytes: bytes,
        raw_envelope_hash: str,
        raw_envelope_length: int,
        structured_bytes: bytes,
        structured_hash: str,
        structured_length: int,
        raw_artifact: ArtifactWrite,
        structured_artifact: ArtifactWrite,
        scoring_call_request: ProviderCallRequest,
        judge_call_request: ProviderCallRequest,
        scoring_call_completion: ProviderCallCompletion,
        judge_call_completion: ProviderCallCompletion,
        scoring_summary: ScoringSummaryWrite,
        video_id: str,
    ) -> None:
        if sentinel is not _VALIDATED_SCORING_WRITE_PLAN_SENTINEL:
            msg = "_ValidatedScoringWritePlan can only be minted by PREWRITE_VALIDATE"
            raise ValueError(msg)
        self._success = success
        self._raw_envelope_bytes = raw_envelope_bytes
        self._raw_envelope_hash = raw_envelope_hash
        self._raw_envelope_length = raw_envelope_length
        self._structured_bytes = structured_bytes
        self._structured_hash = structured_hash
        self._structured_length = structured_length
        self._raw_artifact = raw_artifact
        self._structured_artifact = structured_artifact
        self._scoring_call_request = scoring_call_request
        self._judge_call_request = judge_call_request
        self._scoring_call_completion = scoring_call_completion
        self._judge_call_completion = judge_call_completion
        self._scoring_summary = scoring_summary
        self._video_id = video_id
        self._sealed = True

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("_ValidatedScoringWritePlan is immutable")
        object.__setattr__(self, name, value)

    @property
    def success(self) -> PhaseFTrustedScoringSuccess:
        return self._success

    @property
    def raw_envelope_bytes(self) -> bytes:
        return self._raw_envelope_bytes

    @property
    def raw_envelope_hash(self) -> str:
        return self._raw_envelope_hash

    @property
    def raw_envelope_length(self) -> int:
        return self._raw_envelope_length

    @property
    def structured_bytes(self) -> bytes:
        return self._structured_bytes

    @property
    def structured_hash(self) -> str:
        return self._structured_hash

    @property
    def structured_length(self) -> int:
        return self._structured_length

    @property
    def raw_artifact(self) -> ArtifactWrite:
        return self._raw_artifact

    @property
    def structured_artifact(self) -> ArtifactWrite:
        return self._structured_artifact

    @property
    def scoring_call_request(self) -> ProviderCallRequest:
        return self._scoring_call_request

    @property
    def judge_call_request(self) -> ProviderCallRequest:
        return self._judge_call_request

    @property
    def scoring_call_completion(self) -> ProviderCallCompletion:
        return self._scoring_call_completion

    @property
    def judge_call_completion(self) -> ProviderCallCompletion:
        return self._judge_call_completion

    @property
    def scoring_summary(self) -> ScoringSummaryWrite:
        return self._scoring_summary

    @property
    def video_id(self) -> str:
        return self._video_id

    def __copy__(self) -> NoReturn:
        raise TypeError("_ValidatedScoringWritePlan cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("_ValidatedScoringWritePlan cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("_ValidatedScoringWritePlan cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("_ValidatedScoringWritePlan cannot be serialized")


class TrustedPersistenceEntry:
    """Runtime-owned Phase G trusted persistence boundary.

    The committer is created by ``RuntimeOperations`` with runtime-owned
    context, repository, DATA root and job identity.  Its only
    public operation accepts an exact ``PhaseFTrustedScoringSuccess`` and,
    after zero-write PREWRITE_VALIDATE, performs the ordered filesystem +
    SQLite registration protocol.  It never recalls providers, repairs,
    retries, reads cache, or treats legacy/Artifact/ProviderCall records as
    trusted input.
    """

    def __init__(
        self,
        *,
        repository: _ScoringRepository,
        data_root: Path,
        quality_authority: QualityProvenanceAuthority,
        scoring_context: TrustedScoringContext,
        context: ScoringJobContext,
        summary_threshold: float,
        clock: _CLOCK = _utcnow,
    ) -> None:
        from youtube_intel.quality import (
            QualityProvenanceAuthority,
            TrustedScoringContext,
        )

        if type(quality_authority) is not QualityProvenanceAuthority:
            msg = "quality_authority must be a runtime-minted QualityProvenanceAuthority"
            raise ValueError(msg)
        if type(scoring_context) is not TrustedScoringContext:
            msg = "scoring_context must be a runtime-minted TrustedScoringContext"
            raise ValueError(msg)
        if not 0 <= summary_threshold <= 10:
            msg = "summary_threshold must be in 0..10"
            raise ValueError(msg)
        self._repository = repository
        self._data_root = data_root
        self._quality_authority = quality_authority
        self._scoring_context = scoring_context
        self._context = context
        self._summary_threshold = summary_threshold
        self._clock = clock

    def _prewrite_validate(
        self,
        success: PhaseFTrustedScoringSuccess,
    ) -> _ValidatedScoringWritePlan:
        """Zero-write validation of an exact Phase F success -> write plan.

        All verification happens in memory.  No temporary file, final file,
        directory, Artifact, ProviderCall, cache entry, stage or response id
        is created before this method returns successfully.
        """

        from youtube_intel.providers.ollama import parse_scoring_candidate
        from youtube_intel.quality import (
            TrustedScoreResult,
            build_content_quality_input_hash,
            build_content_quality_result_hash,
            build_judge_h1_h2,
            build_scoring_candidate_hash,
            verify_quality_pass_attestation,
        )

        # 1. Exact aggregate type and enrichment capability.
        if type(success) is not PhaseFTrustedScoringSuccess:
            msg = (
                "Phase G ingress requires an exact PhaseFTrustedScoringSuccess; "
                f"got {type(success).__name__}"
            )
            raise ValueError(msg)
        if success._enriched_evidence is None:
            msg = "Phase F success is missing the required Phase G quality evidence"
            raise ValueError(msg)
        evidence = success._enriched_evidence

        # 2. Canonical bytes/hash self-consistency.
        _verify_canonical_bytes_hash(
            evidence.canonical_scoring_input_bytes,
            evidence.canonical_scoring_input_hash,
            "scoring_input",
        )
        _verify_canonical_bytes_hash(
            evidence.canonical_quality_input_bytes,
            evidence.canonical_quality_input_hash,
            "quality_input",
        )
        _verify_canonical_bytes_hash(
            evidence.canonical_quality_result_bytes,
            evidence.canonical_quality_result_hash,
            "quality_result",
        )
        _verify_canonical_bytes_hash(
            evidence.canonical_quality_operation_bytes,
            evidence.canonical_quality_operation_hash,
            "quality_operation",
        )
        _verify_canonical_bytes_hash(
            evidence.canonical_attestation_bytes,
            evidence.canonical_attestation_hash,
            "attestation",
        )
        _verify_canonical_bytes_hash(
            evidence.canonical_structured_result_bytes,
            evidence.canonical_structured_result_hash,
            "structured_result",
        )

        # 3. Reconstruct validated domain objects from canonical bytes.
        scoring_input = ScoringInput.model_validate_json(
            evidence.canonical_scoring_input_bytes
        )
        quality_input = ContentQualityInput.model_validate_json(
            evidence.canonical_quality_input_bytes
        )
        quality_result = ContentQualityResult.model_validate_json(
            evidence.canonical_quality_result_bytes
        )
        quality_operation = QualityJudgeOperationInput.model_validate_json(
            evidence.canonical_quality_operation_bytes
        )
        attestation = QualityPassAttestation.model_validate_json(
            evidence.canonical_attestation_bytes
        )
        trusted_result = success.trusted_result
        if type(trusted_result) is not TrustedScoreResult:
            msg = "trusted result must be an exact TrustedScoreResult"
            raise ValueError(msg)

        primary_attempt = success.primary_attempt
        candidate = primary_attempt.candidate
        video_id = scoring_input.video.video_id

        # 4. Raw/candidate binding: exact raw source, canonical parser, hashes.
        try:
            raw_bytes = primary_attempt.final_raw_response.encode("utf-8")
        except UnicodeEncodeError:
            msg = "raw response is not valid strict UTF-8"
            raise ValueError(msg) from None
        raw_response_hash = hashlib.sha256(raw_bytes).hexdigest()
        if raw_response_hash != primary_attempt.raw_response_hash:
            msg = "raw response hash mismatches the primary attempt binding"
            raise ValueError(msg)
        if raw_response_hash != success.raw_response_hash:
            msg = "raw response hash mismatches the success aggregate seal"
            raise ValueError(msg)
        reparsed_candidate = parse_scoring_candidate(primary_attempt.final_raw_response)
        if reparsed_candidate != candidate:
            msg = "candidate does not match the canonical parse of the raw response"
            raise ValueError(msg)
        candidate_hash = build_scoring_candidate_hash(candidate)
        if candidate_hash != primary_attempt.candidate_hash:
            msg = "candidate hash mismatches the primary attempt binding"
            raise ValueError(msg)
        if candidate_hash != success.candidate_hash:
            msg = "candidate hash mismatches the success aggregate seal"
            raise ValueError(msg)

        # 5. Candidate -> result business binding.
        result = trusted_result.result
        if (
            result.score != candidate.score
            or result.reason != candidate.reason
            or result.topics != candidate.topics
            or result.should_summarize != candidate.should_summarize
            or result.dimensions != candidate.dimensions
        ):
            msg = "trusted result business fields mismatch the primary candidate"
            raise ValueError(msg)

        # 6. Request identity against current runtime scoring context.
        identity = build_scoring_request_identity(
            scoring_input=scoring_input,
            model=self._scoring_context.scoring_model,
            temperature=self._scoring_context.temperature,
            max_output_tokens=self._scoring_context.max_output_tokens,
            max_description_chars=self._scoring_context.max_description_chars,
        )
        if identity.request_hash != scoring_input.request_hash:
            msg = "scoring request hash mismatches the canonical identity"
            raise ValueError(msg)
        if identity.request_hash != primary_attempt.scoring_request_hash:
            msg = "scoring request hash mismatches the primary attempt"
            raise ValueError(msg)
        if identity.request_hash != success.scoring_request_hash:
            msg = "scoring request hash mismatches the success aggregate seal"
            raise ValueError(msg)
        if identity.normalized_input_hash != primary_attempt.scoring_input_normalized_hash:
            msg = "scoring input identity mismatches the primary attempt"
            raise ValueError(msg)

        # 7. Provider/model/digest/schema/prompt/operation/output language rotation.
        context = self._scoring_context
        if primary_attempt.provider != context.scoring_provider:
            msg = "attempt provider mismatches the trusted scoring context"
            raise ValueError(msg)
        if primary_attempt.model != context.scoring_model:
            msg = "attempt model mismatches the trusted scoring context"
            raise ValueError(msg)
        if primary_attempt.model_digest != context.scoring_model_digest:
            msg = "attempt model digest mismatches the trusted scoring context"
            raise ValueError(msg)
        if result.provider != context.scoring_provider:
            msg = "result provider mismatches the trusted scoring context"
            raise ValueError(msg)
        if result.model != context.scoring_model:
            msg = "result model mismatches the trusted scoring context"
            raise ValueError(msg)
        if result.prompt_version != context.scoring_prompt_version:
            msg = "result prompt version mismatches the trusted scoring context"
            raise ValueError(msg)
        if result.schema_version != context.scoring_schema_version:
            msg = "result schema version mismatches the trusted scoring context"
            raise ValueError(msg)
        if result.output_language != context.output_language:
            msg = "result output_language mismatches the trusted scoring context"
            raise ValueError(msg)
        if result.request_hash != identity.request_hash:
            msg = "result request_hash mismatches the canonical identity"
            raise ValueError(msg)

        # 8. Quality authority and full PASS attestation re-verification.
        authority = self._quality_authority
        verify_quality_pass_attestation(
            attestation,
            quality_result=quality_result,
            operation_input=quality_operation,
            quality_input=quality_input,
            authority=authority,
        )
        if attestation.scoring_request_hash != identity.request_hash:
            msg = "attestation scoring_request_hash mismatches the canonical identity"
            raise ValueError(msg)
        expected_qih = build_content_quality_input_hash(quality_input)
        if quality_input.candidate_hash != candidate_hash:
            msg = "quality input candidate_hash mismatches the primary candidate"
            raise ValueError(msg)
        if quality_result.candidate_hash != candidate_hash:
            msg = "quality result candidate_hash mismatches the primary candidate"
            raise ValueError(msg)
        if quality_operation.candidate_hash != candidate_hash:
            msg = "quality operation candidate_hash mismatches the primary candidate"
            raise ValueError(msg)
        if quality_result.quality_input_hash != expected_qih:
            msg = "quality result quality_input_hash is invalid"
            raise ValueError(msg)
        if quality_operation.quality_input_hash != expected_qih:
            msg = "quality operation quality_input_hash is invalid"
            raise ValueError(msg)
        expected_qrh = build_content_quality_result_hash(quality_result)
        if attestation.quality_result_hash != expected_qrh:
            msg = "attestation quality_result_hash is invalid"
            raise ValueError(msg)
        if quality_result.status.value != "PASS":
            msg = "Phase G only persists PASS quality results"
            raise ValueError(msg)

        # 9. Canonical raw envelope and structured bytes.
        structured_bytes = _sealed_trusted_score_result_serializer(trusted_result)
        if structured_bytes != evidence.canonical_structured_result_bytes:
            msg = "structured result bytes do not match the sealed serializer output"
            raise ValueError(msg)
        envelope = {
            "envelope_schema": _G_RAW_ENVELOPE_SCHEMA,
            "provider_raw_response": primary_attempt.final_raw_response,
            "candidate": candidate.model_dump(mode="json"),
            "trusted_result": result.model_dump(mode="json"),
            "quality_input": quality_input.model_dump(mode="json"),
            "quality_result": quality_result.model_dump(mode="json"),
            "quality_operation": quality_operation.model_dump(mode="json"),
            "attestation": attestation.model_dump(mode="json"),
            "provenance": {
                "scoring_provider": context.scoring_provider,
                "scoring_model": context.scoring_model,
                "scoring_model_digest": context.scoring_model_digest,
                "scoring_operation": context.scoring_operation,
                "scoring_schema_version": context.scoring_schema_version,
                "scoring_prompt_version": context.scoring_prompt_version,
                "output_language": context.output_language,
                "temperature": context.temperature,
                "max_output_tokens": context.max_output_tokens,
                "max_description_chars": context.max_description_chars,
                "judge_provider": authority.judge_provider,
                "judge_model": authority.judge_model,
                "judge_model_digest": authority.judge_model_digest,
                "judge_operation": authority.judge_operation,
                "quality_policy_version": authority.quality_policy_version,
                "quality_schema_version": authority.quality_schema_version,
                "quality_prompt_version": authority.quality_prompt_version,
            },
        }
        raw_envelope_bytes = _canonical_json_bytes(envelope)
        raw_envelope_hash = hashlib.sha256(raw_envelope_bytes).hexdigest()

        # 10. ArtifactWrite records (no filesystem effect yet).
        now = self._clock()
        raw_key = f"scoring/{identity.request_hash}/raw"
        structured_key = f"scoring/{identity.request_hash}/structured"
        raw_relative_path = f"scoring/{identity.request_hash}/raw.json"
        structured_relative_path = f"scoring/{identity.request_hash}/structured.json"
        raw_artifact = ArtifactWrite(
            artifact_id=f"scoring-raw-{_sha256_text(raw_key + raw_envelope_hash)}",
            artifact_key=raw_key,
            video_id=video_id,
            job_id=self._context.job_id,
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=raw_relative_path,
            content_hash=raw_envelope_hash,
            provider=context.scoring_provider,
            model=context.scoring_model,
            producer_version=_G_RAW_ARTIFACT_PRODUCER_VERSION,
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=now + _G_ARTIFACT_RETENTION,
        )
        structured_artifact = ArtifactWrite(
            artifact_id=(
                "scoring-structured-"
                + _sha256_text(structured_key + evidence.canonical_structured_result_hash)
            ),
            artifact_key=structured_key,
            video_id=video_id,
            job_id=self._context.job_id,
            kind=ArtifactKind.SCORING_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path=structured_relative_path,
            content_hash=evidence.canonical_structured_result_hash,
            provider=context.scoring_provider,
            model=context.scoring_model,
            producer_version=_G_STRUCTURED_ARTIFACT_PRODUCER_VERSION,
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        )

        # 11. ProviderCall identities cross-bound to Artifact records.
        # The scoring request hash must match the canonical identity built with
        # the same prompt/schema versions used by build_scoring_request_identity.
        scoring_call_request = ProviderCallRequest(
            operation=context.scoring_operation,
            normalized_input_hash=identity.normalized_input_hash,
            provider=context.scoring_provider,
            model=context.scoring_model,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            deterministic_artifact_key=raw_key,
        )
        if scoring_call_request.request_hash != identity.request_hash:
            msg = "scoring ProviderCall request_hash mismatches the canonical identity"
            raise ValueError(msg)

        judge_h1, judge_h2 = build_judge_h1_h2(quality_operation)
        judge_call_request = ProviderCallRequest(
            operation=authority.judge_operation,
            normalized_input_hash=judge_h1,
            provider=authority.judge_provider,
            model=authority.judge_model,
            prompt_version=authority.quality_prompt_version,
            schema_version=authority.quality_schema_version,
            deterministic_artifact_key=raw_key,
        )
        if judge_call_request.request_hash != judge_h2:
            msg = "judge ProviderCall request_hash mismatches the attestation H2"
            raise ValueError(msg)
        if judge_h2 != attestation.judge_request_hash:
            msg = "judge ProviderCall request_hash mismatches the attestation"
            raise ValueError(msg)

        scoring_call_completion = ProviderCallCompletion(
            request_hash=scoring_call_request.request_hash,
            response_artifact_id=raw_artifact.artifact_id,
            input_tokens=None,
            output_tokens=None,
            cost_microusd=None,
        )
        judge_call_completion = ProviderCallCompletion(
            request_hash=judge_call_request.request_hash,
            response_artifact_id=raw_artifact.artifact_id,
            input_tokens=None,
            output_tokens=None,
            cost_microusd=None,
        )

        scoring_summary = ScoringSummaryWrite(
            score=result.score,
            should_summarize=result.score >= self._summary_threshold,
        )

        return _ValidatedScoringWritePlan(
            sentinel=_VALIDATED_SCORING_WRITE_PLAN_SENTINEL,
            success=success,
            raw_envelope_bytes=raw_envelope_bytes,
            raw_envelope_hash=raw_envelope_hash,
            raw_envelope_length=len(raw_envelope_bytes),
            structured_bytes=structured_bytes,
            structured_hash=evidence.canonical_structured_result_hash,
            structured_length=len(structured_bytes),
            raw_artifact=raw_artifact,
            structured_artifact=structured_artifact,
            scoring_call_request=scoring_call_request,
            judge_call_request=judge_call_request,
            scoring_call_completion=scoring_call_completion,
            judge_call_completion=judge_call_completion,
            scoring_summary=scoring_summary,
            video_id=video_id,
        )

    def persist_success(
        self, success: PhaseFTrustedScoringSuccess | PhaseHTrustedRepairSuccess
    ) -> StageCompletionResult:
        """Sole Phase G trusted-success data ingress (exact closed union).

        ``type(success) is PhaseFTrustedScoringSuccess`` takes the existing
        PRIMARY verifier; ``type(success) is PhaseHTrustedRepairSuccess``
        takes the H2-C REPAIR verifier; anything else rejects before field
        access.  Exact type is necessary for dispatch but is not authority.
        """

        if type(success) is PhaseFTrustedScoringSuccess:
            return self._persist_primary_success(success)
        if type(success) is PhaseHTrustedRepairSuccess:
            return self._persist_repair_success(success)
        msg = (
            "Phase G ingress requires an exact PhaseFTrustedScoringSuccess or "
            f"PhaseHTrustedRepairSuccess; got {type(success).__name__}"
        )
        raise ValueError(msg)

    def _persist_primary_success(
        self, success: PhaseFTrustedScoringSuccess
    ) -> StageCompletionResult:
        """Execute the trusted filesystem + SQLite registration protocol.

        Ordered durability: tmp exclusive-create -> fsync -> hash/length verify
        -> atomic no-clobber link promote -> parent-directory fsync -> reopen
        final verify -> single SQLite transaction.

        Strict same-plan idempotency: if the complete committed graph
        (files + Artifact rows + ProviderCalls + video/stage/job) already
        matches the plan, the existing committed result is returned without
        rewriting files or creating duplicate rows.  Any partial or
        mismatched state is fail-closed.
        """

        # PREWRITE_VALIDATE and the temporary write plan are both contained in
        # this call.  No caller can provide a DTO/capability to the write sink.
        plan = self._prewrite_validate(success)
        raw_artifact = plan.raw_artifact
        structured_artifact = plan.structured_artifact
        raw_final = self._data_root / raw_artifact.relative_path
        structured_final = self._data_root / structured_artifact.relative_path

        lineage_ctx = _H2CLineageCasContext(
            job_id=self._context.job_id,
            owner=self._context.owner,
            video_id=plan.video_id,
            pipeline_version=self._context.pipeline_version,
            raw_key=raw_artifact.artifact_key,
            structured_key=structured_artifact.artifact_key,
            provenance="PRIMARY",
        )
        # Phase G lineage precheck: the authoritative pointer state is inspected
        # before any filesystem effect.  Pre-v2 NULL-generation jobs keep the
        # frozen P-only behavior with no lineage writes.
        existing_lineage = self._lineage_pointer_precheck(
            ctx=lineage_ctx,
            raw_artifact=plan.raw_artifact,
            structured_artifact=plan.structured_artifact,
            raw_envelope_hash=plan.raw_envelope_hash,
            raw_envelope_length=plan.raw_envelope_length,
            structured_hash=plan.structured_hash,
            structured_length=plan.structured_length,
            scoring_call_request=plan.scoring_call_request,
            judge_call_request=plan.judge_call_request,
            scoring_call_completion=plan.scoring_call_completion,
            judge_call_completion=plan.judge_call_completion,
            scoring_summary=plan.scoring_summary,
            raw_final=raw_final,
            structured_final=structured_final,
        )
        if existing_lineage is not None:
            return existing_lineage

        # Strict same-plan idempotency: check if a complete committed graph
        # already exists before attempting any write.
        existing = self._check_committed_graph(
            raw_artifact=plan.raw_artifact,
            structured_artifact=plan.structured_artifact,
            raw_envelope_hash=plan.raw_envelope_hash,
            raw_envelope_length=plan.raw_envelope_length,
            structured_hash=plan.structured_hash,
            structured_length=plan.structured_length,
            scoring_call_request=plan.scoring_call_request,
            judge_call_request=plan.judge_call_request,
            scoring_call_completion=plan.scoring_call_completion,
            judge_call_completion=plan.judge_call_completion,
            scoring_summary=plan.scoring_summary,
            video_id=plan.video_id,
            raw_final=raw_final,
            structured_final=structured_final,
        )
        if existing is not None:
            return existing

        self._write_atomic_file(
            final_path=raw_final,
            content=plan.raw_envelope_bytes,
            expected_hash=plan.raw_envelope_hash,
            video_id=plan.video_id,
        )
        self._write_atomic_file(
            final_path=structured_final,
            content=plan.structured_bytes,
            expected_hash=plan.structured_hash,
            video_id=plan.video_id,
        )

        try:
            now = self._clock()
            now_text = format_utc_datetime(now)
            lease_until = now + timedelta(minutes=5)
            repository = cast(Any, self._repository)
            connection = repository._connect()
            try:
                try:
                    with _immediate_transaction(connection):
                        job_row = repository._owned_running_job(
                            connection,
                            job_id=self._context.job_id,
                            owner=self._context.owner,
                            now=now_text,
                        )
                        if (
                            job_row["video_id"] != plan.video_id
                            or job_row["pipeline_version"]
                            != self._context.pipeline_version
                        ):
                            raise ConcurrencyConflict(
                                "job scope does not match atomic registration"
                            )
                        if job_row["target_stage"] != ProcessingStage.SCORING.value:
                            raise ConcurrencyConflict("job target stage is not SCORING")

                        repository._inject_failure("atomic_register.before_artifacts")
                        raw_record = repository._upsert_artifact_in_transaction(
                            connection, plan.raw_artifact, now=now_text
                        )
                        structured_record = repository._upsert_artifact_in_transaction(
                            connection, plan.structured_artifact, now=now_text
                        )
                        repository._inject_failure("atomic_register.after_artifacts")
                        scoring_record = repository._reserve_provider_call_in_transaction(
                            connection,
                            plan.scoring_call_request,
                            owner=self._context.owner,
                            lease_until=lease_until,
                            available_at=now,
                            now=now,
                        )
                        judge_record = repository._reserve_provider_call_in_transaction(
                            connection,
                            plan.judge_call_request,
                            owner=self._context.owner,
                            lease_until=lease_until,
                            available_at=now,
                            now=now,
                        )
                        repository._inject_failure("atomic_register.after_reservations")
                        if scoring_record.status is ProviderCallStatus.PENDING:
                            scoring_record = repository._complete_provider_call_in_transaction(
                                connection,
                                plan.scoring_call_completion,
                                owner=self._context.owner,
                                now=now_text,
                            )
                        if judge_record.status is ProviderCallStatus.PENDING:
                            judge_record = repository._complete_provider_call_in_transaction(
                                connection,
                                plan.judge_call_completion,
                                owner=self._context.owner,
                                now=now_text,
                            )
                        repository._inject_failure("atomic_register.after_provider_calls")
                        self._apply_lineage_cas_in_transaction(
                            connection,
                            repository,
                            ctx=lineage_ctx,
                            job_row=job_row,
                            now_text=now_text,
                        )
                        changed = connection.execute(
                            "UPDATE videos SET pipeline_status = :target_status, "
                            "score = :score, should_summarize = :should_summarize, "
                            "updated_at = :now, completed_at = NULL "
                            "WHERE video_id = :video_id "
                            "AND pipeline_status = :expected_status "
                            "AND pipeline_version = :pipeline_version",
                            {
                                "target_status": PipelineStatus.SCORED.value,
                                "score": plan.scoring_summary.score,
                                "should_summarize": int(
                                    plan.scoring_summary.should_summarize
                                ),
                                "now": now_text,
                                "video_id": plan.video_id,
                                "expected_status": PipelineStatus.TRANSCRIPT_READY.value,
                                "pipeline_version": self._context.pipeline_version,
                            },
                        ).rowcount
                        if changed != 1:
                            raise ConcurrencyConflict(
                                "pipeline changed before atomic scoring registration"
                            )
                        repository._inject_failure("atomic_register.after_pipeline")
                        job = repository._finish_job_success_in_transaction(
                            connection,
                            job_id=self._context.job_id,
                            owner=self._context.owner,
                            now=now_text,
                        )
                        video_row = connection.execute(
                            "SELECT * FROM videos WHERE video_id = :video_id",
                            {"video_id": plan.video_id},
                        ).fetchone()
                        if video_row is None:
                            raise StateStoreError("completed video could not be read")
                        return StageCompletionResult(
                            job=job,
                            video=repository._video_from_row(video_row),
                            artifacts=(raw_record, structured_record),
                            provider_call=scoring_record,
                        )
                except sqlite3.IntegrityError as error:
                    raise IntegrityConflict(
                        "atomic scoring registration violates repository integrity"
                    ) from error
                except _H2CLineageCasZeroRow as zero:
                    # The BEGIN IMMEDIATE transaction is already rolled back by
                    # the exception; classification used tx-local reads before
                    # the rollback, and the terminal fail_job (when authorized)
                    # happens only after a fresh lease re-proof.
                    return self._dispatch_lineage_cas_finding(
                        zero,
                        ctx=lineage_ctx,
                        raw_artifact=plan.raw_artifact,
                        structured_artifact=plan.structured_artifact,
                        raw_envelope_hash=plan.raw_envelope_hash,
                        raw_envelope_length=plan.raw_envelope_length,
                        structured_hash=plan.structured_hash,
                        structured_length=plan.structured_length,
                        scoring_call_request=plan.scoring_call_request,
                        judge_call_request=plan.judge_call_request,
                        scoring_call_completion=plan.scoring_call_completion,
                        judge_call_completion=plan.judge_call_completion,
                        scoring_summary=plan.scoring_summary,
                        raw_final=raw_final,
                        structured_final=structured_final,
                    )
            finally:
                connection.close()
        except ScoringPersistenceError:
            raise
        except (
            H2CStaleScoringLease,
            H2CAuthoritativeGraphConflict,
            _H2CLineageTerminalHandled,
        ):
            raise
        except Exception as error:
            from youtube_intel.pipeline import PipelineInterrupted

            if isinstance(error, PipelineInterrupted):
                raise
            msg = f"atomic scoring registration failed: {error}"
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=msg,
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error

    def _check_committed_graph(
        self,
        *,
        raw_artifact: ArtifactWrite,
        structured_artifact: ArtifactWrite,
        raw_envelope_hash: str,
        raw_envelope_length: int,
        structured_hash: str,
        structured_length: int,
        scoring_call_request: ProviderCallRequest,
        judge_call_request: ProviderCallRequest,
        scoring_call_completion: ProviderCallCompletion,
        judge_call_completion: ProviderCallCompletion,
        scoring_summary: ScoringSummaryWrite,
        video_id: str,
        raw_final: Path,
        structured_final: Path,
    ) -> StageCompletionResult | None:
        """Return existing committed result if the full graph matches the plan.

        If files exist, every design field must match exactly.  If files exist
        but any field mismatches, fail-closed (do not attempt to overwrite or
        repair).  If no files exist, return None (normal first-write path).
        """

        plan = SimpleNamespace(
            raw_artifact=raw_artifact,
            structured_artifact=structured_artifact,
            raw_envelope_hash=raw_envelope_hash,
            raw_envelope_length=raw_envelope_length,
            structured_hash=structured_hash,
            structured_length=structured_length,
            scoring_call_request=scoring_call_request,
            judge_call_request=judge_call_request,
            scoring_call_completion=scoring_call_completion,
            judge_call_completion=judge_call_completion,
            scoring_summary=scoring_summary,
            video_id=video_id,
        )
        raw_exists = raw_final.exists()
        structured_exists = structured_final.exists()

        if not raw_exists and not structured_exists:
            return None

        # If only one file exists, this is a partial/orphan state — fail-closed.
        if raw_exists != structured_exists:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=(
                        f"partial artifact state: raw_exists={raw_exists}, "
                        f"structured_exists={structured_exists}"
                    ),
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )

        # Both files exist — verify the complete committed graph.
        raw_body = self._read_existing_final(raw_final, plan.video_id)
        structured_body = self._read_existing_final(
            structured_final, plan.video_id
        )
        self._verify_existing_final(
            raw_final,
            raw_body,
            plan.raw_envelope_hash,
            plan.raw_envelope_length,
            plan.raw_artifact.relative_path,
            plan.video_id,
        )
        self._verify_existing_final(
            structured_final,
            structured_body,
            plan.structured_hash,
            plan.structured_length,
            plan.structured_artifact.relative_path,
            plan.video_id,
        )

        # Verify the DB graph: Artifacts, ProviderCalls, video/stage/job.
        repo = self._repository
        raw_record = repo.get_artifact_by_key(plan.raw_artifact.artifact_key)
        structured_record = repo.get_artifact_by_key(
            plan.structured_artifact.artifact_key
        )
        if raw_record is None or structured_record is None:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="files exist but Artifact rows are missing",
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        self._verify_artifact_record(
            record=raw_record,
            expected=plan.raw_artifact,
            expected_final=raw_final,
            video_id=plan.video_id,
        )
        self._verify_artifact_record(
            record=structured_record,
            expected=plan.structured_artifact,
            expected_final=structured_final,
            video_id=plan.video_id,
        )

        scoring_call = repo.get_provider_call(
            plan.scoring_call_request.request_hash
        )
        judge_call = repo.get_provider_call(
            plan.judge_call_request.request_hash
        )
        if scoring_call is None or judge_call is None:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="files exist but ProviderCall rows are missing",
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        self._verify_provider_call_record(
            record=scoring_call,
            request=plan.scoring_call_request,
            completion=plan.scoring_call_completion,
            raw_artifact_id=plan.raw_artifact.artifact_id,
            video_id=plan.video_id,
        )
        self._verify_provider_call_record(
            record=judge_call,
            request=plan.judge_call_request,
            completion=plan.judge_call_completion,
            raw_artifact_id=plan.raw_artifact.artifact_id,
            video_id=plan.video_id,
        )

        video = repo.get_video(plan.video_id)
        if video is None or video.pipeline_status is not PipelineStatus.SCORED:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="files exist but video is not SCORED",
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        if video.score != plan.scoring_summary.score:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="existing video score mismatch",
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        if video.should_summarize != plan.scoring_summary.should_summarize:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="existing video should_summarize mismatch",
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )

        job = repo.get_job(self._context.job_id)
        if job is None or job.status is not JobStatus.SUCCEEDED:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message="files exist but job is not SUCCEEDED",
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        self._verify_job_record(
            record=job,
            expected_job_id=self._context.job_id,
            expected_video_id=plan.video_id,
            expected_pipeline_version=self._context.pipeline_version,
            video_id=plan.video_id,
        )

        # Complete committed graph matches — return existing result.
        return StageCompletionResult(
            job=job,
            video=video,
            artifacts=(raw_record, structured_record),
            provider_call=scoring_call,
        )

    def _read_existing_final(self, final_path: Path, video_id: str) -> bytes:
        try:
            return final_path.read_bytes()
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to read existing final {final_path}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error

    def _verify_existing_final(
        self,
        final_path: Path,
        body: bytes,
        expected_hash: str,
        expected_length: int,
        expected_relative_path: str,
        video_id: str,
    ) -> None:
        expected_path = self._data_root / expected_relative_path
        if final_path.resolve() != expected_path.resolve():
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=(
                        f"existing final path mismatch: "
                        f"expected {expected_path}, got {final_path}"
                    ),
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        if len(body) != expected_length:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=(
                        f"existing final {final_path} length mismatch: "
                        f"expected {expected_length}, got {len(body)}"
                    ),
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        if hashlib.sha256(body).hexdigest() != expected_hash:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"existing final {final_path} hash mismatch",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            )

    def _verify_artifact_record(
        self,
        *,
        record: ArtifactRecord,
        expected: ArtifactWrite,
        expected_final: Path,
        video_id: str,
    ) -> None:
        expected_path = self._data_root / expected.relative_path
        record_path = self._data_root / record.relative_path
        # Exact relative_path string is the primary check; Path.resolve() can
        # normalize away differences that the design treats as distinct.
        checks: list[tuple[bool, str]] = [
            (record.artifact_id == expected.artifact_id, "artifact_id"),
            (record.artifact_key == expected.artifact_key, "artifact_key"),
            (record.video_id == expected.video_id, "video_id"),
            (record.job_id == expected.job_id, "job_id"),
            (record.kind is expected.kind, "kind"),
            (record.storage_root is expected.storage_root, "storage_root"),
            (record.relative_path == expected.relative_path, "relative_path"),
            (
                record_path.resolve() == expected_path.resolve(),
                "absolute_path",
            ),
            (record.content_hash == expected.content_hash, "content_hash"),
            (record.provider == expected.provider, "provider"),
            (record.model == expected.model, "model"),
            (
                record.producer_version == expected.producer_version,
                "producer_version",
            ),
            (
                record.retention_class is expected.retention_class,
                "retention_class",
            ),
            (record.expires_at == expected.expires_at, "expires_at"),
        ]
        for ok, field in checks:
            if not ok:
                raise ScoringPersistenceError(
                    AppError(
                        code=ErrorCode.LOCAL_RESOURCE,
                        message=(
                            f"existing Artifact {field} mismatch: "
                            f"expected {getattr(expected, field)!r}, "
                            f"got {getattr(record, field)!r}"
                        ),
                        retryable=False,
                        video_id=video_id,
                        stage=ProcessingStage.SCORING,
                    )
                )

    def _verify_provider_call_record(
        self,
        *,
        record: ProviderCallRecord,
        request: ProviderCallRequest,
        completion: ProviderCallCompletion,
        raw_artifact_id: str,
        video_id: str,
    ) -> None:
        checks: list[tuple[bool, str]] = [
            (record.request_hash == request.request_hash, "request_hash"),
            (record.operation == request.operation, "operation"),
            (record.provider == request.provider, "provider"),
            (record.model == request.model, "model"),
            (record.prompt_version == request.prompt_version, "prompt_version"),
            (record.schema_version == request.schema_version, "schema_version"),
            (record.status is ProviderCallStatus.SUCCEEDED, "status"),
            (
                record.response_artifact_id == raw_artifact_id,
                "response_artifact_id",
            ),
            (
                record.response_artifact_id == completion.response_artifact_id,
                "completion response_artifact_id",
            ),
        ]
        for ok, field in checks:
            if not ok:
                raise ScoringPersistenceError(
                    AppError(
                        code=ErrorCode.LOCAL_RESOURCE,
                        message=f"existing ProviderCall {field} mismatch",
                        retryable=False,
                        video_id=video_id,
                        stage=ProcessingStage.SCORING,
                    )
                )

    def _verify_job_record(
        self,
        *,
        record: JobRecord,
        expected_job_id: str,
        expected_video_id: str,
        expected_pipeline_version: str,
        video_id: str,
    ) -> None:
        checks: list[tuple[bool, str]] = [
            (record.job_id == expected_job_id, "job_id"),
            (record.video_id == expected_video_id, "video_id"),
            (record.job_type is JobType.VIDEO_STAGE, "job_type"),
            (record.target_stage is ProcessingStage.SCORING, "target_stage"),
            (
                record.pipeline_version == expected_pipeline_version,
                "pipeline_version",
            ),
            (record.status is JobStatus.SUCCEEDED, "status"),
        ]
        for ok, field in checks:
            if not ok:
                raise ScoringPersistenceError(
                    AppError(
                        code=ErrorCode.LOCAL_RESOURCE,
                        message=f"existing Job {field} mismatch",
                        retryable=False,
                        video_id=video_id,
                        stage=ProcessingStage.SCORING,
                    )
                )

    def _write_atomic_file(
        self,
        *,
        final_path: Path,
        content: bytes,
        expected_hash: str,
        video_id: str,
    ) -> None:
        """Write one artifact through the Phase G durability ordering.

        Atomic no-clobber promote uses ``os.link(tmp, final)`` which
        atomically fails with ``EEXIST`` if the destination already
        exists, followed by ``os.unlink(tmp)``.  This eliminates the
        TOCTOU race that ``exists() + os.rename()`` would introduce and
        prevents silent overwrites that POSIX ``rename`` permits.
        """

        final_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp_path = final_path.with_name(final_path.name + ".tmp")
        # Stale-tmp detection uses O_EXCL so it is itself atomic.
        try:
            fd = os.open(
                tmp_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"stale temporary artifact at {tmp_path}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from None
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to create temporary artifact {tmp_path}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error
        try:
            os.write(fd, content)
            os.fsync(fd)
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to write temporary artifact {tmp_path}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error
        finally:
            os.close(fd)

        # Verify the temporary file before promotion.
        self._verify_file_hash(tmp_path, content, expected_hash, video_id=video_id)

        # Atomic no-clobber promote: os.link atomically creates the hard
        # link and fails with EEXIST if the destination already exists.
        # Unlike os.rename, it can never silently overwrite an existing
        # final.  If this succeeds the final path now references the same
        # inode as the tmp; we then unlink the tmp name.
        try:
            os.link(tmp_path, final_path)
        except FileExistsError:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"artifact already exists at {final_path}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from None
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to promote {tmp_path} to {final_path}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error

        # The link succeeded; remove the temporary name so only the final
        # path references the inode.
        try:
            os.unlink(tmp_path)
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to unlink temporary {tmp_path}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error

        # Fsync parent directory so the link is durable.
        parent_fd = os.open(final_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to fsync artifact directory {final_path.parent}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error
        finally:
            os.close(parent_fd)

        # Final verify after promotion.
        self._verify_file_hash(final_path, content, expected_hash, video_id=video_id)

    def _verify_file_hash(
        self,
        path: Path,
        expected_content: bytes,
        expected_hash: str,
        *,
        video_id: str,
    ) -> None:
        """Re-read a file and assert length/hash."""

        try:
            actual_content = path.read_bytes()
        except OSError as error:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"failed to read artifact {path}: {error}",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error
        if len(actual_content) != len(expected_content):
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=(
                        f"artifact {path} length mismatch: "
                        f"expected {len(expected_content)}, got {len(actual_content)}"
                    ),
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            )
        actual_hash = hashlib.sha256(actual_content).hexdigest()
        if actual_hash != expected_hash:
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=f"artifact {path} hash mismatch",
                    retryable=False,
                    video_id=video_id,
                    stage=ProcessingStage.SCORING,
                )
            )

    # ------------------------------------------------------------------
    # TASK-016C Phase H2-C lineage CAS and REPAIR persistence
    # ------------------------------------------------------------------

    def _apply_lineage_cas_in_transaction(
        self,
        connection: sqlite3.Connection,
        repository: Any,
        *,
        ctx: _H2CLineageCasContext,
        job_row: sqlite3.Row,
        now_text: str,
    ) -> None:
        """Run the Job pointer/provenance CAS then the Video first-success CAS.

        Pre-v2 NULL-generation jobs keep the frozen behavior with no lineage
        writes.  A zero-row CAS raises the classified carrier exception after
        tx-local read-back; the surrounding transaction rolls it back.
        """

        generation = job_row["scoring_lineage_version"]
        if generation is None:
            return
        if generation != SCORING_LINEAGE_VERSION_V1:
            raise _H2CLineageCasZeroRow(
                _H2CLineageCasFinding.TERMINAL_JOB_UNEXPECTED, is_video_cas=False
            )
        job_changed = connection.execute(
            "UPDATE jobs SET "
            "authoritative_scoring_artifact_key = :key, "
            "scoring_success_provenance = :provenance, updated_at = :now "
            "WHERE job_id = :job_id AND job_type = 'VIDEO_STAGE' "
            "AND target_stage = 'SCORING' AND video_id = :video_id "
            "AND pipeline_version = :pipeline_version "
            "AND scoring_lineage_version = :generation "
            "AND status = 'RUNNING' AND lease_owner = :owner "
            "AND lease_until > :now "
            "AND authoritative_scoring_artifact_key IS NULL "
            "AND scoring_success_provenance IS NULL",
            {
                "key": ctx.structured_key,
                "provenance": ctx.provenance,
                "now": now_text,
                "job_id": ctx.job_id,
                "video_id": ctx.video_id,
                "pipeline_version": ctx.pipeline_version,
                "generation": SCORING_LINEAGE_VERSION_V1,
                "owner": ctx.owner,
            },
        ).rowcount
        if job_changed != 1:
            finding = self._classify_job_lineage_cas_zero_row(
                connection, repository, ctx=ctx, now_text=now_text
            )
            raise _H2CLineageCasZeroRow(finding, is_video_cas=False)
        video_changed = connection.execute(
            "UPDATE videos SET authoritative_scoring_job_id = :job_id "
            "WHERE video_id = :video_id "
            "AND authoritative_scoring_job_id IS NULL "
            "AND pipeline_status = :expected_status "
            "AND pipeline_version = :pipeline_version",
            {
                "job_id": ctx.job_id,
                "video_id": ctx.video_id,
                "expected_status": PipelineStatus.TRANSCRIPT_READY.value,
                "pipeline_version": ctx.pipeline_version,
            },
        ).rowcount
        if video_changed != 1:
            finding = self._classify_video_lineage_cas_zero_row(
                connection, repository, ctx=ctx, now_text=now_text
            )
            raise _H2CLineageCasZeroRow(finding, is_video_cas=True)

    @staticmethod
    def _owned_active_now(job: Any, owner: str, now: datetime) -> bool:
        return (
            job is not None
            and job.status is JobStatus.RUNNING
            and job.lease_owner == owner
            and job.lease_until is not None
            and job.lease_until > now
        )

    def _classify_job_lineage_cas_zero_row(
        self,
        connection: sqlite3.Connection,
        repository: Any,
        *,
        ctx: _H2CLineageCasContext,
        now_text: str,
    ) -> _H2CLineageCasFinding:
        """Classify one zero-row Job lineage CAS on the same transaction."""

        now = datetime.fromisoformat(now_text.replace("Z", "+00:00"))
        job = repository._read_job_in_transaction(connection, ctx.job_id)
        if job is None:
            return _H2CLineageCasFinding.MISSING_JOB
        owned = self._owned_active_now(job, ctx.owner, now)
        identity_ok = (
            job.job_type is JobType.VIDEO_STAGE
            and job.target_stage is ProcessingStage.SCORING
            and job.video_id == ctx.video_id
            and job.pipeline_version == ctx.pipeline_version
        )
        generation_ok = job.scoring_lineage_version == SCORING_LINEAGE_VERSION_V1
        if not identity_ok or not generation_ok:
            if job.status is JobStatus.RUNNING and owned:
                return _H2CLineageCasFinding.TERMINAL_JOB_UNEXPECTED
            if job.status is JobStatus.RUNNING:
                return _H2CLineageCasFinding.STALE_LEASE
            if job.status is JobStatus.FAILED_FINAL:
                return _H2CLineageCasFinding.STALE_LEASE
            return _H2CLineageCasFinding.INTERRUPTED
        if job.status is JobStatus.RUNNING and not owned:
            return _H2CLineageCasFinding.STALE_LEASE
        if job.status is JobStatus.SUCCEEDED:
            if (
                job.authoritative_scoring_artifact_key == ctx.structured_key
                and job.scoring_success_provenance == ctx.provenance
            ):
                return _H2CLineageCasFinding.IDEMPOTENT
            return _H2CLineageCasFinding.COMMITTED_CONFLICT
        if job.status is JobStatus.FAILED_FINAL:
            return _H2CLineageCasFinding.STALE_LEASE
        # Active owned RUNNING with a failed predicate or prepopulated pointer.
        if (
            job.authoritative_scoring_artifact_key is not None
            or job.scoring_success_provenance is not None
        ):
            if (
                job.authoritative_scoring_artifact_key == ctx.structured_key
                and job.scoring_success_provenance == ctx.provenance
            ):
                return _H2CLineageCasFinding.TERMINAL_JOB_UNEXPECTED
            return _H2CLineageCasFinding.TERMINAL_GRAPH_CONFLICT
        if job.status is not JobStatus.RUNNING:
            return _H2CLineageCasFinding.INTERRUPTED
        return _H2CLineageCasFinding.TERMINAL_JOB_UNEXPECTED

    def _classify_video_lineage_cas_zero_row(
        self,
        connection: sqlite3.Connection,
        repository: Any,
        *,
        ctx: _H2CLineageCasContext,
        now_text: str,
    ) -> _H2CLineageCasFinding:
        """Classify one zero-row Video lineage CAS on the same transaction."""

        now = datetime.fromisoformat(now_text.replace("Z", "+00:00"))
        video = repository._read_video_in_transaction(connection, ctx.video_id)
        if video is None:
            return _H2CLineageCasFinding.MISSING_VIDEO
        job = repository._read_job_in_transaction(connection, ctx.job_id)
        if job is None:
            return _H2CLineageCasFinding.MISSING_JOB
        if not self._owned_active_now(job, ctx.owner, now):
            return _H2CLineageCasFinding.STALE_LEASE
        if video.pipeline_version != ctx.pipeline_version:
            return _H2CLineageCasFinding.TERMINAL_VIDEO_UNEXPECTED
        if video.pipeline_status is not PipelineStatus.TRANSCRIPT_READY:
            return _H2CLineageCasFinding.TERMINAL_VIDEO_UNEXPECTED
        if video.authoritative_scoring_job_id == ctx.job_id:
            return _H2CLineageCasFinding.TERMINAL_VIDEO_UNEXPECTED
        if video.authoritative_scoring_job_id is not None:
            return _H2CLineageCasFinding.TERMINAL_VIDEO_CONFLICT
        return _H2CLineageCasFinding.TERMINAL_VIDEO_UNEXPECTED

    def _terminalize_lineage_integrity(
        self, ctx: _H2CLineageCasContext, *, detail: str
    ) -> NoReturn:
        """Re-prove the lease, then write exactly one integrity fail_job.

        Never called inside the failed persistence transaction.  If the lease
        re-proof fails, the stale no-mutation path is taken instead.
        """

        repository = cast(Any, self._repository)
        now = self._clock()
        job = repository.get_job(ctx.job_id)
        if not self._owned_active_now(job, ctx.owner, now):
            raise H2CStaleScoringLease(
                "lease lost before lineage integrity terminalization"
            )
        try:
            repository.fail_job(
                ctx.job_id,
                owner=ctx.owner,
                error_code=ErrorCode.TRUST_INTEGRITY_INVALID,
                error_message=detail,
                retry_at=None,
                now=now,
            )
        except LeaseConflict as error:
            raise H2CStaleScoringLease(
                "lease lost during lineage integrity terminalization"
            ) from error
        confirmed = repository.get_job(ctx.job_id)
        if confirmed is None or confirmed.status is not JobStatus.FAILED_FINAL:
            from youtube_intel.scoring_admission import UnknownProviderState

            raise UnknownProviderState(
                "lineage integrity terminalization could not be finalized"
            )
        raise _H2CLineageTerminalHandled(detail)

    def _build_committed_lineage_result(
        self,
        *,
        ctx: _H2CLineageCasContext,
        scoring_call_request: ProviderCallRequest,
    ) -> StageCompletionResult:
        repository = cast(Any, self._repository)
        job = repository.get_job(ctx.job_id)
        video = repository.get_video(ctx.video_id)
        raw_record = repository.get_artifact_by_key(ctx.raw_key)
        structured_record = repository.get_artifact_by_key(ctx.structured_key)
        scoring_call = repository.get_provider_call(
            scoring_call_request.request_hash
        )
        if (
            job is None
            or video is None
            or raw_record is None
            or structured_record is None
            or scoring_call is None
            or job.status is not JobStatus.SUCCEEDED
            or job.authoritative_scoring_artifact_key != ctx.structured_key
            or job.scoring_success_provenance != ctx.provenance
            or video.authoritative_scoring_job_id != ctx.job_id
        ):
            raise H2CAuthoritativeGraphConflict(
                "idempotent committed lineage graph could not be verified"
            )
        return StageCompletionResult(
            job=job,
            video=video,
            artifacts=(raw_record, structured_record),
            provider_call=scoring_call,
        )

    def _dispatch_lineage_cas_finding(
        self,
        zero: _H2CLineageCasZeroRow,
        *,
        ctx: _H2CLineageCasContext,
        raw_artifact: ArtifactWrite,
        structured_artifact: ArtifactWrite,
        raw_envelope_hash: str,
        raw_envelope_length: int,
        structured_hash: str,
        structured_length: int,
        scoring_call_request: ProviderCallRequest,
        judge_call_request: ProviderCallRequest,
        scoring_call_completion: ProviderCallCompletion,
        judge_call_completion: ProviderCallCompletion,
        scoring_summary: ScoringSummaryWrite,
        raw_final: Path,
        structured_final: Path,
    ) -> StageCompletionResult:
        """Act on a classified zero-row lineage CAS after rollback."""

        finding = zero.finding
        if finding in {
            _H2CLineageCasFinding.MISSING_JOB,
            _H2CLineageCasFinding.MISSING_VIDEO,
        }:
            from youtube_intel.pipeline import PipelineInterrupted

            raise PipelineInterrupted(
                "lineage CAS observed a missing job or video row"
            )
        if finding is _H2CLineageCasFinding.STALE_LEASE:
            raise H2CStaleScoringLease("lineage CAS lost the active lease")
        if finding is _H2CLineageCasFinding.COMMITTED_CONFLICT:
            raise H2CAuthoritativeGraphConflict(
                "committed authoritative graph conflicts with the trusted plan"
            )
        if finding is _H2CLineageCasFinding.IDEMPOTENT:
            if not self._committed_lineage_graph_matches(
                ctx=ctx,
                raw_artifact=raw_artifact,
                structured_artifact=structured_artifact,
                raw_envelope_hash=raw_envelope_hash,
                raw_envelope_length=raw_envelope_length,
                structured_hash=structured_hash,
                structured_length=structured_length,
                scoring_call_request=scoring_call_request,
                judge_call_request=judge_call_request,
                scoring_call_completion=scoring_call_completion,
                judge_call_completion=judge_call_completion,
                scoring_summary=scoring_summary,
                raw_final=raw_final,
                structured_final=structured_final,
            ):
                raise H2CAuthoritativeGraphConflict(
                    "idempotent lineage graph is incomplete after read-back"
                )
            return self._build_committed_lineage_result(
                ctx=ctx, scoring_call_request=scoring_call_request
            )
        detail = _H2C_LINEAGE_TERMINAL_DETAILS[finding]
        self._terminalize_lineage_integrity(ctx, detail=detail)

    def _committed_lineage_graph_matches(
        self,
        *,
        ctx: _H2CLineageCasContext,
        raw_artifact: ArtifactWrite,
        structured_artifact: ArtifactWrite,
        raw_envelope_hash: str,
        raw_envelope_length: int,
        structured_hash: str,
        structured_length: int,
        scoring_call_request: ProviderCallRequest,
        judge_call_request: ProviderCallRequest,
        scoring_call_completion: ProviderCallCompletion,
        judge_call_completion: ProviderCallCompletion,
        scoring_summary: ScoringSummaryWrite,
        raw_final: Path,
        structured_final: Path,
    ) -> bool:
        """Return True only if the complete committed lineage graph matches."""

        repository = cast(Any, self._repository)
        try:
            job = repository.get_job(ctx.job_id)
            video = repository.get_video(ctx.video_id)
            if (
                job is None
                or video is None
                or job.status is not JobStatus.SUCCEEDED
                or job.job_type is not JobType.VIDEO_STAGE
                or job.target_stage is not ProcessingStage.SCORING
                or job.video_id != ctx.video_id
                or job.pipeline_version != ctx.pipeline_version
                or job.authoritative_scoring_artifact_key != ctx.structured_key
                or job.scoring_success_provenance != ctx.provenance
                or video.authoritative_scoring_job_id != ctx.job_id
                or video.pipeline_status is not PipelineStatus.SCORED
                or video.score != scoring_summary.score
                or video.should_summarize != scoring_summary.should_summarize
            ):
                return False
            if not raw_final.exists() or not structured_final.exists():
                return False
            raw_body = raw_final.read_bytes()
            structured_body = structured_final.read_bytes()
            if (
                len(raw_body) != raw_envelope_length
                or hashlib.sha256(raw_body).hexdigest() != raw_envelope_hash
                or len(structured_body) != structured_length
                or hashlib.sha256(structured_body).hexdigest() != structured_hash
            ):
                return False
            raw_record = repository.get_artifact_by_key(raw_artifact.artifact_key)
            structured_record = repository.get_artifact_by_key(
                structured_artifact.artifact_key
            )
            if raw_record is None or structured_record is None:
                return False
            self._verify_artifact_record(
                record=raw_record,
                expected=raw_artifact,
                expected_final=raw_final,
                video_id=ctx.video_id,
            )
            self._verify_artifact_record(
                record=structured_record,
                expected=structured_artifact,
                expected_final=structured_final,
                video_id=ctx.video_id,
            )
            scoring_call = repository.get_provider_call(
                scoring_call_request.request_hash
            )
            judge_call = repository.get_provider_call(
                judge_call_request.request_hash
            )
            if scoring_call is None or judge_call is None:
                return False
            self._verify_provider_call_record(
                record=scoring_call,
                request=scoring_call_request,
                completion=scoring_call_completion,
                raw_artifact_id=raw_artifact.artifact_id,
                video_id=ctx.video_id,
            )
            self._verify_provider_call_record(
                record=judge_call,
                request=judge_call_request,
                completion=judge_call_completion,
                raw_artifact_id=raw_artifact.artifact_id,
                video_id=ctx.video_id,
            )
            return True
        except (ScoringPersistenceError, OSError, ValueError):
            return False

    def _lineage_pointer_precheck(
        self,
        *,
        ctx: _H2CLineageCasContext,
        raw_artifact: ArtifactWrite,
        structured_artifact: ArtifactWrite,
        raw_envelope_hash: str,
        raw_envelope_length: int,
        structured_hash: str,
        structured_length: int,
        scoring_call_request: ProviderCallRequest,
        judge_call_request: ProviderCallRequest,
        scoring_call_completion: ProviderCallCompletion,
        judge_call_completion: ProviderCallCompletion,
        scoring_summary: ScoringSummaryWrite,
        raw_final: Path,
        structured_final: Path,
    ) -> StageCompletionResult | None:
        """Inspect the durable pointer state before any filesystem effect.

        NULL-generation jobs retain the frozen legacy behavior (None).  A
        complete committed v1 graph returns the idempotent result.  Conflicts
        fail closed exactly as the transaction-local classification would.
        """

        from youtube_intel.pipeline import PipelineInterrupted

        repository = cast(Any, self._repository)
        job = repository.get_job(ctx.job_id)
        if job is None:
            raise PipelineInterrupted("persistence job row is missing")
        generation = job.scoring_lineage_version
        if generation is None:
            return None
        if generation != SCORING_LINEAGE_VERSION_V1:
            self._terminalize_lineage_integrity(
                ctx, detail="H2C_JOB_LINEAGE_CAS_UNEXPECTED"
            )
        stored_key = job.authoritative_scoring_artifact_key
        stored_provenance = job.scoring_success_provenance
        if stored_key is None and stored_provenance is None:
            return None
        if job.status is JobStatus.SUCCEEDED:
            if (
                stored_key == ctx.structured_key
                and stored_provenance == ctx.provenance
                and self._committed_lineage_graph_matches(
                    ctx=ctx,
                    raw_artifact=raw_artifact,
                    structured_artifact=structured_artifact,
                    raw_envelope_hash=raw_envelope_hash,
                    raw_envelope_length=raw_envelope_length,
                    structured_hash=structured_hash,
                    structured_length=structured_length,
                    scoring_call_request=scoring_call_request,
                    judge_call_request=judge_call_request,
                    scoring_call_completion=scoring_call_completion,
                    judge_call_completion=judge_call_completion,
                    scoring_summary=scoring_summary,
                    raw_final=raw_final,
                    structured_final=structured_final,
                )
            ):
                return self._build_committed_lineage_result(
                    ctx=ctx, scoring_call_request=scoring_call_request
                )
            raise H2CAuthoritativeGraphConflict(
                "committed authoritative graph differs from the trusted plan"
            )
        now = self._clock()
        if job.status is JobStatus.RUNNING and self._owned_active_now(
            job, ctx.owner, now
        ):
            if (
                stored_key == ctx.structured_key
                and stored_provenance == ctx.provenance
            ):
                self._terminalize_lineage_integrity(
                    ctx, detail="H2C_JOB_LINEAGE_CAS_UNEXPECTED"
                )
            self._terminalize_lineage_integrity(
                ctx, detail="H2C_AUTHORITATIVE_GRAPH_CONFLICT"
            )
        if job.status is JobStatus.RUNNING or job.status is JobStatus.FAILED_FINAL:
            raise H2CStaleScoringLease(
                "authoritative pointer exists without an owned active lease"
            )
        raise PipelineInterrupted("authoritative pointer state is inconsistent")

    # ------------------------------------------------------------------
    # REPAIR (H2-C) persistence
    # ------------------------------------------------------------------

    def _repair_persistence_error(
        self, message: str, video_id: str
    ) -> ScoringPersistenceError:
        return ScoringPersistenceError(
            AppError(
                code=ErrorCode.LOCAL_RESOURCE,
                message=message,
                retryable=False,
                video_id=video_id,
                stage=ProcessingStage.SCORING,
            )
        )

    def _open_repair_graph_directory(self, *, p: str, g: str, video_id: str) -> int:
        """Open the verified ``DATA/scoring/<P>/repair/<G>`` descriptor.

        Descriptor-anchored, no-follow, no-special-file, one level at a time.
        Newly created levels fsync parent and child before a descendant is
        created.  Absence of a required primitive is a LOCAL_RESOURCE
        fail-closed condition; there is no insecure pathname fallback.
        """

        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise self._repair_persistence_error(
                "platform lacks the repair directory safety primitives",
                video_id,
            )
        _validate_lower_hex(p, field_name="primary_request_hash")
        _validate_lower_hex(g, field_name="graph_hash")
        dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fds: list[int] = []
        try:
            root_fd = os.open(self._data_root, dir_flags)
            fds.append(root_fd)
            for component in ("scoring", p, "repair", g):
                current_fd = fds[-1]
                try:
                    child_fd = os.open(component, dir_flags, dir_fd=current_fd)
                except FileNotFoundError:
                    try:
                        os.mkdir(component, 0o700, dir_fd=current_fd)
                    except FileExistsError:
                        child_fd = os.open(component, dir_flags, dir_fd=current_fd)
                    else:
                        os.fsync(current_fd)
                        child_fd = os.open(component, dir_flags, dir_fd=current_fd)
                        os.fsync(child_fd)
                fds.append(child_fd)
            return fds.pop()
        except OSError as error:
            raise self._repair_persistence_error(
                f"repair graph directory is unsafe or unavailable: {error}",
                video_id,
            ) from error
        finally:
            for fd in fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

    @staticmethod
    def _repair_orphan_state(
        g_fd: int, name: str, expected_content: bytes, expected_hash: str
    ) -> str:
        """Classify one G-level final as missing, exact orphan, or conflict.

        Inspection is descriptor-anchored, no-follow, and race-safe against
        FIFO/special final names: the type is checked with
        ``stat(..., follow_symlinks=False)`` before any read open, and the
        open itself uses ``O_NOFOLLOW | O_NONBLOCK`` plus an fstat
        regular-file confirmation, so no code path can block opening a FIFO
        even if the name is replaced between the stat and the open.
        """

        import stat as stat_module

        try:
            stats = os.stat(name, dir_fd=g_fd, follow_symlinks=False)
        except FileNotFoundError:
            return "missing"
        except OSError:
            return "conflict"
        if not stat_module.S_ISREG(stats.st_mode):
            return "conflict"
        try:
            fd = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=g_fd,
            )
        except FileNotFoundError:
            return "missing"
        except OSError:
            return "conflict"
        try:
            if not stat_module.S_ISREG(os.fstat(fd).st_mode):
                return "conflict"
            body = b""
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                body += chunk
                if len(body) > len(expected_content) + 1:
                    return "conflict"
            if (
                len(body) != len(expected_content)
                or hashlib.sha256(body).hexdigest() != expected_hash
            ):
                return "conflict"
            return "exact"
        except OSError:
            return "conflict"
        finally:
            os.close(fd)

    def _write_repair_final_in_directory(
        self,
        g_fd: int,
        *,
        name: str,
        content: bytes,
        expected_hash: str,
        video_id: str,
    ) -> None:
        """Write one G-level final through the Phase G durability ordering.

        Temporary exclusive create relative to the G descriptor, fsync,
        hash/length verify, atomic no-clobber link promotion, fsync(G),
        unlink temporary, fsync(G), reopen no-follow verify.  An existing
        final is never overwritten: only exact expected bytes are accepted.
        """

        tmp_name = name + ".tmp"
        try:
            fd = os.open(
                tmp_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=g_fd,
            )
        except FileExistsError:
            raise self._repair_persistence_error(
                f"stale temporary repair artifact at {name}", video_id
            ) from None
        except OSError as error:
            raise self._repair_persistence_error(
                f"failed to create temporary repair artifact {name}: {error}",
                video_id,
            ) from error
        try:
            os.write(fd, content)
            os.fsync(fd)
        except OSError as error:
            raise self._repair_persistence_error(
                f"failed to write temporary repair artifact {name}: {error}",
                video_id,
            ) from error
        finally:
            os.close(fd)

        verify_fd = os.open(tmp_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=g_fd)
        try:
            tmp_body = b""
            while True:
                chunk = os.read(verify_fd, 1 << 20)
                if not chunk:
                    break
                tmp_body += chunk
        finally:
            os.close(verify_fd)
        if (
            len(tmp_body) != len(content)
            or hashlib.sha256(tmp_body).hexdigest() != expected_hash
        ):
            raise self._repair_persistence_error(
                f"temporary repair artifact {name} failed verification",
                video_id,
            )

        try:
            os.link(tmp_name, name, src_dir_fd=g_fd, dst_dir_fd=g_fd)
        except FileExistsError:
            state = self._repair_orphan_state(g_fd, name, content, expected_hash)
            if state != "exact":
                raise self._repair_persistence_error(
                    f"repair artifact already exists at {name}", video_id
                ) from None
            os.unlink(tmp_name, dir_fd=g_fd)
            os.fsync(g_fd)
            return
        except OSError as error:
            raise self._repair_persistence_error(
                f"failed to promote repair artifact {name}: {error}", video_id
            ) from error

        try:
            os.unlink(tmp_name, dir_fd=g_fd)
        except OSError as error:
            raise self._repair_persistence_error(
                f"failed to unlink temporary repair artifact {name}: {error}",
                video_id,
            ) from error
        os.fsync(g_fd)

        final_fd = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=g_fd
        )
        try:
            import stat as stat_module

            if not stat_module.S_ISREG(os.fstat(final_fd).st_mode):
                raise self._repair_persistence_error(
                    f"promoted repair artifact {name} is not a regular file",
                    video_id,
                )
            final_body = b""
            while True:
                chunk = os.read(final_fd, 1 << 20)
                if not chunk:
                    break
                final_body += chunk
        except OSError as error:
            raise self._repair_persistence_error(
                f"failed to reopen repair artifact {name}: {error}", video_id
            ) from error
        finally:
            os.close(final_fd)
        if (
            len(final_body) != len(content)
            or hashlib.sha256(final_body).hexdigest() != expected_hash
        ):
            raise self._repair_persistence_error(
                f"promoted repair artifact {name} failed verification",
                video_id,
            )

    def _materialize_repair_files(self, plan: Any) -> None:
        """Adopt exact orphans or write the missing G-based finals."""

        g_fd = self._open_repair_graph_directory(
            p=plan.primary_request_hash,
            g=plan.graph_hash,
            video_id=plan.video_id,
        )
        try:
            raw_state = self._repair_orphan_state(
                g_fd, "raw.json", plan.envelope_bytes, plan.envelope_hash
            )
            structured_state = self._repair_orphan_state(
                g_fd,
                "structured.json",
                plan.structured_bytes,
                plan.structured_hash,
            )
            if raw_state == "conflict" or structured_state == "conflict":
                raise self._repair_persistence_error(
                    "existing repair graph material conflicts with the plan",
                    plan.video_id,
                )
            if raw_state == "missing":
                self._write_repair_final_in_directory(
                    g_fd,
                    name="raw.json",
                    content=plan.envelope_bytes,
                    expected_hash=plan.envelope_hash,
                    video_id=plan.video_id,
                )
            if structured_state == "missing":
                self._write_repair_final_in_directory(
                    g_fd,
                    name="structured.json",
                    content=plan.structured_bytes,
                    expected_hash=plan.structured_hash,
                    video_id=plan.video_id,
                )
        finally:
            os.close(g_fd)

    def _prewrite_validate_repair(
        self, success: PhaseHTrustedRepairSuccess
    ) -> _ValidatedRepairWritePlan:
        """Zero-write validation of an exact H2-C repair success -> plan.

        Replays the composite version/JCS/hash/length/admission bounds, the
        trusted result and sealed structured bytes, and every P/R/J/settings
        cross-binding entirely in memory.  No file, directory, Artifact,
        ProviderCall, stage, or response identity is created here.
        """

        from youtube_intel.h2_evidence import (
            REPAIR_RAW_PRODUCER_VERSION,
            REPAIR_STRUCTURED_PRODUCER_VERSION,
            RepairCompositeEnvelope,
            build_repair_request_hash,
            repair_normalized_input_hash,
            repair_persistence_graph_hash,
        )
        from youtube_intel.h2_jcs import jcs_loads_strict, jcs_serialize
        from youtube_intel.providers.ollama import parse_scoring_candidate
        from youtube_intel.quality import (
            TrustedScoreResult,
            build_judge_h1_h2,
            build_scoring_candidate_hash,
        )

        # 1. Runtime context binding: the carrier belongs to this entry.
        if success.job_id != self._context.job_id:
            msg = "repair success job_id mismatches the persistence context"
            raise ValueError(msg)
        if success.owner != self._context.owner:
            msg = "repair success owner mismatches the persistence context"
            raise ValueError(msg)
        if success.pipeline_version != self._context.pipeline_version:
            msg = "repair success pipeline version mismatches the context"
            raise ValueError(msg)

        trusted_result = success.trusted_result
        if type(trusted_result) is not TrustedScoreResult:
            msg = "trusted result must be an exact TrustedScoreResult"
            raise ValueError(msg)

        # 2. Composite envelope replay: strict parse, typed validation,
        #    canonical reserialize equality, hash/length, admission bounds.
        envelope_bytes = success.repair_composite_envelope_bytes
        try:
            decoded = jcs_loads_strict(envelope_bytes)
            envelope = RepairCompositeEnvelope.model_validate(decoded)
        except ValueError as error:
            raise ValueError(f"repair envelope is invalid: {error}") from error
        if jcs_serialize(envelope.model_dump(mode="json")) != envelope_bytes:
            msg = "repair envelope bytes are not canonical H2 JCS"
            raise ValueError(msg)
        envelope_hash = hashlib.sha256(envelope_bytes).hexdigest()
        if envelope_hash != success.repair_composite_envelope_sha256:
            msg = "repair envelope hash mismatches the sealed commitment"
            raise ValueError(msg)
        if len(envelope_bytes) != success.repair_composite_envelope_length:
            msg = "repair envelope length mismatches the sealed commitment"
            raise ValueError(msg)
        verify_repair_envelope_admission(envelope)

        pfe = envelope.primary_failure_evidence
        provider_evidence = envelope.repair_provider_evidence
        candidate_evidence = envelope.repair_candidate_evidence
        quality_evidence = envelope.repair_quality_evidence
        binding = envelope.finalizer_binding

        # 3. Sealed structured replay through the unchanged sealed serializer.
        structured_bytes = _sealed_trusted_score_result_serializer(trusted_result)
        if structured_bytes != success.structured_bytes:
            msg = "structured bytes do not match the sealed serializer output"
            raise ValueError(msg)
        structured_hash = hashlib.sha256(structured_bytes).hexdigest()
        if structured_hash != success.structured_sha256:
            msg = "structured hash mismatches the sealed commitment"
            raise ValueError(msg)
        if len(structured_bytes) != success.structured_length:
            msg = "structured length mismatches the sealed commitment"
            raise ValueError(msg)
        if binding.structured_result_sha256 != structured_hash:
            msg = "finalizer binding structured hash mismatches the seal"
            raise ValueError(msg)
        if binding.structured_result_length != len(structured_bytes):
            msg = "finalizer binding structured length mismatches the seal"
            raise ValueError(msg)

        # 4. P/R/J/settings-provenance cross-binding.
        p = success.primary_request_hash
        if p != trusted_result.result.request_hash:
            msg = "trusted result request_hash mismatches the PRIMARY identity"
            raise ValueError(msg)
        if p != binding.primary_request_hash:
            msg = "finalizer binding P commitment mismatches"
            raise ValueError(msg)
        if p != pfe.primary_request_hash or p != provider_evidence.normalized_input.primary_request_hash:
            msg = "PRIMARY request hash mismatches across the envelope"
            raise ValueError(msg)
        if success.primary_normalized_input_hash != pfe.primary_normalized_input_hash:
            msg = "PRIMARY normalized input hash mismatches the PFE"
            raise ValueError(msg)
        if success.scoring_input_sha256 != pfe.primary_scoring_input_sha256:
            msg = "scoring input hash mismatches the PFE"
            raise ValueError(msg)
        rni = provider_evidence.normalized_input
        if rni.scoring_input != pfe.primary_scoring_input:
            msg = "RNI scoring input mismatches the PFE scoring input"
            raise ValueError(msg)
        recomputed_rni_hash = repair_normalized_input_hash(rni)
        if recomputed_rni_hash != provider_evidence.normalized_input_hash:
            msg = "RNI canonical hash mismatches the provider evidence"
            raise ValueError(msg)
        recomputed_r = build_repair_request_hash(rni)
        if recomputed_r != provider_evidence.request_hash:
            msg = "REPAIR request hash mismatches the canonical RNI identity"
            raise ValueError(msg)
        if recomputed_r != binding.repair_request_hash:
            msg = "finalizer binding R commitment mismatches"
            raise ValueError(msg)
        if provider_evidence.provider != rni.repair_provider:
            msg = "repair provider mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.model != rni.repair_model:
            msg = "repair model mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.model_digest != rni.repair_model_digest:
            msg = "repair model digest mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.prompt_version != rni.repair_prompt_version:
            msg = "repair prompt version mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.operation_schema_version != rni.repair_schema_version:
            msg = "repair schema version mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.output_language != rni.output_language:
            msg = "repair output language mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.temperature != rni.temperature:
            msg = "repair temperature mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.max_output_tokens != rni.max_output_tokens:
            msg = "repair max_output_tokens mismatches the RNI"
            raise ValueError(msg)
        if provider_evidence.max_description_chars != rni.max_description_chars:
            msg = "repair max_description_chars mismatches the RNI"
            raise ValueError(msg)

        settings_bytes = jcs_serialize(
            provider_evidence.settings_provenance.model_dump(mode="json")
        )
        settings_hash = hashlib.sha256(settings_bytes).hexdigest()
        if settings_hash != provider_evidence.settings_provenance_sha256:
            msg = "settings provenance hash mismatches its canonical bytes"
            raise ValueError(msg)

        candidate = candidate_evidence.candidate
        reparsed = parse_scoring_candidate(candidate_evidence.repair_raw_utf8)
        if reparsed != candidate:
            msg = "repair candidate mismatches the canonical raw parse"
            raise ValueError(msg)
        candidate_hash = build_scoring_candidate_hash(candidate)
        if candidate_hash != candidate_evidence.candidate_sha256:
            msg = "repair candidate hash mismatches the evidence"
            raise ValueError(msg)
        repair_raw_bytes = candidate_evidence.repair_raw_utf8.encode("utf-8")
        if hashlib.sha256(repair_raw_bytes).hexdigest() != candidate_evidence.repair_raw_sha256:
            msg = "repair raw hash mismatches the evidence"
            raise ValueError(msg)
        if len(repair_raw_bytes) != candidate_evidence.repair_raw_length:
            msg = "repair raw length mismatches the evidence"
            raise ValueError(msg)
        if candidate_evidence.language_evidence.result != "VALID":
            msg = "repair language evidence must be VALID"
            raise ValueError(msg)
        if candidate_evidence.language_evidence.candidate_sha256 != candidate_hash:
            msg = "language evidence candidate hash mismatches"
            raise ValueError(msg)
        result = trusted_result.result
        if (
            result.score != candidate.score
            or result.reason != candidate.reason
            or result.topics != candidate.topics
            or result.should_summarize != candidate.should_summarize
            or result.dimensions != candidate.dimensions
        ):
            msg = "trusted result business fields mismatch the repair candidate"
            raise ValueError(msg)
        if binding.trusted_result != result:
            msg = "finalizer binding trusted result mismatches the seal"
            raise ValueError(msg)

        if quality_evidence.deterministic_gate_status != "PASS":
            msg = "repair deterministic gate status must be PASS"
            raise ValueError(msg)
        if quality_evidence.quality_result.status.value != "PASS":
            msg = "repair quality result must be PASS"
            raise ValueError(msg)
        if quality_evidence.quality_input.candidate_hash != candidate_hash:
            msg = "repair quality input candidate hash mismatches"
            raise ValueError(msg)
        from youtube_intel.quality import (
            build_content_quality_input_hash,
            build_content_quality_result_hash,
        )

        if build_content_quality_input_hash(
            quality_evidence.quality_input
        ) != quality_evidence.quality_input_hash:
            msg = "repair quality input hash mismatches"
            raise ValueError(msg)
        authority = self._quality_authority
        judge_h1, judge_h2 = build_judge_h1_h2(quality_evidence.judge_operation_input)
        if judge_h1 != quality_evidence.judge_h1 or judge_h2 != quality_evidence.judge_h2:
            msg = "repair Judge H1/H2 mismatch the canonical derivation"
            raise ValueError(msg)
        if quality_evidence.judge_evidence.role != "REPAIR":
            msg = "repair Judge evidence role must be REPAIR"
            raise ValueError(msg)
        if quality_evidence.judge_evidence.judge_h2 != judge_h2:
            msg = "repair Judge evidence H2 mismatches"
            raise ValueError(msg)
        if quality_evidence.judge_evidence.model != authority.judge_model:
            msg = "repair Judge model mismatches the runtime authority"
            raise ValueError(msg)
        if quality_evidence.judge_evidence.provider != authority.judge_provider:
            msg = "repair Judge provider mismatches the runtime authority"
            raise ValueError(msg)
        judge_raw_bytes = quality_evidence.judge_raw_utf8.encode("utf-8")
        if hashlib.sha256(judge_raw_bytes).hexdigest() != quality_evidence.judge_raw_sha256:
            msg = "repair Judge raw hash mismatches the evidence"
            raise ValueError(msg)
        if len(judge_raw_bytes) != quality_evidence.judge_raw_length:
            msg = "repair Judge raw length mismatches the evidence"
            raise ValueError(msg)
        attestation = quality_evidence.attestation
        if attestation.judge_request_hash != judge_h2:
            msg = "repair attestation Judge request hash mismatches"
            raise ValueError(msg)
        if attestation.scoring_request_hash != recomputed_r:
            msg = "repair attestation must bind the REPAIR request hash"
            raise ValueError(msg)
        if attestation.quality_result_hash != build_content_quality_result_hash(
            quality_evidence.quality_result
        ):
            msg = "repair attestation quality result hash mismatches"
            raise ValueError(msg)

        # 5. Complete graph identity v2 and the G-based persistence plan.
        graph_identity = build_repair_persistence_graph_identity(
            primary_request_hash=p,
            repair_request_hash=recomputed_r,
            repair_judge_request_hash=judge_h2,
            settings_provenance_sha256=settings_hash,
            repair_envelope_sha256=envelope_hash,
            structured_result_sha256=structured_hash,
        )
        graph_hash = repair_persistence_graph_hash(graph_identity)
        (
            raw_key,
            raw_relative_path,
            structured_key,
            structured_relative_path,
        ) = build_repair_artifact_keys(primary_request_hash=p, graph_hash=graph_hash)

        video_id = rni.video_id
        now = self._clock()
        raw_artifact = ArtifactWrite(
            artifact_id=f"scoring-raw-{_sha256_text(raw_key + envelope_hash)}",
            artifact_key=raw_key,
            video_id=video_id,
            job_id=self._context.job_id,
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=raw_relative_path,
            content_hash=envelope_hash,
            provider=provider_evidence.provider,
            model=provider_evidence.model,
            producer_version=REPAIR_RAW_PRODUCER_VERSION,
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=now + _G_ARTIFACT_RETENTION,
        )
        structured_artifact = ArtifactWrite(
            artifact_id=(
                "scoring-structured-" + _sha256_text(structured_key + structured_hash)
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
            producer_version=REPAIR_STRUCTURED_PRODUCER_VERSION,
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        )

        repair_call_request = ProviderCallRequest(
            operation=rni.operation,
            normalized_input_hash=recomputed_rni_hash,
            provider=rni.repair_provider,
            model=rni.repair_model,
            prompt_version=rni.repair_prompt_version,
            schema_version=rni.repair_schema_version,
            deterministic_artifact_key=raw_key,
        )
        if repair_call_request.request_hash != recomputed_r:
            msg = "repair ProviderCall request_hash mismatches R"
            raise ValueError(msg)
        judge_call_request = ProviderCallRequest(
            operation=authority.judge_operation,
            normalized_input_hash=judge_h1,
            provider=authority.judge_provider,
            model=authority.judge_model,
            prompt_version=authority.quality_prompt_version,
            schema_version=authority.quality_schema_version,
            deterministic_artifact_key=raw_key,
        )
        if judge_call_request.request_hash != judge_h2:
            msg = "judge ProviderCall request_hash mismatches J"
            raise ValueError(msg)

        return _ValidatedRepairWritePlan(
            success=success,
            envelope=envelope,
            envelope_bytes=envelope_bytes,
            envelope_hash=envelope_hash,
            envelope_length=len(envelope_bytes),
            structured_bytes=structured_bytes,
            structured_hash=structured_hash,
            structured_length=len(structured_bytes),
            primary_request_hash=p,
            repair_request_hash=recomputed_r,
            judge_request_hash=judge_h2,
            settings_provenance_sha256=settings_hash,
            graph_identity=graph_identity,
            graph_hash=graph_hash,
            raw_artifact=raw_artifact,
            structured_artifact=structured_artifact,
            repair_call_request=repair_call_request,
            judge_call_request=judge_call_request,
            repair_call_completion=ProviderCallCompletion(
                request_hash=recomputed_r,
                response_artifact_id=raw_artifact.artifact_id,
                input_tokens=None,
                output_tokens=None,
                cost_microusd=None,
            ),
            judge_call_completion=ProviderCallCompletion(
                request_hash=judge_h2,
                response_artifact_id=raw_artifact.artifact_id,
                input_tokens=None,
                output_tokens=None,
                cost_microusd=None,
            ),
            scoring_summary=ScoringSummaryWrite(
                score=result.score,
                should_summarize=result.score >= self._summary_threshold,
            ),
            video_id=video_id,
        )

    def _repair_owned_job_precheck(self, ctx: _H2CLineageCasContext) -> None:
        """PREWRITE repository-owned current job/lease/identity check.

        The active-lease proof applies to fresh registration (a RUNNING job).
        An already-SUCCEEDED committed job proceeds to the pointer precheck,
        which classifies same-graph idempotency and committed conflicts.  A
        stale runtime raises ``H2CStaleScoringLease``, performs no
        ``fail_job``, makes zero filesystem changes, records no error code or
        detail, and leaves retry/status unchanged.
        """

        from youtube_intel.pipeline import PipelineInterrupted

        repository = cast(Any, self._repository)
        job = repository.get_job(ctx.job_id)
        if job is None:
            raise PipelineInterrupted("repair persistence job row is missing")
        if job.status is JobStatus.RUNNING:
            now = self._clock()
            if not self._owned_active_now(job, ctx.owner, now):
                raise H2CStaleScoringLease(
                    "repair persistence lost the active scoring lease"
                )
            if (
                job.job_type is not JobType.VIDEO_STAGE
                or job.target_stage is not ProcessingStage.SCORING
                or job.video_id != ctx.video_id
                or job.pipeline_version != ctx.pipeline_version
                or job.scoring_lineage_version != SCORING_LINEAGE_VERSION_V1
            ):
                self._terminalize_lineage_integrity(
                    ctx, detail="H2C_JOB_LINEAGE_CAS_UNEXPECTED"
                )

    def _persist_repair_success(
        self, success: PhaseHTrustedRepairSuccess
    ) -> StageCompletionResult:
        """Execute the trusted REPAIR filesystem + SQLite registration."""

        plan = self._prewrite_validate_repair(success)
        ctx = _H2CLineageCasContext(
            job_id=self._context.job_id,
            owner=self._context.owner,
            video_id=plan.video_id,
            pipeline_version=self._context.pipeline_version,
            raw_key=plan.raw_artifact.artifact_key,
            structured_key=plan.structured_artifact.artifact_key,
            provenance="REPAIR_H2C",
        )
        self._repair_owned_job_precheck(ctx)
        existing_lineage = self._lineage_pointer_precheck(
            ctx=ctx,
            raw_artifact=plan.raw_artifact,
            structured_artifact=plan.structured_artifact,
            raw_envelope_hash=plan.envelope_hash,
            raw_envelope_length=plan.envelope_length,
            structured_hash=plan.structured_hash,
            structured_length=plan.structured_length,
            scoring_call_request=plan.repair_call_request,
            judge_call_request=plan.judge_call_request,
            scoring_call_completion=plan.repair_call_completion,
            judge_call_completion=plan.judge_call_completion,
            scoring_summary=plan.scoring_summary,
            raw_final=self._data_root / plan.raw_artifact.relative_path,
            structured_final=self._data_root / plan.structured_artifact.relative_path,
        )
        if existing_lineage is not None:
            return existing_lineage

        self._materialize_repair_files(plan)

        try:
            now = self._clock()
            now_text = format_utc_datetime(now)
            lease_until = now + timedelta(minutes=5)
            repository = cast(Any, self._repository)
            connection = repository._connect()
            try:
                try:
                    with _immediate_transaction(connection):
                        job_row = repository._owned_running_job(
                            connection,
                            job_id=self._context.job_id,
                            owner=self._context.owner,
                            now=now_text,
                        )
                        if (
                            job_row["video_id"] != plan.video_id
                            or job_row["pipeline_version"]
                            != self._context.pipeline_version
                        ):
                            raise ConcurrencyConflict(
                                "job scope does not match repair registration"
                            )
                        if job_row["target_stage"] != ProcessingStage.SCORING.value:
                            raise ConcurrencyConflict(
                                "repair job target stage is not SCORING"
                            )
                        raw_record = repository._upsert_artifact_in_transaction(
                            connection, plan.raw_artifact, now=now_text
                        )
                        structured_record = repository._upsert_artifact_in_transaction(
                            connection, plan.structured_artifact, now=now_text
                        )
                        repair_record = repository._reserve_provider_call_in_transaction(
                            connection,
                            plan.repair_call_request,
                            owner=self._context.owner,
                            lease_until=lease_until,
                            available_at=now,
                            now=now,
                        )
                        judge_record = repository._reserve_provider_call_in_transaction(
                            connection,
                            plan.judge_call_request,
                            owner=self._context.owner,
                            lease_until=lease_until,
                            available_at=now,
                            now=now,
                        )
                        if repair_record.status is ProviderCallStatus.PENDING:
                            repair_record = repository._complete_provider_call_in_transaction(
                                connection,
                                plan.repair_call_completion,
                                owner=self._context.owner,
                                now=now_text,
                            )
                        if judge_record.status is ProviderCallStatus.PENDING:
                            judge_record = repository._complete_provider_call_in_transaction(
                                connection,
                                plan.judge_call_completion,
                                owner=self._context.owner,
                                now=now_text,
                            )
                        self._apply_lineage_cas_in_transaction(
                            connection,
                            repository,
                            ctx=ctx,
                            job_row=job_row,
                            now_text=now_text,
                        )
                        changed = connection.execute(
                            "UPDATE videos SET pipeline_status = :target_status, "
                            "score = :score, should_summarize = :should_summarize, "
                            "updated_at = :now, completed_at = NULL "
                            "WHERE video_id = :video_id "
                            "AND pipeline_status = :expected_status "
                            "AND pipeline_version = :pipeline_version",
                            {
                                "target_status": PipelineStatus.SCORED.value,
                                "score": plan.scoring_summary.score,
                                "should_summarize": int(
                                    plan.scoring_summary.should_summarize
                                ),
                                "now": now_text,
                                "video_id": plan.video_id,
                                "expected_status": PipelineStatus.TRANSCRIPT_READY.value,
                                "pipeline_version": self._context.pipeline_version,
                            },
                        ).rowcount
                        if changed != 1:
                            raise ConcurrencyConflict(
                                "pipeline changed before repair registration"
                            )
                        job = repository._finish_job_success_in_transaction(
                            connection,
                            job_id=self._context.job_id,
                            owner=self._context.owner,
                            now=now_text,
                        )
                        video_row = connection.execute(
                            "SELECT * FROM videos WHERE video_id = :video_id",
                            {"video_id": plan.video_id},
                        ).fetchone()
                        if video_row is None:
                            raise StateStoreError("completed video could not be read")
                        return StageCompletionResult(
                            job=job,
                            video=repository._video_from_row(video_row),
                            artifacts=(raw_record, structured_record),
                            provider_call=repair_record,
                        )
                except sqlite3.IntegrityError as error:
                    raise IntegrityConflict(
                        "atomic repair registration violates repository integrity"
                    ) from error
                except _H2CLineageCasZeroRow as zero:
                    return self._dispatch_lineage_cas_finding(
                        zero,
                        ctx=ctx,
                        raw_artifact=plan.raw_artifact,
                        structured_artifact=plan.structured_artifact,
                        raw_envelope_hash=plan.envelope_hash,
                        raw_envelope_length=plan.envelope_length,
                        structured_hash=plan.structured_hash,
                        structured_length=plan.structured_length,
                        scoring_call_request=plan.repair_call_request,
                        judge_call_request=plan.judge_call_request,
                        scoring_call_completion=plan.repair_call_completion,
                        judge_call_completion=plan.judge_call_completion,
                        scoring_summary=plan.scoring_summary,
                        raw_final=self._data_root / plan.raw_artifact.relative_path,
                        structured_final=(
                            self._data_root / plan.structured_artifact.relative_path
                        ),
                    )
            finally:
                connection.close()
        except ScoringPersistenceError:
            raise
        except (
            H2CStaleScoringLease,
            H2CAuthoritativeGraphConflict,
            _H2CLineageTerminalHandled,
        ):
            raise
        except Exception as error:
            from youtube_intel.pipeline import PipelineInterrupted

            if isinstance(error, PipelineInterrupted):
                raise
            msg = f"atomic repair registration failed: {error}"
            raise ScoringPersistenceError(
                AppError(
                    code=ErrorCode.LOCAL_RESOURCE,
                    message=msg,
                    retryable=False,
                    video_id=plan.video_id,
                    stage=ProcessingStage.SCORING,
                )
            ) from error


# ---------------------------------------------------------------------------
# TASK-016C Phase H2-C: trusted repair persistence data layer
# ---------------------------------------------------------------------------
#
# The H2-C persistence boundary is the runtime-internal continuation of one
# actual SCORING execution frame.  Nothing below accepts caller-provided
# trust, Judge context, repair graph identity, provider evidence, artifact
# paths, success provenance, or authoritative pointers: every value is
# derived inside the trusted runtime replay or re-verified here.


class H2CStaleScoringLease(Exception):
    """The runtime is no longer the active owner of the current SCORING job.

    Raised only by the H2-C lease/ownership proofs (PREWRITE repository-owned
    check, lineage CAS diagnosis, generation-decision authority).  It carries
    no capability and is never used for evidence/replay mismatches or any
    existing ``ScoringDispatchDenied`` source.  The stale runtime performs no
    ``fail_job`` and no mutation.
    """


class H2CAuthoritativeGraphConflict(IntegrityConflict):
    """A committed authoritative graph differs from the planned complete graph.

    Fail-closed: no second graph registration, pointer update, state
    transition, or file overwrite.  The stable diagnostic code is carried for
    the trusted persistence boundary mapping.
    """

    stable_code = "H2C_AUTHORITATIVE_GRAPH_CONFLICT"

    def __init__(self, message: str = "authoritative graph conflict") -> None:
        super().__init__(message)


class _H2CLineageTerminalHandled(Exception):
    """Internal: one owner-authoritative integrity fail_job already committed.

    Raised by the trusted persistence boundary after a rollback + lease
    re-proof + exactly one ``fail_job`` whose FAILED_FINAL read-back was
    confirmed.  The runtime maps it to ``StageDisposition.TERMINAL``; it never
    escapes to generic failure handling.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class _H2CEnvelopeOversize(ValueError):
    """A repair envelope component exceeded its bounded admission ceiling."""


class _H2CLineageCasFinding(str, Enum):
    """Closed classification outcomes for a zero-row lineage CAS."""

    IDEMPOTENT = "IDEMPOTENT"
    COMMITTED_CONFLICT = "COMMITTED_CONFLICT"
    STALE_LEASE = "STALE_LEASE"
    MISSING_JOB = "MISSING_JOB"
    MISSING_VIDEO = "MISSING_VIDEO"
    TERMINAL_JOB_UNEXPECTED = "TERMINAL_JOB_UNEXPECTED"
    TERMINAL_GRAPH_CONFLICT = "TERMINAL_GRAPH_CONFLICT"
    TERMINAL_VIDEO_UNEXPECTED = "TERMINAL_VIDEO_UNEXPECTED"
    TERMINAL_VIDEO_CONFLICT = "TERMINAL_VIDEO_CONFLICT"
    INTERRUPTED = "INTERRUPTED"


#: The exact frozen terminal detail for each active-owned integrity finding.
_H2C_LINEAGE_TERMINAL_DETAILS: Final[dict[_H2CLineageCasFinding, str]] = {
    _H2CLineageCasFinding.TERMINAL_JOB_UNEXPECTED: (
        "H2C_JOB_LINEAGE_CAS_UNEXPECTED"
    ),
    _H2CLineageCasFinding.TERMINAL_GRAPH_CONFLICT: (
        "H2C_AUTHORITATIVE_GRAPH_CONFLICT"
    ),
    _H2CLineageCasFinding.TERMINAL_VIDEO_UNEXPECTED: (
        "H2C_VIDEO_LINEAGE_CAS_UNEXPECTED"
    ),
    _H2CLineageCasFinding.TERMINAL_VIDEO_CONFLICT: (
        "H2C_VIDEO_LINEAGE_CAS_CONFLICT"
    ),
}


class _H2CLineageCasZeroRow(Exception):
    """Carrier: a lineage CAS matched zero rows; the finding is classified."""

    def __init__(
        self,
        finding: _H2CLineageCasFinding,
        *,
        is_video_cas: bool,
    ) -> None:
        super().__init__(finding.value)
        self.finding = finding
        self.is_video_cas = is_video_cas


@dataclass(frozen=True, slots=True)
class _H2CLineageCasContext:
    """Identity/provenance inputs of one lineage pointer CAS."""

    job_id: str
    owner: str
    video_id: str
    pipeline_version: str
    raw_key: str
    structured_key: str
    provenance: str


@dataclass(frozen=True, slots=True)
class _ValidatedRepairWritePlan:
    """Zero-write REPAIR PREWRITE output freezing every persistence input.

    Internal to ``TrustedPersistenceEntry._persist_repair_success``: it fixes
    the envelope/structured bytes, E/S/G commitments, G-based artifact
    identity, the two truthful ProviderCall identities, and the summary.  It
    is not a DTO, cache identity, authority, or persistence record.
    """

    success: Any
    envelope: Any
    envelope_bytes: bytes
    envelope_hash: str
    envelope_length: int
    structured_bytes: bytes
    structured_hash: str
    structured_length: int
    primary_request_hash: str
    repair_request_hash: str
    judge_request_hash: str
    settings_provenance_sha256: str
    graph_identity: Any
    graph_hash: str
    raw_artifact: ArtifactWrite
    structured_artifact: ArtifactWrite
    repair_call_request: ProviderCallRequest
    judge_call_request: ProviderCallRequest
    repair_call_completion: ProviderCallCompletion
    judge_call_completion: ProviderCallCompletion
    scoring_summary: ScoringSummaryWrite
    video_id: str


#: Closed H2-C trust-integrity diagnostics.  Every detail is exactly one
#: ``H2C_REPLAY_INVALID:<REASON>`` literal from the approved closed set; no
#: arbitrary formatted reasons are permitted.
H2C_REPLAY_INVALID_PREFIX: Final = "H2C_REPLAY_INVALID:"
H2C_REPLAY_INVALID_REASONS: Final[frozenset[str]] = frozenset(
    {
        "PRIMARY_EVIDENCE_MISMATCH",
        "PFE_INVALID",
        "FAILURE_CLASS_INELIGIBLE",
        "RNI_MISMATCH",
        "REPAIR_REQUEST_MISMATCH",
        "REPAIR_PAYLOAD_MISMATCH",
        "REPAIR_RAW_INVALID",
        "CANDIDATE_MISMATCH",
        "LANGUAGE_INVALID",
        "DETERMINISTIC_GATE_INVALID",
        "JUDGE_EVIDENCE_INVALID",
        "ATTESTATION_INVALID",
        "FINALIZER_INVALID",
        "TRUSTED_RESULT_MISMATCH",
        "STRUCTURED_RESULT_MISMATCH",
        "SETTINGS_MISMATCH",
        "PROVENANCE_MISMATCH",
        "ENVELOPE_OVERSIZE",
        "SETTINGS_BOUND_EXCEEDED",
        "SCORING_LINEAGE_VERSION_INVALID",
    }
)


def h2c_replay_invalid_detail(reason: str) -> str:
    """Return the exact qualified diagnostic for one closed reason literal."""

    if reason not in H2C_REPLAY_INVALID_REASONS:
        msg = f"H2C diagnostic reason is not in the closed set: {reason!r}"
        raise ValueError(msg)
    return H2C_REPLAY_INVALID_PREFIX + reason


_H2C_SHA256_HEX_LENGTH: Final = 64


def _validate_lower_hex(value: str, *, field_name: str) -> None:
    if (
        len(value) != _H2C_SHA256_HEX_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        msg = f"{field_name} must be a lowercase 64-character SHA-256 value"
        raise ValueError(msg)


def build_repair_persistence_graph_identity(
    *,
    primary_request_hash: str,
    repair_request_hash: str,
    repair_judge_request_hash: str,
    settings_provenance_sha256: str,
    repair_envelope_sha256: str,
    structured_result_sha256: str,
) -> Any:
    """Construct the exact v2 complete-graph identity from verified commitments.

    The frozen producer/schema/policy literals are filled internally; no caller
    supplies a producer, schema, or policy variant.  The result is the sole
    input to ``G = SHA256(H2-JCS(identity))``.
    """

    from youtube_intel.h2_evidence import (
        REPAIR_COMPOSITE_ENVELOPE_SCHEMA,
        REPAIR_PERSISTENCE_GRAPH_SCHEMA_V2,
        REPAIR_PROVIDER_EVIDENCE_SCHEMA_V2,
        REPAIR_RAW_PRODUCER_VERSION,
        REPAIR_STRUCTURED_PRODUCER_VERSION,
        RepairPersistenceGraphIdentityV2,
    )
    from youtube_intel.providers.ollama import (
        _QUALITY_POLICY_VERSION,
        _QUALITY_PROMPT_VERSION,
        _QUALITY_SCHEMA_VERSION,
    )

    return RepairPersistenceGraphIdentityV2.model_validate(
        {
            "schema_version": REPAIR_PERSISTENCE_GRAPH_SCHEMA_V2,
            "primary_request_hash": primary_request_hash,
            "repair_request_hash": repair_request_hash,
            "repair_judge_request_hash": repair_judge_request_hash,
            "settings_provenance_sha256": settings_provenance_sha256,
            "repair_envelope_sha256": repair_envelope_sha256,
            "structured_result_sha256": structured_result_sha256,
            "raw_producer_version": REPAIR_RAW_PRODUCER_VERSION,
            "structured_producer_version": REPAIR_STRUCTURED_PRODUCER_VERSION,
            "envelope_schema": REPAIR_COMPOSITE_ENVELOPE_SCHEMA,
            "repair_provider_evidence_schema": REPAIR_PROVIDER_EVIDENCE_SCHEMA_V2,
            "quality_policy_version": _QUALITY_POLICY_VERSION,
            "quality_prompt_version": _QUALITY_PROMPT_VERSION,
            "quality_schema_version": _QUALITY_SCHEMA_VERSION,
        }
    )


def build_repair_artifact_keys(
    *,
    primary_request_hash: str,
    graph_hash: str,
) -> tuple[str, str, str, str]:
    """Derive the exact G-based repair keys and relative paths.

    Returns ``(raw_key, raw_relative_path, structured_key,
    structured_relative_path)``.  P and G are fixed lower-hex SHA-256
    components only; nothing else can influence a path.
    """

    _validate_lower_hex(primary_request_hash, field_name="primary_request_hash")
    _validate_lower_hex(graph_hash, field_name="graph_hash")
    raw_key = f"scoring/{primary_request_hash}/repair/{graph_hash}/raw"
    structured_key = f"scoring/{primary_request_hash}/repair/{graph_hash}/structured"
    return (
        raw_key,
        raw_key + ".json",
        structured_key,
        structured_key + ".json",
    )


def _parse_repair_key_components(key: str, *, suffix: str) -> tuple[str, str]:
    parts = key.split("/")
    if (
        len(parts) != 5
        or parts[0] != "scoring"
        or parts[2] != "repair"
        or parts[4] != suffix
    ):
        msg = f"repair artifact key grammar is invalid: {key!r}"
        raise ValueError(msg)
    primary_request_hash = parts[1]
    graph_hash = parts[3]
    _validate_lower_hex(primary_request_hash, field_name="primary_request_hash")
    _validate_lower_hex(graph_hash, field_name="graph_hash")
    return primary_request_hash, graph_hash


def parse_repair_raw_key(key: str) -> tuple[str, str]:
    """Parse ``scoring/<P>/repair/<G>/raw`` into ``(P, G)`` fail-closed."""

    return _parse_repair_key_components(key, suffix="raw")


def parse_repair_structured_key(key: str) -> tuple[str, str]:
    """Parse ``scoring/<P>/repair/<G>/structured`` into ``(P, G)`` fail-closed."""

    return _parse_repair_key_components(key, suffix="structured")


def parse_repair_raw_relative_path(path: str) -> tuple[str, str]:
    """Parse ``scoring/<P>/repair/<G>/raw.json`` into ``(P, G)`` fail-closed."""

    return _parse_repair_key_components(path, suffix="raw.json")


def parse_repair_structured_relative_path(path: str) -> tuple[str, str]:
    """Parse ``scoring/<P>/repair/<G>/structured.json`` into ``(P, G)``."""

    return _parse_repair_key_components(path, suffix="structured.json")


# Bounded repair-envelope admission ceilings (§6).  Every variable-size value
# is bounded by its containing canonical subtree; the narrower explicit row
# wins.  Nothing is truncated or abbreviated to fit.
_H2C_PRIMARY_FAILURE_SUBTREE_MAX: Final = 8_388_608
_H2C_REPAIR_PROVIDER_SUBTREE_MAX: Final = 8_388_608
_H2C_REPAIR_CANDIDATE_SUBTREE_MAX: Final = 7_340_032
_H2C_REPAIR_QUALITY_SUBTREE_MAX: Final = 8_388_608
_H2C_FINALIZER_BINDING_SUBTREE_MAX: Final = 1_044_480
_H2C_ENVELOPE_ROOT_MAX: Final = 33_554_432
_H2C_RNI_BYTES_MAX: Final = 393_216
_H2C_SETTINGS_PROVENANCE_BYTES_MAX: Final = 8_192
_H2C_REPAIR_PRIMARY_RAW_MAX: Final = 1_000_000
_H2C_REPAIR_JUDGE_RAW_MAX: Final = 20_000
_H2C_REPAIR_OUTER_RAW_MAX: Final = 1_000_000
_H2C_CANDIDATE_CONTENT_COLLECTIVE_MAX: Final = 1_340_032


def verify_repair_envelope_admission(envelope: Any) -> None:
    """Enforce the closed repair-only serialized-component limits.

    Serialize each typed subtree with H2 JCS and enforce its cap, then
    root-serialize and enforce the exact 33,554,432-byte total.  Oversize is
    not truncation or retry; it maps to ``H2C_REPLAY_INVALID:ENVELOPE_OVERSIZE``
    with zero network, filesystem, or persistence.
    """

    from youtube_intel.h2_jcs import jcs_serialize

    def _subtree_bytes(value: object) -> bytes:
        return jcs_serialize(value)

    primary_bytes = _subtree_bytes(
        envelope.primary_failure_evidence.model_dump(mode="json")
    )
    if len(primary_bytes) > _H2C_PRIMARY_FAILURE_SUBTREE_MAX:
        raise _H2CEnvelopeOversize("primary_failure_evidence subtree exceeds its cap")
    primary_raw_length = len(
        envelope.primary_failure_evidence.primary_raw_utf8.encode("utf-8")
    )
    if primary_raw_length > _H2C_REPAIR_PRIMARY_RAW_MAX:
        raise _H2CEnvelopeOversize("PRIMARY outer raw exceeds its cap")

    provider_bytes = _subtree_bytes(
        envelope.repair_provider_evidence.model_dump(mode="json")
    )
    if len(provider_bytes) > _H2C_REPAIR_PROVIDER_SUBTREE_MAX:
        raise _H2CEnvelopeOversize("repair_provider_evidence subtree exceeds its cap")
    rni_bytes = jcs_serialize(
        envelope.repair_provider_evidence.normalized_input.model_dump(mode="json")
    )
    if len(rni_bytes) > _H2C_RNI_BYTES_MAX:
        raise _H2CEnvelopeOversize("RNI canonical bytes exceed their cap")
    settings_bytes = jcs_serialize(
        envelope.repair_provider_evidence.settings_provenance.model_dump(mode="json")
    )
    if len(settings_bytes) > _H2C_SETTINGS_PROVENANCE_BYTES_MAX:
        raise _H2CEnvelopeOversize("settings provenance bytes exceed their cap")

    candidate_bytes = _subtree_bytes(
        envelope.repair_candidate_evidence.model_dump(mode="json")
    )
    if len(candidate_bytes) > _H2C_REPAIR_CANDIDATE_SUBTREE_MAX:
        raise _H2CEnvelopeOversize("repair_candidate_evidence subtree exceeds its cap")
    repair_raw_length = len(
        envelope.repair_candidate_evidence.repair_raw_utf8.encode("utf-8")
    )
    if repair_raw_length > _H2C_REPAIR_OUTER_RAW_MAX:
        raise _H2CEnvelopeOversize("REPAIR outer raw exceeds its cap")
    content_collective = _subtree_bytes(
        [
            envelope.repair_candidate_evidence.repair_model_content,
            envelope.repair_candidate_evidence.candidate.model_dump(mode="json"),
            envelope.repair_candidate_evidence.language_evidence.model_dump(
                mode="json"
            ),
        ]
    )
    if len(content_collective) > _H2C_CANDIDATE_CONTENT_COLLECTIVE_MAX:
        raise _H2CEnvelopeOversize("extracted candidate content exceeds its cap")

    quality_bytes = _subtree_bytes(
        envelope.repair_quality_evidence.model_dump(mode="json")
    )
    if len(quality_bytes) > _H2C_REPAIR_QUALITY_SUBTREE_MAX:
        raise _H2CEnvelopeOversize("repair_quality_evidence subtree exceeds its cap")
    judge_raw_length = len(
        envelope.repair_quality_evidence.judge_raw_utf8.encode("utf-8")
    )
    if judge_raw_length > _H2C_REPAIR_JUDGE_RAW_MAX:
        raise _H2CEnvelopeOversize("REPAIR Judge raw exceeds its cap")

    binding_bytes = _subtree_bytes(envelope.finalizer_binding.model_dump(mode="json"))
    if len(binding_bytes) > _H2C_FINALIZER_BINDING_SUBTREE_MAX:
        raise _H2CEnvelopeOversize("finalizer_binding subtree exceeds its cap")

    root_bytes = jcs_serialize(envelope.model_dump(mode="json"))
    if len(root_bytes) > _H2C_ENVELOPE_ROOT_MAX:
        raise _H2CEnvelopeOversize("repair envelope root exceeds the total cap")


def build_repair_composite_envelope(
    *,
    primary_failure_evidence: Any,
    repair_provider_evidence: Any,
    repair_candidate_evidence: Any,
    repair_quality_evidence: Any,
    finalizer_binding: Any,
) -> tuple[Any, bytes, str, int]:
    """Assemble the six-field root envelope and its canonical E commitment.

    Returns ``(envelope, envelope_bytes, envelope_sha256, envelope_length)``.
    The envelope contains neither G nor an artifact key/path nor identity
    bytes/digest, so neither E nor S requires G and the construction has no
    circular dependency.
    """

    from youtube_intel.h2_evidence import RepairCompositeEnvelope
    from youtube_intel.h2_jcs import jcs_loads_strict, jcs_serialize

    envelope = RepairCompositeEnvelope.model_validate(
        {
            "envelope_schema": "trusted-scoring-repair-envelope-v1",
            "primary_failure_evidence": primary_failure_evidence.model_dump(
                mode="json"
            ),
            "repair_provider_evidence": repair_provider_evidence.model_dump(
                mode="json"
            ),
            "repair_candidate_evidence": repair_candidate_evidence.model_dump(
                mode="json"
            ),
            "repair_quality_evidence": repair_quality_evidence.model_dump(
                mode="json"
            ),
            "finalizer_binding": finalizer_binding.model_dump(mode="json"),
        }
    )
    verify_repair_envelope_admission(envelope)
    envelope_bytes = jcs_serialize(envelope.model_dump(mode="json"))
    # Canonical reserialize equality through the strict decoder proves the
    # bytes are the exact H2 JCS representation of the typed envelope.
    if jcs_serialize(jcs_loads_strict(envelope_bytes)) != envelope_bytes:
        msg = "repair envelope bytes are not canonical H2 JCS"
        raise ValueError(msg)
    return (
        envelope,
        envelope_bytes,
        hashlib.sha256(envelope_bytes).hexdigest(),
        len(envelope_bytes),
    )


class _PhaseHTrustedRepairSuccessSentinel:
    """Private sentinel; only the H2-C seam can mint the repair aggregate."""

    __slots__ = ()


_PHASE_H_TRUSTED_REPAIR_SUCCESS_SENTINEL = _PhaseHTrustedRepairSuccessSentinel()


class PhaseHTrustedRepairSuccess:
    """Opaque memory-only H2-C trusted repair success carrier.

    The carrier is a narrow immutable data carrier with no persistence
    behavior and no public mint/factory.  It is not a capability.  It seals
    the exact approved persistence inputs: runtime job/owner/pipeline
    identity, the PRIMARY semantic hash, the sealed envelope bytes with E,
    the exact finalizer ``TrustedScoreResult`` and sealed structured bytes
    with S, and the prompt/schema version literals.  The parsed envelope is
    retained only as a redundant in-memory verifier input; the sealed bytes
    are authoritative.
    """

    __slots__ = (
        "_job_id",
        "_owner",
        "_pipeline_version",
        "_primary_request_hash",
        "_primary_normalized_input_hash",
        "_scoring_input_sha256",
        "_repair_composite_envelope_bytes",
        "_repair_composite_envelope_sha256",
        "_repair_composite_envelope_length",
        "_trusted_result",
        "_structured_bytes",
        "_structured_sha256",
        "_structured_length",
        "_prompt_version",
        "_schema_version",
        "_envelope",
        "_sealed",
    )

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("PhaseHTrustedRepairSuccess cannot be subclassed")

    def __init__(
        self,
        *,
        sentinel: object,
        job_id: str,
        owner: str,
        pipeline_version: str,
        primary_request_hash: str,
        primary_normalized_input_hash: str,
        scoring_input_sha256: str,
        repair_composite_envelope_bytes: bytes,
        repair_composite_envelope_sha256: str,
        repair_composite_envelope_length: int,
        trusted_result: Any,
        structured_bytes: bytes,
        structured_sha256: str,
        structured_length: int,
        prompt_version: str,
        schema_version: str,
        envelope: Any,
    ) -> None:
        if sentinel is not _PHASE_H_TRUSTED_REPAIR_SUCCESS_SENTINEL:
            msg = (
                "PhaseHTrustedRepairSuccess can only be minted by the trusted "
                "H2-C seam"
            )
            raise ValueError(msg)
        self._job_id = job_id
        self._owner = owner
        self._pipeline_version = pipeline_version
        self._primary_request_hash = primary_request_hash
        self._primary_normalized_input_hash = primary_normalized_input_hash
        self._scoring_input_sha256 = scoring_input_sha256
        self._repair_composite_envelope_bytes = repair_composite_envelope_bytes
        self._repair_composite_envelope_sha256 = repair_composite_envelope_sha256
        self._repair_composite_envelope_length = repair_composite_envelope_length
        self._trusted_result = trusted_result
        self._structured_bytes = structured_bytes
        self._structured_sha256 = structured_sha256
        self._structured_length = structured_length
        self._prompt_version = prompt_version
        self._schema_version = schema_version
        self._envelope = envelope
        self._sealed = True

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("PhaseHTrustedRepairSuccess is immutable")
        object.__setattr__(self, name, value)

    @property
    def job_id(self) -> str:
        return self._job_id

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def pipeline_version(self) -> str:
        return self._pipeline_version

    @property
    def primary_request_hash(self) -> str:
        return self._primary_request_hash

    @property
    def primary_normalized_input_hash(self) -> str:
        return self._primary_normalized_input_hash

    @property
    def scoring_input_sha256(self) -> str:
        return self._scoring_input_sha256

    @property
    def repair_composite_envelope_bytes(self) -> bytes:
        return self._repair_composite_envelope_bytes

    @property
    def repair_composite_envelope_sha256(self) -> str:
        return self._repair_composite_envelope_sha256

    @property
    def repair_composite_envelope_length(self) -> int:
        return self._repair_composite_envelope_length

    @property
    def trusted_result(self) -> Any:
        return self._trusted_result

    @property
    def structured_bytes(self) -> bytes:
        return self._structured_bytes

    @property
    def structured_sha256(self) -> str:
        return self._structured_sha256

    @property
    def structured_length(self) -> int:
        return self._structured_length

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    @property
    def schema_version(self) -> str:
        return self._schema_version

    def __copy__(self) -> NoReturn:
        raise TypeError("PhaseHTrustedRepairSuccess cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("PhaseHTrustedRepairSuccess cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("PhaseHTrustedRepairSuccess cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("PhaseHTrustedRepairSuccess cannot be serialized")


def _mint_phase_h_trusted_repair_success(
    *,
    job_id: str,
    owner: str,
    pipeline_version: str,
    primary_request_hash: str,
    primary_normalized_input_hash: str,
    scoring_input_sha256: str,
    envelope: Any,
    envelope_bytes: bytes,
    trusted_result: Any,
    structured_bytes: bytes,
) -> PhaseHTrustedRepairSuccess:
    """Seal the only H2-C trusted repair success carrier (private seam mint).

    The mint re-verifies the sealed data self-consistency before sealing:
    envelope hash/length equality, structured hash/length equality, the
    P commitment binding between the trusted result and the finalizer
    binding, and the prompt/schema literals.  It confers no authority by
    itself: only the actual lexical H2-C replay may call it.
    """

    from youtube_intel.quality import TrustedScoreResult

    if type(trusted_result) is not TrustedScoreResult:
        msg = (
            "trusted result must be an exact TrustedScoreResult; "
            f"got {type(trusted_result).__name__}"
        )
        raise ValueError(msg)
    if not job_id.strip() or not owner.strip() or not pipeline_version.strip():
        msg = "job identity fields must be non-empty"
        raise ValueError(msg)
    _validate_lower_hex(primary_request_hash, field_name="primary_request_hash")
    _validate_lower_hex(
        primary_normalized_input_hash, field_name="primary_normalized_input_hash"
    )
    _validate_lower_hex(scoring_input_sha256, field_name="scoring_input_sha256")

    envelope_sha256 = hashlib.sha256(envelope_bytes).hexdigest()
    envelope_length = len(envelope_bytes)
    structured_sha256 = hashlib.sha256(structured_bytes).hexdigest()
    structured_length = len(structured_bytes)

    binding = envelope.finalizer_binding
    if binding.primary_request_hash != primary_request_hash:
        msg = "finalizer binding primary_request_hash mismatches the P commitment"
        raise ValueError(msg)
    if binding.trusted_result != trusted_result.result:
        msg = "finalizer binding trusted result mismatches the sealed result"
        raise ValueError(msg)
    if binding.structured_result_sha256 != structured_sha256:
        msg = "finalizer binding structured hash mismatches the sealed bytes"
        raise ValueError(msg)
    if binding.structured_result_length != structured_length:
        msg = "finalizer binding structured length mismatches the sealed bytes"
        raise ValueError(msg)
    if trusted_result.result.request_hash != primary_request_hash:
        msg = "trusted result request_hash mismatches the PRIMARY semantic hash"
        raise ValueError(msg)

    return PhaseHTrustedRepairSuccess(
        sentinel=_PHASE_H_TRUSTED_REPAIR_SUCCESS_SENTINEL,
        job_id=job_id,
        owner=owner,
        pipeline_version=pipeline_version,
        primary_request_hash=primary_request_hash,
        primary_normalized_input_hash=primary_normalized_input_hash,
        scoring_input_sha256=scoring_input_sha256,
        repair_composite_envelope_bytes=envelope_bytes,
        repair_composite_envelope_sha256=envelope_sha256,
        repair_composite_envelope_length=envelope_length,
        trusted_result=trusted_result,
        structured_bytes=structured_bytes,
        structured_sha256=structured_sha256,
        structured_length=structured_length,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        envelope=envelope,
    )


@dataclass(frozen=True, slots=True)
class VerifiedScoringRead:
    """The single conceptual interface returned by the trusted scoring reader.

    Downstream callers (analysis, note, weekly, reporting) consume this
    pre-verified value and must not reconstruct scoring authority or apply a
    "latest scoring artifact" heuristic for v1 lineage.
    """

    scoring_outcome: ScoringOutcome
    video_id: str
    scoring_job_id: str
    scoring_success_provenance: str | None


class AuthoritativeScoringReader:
    """The sole trusted scoring selector/verifier.

    For a Video with a non-NULL authoritative pointer, the exact Job is fetched
    and classified FIRST on ``scoring_lineage_version``: v1 takes the exact
    lineage branch; NULL/unknown is malformed for a pointer and fails closed.
    For a pointerless Video, only the legacy compatibility branch may run, and
    the selected producing SCORING Job must be NULL-generation, so a v1 result
    can never downgrade through the legacy path.
    """

    def __init__(
        self,
        *,
        repository: Any,
        data_root: Path,
        summary_threshold: float,
        pipeline_version: str,
        current_model: str,
        current_output_language: str,
    ) -> None:
        if not 0 <= summary_threshold <= 10:
            msg = "summary_threshold must be in 0..10"
            raise ValueError(msg)
        self._repository = repository
        self._data_root = data_root
        self._summary_threshold = summary_threshold
        self._pipeline_version = pipeline_version
        self._current_model = current_model
        self._current_output_language = current_output_language

    def read(self, video_id: str) -> VerifiedScoringRead:
        video = self._repository.get_video(video_id)
        if video is None:
            raise ValueError("video does not exist")
        pointer = video.authoritative_scoring_job_id
        if pointer is not None:
            return self._read_lineage(video_id, pointer)
        return self._read_legacy(video_id)

    # -- helpers ------------------------------------------------------------

    def _read_artifact_bytes(self, record: ArtifactRecord, *, max_bytes: int) -> bytes:
        if (
            record.storage_root is not StorageRoot.DATA
            or record.deleted_at is not None
            or not record.relative_path
        ):
            raise ValueError("persisted artifact index is invalid")
        relative = PurePosixPath(record.relative_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in record.relative_path:
            raise ValueError("persisted artifact path is unsafe")
        path = self._data_root.joinpath(*relative.parts)
        current = path
        while current != self._data_root:
            if current.is_symlink():
                raise ValueError("persisted artifact path is unsafe")
            current = current.parent
        body = path.read_bytes()
        if len(body) > max_bytes or hashlib.sha256(body).hexdigest() != record.content_hash:
            raise ValueError("persisted artifact hash is invalid")
        return body

    def _outcome(self, result: ScoreResult, artifact: ArtifactRecord) -> ScoringOutcome:
        decision = result.score >= self._summary_threshold
        return ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=self._summary_threshold,
                final_should_summarize=decision,
                model_disagrees=result.should_summarize is not decision,
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=artifact.created_at,
                finished_at=artifact.created_at,
            ),
        )

    # -- v1 lineage branch --------------------------------------------------

    def _read_lineage(self, video_id: str, job_id: str) -> VerifiedScoringRead:
        job = self._repository.get_job(job_id)
        if (
            job is None
            or job.video_id != video_id
            or job.job_type is not JobType.VIDEO_STAGE
            or job.target_stage is not ProcessingStage.SCORING
            or job.pipeline_version != self._pipeline_version
            or job.status is not JobStatus.SUCCEEDED
        ):
            raise ValueError("authoritative scoring job is invalid")
        # Classify FIRST on lineage version: a pointer with a NULL or unknown
        # generation is malformed and fails closed (no legacy fallback).
        if job.scoring_lineage_version != SCORING_LINEAGE_VERSION_V1:
            raise ValueError("authoritative scoring job lineage is invalid")
        provenance = job.scoring_success_provenance
        structured_key = job.authoritative_scoring_artifact_key
        if provenance not in {"PRIMARY", "REPAIR_H2C"} or not structured_key:
            raise ValueError("authoritative scoring job provenance is invalid")
        structured = self._repository.get_artifact_by_key(structured_key)
        if (
            structured is None
            or structured.kind is not ArtifactKind.SCORING_STRUCTURED
            or structured.storage_root is not StorageRoot.DATA
            or structured.deleted_at is not None
            or structured.video_id != video_id
            or structured.job_id != job_id
            or structured.artifact_key != structured_key
        ):
            raise ValueError("authoritative structured artifact is invalid")
        if provenance == "REPAIR_H2C":
            result = self._verify_repair_structured(structured, video_id, job_id)
        else:
            result = self._verify_primary_structured(structured, video_id, job_id)
        return VerifiedScoringRead(
            scoring_outcome=self._outcome(result, structured),
            video_id=video_id,
            scoring_job_id=job_id,
            scoring_success_provenance=provenance,
        )

    def _verify_primary_structured(
        self, structured: ArtifactRecord, video_id: str, job_id: str
    ) -> ScoreResult:
        from youtube_intel.quality import (
            _SCORING_PROMPT_VERSION,
            _SCORING_SCHEMA_VERSION,
        )

        result = validate_score_result_json(
            self._read_artifact_bytes(structured, max_bytes=1_000_000)
        )
        if (
            structured.producer_version
            not in {
                _STRUCTURED_ARTIFACT_PRODUCER_VERSION,
                _G_STRUCTURED_ARTIFACT_PRODUCER_VERSION,
            }
            or structured.artifact_key != f"scoring/{result.request_hash}/structured"
            or structured.provider != "ollama"
            or structured.provider != result.provider
            or structured.model is None
            or structured.model != result.model
        ):
            raise ValueError("primary structured artifact identity is invalid")
        job = self._repository.get_job(job_id)
        if (
            job is None
            or job.video_id != video_id
            or job.target_stage is not ProcessingStage.SCORING
            or job.pipeline_version != self._pipeline_version
            or job.status is not JobStatus.SUCCEEDED
        ):
            raise ValueError("primary scoring job provenance is invalid")
        provider_call = self._repository.get_provider_call(result.request_hash)
        if (
            provider_call is None
            or provider_call.status is not ProviderCallStatus.SUCCEEDED
            or provider_call.operation != "local-scoring"
            or provider_call.provider != "ollama"
            or provider_call.provider != result.provider
            or provider_call.model != result.model
            or provider_call.prompt_version != PROMPT_VERSION
            or provider_call.schema_version != SCHEMA_VERSION
            or provider_call.request_hash != result.request_hash
            or not provider_call.response_artifact_id
            or result.schema_version not in {SCHEMA_VERSION, _SCORING_SCHEMA_VERSION}
            or result.prompt_version not in {PROMPT_VERSION, _SCORING_PROMPT_VERSION}
        ):
            raise ValueError("primary provider call provenance is invalid")
        raw = self._repository.get_artifact_by_key(
            f"scoring/{result.request_hash}/raw"
        )
        if (
            raw is None
            or raw.artifact_id != provider_call.response_artifact_id
            or raw.kind is not ArtifactKind.SCORING_RAW
            or raw.video_id != video_id
            or raw.job_id != job_id
            or raw.provider != result.provider
            or raw.provider != structured.provider
            or raw.model != result.model
            or raw.model != structured.model
            or raw.producer_version
            not in {
                _RAW_ARTIFACT_PRODUCER_VERSION,
                _G_RAW_ARTIFACT_PRODUCER_VERSION,
            }
        ):
            raise ValueError("primary raw artifact provenance is invalid")
        self._read_artifact_bytes(raw, max_bytes=1_000_000)
        self._check_current_config(result)
        return result

    def _verify_repair_structured(
        self, structured: ArtifactRecord, video_id: str, job_id: str
    ) -> ScoreResult:
        from youtube_intel.h2_evidence import (
            RepairCompositeEnvelope,
            repair_persistence_graph_hash,
        )
        from youtube_intel.h2_jcs import jcs_loads_strict, jcs_serialize

        if structured.producer_version != "scoring-structured-content-quality-repair-v1":
            raise ValueError("repair structured producer is invalid")
        p, g = parse_repair_structured_key(structured.artifact_key)
        if structured.relative_path != f"scoring/{p}/repair/{g}/structured.json":
            raise ValueError("repair structured path is invalid")
        result = validate_score_result_json(
            self._read_artifact_bytes(structured, max_bytes=1_000_000)
        )
        if result.request_hash != p:
            raise ValueError("repair structured result mismatches P")
        raw_key = f"scoring/{p}/repair/{g}/raw"
        raw = self._repository.get_artifact_by_key(raw_key)
        if (
            raw is None
            or raw.kind is not ArtifactKind.SCORING_RAW
            or raw.video_id != video_id
            or raw.job_id != job_id
            or raw.relative_path != f"scoring/{p}/repair/{g}/raw.json"
            or raw.producer_version != "scoring-raw-content-quality-repair-v1"
        ):
            raise ValueError("repair raw artifact is invalid")
        raw_body = self._read_artifact_bytes(raw, max_bytes=_H2C_ENVELOPE_ROOT_MAX)
        envelope_hash = hashlib.sha256(raw_body).hexdigest()
        if envelope_hash != raw.content_hash:
            raise ValueError("repair raw envelope hash is invalid")
        envelope = RepairCompositeEnvelope.model_validate(jcs_loads_strict(raw_body))
        if jcs_serialize(envelope.model_dump(mode="json")) != raw_body:
            raise ValueError("repair raw envelope is not canonical")
        provider_evidence = envelope.repair_provider_evidence
        quality_evidence = envelope.repair_quality_evidence
        r = provider_evidence.request_hash
        j = quality_evidence.judge_h2
        settings_hash = hashlib.sha256(
            jcs_serialize(provider_evidence.settings_provenance.model_dump(mode="json"))
        ).hexdigest()
        if settings_hash != provider_evidence.settings_provenance_sha256:
            raise ValueError("repair settings provenance hash is invalid")
        identity = build_repair_persistence_graph_identity(
            primary_request_hash=p,
            repair_request_hash=r,
            repair_judge_request_hash=j,
            settings_provenance_sha256=settings_hash,
            repair_envelope_sha256=envelope_hash,
            structured_result_sha256=structured.content_hash,
        )
        if repair_persistence_graph_hash(identity) != g:
            raise ValueError("repair graph identity G is invalid")
        repair_call = self._repository.get_provider_call(r)
        judge_call = self._repository.get_provider_call(j)
        if repair_call is None or judge_call is None:
            raise ValueError("repair provider calls are missing")
        # Re-prove every persisted identity-bearing ProviderCall field against
        # the sealed envelope evidence; the provenance flag and the R/J hashes
        # alone are not trusted.
        if (
            repair_call.status is not ProviderCallStatus.SUCCEEDED
            or repair_call.operation != provider_evidence.operation
            or repair_call.provider != provider_evidence.provider
            or repair_call.model != provider_evidence.model
            or repair_call.prompt_version != provider_evidence.prompt_version
            or repair_call.schema_version
            != provider_evidence.operation_schema_version
            or repair_call.request_hash != r
            or repair_call.request_hash != provider_evidence.request_hash
            or build_provider_request_hash(
                operation=provider_evidence.operation,
                normalized_input_hash=provider_evidence.normalized_input_hash,
                provider=provider_evidence.provider,
                model=provider_evidence.model,
                prompt_version=provider_evidence.prompt_version,
                schema_version=provider_evidence.operation_schema_version,
            )
            != r
            or repair_call.response_artifact_id != raw.artifact_id
        ):
            raise ValueError("repair provider call identity is invalid")
        if (
            judge_call.status is not ProviderCallStatus.SUCCEEDED
            or judge_call.operation != quality_evidence.judge_evidence.operation
            or judge_call.provider != quality_evidence.judge_evidence.provider
            or judge_call.model != quality_evidence.judge_evidence.model
            or judge_call.prompt_version
            != quality_evidence.judge_evidence.prompt_version
            or judge_call.schema_version
            != quality_evidence.judge_evidence.operation_schema_version
            or judge_call.request_hash != j
            or judge_call.request_hash != quality_evidence.judge_h2
            or build_provider_request_hash(
                operation=quality_evidence.judge_evidence.operation,
                normalized_input_hash=quality_evidence.judge_h1,
                provider=quality_evidence.judge_evidence.provider,
                model=quality_evidence.judge_evidence.model,
                prompt_version=quality_evidence.judge_evidence.prompt_version,
                schema_version=(
                    quality_evidence.judge_evidence.operation_schema_version
                ),
            )
            != j
            or judge_call.response_artifact_id != raw.artifact_id
        ):
            raise ValueError("repair judge provider call identity is invalid")
        self._check_current_config(result)
        return result

    def _check_current_config(self, result: ScoreResult) -> None:
        if result.model != self._current_model:
            raise ValueError(
                "persisted scoring model does not match current configuration"
            )
        if result.output_language != self._current_output_language:
            raise ValueError(
                "persisted scoring output language does not match current configuration"
            )

    # -- legacy pointerless branch ------------------------------------------

    def _read_legacy(self, video_id: str) -> VerifiedScoringRead:
        artifact = self._repository.latest_artifact(
            video_id, ArtifactKind.SCORING_STRUCTURED
        )
        if artifact is None:
            raise ValueError("persisted score is unavailable")
        # The selected producing SCORING Job must be pre-lineage (NULL
        # generation); a v1/unknown result can never downgrade to legacy.
        if not artifact.job_id:
            raise ValueError("legacy scoring artifact has no producing job")
        job = self._repository.get_job(artifact.job_id)
        if (
            job is None
            or job.target_stage is not ProcessingStage.SCORING
            or job.scoring_lineage_version is not None
        ):
            raise ValueError("legacy scoring selection is invalid")
        result = self._verify_primary_structured(artifact, video_id, artifact.job_id)
        return VerifiedScoringRead(
            scoring_outcome=self._outcome(result, artifact),
            video_id=video_id,
            scoring_job_id=artifact.job_id,
            scoring_success_provenance=None,
        )


__all__ = [
    "AuthoritativeScoringReader",
    "H2CAuthoritativeGraphConflict",
    "H2CStaleScoringLease",
    "InMemoryScoringCache",
    "PROMPT_VERSION",
    "PhaseFTrustedScoringSuccess",
    "PhaseHTrustedRepairSuccess",
    "PrimaryScoringAttempt",
    "RepositoryBackedScoringService",
    "SAMPLING_VERSION",
    "SCHEMA_VERSION",
    "ScoringCache",
    "ScoringJobContext",
    "ScoringPersistenceError",
    "ScoringService",
    "TrustedPersistenceEntry",
    "VerifiedScoringRead",
    "build_primary_scoring_attempt",
    "build_repair_artifact_keys",
    "build_repair_composite_envelope",
    "build_repair_persistence_graph_identity",
    "build_scoring_input",
    "h2c_replay_invalid_detail",
    "parse_repair_raw_key",
    "parse_repair_raw_relative_path",
    "parse_repair_structured_key",
    "parse_repair_structured_relative_path",
    "sample_transcript",
    "verify_repair_envelope_admission",
]
