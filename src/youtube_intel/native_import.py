"""Explicit AppKit selection grants and asynchronous local snapshots; no path API."""

from __future__ import annotations

import json
import os
import secrets
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from .backup_restore import BackupRestoreService
from .local_content import FORMATS, LocalContentProvider, LocalImportError
from .source_authority import (
    MAX_MEDIA_BYTES,
    MAX_TEXT_BYTES,
    managed_directory,
    safe_filename,
)

GRANT_TTL_SECONDS = 600
PICKER_TIMEOUT_SECONDS = 300
JOB_TTL_SECONDS = 1800


def macos_pick(cancelled: Callable[[], bool], *, executable: Path) -> list[Path]:
    """Only a real NSOpenPanel response authorizes a source path in production."""
    if sys.platform != "darwin":
        raise LocalImportError("LOCAL_NATIVE_PICKER_UNAVAILABLE")
    process = subprocess.Popen(
        [str(executable)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + PICKER_TIMEOUT_SECONDS
    try:
        while True:
            if cancelled():
                raise LocalImportError("LOCAL_IMPORT_CANCELLED")
            if time.monotonic() > deadline:
                raise LocalImportError("LOCAL_IMPORT_TIMEOUT")
            try:
                output, _ = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                continue
        if process.returncode or len(output) > 128 * 1024:
            raise LocalImportError("LOCAL_NATIVE_PICKER_FAILED")
        paths = json.loads(output)
        if not isinstance(paths, list) or len(paths) > 20 or any(not isinstance(path, str) or len(path) > 4096 for path in paths):
            raise LocalImportError("LOCAL_NATIVE_PICKER_FAILED")
        return [Path(path) for path in paths]
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()  # only this task-owned picker subprocess
                process.wait()


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns


@dataclass
class NativeFile:
    filename: str
    byte_count: int = 0
    phase: str = "SELECTED"
    loaded: int = 0
    method: str = "PENDING"
    error: str | None = None
    result: dict[str, object] | None = None
    processing_error: str | None = None

    def public(self) -> dict[str, object]:
        return {"filename": self.filename, "byte_count": self.byte_count,
                "phase": self.phase, "loaded": self.loaded, "snapshot_method": self.method,
                "error_code": self.error, "import": self.result,
                "processing_error_code": self.processing_error}


@dataclass
class Grant:
    source: BinaryIO
    identity: tuple[int, int, int, int, int]
    view: NativeFile


@dataclass
class NativeJob:
    job_id: str
    origin: str
    state: str = "SELECTING"
    created: float = field(default_factory=time.monotonic)
    selected: float | None = None
    files: list[NativeFile] = field(default_factory=list)
    grants: list[Grant] = field(default_factory=list)
    cancelled: threading.Event = field(default_factory=threading.Event)
    error: str | None = None
    thread: threading.Thread | None = None

    def public(self) -> dict[str, object]:
        return {"job_id": self.job_id, "state": self.state,
                "files": [item.public() for item in self.files], "error_code": self.error}


class NativeImportService:
    def __init__(self, provider: LocalContentProvider, *,
                 origins: tuple[str, ...], backup: BackupRestoreService | None = None,
                 process_saved: Callable[[str], None] | None = None,
                 picker: Callable[[Callable[[], bool]], list[Path]]) -> None:
        self.provider, self.origins, self.backup = provider, origins, backup
        self.process_saved, self.picker = process_saved, picker
        self._lock = threading.RLock()
        self._jobs: dict[str, NativeJob] = {}
        self._closed = False

    def _expire(self) -> None:
        now = time.monotonic()
        for key, job in list(self._jobs.items()):
            if job.state == "SELECTED" and job.selected is not None and now - job.selected > GRANT_TTL_SECONDS:
                self._close_grants(job)
                job.state, job.error = "FAILED", "LOCAL_SELECTION_EXPIRED"
            if job.state not in {"SELECTING", "IMPORTING", "SELECTED"} and now - job.created > JOB_TTL_SECONDS:
                del self._jobs[key]

    @staticmethod
    def _close_grants(job: NativeJob) -> None:
        for grant in job.grants:
            grant.source.close()
        job.grants.clear()

    def choose(self, origin: str) -> dict[str, object]:
        with self._lock:
            self._expire()
            if self._closed or origin not in self.origins:
                raise LocalImportError("LOCAL_NATIVE_ACCESS_REJECTED")
            if any(job.state in {"SELECTING", "IMPORTING", "SELECTED"} for job in self._jobs.values()):
                raise LocalImportError("LOCAL_IMPORT_BUSY")
            # Bound UI history without blocking new selections after 16 batches.
            while len(self._jobs) >= 16:
                del self._jobs[next(iter(self._jobs))]
            job = NativeJob(secrets.token_urlsafe(32), origin)
            self._jobs[job.job_id] = job
            job.thread = threading.Thread(target=self._pick, args=(job,), daemon=True, name="local-native-picker")
            job.thread.start()
            return job.public()

    def _pick(self, job: NativeJob) -> None:
        grants: list[Grant] = []
        files: list[NativeFile] = []
        try:
            paths = self.picker(job.cancelled.is_set)
            if len(paths) > 20:
                raise LocalImportError("LOCAL_SELECTION_TOO_MANY")
            for path in paths:
                name = safe_filename(path.name)
                view = NativeFile(name)
                files.append(view)
                try:
                    if not path.is_absolute() or ".." in path.parts:
                        raise LocalImportError("LOCAL_FILE_UNREADABLE")
                    extension = path.suffix.lower()
                    if extension not in FORMATS:
                        raise LocalImportError("LOCAL_UNSUPPORTED_FORMAT")
                    with managed_directory(path.parent) as directory:
                        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                    source = os.fdopen(fd, "rb")
                    try:
                        metadata = os.fstat(fd)
                        view.byte_count = metadata.st_size
                        if not stat.S_ISREG(metadata.st_mode):
                            raise LocalImportError("LOCAL_FILE_UNREADABLE")
                        if not metadata.st_size:
                            raise LocalImportError("LOCAL_EMPTY_FILE")
                        maximum = MAX_TEXT_BYTES if FORMATS[extension] == "TEXT" else MAX_MEDIA_BYTES
                        if metadata.st_size > maximum:
                            raise LocalImportError("LOCAL_FILE_TOO_LARGE")
                        grants.append(Grant(source, _identity(metadata), view))
                    except BaseException:
                        source.close()
                        raise
                except LocalImportError as error:
                    view.phase, view.error = "FAILED", error.code
                except (OSError, ValueError):
                    view.phase, view.error = "FAILED", "LOCAL_FILE_UNREADABLE"
            with self._lock:
                job.files = files
                job.grants = grants
                job.selected = time.monotonic()
                job.state = "SELECTED" if grants else "FAILED" if paths else "CANCELLED"
                if job.cancelled.is_set() or self._closed:
                    self._close_grants(job)
                    job.state = "CANCELLED"
                else:
                    expiry = threading.Timer(GRANT_TTL_SECONDS + 1, self._expire_selected)
                    expiry.daemon = True
                    expiry.start()
        except Exception as error:
            for grant in grants:
                grant.source.close()
            with self._lock:
                if isinstance(error, LocalImportError) and error.code == "LOCAL_IMPORT_CANCELLED":
                    job.state, job.error = "CANCELLED", None
                else:
                    job.state, job.error = "FAILED", error.code if isinstance(error, LocalImportError) else "LOCAL_NATIVE_PICKER_FAILED"

    def _job(self, job_id: str, origin: str) -> NativeJob:
        self._expire()
        job = self._jobs.get(job_id)
        if job is None or job.origin != origin:
            raise LocalImportError("LOCAL_SELECTION_EXPIRED")
        return job

    def _expire_selected(self) -> None:
        with self._lock:
            self._expire()

    def status(self, job_id: str, origin: str) -> dict[str, object]:
        with self._lock:
            return self._job(job_id, origin).public()

    def jobs(self, origin: str) -> list[dict[str, object]]:
        with self._lock:
            self._expire()
            return [job.public() for job in self._jobs.values() if job.origin == origin and job.state != "SELECTED"]

    def confirm(self, job_id: str, origin: str) -> dict[str, object]:
        with self._lock:
            job = self._job(job_id, origin)
            if job.state != "SELECTED" or not job.grants or self._closed:
                raise LocalImportError("LOCAL_SELECTION_EXPIRED")
            job.state = "IMPORTING"  # consumes the one-use grant before dispatch
            job.thread = threading.Thread(target=self._run, args=(job,), daemon=True, name="local-native-snapshot")
            job.thread.start()
            return job.public()

    def _run(self, job: NativeJob) -> None:
        try:
            window = self.backup.background_work(native_import=True) if self.backup else nullcontext(True)
            with window as allowed:
                if not allowed:
                    raise LocalImportError("LOCAL_IMPORT_BUSY")
                for grant in job.grants:
                    view = grant.view
                    def progress(phase: str, loaded: int, total: int, method: str) -> None:
                        with self._lock:
                            view.phase, view.loaded, view.byte_count, view.method = phase, loaded, total, method
                    try:
                        if job.cancelled.is_set():
                            raise LocalImportError("LOCAL_IMPORT_CANCELLED")
                        if _identity(os.fstat(grant.source.fileno())) != grant.identity:
                            raise LocalImportError("LOCAL_SELECTED_FILE_CHANGED")
                        result = self.provider.import_selected(view.filename, grant.source,
                                    cancelled=job.cancelled.is_set, progress=progress)
                        with self._lock:
                            view.result, view.phase = result.as_dict(), "SAVED"
                            view.processing_error = result.processing_error_code
                        if self.process_saved and result.status != "READY":
                            try:
                                self.process_saved(result.content_id)
                            except Exception:
                                view.processing_error = "LOCAL_PROCESSING_UNAVAILABLE"
                    except Exception as error:
                        with self._lock:
                            view.phase, view.error = "FAILED", error.code if isinstance(error, LocalImportError) else "LOCAL_FILE_UNREADABLE"
            with self._lock:
                job.state = "COMPLETE"
        except Exception as error:
            with self._lock:
                job.state, job.error = "FAILED", error.code if isinstance(error, LocalImportError) else "LOCAL_FILE_UNREADABLE"
        finally:
            with self._lock:
                self._close_grants(job)

    def cancel(self, job_id: str, origin: str) -> dict[str, object]:
        with self._lock:
            job = self._job(job_id, origin)
            job.cancelled.set()
            if job.state == "SELECTED":
                self._close_grants(job)
                job.state = "CANCELLED"
            return job.public()

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            for job in self._jobs.values():
                job.cancelled.set()
                if job.state == "SELECTED":
                    self._close_grants(job)
            threads = [job.thread for job in self._jobs.values() if job.thread]
        for thread in threads:
            thread.join(timeout=25)
