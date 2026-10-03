"""Provider-neutral immutable source snapshots and exact-text range authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import uuid
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from youtube_intel.state import SQLiteStateRepository, VerifiedEvidenceText

MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_MEDIA_BYTES = 64 * 1024 * 1024
SOURCE_CONTRACT = "source-snapshot-v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        if row["source_identity"] != "sha256:" + row["source_hash"] or (
            row["provider"] == "LOCAL" and content_id != "local-" + row["source_hash"]
        ):
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
        data = read_managed(
            root,
            artifact["relative_path"],
            maximum=MAX_MEDIA_BYTES if row["media_kind"] != "TEXT" else MAX_TEXT_BYTES,
        )
        if len(data) != row["byte_count"] or sha256(data) != row["source_hash"]:
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


@lru_cache(maxsize=1)
def _expected_source_schema() -> tuple[tuple[str, str], ...]:
    from youtube_intel.state import SQLiteStateRepository

    expected = sqlite3.connect(":memory:")
    try:
        expected.execute("PRAGMA legacy_alter_table=ON")
        for migration in SQLiteStateRepository(Path(":memory:"))._load_migrations():
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
    if _source_schema(connection) != _expected_source_schema():
        raise ValueError("source authority schema is incompatible")
