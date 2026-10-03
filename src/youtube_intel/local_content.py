"""Explicit Local provider import, unified Content and immutable DATA artifacts."""

from __future__ import annotations

import json
import math
import os
import shutil
import sqlite3
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
    text_evidence_id,
    verify_source,
    write_managed,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    RetentionClass,
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
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


@dataclass(frozen=True)
class MediaTranscript:
    language: str
    cues: tuple[TimedTranscriptCueWrite, ...]
    provenance: str


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
    executable = shutil.which("ffprobe")
    if executable is None:
        raise LocalImportError("LOCAL_MEDIA_TOOL_UNAVAILABLE")
    try:
        process = subprocess.run(
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
            capture_output=True,
            timeout=20,
            check=False,
        )
        if process.returncode or len(process.stdout) > 65536:
            raise ValueError("invalid probe")
        result = json.loads(process.stdout)
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


class LocalContentProvider:
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

    def _artifact_write(
        self, content_id: str, suffix: str, payload: bytes, kind: ArtifactKind
    ) -> ArtifactWrite:
        digest = sha256(payload)
        artifact_id = f"{content_id}/{suffix}"
        relative = f"transcripts/local/{content_id}/{suffix}"
        write_managed(self.data_root, relative, payload)
        return ArtifactWrite(
            artifact_id=artifact_id,
            artifact_key=artifact_id,
            video_id=content_id,
            job_id=None,
            kind=kind,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=digest,
            provider="LOCAL",
            model=None,
            producer_version="local-import-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
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
                    if (
                        not transcript.cues
                        or len(transcript.cues) > 4096
                        or not transcript.language.strip()
                        or not transcript.provenance.strip()
                    ):
                        raise ValueError("invalid transcription")
                    previous_end = 0
                    for cue in transcript.cues:
                        if (
                            cue.start_ms < previous_end
                            or cue.end_ms <= cue.start_ms
                            or cue.end_ms > duration * 1000 + 1000
                            or not cue.text.strip()
                            or len(cue.text) > 2000
                        ):
                            raise ValueError("invalid transcript positions")
                        previous_end = cue.end_ms
                    text = "\n".join(c.text for c in transcript.cues)
                    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise ValueError("transcript too large")
                    language = transcript.language
                    status = "READY"
                except Exception:
                    status = "TRANSCRIPTION_FAILED"
        if status == "READY" and text is not None:
            canonical = self._artifact_write(
                content_id,
                "canonical.txt",
                text.encode("utf-8"),
                ArtifactKind.TRANSCRIPT_CANONICAL,
            )
            provenance = None
            if transcript is not None:
                timed = TimedTranscriptWrite.from_cues(
                    video_id=content_id,
                    canonical_artifact_id=canonical.artifact_id,
                    cues=transcript.cues,
                )
                from youtube_intel.research_contract import canonical as canonical_json

                envelope = canonical_json(
                    {
                        "contract": "source-transcript-provenance-v1",
                        "content_id": content_id,
                        "source_hash": digest,
                        "canonical_text_hash": sha256(text.encode("utf-8")),
                        "timed_transcript_hash": timed.timed_transcript_hash,
                        "language": language,
                        "duration_seconds": duration,
                        "transcriber": transcript.provenance,
                    }
                ).encode("utf-8")
                provenance = self._artifact_write(
                    content_id,
                    "transcript-provenance.json",
                    envelope,
                    ArtifactKind.SUBTITLE_SOURCE,
                )
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self.repository._upsert_artifact_in_transaction(
                    connection, canonical, now=timestamp
                )
                if provenance is not None:
                    self.repository._upsert_artifact_in_transaction(
                        connection, provenance, now=timestamp
                    )
                    connection.execute(
                        "UPDATE content_source_snapshots SET provenance_artifact_id=? WHERE content_id=?",
                        (provenance.artifact_id, content_id),
                    )
                connection.execute(
                    "UPDATE content_source_snapshots SET canonical_artifact_id=?,canonical_text=?,canonical_text_hash=?,language=?,transcript_provenance=? WHERE content_id=?",
                    (
                        canonical.artifact_id,
                        text,
                        sha256(text.encode("utf-8")),
                        language,
                        "utf-8-exact-v1"
                        if transcript is None
                        else transcript.provenance,
                        content_id,
                    ),
                )
                if transcript is None:
                    self._text_evidence(
                        connection, content_id, canonical.artifact_id, text, digest, now
                    )
                else:
                    self._media_evidence(
                        connection, content_id, canonical.artifact_id, transcript, now
                    )
                connection.execute(
                    "UPDATE content_source_snapshots SET status='READY' WHERE content_id=?",
                    (content_id,),
                )
            self._finish_summary(content_id, now, language)
        else:
            with self.repository._connect() as connection:
                connection.execute(
                    "UPDATE content_source_snapshots SET status=? WHERE content_id=?",
                    (status, content_id),
                )
        return LocalImportResult(content_id, name, status, existing is not None)

    def _finish_summary(self, content_id: str, now: datetime, language: str) -> None:
        from youtube_intel.extractive_summary import ExtractiveSummaryService

        pointer = self.repository.current_local_summary_pointer(content_id)
        if pointer is None:
            ExtractiveSummaryService(self.repository, self.data_root).create(
                content_id, now=now
            )
        timestamp = format_utc_datetime(now)
        with self.repository._connect() as connection:
            connection.execute(
                "UPDATE videos SET pipeline_status='COMPLETE',completed_at=COALESCE(completed_at,?),updated_at=?,default_language=? WHERE video_id=? AND pipeline_status!='COMPLETE'",
                (timestamp, timestamp, language, content_id),
            )

    def _text_evidence(
        self,
        connection: sqlite3.Connection,
        content_id: str,
        artifact_id: str,
        text: str,
        source_hash: str,
        now: datetime,
    ) -> None:
        offset = 0
        # Ordinary text retains line-level excerpts. Highly fragmented input
        # uses bounded exact windows, preventing millions of evidence rows.
        lines = text.splitlines(keepends=True)
        parts = (
            lines
            if len(lines) <= 2048
            else [text[i : i + 1000] for i in range(0, len(text), 1000)]
        )
        canonical_hash = sha256(text.encode("utf-8"))
        for line in parts:
            for index in range(0, len(line), 1000):
                excerpt = line[index : index + 1000]
                start = offset + index
                end = start + len(excerpt)
                if not excerpt.strip():
                    continue
                eid = text_evidence_id(
                    content_id=content_id,
                    artifact_id=artifact_id,
                    start_offset=start,
                    end_offset=end,
                )
                connection.execute(
                    "INSERT INTO evidence(evidence_id,video_id,artifact_id,locator_type,start_offset,end_offset,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES(?,?,?,'TEXT_RANGE',?,?,'ORIGINAL_TRANSCRIPT','PRIMARY_ORIGINAL','und','AVAILABLE',?,?)",
                    (
                        eid,
                        content_id,
                        artifact_id,
                        start,
                        end,
                        format_utc_datetime(now),
                        excerpt,
                    ),
                )
                connection.execute(
                    "INSERT INTO evidence_source_ranges VALUES(?,?,?,?,?,?)",
                    (
                        eid,
                        artifact_id,
                        excerpt,
                        sha256(excerpt.encode("utf-8")),
                        canonical_hash,
                        source_hash,
                    ),
                )
            offset += len(line)

    def _media_evidence(
        self,
        connection: sqlite3.Connection,
        content_id: str,
        artifact_id: str,
        transcript: MediaTranscript,
        now: datetime,
    ) -> None:
        timed = TimedTranscriptWrite.from_cues(
            video_id=content_id, canonical_artifact_id=artifact_id, cues=transcript.cues
        )
        timestamp = format_utc_datetime(now)
        connection.execute(
            "INSERT INTO timed_transcripts(timed_transcript_id,video_id,canonical_artifact_id,timed_transcript_hash,created_at) VALUES(?,?,?,?,?)",
            (
                timed.timed_transcript_id,
                content_id,
                artifact_id,
                timed.timed_transcript_hash,
                timestamp,
            ),
        )
        connection.executemany(
            "INSERT INTO timed_transcript_cues(timed_transcript_id,cue_index,start_ms,end_ms,cue_text,cue_text_hash) VALUES(?,?,?,?,?,?)",
            [
                (
                    timed.timed_transcript_id,
                    index,
                    c.start_ms,
                    c.end_ms,
                    c.text,
                    c.text_hash,
                )
                for index, c in enumerate(transcript.cues)
            ],
        )
        for index, cue in enumerate(transcript.cues):
            eid = build_evidence_id(
                video_id=content_id,
                artifact_id=artifact_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
            )
            evidence = EvidenceWrite(
                evidence_id=eid,
                video_id=content_id,
                artifact_id=artifact_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
                language=transcript.language,
                availability=EvidenceAvailability.AVAILABLE,
                source_excerpt=cue.text,
            )
            binding = EvidenceTextBindingWrite.from_timed_transcript(
                evidence=evidence,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=index,
                end_cue_index=index + 1,
                excerpt=cue.text,
            )
            connection.execute(
                "INSERT INTO evidence(evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    eid,
                    content_id,
                    artifact_id,
                    cue.start_ms,
                    cue.end_ms,
                    evidence.lineage_kind.value,
                    evidence.role.value,
                    transcript.language,
                    evidence.availability.value,
                    timestamp,
                    cue.text,
                ),
            )
            self.repository._insert_evidence_text_binding_in_transaction(
                connection, evidence, binding, now=now
            )
