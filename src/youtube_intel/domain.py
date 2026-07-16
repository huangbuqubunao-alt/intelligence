"""Domain contracts: entities, provider ports, state machines, and errors.

This module must not import concrete provider SDKs or free-form dict public APIs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Final, Literal, Protocol, TypeAlias, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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
    METADATA = "metadata"
    TRANSCRIPT = "transcript"


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


class EvidenceExcerpt(_DomainModel):
    evidence_id: str = Field(min_length=1)
    source: EvidenceSource
    excerpt: str = Field(min_length=1, max_length=2000)
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _time_range(self) -> EvidenceExcerpt:
        if self.start_seconds is not None and self.end_seconds is not None:
            if self.end_seconds < self.start_seconds:
                msg = "end_seconds must be >= start_seconds"
                raise ValueError(msg)
        return self


class AnalysisPoint(_DomainModel):
    text: str = Field(min_length=1, max_length=2000)
    kind: PointKind
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=10)

    @field_validator("evidence_ids")
    @classmethod
    def _unique_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            msg = "evidence_ids must be unique"
            raise ValueError(msg)
        for eid in value:
            if not eid:
                msg = "evidence_ids items must be non-empty"
                raise ValueError(msg)
        return value


class AnalysisResult(_DomainModel):
    schema_version: str = Field(min_length=1)
    one_sentence_summary: str = Field(min_length=1, max_length=500)
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
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    request_hash: str = Field(min_length=1)

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
            if not 1 <= len(kw) <= 80:
                msg = "each keyword must have length 1..80"
                raise ValueError(msg)
            if kw in seen:
                msg = "keywords must be unique"
                raise ValueError(msg)
            seen.add(kw)
        return value

    @model_validator(mode="after")
    def _cross_field_integrity(self) -> AnalysisResult:
        evidence_ids = {item.evidence_id for item in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            msg = "evidence_id values must be unique within AnalysisResult"
            raise ValueError(msg)

        for point in self.key_facts:
            if point.kind is not PointKind.FACT:
                msg = "key_facts items must have kind=fact"
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


class ScoringInput(_DomainModel):
    video: VideoMetadata
    transcript_text: str
    transcript_content_hash: str = Field(min_length=1)
    language: str = Field(min_length=1)
    request_hash: str = Field(min_length=1)


class AnalysisInput(_DomainModel):
    video: VideoMetadata
    transcript_text: str
    transcript_content_hash: str = Field(min_length=1)
    score: ScoreResult
    language: str = Field(min_length=1)
    request_hash: str = Field(min_length=1)


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


class NoteRef(_DomainModel):
    kind: NoteKind
    relative_path: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)

    @field_validator("relative_path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        from pathlib import Path, PurePosixPath

        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or any(part == ".." for part in path.parts):
            msg = "relative_path must be a safe relative path under the vault"
            raise ValueError(msg)
        if not value or value.strip() != value:
            msg = "relative_path must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        # Reject empty path components that collapse oddly
        if Path(value).is_absolute():
            msg = "relative_path must not be absolute"
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
        video: VideoMetadata,
        transcript: TranscriptArtifact,
        score: ScoreResult,
        analysis: AnalysisResult | None,
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
    "EvidenceExcerpt",
    "AnalysisPoint",
    "AnalysisResult",
    "DiagnosticEntry",
    "ProviderCallMetadata",
    "DiscoveryCursor",
    "DiscoveryBatch",
    "ScoringInput",
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
