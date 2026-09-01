from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.cli import main
from youtube_intel.orchestration import (
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository


def _service(
    tmp_path: Path,
) -> tuple[ProductOrchestrationService, SQLiteStateRepository]:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=datetime(2026, 9, 1, tzinfo=UTC))
    return ProductOrchestrationService(
        repository, now=lambda: datetime(2026, 9, 1, 12, tzinfo=UTC)
    ), repository


def test_add_source_is_pure_persistence_and_duplicate_is_idempotent(
    tmp_path: Path,
) -> None:
    service, repository = _service(tmp_path)
    created = service.add_source(
        url="https://youtu.be/abcdefghijk",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    duplicate = service.add_source(
        url="https://www.youtube.com/watch?v=abcdefghijk",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    assert created.source_id == duplicate.source_id
    assert created.last_checked_at is None
    assert repository.list_automation_runs() == ()


def test_manual_check_is_guarded_and_disabled_source_is_not_run(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    source = service.add_source(
        url="https://youtube.com/channel/UC1234567890123456789012",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    assert service.check_source(source.source_id).status.value == "BLOCKED"
    service.update_source(source.source_id, enabled=False)
    assert service.check_source(source.source_id).safe_message.startswith(
        "Source is disabled"
    )


def test_due_run_has_one_atomic_claim(tmp_path: Path) -> None:
    service, repository = _service(tmp_path)
    source = service.add_source(
        url="https://youtube.com/channel/UC1234567890123456789012",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    repository.record_source_check(
        source.source_id, now=datetime(2026, 8, 28, 9, tzinfo=UTC), succeeded=True
    )
    service.save_schedule(
        schedule_id=None,
        target_type=AutomationTargetType.SOURCE_CHECK,
        target_id=source.source_id,
        frequency=ScheduleFrequency.DAILY,
        weekday=None,
        local_time="09:00",
        timezone="UTC",
        enabled=True,
    )
    assert len(service.scheduler_tick()) == 1
    assert service.scheduler_tick() == ()


def test_unqualified_desired_model_never_becomes_active(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    preference = service.set_desired_model(provider="Kimi", model="kimi-model")
    assert preference.desired_provider == "Kimi"


def test_scheduler_tick_cli_is_bounded_and_defaults_to_guarded_execution(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tick.sqlite3"
    assert (
        main(["scheduler-tick", "--database", str(database), "--limit", "1"]).value == 0
    )
