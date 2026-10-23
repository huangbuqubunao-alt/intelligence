"""ENGINEERING_ONLY long completion lifecycle; no real qualification or models."""

import json

import pytest
from conftest import _load_module

from youtube_intel.local_distillation_profile import CURRENT_RUNTIME_PROFILE_ID
from youtube_intel.long_distillation_persistence import PROOFS
from youtube_intel.long_distillation_profile import (
    CURRENT_RUNTIME_PROFILE_ID as LONG_CURRENT,
)
from youtube_intel.long_distillation_profile import PROFILE_ID as LONG_OLD

wait = _load_module("test_long_input_wait_lifecycle")


def test_historical_wait_proof_and_current_runtime_proof_have_independent_builders(tmp_path):
    repository, _root, sid, vid, service, _app, transport = wait.workspace(tmp_path, 21)
    old = service.reserve_distillation_execution(
        source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="historical",
    )
    with repository._connect() as connection:
        before = tuple(connection.execute(f"SELECT * FROM {PROOFS} WHERE execution_id=?", (old.execution_id,)).fetchone())
    # Fixture-only configured route selection; not eligibility or runtime proof.
    service._local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    transport.local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    current = service.reserve_distillation_execution(
        source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="current",
    )
    with repository._connect() as connection:
        profiles = {row["execution_id"]: json.loads(row["profile_wire"])["profile_id"] for row in connection.execute(f"SELECT * FROM {PROOFS}")}
        assert tuple(connection.execute(f"SELECT * FROM {PROOFS} WHERE execution_id=?", (old.execution_id,)).fetchone()) == before
    assert profiles == {old.execution_id: LONG_OLD, current.execution_id: LONG_CURRENT}
    assert repository.get_distillation_execution(old.execution_id).status == "WAITING_MODEL"
    assert repository.get_distillation_execution(current.execution_id).status == "WAITING_MODEL"
    assert transport.calls == 0


def ready_fixture(tmp_path):
    """Explicit ENGINEERING_ONLY qualification and held application lease."""
    from youtube_intel.local_model_capacity import ApplicationHeavyLease

    repo, root, sid, vid, service, _app, transport = wait.workspace(tmp_path, 21)
    service._local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    transport.local_profile_id = CURRENT_RUNTIME_PROFILE_ID
    lease = ApplicationHeavyLease(repository=repo, data_root=root)
    assert lease.acquire()
    transport.long_profile_qualified = lambda profile_id, language, now: profile_id == LONG_CURRENT and language in {"en", "zh-CN"}
    transport.armed_long_for_claim = lambda execution_id, prepared: lease.valid()
    return repo, root, sid, vid, service, transport, lease


def test_dedicated_new_manual_pending_claim_creates_no_fake_zero_usage(tmp_path):
    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        reserve_pending,
    )

    repo, _root, sid, vid, service, transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="one-shot")
        assert repo.get_distillation_execution(eid).status == "PENDING"
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, eid).prepared
            assert not connection.execute("SELECT 1 FROM distillation_resource_usage WHERE execution_id=?", (eid,)).fetchone()
        claim = claim_long(service, eid, prepared)
        assert claim.execution_id == eid
        record = repo.get_distillation_execution(eid)
        assert record.invocation_count == 1 and record.budget_state == "DISPATCH_CLAIMED"
        assert transport.calls == 0
        with repo._connect() as connection:
            assert not connection.execute("SELECT 1 FROM distillation_resource_usage WHERE execution_id=?", (eid,)).fetchone()
    finally:
        lease.release()


@pytest.mark.parametrize("change", ["qualification", "lease", "budget", "request"])
def test_long_claim_rechecks_preconditions_without_an_invocation_or_zero_usage(tmp_path, change):
    from dataclasses import replace

    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.state import StateStoreError

    repo, root, sid, vid, service, transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="changed")
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, eid).prepared
        before = wait._inventory(repo, root)
        if change == "qualification":
            transport.long_profile_qualified = lambda *args: False
        elif change == "lease":
            lease.release()
        elif change == "budget":
            service._budget = wait.support._FakeBudget(False)
        else:
            prepared = replace(prepared, request_wire=prepared.request_wire + b" ")
        with pytest.raises(StateStoreError):
            claim_long(service, eid, prepared)
        assert wait._inventory(repo, root) == before
        assert repo.get_distillation_execution(eid).invocation_count == 0
        assert transport.calls == 0
    finally:
        lease.release()


def test_long_claim_cannot_promote_an_old_wait_or_cancelled_attempt(tmp_path):
    from youtube_intel.long_distillation_execution import claim_long, rebuild_long
    from youtube_intel.state import StateStoreError

    repo, root, sid, vid, service, _transport, lease = ready_fixture(tmp_path)
    try:
        old = service.reserve_distillation_execution(source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="old-wait")
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, old.execution_id).prepared
        before = wait._inventory(repo, root)
        with pytest.raises(StateStoreError):
            claim_long(service, old.execution_id, prepared)
        assert wait._inventory(repo, root) == before
        repo.cancel_waiting_model_execution(old.execution_id, video_id=vid, now=wait.NOW)
        before = wait._inventory(repo, root)
        with pytest.raises(StateStoreError):
            claim_long(service, old.execution_id, prepared)
        assert wait._inventory(repo, root) == before
        assert repo.get_distillation_execution(old.execution_id).status == "CANCELLED"
    finally:
        lease.release()


def test_long_claim_cas_is_single_invocation_even_with_two_fixture_ready_contenders(tmp_path):
    import threading

    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        reserve_pending,
    )
    from youtube_intel.state import StateStoreError

    repo, _root, sid, vid, service, transport, lease = ready_fixture(tmp_path)
    try:
        eid = reserve_pending(service, source_id=sid, video_id=vid,
            evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="race")
        with repo._connect() as connection:
            prepared = rebuild_long(repo, connection, eid).prepared
        # ENGINEERING_ONLY readiness seam isolates the database CAS race. Actual
        # native session thread/lease checks are separate mandatory negatives.
        transport.armed_long_for_claim = lambda *args: True
        barrier = threading.Barrier(2)
        claimed, rejected = [], []
        def contender():
            barrier.wait(timeout=5)
            try:
                claimed.append(claim_long(service, eid, prepared))
            except StateStoreError as error:
                rejected.append(str(error))
        threads = [threading.Thread(target=contender) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        assert not any(thread.is_alive() for thread in threads)
        assert len(claimed) == len(rejected) == 1
        assert repo.get_distillation_execution(eid).invocation_count == 1
        with pytest.raises(StateStoreError):
            claim_long(service, eid, prepared)
        assert transport.calls == 0
    finally:
        lease.release()
