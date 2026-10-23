"""Dedicated persisted-proof long execution boundaries; no qualification grant."""

from __future__ import annotations

import threading
from contextlib import closing
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from youtube_intel import long_distillation_persistence as persistence
from youtube_intel.local_distillation_profile import (
    CURRENT_RUNTIME_PROFILE_ID as SHORT_CURRENT,
)
from youtube_intel.local_distillation_profile import canonical
from youtube_intel.long_distillation_profile import (
    CURRENT_RUNTIME_PROFILE_ID,
    PreparedLongRequest,
    prepare_long_request,
)
from youtube_intel.long_grounding_codec import EncodedGrounding
from youtube_intel.state import (
    StateStoreError,
    _immediate_transaction,
    format_utc_datetime,
)

if TYPE_CHECKING:
    import sqlite3

    from youtube_intel.distillation import (
        DistillationCommand,
        PersonalizedDistillationService,
        VerifiedDistillationInput,
    )
    from youtube_intel.state import SQLiteStateRepository

_CLAIM_SEAL = object()


@dataclass(frozen=True, slots=True)
class RebuiltLongInput:
    proof: dict[str, Any]
    command: DistillationCommand
    value: VerifiedDistillationInput
    prepared: PreparedLongRequest


@dataclass(frozen=True, slots=True)
class ClaimedLongExecution:
    execution_id: str
    proof_hash: str
    request_hash: str
    owner: int
    _seal: object


def profile_qualified(service: PersonalizedDistillationService, language: str) -> bool:
    check = getattr(service._transport, "long_profile_qualified", None)
    return (service._local_profile_id == SHORT_CURRENT and service._selected_provider == "ollama"
        and callable(check) and check(CURRENT_RUNTIME_PROFILE_ID, language, service._now()) is True)


def reserve_pending(
    service: PersonalizedDistillationService, *, source_id: str, video_id: str,
    evidence_ids: tuple[str, ...], manual_command_id: str,
) -> str:
    if not manual_command_id or not profile_qualified(service, service.capability_output_language(video_id) or ""):
        raise StateStoreError("new long dispatch requires its qualified manual command")
    return persistence._reserve(service, source_id=source_id, video_id=video_id,
        evidence_ids=evidence_ids, manual_command_id=manual_command_id, pending=True)


def rebuild_long(
    repository: SQLiteStateRepository, connection: sqlite3.Connection, execution_id: str,
) -> RebuiltLongInput:
    from youtube_intel.distillation import (
        ActivePreferenceProjection,
        DistillationCommand,
        VerifiedDistillationInput,
        VerifiedEvidenceInput,
    )

    proof = persistence.verify_proof(repository, connection, execution_id)
    side = persistence.loads(proof["semantic_snapshot_wire"])
    values = dict(side["value"])
    values["evidence"] = tuple(VerifiedEvidenceInput(**e) for e in values["evidence"])
    for key in ("personalization", "source_focus_rules", "source_ignore_rules"):
        values[key] = tuple(values[key])
    value = VerifiedDistillationInput(**values)
    command_data = dict(persistence.loads(side["snapshots"]["policy"]["wire"])["command"])
    for key in ("evidence_ids", "preference_ids", "source_focus_rules", "source_ignore_rules"):
        command_data[key] = tuple(command_data[key])
    command_data["active_preferences"] = tuple(ActivePreferenceProjection(**p) for p in command_data["active_preferences"])
    command = DistillationCommand(**command_data)
    prepared = prepare_long_request(
        EncodedGrounding(side["codec"]["canonical_wire"].encode()), value,
        source_snapshot=side["snapshots"]["source"]["wire"].encode(),
        summary_snapshot=side["snapshots"]["summary"]["wire"].encode(),
        policy_snapshot=side["snapshots"]["policy"]["wire"].encode(),
        profile_id=persistence._profile_id(proof),
    )
    persistence._verify_prepared(proof, prepared)
    return RebuiltLongInput(proof, command, value, prepared)


def claim_long(
    service: PersonalizedDistillationService, execution_id: str, prepared: PreparedLongRequest,
) -> ClaimedLongExecution:
    repository = service._repository
    with closing(repository._connect()) as connection, _immediate_transaction(connection):
        rebuilt = rebuild_long(repository, connection, execution_id)
        proof, command = rebuilt.proof, rebuilt.command
        persistence.verify_execution(repository, connection, execution_id)
        checkpoint = persistence._row(connection, "distillation_execution_checkpoints", "execution_id", execution_id)
        if (persistence._profile_id(proof) != CURRENT_RUNTIME_PROFILE_ID
            or checkpoint["status"] != "PENDING" or checkpoint["invocation_count"] != 0
            or checkpoint["budget_state"] != "RESERVED_NOT_DISPATCHED"
            or not checkpoint["reason"].startswith("MANUAL_CONTENT:")
            or type(prepared) is not PreparedLongRequest or prepared != rebuilt.prepared):
            raise StateStoreError("long claim is not a new exact pending manual request")
        ready = getattr(service._transport, "armed_long_for_claim", None)
        if (not profile_qualified(service, rebuilt.value.output_language)
            or not callable(ready) or ready(execution_id, rebuilt.prepared) is not True):
            raise StateStoreError("long claim readiness, lease or qualification differs")
        if not service._manual_content_ready(command.source_id, command.video_id):
            raise StateStoreError("long manual Content is no longer eligible")
        summary = connection.execute("SELECT analysis_artifact_id FROM current_content_summaries WHERE video_id=?", (command.video_id,)).fetchone()
        policy = connection.execute("SELECT revision_id FROM source_policy_current WHERE policy_key='GLOBAL'").fetchone()
        if (summary is None or summary[0] != proof["original_summary_artifact_id"]
            or policy is None or policy[0] != proof["global_policy_revision_id"]
            or canonical(asdict(service._projection(command))) != canonical(asdict(command))):
            raise StateStoreError("long current Summary/policy/preference selection changed before claim")
        packet = EncodedGrounding(persistence.loads(proof["semantic_snapshot_wire"])["codec"]["canonical_wire"].encode())
        source = persistence._row(connection, "source_subscriptions", "source_id", command.source_id)
        video = persistence._row(connection, "videos", "video_id", command.video_id)
        if persistence._value(command, source, video, packet, rebuilt.value.local_profile_id) != rebuilt.value:
            raise StateStoreError("long current source attribution changed before claim")
        decision = service._budget.check(command)
        if not decision.allowed or decision.state not in {"ADMITTED", "RUNTIME_BUDGET_ADMITTED"}:
            raise StateStoreError("long claim budget is unavailable")
        changed = connection.execute(
            "UPDATE distillation_execution_checkpoints SET invocation_count=1,budget_state='DISPATCH_CLAIMED',updated_at=? "
            "WHERE execution_id=? AND status='PENDING' AND invocation_count=0 AND budget_state='RESERVED_NOT_DISPATCHED'",
            (format_utc_datetime(service._now()), execution_id),
        ).rowcount
        if changed != 1:
            raise StateStoreError("long invocation was already claimed")
        persistence.verify_execution(repository, connection, execution_id)
    return ClaimedLongExecution(execution_id, proof["proof_hash"], proof["request_hash"], threading.get_ident(), _CLAIM_SEAL)
