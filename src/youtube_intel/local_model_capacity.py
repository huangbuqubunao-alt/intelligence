"""Fixed qwen35 host prerequisites and application-only heavyweight leases.

No readiness or load receipt confers model qualification. The file slot is the
existing ASR worker slot, not a lock on unrelated external Ollama clients.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import threading
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any, Protocol

from youtube_intel.local_distillation_profile import (
    FIXED_RUNTIME_PROFILE_ID,
    PROFILE_ID,
    canonical,
    digest,
    resolve_profile,
)

if TYPE_CHECKING:
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.distillation import VerifiedDistillationInput
    from youtube_intel.state import SQLiteStateRepository

GIB = 1024**3
BINARIES = {
    "ollama": "7f598201b6e77bf39079b02a44c64abcb34e83a0e685da24a71fd9aebff2344b",
    "llama-server": "35844857b55bb541fe914064b96e437f8b8d187968ecd8cfe50c52dd8434b8b8",
    "libllama-server-impl.dylib": "096573a0fe1ea34f126c937c7be021ffaa27647ff31eac5852cda8165a939b66",
}
BLOBS = {
    "08f9698c1116d2ba3d2c1751f6e98919823e13bb28ff5eb7451c7bc9b40907c5": 177,
    "f836f08f921193f4d6b6a6952dba0a6fb116759d26a757bcb395d570d73976ca": 921704832,
    "02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d": 5629109120,
    "b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315": 13,
    "50cbab8a892c5f2993b8c7351a99182507472def3b1374558308605d99b86b32": 11343,
    "9371364b27a52acac9d87f88bd93c9db1174d8d6ec57f6888925cdc1788871ff": 65,
}
ROOT = Path("/Applications/Ollama.app/Contents/Resources")
# v0.40.1 writes this legacy downgrade anchor, not the API-selected manifest.
_WRAPPER_SHA256 = "7dd7bb310c1f18ad132c7fd72e73d4f6cff2e916c596a818701d2a1269037c7f"
_WRAPPER_MANIFEST_BYTES = 1252
_PARENT_MANIFEST_BYTES = 1088
_MANIFEST_MEDIA_TYPE = "application/vnd.docker.distribution.manifest.v2+json"


class CapacityUnavailable(OSError):
    """Known pre-dispatch resource/identity failure; no generation attempted."""


def _stat_identity(stat: os.stat_result) -> tuple[int, int, int, int]:
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def file_hash(
    path: Path, *, expected_identity: tuple[int, int, int, int] | None = None
) -> str:
    expected = (
        expected_identity if expected_identity is not None else file_identity(path)
    )
    result = hashlib.sha256()
    with path.open("rb") as stream:
        if _stat_identity(os.fstat(stream.fileno())) != expected:
            raise CapacityUnavailable("opened runtime file identity differs")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
        if (
            _stat_identity(os.fstat(stream.fileno())) != expected
            or file_identity(path) != expected
        ):
            raise CapacityUnavailable("runtime file changed while hashing")
    return result.hexdigest()


def file_identity(path: Path) -> tuple[int, int, int, int]:
    return _stat_identity(path.stat())


def processes(binary: str) -> str:
    """Read only matching fixed-runtime process metadata, never process env."""
    result = subprocess.run(
        ["/usr/bin/pgrep", "-f", "^" + re.escape(str(ROOT / binary)) + "( |$)"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode == 1:
        return ""
    pids = result.stdout.split()
    if result.returncode != 0 or not pids or any(not p.isdecimal() for p in pids):
        raise CapacityUnavailable("runtime process identity is unavailable")
    return subprocess.run(
        ["/bin/ps", "-p", ",".join(pids), "-o", "pid=,lstart=,args="],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    ).stdout.strip()


def available_memory_bytes() -> int:
    result = subprocess.run(
        ["/usr/bin/vm_stat"], capture_output=True, text=True, timeout=5, check=True
    ).stdout
    page = re.search(r"page size of (\d+) bytes", result)
    if page is None:
        raise CapacityUnavailable("memory observation is unavailable")
    matches = [
        re.search(rf"{key}:\s+(\d+)\.", result)
        for key in ("Pages free", "Pages inactive", "Pages speculative")
    ]
    if any(m is None for m in matches):
        raise CapacityUnavailable("memory observation is incomplete")
    return int(page.group(1)) * sum(int(m.group(1)) for m in matches if m is not None)


def _stopped_after_unknown(latest: datetime) -> bool:
    """A fresh server process removes the old server's unknown request queue.

    An empty ps alone is insufficient: an old server may still have a queued
    request. No stored machine witness/boolean survives restore as authority.
    This observation never restarts, loads, unloads or generates a model.
    """
    if file_hash(ROOT / "ollama") != BINARIES["ollama"] or processes("llama-server"):
        return False
    server = processes("ollama")
    suffix = str(ROOT / "ollama") + " serve"
    if len(server.splitlines()) != 1 or not server.endswith(suffix):
        return False
    prefix = server[: -len(suffix)].strip().split(maxsplit=1)
    if len(prefix) != 2 or not prefix[0].isdecimal():
        return False
    started = datetime.strptime(prefix[1], "%a %b %d %H:%M:%S %Y").astimezone(UTC)
    if started <= latest:
        return False
    from youtube_intel.local_distillation_qualification import strict_object

    def get(path: str) -> Mapping[str, object]:
        request = urllib.request.Request(
            "http://127.0.0.1:11434" + path,
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise CapacityUnavailable("runtime metadata exceeds bounds")
        value = json.loads(raw, object_pairs_hook=strict_object)
        if not isinstance(value, dict):
            raise CapacityUnavailable("runtime metadata is invalid")
        return value

    if (
        get("/api/version").get("version") != resolve_profile(PROFILE_ID).runtime
        or get("/api/ps").get("models") != []
    ):
        return False
    return processes("ollama") == server and processes("llama-server") == ""


def unresolved_local_work(repository: SQLiteStateRepository) -> bool:
    """Called only under the application file slot; no mutation of history."""
    try:
        with repository._connect() as connection:
            rows = connection.execute(
                "SELECT execution_id,status,updated_at FROM distillation_execution_checkpoints "
                "WHERE selected_provider='ollama' AND (status='AMBIGUOUS' OR (status='PENDING' AND invocation_count=1))"
            ).fetchall()
        if any(row["status"] == "PENDING" for row in rows):
            return True
        if not rows:
            return False
        from youtube_intel.backup_restore import _AMBIGUOUS_DISTILLATION_OUTCOMES

        latest = datetime.min.replace(tzinfo=UTC)
        for row in rows:
            execution = repository.get_distillation_execution(row["execution_id"])
            usage = repository.get_distillation_resource_usage(row["execution_id"])
            if (
                execution is None
                or usage.status != "AMBIGUOUS"
                or usage.invocation_count
                not in _AMBIGUOUS_DISTILLATION_OUTCOMES.get(usage.outcome, set())
                or any(
                    getattr(execution, key) != getattr(usage, key)
                    for key in (
                        "execution_id",
                        "source_id",
                        "video_id",
                        "reason",
                        "use_case",
                        "selected_provider",
                        "selected_model",
                        "invocation_count",
                        "budget_state",
                        "intelligence_id",
                        "revision_id",
                    )
                )
                or execution.intelligence_id is not None
                or execution.revision_id is not None
                or any(
                    getattr(usage, key) is not None
                    for key in (
                        "actual_provider",
                        "actual_model",
                        "input_tokens",
                        "output_tokens",
                        "cost_microunits",
                        "duration_ms",
                    )
                )
            ):
                return True
            date = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
            if date.tzinfo is None or date.utcoffset() != UTC.utcoffset(date):
                return True
            latest = max(latest, date)
        return not _stopped_after_unknown(latest)
    except Exception:
        return True  # missing/foreign/restored local evidence is never authority


def _reference_identity(path: Path) -> tuple[int, int, int, int, str]:
    stat = path.lstat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, os.readlink(path)


def _verify_model_manifests(
    wrapper: Path,
    parent: Path,
    *,
    identities: Mapping[Path, tuple[int, int, int, int]] | None = None,
) -> None:
    """Verify the exact legacy anchor and its original runnable manifest.

    Official v0.40.1 WriteLegacyAnchor appends manifest blobs as GC anchors;
    the public digest comes from the v2 named reference to the original blob.
    This accepts one pinned installation shape, never arbitrary extra layers.
    """
    from youtube_intel.local_distillation_qualification import strict_object

    parent_hash = resolve_profile(PROFILE_ID).model_digest.removeprefix("sha256:")

    def read(path: Path, size: int, expected_hash: str) -> object:
        expected = file_identity(path) if identities is None else identities[path]
        with path.open("rb") as stream:
            if _stat_identity(os.fstat(stream.fileno())) != expected:
                raise CapacityUnavailable("opened manifest file identity differs")
            raw = stream.read(size + 1)
            if (
                _stat_identity(os.fstat(stream.fileno())) != expected
                or file_identity(path) != expected
            ):
                raise CapacityUnavailable("manifest changed while reading")
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise CapacityUnavailable("model manifest bytes differ")
        try:
            return json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
        except (ValueError, UnicodeError, RecursionError):
            raise CapacityUnavailable("model manifest JSON differs") from None

    wrapper_value = read(wrapper, _WRAPPER_MANIFEST_BYTES, _WRAPPER_SHA256)
    parent_value = read(parent, _PARENT_MANIFEST_BYTES, parent_hash)
    payloads = list(BLOBS.items())
    if len(payloads) != 6:
        raise CapacityUnavailable("fixed payload descriptor contract differs")
    config_hash, config_size = payloads[0]
    layers: list[dict[str, object]] = []
    for (blob_hash, size), (kind, source) in zip(
        payloads[1:],
        (
            ("projector", "mmproj.gguf"),
            ("model", "model.gguf"),
            ("template", None),
            ("license", None),
            ("params", None),
        ),
        strict=True,
    ):
        layer: dict[str, object] = {
            "mediaType": "application/vnd.ollama.image." + kind,
            "digest": "sha256:" + blob_hash,
            "size": size,
        }
        if source is not None:
            layer["from"] = source
        layers.append(layer)
    expected = {
        "schemaVersion": 2,
        "mediaType": _MANIFEST_MEDIA_TYPE,
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "digest": "sha256:" + config_hash,
            "size": config_size,
        },
        "layers": layers,
        "runner": "llamacpp",
        "format": "gguf",
    }
    expected_wrapper = {
        **expected,
        "layers": [
            *layers,
            {
                "mediaType": _MANIFEST_MEDIA_TYPE,
                "digest": "sha256:" + parent_hash,
                "size": _PARENT_MANIFEST_BYTES,
            },
        ],
    }
    if canonical(parent_value) != canonical(expected) or canonical(
        wrapper_value
    ) != canonical(expected_wrapper):
        raise CapacityUnavailable(
            "model manifest descriptors or parent relation differ"
        )


@dataclass(frozen=True)
class HostObservation:
    files: tuple[tuple[Path, tuple[int, int, int, int]], ...]
    server: str
    runner: str
    references: tuple[tuple[Path, tuple[int, int, int, int, str]], ...] = ()

    def is_current(self) -> bool:
        try:
            return (
                all(file_identity(p) == identity for p, identity in self.files)
                and all(
                    _reference_identity(p) == identity
                    for p, identity in self.references
                )
                and processes("ollama") == self.server
                and processes("llama-server") == self.runner
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            return False


def verify_installed_model_bytes(
    cache: Path,
) -> tuple[
    tuple[tuple[Path, tuple[int, int, int, int]], ...],
    tuple[tuple[Path, tuple[int, int, int, int, str]], ...],
]:
    """Shared fixed-byte gate; performs no process, HTTP, load or generation IO."""
    profile = resolve_profile(PROFILE_ID)
    manifest = cache / "manifests/registry.ollama.ai/library/qwen3.5/9b-q4_K_M"
    parent_hash = profile.model_digest.removeprefix("sha256:")
    parent = cache / "blobs" / ("sha256-" + parent_hash)
    reference = cache / "manifests-v2/ollama.com/library/qwen3.5/9b-q4_K_M"
    references = ((reference, _reference_identity(reference)),)
    if (
        references[0][1][-1] != "../../../../blobs/sha256-" + parent_hash
        or reference.resolve() != parent.resolve()
    ):
        raise CapacityUnavailable("API manifest reference differs")
    paths = [
        manifest,
        parent,
        reference,
        *(ROOT / name for name in BINARIES),
        *(cache / "blobs" / ("sha256-" + h) for h in BLOBS),
    ]
    before = tuple((p, file_identity(p)) for p in paths)
    identities = dict(before)
    _verify_model_manifests(manifest, parent, identities=identities)
    for name, expected in BINARIES.items():
        if (
            file_hash(ROOT / name, expected_identity=identities[ROOT / name])
            != expected
        ):
            raise CapacityUnavailable("runtime binary differs")
    for expected, size in BLOBS.items():
        path = cache / "blobs" / ("sha256-" + expected)
        if (
            path.stat().st_size != size
            or file_hash(path, expected_identity=identities[path]) != expected
        ):
            raise CapacityUnavailable("model blob differs")
    if any(file_identity(p) != identity for p, identity in before) or any(
        _reference_identity(p) != identity for p, identity in references
    ):
        raise CapacityUnavailable("installed bytes changed while hashing")
    return before, references


def observe_host(
    *, data_root: Path, loaded: bool, profile_id: str = PROFILE_ID,
) -> HostObservation:
    """Ordinary host gate; v2 execution observations require explicit512."""
    profile = resolve_profile(profile_id)
    return _observe_host(
        data_root=data_root, loaded=loaded,
        fixed_batch=512 if profile.profile_id == FIXED_RUNTIME_PROFILE_ID else None,
    )


def observe_load_only_reconfiguration(*, data_root: Path) -> HostObservation:
    """Only the pinned legacy1024 shape may precede an empty reload probe.

    This observation cannot be used as readiness: the session must observe the
    ordinary fixed512 host after the probe before it can mint its ready state.
    """
    return _observe_host(data_root=data_root, loaded=True, fixed_batch=1024)


def _observe_host(
    *, data_root: Path, loaded: bool, fixed_batch: int | None = None,
) -> HostObservation:
    """Verify installed bytes and resource truth, never an old receipt boolean."""
    cache = Path.home() / ".ollama/models"
    before, references = verify_installed_model_bytes(cache)
    server, runner = processes("ollama"), processes("llama-server")
    if len(server.splitlines()) != 1 or not server.endswith(" serve"):
        raise CapacityUnavailable("server process differs")
    if loaded:
        _validate_runner(runner, cache, fixed_batch=fixed_batch)
    elif runner:
        raise CapacityUnavailable("untracked runner exists before load-only")
    if fixed_batch is not None:
        _validate_process_prefix(server, ROOT / "ollama", suffix=" serve")
    if shutil.disk_usage(data_root).free < 10 * GIB or available_memory_bytes() < (
        2 * GIB if loaded and fixed_batch != 1024 else sum(BLOBS.values()) + 2 * GIB
    ):
        raise CapacityUnavailable("disk or available RAM is insufficient")
    return HostObservation(before, server, runner, references)


def _validate_process_prefix(process: str, binary: Path, *, suffix: str | None = None) -> None:
    prefix, marker, args = process.partition(" " + str(binary))
    try:
        pid, started = prefix.strip().split(maxsplit=1)
        datetime.strptime(started, "%a %b %d %H:%M:%S %Y")
        if not marker or not pid.isdecimal() or not args.startswith(" ") or (suffix is not None and args != suffix):
            raise ValueError("process identity differs")
    except ValueError as error:
        raise CapacityUnavailable("runtime process identity differs") from error


def validate_runner(runner: str, cache: Path) -> None:
    """Preserve the original v1 runner gate, never accept legacy1024."""
    _validate_runner(runner, cache)


def _validate_runner(runner: str, cache: Path, *, fixed_batch: int | None = None) -> None:
    if fixed_batch is not None:
        _validate_process_prefix(runner, ROOT / "llama-server")
    if len(runner.splitlines()) != 1 or str(ROOT / "llama-server") not in runner:
        raise CapacityUnavailable("actual runner process is unavailable")
    args = shlex.split(runner[runner.index(str(ROOT / "llama-server")) :])[1:]
    flags = {
        "--no-webui",
        "--offline",
        "--no-jinja",
        "--no-log-prefix",
        "--no-log-timestamps",
    }
    valued = {
        "--model",
        "--port",
        "--host",
        "-c",
        "-np",
        "--log-verbosity",
        "--chat-template",
        "--mmproj",
        "--load-mode",
        "--flash-attn",
        "-b",
        "-ub",
    }
    values: dict[str, str] = {}
    index = 0
    while index < len(args):
        key = args[index]
        if key in values:
            raise CapacityUnavailable("duplicate runner override")
        if key in flags:
            values[key] = "true"
            index += 1
        elif key in valued and index + 1 < len(args):
            values[key] = args[index + 1]
            index += 2
        else:
            raise CapacityUnavailable("unknown runner override")
    expected = {
        "--model": str(
            cache
            / "blobs/sha256-02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d"
        ),
        "--host": "127.0.0.1",
        "-c": "16384",
        "-np": "1",
        "--chat-template": "chatml",
        "--no-jinja": "true",
        "--offline": "true",
        "--no-webui": "true",
    }
    if any(values.get(k) != v for k, v in expected.items()):
        raise CapacityUnavailable("actual per-slot context or renderer differs")
    fixed_optional = {
        "--mmproj": str(
            cache
            / "blobs/sha256-f836f08f921193f4d6b6a6952dba0a6fb116759d26a757bcb395d570d73976ca"
        ),
        "--load-mode": "none",
        "--flash-attn": "auto",
        "-b": str(fixed_batch or 512),
        "-ub": str(fixed_batch or 512),
        "--log-verbosity": "4",
    }
    if any(
        key in values and values[key] != expected_value
        for key, expected_value in fixed_optional.items()
    ):
        raise CapacityUnavailable("runner resource override differs")
    if fixed_batch is not None and (
        values.get("-b") != str(fixed_batch) or values.get("-ub") != str(fixed_batch)
    ):
        raise CapacityUnavailable("explicit paired runner batch differs")
    if fixed_batch == 1024:
        # Sole observed legacy shape: all official flags are present, with
        # only the ephemeral loopback port and process start varying.
        legacy = {
            **expected, **{k: v for k, v in fixed_optional.items() if k != "--load-mode"},
            "-b": "1024", "-ub": "1024",
            "--no-log-prefix": "true", "--no-log-timestamps": "true",
            "--port": values.get("--port", ""),
        }
        if values != legacy:
            raise CapacityUnavailable("unknown legacy load-only runner shape")
    if (
        not values.get("--port", "").isdecimal()
        or not 1024 <= int(values["--port"]) <= 65535
    ):
        raise CapacityUnavailable("runner endpoint differs")


class ApplicationHeavyLease:
    def __init__(
        self,
        *,
        repository: SQLiteStateRepository,
        data_root: Path,
        backup_restore: BackupRestoreService | None = None,
    ) -> None:
        self.repository, self.data_root, self.backup = (
            repository,
            data_root.absolute(),
            backup_restore,
        )
        self.fd: int | None = None
        self.gate: AbstractContextManager[bool] | None = None
        self.owner: int | None = None

    def acquire(self) -> bool:
        if self.fd is not None:
            return False
        machine = self.data_root.parent / ".local-transcription"
        try:
            machine.mkdir(mode=0o700, exist_ok=True)
            if machine.is_symlink() or machine.resolve() != machine:
                return False
            fd = os.open(
                machine / "worker.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
            )
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                return False
            self.fd, self.owner = fd, threading.get_ident()
            if self.backup is not None:
                self.gate = self.backup.background_work()
                if not self.gate.__enter__():
                    self.release()
                    return False
            if unresolved_local_work(self.repository):
                self.release()
                return False
            if not self.valid():
                self.release()
                return False
            return True
        except (OSError, ValueError, sqlite3.Error):
            self.release()
            return False

    def valid(self) -> bool:
        if self.fd is None or self.owner != threading.get_ident():
            return False
        try:
            stat = (self.data_root.parent / ".local-transcription/worker.lock").stat()
            held = os.fstat(self.fd)
            return (stat.st_dev, stat.st_ino) == (held.st_dev, held.st_ino) and (
                self.backup is None or self.backup.background_allowed
            )
        except OSError:
            return False

    def release(self) -> None:
        if self.owner is not None and self.owner != threading.get_ident():
            return
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None
        if self.gate is not None:
            self.gate.__exit__(None, None, None)
            self.gate = None
        self.owner = None


class Send(Protocol):
    def __call__(
        self, path: str, *, method: str, body: Mapping[str, object] | None = None
    ) -> Mapping[str, object]: ...


class SharedHeavyGuard:
    """Cooperating local adapters share the ASR file slot; no worker mutex."""

    def __init__(
        self,
        *,
        repository: SQLiteStateRepository,
        data_root: Path,
        backup_restore: BackupRestoreService | None = None,
    ) -> None:
        self.repository, self.data_root, self.backup = (
            repository,
            data_root,
            backup_restore,
        )
        self._local = threading.local()

    @contextmanager
    def __call__(self) -> Iterator[None]:
        active = getattr(self._local, "lease", None)
        if isinstance(active, ApplicationHeavyLease) and active.valid():
            yield
            return
        lease = ApplicationHeavyLease(
            repository=self.repository,
            data_root=self.data_root,
            backup_restore=self.backup,
        )
        if not lease.acquire():
            raise CapacityUnavailable(
                "application heavyweight slot is busy or unresolved"
            )
        self._local.lease = lease
        try:
            yield
        finally:
            self._local.lease = None
            lease.release()


class _LeasedResponse:
    def __init__(self, response: Any, gate: AbstractContextManager[None]) -> None:
        self._response, self._gate = response, gate
        self._closed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    def read(self, maximum: int) -> bytes:
        try:
            result: bytes = self._response.read(maximum)
            return result
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._response.close()
            finally:
                self._gate.__exit__(None, None, None)


def guarded_transport(
    transport: Callable[..., Any], guard: SharedHeavyGuard
) -> Callable[..., Any]:
    def send(*args: Any, **kwargs: Any) -> Any:
        gate = guard()
        gate.__enter__()
        try:
            return _LeasedResponse(transport(*args, **kwargs), gate)
        except BaseException:
            gate.__exit__(None, None, None)
            raise

    return send


@dataclass(frozen=True)
class _Ready:
    profile_id: str
    value_hash: str
    execution_id: str
    request_hash: str
    wire_hash: str
    expires: float
    host: HostObservation


def wire_bytes(request: Mapping[str, object]) -> bytes:
    return json.dumps(
        request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class LocalCapacitySession:
    def __init__(
        self,
        *,
        repository: SQLiteStateRepository,
        data_root: Path,
        backup_restore: BackupRestoreService | None = None,
        profile_id: str = PROFILE_ID,
    ) -> None:
        self._profile = resolve_profile(profile_id)
        self.repository, self.data_root = repository, data_root
        self.lease = ApplicationHeavyLease(
            repository=repository, data_root=data_root, backup_restore=backup_restore
        )
        self._ready: _Ready | None = None
        self._consumed = False
        self._armed = False

    def prepare(
        self,
        execution_id: str,
        value: VerifiedDistillationInput,
        request: Mapping[str, object],
        send: Send,
    ) -> bool:
        from youtube_intel.distillation import (
            VerifiedDistillationInput,
            build_local_distillation_request,
            verified_distillation_input_projection,
        )
        profile = self._profile
        try:
            if type(value) is not VerifiedDistillationInput or value.local_profile_id != profile.profile_id:
                return False
            expected = build_local_distillation_request(value)
            if canonical(request) != canonical(expected) or wire_bytes(request) != wire_bytes(expected):
                return False
            value_hash = digest(verified_distillation_input_projection(value))
            request_hash = digest(expected)
            wire_hash = hashlib.sha256(wire_bytes(expected)).hexdigest()
            if self._ready is not None:
                return self._ready.value_hash == value_hash and self.ready_for_claim(execution_id, request)
            bound = profile.complete_input_token_upper_bound(request)
            if not 0 < bound <= profile.options()["num_ctx"] - profile.options()["num_predict"] - 1:
                return False
            if (
                not execution_id
                or not self.lease.acquire()
            ):
                return False
            if send("/api/version", method="GET").get("version") != profile.runtime:
                raise CapacityUnavailable("runtime version differs")
            models = send("/api/tags", method="GET").get("models")
            if (
                not isinstance(models, list)
                or sum(
                    isinstance(m, dict)
                    and m.get("name") == profile.model
                    and str(m.get("digest")).removeprefix("sha256:")
                    == profile.model_digest.removeprefix("sha256:")
                    for m in models
                )
                != 1
            ):
                raise CapacityUnavailable("installed model differs")
            show = send("/api/show", method="POST", body={"model": profile.model})
            info, modelfile = show.get("model_info"), show.get("modelfile")
            if (
                show.get("system") not in (None, "")
                or show.get("messages") not in (None, [])
                or show.get("template") != "{{ .Prompt }}"
                or not isinstance(info, dict)
                or any(
                    info.get(k) != v
                    for k, v in {
                        "general.architecture": "qwen35",
                        "qwen35.context_length": 262144,
                        "tokenizer.ggml.model": "gpt2",
                        "tokenizer.ggml.pre": "qwen35",
                    }.items()
                )
                or not isinstance(modelfile, str)
                or re.findall(r"(?m)^RENDERER (\S+)\s*$", modelfile) != ["qwen3.5"]
                or re.findall(r"(?m)^PARSER (\S+)\s*$", modelfile) != ["qwen3.5"]
            ):
                raise CapacityUnavailable(
                    "renderer/tokenizer or hidden messages differ"
                )
            loaded = self._loaded(send)
            fixed = profile.profile_id == FIXED_RUNTIME_PROFILE_ID
            if fixed:
                try:
                    before = observe_host(data_root=self.data_root, loaded=loaded, profile_id=profile.profile_id)
                except CapacityUnavailable:
                    if not loaded:
                        raise
                    before = observe_load_only_reconfiguration(data_root=self.data_root)
            else:
                before = observe_host(data_root=self.data_root, loaded=loaded)
            if not before.is_current() or not self.lease.valid() or unresolved_local_work(self.repository):
                raise CapacityUnavailable("host or quiescence changed before load-only")
            if not loaded or fixed:
                response = send(
                    "/api/chat",
                    method="POST",
                    body={
                        "model": profile.model,
                        "messages": [],
                        "stream": False,
                        "think": True,
                        "truncate": False,
                        "shift": False,
                        "options": profile.options(),
                        "keep_alive": "5m",
                    },
                )
                message = response.get("message")
                if (
                    response.get("model") != profile.model
                    or response.get("done") is not True
                    or response.get("done_reason") != "load"
                    or not isinstance(message, dict)
                    or set(message) != {"role", "content"}
                    or message.get("role") not in ("assistant", "")
                    or message.get("content") != ""
                    or "error" in response
                    or any(
                        k in response
                        for k in (
                            "eval_count",
                            "prompt_eval_count",
                            "eval_duration",
                            "prompt_eval_duration",
                        )
                    )
                ):
                    raise CapacityUnavailable(
                        "load-only response is not empty load completion"
                    )
            if not self._loaded(send):
                raise CapacityUnavailable("actual model slot is unavailable")
            host = (
                observe_host(data_root=self.data_root, loaded=True, profile_id=profile.profile_id)
                if fixed else observe_host(data_root=self.data_root, loaded=True)
            )
            if fixed and (host.files != before.files or host.references != before.references or host.server != before.server):
                raise CapacityUnavailable("runtime identity changed across load-only")
            self._ready = _Ready(
                profile.profile_id,
                value_hash,
                execution_id,
                request_hash,
                wire_hash,
                monotonic() + 30,
                host,
            )
            self._consumed = False
            self._armed = False
            if not self.ready_for_claim(execution_id, request):
                raise CapacityUnavailable("readiness changed before claim")
            return True
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            self.release()
            return False

    def _loaded(self, send: Send) -> bool:
        models = send("/api/ps", method="GET").get("models")
        profile = self._profile
        if models == []:
            return False
        if (
            not isinstance(models, list)
            or len(models) != 1
            or not isinstance(models[0], dict)
            or models[0].get("name") != profile.model
            or str(models[0].get("digest")).removeprefix("sha256:")
            != profile.model_digest.removeprefix("sha256:")
            or models[0].get("runner") != "llamacpp"
        ):
            raise CapacityUnavailable("another or unknown heavyweight runner is loaded")
        if (
            type(models[0].get("context_length")) is not int
            or models[0]["context_length"] != 16384
        ):
            raise CapacityUnavailable("actual context differs")
        return True

    def matches_value(self, value: VerifiedDistillationInput) -> bool:
        """Bind transport claim/consume to the complete backend-prepared value."""
        from youtube_intel.distillation import (
            VerifiedDistillationInput,
            verified_distillation_input_projection,
        )
        return (
            self._ready is not None
            and type(value) is VerifiedDistillationInput
            and value.local_profile_id == self._profile.profile_id
            and digest(verified_distillation_input_projection(value)) == self._ready.value_hash
        )

    def ready_for_claim(self, execution_id: str, request: Mapping[str, object]) -> bool:
        ready = self._ready
        return (
            ready is not None
            and ready.profile_id == self._profile.profile_id
            and not self._armed
            and not self._consumed
            and ready.execution_id == execution_id
            and ready.request_hash == digest(request)
            and ready.wire_hash == hashlib.sha256(wire_bytes(request)).hexdigest()
            and monotonic() < ready.expires
            and self.lease.valid()
            and ready.host.is_current()
        )

    def arm(self, execution_id: str, request: Mapping[str, object]) -> None:
        if not self.ready_for_claim(execution_id, request):
            raise CapacityUnavailable("readiness expired or changed before claim")
        self._armed = True

    def consume(self, execution_id: str, request: Mapping[str, object]) -> None:
        # After SQLite claim: no HTTP/file/process metadata IO. Preclaim checks
        # already validated the host; only the held lease and sealed bytes
        # are consumed here. External clients cannot be locked by this lease.
        ready = self._ready
        if (
            ready is None
            or ready.profile_id != self._profile.profile_id
            or not self._armed
            or self._consumed
            or self.lease.fd is None
            or self.lease.owner != threading.get_ident()
            or ready.execution_id != execution_id
            or ready.request_hash != digest(request)
            or ready.wire_hash != hashlib.sha256(wire_bytes(request)).hexdigest()
        ):
            raise RuntimeError(
                "local capacity readiness is missing, stale, or consumed"
            )
        self._consumed = True

    def release(self) -> None:
        if self.lease.owner is not None and self.lease.owner != threading.get_ident():
            return
        self._ready = None
        self._armed = False
        self.lease.release()
