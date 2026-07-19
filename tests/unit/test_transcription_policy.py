"""Offline policy and cleanup tests for local Whisper transcription."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    RetentionClass,
    StorageRoot,
)
from youtube_intel.transcription import (
    AudioArtifact,
    AudioCleanupResult,
    AudioResourceSnapshot,
    DurationDecision,
    TranscriptionPolicy,
    build_transcription_cache_key,
    cleanup_successful_audio,
)

FIXED_NOW = datetime(2026, 7, 19, 10, 0, tzinfo=UTC)


class _FakeArtifactRepository:
    def __init__(
        self,
        *,
        record: ArtifactRecord | None,
        result: bool = True,
    ) -> None:
        self.record = record
        self.result = result
        self.calls: list[tuple[str, str, datetime]] = []
        self.lookups: list[str] = []

    def get_artifact_by_key(self, artifact_key: str) -> ArtifactRecord | None:
        self.lookups.append(artifact_key)
        return self.record

    def mark_artifact_deleted(
        self,
        artifact_id: str,
        expected_content_hash: str,
        now: datetime,
    ) -> bool:
        self.calls.append((artifact_id, expected_content_hash, now))
        return self.result


def _audio(tmp_path: Path, *, duration_seconds: int = 60) -> tuple[AudioArtifact, Path]:
    audio_dir = tmp_path / "data" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    path = audio_dir / "fixture.wav"
    body = b"deterministic synthetic wav payload"
    path.write_bytes(body)
    return (
        AudioArtifact(
            artifact_id="audio-1",
            video_id="video-1",
            relative_path="audio/fixture.wav",
            content_hash=hashlib.sha256(body).hexdigest(),
            byte_count=len(body),
            duration_seconds=duration_seconds,
        ),
        path,
    )


def _record(audio: AudioArtifact) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=audio.artifact_id,
        artifact_key="audio-key",
        video_id=audio.video_id,
        job_id="job-1",
        kind=ArtifactKind.AUDIO,
        storage_root=StorageRoot.DATA,
        relative_path=audio.relative_path,
        content_hash=audio.content_hash,
        provider="yt-dlp",
        model=None,
        producer_version="test-v1",
        retention_class=RetentionClass.EPHEMERAL_AUDIO,
        created_at=FIXED_NOW,
        expires_at=FIXED_NOW,
        deleted_at=None,
    )


def test_duration_and_resource_policy_is_pure_and_never_changes_stage(tmp_path: Path) -> None:
    audio, _ = _audio(tmp_path, duration_seconds=10_801)
    policy = TranscriptionPolicy(
        max_duration_seconds=10_800,
        max_audio_bytes=100,
        min_free_disk_gib=20,
        min_available_memory_gib=10,
    )

    decision = policy.evaluate(
        audio,
        AudioResourceSnapshot(free_disk_gib=100, available_memory_gib=100),
    )

    assert decision is DurationDecision.DURATION_LIMIT_EXCEEDED
    assert policy.evaluate(
        audio,
        AudioResourceSnapshot(free_disk_gib=19, available_memory_gib=100),
    ) is DurationDecision.DURATION_LIMIT_EXCEEDED


def test_resource_policy_distinguishes_audio_disk_and_memory_limits(tmp_path: Path) -> None:
    audio, _ = _audio(tmp_path)
    policy = TranscriptionPolicy(
        max_duration_seconds=10_800,
        max_audio_bytes=audio.byte_count - 1,
        min_free_disk_gib=20,
        min_available_memory_gib=10,
    )

    assert policy.evaluate(
        audio,
        AudioResourceSnapshot(free_disk_gib=100, available_memory_gib=100),
    ) is DurationDecision.AUDIO_TOO_LARGE

    permitted_policy = TranscriptionPolicy(
        max_duration_seconds=10_800,
        max_audio_bytes=audio.byte_count,
        min_free_disk_gib=20,
        min_available_memory_gib=10,
    )
    assert permitted_policy.evaluate(
        audio,
        AudioResourceSnapshot(free_disk_gib=19, available_memory_gib=100),
    ) is DurationDecision.INSUFFICIENT_DISK
    assert permitted_policy.evaluate(
        audio,
        AudioResourceSnapshot(free_disk_gib=20, available_memory_gib=9),
    ) is DurationDecision.INSUFFICIENT_MEMORY
    assert permitted_policy.evaluate(
        audio,
        AudioResourceSnapshot(free_disk_gib=20, available_memory_gib=10),
    ) is DurationDecision.PERMITTED


def test_cache_key_binds_audio_model_revision_and_parameter_policy(tmp_path: Path) -> None:
    audio, _ = _audio(tmp_path)
    base = build_transcription_cache_key(
        audio_content_hash=audio.content_hash,
        model="mlx-community/whisper-large-v3-turbo",
        model_revision="a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb",
        parameter_policy_version="mlx-whisper-v1",
    )

    assert base == build_transcription_cache_key(
        audio_content_hash=audio.content_hash,
        model="mlx-community/whisper-large-v3-turbo",
        model_revision="a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb",
        parameter_policy_version="mlx-whisper-v1",
    )
    assert base != build_transcription_cache_key(
        audio_content_hash=audio.content_hash,
        model="mlx-community/whisper-large-v3-turbo",
        model_revision="b" * 40,
        parameter_policy_version="mlx-whisper-v1",
    )
    assert base != build_transcription_cache_key(
        audio_content_hash=audio.content_hash,
        model="mlx-community/whisper-large-v3-turbo",
        model_revision="a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb",
        parameter_policy_version="mlx-whisper-v2",
    )


def test_successful_cleanup_requires_verified_data_relative_audio(tmp_path: Path) -> None:
    audio, path = _audio(tmp_path)
    repository = _FakeArtifactRepository(record=_record(audio))

    result = cleanup_successful_audio(
        _record(audio),
        data_root=tmp_path / "data",
        repository=repository,
        now=FIXED_NOW,
    )

    assert result is AudioCleanupResult.DELETED
    assert not path.exists()
    assert repository.calls == [(audio.artifact_id, audio.content_hash, FIXED_NOW)]


def test_cleanup_hash_mismatch_never_deletes_unverified_audio(tmp_path: Path) -> None:
    audio, path = _audio(tmp_path)
    path.write_bytes(b"tampered")
    repository = _FakeArtifactRepository(record=_record(audio))

    mismatch = cleanup_successful_audio(
        _record(audio),
        data_root=tmp_path / "data",
        repository=repository,
        now=FIXED_NOW,
    )

    assert mismatch is AudioCleanupResult.HASH_MISMATCH
    assert path.exists()
    assert repository.calls == []


def test_final_cleanup_cas_race_reports_conflict_after_deletion(tmp_path: Path) -> None:
    audio, path = _audio(tmp_path)
    conflict = cleanup_successful_audio(
        _record(audio),
        data_root=tmp_path / "data",
        repository=_FakeArtifactRepository(record=_record(audio), result=False),
        now=FIXED_NOW,
    )

    assert conflict is AudioCleanupResult.INDEX_CONFLICT
    assert not path.exists()


def test_cleanup_rejects_a_non_audio_or_non_ephemeral_index_record(tmp_path: Path) -> None:
    audio, path = _audio(tmp_path)
    repository = _FakeArtifactRepository(record=_record(audio))

    result = cleanup_successful_audio(
        replace(_record(audio), kind=ArtifactKind.SUBTITLE_SOURCE),
        data_root=tmp_path / "data",
        repository=repository,
        now=FIXED_NOW,
    )

    assert result is AudioCleanupResult.INELIGIBLE_ARTIFACT
    assert path.exists()
    assert repository.calls == []


def test_cleanup_preflight_rejects_mismatched_registered_artifact(tmp_path: Path) -> None:
    audio, path = _audio(tmp_path)
    expected = _record(audio)

    for registered in (
        replace(expected, artifact_id="other-audio"),
        replace(expected, kind=ArtifactKind.SUBTITLE_SOURCE),
        replace(expected, storage_root=StorageRoot.VAULT),
        replace(expected, retention_class=RetentionClass.LONG_LIVED),
        replace(expected, content_hash="f" * 64),
    ):
        repository = _FakeArtifactRepository(record=registered)

        result = cleanup_successful_audio(
            expected,
            data_root=tmp_path / "data",
            repository=repository,
            now=FIXED_NOW,
        )

        assert result is AudioCleanupResult.INDEX_CONFLICT
        assert path.exists()
        assert repository.calls == []


def test_cleanup_preflight_rejects_missing_or_deleted_registered_artifact(
    tmp_path: Path,
) -> None:
    audio, path = _audio(tmp_path)
    expected = _record(audio)

    for registered in (None, replace(expected, deleted_at=FIXED_NOW)):
        repository = _FakeArtifactRepository(record=registered)

        result = cleanup_successful_audio(
            expected,
            data_root=tmp_path / "data",
            repository=repository,
            now=FIXED_NOW,
        )

        assert result is AudioCleanupResult.INDEX_CONFLICT
        assert path.exists()
        assert repository.calls == []


def test_cleanup_rejects_symlink_without_leaking_paths(
    tmp_path: Path,
) -> None:
    audio, path = _audio(tmp_path)
    outside = tmp_path / "outside-secret.wav"
    outside.write_bytes(b"outside payload")
    path.unlink()
    path.symlink_to(outside)
    record = _record(audio)

    result = cleanup_successful_audio(
        record,
        data_root=tmp_path / "data",
        repository=_FakeArtifactRepository(record=record),
        now=FIXED_NOW,
    )

    assert result is AudioCleanupResult.INDEX_CONFLICT
    assert path.is_symlink()
    assert outside.exists()
    assert str(path) not in result.value
    assert "payload" not in result.value


def test_cleanup_rejects_relative_and_absolute_escapes_without_deletion(
    tmp_path: Path,
) -> None:
    audio, _ = _audio(tmp_path)
    outside = tmp_path / "outside-synthetic.wav"
    outside.write_bytes(b"outside synthetic audio")

    for relative_path in ("../outside-synthetic.wav", str(outside)):
        record = replace(_record(audio), relative_path=relative_path)
        repository = _FakeArtifactRepository(record=record)

        result = cleanup_successful_audio(
            record,
            data_root=tmp_path / "data",
            repository=repository,
            now=FIXED_NOW,
        )

        assert result is AudioCleanupResult.INDEX_CONFLICT
        assert outside.exists()
        assert repository.calls == []
        assert str(outside) not in result.value
