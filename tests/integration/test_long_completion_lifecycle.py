"""ENGINEERING_ONLY long completion lifecycle; no real qualification or models."""

import json

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
