"""Final41 storage branches with explicit synthetic SQL, never model authority.

The WAIT-only application intentionally rejects every result fixture below.
These cases prove final DDL can express real success/zero/rejection observations
and deferred insertion order without changing historical migration41 later.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest
from conftest import _load_module

from youtube_intel.local_distillation_profile import canonical, digest
from youtube_intel.long_card_canonical import canonicalize_long_card
from youtube_intel.long_distillation_persistence import (
    PREFIX,
    PROOFS,
    RECEIPTS,
    _proof_digest,
    verify_receipt_payload,
)
from youtube_intel.long_grounding_codec import EncodedGrounding, decode_output
from youtube_intel.state import StateStoreError

long = _load_module("test_long_input_wait_lifecycle")


def insert(connection, table, values):
    connection.execute(
        f"INSERT INTO {table}({','.join(values)}) VALUES({','.join('?' for _ in values)})",
        tuple(values.values()),
    )


def pending(repository, service, sid, vid):
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="sql-storage-seed",
    )
    c = repository._connect()
    c.execute("BEGIN IMMEDIATE")
    proof = dict(
        c.execute(
            f"SELECT * FROM {PROOFS} WHERE execution_id=?", (reservation.execution_id,)
        ).fetchone()
    )
    checkpoint = dict(
        c.execute(
            "SELECT * FROM distillation_execution_checkpoints WHERE execution_id=?",
            (reservation.execution_id,),
        ).fetchone()
    )
    execution_id = PREFIX + "f" * 64
    checkpoint.update(
        execution_id=execution_id,
        status="PENDING",
        invocation_count=0,
        budget_state="RESERVED_NOT_DISPATCHED",
    )
    insert(c, "distillation_execution_checkpoints", checkpoint)
    proof["execution_id"] = execution_id
    proof["proof_hash"] = _proof_digest(proof)
    insert(c, PROOFS, proof)
    c.execute(
        "UPDATE distillation_execution_checkpoints SET invocation_count=1,budget_state='DISPATCH_CLAIMED' WHERE execution_id=?",
        (execution_id,),
    )
    return c, proof, checkpoint


def receipt(
    proof,
    kind="INTELLIGENCE",
    *,
    done=True,
    reason="stop",
    public_state="PRESENT",
    actual_model=None,
):
    packet = EncodedGrounding(
        json.loads(proof["semantic_snapshot_wire"])["codec"]["canonical_wire"].encode()
    )
    rows = json.loads(packet.canonical_wire)["evidence"]
    refs = [
        {
            "evidence_id": r["alias"],
            "start_ms": r["start_ms"],
            "end_ms": r["end_ms"],
            "stance": "supporting",
        }
        for r in rows
    ]
    positive = {
        "result": "INTELLIGENCE",
        "core_conclusion": "Fixture claim.",
        "user_relevant_information": [],
        "important_new_information": [],
        "meaningful_details": [],
        "filtered_noise": [],
        "claim_kind": "FACT",
        "evidence": refs[:1],
    }
    public = (
        canonical(
            positive
            if kind == "INTELLIGENCE"
            else {
                "result": "NO_NEW_INTELLIGENCE",
                "evidence": [
                    {k: v for k, v in r.items() if k != "stance"} for r in refs
                ],
            }
        )
        if kind != "REJECTED"
        else b""
    )
    decoded = decode_output(public, packet) if kind != "REJECTED" else None
    metadata = {
        "done": done,
        "done_reason": reason,
        "actual_provider": "ollama",
        "actual_model": actual_model or json.loads(proof["request_wire"])["model"],
        "request_hash": proof["request_hash"],
        "input_tokens": 10,
        "output_tokens": 20,
        "cost_microunits": None,
        "duration_ms": 12,
        "public_state": public_state,
    }
    wire = public.decode() if public_state == "PRESENT" else None
    result = dict(
        execution_id=proof["execution_id"],
        usage_execution_id=None
        if kind == "NO_NEW_INTELLIGENCE"
        else proof["execution_id"],
        receipt_version="long-timed-completion-receipt-v1",
        proof_hash=proof["proof_hash"],
        public_wire=wire,
        public_hash=None if wire is None else hashlib.sha256(wire.encode()).hexdigest(),
        decoded_wire=None if decoded is None else decoded.decoded_wire.decode(),
        decoded_hash=None if decoded is None else decoded.decoded_hash,
        completion_json=canonical(metadata).decode(),
        completion_hash=hashlib.sha256(canonical(metadata)).hexdigest(),
        result_kind=kind,
        terminal={
            "INTELLIGENCE": "SUCCEEDED",
            "NO_NEW_INTELLIGENCE": "SUCCEEDED_NO_NEW_INTELLIGENCE",
            "REJECTED": "REJECTED_OUTPUT",
        }[kind],
        intelligence_id="intelligence:distillation:" + proof["execution_id"]
        if kind == "INTELLIGENCE"
        else None,
        revision_id="revision:distillation:" + proof["execution_id"]
        if kind == "INTELLIGENCE"
        else None,
        admitted_content_hash=canonicalize_long_card(decoded.decoded_wire).content_hash
        if kind == "INTELLIGENCE"
        else None,
        no_new_execution_id=proof["execution_id"]
        if kind == "NO_NEW_INTELLIGENCE"
        else None,
        receipt_hash="",
        created_at=proof["created_at"],
    )
    result["receipt_hash"] = digest(
        {k: v for k, v in result.items() if k != "receipt_hash"}
    )
    return result


def finalize(
    c, proof, checkpoint, result, *, omit_dependency=False, usage_changes=None
):
    insert(c, RECEIPTS, result)  # Deferred references do not exist yet.
    if result["result_kind"] == "INTELLIGENCE":
        insert(
            c,
            "intelligences",
            {
                "intelligence_id": result["intelligence_id"],
                "current_revision_id": None,
                "created_at": proof["created_at"],
            },
        )
        insert(
            c,
            "intelligence_revisions",
            dict(
                revision_id=result["revision_id"],
                intelligence_id=result["intelligence_id"],
                revision_number=1,
                prior_revision_id=None,
                interpretation_kind="DISTILLATION",
                content_hash=result["admitted_content_hash"],
                created_at=proof["created_at"],
                claim_kind="FACT",
            ),
        )
        decoded = json.loads(result["decoded_wire"])
        insert(
            c,
            "distillation_cards",
            dict(
                revision_id=result["revision_id"],
                source_id=proof["source_id"],
                video_id=proof["video_id"],
                core_conclusion=decoded["core_conclusion"],
                user_relevant_information_json="[]",
                important_new_information_json="[]",
                meaningful_details_json="[]",
                filtered_noise_json="[]",
                preference_ids_json="[]",
                source_policy_revision_id=proof["source_policy_revision_id"],
                created_at=proof["created_at"],
            ),
        )
    metadata = json.loads(result["completion_json"])
    if result["result_kind"] == "NO_NEW_INTELLIGENCE":
        ids = sorted(
            e["evidence_id"]
            for e in json.loads(proof["semantic_snapshot_wire"])["value"]["evidence"]
        )
        zero = {
            k: checkpoint[k]
            for k in ("execution_id", "source_id", "video_id", "reason", "use_case")
        }
        zero.update(
            evidence_ids_json=json.dumps(ids, separators=(",", ":")),
            evidence_set_hash=hashlib.sha256(
                json.dumps(ids, separators=(",", ":")).encode()
            ).hexdigest(),
            actual_provider=metadata["actual_provider"],
            actual_model=metadata["actual_model"],
            input_tokens=metadata["input_tokens"],
            output_tokens=metadata["output_tokens"],
            cost_microunits=metadata["cost_microunits"],
            duration_ms=metadata["duration_ms"],
            budget_state="ADMITTED",
            outcome="NO_NEW_INTELLIGENCE",
            created_at=proof["created_at"],
            http_status_code=None,
        )
        # m020 makes the checkpoint terminal after inserting zero, so complete
        # its budget/time first. No physical zero usage row is created.
        c.execute(
            "UPDATE distillation_execution_checkpoints SET budget_state='ADMITTED' WHERE execution_id=?",
            (proof["execution_id"],),
        )
        if not omit_dependency:
            insert(c, "distillation_no_new_intelligence_results", zero)
    else:
        usage = {
            k: checkpoint[k]
            for k in (
                "execution_id",
                "source_id",
                "video_id",
                "reason",
                "use_case",
                "selected_provider",
                "selected_model",
            )
        }
        usage.update(
            intelligence_id=result["intelligence_id"],
            revision_id=result["revision_id"],
            status=result["terminal"],
            invocation_count=1,
            actual_provider=metadata["actual_provider"],
            actual_model=metadata["actual_model"],
            input_tokens=metadata["input_tokens"],
            output_tokens=metadata["output_tokens"],
            cost_microunits=metadata["cost_microunits"],
            duration_ms=metadata["duration_ms"],
            budget_state="ADMITTED",
            outcome=result["terminal"],
            created_at=proof["created_at"],
        )
        usage.update(usage_changes or {})
        if not omit_dependency:
            insert(c, "distillation_resource_usage", usage)
        c.execute(
            "UPDATE distillation_execution_checkpoints SET status=?,budget_state='ADMITTED',intelligence_id=?,revision_id=? WHERE execution_id=?",
            (
                result["terminal"],
                result["intelligence_id"],
                result["revision_id"],
                proof["execution_id"],
            ),
        )


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"])
def test_final_sql_three_branches_deferred_order_but_application_result_authority_closed(
    tmp_path, kind
):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(
        tmp_path, 21
    )
    c, proof, checkpoint = pending(repository, service, sid, vid)
    checkpoint["execution_id"] = proof["execution_id"]
    try:
        result = receipt(proof, kind)
        finalize(c, proof, checkpoint, result)
        c.commit()
        assert not c.execute("PRAGMA foreign_key_check").fetchall()
        verify_receipt_payload(c, proof, result)
        assert (
            c.execute(
                "SELECT 1 FROM distillation_resource_usage WHERE execution_id=?",
                (proof["execution_id"],),
            ).fetchone()
            is None
        ) == (kind == "NO_NEW_INTELLIGENCE")
        with pytest.raises(StateStoreError):
            repository.get_distillation_execution(proof["execution_id"])
    finally:
        c.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"done": False},
        {"reason": "length"},
        {"public_state": "ABSENT"},
        {"public_state": "OVERSIZE"},
        {"actual_model": "different-observed-model"},
        {"done": None, "reason": None},
    ],
)
def test_rejected_receipt_preserves_real_incomplete_missing_or_wrong_identity(
    tmp_path, changes
):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(
        tmp_path, 21
    )
    c, proof, checkpoint = pending(repository, service, sid, vid)
    checkpoint["execution_id"] = proof["execution_id"]
    try:
        result = receipt(proof, "REJECTED", **changes)
        finalize(c, proof, checkpoint, result)
        c.commit()
        verify_receipt_payload(c, proof, result)
        assert (
            dict(
                c.execute(
                    f"SELECT * FROM {RECEIPTS} WHERE execution_id=?",
                    (proof["execution_id"],),
                ).fetchone()
            )
            == result
        )
    finally:
        c.close()


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE"])
@pytest.mark.parametrize(
    "defect",
    [
        "missing_done_reason",
        "length",
        "false",
        "wrong_model",
        "unpaired",
        "float",
        "overflow",
        "thinking",
    ],
)
def test_success_metadata_missing_keys_or_unreliable_observation_is_rejected(
    tmp_path, kind, defect
):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(
        tmp_path, 21
    )
    c, proof, _checkpoint = pending(repository, service, sid, vid)
    try:
        result = receipt(proof, kind)
        metadata = json.loads(result["completion_json"])
        if defect == "missing_done_reason":
            del metadata["done_reason"]
        elif defect == "length":
            metadata["done_reason"] = "length"
        elif defect == "false":
            metadata["done"] = False
        elif defect == "wrong_model":
            metadata["actual_model"] = "other-model"
        elif defect == "unpaired":
            metadata["input_tokens"] = None
        elif defect == "float":
            metadata["input_tokens"] = 1.5
        elif defect == "overflow":
            metadata["input_tokens"] = 2**63
        elif defect == "thinking":
            metadata["thinking"] = "forbidden"
        result["completion_json"] = canonical(metadata).decode()
        with pytest.raises(sqlite3.IntegrityError):
            insert(c, RECEIPTS, result)
    finally:
        c.rollback()
        c.close()


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"])
def test_receipt_cannot_commit_without_its_conditional_usage_authority(tmp_path, kind):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(
        tmp_path, 21
    )
    c, proof, checkpoint = pending(repository, service, sid, vid)
    checkpoint["execution_id"] = proof["execution_id"]
    try:
        finalize(c, proof, checkpoint, receipt(proof, kind), omit_dependency=True)
        with pytest.raises(sqlite3.IntegrityError):
            c.commit()
    finally:
        c.rollback()
        c.close()


@pytest.mark.parametrize(
    "field",
    ["actual_model", "input_tokens", "output_tokens", "duration_ms", "cost_microunits"],
)
def test_physical_usage_must_match_the_actual_receipt_observation(tmp_path, field):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(
        tmp_path, 21
    )
    c, proof, checkpoint = pending(repository, service, sid, vid)
    checkpoint["execution_id"] = proof["execution_id"]
    try:
        with pytest.raises(sqlite3.IntegrityError, match="usage differs"):
            finalize(
                c,
                proof,
                checkpoint,
                receipt(proof, "REJECTED"),
                usage_changes={
                    field: "wrong-model" if field == "actual_model" else 999
                },
            )
    finally:
        c.rollback()
        c.close()
