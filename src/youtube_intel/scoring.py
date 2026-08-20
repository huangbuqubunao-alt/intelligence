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
from typing import TYPE_CHECKING, Final, NoReturn, Protocol

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    AppError,
    ContentQualityInput,
    ContentQualityResult,
    DiagnosticEntry,
    ErrorCode,
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


class PhaseFTrustedScoringSuccess:
    """Opaque memory-only Phase F success aggregate.

    The aggregate is not a Pydantic DTO and cannot be constructed, copied,
    serialized, subclassed, or mutated by callers.  It seals the trusted
    result together with its primary attempt through the three canonical
    hashes so a later phase can verify the complete binding in memory.
    """

    __slots__ = (
        "_trusted_result",
        "_primary_attempt",
        "_scoring_request_hash",
        "_candidate_hash",
        "_raw_response_hash",
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
    ) -> None:
        if sentinel is not _PHASE_F_TRUSTED_SCORING_SUCCESS_SENTINEL:
            msg = "PhaseFTrustedScoringSuccess can only be minted by the trusted seam"
            raise ValueError(msg)
        self._trusted_result = trusted_result
        self._primary_attempt = primary_attempt
        self._scoring_request_hash = scoring_request_hash
        self._candidate_hash = candidate_hash
        self._raw_response_hash = raw_response_hash
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

    def __copy__(self) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("PhaseFTrustedScoringSuccess cannot be serialized")


def mint_phase_f_trusted_scoring_success(
    *,
    trusted_result: TrustedScoreResult,
    primary_attempt: PrimaryScoringAttempt,
) -> PhaseFTrustedScoringSuccess:
    """Seal the only Phase F success aggregate with self-verifying hashes.

    A bare ``TrustedScoreResult`` is not a Phase F success; the aggregate is
    minted only with the exact primary attempt and re-verified in memory.
    """

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

    return PhaseFTrustedScoringSuccess(
        sentinel=_PHASE_F_TRUSTED_SCORING_SUCCESS_SENTINEL,
        trusted_result=trusted_result,
        primary_attempt=primary_attempt,
        scoring_request_hash=primary_attempt.scoring_request_hash,
        candidate_hash=primary_attempt.candidate_hash,
        raw_response_hash=primary_attempt.raw_response_hash,
    )


def run_primary_trusted_scoring_seam(
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
    return mint_phase_f_trusted_scoring_success(
        trusted_result=trusted_result,
        primary_attempt=attempt,
    )


__all__ = [
    "InMemoryScoringCache",
    "PROMPT_VERSION",
    "PhaseFTrustedScoringSuccess",
    "PrimaryScoringAttempt",
    "RepositoryBackedScoringService",
    "SAMPLING_VERSION",
    "SCHEMA_VERSION",
    "ScoringCache",
    "ScoringJobContext",
    "ScoringPersistenceError",
    "ScoringService",
    "build_primary_scoring_attempt",
    "build_scoring_input",
    "mint_phase_f_trusted_scoring_success",
    "run_primary_trusted_scoring_seam",
    "sample_transcript",
]
