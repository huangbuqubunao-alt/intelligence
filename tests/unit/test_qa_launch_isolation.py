"""QA startup must not inherit production credentials or paid execution gates."""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import threading
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import _load_module

from youtube_intel.local_api import ApiError
from youtube_intel.model_settings import (
    CredentialStoreError,
    MacOSKeychainCredentialStore,
    ModelSettingsService,
)
from youtube_intel.runtime_composition import build_local_source_run_runtime

native_get = MacOSKeychainCredentialStore.get


class FakeStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.secret: str | None = None
        self.fail = fail

    def get(self) -> str | None:
        if self.fail:
            raise CredentialStoreError()
        return self.secret

    def save(self, secret: str) -> None:
        self.secret = secret

    def delete(self) -> None:
        self.secret = None

    def __bool__(self) -> bool:
        # Explicit empty/falsy stores must still win over the production default.
        return False


@pytest.mark.parametrize("failed", [False, True])
def test_isolated_settings_never_fall_back_to_environment(
    monkeypatch: pytest.MonkeyPatch, failed: bool
) -> None:
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-unrelated-environment")
    store = FakeStore(fail=failed)
    settings = ModelSettingsService(store, allow_environment_credentials=False)
    assert settings.credential() == ""
    assert settings.credential_status() == {
        "configured": False, "source": "UNAVAILABLE" if failed else "NONE"
    }
    if not failed:
        settings.save_credential("synthetic-qa-only")
        assert settings.credential() == "synthetic-qa-only"
        settings.delete_credential()
        assert settings.credential() == ""
        assert settings.credential_status() == {"configured": False, "source": "NONE"}


def test_isolated_runtime_has_no_paid_cloud_gate_even_with_configured_fake_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from youtube_intel.config import load_app_config

    support = _load_module("test_runtime_composition")
    root = support._project(tmp_path)
    workspace = _load_module("test_long_input_wait_lifecycle").workspace(root, 2)
    source, video = workspace[2:4]
    config = load_app_config(root / "config/channels.yaml", root / "config/settings.yaml")
    store = FakeStore()
    store.save("synthetic-qa-only")
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-unrelated-environment")
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    runtime = build_local_source_run_runtime(
        config=config, project_root=root, database=root / "state.sqlite3",
        credential_store=store, bigmodel_credential_store=FakeStore(),
        allow_environment_credentials=False, allow_cloud_execution=False,
    )
    assert runtime.application._cloud_credential_available
    assert runtime.application._model_settings._store is store
    assert runtime.application._cloud_intelligence_qualified  # historical K2.6 fact unchanged
    assert not runtime.application._cloud_execution_enabled
    assert not runtime.cloud_distillation._transport._authorization.cloud_enabled
    # Refresh after saving a credential must not turn the QA spending gate on.
    runtime.application.handle("PUT", "/api/v1/settings/cloud-credential", b'{"credential":"synthetic-new-qa"}')
    assert runtime.application._cloud_intelligence_qualified
    assert not runtime.application._cloud_execution_enabled
    assert not runtime.application._refresh_cloud_distillation()._transport._authorization.cloud_enabled
    cloud = runtime.application._cloud_distillation_service
    wire_calls: list[object] = []
    def forbidden_wire(*args: object) -> None:
        wire_calls.append(args)
        pytest.fail("QA cloud gate dispatched paid transport")
    monkeypatch.setattr(cloud._transport, "_wire_transport", forbidden_wire)
    _, payload = runtime.application.handle("POST", f"/api/v1/videos/{video}/cloud-intelligence/review", b"{}")
    review = payload["review"]
    assert not review["readiness"]["can_confirm"]
    assert "CLOUD_EXECUTION_DISABLED" in review["readiness"]["blockers"]
    assert "MODEL_UNQUALIFIED" not in review["readiness"]["blockers"]
    _, settings = runtime.application.handle("GET", "/api/v1/settings")
    model = next(item for item in settings["providers"] if item["model"] == "kimi-k2.6")
    assert model["qualification_status"] == "QUALIFIED"
    assert model["production_eligible"] is False
    assert settings["cloud_execution_enabled"] is False
    body = json.dumps({"execution_id": review["execution_id"], "review_hash": review["review_hash"], "authorize": True}).encode()
    with runtime.repository._connect() as connection:
        before = tuple(connection.iterdump())
    with pytest.raises(ApiError, match="Cloud execution is disabled") as rejected:
        runtime.application.handle("POST", f"/api/v1/videos/{video}/cloud-intelligence/confirm", body)
    assert rejected.value.code == "CLOUD_EXECUTION_DISABLED"
    # Bypassing the UI and application flag still fails the immutable transport
    # authorization before consent, budget reservation or dispatch can commit.
    with pytest.raises(ValueError, match="model or credential is unavailable"):
        cloud.confirm_cloud_preview(video_id=video, execution_id=review["execution_id"], review_hash=review["review_hash"])
    with runtime.repository._connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert wire_calls == []
    assert source


def launcher() -> Any:
    path = Path(__file__).resolve().parents[2] / "scripts/validation/serve_user_readiness_candidate.py"
    specification = importlib.util.spec_from_file_location("qa_candidate_launcher", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def qa_repository(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "checkout"
    (repo / "config").mkdir(parents=True)
    example = Path(__file__).resolve().parents[2] / "config/settings.example.yaml"
    (repo / "config/settings.example.yaml").write_bytes(example.read_bytes())
    return repo, repo / ".var/user-readiness-candidate"


@pytest.mark.parametrize("provider", ["moonshot", "bigmodel"])
def test_fixed_qa_native_namespaces_never_query_production(provider: str, monkeypatch: pytest.MonkeyPatch) -> None:
    app = launcher()
    store = app.MacOSMoonshotQACredentialStore() if provider == "moonshot" else app.MacOSBigModelQACredentialStore()
    expected = (b"com.huangbuqubunao.intelligence.qa.kimi-public-20261029"
        if provider == "moonshot" else b"com.huangbuqubunao.intelligence.qa.zhipu-bigmodel")
    calls: list[tuple[bytes, bytes]] = []
    class Framework:
        def SecKeychainFindGenericPassword(self, _: object, sl: int, service: bytes,
            al: int, account: bytes, length: object, data: object, item: object) -> int:
            assert sl == len(expected) and al == len(b"api-key")
            calls.append((service, account))
            return -25300
        def SecKeychainAddGenericPassword(self, _: object, sl: int, service: bytes,
            al: int, account: bytes, length: int, raw: bytes, item: object) -> int:
            calls.append((service, account))
            assert raw == b"synthetic-qa-key"
            return 0
    framework = Framework()
    monkeypatch.setattr(store, "_libraries", lambda: (framework, framework))
    assert native_get(store) is None
    store.save("synthetic-qa-key")
    store.delete()
    assert calls == [(expected, b"api-key")] * 4


def test_candidate_config_uses_only_owned_paths_and_disabled_cloud(tmp_path: Path) -> None:
    repo, root = qa_repository(tmp_path)
    config = launcher().candidate_config(root, repository_root=repo)
    assert config.channels == ()
    assert not config.settings.cloud.enabled
    assert config.settings.intelligence.mode.value == "local-only"
    assert config.settings.storage.data_dir == "data"
    assert config.settings.storage.vault_root == str(root / "vault")
    assert not root.exists()  # configuration validation does not initialize state
    with pytest.raises(ValueError, match="dedicated candidate"):
        launcher().candidate_config(tmp_path / "formal-owner", repository_root=repo)
    assert not (tmp_path / "formal-owner").exists()


@pytest.mark.parametrize("link", [".var", "root", "state.sqlite3", "data", "vault", "logs"])
def test_candidate_refuses_symlink_escapes_before_composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link: str
) -> None:
    app = launcher()
    repo, root = qa_repository(tmp_path)
    owner = tmp_path / "formal-owner"
    owner.mkdir()
    sentinel = owner / "state.sqlite3"
    sentinel.write_bytes(b"synthetic-owner-database-do-not-open")
    if link == ".var":
        (repo / ".var").symlink_to(owner, target_is_directory=True)
    elif link == "root":
        root.parent.mkdir()
        root.symlink_to(owner, target_is_directory=True)
    else:
        root.mkdir(parents=True)
        (root / link).symlink_to(sentinel if link == "state.sqlite3" else owner)
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid QA path reached runtime/credential composition")
    monkeypatch.setattr(app, "build_local_source_run_runtime", forbidden)
    with pytest.raises(ValueError, match="(symbolic links|link to another data owner)"):
        app.serve_candidate(repository_root=repo)
    assert sentinel.read_bytes() == b"synthetic-owner-database-do-not-open"
    assert sorted(path.name for path in owner.iterdir()) == ["state.sqlite3"]


def test_candidate_refuses_hardlinked_database(tmp_path: Path) -> None:
    repo, root = qa_repository(tmp_path)
    root.mkdir(parents=True)
    owner = tmp_path / "owner.sqlite3"
    owner.write_bytes(b"synthetic-owner-data")
    os.link(owner, root / "state.sqlite3")
    with pytest.raises(ValueError, match="another data owner"):
        launcher().serve_candidate(repository_root=repo)
    assert owner.read_bytes() == b"synthetic-owner-data"
    assert not (root / "qa-launch.lock").exists()


def test_candidate_rejects_ports_and_remote_host_before_state_creation(tmp_path: Path) -> None:
    app = launcher()
    repo, root = qa_repository(tmp_path)
    for port in (0, 1023, 65536):
        with pytest.raises(ValueError, match="port"):
            app.serve_candidate(port=port, repository_root=repo)
    with pytest.raises(SystemExit) as rejected:
        app.main(["--host", "0.0.0.0"])
    assert rejected.value.code == 2
    assert not root.exists()


def test_candidate_retains_ownership_and_stops_worker_across_restore_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = launcher()
    repo, root = qa_repository(tmp_path)
    events: list[str] = []
    compositions: list[Any] = []
    def build(**kwargs: Any) -> Any:
        assert kwargs["database"] == root / "state.sqlite3"
        assert kwargs["project_root"] == root
        assert kwargs["allow_environment_credentials"] is False
        assert kwargs["allow_cloud_execution"] is False
        assert kwargs["credential_store"]._service == b"com.huangbuqubunao.intelligence.qa.kimi-public-20261029"
        assert kwargs["bigmodel_credential_store"]._service == b"com.huangbuqubunao.intelligence.qa.zhipu-bigmodel"
        assert not kwargs["config"].settings.cloud.enabled
        n = len(compositions)
        current = SimpleNamespace(
            application=SimpleNamespace(shutdown_native_import=lambda: events.append(f"native-stop{n}")),
            worker=SimpleNamespace(start=lambda: events.append(f"start{n}"), stop=lambda: events.append(f"stop{n}")),
            backup_restore=SimpleNamespace(restart_requested=n == 0),
        )
        compositions.append(current)
        return current
    def server(application: object, *, port: int) -> Any:
        n = len(compositions) - 1
        assert port == 6378
        def serve() -> None:
            events.append(f"serve{n}")
            # The owner lock survives the entire restore-restart boundary.
            with pytest.raises(ValueError, match="running owner"):
                app.serve_candidate(repository_root=repo)
        return SimpleNamespace(serve_forever=serve, server_close=lambda: events.append(f"close{n}"))
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    monkeypatch.setattr(app, "build_local_source_run_runtime", build)
    monkeypatch.setattr(app, "serve_loopback", server)
    app.serve_candidate(repository_root=repo)
    assert len(compositions) == 2
    assert events == ["start0", "serve0", "close0", "native-stop0", "stop0",
        "start1", "serve1", "close1", "native-stop1", "stop1"]
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())


def test_candidate_real_loopback_start_and_stop_with_test_stores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = launcher()
    repo, root = qa_repository(tmp_path)
    ready = threading.Event()
    servers: list[Any] = []
    errors: list[BaseException] = []
    real_server = app.serve_loopback
    def listen(application: object, *, port: int) -> Any:
        # Only the bind port is substituted; real handler, application,
        # composition and worker lifecycle run against the isolated database.
        server = real_server(application, port=0)
        servers.append(server)
        ready.set()
        return server
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-owner-environment-must-not-appear")
    monkeypatch.setattr(app, "MacOSMoonshotQACredentialStore", FakeStore)
    monkeypatch.setattr(app, "MacOSBigModelQACredentialStore", FakeStore)
    monkeypatch.setattr(app, "serve_loopback", listen)
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    def serve() -> None:
        try:
            app.serve_candidate(repository_root=repo)
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        assert ready.wait(10), errors
        server = servers[0]
        assert server.server_address[0] == "127.0.0.1"
        connection = HTTPConnection(*server.server_address, timeout=5)
        try:
            connection.request("GET", "/api/v1/settings")
            response = connection.getresponse()
            body = response.read()
            assert response.status == 200
            assert json.loads(body)["cloud_credential"] == {"configured": False, "source": "NONE"}
            assert b"synthetic-owner-environment" not in body
        finally:
            connection.close()
    finally:
        if servers:
            servers[0].shutdown()
        thread.join(10)
    assert not thread.is_alive() and errors == []
    assert (root / "state.sqlite3").is_file()
