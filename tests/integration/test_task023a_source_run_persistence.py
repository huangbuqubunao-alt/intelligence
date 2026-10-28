"""TASK-023A durable Source Run persistence contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path

import pytest

import youtube_intel.state as state_mod
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.source_run import (
    SOURCE_RUN_CHECKPOINT_ORDER,
    SourceRunAttentionReason,
    SourceRunCheckpoint,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunState,
    SourceRunTrigger,
    SourceRunWrite,
    build_source_run_id,
)
from youtube_intel.state import (
    AutomationRunRecord,
    AutomationRunStatus,
    AutomationScheduleRecord,
    AutomationTargetType,
    Availability,
    DistillationExecutionWrite,
    IntegrityConflict,
    LiveStatus,
    ScheduleFrequency,
    SQLiteStateRepository,
    VideoMetadata,
)

NOW = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 43
    return repository


def _v011_migrations() -> tuple[state_mod._Migration, ...]:
    migrations: list[state_mod._Migration] = []
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
    )
    for version, name in enumerate(names, start=1):
        sql_bytes = resources.files("youtube_intel").joinpath("migrations", name).read_bytes()
        migrations.append(
            state_mod._Migration(
                version=version,
                name=name,
                sql=sql_bytes.decode("utf-8"),
                checksum=state_mod.hashlib.sha256(sql_bytes).hexdigest(),
            )
        )
    return tuple(migrations)


def _source(repository: SQLiteStateRepository, suffix: str = "one") -> str:
    source = ProductOrchestrationService(repository, now=lambda: NOW).add_source(
        url=f"https://www.youtube.com/channel/UC{suffix:0<22}",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    return source.source_id


def _video(repository: SQLiteStateRepository, source_id: str, suffix: str = "one") -> str:
    video_id = f"video-023a-{suffix}"
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UCfixture",
            channel_name="Fixture channel",
            title="Source Run fixture",
            description="Durable Source Run test fixture.",
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
    repository.link_source_video(source_id, video_id, discovered_at=NOW)
    return video_id


def _manual_check(source_id: str, command_id: str = "command-1") -> SourceRunWrite:
    return SourceRunWrite.manual_check_now(
        source_id=source_id,
        command_id=command_id,
        priority=SourceRunPriority.P0,
        created_at=NOW,
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
        local_time="09:00",
        timezone="UTC",
        enabled=True,
        created_at=NOW,
        updated_at=NOW,
    )
    repository.create_or_update_schedule(schedule)
    run = AutomationRunRecord(
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
    assert repository.claim_automation_run(run=run)
    return run


def _manual_analyze_override(
    repository: SQLiteStateRepository, source_id: str, video_id: str
) -> tuple[str, str]:
    override_id = f"override-{video_id}"
    command_id = f"analyze-{video_id}"
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO source_video_filter_decisions "
            "(decision_id, source_id, video_id, stage, outcome, reason, "
            "global_policy_revision_id, source_policy_revision_id, manual_override_id, "
            "prior_decision_id, evaluated_at) "
            "VALUES (?, ?, ?, 'STAGE_1', 'NOT_RELEVANT', 'NO_FOCUS_MATCH', "
            "'source-policy:global:bootstrap', NULL, NULL, NULL, ?)",
            (f"prior-{video_id}", source_id, video_id, "2026-09-08T09:00:00.000000Z"),
        )
        connection.execute(
            "INSERT INTO manual_analyze_overrides "
            "(override_id, source_id, video_id, command_id, prior_decision_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                override_id,
                source_id,
                video_id,
                command_id,
                f"prior-{video_id}",
                "2026-09-08T09:00:00.000000Z",
            ),
        )
    finally:
        connection.close()
    return override_id, command_id


def test_m013_fresh_database_preserves_empty_source_runs_and_weeklies(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    connection = repository._connect()
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 43
        migrations = tuple(
            row["name"]
            for row in connection.execute("SELECT name FROM schema_migrations ORDER BY version")
        )
        tables = {
            str(row["name"])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert connection.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == 0
    finally:
        connection.close()

    assert migrations[-28:] == (
        "015_add_timed_transcript_evidence_bindings.sql",
        "016_add_ambiguous_resource_ledger_outcome.sql",
        "017_add_current_content_summary.sql",
        "018_add_global_output_language.sql",
        "019_add_evidence_excerpt_stance.sql",
        "020_add_no_new_intelligence_result.sql",
        "021_seal_distillation_output_language.sql",
        "022_bind_current_local_summary.sql",
        "023_add_evidence_translation_presentation.sql",
        "024_bind_current_summary_to_content.sql",
        "025_add_explicit_cloud_execution_audit.sql",
        "026_add_openai_cloud_execution_audit.sql",
        "027_add_moonshot_cloud_execution_audit.sql",
        "028_add_cloud_response_failure_ledger.sql",
        "030_add_deep_analysis_durable_evidence.sql",
        "031_add_research_lite.sql",
        "032_add_source_provider_authority.sql",
        "033_add_bilibili_provider.sql",
        "034_add_source_tracking.sql",
        "035_align_no_new_canonical_evidence.sql",
        "036_expand_local_media_snapshot_limit.sql",
        "037_add_waiting_model_cancellation.sql",
        "038_add_retained_subtitle_derivations.sql",
        "039_add_local_text_input_proofs.sql",
        "040_add_tracked_content_retry.sql",
        "041_add_long_distillation_provenance.sql",
        "042_add_zhipu_cloud_execution_audit.sql",
        "043_add_cloud_wait_zero_cancellation.sql",
    )
    assert {"source_runs", "source_run_state_events", "source_run_checkpoint_events"} <= tables
    assert {"weekly_briefs", "brief_items", "brief_item_evidence"} <= tables


def test_v011_upgrade_preserves_existing_automation_and_creates_no_synthetic_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "state.sqlite3"
    with monkeypatch.context() as patch:
        patch.setattr(SQLiteStateRepository, "_load_migrations", lambda _: _v011_migrations())
        old_repository = SQLiteStateRepository(database)
        assert old_repository.initialize(now=NOW).version == 11
        source_id = _source(old_repository)
        occurrence = _scheduled_occurrence(old_repository, source_id)

    repository = SQLiteStateRepository(database)
    assert repository.initialize(now=NOW).version == 43
    assert repository.get_source_subscription(source_id) is not None
    assert repository.list_automation_runs() == (occurrence,)
    assert repository.list_source_runs() == ()


def test_source_run_identity_trigger_priority_and_idempotency_are_source_bound(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    command = _manual_check(source_id)

    first = repository.create_source_run(command)
    second = repository.create_source_run(command)

    assert first == second
    assert first.run_id == build_source_run_id(
        source_id=source_id,
        trigger=SourceRunTrigger.MANUAL_CHECK_NOW,
        trigger_reference="command-1",
    )
    assert first.trigger is SourceRunTrigger.MANUAL_CHECK_NOW
    assert first.priority is SourceRunPriority.P0
    assert first.state is SourceRunState.QUEUED
    assert first.idempotency_key != "command-1"

    other_source = _source(repository, "two")
    other = repository.create_source_run(_manual_check(other_source))
    assert other.run_id != first.run_id
    assert other.source_id == other_source
    assert set(repository.list_source_runs()) == {first, other}


@pytest.mark.parametrize("priority", tuple(SourceRunPriority))
def test_every_finite_priority_round_trips_without_permission_fields(
    tmp_path: Path, priority: SourceRunPriority
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    run = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id=f"priority-{priority.value}",
            priority=priority,
            created_at=NOW,
        )
    )

    assert run.priority is priority
    assert "permission" not in run.__dataclass_fields__


def test_foreign_source_is_rejected_without_creating_or_rebinding_a_run(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    with pytest.raises(IntegrityConflict):
        repository.create_source_run(
            SourceRunWrite.manual_check_now(
                source_id="foreign-source",
                command_id="foreign-command",
                priority=SourceRunPriority.P0,
                created_at=NOW,
            )
        )
    assert repository.list_source_runs() == ()


@pytest.mark.parametrize(
    ("trigger", "priority"),
    [
        ("MANUAL_CHECK_NOW", SourceRunPriority.P0),
        (SourceRunTrigger.MANUAL_CHECK_NOW, "P9"),
    ],
)
def test_arbitrary_trigger_or_priority_is_rejected_before_persistence(
    tmp_path: Path, trigger: object, priority: object
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    with pytest.raises(ValueError, match="finite"):
        repository.create_source_run(
            SourceRunWrite(
                run_id="source-run:invalid",
                source_id=source_id,
                trigger=trigger,
                trigger_reference="command-invalid",
                priority=priority,
                idempotency_key="not-authoritative",
                automation_run_id=None,
                manual_command_id="command-invalid",
                manual_analyze_override_id=None,
                created_at=NOW,
            )
        )


def test_scheduled_and_manual_analyze_relations_are_exact_and_distinct(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    occurrence = _scheduled_occurrence(repository, source_id)
    scheduled = repository.create_source_run(
        SourceRunWrite.scheduled_source_run(
            source_id=source_id,
            automation_run_id=occurrence.run_id,
            priority=SourceRunPriority.P2,
            created_at=NOW,
        )
    )
    video_id = _video(repository, source_id)
    override_id, command_id = _manual_analyze_override(repository, source_id, video_id)
    manual_analyze = repository.create_source_run(
        SourceRunWrite.manual_analyze_video(
            source_id=source_id,
            override_id=override_id,
            command_id=command_id,
            priority=SourceRunPriority.P0,
            created_at=NOW,
        )
    )

    assert scheduled.automation_run_id == occurrence.run_id
    assert scheduled.manual_analyze_override_id is None
    assert manual_analyze.manual_analyze_override_id == override_id
    assert manual_analyze.manual_command_id == command_id
    assert manual_analyze.trigger is SourceRunTrigger.MANUAL_ANALYZE_VIDEO

    foreign_source = _source(repository, "foreign")
    with pytest.raises(IntegrityConflict):
        repository.create_source_run(
            SourceRunWrite.scheduled_source_run(
                source_id=foreign_source,
                automation_run_id=occurrence.run_id,
                priority=SourceRunPriority.P2,
                created_at=NOW,
            )
        )


def test_state_transitions_are_finite_terminal_and_attention_is_not_retry(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    run = repository.create_source_run(_manual_check(_source(repository)))
    running = repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    attention = repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE,
        now=NOW + timedelta(seconds=1),
    )

    assert running.state is SourceRunState.RUNNING
    assert attention.attention_reason is SourceRunAttentionReason.MODEL_UNAVAILABLE
    with pytest.raises(ValueError, match="not allowed"):
        repository.transition_source_run(
            run.run_id, to_state=SourceRunState.RUNNING, now=NOW + timedelta(seconds=2)
        )
    with pytest.raises(ValueError, match="attention"):
        repository.transition_source_run(
            run.run_id,
            to_state=SourceRunState.AMBIGUOUS,
            attention_reason=SourceRunAttentionReason.MODEL_UNAVAILABLE,
            now=NOW + timedelta(seconds=3),
        )


def test_needs_attention_is_finite_and_has_no_freeform_secret_detail(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_source_run(_manual_check(_source(repository)))
    repository.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=NOW)
    attention = repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.BUDGET_BLOCKED,
        now=NOW + timedelta(seconds=1),
    )

    connection = repository._connect()
    try:
        columns = {
            str(row["name"])
            for row in connection.execute('PRAGMA table_info("source_runs")')
        }
    finally:
        connection.close()
    assert attention.attention_reason is SourceRunAttentionReason.BUDGET_BLOCKED
    assert "attention_detail" not in columns
    assert "error_message" not in columns


def test_completion_and_checkpoint_blocks_fail_closed_without_safe_progress(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    run = repository.create_source_run(_manual_check(_source(repository)))
    repository.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=NOW)

    with pytest.raises(IntegrityConflict, match="state violates"):
        repository.transition_source_run(
            run.run_id, to_state=SourceRunState.COMPLETED, now=NOW + timedelta(seconds=1)
        )
    queued = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=run.source_id,
            command_id="queued-block",
            priority=SourceRunPriority.P0,
            created_at=NOW,
        )
    )
    with pytest.raises(ValueError, match="cannot block"):
        repository.block_source_run_checkpoint(
            queued.run_id, SourceRunCheckpoint.DISCOVERY, now=NOW
        )


def test_finalized_source_run_can_complete_and_remains_terminal(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run = repository.create_source_run(_manual_check(_source(repository)))
    active = repository.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    for offset, checkpoint in enumerate(SOURCE_RUN_CHECKPOINT_ORDER):
        repository.complete_source_run_checkpoint(
            active.run_id, checkpoint, now=NOW + timedelta(seconds=offset)
        )
    completed = repository.transition_source_run(
        active.run_id, to_state=SourceRunState.COMPLETED, now=NOW + timedelta(seconds=9)
    )

    assert completed.state is SourceRunState.COMPLETED
    assert repository.source_run_checkpoint_progress(active.run_id).next_checkpoint is None
    with pytest.raises(ValueError, match="not allowed"):
        repository.transition_source_run(
            active.run_id, to_state=SourceRunState.RUNNING, now=NOW + timedelta(seconds=10)
        )


def test_checkpoint_progress_and_priority_are_durable_across_reopen(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    repository = SQLiteStateRepository(database)
    assert repository.initialize(now=NOW).version == 43
    source_id = _source(repository)
    low = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id="low",
            priority=SourceRunPriority.P3,
            created_at=NOW,
        )
    )
    high = repository.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id="high",
            priority=SourceRunPriority.P0,
            created_at=NOW + timedelta(seconds=1),
        )
    )
    high = repository.transition_source_run(
        high.run_id, to_state=SourceRunState.RUNNING, now=NOW
    )
    repository.complete_source_run_checkpoint(
        high.run_id, SourceRunCheckpoint.DISCOVERY, now=NOW
    )
    repository.complete_source_run_checkpoint(
        high.run_id, SourceRunCheckpoint.SELECTION, now=NOW + timedelta(seconds=1)
    )
    high = repository.transition_source_run(
        high.run_id, to_state=SourceRunState.PARTIAL, now=NOW + timedelta(seconds=2)
    )

    reopened = SQLiteStateRepository(database)
    assert reopened.get_source_run(high.run_id) is not None
    progress = reopened.source_run_checkpoint_progress(high.run_id)
    assert progress.completed == (SourceRunCheckpoint.DISCOVERY, SourceRunCheckpoint.SELECTION)
    assert progress.next_checkpoint is SourceRunCheckpoint.FILTERING
    assert reopened.list_resumable_source_runs() == (high, low)

    connection = reopened._connect()
    try:
        with pytest.raises(Exception, match="checkpoint history is immutable"):
            connection.execute(
                "UPDATE source_run_checkpoint_events SET event_status = 'BLOCKED' "
                "WHERE run_id = ?",
                (high.run_id,),
            )
    finally:
        connection.close()
    assert reopened.source_run_checkpoint_progress(high.run_id) == progress


def test_multiple_child_outcomes_persist_without_collapsing_the_source_run(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    first_video = _video(repository, source_id, "first")
    second_video = _video(repository, source_id, "second")
    run = repository.create_source_run(_manual_check(source_id))
    repository.record_source_run_child(
        run.run_id,
        video_id=first_video,
        state=SourceRunChildState.PENDING,
        distillation_execution_id=None,
        now=NOW,
    )
    repository.record_source_run_child(
        run.run_id,
        video_id=second_video,
        state=SourceRunChildState.PENDING,
        distillation_execution_id=None,
        now=NOW,
    )
    repository.transition_source_run_child(
        run.run_id,
        video_id=first_video,
        to_state=SourceRunChildState.SKIPPED,
        now=NOW + timedelta(seconds=1),
    )
    repository.transition_source_run_child(
        run.run_id,
        video_id=second_video,
        to_state=SourceRunChildState.DEFERRED,
        now=NOW + timedelta(seconds=1),
    )

    children = repository.list_source_run_children(run.run_id)
    assert tuple(child.state for child in children) == (
        SourceRunChildState.SKIPPED,
        SourceRunChildState.DEFERRED,
    )
    assert repository.get_source_run(run.run_id).state is SourceRunState.QUEUED


def test_child_execution_cannot_fabricate_provider_success_or_weaken_ambiguous(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    source_id = _source(repository)
    video_id = _video(repository, source_id)
    run = repository.create_source_run(_manual_check(source_id))
    repository.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=NOW)
    for checkpoint in (
        SourceRunCheckpoint.DISCOVERY,
        SourceRunCheckpoint.SELECTION,
        SourceRunCheckpoint.FILTERING,
        SourceRunCheckpoint.SOURCE_PREPARATION,
    ):
        repository.complete_source_run_checkpoint(run.run_id, checkpoint, now=NOW)
    execution_id = "execution-ambiguous"
    repository.begin_distillation_execution(
        DistillationExecutionWrite(
            execution_id=execution_id,
            source_id=source_id,
            video_id=video_id,
            reason="source run fixture",
            use_case="V1_PERSONALIZED_DISTILLATION",
            selected_provider="offline",
            selected_model="fixture-v1",
        ),
        now=NOW,
    )
    repository.record_source_run_child(
        run.run_id,
        video_id=video_id,
        state=SourceRunChildState.PENDING,
        distillation_execution_id=execution_id,
        now=NOW,
    )
    with pytest.raises(IntegrityConflict, match="checkpoint"):
        repository.complete_source_run_checkpoint(
            run.run_id, SourceRunCheckpoint.DISTILLATION, now=NOW
        )

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE distillation_execution_checkpoints SET status = 'AMBIGUOUS', "
            "budget_state = 'UNKNOWN', updated_at = ? WHERE execution_id = ?",
            ("2026-09-08T09:00:00.000000Z", execution_id),
        )
        with pytest.raises(Exception, match="terminal distillation checkpoint"):
            connection.execute(
                "UPDATE distillation_execution_checkpoints SET status = 'PENDING' "
                "WHERE execution_id = ?",
                (execution_id,),
            )
    finally:
        connection.close()

    child = repository.transition_source_run_child(
        run.run_id,
        video_id=video_id,
        to_state=SourceRunChildState.AMBIGUOUS,
        now=NOW + timedelta(seconds=1),
    )
    assert child.state is SourceRunChildState.AMBIGUOUS
    ambiguous = repository.transition_source_run(
        run.run_id,
        to_state=SourceRunState.AMBIGUOUS,
        attention_reason=SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME,
        now=NOW + timedelta(seconds=2),
    )
    assert ambiguous.state is SourceRunState.AMBIGUOUS
    with pytest.raises(ValueError, match="not allowed"):
        repository.transition_source_run(
            run.run_id, to_state=SourceRunState.RUNNING, now=NOW + timedelta(seconds=3)
        )
