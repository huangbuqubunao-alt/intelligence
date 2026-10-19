"""Explicit authority for the independent tracked retry protocol, never a generic lease."""
from __future__ import annotations

import fcntl
import hashlib
import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from pathlib import Path

from youtube_intel.source_authority import managed_directory

JOB_PREFIX = "tracked-content-retry-job:"
REQUEST_PREFIX = "tracked-content-retry:"
TABLE = "tracked_content_retry_requests"


class RetryConflict(ValueError):
    """A command cannot acquire this Content's current authority."""


class RetryIntegrity(ValueError):
    """An explicit retry identity cannot be reconstructed safely."""


_AUTH: ContextVar[tuple[str, str, Callable[[], None]] | None] = ContextVar("tracked_retry_authority", default=None)
_WRITE: ContextVar[Callable[[Path, str, bytes], None] | None] = ContextVar("tracked_retry_writer", default=None)


def present(connection: sqlite3.Connection) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone() is not None


def require_job(connection: sqlite3.Connection, job_id: str) -> None:
    owned = job_id.startswith(JOB_PREFIX) or (present(connection) and connection.execute(
        "SELECT 1 FROM tracked_content_retry_requests WHERE target_job_id=? OR expected_old_job_id=?", (job_id, job_id)).fetchone() is not None)
    if owned:
        authority = _AUTH.get()
        if authority is None or authority[0] != job_id:
            raise RetryConflict("Content retry target requires its dedicated worker")
        authority[2]()


def require_provider(connection: sqlite3.Connection, request_hash: str) -> None:
    if present(connection) and connection.execute("SELECT 1 FROM tracked_content_retry_requests WHERE provider_request_hash=?", (request_hash,)).fetchone():
        authority = _AUTH.get()
        if authority is None or authority[1] != request_hash:
            raise RetryConflict("Content retry provider requires its dedicated worker")
        authority[2]()


@contextmanager
def authority(job_id: str, provider_hash: str, check: Callable[[], None], writer: Callable[[Path, str, bytes], None]) -> Iterator[None]:
    auth_token = _AUTH.set((job_id, provider_hash, check))
    write_token = _WRITE.set(writer)
    try:
        yield
    finally:
        _WRITE.reset(write_token)
        _AUTH.reset(auth_token)


def intercept_write(root: Path, relative: str, body: bytes) -> bool:
    writer = _WRITE.get()
    if writer is None:
        return False
    writer(root, relative, body)
    return True


@contextmanager
def _lock(database: Path, name: str, *, exclusive: bool) -> Iterator[None]:
    # This stable directory is outside the replaceable DATA/database payload.
    root = database.absolute().parent / ".tracked-content-retry-locks"
    with managed_directory(root, create=True) as directory:
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            # Separate atomic creation from opening an existing stable inode.
            # Contended O_CREAT without O_EXCL can return ENOENT on this host.
            descriptor = os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
        except FileExistsError:
            descriptor = os.open(name, flags, dir_fd=directory)
        try:
            own = os.fstat(descriptor)
            if not stat.S_ISREG(own.st_mode) or own.st_uid != os.getuid() or own.st_nlink != 1:
                raise RetryIntegrity("Content retry lock identity is unsafe")
            try:
                fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RetryConflict("Content retry writer or Backup is still active") from None
            named = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if (own.st_dev, own.st_ino) != (named.st_dev, named.st_ino):
                raise RetryIntegrity("Content retry lock changed")
            yield
        finally:
            # Never unlink a lock file: another inode would bypass a live lock.
            os.close(descriptor)


def store_lock(database: Path, *, exclusive: bool = False) -> AbstractContextManager[None]:
    return _lock(database, "store.lock", exclusive=exclusive)


def request_lock(database: Path, request_id: str) -> AbstractContextManager[None]:
    return _lock(database, hashlib.sha256(request_id.encode()).hexdigest() + ".lock", exclusive=True)


def generic_job_filter(connection: sqlite3.Connection, alias: str = "") -> str:
    column = (alias + "." if alias else "") + "job_id"
    result = f" AND {column} NOT GLOB 'tracked-content-retry-job:*' "
    if present(connection):
        result += f" AND {column} NOT IN (SELECT target_job_id FROM tracked_content_retry_requests UNION SELECT expected_old_job_id FROM tracked_content_retry_requests) "
    return result


class NativeTimingUnavailable(ValueError):
    """A received native body has no authoritative timed representation."""


def require_native_timing(available: bool) -> None:
    if _AUTH.get() is not None and not available:
        raise NativeTimingUnavailable("Native timed subtitles are unavailable")


def active_provider(request_hash: str) -> bool:
    value = _AUTH.get()
    if value is None or value[1] != request_hash:
        return False
    value[2]()
    return True
