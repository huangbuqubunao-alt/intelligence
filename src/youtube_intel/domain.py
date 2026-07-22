"""Domain contracts: entities, provider ports, state machines, and errors.

This module must not import concrete provider SDKs or free-form dict public APIs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Final, Literal, Never, Protocol, Self, TypeAlias, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Shared model config
# ---------------------------------------------------------------------------

_FROZEN: Final = ConfigDict(extra="forbid", frozen=True)


class _DomainModel(BaseModel):
    model_config = _FROZEN


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class LiveStatus(str, Enum):
    NONE = "none"
    UPCOMING = "upcoming"
    LIVE = "live"
    ENDED = "ended"


class Availability(str, Enum):
    PUBLIC = "public"
    UNAVAILABLE = "unavailable"
    PRIVATE = "private"
    DELETED = "deleted"
    RESTRICTED = "restricted"


class TranscriptSourceType(str, Enum):
    MANUAL_SUBTITLE = "manual_subtitle"
    AUTO_SUBTITLE = "auto_subtitle"
    WHISPER = "whisper"


class SubtitleFormat(str, Enum):
    JSON3 = "json3"
    VTT = "vtt"
    SRT = "srt"


class TranscriptQualityFlag(str, Enum):
    ROLLING_CUES_DEDUPED = "ROLLING_CUES_DEDUPED"
    SPEAKER_LABELS_PRESENT = "SPEAKER_LABELS_PRESENT"
    NON_SPEECH_MARKERS_PRESENT = "NON_SPEECH_MARKERS_PRESENT"


class TranscriptionReason(str, Enum):
    NO_TRACKS = "NO_TRACKS"
    NO_MATCHING_LANGUAGE = "NO_MATCHING_LANGUAGE"
    ALL_CANDIDATES_INVALID = "ALL_CANDIDATES_INVALID"


class PointKind(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"


class EvidenceSource(str, Enum):
    TITLE = "title"
    CHANNEL_NAME = "channel_name"
    DESCRIPTION = "description"
    TRANSCRIPT_SAMPLE = "transcript_sample"


class AnalysisSkipReason(str, Enum):
    CLOUD_DISABLED = "CLOUD_DISABLED"
    CREDENTIAL_UNAVAILABLE = "CREDENTIAL_UNAVAILABLE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    PROVIDER_REFUSAL = "PROVIDER_REFUSAL"


class NotAvailableReason(str, Enum):
    NO_MATCHING_LANGUAGE = "NO_MATCHING_LANGUAGE"
    NO_CONTENT = "NO_CONTENT"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"


class NoteKind(str, Enum):
    VIDEO = "video"
    WEEKLY = "weekly"


class PipelineStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    METADATA_READY = "METADATA_READY"
    DEFERRED = "DEFERRED"
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    SCORED = "SCORED"
    LOW_VALUE_READY = "LOW_VALUE_READY"
    ANALYSIS_READY = "ANALYSIS_READY"
    NOTE_WRITTEN = "NOTE_WRITTEN"
    COMPLETE = "COMPLETE"
    SKIPPED_DURATION_LIMIT = "SKIPPED_DURATION_LIMIT"


class ProcessingStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    METADATA = "METADATA"
    TRANSCRIPT = "TRANSCRIPT"
    SCORING = "SCORING"
    ANALYSIS = "ANALYSIS"
    NOTE_WRITE = "NOTE_WRITE"
    WEEKLY_REPORT = "WEEKLY_REPORT"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRY_PENDING = "RETRY_PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"


class ErrorCode(str, Enum):
    """Unified error codes frozen in System Design §12 (exact set; no extras)."""

    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    CONFIG_INVALID = "CONFIG_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    LOCAL_RESOURCE = "LOCAL_RESOURCE"


SCORE_DIMENSION_NAMES: Final[tuple[str, ...]] = (
    "technical",
    "business",
    "product",
    "originality",
    "practicality",
    "industry_impact",
)

# Private mutable builders → public runtime-immutable mappings (values are frozensets).
_PIPELINE_TRANSITIONS: dict[PipelineStatus, frozenset[PipelineStatus]] = {
    PipelineStatus.DISCOVERED: frozenset(
        {PipelineStatus.METADATA_READY, PipelineStatus.DEFERRED}
    ),
    PipelineStatus.DEFERRED: frozenset({PipelineStatus.METADATA_READY}),
    PipelineStatus.METADATA_READY: frozenset(
        {PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SKIPPED_DURATION_LIMIT}
    ),
    PipelineStatus.TRANSCRIPT_READY: frozenset({PipelineStatus.SCORED}),
    PipelineStatus.SCORED: frozenset(
        {PipelineStatus.LOW_VALUE_READY, PipelineStatus.ANALYSIS_READY}
    ),
    PipelineStatus.LOW_VALUE_READY: frozenset({PipelineStatus.COMPLETE}),
    PipelineStatus.ANALYSIS_READY: frozenset({PipelineStatus.NOTE_WRITTEN}),
    PipelineStatus.NOTE_WRITTEN: frozenset({PipelineStatus.COMPLETE}),
    PipelineStatus.COMPLETE: frozenset(),
    PipelineStatus.SKIPPED_DURATION_LIMIT: frozenset(),
}
PIPELINE_TRANSITIONS: Final[Mapping[PipelineStatus, frozenset[PipelineStatus]]] = (
    MappingProxyType(_PIPELINE_TRANSITIONS)
)

_JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PENDING: frozenset({JobStatus.RUNNING}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.SUCCEEDED, JobStatus.RETRY_PENDING, JobStatus.FAILED_FINAL}
    ),
    JobStatus.RETRY_PENDING: frozenset({JobStatus.PENDING}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED_FINAL: frozenset(),
}
JOB_TRANSITIONS: Final[Mapping[JobStatus, frozenset[JobStatus]]] = MappingProxyType(
    _JOB_TRANSITIONS
)


# ---------------------------------------------------------------------------
# Structured errors
# ---------------------------------------------------------------------------


class AppError(_DomainModel):
    """Structured, redacted application error.

    Retry semantics live in ``retryable`` and ``retry_after_seconds``, not in
    free-form message strings.
    """

    code: ErrorCode
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool
    retry_after_seconds: float | None = Field(default=None, ge=0)
    run_id: str | None = None
    job_id: str | None = None
    video_id: str | None = None
    stage: ProcessingStage | None = None

    @model_validator(mode="after")
    def _retry_after_only_when_retryable(self) -> AppError:
        if self.retry_after_seconds is not None and not self.retryable:
            msg = "retry_after_seconds requires retryable=True"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Core data objects
# ---------------------------------------------------------------------------


class VideoMetadata(_DomainModel):
    video_id: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)
    channel_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    source_url: str = Field(min_length=1)
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    default_language: str | None = None
    available_languages: tuple[str, ...] = ()
    live_status: LiveStatus
    availability: Availability


class TranscriptArtifact(_DomainModel):
    video_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    source_type: TranscriptSourceType
    requested_language: str | None
    source_format: SubtitleFormat | None
    text_path: str = Field(min_length=1)
    timed_text_path: str | None = None
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_byte_count: int = Field(gt=0)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    char_count: int = Field(ge=0)
    segment_count: int = Field(ge=0)
    normalization_version: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str | None = None
    created_at: datetime
    quality_flags: tuple[TranscriptQualityFlag, ...] = ()

    @field_validator("requested_language")
    @classmethod
    def _validate_requested_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.strip() != value:
            msg = "requested_language must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        return value

    @field_validator("text_path", "timed_text_path")
    @classmethod
    def _safe_data_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.strip() != value or "\\" in value:
            msg = "transcript paths must be safe DATA-relative POSIX paths"
            raise ValueError(msg)
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or not path.parts
            or path.parts[0] != "transcripts"
        ):
            msg = "transcript paths must be safe DATA-relative paths under transcripts/"
            raise ValueError(msg)
        return value

    @field_validator("quality_flags")
    @classmethod
    def _unique_quality_flags(
        cls,
        value: tuple[TranscriptQualityFlag, ...],
    ) -> tuple[TranscriptQualityFlag, ...]:
        if len(value) != len(set(value)):
            msg = "quality_flags must be unique"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _source_specific_fields(self) -> TranscriptArtifact:
        if self.source_type is TranscriptSourceType.WHISPER:
            if self.requested_language is not None:
                msg = "requested_language must be None for whisper"
                raise ValueError(msg)
            if self.source_format is not None:
                msg = "source_format must be None for whisper"
                raise ValueError(msg)
            return self

        if self.requested_language is None:
            msg = "requested_language is required for subtitle sources"
            raise ValueError(msg)
        if self.source_format is None:
            msg = "source_format is required for subtitle sources"
            raise ValueError(msg)
        if self.timed_text_path is None:
            msg = "timed_text_path is required for subtitle sources"
            raise ValueError(msg)
        return self


class ScoreDimensions(_DomainModel):
    technical: float | None = Field(default=None, ge=0, le=10)
    business: float | None = Field(default=None, ge=0, le=10)
    product: float | None = Field(default=None, ge=0, le=10)
    originality: float | None = Field(default=None, ge=0, le=10)
    practicality: float | None = Field(default=None, ge=0, le=10)
    industry_impact: float | None = Field(default=None, ge=0, le=10)


class ScoreResult(_DomainModel):
    schema_version: str = Field(min_length=1)
    score: float = Field(ge=0, le=10)
    reason: str = Field(min_length=1, max_length=2000)
    topics: tuple[str, ...] = Field(min_length=1, max_length=10)
    should_summarize: bool
    dimensions: ScoreDimensions | None = None
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    request_hash: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "reason must be non-empty after strip"
            raise ValueError(msg)
        if len(stripped) > 2000:
            msg = "reason must be at most 2000 characters after strip"
            raise ValueError(msg)
        return stripped

    @field_validator("topics")
    @classmethod
    def _validate_topics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            msg = "topics must contain at least one item"
            raise ValueError(msg)
        if len(value) > 10:
            msg = "topics must contain at most 10 items"
            raise ValueError(msg)
        seen: set[str] = set()
        for topic in value:
            if not 1 <= len(topic) <= 80:
                msg = "each topic must have length 1..80"
                raise ValueError(msg)
            if topic in seen:
                msg = "topics must be unique"
                raise ValueError(msg)
            seen.add(topic)
        return value


class _UpdateProtectedAnalysisContract(_DomainModel):
    """Preserve validation boundaries for shared cloud-analysis contracts."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for analysis contracts"
            raise ValueError(msg)
        return super().model_copy(deep=deep)


class AnalysisPayload(_UpdateProtectedAnalysisContract):
    """The complete and exclusive set of fields permitted to leave the machine."""

    video_id: str = Field(min_length=1, pattern=r"\S")
    title: str = Field(min_length=1, pattern=r"\S")
    channel_name: str = Field(min_length=1, pattern=r"\S")
    published_at: datetime
    duration_seconds: int = Field(ge=0)
    default_language: str | None = Field(default=None, pattern=r"\S")
    description: str = Field(default="", max_length=4000)
    transcript_language: str = Field(min_length=1, pattern=r"\S")
    output_language: str = Field(min_length=1, pattern=r"\S")
    transcript_sample: str = Field(min_length=1, pattern=r"\S")


class EvidenceExcerpt(_UpdateProtectedAnalysisContract):
    evidence_id: str = Field(min_length=1, pattern=r"\S")
    source: EvidenceSource
    excerpt: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    start_seconds: Literal[None] = None
    end_seconds: Literal[None] = None


class AnalysisPoint(_UpdateProtectedAnalysisContract):
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    kind: PointKind
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=10)

    @field_validator("evidence_ids")
    @classmethod
    def _unique_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "evidence_ids must be unique"
            raise ValueError(msg)
        for eid in value:
            if not eid.strip():
                msg = "evidence_ids items must be non-empty"
                raise ValueError(msg)
        return value


class AnalysisContent(_UpdateProtectedAnalysisContract):
    one_sentence_summary: str = Field(min_length=1, max_length=500, pattern=r"\S")
    core_points: tuple[AnalysisPoint, ...] = Field(min_length=1, max_length=10)
    key_facts: tuple[AnalysisPoint, ...] = Field(default=(), max_length=20)
    product_opportunities: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    business_opportunities: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    actionable_directions: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    hypotheses_to_validate: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    action_recommendations: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    risks: tuple[AnalysisPoint, ...] = Field(default=(), max_length=10)
    keywords: tuple[str, ...] = Field(min_length=1, max_length=20)
    evidence: tuple[EvidenceExcerpt, ...] = Field(default=(), max_length=20)

    @field_validator("keywords")
    @classmethod
    def _validate_keywords(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            msg = "keywords must contain at least one item"
            raise ValueError(msg)
        if len(value) > 20:
            msg = "keywords must contain at most 20 items"
            raise ValueError(msg)
        seen: set[str] = set()
        for kw in value:
            if not kw.strip() or not 1 <= len(kw) <= 80:
                msg = "each keyword must have length 1..80"
                raise ValueError(msg)
            if kw in seen:
                msg = "keywords must be unique"
                raise ValueError(msg)
            seen.add(kw)
        return value

    @model_validator(mode="after")
    def _cross_field_integrity(self) -> AnalysisContent:
        evidence_ids = {item.evidence_id for item in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            msg = "evidence_id values must be unique within AnalysisContent"
            raise ValueError(msg)

        kind_rules = (
            ("core_points", self.core_points, {PointKind.FACT, PointKind.INFERENCE}),
            ("key_facts", self.key_facts, {PointKind.FACT}),
            ("product_opportunities", self.product_opportunities, {PointKind.INFERENCE}),
            ("business_opportunities", self.business_opportunities, {PointKind.INFERENCE}),
            ("actionable_directions", self.actionable_directions, {PointKind.RECOMMENDATION}),
            ("hypotheses_to_validate", self.hypotheses_to_validate, {PointKind.INFERENCE}),
            ("action_recommendations", self.action_recommendations, {PointKind.RECOMMENDATION}),
            ("risks", self.risks, {PointKind.INFERENCE}),
        )
        for field_name, points, allowed_kinds in kind_rules:
            for point in points:
                if point.kind not in allowed_kinds:
                    allowed = ", ".join(sorted(kind.value for kind in allowed_kinds))
                    msg = f"{field_name} items must have kind in {{{allowed}}}"
                    raise ValueError(msg)

        all_points: list[AnalysisPoint] = [
            *self.core_points,
            *self.key_facts,
            *self.product_opportunities,
            *self.business_opportunities,
            *self.actionable_directions,
            *self.hypotheses_to_validate,
            *self.action_recommendations,
            *self.risks,
        ]
        for point in all_points:
            missing = [eid for eid in point.evidence_ids if eid not in evidence_ids]
            if missing:
                msg = f"evidence_ids reference unknown evidence: {missing}"
                raise ValueError(msg)
        return self


class AnalysisResult(AnalysisContent):
    schema_version: Literal["analysis-result-v1"] = "analysis-result-v1"
    provider: str = Field(min_length=1, pattern=r"\S")
    model: str = Field(min_length=1, pattern=r"\S")
    prompt_version: Literal["analysis-prompt-v1"] = "analysis-prompt-v1"
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Cross-module I/O objects
# ---------------------------------------------------------------------------


class DiagnosticEntry(_DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=2000)


class ProviderCallMetadata(_DomainModel):
    provider: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    provider_version: str | None = None
    model: str | None = None
    diagnostics: tuple[DiagnosticEntry, ...] = ()

    @model_validator(mode="after")
    def _time_order(self) -> ProviderCallMetadata:
        if self.finished_at < self.started_at:
            msg = "finished_at must be >= started_at"
            raise ValueError(msg)
        return self


class AnalysisCompleted(_UpdateProtectedAnalysisContract):
    result: AnalysisResult
    call: ProviderCallMetadata

    @field_validator("call")
    @classmethod
    def _call_matches_result(
        cls,
        value: ProviderCallMetadata,
        info: ValidationInfo,
    ) -> ProviderCallMetadata:
        if not value.provider.strip():
            msg = "analysis call provider must be non-empty"
            raise ValueError(msg)
        if value.model is None or not value.model.strip():
            msg = "analysis call model must be non-empty"
            raise ValueError(msg)
        result = info.data.get("result")
        if isinstance(result, AnalysisResult):
            if result.provider != value.provider:
                msg = "analysis result provider must match call provider"
                raise ValueError(msg)
            if result.model != value.model:
                msg = "analysis result model must match call model"
                raise ValueError(msg)
        return value


class AnalysisSkipped(_UpdateProtectedAnalysisContract):
    reason: AnalysisSkipReason
    call: ProviderCallMetadata | None
    safe_message: str = Field(min_length=1, max_length=2000)

    @field_validator("safe_message")
    @classmethod
    def _safe_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "safe_message must be non-empty after strip"
            raise ValueError(msg)
        return stripped


AnalysisOutcome: TypeAlias = AnalysisCompleted | AnalysisSkipped


class DiscoveryCursor(_DomainModel):
    channel_id: str = Field(min_length=1)
    last_checked_at: datetime | None = None
    latest_published_at: datetime | None = None
    latest_video_id: str | None = None
    provider_cursor: str | None = None


class DiscoveryBatch(_DomainModel):
    channel_id: str = Field(min_length=1)
    video_ids: tuple[str, ...]
    next_cursor: DiscoveryCursor
    call: ProviderCallMetadata

    @field_validator("video_ids")
    @classmethod
    def _unique_video_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for vid in value:
            if not vid:
                msg = "video_ids items must be non-empty"
                raise ValueError(msg)
            if vid in seen:
                msg = "video_ids must be unique while preserving order"
                raise ValueError(msg)
            seen.add(vid)
        return value


class _UpdateProtectedScoringContract(_DomainModel):
    """Preserve validation boundaries for shared scoring contracts."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for scoring contracts"
            raise ValueError(msg)
        return super().model_copy(deep=deep)


class TranscriptSample(_UpdateProtectedScoringContract):
    """A bounded, ordered selection from one canonical transcript.

    The scoring service owns the ``sampling-v1`` slicing algorithm. This contract
    preserves its selected segments and binds them to the full canonical content
    hash so a sample cannot be reused for different transcript content.
    """

    head: str = Field(min_length=1)
    body: str = ""
    tail: str = ""
    selected_char_count: int = Field(ge=3)
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    sampling_version: Literal["sampling-v1"] = "sampling-v1"

    @model_validator(mode="after")
    def _selected_character_count_matches_segments(self) -> TranscriptSample:
        if self.selected_char_count != len(self.head) + len(self.body) + len(self.tail):
            msg = "selected_char_count must equal the total selected sample characters"
            raise ValueError(msg)
        return self


class ScoringInput(_UpdateProtectedScoringContract):
    video: VideoMetadata
    sample: TranscriptSample
    transcript_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    language: str = Field(min_length=1)
    request_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def _sample_binds_to_full_transcript(self) -> ScoringInput:
        if self.sample.source_content_hash != self.transcript_content_hash:
            msg = "transcript_content_hash must match sample.source_content_hash"
            raise ValueError(msg)
        return self


class ScoringDecision(_UpdateProtectedScoringContract):
    threshold: float = Field(ge=0, le=10)
    final_should_summarize: bool
    model_disagrees: bool


class ScoringOutcome(_UpdateProtectedScoringContract):
    result: ScoreResult
    decision: ScoringDecision
    call: ProviderCallMetadata

    @model_validator(mode="after")
    def _final_decision_is_derived_from_score(self) -> ScoringOutcome:
        expected_final = self.result.score >= self.decision.threshold
        if self.decision.final_should_summarize is not expected_final:
            msg = "final_should_summarize must equal score >= threshold"
            raise ValueError(msg)
        expected_disagreement = (
            self.result.should_summarize != self.decision.final_should_summarize
        )
        if self.decision.model_disagrees is not expected_disagreement:
            msg = "model_disagrees must equal model suggestion disagreement"
            raise ValueError(msg)
        return self


class AnalysisInput(_UpdateProtectedAnalysisContract):
    payload: AnalysisPayload
    transcript_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_version: Literal["analysis-prompt-v1"] = "analysis-prompt-v1"
    schema_version: Literal["analysis-result-v1"] = "analysis-result-v1"
    sampling_version: Literal["cloud-token-sampling-v1"] = "cloud-token-sampling-v1"
    privacy_version: Literal["cloud-privacy-v1"] = "cloud-privacy-v1"


class NotAvailable(_DomainModel):
    reason_code: NotAvailableReason
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool
    call: ProviderCallMetadata
    retry_after_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _retry_after_consistency(self) -> NotAvailable:
        if self.retry_after_seconds is not None and not self.retryable:
            msg = "retry_after_seconds requires retryable=True"
            raise ValueError(msg)
        return self


class TranscriptReady(_DomainModel):
    outcome: Literal["ready"] = "ready"
    artifact: TranscriptArtifact
    call: ProviderCallMetadata


class TranscriptionRequired(_DomainModel):
    outcome: Literal["transcription_required"] = "transcription_required"
    reason: TranscriptionReason
    call: ProviderCallMetadata
    attempted_track_count: int = Field(ge=0)


TranscriptFetchResult: TypeAlias = TranscriptReady | TranscriptionRequired


class _UpdateProtectedNoteRef(_DomainModel):
    """Prevent callers from bypassing NoteRef identity validation."""

    def model_copy(
        self,
        *,
        update: Mapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            msg = "model_copy(update=...) is disabled for NoteRef"
            raise ValueError(msg)
        return super().model_copy(deep=deep)


class NoteRef(_UpdateProtectedNoteRef):
    kind: NoteKind
    relative_path: str = Field(min_length=1)
    content_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    @field_validator("relative_path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        if not value or value.strip() != value:
            msg = "relative_path must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        if "\x00" in value or "\\" in value:
            msg = "relative_path must be a safe relative path under the vault"
            raise ValueError(msg)
        if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
            msg = "relative_path must not include a drive prefix"
            raise ValueError(msg)
        path = PurePosixPath(value)
        if path.is_absolute() or any(
            not part or part in {".", ".."} for part in value.split("/")
        ):
            msg = "relative_path must be a canonical relative path"
            raise ValueError(msg)
        if not value.endswith(".md"):
            msg = "relative_path must end in .md"
            raise ValueError(msg)
        return value


class WeeklyReportItem(_DomainModel):
    video: VideoMetadata
    score: ScoreResult
    note_ref: NoteRef
    one_sentence_summary: str = Field(min_length=1, max_length=500)


class WeeklyReportInput(_DomainModel):
    iso_year: int = Field(ge=1)
    iso_week: int = Field(ge=1, le=53)
    timezone: str = Field(min_length=1)
    items: tuple[WeeklyReportItem, ...]
    generated_at: datetime

    @model_validator(mode="after")
    def _items_sorted(self) -> WeeklyReportInput:
        expected = tuple(
            sorted(
                self.items,
                key=lambda item: (-item.score.score, item.video.video_id),
            )
        )
        if self.items != expected:
            msg = "items must be sorted by score desc then video_id asc"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Channel (domain view used by SourceProvider)
# ---------------------------------------------------------------------------


class ChannelRef(_DomainModel):
    channel_id: str = Field(min_length=1)
    enabled: bool = True
    priority: int = Field(default=50, ge=0, le=100)


# ---------------------------------------------------------------------------
# State transition helpers
# ---------------------------------------------------------------------------


class InvalidTransitionError(Exception):
    """Raised when a pipeline or job transition is not allowed.

    Not mapped to a dedicated ErrorCode: System Design §12 does not freeze an
    INVALID_TRANSITION code. Callers may treat this as a programming/contract error.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def can_transition_pipeline(current: PipelineStatus, target: PipelineStatus) -> bool:
    return target in PIPELINE_TRANSITIONS.get(current, frozenset())


def transition_pipeline(current: PipelineStatus, target: PipelineStatus) -> PipelineStatus:
    if not can_transition_pipeline(current, target):
        raise InvalidTransitionError(
            f"illegal pipeline transition: {current.value} -> {target.value}"
        )
    return target


def can_transition_job(current: JobStatus, target: JobStatus) -> bool:
    return target in JOB_TRANSITIONS.get(current, frozenset())


def transition_job(current: JobStatus, target: JobStatus) -> JobStatus:
    if not can_transition_job(current, target):
        raise InvalidTransitionError(
            f"illegal job transition: {current.value} -> {target.value}"
        )
    return target


def pipeline_after_job_failure(
    pipeline_status: PipelineStatus,
    job_status: JobStatus,
) -> PipelineStatus:
    """Failed or retrying jobs do not change the video's last successful pipeline status.

    C-07 recovery stage identity is expressed by ``ProcessingStage`` (Job target stage
    enum). This task does not freeze a Job aggregate with a ``target_stage`` field;
    persistence of that field is TASK-003 scope.
    """
    if job_status not in {JobStatus.RETRY_PENDING, JobStatus.FAILED_FINAL}:
        raise InvalidTransitionError(
            "pipeline_after_job_failure only applies to RETRY_PENDING or FAILED_FINAL"
        )
    return pipeline_status


# ---------------------------------------------------------------------------
# Provider protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class SourceProvider(Protocol):
    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch: ...


@runtime_checkable
class MetadataProvider(Protocol):
    def fetch(self, video_id: str) -> VideoMetadata: ...


@runtime_checkable
class TranscriptProvider(Protocol):
    def fetch(
        self,
        video: VideoMetadata,
        language_preferences: Sequence[str],
    ) -> TranscriptFetchResult: ...


@runtime_checkable
class ScoringProvider(Protocol):
    def score(self, scoring_input: ScoringInput) -> ScoreResult: ...


@runtime_checkable
class SummaryProvider(Protocol):
    def summarize(self, analysis_input: AnalysisInput) -> AnalysisResult: ...


@runtime_checkable
class KnowledgeSink(Protocol):
    def upsert_video_note(
        self,
        *,
        video: VideoMetadata,
        transcript: TranscriptArtifact,
        scoring: ScoringOutcome,
        analysis: AnalysisOutcome,
        processed_at: datetime,
        pipeline_version: str,
    ) -> NoteRef: ...

    def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef: ...


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "SCORE_DIMENSION_NAMES",
    "PIPELINE_TRANSITIONS",
    "JOB_TRANSITIONS",
    "LiveStatus",
    "Availability",
    "TranscriptSourceType",
    "SubtitleFormat",
    "TranscriptQualityFlag",
    "TranscriptionReason",
    "PointKind",
    "EvidenceSource",
    "AnalysisSkipReason",
    "NotAvailableReason",
    "NoteKind",
    "PipelineStatus",
    "ProcessingStage",
    "JobStatus",
    "ErrorCode",
    "AppError",
    "VideoMetadata",
    "TranscriptArtifact",
    "ScoreDimensions",
    "ScoreResult",
    "AnalysisPayload",
    "EvidenceExcerpt",
    "AnalysisPoint",
    "AnalysisContent",
    "AnalysisResult",
    "DiagnosticEntry",
    "ProviderCallMetadata",
    "AnalysisCompleted",
    "AnalysisSkipped",
    "AnalysisOutcome",
    "DiscoveryCursor",
    "DiscoveryBatch",
    "TranscriptSample",
    "ScoringInput",
    "ScoringDecision",
    "ScoringOutcome",
    "AnalysisInput",
    "NotAvailable",
    "TranscriptReady",
    "TranscriptionRequired",
    "TranscriptFetchResult",
    "NoteRef",
    "WeeklyReportItem",
    "WeeklyReportInput",
    "ChannelRef",
    "InvalidTransitionError",
    "can_transition_pipeline",
    "transition_pipeline",
    "can_transition_job",
    "transition_job",
    "pipeline_after_job_failure",
    "SourceProvider",
    "MetadataProvider",
    "TranscriptProvider",
    "ScoringProvider",
    "SummaryProvider",
    "KnowledgeSink",
]
