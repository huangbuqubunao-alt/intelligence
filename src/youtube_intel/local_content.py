"""Explicit Local provider import, unified Content and immutable DATA artifacts."""

from __future__ import annotations

import errno
import json
import math
import os
import stat
import subprocess
import threading
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Protocol

from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.source_authority import (
    MAX_MEDIA_BYTES,
    MAX_TEXT_BYTES,
    BytesReader,
    ChunkReader,
    StagedFile,
    cleanup_abandoned_imports,
    open_managed,
    read_managed,
    safe_filename,
    stage_native,
    stage_stream,
    verify_source,
)
from youtube_intel.source_publication import SourceContentPublisher
from youtube_intel.source_transcript import MediaTranscript as MediaTranscript
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    StorageRoot,
    format_utc_datetime,
)

FORMATS = {
    ".txt": "TEXT",
    ".md": "TEXT",
    ".mp3": "AUDIO",
    ".m4a": "AUDIO",
    ".wav": "AUDIO",
    ".mp4": "VIDEO",
    ".mov": "VIDEO",
    ".m4v": "VIDEO",
}
LOCAL_SOURCE_ID = "local-library"
_IMPORT_LOCK = threading.RLock()


class LocalImportError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def validate_media_transcript(transcript: MediaTranscript, duration: float) -> None:
    if not isinstance(transcript, MediaTranscript) or not 1 <= len(transcript.cues) <= 4096:
        raise ValueError("invalid transcript")
    if not isinstance(transcript.language, str) or not transcript.language.strip() or len(transcript.language) > 64:
        raise ValueError("invalid language")
    if not isinstance(transcript.provenance, str) or not transcript.provenance.strip() or len(transcript.provenance) > 4096:
        raise ValueError("invalid provenance")
    previous = 0
    for cue in transcript.cues:
        if (type(cue.start_ms) is not int or type(cue.end_ms) is not int
            or cue.start_ms < previous or cue.end_ms <= cue.start_ms
            or cue.end_ms > duration * 1000 + 1000 or not isinstance(cue.text, str)
            or not cue.text.strip() or len(cue.text) > 2000):
            raise ValueError("invalid transcript positions")
        decode_text(cue.text.encode("utf-8", errors="strict"))
        previous = cue.end_ms
    if len("\n".join(c.text for c in transcript.cues).encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("transcript too large")


class MediaTranscriber(Protocol):
    def transcribe(
        self, snapshot: Path, *, duration_seconds: float
    ) -> MediaTranscript: ...


@dataclass(frozen=True)
class LocalImportResult:
    content_id: str
    filename: str
    status: str
    duplicate: bool
    processing_error_code: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "content_id": self.content_id,
            "filename": self.filename,
            "status": self.status,
            "duplicate": self.duplicate,
            "source_id": LOCAL_SOURCE_ID,
            "provider": "LOCAL",
        }
        if self.processing_error_code:
            result["processing_error_code"] = self.processing_error_code
        return result


def decode_text(payload: bytes) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeError:
        raise LocalImportError("LOCAL_INVALID_TEXT") from None
    if not text.strip() or any(
        (ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 or c == "\ufffd"
        for c in text
    ):
        raise LocalImportError("LOCAL_INVALID_TEXT")
    return text


def probe_media(path: Path, extension: str) -> float:
    """Bounded OS adapter; no URL, shell, credentials or remote protocols."""
    from youtube_intel.offline_transcription import media_tool
    executable = media_tool("ffprobe")
    if executable is None:
        raise LocalImportError("LOCAL_MEDIA_TOOL_UNAVAILABLE")
    try:
        from youtube_intel.offline_transcription import run_bounded

        with open_managed(path.parent, path.name, maximum=MAX_MEDIA_BYTES) as source:
            output = run_bounded(
                [
                    executable,
                    "-v",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-max_alloc",
                    "16777216",
                    "-analyzeduration",
                    "3000000",
                    "-probesize",
                    "5000000",
                    *(
                        []
                        if extension in {".mp3", ".wav"}
                        else ["-enable_drefs", "0", "-use_absolute_path", "0"]
                    ),
                    "-show_entries",
                    "stream=codec_type:format=duration,format_name",
                    "-of",
                    "json",
                    "-f",
                    {".mp3": "mp3", ".wav": "wav"}.get(extension, "mov"),
                    f"/dev/fd/{source.fileno()}",
                ],
                timeout=20,
                maximum=65536,
                pass_fds=(source.fileno(),),
            )
        result = json.loads(output)
        streams = {s["codec_type"] for s in result["streams"]}
        formats = set(result["format"]["format_name"].split(","))
        expected = (
            {"mp3"}
            if extension == ".mp3"
            else {"wav"}
            if extension == ".wav"
            else {"mov", "mp4", "m4a"}
        )
        if not formats & expected or "audio" not in streams and "video" not in streams:
            raise ValueError("wrong container")
        if FORMATS[extension] == "AUDIO" and (
            "audio" not in streams or "video" in streams
        ):
            raise ValueError("wrong stream")
        if FORMATS[extension] == "VIDEO" and "video" not in streams:
            raise ValueError("wrong stream")
        duration = float(result["format"]["duration"])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("invalid media duration")
        if duration > 7200:
            raise LocalImportError("LOCAL_MEDIA_TOO_LONG")
        return duration
    except LocalImportError:
        raise
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError):
        raise LocalImportError("LOCAL_INVALID_MEDIA") from None


def selected_file_bytes(
    path: Path, *, after_open: Callable[[], None] | None = None
) -> bytes:
    """Native adapter test seam: select a target once, never retain a live symlink.

    Browser production selection submits File bytes directly. A native adapter
    may use this bounded descriptor read. Target replacement cannot change the
    selected inode; in-place mutation during reading is rejected.
    """
    extension = path.suffix.lower()
    if extension not in FORMATS:
        raise LocalImportError("LOCAL_UNSUPPORTED_FORMAT")
    # Legacy byte adapter remains explicitly bounded. Large native selections
    # use LocalContentProvider.import_file instead.
    maximum = MAX_TEXT_BYTES if FORMATS[extension] == "TEXT" else 64 * 1024 * 1024
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
                raise LocalImportError("LOCAL_FILE_TOO_LARGE")
            if after_open:
                after_open()
            payload = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) or len(payload) != before.st_size:
                raise LocalImportError("LOCAL_FILE_CHANGED")
            return payload
    except OSError:
        raise LocalImportError("LOCAL_FILE_UNREADABLE") from None


class LocalContentProvider(SourceContentPublisher):
    def _source_error(self) -> ValueError:
        return LocalImportError("LOCAL_SOURCE_UNTRUSTED")

    provider = "LOCAL"
    source_kind = SourceType.LOCAL_LIBRARY

    def __init__(
        self,
        repository: SQLiteStateRepository,
        data_root: Path,
        *,
        now: Callable[[], datetime] | None = None,
        transcriber: MediaTranscriber | None = None,
    ) -> None:
        self.repository = repository
        self.data_root = data_root.absolute()
        repository.bind_source_storage(self.data_root)
        self.now = now or (lambda: datetime.now(UTC))
        self.transcriber = transcriber
        cleanup_abandoned_imports(self.data_root / ".imports")

    def _library(self, now: datetime) -> None:
        if self.repository.get_source_subscription(LOCAL_SOURCE_ID) is None:
            self.repository.create_source_subscription(
                SourceSubscriptionRecord(
                    source_id=LOCAL_SOURCE_ID,
                    source_type=SourceType.LOCAL_LIBRARY,
                    canonical_url="local:library",
                    channel_id=None,
                    video_id=None,
                    display_name="Local library",
                    enabled=True,
                    processing_policy=ProcessingPolicy.DISCOVER_ONLY,
                    last_checked_at=None,
                    last_success_at=None,
                    last_error_code=None,
                    last_error_message=None,
                    created_at=now,
                    updated_at=now,
                    provider="LOCAL",
                )
            )

    def import_bytes(self, filename: str, payload: bytes) -> LocalImportResult:
        """Compatibility for bounded callers; HTTP and native files stream."""
        return self.import_stream(filename, BytesReader(payload), len(payload))

    def import_stream(
        self, filename: str, stream: ChunkReader, length: int,
        *, cancelled: Callable[[], bool] | None = None,
    ) -> LocalImportResult:
        name = safe_filename(filename)
        extension = Path(name).suffix.lower()
        if extension not in FORMATS:
            raise LocalImportError("LOCAL_UNSUPPORTED_FORMAT")
        maximum = MAX_TEXT_BYTES if FORMATS[extension] == "TEXT" else MAX_MEDIA_BYTES
        if length == 0:
            raise LocalImportError("LOCAL_EMPTY_FILE")
        if not 0 < length <= maximum:
            raise LocalImportError("LOCAL_FILE_TOO_LARGE")
        try:
            with _IMPORT_LOCK, stage_stream(self.data_root / ".imports", stream, length, maximum=maximum) as staged:
                if cancelled and cancelled():
                    raise LocalImportError("LOCAL_IMPORT_CANCELLED")
                return self._import_staged(name, extension, staged, cancelled=cancelled)
        except TimeoutError:
            raise LocalImportError("LOCAL_IMPORT_TIMEOUT") from None
        except EOFError:
            raise LocalImportError("LOCAL_IMPORT_INTERRUPTED") from None
        except ValueError as error:
            if isinstance(error, LocalImportError):
                raise
            raise LocalImportError("LOCAL_SOURCE_UNTRUSTED") from None
        except OSError as error:
            raise LocalImportError("LOCAL_DISK_SPACE_INSUFFICIENT" if error.errno == errno.ENOSPC else "LOCAL_FILE_UNREADABLE") from None

    def import_file(self, path: Path) -> LocalImportResult:
        """Native selection: check the source read before granting authority."""
        name = safe_filename(path.name)
        extension = Path(name).suffix.lower()
        if extension not in FORMATS:
            raise LocalImportError("LOCAL_UNSUPPORTED_FORMAT")
        maximum = MAX_TEXT_BYTES if FORMATS[extension] == "TEXT" else MAX_MEDIA_BYTES
        with _IMPORT_LOCK, ExitStack() as staging:
            with open_managed(path.parent, path.name, maximum=maximum) as source:
                staged = staging.enter_context(stage_stream(self.data_root / ".imports", source, os.fstat(source.fileno()).st_size, maximum=maximum))
            # The original descriptor's mutation check completed before publish.
            return self._import_staged(name, extension, staged)

    def import_selected(self, filename: str, source: BinaryIO, *,
                        cancelled: Callable[[], bool],
                        progress: Callable[[str, int, int, str], None]) -> LocalImportResult:
        """Only the native picker grant service supplies this read-only descriptor."""
        name = safe_filename(filename)
        extension = Path(name).suffix.lower()
        if extension not in FORMATS:
            raise LocalImportError("LOCAL_UNSUPPORTED_FORMAT")
        size = os.fstat(source.fileno()).st_size
        maximum = MAX_TEXT_BYTES if FORMATS[extension] == "TEXT" else MAX_MEDIA_BYTES
        if size == 0:
            raise LocalImportError("LOCAL_EMPTY_FILE")
        if not 0 < size <= maximum:
            raise LocalImportError("LOCAL_FILE_TOO_LARGE")
        try:
            with _IMPORT_LOCK, stage_native(self.data_root / ".imports", source,
                    maximum=maximum, cancelled=cancelled, progress=progress) as staged:
                if cancelled():
                    raise LocalImportError("LOCAL_IMPORT_CANCELLED")
                return self._import_staged(name, extension, staged, cancelled=cancelled)
        except InterruptedError:
            raise LocalImportError("LOCAL_IMPORT_CANCELLED") from None
        except TimeoutError:
            raise LocalImportError("LOCAL_IMPORT_TIMEOUT") from None
        except ValueError as error:
            if isinstance(error, LocalImportError):
                raise
            raise LocalImportError("LOCAL_SOURCE_UNTRUSTED") from None
        except OSError as error:
            raise LocalImportError("LOCAL_DISK_SPACE_INSUFFICIENT" if error.errno == errno.ENOSPC else "LOCAL_FILE_UNREADABLE") from None

    def _check_backup_capacity(self, incoming: int) -> None:
        from youtube_intel.backup_restore import (
            MAX_ARCHIVE_FILES,
            MAX_DATA_FILE_BYTES,
            MAX_TOTAL_BYTES,
        )
        with self.repository._connect() as connection:
            paths = [row[0] for row in connection.execute("SELECT DISTINCT relative_path FROM artifacts WHERE storage_root='DATA' AND deleted_at IS NULL")]
            database_size = int(connection.execute("PRAGMA page_count").fetchone()[0]) * int(connection.execute("PRAGMA page_size").fetchone()[0])
        # Include transaction-visible SQLite pages (including WAL), then retain
        # 1 GiB for subsequent transcripts, admission rows and archive metadata.
        total = incoming + database_size
        for relative in paths:
            try:
                with open_managed(self.data_root, relative, maximum=MAX_DATA_FILE_BYTES) as source:
                    total += os.fstat(source.fileno()).st_size
            except (OSError, ValueError):
                raise LocalImportError("LOCAL_SOURCE_UNTRUSTED") from None
        if total > MAX_TOTAL_BYTES - 1024 * 1024 * 1024 or len(paths) + 16 > MAX_ARCHIVE_FILES:
            raise LocalImportError("LOCAL_BACKUP_CAPACITY_EXCEEDED")

    def _import_staged(
        self, name: str, extension: str, staged: StagedFile,
        *, cancelled: Callable[[], bool] | None = None,
    ) -> LocalImportResult:
        kind = FORMATS[extension]
        text = decode_text(read_managed(staged.root, staged.name, maximum=MAX_TEXT_BYTES)) if kind == "TEXT" else None
        digest = staged.digest
        content_id = "local-" + digest
        now = self.now()
        existing = None
        with self.repository._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM content_source_snapshots WHERE content_id=?",
                (content_id,),
            ).fetchone()
            if existing is not None:
                interchangeable_text = kind == existing["media_kind"] == "TEXT"
                interchangeable_video = (
                    kind == existing["media_kind"] == "VIDEO"
                    and extension in {".mp4", ".mov", ".m4v"}
                    and existing["format"] in {".mp4", ".mov", ".m4v"}
                )
                if not (
                    interchangeable_text
                    or interchangeable_video
                    or extension == existing["format"]
                ):
                    raise LocalImportError("LOCAL_INVALID_MEDIA")
                if verify_source(self.repository, connection, content_id) is None:
                    raise LocalImportError("LOCAL_SOURCE_UNTRUSTED")
                if existing["status"] != "IMPORTED":
                    if existing["status"] == "READY":
                        try:
                            self._finish_summary(content_id, now, existing["language"])
                        except Exception:
                            return self._saved_processing_failure(content_id, True)
                    return LocalImportResult(
                        content_id, existing["filename"], existing["status"], True
                    )
                # A crash before READY is retried from the same verified bytes.
                name, extension, kind = (
                    existing["filename"],
                    existing["format"],
                    existing["media_kind"],
                )
        # Validate media before library admission. Orphan staging bytes have no authority.
        staged_relative = f"transcripts/local/{content_id}/source{extension}"
        self._check_backup_capacity(0 if existing is not None else staged.size)
        duration = probe_media(staged.path, extension) if kind != "TEXT" else None
        if cancelled and cancelled():
            raise LocalImportError("LOCAL_IMPORT_CANCELLED")
        published = staged.publish(self.data_root, staged_relative)
        try:
            self._library(now)
            timestamp = format_utc_datetime(now)
            # The immutable inode is already published; metadata retains the exact
            # original artifact identity without reading/copying the media again.
            artifact_id = f"{content_id}/source{extension}"
            snapshot = ArtifactWrite(
                artifact_id=artifact_id, artifact_key=artifact_id,
                video_id=content_id, job_id=None,
                kind=ArtifactKind.SUBTITLE_SOURCE if kind == "TEXT" else ArtifactKind.AUDIO,
                storage_root=StorageRoot.DATA, relative_path=staged_relative,
                content_hash=digest, provider=self.provider, model=None,
                producer_version=self.producer_version,
                retention_class=RetentionClass.LONG_LIVED, expires_at=None,
            )
            if existing is None:
                with self.repository._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "INSERT INTO videos(video_id,channel_id,title,availability,pipeline_status,pipeline_version,discovered_at,updated_at,provider,duration_seconds) VALUES(?,?,?,'public','METADATA_READY','local-import-v1',?,?,'LOCAL',?)",
                        (
                            content_id,
                            LOCAL_SOURCE_ID,
                            name,
                            timestamp,
                            timestamp,
                            None if duration is None else math.ceil(duration),
                        ),
                    )
                    connection.execute(
                        "INSERT INTO source_video_links(source_id,video_id,discovered_at) VALUES(?,?,?)",
                        (LOCAL_SOURCE_ID, content_id, timestamp),
                    )
                    self.repository._upsert_artifact_in_transaction(
                        connection, snapshot, now=timestamp
                    )
                    connection.execute(
                        "INSERT INTO content_source_snapshots(content_id,source_id,provider,source_identity,source_hash,snapshot_artifact_id,filename,format,media_kind,byte_count,imported_at,status,duration_seconds) VALUES(?,?,'LOCAL',?,?,?,?,?,?,?,?,'IMPORTED',?)",
                        (
                            content_id,
                            LOCAL_SOURCE_ID,
                            "sha256:" + digest,
                            digest,
                            snapshot.artifact_id,
                            name,
                            extension,
                            kind,
                            staged.size,
                            timestamp,
                            duration,
                        ),
                    )
        except BaseException:
            if published:
                staged.remove_uncommitted(self.data_root, staged_relative)
            raise
        status = "READY"
        transcript: MediaTranscript | None = None
        language = "und"
        if kind != "TEXT":
            status = "TRANSCRIPTION_UNAVAILABLE"
            if self.transcriber is not None and duration is not None:
                try:
                    transcript = self.transcriber.transcribe(
                        self.data_root / staged_relative, duration_seconds=duration
                    )
                    validate_media_transcript(transcript, duration)
                    text = "\n".join(c.text for c in transcript.cues)
                    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise ValueError("transcript too large")
                    language = transcript.language
                    status = "READY"
                except Exception:
                    status = "TRANSCRIPTION_FAILED"
        if status == "READY" and text is not None:
            try:
                self._persist_source_result(content_id, text, transcript, digest, duration, language, now)
            except Exception:
                return self._saved_processing_failure(content_id, existing is not None)
        else:
            try:
                with self.repository._connect() as connection:
                    connection.execute(
                        "UPDATE content_source_snapshots SET status=? WHERE content_id=?",
                        (status, content_id),
                    )
            except Exception:
                return self._saved_processing_failure(content_id, existing is not None)
        return LocalImportResult(content_id, name, status, existing is not None)

    def _saved_processing_failure(self, content_id: str, duplicate: bool) -> LocalImportResult:
        # Admission is already committed. Never report a lost file because a
        # later transcript/summary publication failed, but re-verify authority.
        with self.repository._connect() as connection:
            source = verify_source(self.repository, connection, content_id)
            if source is None:
                raise LocalImportError("LOCAL_SOURCE_UNTRUSTED")
            return LocalImportResult(content_id, source["filename"], source["status"], duplicate,
                                     "LOCAL_PROCESSING_UNAVAILABLE")

    def accept_transcript(self, content_id: str, transcript: MediaTranscript) -> None:
        """Reuse Phase 7 authority publication; never replace a trusted success."""
        with self.repository._connect() as connection:
            source = verify_source(self.repository, connection, content_id)
            if source is None:
                raise LocalImportError("LOCAL_SOURCE_UNTRUSTED")
            if source["media_kind"] == "TEXT":
                raise LocalImportError("LOCAL_NOT_MEDIA")
            if source["status"] == "READY":
                self._finish_summary(content_id, self.now(), source["language"])
                return
            validate_media_transcript(transcript, source["duration_seconds"])
            digest, duration = source["source_hash"], source["duration_seconds"]
        self._persist_source_result(content_id, "\n".join(c.text for c in transcript.cues),
                                    transcript, digest, duration, transcript.language, self.now())
