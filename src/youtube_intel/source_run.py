"""Finite, durable Source Run persistence contracts for TASK-024 to consume.

This module deliberately contains no scheduler, provider, filtering, or
distillation behavior.  A Source Run is the top-level execution identity; a
TASK-022 distillation checkpoint remains the separate authority for any
irreversible per-video provider dispatch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SourceRunTrigger(str, Enum):
    MANUAL_CHECK_NOW = "MANUAL_CHECK_NOW"
    SCHEDULED_SOURCE_RUN = "SCHEDULED_SOURCE_RUN"
    MANUAL_ANALYZE_VIDEO = "MANUAL_ANALYZE_VIDEO"


class SourceRunPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class SourceRunState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    PARTIAL = "PARTIAL"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"
    CANCELLED = "CANCELLED"


class SourceRunCheckpoint(str, Enum):
    DISCOVERY = "DISCOVERY"
    SELECTION = "SELECTION"
    FILTERING = "FILTERING"
    SOURCE_PREPARATION = "SOURCE_PREPARATION"
    DISTILLATION = "DISTILLATION"
    INTELLIGENCE_ADMISSION = "INTELLIGENCE_ADMISSION"
    TOPIC_UPDATE = "TOPIC_UPDATE"
    FINALIZATION = "FINALIZATION"


class SourceRunCheckpointEventStatus(str, Enum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class SourceRunAttentionReason(str, Enum):
    AMBIGUOUS_EXTERNAL_OUTCOME = "AMBIGUOUS_EXTERNAL_OUTCOME"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    BUDGET_BLOCKED = "BUDGET_BLOCKED"
    USER_DECISION_REQUIRED = "USER_DECISION_REQUIRED"
    EXECUTION_CONDITION_UNRESOLVED = "EXECUTION_CONDITION_UNRESOLVED"


class SourceRunChildState(str, Enum):
    PENDING = "PENDING"
    WAITING = "WAITING"
    DEFERRED = "DEFERRED"
    SKIPPED = "SKIPPED"
    COMPLETED = "COMPLETED"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"


SOURCE_RUN_CHECKPOINT_ORDER: tuple[SourceRunCheckpoint, ...] = (
    SourceRunCheckpoint.DISCOVERY,
    SourceRunCheckpoint.SELECTION,
    SourceRunCheckpoint.FILTERING,
    SourceRunCheckpoint.SOURCE_PREPARATION,
    SourceRunCheckpoint.DISTILLATION,
    SourceRunCheckpoint.INTELLIGENCE_ADMISSION,
    SourceRunCheckpoint.TOPIC_UPDATE,
    SourceRunCheckpoint.FINALIZATION,
)


_SOURCE_RUN_STATE_TRANSITIONS: dict[SourceRunState, frozenset[SourceRunState]] = {
    SourceRunState.QUEUED: frozenset(
        {
            SourceRunState.RUNNING,
            SourceRunState.WAITING,
            SourceRunState.PARTIAL,
            SourceRunState.NEEDS_ATTENTION,
            SourceRunState.FAILED,
            SourceRunState.CANCELLED,
        }
    ),
    SourceRunState.RUNNING: frozenset(
        {
            SourceRunState.WAITING,
            SourceRunState.PARTIAL,
            SourceRunState.NEEDS_ATTENTION,
            SourceRunState.COMPLETED,
            SourceRunState.FAILED,
            SourceRunState.AMBIGUOUS,
            SourceRunState.CANCELLED,
        }
    ),
    SourceRunState.WAITING: frozenset(
        {
            SourceRunState.QUEUED,
            SourceRunState.NEEDS_ATTENTION,
            SourceRunState.FAILED,
            SourceRunState.CANCELLED,
        }
    ),
    SourceRunState.PARTIAL: frozenset(
        {
            SourceRunState.QUEUED,
            SourceRunState.RUNNING,
            SourceRunState.WAITING,
            SourceRunState.NEEDS_ATTENTION,
            SourceRunState.COMPLETED,
            SourceRunState.FAILED,
            SourceRunState.CANCELLED,
        }
    ),
    SourceRunState.NEEDS_ATTENTION: frozenset(),
    SourceRunState.COMPLETED: frozenset(),
    SourceRunState.FAILED: frozenset(),
    SourceRunState.AMBIGUOUS: frozenset(),
    SourceRunState.CANCELLED: frozenset(),
}


_SOURCE_RUN_CHILD_TRANSITIONS: dict[
    SourceRunChildState, frozenset[SourceRunChildState]
] = {
    SourceRunChildState.PENDING: frozenset(
        {
            SourceRunChildState.WAITING,
            SourceRunChildState.DEFERRED,
            SourceRunChildState.SKIPPED,
            SourceRunChildState.COMPLETED,
            SourceRunChildState.NEEDS_ATTENTION,
            SourceRunChildState.AMBIGUOUS,
            SourceRunChildState.FAILED,
        }
    ),
    SourceRunChildState.WAITING: frozenset(
        {
            SourceRunChildState.PENDING,
            SourceRunChildState.DEFERRED,
            SourceRunChildState.NEEDS_ATTENTION,
            SourceRunChildState.FAILED,
        }
    ),
    SourceRunChildState.DEFERRED: frozenset({SourceRunChildState.PENDING}),
    SourceRunChildState.SKIPPED: frozenset(),
    SourceRunChildState.COMPLETED: frozenset(),
    SourceRunChildState.NEEDS_ATTENTION: frozenset(),
    SourceRunChildState.AMBIGUOUS: frozenset(),
    SourceRunChildState.FAILED: frozenset(),
}


def _require_identity(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 512:
        raise ValueError(f"{field} is invalid")
    return value


def _require_trigger(trigger: SourceRunTrigger) -> SourceRunTrigger:
    if not isinstance(trigger, SourceRunTrigger):
        raise ValueError("Source Run trigger must be finite")
    return trigger


def build_source_run_id(
    *, source_id: str, trigger: SourceRunTrigger, trigger_reference: str
) -> str:
    """Build a source-bound opaque identity without mutable labels or time."""

    digest = hashlib.sha256(
        "\x1f".join(
            (
                "source-run-v1",
                _require_identity(source_id, field="source id"),
                _require_trigger(trigger).value,
                _require_identity(trigger_reference, field="trigger reference"),
            )
        ).encode("utf-8")
    ).hexdigest()
    return f"source-run:{digest}"


def build_source_run_idempotency_key(
    *, source_id: str, trigger: SourceRunTrigger, trigger_reference: str
) -> str:
    """Build the bounded, source-scoped logical duplicate identity."""

    digest = hashlib.sha256(
        "\x1f".join(
            (
                "source-run-idempotency-v1",
                _require_identity(source_id, field="source id"),
                _require_trigger(trigger).value,
                _require_identity(trigger_reference, field="trigger reference"),
            )
        ).encode("utf-8")
    ).hexdigest()
    return f"source-run-key:{digest}"


@dataclass(frozen=True, slots=True)
class SourceRunWrite:
    run_id: str
    source_id: str
    trigger: SourceRunTrigger
    trigger_reference: str
    priority: SourceRunPriority
    idempotency_key: str
    automation_run_id: str | None
    manual_command_id: str | None
    manual_analyze_override_id: str | None
    created_at: datetime

    @classmethod
    def manual_check_now(
        cls,
        *,
        source_id: str,
        command_id: str,
        priority: SourceRunPriority,
        created_at: datetime,
    ) -> SourceRunWrite:
        return cls._create(
            source_id=source_id,
            trigger=SourceRunTrigger.MANUAL_CHECK_NOW,
            trigger_reference=command_id,
            priority=priority,
            automation_run_id=None,
            manual_command_id=command_id,
            manual_analyze_override_id=None,
            created_at=created_at,
        )

    @classmethod
    def scheduled_source_run(
        cls,
        *,
        source_id: str,
        automation_run_id: str,
        priority: SourceRunPriority,
        created_at: datetime,
    ) -> SourceRunWrite:
        return cls._create(
            source_id=source_id,
            trigger=SourceRunTrigger.SCHEDULED_SOURCE_RUN,
            trigger_reference=automation_run_id,
            priority=priority,
            automation_run_id=automation_run_id,
            manual_command_id=None,
            manual_analyze_override_id=None,
            created_at=created_at,
        )

    @classmethod
    def manual_analyze_video(
        cls,
        *,
        source_id: str,
        override_id: str,
        command_id: str,
        priority: SourceRunPriority,
        created_at: datetime,
    ) -> SourceRunWrite:
        return cls._create(
            source_id=source_id,
            trigger=SourceRunTrigger.MANUAL_ANALYZE_VIDEO,
            trigger_reference=override_id,
            priority=priority,
            automation_run_id=None,
            manual_command_id=command_id,
            manual_analyze_override_id=override_id,
            created_at=created_at,
        )

    @classmethod
    def _create(
        cls,
        *,
        source_id: str,
        trigger: SourceRunTrigger,
        trigger_reference: str,
        priority: SourceRunPriority,
        automation_run_id: str | None,
        manual_command_id: str | None,
        manual_analyze_override_id: str | None,
        created_at: datetime,
    ) -> SourceRunWrite:
        return cls(
            run_id=build_source_run_id(
                source_id=source_id,
                trigger=trigger,
                trigger_reference=trigger_reference,
            ),
            source_id=source_id,
            trigger=trigger,
            trigger_reference=trigger_reference,
            priority=priority,
            idempotency_key=build_source_run_idempotency_key(
                source_id=source_id,
                trigger=trigger,
                trigger_reference=trigger_reference,
            ),
            automation_run_id=automation_run_id,
            manual_command_id=manual_command_id,
            manual_analyze_override_id=manual_analyze_override_id,
            created_at=created_at,
        )


@dataclass(frozen=True, slots=True)
class SourceRunRecord:
    run_id: str
    source_id: str
    trigger: SourceRunTrigger
    trigger_reference: str
    priority: SourceRunPriority
    idempotency_key: str
    state: SourceRunState
    attention_reason: SourceRunAttentionReason | None
    automation_run_id: str | None
    manual_command_id: str | None
    manual_analyze_override_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SourceRunCheckpointProgress:
    run_id: str
    completed: tuple[SourceRunCheckpoint, ...]
    next_checkpoint: SourceRunCheckpoint | None
    blocked_checkpoint: SourceRunCheckpoint | None


@dataclass(frozen=True, slots=True)
class SourceRunChildRecord:
    run_id: str
    video_id: str
    state: SourceRunChildState
    distillation_execution_id: str | None
    created_at: datetime
    updated_at: datetime


def source_run_transition_allowed(
    current: SourceRunState, target: SourceRunState
) -> bool:
    if not isinstance(current, SourceRunState) or not isinstance(target, SourceRunState):
        return False
    return target in _SOURCE_RUN_STATE_TRANSITIONS[current]


def source_run_child_transition_allowed(
    current: SourceRunChildState, target: SourceRunChildState
) -> bool:
    if not isinstance(current, SourceRunChildState) or not isinstance(target, SourceRunChildState):
        return False
    return target in _SOURCE_RUN_CHILD_TRANSITIONS[current]
