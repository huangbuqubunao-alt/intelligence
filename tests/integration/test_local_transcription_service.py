"""Offline service-flow coverage for persisted local Whisper transcription."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.domain import (
    Availability,
    DiscoveryBatch,
    DiscoveryCursor,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    VideoMetadata,
)
from youtube_intel.providers.whisper import (
    MlxWhisperAdapter,
    WhisperDecodePolicy,
    WhisperResponse,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactWrite,
    JobStatus,
    JobType,
    ProviderCallStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)
from youtube_intel.transcription import AudioResourceSnapshot
from youtube_intel.transcripts import (
    LocalTranscriptionService,
    TranscriptError,
    TranscriptJobContext,
)

NOW = datetime(2026, 7, 26, 8, 0, tzinfo=UTC)
PIPELINE_VERSION = "pipeline-v1"
VIDEO_ID = "video123"


class _FakeWhisperExecutor:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def transcribe(
        self, audio_path: Path, policy: WhisperDecodePolicy
    ) -> WhisperResponse:
        self.calls.append(audio_path)
        assert policy.language_hint == "en"
        return WhisperResponse(text="A verified local transcription.", language="en")


class _FailingStageRepository:
    def __init__(self, repository: SQLiteStateRepository) -> None:
        self._repository = repository

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._repository, name)

    def complete_stage(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("injected stage failure")


def _metadata(video_id: str = VIDEO_ID) -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        channel_id="UC_TEST",
        channel_name="Test channel",
        title="Offline local transcription",
        description="",
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=NOW,
        duration_seconds=60,
        default_language="en",
        available_languages=(),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _prepare_repository(tmp_path: Path, *, job_id: str = "whisper-job") -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id="UC_TEST",
            video_ids=(VIDEO_ID,),
            next_cursor=DiscoveryCursor(channel_id="UC_TEST"),
            call=ProviderCallMetadata(provider="fake-source", started_at=NOW, finished_at=NOW),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version=PIPELINE_VERSION,
        now=NOW,
    )
    repository.upsert_video_metadata(_metadata(), pipeline_version=PIPELINE_VERSION, now=NOW)
    assert repository.advance_pipeline(
        VIDEO_ID,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version=PIPELINE_VERSION,
        now=NOW,
    )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{VIDEO_ID}:TRANSCRIPT",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    claimed = repository.claim_next_job(owner="worker-1", lease_until=NOW + timedelta(minutes=10), now=NOW)
    assert claimed is not None and claimed.job_id == job_id
    return repository


def _registered_audio(repository: SQLiteStateRepository, data_root: Path) -> ArtifactRecord:
    body = b"synthetic registered audio"
    path = data_root / "audio" / "fixture.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="audio-1",
            artifact_key="audio:fixture",
            video_id=VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.AUDIO,
            storage_root=StorageRoot.DATA,
            relative_path="audio/fixture.wav",
            content_hash=hashlib.sha256(body).hexdigest(),
            provider="fake-audio",
            model=None,
            producer_version="audio-v1",
            retention_class=RetentionClass.EPHEMERAL_AUDIO,
            expires_at=NOW + timedelta(days=7),
        ),
        now=NOW,
    )


def _service(
    repository: SQLiteStateRepository,
    data_root: Path,
    executor: _FakeWhisperExecutor,
    *,
    job_id: str = "whisper-job",
) -> LocalTranscriptionService:
    policy = WhisperDecodePolicy(language_hint="en")
    return LocalTranscriptionService(
        adapter=MlxWhisperAdapter(
            executor=executor,
            decode_policy=policy,
            clock=lambda: NOW,
        ),
        repository=repository,
        context=TranscriptJobContext(job_id=job_id, owner="worker-1", pipeline_version=PIPELINE_VERSION),
        data_root=data_root,
        resources=AudioResourceSnapshot(free_disk_gib=100, available_memory_gib=100),
        decode_policy=policy,
        clock=lambda: NOW,
    )


def test_real_service_persists_verified_transcript_completes_stage_and_cleans_audio(tmp_path: Path) -> None:
    repository = _prepare_repository(tmp_path)
    data_root = tmp_path / "data"
    audio = _registered_audio(repository, data_root)
    executor = _FakeWhisperExecutor()

    result = _service(repository, data_root, executor).transcribe(audio)

    assert result.artifact.text_path.startswith(f"transcripts/{VIDEO_ID}/")
    assert (data_root / result.artifact.text_path).read_text(encoding="utf-8") == "A verified local transcription.\n"
    assert len(executor.calls) == 1
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.TRANSCRIPT_READY  # type: ignore[union-attr]
    assert repository.get_job("whisper-job").status is JobStatus.SUCCEEDED  # type: ignore[union-attr]
    persisted_audio = repository.get_artifact_by_key(audio.artifact_key)
    assert persisted_audio is not None and persisted_audio.deleted_at is not None
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        artifact = connection.execute("SELECT kind, storage_root FROM artifacts WHERE kind = 'transcript_canonical'").fetchone()
        provider_call = connection.execute("SELECT status, response_artifact_id FROM provider_calls").fetchone()
    assert artifact == ("transcript_canonical", "DATA")
    assert provider_call is not None and provider_call[0] == ProviderCallStatus.SUCCEEDED.value


def test_persisted_cache_reuses_verified_result_without_executor_or_duplicate_records(tmp_path: Path) -> None:
    repository = _prepare_repository(tmp_path)
    data_root = tmp_path / "data"
    audio = _registered_audio(repository, data_root)
    first_executor = _FakeWhisperExecutor()
    _service(repository, data_root, first_executor).transcribe(audio)

    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute("UPDATE videos SET pipeline_status = 'METADATA_READY' WHERE video_id = ?", (VIDEO_ID,))
        connection.execute("UPDATE artifacts SET deleted_at = NULL WHERE artifact_key = ?", (audio.artifact_key,))
        connection.commit()
    (data_root / audio.relative_path).write_bytes(b"synthetic registered audio")
    repository.create_job(
        job_id="cache-job",
        scope_key=f"video:{VIDEO_ID}:TRANSCRIPT",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    assert repository.claim_next_job(owner="worker-1", lease_until=NOW + timedelta(minutes=10), now=NOW) is not None
    second_executor = _FakeWhisperExecutor()

    _service(repository, data_root, second_executor, job_id="cache-job").transcribe(repository.get_artifact_by_key(audio.artifact_key))  # type: ignore[arg-type]

    assert second_executor.calls == []
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM artifacts WHERE kind = 'transcript_canonical'").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM provider_calls").fetchone() == (1,)


@pytest.mark.parametrize("tamper", ("hash", "symlink", "outside"))
def test_unverified_audio_fails_closed_without_execution_or_cleanup(tmp_path: Path, tamper: str) -> None:
    repository = _prepare_repository(tmp_path)
    data_root = tmp_path / "data"
    audio = _registered_audio(repository, data_root)
    path = data_root / audio.relative_path
    outside = tmp_path / "outside.wav"
    if tamper == "hash":
        path.write_bytes(b"tampered")
    elif tamper == "symlink":
        outside.write_bytes(b"outside")
        path.unlink()
        path.symlink_to(outside)
    else:
        audio = replace(audio, relative_path=str(outside))
    executor = _FakeWhisperExecutor()

    with pytest.raises(TranscriptError):
        _service(repository, data_root, executor).transcribe(audio)

    assert executor.calls == []
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.METADATA_READY  # type: ignore[union-attr]
    assert path.exists() or outside.exists()


def test_stale_pipeline_context_fails_closed_before_executor_or_cleanup(tmp_path: Path) -> None:
    repository = _prepare_repository(tmp_path)
    data_root = tmp_path / "data"
    audio = _registered_audio(repository, data_root)
    executor = _FakeWhisperExecutor()
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute("UPDATE videos SET pipeline_status = 'DISCOVERED' WHERE video_id = ?", (VIDEO_ID,))
        connection.commit()

    with pytest.raises(TranscriptError) as raised:
        _service(repository, data_root, executor).transcribe(audio)

    assert raised.value.error.retryable is True
    assert executor.calls == []
    assert (data_root / audio.relative_path).exists()


def test_database_failure_removes_new_transcript_and_preserves_retryable_provider_call(tmp_path: Path) -> None:
    repository = _prepare_repository(tmp_path)
    data_root = tmp_path / "data"
    audio = _registered_audio(repository, data_root)
    executor = _FakeWhisperExecutor()

    with pytest.raises(TranscriptError) as raised:
        _service(_FailingStageRepository(repository), data_root, executor).transcribe(audio)

    assert raised.value.error.retryable is True
    if (data_root / "transcripts").exists():
        assert list((data_root / "transcripts").rglob("*.txt")) == []
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.METADATA_READY  # type: ignore[union-attr]
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        assert connection.execute("SELECT status FROM provider_calls").fetchone() == (ProviderCallStatus.FAILED_RETRYABLE.value,)
