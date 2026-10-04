"""TASK-023B reservation/continuation seam preserves TASK-022 authority."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.distillation import (
    BudgetDecision,
    DistillationCommand,
    DistillationExecutionStatus,
    DistillationTransportResult,
    PersonalizedDistillationService,
)
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.source_policy import (
    MetadataFilterCandidate,
    SourcePolicyApplicationService,
    VideoType,
)
from youtube_intel.source_run import (
    SourceRunChildState,
    SourceRunPriority,
    SourceRunWrite,
)
from youtube_intel.state import (
    ArtifactKind,
    Availability,
    DistillationExecutionWrite,
    DistillationStyle,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    LiveStatus,
    SQLiteStateRepository,
    StateStoreError,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
    build_evidence_id,
)

NOW = datetime(2026, 9, 8, 10, 0, tzinfo=UTC)


class _Budget:
    def __init__(self, allowed: bool = True, state: str = "ADMITTED") -> None:
        self.decision = BudgetDecision(allowed=allowed, state=state)
        self.calls = 0

    def check(self, command: DistillationCommand) -> BudgetDecision:
        self.calls += 1
        return self.decision


class _Transport:
    is_offline_test_transport = True

    def __init__(self, raw: str, *, available: bool = True, model: str = "deterministic-v1") -> None:
        self.raw = raw
        self.available = available
        self.actual_provider = "test-transport"
        self.actual_model = model
        self.calls = 0
        self.last_input: object | None = None

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        self.last_input = command
        return DistillationTransportResult(
            raw=self.raw,
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


class _BlockingTransport(_Transport):
    def __init__(self, raw: str) -> None:
        super().__init__(raw)
        self.started = threading.Event()
        self.release = threading.Event()

    def generate(self, command: DistillationCommand) -> DistillationTransportResult:
        self.calls += 1
        self.started.set()
        assert self.release.wait(timeout=5)
        return DistillationTransportResult(
            raw=self.raw,
            actual_provider=self.actual_provider,
            actual_model=self.actual_model,
            input_tokens=120,
            output_tokens=45,
            cost_microunits=7,
            duration_ms=8,
        )


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 34
    return repository


def _source_video_evidence(repository: SQLiteStateRepository) -> tuple[str, str, str]:
    source = ProductOrchestrationService(repository, now=lambda: NOW).add_source(
        url="https://www.youtube.com/channel/UC______________________",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    video_id = "video-023b"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC______________________",
            channel_name="Fixture channel",
            title="AI Agent release",
            description="Evidence-bound execution.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=NOW,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.link_source_video(source.source_id, video_id, discovered_at=NOW)
    policy = SourcePolicyApplicationService(repository, now=lambda: NOW)
    policy.update_global(
        command_id="policy-023b",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI Agent",),
        ignore_rules=(),
        distillation_style=DistillationStyle.BALANCED,
    )
    policy.evaluate_and_record_stage_one(
        source.source_id,
        MetadataFilterCandidate(
            video_id=video_id,
            title="AI Agent release",
            description="Evidence-bound execution.",
            channel_name="Fixture channel",
            published_at=NOW,
            video_type=VideoType.STANDARD,
        ),
    )
    artifact_id = f"artifact-{video_id}"
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO artifacts (artifact_id, artifact_key, video_id, job_id, kind, storage_root, relative_path, content_hash, provider, model, producer_version, retention_class, created_at, expires_at, deleted_at) "
            "VALUES (?, ?, ?, NULL, ?, 'DATA', ?, ?, NULL, NULL, 'v1', 'LONG_LIVED', ?, NULL, NULL)",
            (artifact_id, f"key-{video_id}", video_id, ArtifactKind.TRANSCRIPT_CANONICAL.value,
             f"{video_id}.txt", "a" * 64, "2026-09-08T10:00:00.000000Z",
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
    return source.source_id, video_id, evidence_id


def _raw(evidence_id: str, *, claim_kind: str = "EVIDENCE_BACKED_STATEMENT") -> str:
    return json.dumps(
        {
            "core_conclusion": "The release has a durable execution identity.",
            "user_relevant_information": ["It prevents duplicate dispatch."],
            "important_new_information": ["Reservation remains pre-dispatch."],
            "meaningful_details": ["Evidence is retained."],
            "filtered_noise": ["Sponsor omitted."],
            "claim_kind": claim_kind,
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
    )


def _service(
    repository: SQLiteStateRepository, transport: _Transport, budget: _Budget | None = None,
) -> PersonalizedDistillationService:
    return PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: NOW),
        transport,
        budget or _Budget(),
        now=lambda: NOW,
    )


def test_reserve_mints_one_canonical_pre_dispatch_execution_without_side_effects(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    transport = _Transport(_raw(evidence_id))
    service = _service(repository, transport)

    first = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    second = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    assert first == second
    assert first.execution_id.startswith("distillation:reservation:v3:")
    checkpoint = repository.get_distillation_execution(first.execution_id)
    assert checkpoint is not None
    assert checkpoint.status == "PENDING"
    assert checkpoint.budget_state == "RESERVED_NOT_DISPATCHED"
    assert checkpoint.invocation_count == 0
    assert transport.calls == 0
    assert repository.list_distillation_cards() == ()
    with pytest.raises(StateStoreError):
        repository.get_distillation_resource_usage(first.execution_id)


def test_reserve_rejects_foreign_or_noncanonical_evidence_without_execution(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    service = _service(repository, _Transport(_raw(evidence_id)))

    with pytest.raises(ValueError, match="canonical evidence"):
        service.reserve_distillation_execution(
            source_id=source_id, video_id=video_id, evidence_ids=("foreign-evidence",)
        )
    assert repository.list_distillation_cards() == ()
    connection = repository._connect()
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM distillation_execution_checkpoints").fetchone()[0] == 0
        )
    finally:
        connection.close()


def test_reserved_identity_binds_m012_child_and_cannot_be_replaced(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(repository, _Transport(_raw(evidence_id))).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id, command_id="check-023b", priority=SourceRunPriority.P0, created_at=NOW,
        )
    )
    child = repository.record_source_run_child(
        run.run_id,
        video_id=video_id,
        state=SourceRunChildState.PENDING,
        distillation_execution_id=reservation.execution_id,
        now=NOW,
    )

    assert child.distillation_execution_id == reservation.execution_id
    connection = repository._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="identity"):
            connection.execute(
                "UPDATE source_run_video_executions SET distillation_execution_id = ? WHERE run_id = ? AND video_id = ?",
                ("other-execution", run.run_id, video_id),
            )
    finally:
        connection.close()


def test_continue_uses_exact_reserved_identity_once_and_recovers_success(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    transport = _Transport(_raw(evidence_id))
    service = _service(repository, transport)
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    first = service.continue_reserved_distillation(reservation.execution_id)
    second = service.continue_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.SUCCEEDED
    assert second == first
    assert transport.calls == 1
    assert (
        repository.get_distillation_resource_usage(reservation.execution_id).execution_id == reservation.execution_id
    )
    connection = repository._connect()
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM intelligences").fetchone()[0] == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM dependency_edges").fetchone()[0] == 1
        )
    finally:
        connection.close()


def test_reopen_continues_only_from_persisted_reservation_state(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(repository, _Transport(_raw(evidence_id))).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.initialize(now=NOW).version == 34
    transport = _Transport(_raw(evidence_id))

    result = _service(reopened, transport).continue_reserved_distillation(reservation.execution_id)

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert transport.calls == 1


def test_reserved_language_survives_preference_change_and_repository_restart(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    repository.save_global_output_language(output_language="zh-CN", now=NOW)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    first_transport = _Transport(_raw(evidence_id))
    first_service = PersonalizedDistillationService(
        repository,
        SourcePolicyApplicationService(repository, now=lambda: NOW),
        first_transport,
        _Budget(),
        now=lambda: NOW,
        output_language_for_video=lambda _video: (
            repository.get_global_user_settings().output_language
        ),
    )
    reservation = first_service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    checkpoint = repository.get_distillation_execution(reservation.execution_id)
    assert checkpoint is not None and checkpoint.output_language == "zh-CN"

    repository.save_global_output_language(output_language="en", now=NOW)
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    second_transport = _Transport(_raw(evidence_id))
    resumed_service = PersonalizedDistillationService(
        reopened,
        SourcePolicyApplicationService(reopened, now=lambda: NOW),
        second_transport,
        _Budget(),
        now=lambda: NOW,
        output_language_for_video=lambda _video: (
            reopened.get_global_user_settings().output_language
        ),
    )

    result = resumed_service.continue_reserved_distillation(
        reservation.execution_id
    )

    assert result.status is DistillationExecutionStatus.SUCCEEDED
    assert second_transport.last_input is not None
    assert second_transport.last_input.output_language == "zh-CN"

    future = resumed_service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    future_record = reopened.get_distillation_execution(future.execution_id)
    assert future_record is not None and future_record.output_language == "en"
    assert future.execution_id != reservation.execution_id


def test_v020_upgrade_keeps_historical_distillation_language_unknown(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "state.sqlite3"
    v20 = SQLiteStateRepository(path)
    migrations = v20._load_migrations()
    monkeypatch.setattr(v20, "_load_migrations", lambda: migrations[:20])
    assert v20.initialize(now=NOW).version == 20
    source_id, video_id, _evidence_id = _source_video_evidence(v20)
    historical = v20.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="historical-v020-execution",
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )
    assert historical.output_language is None

    upgraded = SQLiteStateRepository(path)
    assert upgraded.initialize(now=NOW).version == 34
    preserved = upgraded.get_distillation_execution("historical-v020-execution")
    assert preserved is not None and preserved.output_language is None
    with upgraded._connect() as connection:
        row = connection.execute(
            "SELECT output_language FROM distillation_execution_checkpoints WHERE execution_id=?",
            ("historical-v020-execution",),
        ).fetchone()
    assert row is not None and row["output_language"] is None


def test_budget_is_checked_before_claim_or_transport_and_preserves_identity(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(
        repository, _Transport(_raw(evidence_id))
    ).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    transport = _Transport(_raw(evidence_id))

    result = _service(
        repository, transport, _Budget(False, "EXHAUSTED")
    ).continue_reserved_distillation(reservation.execution_id)

    assert result.status is DistillationExecutionStatus.WAITING_BUDGET
    assert result.execution_id == reservation.execution_id
    assert result.invocation_count == 0
    assert transport.calls == 0


def test_ambiguous_or_claimed_execution_never_redispatches_after_restart(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(repository, _Transport(_raw(evidence_id))).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    unknown_transport = _UnknownTransport(_raw(evidence_id))
    first = _service(repository, unknown_transport).continue_reserved_distillation(reservation.execution_id)
    restarted_transport = _Transport(_raw(evidence_id))
    second = _service(
        SQLiteStateRepository(tmp_path / "state.sqlite3"), restarted_transport
    ).continue_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.AMBIGUOUS
    assert second == first
    assert unknown_transport.calls == 1
    assert restarted_transport.calls == 0


def test_dispatch_claim_without_response_is_persisted_as_ambiguous_not_safe_to_continue(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(repository, _Transport(_raw(evidence_id))).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=reservation.execution_id,
        source_id=source_id,
        video_id=video_id,
        reason="SOURCE_RUN_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="test-transport",
        selected_model="deterministic-v1",
        now=NOW,
    )
    transport = _Transport(_raw(evidence_id))

    result = _service(repository, transport).continue_reserved_distillation(reservation.execution_id)

    assert result.status is DistillationExecutionStatus.AMBIGUOUS
    assert result.invocation_count == 1
    assert transport.calls == 0


def test_claimed_execution_cannot_be_represented_as_a_second_reservation(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    service = _service(repository, _Transport(_raw(evidence_id)))
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    assert repository.claim_reserved_distillation_execution(
        execution_id=reservation.execution_id,
        source_id=source_id,
        video_id=video_id,
        reason="SOURCE_RUN_PERSONALIZED_DISTILLATION",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider="test-transport",
        selected_model="deterministic-v1",
        now=NOW,
    )

    with pytest.raises(StateStoreError, match="no longer a safe reservation"):
        service.reserve_distillation_execution(
            source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
        )


def test_legacy_pending_checkpoint_is_not_a_reservation_or_dispatch_authority(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    transport = _Transport(_raw(evidence_id))
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id="legacy-pending-023b",
            source_id=source_id,
            video_id=video_id,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider="test-transport",
            selected_model="deterministic-v1",
        ),
        now=NOW,
    )

    with pytest.raises(StateStoreError, match="safely reserved"):
        _service(repository, transport).continue_reserved_distillation("legacy-pending-023b")

    assert transport.calls == 0


def test_overlapping_continuations_claim_once_and_never_dispatch_twice(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(repository, _Transport(_raw(evidence_id))).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    first_transport = _BlockingTransport(_raw(evidence_id))
    first_service = _service(repository, first_transport)
    second_transport = _Transport(_raw(evidence_id))
    second_service = _service(
        SQLiteStateRepository(tmp_path / "state.sqlite3"), second_transport
    )
    first_results: list[object] = []
    worker = threading.Thread(
        target=lambda: first_results.append(
            first_service.continue_reserved_distillation(reservation.execution_id)
        ),
    )

    worker.start()
    assert first_transport.started.wait(timeout=5)
    second = second_service.continue_reserved_distillation(reservation.execution_id)
    first_transport.release.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert len(first_results) == 1
    assert second.status is DistillationExecutionStatus.AMBIGUOUS
    assert first_results[0] == second
    assert first_transport.calls == 1
    assert second_transport.calls == 0


@pytest.mark.parametrize("raw", ("{}", _raw("unused", claim_kind="UNCLASSIFIED")))
def test_terminal_validation_failures_cannot_be_retried_by_continuation(tmp_path: Path, raw: str) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    transport = _Transport(raw if raw == "{}" else _raw(evidence_id, claim_kind="UNCLASSIFIED"))
    service = _service(repository, transport)
    reservation = service.reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )

    first = service.continue_reserved_distillation(reservation.execution_id)
    second = service.continue_reserved_distillation(reservation.execution_id)

    assert first.status is DistillationExecutionStatus.REJECTED_OUTPUT
    assert second == first
    assert transport.calls == 1


def test_model_identity_is_owned_by_task022_and_migrations_remain_frozen(tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id, video_id, evidence_id = _source_video_evidence(repository)
    reservation = _service(repository, _Transport(_raw(evidence_id))).reserve_distillation_execution(
        source_id=source_id, video_id=video_id, evidence_ids=(evidence_id,)
    )
    alternate_transport = _Transport(_raw(evidence_id), model="other-model")

    with pytest.raises(ValueError, match="model identity"):
        _service(repository, alternate_transport).continue_reserved_distillation(reservation.execution_id)
    assert alternate_transport.calls == 0
    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 34
        migrations = tuple(row["name"] for row in connection.execute("SELECT name FROM schema_migrations"))
    finally:
        connection.close()
    assert "013_add_weekly_brief_foundation.sql" in migrations
    assert {
        "015_add_timed_transcript_evidence_bindings.sql",
        "016_add_ambiguous_resource_ledger_outcome.sql",
        "017_add_current_content_summary.sql",
        "018_add_global_output_language.sql",
        "019_add_evidence_excerpt_stance.sql",
        "020_add_no_new_intelligence_result.sql",
        "021_seal_distillation_output_language.sql",
    } <= set(migrations)
    assert "023_add_evidence_translation_presentation.sql" in migrations
