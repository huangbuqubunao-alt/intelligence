"""Application-service boundary for source configuration and scheduled checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Protocol
from uuid import uuid4

from youtube_intel.orchestration import (
    AutomationRunStatus,
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    due_scheduled_for,
    normalize_source_url,
    validate_policy,
    validate_schedule,
)
from youtube_intel.source_run import SourceRunPriority, SourceRunRecord
from youtube_intel.state import (
    AutomationRunRecord,
    AutomationScheduleRecord,
    GlobalModelPreferenceRecord,
    IntegrityConflict,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
)


class SourceCheckExecutor(Protocol):
    """A runtime adapter; it may call existing RuntimeOperations, never provider SDKs."""

    def check_source(self, source: SourceSubscriptionRecord) -> str: ...


class SourceRunSubmitter(Protocol):
    """TASK-024 trigger seam; it admits durable work but does not execute it."""

    def enqueue_manual_check_now(
        self,
        *,
        source_id: str,
        command_id: str,
        priority: SourceRunPriority = SourceRunPriority.P0,
    ) -> SourceRunRecord: ...

    def enqueue_scheduled_source_run(
        self,
        *,
        source_id: str,
        automation_run_id: str,
        priority: SourceRunPriority = SourceRunPriority.P2,
    ) -> SourceRunRecord: ...


@dataclass(frozen=True, slots=True)
class SourceCheckResult:
    status: AutomationRunStatus
    safe_message: str


class ProductOrchestrationService:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        now: Callable[[], datetime] | None = None,
        execution_enabled: bool = False,
        source_check_executor: SourceCheckExecutor | None = None,
        source_run_submitter: SourceRunSubmitter | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))
        self._execution_enabled = execution_enabled
        self._source_check_executor = source_check_executor
        self._source_run_submitter = source_run_submitter

    def add_source(
        self, *, url: str, processing_policy: ProcessingPolicy
    ) -> SourceSubscriptionRecord:
        normalized = normalize_source_url(url)
        # FULL is an explicit desired preference only at the product layer; its
        # execution remains unavailable while no eligible provider exists.
        if processing_policy is ProcessingPolicy.FULL_INTELLIGENCE:
            validate_policy(processing_policy, deep_analysis_eligible=False)
        now = self._now()
        source = SourceSubscriptionRecord(
            source_id=str(uuid4()),
            source_type=normalized.source_type,
            canonical_url=normalized.canonical_url,
            channel_id=normalized.channel_id,
            video_id=normalized.video_id,
            display_name=None,
            enabled=True,
            processing_policy=processing_policy,
            last_checked_at=None,
            last_success_at=None,
            last_error_code=None,
            last_error_message=None,
            created_at=now,
            updated_at=now,
        )
        try:
            return self._repository.create_source_subscription(source)
        except IntegrityConflict as error:
            existing = self._repository.get_source_by_canonical_url(
                normalized.canonical_url
            )
            if existing is not None:
                return existing
            raise error

    def update_source(
        self,
        source_id: str,
        *,
        enabled: bool | None = None,
        processing_policy: ProcessingPolicy | None = None,
    ) -> SourceSubscriptionRecord | None:
        if processing_policy is ProcessingPolicy.FULL_INTELLIGENCE:
            validate_policy(processing_policy, deep_analysis_eligible=False)
        return self._repository.update_source_subscription(
            source_id,
            enabled=enabled,
            processing_policy=processing_policy,
            now=self._now(),
        )

    def save_schedule(
        self,
        *,
        schedule_id: str | None,
        target_type: AutomationTargetType,
        target_id: str | None,
        frequency: ScheduleFrequency,
        weekday: int | None,
        local_time: str | None,
        timezone: str,
        enabled: bool,
    ) -> AutomationScheduleRecord:
        if target_type is AutomationTargetType.SOURCE_CHECK:
            if (
                target_id is None
                or self._repository.get_source_subscription(target_id) is None
            ):
                raise ValueError("source schedule target does not exist")
        validate_schedule(
            target_type=target_type,
            frequency=frequency,
            weekday=weekday,
            local_time=local_time,
            timezone=timezone,
        )
        now = self._now()
        return self._repository.create_or_update_schedule(
            AutomationScheduleRecord(
                schedule_id=schedule_id or str(uuid4()),
                target_type=target_type,
                target_id=target_id,
                frequency=frequency,
                weekday=weekday,
                local_time=local_time,
                timezone=timezone,
                enabled=enabled,
                created_at=now,
                updated_at=now,
            )
        )

    def set_desired_model(
        self, *, provider: str | None, model: str | None
    ) -> GlobalModelPreferenceRecord:
        if provider is None and model is not None:
            raise ValueError("a model requires a provider")
        if provider is not None and provider not in {"OpenAI", "Kimi", "Local"}:
            raise ValueError("unknown provider preference")
        return self._repository.save_global_model_preference(
            desired_provider=provider, desired_model=model, now=self._now()
        )

    def check_source(
        self, source_id: str, *, command_id: str | None = None
    ) -> SourceCheckResult:
        source = self._repository.get_source_subscription(source_id)
        if source is None:
            raise ValueError("source does not exist")
        if not source.enabled:
            return SourceCheckResult(
                AutomationRunStatus.BLOCKED, "Source is disabled; no check was started."
            )
        if self._source_run_submitter is not None:
            if not isinstance(command_id, str) or not command_id.strip():
                raise ValueError("Check Now requires a durable command identity")
            self._source_run_submitter.enqueue_manual_check_now(
                source_id=source.source_id,
                command_id=command_id,
                priority=SourceRunPriority.P0,
            )
            return SourceCheckResult(
                AutomationRunStatus.SUCCEEDED,
                "Full Source Run was durably queued.",
            )
        if not self._execution_enabled or self._source_check_executor is None:
            self._repository.record_source_check(
                source_id,
                now=self._now(),
                succeeded=False,
                error_code="EXECUTION_GUARD_BLOCKED",
                error_message="Source checking requires explicit runtime side-effect authorization.",
            )
            return SourceCheckResult(
                AutomationRunStatus.BLOCKED,
                "Check now is blocked by the runtime side-effect guard.",
            )
        try:
            summary = self._source_check_executor.check_source(source)
        except Exception:
            self._repository.record_source_check(
                source_id,
                now=self._now(),
                succeeded=False,
                error_code="SOURCE_CHECK_FAILED",
                error_message="Source check failed safely.",
            )
            return SourceCheckResult(
                AutomationRunStatus.FAILED_FINAL, "Source check failed safely."
            )
        self._repository.record_source_check(source_id, now=self._now(), succeeded=True)
        return SourceCheckResult(AutomationRunStatus.SUCCEEDED, summary[:500])

    def scheduler_tick(self, *, limit: int = 20) -> tuple[AutomationRunRecord, ...]:
        """Claim at most one missed occurrence per schedule and never loops/retries."""
        if limit <= 0 or limit > 100:
            raise ValueError("scheduler tick limit is invalid")
        now = self._now()
        claimed: list[AutomationRunRecord] = []
        for schedule in self._repository.list_automation_schedules():
            if (
                len(claimed) >= limit
                or not schedule.enabled
                or schedule.frequency is ScheduleFrequency.MANUAL
            ):
                continue
            if schedule.target_type is AutomationTargetType.SOURCE_CHECK:
                assert schedule.target_id is not None
                source = self._repository.get_source_subscription(schedule.target_id)
                if source is None or not source.enabled:
                    continue
                last = source.last_checked_at
            else:
                last = None
            if last is None:
                # A new schedule's first planned run is its first future period;
                # it does not backfill unknown history.
                continue
            scheduled_for = due_scheduled_for(
                frequency=schedule.frequency,
                weekday=schedule.weekday,
                local_time=schedule.local_time,
                timezone=schedule.timezone,
                now=now,
                last_scheduled_for=last,
            )
            if scheduled_for is None:
                continue
            run = AutomationRunRecord(
                str(uuid4()),
                schedule.schedule_id,
                schedule.target_type,
                schedule.target_id,
                scheduled_for,
                now,
                None,
                None,
                AutomationRunStatus.CLAIMED,
                None,
                None,
                None,
            )
            if not self._repository.claim_automation_run(run=run):
                continue
            if schedule.target_type is AutomationTargetType.SOURCE_CHECK:
                assert schedule.target_id is not None
                if self._source_run_submitter is not None:
                    self._source_run_submitter.enqueue_scheduled_source_run(
                        source_id=schedule.target_id,
                        automation_run_id=run.run_id,
                        priority=SourceRunPriority.P2,
                    )
                    result = SourceCheckResult(
                        AutomationRunStatus.SUCCEEDED,
                        "Scheduled Source Run was durably queued.",
                    )
                else:
                    result = self.check_source(schedule.target_id)
                self._repository.finish_automation_run(
                    run.run_id,
                    status=result.status,
                    now=self._now(),
                    error_code=None
                    if result.status is AutomationRunStatus.SUCCEEDED
                    else "EXECUTION_GUARD_BLOCKED",
                    result_summary=result.safe_message,
                )
            else:
                self._repository.finish_automation_run(
                    run.run_id,
                    status=AutomationRunStatus.BLOCKED,
                    now=self._now(),
                    error_code="EXECUTION_GUARD_BLOCKED",
                    result_summary="Weekly generation requires explicit runtime side-effect authorization.",
                )
            claimed.append(run)
        return tuple(claimed)
