"""ENGINEERING_ONLY never-invoked long restart recovery, not model eligibility."""
import pytest
from conftest import _load_module

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_model_capacity import ApplicationHeavyLease
from youtube_intel.long_distillation_execution import reserve_pending
from youtube_intel.state import SQLiteStateRepository

life = _load_module("test_long_completion_lifecycle")


def pending(tmp_path, *, full=False):
    repo, root, sid, vid, service, transport, lease = life.ready_fixture(tmp_path, full=full)
    eid = reserve_pending(service, source_id=sid, video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid), manual_command_id="crash-before-claim")
    lease.release()
    return repo, root, sid, vid, service, transport, eid


def test_restart_defers_only_unclaimed_then_cancel_and_full_restore_never_revives(tmp_path):
    from youtube_intel.long_distillation_execution import recover_pre_dispatch_long
    repo, root, sid, vid, service, transport, eid = pending(tmp_path, full=True)
    backup = BackupRestoreService(database=repo._database_path, data_root=root)
    assert not backup.readiness()["ready"]
    assert recover_pre_dispatch_long(service, backup_restore=backup) == 1
    first = life.wait._inventory(repo, root)
    assert recover_pre_dispatch_long(service, backup_restore=backup) == 0
    assert life.wait._inventory(repo, root) == first
    assert repo.get_distillation_execution(eid).status == "WAITING_MODEL"
    repo.cancel_waiting_model_execution(eid, video_id=vid, now=life.wait.NOW)
    assert backup.readiness()["ready"]
    before = life.wait._inventory(repo, root)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    staged = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert life.wait._inventory(repo, root) == before
    reboot = SQLiteStateRepository(repo._database_path)
    reboot.bind_source_storage(root)
    service._repository = reboot
    assert recover_pre_dispatch_long(service) == 0
    assert reboot.get_distillation_execution(eid).status == "CANCELLED"
    assert transport.calls == 0


@pytest.mark.parametrize("damage", ["active-lease", "claimed", "budget"])
def test_restart_respects_real_heavy_lease_unknown_claim_and_existing_budget_rules(tmp_path, damage):
    from youtube_intel.long_distillation_execution import (
        claim_long,
        rebuild_long,
        recover_pre_dispatch_long,
    )
    repo, root, sid, vid, service, transport, eid = pending(tmp_path)
    lease = ApplicationHeavyLease(repository=repo, data_root=root)
    if damage == "active-lease":
        assert lease.acquire()
    elif damage == "claimed":
        assert lease.acquire()
        transport.armed_long_for_claim = lambda *args: lease.valid()
        with repo._connect() as c:
            prepared = rebuild_long(repo, c, eid).prepared
        claim_long(service, eid, prepared)
        lease.release()
    else:
        service._budget = life.wait.support._FakeBudget(False)
    before = life.wait._inventory(repo, root)
    try:
        count = recover_pre_dispatch_long(service)
    finally:
        lease.release()
    if damage == "budget":
        assert count == 1 and repo.get_distillation_execution(eid).status == "WAITING_BUDGET"
        assert not repo.can_cancel_waiting_model_execution(eid)
    else:
        assert count == 0 and life.wait._inventory(repo, root) == before
    assert transport.calls == 0


def test_safe_deferral_uses_intact_frozen_history_after_current_policy_refresh(tmp_path):
    from youtube_intel.long_distillation_execution import recover_pre_dispatch_long
    from youtube_intel.source_policy import DistillationStyle
    repo, root, sid, vid, service, transport, eid = pending(tmp_path)
    service._source_policy.update_global(command_id="new-policy", initial_history_count=5,
        per_run_max_new_videos=3, focus_rules=("New focus",), ignore_rules=(), distillation_style=DistillationStyle.BALANCED)
    assert recover_pre_dispatch_long(service) == 1
    assert repo.get_distillation_execution(eid).status == "WAITING_MODEL"
    assert repo.can_cancel_waiting_model_execution(eid)
    assert transport.calls == 0


def test_corrupt_retained_source_remains_fail_closed_without_a_wait_or_usage(tmp_path):
    from youtube_intel.long_distillation_execution import recover_pre_dispatch_long
    repo, root, sid, vid, service, transport, eid = pending(tmp_path)
    (root / "canonical.txt").write_bytes(b"corrupt authentic source fixture")
    before = life.wait._inventory(repo, root)
    assert recover_pre_dispatch_long(service) == 0
    assert life.wait._inventory(repo, root) == before
    assert not BackupRestoreService(database=repo._database_path, data_root=root).readiness()["ready"]
    assert transport.calls == 0


@pytest.mark.parametrize("attempt", range(3))
def test_recovery_and_claim_transaction_have_one_winner(tmp_path, monkeypatch, attempt):
    import threading

    from youtube_intel import long_distillation_execution as execution
    from youtube_intel.state import StateStoreError
    repo, root, sid, vid, service, transport, eid = pending(tmp_path)
    with repo._connect() as c:
        prepared = execution.rebuild_long(repo, c, eid).prepared
    # ENGINEERING_ONLY bypasses native readiness to isolate SQLite claim vs
    # recovery CAS. Real lease exclusion is separately tested above.
    transport.armed_long_for_claim = lambda *args: True
    barrier = threading.Barrier(2)
    defer = execution.defer_long
    def simultaneous(*args, **kwargs):
        barrier.wait(timeout=10)
        return defer(*args, **kwargs)
    monkeypatch.setattr(execution, "defer_long", simultaneous)
    claimed, errors, recovered = [], [], []
    def recover():
        recovered.append(execution.recover_pre_dispatch_long(service))
    def claim():
        barrier.wait(timeout=10)
        try:
            claimed.append(execution.claim_long(service, eid, prepared))
        except StateStoreError as error:
            errors.append(str(error))
    threads = [threading.Thread(target=recover), threading.Thread(target=claim)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(15)
    assert not any(thread.is_alive() for thread in threads)
    assert recovered == [1 - len(claimed)]
    record = repo.get_distillation_execution(eid)
    assert record.invocation_count == len(claimed)
    assert record.status == ("PENDING" if claimed else "WAITING_MODEL")
    assert len(claimed) + len(errors) == 1
    assert transport.calls == 0


def test_normal_factory_recovers_crashed_pending_without_loading_or_generating(tmp_path, monkeypatch):
    from youtube_intel.config import load_app_config
    from youtube_intel.distillation import OllamaLocalDistillationTransport
    from youtube_intel.local_distillation_profile import (
        CURRENT_RUNTIME_PROFILE_ID,
        resolve_profile,
    )
    from youtube_intel.runtime_composition import build_local_source_run_runtime
    repo, root, sid, vid, service, transport, eid = pending(tmp_path)
    helpers = _load_module("test_runtime_composition")
    profile = resolve_profile(CURRENT_RUNTIME_PROFILE_ID)
    helpers._project(tmp_path, model=profile.model, digest=profile.model_digest)
    monkeypatch.setattr(OllamaLocalDistillationTransport, "available", property(lambda _: False))
    monkeypatch.setattr(OllamaLocalDistillationTransport, "_request", lambda *a, **k: pytest.fail("startup recovery must not make provider IO"))
    class NoCredentials:
        def get(self): return None
    runtime = build_local_source_run_runtime(config=load_app_config(tmp_path / "config/channels.yaml", tmp_path / "config/settings.yaml"),
        project_root=tmp_path, database=repo._database_path, credential_store=NoCredentials())
    assert runtime.repository.get_distillation_execution(eid).status == "WAITING_MODEL"
    assert runtime.repository.can_cancel_waiting_model_execution(eid)
    assert transport.calls == 0
