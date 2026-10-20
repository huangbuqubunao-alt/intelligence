"""Usage projections must not grant the unopened long-result capability."""

from __future__ import annotations

import pytest
from conftest import _load_module

from youtube_intel.local_api import ApiError
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
