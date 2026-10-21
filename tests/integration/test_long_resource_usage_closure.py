"""Usage projections must not grant the unopened long-result capability."""

from __future__ import annotations

import pytest
from conftest import _load_module

from youtube_intel.intelligence_read import (
    AuthoritativeIntelligenceReader,
    IntelligenceReadRejected,
)
from youtube_intel.local_api import ApiError
from youtube_intel.long_distillation_persistence import (
    is_long,
    is_long_revision,
    verify_database,
)
from youtube_intel.state import StateStoreError

long = _load_module("test_long_input_wait_lifecycle")
contract = _load_module("test_long_completion_storage_contract")


@pytest.mark.parametrize("kind", ["INTELLIGENCE", "NO_NEW_INTELLIGENCE", "REJECTED"])
@pytest.mark.parametrize("reader", ["direct", "list", "api"])
def test_unopened_long_result_never_becomes_resource_authority(tmp_path, kind, reader):
    repository, _root, sid, vid, service, app, _transport = long.workspace(tmp_path)
    c, proof, checkpoint = contract.pending(repository, service, sid, vid)
    checkpoint["execution_id"] = proof["execution_id"]
    try:
        contract.finalize(c, proof, checkpoint, contract.receipt(proof, kind))
        c.commit()
    finally:
        c.close()
    if reader == "api":
        with pytest.raises(ApiError) as rejected:
            app.handle("GET", "/api/v1/settings/resource-usage")
        assert rejected.value.status == 409
        assert rejected.value.code == "RESOURCE_USAGE_UNAVAILABLE"
    else:
        with pytest.raises(StateStoreError):
            if reader == "direct":
                repository.get_distillation_resource_usage(proof["execution_id"])
            else:
                repository.list_distillation_resource_usage()


FOLDED_FAMILIES = [
    "DISTILLATION:LONG-TIMED-V1:",
    "dIsTiLlAtIoN:LoNg-TiMeD-v1:",
    "diſtillation:long-timed-v1:",
]


@pytest.mark.parametrize("prefix", FOLDED_FAMILIES)
@pytest.mark.parametrize("reader", ["direct", "list", "api", "database"])
def test_casefold_family_missing_ledger_cannot_disappear(tmp_path, prefix, reader):
    repository, _root, sid, vid, service, app, _transport = long.workspace(tmp_path)
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="casefold-resource-wait",
    )
    altered = prefix + "a" * 64
    assert is_long(altered)
    c = repository._connect()
    try:
        c.execute("PRAGMA foreign_keys=OFF")
        triggers = c.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
        for name, _sql in triggers:
            c.execute('DROP TRIGGER "' + name + '"')
        c.execute(
            "DELETE FROM distillation_resource_usage WHERE execution_id=?",
            (reservation.execution_id,),
        )
        # Isolate the reverse scan: another retained proof must not be what
        # happens to discover this damaged reserved-family checkpoint.
        if reader == "database":
            c.execute(
                "DELETE FROM long_distillation_input_proofs WHERE execution_id=?",
                (reservation.execution_id,),
            )
        c.execute(
            "UPDATE distillation_execution_checkpoints SET execution_id=? WHERE execution_id=?",
            (altered, reservation.execution_id),
        )
        for _name, sql in triggers:
            c.execute(sql)
        if reader == "database":
            with pytest.raises(StateStoreError):
                verify_database(repository, c)
        elif reader == "api":
            with pytest.raises(ApiError) as rejected:
                app.handle("GET", "/api/v1/settings/resource-usage")
            assert rejected.value.status == 409
            assert rejected.value.code == "RESOURCE_USAGE_UNAVAILABLE"
        else:
            with pytest.raises(StateStoreError):
                if reader == "direct":
                    repository.get_distillation_resource_usage(altered)
                else:
                    repository.list_distillation_resource_usage()
    finally:
        c.close()


@pytest.mark.parametrize("prefix", FOLDED_FAMILIES)
def test_casefold_orphan_revision_is_reserved_result_authority(tmp_path, prefix):
    repository, _root, _sid, _vid, _service, _app, _transport = long.workspace(tmp_path)
    revision_id = "revision:distillation:" + prefix + "b" * 64
    assert is_long_revision(revision_id)
    c = repository._connect()
    try:
        contract.insert(
            c,
            "intelligences",
            {
                "intelligence_id": "orphan-casefold",
                "current_revision_id": None,
                "created_at": long.NOW.isoformat().replace("+00:00", "Z"),
            },
        )
        contract.insert(
            c,
            "intelligence_revisions",
            {
                "revision_id": revision_id,
                "intelligence_id": "orphan-casefold",
                "revision_number": 1,
                "prior_revision_id": None,
                "interpretation_kind": "DISTILLATION",
                "content_hash": "b" * 64,
                "created_at": long.NOW.isoformat().replace("+00:00", "Z"),
                "claim_kind": "FACT",
            },
        )
        with pytest.raises(StateStoreError, match="long revision authority"):
            verify_database(repository, c)
    finally:
        c.close()


@pytest.mark.parametrize("prefix", FOLDED_FAMILIES)
def test_generic_revision_cannot_hide_casefold_long_checkpoint(tmp_path, prefix):
    repository, _root, sid, vid, service, _app, _transport = long.workspace(tmp_path)
    reserved = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="associated-casefold",
    )
    c = repository._connect()
    try:
        contract.insert(
            c,
            "intelligences",
            {
                "intelligence_id": "generic-intelligence",
                "current_revision_id": None,
                "created_at": long.NOW.isoformat().replace("+00:00", "Z"),
            },
        )
        contract.insert(
            c,
            "intelligence_revisions",
            {
                "revision_id": "generic-revision",
                "intelligence_id": "generic-intelligence",
                "revision_number": 1,
                "prior_revision_id": None,
                "interpretation_kind": "DISTILLATION",
                "content_hash": "c" * 64,
                "created_at": long.NOW.isoformat().replace("+00:00", "Z"),
                "claim_kind": "FACT",
            },
        )
        triggers = c.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
        for name, _sql in triggers:
            c.execute('DROP TRIGGER "' + name + '"')
        c.execute("PRAGMA foreign_keys=OFF")
        c.execute(
            "UPDATE intelligences SET current_revision_id='generic-revision' WHERE intelligence_id='generic-intelligence'"
        )
        c.execute(
            "UPDATE distillation_execution_checkpoints SET execution_id=?,status='SUCCEEDED',invocation_count=1,budget_state='ADMITTED',intelligence_id='generic-intelligence',revision_id='generic-revision' WHERE execution_id=?",
            (prefix + "a" * 64, reserved.execution_id),
        )
        for _name, sql in triggers:
            c.execute(sql)
        with pytest.raises(IntelligenceReadRejected) as rejected:
            AuthoritativeIntelligenceReader(repository).read_recorded_card(
                "generic-intelligence", "generic-revision"
            )
        assert rejected.value.code == "LONG_AUTHORITY_UNAVAILABLE"
    finally:
        c.close()


@pytest.mark.parametrize("cancelled", [False, True])
def test_verified_wait_and_cancel_remain_truthful_zero_invocation_usage(
    tmp_path, cancelled
):
    repository, _root, sid, vid, service, app, transport = long.workspace(tmp_path)
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="resource-wait",
    )
    execution_id = reservation.execution_id
    if cancelled:
        repository.cancel_waiting_model_execution(
            execution_id, video_id=vid, now=long.NOW
        )
    direct = repository.get_distillation_resource_usage(execution_id)
    assert direct.status == "WAITING_MODEL" and direct.invocation_count == 0
    assert repository.list_distillation_resource_usage() == (direct,)
    status, response = app.handle("GET", "/api/v1/settings/resource-usage")
    assert status == 200
    assert len(response["usage"]) == 1
    assert response["usage"][0]["invocation_count"] == 0
    assert transport.calls == 0


@pytest.mark.parametrize(
    "damage", ["proof", "ledger", "source", "unknown", "malformed"]
)
@pytest.mark.parametrize("reader", ["direct", "list", "api"])
def test_damaged_or_unknown_long_usage_fails_closed(tmp_path, damage, reader):
    repository, root, sid, vid, service, app, _transport = long.workspace(tmp_path)
    reservation = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="damaged-resource-wait",
    )
    execution_id = reservation.execution_id
    if damage == "source":
        (root / "canonical.txt").write_bytes(b"corrupt source")
    else:
        c = repository._connect()
        try:
            c.execute("PRAGMA foreign_keys=OFF")
            triggers = c.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger'"
            ).fetchall()
            for name, _sql in triggers:
                c.execute('DROP TRIGGER "' + name + '"')
            if damage in {"proof", "ledger"}:
                table = {
                    "proof": "long_distillation_input_proofs",
                    "ledger": "distillation_resource_usage",
                }[damage]
                c.execute(
                    "DELETE FROM " + table + " WHERE execution_id=?", (execution_id,)
                )
            else:
                altered = (
                    "distillation:long-timed-v999:" + "a" * 64
                    if damage == "unknown"
                    else "distillation:long-timed-v1:bad"
                )
                for table in (
                    "distillation_execution_checkpoints",
                    "distillation_resource_usage",
                ):
                    c.execute(
                        "UPDATE " + table + " SET execution_id=? WHERE execution_id=?",
                        (altered, execution_id),
                    )
                execution_id = altered
            for _name, sql in triggers:
                c.execute(sql)
        finally:
            c.close()
    if reader == "api":
        with pytest.raises(ApiError) as rejected:
            app.handle("GET", "/api/v1/settings/resource-usage")
        assert rejected.value.status == 409
        assert rejected.value.code == "RESOURCE_USAGE_UNAVAILABLE"
    else:
        with pytest.raises(StateStoreError):
            if reader == "direct":
                repository.get_distillation_resource_usage(execution_id)
            else:
                repository.list_distillation_resource_usage()
