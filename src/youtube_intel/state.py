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
from youtube_intel.source_run import (
    SOURCE_RUN_CHECKPOINT_ORDER,
    SourceRunAttentionReason,
    SourceRunCheckpoint,
    SourceRunCheckpointEventStatus,
    SourceRunCheckpointProgress,
    SourceRunChildRecord,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunRecord,
    SourceRunState,
    SourceRunTrigger,
    SourceRunWrite,
    build_source_run_id,
    build_source_run_idempotency_key,
    source_run_child_transition_allowed,
    source_run_transition_allowed,
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


class EvidenceStance(str, Enum):
    """How one Evidence item relates to one specific Intelligence revision."""

    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONDITIONAL = "conditional"


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


class TopicLifecycle(str, Enum):
    ACTIVE = "ACTIVE"
    MERGED = "MERGED"


class TopicAssociationKind(str, Enum):
    """Finite V1 cross-video information-gain classification."""

    NEW_INFORMATION = "NEW_INFORMATION"
    SUPPORTING_REPETITION = "SUPPORTING_REPETITION"
    NEW_EVIDENCE = "NEW_EVIDENCE"
    CONTRADICTORY_INFORMATION = "CONTRADICTORY_INFORMATION"
    LOW_VALUE_DUPLICATE = "LOW_VALUE_DUPLICATE"


class TopicCurrentState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    CONSENSUS = "CONSENSUS"
    DISAGREEMENT = "DISAGREEMENT"
    DEGRADED = "DEGRADED"


class TopicTimelineEventKind(str, Enum):
    NEW_INFORMATION = "NEW_INFORMATION"
    NEW_EVIDENCE = "NEW_EVIDENCE"
    CONTRADICTION = "CONTRADICTION"


class TopicRelationKind(str, Enum):
    RELATED = "RELATED"


class WeeklyBriefStatus(str, Enum):
    FINALIZED = "FINALIZED"


class WeeklyBriefMarkerKind(str, Enum):
    SUPERSEDED = "SUPERSEDED"
    EVIDENCE_DELETED = "EVIDENCE_DELETED"
    SOURCE_INVALIDATED = "SOURCE_INVALIDATED"


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
    source_excerpt: str | None = None


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
    source_excerpt: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceRelationRecord:
    revision_id: str
    evidence_id: str
    stance: EvidenceStance | None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TimedTranscriptCueWrite:
    start_ms: int
    end_ms: int
    text: str

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("timed transcript cue range is invalid")
        if not self.text or self.text.strip() != self.text:
            raise ValueError("timed transcript cue text is invalid")

    @property
    def text_hash(self) -> str:
        return _sha256_text(self.text)


def build_timed_transcript_hash(cues: tuple[TimedTranscriptCueWrite, ...]) -> str:
    """Hash ordered cue-level semantic content, never local storage metadata."""
    canonical = json.dumps(
        [[cue.start_ms, cue.end_ms, cue.text_hash] for cue in cues],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class TimedTranscriptWrite:
    timed_transcript_id: str
    video_id: str
    canonical_artifact_id: str
    timed_transcript_hash: str
    cues: tuple[TimedTranscriptCueWrite, ...]

    @classmethod
    def from_cues(
        cls,
        *,
        video_id: str,
        canonical_artifact_id: str,
        cues: tuple[TimedTranscriptCueWrite, ...],
    ) -> TimedTranscriptWrite:
        if not video_id.strip() or not canonical_artifact_id.strip() or not cues:
            raise ValueError("timed transcript identity and cues are required")
        previous_end = -1
        for cue in cues:
            if cue.start_ms < previous_end:
                raise ValueError("timed transcript cues must not overlap")
            previous_end = cue.end_ms
        transcript_hash = build_timed_transcript_hash(cues)
        identity = hashlib.sha256(
            json.dumps(
                [video_id, canonical_artifact_id, transcript_hash],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return cls(
            timed_transcript_id=f"timed-transcript:v1:{identity}",
            video_id=video_id,
            canonical_artifact_id=canonical_artifact_id,
            timed_transcript_hash=transcript_hash,
            cues=cues,
        )


@dataclass(frozen=True, slots=True)
class EvidenceTextBindingWrite:
    evidence_id: str
    timed_transcript_id: str
    start_cue_index: int
    end_cue_index: int
    excerpt: str
    excerpt_hash: str

    @classmethod
    def from_timed_transcript(
        cls,
        *,
        evidence: EvidenceWrite,
        timed_transcript_id: str,
        start_cue_index: int,
        end_cue_index: int,
        excerpt: str,
    ) -> EvidenceTextBindingWrite:
        return cls(
            evidence_id=evidence.evidence_id,
            timed_transcript_id=timed_transcript_id,
            start_cue_index=start_cue_index,
            end_cue_index=end_cue_index,
            excerpt=excerpt,
            excerpt_hash=_sha256_text(excerpt),
        )


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceText:
    """Exact persisted Evidence text; not a provider request and not a trust read."""

    evidence_id: str
    video_id: str
    timed_transcript_id: str
    timed_transcript_hash: str
    start_ms: int
    end_ms: int
    excerpt: str
    excerpt_hash: str


@dataclass(frozen=True, slots=True)
class SavedIntelligenceRecord:
    """Raw local organization metadata; never an Intelligence authority."""

    intelligence_id: str
    saved_at: datetime


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
class DistillationExecutionWrite:
    execution_id: str
    source_id: str
    video_id: str
    reason: str
    use_case: str
    selected_provider: str
    selected_model: str


@dataclass(frozen=True, slots=True)
class DistillationExecutionRecord:
    execution_id: str
    source_id: str
    video_id: str
    reason: str
    use_case: str
    selected_provider: str
    selected_model: str
    status: str
    budget_state: str
    invocation_count: int
    intelligence_id: str | None
    revision_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DistillationCardWrite:
    source_id: str
    video_id: str
    core_conclusion: str
    user_relevant_information: tuple[str, ...]
    important_new_information: tuple[str, ...]
    meaningful_details: tuple[str, ...]
    filtered_noise: tuple[str, ...]
    preference_ids: tuple[str, ...]
    source_policy_revision_id: str | None


@dataclass(frozen=True, slots=True)
class DistillationCardRecord:
    revision_id: str
    source_id: str
    video_id: str
    core_conclusion: str
    user_relevant_information: tuple[str, ...]
    important_new_information: tuple[str, ...]
    meaningful_details: tuple[str, ...]
    filtered_noise: tuple[str, ...]
    preference_ids: tuple[str, ...]
    source_policy_revision_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DistillationResourceUsageRecord:
    execution_id: str
    reason: str
    use_case: str
    source_id: str
    video_id: str
    intelligence_id: str | None
    revision_id: str | None
    selected_provider: str
    selected_model: str
    actual_provider: str | None
    actual_model: str | None
    status: str
    invocation_count: int
    input_tokens: int | None
    output_tokens: int | None
    cost_microunits: int | None
    duration_ms: int | None
    budget_state: str
    outcome: str
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
class TopicRecord:
    topic_id: str
    name: str
    pinned: bool
    lifecycle: TopicLifecycle
    merged_into_topic_id: str | None
    current_event_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TopicMembershipWrite:
    membership_id: str
    topic_id: str
    intelligence_id: str
    revision_id: str
    association_kind: TopicAssociationKind
    source_claim_kind: IntelligenceClaimKind
    source_state: IntelligenceState
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopicMembershipRecord:
    membership_id: str
    topic_id: str
    intelligence_id: str
    revision_id: str
    association_kind: TopicAssociationKind
    source_claim_kind: IntelligenceClaimKind
    source_state: IntelligenceState
    evidence_ids: tuple[str, ...]
    created_at: datetime
    effective_at: datetime


@dataclass(frozen=True, slots=True)
class TopicTimelineEventWrite:
    event_id: str
    topic_id: str
    event_kind: TopicTimelineEventKind
    state: TopicCurrentState
    membership_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopicTimelineEventRecord:
    event_id: str
    topic_id: str
    event_kind: TopicTimelineEventKind
    state: TopicCurrentState
    membership_ids: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TopicRelationRecord:
    topic_id: str
    related_topic_id: str
    relation: TopicRelationKind
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyBriefWrite:
    brief_id: str
    logical_period_id: str
    timezone: str
    period_start: datetime
    period_end: datetime
    no_important_information: bool
    preference_projection_hash: str
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyBriefRecord:
    brief_id: str
    version: str
    logical_period_id: str
    timezone: str
    period_start: datetime
    period_end: datetime
    status: WeeklyBriefStatus
    no_important_information: bool
    preference_projection_hash: str
    generated_at: datetime
    finalized_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyBriefItemWrite:
    brief_item_id: str
    membership_id: str
    topic_id: str
    topic_name: str
    intelligence_id: str
    revision_id: str
    association_kind: TopicAssociationKind
    claim_kind: IntelligenceClaimKind
    source_state: IntelligenceState
    summary: str
    source_content_hash: str
    position: int
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeeklyBriefItemRecord:
    brief_item_id: str
    brief_id: str
    membership_id: str
    topic_id: str
    topic_name: str
    intelligence_id: str
    revision_id: str
    association_kind: TopicAssociationKind
    claim_kind: IntelligenceClaimKind
    source_state: IntelligenceState
    summary: str
    source_content_hash: str
    position: int
    evidence_ids: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WeeklyBriefPreferenceProjectionWrite:
    preference_id: str
    horizon: PreferenceHorizon
    provenance: PreferenceProvenance
    statement_hash: str


@dataclass(frozen=True, slots=True)
class WeeklyBriefPreferenceProjectionRecord:
    brief_id: str
    preference_id: str
    horizon: PreferenceHorizon
    provenance: PreferenceProvenance
    statement_hash: str


@dataclass(frozen=True, slots=True)
class WeeklyBriefMarkerWrite:
    marker_id: str
    brief_item_id: str
    kind: WeeklyBriefMarkerKind
    reason: str
    current_revision_id: str | None
    evidence_id: str | None


@dataclass(frozen=True, slots=True)
class WeeklyBriefMarkerRecord:
    marker_id: str
    brief_item_id: str
    kind: WeeklyBriefMarkerKind
    reason: str
    current_revision_id: str | None
    evidence_id: str | None
    marked_at: datetime


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
class GlobalUserSettingsRecord:
    output_language: str
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
            "010_add_personalized_distillation.sql",
            "011_add_topic_timeline.sql",
            "012_add_source_run_orchestration.sql",
            "013_add_weekly_brief_foundation.sql",
            "014_add_saved_intelligence.sql",
            "015_add_timed_transcript_evidence_bindings.sql",
            "016_add_ambiguous_resource_ledger_outcome.sql",
            "017_add_current_content_summary.sql",
            "018_add_global_output_language.sql",
            "019_add_evidence_excerpt_stance.sql",
            "020_add_no_new_intelligence_result.sql",
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

    def source_has_video(self, source_id: str, video_id: str) -> bool:
        """Check source membership without applying a presentation-list limit."""

        if not source_id.strip() or not video_id.strip():
            raise ValueError("source video membership arguments are invalid")
        connection = self._connect()
        try:
            return (
                connection.execute(
                    "SELECT 1 FROM source_video_links WHERE source_id = :source_id "
                    "AND video_id = :video_id",
                    {"source_id": source_id, "video_id": video_id},
                ).fetchone()
                is not None
            )
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

    @staticmethod
    def _source_run_from_row(row: sqlite3.Row) -> SourceRunRecord:
        return SourceRunRecord(
            run_id=str(row["run_id"]),
            source_id=str(row["source_id"]),
            trigger=SourceRunTrigger(str(row["trigger"])),
            trigger_reference=str(row["trigger_reference"]),
            priority=SourceRunPriority(str(row["priority"])),
            idempotency_key=str(row["idempotency_key"]),
            state=SourceRunState(str(row["state"])),
            attention_reason=(
                None
                if row["attention_reason"] is None
                else SourceRunAttentionReason(str(row["attention_reason"]))
            ),
            automation_run_id=(
                None if row["automation_run_id"] is None else str(row["automation_run_id"])
            ),
            manual_command_id=(
                None if row["manual_command_id"] is None else str(row["manual_command_id"])
            ),
            manual_analyze_override_id=(
                None
                if row["manual_analyze_override_id"] is None
                else str(row["manual_analyze_override_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _source_run_child_from_row(row: sqlite3.Row) -> SourceRunChildRecord:
        return SourceRunChildRecord(
            run_id=str(row["run_id"]),
            video_id=str(row["video_id"]),
            state=SourceRunChildState(str(row["state"])),
            distillation_execution_id=(
                None
                if row["distillation_execution_id"] is None
                else str(row["distillation_execution_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _validate_source_run_write(run: SourceRunWrite) -> None:
        if not isinstance(run, SourceRunWrite):
            raise ValueError("Source Run write is invalid")
        if (
            not isinstance(run.trigger, SourceRunTrigger)
            or not isinstance(run.priority, SourceRunPriority)
        ):
            raise ValueError("Source Run trigger and priority must be finite")
        identity_fields = (
            run.run_id,
            run.source_id,
            run.trigger_reference,
            run.idempotency_key,
        )
        if any(
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 512
            for value in identity_fields
        ):
            raise ValueError("Source Run identity is invalid")
        for value in (
            run.automation_run_id,
            run.manual_command_id,
            run.manual_analyze_override_id,
        ):
            if value is not None and (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
                or len(value) > 512
            ):
                raise ValueError("Source Run trigger reference is invalid")
        expected_run_id = build_source_run_id(
            source_id=run.source_id,
            trigger=run.trigger,
            trigger_reference=run.trigger_reference,
        )
        expected_idempotency_key = build_source_run_idempotency_key(
            source_id=run.source_id,
            trigger=run.trigger,
            trigger_reference=run.trigger_reference,
        )
        if run.run_id != expected_run_id or run.idempotency_key != expected_idempotency_key:
            raise ValueError("Source Run identity must be derived from its bound trigger")
        if run.trigger is SourceRunTrigger.MANUAL_CHECK_NOW:
            context_is_legal = (
                run.automation_run_id is None
                and run.manual_command_id == run.trigger_reference
                and run.manual_analyze_override_id is None
            )
        elif run.trigger is SourceRunTrigger.SCHEDULED_SOURCE_RUN:
            context_is_legal = (
                run.automation_run_id == run.trigger_reference
                and run.manual_command_id is None
                and run.manual_analyze_override_id is None
            )
        else:
            context_is_legal = (
                run.automation_run_id is None
                and run.manual_command_id is not None
                and run.manual_analyze_override_id == run.trigger_reference
            )
        if not context_is_legal:
            raise ValueError("Source Run trigger context is invalid")
        format_utc_datetime(run.created_at)

    @staticmethod
    def _same_source_run_admission(
        record: SourceRunRecord, run: SourceRunWrite
    ) -> bool:
        return (
            record.run_id == run.run_id
            and record.source_id == run.source_id
            and record.trigger is run.trigger
            and record.trigger_reference == run.trigger_reference
            and record.priority is run.priority
            and record.idempotency_key == run.idempotency_key
            and record.automation_run_id == run.automation_run_id
            and record.manual_command_id == run.manual_command_id
            and record.manual_analyze_override_id == run.manual_analyze_override_id
        )

    def create_source_run(self, run: SourceRunWrite) -> SourceRunRecord:
        """Durably admit one source-bound logical run without executing it."""

        self._validate_source_run_write(run)
        timestamp = format_utc_datetime(run.created_at)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM source_runs WHERE source_id = :source_id "
                    "AND idempotency_key = :idempotency_key",
                    {
                        "source_id": run.source_id,
                        "idempotency_key": run.idempotency_key,
                    },
                ).fetchone()
                if existing is not None:
                    record = self._source_run_from_row(existing)
                    if not self._same_source_run_admission(record, run):
                        raise IntegrityConflict("Source Run idempotency identity conflicts")
                    return record
                connection.execute(
                    "INSERT INTO source_runs "
                    "(run_id, source_id, trigger, trigger_reference, priority, "
                    "idempotency_key, state, attention_reason, automation_run_id, "
                    "manual_command_id, manual_analyze_override_id, created_at, updated_at) "
                    "VALUES (:run_id, :source_id, :trigger, :trigger_reference, :priority, "
                    ":idempotency_key, 'QUEUED', NULL, :automation_run_id, "
                    ":manual_command_id, :manual_analyze_override_id, :created_at, :updated_at)",
                    {
                        "run_id": run.run_id,
                        "source_id": run.source_id,
                        "trigger": run.trigger.value,
                        "trigger_reference": run.trigger_reference,
                        "priority": run.priority.value,
                        "idempotency_key": run.idempotency_key,
                        "automation_run_id": run.automation_run_id,
                        "manual_command_id": run.manual_command_id,
                        "manual_analyze_override_id": run.manual_analyze_override_id,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM source_runs WHERE run_id = :run_id",
                    {"run_id": run.run_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("Source Run was not saved")
                return self._source_run_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("Source Run violates its durable admission contract") from error
        finally:
            connection.close()

    def get_source_run(self, run_id: str) -> SourceRunRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM source_runs WHERE run_id = :run_id", {"run_id": run_id}
            ).fetchone()
            return None if row is None else self._source_run_from_row(row)
        finally:
            connection.close()

    def list_source_runs(self) -> tuple[SourceRunRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._source_run_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM source_runs ORDER BY created_at ASC, run_id ASC"
                )
            )
        finally:
            connection.close()

    def list_resumable_source_runs(self) -> tuple[SourceRunRecord, ...]:
        """Read durable queue/resume candidates; this does not claim or execute them."""

        connection = self._connect()
        try:
            return tuple(
                self._source_run_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM source_runs "
                    "WHERE state IN ('QUEUED', 'WAITING', 'PARTIAL') "
                    "ORDER BY CASE priority "
                    "WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, "
                    "created_at ASC, run_id ASC"
                )
            )
        finally:
            connection.close()

    def transition_source_run(
        self,
        run_id: str,
        *,
        to_state: SourceRunState,
        now: datetime,
        attention_reason: SourceRunAttentionReason | None = None,
    ) -> SourceRunRecord:
        if not isinstance(to_state, SourceRunState):
            raise ValueError("Source Run state must be finite")
        if to_state in {SourceRunState.NEEDS_ATTENTION, SourceRunState.AMBIGUOUS}:
            if not isinstance(attention_reason, SourceRunAttentionReason):
                raise ValueError("Source Run attention reason must be finite")
            if (
                to_state is SourceRunState.AMBIGUOUS
                and attention_reason
                is not SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
            ):
                raise ValueError("Source Run attention reason is invalid for AMBIGUOUS")
        elif attention_reason is not None:
            raise ValueError("Source Run attention reason is valid only for attention states")
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM source_runs WHERE run_id = :run_id", {"run_id": run_id}
                ).fetchone()
                if row is None:
                    raise ValueError("Source Run does not exist")
                current = SourceRunState(str(row["state"]))
                if not source_run_transition_allowed(current, to_state):
                    raise ValueError("Source Run state transition is not allowed")
                connection.execute(
                    "UPDATE source_runs SET state = :state, attention_reason = :attention_reason, "
                    "updated_at = :updated_at WHERE run_id = :run_id",
                    {
                        "run_id": run_id,
                        "state": to_state.value,
                        "attention_reason": (
                            None if attention_reason is None else attention_reason.value
                        ),
                        "updated_at": timestamp,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM source_runs WHERE run_id = :run_id", {"run_id": run_id}
                ).fetchone()
                if saved is None:
                    raise StateStoreError("Source Run state was not saved")
                return self._source_run_from_row(saved)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("Source Run state violates its durable contract") from error
        finally:
            connection.close()

    def source_run_checkpoint_progress(self, run_id: str) -> SourceRunCheckpointProgress:
        connection = self._connect()
        try:
            run = connection.execute(
                "SELECT 1 FROM source_runs WHERE run_id = :run_id", {"run_id": run_id}
            ).fetchone()
            if run is None:
                raise ValueError("Source Run does not exist")
            rows = tuple(
                connection.execute(
                    "SELECT checkpoint, checkpoint_position, event_status, event_id "
                    "FROM source_run_checkpoint_events WHERE run_id = :run_id "
                    "ORDER BY checkpoint_position ASC, event_id ASC",
                    {"run_id": run_id},
                )
            )
            completed_positions = {
                int(row["checkpoint_position"])
                for row in rows
                if str(row["event_status"])
                == SourceRunCheckpointEventStatus.COMPLETED.value
            }
            completed = tuple(
                checkpoint
                for position, checkpoint in enumerate(SOURCE_RUN_CHECKPOINT_ORDER, start=1)
                if position in completed_positions
            )
            next_checkpoint = next(
                (
                    checkpoint
                    for position, checkpoint in enumerate(
                        SOURCE_RUN_CHECKPOINT_ORDER, start=1
                    )
                    if position not in completed_positions
                ),
                None,
            )
            blocked_checkpoint = None
            if next_checkpoint is not None:
                next_position = SOURCE_RUN_CHECKPOINT_ORDER.index(next_checkpoint) + 1
                blocked = [
                    row
                    for row in rows
                    if int(row["checkpoint_position"]) == next_position
                    and str(row["event_status"])
                    == SourceRunCheckpointEventStatus.BLOCKED.value
                ]
                if blocked:
                    blocked_checkpoint = next_checkpoint
            return SourceRunCheckpointProgress(
                run_id=run_id,
                completed=completed,
                next_checkpoint=next_checkpoint,
                blocked_checkpoint=blocked_checkpoint,
            )
        finally:
            connection.close()

    def _require_safe_checkpoint(
        self, run_id: str, checkpoint: SourceRunCheckpoint
    ) -> None:
        if not isinstance(checkpoint, SourceRunCheckpoint):
            raise ValueError("Source Run checkpoint must be finite")
        progress = self.source_run_checkpoint_progress(run_id)
        if progress.next_checkpoint is not checkpoint:
            raise ValueError("Source Run checkpoint is not the safe next step")

    def complete_source_run_checkpoint(
        self, run_id: str, checkpoint: SourceRunCheckpoint, *, now: datetime
    ) -> SourceRunCheckpointProgress:
        self._require_safe_checkpoint(run_id, checkpoint)
        timestamp = format_utc_datetime(now)
        position = SOURCE_RUN_CHECKPOINT_ORDER.index(checkpoint) + 1
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT state FROM source_runs WHERE run_id = :run_id", {"run_id": run_id}
                ).fetchone()
                if row is None:
                    raise ValueError("Source Run does not exist")
                if SourceRunState(str(row["state"])) not in {
                    SourceRunState.RUNNING,
                    SourceRunState.PARTIAL,
                }:
                    raise ValueError("Source Run cannot complete a checkpoint from its state")
                connection.execute(
                    "INSERT INTO source_run_checkpoint_events "
                    "(run_id, checkpoint, checkpoint_position, event_status, created_at) "
                    "VALUES (:run_id, :checkpoint, :checkpoint_position, :event_status, :created_at)",
                    {
                        "run_id": run_id,
                        "checkpoint": checkpoint.value,
                        "checkpoint_position": position,
                        "event_status": SourceRunCheckpointEventStatus.COMPLETED.value,
                        "created_at": timestamp,
                    },
                )
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("Source Run checkpoint violates safe child proof") from error
        finally:
            connection.close()
        return self.source_run_checkpoint_progress(run_id)

    def block_source_run_checkpoint(
        self, run_id: str, checkpoint: SourceRunCheckpoint, *, now: datetime
    ) -> SourceRunCheckpointProgress:
        self._require_safe_checkpoint(run_id, checkpoint)
        timestamp = format_utc_datetime(now)
        position = SOURCE_RUN_CHECKPOINT_ORDER.index(checkpoint) + 1
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT state FROM source_runs WHERE run_id = :run_id", {"run_id": run_id}
                ).fetchone()
                if row is None:
                    raise ValueError("Source Run does not exist")
                if SourceRunState(str(row["state"])) not in {
                    SourceRunState.RUNNING,
                    SourceRunState.WAITING,
                    SourceRunState.PARTIAL,
                    SourceRunState.NEEDS_ATTENTION,
                }:
                    raise ValueError("Source Run cannot block a checkpoint from its state")
                connection.execute(
                    "INSERT INTO source_run_checkpoint_events "
                    "(run_id, checkpoint, checkpoint_position, event_status, created_at) "
                    "VALUES (:run_id, :checkpoint, :checkpoint_position, :event_status, :created_at)",
                    {
                        "run_id": run_id,
                        "checkpoint": checkpoint.value,
                        "checkpoint_position": position,
                        "event_status": SourceRunCheckpointEventStatus.BLOCKED.value,
                        "created_at": timestamp,
                    },
                )
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("Source Run checkpoint block is invalid") from error
        finally:
            connection.close()
        return self.source_run_checkpoint_progress(run_id)

    def record_source_run_child(
        self,
        run_id: str,
        *,
        video_id: str,
        state: SourceRunChildState,
        distillation_execution_id: str | None,
        now: datetime,
    ) -> SourceRunChildRecord:
        if not isinstance(state, SourceRunChildState) or state is not SourceRunChildState.PENDING:
            raise ValueError("Source Run child must begin in finite PENDING state")
        if (
            not isinstance(video_id, str)
            or not video_id.strip()
            or video_id != video_id.strip()
            or len(video_id) > 512
        ):
            raise ValueError("Source Run child video identity is invalid")
        if distillation_execution_id is not None and (
            not isinstance(distillation_execution_id, str)
            or not distillation_execution_id.strip()
            or distillation_execution_id != distillation_execution_id.strip()
            or len(distillation_execution_id) > 512
        ):
            raise ValueError("Source Run child execution identity is invalid")
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO source_run_video_executions "
                    "(run_id, video_id, state, distillation_execution_id, created_at, updated_at) "
                    "VALUES (:run_id, :video_id, :state, :distillation_execution_id, "
                    ":created_at, :updated_at)",
                    {
                        "run_id": run_id,
                        "video_id": video_id,
                        "state": state.value,
                        "distillation_execution_id": distillation_execution_id,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM source_run_video_executions "
                    "WHERE run_id = :run_id AND video_id = :video_id",
                    {"run_id": run_id, "video_id": video_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("Source Run child was not saved")
                return self._source_run_child_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("Source Run child violates its durable contract") from error
        finally:
            connection.close()

    def list_source_run_children(self, run_id: str) -> tuple[SourceRunChildRecord, ...]:
        connection = self._connect()
        try:
            return tuple(
                self._source_run_child_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM source_run_video_executions WHERE run_id = :run_id "
                    "ORDER BY video_id ASC",
                    {"run_id": run_id},
                )
            )
        finally:
            connection.close()

    def transition_source_run_child(
        self,
        run_id: str,
        *,
        video_id: str,
        to_state: SourceRunChildState,
        now: datetime,
    ) -> SourceRunChildRecord:
        if not isinstance(to_state, SourceRunChildState):
            raise ValueError("Source Run child state must be finite")
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                row = connection.execute(
                    "SELECT * FROM source_run_video_executions "
                    "WHERE run_id = :run_id AND video_id = :video_id",
                    {"run_id": run_id, "video_id": video_id},
                ).fetchone()
                if row is None:
                    raise ValueError("Source Run child does not exist")
                current = SourceRunChildState(str(row["state"]))
                if not source_run_child_transition_allowed(current, to_state):
                    raise ValueError("Source Run child state transition is not allowed")
                connection.execute(
                    "UPDATE source_run_video_executions SET state = :state, "
                    "updated_at = :updated_at WHERE run_id = :run_id AND video_id = :video_id",
                    {
                        "run_id": run_id,
                        "video_id": video_id,
                        "state": to_state.value,
                        "updated_at": timestamp,
                    },
                )
                saved = connection.execute(
                    "SELECT * FROM source_run_video_executions "
                    "WHERE run_id = :run_id AND video_id = :video_id",
                    {"run_id": run_id, "video_id": video_id},
                ).fetchone()
                if saved is None:
                    raise StateStoreError("Source Run child state was not saved")
                return self._source_run_child_from_row(saved)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("Source Run child state violates protected execution") from error
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

    def save_global_output_language(
        self, *, output_language: str, now: datetime
    ) -> GlobalUserSettingsRecord:
        if output_language not in {"zh-CN", "en"}:
            raise ValueError("output language is unsupported")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO global_user_settings "
                    "(settings_key, output_language, updated_at) "
                    "VALUES ('global', :output_language, :updated_at) "
                    "ON CONFLICT(settings_key) DO UPDATE SET "
                    "output_language=excluded.output_language, "
                    "updated_at=excluded.updated_at",
                    {
                        "output_language": output_language,
                        "updated_at": format_utc_datetime(now),
                    },
                )
                row = connection.execute(
                    "SELECT output_language, updated_at FROM global_user_settings "
                    "WHERE settings_key='global'"
                ).fetchone()
                if row is None:
                    raise StateStoreError("global output language was not saved")
                return GlobalUserSettingsRecord(
                    output_language=str(row["output_language"]),
                    updated_at=_parse_utc_datetime(str(row["updated_at"])),
                )
        finally:
            connection.close()

    def get_global_user_settings(self) -> GlobalUserSettingsRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT output_language, updated_at FROM global_user_settings "
                "WHERE settings_key='global'"
            ).fetchone()
            return (
                None
                if row is None
                else GlobalUserSettingsRecord(
                    output_language=str(row["output_language"]),
                    updated_at=_parse_utc_datetime(str(row["updated_at"])),
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
            source_excerpt=(
                None
                if row["source_excerpt"] is None
                else str(row["source_excerpt"])
            ),
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

    def create_timed_transcript(
        self, timed: TimedTranscriptWrite, *, now: datetime
    ) -> TimedTranscriptWrite:
        """Persist one cue-level authority after validating its canonical Artifact."""
        if (
            not timed.timed_transcript_id.strip()
            or not timed.video_id.strip()
            or not timed.canonical_artifact_id.strip()
            or not re.fullmatch(r"[0-9a-f]{64}", timed.timed_transcript_hash)
            or not timed.cues
            or build_timed_transcript_hash(timed.cues) != timed.timed_transcript_hash
        ):
            raise ValueError("timed transcript authority is invalid")
        previous_end = -1
        for cue in timed.cues:
            if cue.start_ms < previous_end:
                raise ValueError("timed transcript cues must not overlap")
            previous_end = cue.end_ms
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                artifact = connection.execute(
                    "SELECT video_id, kind, deleted_at FROM artifacts WHERE artifact_id = ?",
                    (timed.canonical_artifact_id,),
                ).fetchone()
                if (
                    artifact is None
                    or artifact["video_id"] != timed.video_id
                    or artifact["kind"] != ArtifactKind.TRANSCRIPT_CANONICAL.value
                    or artifact["deleted_at"] is not None
                ):
                    raise IntegrityConflict("timed transcript canonical artifact is not legal")
                existing = connection.execute(
                    "SELECT timed_transcript_hash FROM timed_transcripts WHERE timed_transcript_id = ?",
                    (timed.timed_transcript_id,),
                ).fetchone()
                if existing is not None:
                    if existing["timed_transcript_hash"] != timed.timed_transcript_hash:
                        raise IntegrityConflict("timed transcript identity conflicts")
                    return timed
                connection.execute(
                    "INSERT INTO timed_transcripts (timed_transcript_id, video_id, canonical_artifact_id, timed_transcript_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (timed.timed_transcript_id, timed.video_id, timed.canonical_artifact_id, timed.timed_transcript_hash, format_utc_datetime(now)),
                )
                connection.executemany(
                    "INSERT INTO timed_transcript_cues (timed_transcript_id, cue_index, start_ms, end_ms, cue_text, cue_text_hash) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (timed.timed_transcript_id, index, cue.start_ms, cue.end_ms, cue.text, cue.text_hash)
                        for index, cue in enumerate(timed.cues)
                    ],
                )
                return timed
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("timed transcript violates immutable authority") from error
        finally:
            connection.close()

    def _insert_evidence_text_binding_in_transaction(
        self,
        connection: sqlite3.Connection,
        evidence: EvidenceWrite,
        binding: EvidenceTextBindingWrite,
        *,
        now: datetime,
    ) -> None:
        if binding.evidence_id != evidence.evidence_id or _sha256_text(binding.excerpt) != binding.excerpt_hash:
            raise IntegrityConflict("evidence text binding identity is invalid")
        timed = connection.execute(
            "SELECT timed_transcript_id, video_id, canonical_artifact_id, timed_transcript_hash FROM timed_transcripts WHERE timed_transcript_id = ?",
            (binding.timed_transcript_id,),
        ).fetchone()
        if (
            timed is None
            or timed["video_id"] != evidence.video_id
            or timed["canonical_artifact_id"] != evidence.artifact_id
        ):
            raise IntegrityConflict("evidence text binding is foreign to its evidence")
        cues = connection.execute(
            "SELECT cue_index, start_ms, end_ms, cue_text, cue_text_hash FROM timed_transcript_cues WHERE timed_transcript_id = ? AND cue_index >= ? AND cue_index < ? ORDER BY cue_index ASC",
            (binding.timed_transcript_id, binding.start_cue_index, binding.end_cue_index),
        ).fetchall()
        if len(cues) != binding.end_cue_index - binding.start_cue_index:
            raise IntegrityConflict("evidence text binding cue set is incomplete")
        if (
            not cues
            or cues[0]["cue_index"] != binding.start_cue_index
            or cues[-1]["cue_index"] != binding.end_cue_index - 1
            or cues[0]["start_ms"] != evidence.start_ms
            or cues[-1]["end_ms"] != evidence.end_ms
        ):
            raise IntegrityConflict("evidence range must align to full canonical cues")
        expected_excerpt = "\n".join(str(cue["cue_text"]) for cue in cues)
        if (
            expected_excerpt != binding.excerpt
            or any(_sha256_text(str(cue["cue_text"])) != cue["cue_text_hash"] for cue in cues)
        ):
            raise IntegrityConflict("evidence text binding does not match canonical cues")
        connection.execute(
            "INSERT INTO evidence_text_bindings (evidence_id, timed_transcript_id, start_cue_index, end_cue_index, excerpt, excerpt_hash, timed_transcript_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (binding.evidence_id, binding.timed_transcript_id, binding.start_cue_index, binding.end_cue_index, binding.excerpt, binding.excerpt_hash, timed["timed_transcript_hash"], format_utc_datetime(now)),
        )

    def create_evidence_text_binding(
        self, binding: EvidenceTextBindingWrite, *, now: datetime
    ) -> None:
        evidence = self.get_evidence(binding.evidence_id)
        if evidence is None:
            raise IntegrityConflict("evidence text binding evidence is missing")
        write = EvidenceWrite(
            evidence_id=evidence.evidence_id, video_id=evidence.video_id, artifact_id=evidence.artifact_id,
            start_ms=evidence.start_ms, end_ms=evidence.end_ms, lineage_kind=evidence.lineage_kind,
            role=evidence.role, language=evidence.language, availability=evidence.availability,
        )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                self._insert_evidence_text_binding_in_transaction(connection, write, binding, now=now)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("evidence text binding is immutable or invalid") from error
        finally:
            connection.close()

    def create_evidence_with_text_binding(
        self, evidence: EvidenceWrite, binding: EvidenceTextBindingWrite, *, now: datetime
    ) -> EvidenceRecord:
        expected_id = build_evidence_id(video_id=evidence.video_id, artifact_id=evidence.artifact_id, start_ms=evidence.start_ms, end_ms=evidence.end_ms, lineage_kind=evidence.lineage_kind, role=evidence.role)
        if evidence.evidence_id != expected_id or not evidence.language.strip():
            raise ValueError("evidence identity is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO evidence (evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, role, language, availability, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (evidence.evidence_id, evidence.video_id, evidence.artifact_id, evidence.start_ms, evidence.end_ms, evidence.lineage_kind.value, evidence.role.value, evidence.language, evidence.availability.value, format_utc_datetime(now)),
                )
                self._insert_evidence_text_binding_in_transaction(connection, evidence, binding, now=now)
                row = connection.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence.evidence_id,)).fetchone()
                if row is None:
                    raise StateStoreError("evidence was not saved")
                return self._evidence_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("evidence and exact-text binding must be coherent") from error
        finally:
            connection.close()

    def resolve_verified_evidence_text(self, evidence_id: str) -> VerifiedEvidenceText | None:
        """Return exact persisted cue-bound text, or ``None`` for legacy/unbound/invalid Evidence."""
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT e.evidence_id, e.video_id, e.artifact_id, e.start_ms, e.end_ms, e.availability, a.kind, a.deleted_at, b.timed_transcript_id, b.start_cue_index, b.end_cue_index, b.excerpt, b.excerpt_hash, b.timed_transcript_hash, t.video_id AS timed_video_id, t.canonical_artifact_id, t.timed_transcript_hash AS actual_timed_hash FROM evidence e JOIN artifacts a ON a.artifact_id = e.artifact_id JOIN evidence_text_bindings b ON b.evidence_id = e.evidence_id JOIN timed_transcripts t ON t.timed_transcript_id = b.timed_transcript_id WHERE e.evidence_id = ?",
                (evidence_id,),
            ).fetchone()
            if (
                row is None or row["availability"] != EvidenceAvailability.AVAILABLE.value
                or row["kind"] != ArtifactKind.TRANSCRIPT_CANONICAL.value or row["deleted_at"] is not None
                or row["video_id"] != row["timed_video_id"] or row["artifact_id"] != row["canonical_artifact_id"]
                or row["timed_transcript_hash"] != row["actual_timed_hash"]
                or _sha256_text(str(row["excerpt"])) != row["excerpt_hash"]
            ):
                return None
            cues = connection.execute(
                "SELECT cue_index, start_ms, end_ms, cue_text, cue_text_hash FROM timed_transcript_cues WHERE timed_transcript_id = ? AND cue_index >= ? AND cue_index < ? ORDER BY cue_index ASC",
                (row["timed_transcript_id"], row["start_cue_index"], row["end_cue_index"]),
            ).fetchall()
            if (
                len(cues) != row["end_cue_index"] - row["start_cue_index"] or not cues
                or cues[0]["start_ms"] != row["start_ms"] or cues[-1]["end_ms"] != row["end_ms"]
                or "\n".join(str(cue["cue_text"]) for cue in cues) != row["excerpt"]
                or any(_sha256_text(str(cue["cue_text"])) != cue["cue_text_hash"] for cue in cues)
            ):
                return None
            return VerifiedEvidenceText(evidence_id=str(row["evidence_id"]), video_id=str(row["video_id"]), timed_transcript_id=str(row["timed_transcript_id"]), timed_transcript_hash=str(row["actual_timed_hash"]), start_ms=int(row["start_ms"]), end_ms=int(row["end_ms"]), excerpt=str(row["excerpt"]), excerpt_hash=str(row["excerpt_hash"]))
        finally:
            connection.close()

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
        if evidence.source_excerpt is not None:
            raise ValueError(
                "evidence source excerpt requires a trusted capture path"
            )
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO evidence (evidence_id, video_id, artifact_id, start_ms, end_ms, lineage_kind, role, language, availability, created_at, source_excerpt) "
                    "VALUES (:evidence_id, :video_id, :artifact_id, :start_ms, :end_ms, :lineage_kind, :role, :language, :availability, :created_at, :source_excerpt)",
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
                        "source_excerpt": evidence.source_excerpt,
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

    def list_available_canonical_evidence_ids(self, video_id: str) -> tuple[str, ...]:
        """Return the stable evidence set eligible for a restart-safe reservation.

        This is deliberately a narrow read over existing Evidence/Artifact authority.
        It neither creates Evidence nor reinterprets its availability or lineage.
        """
        if (
            not isinstance(video_id, str)
            or not video_id.strip()
            or video_id != video_id.strip()
            or len(video_id) > 512
        ):
            raise ValueError("video identity is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT evidence.evidence_id FROM evidence "
                "JOIN artifacts ON artifacts.artifact_id = evidence.artifact_id "
                "WHERE evidence.video_id = :video_id "
                "AND evidence.availability = :availability "
                "AND artifacts.video_id = :video_id "
                "AND artifacts.deleted_at IS NULL "
                "AND artifacts.kind = :artifact_kind "
                "ORDER BY evidence.evidence_id ASC LIMIT 21",
                {
                    "video_id": video_id,
                    "availability": EvidenceAvailability.AVAILABLE.value,
                    "artifact_kind": ArtifactKind.TRANSCRIPT_CANONICAL.value,
                },
            ).fetchall()
            return tuple(str(row["evidence_id"]) for row in rows)
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

    def save_intelligence_relation(
        self, *, intelligence_id: str, now: datetime, expected_revision_id: str | None
    ) -> SavedIntelligenceRecord:
        """Set organization state only; the application owns Save admission."""
        saved_at = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                current = connection.execute(
                    "SELECT current_revision_id FROM intelligences WHERE intelligence_id = ?",
                    (intelligence_id,),
                ).fetchone()
                if current is None or current["current_revision_id"] != expected_revision_id:
                    raise IntegrityConflict("saved target changed after admission")
                connection.execute(
                    "INSERT INTO saved_intelligences (intelligence_id, saved_at) VALUES (?, ?) "
                    "ON CONFLICT(intelligence_id) DO NOTHING",
                    (intelligence_id, saved_at),
                )
                row = connection.execute(
                    "SELECT intelligence_id, saved_at FROM saved_intelligences WHERE intelligence_id = ?",
                    (intelligence_id,),
                ).fetchone()
                if row is None:
                    raise StateStoreError("saved relation is unavailable")
                return SavedIntelligenceRecord(row["intelligence_id"], _parse_utc_datetime(row["saved_at"]))
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("saved relation requires an existing Intelligence") from error
        finally:
            connection.close()

    def unsave_intelligence_relation(self, intelligence_id: str) -> None:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "DELETE FROM saved_intelligences WHERE intelligence_id = ?",
                    (intelligence_id,),
                )
        finally:
            connection.close()

    def list_saved_intelligence_relations(
        self, *, limit: int, after: SavedIntelligenceRecord | None = None
    ) -> tuple[SavedIntelligenceRecord, ...]:
        if type(limit) is not int or not 1 <= limit <= 101:
            raise ValueError("saved page limit must be between 1 and 101")
        after_time = None if after is None else format_utc_datetime(after.saved_at)
        after_id = None if after is None else after.intelligence_id
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT intelligence_id, saved_at FROM saved_intelligences "
                "WHERE (? IS NULL OR saved_at < ? OR (saved_at = ? AND intelligence_id > ?)) "
                "ORDER BY saved_at DESC, intelligence_id ASC LIMIT ?",
                (after_time, after_time, after_time, after_id, limit),
            ).fetchall()
            return tuple(
                SavedIntelligenceRecord(row["intelligence_id"], _parse_utc_datetime(row["saved_at"]))
                for row in rows
            )
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

    def list_current_intelligence_ids(self, *, limit: int = 100) -> tuple[str, ...]:
        """Return bounded identities only; callers must re-read through TASK-019."""
        if not 1 <= limit <= 100:
            raise ValueError("intelligence list limit must be between 1 and 100")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT intelligence_id FROM intelligences "
                "WHERE current_revision_id IS NOT NULL ORDER BY created_at DESC, intelligence_id ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return tuple(str(row["intelligence_id"]) for row in rows)
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

    def list_intelligence_revision_evidence_relations(
        self, revision_id: str
    ) -> tuple[EvidenceRelationRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT revision_id, evidence_id, stance FROM intelligence_revision_evidence "
                "WHERE revision_id = :revision_id ORDER BY evidence_id ASC",
                {"revision_id": revision_id},
            ).fetchall()
            return tuple(
                EvidenceRelationRecord(
                    revision_id=str(row["revision_id"]),
                    evidence_id=str(row["evidence_id"]),
                    stance=(
                        None
                        if row["stance"] is None
                        else EvidenceStance(str(row["stance"]))
                    ),
                )
                for row in rows
            )
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

    @staticmethod
    def _weekly_brief_from_row(row: sqlite3.Row) -> WeeklyBriefRecord:
        return WeeklyBriefRecord(
            brief_id=str(row["brief_id"]),
            version=str(row["version"]),
            logical_period_id=str(row["logical_period_id"]),
            timezone=str(row["timezone"]),
            period_start=_parse_utc_datetime(str(row["period_start_utc"])),
            period_end=_parse_utc_datetime(str(row["period_end_utc"])),
            status=WeeklyBriefStatus(str(row["status"])),
            no_important_information=bool(row["no_important_information"]),
            preference_projection_hash=str(row["preference_projection_hash"]),
            generated_at=_parse_utc_datetime(str(row["generated_at"])),
            finalized_at=_parse_utc_datetime(str(row["finalized_at"])),
        )

    @staticmethod
    def _weekly_brief_item_evidence_ids(
        connection: sqlite3.Connection, brief_item_id: str
    ) -> tuple[str, ...]:
        rows = connection.execute(
            "SELECT evidence_id FROM brief_item_evidence WHERE brief_item_id = :brief_item_id "
            "ORDER BY evidence_id ASC",
            {"brief_item_id": brief_item_id},
        ).fetchall()
        return tuple(str(row["evidence_id"]) for row in rows)

    @classmethod
    def _weekly_brief_item_from_row(
        cls, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> WeeklyBriefItemRecord:
        brief_item_id = str(row["brief_item_id"])
        return WeeklyBriefItemRecord(
            brief_item_id=brief_item_id,
            brief_id=str(row["brief_id"]),
            membership_id=str(row["membership_id"]),
            topic_id=str(row["topic_id"]),
            topic_name=str(row["topic_name"]),
            intelligence_id=str(row["intelligence_id"]),
            revision_id=str(row["revision_id"]),
            association_kind=TopicAssociationKind(str(row["association_kind"])),
            claim_kind=IntelligenceClaimKind(str(row["claim_kind"])),
            source_state=IntelligenceState(str(row["source_state"])),
            summary=str(row["summary"]),
            source_content_hash=str(row["source_content_hash"]),
            position=int(row["position"]),
            evidence_ids=cls._weekly_brief_item_evidence_ids(connection, brief_item_id),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _weekly_brief_marker_from_row(row: sqlite3.Row) -> WeeklyBriefMarkerRecord:
        return WeeklyBriefMarkerRecord(
            marker_id=str(row["marker_id"]),
            brief_item_id=str(row["brief_item_id"]),
            kind=WeeklyBriefMarkerKind(str(row["marker_kind"])),
            reason=str(row["reason"]),
            current_revision_id=(
                None if row["current_revision_id"] is None else str(row["current_revision_id"])
            ),
            evidence_id=None if row["evidence_id"] is None else str(row["evidence_id"]),
            marked_at=_parse_utc_datetime(str(row["marked_at"])),
        )

    @staticmethod
    def _topic_from_row(row: sqlite3.Row) -> TopicRecord:
        return TopicRecord(
            topic_id=str(row["topic_id"]),
            name=str(row["name"]),
            pinned=bool(row["pinned"]),
            lifecycle=TopicLifecycle(str(row["lifecycle"])),
            merged_into_topic_id=(
                None if row["merged_into_topic_id"] is None else str(row["merged_into_topic_id"])
            ),
            current_event_id=(
                None if row["current_event_id"] is None else str(row["current_event_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _topic_membership_evidence_ids(
        connection: sqlite3.Connection, membership_id: str
    ) -> tuple[str, ...]:
        rows = connection.execute(
            "SELECT evidence_id FROM topic_membership_evidence "
            "WHERE membership_id = :membership_id ORDER BY evidence_id ASC",
            {"membership_id": membership_id},
        ).fetchall()
        return tuple(str(item["evidence_id"]) for item in rows)

    @classmethod
    def _topic_membership_from_row(
        cls, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> TopicMembershipRecord:
        membership_id = str(row["membership_id"])
        return TopicMembershipRecord(
            membership_id=membership_id,
            topic_id=str(row["topic_id"]),
            intelligence_id=str(row["intelligence_id"]),
            revision_id=str(row["revision_id"]),
            association_kind=TopicAssociationKind(str(row["association_kind"])),
            source_claim_kind=IntelligenceClaimKind(str(row["source_claim_kind"])),
            source_state=IntelligenceState(str(row["source_state"])),
            evidence_ids=cls._topic_membership_evidence_ids(connection, membership_id),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            effective_at=_parse_utc_datetime(str(row["effective_at"])),
        )

    @classmethod
    def _topic_timeline_event_from_row(
        cls, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> TopicTimelineEventRecord:
        event_id = str(row["event_id"])
        members = connection.execute(
            "SELECT membership_id FROM ("
            "SELECT membership_id FROM topic_timeline_event_memberships "
            "WHERE event_id = :event_id "
            "UNION "
            "SELECT primary_membership_id AS membership_id FROM topic_timeline_events "
            "WHERE event_id = :event_id"
            ") ORDER BY membership_id ASC",
            {"event_id": event_id},
        ).fetchall()
        return TopicTimelineEventRecord(
            event_id=event_id,
            topic_id=str(row["topic_id"]),
            event_kind=TopicTimelineEventKind(str(row["event_kind"])),
            state=TopicCurrentState(str(row["state"])),
            membership_ids=tuple(str(item["membership_id"]) for item in members),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _topic_relation_from_row(row: sqlite3.Row) -> TopicRelationRecord:
        return TopicRelationRecord(
            topic_id=str(row["topic_id"]),
            related_topic_id=str(row["related_topic_id"]),
            relation=TopicRelationKind(str(row["relation"])),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _topic_identity(value: str, *, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 512:
            raise ValueError(f"{field_name} is invalid")
        return value

    @staticmethod
    def _topic_name(value: str) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 240:
            raise ValueError("topic name is invalid")
        return value

    def create_topic(self, *, topic_id: str, name: str, now: datetime) -> TopicRecord:
        topic_id = self._topic_identity(topic_id, field_name="topic identity")
        name = self._topic_name(name)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM topics WHERE topic_id = :topic_id", {"topic_id": topic_id}
                ).fetchone()
                if existing is not None:
                    return self._topic_from_row(existing)
                connection.execute(
                    "INSERT INTO topics (topic_id, name, pinned, lifecycle, merged_into_topic_id, current_event_id, created_at, updated_at) "
                    "VALUES (:topic_id, :name, 0, 'ACTIVE', NULL, NULL, :now, :now)",
                    {"topic_id": topic_id, "name": name, "now": format_utc_datetime(now)},
                )
                row = connection.execute(
                    "SELECT * FROM topics WHERE topic_id = :topic_id", {"topic_id": topic_id}
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic was not saved")
                return self._topic_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("topic violates its identity contract") from error
        finally:
            connection.close()

    def get_topic(self, topic_id: str) -> TopicRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM topics WHERE topic_id = :topic_id", {"topic_id": topic_id}
            ).fetchone()
            return None if row is None else self._topic_from_row(row)
        finally:
            connection.close()

    def list_topics(self) -> tuple[TopicRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM topics ORDER BY pinned DESC, updated_at DESC, topic_id ASC"
            ).fetchall()
            return tuple(self._topic_from_row(row) for row in rows)
        finally:
            connection.close()

    def rename_topic(self, *, topic_id: str, name: str, now: datetime) -> TopicRecord:
        name = self._topic_name(name)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE topics SET name = :name, updated_at = :now WHERE topic_id = :topic_id",
                    {"topic_id": topic_id, "name": name, "now": format_utc_datetime(now)},
                ).rowcount
                if changed != 1:
                    raise StateStoreError("topic does not exist")
                row = connection.execute(
                    "SELECT * FROM topics WHERE topic_id = :topic_id", {"topic_id": topic_id}
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic was not saved")
                return self._topic_from_row(row)
        finally:
            connection.close()

    def set_topic_pinned(self, *, topic_id: str, pinned: bool, now: datetime) -> TopicRecord:
        if not isinstance(pinned, bool):
            raise ValueError("topic pin state is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE topics SET pinned = :pinned, updated_at = :now WHERE topic_id = :topic_id",
                    {"topic_id": topic_id, "pinned": int(pinned), "now": format_utc_datetime(now)},
                ).rowcount
                if changed != 1:
                    raise StateStoreError("topic does not exist")
                row = connection.execute(
                    "SELECT * FROM topics WHERE topic_id = :topic_id", {"topic_id": topic_id}
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic was not saved")
                return self._topic_from_row(row)
        finally:
            connection.close()

    def mark_topic_merged(
        self, *, source_topic_id: str, target_topic_id: str, now: datetime
    ) -> TopicRecord:
        if source_topic_id == target_topic_id:
            raise ValueError("topic merge requires different topics")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE topics SET lifecycle = 'MERGED', merged_into_topic_id = :target_topic_id, updated_at = :now "
                    "WHERE topic_id = :source_topic_id AND lifecycle = 'ACTIVE'",
                    {
                        "source_topic_id": source_topic_id,
                        "target_topic_id": target_topic_id,
                        "now": format_utc_datetime(now),
                    },
                ).rowcount
                if changed != 1:
                    raise StateStoreError("active source topic does not exist")
                row = connection.execute(
                    "SELECT * FROM topics WHERE topic_id = :source_topic_id",
                    {"source_topic_id": source_topic_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic was not saved")
                return self._topic_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("topic merge target is invalid") from error
        finally:
            connection.close()

    def get_topic_membership(self, membership_id: str) -> TopicMembershipRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM topic_memberships WHERE membership_id = :membership_id",
                {"membership_id": membership_id},
            ).fetchone()
            return None if row is None else self._topic_membership_from_row(connection, row)
        finally:
            connection.close()

    def list_topic_memberships(self, topic_id: str) -> tuple[TopicMembershipRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM topic_memberships WHERE topic_id = :topic_id "
                "ORDER BY created_at ASC, membership_id ASC",
                {"topic_id": topic_id},
            ).fetchall()
            return tuple(self._topic_membership_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    def list_topic_memberships_for_revision(
        self, intelligence_id: str, revision_id: str
    ) -> tuple[TopicMembershipRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM topic_memberships WHERE intelligence_id = :intelligence_id "
                "AND revision_id = :revision_id ORDER BY topic_id ASC, membership_id ASC",
                {"intelligence_id": intelligence_id, "revision_id": revision_id},
            ).fetchall()
            return tuple(self._topic_membership_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    def list_topic_memberships_between(
        self, *, start: datetime, end: datetime
    ) -> tuple[TopicMembershipRecord, ...]:
        start_text = format_utc_datetime(start)
        end_text = format_utc_datetime(end)
        if start_text >= end_text:
            raise ValueError("topic membership period is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM topic_memberships WHERE effective_at >= :start "
                "AND effective_at < :end ORDER BY effective_at ASC, membership_id ASC",
                {"start": start_text, "end": end_text},
            ).fetchall()
            return tuple(self._topic_membership_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _weekly_brief_identity(value: str, *, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 512:
            raise ValueError(f"{field_name} is invalid")
        return value

    @staticmethod
    def _weekly_brief_summary(value: str) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 4_000:
            raise ValueError("weekly brief summary is invalid")
        return value

    def create_finalized_weekly_brief(
        self,
        brief: WeeklyBriefWrite,
        *,
        items: tuple[WeeklyBriefItemWrite, ...],
        preferences: tuple[WeeklyBriefPreferenceProjectionWrite, ...],
    ) -> WeeklyBriefRecord:
        for field_name, value in (
            ("weekly brief identity", brief.brief_id),
            ("weekly logical period identity", brief.logical_period_id),
            ("weekly timezone", brief.timezone),
        ):
            self._weekly_brief_identity(value, field_name=field_name)
        _validate_sha256(
            brief.preference_projection_hash, field_name="weekly preference projection hash"
        )
        start_text = format_utc_datetime(brief.period_start)
        end_text = format_utc_datetime(brief.period_end)
        if start_text >= end_text or brief.no_important_information != (not items):
            raise ValueError("weekly brief finalization shape is invalid")
        if len({item.brief_item_id for item in items}) != len(items) or len(
            {item.topic_id for item in items}
        ) != len(items) or {item.position for item in items} != set(range(1, len(items) + 1)):
            raise ValueError("weekly brief items must have distinct identities and topics")
        if len({item.preference_id for item in preferences}) != len(preferences):
            raise ValueError("weekly brief preference projections must be unique")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM weekly_briefs WHERE logical_period_id = :logical_period_id",
                    {"logical_period_id": brief.logical_period_id},
                ).fetchone()
                if existing is not None:
                    return self._weekly_brief_from_row(existing)
                timestamp = format_utc_datetime(brief.generated_at)
                connection.execute(
                    "INSERT INTO weekly_briefs (brief_id, version, logical_period_id, timezone, "
                    "period_start_utc, period_end_utc, status, no_important_information, "
                    "preference_projection_hash, generated_at, finalized_at) "
                    "VALUES (:brief_id, 'weekly-v1', :logical_period_id, :timezone, :period_start, "
                    ":period_end, 'FINALIZED', :no_important_information, :preference_projection_hash, "
                    ":generated_at, :finalized_at)",
                    {
                        "brief_id": brief.brief_id,
                        "logical_period_id": brief.logical_period_id,
                        "timezone": brief.timezone,
                        "period_start": start_text,
                        "period_end": end_text,
                        "no_important_information": int(brief.no_important_information),
                        "preference_projection_hash": brief.preference_projection_hash,
                        "generated_at": timestamp,
                        "finalized_at": timestamp,
                    },
                )
                for item in items:
                    self._weekly_brief_identity(
                        item.brief_item_id, field_name="weekly brief item identity"
                    )
                    self._weekly_brief_identity(
                        item.membership_id, field_name="weekly brief membership identity"
                    )
                    self._weekly_brief_identity(item.topic_id, field_name="weekly topic identity")
                    self._weekly_brief_identity(
                        item.intelligence_id, field_name="weekly intelligence identity"
                    )
                    self._weekly_brief_identity(
                        item.revision_id, field_name="weekly revision identity"
                    )
                    self._topic_name(item.topic_name)
                    self._weekly_brief_summary(item.summary)
                    if (
                        item.association_kind
                        not in {
                            TopicAssociationKind.NEW_INFORMATION,
                            TopicAssociationKind.NEW_EVIDENCE,
                            TopicAssociationKind.CONTRADICTORY_INFORMATION,
                        }
                        or item.claim_kind is IntelligenceClaimKind.UNCLASSIFIED
                    ):
                        raise ValueError("weekly brief item semantics are invalid")
                    _validate_sha256(
                        item.source_content_hash, field_name="weekly source content hash"
                    )
                    evidence_ids = tuple(sorted(item.evidence_ids))
                    if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
                        raise ValueError("weekly brief item evidence is invalid")
                    connection.execute(
                        "INSERT INTO brief_items (brief_item_id, brief_id, membership_id, topic_id, "
                        "topic_name, intelligence_id, revision_id, association_kind, claim_kind, "
                        "source_state, summary, source_content_hash, position, created_at) "
                        "VALUES (:brief_item_id, :brief_id, :membership_id, :topic_id, :topic_name, "
                        ":intelligence_id, :revision_id, :association_kind, :claim_kind, :source_state, "
                        ":summary, :source_content_hash, :position, :created_at)",
                        {
                            "brief_item_id": item.brief_item_id,
                            "brief_id": brief.brief_id,
                            "membership_id": item.membership_id,
                            "topic_id": item.topic_id,
                            "topic_name": item.topic_name,
                            "intelligence_id": item.intelligence_id,
                            "revision_id": item.revision_id,
                            "association_kind": item.association_kind.value,
                            "claim_kind": item.claim_kind.value,
                            "source_state": item.source_state.value,
                            "summary": item.summary,
                            "source_content_hash": item.source_content_hash,
                            "position": item.position,
                            "created_at": timestamp,
                        },
                    )
                    for evidence_id in evidence_ids:
                        connection.execute(
                            "INSERT INTO brief_item_evidence (brief_item_id, evidence_id) "
                            "VALUES (:brief_item_id, :evidence_id)",
                            {
                                "brief_item_id": item.brief_item_id,
                                "evidence_id": evidence_id,
                            },
                        )
                for preference in preferences:
                    self._weekly_brief_identity(
                        preference.preference_id, field_name="weekly preference identity"
                    )
                    if not isinstance(preference.horizon, PreferenceHorizon) or not isinstance(
                        preference.provenance, PreferenceProvenance
                    ):
                        raise ValueError("weekly preference projection semantics are invalid")
                    _validate_sha256(
                        preference.statement_hash, field_name="weekly preference statement hash"
                    )
                    connection.execute(
                        "INSERT INTO weekly_brief_preference_projections "
                        "(brief_id, preference_id, horizon, provenance, statement_hash) "
                        "VALUES (:brief_id, :preference_id, :horizon, :provenance, :statement_hash)",
                        {
                            "brief_id": brief.brief_id,
                            "preference_id": preference.preference_id,
                            "horizon": preference.horizon.value,
                            "provenance": preference.provenance.value,
                            "statement_hash": preference.statement_hash,
                        },
                    )
                row = connection.execute(
                    "SELECT * FROM weekly_briefs WHERE brief_id = :brief_id",
                    {"brief_id": brief.brief_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("weekly brief was not saved")
                return self._weekly_brief_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("weekly brief violates its immutable provenance contract") from error
        finally:
            connection.close()

    def get_weekly_v1_brief(self, brief_id: str) -> WeeklyBriefRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM weekly_briefs WHERE brief_id = :brief_id", {"brief_id": brief_id}
            ).fetchone()
            return None if row is None else self._weekly_brief_from_row(row)
        finally:
            connection.close()

    def list_weekly_v1_briefs(self) -> tuple[WeeklyBriefRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM weekly_briefs ORDER BY period_start_utc DESC, brief_id ASC"
            ).fetchall()
            return tuple(self._weekly_brief_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_weekly_v1_brief_items(
        self, brief_id: str
    ) -> tuple[WeeklyBriefItemRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM brief_items WHERE brief_id = :brief_id "
                "ORDER BY position ASC, brief_item_id ASC",
                {"brief_id": brief_id},
            ).fetchall()
            return tuple(self._weekly_brief_item_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    def list_weekly_v1_items(self) -> tuple[WeeklyBriefItemRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM brief_items ORDER BY brief_id ASC, position ASC, brief_item_id ASC"
            ).fetchall()
            return tuple(self._weekly_brief_item_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    def list_weekly_v1_items_for_evidence(
        self, evidence_id: str
    ) -> tuple[WeeklyBriefItemRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT item.* FROM brief_items AS item JOIN brief_item_evidence AS evidence "
                "ON evidence.brief_item_id = item.brief_item_id "
                "WHERE evidence.evidence_id = :evidence_id "
                "ORDER BY item.brief_id ASC, item.brief_item_id ASC",
                {"evidence_id": evidence_id},
            ).fetchall()
            return tuple(self._weekly_brief_item_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    def list_weekly_v1_markers(
        self, brief_item_id: str
    ) -> tuple[WeeklyBriefMarkerRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM brief_item_markers WHERE brief_item_id = :brief_item_id "
                "ORDER BY marked_at ASC, marker_id ASC",
                {"brief_item_id": brief_item_id},
            ).fetchall()
            return tuple(self._weekly_brief_marker_from_row(row) for row in rows)
        finally:
            connection.close()

    def list_weekly_v1_preference_projections(
        self, brief_id: str
    ) -> tuple[WeeklyBriefPreferenceProjectionRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM weekly_brief_preference_projections WHERE brief_id = :brief_id "
                "ORDER BY preference_id ASC",
                {"brief_id": brief_id},
            ).fetchall()
            return tuple(
                WeeklyBriefPreferenceProjectionRecord(
                    brief_id=str(row["brief_id"]),
                    preference_id=str(row["preference_id"]),
                    horizon=PreferenceHorizon(str(row["horizon"])),
                    provenance=PreferenceProvenance(str(row["provenance"])),
                    statement_hash=str(row["statement_hash"]),
                )
                for row in rows
            )
        finally:
            connection.close()

    def append_weekly_v1_marker(
        self, marker: WeeklyBriefMarkerWrite, *, now: datetime
    ) -> bool:
        self._weekly_brief_identity(marker.marker_id, field_name="weekly marker identity")
        self._weekly_brief_identity(marker.brief_item_id, field_name="weekly marker item identity")
        if not isinstance(marker.kind, WeeklyBriefMarkerKind) or not marker.reason.strip():
            raise ValueError("weekly marker semantics are invalid")
        if marker.kind is WeeklyBriefMarkerKind.SUPERSEDED:
            if marker.current_revision_id is None or marker.evidence_id is not None:
                raise ValueError("weekly supersession marker source is invalid")
        elif marker.evidence_id is None or marker.current_revision_id is not None:
            raise ValueError("weekly evidence marker source is invalid")
        expected_reason = {
            WeeklyBriefMarkerKind.SUPERSEDED: (
                "A later trusted Intelligence revision supersedes this historical snapshot item."
            ),
            WeeklyBriefMarkerKind.EVIDENCE_DELETED: (
                "Historical supporting evidence was later deleted."
            ),
            WeeklyBriefMarkerKind.SOURCE_INVALIDATED: (
                "Historical supporting evidence is no longer available."
            ),
        }[marker.kind]
        if marker.reason != expected_reason:
            raise ValueError("weekly marker reason is not task-authorized")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                if connection.execute(
                    "SELECT 1 FROM brief_item_markers WHERE marker_id = :marker_id",
                    {"marker_id": marker.marker_id},
                ).fetchone() is not None:
                    return False
                connection.execute(
                    "INSERT INTO brief_item_markers (marker_id, brief_item_id, marker_kind, reason, "
                    "current_revision_id, evidence_id, marked_at) "
                    "VALUES (:marker_id, :brief_item_id, :marker_kind, :reason, "
                    ":current_revision_id, :evidence_id, :marked_at)",
                    {
                        "marker_id": marker.marker_id,
                        "brief_item_id": marker.brief_item_id,
                        "marker_kind": marker.kind.value,
                        "reason": marker.reason,
                        "current_revision_id": marker.current_revision_id,
                        "evidence_id": marker.evidence_id,
                        "marked_at": format_utc_datetime(now),
                    },
                )
                return True
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("weekly marker violates its legal source contract") from error
        finally:
            connection.close()

    def create_topic_membership(
        self, membership: TopicMembershipWrite, *, now: datetime
    ) -> TopicMembershipRecord:
        if (
            not isinstance(membership.association_kind, TopicAssociationKind)
            or not isinstance(membership.source_claim_kind, IntelligenceClaimKind)
            or membership.source_claim_kind is IntelligenceClaimKind.UNCLASSIFIED
            or not isinstance(membership.source_state, IntelligenceState)
        ):
            raise ValueError("topic membership semantics are invalid")
        for field_name, value in (
            ("membership identity", membership.membership_id),
            ("topic identity", membership.topic_id),
            ("intelligence identity", membership.intelligence_id),
            ("revision identity", membership.revision_id),
        ):
            self._topic_identity(value, field_name=field_name)
        evidence_ids = tuple(sorted(membership.evidence_ids))
        if not evidence_ids or len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("topic membership requires unique evidence identities")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM topic_memberships WHERE topic_id = :topic_id "
                    "AND intelligence_id = :intelligence_id AND revision_id = :revision_id",
                    {
                        "topic_id": membership.topic_id,
                        "intelligence_id": membership.intelligence_id,
                        "revision_id": membership.revision_id,
                    },
                ).fetchone()
                if existing is not None:
                    existing_record = self._topic_membership_from_row(connection, existing)
                    if (
                        existing_record.association_kind is not membership.association_kind
                        or existing_record.source_claim_kind is not membership.source_claim_kind
                        or existing_record.source_state is not membership.source_state
                        or existing_record.evidence_ids != evidence_ids
                    ):
                        raise IntegrityConflict("topic membership replay conflicts with immutable provenance")
                    return existing_record
                connection.execute(
                    "INSERT INTO topic_memberships (membership_id, topic_id, intelligence_id, revision_id, association_kind, source_claim_kind, source_state, created_at, effective_at) "
                    "VALUES (:membership_id, :topic_id, :intelligence_id, :revision_id, :association_kind, :source_claim_kind, :source_state, :now, :now)",
                    {
                        "membership_id": membership.membership_id,
                        "topic_id": membership.topic_id,
                        "intelligence_id": membership.intelligence_id,
                        "revision_id": membership.revision_id,
                        "association_kind": membership.association_kind.value,
                        "source_claim_kind": membership.source_claim_kind.value,
                        "source_state": membership.source_state.value,
                        "now": format_utc_datetime(now),
                    },
                )
                for evidence_id in evidence_ids:
                    connection.execute(
                        "INSERT INTO topic_membership_evidence (membership_id, evidence_id) "
                        "VALUES (:membership_id, :evidence_id)",
                        {"membership_id": membership.membership_id, "evidence_id": evidence_id},
                    )
                row = connection.execute(
                    "SELECT * FROM topic_memberships WHERE membership_id = :membership_id",
                    {"membership_id": membership.membership_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic membership was not saved")
                return self._topic_membership_from_row(connection, row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("topic membership violates its provenance contract") from error
        finally:
            connection.close()

    def create_topic_timeline_event(
        self, event: TopicTimelineEventWrite, *, now: datetime
    ) -> TopicTimelineEventRecord:
        if not isinstance(event.event_kind, TopicTimelineEventKind) or not isinstance(
            event.state, TopicCurrentState
        ):
            raise ValueError("topic timeline semantics are invalid")
        self._topic_identity(event.event_id, field_name="topic event identity")
        self._topic_identity(event.topic_id, field_name="topic identity")
        membership_ids = tuple(sorted(event.membership_ids))
        if not membership_ids or len(membership_ids) != len(set(membership_ids)):
            raise ValueError("topic timeline event requires unique membership dependencies")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM topic_timeline_events WHERE event_id = :event_id",
                    {"event_id": event.event_id},
                ).fetchone()
                if existing is not None:
                    return self._topic_timeline_event_from_row(connection, existing)
                connection.execute(
                    "INSERT INTO topic_timeline_events (event_id, topic_id, primary_membership_id, event_kind, state, created_at) "
                    "VALUES (:event_id, :topic_id, :primary_membership_id, :event_kind, :state, :now)",
                    {
                        "event_id": event.event_id,
                        "topic_id": event.topic_id,
                        "primary_membership_id": membership_ids[0],
                        "event_kind": event.event_kind.value,
                        "state": event.state.value,
                        "now": format_utc_datetime(now),
                    },
                )
                for membership_id in membership_ids:
                    connection.execute(
                        "INSERT INTO topic_timeline_event_memberships (event_id, membership_id) "
                        "VALUES (:event_id, :membership_id)",
                        {"event_id": event.event_id, "membership_id": membership_id},
                    )
                row = connection.execute(
                    "SELECT * FROM topic_timeline_events WHERE event_id = :event_id",
                    {"event_id": event.event_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic timeline event was not saved")
                return self._topic_timeline_event_from_row(connection, row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("topic timeline event violates its provenance contract") from error
        finally:
            connection.close()

    def set_topic_current_event(
        self, *, topic_id: str, event_id: str, now: datetime
    ) -> TopicRecord:
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE topics SET current_event_id = :event_id, updated_at = :now "
                    "WHERE topic_id = :topic_id",
                    {
                        "topic_id": topic_id,
                        "event_id": event_id,
                        "now": format_utc_datetime(now),
                    },
                ).rowcount
                if changed != 1:
                    raise StateStoreError("topic does not exist")
                row = connection.execute(
                    "SELECT * FROM topics WHERE topic_id = :topic_id", {"topic_id": topic_id}
                ).fetchone()
                if row is None:
                    raise StateStoreError("topic was not saved")
                return self._topic_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("topic current state must cite a meaningful event") from error
        finally:
            connection.close()

    def list_topic_timeline_events(self, topic_id: str) -> tuple[TopicTimelineEventRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM topic_timeline_events WHERE topic_id = :topic_id "
                "ORDER BY created_at ASC, event_id ASC",
                {"topic_id": topic_id},
            ).fetchall()
            return tuple(self._topic_timeline_event_from_row(connection, row) for row in rows)
        finally:
            connection.close()

    def create_topic_relation(
        self, *, topic_id: str, related_topic_id: str, now: datetime
    ) -> TopicRelationRecord:
        self._topic_identity(topic_id, field_name="topic identity")
        self._topic_identity(related_topic_id, field_name="related topic identity")
        if topic_id == related_topic_id:
            raise ValueError("topic relation requires different topics")
        first, second = sorted((topic_id, related_topic_id))
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                existing = connection.execute(
                    "SELECT * FROM topic_relations WHERE topic_id = :topic_id "
                    "AND related_topic_id = :related_topic_id",
                    {"topic_id": first, "related_topic_id": second},
                ).fetchone()
                if existing is None:
                    connection.execute(
                        "INSERT INTO topic_relations (topic_id, related_topic_id, relation, created_at) "
                        "VALUES (:topic_id, :related_topic_id, 'RELATED', :now)",
                        {
                            "topic_id": first,
                            "related_topic_id": second,
                            "now": format_utc_datetime(now),
                        },
                    )
                    existing = connection.execute(
                        "SELECT * FROM topic_relations WHERE topic_id = :topic_id "
                        "AND related_topic_id = :related_topic_id",
                        {"topic_id": first, "related_topic_id": second},
                    ).fetchone()
                if existing is None:
                    raise StateStoreError("topic relation was not saved")
                return self._topic_relation_from_row(existing)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("topic relation is invalid") from error
        finally:
            connection.close()

    def list_topic_relations(self, topic_id: str) -> tuple[TopicRelationRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM topic_relations WHERE topic_id = :topic_id OR related_topic_id = :topic_id "
                "ORDER BY created_at ASC, topic_id ASC, related_topic_id ASC",
                {"topic_id": topic_id},
            ).fetchall()
            result: list[TopicRelationRecord] = []
            for row in rows:
                record = self._topic_relation_from_row(row)
                if record.related_topic_id == topic_id:
                    result.append(
                        TopicRelationRecord(
                            topic_id=topic_id,
                            related_topic_id=record.topic_id,
                            relation=record.relation,
                            created_at=record.created_at,
                        )
                    )
                else:
                    result.append(record)
            return tuple(result)
        finally:
            connection.close()

    @staticmethod
    def _distillation_strings(value: object, *, field_name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or len(value) > 20:
            raise StateStoreError(f"distillation {field_name} is invalid")
        values = tuple(value)
        if any(
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or len(item) > 2_000
            for item in values
        ):
            raise StateStoreError(f"distillation {field_name} is invalid")
        return cast(tuple[str, ...], values)

    @classmethod
    def _distillation_card_from_row(cls, row: sqlite3.Row) -> DistillationCardRecord:
        def decode(name: str) -> tuple[str, ...]:
            try:
                value = json.loads(str(row[name]))
            except json.JSONDecodeError as error:
                raise StateStoreError("distillation card persistence is invalid") from error
            return cls._distillation_strings(value, field_name=name)

        return DistillationCardRecord(
            revision_id=str(row["revision_id"]),
            source_id=str(row["source_id"]),
            video_id=str(row["video_id"]),
            core_conclusion=str(row["core_conclusion"]),
            user_relevant_information=decode("user_relevant_information_json"),
            important_new_information=decode("important_new_information_json"),
            meaningful_details=decode("meaningful_details_json"),
            filtered_noise=decode("filtered_noise_json"),
            preference_ids=decode("preference_ids_json"),
            source_policy_revision_id=(
                None
                if row["source_policy_revision_id"] is None
                else str(row["source_policy_revision_id"])
            ),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _distillation_execution_from_row(
        row: sqlite3.Row, *, status_override: str | None = None
    ) -> DistillationExecutionRecord:
        return DistillationExecutionRecord(
            execution_id=str(row["execution_id"]),
            source_id=str(row["source_id"]),
            video_id=str(row["video_id"]),
            reason=str(row["reason"]),
            use_case=str(row["use_case"]),
            selected_provider=str(row["selected_provider"]),
            selected_model=str(row["selected_model"]),
            status=str(row["status"]) if status_override is None else status_override,
            budget_state=str(row["budget_state"]),
            invocation_count=int(row["invocation_count"]),
            intelligence_id=(
                None if row["intelligence_id"] is None else str(row["intelligence_id"])
            ),
            revision_id=None if row["revision_id"] is None else str(row["revision_id"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
            updated_at=_parse_utc_datetime(str(row["updated_at"])),
        )

    @staticmethod
    def _distillation_usage_from_row(row: sqlite3.Row) -> DistillationResourceUsageRecord:
        return DistillationResourceUsageRecord(
            execution_id=str(row["execution_id"]),
            reason=str(row["reason"]),
            use_case=str(row["use_case"]),
            source_id=str(row["source_id"]),
            video_id=str(row["video_id"]),
            intelligence_id=(
                None if row["intelligence_id"] is None else str(row["intelligence_id"])
            ),
            revision_id=None if row["revision_id"] is None else str(row["revision_id"]),
            selected_provider=str(row["selected_provider"]),
            selected_model=str(row["selected_model"]),
            actual_provider=(
                None if row["actual_provider"] is None else str(row["actual_provider"])
            ),
            actual_model=None if row["actual_model"] is None else str(row["actual_model"]),
            status=str(row["status"]),
            invocation_count=int(row["invocation_count"]),
            input_tokens=None if row["input_tokens"] is None else int(row["input_tokens"]),
            output_tokens=None if row["output_tokens"] is None else int(row["output_tokens"]),
            cost_microunits=(
                None if row["cost_microunits"] is None else int(row["cost_microunits"])
            ),
            duration_ms=None if row["duration_ms"] is None else int(row["duration_ms"]),
            budget_state=str(row["budget_state"]),
            outcome=str(row["outcome"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _distillation_no_new_usage_from_row(
        row: sqlite3.Row,
    ) -> DistillationResourceUsageRecord:
        return DistillationResourceUsageRecord(
            execution_id=str(row["execution_id"]),
            reason=str(row["reason"]),
            use_case=str(row["use_case"]),
            source_id=str(row["source_id"]),
            video_id=str(row["video_id"]),
            intelligence_id=None,
            revision_id=None,
            selected_provider=str(row["selected_provider"]),
            selected_model=str(row["selected_model"]),
            actual_provider=str(row["actual_provider"]),
            actual_model=str(row["actual_model"]),
            status="SUCCEEDED_NO_NEW_INTELLIGENCE",
            invocation_count=1,
            input_tokens=None if row["input_tokens"] is None else int(row["input_tokens"]),
            output_tokens=None if row["output_tokens"] is None else int(row["output_tokens"]),
            cost_microunits=(
                None if row["cost_microunits"] is None else int(row["cost_microunits"])
            ),
            duration_ms=None if row["duration_ms"] is None else int(row["duration_ms"]),
            budget_state=str(row["budget_state"]),
            outcome=str(row["outcome"]),
            created_at=_parse_utc_datetime(str(row["created_at"])),
        )

    @staticmethod
    def _validate_no_new_result_row(
        result: sqlite3.Row, checkpoint: sqlite3.Row
    ) -> None:
        try:
            evidence_ids = json.loads(str(result["evidence_ids_json"]))
        except (json.JSONDecodeError, TypeError) as error:
            raise StateStoreError(
                "no-new Intelligence result persistence is invalid"
            ) from error
        if (
            not isinstance(evidence_ids, list)
            or not evidence_ids
            or any(
                not isinstance(evidence_id, str)
                or not evidence_id.strip()
                or evidence_id != evidence_id.strip()
                for evidence_id in evidence_ids
            )
            or evidence_ids != sorted(evidence_ids)
            or len(evidence_ids) != len(set(evidence_ids))
        ):
            raise StateStoreError("no-new Intelligence Evidence binding is invalid")
        canonical = json.dumps(evidence_ids, separators=(",", ":")).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != str(result["evidence_set_hash"]):
            raise StateStoreError("no-new Intelligence Evidence hash is invalid")
        if (
            str(result["execution_id"]) != str(checkpoint["execution_id"])
            or str(result["source_id"]) != str(checkpoint["source_id"])
            or str(result["video_id"]) != str(checkpoint["video_id"])
            or str(result["reason"]) != str(checkpoint["reason"])
            or str(result["use_case"]) != str(checkpoint["use_case"])
            or str(result["actual_provider"]) != str(checkpoint["selected_provider"])
            or str(result["actual_model"]) != str(checkpoint["selected_model"])
            or str(result["outcome"]) != "NO_NEW_INTELLIGENCE"
            or str(checkpoint["status"]) != "PENDING"
            or int(checkpoint["invocation_count"]) != 1
            or checkpoint["intelligence_id"] is not None
            or checkpoint["revision_id"] is not None
        ):
            raise StateStoreError("no-new Intelligence execution binding is invalid")

    def get_distillation_execution(self, execution_id: str) -> DistillationExecutionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                {"execution_id": execution_id},
            ).fetchone()
            if row is None:
                return None
            no_new = connection.execute(
                "SELECT * FROM distillation_no_new_intelligence_results "
                "WHERE execution_id = :execution_id",
                {"execution_id": execution_id},
            ).fetchone()
            if no_new is not None:
                self._validate_no_new_result_row(no_new, row)
            return self._distillation_execution_from_row(
                row,
                status_override=(
                    "SUCCEEDED_NO_NEW_INTELLIGENCE" if no_new is not None else None
                ),
            )
        finally:
            connection.close()

    def latest_distillation_execution_for_video(
        self, video_id: str
    ) -> DistillationExecutionRecord | None:
        if (
            not isinstance(video_id, str)
            or not video_id.strip()
            or video_id != video_id.strip()
            or len(video_id) > 512
        ):
            raise ValueError("video identity is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM distillation_execution_checkpoints "
                "WHERE video_id = :video_id "
                "ORDER BY updated_at DESC, execution_id DESC LIMIT 1",
                {"video_id": video_id},
            ).fetchone()
            if row is None:
                return None
            no_new = connection.execute(
                "SELECT * FROM distillation_no_new_intelligence_results "
                "WHERE execution_id = :execution_id",
                {"execution_id": str(row["execution_id"])},
            ).fetchone()
            if no_new is not None:
                self._validate_no_new_result_row(no_new, row)
            return self._distillation_execution_from_row(
                row,
                status_override=(
                    "SUCCEEDED_NO_NEW_INTELLIGENCE" if no_new is not None else None
                ),
            )
        finally:
            connection.close()

    def begin_distillation_execution(
        self, execution: DistillationExecutionWrite, *, now: datetime
    ) -> DistillationExecutionRecord:
        fields = (
            execution.execution_id,
            execution.source_id,
            execution.video_id,
            execution.reason,
            execution.use_case,
            execution.selected_provider,
            execution.selected_model,
        )
        if any(not value.strip() or len(value) > 512 for value in fields):
            raise ValueError("distillation execution identity is invalid")
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO distillation_execution_checkpoints (execution_id, source_id, video_id, reason, use_case, selected_provider, selected_model, status, budget_state, invocation_count, intelligence_id, revision_id, created_at, updated_at) "
                    "VALUES (:execution_id, :source_id, :video_id, :reason, :use_case, :selected_provider, :selected_model, 'PENDING', 'NOT_CHECKED', 0, NULL, NULL, :created_at, :updated_at)",
                    {
                        "execution_id": execution.execution_id,
                        "source_id": execution.source_id,
                        "video_id": execution.video_id,
                        "reason": execution.reason,
                        "use_case": execution.use_case,
                        "selected_provider": execution.selected_provider,
                        "selected_model": execution.selected_model,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                    {"execution_id": execution.execution_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("distillation execution was not saved")
                return self._distillation_execution_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("distillation execution identity conflicts") from error
        finally:
            connection.close()

    def reserve_distillation_execution(
        self, execution: DistillationExecutionWrite, *, now: datetime
    ) -> DistillationExecutionRecord:
        """Persist a TASK-022 execution known to be pre-dispatch.

        `RESERVED_NOT_DISPATCHED` is a finite application-contract marker on the
        existing m010 PENDING row.  Unlike a legacy PENDING row, only this marker
        combined with invocation_count=0 proves no dispatch has been claimed.
        """
        fields = (
            execution.execution_id,
            execution.source_id,
            execution.video_id,
            execution.reason,
            execution.use_case,
            execution.selected_provider,
            execution.selected_model,
        )
        if any(not value.strip() or len(value) > 512 for value in fields):
            raise ValueError("distillation execution identity is invalid")
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                connection.execute(
                    "INSERT INTO distillation_execution_checkpoints (execution_id, source_id, video_id, reason, use_case, selected_provider, selected_model, status, budget_state, invocation_count, intelligence_id, revision_id, created_at, updated_at) "
                    "VALUES (:execution_id, :source_id, :video_id, :reason, :use_case, :selected_provider, :selected_model, 'PENDING', 'RESERVED_NOT_DISPATCHED', 0, NULL, NULL, :created_at, :updated_at)",
                    {
                        "execution_id": execution.execution_id,
                        "source_id": execution.source_id,
                        "video_id": execution.video_id,
                        "reason": execution.reason,
                        "use_case": execution.use_case,
                        "selected_provider": execution.selected_provider,
                        "selected_model": execution.selected_model,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                    {"execution_id": execution.execution_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("distillation reservation was not saved")
                return self._distillation_execution_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("distillation reservation identity conflicts") from error
        finally:
            connection.close()

    def claim_reserved_distillation_execution(
        self,
        *,
        execution_id: str,
        source_id: str,
        video_id: str,
        reason: str,
        use_case: str,
        selected_provider: str,
        selected_model: str,
        now: datetime,
    ) -> bool:
        """Atomically claim the one permitted external dispatch boundary.

        A successful claim records that a transport call may follow *before* the
        call is made.  A crash after this point is deliberately not resumable as
        a new dispatch: the caller must surface AMBIGUOUS instead.
        """
        fields = (
            execution_id,
            source_id,
            video_id,
            reason,
            use_case,
            selected_provider,
            selected_model,
        )
        if any(not isinstance(value, str) or not value.strip() or len(value) > 512 for value in fields):
            raise ValueError("distillation execution identity is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE distillation_execution_checkpoints "
                    "SET budget_state = 'DISPATCH_CLAIMED', invocation_count = 1, updated_at = :updated_at "
                    "WHERE execution_id = :execution_id "
                    "AND source_id = :source_id AND video_id = :video_id "
                    "AND reason = :reason AND use_case = :use_case "
                    "AND selected_provider = :selected_provider AND selected_model = :selected_model "
                    "AND status = 'PENDING' AND budget_state = 'RESERVED_NOT_DISPATCHED' "
                    "AND invocation_count = 0",
                    {
                        "execution_id": execution_id,
                        "source_id": source_id,
                        "video_id": video_id,
                        "reason": reason,
                        "use_case": use_case,
                        "selected_provider": selected_provider,
                        "selected_model": selected_model,
                        "updated_at": format_utc_datetime(now),
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    def claim_distillation_execution(
        self,
        *,
        execution_id: str,
        source_id: str,
        video_id: str,
        reason: str,
        use_case: str,
        selected_provider: str,
        selected_model: str,
        now: datetime,
    ) -> bool:
        """Claim a directly-started execution before its one transport call."""
        fields = (
            execution_id,
            source_id,
            video_id,
            reason,
            use_case,
            selected_provider,
            selected_model,
        )
        if any(
            not isinstance(value, str)
            or not value.strip()
            or len(value) > 512
            for value in fields
        ):
            raise ValueError("distillation execution identity is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                changed = connection.execute(
                    "UPDATE distillation_execution_checkpoints "
                    "SET budget_state = 'DISPATCH_CLAIMED', invocation_count = 1, "
                    "updated_at = :updated_at "
                    "WHERE execution_id = :execution_id "
                    "AND source_id = :source_id AND video_id = :video_id "
                    "AND reason = :reason AND use_case = :use_case "
                    "AND selected_provider = :selected_provider "
                    "AND selected_model = :selected_model "
                    "AND status = 'PENDING' AND budget_state = 'NOT_CHECKED' "
                    "AND invocation_count = 0",
                    {
                        "execution_id": execution_id,
                        "source_id": source_id,
                        "video_id": video_id,
                        "reason": reason,
                        "use_case": use_case,
                        "selected_provider": selected_provider,
                        "selected_model": selected_model,
                        "updated_at": format_utc_datetime(now),
                    },
                ).rowcount
                return changed == 1
        finally:
            connection.close()

    @staticmethod
    def _validate_observed_usage(
        *,
        status: str,
        invocation_count: int,
        actual_provider: str | None,
        actual_model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microunits: int | None,
        duration_ms: int | None,
    ) -> None:
        if invocation_count not in (0, 1):
            raise ValueError("distillation invocation count is invalid")
        if invocation_count == 0 and (actual_provider is not None or actual_model is not None):
            raise ValueError("uninvoked distillation cannot have an actual model")
        if invocation_count == 1:
            unknown_ambiguous_identity = (
                status == "AMBIGUOUS"
                and actual_provider is None
                and actual_model is None
            )
            known_actual_identity = (
                actual_provider is not None
                and actual_model is not None
                and bool(actual_provider.strip())
                and bool(actual_model.strip())
            )
            if not (unknown_ambiguous_identity or known_actual_identity):
                raise ValueError("invoked distillation requires its actual model identity")
        if (input_tokens is None) != (output_tokens is None):
            raise ValueError("token usage must be reliable or unknown as a pair")
        for value in (input_tokens, output_tokens, cost_microunits, duration_ms):
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError("distillation observed usage is invalid")

    def _insert_distillation_usage(
        self,
        connection: sqlite3.Connection,
        *,
        checkpoint: sqlite3.Row,
        status: str,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        actual_provider: str | None,
        actual_model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microunits: int | None,
        duration_ms: int | None,
        intelligence_id: str | None,
        revision_id: str | None,
        now: datetime,
    ) -> None:
        self._validate_observed_usage(
            status=status,
            invocation_count=invocation_count,
            actual_provider=actual_provider,
            actual_model=actual_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_microunits=cost_microunits,
            duration_ms=duration_ms,
        )
        connection.execute(
            "INSERT INTO distillation_resource_usage (execution_id, reason, use_case, source_id, video_id, intelligence_id, revision_id, selected_provider, selected_model, actual_provider, actual_model, status, invocation_count, input_tokens, output_tokens, cost_microunits, duration_ms, budget_state, outcome, created_at) "
            "VALUES (:execution_id, :reason, :use_case, :source_id, :video_id, :intelligence_id, :revision_id, :selected_provider, :selected_model, :actual_provider, :actual_model, :status, :invocation_count, :input_tokens, :output_tokens, :cost_microunits, :duration_ms, :budget_state, :outcome, :created_at)",
            {
                "execution_id": checkpoint["execution_id"],
                "reason": checkpoint["reason"],
                "use_case": checkpoint["use_case"],
                "source_id": checkpoint["source_id"],
                "video_id": checkpoint["video_id"],
                "intelligence_id": intelligence_id,
                "revision_id": revision_id,
                "selected_provider": checkpoint["selected_provider"],
                "selected_model": checkpoint["selected_model"],
                "actual_provider": actual_provider,
                "actual_model": actual_model,
                "status": status,
                "invocation_count": invocation_count,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_microunits": cost_microunits,
                "duration_ms": duration_ms,
                "budget_state": budget_state,
                "outcome": outcome,
                "created_at": format_utc_datetime(now),
            },
        )

    def finish_distillation_without_admission(
        self,
        *,
        execution_id: str,
        status: str,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        actual_provider: str | None,
        actual_model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microunits: int | None,
        duration_ms: int | None,
        now: datetime,
    ) -> DistillationExecutionRecord:
        if status not in {
            "WAITING_BUDGET", "WAITING_MODEL", "REJECTED_INELIGIBLE", "REJECTED_EVIDENCE",
            "REJECTED_OUTPUT", "AMBIGUOUS",
        } or not budget_state.strip() or not outcome.strip():
            raise ValueError("distillation terminal status is invalid")
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                checkpoint = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if checkpoint is None or str(checkpoint["status"]) != "PENDING":
                    raise StateStoreError("distillation execution is not safely resumable")
                connection.execute(
                    "UPDATE distillation_execution_checkpoints SET status = :status, budget_state = :budget_state, invocation_count = :invocation_count, updated_at = :updated_at WHERE execution_id = :execution_id",
                    {
                        "status": status,
                        "budget_state": budget_state,
                        "invocation_count": invocation_count,
                        "updated_at": format_utc_datetime(now),
                        "execution_id": execution_id,
                    },
                )
                self._insert_distillation_usage(
                    connection,
                    checkpoint=checkpoint,
                    status=status,
                    budget_state=budget_state,
                    outcome=outcome,
                    invocation_count=invocation_count,
                    actual_provider=actual_provider,
                    actual_model=actual_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_microunits=cost_microunits,
                    duration_ms=duration_ms,
                    intelligence_id=None,
                    revision_id=None,
                    now=now,
                )
                row = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("distillation terminal state was not saved")
                return self._distillation_execution_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("distillation terminal state violates the ledger contract") from error
        finally:
            connection.close()

    def record_distillation_no_new_intelligence(
        self,
        *,
        execution_id: str,
        evidence_ids: tuple[str, ...],
        budget_state: str,
        actual_provider: str,
        actual_model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microunits: int | None,
        duration_ms: int | None,
        now: datetime,
    ) -> DistillationExecutionRecord:
        evidence_ids = tuple(sorted(evidence_ids))
        if (
            not evidence_ids
            or len(evidence_ids) > 20
            or len(set(evidence_ids)) != len(evidence_ids)
            or any(
                not isinstance(evidence_id, str)
                or not evidence_id.strip()
                or evidence_id != evidence_id.strip()
                or len(evidence_id) > 512
                for evidence_id in evidence_ids
            )
        ):
            raise ValueError("no-new Intelligence evidence set is invalid")
        if (
            not isinstance(budget_state, str)
            or not budget_state.strip()
            or len(budget_state) > 160
            or not isinstance(actual_provider, str)
            or not actual_provider.strip()
            or len(actual_provider) > 160
            or not isinstance(actual_model, str)
            or not actual_model.strip()
            or len(actual_model) > 320
        ):
            raise ValueError("no-new Intelligence execution metadata is invalid")
        self._validate_observed_usage(
            status="SUCCEEDED_NO_NEW_INTELLIGENCE",
            invocation_count=1,
            actual_provider=actual_provider,
            actual_model=actual_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_microunits=cost_microunits,
            duration_ms=duration_ms,
        )
        encoded_evidence = json.dumps(list(evidence_ids), separators=(",", ":"))
        evidence_set_hash = hashlib.sha256(encoded_evidence.encode("utf-8")).hexdigest()
        timestamp = format_utc_datetime(now)
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                checkpoint = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints "
                    "WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if checkpoint is None or str(checkpoint["status"]) != "PENDING":
                    raise StateStoreError("distillation execution is not safely completable")
                if (
                    checkpoint["intelligence_id"] is not None
                    or checkpoint["revision_id"] is not None
                    or int(checkpoint["invocation_count"]) != 1
                    or str(checkpoint["budget_state"]) != "DISPATCH_CLAIMED"
                ):
                    raise StateStoreError("no-new Intelligence execution is not a legal invocation")
                if (
                    str(checkpoint["selected_provider"]) != actual_provider
                    or str(checkpoint["selected_model"]) != actual_model
                ):
                    raise StateStoreError(
                        "no-new Intelligence model identity does not match execution"
                    )
                legal_context = connection.execute(
                    "SELECT 1 FROM source_subscriptions AS source "
                    "JOIN source_video_links AS link ON link.source_id = source.source_id "
                    "JOIN videos AS video ON video.video_id = link.video_id "
                    "WHERE source.source_id = :source_id AND source.enabled = 1 "
                    "AND video.video_id = :video_id AND video.availability = :availability",
                    {
                        "source_id": str(checkpoint["source_id"]),
                        "video_id": str(checkpoint["video_id"]),
                        "availability": Availability.PUBLIC.value,
                    },
                ).fetchone()
                if legal_context is None:
                    raise StateStoreError(
                        "no-new Intelligence source/video authority is no longer legal"
                    )
                canonical_rows = connection.execute(
                    "SELECT evidence.evidence_id "
                    "FROM evidence JOIN artifacts "
                    "ON artifacts.artifact_id = evidence.artifact_id "
                    "WHERE evidence.video_id = :video_id "
                    "AND evidence.availability = :availability "
                    "AND artifacts.video_id = :video_id "
                    "AND artifacts.deleted_at IS NULL "
                    "AND artifacts.kind = :artifact_kind "
                    "ORDER BY evidence.evidence_id ASC LIMIT 21",
                    {
                        "video_id": str(checkpoint["video_id"]),
                        "availability": EvidenceAvailability.AVAILABLE.value,
                        "artifact_kind": ArtifactKind.TRANSCRIPT_CANONICAL.value,
                    },
                ).fetchall()
                canonical_ids = tuple(str(row["evidence_id"]) for row in canonical_rows)
                if evidence_ids != canonical_ids:
                    raise StateStoreError(
                        "no-new Intelligence requires the current canonical Evidence set"
                    )
                connection.execute(
                    "UPDATE distillation_execution_checkpoints "
                    "SET budget_state = :budget_state, invocation_count = 1, "
                    "updated_at = :updated_at WHERE execution_id = :execution_id",
                    {
                        "execution_id": execution_id,
                        "budget_state": budget_state,
                        "updated_at": timestamp,
                    },
                )
                connection.execute(
                    "INSERT INTO distillation_no_new_intelligence_results "
                    "(execution_id, source_id, video_id, reason, use_case, "
                    "evidence_ids_json, evidence_set_hash, actual_provider, actual_model, "
                    "input_tokens, output_tokens, cost_microunits, duration_ms, "
                    "budget_state, outcome, created_at) "
                    "VALUES (:execution_id, :source_id, :video_id, :reason, :use_case, "
                    ":evidence_ids_json, :evidence_set_hash, :actual_provider, "
                    ":actual_model, :input_tokens, :output_tokens, :cost_microunits, "
                    ":duration_ms, :budget_state, 'NO_NEW_INTELLIGENCE', :created_at)",
                    {
                        "execution_id": execution_id,
                        "source_id": str(checkpoint["source_id"]),
                        "video_id": str(checkpoint["video_id"]),
                        "reason": str(checkpoint["reason"]),
                        "use_case": str(checkpoint["use_case"]),
                        "evidence_ids_json": encoded_evidence,
                        "evidence_set_hash": evidence_set_hash,
                        "actual_provider": actual_provider,
                        "actual_model": actual_model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_microunits": cost_microunits,
                        "duration_ms": duration_ms,
                        "budget_state": budget_state,
                        "created_at": timestamp,
                    },
                )
                row = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints "
                    "WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("no-new Intelligence execution disappeared")
                return self._distillation_execution_from_row(
                    row, status_override="SUCCEEDED_NO_NEW_INTELLIGENCE"
                )
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict(
                "no-new Intelligence result violates its durable authority contract"
            ) from error
        finally:
            connection.close()

    def admit_distillation(
        self,
        *,
        execution_id: str,
        intelligence_id: str,
        revision_id: str,
        claim_kind: IntelligenceClaimKind,
        content_hash: str,
        evidence_ids: tuple[str, ...],
        evidence_stances: tuple[tuple[str, EvidenceStance], ...],
        card: DistillationCardWrite,
        actual_provider: str,
        actual_model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microunits: int | None,
        duration_ms: int | None,
        now: datetime,
    ) -> DistillationExecutionRecord:
        if claim_kind is IntelligenceClaimKind.UNCLASSIFIED or not isinstance(claim_kind, IntelligenceClaimKind):
            raise ValueError("distillation claim kind must be classified")
        _validate_sha256(content_hash, field_name="distillation content_hash")
        evidence_ids = tuple(sorted(evidence_ids))
        if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("distillation evidence identities are invalid")
        stance_by_id = dict(evidence_stances)
        if (
            len(stance_by_id) != len(evidence_stances)
            or set(stance_by_id) != set(evidence_ids)
            or any(not isinstance(stance, EvidenceStance) for stance in stance_by_id.values())
        ):
            raise ValueError("distillation evidence stances are invalid")
        supporting_evidence_ids = tuple(
            evidence_id
            for evidence_id in evidence_ids
            if stance_by_id[evidence_id] is EvidenceStance.SUPPORTING
        )
        if not supporting_evidence_ids:
            raise ValueError("distillation requires at least one supporting Evidence")
        if not card.core_conclusion.strip() or len(card.core_conclusion) > 4_000:
            raise ValueError("distillation card conclusion is invalid")
        encoded_card = {
            "user_relevant_information_json": json.dumps(
                self._distillation_strings(list(card.user_relevant_information), field_name="user relevance"), separators=(",", ":")
            ),
            "important_new_information_json": json.dumps(
                self._distillation_strings(list(card.important_new_information), field_name="important information"), separators=(",", ":")
            ),
            "meaningful_details_json": json.dumps(
                self._distillation_strings(list(card.meaningful_details), field_name="details"), separators=(",", ":")
            ),
            "filtered_noise_json": json.dumps(
                self._distillation_strings(list(card.filtered_noise), field_name="noise"), separators=(",", ":")
            ),
            "preference_ids_json": json.dumps(
                self._distillation_strings(list(card.preference_ids), field_name="preferences"), separators=(",", ":")
            ),
        }
        connection = self._connect()
        try:
            with _immediate_transaction(connection):
                checkpoint = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if checkpoint is None or str(checkpoint["status"]) != "PENDING":
                    raise StateStoreError("distillation execution is not safely admissible")
                if card.source_id != checkpoint["source_id"] or card.video_id != checkpoint["video_id"]:
                    raise StateStoreError("distillation card target does not match execution")
                evidence_rows = connection.execute(
                    "SELECT evidence_id, video_id, availability FROM evidence WHERE evidence_id IN ("
                    + ",".join("?" for _ in evidence_ids)
                    + ")",
                    evidence_ids,
                ).fetchall()
                evidence_by_id = {str(row["evidence_id"]): row for row in evidence_rows}
                if len(evidence_by_id) != len(evidence_ids) or any(
                    str(evidence_by_id[evidence_id]["video_id"]) != card.video_id
                    or str(evidence_by_id[evidence_id]["availability"]) != EvidenceAvailability.AVAILABLE.value
                    for evidence_id in evidence_ids
                ):
                    raise StateStoreError("distillation evidence is unavailable or foreign")
                timestamp = format_utc_datetime(now)
                connection.execute(
                    "INSERT INTO intelligences (intelligence_id, current_revision_id, created_at) VALUES (:intelligence_id, NULL, :created_at)",
                    {"intelligence_id": intelligence_id, "created_at": timestamp},
                )
                connection.execute(
                    "INSERT INTO intelligence_revisions (revision_id, intelligence_id, revision_number, prior_revision_id, interpretation_kind, claim_kind, content_hash, created_at) VALUES (:revision_id, :intelligence_id, 1, NULL, 'DISTILLATION', :claim_kind, :content_hash, :created_at)",
                    {"revision_id": revision_id, "intelligence_id": intelligence_id, "claim_kind": claim_kind.value, "content_hash": content_hash, "created_at": timestamp},
                )
                for evidence_id in evidence_ids:
                    connection.execute(
                        "INSERT INTO intelligence_revision_evidence (revision_id, evidence_id, stance) "
                        "VALUES (:revision_id, :evidence_id, :stance)",
                        {
                            "revision_id": revision_id,
                            "evidence_id": evidence_id,
                            "stance": stance_by_id[evidence_id].value,
                        },
                    )
                connection.execute(
                    "INSERT INTO intelligence_state_history (state_event_id, intelligence_id, revision_id, state, prior_state, reason, evidence_id, created_at) VALUES (:state_event_id, :intelligence_id, :revision_id, 'NEW', NULL, 'DISTILLATION_ADMITTED', :evidence_id, :created_at)",
                    {"state_event_id": f"state:{revision_id}", "intelligence_id": intelligence_id, "revision_id": revision_id, "evidence_id": supporting_evidence_ids[0], "created_at": timestamp},
                )
                connection.execute(
                    "UPDATE intelligences SET current_revision_id = :revision_id WHERE intelligence_id = :intelligence_id",
                    {"revision_id": revision_id, "intelligence_id": intelligence_id},
                )
                # Legacy EVIDENCE_SUPPORT edges are structural dependency/provenance
                # bindings for the full Evidence set. Semantic stance is owned only by
                # intelligence_revision_evidence.stance and must never be inferred here.
                for evidence_id in evidence_ids:
                    connection.execute(
                        "INSERT INTO dependency_edges (edge_id, dependent_revision_id, relation, input_evidence_id, input_revision_id, created_at) VALUES (:edge_id, :revision_id, 'EVIDENCE_SUPPORT', :evidence_id, NULL, :created_at)",
                        {"edge_id": f"support:{revision_id}:{evidence_id}", "revision_id": revision_id, "evidence_id": evidence_id, "created_at": timestamp},
                    )
                connection.execute(
                    "INSERT INTO distillation_cards (revision_id, source_id, video_id, core_conclusion, user_relevant_information_json, important_new_information_json, meaningful_details_json, filtered_noise_json, preference_ids_json, source_policy_revision_id, created_at) VALUES (:revision_id, :source_id, :video_id, :core_conclusion, :user_relevant_information_json, :important_new_information_json, :meaningful_details_json, :filtered_noise_json, :preference_ids_json, :source_policy_revision_id, :created_at)",
                    {"revision_id": revision_id, "source_id": card.source_id, "video_id": card.video_id, "core_conclusion": card.core_conclusion.strip(), "source_policy_revision_id": card.source_policy_revision_id, "created_at": timestamp, **encoded_card},
                )
                connection.execute(
                    "UPDATE distillation_execution_checkpoints SET status = 'SUCCEEDED', budget_state = 'ADMITTED', invocation_count = 1, intelligence_id = :intelligence_id, revision_id = :revision_id, updated_at = :updated_at WHERE execution_id = :execution_id",
                    {"intelligence_id": intelligence_id, "revision_id": revision_id, "updated_at": timestamp, "execution_id": execution_id},
                )
                self._insert_distillation_usage(
                    connection,
                    checkpoint=checkpoint,
                    status="SUCCEEDED",
                    budget_state="ADMITTED",
                    outcome="ADMITTED",
                    invocation_count=1,
                    actual_provider=actual_provider,
                    actual_model=actual_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_microunits=cost_microunits,
                    duration_ms=duration_ms,
                    intelligence_id=intelligence_id,
                    revision_id=revision_id,
                    now=now,
                )
                row = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if row is None:
                    raise StateStoreError("distillation admission was not saved")
                return self._distillation_execution_from_row(row)
        except sqlite3.IntegrityError as error:
            raise IntegrityConflict("distillation admission violates the evidence contract") from error
        finally:
            connection.close()

    def get_distillation_resource_usage(
        self, execution_id: str
    ) -> DistillationResourceUsageRecord:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM distillation_resource_usage WHERE execution_id = :execution_id",
                {"execution_id": execution_id},
            ).fetchone()
            if row is not None:
                return self._distillation_usage_from_row(row)
            no_new = connection.execute(
                "SELECT checkpoint.execution_id, checkpoint.reason, checkpoint.use_case, "
                "checkpoint.source_id, checkpoint.video_id, "
                "checkpoint.selected_provider, checkpoint.selected_model, "
                "result.actual_provider, result.actual_model, result.input_tokens, "
                "result.output_tokens, result.cost_microunits, result.duration_ms, "
                "result.budget_state, result.outcome, result.created_at "
                "FROM distillation_no_new_intelligence_results AS result "
                "JOIN distillation_execution_checkpoints AS checkpoint "
                "ON checkpoint.execution_id = result.execution_id "
                "WHERE result.execution_id = :execution_id",
                {"execution_id": execution_id},
            ).fetchone()
            if no_new is None:
                raise StateStoreError("distillation resource usage does not exist")
            checkpoint = connection.execute(
                "SELECT * FROM distillation_execution_checkpoints "
                "WHERE execution_id = :execution_id",
                {"execution_id": execution_id},
            ).fetchone()
            result = connection.execute(
                "SELECT * FROM distillation_no_new_intelligence_results "
                "WHERE execution_id = :execution_id",
                {"execution_id": execution_id},
            ).fetchone()
            if checkpoint is None or result is None:
                raise StateStoreError("no-new Intelligence resource binding is missing")
            self._validate_no_new_result_row(result, checkpoint)
            return self._distillation_no_new_usage_from_row(no_new)
        finally:
            connection.close()

    def list_distillation_resource_usage(
        self, *, limit: int = 100
    ) -> tuple[DistillationResourceUsageRecord, ...]:
        """Return a bounded immutable TASK-022/M5B ledger projection."""
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("distillation resource usage limit is invalid")
        connection = self._connect()
        try:
            normal_rows = connection.execute(
                "SELECT * FROM distillation_resource_usage "
                "ORDER BY created_at DESC, execution_id DESC LIMIT :limit",
                {"limit": limit},
            ).fetchall()
            zero_rows = connection.execute(
                "SELECT checkpoint.execution_id, checkpoint.reason, checkpoint.use_case, "
                "checkpoint.source_id, checkpoint.video_id, "
                "checkpoint.selected_provider, checkpoint.selected_model, "
                "result.actual_provider, result.actual_model, result.input_tokens, "
                "result.output_tokens, result.cost_microunits, result.duration_ms, "
                "result.budget_state, result.outcome, result.created_at "
                "FROM distillation_no_new_intelligence_results AS result "
                "JOIN distillation_execution_checkpoints AS checkpoint "
                "ON checkpoint.execution_id = result.execution_id "
                "ORDER BY result.created_at DESC, result.execution_id DESC LIMIT :limit",
                {"limit": limit},
            ).fetchall()
            for row in zero_rows:
                execution_id = str(row["execution_id"])
                checkpoint = connection.execute(
                    "SELECT * FROM distillation_execution_checkpoints "
                    "WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                result = connection.execute(
                    "SELECT * FROM distillation_no_new_intelligence_results "
                    "WHERE execution_id = :execution_id",
                    {"execution_id": execution_id},
                ).fetchone()
                if checkpoint is None or result is None:
                    raise StateStoreError("no-new Intelligence resource binding is missing")
                self._validate_no_new_result_row(result, checkpoint)
            combined = [
                *(self._distillation_usage_from_row(row) for row in normal_rows),
                *(self._distillation_no_new_usage_from_row(row) for row in zero_rows),
            ]
            combined.sort(
                key=lambda item: (item.created_at, item.execution_id), reverse=True
            )
            return tuple(combined[:limit])
        finally:
            connection.close()

    def get_distillation_card(self, revision_id: str) -> DistillationCardRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM distillation_cards WHERE revision_id = :revision_id",
                {"revision_id": revision_id},
            ).fetchone()
            return None if row is None else self._distillation_card_from_row(row)
        finally:
            connection.close()

    def list_distillation_cards(self) -> tuple[DistillationCardRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM distillation_cards ORDER BY created_at ASC, revision_id ASC"
            ).fetchall()
            return tuple(self._distillation_card_from_row(row) for row in rows)
        finally:
            connection.close()
