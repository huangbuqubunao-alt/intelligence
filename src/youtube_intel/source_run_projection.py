"""Truthful RC4 Source Run orientation derived from existing durable records."""

from __future__ import annotations

from datetime import UTC
from typing import cast

from youtube_intel.readiness import ProductionReadinessAuthority
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunCheckpoint,
    SourceRunRecord,
    SourceRunState,
)
from youtube_intel.state import SQLiteStateRepository

_CHECKPOINT_PRESENTATION: dict[SourceRunCheckpoint, tuple[str, str]] = {
    SourceRunCheckpoint.DISCOVERY: ("CHECKING_SOURCE", "Checking Source"),
    SourceRunCheckpoint.SELECTION: ("CHOOSING_RELEVANT", "Choosing relevant videos"),
    SourceRunCheckpoint.FILTERING: ("CHOOSING_RELEVANT", "Choosing relevant videos"),
    SourceRunCheckpoint.SOURCE_PREPARATION: (
        "PREPARING_SOURCE",
        "Preparing source material",
    ),
    SourceRunCheckpoint.DISTILLATION: (
        "CREATING_INTELLIGENCE",
        "Creating Intelligence",
    ),
    SourceRunCheckpoint.INTELLIGENCE_ADMISSION: (
        "VERIFYING_INTELLIGENCE",
        "Verifying Intelligence",
    ),
    SourceRunCheckpoint.TOPIC_UPDATE: ("UPDATING_TOPICS", "Updating Topics"),
    SourceRunCheckpoint.FINALIZATION: ("FINISHING", "Finishing"),
}


def _progress(
    repository: SQLiteStateRepository, run: SourceRunRecord
) -> dict[str, object]:
    fixed: dict[SourceRunState, tuple[str, str]] = {
        SourceRunState.QUEUED: ("WAITING_TO_START", "Waiting to start"),
        SourceRunState.WAITING: ("WAITING", "Waiting for a prerequisite"),
        SourceRunState.PARTIAL: ("PARTIAL", "Some work completed"),
        SourceRunState.NEEDS_ATTENTION: ("NEEDS_ATTENTION", "Needs attention"),
        SourceRunState.COMPLETED: ("COMPLETED", "Completed"),
        SourceRunState.FAILED: ("FAILED", "Could not complete"),
        SourceRunState.AMBIGUOUS: (
            "EXTERNAL_RESULT_UNCONFIRMED",
            "External result unconfirmed",
        ),
        SourceRunState.CANCELLED: ("CANCELLED", "Cancelled"),
    }
    if run.state is SourceRunState.RUNNING:
        checkpoint = repository.source_run_checkpoint_progress(run.run_id)
        current = checkpoint.blocked_checkpoint or checkpoint.next_checkpoint
        code, label = (
            ("PROCESSING", "Processing")
            if current is None
            else _CHECKPOINT_PRESENTATION[current]
        )
        return {
            "code": code,
            "label": label,
            "completed_checkpoints": [item.value for item in checkpoint.completed],
            "current_checkpoint": None if current is None else current.value,
        }
    code, label = fixed[run.state]
    return {"code": code, "label": label}


def _admitted_intelligence_count(
    repository: SQLiteStateRepository, run_id: str
) -> int:
    count = 0
    for child in repository.list_source_run_children(run_id):
        if child.distillation_execution_id is None:
            continue
        execution = repository.get_distillation_execution(
            child.distillation_execution_id
        )
        if (
            execution is None
            or execution.status != "SUCCEEDED"
            or execution.intelligence_id is None
        ):
            continue
        count += 1
    return count


def _result(
    repository: SQLiteStateRepository,
    run: SourceRunRecord,
) -> dict[str, object]:
    if run.state is SourceRunState.COMPLETED:
        count = _admitted_intelligence_count(repository, run.run_id)
        if count:
            return {
                "kind": "COMPLETED_WITH_INTELLIGENCE",
                "label": "Completed with Intelligence",
                "intelligence_count": count,
            }
        return {
            "kind": "COMPLETED_NO_IMPORTANT_RESULT",
            "label": "Completed — no important new result",
            "intelligence_count": 0,
        }
    if (
        run.state is SourceRunState.AMBIGUOUS
        or run.attention_reason is SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
    ):
        return {
            "kind": "EXTERNAL_RESULT_UNCONFIRMED",
            "label": "External result could not be confirmed",
            "intelligence_count": 0,
        }
    if run.state in {SourceRunState.QUEUED, SourceRunState.RUNNING}:
        kind = "ACCEPTED" if run.state is SourceRunState.QUEUED else "IN_PROGRESS"
        return {"kind": kind, "label": _progress(repository, run)["label"]}
    return {
        "kind": run.state.value,
        "label": _progress(repository, run)["label"],
        "intelligence_count": 0,
    }


def _recovery(
    run: SourceRunRecord,
    readiness: ProductionReadinessAuthority,
) -> dict[str, object] | None:
    reason = run.attention_reason
    if reason is None and run.state not in {
        SourceRunState.FAILED,
        SourceRunState.AMBIGUOUS,
    }:
        return None
    if (
        reason is SourceRunAttentionReason.AMBIGUOUS_EXTERNAL_OUTCOME
        or run.state is SourceRunState.AMBIGUOUS
    ):
        return {
            "kind": "AMBIGUOUS",
            "what_happened": "The external result could not be confirmed.",
            "why_it_matters": "Repeating the protected execution could duplicate an external action.",
            "safe_action": {
                "kind": "VIEW_RUN_DETAILS",
                "label": "View run details",
                "target": run.run_id,
            },
            "will_not": "The system will not retry, resume, continue, or repeat this execution automatically.",
        }
    if reason is SourceRunAttentionReason.BUDGET_BLOCKED:
        return {
            "kind": "BUDGET",
            "what_happened": "The current usage limit blocked this run.",
            "why_it_matters": "No provider call was authorized for the blocked work.",
            "safe_action": {
                "kind": "VIEW_USAGE",
                "label": "View usage and limit",
                "target": "resource-usage",
            },
            "will_not": "The system will not increase the limit or authorize spending automatically.",
        }
    if reason is SourceRunAttentionReason.MODEL_UNAVAILABLE:
        projection = readiness.project(source_id=run.source_id)
        credential = cast(dict[str, object], projection["credential"])
        processing = cast(dict[str, object], projection["video_distillation"])
        if credential.get("code") == "SETUP_REQUIRED":
            return {
                "kind": "CREDENTIAL",
                "what_happened": "The NVIDIA credential was unavailable to the local service.",
                "why_it_matters": "Video Distillation cannot call the approved provider without it.",
                "safe_action": {
                    "kind": "VIEW_CREDENTIAL_SETUP",
                    "label": "View credential setup",
                    "target": "run-readiness",
                },
                "will_not": "The product will not ask for, store, echo, or test the key by generating content.",
            }
        return {
            "kind": "PROVIDER",
            "what_happened": cast(str, processing["message"]),
            "why_it_matters": "Normal Video Distillation cannot execute on the configured production route.",
            "safe_action": {
                "kind": "CHECK_READINESS",
                "label": "Check readiness again",
                "target": "run-readiness",
            },
            "will_not": "The system will not switch provider or model and will not retry this run.",
        }
    if reason is SourceRunAttentionReason.USER_DECISION_REQUIRED:
        return {
            "kind": "DECISION_REQUIRED",
            "what_happened": "This run requires an explicit user decision.",
            "why_it_matters": "The system cannot safely choose on your behalf.",
            "safe_action": {
                "kind": "REVIEW_SOURCE_DECISION",
                "label": "Review Source",
                "target": run.source_id,
            },
            "will_not": "The system will not continue until an authorized decision is recorded.",
        }
    return {
        "kind": "EXECUTION_CONDITION",
        "what_happened": "The run could not confirm a safe execution condition.",
        "why_it_matters": "Continuing without that condition could violate execution safeguards.",
        "safe_action": {
            "kind": "VIEW_RUN_DETAILS",
            "label": "View run details",
            "target": run.run_id,
        },
        "will_not": "The system will not redispatch protected work automatically.",
    }


def project_source_run(
    repository: SQLiteStateRepository,
    readiness: ProductionReadinessAuthority,
    run: SourceRunRecord,
) -> dict[str, object]:
    """Return only persisted run facts plus bounded derived presentation."""

    return {
        "run_id": run.run_id,
        "source_id": run.source_id,
        "trigger": run.trigger.value,
        "trigger_reference": run.trigger_reference,
        "priority": run.priority.value,
        "state": run.state.value,
        "attention_reason": (
            None if run.attention_reason is None else run.attention_reason.value
        ),
        "automation_run_id": run.automation_run_id,
        "manual_command_id": run.manual_command_id,
        "manual_analyze_override_id": run.manual_analyze_override_id,
        "created_at": run.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "updated_at": run.updated_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "progress": _progress(repository, run),
        "result": _result(repository, run),
        "recovery": _recovery(run, readiness),
    }


__all__ = ["project_source_run"]
