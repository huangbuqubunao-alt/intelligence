"""Machine-local configuration, never model qualification or cloud consent."""

from __future__ import annotations

import ctypes
import json
import os
from collections.abc import Callable
from http.client import HTTPConnection, HTTPException
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .local_intelligence_catalog import InstalledCandidate
from urllib.parse import urlparse

from youtube_intel.config import _validate_loopback_http_base_url


class CredentialStoreError(Exception):
    """Redacted system credential-store failure."""


class CredentialStore(Protocol):
    def get(self) -> str | None: ...
    def save(self, secret: str) -> None: ...
    def delete(self) -> None: ...


class MacOSKeychainCredentialStore:
    """Native Keychain API: no credential in argv, subprocess output or files.

    Reuse the historical M13 service/account identity without touching its store
    during automated checks. Framework loading and access are lazy.
    """

    _service = b"com.huangbuqubunao.intelligence.moonshot"
    _account = b"api-key"

    def _libraries(self) -> tuple[Any, Any]:
        try:
            security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
            core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        except OSError:
            raise CredentialStoreError() from None
        pointer, uint = ctypes.c_void_p, ctypes.c_uint32
        security.SecKeychainFindGenericPassword.argtypes = [pointer, uint, pointer, uint, pointer, ctypes.POINTER(uint), ctypes.POINTER(pointer), ctypes.POINTER(pointer)]
        security.SecKeychainAddGenericPassword.argtypes = [pointer, uint, pointer, uint, pointer, uint, pointer, ctypes.POINTER(pointer)]
        security.SecKeychainItemModifyAttributesAndData.argtypes = [pointer, pointer, uint, pointer]
        security.SecKeychainItemDelete.argtypes = [pointer]
        security.SecKeychainItemFreeContent.argtypes = [pointer, pointer]
        core.CFRelease.argtypes = [pointer]
        core.CFRelease.restype = None
        return security, core

    def _find(self, security: Any) -> tuple[int, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]:
        length, data, item = ctypes.c_uint32(), ctypes.c_void_p(), ctypes.c_void_p()
        status = security.SecKeychainFindGenericPassword(None, len(self._service), self._service, len(self._account), self._account, ctypes.byref(length), ctypes.byref(data), ctypes.byref(item))
        if status not in (0, -25300):
            raise CredentialStoreError()
        return status, length, data, item

    def get(self) -> str | None:
        security, core = self._libraries()
        status, length, data, item = self._find(security)
        if status == -25300:
            return None
        try:
            return ctypes.string_at(data, length.value).decode("utf-8") or None
        except UnicodeError:
            raise CredentialStoreError() from None
        finally:
            security.SecKeychainItemFreeContent(None, data)
            core.CFRelease(item)

    def save(self, secret: str) -> None:
        security, core = self._libraries()
        status, _, data, item = self._find(security)
        raw = secret.encode("utf-8")
        if status == -25300:
            status = security.SecKeychainAddGenericPassword(None, len(self._service), self._service, len(self._account), self._account, len(raw), raw, None)
        else:
            try:
                status = security.SecKeychainItemModifyAttributesAndData(item, None, len(raw), raw)
            finally:
                security.SecKeychainItemFreeContent(None, data)
                core.CFRelease(item)
        if status != 0:
            raise CredentialStoreError()

    def delete(self) -> None:
        security, core = self._libraries()
        status, _, data, item = self._find(security)
        if status == -25300:
            return
        try:
            if security.SecKeychainItemDelete(item) != 0:
                raise CredentialStoreError()
        finally:
            security.SecKeychainItemFreeContent(None, data)
            core.CFRelease(item)


def local_models(base_url: str = "http://127.0.0.1:11434") -> object:
    return _local_metadata(base_url, "/api/tags")


def local_runtime_version(base_url: str = "http://127.0.0.1:11434") -> object:
    return _local_metadata(base_url, "/api/version")


def _local_metadata(base_url: str, endpoint: str) -> object:
    # Discovery only. No /generate, /pull, qualification or external request.
    parsed = urlparse(_validate_loopback_http_base_url(base_url))
    connection = HTTPConnection(parsed.hostname or "127.0.0.1", parsed.port or 80, timeout=2)
    try:
        connection.request("GET", parsed.path.rstrip("/") + endpoint)
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Discovery unavailable")
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Discovery response too large")
        return json.loads(raw)
    finally:
        connection.close()


class ModelSettingsService:
    def __init__(self, store: CredentialStore, *, tags_fetch: Callable[[], object] = local_models,
        version_fetch: Callable[[], object] = local_runtime_version) -> None:
        self._store = store
        self._tags_fetch = tags_fetch
        self._version_fetch = version_fetch

    def fixed_local_identity(self, candidate: InstalledCandidate | None = None) -> str:
        """Only bounded metadata for the one fixed candidate; no inference."""
        from .local_intelligence_catalog import CATALOG
        profile = candidate or CATALOG[0]
        state = self.runtime_status(profile.model, profile.model_digest)["status"]
        if state == "NOT_INSTALLED":
            return "NOT_INSTALLED"
        if state == "DIGEST_MISMATCH":
            return "IDENTITY_MISMATCH"
        if state != "READY":
            return "UNAVAILABLE"
        try:
            version = self._version_fetch()
            return ("READY" if isinstance(version, dict) and version.get("version") == profile.runtime
                else "RUNTIME_MISMATCH")
        except (OSError, ValueError, UnicodeError, HTTPException):
            return "UNAVAILABLE"

    def credential(self) -> str:
        try:
            return self._store.get() or os.environ.get("MOONSHOT_API_KEY", "")
        except CredentialStoreError:
            # Preserve the previously accepted explicit development credential
            # path when native storage is unavailable; this grants no authority.
            return os.environ.get("MOONSHOT_API_KEY", "")

    def credential_status(self) -> dict[str, object]:
        try:
            source = "KEYCHAIN" if self._store.get() else "ENVIRONMENT" if os.environ.get("MOONSHOT_API_KEY") else "NONE"
        except CredentialStoreError:
            source = "ENVIRONMENT" if os.environ.get("MOONSHOT_API_KEY") else "UNAVAILABLE"
        return {"configured": source in {"KEYCHAIN", "ENVIRONMENT"}, "source": source}

    def save_credential(self, secret: str) -> None:
        if not secret or len(secret) > 2048 or any(ord(c) < 33 or ord(c) == 127 for c in secret):
            raise ValueError("Credential is invalid")
        self._store.save(secret)

    def delete_credential(self) -> None:
        self._store.delete()

    def runtime_status(self, model: str, expected_digest: str) -> dict[str, object]:
        """Read-only discovery validates the configured identity; never infer or pull."""
        try:
            payload = self._tags_fetch()
            if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
                raise ValueError("Invalid local model discovery response")
            models = payload["models"]
            installed = next((item for item in models if isinstance(item, dict) and item.get("name") == model), None)
            valid = installed is not None and isinstance(installed.get("digest"), str) and installed.get("digest") in {expected_digest, expected_digest.removeprefix("sha256:")}
            return {"model": model, "status": "READY" if valid else "DIGEST_MISMATCH" if installed else "NOT_INSTALLED", "installed": installed is not None, "digest_valid": valid}
        except (OSError, ValueError, UnicodeError, HTTPException):
            return {"model": model, "status": "UNREACHABLE", "installed": False, "digest_valid": False}

    def discovered_models(self) -> dict[str, object]:
        try:
            payload = self._tags_fetch()
            if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
                raise ValueError()
            models = []
            for item in payload["models"][:100]:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if isinstance(name, str) and 0 < len(name) <= 160:
                    models.append({"model": name, "qualified": False})
            return {"connection": "REACHABLE", "models": models}
        except (OSError, ValueError, UnicodeError, HTTPException):
            return {"connection": "UNAVAILABLE", "models": []}
