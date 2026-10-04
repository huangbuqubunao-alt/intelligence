"""Explicit Local provider import, unified Content and immutable DATA artifacts."""

from __future__ import annotations

import json
import math
import os
import stat
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.source_authority import (
    MAX_MEDIA_BYTES,
    MAX_TEXT_BYTES,
    safe_filename,
    sha256,
    verify_source,
    write_managed,
)
from youtube_intel.source_publication import SourceContentPublisher
from youtube_intel.source_transcript import MediaTranscript as MediaTranscript
from youtube_intel.state import (
    ArtifactKind,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
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

    def as_dict(self) -> dict[str, object]:
        return {
            "content_id": self.content_id,
            "filename": self.filename,
            "status": self.status,
            "duplicate": self.duplicate,
            "source_id": LOCAL_SOURCE_ID,
            "provider": "LOCAL",
        }


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
                str(path),
            ],
            timeout=20,
            maximum=65536,
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
        if not math.isfinite(duration) or not 0 < duration <= 7200:
            raise ValueError("unbounded media duration")
        return duration
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
    maximum = MAX_TEXT_BYTES if FORMATS[extension] == "TEXT" else MAX_MEDIA_BYTES
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
        with _IMPORT_LOCK:
            return self._import_bytes(filename, payload)

    def _import_bytes(self, filename: str, payload: bytes) -> LocalImportResult:
        name = safe_filename(filename)
        extension = Path(name).suffix.lower()
        if extension not in FORMATS:
            raise LocalImportError("LOCAL_UNSUPPORTED_FORMAT")
        kind = FORMATS[extension]
        maximum = MAX_TEXT_BYTES if kind == "TEXT" else MAX_MEDIA_BYTES
        if not payload or len(payload) > maximum:
            raise LocalImportError("LOCAL_FILE_TOO_LARGE")
        text = decode_text(payload) if kind == "TEXT" else None
        digest = sha256(payload)
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
                        self._finish_summary(content_id, now, existing["language"])
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
        write_managed(self.data_root, staged_relative, payload)
        duration = None
        if kind != "TEXT":
            try:
                duration = probe_media(self.data_root / staged_relative, extension)
            except LocalImportError as error:
                raise error
        self._library(now)
        timestamp = format_utc_datetime(now)
        # Legacy videos table is the Content repository. channel_id holds the
        # collection's internal identity for compatibility, never a creator.
        snapshot = self._artifact_write(
            content_id,
            "source" + extension,
            payload,
            ArtifactKind.SUBTITLE_SOURCE if kind == "TEXT" else ArtifactKind.AUDIO,
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
                        len(payload),
                        timestamp,
                        duration,
                    ),
                )
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
            self._persist_source_result(content_id, text, transcript, digest, duration, language, now)
        else:
            with self.repository._connect() as connection:
                connection.execute(
                    "UPDATE content_source_snapshots SET status=? WHERE content_id=?",
                    (status, content_id),
                )
        return LocalImportResult(content_id, name, status, existing is not None)

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
