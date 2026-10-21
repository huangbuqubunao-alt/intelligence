"""One machine-local Intelligence choice; no model execution authority."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import stat
import uuid
from collections.abc import Callable, Iterator
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from typing import Any

from youtube_intel.backup_restore import (
    BackupRestoreError,
    BackupRestoreService,
    machine_configuration_root,
)
from youtube_intel.local_distillation_profile import canonical
from youtube_intel.local_intelligence_catalog import (
    CANDIDATE_ID,
    CATALOG,
    InstalledCandidate,
    resolve_candidate,
)
from youtube_intel.source_authority import managed_directory
from youtube_intel.state import SQLiteStateRepository, StateStoreError
from youtube_intel.tracked_retry_context import (
    RetryConflict,
    RetryIntegrity,
    store_lock,
)

MAX_BYTES = 16_384


class SettingsRejected(ValueError):
    def __init__(self, code: str, reason: str | None = None) -> None:
        self.code = code
        self.reason = reason
        super().__init__(code)


def _etag(raw: bytes | None) -> str:
    return hashlib.sha256(
        b"MISSING-v1" if raw is None else b"FILE-v1\0" + raw
    ).hexdigest()


def _object(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate configuration key")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("configuration must be an object")
    return value


def _read_configuration(root: Path, name: str) -> bytes | None:
    with managed_directory(root, create=True) as directory:
        identity = os.fstat(directory)
        if identity.st_uid != os.getuid() or identity.st_mode & 0o022:
            raise ValueError("unsafe configuration directory")
        try:
            fd = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            maximum = MAX_BYTES * 3 if name == "change.json" else MAX_BYTES
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or before.st_mode & 0o022
                or before.st_size > maximum
            ):
                raise ValueError("unsafe configuration file")
            raw = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)

            def fingerprint(s: os.stat_result) -> tuple[int, int, int, int, int]:
                return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

            if (
                fingerprint(before) != fingerprint(after)
                or fingerprint(after) != fingerprint(named)
                or len(raw) != before.st_size
            ):
                raise ValueError("configuration changed while reading")
            return raw


def _decode_selection(raw: bytes | None) -> InstalledCandidate | None:
    if raw is None:
        return None
    value = _object(raw)
    if type(value.get("version")) is not int:
        raise ValueError("unsupported machine selection")
    if value["version"] == 1:
        if (
            set(value) != {"version", "candidate_id", "generation"}
            or value["candidate_id"] != CANDIDATE_ID
        ):
            raise ValueError("unsupported historical machine selection")
    elif value["version"] == 2:
        if set(value) != {"version", "candidate_id", "generation", "catalog_hash"}:
            raise ValueError("unsupported machine selection")
    else:
        raise ValueError("unsupported machine selection")
    candidate = resolve_candidate(value["candidate_id"])
    if value["version"] == 2 and value["catalog_hash"] != candidate.catalog_hash:
        raise ValueError("installation catalog identity differs")
    if (
        not isinstance(value["generation"], str)
        or re.fullmatch(r"[0-9a-f]{64}", value["generation"]) is None
    ):
        raise ValueError("unsupported machine selection")
    return candidate


@contextmanager
def legacy_configuration_admission(data_root: Path) -> Iterator[bool]:
    """Legacy processing shares the machine latch but never recovers/applies it."""
    root = machine_configuration_root(data_root)
    with ExitStack() as stack:
        for path in (root.parent, root):
            directory = stack.enter_context(managed_directory(path, create=True))
            identity = os.fstat(directory)
            if identity.st_uid != os.getuid() or identity.st_mode & 0o022:
                raise ValueError("Machine configuration directory is unsafe.")
        try:
            stack.enter_context(store_lock(root / ".admission", exclusive=False))
        except (RetryConflict, RetryIntegrity):
            yield False
            return
        # Any journal, including a pre-promotion or damaged one, requires the
        # owning GUI composition to recover it. CLI must not clear this latch.
        if _read_configuration(root, "change.json") is not None:
            yield False
            return
        _decode_selection(_read_configuration(root, "model.json"))
        yield True


class LocalIntelligenceSettings:
    def __init__(
        self,
        backup: BackupRestoreService,
        *,
        probe: Callable[[InstalledCandidate], str],
    ) -> None:
        self.backup = backup
        self.root = backup.machine_configuration_root
        self.path = self.root / "model.json"
        self.probe = probe
        self.actual: dict[str, str | None] | None = None
        self.actual_digest: str | None = None
        self.bound_etag: str | None = None
        self.error: str | None = None
        try:
            with backup.admission_lock(exclusive=True):
                self._recover()
                self.bound_etag = _etag(self._read("model.json"))
        except (OSError, ValueError, RetryConflict, RetryIntegrity):
            self.error = "CONFIGURATION_INVALID"
        backup.bind_configuration_guard(self.admission_allowed)

    def _read(self, name: str) -> bytes | None:
        return _read_configuration(self.root, name)

    def _write(self, name: str, raw: bytes | None) -> None:
        with managed_directory(self.root, create=True) as directory:
            identity = os.fstat(directory)
            if identity.st_uid != os.getuid() or identity.st_mode & 0o022:
                raise ValueError("unsafe configuration directory")
            if raw is None:
                try:
                    os.unlink(name, dir_fd=directory)
                except FileNotFoundError:
                    pass
                os.fsync(directory)
                return
            if len(raw) > (MAX_BYTES * 3 if name == "change.json" else MAX_BYTES):
                raise ValueError("configuration exceeds bound")
            temporary = uuid.uuid4().hex + ".tmp"
            try:
                fd = os.open(
                    temporary,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=directory,
                )
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Verify the target is still a safe owned regular file.
                self._read(name)
                os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
                os.fsync(directory)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass

    def _selection(self, raw: bytes | None) -> InstalledCandidate | None:
        return _decode_selection(raw)

    @property
    def candidate(self) -> InstalledCandidate:
        return self._selection(self._read("model.json")) or CATALOG[0]

    def _journal(self) -> dict[str, Any] | None:
        raw = self._read("change.json")
        if raw is None:
            return None
        value = _object(raw)
        version = value.get("version")
        expected = {"version", "old", "new", "old_etag", "new_etag"}
        if version == 2:
            expected.add("old_recoverable")
        if type(version) is not int or version not in {1, 2} or set(value) != expected:
            raise ValueError("invalid settings journal")
        recoverable = value.get("old_recoverable", True)
        if type(recoverable) is not bool:
            raise ValueError("invalid recovery metadata")
        for key in ("old", "new"):
            encoded = value[key]
            if encoded is None and key == "old":
                body = None
            elif isinstance(encoded, str):
                body = base64.b64decode(encoded, validate=True)
                if len(body) > MAX_BYTES:
                    raise ValueError("journal exceeds bound")
            else:
                raise ValueError("invalid settings journal bytes")
            if key == "old" and not recoverable:
                if (
                    body is not None
                    or not isinstance(value["old_etag"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", value["old_etag"]) is None
                ):
                    raise ValueError("invalid damaged-configuration identity")
            elif value[key + "_etag"] != _etag(body):
                raise ValueError("invalid settings journal identity")
            if key == "old" and body is not None:
                self._selection(body)  # journal never copies unknown/corrupt text
            value[key + "_bytes"] = body
        if not self._selection(value["new_bytes"]):
            raise ValueError("journal has no new choice")
        return value

    def _recover(self) -> None:
        journal = self._journal()
        if journal is not None:
            current = _etag(self._read("model.json"))
            if current == journal["old_etag"]:
                # Interrupted before promotion: preserve old configuration.
                self._write("change.json", None)
            elif current != journal["new_etag"]:
                raise ValueError("settings journal conflicts with current bytes")
            # New bytes remain latched until actual runtime binding confirms.

    def selected(self) -> bool:
        try:
            return self._selection(self._read("model.json")) is not None
        except (OSError, ValueError):
            return False

    def bind_actual(self, binding: dict[str, str | None], digest: str) -> None:
        self.actual, self.actual_digest = dict(binding), digest
        if (
            self.selected()
            and binding.get("provider") == "ollama"
            and binding.get("model") == self.candidate.model
            and digest == self.candidate.model_digest
        ):
            try:
                with self.backup.admission_lock(exclusive=True):
                    if _etag(self._read("model.json")) != self.bound_etag:
                        raise ValueError(
                            "selection changed during runtime construction"
                        )
                    journal = self._journal()
                    if self.probe(self.candidate) != "READY":
                        self.error = "MODEL_NOT_READY"
                        return
                    if journal is not None:
                        self._write("change.json", None)
            except (OSError, ValueError, RetryConflict, RetryIntegrity):
                self.error = "CONFIGURATION_APPLY_FAILED"

    def admission_allowed(self) -> bool:
        try:
            raw = self._read("model.json")
            self._selection(raw)
            return (
                self.error is None
                and self._read("change.json") is None
                and _etag(raw) == self.bound_etag
            )
        except (OSError, ValueError):
            return False

    @contextmanager
    def admission(self, *, maintenance: bool = False) -> Iterator[bool]:
        with ExitStack() as stack:
            try:
                stack.enter_context(self.backup.admission_lock())
            except (RetryConflict, RetryIntegrity):
                yield False
                return
            yield maintenance or self.admission_allowed()

    def status(self) -> dict[str, object]:
        state = "NOT_CONFIGURED"
        token: str | None = None
        selected: str | None = None
        try:
            raw = self._read("model.json")
            token = _etag(raw)
            valid = self._selection(raw)
            if valid:
                selected = valid.candidate_id
                state = (
                    "APPLIED"
                    if (
                        self.actual is not None
                        and self.actual.get("provider") == "ollama"
                        and self.actual.get("model") == self.candidate.model
                        and self.actual_digest == self.candidate.model_digest
                        and token == self.bound_etag
                    )
                    else "ROUTE_MISMATCH"
                )
            if self._journal() is not None and self.error is None:
                state = "APPLYING"
            if self.error is not None:
                state = "ROUTE_MISMATCH" if valid else "INVALID"
        except (OSError, ValueError):
            state = "INVALID"
        candidates: list[dict[str, object]] = []
        for entry in CATALOG:
            try:
                installation = self.probe(entry)
                if installation not in {
                    "READY",
                    "NOT_INSTALLED",
                    "IDENTITY_MISMATCH",
                    "RUNTIME_MISMATCH",
                    "UNAVAILABLE",
                }:
                    installation = "UNAVAILABLE"
            except (OSError, ValueError):
                installation = "UNAVAILABLE"
            candidates.append(
                {
                    "candidate_id": entry.candidate_id,
                    "model": entry.model,
                    "model_digest": entry.model_digest,
                    "runtime": entry.runtime,
                    "catalog_hash": entry.catalog_hash,
                    "installation": installation,
                    "qualification": "NOT_GRANTED_BY_SETTINGS",
                }
            )
        blocking: list[dict[str, object]] = []
        repository = SQLiteStateRepository(self.backup.database)
        repository.bind_source_storage(self.backup.data_root)
        try:
            with closing(repository._connect(read_only=True)) as connection:
                rows = connection.execute(
                    "SELECT execution_id,video_id FROM distillation_execution_checkpoints WHERE status IN ('PENDING','RUNNING','WAITING_MODEL','WAITING_BUDGET','AMBIGUOUS') ORDER BY updated_at DESC LIMIT 100"
                ).fetchall()
            for row in rows:
                try:
                    execution = repository.get_distillation_execution(
                        row["execution_id"]
                    )
                    status = "UNVERIFIED" if execution is None else execution.status
                except (StateStoreError, ValueError, sqlite3.Error):
                    status = "UNVERIFIED"
                if status in {
                    "PENDING",
                    "RUNNING",
                    "WAITING_MODEL",
                    "WAITING_BUDGET",
                    "AMBIGUOUS",
                    "UNVERIFIED",
                }:
                    blocking.append({"video_id": row["video_id"], "status": status})
        except (OSError, ValueError, StateStoreError, sqlite3.Error):
            blocking = []
        return {
            "status": state,
            "etag": token,
            "selected_candidate_id": selected,
            "actual_route": self.actual,
            "restart_required": state == "APPLYING",
            "blocking_work": blocking,
            "error_code": self.error
            or ("CONFIGURATION_INVALID" if state == "INVALID" else None),
            "candidates": candidates,
        }

    def apply(self, candidate_id: str, expected_etag: str) -> dict[str, object]:
        try:
            requested = resolve_candidate(candidate_id)
        except ValueError as error:
            raise SettingsRejected("MODEL_CANDIDATE_INVALID") from error
        if re.fullmatch(r"[0-9a-f]{64}", expected_etag) is None:
            raise SettingsRejected("CONFIGURATION_CONFLICT")
        try:
            with self.backup.configuration_window():
                old = self._read("model.json")
                if _etag(old) != expected_etag:
                    try:
                        journal = self._journal()
                    except ValueError:
                        journal = None
                    if (
                        journal is not None
                        and journal["old_etag"] == expected_etag
                        and journal["new_etag"] == _etag(old)
                        and self._selection(journal["new_bytes"]) == requested
                    ):
                        self.error = None
                        self.backup.request_restart()
                        return self.status()
                    raise SettingsRejected("CONFIGURATION_CONFLICT")
                if self.probe(requested) != "READY":
                    raise SettingsRejected("MODEL_NOT_READY")
                if (
                    self.selected()
                    and self.candidate == requested
                    and self.status()["status"] == "APPLIED"
                ):
                    return self.status()
                new = canonical(
                    {
                        "version": 2,
                        "candidate_id": candidate_id,
                        "catalog_hash": requested.catalog_hash,
                        "generation": uuid.uuid4().hex + uuid.uuid4().hex,
                    }
                )
                try:
                    self._selection(old)
                    old_recoverable = True
                except ValueError:
                    old_recoverable = False
                retained_old = old if old_recoverable else None
                journal = {
                    "version": 2,
                    "old_recoverable": old_recoverable,
                    "old": None
                    if retained_old is None
                    else base64.b64encode(retained_old).decode(),
                    "new": base64.b64encode(new).decode(),
                    "old_etag": _etag(old),
                    "new_etag": _etag(new),
                }
                self._write("change.json", canonical(journal))
                try:
                    self._write("model.json", new)
                except BaseException:
                    current = self._read("model.json")
                    if (
                        _etag(current) == journal["old_etag"]
                        or old_recoverable
                        and _etag(current) == journal["new_etag"]
                    ):
                        if _etag(current) == journal["new_etag"]:
                            self._write("model.json", retained_old)
                        self._write("change.json", None)
                    # Damaged old bytes are never copied into a journal. If
                    # promotion happened before an fsync error, retain the new
                    # choice and durable latch; explicit replay or next startup
                    # must confirm the actual route before admitting work.
                    raise
                self.error = None
                self.backup.request_restart()
                return self.status()
        except SettingsRejected:
            raise
        except BackupRestoreError as error:
            raise SettingsRejected("CONFIGURATION_BUSY", str(error)) from error
        except (OSError, ValueError, RetryConflict, RetryIntegrity) as error:
            raise SettingsRejected("CONFIGURATION_APPLY_FAILED") from error
