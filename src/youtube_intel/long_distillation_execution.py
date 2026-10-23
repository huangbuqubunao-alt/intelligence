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

    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.distillation import (
        DistillationCommand,
        DistillationResult,
        PersonalizedDistillationService,
        VerifiedDistillationInput,
    )
    from youtube_intel.local_model_capacity import ApplicationHeavyLease
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
    *, qualification: bool = False,
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
        permitted = profile_qualified(service, rebuilt.value.output_language)
        if qualification:
            permits = getattr(service._transport, "long_request_authorized", None)
            permitted = callable(permits) and permits(execution_id, rebuilt.prepared, rebuilt.value, qualification=True) is True
        if (not permitted
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


def _insert(connection: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
    # Tables and fields are private fixed application literals.
    connection.execute(
        f"INSERT INTO {table}({','.join(values)}) VALUES({','.join('?' for _ in values)})",
        tuple(values.values()),
    )


def _completion_receipt(
    rebuilt: RebuiltLongInput, response: dict[str, Any], *, duration_ms: int, timestamp: str,
) -> dict[str, Any]:
    import hashlib

    from youtube_intel.local_distillation_profile import digest
    from youtube_intel.long_card_canonical import canonicalize_long_card
    from youtube_intel.long_grounding_codec import decode_output

    model = response.get("model")
    if (not isinstance(model, str) or not model.strip() or model != model.strip()
        or len(model) > 320 or type(duration_ms) is not int or not 0 <= duration_ms <= 2**63 - 1):
        raise StateStoreError("long response identity or duration is unknown")
    inputs, outputs = response.get("prompt_eval_count"), response.get("eval_count")
    reliable = all(type(v) is int and 0 <= v <= 2**63 - 1 for v in (inputs, outputs))
    if not reliable:
        inputs = outputs = None
    done = response.get("done") if type(response.get("done")) is bool else None
    reason = response.get("done_reason") if isinstance(response.get("done_reason"), str) else None
    if reason is not None and len(reason) > 160:
        reason = None
    message = response.get("message")
    public = message.get("content") if isinstance(message, dict) else None
    if isinstance(public, str):
        wire = public.encode("utf-8", errors="strict")
        public_state = "PRESENT" if len(wire) <= 1_000_000 else "OVERSIZE"
        if public_state == "OVERSIZE":
            public = None
    else:
        public, public_state = None, "ABSENT"
    packet = EncodedGrounding(persistence.loads(rebuilt.proof["semantic_snapshot_wire"])["codec"]["canonical_wire"].encode())
    decoded = None
    if public:
        try:
            decoded = decode_output(public.encode(), packet)
        except ValueError:
            pass  # Keep authentic malformed public bytes as a rejected outcome.
    kind = "REJECTED"
    admitted_hash = None
    if (done is True and reason == "stop" and model == rebuilt.value.selected_model
        and type(inputs) is int and type(outputs) is int
        and 0 < outputs < 6144 and 0 < inputs and inputs + 6144 + 2 <= 32768
        and decoded is not None):
        kind = persistence.loads(decoded.decoded_wire.decode())["result"]
        if kind == "INTELLIGENCE":
            admitted_hash = canonicalize_long_card(decoded.decoded_wire).content_hash
    metadata = dict(done=done, done_reason=reason, actual_provider="ollama", actual_model=model,
        request_hash=rebuilt.prepared.request_hash, input_tokens=inputs, output_tokens=outputs,
        cost_microunits=None, duration_ms=duration_ms, public_state=public_state)
    eid = rebuilt.proof["execution_id"]
    receipt = dict(execution_id=eid, usage_execution_id=None if kind == "NO_NEW_INTELLIGENCE" else eid,
        receipt_version="long-timed-completion-receipt-v1", proof_hash=rebuilt.proof["proof_hash"],
        public_wire=public, public_hash=None if public is None else hashlib.sha256(public.encode()).hexdigest(),
        decoded_wire=None if decoded is None else decoded.decoded_wire.decode(),
        decoded_hash=None if decoded is None else decoded.decoded_hash,
        completion_json=canonical(metadata).decode(), completion_hash=hashlib.sha256(canonical(metadata)).hexdigest(),
        result_kind=kind, terminal={"INTELLIGENCE": "SUCCEEDED", "NO_NEW_INTELLIGENCE": "SUCCEEDED_NO_NEW_INTELLIGENCE", "REJECTED": "REJECTED_OUTPUT"}[kind],
        intelligence_id="intelligence:distillation:" + eid if kind == "INTELLIGENCE" else None,
        revision_id="revision:distillation:" + eid if kind == "INTELLIGENCE" else None,
        admitted_content_hash=admitted_hash, no_new_execution_id=eid if kind == "NO_NEW_INTELLIGENCE" else None,
        receipt_hash="", created_at=timestamp)
    receipt["receipt_hash"] = digest({k: v for k, v in receipt.items() if k != "receipt_hash"})
    return receipt


def complete_long(
    service: PersonalizedDistillationService, claim: ClaimedLongExecution,
    response: dict[str, Any], *, duration_ms: int,
) -> None:
    """Commit a known response and its entire branch in one immediate transaction.

    Only the dedicated claimed boundary may call this after its one-shot native
    consume. Unknown identity/transport raises without a receipt or a retry.
    Persisted bytes are strictly decoded, never repaired or rephrased.
    """
    import hashlib
    import json

    from youtube_intel.state import (
        DistillationCardWrite,
        EvidenceStance,
        IntelligenceClaimKind,
    )

    if type(claim) is not ClaimedLongExecution or claim._seal is not _CLAIM_SEAL or claim.owner != threading.get_ident():
        raise StateStoreError("long completion claim is foreign or on a different thread")
    repository = service._repository
    now = service._now()
    timestamp = format_utc_datetime(now)
    with closing(repository._connect()) as connection, _immediate_transaction(connection):
        rebuilt = rebuild_long(repository, connection, claim.execution_id)
        if (rebuilt.proof["proof_hash"] != claim.proof_hash or rebuilt.prepared.request_hash != claim.request_hash
            or persistence._profile_id(rebuilt.proof) != CURRENT_RUNTIME_PROFILE_ID):
            raise StateStoreError("long completion claim differs from its persisted request")
        persistence.verify_execution(repository, connection, claim.execution_id)
        checkpoint = connection.execute("SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?", (claim.execution_id,)).fetchone()
        if checkpoint is None or checkpoint["invocation_count"] != 1 or checkpoint["budget_state"] != "DISPATCH_CLAIMED" or checkpoint["status"] != "PENDING":
            raise StateStoreError("long completion is not the single claimed invocation")
        receipt = _completion_receipt(rebuilt, response, duration_ms=duration_ms, timestamp=timestamp)
        _insert(connection, persistence.RECEIPTS, receipt)
        metadata = persistence.loads(receipt["completion_json"])
        kind = receipt["result_kind"]
        budget = "ADMITTED" if kind != "REJECTED" else "REJECTED_OUTPUT"
        if kind == "INTELLIGENCE":
            value = persistence.loads(receipt["decoded_wire"])
            evidence = tuple(sorted(ref["evidence_id"] for ref in value["evidence"]))
            stances = {ref["evidence_id"]: EvidenceStance(ref["stance"]) for ref in value["evidence"]}
            card = DistillationCardWrite(source_id=rebuilt.command.source_id, video_id=rebuilt.command.video_id,
                core_conclusion=value["core_conclusion"],
                user_relevant_information=tuple(value["user_relevant_information"]),
                important_new_information=tuple(value["important_new_information"]),
                meaningful_details=tuple(value["meaningful_details"]), filtered_noise=tuple(value["filtered_noise"]),
                preference_ids=rebuilt.command.preference_ids, source_policy_revision_id=rebuilt.command.source_policy_revision_id)
            encoded = {key + "_json": json.dumps(list(getattr(card, key)), separators=(",", ":")) for key in (
                "user_relevant_information", "important_new_information", "meaningful_details", "filtered_noise", "preference_ids")}
            repository._insert_distillation_card_in_transaction(connection,
                intelligence_id=receipt["intelligence_id"], revision_id=receipt["revision_id"],
                claim_kind=IntelligenceClaimKind(value["claim_kind"]), content_hash=receipt["admitted_content_hash"],
                evidence_ids=evidence, stance_by_id=stances,
                supporting_evidence_ids=tuple(e for e in evidence if stances[e] is EvidenceStance.SUPPORTING),
                card=card, encoded_card=encoded, timestamp=timestamp)
        # The NO_NEW physical checkpoint deliberately remains PENDING/inv1.
        # Its immutable sidecar bans any subsequent checkpoint UPDATE.
        connection.execute("UPDATE distillation_execution_checkpoints SET status=?,budget_state=?,intelligence_id=?,revision_id=?,updated_at=? WHERE execution_id=?",
            ("PENDING" if kind == "NO_NEW_INTELLIGENCE" else receipt["terminal"], budget,
             receipt["intelligence_id"], receipt["revision_id"], timestamp, claim.execution_id))
        if kind == "NO_NEW_INTELLIGENCE":
            ids = json.dumps(sorted(e.evidence_id for e in rebuilt.value.evidence), separators=(",", ":"))
            _insert(connection, "distillation_no_new_intelligence_results", dict(
                execution_id=claim.execution_id, source_id=checkpoint["source_id"], video_id=checkpoint["video_id"],
                reason=checkpoint["reason"], use_case=checkpoint["use_case"], evidence_ids_json=ids,
                evidence_set_hash=hashlib.sha256(ids.encode()).hexdigest(),
                **{k: metadata[k] for k in ("actual_provider", "actual_model", "input_tokens", "output_tokens", "cost_microunits", "duration_ms")},
                budget_state=budget, outcome="NO_NEW_INTELLIGENCE", created_at=timestamp, http_status_code=None))
        else:
            repository._insert_distillation_usage(connection, checkpoint=checkpoint,
                status=receipt["terminal"], budget_state=budget,
                outcome="ADMITTED" if kind == "INTELLIGENCE" else "LONG_OUTPUT_REJECTED",
                invocation_count=1, **{k: metadata[k] for k in ("actual_provider", "actual_model", "input_tokens", "output_tokens", "cost_microunits", "duration_ms")},
                http_status_code=None, intelligence_id=receipt["intelligence_id"], revision_id=receipt["revision_id"], now=now)
        persistence.verify_execution(repository, connection, claim.execution_id)


def defer_long(service: PersonalizedDistillationService, execution_id: str, *, budget: bool = False,
    lease: ApplicationHeavyLease | None = None) -> None:
    """Durably defer only an exactly verified never-claimed current pending job."""
    repository = service._repository
    with closing(repository._connect()) as connection, _immediate_transaction(connection):
        rebuilt = rebuild_long(repository, connection, execution_id)
        persistence.verify_execution(repository, connection, execution_id)
        checkpoint = persistence._row(connection, "distillation_execution_checkpoints", "execution_id", execution_id)
        if (checkpoint["status"], checkpoint["invocation_count"], checkpoint["budget_state"]) != ("PENDING", 0, "RESERVED_NOT_DISPATCHED"):
            raise StateStoreError("long deferral cannot alter a claimed or terminated invocation")
        if lease is not None and not lease.valid():
            raise StateStoreError("long recovery lost its application lease")
        decision = service._budget.check(rebuilt.command)
        if not decision.allowed:
            state, outcome = "WAITING_BUDGET", "BUDGET_BLOCKED_BEFORE_TRANSPORT"
        elif budget:
            raise StateStoreError("long budget wait is no longer a blocked budget")
        else:
            state, outcome = "WAITING_MODEL", "MODEL_UNAVAILABLE_BEFORE_TRANSPORT"
        persistence._checkpoint_wait(connection, execution_id, state, decision.state, outcome,
            format_utc_datetime(service._now()))
        persistence.verify_execution(repository, connection, execution_id)


def continue_long(service: PersonalizedDistillationService, execution_id: str, *, qualification: bool) -> DistillationResult:
    """Normal service seam: persisted proof, ready/arm, CAS, one consume, atomic result."""
    import time

    record = service._repository.get_distillation_execution(execution_id)
    if record is None:
        raise StateStoreError("long reservation is missing")
    if (record.status, record.invocation_count, record.budget_state) != ("PENDING", 0, "RESERVED_NOT_DISPATCHED"):
        from dataclasses import replace
        # Presentation only: immutable inv1 unknown remains physically PENDING.
        return service._result(replace(record, status="AMBIGUOUS") if record.status == "PENDING" else record)
    with closing(service._repository._connect()) as connection:
        rebuilt = rebuild_long(service._repository, connection, execution_id)
    transport = service._transport
    prepare = getattr(transport, "prepare_long_execution", None)
    arm = getattr(transport, "arm_long_for_claim", None)
    generate = getattr(transport, "generate_long", None)
    claimed = False
    try:
        decision = service._budget.check(rebuilt.command)
        if not decision.allowed:
            defer_long(service, execution_id, budget=True)
        elif (not callable(prepare) or not callable(arm) or not callable(generate)
            or prepare(execution_id, rebuilt.prepared, rebuilt.value, qualification=qualification) is not True
            or arm(execution_id, rebuilt.prepared) is not True):
            defer_long(service, execution_id)
        else:
            claim = claim_long(service, execution_id, rebuilt.prepared, qualification=qualification)
            claimed = True
            started = time.monotonic()
            response = generate(execution_id, rebuilt.prepared)
            complete_long(service, claim, response, duration_ms=round((time.monotonic() - started) * 1000))
        current = service._repository.get_distillation_execution(execution_id)
        if current is None:
            raise StateStoreError("long execution disappeared")
        return service._result(current)
    except (OSError, ValueError, RuntimeError, StateStoreError):
        if not claimed:
            current = service._repository.get_distillation_execution(execution_id)
            if current is not None and (current.status, current.invocation_count, current.budget_state) == ("PENDING", 0, "RESERVED_NOT_DISPATCHED"):
                defer_long(service, execution_id)
        raise
    finally:
        service._release_local_readiness()


def recover_pre_dispatch_long(service: PersonalizedDistillationService, *,
    backup_restore: BackupRestoreService | None = None) -> int:
    """Defer only proven current manual inv0 after a process interruption.

    No native/model IO or automatic dispatch. Unknown claims and corrupt/legacy
    histories remain closed. A busy lease leaves the real blocker for the next
    ordinary startup; it is never exempted from Backup readiness.
    """
    import logging

    from youtube_intel.local_model_capacity import ApplicationHeavyLease
    repository = service._repository
    if service._local_profile_id != SHORT_CURRENT or repository._source_data_root is None:
        return 0
    with closing(repository._connect()) as connection:
        candidates = [row[0] for row in connection.execute(
            "SELECT execution_id FROM distillation_execution_checkpoints WHERE status='PENDING' "
            "AND invocation_count=0 AND budget_state='RESERVED_NOT_DISPATCHED' "
            "AND selected_provider='ollama' AND reason LIKE 'MANUAL_CONTENT:%'") if persistence.is_long(row[0])]
    if not candidates:
        return 0
    lease = ApplicationHeavyLease(repository=repository, data_root=repository._source_data_root,
        backup_restore=backup_restore)
    if not lease.acquire():
        logging.getLogger(__name__).warning("Current long pre-dispatch recovery remains blocked by active or unknown work")
        return 0
    count = 0
    try:
        for execution_id in candidates:
            try:
                with closing(repository._connect()) as connection:
                    rebuilt = rebuild_long(repository, connection, execution_id)
                if persistence._profile_id(rebuilt.proof) != CURRENT_RUNTIME_PROFILE_ID:
                    continue
                defer_long(service, execution_id, lease=lease)
                count += 1
            except (OSError, ValueError, StateStoreError):
                # Readers/quiescence continue to report the unmodified blocker.
                logging.getLogger(__name__).warning("Current long pre-dispatch recovery remains closed for an unverifiable or changed request")
        return count
    finally:
        lease.release()
