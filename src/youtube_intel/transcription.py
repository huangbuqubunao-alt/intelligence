"""Offline policy, cache identity, and safe audio cleanup for local transcription.

This module deliberately has no model, media, subprocess, or network integration.
Those resource-consuming paths require separate task-level authorization.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path, PurePosixPath
from re import fullmatch
from typing import Protocol, TypeVar

from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    RetentionClass,
    StorageRoot,
)

_SHA256_RE = r"[0-9a-f]{64}"
_CACHE_OPERATION = "local-whisper-transcription-v1"


@dataclass(frozen=True, slots=True)
class AudioArtifact:
    """The minimum verified audio metadata needed by the Phase A adapter."""

    artifact_id: str
    video_id: str
    relative_path: str
    content_hash: str
    byte_count: int
    duration_seconds: int

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.video_id:
            raise ValueError("audio artifact identifiers must be non-empty")
        if not self.relative_path or self.relative_path != self.relative_path.strip():
            raise ValueError("audio relative_path must be a non-empty trimmed path")
        if fullmatch(_SHA256_RE, self.content_hash) is None:
            raise ValueError("audio content_hash must be a SHA-256 hex digest")
        if self.byte_count < 0 or self.duration_seconds < 0:
            raise ValueError("audio byte_count and duration_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class AudioResourceSnapshot:
    """Available local resources in whole GiB, supplied by a later runtime gate."""

    free_disk_gib: int
    available_memory_gib: int

    def __post_init__(self) -> None:
        if self.free_disk_gib < 0 or self.available_memory_gib < 0:
            raise ValueError("available audio resources must be non-negative")


class DurationDecision(str, Enum):
    """Pure eligibility result; this function never changes pipeline state."""

    PERMITTED = "PERMITTED"
    DURATION_LIMIT_EXCEEDED = "DURATION_LIMIT_EXCEEDED"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    INSUFFICIENT_DISK = "INSUFFICIENT_DISK"
    INSUFFICIENT_MEMORY = "INSUFFICIENT_MEMORY"


@dataclass(frozen=True, slots=True)
class TranscriptionPolicy:
    max_duration_seconds: int = 180 * 60
    max_audio_bytes: int = 2_000_000_000
    min_free_disk_gib: int = 8
    min_available_memory_gib: int = 6

    def __post_init__(self) -> None:
        if (
            self.max_duration_seconds < 0
            or self.max_audio_bytes < 0
            or self.min_free_disk_gib < 0
            or self.min_available_memory_gib < 0
        ):
            raise ValueError("transcription policy limits must be non-negative")

    def evaluate(
        self,
        audio: AudioArtifact,
        resources: AudioResourceSnapshot,
    ) -> DurationDecision:
        if audio.duration_seconds > self.max_duration_seconds:
            return DurationDecision.DURATION_LIMIT_EXCEEDED
        if audio.byte_count > self.max_audio_bytes:
            return DurationDecision.AUDIO_TOO_LARGE
        if resources.free_disk_gib < self.min_free_disk_gib:
            return DurationDecision.INSUFFICIENT_DISK
        if resources.available_memory_gib < self.min_available_memory_gib:
            return DurationDecision.INSUFFICIENT_MEMORY
        return DurationDecision.PERMITTED


def build_transcription_cache_key(
    *,
    audio_content_hash: str,
    model: str,
    model_revision: str,
    parameter_policy_version: str,
) -> str:
    """Hash the immutable cache dimensions required by System Design §10."""
    if fullmatch(_SHA256_RE, audio_content_hash) is None:
        raise ValueError("audio_content_hash must be a SHA-256 hex digest")
    if not model or not model_revision or not parameter_policy_version:
        raise ValueError("model cache dimensions must be non-empty")
    body = json.dumps(
        {
            "audio_content_hash": audio_content_hash,
            "model": model,
            "model_revision": model_revision,
            "operation": _CACHE_OPERATION,
            "parameter_policy_version": parameter_policy_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


CachedValue = TypeVar("CachedValue")


class TranscriptionCache(Protocol[CachedValue]):
    def get(self, key: str) -> CachedValue | None: ...

    def put(self, key: str, value: CachedValue) -> None: ...


@dataclass(slots=True)
class InMemoryTranscriptionCache(TranscriptionCache[CachedValue]):
    """A deliberately small Fake-compatible cache for offline adapter tests."""

    _entries: MutableMapping[str, CachedValue] = field(default_factory=dict)

    def get(self, key: str) -> CachedValue | None:
        return self._entries.get(key)

    def put(self, key: str, value: CachedValue) -> None:
        self._entries[key] = value


class AudioDeletionRepository(Protocol):
    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None: ...

    def mark_artifact_deleted(
        self,
        artifact_id: str,
        expected_content_hash: str,
        now: datetime,
    ) -> bool: ...


class AudioCleanupResult(str, Enum):
    DELETED = "DELETED"
    MISSING = "MISSING"
    INELIGIBLE_ARTIFACT = "INELIGIBLE_ARTIFACT"
    PATH_OUTSIDE_DATA = "PATH_OUTSIDE_DATA"
    HASH_MISMATCH = "HASH_MISMATCH"
    IO_ERROR = "IO_ERROR"
    INDEX_CONFLICT = "INDEX_CONFLICT"


def _matches_registered_audio(
    expected: ArtifactRecord,
    registered: ArtifactRecord | None,
) -> bool:
    """Require the current index row to still authorize this exact cleanup."""
    return (
        registered is not None
        and registered.artifact_id == expected.artifact_id
        and registered.artifact_key == expected.artifact_key
        and registered.kind is ArtifactKind.AUDIO
        and registered.storage_root is StorageRoot.DATA
        and registered.relative_path == expected.relative_path
        and registered.content_hash == expected.content_hash
        and registered.retention_class is RetentionClass.EPHEMERAL_AUDIO
        and registered.deleted_at is None
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def cleanup_successful_audio(
    audio: ArtifactRecord,
    *,
    data_root: Path,
    repository: AudioDeletionRepository,
    now: datetime,
) -> AudioCleanupResult:
    """Best-effort, hash-verified cleanup after a completed transcription.

    A cleanup failure is intentionally returned as a diagnostic value instead of
    invalidating a successfully produced transcript.  The function never removes
    an unverified file or a file outside the caller's DATA root.
    """
    if (
        audio.kind is not ArtifactKind.AUDIO
        or audio.storage_root is not StorageRoot.DATA
        or audio.retention_class is not RetentionClass.EPHEMERAL_AUDIO
        or audio.deleted_at is not None
    ):
        return AudioCleanupResult.INELIGIBLE_ARTIFACT

    if not _matches_registered_audio(
        audio,
        repository.get_artifact_by_key(audio.artifact_key),
    ):
        return AudioCleanupResult.INDEX_CONFLICT

    relative = PurePosixPath(audio.relative_path.replace("\\", "/"))
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        return AudioCleanupResult.PATH_OUTSIDE_DATA

    try:
        root = data_root.resolve(strict=True)
        candidate = root.joinpath(*relative.parts)
        if candidate.is_symlink():
            return AudioCleanupResult.PATH_OUTSIDE_DATA
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        return AudioCleanupResult.MISSING
    except OSError:
        return AudioCleanupResult.IO_ERROR

    try:
        resolved.relative_to(root)
    except ValueError:
        return AudioCleanupResult.PATH_OUTSIDE_DATA

    try:
        digest = _sha256_file(resolved)
    except OSError:
        return AudioCleanupResult.IO_ERROR
    if digest != audio.content_hash:
        return AudioCleanupResult.HASH_MISMATCH

    try:
        resolved.unlink()
    except OSError:
        return AudioCleanupResult.IO_ERROR

    if not repository.mark_artifact_deleted(audio.artifact_id, audio.content_hash, now):
        return AudioCleanupResult.INDEX_CONFLICT
    return AudioCleanupResult.DELETED


__all__ = [
    "AudioArtifact",
    "AudioCleanupResult",
    "AudioDeletionRepository",
    "AudioResourceSnapshot",
    "DurationDecision",
    "InMemoryTranscriptionCache",
    "TranscriptionCache",
    "TranscriptionPolicy",
    "build_transcription_cache_key",
    "cleanup_successful_audio",
]
