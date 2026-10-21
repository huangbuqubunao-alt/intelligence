"""Machine selection is explicit configuration, never model qualification."""

from __future__ import annotations

import json

import pytest
from conftest import _load_module

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_intelligence_settings import (
    CANDIDATE_ID,
    LocalIntelligenceSettings,
    SettingsRejected,
)

long = _load_module("test_long_input_wait_lifecycle")


def setup(tmp_path):
    repo, data, _sid, _vid, _service, _app, _transport = long.workspace(tmp_path)
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    settings = LocalIntelligenceSettings(backup, probe=lambda _candidate: "READY")
    settings.bind_actual(
        {"provider": "ollama", "model": "qwen3:8b", "profile_id": None},
        "sha256:" + "0" * 64,
    )
    return repo, data, backup, settings


def test_save_apply_restart_reads_choice_without_touching_data_or_fast_config(tmp_path):
    repo, data, backup, settings = setup(tmp_path)
    before = long._inventory(repo, data)
    status = settings.status()
    assert status["status"] == "NOT_CONFIGURED"
    assert settings.apply(CANDIDATE_ID, status["etag"])["status"] == "APPLYING"
    assert backup.restart_requested
    with settings.admission() as allowed:
        assert not allowed
    reboot = LocalIntelligenceSettings(
        BackupRestoreService(database=repo._database_path, data_root=data),
        probe=lambda _candidate: "READY",
    )
    assert reboot.selected()
    reboot.bind_actual(
        {"provider": "ollama", "model": reboot.candidate.model, "profile_id": None},
        reboot.candidate.model_digest,
    )
    assert reboot.status()["status"] == "APPLIED"
    with reboot.admission() as allowed:
        assert allowed
    with settings.admission() as allowed:
        assert not allowed  # stale runtime after another process applied
    assert long._inventory(repo, data) == before


def test_cas_invalid_repair_unavailable_and_active_work_do_not_overwrite(tmp_path):
    _repo, _data, backup, settings = setup(tmp_path)
    with backup.background_work() as admitted:
        assert admitted
        with pytest.raises(SettingsRejected, match="CONFIGURATION_BUSY"):
            settings.apply(CANDIDATE_ID, settings.status()["etag"])
    settings.root.mkdir(exist_ok=True)
    settings.path.write_bytes(b"broken")
    status = settings.status()
    assert status["status"] == "INVALID"
    with pytest.raises(SettingsRejected, match="CONFIGURATION_CONFLICT"):
        settings.apply(CANDIDATE_ID, "0" * 64)
    assert settings.path.read_bytes() == b"broken"
    settings.probe = lambda _candidate: "NOT_INSTALLED"
    with pytest.raises(SettingsRejected, match="MODEL_NOT_READY"):
        settings.apply(CANDIDATE_ID, status["etag"])
    assert settings.path.read_bytes() == b"broken"
    settings.probe = lambda _candidate: "READY"
    settings.apply(CANDIDATE_ID, status["etag"])
    assert json.loads(settings.path.read_bytes())["candidate_id"] == CANDIDATE_ID


@pytest.mark.parametrize(
    "runtime,selected,expected",
    [
        ("0.40.6", "current", "READY"),
        ("0.40.6", "old", "RUNTIME_MISMATCH"),
        ("0.40.1", "old", "READY"),
        ("0.40.7", "current", "RUNTIME_MISMATCH"),
    ],
)
def test_catalog_metadata_matches_each_explicit_runtime(runtime, selected, expected):
    from youtube_intel.local_intelligence_catalog import CATALOG
    from youtube_intel.model_settings import ModelSettingsService

    candidate = CATALOG[1 if selected == "current" else 0]
    service = ModelSettingsService(
        object(),
        tags_fetch=lambda: {
            "models": [{"name": candidate.model, "digest": candidate.model_digest}]
        },
        version_fetch=lambda: {"version": runtime},
    )
    assert service.fixed_local_identity(candidate) == expected


def _reboot(repo, data, candidate, *, ready=True):
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    service = LocalIntelligenceSettings(
        backup,
        probe=lambda item: (
            "READY" if ready and item == candidate else "RUNTIME_MISMATCH"
        ),
    )
    service.bind_actual(
        {"provider": "ollama", "model": candidate.model, "profile_id": None},
        candidate.model_digest,
    )
    return backup, service


@pytest.mark.parametrize("candidate_index", [0, 1])
def test_catalog_choice_requires_explicit_restart_and_preserves_every_table(
    tmp_path, candidate_index
):
    from youtube_intel.local_intelligence_catalog import CATALOG

    repo, data, backup, settings = setup(tmp_path)
    before = long._inventory(repo, data)
    candidate = CATALOG[candidate_index]
    settings.probe = lambda item: "READY" if item == candidate else "RUNTIME_MISMATCH"
    result = settings.apply(candidate.candidate_id, settings.status()["etag"])
    assert result["status"] == "APPLYING"
    assert result["actual_route"]["model"] == "qwen3:8b"
    assert not backup.background_allowed
    _, new = _reboot(repo, data, candidate)
    assert new.status()["status"] == "APPLIED"
    assert new.status()["selected_candidate_id"] == candidate.candidate_id
    assert new.admission_allowed() and not settings.admission_allowed()
    assert all(
        c["qualification"] == "NOT_GRANTED_BY_SETTINGS"
        for c in new.status()["candidates"]
    )
    assert long._inventory(repo, data) == before


@pytest.mark.parametrize("count", [5, 21, 114])
def test_installed_current_choice_real_budget_ordinary_api_wait_and_cancel_without_dispatch(
    tmp_path, count, monkeypatch
):
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import PersonalizedDistillationService
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.local_intelligence_catalog import CATALOG
    from youtube_intel.orchestration_service import ProductOrchestrationService
    from youtube_intel.runtime_composition import (
        ProductionDistillationBudget,
        build_production_local_distillation_transport,
    )

    repo, data, _sid, vid, old, _, _ = long.workspace(tmp_path, count)
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    candidate = CATALOG[1]
    settings = LocalIntelligenceSettings(
        backup, probe=lambda item: "READY" if item == candidate else "RUNTIME_MISMATCH"
    )
    settings.apply(candidate.candidate_id, settings.status()["etag"])
    backup, settings = _reboot(repo, data, candidate)
    transport = build_production_local_distillation_transport(
        LocalScoringSettings(
            model=candidate.model, expected_model_digest=candidate.model_digest
        )
    )
    calls = []

    def no_request(*args, **kwargs):
        calls.append((args, kwargs))
        pytest.fail("Unqualified selected model must never make a model request")

    monkeypatch.setattr(transport, "_request", no_request)
    service = PersonalizedDistillationService(
        repo,
        old._source_policy,
        transport,
        ProductionDistillationBudget(),
        now=lambda: long.NOW,
    )
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo, now=lambda: long.NOW),
        data_root=data,
        distillation_service=service,
        local_intelligence_settings=settings,
        backup_restore_service=backup,
        now=lambda: long.NOW,
    )
    status, payload = app.handle(
        "POST",
        f"/api/v1/videos/{vid}/intelligence",
        json.dumps({"command_id": "real-budget"}).encode(),
    )
    assert status == 202
    execution = repo.get_distillation_execution(payload["execution"]["execution_id"])
    assert execution.status == "WAITING_MODEL" and execution.invocation_count == 0
    assert execution.budget_state == "RUNTIME_BUDGET_ADMITTED"
    usage = repo.get_distillation_resource_usage(execution.execution_id)
    assert usage.actual_model is None and usage.actual_provider is None
    assert usage.input_tokens is None and usage.output_tokens is None
    assert repo.list_distillation_cards() == ()
    assert repo.list_distillation_resource_usage()[0].actual_model is None
    with repo._connect(read_only=True) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM long_distillation_completion_receipts"
            ).fetchone()[0]
            == 0
        )
    result = service.continue_reserved_distillation(execution.execution_id)
    assert result.status.value == "WAITING_MODEL"
    status, payload = app.handle(
        "POST",
        f"/api/v1/videos/{vid}/intelligence/cancel",
        json.dumps({"execution_id": execution.execution_id}).encode(),
    )
    assert status == 200 and payload["execution"]["status"] == "CANCELLED"
    assert calls == []


@pytest.mark.parametrize("count", [5, 21])
def test_wrong_model_action_returns_settings_guidance_without_creating_task(
    tmp_path, count
):
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import PersonalizedDistillationService
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    from youtube_intel.runtime_composition import (
        ProductionDistillationBudget,
        build_production_local_distillation_transport,
    )

    repo, data, _, vid, old, _, _ = long.workspace(tmp_path, count)
    service = PersonalizedDistillationService(
        repo,
        old._source_policy,
        build_production_local_distillation_transport(
            LocalScoringSettings(
                model="qwen3:8b", expected_model_digest="sha256:" + "0" * 64
            )
        ),
        ProductionDistillationBudget(),
        now=lambda: long.NOW,
    )
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=data,
        distillation_service=service,
    )
    before = long._inventory(repo, data)
    with pytest.raises(ApiError) as caught:
        app.handle(
            "POST",
            f"/api/v1/videos/{vid}/intelligence",
            b'{"command_id":"wrong-model"}',
        )
    assert caught.value.code == "MODEL_CONFIGURATION_REQUIRED"
    assert caught.value.status == 409
    assert long._inventory(repo, data) == before


@pytest.mark.parametrize(
    "installation",
    ["NOT_INSTALLED", "IDENTITY_MISMATCH", "RUNTIME_MISMATCH", "UNAVAILABLE"],
)
def test_unready_known_candidate_never_saves_or_restarts(tmp_path, installation):
    from youtube_intel.local_intelligence_catalog import CURRENT_CANDIDATE_ID

    _, _, backup, settings = setup(tmp_path)
    settings.probe = lambda _: installation
    with pytest.raises(SettingsRejected, match="MODEL_NOT_READY"):
        settings.apply(CURRENT_CANDIDATE_ID, settings.status()["etag"])
    assert not settings.path.exists() and not backup.restart_requested
    assert not (settings.root / "change.json").exists()


@pytest.mark.parametrize(
    "identity",
    ["unknown", "qwen3.5:9b-q4_K_M", "local-intelligence-qwen35-9b-ollama-0.40.7-v1"],
)
def test_unknown_candidate_cannot_write_config(tmp_path, identity):
    _, _, backup, settings = setup(tmp_path)
    with pytest.raises(SettingsRejected, match="MODEL_CANDIDATE_INVALID"):
        settings.apply(identity, settings.status()["etag"])
    assert not settings.path.exists() and not backup.restart_requested


def test_runtime_drift_requires_explicit_new_catalog_selection(tmp_path):
    from youtube_intel.local_intelligence_catalog import CATALOG

    repo, data, _, settings = setup(tmp_path)
    settings.apply(CATALOG[0].candidate_id, settings.status()["etag"])
    _, current = _reboot(repo, data, CATALOG[0], ready=False)
    assert current.status()["status"] == "ROUTE_MISMATCH"
    assert current.status()["selected_candidate_id"] == CATALOG[0].candidate_id
    assert not current.admission_allowed()
    current.probe = lambda candidate: (
        "READY" if candidate == CATALOG[1] else "RUNTIME_MISMATCH"
    )
    current.apply(CATALOG[1].candidate_id, current.status()["etag"])
    _, restarted = _reboot(repo, data, CATALOG[1])
    assert restarted.status()["status"] == "APPLIED"


def test_apply_idempotent_ack_lost_replay_and_cas_conflict(tmp_path):
    repo, data, _, settings = setup(tmp_path)
    token = settings.status()["etag"]
    settings.apply(CANDIDATE_ID, token)
    raw = settings.path.read_bytes()
    assert settings.apply(CANDIDATE_ID, token)["status"] == "APPLYING"
    assert settings.path.read_bytes() == raw
    _, current = _reboot(repo, data, settings.candidate)
    assert current.apply(CANDIDATE_ID, current.status()["etag"])["status"] == "APPLIED"
    assert settings.path.read_bytes() == raw
    with pytest.raises(SettingsRejected, match="CONFIGURATION_CONFLICT"):
        current.apply(CANDIDATE_ID, token)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "directory", "oversize"])
def test_unsafe_config_identity_is_not_overwritten(tmp_path, kind):
    _, _, backup, settings = setup(tmp_path)
    settings.root.mkdir(exist_ok=True)
    external = tmp_path / "untouched"
    external.write_bytes(b"private bytes never exported")
    if kind == "symlink":
        settings.path.symlink_to(external)
    elif kind == "hardlink":
        import os

        os.link(external, settings.path)
    elif kind == "directory":
        settings.path.mkdir()
    else:
        settings.path.write_bytes(b"x" * 16385)
    assert settings.status()["status"] == "INVALID"
    with pytest.raises(SettingsRejected, match="CONFIGURATION_APPLY_FAILED"):
        settings.apply(CANDIDATE_ID, "0" * 64)
    assert external.read_bytes() == b"private bytes never exported"
    assert not backup.restart_requested


@pytest.mark.parametrize("point", ["before-promotion", "after-promotion"])
def test_failed_promotion_restores_old_valid_metadata_and_never_reports_success(
    tmp_path, monkeypatch, point
):
    repo, data, _, settings = setup(tmp_path)
    settings.apply(CANDIDATE_ID, settings.status()["etag"])
    _, settings = _reboot(repo, data, settings.candidate)
    before = settings.path.read_bytes()
    original = settings._write
    fired = False

    def write(name, raw):
        nonlocal fired
        if name == "model.json" and not fired:
            fired = True
            if point == "after-promotion":
                original(name, raw)
            raise OSError("controlled fsync/promotion failure")
        original(name, raw)

    monkeypatch.setattr(settings, "_write", write)
    from youtube_intel.local_intelligence_catalog import CURRENT_CANDIDATE_ID

    settings.probe = lambda _: "READY"
    with pytest.raises(SettingsRejected, match="CONFIGURATION_APPLY_FAILED"):
        settings.apply(CURRENT_CANDIDATE_ID, settings.status()["etag"])
    assert settings.path.read_bytes() == before
    assert not (settings.root / "change.json").exists()
    assert not settings.backup.restart_requested


def test_real_composition_cached_app_config_reloads_only_intelligence_choice(
    tmp_path, monkeypatch
):
    import youtube_intel.runtime_composition as composition
    from youtube_intel.config import load_app_config
    from youtube_intel.local_intelligence_catalog import CATALOG
    from youtube_intel.runtime_composition import build_local_source_run_runtime

    helpers = _load_module("test_runtime_composition")
    project = helpers._project(tmp_path)
    candidate = CATALOG[1]
    monkeypatch.setattr(
        composition,
        "local_models",
        lambda _: {
            "models": [{"name": candidate.model, "digest": candidate.model_digest}]
        },
    )
    monkeypatch.setattr(
        composition, "local_runtime_version", lambda _: {"version": candidate.runtime}
    )

    class NoCredentials:
        def get(self):
            return None

    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )
    yaml = (project / "config/settings.yaml").read_bytes()
    first = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=project / "gui.sqlite3",
        credential_store=NoCredentials(),
    )
    assert (
        first.application._distillation_service.capability_binding()["model"]
        == "qwen3:8b"
    )
    code, payload = first.application.handle(
        "GET", "/api/v1/settings/local-intelligence"
    )
    assert code == 200
    code, payload = first.application.handle(
        "PUT",
        "/api/v1/settings/local-intelligence",
        json.dumps(
            {
                "candidate_id": candidate.candidate_id,
                "expected_etag": payload["local_intelligence"]["etag"],
            }
        ).encode(),
    )
    assert code == 202 and payload["runtime_restart_required"] is True
    assert first.backup_restore.restart_requested
    first.worker.stop()
    second = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=project / "gui.sqlite3",
        credential_store=NoCredentials(),
    )
    actual = second.application.handle("GET", "/api/v1/settings/local-intelligence")[1][
        "local_intelligence"
    ]
    assert (
        actual["status"] == "APPLIED"
        and actual["actual_route"]["model"] == candidate.model
    )
    assert actual["actual_route"]["profile_id"] is None
    assert config.settings.local_scoring.model == "qwen3:8b"
    assert second.runtime._config.settings.local_scoring.model == "qwen3:8b"
    assert (project / "config/settings.yaml").read_bytes() == yaml
    assert (
        not first.backup_restore.background_allowed
        and second.backup_restore.background_allowed
    )


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/videos/example/intelligence",
        "/api/v1/videos/example/intelligence/continue",
        "/api/v1/videos/example/cloud-intelligence/review",
        "/api/v1/videos/example/cloud-intelligence/confirm",
        "/api/v1/sources/check-stale",
        "/api/v1/sources/example/check",
    ],
)
def test_pending_apply_blocks_every_manual_producer_before_route_dispatch(
    tmp_path, route
):
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repo, data, backup, settings = setup(tmp_path)
    settings.apply(CANDIDATE_ID, settings.status()["etag"])
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=data,
        local_intelligence_settings=settings,
        backup_restore_service=backup,
    )
    before = long._inventory(repo, data)
    with pytest.raises(ApiError) as caught:
        app.handle("POST", route, b"{}")
    assert caught.value.code == "CONFIGURATION_APPLYING"
    assert long._inventory(repo, data) == before


def test_existing_wait_blocks_apply_until_normal_cancel_and_history_survives_restore(
    tmp_path,
):
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.local_intelligence_catalog import CATALOG
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repo, data, sid, vid, service, _, _ = long.workspace(tmp_path, 21)
    reserved = service.reserve_distillation_execution(
        source_id=sid,
        video_id=vid,
        evidence_ids=service.reservation_evidence_ids(vid),
        manual_command_id="old-history",
    )
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    settings = LocalIntelligenceSettings(backup, probe=lambda _: "READY")
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=data,
        distillation_service=service,
        local_intelligence_settings=settings,
        backup_restore_service=backup,
        now=lambda: long.NOW,
    )
    with pytest.raises(SettingsRejected, match="CONFIGURATION_BUSY"):
        settings.apply(CATALOG[1].candidate_id, settings.status()["etag"])
    assert settings.status()["blocking_work"] == [
        {"video_id": vid, "status": "WAITING_MODEL"}
    ]
    app.handle(
        "POST",
        f"/api/v1/videos/{vid}/intelligence/cancel",
        json.dumps({"execution_id": reserved.execution_id}).encode(),
    )
    before = long._inventory(repo, data)
    settings.apply(CATALOG[1].candidate_id, settings.status()["etag"])
    backup, settings = _reboot(repo, data, CATALOG[1])
    sidecar = settings.path.read_bytes()
    assert repo.get_distillation_execution(reserved.execution_id).status == "CANCELLED"
    assert (
        repo.get_distillation_resource_usage(reserved.execution_id).status
        == "WAITING_MODEL"
    )
    assert (
        repo.get_distillation_resource_usage(reserved.execution_id).invocation_count
        == 0
    )
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    staged = backup.stage_restore(package.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert settings.path.read_bytes() == sidecar
    assert long._inventory(repo, data) == before
    assert repo.get_distillation_execution(reserved.execution_id).status == "CANCELLED"


def test_cross_process_shared_admission_blocks_apply(tmp_path):
    import subprocess
    import sys

    repo, _, _, settings = setup(tmp_path)
    script = "from pathlib import Path\nfrom youtube_intel.tracked_retry_context import store_lock\nimport sys\nwith store_lock(Path(sys.argv[1])):\n print('locked',flush=True)\n sys.stdin.readline()\n"
    child = subprocess.Popen(
        [sys.executable, "-c", script, str(repo._database_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(SettingsRejected, match="CONFIGURATION_BUSY"):
            settings.apply(CANDIDATE_ID, settings.status()["etag"])
        assert not settings.path.exists()
    finally:
        child.communicate("done\n", timeout=10)
    assert child.returncode == 0
    settings.apply(CANDIDATE_ID, settings.status()["etag"])


def test_invalid_old_bytes_not_copied_and_post_promotion_fault_stays_latched(
    tmp_path, monkeypatch
):
    repo, data, _, settings = setup(tmp_path)
    settings.path.write_bytes(b"unknown private text must not be journaled")
    token = settings.status()["etag"]
    original = settings._write

    def write(name, raw):
        original(name, raw)
        if name == "model.json":
            raise OSError("controlled fsync failure")

    monkeypatch.setattr(settings, "_write", write)
    with pytest.raises(SettingsRejected, match="CONFIGURATION_APPLY_FAILED"):
        settings.apply(CANDIDATE_ID, token)
    journal = (settings.root / "change.json").read_bytes()
    assert b"unknown private" not in journal
    assert json.loads(journal)["old"] is None
    assert json.loads(journal)["old_recoverable"] is False
    assert not settings.admission_allowed()
    _, current = _reboot(repo, data, settings.candidate)
    assert current.status()["status"] == "APPLIED" and current.admission_allowed()


def test_journal_pre_promotion_recovery_preserves_old_selection(tmp_path):
    repo, data, _, settings = setup(tmp_path)
    settings.apply(CANDIDATE_ID, settings.status()["etag"])
    journal = settings._journal()
    settings._write("model.json", journal["old_bytes"])
    reboot = LocalIntelligenceSettings(
        BackupRestoreService(database=repo._database_path, data_root=data),
        probe=lambda _: "READY",
    )
    assert not reboot.selected() and reboot.admission_allowed()
    assert not (settings.root / "change.json").exists()


def test_corrupt_config_and_journal_leave_settings_readable_and_explicit_cas_repairable(
    tmp_path,
):
    repo, data, _, settings = setup(tmp_path)
    settings.path.write_bytes(b'{"version":2,"version":2}')
    (settings.root / "change.json").write_bytes(b"invalid journal")
    current = LocalIntelligenceSettings(
        BackupRestoreService(database=repo._database_path, data_root=data),
        probe=lambda _: "READY",
    )
    status = current.status()
    assert status["status"] == "INVALID" and status["etag"] is not None
    assert not current.admission_allowed()
    assert current.apply(CANDIDATE_ID, status["etag"])["status"] == "APPLYING"
    _, reboot = _reboot(repo, data, current.candidate)
    assert reboot.status()["status"] == "APPLIED"


def test_legacy_cli_pending_apply_denies_before_provider_bootstrap(
    tmp_path, monkeypatch
):
    import youtube_intel.runtime_composition as composition
    from youtube_intel.cli import ExitCode, main
    from youtube_intel.config import load_app_config
    from youtube_intel.local_intelligence_catalog import CATALOG
    from youtube_intel.runtime_composition import build_local_source_run_runtime

    helpers = _load_module("test_runtime_composition")
    project = helpers._project(tmp_path)
    candidate = CATALOG[1]
    monkeypatch.setattr(
        composition,
        "local_models",
        lambda _: {
            "models": [{"name": candidate.model, "digest": candidate.model_digest}]
        },
    )
    monkeypatch.setattr(
        composition, "local_runtime_version", lambda _: {"version": candidate.runtime}
    )

    class NoCredentials:
        def get(self):
            return None

    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )
    runtime = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=project / "gui.sqlite3",
        credential_store=NoCredentials(),
    )
    settings = runtime.application._local_intelligence_settings
    settings.apply(candidate.candidate_id, settings.status()["etag"])
    # Pending journal must be checked before legacy runtime/provider creation.
    import youtube_intel.runtime as legacy

    monkeypatch.setattr(
        legacy,
        "create_runtime_operations",
        lambda *args: pytest.fail("pending apply dispatched CLI bootstrap"),
    )
    assert (
        main(["--project-root", str(project), "process"])
        == ExitCode.USAGE_OR_CONFIGURATION
    )


def test_http_ack_disconnect_still_stops_old_server_and_reboot_confirms_route(
    tmp_path, monkeypatch
):
    import threading
    from http.client import HTTPConnection, RemoteDisconnected

    from youtube_intel.local_api import LocalApiApplication, serve_loopback
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repo, data, backup, settings = setup(tmp_path)
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=data,
        local_intelligence_settings=settings,
        backup_restore_service=backup,
    )
    server = serve_loopback(app, port=0)
    original = server.RequestHandlerClass._send

    def dropped_ack(handler, status, payload):
        if payload.get("runtime_restart_required") is True:
            raise BrokenPipeError("controlled disconnected client after persistence")
        return original(handler, status, payload)

    monkeypatch.setattr(server.RequestHandlerClass, "_send", dropped_ack)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request(
            "PUT",
            "/api/v1/settings/local-intelligence",
            json.dumps(
                {
                    "candidate_id": CANDIDATE_ID,
                    "expected_etag": settings.status()["etag"],
                }
            ),
            headers={"X-YIA-Request": "local-ui"},
        )
        with pytest.raises(RemoteDisconnected):
            client.getresponse()
        thread.join(timeout=3)
        assert not thread.is_alive() and backup.restart_requested
        assert not settings.admission_allowed()
        _, reboot = _reboot(repo, data, settings.candidate)
        assert reboot.status()["status"] == "APPLIED"
        assert (
            not settings.admission_allowed()
        )  # old runtime stays stale after journal clears
    finally:
        client.close()
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=3)
        server.server_close()


def test_data_identity_separates_choices_and_shares_machine_lock_across_database_paths(
    tmp_path,
):
    from youtube_intel.backup_restore import machine_configuration_root
    from youtube_intel.tracked_retry_context import RetryConflict

    _, data, backup, settings = setup(tmp_path)
    inside = BackupRestoreService(
        database=machine_configuration_root(data) / ".admission", data_root=data
    )
    assert inside.machine_configuration_root == backup.machine_configuration_root
    assert (
        machine_configuration_root(data / ".." / data.name)
        == backup.machine_configuration_root
    )
    with inside.background_work() as allowed:
        assert allowed
        with pytest.raises(SettingsRejected, match="CONFIGURATION_BUSY"):
            settings.apply(CANDIDATE_ID, settings.status()["etag"])
    with backup.admission_lock(exclusive=True):
        with pytest.raises(RetryConflict):
            with inside.admission_lock():
                pytest.fail("machine lock admitted a different database path")
    other_data = tmp_path / "other-data"
    other_data.mkdir()
    other = LocalIntelligenceSettings(
        BackupRestoreService(database=tmp_path / "other.sqlite", data_root=other_data),
        probe=lambda _: "READY",
    )
    assert other.root != settings.root and not other.selected()
    assert not any("lock" in str(path.relative_to(data)) for path in data.rglob("*"))


@pytest.mark.parametrize(
    "version,digest,expected",
    [
        ("0.40.6", "wrong", "IDENTITY_MISMATCH"),
        ("0.40.7", "correct", "RUNTIME_MISMATCH"),
    ],
)
def test_catalog_does_not_accept_nearby_runtime_or_wrong_digest(
    version, digest, expected
):
    from youtube_intel.local_intelligence_catalog import CATALOG
    from youtube_intel.model_settings import ModelSettingsService

    candidate = CATALOG[1]
    service = ModelSettingsService(
        object(),
        tags_fetch=lambda: {
            "models": [
                {
                    "name": candidate.model,
                    "digest": candidate.model_digest
                    if digest == "correct"
                    else "sha256:" + "0" * 64,
                }
            ]
        },
        version_fetch=lambda: {"version": version},
    )
    assert service.fixed_local_identity(candidate) == expected


@pytest.mark.parametrize(
    "profile_id", ["local-grounding-qwen35-9b-thinking-v1", CANDIDATE_ID]
)
def test_current_installation_cannot_reinterpret_old_execution_runtime_or_enable_generation(
    profile_id, monkeypatch
):
    from youtube_intel.config import LocalScoringSettings
    from youtube_intel.distillation import (
        OllamaLocalDistillationTransport,
        bind_local_profile,
    )
    from youtube_intel.local_distillation_profile import resolve_profile
    from youtube_intel.local_intelligence_catalog import CATALOG

    support = _load_module("test_local_grounding_profile")
    profile = resolve_profile(profile_id)
    assert profile.runtime == "0.40.1" and CATALOG[1].runtime == "0.40.6"
    transport = OllamaLocalDistillationTransport(
        settings=LocalScoringSettings(
            model=profile.model, expected_model_digest=profile.model_digest
        ),
        local_profile_id=profile_id,
    )
    requests = []

    def metadata(path, *, method="POST", **kwargs):
        requests.append((path, method))
        assert method == "GET" and path == "/api/version"
        return {"version": "0.40.6"}

    monkeypatch.setattr(transport, "_request", metadata)
    assert not transport.available
    value = bind_local_profile(support._input(), profile_id)
    assert not transport.is_authorized_for_normal_production(value)
    assert not transport.is_authorized_for_qualification(value)
    assert not transport.prepare_execution(
        "old-runtime-proof-cannot-grant-authority", value, qualification=True
    )
    with pytest.raises(RuntimeError):
        transport.generate(value)
    assert requests == [("/api/version", "GET")]


def test_world_writable_scope_or_file_is_not_a_configuration_authority(tmp_path):
    import os

    _, _, _, settings = setup(tmp_path)
    settings.root.chmod(0o777)
    try:
        assert settings.status()["status"] == "INVALID"
        with pytest.raises(SettingsRejected, match="CONFIGURATION_APPLY_FAILED"):
            settings.apply(CANDIDATE_ID, "0" * 64)
    finally:
        settings.root.chmod(0o700)
    settings.path.write_bytes(b"invalid")
    settings.path.chmod(0o666)
    assert settings.status()["status"] == "INVALID"
    assert not settings.admission_allowed()
    assert os.stat(settings.path).st_mode & 0o022


def test_real_legacy_cli_dispatch_holds_shared_machine_barrier_against_gui_database(
    tmp_path,
):
    import subprocess
    import sys

    _, data, backup, settings = setup(tmp_path)
    _load_module("test_runtime_composition")._project(tmp_path)
    script = """from youtube_intel.cli import main
from youtube_intel.operations import CommandOutcome
import youtube_intel.runtime as runtime
import sys
class ControlledProviderOperations:
 def process(self, **kwargs):
  print('CLI_DISPATCH_ADMITTED', flush=True)
  sys.stdin.readline()
  return CommandOutcome()
def factory(config, root):
 assert config.settings.storage.data_dir == 'data'
 return ControlledProviderOperations()
runtime.create_runtime_operations = factory
raise SystemExit(main(['--project-root', sys.argv[1], 'process']))
"""
    child = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "CLI_DISPATCH_ADMITTED"
        with pytest.raises(SettingsRejected, match="CONFIGURATION_BUSY"):
            settings.apply(CANDIDATE_ID, settings.status()["etag"])
        assert backup.database.parent != data
        assert not list(data.rglob("*lock*"))
        assert not (data / ".local-intelligence-admission").exists()
    finally:
        _out, error = child.communicate("settle\n", timeout=10)
    assert child.returncode == 0, error
    assert not settings.path.exists()


@pytest.mark.parametrize(
    "state,provider",
    [
        ("PENDING", "ollama"),
        ("RUNNING", "ollama"),
        ("WAITING_BUDGET", "ollama"),
        ("WAITING_MODEL", "moonshot"),
    ],
)
def test_settings_apply_preserves_active_budget_and_cloud_execution_authorities(
    tmp_path, state, provider
):
    from youtube_intel.state import DistillationExecutionWrite

    repo, data, sid, vid, _, _, _ = long.workspace(tmp_path, 5)
    execution = DistillationExecutionWrite(
        execution_id="settings-blocker",
        source_id=sid,
        video_id=vid,
        reason="MANUAL_CONTENT:settings-blocker",
        use_case="PERSONALIZED_INTELLIGENCE",
        selected_provider=provider,
        selected_model="kimi-k2.6" if provider == "moonshot" else "qwen3:8b",
        output_language="en",
    )
    if state == "RUNNING":
        repo.begin_distillation_execution(execution, now=long.NOW)
    else:
        repo.reserve_distillation_execution(execution, now=long.NOW)
    if state in {"WAITING_BUDGET", "WAITING_MODEL"}:
        repo.finish_distillation_without_admission(
            execution_id=execution.execution_id,
            status=state,
            budget_state="RUNTIME_BUDGET_ADMITTED"
            if state == "WAITING_MODEL"
            else "BLOCKED",
            outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT"
            if state == "WAITING_MODEL"
            else "BUDGET_BLOCKED_BEFORE_TRANSPORT",
            invocation_count=0,
            actual_provider=None,
            actual_model=None,
            input_tokens=None,
            output_tokens=None,
            cost_microunits=None,
            duration_ms=None,
            now=long.NOW,
        )
    backup = BackupRestoreService(database=repo._database_path, data_root=data)
    settings = LocalIntelligenceSettings(backup, probe=lambda _: "READY")
    before = long._inventory(repo, data)
    with pytest.raises(SettingsRejected, match="CONFIGURATION_BUSY"):
        settings.apply(CANDIDATE_ID, settings.status()["etag"])
    assert not settings.path.exists() and not backup.restart_requested
    assert long._inventory(repo, data) == before


def test_native_backup_file_change_stream_stage_confirm_uses_ex_without_outer_shared_admission(
    tmp_path,
):
    from io import BytesIO

    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    repo, data, backup, settings = setup(tmp_path)
    settings.apply(CANDIDATE_ID, settings.status()["etag"])
    backup, settings = _reboot(repo, data, settings.candidate)
    sidecar = settings.path.read_bytes()
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo),
        data_root=data,
        local_intelligence_settings=settings,
        backup_restore_service=backup,
    )
    original = long._inventory(repo, data)
    package, _ = backup.backup_download(backup.create_backup().backup_id)
    wire = package.read_bytes()
    # Browser-native ZIP selection uses chooseBackup -> uploadZip -> this
    # streamed handler, never the Content native snapshot background worker.
    code, payload = app.handle_stream(
        "/api/v1/backup-restore/restore/stage", BytesIO(wire), len(wire)
    )
    assert code == 200
    code, payload = app.handle(
        "POST",
        "/api/v1/backup-restore/restore/confirm",
        json.dumps({"restore_id": payload["restore"]["restore_id"]}).encode(),
    )
    assert code == 202 and payload["restore"]["restart_required"] is True
    backup.recover_and_apply_pending_restore()
    assert not backup.restore_pending
    assert json.loads(backup.result_path.read_bytes())["state"] == "APPLIED"
    assert long._inventory(repo, data) == original
    assert settings.path.read_bytes() == sidecar
