"""Configuration-only fake stores: never system credentials or network."""
import json
import threading
from datetime import UTC, datetime
from http.client import HTTPConnection

import pytest

from youtube_intel.local_api import ApiError, LocalApiApplication, serve_loopback
from youtube_intel.model_settings import (
    BigModelCredentialSettings,
    CredentialStoreError,
    MacOSBigModelCredentialStore,
    MacOSBigModelQACredentialStore,
    MacOSKeychainCredentialStore,
    ModelSettingsService,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository

PATH = "/api/v1/settings/bigmodel-credential"


class MemoryStore:
    def __init__(self):
        self.secret = None
        self.calls = []

    def get(self):
        self.calls.append("get")
        return self.secret

    def save(self, secret):
        self.calls.append("save")
        self.secret = secret

    def delete(self):
        self.calls.append("delete")
        self.secret = None


class ForbiddenStore:
    def get(self):
        raise AssertionError("Unrelated credential read")

    def save(self, secret):
        raise AssertionError("Unrelated credential write")

    def delete(self):
        raise AssertionError("Unrelated credential delete")


@pytest.fixture
def setup(tmp_path):
    repo = SQLiteStateRepository(tmp_path / "isolated.sqlite3")
    repo.initialize(now=datetime.now(UTC))
    store = MemoryStore()
    def forbidden():
        raise AssertionError("Old factory/model must not run")
    app = LocalApiApplication(repo, ProductOrchestrationService(repo),
        model_settings=ModelSettingsService(ForbiddenStore()),
        bigmodel_settings=BigModelCredentialSettings(store),
        refresh_cloud_distillation=forbidden)
    return app, store


def test_namespaces_are_finite_distinct_and_lazy(monkeypatch):
    def forbidden(self):
        raise AssertionError("No native access on construction")
    monkeypatch.setattr(MacOSKeychainCredentialStore, "_libraries", forbidden)
    stores = [MacOSKeychainCredentialStore(), MacOSBigModelCredentialStore(), MacOSBigModelQACredentialStore()]
    assert [s._service for s in stores] == [
        b"com.huangbuqubunao.intelligence.moonshot",
        b"com.huangbuqubunao.intelligence.zhipu-bigmodel",
        b"com.huangbuqubunao.intelligence.qa.zhipu-bigmodel"]
    assert all(s._account == b"api-key" for s in stores)
    with pytest.raises(TypeError):
        MacOSBigModelCredentialStore(service="arbitrary")


def test_new_provider_configuration_never_touches_old_store_or_grants_authority(setup, monkeypatch):
    app, store = setup
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-unrelated-env")
    before = "\n".join(app._repository._connect().iterdump())
    status, result = app.handle("GET", PATH)
    assert status == 200
    assert result == {"provider": "zhipu_bigmodel", "model": "glm-4.7-flash", "configured": False,
        "source": "NONE", "qualification": "NOT_VERIFIED", "budget": "CLOSED"}
    secret = "synthetic-bigmodel-only"
    status, result = app.handle("PUT", PATH, json.dumps({"credential": secret}).encode())
    assert status == 200 and result["configured"] is True and result["source"] == "KEYCHAIN"
    assert result["qualification"] == "NOT_VERIFIED" and result["budget"] == "CLOSED"
    assert store.calls == ["get", "save", "get"]
    assert secret not in json.dumps(result)
    assert not app._cloud_credential_available and not app._cloud_intelligence_qualified
    app.handle("POST", PATH + "/delete", b'{"confirm":"DELETE"}')
    app.handle("POST", PATH + "/delete", b'{"confirm":"DELETE"}')
    assert store.secret is None
    assert "\n".join(app._repository._connect().iterdump()) == before


@pytest.mark.parametrize("method,path,body", [
    ("PUT", PATH, {"credential": "contains space"}),
    ("PUT", PATH, {"credential": " leading"}),
    ("PUT", PATH, {"credential": "trailing "}),
    ("PUT", PATH, {"credential": ""}),
    ("PUT", PATH, {"credential": "x" * 2049}),
    ("PUT", PATH, {"credential": "line\nfeed"}),
    ("PUT", PATH, {"credential": 123}),
    ("PUT", PATH, {"credential": "synthetic", "provider": "moonshot"}),
    ("PUT", PATH, {"credential": "synthetic", "model": "glm-4.7-flashx"}),
    ("POST", PATH + "/delete", {}),
    ("DELETE", PATH, {}),
    ("PUT", PATH + "/unknown", {"credential": "synthetic"}),
    ("GET", PATH, {"service": "other"}),
    ("GET", PATH + "?provider=moonshot", {}),
    ("PUT", PATH + "?model=glm-4.7-flashx", {"credential": "synthetic"}),
])
def test_invalid_requests_rejected_before_store_access(setup, method, path, body):
    app, store = setup
    with pytest.raises(ApiError):
        app.handle(method, path, json.dumps(body).encode())
    assert store.calls == []


def test_unavailable_native_store_is_honest_and_errors_are_redacted(setup):
    app, store = setup
    def fail(*args):
        raise CredentialStoreError("synthetic-secret-native-error")
    store.get = fail
    _, status = app.handle("GET", PATH)
    assert status["source"] == "UNAVAILABLE" and status["configured"] is False
    store.save = fail
    with pytest.raises(ApiError) as error:
        app.handle("PUT", PATH, b'{"credential":"synthetic-valid"}')
    assert error.value.code == "CREDENTIAL_STORE_UNAVAILABLE"
    assert "synthetic" not in str(error.value)


@pytest.mark.parametrize("headers", [
    {}, {"X-YIA-Request": "wrong"},
    {"X-YIA-Request": "local-ui", "Origin": "https://untrusted.invalid"},
    {"X-YIA-Request": "local-ui", "Origin": "http://127.0.0.1.attacker.invalid"},
])
def test_http_mutation_protection_precedes_store(setup, headers):
    app, store = setup
    server = serve_loopback(app, port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("PUT", PATH, b'{"credential":"synthetic-http"}', headers)
        response = client.getresponse()
        assert response.status == 403
        assert json.loads(response.read())["error"]["code"] == "ORIGIN_REJECTED"
        assert store.calls == []
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join()


def test_http_positive_is_config_only_and_never_returns_secret(setup):
    app, store = setup
    server = serve_loopback(app, port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("PUT", PATH, b'{"credential":"synthetic-http"}',
            {"X-YIA-Request": "local-ui", "Origin": "http://127.0.0.1:5173"})
        response = client.getresponse()
        raw = response.read()
        assert response.status == 200 and b"synthetic-http" not in raw
        assert response.getheader("Cache-Control") == "no-store"
        assert json.loads(raw)["budget"] == "CLOSED"
        assert store.secret == "synthetic-http"
        assert not app._cloud_intelligence_qualified
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("method,body", [("PUT", b'[]'), ("PUT", b'{bad'), ("PUT", b'x' * 32769)])
def test_invalid_body_shape_or_size_never_accesses_store(setup, method, body):
    app, store = setup
    with pytest.raises(ApiError):
        app.handle(method, PATH, body)
    assert store.calls == []


def test_absent_service_fails_redacted_without_touching_old_provider(setup):
    app, store = setup
    app._bigmodel_settings = None
    with pytest.raises(ApiError) as error:
        app.handle("GET", PATH)
    assert error.value.code == "CREDENTIAL_STORE_UNAVAILABLE"
    assert store.calls == []


@pytest.mark.parametrize("store_class", [MacOSBigModelCredentialStore, MacOSBigModelQACredentialStore])
def test_candidate_native_write_delete_uses_only_its_fixed_namespace(store_class, monkeypatch):
    calls = []
    class Framework:
        def SecKeychainFindGenericPassword(self, _, sl, service, al, account, length, data, item):
            calls.append(("find", service, account))
            assert sl == len(service) and al == len(account)
            return -25300
        def SecKeychainAddGenericPassword(self, _, sl, service, al, account, length, raw, item):
            calls.append(("add", service, account))
            assert raw[:length] == b"synthetic-native-candidate"
            return 0
    framework = Framework()
    store = store_class()
    monkeypatch.setattr(store, "_libraries", lambda: (framework, framework))
    store.save("synthetic-native-candidate")
    store.delete()
    assert calls == [("find", store_class._service, b"api-key"),
        ("add", store_class._service, b"api-key"), ("find", store_class._service, b"api-key")]


@pytest.mark.parametrize("secret", ["synthetic\u2003space", "synthetic\u0085control", "synthetic-密钥", "synthetic\u200bzero", "synthetic\ud800surrogate"])
def test_unsendable_key_rejected_by_api_before_any_store_access(setup, secret):
    app, store = setup
    with pytest.raises(ApiError) as error:
        app.handle("PUT", PATH, json.dumps({"credential": secret}).encode())
    assert error.value.code == "VALIDATION_ERROR"
    assert store.calls == []


@pytest.mark.parametrize("secret", ["synthetic\u2003space", "synthetic\u0085control", "synthetic-密钥", "synthetic\u200bzero", "synthetic\ud800surrogate"])
def test_unsendable_key_rejected_by_direct_settings_before_write(secret):
    store = MemoryStore()
    with pytest.raises(ValueError):
        BigModelCredentialSettings(store).save(secret)
    assert store.calls == []


@pytest.mark.parametrize("secret", ["!~", "x" * 2048])
def test_sendable_ascii_boundary_remains_configurable(setup, secret):
    app, store = setup
    status, result = app.handle("PUT", PATH, json.dumps({"credential": secret}).encode())
    assert status == 200 and result["configured"] is True
    assert result["qualification"] == "NOT_VERIFIED" and result["budget"] == "CLOSED"
    assert store.secret == secret and store.calls == ["save", "get"]
