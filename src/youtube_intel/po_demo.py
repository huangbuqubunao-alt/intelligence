"""Isolated, deterministic Product Owner review demo runtime.

This module deliberately creates only synthetic data below ``.var/po-demo``.
It never loads application settings, credentials, a user database, or a user
Vault, and it never composes discovery, provider, or scheduler execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from youtube_intel.brief import WeeklyBriefService
from youtube_intel.distillation import (
    BudgetDecision,
    DistillationCommand,
    DistillationTransportResult,
    PersonalizedDistillationService,
)
from youtube_intel.domain import (
    Availability,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ScoreResult,
    VideoMetadata,
)
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.orchestration import (
    AutomationRunStatus,
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    SourceType,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.preference_service import PreferenceApplicationService
from youtube_intel.saved_intelligence import SavedIntelligenceService, SaveIntelligence
from youtube_intel.scoring import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AuthoritativeScoringReader,
)
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunPriority,
    SourceRunState,
    SourceRunWrite,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    AutomationRunRecord,
    AutomationScheduleRecord,
    DependencyEdgeWrite,
    DependencyRelation,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceWrite,
    IntelligenceClaimKind,
    IntelligenceInterpretationKind,
    IntelligenceRevisionWrite,
    IntelligenceState,
    JobType,
    PreferenceScope,
    ProviderCallRequest,
    ReportStatus,
    ReportWrite,
    RetentionClass,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    StorageRoot,
    TopicAssociationKind,
    build_evidence_id,
)
from youtube_intel.topic import TopicApplicationService

_NOW = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
_PIPELINE_VERSION = "po-demo-v1"
_MODEL = "demo-offline-model"
_GOLDEN_VIDEO_ID = "golden-ai-roadmap"


@dataclass(frozen=True, slots=True)
class DemoRuntime:
    root: Path
    database: Path
    application: LocalApiApplication
    scoring_reader: AuthoritativeScoringReader


class _OfflineDemoBudget:
    """Deterministic admission fixture; it never contacts a provider."""

    def check(self, command: DistillationCommand) -> BudgetDecision:
        del command
        return BudgetDecision(allowed=True, state="ADMITTED")


class _OfflineDemoTransport:
    """In-process synthetic transport allowed only by the PO-demo boundary."""

    is_offline_test_transport = True
    available = True
    actual_provider = "po-demo-offline"
    actual_model = "deterministic-v1"

    def __init__(self, raw: str) -> None:
        self._raw = raw

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        del command
        return DistillationTransportResult(
            raw=self._raw,
            actual_provider=self.actual_provider,
            actual_model=self.actual_model,
            input_tokens=None,
            output_tokens=None,
            cost_microunits=None,
            duration_ms=0,
        )


def demo_runtime_root(project_root: Path) -> Path:
    """Return the one allowable local demo root; callers cannot choose it."""

    return project_root.resolve() / ".var" / "po-demo"


def _assert_demo_root(project_root: Path) -> Path:
    project = project_root.resolve()
    root = demo_runtime_root(project)
    if root.parent != project / ".var" or root.name != "po-demo":
        raise ValueError("PO demo runtime root is invalid")
    if root.is_symlink():
        raise ValueError("PO demo runtime root must not be a symlink")
    if root.exists() and not root.is_dir():
        raise ValueError("PO demo runtime root must be a directory")
    return root


def reset_demo_runtime(project_root: Path) -> Path:
    """Delete only the designated demo root after fixed-path validation."""

    root = _assert_demo_root(project_root)
    if root.exists():
        shutil.rmtree(root)
    return root


def _source(
    source_id: str,
    name: str,
    handle: str,
    *,
    enabled: bool,
    policy: ProcessingPolicy,
) -> SourceSubscriptionRecord:
    return SourceSubscriptionRecord(
        source_id=source_id,
        source_type=SourceType.CHANNEL,
        canonical_url=f"https://www.youtube.com/{handle}",
        channel_id=None,
        video_id=None,
        display_name=name,
        enabled=enabled,
        processing_policy=policy,
        last_checked_at=None,
        last_success_at=None,
        last_error_code=None,
        last_error_message=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _video(
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str,
    *,
    offset_days: int,
) -> VideoMetadata:
    published = _NOW - timedelta(days=offset_days)
    return VideoMetadata(
        video_id=video_id,
        channel_id=channel_id,
        channel_name=channel_name,
        title=title,
        description=(
            "A synthetic, original PO review sample. It is not fetched from YouTube "
            "and is stored only in the isolated demo runtime."
        ),
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=published,
        duration_seconds=860,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _set_video_status(
    repository: SQLiteStateRepository, video_id: str, status: PipelineStatus
) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = :status, updated_at = :now "
            "WHERE video_id = :video_id",
            {
                "status": status.value,
                "now": _NOW.isoformat().replace("+00:00", "Z"),
                "video_id": video_id,
            },
        )
    finally:
        connection.close()


def _record_source_check_state(
    repository: SQLiteStateRepository,
    source_id: str,
    *,
    checked: datetime | None,
    failed: bool = False,
) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE source_subscriptions SET last_checked_at=:checked, "
            "last_success_at=:success, last_error_code=:code, last_error_message=:message, "
            "updated_at=:now WHERE source_id=:source_id",
            {
                "checked": None if checked is None else checked.isoformat().replace("+00:00", "Z"),
                "success": None if failed or checked is None else checked.isoformat().replace("+00:00", "Z"),
                "code": "SOURCE_CHECK_FAILED" if failed else None,
                "message": "The synthetic source check ended in a recorded failure." if failed else None,
                "now": _NOW.isoformat().replace("+00:00", "Z"),
                "source_id": source_id,
            },
        )
    finally:
        connection.close()


def _record_completed_job(
    repository: SQLiteStateRepository,
    *,
    job_id: str,
    video_id: str,
    stage: ProcessingStage,
    status: JobStatus = JobStatus.SUCCEEDED,
    error_code: str | None = None,
) -> None:
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{video_id}:{stage.value}",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=stage,
        pipeline_version=_PIPELINE_VERSION,
        max_attempts=1,
        available_at=_NOW,
        now=_NOW,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE jobs SET status=:status, attempt_count=1, last_error_code=:error_code, "
            "updated_at=:now, finished_at=:now WHERE job_id=:job_id",
            {
                "status": status.value,
                "error_code": error_code,
                "now": _NOW.isoformat().replace("+00:00", "Z"),
                "job_id": job_id,
            },
        )
    finally:
        connection.close()


def _write_artifact(root: Path, relative_path: str, body: bytes) -> str:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def _seed_transcript(
    repository: SQLiteStateRepository, data_root: Path, video_id: str
) -> None:
    transcript = (
        "00:00  The team begins with a customer decision log, not a feature list.\n\n"
        "00:18  Each weekly review compares the intended outcome with observed behavior.\n\n"
        "00:42  The roadmap stays small when owners record assumptions, evidence, and the next experiment.\n\n"
        "01:10  A release is complete only when the decision log explains what changed and why."
    ).encode("utf-8")
    relative = f"transcripts/{video_id}/canonical.txt"
    content_hash = _write_artifact(data_root, relative, transcript)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"demo-transcript-{video_id}",
            artifact_key=f"demo/transcript/{video_id}",
            video_id=video_id,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=content_hash,
            provider=None,
            model=None,
            producer_version="po-demo-transcript-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=_NOW,
    )


def _seed_verified_scoring(
    repository: SQLiteStateRepository, data_root: Path, video_id: str
) -> None:
    """Seed a complete synthetic PRIMARY lineage graph then use the real reader."""

    job_id = f"demo-score-{video_id}"
    _record_completed_job(
        repository, job_id=job_id, video_id=video_id, stage=ProcessingStage.SCORING
    )
    normalized = hashlib.sha256(f"po-demo:{video_id}".encode()).hexdigest()
    request = ProviderCallRequest(
        operation="local-scoring",
        normalized_input_hash=normalized,
        provider="ollama",
        model=_MODEL,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        deterministic_artifact_key="placeholder",
    )
    request_hash = request.request_hash
    request = ProviderCallRequest(
        operation=request.operation,
        normalized_input_hash=request.normalized_input_hash,
        provider=request.provider,
        model=request.model,
        prompt_version=request.prompt_version,
        schema_version=request.schema_version,
        deterministic_artifact_key=f"scoring/{request_hash}/raw",
    )
    result = ScoreResult(
        schema_version=SCHEMA_VERSION,
        score=8.6,
        reason="团队把客户证据写入决策日志，并用每周复盘验证路线图假设。",
        topics=("AI engineering", "product strategy", "decision systems"),
        should_summarize=True,
        provider="ollama",
        model=_MODEL,
        prompt_version=PROMPT_VERSION,
        request_hash=request_hash,
        output_language="zh-CN",
    )
    raw_body = b'{"synthetic":true,"kind":"offline-scoring-response"}'
    structured_body = json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    raw_relative = f"scoring/{request_hash}/raw.json"
    structured_relative = f"scoring/{request_hash}/structured.json"
    raw_hash = _write_artifact(data_root, raw_relative, raw_body)
    structured_hash = _write_artifact(data_root, structured_relative, structured_body)
    raw_id = f"demo-scoring-raw-{video_id}"
    structured_key = f"scoring/{request_hash}/structured"
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=raw_id,
            artifact_key=request.deterministic_artifact_key,
            video_id=video_id,
            job_id=job_id,
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=raw_relative,
            content_hash=raw_hash,
            provider="ollama",
            model=_MODEL,
            producer_version="scoring-raw-content-quality-v1",
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=_NOW + timedelta(days=30),
        ),
        now=_NOW,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"demo-scoring-structured-{video_id}",
            artifact_key=structured_key,
            video_id=video_id,
            job_id=job_id,
            kind=ArtifactKind.SCORING_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path=structured_relative,
            content_hash=structured_hash,
            provider="ollama",
            model=_MODEL,
            producer_version="scoring-structured-content-quality-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=_NOW,
    )
    reservation = repository.reserve_provider_call(
        request,
        owner="po-demo-seed",
        lease_until=_NOW + timedelta(minutes=5),
        available_at=_NOW,
        now=_NOW,
    )
    repository.complete_provider_call(
        reservation.record.request_hash,
        owner="po-demo-seed",
        response_artifact_id=raw_id,
        input_tokens=0,
        output_tokens=0,
        cost_microusd=0,
        now=_NOW,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE jobs SET scoring_success_provenance='PRIMARY', "
            "authoritative_scoring_artifact_key=:key WHERE job_id=:job_id",
            {"key": structured_key, "job_id": job_id},
        )
        connection.execute(
            "UPDATE videos SET pipeline_status=:status, score=8.6, should_summarize=1, "
            "authoritative_scoring_job_id=:job_id, updated_at=:now WHERE video_id=:video_id",
            {
                "status": PipelineStatus.SCORED.value,
                "job_id": job_id,
                "now": _NOW.isoformat().replace("+00:00", "Z"),
                "video_id": video_id,
            },
        )
    finally:
        connection.close()


def _seed_verified_intelligence(
    repository: SQLiteStateRepository, *, source_id: str, video_id: str
) -> str:
    """Create a verified card through TASK-022's offline test boundary only."""

    artifact_id = f"demo-transcript-{video_id}"
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=18_000,
        end_ms=42_000,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    repository.create_evidence(
        EvidenceWrite(
            evidence_id=evidence_id,
            video_id=video_id,
            artifact_id=artifact_id,
            start_ms=18_000,
            end_ms=42_000,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        ),
        now=_NOW,
    )
    policies = SourcePolicyApplicationService(repository, now=lambda: _NOW)
    policies.update_global(
        command_id="po-demo-intelligence-policy",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI",),
        ignore_rules=("rough",),
        distillation_style=DistillationStyle.BALANCED,
    )
    policies.evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(
            video_id=video_id,
            title="How teams turn AI roadmaps into decision systems",
            description="Synthetic PO-demo evidence fixture.",
            channel_name="Practical AI Engineering",
            published_at=_NOW,
            video_type=VideoType.STANDARD,
        ),
    )
    raw = json.dumps(
        {
            "core_conclusion": "Decision logs keep roadmap changes evidence-bound.",
            "user_relevant_information": ["The team can inspect the supporting transcript."],
            "important_new_information": ["Weekly review compares assumptions with outcomes."],
            "meaningful_details": ["The source records a repeatable review cadence."],
            "filtered_noise": ["Synthetic fixture only."],
            "claim_kind": "EVIDENCE_BACKED_STATEMENT",
            "evidence": [{"evidence_id": evidence_id, "start_ms": 18_000, "end_ms": 42_000}],
        },
        separators=(",", ":"),
    )
    result = PersonalizedDistillationService(
        repository,
        policies,
        _OfflineDemoTransport(raw),
        _OfflineDemoBudget(),
        now=lambda: _NOW,
    ).distill(
        DistillationCommand(
            execution_id="po-demo-distill-golden",
            source_id=source_id,
            video_id=video_id,
            evidence_ids=(evidence_id,),
            reason="PO_DEMO_SYNTHETIC_FIXTURE",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="po-demo-offline",
            selected_model="deterministic-v1",
        )
    )
    if result.intelligence_id is None:
        raise RuntimeError(
            "PO demo failed to create its deterministic Intelligence fixture: "
            f"{result.status.value}"
        )
    return result.intelligence_id


def _seed_skipped_video(repository: SQLiteStateRepository) -> None:
    """Record a legal SKIPPED decision for the Sources override surface."""

    SourcePolicyApplicationService(repository, now=lambda: _NOW).evaluate_and_record_stage_one(
        "source-ai",
        MetadataFilterCandidate(
            video_id="unverified-score",
            title="A rough scoring draft without a trusted result",
            description="Synthetic skipped-video fixture.",
            channel_name="Practical AI Engineering",
            published_at=_NOW,
            video_type=VideoType.STANDARD,
        ),
    )


def _seed_preferences(repository: SQLiteStateRepository) -> None:
    """Exercise the legal TASK-020 provenance/expiry distinctions in demo only."""

    preferences = PreferenceApplicationService(repository, now=lambda: _NOW)
    preferences.set_explicit_long_term(
        command_id="po-demo-explicit",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Prefer evidence-led product analysis.",
    )
    preferences.record_derived_recent(
        command_id="po-demo-derived",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Recent interest in evaluation practice.",
    )
    preferences.set_temporary_focus(
        command_id="po-demo-temporary",
        scope=PreferenceScope.GLOBAL_CONTENT,
        target_id=None,
        statement="Focus this week on decision logs.",
        expires_at=_NOW + timedelta(days=1),
    )


def _seed_needs_attention_run(repository: SQLiteStateRepository) -> None:
    """Persist one finite TASK-024-shaped attention state without execution."""

    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id="source-startup",
            command_id="po-demo-attention",
            priority=SourceRunPriority.P0,
            created_at=_NOW,
        )
    )
    repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE,
        now=_NOW,
    )


def _seed_weekly_v1(repository: SQLiteStateRepository, intelligence_id: str) -> None:
    """Finalize an immutable V1 snapshot from the legal Topic association."""

    topics = TopicApplicationService(repository, now=lambda: _NOW)
    topic = topics.create_topic(
        command_id="po-demo-weekly-topic", name="Decision-system practice"
    )
    topics.associate_intelligence(
        topic_id=topic.topic_id,
        intelligence_id=intelligence_id,
        kind=TopicAssociationKind.NEW_INFORMATION,
    )
    WeeklyBriefService(
        repository,
        timezone="UTC",
        now=lambda: _NOW + timedelta(days=5),
    ).finalize_week()


def _seed_weekly_correction(
    repository: SQLiteStateRepository, intelligence_id: str
) -> None:
    """Create a later legal revision and let TASK-025 add its marker."""

    verified = AuthoritativeIntelligenceReader(repository).read_current(intelligence_id)
    prior = repository.get_intelligence_revision(verified.revision_id)
    assert prior is not None
    revision_id = "po-demo-weekly-correction"
    corrected_at = _NOW + timedelta(days=7)
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=revision_id,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash=prior.content_hash,
            state=IntelligenceState.UPDATED,
            reason="Synthetic correction after the frozen Weekly snapshot.",
            evidence_ids=verified.evidence_ids,
        ),
        now=corrected_at,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{revision_id}",
            dependent_revision_id=revision_id,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=verified.evidence_ids[0],
            input_revision_id=None,
        ),
        now=corrected_at,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO distillation_cards "
            "(revision_id, source_id, video_id, core_conclusion, user_relevant_information_json, "
            "important_new_information_json, meaningful_details_json, filtered_noise_json, "
            "preference_ids_json, source_policy_revision_id, created_at) "
            "SELECT ?, source_id, video_id, core_conclusion, user_relevant_information_json, "
            "important_new_information_json, meaningful_details_json, filtered_noise_json, "
            "preference_ids_json, source_policy_revision_id, ? "
            "FROM distillation_cards WHERE revision_id = ?",
            (revision_id, corrected_at.isoformat().replace("+00:00", "Z"), prior.revision_id),
        )
    finally:
        connection.close()
    WeeklyBriefService(repository, timezone="UTC", now=lambda: corrected_at).append_correction_markers()


def _seed_unavailable_saved(
    repository: SQLiteStateRepository, source_intelligence_id: str
) -> None:
    """Preserve a Save relation after a later legal invalidation."""

    source = AuthoritativeIntelligenceReader(repository).read_current(source_intelligence_id)
    prior = repository.get_intelligence_revision(source.revision_id)
    assert prior is not None
    intelligence_id = "po-demo-unavailable-saved"
    available_revision_id = "po-demo-unavailable-saved-available"
    invalidated_revision_id = "po-demo-unavailable-saved-invalidated"
    available_at = _NOW + timedelta(days=8)
    repository.create_intelligence(intelligence_id=intelligence_id, now=available_at)
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=available_revision_id,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=source.claim_kind,
            content_hash=prior.content_hash,
            state=IntelligenceState.NEW,
            reason="Synthetic saved target before later invalidation.",
            evidence_ids=source.evidence_ids,
        ),
        now=available_at,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{available_revision_id}",
            dependent_revision_id=available_revision_id,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=source.evidence_ids[0],
            input_revision_id=None,
        ),
        now=available_at,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO distillation_cards "
            "(revision_id, source_id, video_id, core_conclusion, user_relevant_information_json, "
            "important_new_information_json, meaningful_details_json, filtered_noise_json, "
            "preference_ids_json, source_policy_revision_id, created_at) "
            "SELECT ?, source_id, video_id, core_conclusion, user_relevant_information_json, "
            "important_new_information_json, meaningful_details_json, filtered_noise_json, "
            "preference_ids_json, source_policy_revision_id, ? "
            "FROM distillation_cards WHERE revision_id = ?",
            (available_revision_id, available_at.isoformat().replace("+00:00", "Z"), prior.revision_id),
        )
    finally:
        connection.close()
    SavedIntelligenceService(repository, now=lambda: available_at).save(
        SaveIntelligence(intelligence_id=intelligence_id)
    )
    invalidated_at = available_at + timedelta(seconds=1)
    repository.append_intelligence_revision(
        intelligence_id=intelligence_id,
        revision=IntelligenceRevisionWrite(
            revision_id=invalidated_revision_id,
            interpretation_kind=IntelligenceInterpretationKind.CORRECTION,
            claim_kind=source.claim_kind,
            content_hash=prior.content_hash,
            state=IntelligenceState.INVALIDATED,
            reason="Synthetic invalidation; historical Save must not become trust.",
            evidence_ids=source.evidence_ids,
        ),
        now=invalidated_at,
    )
    repository.create_dependency_edge(
        DependencyEdgeWrite(
            edge_id=f"support:{invalidated_revision_id}",
            dependent_revision_id=invalidated_revision_id,
            relation=DependencyRelation.EVIDENCE_SUPPORT,
            input_evidence_id=source.evidence_ids[0],
            input_revision_id=None,
        ),
        now=invalidated_at,
    )


def _seed_unverified_scoring_like_artifact(
    repository: SQLiteStateRepository, data_root: Path, video_id: str
) -> None:
    body = b'{"synthetic":true,"unverified":"not authoritative"}'
    relative = f"scoring/{video_id}/unverified-raw.json"
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"demo-unverified-raw-{video_id}",
            artifact_key=f"demo/unverified/{video_id}/raw",
            video_id=video_id,
            job_id=None,
            kind=ArtifactKind.SCORING_RAW,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=_write_artifact(data_root, relative, body),
            provider="ollama",
            model=_MODEL,
            producer_version="po-demo-unverified-v1",
            retention_class=RetentionClass.RAW_RESPONSE_30D,
            expires_at=_NOW + timedelta(days=30),
        ),
        now=_NOW,
    )


def _seed_schedule(
    repository: SQLiteStateRepository,
    *,
    schedule_id: str,
    target_type: AutomationTargetType,
    target_id: str | None,
    frequency: ScheduleFrequency,
    weekday: int | None,
    local_time: str | None,
    enabled: bool,
) -> None:
    repository.create_or_update_schedule(
        AutomationScheduleRecord(
            schedule_id=schedule_id,
            target_type=target_type,
            target_id=target_id,
            frequency=frequency,
            weekday=weekday,
            local_time=local_time,
            timezone="Asia/Shanghai",
            enabled=enabled,
            created_at=_NOW,
            updated_at=_NOW,
        )
    )


def _seed_run(
    repository: SQLiteStateRepository,
    *,
    run_id: str,
    schedule_id: str,
    target_type: AutomationTargetType,
    target_id: str | None,
    status: AutomationRunStatus,
    error_code: str | None = None,
) -> None:
    scheduled_for = _NOW - timedelta(days=1)
    run = AutomationRunRecord(
        run_id=run_id,
        schedule_id=schedule_id,
        target_type=target_type,
        target_id=target_id,
        scheduled_for=scheduled_for,
        claimed_at=scheduled_for,
        started_at=None,
        finished_at=None,
        status=AutomationRunStatus.CLAIMED,
        error_code=None,
        error_message=None,
        result_summary=None,
    )
    assert repository.claim_automation_run(run=run)
    repository.finish_automation_run(
        run_id,
        status=status,
        now=scheduled_for + timedelta(minutes=2),
        error_code=error_code,
        error_message=None,
        result_summary="Synthetic PO demo history.",
    )


def _seed_reports(repository: SQLiteStateRepository, vault_root: Path) -> None:
    reports = (
        ("demo-weekly-35", 2026, 35, "Week 35: teams consolidated experiment notes and clarified ownership."),
        ("demo-weekly-36", 2026, 36, "Week 36: decision logs connected evidence, release checks, and follow-up questions."),
    )
    for report_id, year, week, content in reports:
        relative = f"reports/{year}-W{week:02d}.md"
        body = content.encode("utf-8")
        content_hash = _write_artifact(vault_root, relative, body)
        repository.upsert_report(
            ReportWrite(
                report_id=report_id,
                timezone="Asia/Shanghai",
                iso_year=year,
                iso_week=week,
                relative_path=relative,
                content_hash=content_hash,
                status=ReportStatus.WRITTEN,
            ),
            now=_NOW,
        )


def prepare_demo(project_root: Path) -> DemoRuntime:
    """Create an idempotent synthetic demo database in the fixed runtime root."""

    root = _assert_demo_root(project_root)
    database = root / "state.sqlite3"
    if database.exists():
        return _open_demo(root)
    data_root = root / "data"
    vault_root = root / "vault"
    data_root.mkdir(parents=True, exist_ok=True)
    vault_root.mkdir(parents=True, exist_ok=True)
    repository = SQLiteStateRepository(database)
    repository.initialize(now=_NOW)

    sources = (
        _source("source-ai", "Practical AI Engineering", "@practical-ai-engineering", enabled=True, policy=ProcessingPolicy.STANDARD_INTELLIGENCE),
        _source("source-product", "Product Craft Fieldnotes", "@product-craft-fieldnotes", enabled=True, policy=ProcessingPolicy.DISCOVER_ONLY),
        _source("source-startup", "Startup Systems Review", "@startup-systems-review", enabled=True, policy=ProcessingPolicy.STANDARD_INTELLIGENCE),
        _source("source-data", "Data Systems Workshop", "@data-systems-workshop", enabled=True, policy=ProcessingPolicy.DISCOVER_ONLY),
        _source("source-creator", "Creator Economy Signals", "@creator-economy-signals", enabled=False, policy=ProcessingPolicy.DISCOVER_ONLY),
    )
    for source in sources:
        repository.create_source_subscription(source)
    _record_source_check_state(repository, "source-ai", checked=_NOW - timedelta(hours=1))
    _record_source_check_state(repository, "source-product", checked=_NOW - timedelta(days=2))
    _record_source_check_state(repository, "source-startup", checked=_NOW - timedelta(hours=4), failed=True)

    videos = (
        (_GOLDEN_VIDEO_ID, "channel-ai", "Practical AI Engineering", "How teams turn AI roadmaps into decision systems", "source-ai", PipelineStatus.SCORED),
        ("unverified-score", "channel-ai", "Practical AI Engineering", "A rough scoring draft without a trusted result", "source-ai", PipelineStatus.TRANSCRIPT_READY),
        ("agent-eval-loop", "channel-ai", "Practical AI Engineering", "Designing an agent evaluation loop that teams can maintain", "source-ai", PipelineStatus.COMPLETE),
        ("product-evidence", "channel-product", "Product Craft Fieldnotes", "Research evidence that changes roadmap conversations", "source-product", PipelineStatus.METADATA_READY),
        ("service-blueprints", "channel-product", "Product Craft Fieldnotes", "Service blueprints for cross-functional product work", "source-product", PipelineStatus.DISCOVERED),
        ("pricing-memos", "channel-startup", "Startup Systems Review", "Writing pricing memos before launching an experiment", "source-startup", PipelineStatus.DEFERRED),
        ("founder-cadence", "channel-startup", "Startup Systems Review", "Founder operating cadence after product-market fit", "source-startup", PipelineStatus.METADATA_READY),
        ("event-contracts", "channel-data", "Data Systems Workshop", "Event contracts for analytics teams that move quickly", "source-data", PipelineStatus.COMPLETE),
        ("warehouse-costs", "channel-data", "Data Systems Workshop", "Warehouse cost controls for experimental data products", "source-data", PipelineStatus.DISCOVERED),
        ("community-flywheel", "channel-creator", "Creator Economy Signals", "Community flywheels with measurable creator incentives", "source-creator", PipelineStatus.METADATA_READY),
        ("newsletter-ops", "channel-creator", "Creator Economy Signals", "A lightweight operating system for independent newsletters", "source-creator", PipelineStatus.DISCOVERED),
        ("ambiguous-provider", "channel-startup", "Startup Systems Review", "Provider result uncertain after an interrupted request", "source-startup", PipelineStatus.DEFERRED),
    )
    for index, (video_id, channel_id, channel_name, title, source_id, status) in enumerate(videos):
        repository.upsert_video_metadata(
            _video(video_id, channel_id, channel_name, title, offset_days=index),
            pipeline_version=_PIPELINE_VERSION,
            now=_NOW,
        )
        repository.link_source_video(source_id, video_id, discovered_at=_NOW - timedelta(days=index))
        _set_video_status(repository, video_id, status)

    _seed_transcript(repository, data_root, _GOLDEN_VIDEO_ID)
    _seed_verified_scoring(repository, data_root, _GOLDEN_VIDEO_ID)
    intelligence_id = _seed_verified_intelligence(
        repository, source_id="source-ai", video_id=_GOLDEN_VIDEO_ID
    )
    _seed_skipped_video(repository)
    _seed_preferences(repository)
    _seed_needs_attention_run(repository)
    _seed_weekly_v1(repository, intelligence_id)
    _seed_weekly_correction(repository, intelligence_id)
    _seed_unavailable_saved(repository, intelligence_id)
    _seed_unverified_scoring_like_artifact(repository, data_root, "unverified-score")
    _record_completed_job(repository, job_id="demo-metadata-golden", video_id=_GOLDEN_VIDEO_ID, stage=ProcessingStage.METADATA)
    _record_completed_job(repository, job_id="demo-transcript-golden", video_id=_GOLDEN_VIDEO_ID, stage=ProcessingStage.TRANSCRIPT)
    _record_completed_job(repository, job_id="demo-analysis-ambiguous", video_id="ambiguous-provider", stage=ProcessingStage.ANALYSIS, status=JobStatus.FAILED_FINAL, error_code="AMBIGUOUS")

    _seed_schedule(repository, schedule_id="demo-manual", target_type=AutomationTargetType.SOURCE_CHECK, target_id="source-product", frequency=ScheduleFrequency.MANUAL, weekday=None, local_time=None, enabled=True)
    _seed_schedule(repository, schedule_id="demo-daily", target_type=AutomationTargetType.SOURCE_CHECK, target_id="source-ai", frequency=ScheduleFrequency.DAILY, weekday=None, local_time="08:30", enabled=True)
    _seed_schedule(repository, schedule_id="demo-weekly", target_type=AutomationTargetType.WEEKLY_GENERATION, target_id=None, frequency=ScheduleFrequency.WEEKLY, weekday=6, local_time="20:00", enabled=True)
    _seed_schedule(repository, schedule_id="demo-disabled", target_type=AutomationTargetType.SOURCE_CHECK, target_id="source-creator", frequency=ScheduleFrequency.DAILY, weekday=None, local_time="07:00", enabled=False)
    _seed_run(repository, run_id="run-success", schedule_id="demo-daily", target_type=AutomationTargetType.SOURCE_CHECK, target_id="source-ai", status=AutomationRunStatus.SUCCEEDED)
    _seed_run(repository, run_id="run-failed", schedule_id="demo-manual", target_type=AutomationTargetType.SOURCE_CHECK, target_id="source-product", status=AutomationRunStatus.FAILED_FINAL, error_code="SOURCE_CHECK_FAILED")
    _seed_run(repository, run_id="run-ambiguous", schedule_id="demo-weekly", target_type=AutomationTargetType.WEEKLY_GENERATION, target_id=None, status=AutomationRunStatus.FAILED_FINAL, error_code="AMBIGUOUS")
    _seed_run(repository, run_id="run-blocked", schedule_id="demo-disabled", target_type=AutomationTargetType.SOURCE_CHECK, target_id="source-creator", status=AutomationRunStatus.BLOCKED, error_code="DISABLED")
    _seed_reports(repository, vault_root)
    return _open_demo(root)


def _open_demo(root: Path) -> DemoRuntime:
    database = root / "state.sqlite3"
    repository = SQLiteStateRepository(database)
    reader = AuthoritativeScoringReader(
        repository=repository,
        data_root=root / "data",
        summary_threshold=7.0,
        pipeline_version=_PIPELINE_VERSION,
        current_model=_MODEL,
        current_output_language="zh-CN",
    )
    application = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: _NOW),
        scoring_reader=reader,
        data_root=root / "data",
        vault_root=root / "vault",
        timezone="Asia/Shanghai",
        now=lambda: _NOW,
        runtime_mode="PO_REVIEW_DEMO",
        demo_data=True,
    )
    return DemoRuntime(root, database, application, reader)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the isolated PO review demo API.")
    parser.add_argument("command", choices=("prepare", "serve", "reset"))
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "reset":
        print(reset_demo_runtime(args.project_root))
        return
    runtime = prepare_demo(args.project_root)
    if args.command == "prepare":
        print(runtime.database)
        return
    serve_loopback(runtime.application, port=args.port).serve_forever()


if __name__ == "__main__":
    main()
