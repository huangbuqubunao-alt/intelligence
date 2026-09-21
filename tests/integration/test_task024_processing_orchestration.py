"""TASK-024 durable, unified processing orchestration contracts."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.distillation import (
    BudgetDecision,
    CloudDistillationAuthorization,
    DistillationCapabilityScope,
    DistillationCommand,
    DistillationTransportResult,
    NormalV1ProductionAuthorizationAuthority,
    NvidiaNimCloudDistillationTransport,
    PersonalizedDistillationService,
)
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration import (
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.processing_orchestrator import (
    DurableProcessingOrchestrator,
    TopicAssociationUpdater,
)
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.source_run import (
    SOURCE_RUN_CHECKPOINT_ORDER,
    SourceRunAttentionReason,
    SourceRunCheckpoint,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunState,
    SourceRunTrigger,
)
from youtube_intel.state import (
    ArtifactKind,
    AutomationRunRecord,
    AutomationRunStatus,
    AutomationScheduleRecord,
    Availability,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    LiveStatus,
    PolicyOverrideMode,
    SQLiteStateRepository,
    StateStoreError,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    TopicAssociationKind,
    VideoMetadata,
    build_evidence_id,
)
from youtube_intel.topic import TopicApplicationService

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


class _Budget:
    def __init__(self, *, allowed: bool = True, state: str = "ADMITTED") -> None:
        self.decision = BudgetDecision(allowed=allowed, state=state)
        self.calls = 0

    def check(self, command: DistillationCommand) -> BudgetDecision:
        self.calls += 1
        return self.decision


class _Transport:
    is_offline_test_transport = True

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.actual_provider = "test-transport"
        self.actual_model = "deterministic-v1"
        self.calls = 0

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        evidence_id = command.evidence_ids[0]
        return DistillationTransportResult(
            raw=json.dumps(
                {
                    "core_conclusion": "The execution is evidence-bound.",
                    "user_relevant_information": ["It is restart-safe."],
                    "important_new_information": ["It is durable."],
                    "meaningful_details": ["The ledger is authoritative."],
                    "filtered_noise": ["Sponsor omitted."],
                    "claim_kind": "EVIDENCE_BACKED_STATEMENT",
                    "evidence": [
                        {
                            "evidence_id": evidence_id,
                            "start_ms": 1_000,
                            "end_ms": 1_500,
                            "stance": "supporting",
                        }
                    ],
                },
                separators=(",", ":"),
            ),
            actual_provider=self.actual_provider,
            actual_model=self.actual_model,
            input_tokens=120,
            output_tokens=45,
            cost_microunits=7,
            duration_ms=8,
        )


class _UnknownTransport(_Transport):
    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        raise RuntimeError("outcome unknown")


class _NoNewTransport(_Transport):
    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        evidence_id = command.evidence_ids[0]
        return DistillationTransportResult(
            raw=json.dumps(
                {
                    "result": "NO_NEW_INTELLIGENCE",
                    "evidence": [
                        {
                            "evidence_id": evidence_id,
                            "start_ms": 1_000,
                            "end_ms": 1_500,
                        }
                    ],
                },
                separators=(",", ":"),
            ),
            actual_provider=self.actual_provider,
            actual_model=self.actual_model,
            input_tokens=100,
            output_tokens=12,
            cost_microunits=3,
            duration_ms=5,
        )


class _BlockingTransport(_Transport):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.started.set()
        assert self.release.wait(timeout=5)
        return super().generate(command)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 20
    return repository


def _source(repository: SQLiteStateRepository, *, suffix: str = "one") -> str:
    source = ProductOrchestrationService(repository, now=lambda: NOW).add_source(
        url=f"https://www.youtube.com/channel/UC{suffix:0<22}",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    SourcePolicyApplicationService(repository, now=lambda: NOW).update_global(
        command_id=f"policy-{suffix}",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI",),
        ignore_rules=("sponsor",),
        distillation_style=DistillationStyle.BALANCED,
    )
    return source.source_id


def _video_with_evidence(
    repository: SQLiteStateRepository,
    source_id: str,
    *,
    suffix: str = "one",
    title: str = "AI release",
    published_at: datetime = NOW,
) -> tuple[str, str]:
    video_id = f"video-024-{suffix}"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UCfixture",
            channel_name="Fixture channel",
            title=title,
            description="Durable orchestration fixture.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=published_at,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.link_source_video(source_id, video_id, discovered_at=published_at)
    artifact_id = f"artifact-{video_id}"
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, "
            "storage_root, relative_path, content_hash, provider, model, producer_version, "
            "retention_class, created_at, expires_at, deleted_at) "
            "VALUES (?, ?, ?, NULL, ?, 'DATA', ?, ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (
                artifact_id,
                f"key-{video_id}",
                video_id,
                ArtifactKind.TRANSCRIPT_CANONICAL.value,
                f"{video_id}.txt",
                "a" * 64,
                "2026-09-08T12:00:00.000000Z",
            ),
        )
    finally:
        connection.close()
    evidence_id = build_evidence_id(
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    evidence = EvidenceWrite(
        evidence_id=evidence_id,
        video_id=video_id,
        artifact_id=artifact_id,
        start_ms=1_000,
        end_ms=1_500,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en",
        availability=EvidenceAvailability.AVAILABLE,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id,
        canonical_artifact_id=artifact_id,
        cues=(TimedTranscriptCueWrite(start_ms=1_000, end_ms=1_500, text="Fixture canonical evidence."),),
    )
    repository.create_timed_transcript(timed, now=NOW)
    repository.create_evidence_with_text_binding(
        evidence,
        EvidenceTextBindingWrite.from_timed_transcript(
            evidence=evidence,
            timed_transcript_id=timed.timed_transcript_id,
            start_cue_index=0,
            end_cue_index=1,
            excerpt="Fixture canonical evidence.",
        ),
        now=NOW,
    )
    return video_id, evidence_id


def _orchestrator(
    repository: SQLiteStateRepository,
    transport: _Transport,
    *,
    budget: _Budget | None = None,
    topic_updater: TopicAssociationUpdater | None = None,
) -> DurableProcessingOrchestrator:
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    return DurableProcessingOrchestrator(
        repository,
        source_policy=policy,
        distillation=PersonalizedDistillationService(
            repository,
            policy,
            transport,
            budget or _Budget(),
            now=lambda: NOW,
        ),
        topic_updater=topic_updater,
        now=lambda: NOW,
    )


def _scheduled_occurrence(
    repository: SQLiteStateRepository, source_id: str
) -> AutomationRunRecord:
    schedule = AutomationScheduleRecord(
        schedule_id=f"schedule-{source_id}",
        target_type=AutomationTargetType.SOURCE_CHECK,
        target_id=source_id,
        frequency=ScheduleFrequency.DAILY,
        weekday=None,
        local_time="12:00",
        timezone="UTC",
        enabled=True,
        created_at=NOW,
        updated_at=NOW,
    )
    repository.create_or_update_schedule(schedule)
    occurrence = AutomationRunRecord(
        run_id=f"automation-run-{source_id}",
        schedule_id=schedule.schedule_id,
        target_type=AutomationTargetType.SOURCE_CHECK,
        target_id=source_id,
        scheduled_for=NOW,
        claimed_at=NOW,
        started_at=None,
        finished_at=None,
        status=AutomationRunStatus.CLAIMED,
        error_code=None,
        error_message=None,
        result_summary=None,
    )
    assert repository.claim_automation_run(run=occurrence)
    return occurrence


def test_manual_scheduled_and_manual_analyze_use_one_durable_trigger_core(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    video_id, _ = _video_with_evidence(repository, source_id)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.evaluate_and_record_stage_one(
        source_id,
        # Make manual analyze legal through the real TASK-021 service.
        MetadataFilterCandidate(
            video_id=video_id,
            title="sponsor",
            description="Durable orchestration fixture.",
            channel_name="Fixture channel",
            published_at=NOW,
            video_type=VideoType.STANDARD,
        ),
    )
    service = _orchestrator(repository, _Transport())
    occurrence = _scheduled_occurrence(repository, source_id)

    manual = service.enqueue_manual_check_now(
        source_id=source_id, command_id="check-command", priority=SourceRunPriority.P0
    )
    scheduled = service.enqueue_scheduled_source_run(
        source_id=source_id,
        automation_run_id=occurrence.run_id,
        priority=SourceRunPriority.P2,
    )
    manual_analyze = service.enqueue_manual_analyze_video(
        source_id=source_id,
        video_id=video_id,
        command_id="analyze-command",
        priority=SourceRunPriority.P0,
    )

    assert manual.trigger is SourceRunTrigger.MANUAL_CHECK_NOW
    assert scheduled.trigger is SourceRunTrigger.SCHEDULED_SOURCE_RUN
    assert scheduled.automation_run_id == occurrence.run_id
    assert manual_analyze.trigger is SourceRunTrigger.MANUAL_ANALYZE_VIDEO
    assert manual_analyze.manual_analyze_override_id is not None
    assert manual_analyze.manual_command_id == "analyze-command"
    assert service.enqueue_manual_check_now(
        source_id=source_id, command_id="check-command", priority=SourceRunPriority.P0
    ) == manual


def test_full_run_reserves_binds_continues_and_delegates_trusted_topic_update(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    video_id, _ = _video_with_evidence(repository, source_id)
    topic_service = TopicApplicationService(repository, now=lambda: NOW)
    topic = topic_service.create_topic(command_id="topic-command", name="Durability")
    transport = _Transport()
    service = _orchestrator(
        repository,
        transport,
        topic_updater=TopicAssociationUpdater(
            topic_service,
            topic_id=topic.topic_id,
            kind=TopicAssociationKind.NEW_INFORMATION,
        ),
    )
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="check-full", priority=SourceRunPriority.P0
    )

    completed = service.resume(run.run_id)

    assert completed.state is SourceRunState.COMPLETED
    assert repository.source_run_checkpoint_progress(run.run_id).completed == SOURCE_RUN_CHECKPOINT_ORDER
    child = repository.list_source_run_children(run.run_id)
    assert len(child) == 1
    assert child[0].video_id == video_id
    assert child[0].state is SourceRunChildState.COMPLETED
    assert child[0].distillation_execution_id is not None
    assert transport.calls == 1
    assert len(topic_service.read_topic(topic.topic_id).contributions) == 1

    assert service.resume(run.run_id) == completed
    assert transport.calls == 1
    assert len(topic_service.read_topic(topic.topic_id).timeline) == 1


def test_source_run_with_no_new_intelligence_completes_without_topic_mutation(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository, suffix="zero")
    _video_with_evidence(repository, source_id, suffix="zero")
    topic_service = TopicApplicationService(repository, now=lambda: NOW)
    topic = topic_service.create_topic(command_id="topic-zero", name="Zero result")
    transport = _NoNewTransport()
    service = _orchestrator(
        repository,
        transport,
        topic_updater=TopicAssociationUpdater(
            topic_service,
            topic_id=topic.topic_id,
            kind=TopicAssociationKind.NEW_INFORMATION,
        ),
    )
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="check-zero", priority=SourceRunPriority.P0
    )

    completed = service.resume(run.run_id)

    assert completed.state is SourceRunState.COMPLETED
    child = repository.list_source_run_children(run.run_id)[0]
    assert child.state is SourceRunChildState.COMPLETED
    assert child.distillation_execution_id is not None
    execution = repository.get_distillation_execution(child.distillation_execution_id)
    assert execution is not None
    assert execution.status == "SUCCEEDED_NO_NEW_INTELLIGENCE"
    assert execution.intelligence_id is None
    assert repository.list_current_intelligence_ids() == ()
    assert topic_service.read_topic(topic.topic_id).contributions == ()
    assert transport.calls == 1

    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 20
    restarted = _orchestrator(reopened, transport)
    assert restarted.resume(run.run_id).state is SourceRunState.COMPLETED
    assert transport.calls == 1


def test_tampered_no_new_authority_cannot_complete_source_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository, suffix="zero-tamper")
    _video_with_evidence(repository, source_id, suffix="zero-tamper")
    service = _orchestrator(repository, _NoNewTransport())
    run = service.enqueue_manual_check_now(
        source_id=source_id,
        command_id="check-zero-tamper",
        priority=SourceRunPriority.P0,
    )
    original = repository.complete_source_run_checkpoint
    tampered = False

    def tamper_before_distillation_checkpoint(
        run_id: str, checkpoint: SourceRunCheckpoint, *, now: datetime
    ) -> object:
        nonlocal tampered
        if checkpoint is SourceRunCheckpoint.DISTILLATION and not tampered:
            with repository._connect() as connection:
                connection.execute(
                    "DROP TRIGGER distillation_no_new_result_immutable_update"
                )
                connection.execute(
                    "UPDATE distillation_no_new_intelligence_results "
                    "SET evidence_set_hash = ?",
                    ("0" * 64,),
                )
            tampered = True
        return original(run_id, checkpoint, now=now)

    monkeypatch.setattr(
        repository,
        "complete_source_run_checkpoint",
        tamper_before_distillation_checkpoint,
    )

    with pytest.raises(StateStoreError, match="Evidence hash"):
        service.resume(run.run_id)

    assert tampered is True
    assert service.get_run(run.run_id).state is not SourceRunState.COMPLETED


def _authorized_nvidia_transport(
    *,
    available: bool = True,
    cloud_enabled: bool = True,
    credential_available: bool = True,
    credential_resolver,
    wire_transport,
) -> NvidiaNimCloudDistillationTransport:
    eligibility = NormalV1ProductionAuthorizationAuthority.resolve(
        provider="nvidia_nim",
        model="moonshotai/kimi-k3",
        capability_scope=DistillationCapabilityScope.V1_VIDEO_DISTILLATION,
        available=available,
    )
    return NvidiaNimCloudDistillationTransport(
        authorization=CloudDistillationAuthorization.for_normal_production(
            eligibility=eligibility,
            cloud_enabled=cloud_enabled,
            credential_available=credential_available,
        ),
        credential_resolver=credential_resolver,
        wire_transport=wire_transport,
    )


def _nvidia_success_response(request: object) -> dict[str, object]:
    assert isinstance(request, dict)
    messages = request["messages"]
    assert isinstance(messages, list)
    source = json.loads(messages[2]["content"].removeprefix("UNTRUSTED_SOURCE_EVIDENCE="))
    evidence = source["evidence"][0]
    return {
        "model": "moonshotai/kimi-k3",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "core_conclusion": "The execution is evidence-bound.",
                            "user_relevant_information": ["It is restart-safe."],
                            "important_new_information": ["It is durable."],
                            "meaningful_details": ["The ledger is authoritative."],
                            "filtered_noise": ["Sponsor omitted."],
                            "claim_kind": "EVIDENCE_BACKED_STATEMENT",
                            "evidence": [
                                {
                                    "evidence_id": evidence["evidence_id"],
                                    "start_ms": evidence["start_ms"],
                                    "end_ms": evidence["end_ms"],
                                    "stance": "supporting",
                                }
                            ],
                        },
                        separators=(",", ":"),
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45},
    }


def test_authorized_nvidia_normal_source_run_uses_exact_route_once(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    credential_resolutions = 0
    wire_calls: list[tuple[str, object, float, int]] = []

    def resolve_credential() -> str:
        nonlocal credential_resolutions
        credential_resolutions += 1
        return "synthetic-nvidia-credential"

    def wire(endpoint, request, credential, timeout, retries):
        wire_calls.append((endpoint, request, timeout, retries))
        assert credential == "synthetic-nvidia-credential"
        return _nvidia_success_response(request)

    transport = _authorized_nvidia_transport(
        credential_resolver=resolve_credential,
        wire_transport=wire,
    )
    service = _orchestrator(repository, transport)  # type: ignore[arg-type]
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="task-022d-success", priority=SourceRunPriority.P0
    )

    completed = service.resume(run.run_id)

    assert completed.state is SourceRunState.COMPLETED
    assert credential_resolutions == 1
    assert len(wire_calls) == 1
    assert wire_calls[0][0] == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert wire_calls[0][2:] == (120.0, 0)
    child = repository.list_source_run_children(run.run_id)[0]
    assert child.distillation_execution_id is not None
    ledger = repository.get_distillation_resource_usage(child.distillation_execution_id)
    assert ledger.selected_provider == "nvidia_nim"
    assert ledger.selected_model == "moonshotai/kimi-k3"
    assert ledger.actual_provider == "nvidia_nim"
    assert ledger.actual_model == "moonshotai/kimi-k3"
    assert ledger.invocation_count == 1

    assert service.resume(run.run_id) == completed
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 20
    restarted = _orchestrator(reopened, transport)  # type: ignore[arg-type]
    assert restarted.resume(run.run_id) == completed
    assert credential_resolutions == 1
    assert len(wire_calls) == 1


@pytest.mark.parametrize(
    ("available", "cloud_enabled", "credential_available", "expected_reason"),
    [
        (False, True, True, SourceRunAttentionReason.MODEL_UNAVAILABLE),
        (True, False, True, SourceRunAttentionReason.MODEL_UNAVAILABLE),
        (True, True, False, SourceRunAttentionReason.MODEL_UNAVAILABLE),
    ],
)
def test_normal_source_run_missing_runtime_gate_dispatches_zero_times(
    tmp_path: Path,
    available: bool,
    cloud_enabled: bool,
    credential_available: bool,
    expected_reason: SourceRunAttentionReason,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    credential_resolutions = 0
    wire_calls = 0

    def resolve_credential() -> str:
        nonlocal credential_resolutions
        credential_resolutions += 1
        return "credential-must-not-be-resolved"

    def wire(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return _nvidia_success_response(request)

    transport = _authorized_nvidia_transport(
        available=available,
        cloud_enabled=cloud_enabled,
        credential_available=credential_available,
        credential_resolver=resolve_credential,
        wire_transport=wire,
    )
    service = _orchestrator(repository, transport)  # type: ignore[arg-type]
    run = service.enqueue_manual_check_now(
        source_id=source_id,
        command_id=f"task-022d-gate-{available}-{cloud_enabled}-{credential_available}",
        priority=SourceRunPriority.P0,
    )

    blocked = service.resume(run.run_id)

    assert blocked.state is SourceRunState.NEEDS_ATTENTION
    assert blocked.attention_reason is expected_reason
    assert credential_resolutions == 0
    assert wire_calls == 0


def test_authorization_cannot_bypass_budget_or_resolve_credential_early(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    credential_resolutions = 0
    wire_calls = 0

    def resolve_credential() -> str:
        nonlocal credential_resolutions
        credential_resolutions += 1
        return "credential-must-not-be-resolved"

    def wire(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        return _nvidia_success_response(request)

    transport = _authorized_nvidia_transport(
        credential_resolver=resolve_credential,
        wire_transport=wire,
    )
    service = _orchestrator(
        repository,
        transport,  # type: ignore[arg-type]
        budget=_Budget(allowed=False, state="EXHAUSTED"),
    )
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="task-022d-budget", priority=SourceRunPriority.P0
    )

    blocked = service.resume(run.run_id)

    assert blocked.state is SourceRunState.NEEDS_ATTENTION
    assert blocked.attention_reason is SourceRunAttentionReason.BUDGET_BLOCKED
    assert credential_resolutions == 0
    assert wire_calls == 0


def test_authorized_nvidia_ambiguous_outcome_never_redispatches(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    wire_calls = 0

    def wire(endpoint, request, credential, timeout, retries):
        nonlocal wire_calls
        wire_calls += 1
        raise RuntimeError("synthetic unknown outcome")

    transport = _authorized_nvidia_transport(
        credential_resolver=lambda: "synthetic-nvidia-credential",
        wire_transport=wire,
    )
    service = _orchestrator(repository, transport)  # type: ignore[arg-type]
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="task-022d-ambiguous", priority=SourceRunPriority.P0
    )

    attention = service.resume(run.run_id)

    assert attention.state is SourceRunState.NEEDS_ATTENTION
    assert attention.attention_reason is SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
    assert wire_calls == 1
    assert service.resume(run.run_id) == attention
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 20
    restarted = _orchestrator(reopened, transport)  # type: ignore[arg-type]
    assert restarted.resume(run.run_id) == attention
    assert wire_calls == 1


def test_durable_priority_queue_and_restart_recover_the_same_safe_run(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    service = _orchestrator(repository, _Transport())
    low = service.enqueue_manual_check_now(
        source_id=source_id, command_id="low", priority=SourceRunPriority.P3
    )
    high = service.enqueue_manual_check_now(
        source_id=source_id, command_id="high", priority=SourceRunPriority.P0
    )

    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 20
    restarted = _orchestrator(reopened, _Transport())

    assert restarted.queued_runs() == (high, low)
    assert restarted.resume_next() is not None
    assert restarted.get_run(high.run_id).state is SourceRunState.COMPLETED
    assert restarted.get_run(low.run_id).state is SourceRunState.QUEUED


def test_disabled_source_and_budget_block_are_durable_non_dispatch_states(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    transport = _Transport()
    service = _orchestrator(repository, transport, budget=_Budget(allowed=False, state="EXHAUSTED"))
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="budget", priority=SourceRunPriority.P0
    )

    blocked = service.resume(run.run_id)

    assert blocked.state is SourceRunState.NEEDS_ATTENTION
    assert blocked.attention_reason is SourceRunAttentionReason.BUDGET_BLOCKED
    assert transport.calls == 0
    assert repository.list_source_run_children(run.run_id)[0].state is SourceRunChildState.WAITING
    assert service.resume(run.run_id) == blocked
    assert transport.calls == 0

    disabled = _source(repository, suffix="disabled")
    disabled_run = service.enqueue_manual_check_now(
        source_id=disabled, command_id="disabled", priority=SourceRunPriority.P0
    )
    ProductOrchestrationService(repository, now=lambda: NOW).update_source(disabled, enabled=False)
    result = service.resume(disabled_run.run_id)
    assert result.state is SourceRunState.NEEDS_ATTENTION
    assert result.attention_reason is SourceRunAttentionReason.USER_DECISION_REQUIRED
    assert transport.calls == 0


def test_skipped_and_manual_override_children_remain_distinct_and_manual_cannot_retry_ambiguous(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    video_id, _ = _video_with_evidence(repository, source_id, title="sponsor update")
    skipped_service = _orchestrator(repository, _Transport())
    skipped_run = skipped_service.enqueue_manual_check_now(
        source_id=source_id, command_id="skip", priority=SourceRunPriority.P0
    )
    assert skipped_service.resume(skipped_run.run_id).state is SourceRunState.COMPLETED
    skipped_child = repository.list_source_run_children(skipped_run.run_id)[0]
    assert skipped_child.state is SourceRunChildState.SKIPPED
    assert skipped_child.distillation_execution_id is None

    unknown_transport = _UnknownTransport()
    manual_service = _orchestrator(repository, unknown_transport)
    manual_run = manual_service.enqueue_manual_analyze_video(
        source_id=source_id,
        video_id=video_id,
        command_id="analyze-ambiguous",
        priority=SourceRunPriority.P0,
    )
    attention = manual_service.resume(manual_run.run_id)
    assert attention.state is SourceRunState.NEEDS_ATTENTION
    assert attention.attention_reason is SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
    assert repository.list_source_run_children(manual_run.run_id)[0].state is SourceRunChildState.AMBIGUOUS
    assert unknown_transport.calls == 1
    assert manual_service.resume(manual_run.run_id) == attention
    assert unknown_transport.calls == 1


def test_per_run_limit_preserves_overflow_for_a_later_bounded_run(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.update_source(
        source_id=source_id,
        command_id="limit",
        initial_history_count=None,
        per_run_max_new_videos=1,
        focus_mode=PolicyOverrideMode.INHERIT,
        focus_rules=(),
        ignore_mode=PolicyOverrideMode.INHERIT,
        ignore_rules=(),
        distillation_style_mode=PolicyOverrideMode.INHERIT,
        distillation_style=None,
    )
    newest, _ = _video_with_evidence(
        repository, source_id, suffix="new", published_at=NOW + timedelta(minutes=1)
    )
    older, _ = _video_with_evidence(repository, source_id, suffix="old", published_at=NOW)
    # A completed initial history makes this a recurring Check Now, so the
    # per-run cap (rather than the initial-history cap) is the legal selector.
    repository.record_source_check(source_id, now=NOW, succeeded=True)
    transport = _Transport()
    service = _orchestrator(repository, transport)
    manual = service.enqueue_manual_check_now(
        source_id=source_id, command_id="manual-overlap", priority=SourceRunPriority.P0
    )
    scheduled = service.enqueue_scheduled_source_run(
        source_id=source_id,
        automation_run_id=_scheduled_occurrence(repository, source_id).run_id,
        priority=SourceRunPriority.P2,
    )

    assert service.resume(manual.run_id).state is SourceRunState.COMPLETED
    assert [child.video_id for child in repository.list_source_run_children(manual.run_id)] == [newest]
    assert service.resume(scheduled.run_id).state is SourceRunState.COMPLETED
    assert transport.calls == 2
    assert repository.source_has_video(source_id, older)
    assert [child.video_id for child in repository.list_source_run_children(scheduled.run_id)] == [older]


def test_manual_and_schedule_overlap_never_create_a_second_provider_effect(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    transport = _Transport()
    service = _orchestrator(repository, transport)
    manual = service.enqueue_manual_check_now(
        source_id=source_id, command_id="manual-overlap", priority=SourceRunPriority.P0
    )
    scheduled = service.enqueue_scheduled_source_run(
        source_id=source_id,
        automation_run_id=_scheduled_occurrence(repository, source_id).run_id,
        priority=SourceRunPriority.P2,
    )

    assert service.resume(manual.run_id).state is SourceRunState.COMPLETED
    assert service.resume(scheduled.run_id).state is SourceRunState.COMPLETED
    assert transport.calls == 1
    assert repository.list_source_run_children(scheduled.run_id) == ()


def test_one_source_run_preserves_distinct_completed_and_skipped_children(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    completed_video, _ = _video_with_evidence(repository, source_id, suffix="complete")
    skipped_video, _ = _video_with_evidence(
        repository, source_id, suffix="skip", title="sponsor update"
    )
    transport = _Transport()
    service = _orchestrator(repository, transport)
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="partial-children", priority=SourceRunPriority.P0
    )

    assert service.resume(run.run_id).state is SourceRunState.COMPLETED
    children = {child.video_id: child for child in repository.list_source_run_children(run.run_id)}
    assert children[completed_video].state is SourceRunChildState.COMPLETED
    assert children[skipped_video].state is SourceRunChildState.SKIPPED
    assert children[skipped_video].distillation_execution_id is None
    assert transport.calls == 1


@pytest.mark.parametrize(
    ("budget", "available", "reason"),
    [
        (_Budget(allowed=False, state="EXHAUSTED"), True, SourceRunAttentionReason.BUDGET_BLOCKED),
        (_Budget(), False, SourceRunAttentionReason.MODEL_UNAVAILABLE),
    ],
)
def test_manual_analyze_bypasses_relevance_only_not_budget_or_model_authorization(
    tmp_path: Path,
    budget: _Budget,
    available: bool,
    reason: SourceRunAttentionReason,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    video_id, _ = _video_with_evidence(repository, source_id, title="sponsor update")
    SourcePolicyApplicationService(repository, now=lambda: NOW).evaluate_and_record_stage_one(
        source_id,
        MetadataFilterCandidate(
            video_id=video_id,
            title="sponsor update",
            description="Durable orchestration fixture.",
            channel_name="Fixture channel",
            published_at=NOW,
            video_type=VideoType.STANDARD,
        ),
    )
    transport = _Transport(available=available)
    service = _orchestrator(repository, transport, budget=budget)
    run = service.enqueue_manual_analyze_video(
        source_id=source_id,
        video_id=video_id,
        command_id=f"manual-{reason.value}",
        priority=SourceRunPriority.P0,
    )

    attention = service.resume(run.run_id)

    assert attention.state is SourceRunState.NEEDS_ATTENTION
    assert attention.attention_reason is reason
    assert repository.list_source_run_children(run.run_id)[0].state is SourceRunChildState.WAITING
    assert transport.calls == 0


def test_database_version_and_predecessor_migrations_stay_preserved(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 20
        migrations = tuple(row["name"] for row in connection.execute("SELECT name FROM schema_migrations"))
    finally:
        connection.close()
    assert "012_add_source_run_orchestration.sql" in migrations
    assert "013_add_weekly_brief_foundation.sql" in migrations
    assert "015_add_timed_transcript_evidence_bindings.sql" in migrations
    assert "016_add_ambiguous_resource_ledger_outcome.sql" in migrations
    assert {
        "017_add_current_content_summary.sql",
        "018_add_global_output_language.sql",
        "019_add_evidence_excerpt_stance.sql",
    } <= set(migrations)


def test_existing_manual_and_scheduler_entrypoints_only_admit_the_shared_core(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    orchestrator = _orchestrator(repository, _Transport())
    product = ProductOrchestrationService(
        repository,
        source_run_submitter=orchestrator,
        now=lambda: NOW,
    )
    source_id = _source(repository, suffix="entrypoint")
    SourcePolicyApplicationService(repository, now=lambda: NOW).update_global(
        command_id="entrypoint-policy",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI",),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )

    queued = product.check_source(source_id, command_id="manual-entrypoint")
    manual = repository.list_source_runs()[0]
    assert queued.status is AutomationRunStatus.SUCCEEDED
    assert manual.trigger is SourceRunTrigger.MANUAL_CHECK_NOW
    assert manual.priority is SourceRunPriority.P0
    assert manual.state is SourceRunState.QUEUED

    repository.record_source_check(
        source_id, now=NOW - timedelta(days=2), succeeded=True
    )
    product.save_schedule(
        schedule_id=None,
        target_type=AutomationTargetType.SOURCE_CHECK,
        target_id=source_id,
        frequency=ScheduleFrequency.DAILY,
        weekday=None,
        local_time="12:00",
        timezone="UTC",
        enabled=True,
    )
    assert len(product.scheduler_tick()) == 1
    scheduled = [
        run
        for run in repository.list_source_runs()
        if run.trigger is SourceRunTrigger.SCHEDULED_SOURCE_RUN
    ]
    assert len(scheduled) == 1
    assert scheduled[0].priority is SourceRunPriority.P2
    assert scheduled[0].state is SourceRunState.QUEUED


def test_local_api_exposes_only_durable_trigger_and_status_when_core_is_injected(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    orchestrator = _orchestrator(repository, _Transport())
    product = ProductOrchestrationService(
        repository,
        source_run_submitter=orchestrator,
        now=lambda: NOW,
    )
    source_id = _source(repository, suffix="local-api")
    app = LocalApiApplication(
        repository,
        product,
        processing_orchestrator=orchestrator,
        now=lambda: NOW,
    )

    status, queued = app.handle(
        "POST",
        f"/api/v1/sources/{source_id}/check",
        b'{"command_id":"api-check"}',
    )
    assert status == 202
    assert queued["source_run"]["trigger"] == "MANUAL_CHECK_NOW"
    run_id = queued["source_run"]["run_id"]
    status, projected = app.handle("GET", f"/api/v1/source-runs/{run_id}")
    assert status == 200
    assert projected["source_run"]["state"] == "QUEUED"
    assert "attention_detail" not in projected["source_run"]


def test_restart_between_reservation_and_continuation_uses_only_persisted_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    transport = _Transport()
    service = _orchestrator(repository, transport)
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="restart-reservation", priority=SourceRunPriority.P0
    )

    def crash_before_transport(execution_id: str) -> object:
        raise RuntimeError(f"simulated restart before continuation: {execution_id}")

    monkeypatch.setattr(
        service._distillation, "continue_reserved_distillation", crash_before_transport
    )
    with pytest.raises(RuntimeError, match="simulated restart"):
        service.resume(run.run_id)
    child = repository.list_source_run_children(run.run_id)[0]
    assert child.state is SourceRunChildState.PENDING
    assert child.distillation_execution_id is not None
    checkpoint = repository.get_distillation_execution(child.distillation_execution_id)
    assert checkpoint is not None
    assert checkpoint.status == "PENDING"
    assert checkpoint.budget_state == "RESERVED_NOT_DISPATCHED"
    assert checkpoint.invocation_count == 0
    assert transport.calls == 0

    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 20
    restarted_transport = _Transport()
    restarted = _orchestrator(reopened, restarted_transport)
    assert restarted.queued_runs() == (restarted.get_run(run.run_id),)
    assert restarted.resume_next() is not None
    assert restarted.get_run(run.run_id).state is SourceRunState.COMPLETED
    assert restarted_transport.calls == 1


def test_uncertain_filter_never_calls_stage_two_or_transport(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    SourcePolicyApplicationService(repository, now=lambda: NOW).update_global(
        command_id="uncertain-policy",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=(),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )
    transport = _Transport()
    service = _orchestrator(repository, transport)
    run = service.enqueue_manual_check_now(
        source_id=source_id, command_id="uncertain", priority=SourceRunPriority.P0
    )

    attention = service.resume(run.run_id)

    assert attention.state is SourceRunState.NEEDS_ATTENTION
    assert attention.attention_reason is SourceRunAttentionReason.MODEL_UNAVAILABLE
    assert repository.list_source_run_children(run.run_id)[0].state is SourceRunChildState.WAITING
    assert transport.calls == 0
    progress = repository.source_run_checkpoint_progress(run.run_id)
    assert progress.completed[-1].value == "FILTERING"
    assert progress.next_checkpoint.value == "SOURCE_PREPARATION"


def test_untrusted_topic_callback_is_not_an_orchestrator_authority(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    transport = _Transport()
    distillation = PersonalizedDistillationService(
        repository, policy, transport, _Budget(), now=lambda: NOW
    )

    with pytest.raises(ValueError, match="topic"):
        DurableProcessingOrchestrator(
            repository,
            source_policy=policy,
            distillation=distillation,
            topic_updater=object(),  # type: ignore[arg-type]
            now=lambda: NOW,
        )

    with pytest.raises(ValueError, match="topic update configuration"):
        TopicAssociationUpdater(
            service=object(),  # type: ignore[arg-type]
            topic_id="topic-024",
            kind=TopicAssociationKind.NEW_INFORMATION,
        )


def test_concurrent_resume_never_redispatches_or_breaks_source_run_idempotency(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    _video_with_evidence(repository, source_id)
    first_transport = _BlockingTransport()
    first = _orchestrator(repository, first_transport)
    run = first.enqueue_manual_check_now(
        source_id=source_id, command_id="concurrent-resume", priority=SourceRunPriority.P0
    )
    worker_results: list[object] = []
    worker_errors: list[BaseException] = []

    def first_resume() -> None:
        try:
            worker_results.append(first.resume(run.run_id))
        except BaseException as error:  # exercise a competing worker crash boundary
            worker_errors.append(error)

    worker = threading.Thread(target=first_resume)
    worker.start()
    assert first_transport.started.wait(timeout=5)
    second_transport = _Transport()
    restarted = _orchestrator(
        SQLiteStateRepository(tmp_path / "state.sqlite3"), second_transport
    )
    second = restarted.resume(run.run_id)
    first_transport.release.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert worker_errors == []
    assert len(worker_results) == 1
    assert second.state is SourceRunState.NEEDS_ATTENTION
    assert worker_results[0] == second
    assert repository.list_source_run_children(run.run_id)[0].state is SourceRunChildState.AMBIGUOUS
    assert first_transport.calls == 1
    assert second_transport.calls == 0


def test_concurrent_checkpoint_resume_is_deduplicated_from_persisted_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    first = DurableProcessingOrchestrator(
        repository,
        source_policy=policy,
        distillation=PersonalizedDistillationService(
            repository, policy, _Transport(), _Budget(), now=lambda: NOW
        ),
        now=lambda: NOW,
    )
    run = first.enqueue_manual_check_now(
        source_id=source_id, command_id="checkpoint-race", priority=SourceRunPriority.P0
    )
    active = repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restarted_policy = SourcePolicyApplicationService(reopened, now=lambda: NOW)
    second = DurableProcessingOrchestrator(
        reopened,
        source_policy=restarted_policy,
        distillation=PersonalizedDistillationService(
            reopened,
            restarted_policy,
            _Transport(),
            _Budget(),
            now=lambda: NOW,
        ),
        now=lambda: NOW,
    )
    results: list[object] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)
    original = SQLiteStateRepository.complete_source_run_checkpoint

    def synchronized_complete(
        self: SQLiteStateRepository, run_id: str, checkpoint: object, *, now: datetime
    ) -> object:
        barrier.wait(timeout=5)
        return original(self, run_id, checkpoint, now=now)  # type: ignore[arg-type]

    monkeypatch.setattr(
        SQLiteStateRepository, "complete_source_run_checkpoint", synchronized_complete
    )

    def resume(orchestrator: DurableProcessingOrchestrator) -> None:
        try:
            orchestrator._complete_checkpoint(active, SourceRunCheckpoint.DISCOVERY)
            results.append(orchestrator.get_run(run.run_id))
        except BaseException as error:
            errors.append(error)

    first_worker = threading.Thread(target=lambda: resume(first))
    second_worker = threading.Thread(target=lambda: resume(second))
    first_worker.start()
    second_worker.start()
    first_worker.join(timeout=5)
    second_worker.join(timeout=5)

    assert not first_worker.is_alive()
    assert not second_worker.is_alive()
    assert errors == []
    assert len(results) == 2
    assert all(result == results[0] for result in results)
    assert results[0].state is SourceRunState.RUNNING
    assert repository.source_run_checkpoint_progress(run.run_id).completed == (
        SourceRunCheckpoint.DISCOVERY,
    )
