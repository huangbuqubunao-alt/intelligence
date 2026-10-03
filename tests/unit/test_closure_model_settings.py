import ctypes
import json
from datetime import UTC, datetime

import pytest

from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.model_settings import (
    CredentialStoreError,
    MacOSKeychainCredentialStore,
    ModelSettingsService,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository

native_get = MacOSKeychainCredentialStore.get


def test_native_keychain_add_update_read_delete_release_without_system_access(monkeypatch):
    class Framework:
        raw = None
        released = 0
        freed = 0

        def SecKeychainFindGenericPassword(self, _, sl, service, al, account, length, data, item):
            assert service == MacOSKeychainCredentialStore._service
            assert account == MacOSKeychainCredentialStore._account
            assert sl == len(service) and al == len(account)
            if self.raw is None:
                return -25300
            self.buffer = ctypes.create_string_buffer(self.raw)
            length._obj.value = len(self.raw)
            data._obj.value = ctypes.addressof(self.buffer)
            item._obj.value = 17
            return 0

        def SecKeychainAddGenericPassword(self, _, sl, service, al, account, length, raw, item):
            self.raw = raw[:length]
            return 0

        def SecKeychainItemModifyAttributesAndData(self, item, _, length, raw):
            assert item.value == 17
            self.raw = raw[:length]
            return 0

        def SecKeychainItemFreeContent(self, _, data):
            self.freed += 1

        def CFRelease(self, item):
            assert item.value == 17
            self.released += 1

        def SecKeychainItemDelete(self, item):
            assert item.value == 17
            self.raw = None
            return 0

    framework = Framework()
    store = MacOSKeychainCredentialStore()
    monkeypatch.setattr(store, "_libraries", lambda: (framework, framework))
    assert native_get(store) is None
    store.save("synthetic-first")
    assert native_get(store) == "synthetic-first"
    store.save("synthetic-second")
    assert native_get(store) == "synthetic-second"
    store.delete()
    assert native_get(store) is None
    store.delete()
    assert framework.freed == framework.released == 4


class MemoryStore:
    secret = None

    def get(self):
        return self.secret

    def save(self, secret):
        self.secret = secret

    def delete(self):
        self.secret = None


def test_credential_configuration_has_no_qualification_or_dispatch(tmp_path, monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=datetime.now(UTC))
    store = MemoryStore()
    settings = ModelSettingsService(store, tags_fetch=lambda: {"models": [{"name": "other:7b", "digest": "a" * 64}]})
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), model_settings=settings)
    status, models = app.handle("GET", "/api/v1/settings/local-models")
    assert status == 200
    assert models["models"][0]["model"] == "other:7b"
    assert models["models"][0]["qualified"] is False
    secret = "synthetic-closure-only"
    status, result = app.handle("PUT", "/api/v1/settings/cloud-credential", json.dumps({"credential": secret}).encode())
    assert status == 200 and result["configured"] is True
    assert secret not in json.dumps(result)
    assert app._cloud_credential_available is True
    assert app._cloud_intelligence_qualified is False
    assert settings.credential() == secret
    assert secret not in "\n".join(repo._connect().iterdump())
    with pytest.raises(ApiError):
        app.handle("POST", "/api/v1/settings/cloud-credential/delete", b'{}')
    app.handle("POST", "/api/v1/settings/cloud-credential/delete", b'{"confirm":"DELETE"}')
    assert settings.credential() == "" and app._cloud_credential_available is False


def test_credential_store_failure_is_redacted_and_environment_is_preserved(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-environment-only")
    store = MemoryStore()
    settings = ModelSettingsService(store)
    assert settings.credential_status() == {"configured": True, "source": "ENVIRONMENT"}
    store.save("synthetic-store-only")
    settings.delete_credential()
    assert settings.credential() == "synthetic-environment-only"
    for bad in ["", "contains space", "line\nfeed", "x" * 2049]:
        with pytest.raises(ValueError):
            settings.save_credential(bad)
    def fail():
        raise CredentialStoreError()
    store.get = fail
    assert settings.credential_status() == {"configured": True, "source": "ENVIRONMENT"}
    assert settings.credential() == "synthetic-environment-only"
    monkeypatch.delenv("MOONSHOT_API_KEY")
    assert settings.credential_status() == {"configured": False, "source": "UNAVAILABLE"}
    assert settings.credential() == ""
