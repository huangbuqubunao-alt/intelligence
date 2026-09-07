"""SQLite state repository with explicit migrations and transaction boundaries."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Final, cast

from youtube_intel.domain import (
    Availability,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
    transition_pipeline,
)
from youtube_intel.orchestration import (
    AutomationRunStatus,
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    SourceType,
)

#: The sole post-migration scoring lineage generation (schema v2).  Every
#: post-migration SCORING Job receives exactly this literal at creation; the
#: repository derives it internally and callers cannot submit a version.
SCORING_LINEAGE_VERSION_V1: Final = "task016c-scoring-lineage-v1"


class StateStoreError(Exception):
    """Base error for safe state-store failures."""


class MigrationError(StateStoreError):
    """Raised when migration history or application is invalid."""


class ConcurrencyConflict(StateStoreError):
    """Raised when an expected-state compare-and-swap is stale."""


class IntegrityConflict(StateStoreError):
    """Raised when a repository uniqueness or integrity rule is violated."""


class LeaseConflict(StateStoreError):
    """Raised when a worker no longer owns a live lease."""


class JobType(str, Enum):
    CHANNEL_DISCOVERY = "CHANNEL_DISCOVERY"
    VIDEO_STAGE = "VIDEO_STAGE"
    WEEKLY_REPORT = "WEEKLY_REPORT"


class JobAttemptOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    RETRY_PENDING = "RETRY_PENDING"
    FAILED_FINAL = "FAILED_FINAL"
    LEASE_EXPIRED = "LEASE_EXPIRED"


class ArtifactKind(str, Enum):
    SUBTITLE_SOURCE = "subtitle_source"
    TRANSCRIPT_CANONICAL = "transcript_canonical"
    AUDIO = "audio"
    SCORING_RAW = "scoring_raw"
    SCORING_STRUCTURED = "scoring_structured"
    ANALYSIS_RAW = "analysis_raw"
    ANALYSIS_STRUCTURED = "analysis_structured"
    VIDEO_NOTE = "video_note"
    WEEKLY_REPORT = "weekly_report"


class StorageRoot(str, Enum):
    DATA = "DATA"
    VAULT = "VAULT"


class RetentionClass(str, Enum):
    EPHEMERAL_AUDIO = "EPHEMERAL_AUDIO"
    RAW_RESPONSE_30D = "RAW_RESPONSE_30D"
    LONG_LIVED = "LONG_LIVED"


class ProviderCallStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"


class ProviderDispatchStatus(str, Enum):
    """Durable evidence about one cloud request's external dispatch boundary.

    ``AMBIGUOUS`` is deliberately terminal for automatic recovery.  It means a
    process stopped after it had durably authorized a cloud request, but before
    the local success receipt became durable; SQLite cannot prove whether the
    provider acted.
    """

    NOT_DISPATCHED = "NOT_DISPATCHED"
    DISPATCH_INTENT_DURABLE = "DISPATCH_INTENT_DURABLE"
    DISPATCHED_RESULT_UNKNOWN = "DISPATCHED_RESULT_UNKNOWN"
    SUCCESS_DURABLY_RECORDED = "SUCCESS_DURABLY_RECORDED"
    FAILED_KNOWN = "FAILED_KNOWN"
    AMBIGUOUS = "AMBIGUOUS"


class ReportStatus(str, Enum):
    PENDING = "PENDING"
    WRITTEN = "WRITTEN"


class EvidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DELETED = "DELETED"


class EvidenceLineageKind(str, Enum):
    ORIGINAL_TRANSCRIPT = "ORIGINAL_TRANSCRIPT"
    TRANSLATION = "TRANSLATION"
    EXTRACTION = "EXTRACTION"


class EvidenceRole(str, Enum):
    PRIMARY_ORIGINAL = "PRIMARY_ORIGINAL"
    INDEPENDENT_VERIFICATION = "INDEPENDENT_VERIFICATION"
    ANALYSIS_COMMENTARY = "ANALYSIS_COMMENTARY"
    SECONDARY_RELAY = "SECONDARY_RELAY"


class IntelligenceInterpretationKind(str, Enum):
    DISTILLATION = "DISTILLATION"
    SYNTHESIS = "SYNTHESIS"
    CORRECTION = "CORRECTION"


class IntelligenceClaimKind(str, Enum):
    """Finite semantic classification carried by one immutable revision."""

    UNCLASSIFIED = "UNCLASSIFIED"
    FACT = "FACT"
    EVIDENCE_BACKED_STATEMENT = "EVIDENCE_BACKED_STATEMENT"
    OPINION = "OPINION"
    PREDICTION = "PREDICTION"
    RUMOR = "RUMOR"
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"


class IntelligenceState(str, Enum):
    NEW = "NEW"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    UPDATED = "UPDATED"
    INVALIDATED = "INVALIDATED"
    OVERTURNED = "OVERTURNED"


class DependencyRelation(str, Enum):
    EVIDENCE_SUPPORT = "EVIDENCE_SUPPORT"
    REVISION_SUPERSEDES = "REVISION_SUPERSEDES"


class PreferenceHorizon(str, Enum):
    LONG_TERM = "LONG_TERM"
    RECENT = "RECENT"
    TEMPORARY_FOCUS = "TEMPORARY_FOCUS"


class PreferenceProvenance(str, Enum):
    EXPLICIT = "EXPLICIT"
    DERIVED = "DERIVED"
    TEMPORARY = "TEMPORARY"


class PreferenceScope(str, Enum):
    GLOBAL_CONTENT = "GLOBAL_CONTENT"
    SOURCE_CONTENT = "SOURCE_CONTENT"
    VIDEO_CONTENT = "VIDEO_CONTENT"
    INTELLIGENCE_CONTENT = "INTELLIGENCE_CONTENT"
    DISTILLATION_STYLE = "DISTILLATION_STYLE"


class PreferenceState(str, Enum):
    ACTIVATED = "ACTIVATED"
    REPLACED = "REPLACED"
    DELETED = "DELETED"


class FeedbackKind(str, Enum):
    MORE_LIKE_THIS = "MORE_LIKE_THIS"
    LESS_LIKE_THIS = "LESS_LIKE_THIS"
    IMPORTANT = "IMPORTANT"
    NATURAL_LANGUAGE = "NATURAL_LANGUAGE"
    EXPLICIT_PREFERENCE_STATEMENT = "EXPLICIT_PREFERENCE_STATEMENT"
    FACTUAL_CORRECTION = "FACTUAL_CORRECTION"


class FeedbackCorrectionKind(str, Enum):
    WRONG_INTERPRETATION = "WRONG_INTERPRETATION"
    SOURCE_UNSUPPORTED = "SOURCE_UNSUPPORTED"
    OUTDATED = "OUTDATED"
    VIEWPOINTS_MERGED = "VIEWPOINTS_MERGED"
    OTHER = "OTHER"


class PolicyOverrideMode(str, Enum):
    """Whether a Source field inherits its global policy or replaces it."""

    INHERIT = "INHERIT"
    OVERRIDE = "OVERRIDE"


class DistillationStyle(str, Enum):
    """Finite V1 policy selection; TASK-022 owns actual distillation."""

    BALANCED = "BALANCED"
    TECHNICAL_DETAIL_FIRST = "TECHNICAL_DETAIL_FIRST"
    PRODUCT_CASE_FIRST = "PRODUCT_CASE_FIRST"
    TREND_OPINION_FIRST = "TREND_OPINION_FIRST"


class FilterStage(str, Enum):
    STAGE_1 = "STAGE_1"
    STAGE_2 = "STAGE_2"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class FilterOutcome(str, Enum):
    RELEVANT = "RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"
    UNCERTAIN = "UNCERTAIN"


class FilterReason(str, Enum):
    FOCUS_MATCH = "FOCUS_MATCH"
    IGNORE_RULE_MATCH = "IGNORE_RULE_MATCH"
    SHORT_VIDEO = "SHORT_VIDEO"
    NO_FOCUS_MATCH = "NO_FOCUS_MATCH"
    NO_FOCUS_RULES = "NO_FOCUS_RULES"
    INSUFFICIENT_METADATA = "INSUFFICIENT_METADATA"
    STAGE_TWO_REVIEW = "STAGE_TWO_REVIEW"
    MANUAL_ANALYZE = "MANUAL_ANALYZE"


@dataclass(frozen=True, slots=True)
class EvidenceWrite:
    evidence_id: str
    video_id: str
    artifact_id: str
    start_ms: int
    end_ms: int
    lineage_kind: EvidenceLineageKind
    role: EvidenceRole
    language: str
    availability: EvidenceAvailability


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    video_id: str
    artifact_id: str
    start_ms: int
    end_ms: int
    lineage_kind: EvidenceLineageKind
    role: EvidenceRole
    language: str
    availability: EvidenceAvailability
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IntelligenceRecord:
    intelligence_id: str
    current_revision_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IntelligenceRevisionWrite:
    revision_id: str
    interpretation_kind: IntelligenceInterpretationKind
    claim_kind: IntelligenceClaimKind
    content_hash: str
    state: IntelligenceState
    reason: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IntelligenceRevisionRecord:
    revision_id: str
    intelligence_id: str
    revision_number: int
    prior_revision_id: str | None
    interpretation_kind: IntelligenceInterpretationKind
    claim_kind: IntelligenceClaimKind
    content_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IntelligenceStateHistoryRecord:
    state_event_id: str
    intelligence_id: str
    revision_id: str
    state: IntelligenceState
    prior_state: IntelligenceState | None
    reason: str
    evidence_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PreferenceWrite:
    preference_id: str
    horizon: PreferenceHorizon
    provenance: PreferenceProvenance
    scope: PreferenceScope
    target_id: str | None
    statement: str
    starts_at: datetime | None
    expires_at: datetime | None
    supersedes_preference_id: str | None = None


@dataclass(frozen=True, slots=True)
class PreferenceRecord:
    preference_id: str
    horizon: PreferenceHorizon
    provenance: PreferenceProvenance
    scope: PreferenceScope
    target_id: str | None
    statement: str
    starts_at: datetime | None
    expires_at: datetime | None
    supersedes_preference_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PreferenceStateEventRecord:
    state_event_id: str
    preference_id: str
    state: PreferenceState
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FeedbackWrite:
    feedback_id: str
    kind: FeedbackKind
    scope: PreferenceScope
    target_id: str | None
    content: str | None
    correction_kind: FeedbackCorrectionKind | None


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    feedback_id: str
    kind: FeedbackKind
    scope: PreferenceScope
    target_id: str | None
    content: str | None
    correction_kind: FeedbackCorrectionKind | None
    effect_status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DependencyEdgeWrite:
    edge_id: str
    dependent_revision_id: str
    relation: DependencyRelation
    input_evidence_id: str | None
    input_revision_id: str | None


@dataclass(frozen=True, slots=True)
class DependencyEdgeRecord:
    edge_id: str
    dependent_revision_id: str
    relation: DependencyRelation
    input_evidence_id: str | None
    input_revision_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SourceSubscriptionRecord:
    source_id: str
    source_type: SourceType
    canonical_url: str
    channel_id: str | None
    video_id: str | None
    display_name: str | None
    enabled: bool
    processing_policy: ProcessingPolicy
    last_checked_at: datetime | None
    last_success_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SourcePolicyRevisionWrite:
    revision_id: str
    policy_scope: str
    source_id: str | None
    initial_history_count: int | None
    per_run_max_new_videos: int | None
    focus_mode: PolicyOverrideMode
    focus_rules: tuple[str, ...]
    ignore_mode: PolicyOverrideMode
    ignore_rules: tuple[str, ...]
    distillation_style_mode: PolicyOverrideMode
    distillation_style: DistillationStyle | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SourcePolicyRevisionRecord:
    revision_id: str
    policy_scope: str
    source_id: str | None
    initial_history_count: int | None
    per_run_max_new_videos: int | None
    focus_mode: PolicyOverrideMode
    focus_rules: tuple[str, ...]
    ignore_mode: PolicyOverrideMode
    ignore_rules: tuple[str, ...]
    distillation_style_mode: PolicyOverrideMode
    distillation_style: DistillationStyle | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FilterDecisionWrite:
    decision_id: str
    source_id: str
    video_id: str
    stage: FilterStage
    outcome: FilterOutcome
    reason: FilterReason
    global_policy_revision_id: str
    source_policy_revision_id: str | None
    manual_override_id: str | None
    prior_decision_id: str | None
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class FilterDecisionRecord:
    decision_id: str
    source_id: str
    video_id: str
    stage: FilterStage
    outcome: FilterOutcome
    reason: FilterReason
    global_policy_revision_id: str
    source_policy_revision_id: str | None
    manual_override_id: str | None
    prior_decision_id: str | None
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class ManualAnalyzeOverrideWrite:
    override_id: str
    source_id: str
    video_id: str
    command_id: str
    prior_decision_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AutomationScheduleRecord:
    schedule_id: str
    target_type: AutomationTargetType
    target_id: str | None
    frequency: ScheduleFrequency
    weekday: int | None
    local_time: str | None
    timezone: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AutomationRunRecord:
    run_id: str
    schedule_id: str
    target_type: AutomationTargetType
    target_id: str | None
    scheduled_for: datetime
    claimed_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    status: AutomationRunStatus
    error_code: str | None
    error_message: str | None
    result_summary: str | None


@dataclass(frozen=True, slots=True)
class GlobalModelPreferenceRecord:
    desired_provider: str | None
    desired_model: str | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class _Migration:
    version: int
    name: str
    sql: str
    checksum: str


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    version: int
    name: str
    checksum: str
    applied_at: datetime


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    foreign_keys: bool
    busy_timeout_ms: int
    synchronous: str
    journal_mode: str
    read_uncommitted: bool


@dataclass(frozen=True, slots=True)
class ChannelCursorRecord:
    channel_id: str
    last_checked_at: datetime | None
    latest_published_at: datetime | None
    latest_video_id: str | None
    provider_cursor: str | None
    last_error_code: str | None
    last_error_message: str | None
    revision: int
    updated_at: datetime

    def as_discovery_cursor(self) -> DiscoveryCursor:
        return DiscoveryCursor(
            channel_id=self.channel_id,
            last_checked_at=self.last_checked_at,
            latest_published_at=self.latest_published_at,
            latest_video_id=self.latest_video_id,
            provider_cursor=self.provider_cursor,
        )


@dataclass(frozen=True, slots=True)
class VideoRecord:
    video_id: str
    channel_id: str
    channel_name: str | None
    title: str | None
    description: str | None
    source_url: str | None
    published_at: datetime | None
    duration_seconds: int | None
    default_language: str | None
    available_languages: tuple[str, ...]
    live_status: LiveStatus | None
    availability: Availability | None
    pipeline_status: PipelineStatus
    pipeline_version: str
    score: float | None
    should_summarize: bool | None
    discovered_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    authoritative_scoring_job_id: str | None = None


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    scope_key: str
    video_id: str | None
    job_type: JobType
    target_stage: ProcessingStage
    pipeline_version: str
    status: JobStatus
    attempt_count: int
    max_attempts: int
    available_at: datetime
    lease_owner: str | None
    lease_until: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    authoritative_scoring_artifact_key: str | None = None
    scoring_success_provenance: str | None = None
    scoring_lineage_version: str | None = None


def _release_terminal_scoring_admission(
    repository: SQLiteStateRepository, job: JobRecord
) -> None:
    """Drop H1 runtime-only admission state after a committed scoring terminal."""

    if job.target_stage is not ProcessingStage.SCORING or job.status not in {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED_FINAL,
    }:
        return
    # Keep state persistence independent: this only releases process-local H1 state
    # after the SQLite transaction has committed.
    from youtube_intel.scoring_admission import ScoringAdmissionRegistry

    ScoringAdmissionRegistry.release_terminal(
        repository=repository,
        job_id=job.job_id,
        attempt_count=job.attempt_count,
    )


@dataclass(frozen=True, slots=True)
class JobAttemptRecord:
    attempt_id: int
    job_id: str
    attempt_number: int
    lease_owner: str
    started_at: datetime
    lease_until: datetime
    finished_at: datetime | None
    outcome: JobAttemptOutcome | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class ArtifactWrite:
    artifact_id: str
    artifact_key: str
    video_id: str | None
    job_id: str | None
    kind: ArtifactKind
    storage_root: StorageRoot
    relative_path: str
    content_hash: str
    provider: str | None
    model: str | None
    producer_version: str
    retention_class: RetentionClass
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    artifact_key: str
    video_id: str | None
    job_id: str | None
    kind: ArtifactKind
    storage_root: StorageRoot
    relative_path: str
    content_hash: str
    provider: str | None
    model: str | None
    producer_version: str
    retention_class: RetentionClass
    created_at: datetime
    expires_at: datetime | None
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProviderCallRequest:
    operation: str
    normalized_input_hash: str
    provider: str
    model: str | None
    prompt_version: str | None
    schema_version: str | None
    deterministic_artifact_key: str

    @property
    def request_hash(self) -> str:
        return build_provider_request_hash(
            operation=self.operation,
            normalized_input_hash=self.normalized_input_hash,
            provider=self.provider,
            model=self.model,
            prompt_version=self.prompt_version,
            schema_version=self.schema_version,
        )


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    artifact_key: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class ProviderCallRecord:
    request_hash: str
    operation: str
    provider: str
    model: str | None
    prompt_version: str | None
    schema_version: str | None
    status: ProviderCallStatus
    reservation_owner: str | None
    lease_until: datetime | None
    available_at: datetime
    attempt_count: int
    response_artifact_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_microusd: int | None
    last_error_code: str | None
    last_error_message: str | None
    started_at: datetime
    finished_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderDispatchRecord:
    request_hash: str
    status: ProviderDispatchStatus
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderReservation:
    record: ProviderCallRecord
    acquired: bool
    recovered_from_artifact: bool


@dataclass(frozen=True, slots=True)
class ProviderCallCompletion:
    request_hash: str
    response_artifact_id: str
    input_tokens: int | None
    output_tokens: int | None
    cost_microusd: int | None


@dataclass(frozen=True, slots=True)
class ScoringSummaryWrite:
    """Final application decision persisted only with SCORING stage completion."""

    score: float
    should_summarize: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(self.score)
            or not 0 <= self.score <= 10
        ):
            msg = "score must be a finite value in 0..10"
            raise ValueError(msg)
        if not isinstance(self.should_summarize, bool):
            msg = "should_summarize must be a bool"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ReportWrite:
    report_id: str
    timezone: str
    iso_year: int
    iso_week: int
    relative_path: str | None
    content_hash: str | None
    status: ReportStatus


@dataclass(frozen=True, slots=True)
class ReportRecord:
    report_id: str
    timezone: str
    iso_year: int
    iso_week: int
    report_type: str
    relative_path: str | None
    content_hash: str | None
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyCandidateRecord:
    """Repository-selected inputs that a weekly report must verify locally."""

    video: VideoRecord
    score_artifact: ArtifactRecord
    analysis_artifact: ArtifactRecord | None
    note_artifact: ArtifactRecord


@dataclass(frozen=True, slots=True)
class StageCompletionResult:
    job: JobRecord
    video: VideoRecord
    artifacts: tuple[ArtifactRecord, ...]
    provider_call: ProviderCallRecord | None


def format_utc_datetime(value: datetime) -> str:
    """Return ADR-003's fixed-width UTC RFC 3339 representation."""

    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        msg = "value must be a UTC datetime"
        raise ValueError(msg)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")


def _latest_weekly_artifact(
    connection: sqlite3.Connection, video_id: str, kind: ArtifactKind
) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            "SELECT * FROM artifacts WHERE video_id = :video_id AND kind = :kind "
            "AND storage_root = :root AND deleted_at IS NULL "
            "ORDER BY created_at DESC, artifact_id ASC LIMIT 1",
            {
                "video_id": video_id,
                "kind": kind.value,
                "root": StorageRoot.DATA.value,
            },
        ).fetchone(),
    )


def _safe_error_message(value: str) -> str:
    first_line = value.splitlines()[0] if value.splitlines() else ""
    redacted = re.sub(
        r"(?i)\bBearer\s+\S+",
        "Bearer [REDACTED]",
        first_line,
    )
    redacted = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|authorization)\b\s*[:=]?\s*\S+",
        r"\1=[REDACTED]",
        redacted,
    )
    redacted = re.sub(r"(?<!:)\b/(?:[^\s]+)", "[PATH]", redacted)
    return " ".join(redacted.split())[:500]


def _validate_sha256(value: str, *, field_name: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        msg = f"{field_name} must be a lowercase SHA-256 hexadecimal value"
        raise ValueError(msg)


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or value.startswith("~")
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        msg = "artifact and report paths must be safe relative paths"
        raise ValueError(msg)


def build_provider_request_hash(
    *,
    operation: str,
    normalized_input_hash: str,
    provider: str,
    model: str | None,
    prompt_version: str | None,
    schema_version: str | None,
) -> str:
    """Build the canonical ADR-003 provider-call cache key."""

    if not operation.strip() or not provider.strip():
        msg = "provider call operation and provider must be non-empty"
        raise ValueError(msg)
    _validate_sha256(normalized_input_hash, field_name="normalized_input_hash")
    canonical = json.dumps(
        [
            operation,
            normalized_input_hash,
            provider,
            model,
            prompt_version,
            schema_version,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_evidence_id(
    *,
    video_id: str,
    artifact_id: str,
    start_ms: int,
    end_ms: int,
    lineage_kind: EvidenceLineageKind,
    role: EvidenceRole,
) -> str:
    """Build the stable identity for one precise, source-bound evidence span."""

    if not video_id.strip() or not artifact_id.strip():
        raise ValueError("evidence provenance identities must be non-empty")
    if start_ms < 0 or end_ms < start_ms:
        raise ValueError("evidence timestamp range is invalid")
    canonical = json.dumps(
        [
            video_id,
            artifact_id,
            start_ms,
            end_ms,
            lineage_kind.value,
            role.value,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _processing_stage_for_transition(
    current: PipelineStatus,
    target: PipelineStatus,
) -> ProcessingStage:
    if target in {
        PipelineStatus.METADATA_READY,
        PipelineStatus.DEFERRED,
        PipelineStatus.SKIPPED_DURATION_LIMIT,
    }:
        return ProcessingStage.METADATA
    if target is PipelineStatus.TRANSCRIPT_READY:
        return ProcessingStage.TRANSCRIPT
    if target in {PipelineStatus.SCORED, PipelineStatus.LOW_VALUE_READY}:
        return ProcessingStage.SCORING
    if target is PipelineStatus.ANALYSIS_READY:
        return ProcessingStage.ANALYSIS
    if target is PipelineStatus.NOTE_WRITTEN:
        return ProcessingStage.NOTE_WRITE
    if target is PipelineStatus.COMPLETE:
        return (
            ProcessingStage.SCORING
            if current is PipelineStatus.LOW_VALUE_READY
            else ProcessingStage.NOTE_WRITE
        )
    msg = "pipeline transition has no processing stage"
    raise ValueError(msg)


def _migration_statements(sql: str) -> Iterator[str]:
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                yield statement
            buffer = ""
    if buffer.strip():
        msg = "migration contains an incomplete SQL statement"
        raise MigrationError(msg)


@contextmanager
def _immediate_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()


class SQLiteStateRepository:
    """Owns the approved SQLite schema and repository transaction semantics."""

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self._database_path = Path(database_path)

    def _inject_failure(self, point: str) -> None:
        """Test seam for proving transaction rollback at named boundaries."""

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            isolation_level=None,
            timeout=5.0,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA synchronous = NORMAL")
            settings = self._read_database_settings(connection)
            if (
                not settings.foreign_keys
                or settings.busy_timeout_ms != 5000
                or settings.synchronous != "NORMAL"
                or settings.read_uncommitted
            ):
                msg = "required SQLite connection settings could not be verified"
                raise StateStoreError(msg)
        except BaseException:
            connection.close()
            raise
        return connection

    @staticmethod
    def _read_database_settings(connection: sqlite3.Connection) -> DatabaseSettings:
        synchronous_codes = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}
        foreign_keys = int(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        busy_timeout = int(connection.execute("PRAGMA busy_timeout").fetchone()[0])
        synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        read_uncommitted = int(
            connection.execute("PRAGMA read_uncommitted").fetchone()[0]
        )
        return DatabaseSettings(
            foreign_keys=foreign_keys == 1,
            busy_timeout_ms=busy_timeout,
            synchronous=synchronous_codes.get(synchronous, f"UNKNOWN-{synchronous}"),
            journal_mode=journal_mode.upper(),
            read_uncommitted=read_uncommitted == 1,
        )

    def _load_migrations(self) -> tuple[_Migration, ...]:
        names = (
            "001_initial.sql",
            "002_add_scoring_lineage.sql",
            "003_add_deep_analysis_persistence.sql",
            "004_add_provider_dispatch_state.sql",
            "005_add_product_orchestration.sql",
            "006_add_intelligence_domain.sql",
            "007_add_intelligence_claim_classification.sql",
            "008_add_preference_feedback.sql",
            "009_add_source_policy_filtering.sql",
        )
        migrations: list[_Migration] = []
        for version, name in enumerate(names, start=1):
            sql_bytes = (
                resources.files("youtube_intel")
                .joinpath("migrations", name)
                .read_bytes()
            )
            migrations.append(
                _Migration(
                    version=version,
                    name=name,
                    sql=sql_bytes.decode("utf-8"),
                    checksum=hashlib.sha256(sql_bytes).hexdigest(),
                )
            )
        return tuple(migrations)

    @staticmethod
    def _history_rows(connection: sqlite3.Connection) -> tuple[sqlite3.Row, ...]:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("schema_migrations",),
        ).fetchone()
        if table_exists is None:
            return ()
        return tuple(
            connection.execute(
                "SELECT version, name, checksum, applied_at "
                "FROM schema_migrations ORDER BY version"
            )
        )

    @staticmethod
    def _verify_history(
        connection: sqlite3.Connection,
        migrations: tuple[_Migration, ...],
    ) -> tuple[sqlite3.Row, ...]:
        try:
            rows = SQLiteStateRepository._history_rows(connection)
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        except sqlite3.Error as error:
            msg = "migration history mismatch: unreadable migration metadata"
            raise MigrationError(msg) from error

        if len(rows) > len(migrations):
            msg = "migration history mismatch: database version is unsupported"
            raise MigrationError(msg)
        for index, row in enumerate(rows):
            migration = migrations[index]
            if (
                row["version"] != migration.version
                or row["name"] != migration.name
                or row["checksum"] != migration.checksum
            ):
                msg = "migration history mismatch: version, name, or checksum differs"
                raise MigrationError(msg)
        expected_user_version = int(rows[-1]["version"]) if rows else 0
        if user_version != expected_user_version:
            msg = "migration history mismatch: PRAGMA user_version differs"
            raise MigrationError(msg)
        return rows

    def initialize(self, *, now: datetime) -> SchemaVersion:
        applied_at = format_utc_datetime(now)
        migrations = self._load_migrations()
        connection = self._connect()
        try:
            journal_mode = str(
                connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            )
            if journal_mode.upper() != "WAL":
                msg = "file database did not enable WAL journal mode"
                raise MigrationError(msg)
            rows = self._verify_history(connection, migrations)
            for migration in migrations[len(rows) :]:
                try:
                    with _immediate_transaction(connection):
                        for statement in _migration_statements(migration.sql):
                            connection.execute(statement)
                        connection.execute(
                            "INSERT INTO schema_migrations "
                            "(version, name, checksum, applied_at) "
                            "VALUES (:version, :name, :checksum, :applied_at)",
                            {
                                "version": migration.version,
                                "name": migration.name,
                                "checksum": migration.checksum,
                                "applied_at": applied_at,
                            },
                        )
                        connection.execute(f"PRAGMA user_version = {migration.version}")
                except (sqlite3.Error, MigrationError) as error:
                    msg = f"failed to apply migration {migration.version}"
                    raise MigrationError(msg) from error
            self._verify_history(connection, migrations)
            version = self._schema_version(connection)
            if version is None:
                msg = "migration history mismatch: no applied migration"
                raise MigrationError(msg)
            return version
        finally:
            connection.close()

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> SchemaVersion | None:
        rows = SQLiteStateRepository._history_rows(connection)
        if not rows:
            return None
        row = rows[-1]
        return SchemaVersion(
            version=int(row["version"]),
            name=str(row["name"]),
            checksum=str(row["checksum"]),
            applied_at=_parse_utc_datetime(str(row["applied_at"])),
        )

    def schema_version(self) -> SchemaVersion | None:
        connection = self._connect()
        try:
            return self._schema_version(connection)
        finally:
            connection.close()

    def database_settings(self) -> DatabaseSettings:
        connection = self._connect()
        try:
            return self._read_database_settings(connection)
        finally:
            connection.close()

    @staticmethod
    def _optional_datetime(value: object) -> datetime | None:
        return None if value is None else _parse_utc_datetime(str(value))

    @staticmethod
    def _cursor_from_row(row: sqlite3.Row) -> ChannelCursorRecord:
        return ChannelCursorRecord(
            channel_id=str(row["channel_id"]),
            last_checked_at=SQLiteStateRepository._optional_datetime(
                row["last_checked_at"]
            ),
            latest_published_at=SQLiteStateRepository._optional_datetime(
                row["latest_published_at"]
            ),
            latest_video_id=row["latest_video_id"],
            provider_cursor=row["provider_cursor"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            revision=int(row["revision"]),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _video_from_row(row: sqlite3.Row) -> VideoRecord:
        languages = json.loads(str(row["available_languages_json"]))
        if not isinstance(languages, list) or not all(
            isinstance(language, str) for language in languages
        ):
            msg = "stored available languages are invalid"
            raise StateStoreError(msg)
        return VideoRecord(
            video_id=str(row["video_id"]),
            channel_id=str(row["channel_id"]),
            channel_name=row["channel_name"],
            title=row["title"],
            description=row["description"],
            source_url=row["source_url"],
            published_at=SQLiteStateRepository._optional_datetime(row["published_at"]),
            duration_seconds=row["duration_seconds"],
            default_language=row["default_language"],
            available_languages=tuple(languages),
            live_status=(
                None if row["live_status"] is None else LiveStatus(row["live_status"])
            ),
            availability=(
                None
                if row["availability"] is None
                else Availability(row["availability"])
            ),
            pipeline_status=PipelineStatus(row["pipeline_status"]),
            pipeline_version=str(row["pipeline_version"]),
            score=row["score"],
            should_summarize=(
                None
                if row["should_summarize"] is None
                else bool(row["should_summarize"])
            ),
            discovered_at=_parse_utc_datetime(str(row["discovered_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
            completed_at=SQLiteStateRepository._optional_datetime(row["completed_at"]),
            authoritative_scoring_job_id=row["authoritative_scoring_job_id"],
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=str(row["job_id"]),
            scope_key=str(row["scope_key"]),
            video_id=row["video_id"],
            job_type=JobType(row["job_type"]),
            target_stage=ProcessingStage(row["target_stage"]),
            pipeline_version=str(row["pipeline_version"]),
            status=JobStatus(row["status"]),
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            available_at=_parse_utc_datetime(str(row["available_at"])),
            lease_owner=row["lease_owner"],
            lease_until=SQLiteStateRepository._optional_datetime(row["lease_until"]),
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
            authoritative_scoring_artifact_key=row[
                "authoritative_scoring_artifact_key"
            ],
            scoring_success_provenance=row["scoring_success_provenance"],
            scoring_lineage_version=row["scoring_lineage_version"],
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> JobAttemptRecord:
        return JobAttemptRecord(
            attempt_id=int(row["attempt_id"]),
            job_id=str(row["job_id"]),
            attempt_number=int(row["attempt_number"]),
            lease_owner=str(row["lease_owner"]),
            started_at=_parse_utc_datetime(str(row["started_at"])),
            lease_until=_parse_utc_datetime(str(row["lease_until"])),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
            outcome=(
                None if row["outcome"] is None else JobAttemptOutcome(row["outcome"])
            ),
            error_code=row["error_code"],
            error_message=row["error_message"],
        )

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=str(row["artifact_id"]),
            artifact_key=str(row["artifact_key"]),
            video_id=row["video_id"],
            job_id=row["job_id"],
            kind=ArtifactKind(row["kind"]),
            storage_root=StorageRoot(row["storage_root"]),
            relative_path=str(row["relative_path"]),
            content_hash=str(row["content_hash"]),
            provider=row["provider"],
            model=row["model"],
            producer_version=str(row["producer_version"]),
            retention_class=RetentionClass(row["retention_class"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            expires_at=SQLiteStateRepository._optional_datetime(row["expires_at"]),
            deleted_at=SQLiteStateRepository._optional_datetime(row["deleted_at"]),
        )

    @staticmethod
    def _provider_call_from_row(row: sqlite3.Row) -> ProviderCallRecord:
        return ProviderCallRecord(
            request_hash=str(row["request_hash"]),
            operation=str(row["operation"]),
            provider=str(row["provider"]),
            model=row["model"],
            prompt_version=row["prompt_version"],
            schema_version=row["schema_version"],
            status=ProviderCallStatus(row["status"]),
            reservation_owner=row["reservation_owner"],
            lease_until=SQLiteStateRepository._optional_datetime(row["lease_until"]),
            available_at=_parse_utc_datetime(str(row["available_at"])),
            attempt_count=int(row["attempt_count"]),
            response_artifact_id=row["response_artifact_id"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cost_microusd=row["cost_microusd"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            started_at=_parse_utc_datetime(str(row["started_at"])),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _provider_dispatch_from_row(row: sqlite3.Row) -> ProviderDispatchRecord:
        return ProviderDispatchRecord(
            request_hash=str(row["request_hash"]),
            status=ProviderDispatchStatus(row["status"]),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _report_from_row(row: sqlite3.Row) -> ReportRecord:
        return ReportRecord(
            report_id=str(row["report_id"]),
            timezone=str(row["timezone"]),
            iso_year=int(row["iso_year"]),
            iso_week=int(row["iso_week"]),
            report_type=str(row["report_type"]),
            relative_path=row["relative_path"],
            content_hash=row["content_hash"],
            status=ReportStatus(row["status"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    def get_channel_cursor(self, channel_id: str) -> ChannelCursorRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM channel_cursors WHERE channel_id = :channel_id",
                {"channel_id": channel_id},
            ).fetchone()
            return None if row is None else self._cursor_from_row(row)
        finally:
            connection.close()

    @staticmethod
    def _cursor_matches(
        current: ChannelCursorRecord | None,
        expected_cursor: DiscoveryCursor | None,
        expected_revision: int,
    ) -> bool:
        if current is None:
            return expected_cursor is None and expected_revision == 0
        return (
            expected_cursor is not None
            and current.revision == expected_revision
            and current.as_discovery_cursor() == expected_cursor
        )

    def save_discovery_batch(
        self,
        batch: DiscoveryBatch,
        *,
        expected_cursor: DiscoveryCursor | None,
        expected_revision: int,
        pipeline_version: str,
        now: datetime,
    ) -> ChannelCursorRecord:
        if batch.next_cursor.channel_id != batch.channel_id:
            msg = "discovery batch and next cursor channel differ"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM channel_cursors WHERE channel_id = :channel_id",
                    {"channel_id": batch.channel_id},
                ).fetchone()
                current = None if row is None else self._cursor_from_row(row)
                if not self._cursor_matches(
                    current, expected_cursor, expected_revision
                ):
                    msg = "channel cursor changed before discovery batch commit"
                    raise ConcurrencyConflict(msg)
                for video_id in batch.video_ids:
                    connection.execute(
                        "INSERT INTO videos "
                        "(video_id, channel_id, pipeline_status, pipeline_version, "
                        "discovered_at, updated_at) "
                        "VALUES (:video_id, :channel_id, :pipeline_status, "
                        ":pipeline_version, :discovered_at, :updated_at) "
                        "ON CONFLICT(video_id) DO NOTHING",
                        {
                            "video_id": video_id,
                            "channel_id": batch.channel_id,
                            "pipeline_status": PipelineStatus.DISCOVERED.value,
                            "pipeline_version": pipeline_version,
                            "discovered_at": now_text,
                            "updated_at": now_text,
                        },
                    )
                self._inject_failure("discovery.after_candidates")
                cursor = batch.next_cursor
                if current is None:
                    connection.execute(
                        "INSERT INTO channel_cursors "
                        "(channel_id, last_checked_at, latest_published_at, "
                        "latest_video_id, provider_cursor, revision, updated_at) "
                        "VALUES (:channel_id, :last_checked_at, :latest_published_at, "
                        ":latest_video_id, :provider_cursor, 1, :updated_at)",
                        {
                            "channel_id": batch.channel_id,
                            "last_checked_at": (
                                None
                                if cursor.last_checked_at is None
                                else format_utc_datetime(cursor.last_checked_at)
                            ),
                            "latest_published_at": (
                                None
                                if cursor.latest_published_at is None
                                else format_utc_datetime(cursor.latest_published_at)
                            ),
                            "latest_video_id": cursor.latest_video_id,
                            "provider_cursor": cursor.provider_cursor,
                            "updated_at": now_text,
                        },
                    )
                else:
                    changed = connection.execute(
                        "UPDATE channel_cursors SET "
                        "last_checked_at = :last_checked_at, "
                        "latest_published_at = :latest_published_at, "
                        "latest_video_id = :latest_video_id, "
                        "provider_cursor = :provider_cursor, "
                        "last_error_code = NULL, last_error_message = NULL, "
                        "revision = revision + 1, updated_at = :updated_at "
                        "WHERE channel_id = :channel_id AND revision = :revision",
                        {
                            "channel_id": batch.channel_id,
                            "last_checked_at": (
                                None
                                if cursor.last_checked_at is None
                                else format_utc_datetime(cursor.last_checked_at)
                            ),
                            "latest_published_at": (
                                None
                                if cursor.latest_published_at is None
                                else format_utc_datetime(cursor.latest_published_at)
                            ),
                            "latest_video_id": cursor.latest_video_id,
                            "provider_cursor": cursor.provider_cursor,
                            "updated_at": now_text,
                            "revision": expected_revision,
                        },
                    ).rowcount
                    if changed != 1:
                        msg = "channel cursor changed before discovery batch commit"
                        raise ConcurrencyConflict(msg)
                saved = connection.execute(
                    "SELECT * FROM channel_cursors WHERE channel_id = :channel_id",
                    {"channel_id": batch.channel_id},
                ).fetchone()
                if saved is None:
                    msg = "channel cursor was not saved"
                    raise StateStoreError(msg)
                return self._cursor_from_row(saved)
        finally:
            connection.close()

    def get_video(self, video_id: str) -> VideoRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM videos WHERE video_id = :video_id",
                {"video_id": video_id},
            ).fetchone()
            return None if row is None else self._video_from_row(row)
        finally:
            connection.close()

    def list_videos_for_processing(
        self,
        *,
        pipeline_version: str,
        limit: int = 100,
    ) -> tuple[VideoRecord, ...]:
        """Return stable non-terminal video work without changing state."""

        if not pipeline_version.strip() or limit <= 0 or limit > 1000:
            raise ValueError("processing query arguments are invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM videos WHERE pipeline_version = :pipeline_version "
                "AND pipeline_status NOT IN (:complete, :duration_limit) "
                "ORDER BY discovered_at, video_id LIMIT :limit",
                {
                    "pipeline_version": pipeline_version,
                    "complete": PipelineStatus.COMPLETE.value,
                    "duration_limit": PipelineStatus.SKIPPED_DURATION_LIMIT.value,
                    "limit": limit,
                },
            ).fetchall()
            return tuple(self._video_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_videos(self, *, limit: int = 200) -> tuple[VideoRecord, ...]:
        if limit <= 0 or limit > 1000:
            raise ValueError("video list limit is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM videos ORDER BY updated_at DESC, video_id LIMIT :limit",
                {"limit": limit},
            ).fetchall()
            return tuple(self._video_from_row(row) for row in rows)
        finally:
            connection.close()

    def latest_video_job(
        self,
        video_id: str,
        *,
        target_stage: ProcessingStage | None = None,
    ) -> JobRecord | None:
        """Return the newest video-stage Job for user feedback."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM jobs WHERE video_id = :video_id "
                "AND job_type = :job_type "
                "AND (:target_stage IS NULL OR target_stage = :target_stage) "
                "ORDER BY updated_at DESC, "
                "CASE WHEN status = :succeeded THEN 1 ELSE 0 END, "
                "job_id DESC LIMIT 1",
                {
                    "video_id": video_id,
                    "job_type": JobType.VIDEO_STAGE.value,
                    "succeeded": JobStatus.SUCCEEDED.value,
                    "target_stage": (
                        None if target_stage is None else target_stage.value
                    ),
                },
            ).fetchone()
            return None if row is None else self._job_from_row(row)
        finally:
            connection.close()

    def list_video_jobs(
        self, video_id: str, *, limit: int = 100
    ) -> tuple[JobRecord, ...]:
        """Return persisted lifecycle records for one video without mutation."""

        if not video_id.strip() or limit <= 0 or limit > 1000:
            raise ValueError("video job query arguments are invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE video_id = :video_id "
                "ORDER BY created_at, job_id LIMIT :limit",
                {"video_id": video_id, "limit": limit},
            ).fetchall()
            return tuple(self._job_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_failed_video_jobs(self, *, limit: int = 100) -> tuple[JobRecord, ...]:
        """Return one newest final failure per video in stable order."""

        if limit <= 0 or limit > 1000:
            raise ValueError("failed job query limit is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT j.* FROM jobs AS j WHERE j.job_type = :job_type "
                "AND j.status = :failed AND j.video_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM jobs AS newer "
                "WHERE newer.video_id = j.video_id AND newer.job_type = :job_type "
                "AND newer.status = :failed "
                "AND (newer.updated_at > j.updated_at OR "
                "(newer.updated_at = j.updated_at AND newer.job_id > j.job_id))) "
                "ORDER BY j.updated_at, j.job_id LIMIT :limit",
                {
                    "job_type": JobType.VIDEO_STAGE.value,
                    "failed": JobStatus.FAILED_FINAL.value,
                    "limit": limit,
                },
            ).fetchall()
            return tuple(self._job_from_row(row) for row in rows)
        finally:
            connection.close()

    def transcript_refresh_generation(self, video_id: str) -> int:
        """Return the durable refresh generation after final transcript failures."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE video_id = :video_id "
                "AND job_type = :job_type AND target_stage = :target_stage "
                "AND status = :failed",
                {
                    "video_id": video_id,
                    "job_type": JobType.VIDEO_STAGE.value,
                    "target_stage": ProcessingStage.TRANSCRIPT.value,
                    "failed": JobStatus.FAILED_FINAL.value,
                },
            ).fetchone()
            return int(row[0])
        finally:
            connection.close()

    def latest_artifact(
        self,
        video_id: str,
        kind: ArtifactKind,
    ) -> ArtifactRecord | None:
        """Return the newest active indexed Artifact for an application loader."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE video_id = :video_id AND kind = :kind "
                "AND deleted_at IS NULL ORDER BY created_at DESC, artifact_id DESC LIMIT 1",
                {"video_id": video_id, "kind": kind.value},
            ).fetchone()
            return None if row is None else self._artifact_from_row(row)
        finally:
            connection.close()

    def upsert_video_metadata(
        self,
        metadata: VideoMetadata,
        *,
        pipeline_version: str,
        now: datetime,
    ) -> VideoRecord:
        now_text = format_utc_datetime(now)
        languages = tuple(dict.fromkeys(metadata.available_languages))
        languages_json = json.dumps(
            languages,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO videos "
                    "(video_id, channel_id, channel_name, title, description, "
                    "source_url, published_at, duration_seconds, default_language, "
                    "available_languages_json, live_status, availability, "
                    "pipeline_status, pipeline_version, discovered_at, updated_at) "
                    "VALUES (:video_id, :channel_id, :channel_name, :title, "
                    ":description, :source_url, :published_at, :duration_seconds, "
                    ":default_language, :available_languages_json, :live_status, "
                    ":availability, :pipeline_status, :pipeline_version, "
                    ":discovered_at, :updated_at) "
                    "ON CONFLICT(video_id) DO UPDATE SET "
                    "channel_id = excluded.channel_id, "
                    "channel_name = excluded.channel_name, title = excluded.title, "
                    "description = excluded.description, source_url = excluded.source_url, "
                    "published_at = excluded.published_at, "
                    "duration_seconds = excluded.duration_seconds, "
                    "default_language = excluded.default_language, "
                    "available_languages_json = excluded.available_languages_json, "
                    "live_status = excluded.live_status, "
                    "availability = excluded.availability, updated_at = excluded.updated_at",
                    {
                        "video_id": metadata.video_id,
                        "channel_id": metadata.channel_id,
                        "channel_name": metadata.channel_name,
                        "title": metadata.title,
                        "description": metadata.description,
                        "source_url": metadata.source_url,
                        "published_at": format_utc_datetime(metadata.published_at),
                        "duration_seconds": metadata.duration_seconds,
                        "default_language": metadata.default_language,
                        "available_languages_json": languages_json,
                        "live_status": metadata.live_status.value,
                        "availability": metadata.availability.value,
                        "pipeline_status": PipelineStatus.DISCOVERED.value,
                        "pipeline_version": pipeline_version,
                        "discovered_at": now_text,
                        "updated_at": now_text,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM videos WHERE video_id = :video_id",
                    {"video_id": metadata.video_id},
                ).fetchone()
                if row is None:
                    msg = "video metadata was not saved"
                    raise StateStoreError(msg)
                return self._video_from_row(row)
        finally:
            connection.close()

    def mark_video_unavailable(
        self,
        video_id: str,
        *,
        availability: Availability,
        now: datetime,
    ) -> bool:
        if availability is Availability.PUBLIC:
            msg = "unavailable marker cannot use public availability"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE videos SET availability = :availability, "
                    "updated_at = :updated_at WHERE video_id = :video_id",
                    {
                        "availability": availability.value,
                        "updated_at": format_utc_datetime(now),
                        "video_id": video_id,
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    def advance_pipeline(
        self,
        video_id: str,
        *,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        now: datetime,
    ) -> bool:
        transition_pipeline(expected_status, target_status)
        completed_at = (
            format_utc_datetime(now)
            if target_status
            in {PipelineStatus.COMPLETE, PipelineStatus.SKIPPED_DURATION_LIMIT}
            else None
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE videos SET pipeline_status = :target_status, "
                    "updated_at = :updated_at, completed_at = :completed_at "
                    "WHERE video_id = :video_id "
                    "AND pipeline_status = :expected_status "
                    "AND pipeline_version = :pipeline_version",
                    {
                        "target_status": target_status.value,
                        "updated_at": format_utc_datetime(now),
                        "completed_at": completed_at,
                        "video_id": video_id,
                        "expected_status": expected_status.value,
                        "pipeline_version": pipeline_version,
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    @staticmethod
    def _validate_job_shape(
        *,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
    ) -> None:
        if not scope_key.strip():
            msg = "scope_key must be non-empty"
            raise ValueError(msg)
        if job_type is JobType.VIDEO_STAGE:
            if video_id is None or target_stage in {
                ProcessingStage.DISCOVERY,
                ProcessingStage.WEEKLY_REPORT,
            }:
                msg = "video stage jobs require a video and video processing stage"
                raise ValueError(msg)
            expected_scope = f"video:{video_id}:{target_stage.value}"
            if scope_key != expected_scope:
                msg = "video job scope_key is not canonical"
                raise ValueError(msg)
        elif video_id is not None:
            msg = "global jobs must not reference a video"
            raise ValueError(msg)
        elif (
            job_type is JobType.CHANNEL_DISCOVERY
            and target_stage is not ProcessingStage.DISCOVERY
        ) or (
            job_type is JobType.WEEKLY_REPORT
            and target_stage is not ProcessingStage.WEEKLY_REPORT
        ):
            msg = "global job type and target stage differ"
            raise ValueError(msg)
        elif job_type is JobType.CHANNEL_DISCOVERY:
            parts = scope_key.split(":")
            if (
                len(parts) != 3
                or parts[0] != "channel"
                or not parts[1]
                or parts[2] != "discovery"
            ):
                msg = "channel discovery scope_key is not canonical"
                raise ValueError(msg)
        else:
            parts = scope_key.split(":")
            if (
                len(parts) != 4
                or parts[0] != "weekly"
                or not parts[1]
                or re.fullmatch(r"\d{4}-W\d{2}", parts[2]) is None
                or not parts[3]
            ):
                msg = "weekly report scope_key is not canonical"
                raise ValueError(msg)

    @staticmethod
    def _insert_job(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
        pipeline_version: str,
        max_attempts: int,
        available_at: str,
        now: str,
    ) -> None:
        # The repository alone derives the lineage generation at creation:
        # only a VIDEO_STAGE SCORING Job receives the v1 marker, every other
        # Job stays NULL (pre-lineage generation), and the value is immutable.
        scoring_lineage_version = (
            SCORING_LINEAGE_VERSION_V1
            if job_type is JobType.VIDEO_STAGE
            and target_stage is ProcessingStage.SCORING
            else None
        )
        connection.execute(
            "INSERT INTO jobs "
            "(job_id, scope_key, video_id, job_type, target_stage, "
            "pipeline_version, status, attempt_count, max_attempts, "
            "available_at, scoring_lineage_version, created_at, updated_at) "
            "VALUES (:job_id, :scope_key, :video_id, :job_type, :target_stage, "
            ":pipeline_version, :status, 0, :max_attempts, :available_at, "
            ":scoring_lineage_version, :created_at, :updated_at)",
            {
                "job_id": job_id,
                "scope_key": scope_key,
                "video_id": video_id,
                "job_type": job_type.value,
                "target_stage": target_stage.value,
                "pipeline_version": pipeline_version,
                "status": JobStatus.PENDING.value,
                "max_attempts": max_attempts,
                "available_at": available_at,
                "scoring_lineage_version": scoring_lineage_version,
                "created_at": now,
                "updated_at": now,
            },
        )

    def create_job(
        self,
        *,
        job_id: str,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
        pipeline_version: str,
        max_attempts: int,
        available_at: datetime,
        now: datetime,
    ) -> JobRecord:
        self._validate_job_shape(
            scope_key=scope_key,
            video_id=video_id,
            job_type=job_type,
            target_stage=target_stage,
        )
        if max_attempts <= 0:
            msg = "max_attempts must be positive"
            raise ValueError(msg)
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    self._insert_job(
                        connection,
                        job_id=job_id,
                        scope_key=scope_key,
                        video_id=video_id,
                        job_type=job_type,
                        target_stage=target_stage,
                        pipeline_version=pipeline_version,
                        max_attempts=max_attempts,
                        available_at=format_utc_datetime(available_at),
                        now=format_utc_datetime(now),
                    )
            except sqlite3.IntegrityError as error:
                msg = "active job already exists or job data is invalid"
                raise IntegrityConflict(msg) from error
            job = self.get_job(job_id)
            if job is None:
                msg = "created job could not be read"
                raise StateStoreError(msg)
            return job
        finally:
            connection.close()

    def get_job(self, job_id: str) -> JobRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = :job_id",
                {"job_id": job_id},
            ).fetchone()
            return None if row is None else self._job_from_row(row)
        finally:
            connection.close()

    def _read_job_in_transaction(
        self, connection: sqlite3.Connection, job_id: str
    ) -> JobRecord | None:
        """Read one Job on the exact connection of an open BEGIN IMMEDIATE.

        Private read-only CAS-diagnosis helper: it reuses the transaction's
        connection and canonical row decoder, performs no commit/rollback and
        has no side effects.  Public ``get_job`` is forbidden between a failed
        lineage CAS and its classification.
        """

        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
        ).fetchone()
        return None if row is None else self._job_from_row(row)

    def _read_video_in_transaction(
        self, connection: sqlite3.Connection, video_id: str
    ) -> VideoRecord | None:
        """Read one Video on the exact connection of an open BEGIN IMMEDIATE.

        Private read-only CAS-diagnosis helper with the same contract as
        ``_read_job_in_transaction``.
        """

        row = connection.execute(
            "SELECT * FROM videos WHERE video_id = :video_id",
            {"video_id": video_id},
        ).fetchone()
        return None if row is None else self._video_from_row(row)

    def list_job_attempts(self, job_id: str) -> tuple[JobAttemptRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._attempt_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM job_attempts WHERE job_id = :job_id "
                    "ORDER BY attempt_number",
                    {"job_id": job_id},
                )
            )
        finally:
            connection.close()

    def claim_next_job(
        self,
        *,
        owner: str,
        lease_until: datetime,
        now: datetime,
        video_id: str | None = None,
    ) -> JobRecord | None:
        if not owner.strip():
            msg = "lease owner must be non-empty"
            raise ValueError(msg)
        if video_id is not None and not video_id.strip():
            msg = "video_id filter must be non-empty when provided"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        if lease_text <= now_text:
            msg = "lease_until must be after now"
            raise ValueError(msg)
        video_filter = ""
        params: dict[str, object] = {
            "status": JobStatus.PENDING.value,
            "now": now_text,
        }
        if video_id is not None:
            video_filter = " AND video_id = :video_id"
            params["video_id"] = video_id
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM jobs WHERE status = :status "
                    "AND available_at <= :now AND attempt_count < max_attempts "
                    f"{video_filter} "
                    "ORDER BY available_at, created_at, job_id LIMIT 1",
                    params,
                ).fetchone()
                if row is None:
                    return None
                attempt_number = int(row["attempt_count"]) + 1
                changed = connection.execute(
                    "UPDATE jobs SET status = :running, attempt_count = :attempt, "
                    "lease_owner = :owner, lease_until = :lease_until, "
                    "updated_at = :now WHERE job_id = :job_id "
                    "AND status = :pending AND attempt_count = :previous_attempt",
                    {
                        "running": JobStatus.RUNNING.value,
                        "attempt": attempt_number,
                        "owner": owner,
                        "lease_until": lease_text,
                        "now": now_text,
                        "job_id": row["job_id"],
                        "pending": JobStatus.PENDING.value,
                        "previous_attempt": row["attempt_count"],
                    },
                ).rowcount
                if changed != 1:
                    msg = "job changed before claim"
                    raise ConcurrencyConflict(msg)
                connection.execute(
                    "INSERT INTO job_attempts "
                    "(job_id, attempt_number, lease_owner, started_at, lease_until) "
                    "VALUES (:job_id, :attempt_number, :owner, :started_at, "
                    ":lease_until)",
                    {
                        "job_id": row["job_id"],
                        "attempt_number": attempt_number,
                        "owner": owner,
                        "started_at": now_text,
                        "lease_until": lease_text,
                    },
                )
                claimed = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id",
                    {"job_id": row["job_id"]},
                ).fetchone()
                if claimed is None:
                    msg = "claimed job could not be read"
                    raise StateStoreError(msg)
                return self._job_from_row(claimed)
        finally:
            connection.close()

    def renew_job(
        self,
        job_id: str,
        *,
        owner: str,
        lease_until: datetime,
        now: datetime,
    ) -> bool:
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        if lease_text <= now_text:
            msg = "lease_until must be after now"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE jobs SET lease_until = :lease_until, updated_at = :now "
                    "WHERE job_id = :job_id AND status = :running "
                    "AND lease_owner = :owner AND lease_until > :now",
                    {
                        "lease_until": lease_text,
                        "now": now_text,
                        "job_id": job_id,
                        "running": JobStatus.RUNNING.value,
                        "owner": owner,
                    },
                ).rowcount
                if changed == 0:
                    return False
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET lease_until = :lease_until "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "lease_until": lease_text,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                return True
        finally:
            connection.close()

    @staticmethod
    def _owned_running_job(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        owner: str,
        now: str,
    ) -> sqlite3.Row:
        row: sqlite3.Row | None = connection.execute(
            "SELECT * FROM jobs WHERE job_id = :job_id AND status = :running "
            "AND lease_owner = :owner AND lease_until > :now",
            {
                "job_id": job_id,
                "running": JobStatus.RUNNING.value,
                "owner": owner,
                "now": now,
            },
        ).fetchone()
        if row is None:
            msg = "job lease is not owned or has expired"
            raise LeaseConflict(msg)
        return row

    def fail_job(
        self,
        job_id: str,
        *,
        owner: str,
        error_code: ErrorCode,
        error_message: str,
        retry_at: datetime | None,
        now: datetime,
    ) -> JobRecord:
        now_text = format_utc_datetime(now)
        retry_text = None if retry_at is None else format_utc_datetime(retry_at)
        safe_message = _safe_error_message(error_message)
        saved_job: JobRecord | None = None
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = self._owned_running_job(
                    connection, job_id=job_id, owner=owner, now=now_text
                )
                retryable = retry_text is not None and int(row["attempt_count"]) < int(
                    row["max_attempts"]
                )
                status = (
                    JobStatus.RETRY_PENDING if retryable else JobStatus.FAILED_FINAL
                )
                finished_at = None if retryable else now_text
                available_at = retry_text if retryable else row["available_at"]
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET finished_at = :now, outcome = :outcome, "
                    "error_code = :error_code, error_message = :error_message "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "now": now_text,
                        "outcome": status.value,
                        "error_code": error_code.value,
                        "error_message": safe_message,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                connection.execute(
                    "UPDATE jobs SET status = :status, available_at = :available_at, "
                    "lease_owner = NULL, lease_until = NULL, "
                    "last_error_code = :error_code, "
                    "last_error_message = :error_message, updated_at = :now, "
                    "finished_at = :finished_at WHERE job_id = :job_id",
                    {
                        "status": status.value,
                        "available_at": available_at,
                        "error_code": error_code.value,
                        "error_message": safe_message,
                        "now": now_text,
                        "finished_at": finished_at,
                        "job_id": job_id,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
                ).fetchone()
                saved_job = self._job_from_row(saved)
        finally:
            connection.close()
        if saved_job is None:
            raise StateStoreError("failed job could not be read")
        _release_terminal_scoring_admission(self, saved_job)
        return saved_job

    def finalize_unknown_provider_state(
        self,
        job_id: str,
        *,
        owner: str,
        error_message: str,
        now: datetime,
    ) -> JobRecord:
        """Atomically finalize a contacted SCORING provider whose outcome is unknown."""

        now_text = format_utc_datetime(now)
        safe_message = _safe_error_message(error_message)
        saved_job: JobRecord | None = None
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = self._owned_running_job(
                    connection, job_id=job_id, owner=owner, now=now_text
                )
                if row["target_stage"] != ProcessingStage.SCORING.value:
                    msg = "unknown provider state is only valid for scoring"
                    raise StateStoreError(msg)
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET finished_at = :now, "
                    "outcome = :outcome, error_code = :error_code, "
                    "error_message = :error_message "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "now": now_text,
                        "outcome": JobAttemptOutcome.FAILED_FINAL.value,
                        "error_code": "UNKNOWN_PROVIDER_STATE",
                        "error_message": safe_message,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                connection.execute(
                    "UPDATE jobs SET status = :status, lease_owner = NULL, "
                    "lease_until = NULL, last_error_code = :error_code, "
                    "last_error_message = :error_message, updated_at = :now, "
                    "finished_at = :now WHERE job_id = :job_id",
                    {
                        "status": JobStatus.FAILED_FINAL.value,
                        "error_code": "UNKNOWN_PROVIDER_STATE",
                        "error_message": safe_message,
                        "now": now_text,
                        "job_id": job_id,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
                ).fetchone()
                saved_job = self._job_from_row(saved)
        finally:
            connection.close()
        if saved_job is None:
            raise StateStoreError("unknown provider state job could not be read")
        _release_terminal_scoring_admission(self, saved_job)
        return saved_job

    def complete_job(
        self,
        job_id: str,
        *,
        owner: str,
        now: datetime,
    ) -> JobRecord:
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = self._owned_running_job(
                    connection, job_id=job_id, owner=owner, now=now_text
                )
                if row["video_id"] is not None:
                    msg = (
                        "video stage jobs must complete with pipeline state atomically"
                    )
                    raise StateStoreError(msg)
                attempt_changed = connection.execute(
                    "UPDATE job_attempts SET finished_at = :now, outcome = :outcome "
                    "WHERE job_id = :job_id AND finished_at IS NULL "
                    "AND lease_owner = :owner",
                    {
                        "now": now_text,
                        "outcome": JobAttemptOutcome.SUCCEEDED.value,
                        "job_id": job_id,
                        "owner": owner,
                    },
                ).rowcount
                if attempt_changed != 1:
                    msg = "active job attempt is missing"
                    raise StateStoreError(msg)
                connection.execute(
                    "UPDATE jobs SET status = :succeeded, lease_owner = NULL, "
                    "lease_until = NULL, last_error_code = NULL, "
                    "last_error_message = NULL, updated_at = :now, finished_at = :now "
                    "WHERE job_id = :job_id",
                    {
                        "succeeded": JobStatus.SUCCEEDED.value,
                        "now": now_text,
                        "job_id": job_id,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
                ).fetchone()
                return self._job_from_row(saved)
        finally:
            connection.close()

    def reclaim_expired_jobs(self, *, now: datetime) -> tuple[JobRecord, ...]:
        now_text = format_utc_datetime(now)
        saved_jobs: tuple[JobRecord, ...] = ()
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                expired = tuple(
                    connection.execute(
                        "SELECT * FROM jobs WHERE status = :running "
                        "AND lease_until <= :now ORDER BY lease_until, created_at, job_id",
                        {"running": JobStatus.RUNNING.value, "now": now_text},
                    )
                )
                recovered: list[JobRecord] = []
                for row in expired:
                    scoring_unknown = (
                        row["target_stage"] == ProcessingStage.SCORING.value
                    )
                    retryable = not scoring_unknown and int(row["attempt_count"]) < int(
                        row["max_attempts"]
                    )
                    status = (
                        JobStatus.RETRY_PENDING if retryable else JobStatus.FAILED_FINAL
                    )
                    finished_at = None if retryable else now_text
                    error_code = (
                        "UNKNOWN_PROVIDER_STATE" if scoring_unknown else "LEASE_EXPIRED"
                    )
                    error_message = (
                        "scoring provider outcome is unknown after lease expiry"
                        if scoring_unknown
                        else "job lease expired"
                    )
                    attempt_changed = connection.execute(
                        "UPDATE job_attempts SET finished_at = :now, "
                        "outcome = :outcome, error_code = :error_code, "
                        "error_message = :error_message "
                        "WHERE job_id = :job_id AND finished_at IS NULL",
                        {
                            "now": now_text,
                            "outcome": (
                                JobAttemptOutcome.FAILED_FINAL.value
                                if scoring_unknown
                                else JobAttemptOutcome.LEASE_EXPIRED.value
                            ),
                            "error_code": error_code,
                            "error_message": error_message,
                            "job_id": row["job_id"],
                        },
                    ).rowcount
                    if attempt_changed != 1:
                        msg = "expired job attempt is missing"
                        raise StateStoreError(msg)
                    connection.execute(
                        "UPDATE jobs SET status = :status, available_at = :now, "
                        "lease_owner = NULL, lease_until = NULL, "
                        "last_error_code = :error_code, "
                        "last_error_message = :error_message, updated_at = :now, "
                        "finished_at = :finished_at WHERE job_id = :job_id",
                        {
                            "status": status.value,
                            "now": now_text,
                            "error_code": error_code,
                            "error_message": error_message,
                            "finished_at": finished_at,
                            "job_id": row["job_id"],
                        },
                    )
                    saved = connection.execute(
                        "SELECT * FROM jobs WHERE job_id = :job_id",
                        {"job_id": row["job_id"]},
                    ).fetchone()
                    recovered.append(self._job_from_row(saved))
                saved_jobs = tuple(recovered)
        finally:
            connection.close()
        for saved_job in saved_jobs:
            _release_terminal_scoring_admission(self, saved_job)
        return saved_jobs

    def activate_retry_jobs(self, *, now: datetime) -> tuple[JobRecord, ...]:
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                due = tuple(
                    connection.execute(
                        "SELECT job_id FROM jobs WHERE status = :retry_pending "
                        "AND available_at <= :now ORDER BY available_at, created_at, job_id",
                        {
                            "retry_pending": JobStatus.RETRY_PENDING.value,
                            "now": now_text,
                        },
                    )
                )
                activated: list[JobRecord] = []
                for due_row in due:
                    connection.execute(
                        "UPDATE jobs SET status = :pending, updated_at = :now "
                        "WHERE job_id = :job_id AND status = :retry_pending",
                        {
                            "pending": JobStatus.PENDING.value,
                            "now": now_text,
                            "job_id": due_row["job_id"],
                            "retry_pending": JobStatus.RETRY_PENDING.value,
                        },
                    )
                    saved = connection.execute(
                        "SELECT * FROM jobs WHERE job_id = :job_id",
                        {"job_id": due_row["job_id"]},
                    ).fetchone()
                    activated.append(self._job_from_row(saved))
                return tuple(activated)
        finally:
            connection.close()

    def rerun_job(
        self,
        old_job_id: str,
        *,
        new_job_id: str,
        available_at: datetime,
        now: datetime,
    ) -> JobRecord:
        old = self.get_job(old_job_id)
        if old is None or old.status not in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED_FINAL,
        }:
            msg = "manual rerun requires a terminal source job"
            raise ValueError(msg)
        return self.create_job(
            job_id=new_job_id,
            scope_key=old.scope_key,
            video_id=old.video_id,
            job_type=old.job_type,
            target_stage=old.target_stage,
            pipeline_version=old.pipeline_version,
            max_attempts=old.max_attempts,
            available_at=available_at,
            now=now,
        )

    @staticmethod
    def _validate_artifact(artifact: ArtifactWrite) -> None:
        if not artifact.artifact_id.strip() or not artifact.artifact_key.strip():
            msg = "artifact identifiers must be non-empty"
            raise ValueError(msg)
        if not artifact.producer_version.strip():
            msg = "artifact producer_version must be non-empty"
            raise ValueError(msg)
        _validate_sha256(artifact.content_hash, field_name="content_hash")
        _validate_relative_path(artifact.relative_path)

    def _upsert_artifact_in_transaction(
        self,
        connection: sqlite3.Connection,
        artifact: ArtifactWrite,
        *,
        now: str,
    ) -> ArtifactRecord:
        self._validate_artifact(artifact)
        expires_at = (
            None
            if artifact.expires_at is None
            else format_utc_datetime(artifact.expires_at)
        )
        existing = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
            {"artifact_key": artifact.artifact_key},
        ).fetchone()
        if existing is not None:
            record = self._artifact_from_row(existing)
            if (
                record.artifact_id != artifact.artifact_id
                or record.video_id != artifact.video_id
                or record.job_id != artifact.job_id
                or record.kind is not artifact.kind
                or record.storage_root is not artifact.storage_root
                or record.relative_path != artifact.relative_path
                or record.content_hash != artifact.content_hash
                or record.provider != artifact.provider
                or record.model != artifact.model
                or record.producer_version != artifact.producer_version
                or record.retention_class is not artifact.retention_class
                or record.expires_at != artifact.expires_at
            ):
                msg = "artifact key already identifies different content"
                raise IntegrityConflict(msg)
            return record
        connection.execute(
            "INSERT INTO artifacts "
            "(artifact_id, artifact_key, video_id, job_id, kind, storage_root, "
            "relative_path, content_hash, provider, model, producer_version, "
            "retention_class, created_at, expires_at) "
            "VALUES (:artifact_id, :artifact_key, :video_id, :job_id, :kind, "
            ":storage_root, :relative_path, :content_hash, :provider, :model, "
            ":producer_version, :retention_class, :created_at, :expires_at)",
            {
                "artifact_id": artifact.artifact_id,
                "artifact_key": artifact.artifact_key,
                "video_id": artifact.video_id,
                "job_id": artifact.job_id,
                "kind": artifact.kind.value,
                "storage_root": artifact.storage_root.value,
                "relative_path": artifact.relative_path,
                "content_hash": artifact.content_hash,
                "provider": artifact.provider,
                "model": artifact.model,
                "producer_version": artifact.producer_version,
                "retention_class": artifact.retention_class.value,
                "created_at": now,
                "expires_at": expires_at,
            },
        )
        row = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
            {"artifact_key": artifact.artifact_key},
        ).fetchone()
        if row is None:
            msg = "artifact was not saved"
            raise StateStoreError(msg)
        return self._artifact_from_row(row)

    def upsert_artifact(
        self,
        artifact: ArtifactWrite,
        *,
        now: datetime,
    ) -> ArtifactRecord:
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    return self._upsert_artifact_in_transaction(
                        connection,
                        artifact,
                        now=format_utc_datetime(now),
                    )
            except sqlite3.IntegrityError as error:
                msg = "artifact data violates repository integrity"
                raise IntegrityConflict(msg) from error
        finally:
            connection.close()

    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
                {"artifact_key": artifact_key},
            ).fetchone()
            return None if row is None else self._artifact_from_row(row)
        finally:
            connection.close()

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        """Return a raw persisted artifact record; this confers no display authority."""
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id = :artifact_id",
                {"artifact_id": artifact_id},
            ).fetchone()
            return None if row is None else self._artifact_from_row(row)
        finally:
            connection.close()

    def mark_artifact_deleted(
        self,
        artifact_id: str,
        expected_content_hash: str,
        now: datetime,
    ) -> bool:
        """Record an already-performed file deletion with hash compare-and-swap.

        The repository never deletes a file. Callers must verify storage-root and
        filesystem boundaries before invoking this index-only confirmation.
        """

        _validate_sha256(expected_content_hash, field_name="expected_content_hash")
        if not artifact_id.strip():
            msg = "artifact_id must be non-empty"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE artifacts SET deleted_at = :now "
                    "WHERE artifact_id = :artifact_id "
                    "AND content_hash = :content_hash AND deleted_at IS NULL",
                    {
                        "now": format_utc_datetime(now),
                        "artifact_id": artifact_id,
                        "content_hash": expected_content_hash,
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    def list_expired_artifacts(
        self,
        retention_class: RetentionClass,
        now: datetime,
        limit: int,
    ) -> tuple[ArtifactRecord, ...]:
        """Return registered, undeleted expired artifacts in stable cleanup order."""

        if limit <= 0:
            msg = "limit must be positive"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM artifacts "
                "WHERE retention_class = :retention_class "
                "AND expires_at IS NOT NULL AND expires_at <= :now "
                "AND deleted_at IS NULL "
                "ORDER BY expires_at ASC, created_at ASC, artifact_id ASC "
                "LIMIT :limit",
                {
                    "retention_class": retention_class.value,
                    "now": now_text,
                    "limit": limit,
                },
            ).fetchall()
            return tuple(self._artifact_from_row(row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _provider_request_matches(
        row: sqlite3.Row, request: ProviderCallRequest
    ) -> bool:
        return (
            str(row["operation"]) == request.operation
            and str(row["provider"]) == request.provider
            and (None if row["model"] is None else str(row["model"])) == request.model
            and (None if row["prompt_version"] is None else str(row["prompt_version"]))
            == request.prompt_version
            and (None if row["schema_version"] is None else str(row["schema_version"]))
            == request.schema_version
        )

    @staticmethod
    def _dispatch_state_in_transaction(
        connection: sqlite3.Connection, request_hash: str
    ) -> ProviderDispatchRecord | None:
        row = connection.execute(
            "SELECT * FROM provider_dispatch_states WHERE request_hash = :request_hash",
            {"request_hash": request_hash},
        ).fetchone()
        return (
            None
            if row is None
            else SQLiteStateRepository._provider_dispatch_from_row(row)
        )

    @staticmethod
    def _mark_dispatch_ambiguous_in_transaction(
        connection: sqlite3.Connection, *, request_hash: str, now: str
    ) -> ProviderCallRecord:
        """Make one uncertain cloud request terminal for automatic recovery."""

        connection.execute(
            "UPDATE provider_dispatch_states SET status = :ambiguous, updated_at = :now "
            "WHERE request_hash = :request_hash AND status IN (:intent, :unknown)",
            {
                "ambiguous": ProviderDispatchStatus.AMBIGUOUS.value,
                "now": now,
                "request_hash": request_hash,
                "intent": ProviderDispatchStatus.DISPATCH_INTENT_DURABLE.value,
                "unknown": ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN.value,
            },
        )
        connection.execute(
            "UPDATE provider_calls SET status = :failed_final, "
            "reservation_owner = NULL, lease_until = NULL, "
            "last_error_code = :error_code, last_error_message = :error_message, "
            "finished_at = :now, updated_at = :now WHERE request_hash = :request_hash "
            "AND status IN (:pending, :retryable)",
            {
                "failed_final": ProviderCallStatus.FAILED_FINAL.value,
                "error_code": ErrorCode.PROVIDER_UNAVAILABLE.value,
                "error_message": "cloud provider dispatch outcome is ambiguous; operator resolution required",
                "now": now,
                "request_hash": request_hash,
                "pending": ProviderCallStatus.PENDING.value,
                "retryable": ProviderCallStatus.FAILED_RETRYABLE.value,
            },
        )
        row = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
            {"request_hash": request_hash},
        ).fetchone()
        if row is None:
            raise StateStoreError("ambiguous provider call could not be read")
        return SQLiteStateRepository._provider_call_from_row(row)

    def _reserve_provider_call_in_transaction(
        self,
        connection: sqlite3.Connection,
        request: ProviderCallRequest,
        *,
        owner: str,
        lease_until: datetime,
        available_at: datetime,
        now: datetime,
    ) -> ProviderCallRecord:
        """Insert or re-use an in-transaction PENDING provider-call reservation.

        Unlike the public ``reserve_provider_call``, this helper assumes it runs
        inside an existing transaction and never performs recovery from an
        existing artifact.  It is intended for Phase G-style atomic registration
        where the response artifact is upserted in the same transaction.
        """

        _validate_sha256(request.request_hash, field_name="request_hash")
        if not request.operation.strip() or not request.provider.strip():
            msg = "provider call operation and provider must be non-empty"
            raise ValueError(msg)
        if not request.deterministic_artifact_key.strip():
            msg = "deterministic artifact key must be non-empty"
            raise ValueError(msg)
        if not owner.strip():
            msg = "reservation owner must be non-empty"
            raise ValueError(msg)
        if lease_until <= now:
            msg = "provider call lease_until must be after now"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        available_text = format_utc_datetime(available_at)
        row = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
            {"request_hash": request.request_hash},
        ).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO provider_calls "
                "(request_hash, operation, provider, model, prompt_version, "
                "schema_version, status, reservation_owner, lease_until, "
                "available_at, attempt_count, started_at, updated_at) "
                "VALUES (:request_hash, :operation, :provider, :model, "
                ":prompt_version, :schema_version, :status, :owner, "
                ":lease_until, :available_at, 1, :started_at, :updated_at)",
                {
                    "request_hash": request.request_hash,
                    "operation": request.operation,
                    "provider": request.provider,
                    "model": request.model,
                    "prompt_version": request.prompt_version,
                    "schema_version": request.schema_version,
                    "status": ProviderCallStatus.PENDING.value,
                    "owner": owner,
                    "lease_until": lease_text,
                    "available_at": available_text,
                    "started_at": now_text,
                    "updated_at": now_text,
                },
            )
        else:
            record = self._provider_call_from_row(row)
            if not self._provider_request_matches(row, request):
                msg = "request hash already identifies a different provider call"
                raise IntegrityConflict(msg)
            if record.status is ProviderCallStatus.SUCCEEDED:
                return record
            if (
                record.status is ProviderCallStatus.PENDING
                and record.reservation_owner == owner
                and record.lease_until is not None
                and record.lease_until > now
            ):
                pass
            else:
                msg = "provider call reservation is not owned or has expired"
                raise LeaseConflict(msg)
        saved = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
            {"request_hash": request.request_hash},
        ).fetchone()
        if saved is None:
            msg = "provider call reservation was not saved"
            raise StateStoreError(msg)
        return self._provider_call_from_row(saved)

    def reserve_provider_call(
        self,
        request: ProviderCallRequest,
        *,
        owner: str,
        lease_until: datetime,
        available_at: datetime,
        now: datetime,
        verified_artifact: VerifiedArtifact | None = None,
        fail_closed_on_ambiguous_dispatch: bool = False,
    ) -> ProviderReservation:
        _validate_sha256(request.request_hash, field_name="request_hash")
        if not request.operation.strip() or not request.provider.strip():
            msg = "provider call operation and provider must be non-empty"
            raise ValueError(msg)
        if not request.deterministic_artifact_key.strip():
            msg = "deterministic artifact key must be non-empty"
            raise ValueError(msg)
        if not owner.strip():
            msg = "reservation owner must be non-empty"
            raise ValueError(msg)
        now_text = format_utc_datetime(now)
        lease_text = format_utc_datetime(lease_until)
        available_text = format_utc_datetime(available_at)
        if lease_text <= now_text:
            msg = "provider call lease_until must be after now"
            raise ValueError(msg)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request.request_hash},
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO provider_calls "
                        "(request_hash, operation, provider, model, prompt_version, "
                        "schema_version, status, reservation_owner, lease_until, "
                        "available_at, attempt_count, started_at, updated_at) "
                        "VALUES (:request_hash, :operation, :provider, :model, "
                        ":prompt_version, :schema_version, :status, :owner, "
                        ":lease_until, :available_at, 1, :started_at, :updated_at)",
                        {
                            "request_hash": request.request_hash,
                            "operation": request.operation,
                            "provider": request.provider,
                            "model": request.model,
                            "prompt_version": request.prompt_version,
                            "schema_version": request.schema_version,
                            "status": ProviderCallStatus.PENDING.value,
                            "owner": owner,
                            "lease_until": lease_text,
                            "available_at": available_text,
                            "started_at": now_text,
                            "updated_at": now_text,
                        },
                    )
                    if fail_closed_on_ambiguous_dispatch:
                        connection.execute(
                            "INSERT INTO provider_dispatch_states "
                            "(request_hash, status, updated_at) "
                            "VALUES (:request_hash, :status, :now)",
                            {
                                "request_hash": request.request_hash,
                                "status": ProviderDispatchStatus.NOT_DISPATCHED.value,
                                "now": now_text,
                            },
                        )
                    inserted = connection.execute(
                        "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                        {"request_hash": request.request_hash},
                    ).fetchone()
                    if inserted is None:
                        msg = "provider call reservation was not saved"
                        raise StateStoreError(msg)
                    return ProviderReservation(
                        record=self._provider_call_from_row(inserted),
                        acquired=True,
                        recovered_from_artifact=False,
                    )
                if not self._provider_request_matches(row, request):
                    msg = "request hash already identifies a different provider call"
                    raise IntegrityConflict(msg)
                record = self._provider_call_from_row(row)
                dispatch = self._dispatch_state_in_transaction(
                    connection, request.request_hash
                )
                if (
                    fail_closed_on_ambiguous_dispatch
                    and dispatch is not None
                    and dispatch.status is ProviderDispatchStatus.AMBIGUOUS
                ):
                    if (
                        record.status is ProviderCallStatus.PENDING
                        and record.lease_until is not None
                        and record.lease_until > now
                    ):
                        return ProviderReservation(record, False, False)
                    return ProviderReservation(
                        self._mark_dispatch_ambiguous_in_transaction(
                            connection,
                            request_hash=request.request_hash,
                            now=now_text,
                        ),
                        False,
                        False,
                    )
                if (
                    fail_closed_on_ambiguous_dispatch
                    and dispatch is not None
                    and dispatch.status
                    in {
                        ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
                        ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN,
                    }
                ):
                    if (
                        record.status is ProviderCallStatus.PENDING
                        and record.lease_until is not None
                        and record.lease_until > now
                    ):
                        return ProviderReservation(record, False, False)
                    return ProviderReservation(
                        self._mark_dispatch_ambiguous_in_transaction(
                            connection,
                            request_hash=request.request_hash,
                            now=now_text,
                        ),
                        False,
                        False,
                    )
                if record.status in {
                    ProviderCallStatus.SUCCEEDED,
                    ProviderCallStatus.FAILED_FINAL,
                }:
                    return ProviderReservation(record, False, False)
                if (
                    record.status is ProviderCallStatus.PENDING
                    and record.lease_until is not None
                    and record.lease_until > now
                ) or (
                    record.status is ProviderCallStatus.FAILED_RETRYABLE
                    and record.available_at > now
                ):
                    return ProviderReservation(record, False, False)

                artifact_row = connection.execute(
                    "SELECT * FROM artifacts WHERE artifact_key = :artifact_key",
                    {"artifact_key": request.deterministic_artifact_key},
                ).fetchone()
                if artifact_row is not None:
                    artifact = self._artifact_from_row(artifact_row)
                    if (
                        verified_artifact is None
                        or verified_artifact.artifact_key != artifact.artifact_key
                        or verified_artifact.content_hash != artifact.content_hash
                    ):
                        msg = "deterministic artifact exists without a verified hash"
                        raise IntegrityConflict(msg)
                    connection.execute(
                        "UPDATE provider_calls SET status = :succeeded, "
                        "reservation_owner = NULL, lease_until = NULL, "
                        "response_artifact_id = :artifact_id, finished_at = :now, "
                        "updated_at = :now, last_error_code = NULL, "
                        "last_error_message = NULL WHERE request_hash = :request_hash",
                        {
                            "succeeded": ProviderCallStatus.SUCCEEDED.value,
                            "artifact_id": artifact.artifact_id,
                            "now": now_text,
                            "request_hash": request.request_hash,
                        },
                    )
                    recovered = connection.execute(
                        "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                        {"request_hash": request.request_hash},
                    ).fetchone()
                    if recovered is None:
                        msg = "recovered provider call could not be read"
                        raise StateStoreError(msg)
                    return ProviderReservation(
                        self._provider_call_from_row(recovered), False, True
                    )
                if verified_artifact is not None:
                    msg = "verified artifact is not indexed by its deterministic key"
                    raise IntegrityConflict(msg)
                connection.execute(
                    "UPDATE provider_calls SET status = :pending, "
                    "reservation_owner = :owner, lease_until = :lease_until, "
                    "available_at = :available_at, attempt_count = attempt_count + 1, "
                    "last_error_code = NULL, last_error_message = NULL, "
                    "finished_at = NULL, updated_at = :now "
                    "WHERE request_hash = :request_hash",
                    {
                        "pending": ProviderCallStatus.PENDING.value,
                        "owner": owner,
                        "lease_until": lease_text,
                        "available_at": available_text,
                        "now": now_text,
                        "request_hash": request.request_hash,
                    },
                )
                if fail_closed_on_ambiguous_dispatch and dispatch is not None:
                    connection.execute(
                        "UPDATE provider_dispatch_states SET status = :not_dispatched, "
                        "updated_at = :now WHERE request_hash = :request_hash "
                        "AND status = :failed_known",
                        {
                            "not_dispatched": ProviderDispatchStatus.NOT_DISPATCHED.value,
                            "now": now_text,
                            "request_hash": request.request_hash,
                            "failed_known": ProviderDispatchStatus.FAILED_KNOWN.value,
                        },
                    )
                taken = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request.request_hash},
                ).fetchone()
                if taken is None:
                    msg = "provider call takeover could not be read"
                    raise StateStoreError(msg)
                return ProviderReservation(
                    self._provider_call_from_row(taken), True, False
                )
        finally:
            connection.close()

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                {"request_hash": request_hash},
            ).fetchone()
            return None if row is None else self._provider_call_from_row(row)
        finally:
            connection.close()

    def get_provider_dispatch(self, request_hash: str) -> ProviderDispatchRecord | None:
        """Read cloud-dispatch recovery state without minting a new state."""

        connection = self._connect()
        try:
            return self._dispatch_state_in_transaction(connection, request_hash)
        finally:
            connection.close()

    def _update_provider_dispatch_owned(
        self,
        request_hash: str,
        *,
        owner: str,
        expected: ProviderDispatchStatus,
        target: ProviderDispatchStatus,
        now: datetime,
    ) -> ProviderDispatchRecord:
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE provider_dispatch_states SET status = :target, updated_at = :now "
                    "WHERE request_hash = :request_hash AND status = :expected "
                    "AND EXISTS (SELECT 1 FROM provider_calls WHERE "
                    "request_hash = :request_hash AND status = :pending "
                    "AND reservation_owner = :owner AND lease_until > :now)",
                    {
                        "target": target.value,
                        "now": now_text,
                        "request_hash": request_hash,
                        "expected": expected.value,
                        "pending": ProviderCallStatus.PENDING.value,
                        "owner": owner,
                    },
                ).rowcount
                if changed != 1:
                    raise LeaseConflict(
                        "provider dispatch is not owned or is not in the expected state"
                    )
                saved = self._dispatch_state_in_transaction(connection, request_hash)
                if saved is None:
                    raise StateStoreError("provider dispatch state could not be read")
                return saved
        finally:
            connection.close()

    def record_provider_dispatch_intent(
        self, request_hash: str, *, owner: str, now: datetime
    ) -> ProviderDispatchRecord:
        """Durably authorize one external cloud request before transport starts."""

        return self._update_provider_dispatch_owned(
            request_hash,
            owner=owner,
            expected=ProviderDispatchStatus.NOT_DISPATCHED,
            target=ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
            now=now,
        )

    def record_provider_dispatch_result_unknown(
        self, request_hash: str, *, owner: str, now: datetime
    ) -> ProviderDispatchRecord:
        """Record that a transport returned before the atomic local receipt."""

        return self._update_provider_dispatch_owned(
            request_hash,
            owner=owner,
            expected=ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
            target=ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN,
            now=now,
        )

    def record_provider_dispatch_known_failure(
        self, request_hash: str, *, owner: str, now: datetime
    ) -> ProviderDispatchRecord:
        """Record a provider outcome proven not to be an unknown success."""

        return self._update_provider_dispatch_owned(
            request_hash,
            owner=owner,
            expected=ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
            target=ProviderDispatchStatus.FAILED_KNOWN,
            now=now,
        )

    def mark_provider_dispatch_ambiguous(
        self, request_hash: str, *, owner: str, now: datetime
    ) -> ProviderCallRecord:
        """Fail closed after an in-process error once transport intent was durable."""

        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash "
                    "AND status = :pending AND reservation_owner = :owner "
                    "AND lease_until > :now",
                    {
                        "request_hash": request_hash,
                        "pending": ProviderCallStatus.PENDING.value,
                        "owner": owner,
                        "now": now_text,
                    },
                ).fetchone()
                if row is None:
                    raise LeaseConflict(
                        "provider call reservation is not owned or has expired"
                    )
                dispatch = self._dispatch_state_in_transaction(connection, request_hash)
                if dispatch is None or dispatch.status not in {
                    ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
                    ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN,
                }:
                    raise IntegrityConflict(
                        "provider dispatch is not an ambiguous external boundary"
                    )
                return self._mark_dispatch_ambiguous_in_transaction(
                    connection, request_hash=request_hash, now=now_text
                )
        finally:
            connection.close()

    def recover_provider_dispatch(
        self, request_hash: str, *, now: datetime
    ) -> ProviderDispatchRecord | None:
        """Resolve expired cloud-dispatch uncertainty before reading credentials.

        A still-live lease is left untouched for its owner.  Once the lease is
        expired, an intent or returned-but-uncommitted result becomes a durable
        operator-visible ``AMBIGUOUS`` terminal state instead of a retry.
        """

        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                dispatch = self._dispatch_state_in_transaction(connection, request_hash)
                if dispatch is None:
                    return None
                if dispatch.status not in {
                    ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
                    ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN,
                }:
                    return dispatch
                call_row = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request_hash},
                ).fetchone()
                if call_row is None:
                    raise StateStoreError("provider dispatch call is missing")
                call = self._provider_call_from_row(call_row)
                if (
                    call.status is ProviderCallStatus.PENDING
                    and call.lease_until is not None
                    and call.lease_until > now
                ):
                    return dispatch
                self._mark_dispatch_ambiguous_in_transaction(
                    connection, request_hash=request_hash, now=now_text
                )
                resolved = self._dispatch_state_in_transaction(connection, request_hash)
                if resolved is None:
                    raise StateStoreError(
                        "ambiguous provider dispatch could not be read"
                    )
                return resolved
        finally:
            connection.close()

    def _complete_provider_call_in_transaction(
        self,
        connection: sqlite3.Connection,
        completion: ProviderCallCompletion,
        *,
        owner: str,
        now: str,
    ) -> ProviderCallRecord:
        for value in (
            completion.input_tokens,
            completion.output_tokens,
            completion.cost_microusd,
        ):
            if value is not None and value < 0:
                msg = "provider usage and cost values must be non-negative"
                raise ValueError(msg)
        row = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash "
            "AND status = :pending AND reservation_owner = :owner "
            "AND lease_until > :now",
            {
                "request_hash": completion.request_hash,
                "pending": ProviderCallStatus.PENDING.value,
                "owner": owner,
                "now": now,
            },
        ).fetchone()
        if row is None:
            msg = "provider call reservation is not owned or has expired"
            raise LeaseConflict(msg)
        artifact_exists = connection.execute(
            "SELECT 1 FROM artifacts WHERE artifact_id = :artifact_id",
            {"artifact_id": completion.response_artifact_id},
        ).fetchone()
        if artifact_exists is None:
            msg = "provider response artifact is not indexed"
            raise IntegrityConflict(msg)
        dispatch = self._dispatch_state_in_transaction(
            connection, completion.request_hash
        )
        if (
            dispatch is not None
            and dispatch.status is not ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN
        ):
            raise IntegrityConflict(
                "provider dispatch state does not permit durable success"
            )
        connection.execute(
            "UPDATE provider_calls SET status = :succeeded, "
            "reservation_owner = NULL, lease_until = NULL, "
            "response_artifact_id = :artifact_id, input_tokens = :input_tokens, "
            "output_tokens = :output_tokens, cost_microusd = :cost_microusd, "
            "last_error_code = NULL, last_error_message = NULL, "
            "finished_at = :now, updated_at = :now "
            "WHERE request_hash = :request_hash",
            {
                "succeeded": ProviderCallStatus.SUCCEEDED.value,
                "artifact_id": completion.response_artifact_id,
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "cost_microusd": completion.cost_microusd,
                "now": now,
                "request_hash": completion.request_hash,
            },
        )
        if dispatch is not None:
            changed = connection.execute(
                "UPDATE provider_dispatch_states SET status = :success, updated_at = :now "
                "WHERE request_hash = :request_hash AND status = :unknown",
                {
                    "success": ProviderDispatchStatus.SUCCESS_DURABLY_RECORDED.value,
                    "now": now,
                    "request_hash": completion.request_hash,
                    "unknown": ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN.value,
                },
            ).rowcount
            if changed != 1:
                raise IntegrityConflict(
                    "provider dispatch state changed before durable success"
                )
        saved = connection.execute(
            "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
            {"request_hash": completion.request_hash},
        ).fetchone()
        if saved is None:
            msg = "completed provider call could not be read"
            raise StateStoreError(msg)
        return self._provider_call_from_row(saved)

    def complete_provider_call(
        self,
        request_hash: str,
        *,
        owner: str,
        response_artifact_id: str,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microusd: int | None,
        now: datetime,
    ) -> ProviderCallRecord:
        completion = ProviderCallCompletion(
            request_hash=request_hash,
            response_artifact_id=response_artifact_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_microusd=cost_microusd,
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                return self._complete_provider_call_in_transaction(
                    connection,
                    completion,
                    owner=owner,
                    now=format_utc_datetime(now),
                )
        finally:
            connection.close()

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
    ) -> ProviderCallRecord:
        now_text = format_utc_datetime(now)
        available_text = format_utc_datetime(available_at)
        status = (
            ProviderCallStatus.FAILED_RETRYABLE
            if retryable
            else ProviderCallStatus.FAILED_FINAL
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE provider_calls SET status = :status, "
                    "reservation_owner = NULL, lease_until = NULL, "
                    "available_at = :available_at, last_error_code = :error_code, "
                    "last_error_message = :error_message, finished_at = :finished_at, "
                    "updated_at = :now WHERE request_hash = :request_hash "
                    "AND status = :pending AND reservation_owner = :owner "
                    "AND lease_until > :now",
                    {
                        "status": status.value,
                        "available_at": available_text,
                        "error_code": error_code.value,
                        "error_message": _safe_error_message(error_message),
                        "finished_at": None if retryable else now_text,
                        "now": now_text,
                        "request_hash": request_hash,
                        "pending": ProviderCallStatus.PENDING.value,
                        "owner": owner,
                    },
                ).rowcount
                if changed != 1:
                    msg = "provider call reservation is not owned or has expired"
                    raise LeaseConflict(msg)
                saved = connection.execute(
                    "SELECT * FROM provider_calls WHERE request_hash = :request_hash",
                    {"request_hash": request_hash},
                ).fetchone()
                if saved is None:
                    msg = "failed provider call could not be read"
                    raise StateStoreError(msg)
                return self._provider_call_from_row(saved)
        finally:
            connection.close()

    @staticmethod
    def _finish_job_success_in_transaction(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        owner: str,
        now: str,
    ) -> JobRecord:
        changed = connection.execute(
            "UPDATE job_attempts SET finished_at = :now, outcome = :outcome "
            "WHERE job_id = :job_id AND finished_at IS NULL "
            "AND lease_owner = :owner",
            {
                "now": now,
                "outcome": JobAttemptOutcome.SUCCEEDED.value,
                "job_id": job_id,
                "owner": owner,
            },
        ).rowcount
        if changed != 1:
            msg = "active job attempt is missing"
            raise StateStoreError(msg)
        connection.execute(
            "UPDATE jobs SET status = :succeeded, lease_owner = NULL, "
            "lease_until = NULL, last_error_code = NULL, last_error_message = NULL, "
            "updated_at = :now, finished_at = :now WHERE job_id = :job_id",
            {
                "succeeded": JobStatus.SUCCEEDED.value,
                "now": now,
                "job_id": job_id,
            },
        )
        saved = connection.execute(
            "SELECT * FROM jobs WHERE job_id = :job_id", {"job_id": job_id}
        ).fetchone()
        if saved is None:
            msg = "completed job could not be read"
            raise StateStoreError(msg)
        return SQLiteStateRepository._job_from_row(saved)

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
    ) -> StageCompletionResult:
        transition_pipeline(expected_status, target_status)
        is_scoring_completion = (
            expected_status is PipelineStatus.TRANSCRIPT_READY
            and target_status is PipelineStatus.SCORED
        )
        if is_scoring_completion:
            # Phase G scoring success is deliberately not a generic repository
            # stage completion.  Only RuntimeOperations' local persistence
            # entry may compose the verified filesystem protocol with these
            # low-level transaction primitives.  Reject before opening SQLite.
            raise IntegrityConflict(
                "TRANSCRIPT_READY -> SCORED requires the runtime trusted persistence entry"
            )
        if is_scoring_completion and scoring_summary is None:
            msg = "scoring summary is required for TRANSCRIPT_READY -> SCORED"
            raise IntegrityConflict(msg)
        if not is_scoring_completion and scoring_summary is not None:
            msg = "scoring summary is only allowed for TRANSCRIPT_READY -> SCORED"
            raise IntegrityConflict(msg)
        expected_stage = _processing_stage_for_transition(
            expected_status, target_status
        )
        if any(
            artifact.job_id != job_id or artifact.video_id != video_id
            for artifact in artifacts
        ):
            msg = "stage artifacts must reference the completed job and video"
            raise IntegrityConflict(msg)
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    job_row = self._owned_running_job(
                        connection, job_id=job_id, owner=owner, now=now_text
                    )
                    if (
                        job_row["video_id"] != video_id
                        or job_row["pipeline_version"] != pipeline_version
                    ):
                        msg = "job scope does not match stage completion"
                        raise ConcurrencyConflict(msg)
                    if job_row["target_stage"] != expected_stage.value:
                        msg = "job target stage does not match pipeline transition"
                        raise ConcurrencyConflict(msg)
                    stored_artifacts = tuple(
                        self._upsert_artifact_in_transaction(
                            connection,
                            artifact,
                            now=now_text,
                        )
                        for artifact in artifacts
                    )
                    self._inject_failure("stage.after_artifacts")
                    completed_call = (
                        None
                        if provider_call is None
                        else self._complete_provider_call_in_transaction(
                            connection,
                            provider_call,
                            owner=owner,
                            now=now_text,
                        )
                    )
                    self._inject_failure("stage.after_provider_call")
                    completed_at = (
                        now_text
                        if target_status
                        in {
                            PipelineStatus.COMPLETE,
                            PipelineStatus.SKIPPED_DURATION_LIMIT,
                        }
                        else None
                    )
                    if scoring_summary is None:
                        changed = connection.execute(
                            "UPDATE videos SET pipeline_status = :target_status, "
                            "updated_at = :now, completed_at = :completed_at "
                            "WHERE video_id = :video_id "
                            "AND pipeline_status = :expected_status "
                            "AND pipeline_version = :pipeline_version",
                            {
                                "target_status": target_status.value,
                                "now": now_text,
                                "completed_at": completed_at,
                                "video_id": video_id,
                                "expected_status": expected_status.value,
                                "pipeline_version": pipeline_version,
                            },
                        ).rowcount
                    else:
                        changed = connection.execute(
                            "UPDATE videos SET pipeline_status = :target_status, "
                            "score = :score, should_summarize = :should_summarize, "
                            "updated_at = :now, completed_at = :completed_at "
                            "WHERE video_id = :video_id "
                            "AND pipeline_status = :expected_status "
                            "AND pipeline_version = :pipeline_version",
                            {
                                "target_status": target_status.value,
                                "score": scoring_summary.score,
                                "should_summarize": int(
                                    scoring_summary.should_summarize
                                ),
                                "now": now_text,
                                "completed_at": completed_at,
                                "video_id": video_id,
                                "expected_status": expected_status.value,
                                "pipeline_version": pipeline_version,
                            },
                        ).rowcount
                    if changed != 1:
                        msg = "pipeline changed before stage completion"
                        raise ConcurrencyConflict(msg)
                    self._inject_failure("stage.after_scoring_summary")
                    self._inject_failure("stage.after_pipeline")
                    job = self._finish_job_success_in_transaction(
                        connection, job_id=job_id, owner=owner, now=now_text
                    )
                    video_row = connection.execute(
                        "SELECT * FROM videos WHERE video_id = :video_id",
                        {"video_id": video_id},
                    ).fetchone()
                    if video_row is None:
                        msg = "completed video could not be read"
                        raise StateStoreError(msg)
                    return StageCompletionResult(
                        job=job,
                        video=self._video_from_row(video_row),
                        artifacts=stored_artifacts,
                        provider_call=completed_call,
                    )
            except sqlite3.IntegrityError as error:
                msg = "stage completion violates repository integrity"
                raise IntegrityConflict(msg) from error
        finally:
            connection.close()

    def upsert_report(self, report: ReportWrite, *, now: datetime) -> ReportRecord:
        if not report.report_id.strip() or not report.timezone.strip():
            msg = "report identifiers and timezone must be non-empty"
            raise ValueError(msg)
        if report.relative_path is not None:
            _validate_relative_path(report.relative_path)
        if report.content_hash is not None:
            _validate_sha256(report.content_hash, field_name="content_hash")
        now_text = format_utc_datetime(now)
        connection = self._connect()
        try:
            try:
                with _immediate_transaction(connection):
                    connection.execute(
                        "INSERT INTO reports "
                        "(report_id, timezone, iso_year, iso_week, report_type, "
                        "relative_path, content_hash, status, created_at, updated_at) "
                        "VALUES (:report_id, :timezone, :iso_year, :iso_week, 'weekly', "
                        ":relative_path, :content_hash, :status, :created_at, :updated_at) "
                        "ON CONFLICT(timezone, iso_year, iso_week, report_type) "
                        "DO UPDATE SET relative_path = excluded.relative_path, "
                        "content_hash = excluded.content_hash, status = excluded.status, "
                        "updated_at = excluded.updated_at",
                        {
                            "report_id": report.report_id,
                            "timezone": report.timezone,
                            "iso_year": report.iso_year,
                            "iso_week": report.iso_week,
                            "relative_path": report.relative_path,
                            "content_hash": report.content_hash,
                            "status": report.status.value,
                            "created_at": now_text,
                            "updated_at": now_text,
                        },
                    )
                    self._inject_failure("report.before_commit")
                    row = connection.execute(
                        "SELECT * FROM reports WHERE timezone = :timezone "
                        "AND iso_year = :iso_year AND iso_week = :iso_week "
                        "AND report_type = 'weekly'",
                        {
                            "timezone": report.timezone,
                            "iso_year": report.iso_year,
                            "iso_week": report.iso_week,
                        },
                    ).fetchone()
                    if row is None:
                        msg = "weekly report was not saved"
                        raise StateStoreError(msg)
                    return self._report_from_row(row)
            except sqlite3.IntegrityError as error:
                msg = "weekly report violates repository integrity"
                raise IntegrityConflict(msg) from error
        finally:
            connection.close()

    def get_report(
        self,
        *,
        timezone: str,
        iso_year: int,
        iso_week: int,
    ) -> ReportRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM reports WHERE timezone = :timezone "
                "AND iso_year = :iso_year AND iso_week = :iso_week "
                "AND report_type = 'weekly'",
                {
                    "timezone": timezone,
                    "iso_year": iso_year,
                    "iso_week": iso_week,
                },
            ).fetchone()
            return None if row is None else self._report_from_row(row)
        finally:
            connection.close()

    def list_reports(self, *, limit: int = 100) -> tuple[ReportRecord, ...]:
        if limit <= 0 or limit > 1000:
            raise ValueError("report list limit is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM reports WHERE report_type='weekly' ORDER BY iso_year DESC, iso_week DESC LIMIT :limit",
                {"limit": limit},
            ).fetchall()
            return tuple(self._report_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_weekly_candidates(
        self, *, start_utc: datetime, end_utc: datetime
    ) -> tuple[WeeklyCandidateRecord, ...]:
        """Return deterministically ordered potential weekly-report inputs.

        Artifact bytes and their domain payloads remain untrusted until the
        reporting service verifies them against these indexed records.
        """
        if start_utc >= end_utc:
            msg = "weekly candidate window must be non-empty"
            raise ValueError(msg)
        start_text = format_utc_datetime(start_utc)
        end_text = format_utc_datetime(end_utc)
        connection = self._connect()
        try:
            videos = connection.execute(
                "SELECT * FROM videos WHERE pipeline_status = :complete "
                "AND should_summarize = 1 AND score IS NOT NULL "
                "AND completed_at >= :start AND completed_at < :end "
                "ORDER BY score DESC, video_id ASC",
                {
                    "complete": PipelineStatus.COMPLETE.value,
                    "start": start_text,
                    "end": end_text,
                },
            ).fetchall()
            candidates: list[WeeklyCandidateRecord] = []
            for row in videos:
                video = self._video_from_row(row)
                note = connection.execute(
                    "SELECT * FROM artifacts WHERE artifact_key = :key "
                    "AND kind = :kind AND storage_root = :root "
                    "AND deleted_at IS NULL",
                    {
                        "key": f"video-note/{video.pipeline_version}/{video.video_id}",
                        "kind": ArtifactKind.VIDEO_NOTE.value,
                        "root": StorageRoot.VAULT.value,
                    },
                ).fetchone()
                score = _latest_weekly_artifact(
                    connection, video.video_id, ArtifactKind.SCORING_STRUCTURED
                )
                analysis = _latest_weekly_artifact(
                    connection, video.video_id, ArtifactKind.ANALYSIS_STRUCTURED
                )
                if note is not None and score is not None:
                    candidates.append(
                        WeeklyCandidateRecord(
                            video=video,
                            score_artifact=self._artifact_from_row(score),
                            analysis_artifact=(
                                None
                                if analysis is None
                                else self._artifact_from_row(analysis)
                            ),
                            note_artifact=self._artifact_from_row(note),
                        )
                    )
            return tuple(candidates)
        finally:
            connection.close()

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> SourceSubscriptionRecord:
        return SourceSubscriptionRecord(
            source_id=str(row["source_id"]),
            source_type=SourceType(row["source_type"]),
            canonical_url=str(row["canonical_url"]),
            channel_id=row["channel_id"],
            video_id=row["video_id"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            processing_policy=ProcessingPolicy(row["processing_policy"]),
            last_checked_at=SQLiteStateRepository._optional_datetime(
                row["last_checked_at"]
            ),
            last_success_at=SQLiteStateRepository._optional_datetime(
                row["last_success_at"]
            ),
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _schedule_from_row(row: sqlite3.Row) -> AutomationScheduleRecord:
        return AutomationScheduleRecord(
            schedule_id=str(row["schedule_id"]),
            target_type=AutomationTargetType(row["target_type"]),
            target_id=row["target_id"],
            frequency=ScheduleFrequency(row["frequency"]),
            weekday=row["weekday"],
            local_time=row["local_time"],
            timezone=str(row["timezone"]),
            enabled=bool(row["enabled"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _automation_run_from_row(row: sqlite3.Row) -> AutomationRunRecord:
        return AutomationRunRecord(
            run_id=str(row["run_id"]),
            schedule_id=str(row["schedule_id"]),
            target_type=AutomationTargetType(row["target_type"]),
            target_id=row["target_id"],
            scheduled_for=_parse_utc_datetime(str(row["scheduled_for"])),
            claimed_at=_parse_utc_datetime(str(row["claimed_at"])),
            started_at=SQLiteStateRepository._optional_datetime(row["started_at"]),
            finished_at=SQLiteStateRepository._optional_datetime(row["finished_at"]),
            status=AutomationRunStatus(row["status"]),
            error_code=row["error_code"],
            error_message=row["error_message"],
            result_summary=row["result_summary"],
        )

    def create_source_subscription(
        self, source: SourceSubscriptionRecord
    ) -> SourceSubscriptionRecord:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO source_subscriptions (source_id, source_type, canonical_url, channel_id, video_id, display_name, enabled, processing_policy, last_checked_at, last_success_at, last_error_code, last_error_message, created_at, updated_at) "
                    "VALUES (:source_id, :source_type, :canonical_url, :channel_id, :video_id, :display_name, :enabled, :processing_policy, NULL, NULL, NULL, NULL, :created_at, :updated_at)",
                    {
                        "source_id": source.source_id,
                        "source_type": source.source_type.value,
                        "canonical_url": source.canonical_url,
                        "channel_id": source.channel_id,
                        "video_id": source.video_id,
                        "display_name": source.display_name,
                        "enabled": int(source.enabled),
                        "processing_policy": source.processing_policy.value,
                        "created_at": format_utc_datetime(source.created_at),
                        "updated_at": format_utc_datetime(source.updated_at),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM source_subscriptions WHERE source_id = :source_id",
                    {"source_id": source.source_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("source subscription was not saved")
                return self._source_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict(
                "source subscription identity already exists"
            ) from error
        finally:
            connection.close()

    def get_source_subscription(
        self, source_id: str
    ) -> SourceSubscriptionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM source_subscriptions WHERE source_id = :source_id",
                {"source_id": source_id},
            ).fetchone()
            return None if row is None else self._source_from_row(row)
        finally:
            connection.close()

    def get_source_by_canonical_url(
        self, canonical_url: str
    ) -> SourceSubscriptionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM source_subscriptions WHERE canonical_url = :canonical_url",
                {"canonical_url": canonical_url},
            ).fetchone()
            return None if row is None else self._source_from_row(row)
        finally:
            connection.close()

    def list_source_subscriptions(self) -> tuple[SourceSubscriptionRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._source_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM source_subscriptions ORDER BY created_at DESC, source_id"
                )
            )
        finally:
            connection.close()

    def update_source_subscription(
        self,
        source_id: str,
        *,
        enabled: bool | None = None,
        processing_policy: ProcessingPolicy | None = None,
        now: datetime,
    ) -> SourceSubscriptionRecord | None:
        if enabled is None and processing_policy is None:
            raise ValueError("a source change is required")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM source_subscriptions WHERE source_id = :source_id",
                    {"source_id": source_id},
                ).fetchone()
                if row is None:
                    return None
                connection.execute(
                    "UPDATE source_subscriptions SET enabled = :enabled, processing_policy = :policy, updated_at = :updated_at WHERE source_id = :source_id",
                    {
                        "source_id": source_id,
                        "enabled": int(
                            bool(row["enabled"]) if enabled is None else enabled
                        ),
                        "policy": str(row["processing_policy"])
                        if processing_policy is None
                        else processing_policy.value,
                        "updated_at": format_utc_datetime(now),
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM source_subscriptions WHERE source_id = :source_id",
                    {"source_id": source_id},
                ).fetchone()
                return None if saved is None else self._source_from_row(saved)
        finally:
            connection.close()

    def record_source_check(
        self,
        source_id: str,
        *,
        now: datetime,
        succeeded: bool,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> SourceSubscriptionRecord | None:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE source_subscriptions SET last_checked_at=:now, last_success_at=CASE WHEN :succeeded THEN :now ELSE last_success_at END, last_error_code=:error_code, last_error_message=:error_message, updated_at=:now WHERE source_id=:source_id",
                    {
                        "source_id": source_id,
                        "now": format_utc_datetime(now),
                        "succeeded": int(succeeded),
                        "error_code": error_code,
                        "error_message": error_message,
                    },
                ).rowcount
                if changed != 1:
                    return None
                row = connection.execute(
                    "SELECT * FROM source_subscriptions WHERE source_id=:source_id",
                    {"source_id": source_id},
                ).fetchone()
                return None if row is None else self._source_from_row(row)
        finally:
            connection.close()

    def link_source_video(
        self, source_id: str, video_id: str, *, discovered_at: datetime
    ) -> None:
        """Record source membership without changing VideoRecord authority."""
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO source_video_links (source_id, video_id, discovered_at) "
                    "VALUES (:source_id, :video_id, :discovered_at) "
                    "ON CONFLICT(source_id, video_id) DO NOTHING",
                    {
                        "source_id": source_id,
                        "video_id": video_id,
                        "discovered_at": format_utc_datetime(discovered_at),
                    },
                )
        finally:
            connection.close()

    def list_source_videos(
        self, source_id: str, *, limit: int = 10
    ) -> tuple[VideoRecord, ...]:
        """Read source membership joined to VideoRecord in one query."""

        if not source_id.strip() or limit <= 0 or limit > 100:
            raise ValueError("source video query arguments are invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT v.* FROM source_video_links AS link "
                "JOIN videos AS v ON v.video_id = link.video_id "
                "WHERE link.source_id = :source_id "
                "ORDER BY link.discovered_at DESC, v.video_id DESC LIMIT :limit",
                {"source_id": source_id, "limit": limit},
            ).fetchall()
            return tuple(self._video_from_row(row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _policy_rules_from_json(value: object) -> tuple[str, ...]:
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError) as error:
            raise StateStoreError("stored source policy rules are invalid") from error
        if not isinstance(parsed, list) or not all(
            isinstance(rule, str) for rule in parsed
        ):
            raise StateStoreError("stored source policy rules are invalid")
        return tuple(parsed)

    @staticmethod
    def _source_policy_revision_from_row(
        row: sqlite3.Row,
    ) -> SourcePolicyRevisionRecord:
        return SourcePolicyRevisionRecord(
            revision_id=str(row["revision_id"]),
            policy_scope=str(row["policy_scope"]),
            source_id=(
                None if row["source_id"] is None else str(row["source_id"])
            ),
            initial_history_count=(
                None
                if row["initial_history_count"] is None
                else int(row["initial_history_count"])
            ),
            per_run_max_new_videos=(
                None
                if row["per_run_max_new_videos"] is None
                else int(row["per_run_max_new_videos"])
            ),
            focus_mode=PolicyOverrideMode(str(row["focus_mode"])),
            focus_rules=SQLiteStateRepository._policy_rules_from_json(
                row["focus_rules_json"]
            ),
            ignore_mode=PolicyOverrideMode(str(row["ignore_mode"])),
            ignore_rules=SQLiteStateRepository._policy_rules_from_json(
                row["ignore_rules_json"]
            ),
            distillation_style_mode=PolicyOverrideMode(
                str(row["distillation_style_mode"])
            ),
            distillation_style=(
                None
                if row["distillation_style"] is None
                else DistillationStyle(str(row["distillation_style"]))
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _filter_decision_from_row(row: sqlite3.Row) -> FilterDecisionRecord:
        return FilterDecisionRecord(
            decision_id=str(row["decision_id"]),
            source_id=str(row["source_id"]),
            video_id=str(row["video_id"]),
            stage=FilterStage(str(row["stage"])),
            outcome=FilterOutcome(str(row["outcome"])),
            reason=FilterReason(str(row["reason"])),
            global_policy_revision_id=str(row["global_policy_revision_id"]),
            source_policy_revision_id=(
                None
                if row["source_policy_revision_id"] is None
                else str(row["source_policy_revision_id"])
            ),
            manual_override_id=(
                None
                if row["manual_override_id"] is None
                else str(row["manual_override_id"])
            ),
            prior_decision_id=(
                None
                if row["prior_decision_id"] is None
                else str(row["prior_decision_id"])
            ),
            evaluated_at=_parse_utc_datetime(str(row["evaluated_at"])),
        )

    @staticmethod
    def _validate_policy_rules(rules: tuple[str, ...], *, field_name: str) -> None:
        if len(rules) > 20:
            raise ValueError(f"{field_name} allows at most 20 rules")
        normalized: set[str] = set()
        for rule in rules:
            if (
                not isinstance(rule, str)
                or not rule.strip()
                or rule != rule.strip()
                or len(rule) > 160
            ):
                raise ValueError(f"{field_name} contains an invalid rule")
            folded = rule.casefold()
            if folded in normalized:
                raise ValueError(f"{field_name} cannot contain duplicate rules")
            normalized.add(folded)

    @staticmethod
    def _validate_source_policy_revision(
        revision: SourcePolicyRevisionWrite,
    ) -> None:
        if (
            not revision.revision_id.strip()
            or revision.revision_id != revision.revision_id.strip()
            or len(revision.revision_id) > 512
        ):
            raise ValueError("source policy revision identity is invalid")
        if revision.policy_scope not in {"GLOBAL", "SOURCE"}:
            raise ValueError("source policy scope must be finite")
        if not isinstance(revision.focus_mode, PolicyOverrideMode) or not isinstance(
            revision.ignore_mode, PolicyOverrideMode
        ) or not isinstance(revision.distillation_style_mode, PolicyOverrideMode):
            raise ValueError("source policy override mode must be finite")
        if (
            isinstance(revision.initial_history_count, bool)
            or revision.initial_history_count not in {None, 0, 1, 3, 5, 10}
        ):
            raise ValueError("initial history count must be one of the V1 values")
        if (
            isinstance(revision.per_run_max_new_videos, bool)
            or revision.per_run_max_new_videos not in {None, 1, 3, 5, 10}
        ):
            raise ValueError("per-run new video limit must be one of the V1 values")
        SQLiteStateRepository._validate_policy_rules(
            revision.focus_rules, field_name="focus rules"
        )
        SQLiteStateRepository._validate_policy_rules(
            revision.ignore_rules, field_name="ignore rules"
        )
        if revision.policy_scope == "GLOBAL":
            if (
                revision.source_id is not None
                or revision.initial_history_count is None
                or revision.per_run_max_new_videos is None
                or revision.focus_mode is not PolicyOverrideMode.OVERRIDE
                or revision.ignore_mode is not PolicyOverrideMode.OVERRIDE
                or revision.distillation_style_mode is not PolicyOverrideMode.OVERRIDE
                or not isinstance(revision.distillation_style, DistillationStyle)
            ):
                raise ValueError("global source policy requires complete finite values")
        else:
            if (
                revision.source_id is None
                or not revision.source_id.strip()
                or len(revision.source_id) > 512
            ):
                raise ValueError("source policy requires a source identity")
            if (
                revision.focus_mode is PolicyOverrideMode.INHERIT
                and revision.focus_rules
            ) or (
                revision.ignore_mode is PolicyOverrideMode.INHERIT
                and revision.ignore_rules
            ):
                raise ValueError("inherited source rules cannot carry rule values")
            if (
                revision.distillation_style_mode is PolicyOverrideMode.INHERIT
                and revision.distillation_style is not None
            ) or (
                revision.distillation_style_mode is PolicyOverrideMode.OVERRIDE
                and not isinstance(revision.distillation_style, DistillationStyle)
            ):
                raise ValueError("source distillation style override is invalid")
        format_utc_datetime(revision.created_at)

    def get_global_source_policy_revision(self) -> SourcePolicyRevisionRecord:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT revision.* FROM source_policy_current AS current "
                "JOIN source_policy_revisions AS revision "
                "ON revision.revision_id = current.revision_id "
                "WHERE current.policy_key = 'GLOBAL'"
            ).fetchone()
            if row is None:
                raise StateStoreError("global source policy is not initialized")
            return self._source_policy_revision_from_row(row)
        finally:
            connection.close()

    def get_source_policy_revision(
        self, source_id: str
    ) -> SourcePolicyRevisionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT revision.* FROM source_policy_current AS current "
                "JOIN source_policy_revisions AS revision "
                "ON revision.revision_id = current.revision_id "
                "WHERE current.policy_key = :policy_key",
                {"policy_key": f"SOURCE:{source_id}"},
            ).fetchone()
            return None if row is None else self._source_policy_revision_from_row(row)
        finally:
            connection.close()

    def create_source_policy_revision(
        self, revision: SourcePolicyRevisionWrite
    ) -> SourcePolicyRevisionRecord:
        self._validate_source_policy_revision(revision)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM source_policy_revisions WHERE revision_id = :revision_id",
                    {"revision_id": revision.revision_id},
                ).fetchone()
                if existing is not None:
                    saved = self._source_policy_revision_from_row(existing)
                    if (
                        saved.policy_scope == revision.policy_scope
                        and saved.source_id == revision.source_id
                        and saved.initial_history_count == revision.initial_history_count
                        and saved.per_run_max_new_videos
                        == revision.per_run_max_new_videos
                        and saved.focus_mode is revision.focus_mode
                        and saved.focus_rules == revision.focus_rules
                        and saved.ignore_mode is revision.ignore_mode
                        and saved.ignore_rules == revision.ignore_rules
                        and saved.distillation_style_mode
                        is revision.distillation_style_mode
                        and saved.distillation_style is revision.distillation_style
                    ):
                        return saved
                    raise IntegrityConflict("source policy command identity conflicts")
                connection.execute(
                    "INSERT INTO source_policy_revisions "
                    "(revision_id, policy_scope, source_id, initial_history_count, "
                    "per_run_max_new_videos, focus_mode, focus_rules_json, ignore_mode, "
                    "ignore_rules_json, distillation_style_mode, distillation_style, created_at) "
                    "VALUES (:revision_id, :policy_scope, :source_id, :initial_history_count, "
                    ":per_run_max_new_videos, :focus_mode, :focus_rules_json, :ignore_mode, "
                    ":ignore_rules_json, :distillation_style_mode, :distillation_style, :created_at)",
                    {
                        "revision_id": revision.revision_id,
                        "policy_scope": revision.policy_scope,
                        "source_id": revision.source_id,
                        "initial_history_count": revision.initial_history_count,
                        "per_run_max_new_videos": revision.per_run_max_new_videos,
                        "focus_mode": revision.focus_mode.value,
                        "focus_rules_json": json.dumps(
                            revision.focus_rules,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        "ignore_mode": revision.ignore_mode.value,
                        "ignore_rules_json": json.dumps(
                            revision.ignore_rules,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        "distillation_style_mode": revision.distillation_style_mode.value,
                        "distillation_style": (
                            None
                            if revision.distillation_style is None
                            else revision.distillation_style.value
                        ),
                        "created_at": format_utc_datetime(revision.created_at),
                    },
                )
                policy_key = (
                    "GLOBAL"
                    if revision.policy_scope == "GLOBAL"
                    else f"SOURCE:{revision.source_id}"
                )
                connection.execute(
                    "INSERT INTO source_policy_current "
                    "(policy_key, policy_scope, source_id, revision_id) "
                    "VALUES (:policy_key, :policy_scope, :source_id, :revision_id) "
                    "ON CONFLICT(policy_key) DO UPDATE SET revision_id = excluded.revision_id",
                    {
                        "policy_key": policy_key,
                        "policy_scope": revision.policy_scope,
                        "source_id": revision.source_id,
                        "revision_id": revision.revision_id,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM source_policy_revisions WHERE revision_id = :revision_id",
                    {"revision_id": revision.revision_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("source policy revision was not saved")
                return self._source_policy_revision_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("source policy violates its finite contract") from error
        finally:
            connection.close()

    @staticmethod
    def _validate_filter_decision(decision: FilterDecisionWrite) -> None:
        if (
            not decision.decision_id.strip()
            or decision.decision_id != decision.decision_id.strip()
            or len(decision.decision_id) > 512
            or not decision.source_id.strip()
            or not decision.video_id.strip()
        ):
            raise ValueError("filter decision identity is invalid")
        if not isinstance(decision.stage, FilterStage) or not isinstance(
            decision.outcome, FilterOutcome
        ) or not isinstance(decision.reason, FilterReason):
            raise ValueError("filter decision fields must be finite")
        stage_contract = {
            (FilterStage.STAGE_1, FilterOutcome.RELEVANT): {
                FilterReason.FOCUS_MATCH
            },
            (FilterStage.STAGE_1, FilterOutcome.NOT_RELEVANT): {
                FilterReason.IGNORE_RULE_MATCH,
                FilterReason.SHORT_VIDEO,
                FilterReason.NO_FOCUS_MATCH,
            },
            (FilterStage.STAGE_1, FilterOutcome.UNCERTAIN): {
                FilterReason.INSUFFICIENT_METADATA,
                FilterReason.NO_FOCUS_RULES,
            },
            (FilterStage.STAGE_2, FilterOutcome.RELEVANT): {
                FilterReason.STAGE_TWO_REVIEW
            },
            (FilterStage.STAGE_2, FilterOutcome.NOT_RELEVANT): {
                FilterReason.STAGE_TWO_REVIEW
            },
            (FilterStage.MANUAL_OVERRIDE, FilterOutcome.RELEVANT): {
                FilterReason.MANUAL_ANALYZE
            },
        }
        if decision.reason not in stage_contract.get(
            (decision.stage, decision.outcome), set()
        ):
            raise ValueError("filter outcome and reason are not an approved pair")
        if decision.stage is FilterStage.MANUAL_OVERRIDE:
            if decision.manual_override_id is None or decision.prior_decision_id is None:
                raise ValueError("manual override decision requires immutable context")
        elif (
            decision.manual_override_id is not None
            or decision.prior_decision_id is not None
        ):
            raise ValueError("automated filter decision cannot carry manual context")
        format_utc_datetime(decision.evaluated_at)

    def append_filter_decision(self, decision: FilterDecisionWrite) -> FilterDecisionRecord:
        self._validate_filter_decision(decision)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO source_video_filter_decisions "
                    "(decision_id, source_id, video_id, stage, outcome, reason, "
                    "global_policy_revision_id, source_policy_revision_id, "
                    "manual_override_id, prior_decision_id, evaluated_at) "
                    "VALUES (:decision_id, :source_id, :video_id, :stage, :outcome, "
                    ":reason, :global_policy_revision_id, :source_policy_revision_id, "
                    ":manual_override_id, :prior_decision_id, :evaluated_at)",
                    {
                        "decision_id": decision.decision_id,
                        "source_id": decision.source_id,
                        "video_id": decision.video_id,
                        "stage": decision.stage.value,
                        "outcome": decision.outcome.value,
                        "reason": decision.reason.value,
                        "global_policy_revision_id": decision.global_policy_revision_id,
                        "source_policy_revision_id": decision.source_policy_revision_id,
                        "manual_override_id": decision.manual_override_id,
                        "prior_decision_id": decision.prior_decision_id,
                        "evaluated_at": format_utc_datetime(decision.evaluated_at),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM source_video_filter_decisions "
                    "WHERE decision_id = :decision_id",
                    {"decision_id": decision.decision_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("filter decision was not saved")
                return self._filter_decision_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("filter decision violates its finite audit contract") from error
        finally:
            connection.close()

    def list_filter_decisions(
        self, source_id: str, video_id: str
    ) -> tuple[FilterDecisionRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM source_video_filter_decisions "
                "WHERE source_id = :source_id AND video_id = :video_id "
                "ORDER BY decision_order ASC",
                {"source_id": source_id, "video_id": video_id},
            ).fetchall()
            return tuple(self._filter_decision_from_row(row) for row in rows)
        finally:
            connection.close()

    def current_filter_decision(
        self, source_id: str, video_id: str
    ) -> FilterDecisionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM source_video_filter_decisions "
                "WHERE source_id = :source_id AND video_id = :video_id "
                "ORDER BY decision_order DESC LIMIT 1",
                {"source_id": source_id, "video_id": video_id},
            ).fetchone()
            return None if row is None else self._filter_decision_from_row(row)
        finally:
            connection.close()

    def filter_decision_for_manual_override(
        self, override_id: str
    ) -> FilterDecisionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM source_video_filter_decisions "
                "WHERE manual_override_id = :override_id",
                {"override_id": override_id},
            ).fetchone()
            return None if row is None else self._filter_decision_from_row(row)
        finally:
            connection.close()

    def record_manual_analyze_override(
        self,
        override: ManualAnalyzeOverrideWrite,
        decision: FilterDecisionWrite,
    ) -> FilterDecisionRecord:
        self._validate_filter_decision(decision)
        if (
            decision.stage is not FilterStage.MANUAL_OVERRIDE
            or decision.manual_override_id != override.override_id
            or decision.prior_decision_id != override.prior_decision_id
            or decision.source_id != override.source_id
            or decision.video_id != override.video_id
            or not override.command_id.strip()
            or len(override.command_id) > 512
        ):
            raise ValueError("manual analyze override is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM manual_analyze_overrides "
                    "WHERE source_id = :source_id AND video_id = :video_id "
                    "AND command_id = :command_id",
                    {
                        "source_id": override.source_id,
                        "video_id": override.video_id,
                        "command_id": override.command_id,
                    },
                ).fetchone()
                if existing is not None:
                    if (
                        str(existing["override_id"]) != override.override_id
                        or str(existing["prior_decision_id"])
                        != override.prior_decision_id
                    ):
                        raise IntegrityConflict("manual analyze command identity conflicts")
                    row = connection.execute(
                        "SELECT * FROM source_video_filter_decisions "
                        "WHERE manual_override_id = :override_id",
                        {"override_id": override.override_id},
                    ).fetchone()
                    if row is None:
                        raise StateStoreError("manual analyze override lacks its decision")
                    return self._filter_decision_from_row(row)
                prior = connection.execute(
                    "SELECT * FROM source_video_filter_decisions "
                    "WHERE decision_id = :decision_id",
                    {"decision_id": override.prior_decision_id},
                ).fetchone()
                if (
                    prior is None
                    or str(prior["source_id"]) != override.source_id
                    or str(prior["video_id"]) != override.video_id
                    or str(prior["outcome"]) != FilterOutcome.NOT_RELEVANT.value
                ):
                    raise ValueError("manual analyze requires a currently skipped video")
                current = connection.execute(
                    "SELECT decision_id FROM source_video_filter_decisions "
                    "WHERE source_id = :source_id AND video_id = :video_id "
                    "ORDER BY decision_order DESC LIMIT 1",
                    {"source_id": override.source_id, "video_id": override.video_id},
                ).fetchone()
                if current is None or str(current["decision_id"]) != override.prior_decision_id:
                    raise ValueError("manual analyze requires a currently skipped video")
                connection.execute(
                    "INSERT INTO manual_analyze_overrides "
                    "(override_id, source_id, video_id, command_id, prior_decision_id, created_at) "
                    "VALUES (:override_id, :source_id, :video_id, :command_id, "
                    ":prior_decision_id, :created_at)",
                    {
                        "override_id": override.override_id,
                        "source_id": override.source_id,
                        "video_id": override.video_id,
                        "command_id": override.command_id,
                        "prior_decision_id": override.prior_decision_id,
                        "created_at": format_utc_datetime(override.created_at),
                    },
                )
                connection.execute(
                    "INSERT INTO source_video_filter_decisions "
                    "(decision_id, source_id, video_id, stage, outcome, reason, "
                    "global_policy_revision_id, source_policy_revision_id, "
                    "manual_override_id, prior_decision_id, evaluated_at) "
                    "VALUES (:decision_id, :source_id, :video_id, :stage, :outcome, "
                    ":reason, :global_policy_revision_id, :source_policy_revision_id, "
                    ":manual_override_id, :prior_decision_id, :evaluated_at)",
                    {
                        "decision_id": decision.decision_id,
                        "source_id": decision.source_id,
                        "video_id": decision.video_id,
                        "stage": decision.stage.value,
                        "outcome": decision.outcome.value,
                        "reason": decision.reason.value,
                        "global_policy_revision_id": decision.global_policy_revision_id,
                        "source_policy_revision_id": decision.source_policy_revision_id,
                        "manual_override_id": decision.manual_override_id,
                        "prior_decision_id": decision.prior_decision_id,
                        "evaluated_at": format_utc_datetime(decision.evaluated_at),
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM source_video_filter_decisions "
                    "WHERE decision_id = :decision_id",
                    {"decision_id": decision.decision_id},
                ).fetchone()
                if saved is None:
                    raise StateStoreError("manual analyze decision was not saved")
                return self._filter_decision_from_row(saved)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("manual analyze override violates its audit contract") from error
        finally:
            connection.close()

    def create_or_update_schedule(
        self, schedule: AutomationScheduleRecord
    ) -> AutomationScheduleRecord:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO automation_schedules (schedule_id, target_type, target_id, frequency, weekday, local_time, timezone, enabled, created_at, updated_at) VALUES (:schedule_id, :target_type, :target_id, :frequency, :weekday, :local_time, :timezone, :enabled, :created_at, :updated_at) ON CONFLICT(target_type, target_id) DO UPDATE SET frequency=excluded.frequency, weekday=excluded.weekday, local_time=excluded.local_time, timezone=excluded.timezone, enabled=excluded.enabled, updated_at=excluded.updated_at",
                    {
                        "schedule_id": schedule.schedule_id,
                        "target_type": schedule.target_type.value,
                        "target_id": schedule.target_id,
                        "frequency": schedule.frequency.value,
                        "weekday": schedule.weekday,
                        "local_time": schedule.local_time,
                        "timezone": schedule.timezone,
                        "enabled": int(schedule.enabled),
                        "created_at": format_utc_datetime(schedule.created_at),
                        "updated_at": format_utc_datetime(schedule.updated_at),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM automation_schedules WHERE target_type = :target_type AND target_id IS :target_id",
                    {
                        "target_type": schedule.target_type.value,
                        "target_id": schedule.target_id,
                    },
                ).fetchone()
                if row is None:
                    raise StateStoreError("automation schedule was not saved")
                return self._schedule_from_row(row)
        finally:
            connection.close()

    def list_automation_schedules(self) -> tuple[AutomationScheduleRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._schedule_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM automation_schedules ORDER BY created_at, schedule_id"
                )
            )
        finally:
            connection.close()

    def claim_automation_run(self, *, run: AutomationRunRecord) -> bool:
        """Atomically claim one stable schedule occurrence; False means another tick won."""
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                result = connection.execute(
                    "INSERT INTO automation_runs (run_id, schedule_id, target_type, target_id, scheduled_for, claimed_at, status) VALUES (:run_id, :schedule_id, :target_type, :target_id, :scheduled_for, :claimed_at, :status) ON CONFLICT(schedule_id, scheduled_for) DO NOTHING",
                    {
                        "run_id": run.run_id,
                        "schedule_id": run.schedule_id,
                        "target_type": run.target_type.value,
                        "target_id": run.target_id,
                        "scheduled_for": format_utc_datetime(run.scheduled_for),
                        "claimed_at": format_utc_datetime(run.claimed_at),
                        "status": AutomationRunStatus.CLAIMED.value,
                    },
                )
                return result.rowcount == 1
        finally:
            connection.close()

    def finish_automation_run(
        self,
        run_id: str,
        *,
        status: AutomationRunStatus,
        now: datetime,
        error_code: str | None = None,
        error_message: str | None = None,
        result_summary: str | None = None,
    ) -> AutomationRunRecord | None:
        if status not in {
            AutomationRunStatus.SUCCEEDED,
            AutomationRunStatus.FAILED_FINAL,
            AutomationRunStatus.BLOCKED,
        }:
            raise ValueError("automation run must finish in a terminal state")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "UPDATE automation_runs SET status=:status, finished_at=:finished_at, error_code=:error_code, error_message=:error_message, result_summary=:result_summary WHERE run_id=:run_id AND status IN ('CLAIMED', 'RUNNING')",
                    {
                        "run_id": run_id,
                        "status": status.value,
                        "finished_at": format_utc_datetime(now),
                        "error_code": error_code,
                        "error_message": error_message,
                        "result_summary": result_summary,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM automation_runs WHERE run_id=:run_id",
                    {"run_id": run_id},
                ).fetchone()
                return None if row is None else self._automation_run_from_row(row)
        finally:
            connection.close()

    def list_automation_runs(
        self, *, limit: int = 100
    ) -> tuple[AutomationRunRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._automation_run_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM automation_runs ORDER BY scheduled_for DESC, run_id DESC LIMIT :limit",
                    {"limit": limit},
                )
            )
        finally:
            connection.close()

    def save_global_model_preference(
        self, *, desired_provider: str | None, desired_model: str | None, now: datetime
    ) -> GlobalModelPreferenceRecord:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO global_model_preferences (preference_key, desired_provider, desired_model, updated_at) VALUES ('deep_analysis', :provider, :model, :updated_at) ON CONFLICT(preference_key) DO UPDATE SET desired_provider=excluded.desired_provider, desired_model=excluded.desired_model, updated_at=excluded.updated_at",
                    {
                        "provider": desired_provider,
                        "model": desired_model,
                        "updated_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM global_model_preferences WHERE preference_key='deep_analysis'"
                ).fetchone()
                if row is None:
                    raise StateStoreError("model preference was not saved")
                return GlobalModelPreferenceRecord(
                    row["desired_provider"],
                    row["desired_model"],
                    _parse_utc_datetime(str(row["updated_at"])),
                )
        finally:
            connection.close()

    def get_global_model_preference(self) -> GlobalModelPreferenceRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM global_model_preferences WHERE preference_key='deep_analysis'"
            ).fetchone()
            return (
                None
                if row is None
                else GlobalModelPreferenceRecord(
                    row["desired_provider"],
                    row["desired_model"],
                    _parse_utc_datetime(str(row["updated_at"])),
                )
            )
        finally:
            connection.close()

    @staticmethod
    def _preference_from_row(row: sqlite3.Row) -> PreferenceRecord:
        return PreferenceRecord(
            preference_id=str(row["preference_id"]),
            horizon=PreferenceHorizon(str(row["horizon"])),
            provenance=PreferenceProvenance(str(row["provenance"])),
            scope=PreferenceScope(str(row["scope"])),
            target_id=None if row["target_id"] is None else str(row["target_id"]),
            statement=str(row["statement"]),
            starts_at=SQLiteStateRepository._optional_datetime(row["starts_at"]),
            expires_at=SQLiteStateRepository._optional_datetime(row["expires_at"]),
            supersedes_preference_id=(
                None
                if row["supersedes_preference_id"] is None
                else str(row["supersedes_preference_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _preference_state_event_from_row(
        row: sqlite3.Row,
    ) -> PreferenceStateEventRecord:
        return PreferenceStateEventRecord(
            state_event_id=str(row["state_event_id"]),
            preference_id=str(row["preference_id"]),
            state=PreferenceState(str(row["state"])),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _feedback_from_row(row: sqlite3.Row) -> FeedbackRecord:
        return FeedbackRecord(
            feedback_id=str(row["feedback_id"]),
            kind=FeedbackKind(str(row["kind"])),
            scope=PreferenceScope(str(row["scope"])),
            target_id=None if row["target_id"] is None else str(row["target_id"]),
            content=None if row["content"] is None else str(row["content"]),
            correction_kind=(
                None
                if row["correction_kind"] is None
                else FeedbackCorrectionKind(str(row["correction_kind"]))
            ),
            effect_status=str(row["effect_status"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _validate_target(
        *, scope: PreferenceScope, target_id: str | None
    ) -> None:
        targeted = {
            PreferenceScope.SOURCE_CONTENT,
            PreferenceScope.VIDEO_CONTENT,
            PreferenceScope.INTELLIGENCE_CONTENT,
        }
        if not isinstance(scope, PreferenceScope):
            raise ValueError("preference scope must be finite")
        if scope in targeted:
            if target_id is None or not target_id.strip() or len(target_id) > 2048:
                raise ValueError("targeted preference scope requires a target identity")
        elif target_id is not None:
            raise ValueError("global preference scope cannot have a target identity")

    @staticmethod
    def _validate_preference_write(preference: PreferenceWrite) -> None:
        if not preference.preference_id.strip() or len(preference.preference_id) > 2048:
            raise ValueError("preference identity is invalid")
        if not preference.statement.strip() or len(preference.statement) > 2048:
            raise ValueError("preference statement is invalid")
        if not isinstance(preference.horizon, PreferenceHorizon) or not isinstance(
            preference.provenance, PreferenceProvenance
        ):
            raise ValueError("preference horizon and provenance must be finite")
        SQLiteStateRepository._validate_target(
            scope=preference.scope, target_id=preference.target_id
        )
        if preference.horizon is PreferenceHorizon.LONG_TERM:
            if (
                preference.provenance is not PreferenceProvenance.EXPLICIT
                or preference.starts_at is not None
                or preference.expires_at is not None
            ):
                raise ValueError("long-term preference must be explicit and non-expiring")
        elif preference.horizon is PreferenceHorizon.RECENT:
            if (
                preference.provenance is not PreferenceProvenance.DERIVED
                or preference.starts_at is not None
                or preference.expires_at is not None
            ):
                raise ValueError("recent preference must be derived and non-expiring")
        elif preference.horizon is PreferenceHorizon.TEMPORARY_FOCUS:
            if (
                preference.provenance is not PreferenceProvenance.TEMPORARY
                or preference.starts_at is None
                or preference.expires_at is None
            ):
                raise ValueError("temporary focus requires temporary provenance and expiry")
            format_utc_datetime(preference.starts_at)
            format_utc_datetime(preference.expires_at)
            if preference.expires_at <= preference.starts_at:
                raise ValueError("temporary focus expiry must be after its effective time")
        else:
            raise ValueError("preference horizon must be finite")

    def create_preference(
        self,
        preference: PreferenceWrite,
        *,
        activation_event_id: str,
        now: datetime,
    ) -> PreferenceRecord:
        self._validate_preference_write(preference)
        if not activation_event_id.strip() or len(activation_event_id) > 2048:
            raise ValueError("preference state event identity is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM preferences WHERE preference_id = :preference_id",
                    {"preference_id": preference.preference_id},
                ).fetchone()
                if existing is not None:
                    record = self._preference_from_row(existing)
                    if (
                        record.horizon is preference.horizon
                        and record.provenance is preference.provenance
                        and record.scope is preference.scope
                        and record.target_id == preference.target_id
                        and record.statement == preference.statement
                        and record.starts_at == preference.starts_at
                        and record.expires_at == preference.expires_at
                        and record.supersedes_preference_id
                        == preference.supersedes_preference_id
                    ):
                        return record
                    raise IntegrityConflict("preference command identity conflicts")
                connection.execute(
                    "INSERT INTO preferences (preference_id, horizon, provenance, scope, target_id, statement, starts_at, expires_at, supersedes_preference_id, created_at) "
                    "VALUES (:preference_id, :horizon, :provenance, :scope, :target_id, :statement, :starts_at, :expires_at, :supersedes_preference_id, :created_at)",
                    {
                        "preference_id": preference.preference_id,
                        "horizon": preference.horizon.value,
                        "provenance": preference.provenance.value,
                        "scope": preference.scope.value,
                        "target_id": preference.target_id,
                        "statement": preference.statement.strip(),
                        "starts_at": None
                        if preference.starts_at is None
                        else format_utc_datetime(preference.starts_at),
                        "expires_at": None
                        if preference.expires_at is None
                        else format_utc_datetime(preference.expires_at),
                        "supersedes_preference_id": preference.supersedes_preference_id,
                        "created_at": format_utc_datetime(now),
                    },
                )
                connection.execute(
                    "INSERT INTO preference_state_events (state_event_id, preference_id, state, created_at) "
                    "VALUES (:state_event_id, :preference_id, :state, :created_at)",
                    {
                        "state_event_id": activation_event_id,
                        "preference_id": preference.preference_id,
                        "state": PreferenceState.ACTIVATED.value,
                        "created_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM preferences WHERE preference_id = :preference_id",
                    {"preference_id": preference.preference_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("preference was not saved")
                return self._preference_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("preference violates its finite immutable contract") from error
        finally:
            connection.close()

    def get_preference(self, preference_id: str) -> PreferenceRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM preferences WHERE preference_id = :preference_id",
                {"preference_id": preference_id},
            ).fetchone()
            return None if row is None else self._preference_from_row(row)
        finally:
            connection.close()

    def list_preferences(self) -> tuple[PreferenceRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM preferences ORDER BY created_at ASC, preference_id ASC"
            ).fetchall()
            return tuple(self._preference_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_active_preferences(self, *, now: datetime) -> tuple[PreferenceRecord, ...]:
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT p.* FROM preferences AS p "
                "WHERE EXISTS (SELECT 1 FROM preference_state_events AS activated "
                "WHERE activated.preference_id = p.preference_id AND activated.state = 'ACTIVATED') "
                "AND NOT EXISTS (SELECT 1 FROM preference_state_events AS terminal "
                "WHERE terminal.preference_id = p.preference_id AND terminal.state IN ('REPLACED', 'DELETED')) "
                "AND (p.horizon != 'TEMPORARY_FOCUS' OR p.expires_at > :now) "
                "ORDER BY p.created_at ASC, p.preference_id ASC",
                {"now": timestamp},
            ).fetchall()
            return tuple(self._preference_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_preference_state_events(
        self, preference_id: str
    ) -> tuple[PreferenceStateEventRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM preference_state_events WHERE preference_id = :preference_id "
                "ORDER BY created_at ASC, state_event_id ASC",
                {"preference_id": preference_id},
            ).fetchall()
            return tuple(self._preference_state_event_from_row(row) for row in rows)
        finally:
            connection.close()

    def retire_preference(
        self,
        *,
        preference_id: str,
        state_event_id: str,
        state: PreferenceState,
        now: datetime,
    ) -> PreferenceStateEventRecord:
        if state not in {PreferenceState.REPLACED, PreferenceState.DELETED}:
            raise ValueError("preference retirement requires a terminal finite state")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM preference_state_events WHERE state_event_id = :state_event_id",
                    {"state_event_id": state_event_id},
                ).fetchone()
                if row is not None:
                    event = self._preference_state_event_from_row(row)
                    if event.preference_id == preference_id and event.state is state:
                        return event
                    raise IntegrityConflict("preference state command identity conflicts")
                connection.execute(
                    "INSERT INTO preference_state_events (state_event_id, preference_id, state, created_at) "
                    "VALUES (:state_event_id, :preference_id, :state, :created_at)",
                    {
                        "state_event_id": state_event_id,
                        "preference_id": preference_id,
                        "state": state.value,
                        "created_at": format_utc_datetime(now),
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM preference_state_events WHERE state_event_id = :state_event_id",
                    {"state_event_id": state_event_id},
                ).fetchone()
                if saved is None:
                    raise StateStoreError("preference state event was not saved")
                return self._preference_state_event_from_row(saved)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("preference state change violates immutable lifecycle") from error
        finally:
            connection.close()

    def replace_preference(
        self,
        preference: PreferenceWrite,
        *,
        activation_event_id: str,
        replacement_event_id: str,
        now: datetime,
    ) -> PreferenceRecord:
        """Atomically append a replacement and retire only its prior record."""
        self._validate_preference_write(preference)
        if preference.supersedes_preference_id is None:
            raise ValueError("preference replacement requires a prior preference identity")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM preferences WHERE preference_id = :preference_id",
                    {"preference_id": preference.preference_id},
                ).fetchone()
                if existing is not None:
                    record = self._preference_from_row(existing)
                    if (
                        record.horizon is preference.horizon
                        and record.provenance is preference.provenance
                        and record.scope is preference.scope
                        and record.target_id == preference.target_id
                        and record.statement == preference.statement
                        and record.starts_at == preference.starts_at
                        and record.expires_at == preference.expires_at
                        and record.supersedes_preference_id
                        == preference.supersedes_preference_id
                    ):
                        return record
                    raise IntegrityConflict("preference command identity conflicts")
                prior = connection.execute(
                    "SELECT * FROM preferences WHERE preference_id = :preference_id",
                    {"preference_id": preference.supersedes_preference_id},
                ).fetchone()
                if prior is None:
                    raise StateStoreError("preference to replace does not exist")
                terminal = connection.execute(
                    "SELECT 1 FROM preference_state_events WHERE preference_id = :preference_id "
                    "AND state IN ('REPLACED', 'DELETED')",
                    {"preference_id": preference.supersedes_preference_id},
                ).fetchone()
                if terminal is not None:
                    raise IntegrityConflict("preference to replace is not active")
                connection.execute(
                    "INSERT INTO preferences (preference_id, horizon, provenance, scope, target_id, statement, starts_at, expires_at, supersedes_preference_id, created_at) "
                    "VALUES (:preference_id, :horizon, :provenance, :scope, :target_id, :statement, :starts_at, :expires_at, :supersedes_preference_id, :created_at)",
                    {
                        "preference_id": preference.preference_id,
                        "horizon": preference.horizon.value,
                        "provenance": preference.provenance.value,
                        "scope": preference.scope.value,
                        "target_id": preference.target_id,
                        "statement": preference.statement.strip(),
                        "starts_at": None
                        if preference.starts_at is None
                        else format_utc_datetime(preference.starts_at),
                        "expires_at": None
                        if preference.expires_at is None
                        else format_utc_datetime(preference.expires_at),
                        "supersedes_preference_id": preference.supersedes_preference_id,
                        "created_at": format_utc_datetime(now),
                    },
                )
                connection.execute(
                    "INSERT INTO preference_state_events (state_event_id, preference_id, state, created_at) "
                    "VALUES (:state_event_id, :preference_id, 'REPLACED', :created_at)",
                    {
                        "state_event_id": replacement_event_id,
                        "preference_id": preference.supersedes_preference_id,
                        "created_at": format_utc_datetime(now),
                    },
                )
                connection.execute(
                    "INSERT INTO preference_state_events (state_event_id, preference_id, state, created_at) "
                    "VALUES (:state_event_id, :preference_id, 'ACTIVATED', :created_at)",
                    {
                        "state_event_id": activation_event_id,
                        "preference_id": preference.preference_id,
                        "created_at": format_utc_datetime(now),
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM preferences WHERE preference_id = :preference_id",
                    {"preference_id": preference.preference_id},
                ).fetchone()
                if saved is None:
                    raise StateStoreError("replacement preference was not saved")
                return self._preference_from_row(saved)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("preference replacement violates immutable lifecycle") from error
        finally:
            connection.close()

    @staticmethod
    def _validate_feedback_write(feedback: FeedbackWrite) -> None:
        if not feedback.feedback_id.strip() or len(feedback.feedback_id) > 2048:
            raise ValueError("feedback identity is invalid")
        if not isinstance(feedback.kind, FeedbackKind):
            raise ValueError("feedback kind must be finite")
        SQLiteStateRepository._validate_target(
            scope=feedback.scope, target_id=feedback.target_id
        )
        content = feedback.content
        if content is not None and (not content.strip() or len(content) > 2048):
            raise ValueError("feedback content is invalid")
        quick = {
            FeedbackKind.MORE_LIKE_THIS,
            FeedbackKind.LESS_LIKE_THIS,
            FeedbackKind.IMPORTANT,
        }
        text = {
            FeedbackKind.NATURAL_LANGUAGE,
            FeedbackKind.EXPLICIT_PREFERENCE_STATEMENT,
        }
        if feedback.kind in quick and (content is not None or feedback.correction_kind is not None):
            raise ValueError("quick feedback cannot carry configuration content")
        if feedback.kind in text and (content is None or feedback.correction_kind is not None):
            raise ValueError("natural-language feedback has an invalid correction boundary")
        if feedback.kind is FeedbackKind.FACTUAL_CORRECTION and (
            content is None
            or not isinstance(feedback.correction_kind, FeedbackCorrectionKind)
        ):
            raise ValueError("factual correction requires a finite correction kind")

    def record_feedback(self, feedback: FeedbackWrite, *, now: datetime) -> FeedbackRecord:
        self._validate_feedback_write(feedback)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM feedback_events WHERE feedback_id = :feedback_id",
                    {"feedback_id": feedback.feedback_id},
                ).fetchone()
                if existing is not None:
                    record = self._feedback_from_row(existing)
                    if (
                        record.kind is feedback.kind
                        and record.scope is feedback.scope
                        and record.target_id == feedback.target_id
                        and record.content == feedback.content
                        and record.correction_kind is feedback.correction_kind
                    ):
                        return record
                    raise IntegrityConflict("feedback command identity conflicts")
                connection.execute(
                    "INSERT INTO feedback_events (feedback_id, kind, scope, target_id, content, correction_kind, effect_status, created_at) "
                    "VALUES (:feedback_id, :kind, :scope, :target_id, :content, :correction_kind, 'RECORDED', :created_at)",
                    {
                        "feedback_id": feedback.feedback_id,
                        "kind": feedback.kind.value,
                        "scope": feedback.scope.value,
                        "target_id": feedback.target_id,
                        "content": None if feedback.content is None else feedback.content.strip(),
                        "correction_kind": None
                        if feedback.correction_kind is None
                        else feedback.correction_kind.value,
                        "created_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM feedback_events WHERE feedback_id = :feedback_id",
                    {"feedback_id": feedback.feedback_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("feedback event was not saved")
                return self._feedback_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("feedback violates its finite append-only contract") from error
        finally:
            connection.close()

    def list_feedback(self) -> tuple[FeedbackRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM feedback_events ORDER BY created_at ASC, rowid ASC"
            ).fetchall()
            return tuple(self._feedback_from_row(row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _evidence_from_row(row: sqlite3.Row) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=str(row["evidence_id"]),
            video_id=str(row["video_id"]),
            artifact_id=str(row["artifact_id"]),
            start_ms=int(row["start_ms"]),
            end_ms=int(row["end_ms"]),
            lineage_kind=EvidenceLineageKind(str(row["lineage_kind"])),
            role=EvidenceRole(str(row["role"])),
            language=str(row["language"]),
            availability=EvidenceAvailability(str(row["availability"])),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _intelligence_from_row(row: sqlite3.Row) -> IntelligenceRecord:
        return IntelligenceRecord(
            intelligence_id=str(row["intelligence_id"]),
            current_revision_id=(
                None
                if row["current_revision_id"] is None
                else str(row["current_revision_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _intelligence_revision_from_row(
        row: sqlite3.Row,
    ) -> IntelligenceRevisionRecord:
        return IntelligenceRevisionRecord(
            revision_id=str(row["revision_id"]),
            intelligence_id=str(row["intelligence_id"]),
            revision_number=int(row["revision_number"]),
            prior_revision_id=(
                None
                if row["prior_revision_id"] is None
                else str(row["prior_revision_id"])
            ),
            interpretation_kind=IntelligenceInterpretationKind(
                str(row["interpretation_kind"])
            ),
            claim_kind=IntelligenceClaimKind(str(row["claim_kind"])),
            content_hash=str(row["content_hash"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _intelligence_state_history_from_row(
        row: sqlite3.Row,
    ) -> IntelligenceStateHistoryRecord:
        return IntelligenceStateHistoryRecord(
            state_event_id=str(row["state_event_id"]),
            intelligence_id=str(row["intelligence_id"]),
            revision_id=str(row["revision_id"]),
            state=IntelligenceState(str(row["state"])),
            prior_state=(
                None
                if row["prior_state"] is None
                else IntelligenceState(str(row["prior_state"]))
            ),
            reason=str(row["reason"]),
            evidence_id=str(row["evidence_id"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _dependency_edge_from_row(row: sqlite3.Row) -> DependencyEdgeRecord:
        return DependencyEdgeRecord(
            edge_id=str(row["edge_id"]),
            dependent_revision_id=str(row["dependent_revision_id"]),
            relation=DependencyRelation(str(row["relation"])),
            input_evidence_id=(
                None
                if row["input_evidence_id"] is None
                else str(row["input_evidence_id"])
            ),
            input_revision_id=(
                None
                if row["input_revision_id"] is None
                else str(row["input_revision_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    def create_evidence(self, evidence: EvidenceWrite, *, now: datetime) -> EvidenceRecord:
        expected_id = build_evidence_id(
            video_id=evidence.video_id,
            artifact_id=evidence.artifact_id,
            start_ms=evidence.start_ms,
            end_ms=evidence.end_ms,
            lineage_kind=evidence.lineage_kind,
            role=evidence.role,
        )
        if evidence.evidence_id != expected_id:
            raise ValueError("evidence identity does not match its provenance")
        if not evidence.language.strip():
            raise ValueError("evidence language must be non-empty")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO evidence (evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, role, language, availability, created_at) "
                    "VALUES (:evidence_id, :video_id, :artifact_id, :start_ms, :end_ms, :lineage_kind, :role, :language, :availability, :created_at)",
                    {
                        "evidence_id": evidence.evidence_id,
                        "video_id": evidence.video_id,
                        "artifact_id": evidence.artifact_id,
                        "start_ms": evidence.start_ms,
                        "end_ms": evidence.end_ms,
                        "lineage_kind": evidence.lineage_kind.value,
                        "role": evidence.role.value,
                        "language": evidence.language,
                        "availability": evidence.availability.value,
                        "created_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM evidence WHERE evidence_id = :evidence_id",
                    {"evidence_id": evidence.evidence_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("evidence was not saved")
                return self._evidence_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("evidence identity or provenance is invalid") from error
        finally:
            connection.close()

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id = :evidence_id",
                {"evidence_id": evidence_id},
            ).fetchone()
            return None if row is None else self._evidence_from_row(row)
        finally:
            connection.close()

    def set_evidence_availability(
        self, *, evidence_id: str, availability: EvidenceAvailability
    ) -> EvidenceRecord:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE evidence SET availability = :availability WHERE evidence_id = :evidence_id",
                    {"evidence_id": evidence_id, "availability": availability.value},
                ).rowcount
                if changed != 1:
                    raise StateStoreError("evidence does not exist")
                row = connection.execute(
                    "SELECT * FROM evidence WHERE evidence_id = :evidence_id",
                    {"evidence_id": evidence_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("evidence availability was not saved")
                return self._evidence_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict(
                "current intelligence support must be resolved before evidence changes"
            ) from error
        finally:
            connection.close()

    def create_intelligence(
        self, *, intelligence_id: str, now: datetime
    ) -> IntelligenceRecord:
        if not intelligence_id.strip():
            raise ValueError("intelligence identity must be non-empty")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO intelligences (intelligence_id, current_revision_id, created_at) "
                    "VALUES (:intelligence_id, NULL, :created_at)",
                    {
                        "intelligence_id": intelligence_id,
                        "created_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM intelligences WHERE intelligence_id = :intelligence_id",
                    {"intelligence_id": intelligence_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("intelligence identity was not saved")
                return self._intelligence_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("intelligence identity already exists") from error
        finally:
            connection.close()

    def get_intelligence(self, intelligence_id: str) -> IntelligenceRecord:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM intelligences WHERE intelligence_id = :intelligence_id",
                {"intelligence_id": intelligence_id},
            ).fetchone()
            if row is None:
                raise StateStoreError("intelligence does not exist")
            return self._intelligence_from_row(row)
        finally:
            connection.close()

    def append_intelligence_revision(
        self,
        *,
        intelligence_id: str,
        revision: IntelligenceRevisionWrite,
        now: datetime,
    ) -> IntelligenceRevisionRecord:
        if not revision.revision_id.strip() or not revision.reason.strip():
            raise ValueError("revision identity and reason must be non-empty")
        if not isinstance(revision.claim_kind, IntelligenceClaimKind):
            raise ValueError("revision claim kind must be a finite claim kind")
        if revision.claim_kind is IntelligenceClaimKind.UNCLASSIFIED:
            raise ValueError("UNCLASSIFIED claim kind is reserved for migrated revisions")
        _validate_sha256(revision.content_hash, field_name="revision content_hash")
        evidence_ids = tuple(sorted(revision.evidence_ids))
        if not evidence_ids:
            raise ValueError("an intelligence revision requires evidence")
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("revision evidence identities must be unique")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                intelligence = connection.execute(
                    "SELECT * FROM intelligences WHERE intelligence_id = :intelligence_id",
                    {"intelligence_id": intelligence_id},
                ).fetchone()
                if intelligence is None:
                    raise StateStoreError("intelligence does not exist")
                evidence_rows = connection.execute(
                    "SELECT evidence_id, availability FROM evidence WHERE evidence_id IN ("
                    + ",".join("?" for _ in evidence_ids)
                    + ")",
                    evidence_ids,
                ).fetchall()
                found = {str(row["evidence_id"]): str(row["availability"]) for row in evidence_rows}
                missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in found]
                if missing:
                    raise StateStoreError("evidence does not exist")
                if any(found[evidence_id] != EvidenceAvailability.AVAILABLE.value for evidence_id in evidence_ids):
                    raise StateStoreError("unavailable evidence cannot support a current revision")
                prior_revision_id = intelligence["current_revision_id"]
                prior_state_row = (
                    None
                    if prior_revision_id is None
                    else connection.execute(
                        "SELECT state FROM intelligence_state_history WHERE revision_id = :revision_id",
                        {"revision_id": prior_revision_id},
                    ).fetchone()
                )
                if prior_revision_id is None and revision.state is not IntelligenceState.NEW:
                    raise StateStoreError("first intelligence revision must begin in NEW state")
                if prior_revision_id is not None and prior_state_row is None:
                    raise StateStoreError("current intelligence revision lacks state history")
                revision_number = int(
                    connection.execute(
                        "SELECT COALESCE(MAX(revision_number), 0) + 1 FROM intelligence_revisions WHERE intelligence_id = :intelligence_id",
                        {"intelligence_id": intelligence_id},
                    ).fetchone()[0]
                )
                connection.execute(
                    "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, claim_kind, content_hash, created_at) "
                    "VALUES (:revision_id, :intelligence_id, :revision_number, :prior_revision_id, :interpretation_kind, :claim_kind, :content_hash, :created_at)",
                    {
                        "revision_id": revision.revision_id,
                        "intelligence_id": intelligence_id,
                        "revision_number": revision_number,
                        "prior_revision_id": prior_revision_id,
                        "interpretation_kind": revision.interpretation_kind.value,
                        "claim_kind": revision.claim_kind.value,
                        "content_hash": revision.content_hash,
                        "created_at": format_utc_datetime(now),
                    },
                )
                for evidence_id in evidence_ids:
                    connection.execute(
                        "INSERT INTO intelligence_revision_evidence (revision_id, evidence_id) VALUES (:revision_id, :evidence_id)",
                        {"revision_id": revision.revision_id, "evidence_id": evidence_id},
                    )
                connection.execute(
                    "INSERT INTO intelligence_state_history (state_event_id, intelligence_id, revision_id, state, prior_state, reason, evidence_id, created_at) "
                    "VALUES (:state_event_id, :intelligence_id, :revision_id, :state, :prior_state, :reason, :evidence_id, :created_at)",
                    {
                        "state_event_id": f"state:{revision.revision_id}",
                        "intelligence_id": intelligence_id,
                        "revision_id": revision.revision_id,
                        "state": revision.state.value,
                        "prior_state": (
                            None if prior_state_row is None else str(prior_state_row["state"])
                        ),
                        "reason": revision.reason,
                        "evidence_id": evidence_ids[0],
                        "created_at": format_utc_datetime(now),
                    },
                )
                connection.execute(
                    "UPDATE intelligences SET current_revision_id = :revision_id WHERE intelligence_id = :intelligence_id",
                    {"revision_id": revision.revision_id, "intelligence_id": intelligence_id},
                )
                row = connection.execute(
                    "SELECT * FROM intelligence_revisions WHERE revision_id = :revision_id",
                    {"revision_id": revision.revision_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("intelligence revision was not saved")
                return self._intelligence_revision_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("intelligence revision violates its immutable contract") from error
        finally:
            connection.close()

    def list_intelligence_revisions(
        self, intelligence_id: str
    ) -> tuple[IntelligenceRevisionRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM intelligence_revisions WHERE intelligence_id = :intelligence_id "
                "ORDER BY revision_number ASC",
                {"intelligence_id": intelligence_id},
            ).fetchall()
            return tuple(self._intelligence_revision_from_row(row) for row in rows)
        finally:
            connection.close()

    def get_intelligence_revision(
        self, revision_id: str
    ) -> IntelligenceRevisionRecord | None:
        """Return raw revision persistence for repository-owned validation only."""
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM intelligence_revisions WHERE revision_id = :revision_id",
                {"revision_id": revision_id},
            ).fetchone()
            return None if row is None else self._intelligence_revision_from_row(row)
        finally:
            connection.close()

    def list_intelligence_revision_evidence(self, revision_id: str) -> tuple[str, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT evidence_id FROM intelligence_revision_evidence "
                "WHERE revision_id = :revision_id ORDER BY evidence_id ASC",
                {"revision_id": revision_id},
            ).fetchall()
            return tuple(str(row["evidence_id"]) for row in rows)
        finally:
            connection.close()

    def list_revision_ids_for_evidence(self, evidence_id: str) -> tuple[str, ...]:
        """Raw direct links for a deletion-impact preview, never a trusted read."""
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT revision_id FROM intelligence_revision_evidence "
                "WHERE evidence_id = :evidence_id ORDER BY revision_id ASC",
                {"evidence_id": evidence_id},
            ).fetchall()
            return tuple(str(row["revision_id"]) for row in rows)
        finally:
            connection.close()

    def list_intelligence_state_history(
        self, intelligence_id: str
    ) -> tuple[IntelligenceStateHistoryRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM intelligence_state_history WHERE intelligence_id = :intelligence_id "
                "ORDER BY created_at ASC, state_event_id ASC",
                {"intelligence_id": intelligence_id},
            ).fetchall()
            return tuple(
                self._intelligence_state_history_from_row(row) for row in rows
            )
        finally:
            connection.close()

    def list_dependency_edges_for_revision(
        self, revision_id: str
    ) -> tuple[DependencyEdgeRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM dependency_edges WHERE dependent_revision_id = :revision_id "
                "ORDER BY edge_id ASC",
                {"revision_id": revision_id},
            ).fetchall()
            return tuple(self._dependency_edge_from_row(row) for row in rows)
        finally:
            connection.close()

    def create_dependency_edge(
        self, edge: DependencyEdgeWrite, *, now: datetime
    ) -> DependencyEdgeRecord:
        if not edge.edge_id.strip() or not edge.dependent_revision_id.strip():
            raise ValueError("dependency edge identities must be non-empty")
        is_evidence_edge = edge.relation is DependencyRelation.EVIDENCE_SUPPORT
        if is_evidence_edge != (edge.input_evidence_id is not None) or (
            is_evidence_edge and edge.input_revision_id is not None
        ) or (not is_evidence_edge and edge.input_revision_id is None) or (
            not is_evidence_edge and edge.input_evidence_id is not None
        ):
            raise StateStoreError("dependency relation requires exactly one valid input")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO dependency_edges (edge_id, dependent_revision_id, relation, input_evidence_id, input_revision_id, created_at) "
                    "VALUES (:edge_id, :dependent_revision_id, :relation, :input_evidence_id, :input_revision_id, :created_at)",
                    {
                        "edge_id": edge.edge_id,
                        "dependent_revision_id": edge.dependent_revision_id,
                        "relation": edge.relation.value,
                        "input_evidence_id": edge.input_evidence_id,
                        "input_revision_id": edge.input_revision_id,
                        "created_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT * FROM dependency_edges WHERE edge_id = :edge_id",
                    {"edge_id": edge.edge_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("dependency edge was not saved")
                return self._dependency_edge_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("dependency edge violates the finite provenance contract") from error
        finally:
            connection.close()
