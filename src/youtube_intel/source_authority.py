"""Provider-neutral immutable source snapshots and exact-text range authority."""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Protocol, cast

if TYPE_CHECKING:
    from youtube_intel.state import SQLiteStateRepository, VerifiedEvidenceText

MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_MEDIA_BYTES = 2 * 1024 * 1024 * 1024
IO_CHUNK_BYTES = 1024 * 1024
DISK_RESERVE_BYTES = 256 * 1024 * 1024
IMPORT_DEADLINE_SECONDS = 2 * 60 * 60
SOURCE_CONTRACT = "source-snapshot-v1"


class ChunkReader(Protocol):
    def read(self, size: int = -1) -> bytes: ...


class BytesReader:
    """Compatibility bytes inputs retain one source buffer, copying only chunks."""
    def __init__(self, payload: bytes) -> None:
        self.view = memoryview(payload)
        self.offset = 0

    def read(self, size: int = -1) -> bytes:
        if not 0 < size <= IO_CHUNK_BYTES:
            raise ValueError("unbounded byte read")
        chunk = self.view[self.offset:self.offset + size].tobytes()
        self.offset += len(chunk)
        return chunk


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_space(descriptor: int, required: int) -> None:
    space = os.fstatvfs(descriptor)
    if space.f_bavail * space.f_frsize < required + DISK_RESERVE_BYTES:
        raise OSError(28, "Insufficient local disk space")


def cleanup_abandoned_imports(root: Path) -> None:
    """Only reserved staging entries with no live writer lock may be retired."""
    try:
        with managed_directory(root) as directory:
            try:
                fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            for name in os.listdir(directory):
                if re.fullmatch(r"\.import-[0-9a-f]{32}", name) is None:
                    continue
                try:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                except OSError:
                    continue
                try:
                    own = os.fstat(fd)
                    if not stat.S_ISREG(own.st_mode):
                        continue
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    current = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if (current.st_dev, current.st_ino) == (own.st_dev, own.st_ino):
                        os.unlink(name, dir_fd=directory)
                finally:
                    os.close(fd)
    except FileNotFoundError:
        pass


@contextmanager
def managed_directory(root: Path, relative: str = "", *, create: bool = False) -> Iterator[int]:
    parts = relative.split("/") if relative else []
    if any(not p or p in {".", ".."} or "\\" in p or ":" in p for p in parts):
        raise ValueError("invalid source artifact path")
    # Walk the absolute root too: O_NOFOLLOW on the final component alone does
    # not protect against a symlink in an ancestor directory.
    absolute = root.absolute()
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in [*absolute.parts[1:], *parts]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def open_managed(root: Path, relative: str, *, maximum: int) -> Iterator[BinaryIO]:
    parts = relative.split("/")
    if any(not p or p in {".", ".."} or "\\" in p or ":" in p for p in parts):
        raise ValueError("invalid source artifact path")
    with managed_directory(root, "/".join(parts[:-1])) as directory:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
                raise ValueError("source artifact exceeds policy")
            yield stream
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("source artifact changed while reading")


def hash_managed(root: Path, relative: str, *, maximum: int) -> tuple[int, str]:
    with open_managed(root, relative, maximum=maximum) as stream:
        hasher = hashlib.sha256()
        size = 0
        while chunk := stream.read(IO_CHUNK_BYTES):
            size += len(chunk)
            if size > maximum:
                raise ValueError("source artifact exceeds policy")
            hasher.update(chunk)
        if size != os.fstat(stream.fileno()).st_size:
            raise ValueError("source artifact changed while reading")
        return size, hasher.hexdigest()


@dataclass(frozen=True)
class StagedFile:
    root: Path
    name: str
    size: int
    digest: str
    directory: int
    stream: BinaryIO

    @property
    def path(self) -> Path:
        return self.root / self.name

    def publish(self, root: Path, relative: str) -> bool:
        # Hash the pinned inode, never reopen its replaceable pathname.
        before = os.fstat(self.stream.fileno())
        self.stream.seek(0)
        hasher = hashlib.sha256()
        size = 0
        while chunk := self.stream.read(IO_CHUNK_BYTES):
            hasher.update(chunk)
            size += len(chunk)
            if size > self.size:
                raise ValueError("staged file grew during validation")
        after = os.fstat(self.stream.fileno())
        def identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
            return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
        named = os.stat(self.name, dir_fd=self.directory, follow_symlinks=False)
        if (size, hasher.hexdigest()) != (self.size, self.digest) or identity(before) != identity(after) or identity(named) != identity(after) or not stat.S_ISREG(named.st_mode):
            raise ValueError("staged file changed during validation")
        parts = relative.split("/")
        if any(not p or p in {".", ".."} or "\\" in p or ":" in p for p in parts):
            raise ValueError("invalid source artifact path")
        with managed_directory(root, "/".join(parts[:-1]), create=True) as directory:
            try:
                os.link(self.name, parts[-1], src_dir_fd=self.directory, dst_dir_fd=directory, follow_symlinks=False)
            except FileExistsError:
                if hash_managed(root, relative, maximum=self.size) != (self.size, self.digest):
                    raise ValueError("immutable source artifact conflict") from None
                return False
            linked = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
            try:
                if not stat.S_ISREG(linked.st_mode) or (linked.st_dev, linked.st_ino) != (after.st_dev, after.st_ino):
                    raise ValueError("published source inode changed")
                # A hard link changes ctime. Size/mtime and full bytes must remain exact.
                if hash_managed(root, relative, maximum=self.size) != (self.size, self.digest):
                    raise ValueError("published source bytes changed")
                os.fsync(directory)
            except BaseException:
                current = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (linked.st_dev, linked.st_ino):
                    os.unlink(parts[-1], dir_fd=directory)
                raise
            return True

    def remove_uncommitted(self, root: Path, relative: str) -> None:
        """Remove only a new link still pointing to this attempt's private inode."""
        parts = relative.split("/")
        with managed_directory(root, "/".join(parts[:-1])) as directory:
            own = os.fstat(self.stream.fileno())
            current = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (own.st_dev, own.st_ino):
                os.unlink(parts[-1], dir_fd=directory)
                os.fsync(directory)


@contextmanager
def stage_stream(root: Path, source: ChunkReader, length: int, *, maximum: int,
                 cancelled: Callable[[], bool] | None = None,
                 progress: Callable[[int], None] | None = None) -> Iterator[StagedFile]:
    if not 0 < length <= maximum:
        raise ValueError("file size outside policy")
    with managed_directory(root, create=True) as directory:
        fcntl.flock(directory, fcntl.LOCK_SH)
        require_space(directory, length)
        name = ".import-" + uuid.uuid4().hex
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_EXLOCK", 0), 0o600, dir_fd=directory)
        own = os.fstat(fd)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            hasher = hashlib.sha256()
            size = 0
            deadline = time.monotonic() + IMPORT_DEADLINE_SECONDS
            with os.fdopen(fd, "w+b") as output:
                while size < length:
                    if cancelled and cancelled():
                        raise InterruptedError("Local snapshot was cancelled")
                    if time.monotonic() > deadline:
                        raise TimeoutError("Local import exceeded its time limit")
                    # read1 returns one available receive, allowing deadline
                    # checks even when a client trickles less than a full chunk.
                    reader = getattr(source, "read1", source.read)
                    chunk = reader(min(IO_CHUNK_BYTES, length - size))
                    if time.monotonic() > deadline:
                        raise TimeoutError("Local import exceeded its time limit")
                    if not chunk:
                        raise EOFError("Selected file upload is incomplete")
                    if len(chunk) > min(IO_CHUNK_BYTES, length - size):
                        raise ValueError("source returned more than requested")
                    require_space(directory, len(chunk))
                    output.write(chunk)
                    hasher.update(chunk)
                    size += len(chunk)
                    if progress:
                        progress(size)
                output.flush()
                os.fsync(output.fileno())
                if cancelled and cancelled():
                    raise InterruptedError("Local snapshot was cancelled")
                yield StagedFile(root, name, size, hasher.hexdigest(), directory, output)
        finally:
            _unlink_owned(directory, name, own)


def _unlink_owned(directory: int, name: str, own: os.stat_result) -> None:
    """Cancellation removes only the inode created by this attempt."""
    try:
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (current.st_dev, current.st_ino) == (own.st_dev, own.st_ino):
            os.unlink(name, dir_fd=directory)
    except FileNotFoundError:
        pass


def clone_descriptor(source: int, directory: int, name: str) -> bool:
    """Atomic macOS CoW clone from an already authorized, pinned descriptor."""
    metadata = os.fstat(source)
    immutable = stat.UF_IMMUTABLE | stat.UF_APPEND | stat.SF_IMMUTABLE | stat.SF_APPEND
    if sys.platform != "darwin" or metadata.st_dev != os.fstat(directory).st_dev or getattr(metadata, "st_flags", 0) & immutable:
        return False
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    clone = getattr(library, "fclonefileat", None)
    if clone is None:
        return False
    clone.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32)
    clone.restype = ctypes.c_int
    # CLONE_NOOWNERCOPY; no pathname resolution for the source or parent.
    if clone(source, directory, name.encode(), 2) == 0:
        return True
    error = ctypes.get_errno()
    if error in {errno.ENOTSUP, errno.EXDEV, errno.ENOSYS}:
        return False
    raise OSError(error, "Local CoW snapshot failed")


@contextmanager
def stage_native(root: Path, source: BinaryIO, *, maximum: int,
                 cancelled: Callable[[], bool],
                 progress: Callable[[str, int, int, str], None]) -> Iterator[StagedFile]:
    """Clone first; unsupported volumes copy in bounded chunks off the UI thread."""
    before = os.fstat(source.fileno())
    length = before.st_size
    if not stat.S_ISREG(before.st_mode) or not 0 < length <= maximum:
        raise ValueError("file size outside policy")
    with managed_directory(root, create=True) as directory:
        fcntl.flock(directory, fcntl.LOCK_SH)
        # Reserve a full file even for CoW, protecting later private writes.
        require_space(directory, length)
        name = ".import-" + uuid.uuid4().hex
        progress("SNAPSHOTTING", 0, length, "PENDING")
        if cancelled():
            raise InterruptedError("Local snapshot was cancelled")
        cloned = clone_descriptor(source.fileno(), directory, name)
        if not cloned:
            source.seek(0)
            with stage_stream(root, source, length, maximum=maximum, cancelled=cancelled,
                              progress=lambda value: progress("COPYING", value, length, "STREAM_COPY")) as staged:
                after = os.fstat(source.fileno())
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    raise ValueError("selected source changed during copying")
                progress("VERIFYING", length, length, "STREAM_COPY")
                yield staged
            return
        own = os.stat(name, dir_fd=directory, follow_symlinks=False)
        try:
            after = os.fstat(source.fileno())
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise ValueError("selected source changed during cloning")
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_EXLOCK", 0), dir_fd=directory)
            with os.fdopen(fd, "rb") as output:
                fcntl.flock(output.fileno(), fcntl.LOCK_EX)
                os.fchmod(output.fileno(), 0o600)
                if os.fstat(output.fileno()).st_ino == before.st_ino:
                    raise ValueError("clone must have an independent inode")
                digest = hashlib.sha256()
                count = 0
                deadline = time.monotonic() + IMPORT_DEADLINE_SECONDS
                progress("VERIFYING", 0, length, "APFS_CLONE")
                while chunk := output.read(IO_CHUNK_BYTES):
                    if cancelled():
                        raise InterruptedError("Local snapshot was cancelled")
                    if time.monotonic() > deadline:
                        raise TimeoutError("Local verification exceeded its time limit")
                    digest.update(chunk)
                    count += len(chunk)
                    if count > length:
                        raise ValueError("clone changed during hashing")
                    progress("VERIFYING", count, length, "APFS_CLONE")
                if count != length:
                    raise ValueError("clone size mismatch")
                os.fsync(output.fileno())
                yield StagedFile(root, name, length, digest.hexdigest(), directory, output)
        finally:
            _unlink_owned(directory, name, own)


def read_managed(root: Path, relative: str, *, maximum: int) -> bytes:
    """Read only a bounded regular file under DATA, without following symlinks."""
    parts = relative.split("/")
    if not parts or any(
        not p or p in {".", ".."} or "\\" in p or ":" in p for p in parts
    ):
        raise ValueError("invalid source artifact path")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = child
        fd = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
        )
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
                raise ValueError("source artifact exceeds policy")
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) or len(data) != before.st_size:
                raise ValueError("source artifact changed while reading")
            return data
    finally:
        os.close(descriptor)


def write_managed(root: Path, relative: str, data: bytes) -> None:
    """Atomically publish once; identical retries never rewrite existing bytes."""
    from youtube_intel.tracked_retry_context import intercept_write

    if intercept_write(root, relative, data):
        return
    parts = relative.split("/")
    if any(not p or p in {".", ".."} or "\\" in p or ":" in p for p in parts):
        raise ValueError("invalid source artifact path")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = child
        # Complete and fsync a private staging inode before atomic publication.
        temporary = ".import-" + uuid.uuid4().hex
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=descriptor,
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(
                    temporary,
                    parts[-1],
                    src_dir_fd=descriptor,
                    dst_dir_fd=descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError:
                if read_managed(root, relative, maximum=len(data)) != data:
                    raise ValueError("immutable source artifact conflict") from None
            os.fsync(descriptor)
        finally:
            os.unlink(
                temporary, dir_fd=descriptor
            )  # only this private application staging file
    finally:
        os.close(descriptor)


def verify_source(
    repository: SQLiteStateRepository, connection: sqlite3.Connection, content_id: str
) -> sqlite3.Row | None:
    """Reverify persisted ownership, hash, canonical text and immutable bytes."""
    row = connection.execute(
        "SELECT * FROM content_source_snapshots WHERE content_id=?", (content_id,)
    ).fetchone()
    if row is None:
        return None
    root = repository._source_data_root
    if root is None:
        return None
    try:
        video = connection.execute(
            "SELECT provider,availability FROM videos WHERE video_id=?", (content_id,)
        ).fetchone()
        source = connection.execute(
            "SELECT provider FROM source_subscriptions WHERE source_id=?",
            (row["source_id"],),
        ).fetchone()
        if (
            video is None
            or source is None
            or video["provider"] != row["provider"]
            or source["provider"] != row["provider"]
            or video["availability"] != "public"
        ):
            return None
        if row["provider"] != "BILIBILI" and (row["source_identity"] != "sha256:" + row["source_hash"] or (
            row["provider"] == "LOCAL" and content_id != "local-" + row["source_hash"]
        )):
            return None
        artifact = connection.execute(
            "SELECT * FROM artifacts WHERE artifact_id=?",
            (row["snapshot_artifact_id"],),
        ).fetchone()
        if (
            artifact is None
            or artifact["video_id"] != content_id
            or artifact["storage_root"] != "DATA"
            or artifact["deleted_at"] is not None
            or artifact["content_hash"] != row["source_hash"]
            or artifact["provider"] != row["provider"]
        ):
            return None
        if row["provider"] == "LOCAL" and row["media_kind"] != "TEXT":
            size, digest = hash_managed(root, artifact["relative_path"], maximum=MAX_MEDIA_BYTES)
            data = b""
        else:
            data = read_managed(
            root,
            artifact["relative_path"],
            maximum=(256 * 1024 if row["provider"] == "BILIBILI" else
                     MAX_MEDIA_BYTES if row["media_kind"] != "TEXT" else MAX_TEXT_BYTES),
            )
            size, digest = len(data), sha256(data)
        if size != row["byte_count"] or digest != row["source_hash"]:
            return None
        network_snapshot = None
        if row["provider"] == "BILIBILI":
            from youtube_intel.providers.bilibili import normalize_input
            network_snapshot = json.loads(data)
            identity = normalize_input(network_snapshot["bvid"])
            if (network_snapshot["contract"] != "bilibili-public-metadata-v1"
                or identity.content_id != content_id or row["source_identity"] != "bvid:" + identity.bvid
                or network_snapshot["content_id"] != content_id
                or network_snapshot["canonical_url"] != identity.canonical_url
                or network_snapshot["duration_seconds"] != row["duration_seconds"]
                or network_snapshot["title"] != row["filename"]
                or row["media_kind"] != "VIDEO" or row["format"] != ".json"):
                return None
        if row["status"] == "READY":
            canonical = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id=?",
                (row["canonical_artifact_id"],),
            ).fetchone()
            if (
                canonical is None
                or canonical["video_id"] != content_id
                or canonical["kind"] != "transcript_canonical"
                or canonical["storage_root"] != "DATA"
                or canonical["deleted_at"] is not None
                or canonical["content_hash"] != row["canonical_text_hash"]
                or canonical["provider"] != row["provider"]
            ):
                return None
            text = read_managed(
                root, canonical["relative_path"], maximum=MAX_TEXT_BYTES
            ).decode("utf-8")
            if (
                text != row["canonical_text"]
                or sha256(text.encode("utf-8")) != row["canonical_text_hash"]
            ):
                return None
            if row["media_kind"] == "TEXT":
                if (
                    text != data.decode("utf-8")
                    or row["transcript_provenance"] != "utf-8-exact-v1"
                ):
                    return None
            else:
                from youtube_intel.state import (
                    TimedTranscriptCueWrite,
                    build_timed_transcript_hash,
                )

                timed = connection.execute(
                    "SELECT * FROM timed_transcripts WHERE video_id=? AND canonical_artifact_id=?",
                    (content_id, row["canonical_artifact_id"]),
                ).fetchone()
                if (
                    timed is None
                    or not row["transcript_provenance"]
                    or not row["duration_seconds"]
                ):
                    return None
                cues = connection.execute(
                    "SELECT * FROM timed_transcript_cues WHERE timed_transcript_id=? ORDER BY cue_index",
                    (timed["timed_transcript_id"],),
                ).fetchall()
                if not cues or "\n".join(c["cue_text"] for c in cues) != text:
                    return None
                previous_end = 0
                writes = []
                for index, cue in enumerate(cues):
                    if (
                        type(cue["start_ms"]) is not int
                        or type(cue["end_ms"]) is not int
                        or cue["cue_index"] != index
                        or cue["start_ms"] < previous_end
                        or cue["end_ms"] <= cue["start_ms"]
                        or cue["end_ms"] > row["duration_seconds"] * 1000 + 1000
                        or sha256(cue["cue_text"].encode("utf-8"))
                        != cue["cue_text_hash"]
                    ):
                        return None
                    writes.append(
                        TimedTranscriptCueWrite(
                            start_ms=cue["start_ms"],
                            end_ms=cue["end_ms"],
                            text=cue["cue_text"],
                        )
                    )
                    previous_end = cue["end_ms"]
                if (
                    build_timed_transcript_hash(tuple(writes))
                    != timed["timed_transcript_hash"]
                ):
                    return None
                provenance = connection.execute(
                    "SELECT * FROM artifacts WHERE artifact_id=?",
                    (row["provenance_artifact_id"],),
                ).fetchone()
                if (
                    provenance is None
                    or provenance["video_id"] != content_id
                    or provenance["provider"] != row["provider"]
                    or provenance["storage_root"] != "DATA"
                    or provenance["deleted_at"] is not None
                ):
                    return None
                envelope_bytes = read_managed(
                    root, provenance["relative_path"], maximum=65536
                )
                expected = {
                    "contract": "source-transcript-provenance-v1",
                    "content_id": content_id,
                    "source_hash": row["source_hash"],
                    "canonical_text_hash": row["canonical_text_hash"],
                    "timed_transcript_hash": timed["timed_transcript_hash"],
                    "language": row["language"],
                    "duration_seconds": row["duration_seconds"],
                    "transcriber": row["transcript_provenance"],
                }
                envelope = json.loads(envelope_bytes)
                if isinstance(envelope, dict) and envelope.get("contract") == "source-transcript-provenance-v3":
                    from youtube_intel.providers.bilibili import (
                        parse_captions,
                        validate_request_url,
                    )
                    if network_snapshot is None or row["provider"] != "BILIBILI":
                        return None
                    raw_id, raw_hash = envelope.get("raw_artifact_id"), envelope.get("raw_output_hash")
                    acquisition = envelope.get("acquisition")
                    if not isinstance(raw_id, str) or not isinstance(raw_hash, str) or not isinstance(acquisition, dict):
                        return None
                    if (acquisition.get("provider") != "BILIBILI" or acquisition.get("bvid") != network_snapshot["bvid"]
                        or acquisition.get("cid") != network_snapshot["cid"]
                        or set(acquisition) != {"provider", "bvid", "cid", "subtitle_id", "language_name", "source_url", "acquired_at"}):
                        return None
                    host, _ = validate_request_url(acquisition["source_url"])
                    if host == "api.bilibili.com" or not isinstance(acquisition["subtitle_id"], str) or not re.fullmatch(r"[0-9]{1,30}", acquisition["subtitle_id"]) or not isinstance(acquisition["language_name"], str) or not isinstance(acquisition["acquired_at"], str):
                        return None
                    acquired_at = datetime.fromisoformat(acquisition["acquired_at"].replace("Z", "+00:00"))
                    if acquired_at.tzinfo is None:
                        return None
                    raw_artifact = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?", (raw_id,)).fetchone()
                    if (raw_artifact is None or raw_artifact["video_id"] != content_id or raw_artifact["provider"] != "BILIBILI"
                        or raw_artifact["kind"] != "subtitle_source"
                        or raw_artifact["storage_root"] != "DATA" or raw_artifact["deleted_at"] is not None or raw_artifact["content_hash"] != raw_hash):
                        return None
                    raw_output = read_managed(root, raw_artifact["relative_path"], maximum=MAX_TEXT_BYTES)
                    parsed = parse_captions(raw_output, language=row["language"], duration=row["duration_seconds"])
                    if sha256(raw_output) != raw_hash or parsed.cues != tuple(writes) or parsed.provenance != row["transcript_provenance"]:
                        return None
                    expected.update(contract="source-transcript-provenance-v3", raw_artifact_id=raw_id, raw_output_hash=raw_hash, acquisition=acquisition)
                elif row["provider"] == "BILIBILI":
                    return None
                if isinstance(envelope, dict) and envelope.get("contract") == "source-transcript-provenance-v2":
                    from youtube_intel.offline_transcription import (
                        MAX_RESULT,
                        validate_result,
                    )
                    raw_id = envelope.get("raw_artifact_id")
                    raw_hash = envelope.get("raw_output_hash")
                    if not isinstance(raw_id, str) or not isinstance(raw_hash, str):
                        return None
                    raw_artifact = connection.execute("SELECT * FROM artifacts WHERE artifact_id=?", (raw_id,)).fetchone()
                    if (raw_artifact is None or raw_artifact["video_id"] != content_id
                        or raw_artifact["provider"] != row["provider"] or raw_artifact["storage_root"] != "DATA"
                        or raw_artifact["deleted_at"] is not None or raw_artifact["content_hash"] != raw_hash):
                        return None
                    raw_output = read_managed(root, raw_artifact["relative_path"], maximum=MAX_RESULT)
                    if sha256(raw_output) != raw_hash:
                        return None
                    parsed = validate_result(raw_output, duration_seconds=row["duration_seconds"], provenance=row["transcript_provenance"])
                    if parsed.cues != tuple(writes) or parsed.language != row["language"]:
                        return None
                    expected.update(contract="source-transcript-provenance-v2", raw_artifact_id=raw_id, raw_output_hash=raw_hash)
                if sha256(envelope_bytes) != provenance["content_hash"] or envelope != expected:
                    return None
        return cast(sqlite3.Row, row)
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, RecursionError):
        return None


def text_evidence_id(
    *,
    content_id: str,
    artifact_id: str,
    start_offset: int,
    end_offset: int,
    lineage_kind: str = "ORIGINAL_TRANSCRIPT",
    role: str = "PRIMARY_ORIGINAL",
) -> str:
    from youtube_intel.research_contract import digest

    if not 0 <= start_offset < end_offset:
        raise ValueError("invalid source range")
    return digest(
        [
            SOURCE_CONTRACT,
            content_id,
            artifact_id,
            "TEXT_RANGE",
            start_offset,
            end_offset,
            lineage_kind,
            role,
        ]
    )


def resolve_source_range(
    repository: SQLiteStateRepository, connection: sqlite3.Connection, evidence_id: str
) -> VerifiedEvidenceText | None:
    from youtube_intel.state import VerifiedEvidenceText

    row = connection.execute(
        "SELECT e.*,b.canonical_artifact_id,b.excerpt,b.excerpt_hash,b.source_text_hash,b.source_content_hash FROM evidence e JOIN evidence_source_ranges b USING(evidence_id) WHERE e.evidence_id=?",
        (evidence_id,),
    ).fetchone()
    if (
        row is None
        or row["locator_type"] != "TEXT_RANGE"
        or row["availability"] != "AVAILABLE"
    ):
        return None
    source = verify_source(repository, connection, row["video_id"])
    if source is None or source["status"] != "READY" or source["media_kind"] != "TEXT":
        return None
    start, end = row["start_offset"], row["end_offset"]
    text = source["canonical_text"]
    if (
        not isinstance(start, int)
        or not isinstance(end, int)
        or not 0 <= start < end <= len(text)
    ):
        return None
    if (
        row["artifact_id"] != source["canonical_artifact_id"]
        or row["canonical_artifact_id"] != row["artifact_id"]
        or row["source_text_hash"] != source["canonical_text_hash"]
        or row["source_content_hash"] != source["source_hash"]
    ):
        return None
    if (
        text[start:end] != row["excerpt"]
        or sha256(row["excerpt"].encode("utf-8")) != row["excerpt_hash"]
        or row["source_excerpt"] != row["excerpt"]
    ):
        return None
    if evidence_id != text_evidence_id(
        content_id=row["video_id"],
        artifact_id=row["artifact_id"],
        start_offset=start,
        end_offset=end,
        lineage_kind=row["lineage_kind"],
        role=row["role"],
    ):
        return None
    return VerifiedEvidenceText(
        evidence_id=evidence_id,
        video_id=row["video_id"],
        timed_transcript_id="",
        timed_transcript_hash=source["canonical_text_hash"],
        start_ms=None,
        end_ms=None,
        excerpt=row["excerpt"],
        excerpt_hash=row["excerpt_hash"],
        locator_type="TEXT_RANGE",
        start_offset=start,
        end_offset=end,
        start_line=1 + text.count("\n", 0, start),
        end_line=1 + text.count("\n", 0, end - 1),
        source_content_hash=source["source_hash"],
    )


def safe_filename(value: str) -> str:
    # Paths and Unicode format/control characters are metadata, never identity.
    value = re.split(r"[/\\]", value)[-1]
    import unicodedata

    value = "".join(
        c for c in value if unicodedata.category(c) not in {"Cc", "Cf", "Cs"}
    )
    return value.strip()[:240] or "file"


@lru_cache(maxsize=3)
def _expected_source_schema(version: int) -> tuple[tuple[str, str], ...]:
    from youtube_intel.state import SQLiteStateRepository

    expected = sqlite3.connect(":memory:")
    try:
        expected.execute("PRAGMA legacy_alter_table=ON")
        for migration in SQLiteStateRepository(Path(":memory:"))._load_migrations():
            if migration.version <= version:
                expected.executescript(migration.sql)
        return _source_schema(expected)
    finally:
        expected.close()


def _source_schema(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    tables = (
        "videos",
        "source_subscriptions",
        "evidence",
        "content_source_snapshots",
        "evidence_source_ranges",
        "evidence_search_text",
        "source_tracking_state",
        "source_observations",
        "source_checks",
    )
    marks = ",".join("?" for _ in tables)
    return tuple(
        (r[0], "".join(r[1].split()).rstrip(";"))
        for r in connection.execute(
            f"SELECT name,sql FROM sqlite_master WHERE tbl_name IN ({marks}) AND sql IS NOT NULL ORDER BY name",
            tables,
        )
    )


def verify_source_schema(connection: sqlite3.Connection) -> None:
    """Restore requires the packaged constraints, not just matching row hashes."""
    if _source_schema(connection) != _expected_source_schema(int(connection.execute("PRAGMA user_version").fetchone()[0])):
        raise ValueError("source authority schema is incompatible")
