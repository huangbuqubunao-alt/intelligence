"""Real API/SQLite/journal/Restore; only future model eligibility and wire are fake."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from conftest import _load_module

from youtube_intel import system_synthesis_persistence as synthesis
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.cloud_spending_policy import (
    CloudSpendingPolicy,
    SpendingPolicyRejected,
    money,
)
from youtube_intel.distillation import PersonalizedDistillationService
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService

runtime_tests = _load_module("test_synthesis_runtime")


def setup(tmp_path: Path, branch: str = "positive", *, qualified: bool = True, execution: bool = True) -> Any:
    repo, root, source, video, service, _, calls, credentials, clock = runtime_tests.setup(tmp_path, branch, qualified=qualified)
    backup = BackupRestoreService(database=repo._database_path, data_root=root)
    policy = CloudSpendingPolicy(repo, backup)
    service._synthesis_budget = None
    service._spending_policy = policy
    app = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: clock[0]),
        cloud_synthesis_service=service, cloud_spending_policy=policy,
        cloud_synthesis_qualified=qualified, cloud_execution_enabled=execution, cloud_credential_available=True,
        data_root=root, backup_restore_service=backup, now=lambda: clock[0])
    return repo, root, source, video, service, app, policy, backup, calls, clock


def configure(app: LocalApiApplication, **changes: Any) -> Any:
    state = app.handle("GET", "/api/v1/settings/cloud-spending-policy")[1]["spending_policy"]
    assert isinstance(state, dict) and isinstance(state["price"], dict)
    body = {"expected_revision": state["revision"], "enabled": True, "total_cny": "8", "per_request_cny": "1",
        "max_calls": 8, "accept_price_hash": state["price"]["price_hash"], "acknowledge": True, **changes}
    return app.handle("PUT", "/api/v1/settings/cloud-spending-policy", json.dumps(body).encode())[1]["spending_policy"]


def cny(value: int) -> str:
    return str(value // 1_000_000) + "." + str(value % 1_000_000).zfill(6)


@pytest.mark.parametrize("bad", [None, True, 0, -1, 1.5, "0", "-1", "NaN", "Infinity", "1e2", "1.0000001", "10001", " 1", "01"])
def test_money_requires_exact_positive_bounded_decimal_strings(bad: object) -> None:
    with pytest.raises(SpendingPolicyRejected):
        money(bad)
    assert money("0.000001") == 1 and money("1.234567") == 1_234_567


def test_configure_review_confirm_restart_deduplicates_database_and_journal(tmp_path: Path) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    absent = policy.status()
    assert absent["blocker"] == "CLOUD_SPENDING_POLICY_REQUIRED"
    assert not policy.anchor.exists() and not policy.root.exists()
    before = runtime_tests.support._inventory(repo, root)
    configured = configure(app)
    assert configured["held_requests"] == 0 and calls == []
    journal_bytes = policy.path.read_bytes()
    value = runtime_tests.review(app, video)
    assert runtime_tests.support._inventory(repo, root) == before
    assert policy.path.read_bytes() == journal_bytes and calls == []
    amount = value["spending"]["reserve_microunits"]
    assert value["readiness"]["can_confirm"] and amount > 0
    runtime_tests.confirm(app, video, value)
    assert len(calls) == 1
    restarted = CloudSpendingPolicy(repo, BackupRestoreService(database=repo._database_path, data_root=root))
    state = restarted.status()
    assert state["held_microunits"] == amount and state["held_requests"] == 1
    assert state["remaining_microunits"] == 8_000_000 - amount and state["actual_cost_status"] == "UNKNOWN"
    assert repo.get_distillation_execution(value["execution_id"]).invocation_count == 1
    with repo._connect() as c:
        assert c.execute("SELECT count(*) FROM system_synthesis_cloud_authorizations").fetchone()[0] == 1
        synthesis.verify_database(repo, c)
    with pytest.raises(ApiError):
        runtime_tests.confirm(app, video, value)
    assert len(calls) == 1 and restarted.status()["held_requests"] == 1


@pytest.mark.parametrize("extra", [{"price": 0}, {"eligibility": True}, {"consent_kind": "OWNER_QUALIFICATION"},
    {"endpoint": "https://invalid.example"}, {"synthesis_budget": {"max_calls": 100}}])
def test_policy_api_rejects_unknown_authority_fields_without_initializing_history(tmp_path: Path, extra: dict[str, Any]) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    with pytest.raises(ApiError) as error:
        configure(app, **extra)
    assert error.value.status == 422 and calls == [] and not policy.path.exists()


@pytest.mark.parametrize("changes", [{"total_cny": "0"}, {"per_request_cny": "-1"}, {"max_calls": True},
    {"max_calls": 0}, {"max_calls": 1001}, {"enabled": "yes"}, {"acknowledge": False},
    {"accept_price_hash": "0" * 64}, {"per_request_cny": "9"}])
def test_invalid_policy_cannot_be_saved(tmp_path: Path, changes: dict[str, Any]) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    with pytest.raises(ApiError):
        configure(app, **changes)
    assert not policy.path.exists() and calls == []


@pytest.mark.parametrize("gate", ["qualification", "execution"])
def test_saving_policy_does_not_open_qualification_or_qa_gate(tmp_path: Path, gate: str) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path,
        qualified=gate != "qualification", execution=gate != "execution")
    configure(app)
    value = runtime_tests.review(app, video)
    assert not value["readiness"]["can_confirm"]
    assert ("MODEL_UNQUALIFIED" if gate == "qualification" else "CLOUD_EXECUTION_DISABLED") in value["readiness"]["blockers"]
    with pytest.raises(ApiError):
        runtime_tests.confirm(app, video, value)
    assert calls == [] and policy.status()["held_requests"] == 0


@pytest.mark.parametrize("gate", ["per-call", "total", "count"])
def test_each_cap_refuses_before_another_wire_or_database_reservation(tmp_path: Path, gate: str) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path, "timeout")
    if gate == "per-call":
        configure(app, per_request_cny="0.000001")
        value = runtime_tests.review(app, video)
    else:
        amount = synthesis.loads(synthesis.prepare(repo, source_id=source, video_id=video,
            command_id="first", output_language="en", now=clock[0]).proof_json)["reserve_microunits"]
        configure(app, total_cny=cny(amount) if gate == "total" else "8",
            per_request_cny=cny(amount) if gate == "total" else "1", max_calls=1 if gate == "count" else 8)
        runtime_tests.confirm(app, video, runtime_tests.review(app, video, "first"))
        value = runtime_tests.review(app, video, "second")
    with pytest.raises(ApiError) as error:
        runtime_tests.confirm(app, video, value)
    assert error.value.code == {"per-call": "CLOUD_PER_REQUEST_CAP_EXCEEDED", "total": "CLOUD_BUDGET_EXHAUSTED", "count": "CLOUD_REQUEST_COUNT_EXHAUSTED"}[gate]
    assert len(calls) == (0 if gate == "per-call" else 1)
    assert repo.get_distillation_execution(value["execution_id"]) is None


def test_cas_edits_preserve_held_unknown_costs_and_require_new_review(tmp_path: Path) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path, "timeout")
    configure(app)
    before_change = runtime_tests.review(app, video)
    configure(app, total_cny="9")
    with pytest.raises(ApiError) as changed:
        runtime_tests.confirm(app, video, before_change)
    assert changed.value.code == "CLOUD_POLICY_CHANGED_REVIEW_REQUIRED" and calls == []
    value = runtime_tests.review(app, video)
    runtime_tests.confirm(app, video, value)
    held = policy.status()["held_microunits"]
    with pytest.raises(ApiError) as conflict:
        configure(app, expected_revision=1)
    assert conflict.value.code == "CLOUD_POLICY_CONFLICT"
    assert configure(app, enabled=False, total_cny="10")["held_microunits"] == held
    assert configure(app, total_cny="10")["held_requests"] == 1
    with pytest.raises(ApiError):
        configure(app, total_cny="0.000001", per_request_cny="0.000001")
    assert policy.status()["held_microunits"] == held and len(calls) == 1


def test_two_instances_concurrently_cannot_exceed_one_request_cap(tmp_path: Path) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    configure(app, max_calls=1)
    second_backup = BackupRestoreService(database=repo._database_path, data_root=root)
    second_policy = CloudSpendingPolicy(repo, second_backup)
    second_service = PersonalizedDistillationService(repo, service._source_policy, service._transport,
        service._budget, now=lambda: clock[0], output_language_for_video=lambda _: "en", cloud_spending_policy=second_policy)
    second_app = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: clock[0]),
        cloud_synthesis_service=second_service, cloud_spending_policy=second_policy,
        cloud_synthesis_qualified=True, cloud_credential_available=True, data_root=root, now=lambda: clock[0])
    commands = [(app, runtime_tests.review(app, video, "concurrent-one")),
        (second_app, runtime_tests.review(second_app, video, "concurrent-two"))]
    def submit(command: Any) -> str:
        try:
            runtime_tests.confirm(command[0], video, command[1])
            return "accepted"
        except ApiError:
            return "refused"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, commands)) == ["accepted", "refused"]
    assert len(calls) == 1 and policy.status()["held_requests"] == 1


def test_sync_preclaim_abort_and_crashed_reservation_have_distinct_durable_accounting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    configure(app)
    value = runtime_tests.review(app, video, "sync-failure")
    def fail(point: str) -> None:
        if point == "synthesis_after_consent":
            raise RuntimeError("synthetic synchronous fault, no network")
    monkeypatch.setattr(repo, "_inject_failure", fail)
    with pytest.raises(ApiError) as error:
        runtime_tests.confirm(app, video, value)
    assert error.value.code == "CLOUD_PRECLAIM_ABORTED"
    assert policy.status()["held_requests"] == 0 and policy.status()["consumed_execution_ids"] == 1
    assert repo.get_distillation_execution(value["execution_id"]).status == "CANCELLED"
    def crash(point: str) -> None:
        if point == "synthesis_after_proof":
            raise SystemExit("synthetic crash before a known claim outcome")
    monkeypatch.setattr(repo, "_inject_failure", crash)
    crashed = runtime_tests.review(app, video, "crashed-reservation")
    with pytest.raises(SystemExit):
        runtime_tests.confirm(app, video, crashed)
    assert calls == []
    assert CloudSpendingPolicy(repo, backup).status()["held_requests"] == 1
    assert policy.preview(synthesis.prepare(repo, source_id=source, video_id=video,
        command_id="crashed-reservation", output_language="en", now=clock[0]))["blocker"] == "CLOUD_EXECUTION_REPLAY_BLOCKED"


def test_restore_of_older_valid_backup_never_rewinds_holds_or_replays_later_attempt(tmp_path: Path) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    configure(app)
    original = runtime_tests.support._inventory(repo, root)
    download = backup.backup_download(backup.create_backup().backup_id)
    assert download is not None
    value = runtime_tests.review(app, video, "later-than-backup")
    runtime_tests.confirm(app, video, value)
    held = policy.status()["held_microunits"]
    configure(app, enabled=False)
    external = policy.path.read_bytes()
    preview = backup.stage_restore(download[0].read_bytes())
    backup.confirm_restore(preview.restore_id)
    backup.recover_and_apply_pending_restore()
    assert runtime_tests.support._inventory(repo, root) == original
    assert policy.path.read_bytes() == external and policy.status()["policy"]["enabled"] is False
    assert policy.status()["held_microunits"] == held and policy.status()["held_requests"] == 1
    assert repo.get_distillation_execution(value["execution_id"]) is None
    restarted_backup = BackupRestoreService(database=repo._database_path, data_root=root)
    policy = CloudSpendingPolicy(repo, restarted_backup)
    restarted_service = PersonalizedDistillationService(repo, service._source_policy, service._transport,
        service._budget, now=lambda: clock[0], output_language_for_video=lambda _: "en", cloud_spending_policy=policy)
    app = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: clock[0]),
        cloud_synthesis_service=restarted_service, cloud_spending_policy=policy, cloud_synthesis_qualified=True,
        cloud_credential_available=True, data_root=root, backup_restore_service=restarted_backup, now=lambda: clock[0])
    configure(app)
    replay = runtime_tests.review(app, video, "later-than-backup")
    assert replay["execution_id"] == value["execution_id"]
    with pytest.raises(ApiError) as refused:
        runtime_tests.confirm(app, video, replay)
    assert refused.value.code == "CLOUD_EXECUTION_REPLAY_BLOCKED" and len(calls) == 1
    # A distinct affirmative request can use only remaining external capacity;
    # the later charge absent from the restored DB still counts exactly once.
    next_request = runtime_tests.review(app, video, "new-after-restore")
    runtime_tests.confirm(app, video, next_request)
    assert policy.status()["held_requests"] == 2 and len(calls) == 2
    with repo._connect() as c:
        claims = c.execute("SELECT * FROM system_synthesis_cloud_authorizations").fetchall()
        assert len(claims) == 1 and claims[0]["prior_reserved_microunits"] == held and claims[0]["prior_calls"] == 1


@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink", "hardlink", "missing-anchor"])
def test_journal_damage_never_becomes_fresh_zero_history(tmp_path: Path, damage: str) -> None:
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(tmp_path)
    configure(app)
    value = runtime_tests.review(app, video)
    runtime_tests.confirm(app, video, value)
    if damage == "missing":
        policy.path.unlink()
    elif damage == "corrupt":
        policy.path.write_bytes(b'{"events":[]}')
    elif damage == "symlink":
        policy.path.unlink()
        outside = tmp_path / "unrelated-private-file"
        outside.write_text("synthetic private data must not be loaded")
        policy.path.symlink_to(outside)
    elif damage == "hardlink":
        (tmp_path / "another-link").hardlink_to(policy.path)
    else:
        policy.anchor.unlink()
    status = policy.status()
    assert status["blocker"].startswith("CLOUD_JOURNAL_") and status["held_microunits"] is None
    with pytest.raises(ApiError):
        configure(app, expected_revision=0)
    assert len(calls) == 1
    assert repo.get_distillation_execution(value["execution_id"]).invocation_count == 1


@pytest.mark.parametrize("damage", ["missing", "corrupt", "restore-to-new-owned-root"])
def test_actual_factory_keeps_library_and_backup_readable_when_financial_history_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    from youtube_intel.config import load_app_config
    from youtube_intel.runtime_composition import build_local_source_run_runtime

    project_support = _load_module("test_runtime_composition")
    qa_support = _load_module("test_qa_launch_isolation")
    project = project_support._project(tmp_path)
    repo, root, source, video, service, app, policy, backup, calls, clock = setup(project)
    configure(app)
    value = runtime_tests.review(app, video)
    _, result = runtime_tests.confirm(app, video, value)
    intelligence = result["execution"]["intelligence_id"]
    app.handle("POST", "/api/v1/saved-intelligence/save", json.dumps({"intelligence_id": intelligence}).encode())
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    def factory(at: Path) -> Any:
        return build_local_source_run_runtime(
            config=load_app_config(at / "config/channels.yaml", at / "config/settings.yaml"),
            project_root=at, database=at / "state.sqlite3", credential_store=qa_support.FakeStore(),
            bigmodel_credential_store=qa_support.FakeStore(), allow_environment_credentials=False,
            allow_cloud_execution=False, now=lambda: clock[0])
    if damage == "restore-to-new-owned-root":
        archive = backup.backup_download(backup.create_backup().backup_id)
        assert archive is not None
        target = tmp_path / "new-owned-project"
        target.mkdir()
        project_support._project(target)
        blank = factory(target)
        staged = blank.backup_restore.stage_restore(archive[0].read_bytes())
        blank.backup_restore.confirm_restore(staged.restore_id)
        runtime = factory(target)
    else:
        if damage == "missing":
            policy.path.unlink()
        else:
            policy.path.write_bytes(b"corrupt financial journal")
        runtime = factory(project)
    assert runtime.application.handle("GET", f"/api/v1/videos/{video}")[0] == 200
    assert runtime.application.handle("GET", f"/api/v1/videos/{video}/evidence")[0] == 200
    assert runtime.application.handle("GET", f"/api/v1/intelligence/{intelligence}")[1]["intelligence"]["trusted"]
    assert runtime.application.handle("GET", "/api/v1/saved-intelligence")[0] == 200
    assert runtime.backup_restore.readiness()["ready"]
    runtime.backup_restore.create_backup()
    state = runtime.application.handle("GET", "/api/v1/settings/cloud-spending-policy")[1]["spending_policy"]
    assert state["blocker"].startswith("CLOUD_JOURNAL_") and state["held_microunits"] is None
    forbidden: list[object] = []
    def wire(*args: object) -> None:
        forbidden.append(args)
        pytest.fail("closed factory dispatched a model")
    closed_service = runtime.application._cloud_synthesis_service
    monkeypatch.setattr(closed_service._transport, "_wire_transport", wire)
    review = runtime_tests.review(runtime.application, video, "closed-history")
    assert not review["readiness"]["can_confirm"]
    with pytest.raises(ValueError):
        closed_service.confirm_cloud_preview(video_id=video, execution_id=review["execution_id"], review_hash=review["review_hash"])
    assert forbidden == [] and len(calls) == 1
