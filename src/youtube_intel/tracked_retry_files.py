"""Write-ahead file closure for one exclusively locked tracked retry writer."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

from youtube_intel.source_authority import managed_directory, read_managed, sha256
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.tracked_retry_context import RetryIntegrity
from youtube_intel.tracked_retry_store import CONTRACT, canonical, digest
from youtube_intel.transcripts import (
    NORMALIZATION_VERSION,
    QUALITY_POLICY_VERSION,
    SUBTITLE_QUALITY_POLICY,
    TranscriptJobContext,
    _canonical_artifact_id,
    _canonical_relative_path,
    _capture_artifact_write,
    _decode_source_metadata,
    _raw_artifact_id,
    _source_relative_path,
    _validate_source_provenance,
    build_canonical_request_hash,
    normalize_timed_subtitle,
)


def provenance(
    repository: SQLiteStateRepository,
    root: Path,
    request: dict[str, Any],
    relative: str,
    body: bytes,
    *,
    epoch: int,
) -> tuple[str, dict[str, Any]]:
    """Reconstruct the producer, not merely the digest claimed by a file row."""
    parameters = json.loads(request["parameters_json"])
    proof: dict[str, Any] = dict(
        contract=CONTRACT,
        request_id=request["request_id"],
        provider_request_hash=request["provider_request_hash"],
        parameters_sha256=request["parameters_sha256"],
        fencing_epoch=epoch,
        logical_target_path=relative,
        expected_artifact_id=None,
        capture_artifact_id=None,
        source_format=None,
        source_language=None,
        requested_language=None,
        source_type=None,
        normalization_version=NORMALIZATION_VERSION,
        quality_policy_version=QUALITY_POLICY_VERSION,
    )
    prefix = f"transcripts/{request['video_id']}/{request['raw_request_hash']}/"
    if relative.startswith(prefix) and Path(relative).name.startswith("source."):
        metadata = _decode_source_metadata(
            Path(relative).name, video_id=request["video_id"]
        )
        _validate_source_provenance(
            metadata, parameters["language_preferences"], video_id=request["video_id"]
        )
        normalized = normalize_timed_subtitle(body, metadata.source_format)
        if relative != _source_relative_path(
            video_id=request["video_id"],
            raw_request_hash=request["raw_request_hash"],
            metadata=metadata,
        ):
            raise RetryIntegrity("Content retry capture path changed")
        capture = _capture_artifact_write(
            video_id=request["video_id"],
            context=TranscriptJobContext(
                job_id=request["target_job_id"],
                owner="proof",
                pipeline_version=request["pipeline_version"],
                refresh_generation=request["refresh_generation"],
            ),
            raw_request_hash=request["raw_request_hash"],
            metadata=metadata,
            content_hash=normalized.source_content_hash,
            provider=parameters["adapter_name"],
            provider_version=parameters["adapter_version"],
        )
        proof.update(
            expected_artifact_id=capture.artifact_id,
            capture_artifact_id=capture.artifact_id,
            source_format=metadata.source_format.value,
            source_language=metadata.actual_language,
            requested_language=metadata.requested_language,
            source_type=metadata.source_type.value,
        )
        return "CAPTURE", proof
    if relative.startswith(prefix) and Path(relative).name.startswith("canonical."):
        with closing(repository._connect(read_only=True)) as connection, connection:
            captures = connection.execute(
                "SELECT * FROM artifacts WHERE job_id=? AND artifact_key LIKE 'subtitle-source-capture:%'",
                (request["target_job_id"],),
            ).fetchall()
        for capture in captures:
            source = read_managed(
                root,
                capture["relative_path"],
                maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
            )
            if sha256(source) != capture["content_hash"]:
                raise RetryIntegrity("Content retry source changed")
            _, source_proof = provenance(
                repository, root, request, capture["relative_path"], source, epoch=epoch
            )
            metadata = _decode_source_metadata(
                Path(capture["relative_path"]).name, video_id=request["video_id"]
            )
            normalized = normalize_timed_subtitle(source, metadata.source_format)
            ch = build_canonical_request_hash(
                source_content_hash=normalized.source_content_hash,
                source_format=metadata.source_format,
            )
            expected = _canonical_relative_path(
                video_id=request["video_id"],
                raw_request_hash=request["raw_request_hash"],
                canonical_request_hash=ch,
                quality_flags=normalized.quality_flags,
            )
            if relative == expected and body == normalized.text.encode():
                raw_id = _raw_artifact_id(
                    raw_request_hash=request["raw_request_hash"],
                    metadata=metadata,
                    source_content_hash=normalized.source_content_hash,
                    provider=parameters["adapter_name"],
                )
                source_proof.update(
                    logical_target_path=relative,
                    expected_artifact_id=_canonical_artifact_id(
                        raw_artifact_id=raw_id,
                        raw_content_hash=normalized.source_content_hash,
                        provider=parameters["adapter_name"],
                        model=None,
                        raw_request_hash=request["raw_request_hash"],
                        canonical_request_hash=ch,
                        content_hash=normalized.content_hash,
                        quality_flags=normalized.quality_flags,
                    ),
                )
                return "CANONICAL_DERIVATION", source_proof
        raise RetryIntegrity("Content retry canonical producer cannot be reconstructed")
    if relative.startswith("transcripts/summaries/"):
        from youtube_intel.extractive_summary import ExtractiveSummaryService

        result = ExtractiveSummaryService(repository, root)._result(
            request["video_id"], use_timed_candidates=True
        )
        if (
            body != result.model_dump_json().encode()
            or relative != f"transcripts/summaries/{result.request_hash}.json"
        ):
            raise RetryIntegrity("Content retry Summary producer changed")
        proof["expected_artifact_id"] = f"summary/{result.request_hash}/structured"
        return "SUMMARY_DERIVATION", proof
    raise RetryIntegrity("Content retry write is outside its frozen producer paths")


class RetryFiles:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        root: Path,
        request: dict[str, Any],
        *,
        epoch: int,
        check: Callable[[], None],
        timestamp: Callable[[], str],
    ) -> None:
        self.repository, self.root, self.request = repository, root, request
        self.epoch, self.check, self.timestamp = epoch, check, timestamp

    def write(self, root: Path, relative: str, body: bytes) -> None:
        self.check()
        if (
            root != self.root
            or not body
            or len(body) > SUBTITLE_QUALITY_POLICY.max_raw_bytes
        ):
            raise RetryIntegrity("Content retry write exceeds its DATA boundary")
        role, proof = provenance(
            self.repository, root, self.request, relative, body, epoch=self.epoch
        )
        # Every actual path is journaled before opening it, including the buffer.
        buffer = str(
            Path(relative).with_name(
                ".tracked-buffer-"
                + digest(
                    {
                        "request_id": self.request["request_id"],
                        "relative": relative,
                        "epoch": self.epoch,
                    }
                )
            )
        )
        checksum, size = sha256(body), len(body)
        with closing(self.repository._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            for path, file_role in ((relative, role), (buffer, "WRITE_BUFFER")):
                existing = connection.execute(
                    "SELECT * FROM tracked_content_retry_files WHERE relative_path=?",
                    (path,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["request_id"] != self.request["request_id"]
                        or existing["role"] != file_role
                        or existing["expected_sha256"] != checksum
                        or existing["expected_size_bytes"] != size
                    ):
                        raise RetryIntegrity("Content retry file identity conflicts")
                    if path == relative and existing["state"] == "VERIFIED":
                        if read_managed(root, path, maximum=size) != body:
                            raise RetryIntegrity("Content retry immutable file changed")
                        return
                    if path == relative and existing['state']=='PLANNED':
                        old_proof=json.loads(existing['proof_json'])
                        if {k:v for k,v in old_proof.items() if k!='fencing_epoch'} != {k:v for k,v in proof.items() if k!='fencing_epoch'}:
                            raise RetryIntegrity('Content retry planned producer changed')
                        continue
                    raise RetryIntegrity('Content retry cannot rewrite a settled or reused buffer')
                connection.execute(
                    "INSERT INTO tracked_content_retry_files(request_id,relative_path,role,expected_sha256,expected_size_bytes,state,proof_json,proof_sha256,created_at) VALUES(?,?,?,?,?,'PLANNED',?,?,?)",
                    (
                        self.request["request_id"],
                        path,
                        file_role,
                        checksum,
                        size,
                        canonical(proof),
                        digest(proof),
                        self.timestamp(),
                    ),
                )
        self.repository._inject_failure('tracked_retry.file.'+role+'.after_intents')
        self.check()
        with managed_directory(
            root, str(Path(relative).parent), create=True
        ) as directory:
            fd = os.open(
                Path(buffer).name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            self.repository._inject_failure('tracked_retry.file.'+role+'.after_buffer_fsync')
            self.check()
            os.link(
                Path(buffer).name,
                Path(relative).name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
            os.unlink(Path(buffer).name, dir_fd=directory)
            os.fsync(directory)
        self.repository._inject_failure('tracked_retry.file.'+role+'.after_publish')
        self.settle(terminal=False)

    def settle(self, *, terminal: bool = True) -> None:
        """Only called under the stable request lock after the old writer is excluded."""
        self.check()
        with closing(self.repository._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM tracked_content_retry_files WHERE request_id=? AND state='PLANNED'",
                (self.request["request_id"],),
            ).fetchall()
            for row in rows:
                path = self.root / row["relative_path"]
                try:
                    body = (
                        read_buffer(self.root, row["relative_path"])
                        if row["role"] == "WRITE_BUFFER"
                        else read_managed(
                            self.root,
                            row["relative_path"],
                            maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes,
                        )
                    )
                except FileNotFoundError:
                    if not terminal and row['role']!='WRITE_BUFFER':
                        continue
                    state, checksum, size = "ABSENT", None, None
                else:
                    checksum, size = sha256(body), len(body)
                    if (
                        checksum == row["expected_sha256"]
                        and size == row["expected_size_bytes"]
                    ):
                        state = "VERIFIED"
                    elif row["role"] == "WRITE_BUFFER":
                        state = "RETAINED_PARTIAL"
                    else:
                        raise RetryIntegrity(
                            "Content retry non-buffer bytes are corrupt"
                        )
                if path.is_symlink():
                    raise RetryIntegrity("Content retry file is a symlink")
                connection.execute(
                    "UPDATE tracked_content_retry_files SET state=?,observed_sha256=?,observed_size_bytes=?,settled_at=? WHERE request_id=? AND relative_path=? AND state='PLANNED'",
                    (
                        state,
                        checksum,
                        size,
                        self.timestamp(),
                        self.request["request_id"],
                        row["relative_path"],
                    ),
                )


def read_buffer(root: Path, relative: str) -> bytes:
    """Buffers may be empty after an interrupted first write; never follow links."""
    with managed_directory(root, str(Path(relative).parent)) as directory:
        fd = os.open(
            Path(relative).name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        try:
            before = os.fstat(fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size > SUBTITLE_QUALITY_POLICY.max_raw_bytes
            ):
                raise RetryIntegrity("Content retry buffer is unsafe")
            parts = []
            remaining = before.st_size
            while remaining:
                part = os.read(fd, min(65536, remaining))
                if not part:
                    raise RetryIntegrity("Content retry buffer changed")
                parts.append(part)
                remaining -= len(part)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise RetryIntegrity("Content retry buffer changed")
            return b"".join(parts)
        finally:
            os.close(fd)
