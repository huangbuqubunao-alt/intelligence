"""Temporary-Vault integration tests for the Obsidian note sink."""

from __future__ import annotations

import errno
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import youtube_intel.providers.obsidian as obsidian_module
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisPoint,
    AnalysisResult,
    Availability,
    ErrorCode,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    PipelineStatus,
    PointKind,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
    SubtitleFormat,
    TranscriptArtifact,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.notes import render_video_note
from youtube_intel.providers.obsidian import (
    NotePersistenceError,
    NoteWriteContext,
    ObsidianNoteSink,
)
from youtube_intel.state import (
    ArtifactKind,
    JobStatus,
    JobType,
    ProcessingStage,
    SQLiteStateRepository,
)

NOW = datetime(2026, 7, 22, 9, 8, 7, tzinfo=UTC)
VIDEO_ID = "video-123"
PIPELINE_VERSION = "pipeline-v1"


def _video(*, title: str = "A safe product note") -> VideoMetadata:
    return VideoMetadata(
        video_id=VIDEO_ID,
        channel_id="channel-123",
        channel_name="Example Channel",
        title=title,
        description="A concise description.",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=NOW,
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _transcript() -> TranscriptArtifact:
    return TranscriptArtifact(
        video_id=VIDEO_ID,
        language="en",
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="en",
        source_format=SubtitleFormat.VTT,
        text_path="transcripts/video-123.txt",
        timed_text_path="transcripts/video-123.vtt",
        source_content_hash="a" * 64,
        source_byte_count=100,
        content_hash="b" * 64,
        char_count=100,
        segment_count=3,
        normalization_version="subtitle-normalization-v1",
        provider="fixture",
        created_at=NOW,
    )


def _scoring() -> ScoringOutcome:
    return ScoringOutcome(
        result=ScoreResult(
            schema_version="score-result-v1",
            score=8.5,
            reason="Directly useful to product strategy.",
            topics=("product",),
            should_summarize=True,
            provider="fixture-scoring",
            model="fixture-model",
            prompt_version="scoring-prompt-v1",
            request_hash="c" * 64,
        ),
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=True,
            model_disagrees=False,
        ),
        call=ProviderCallMetadata(
            provider="fixture-scoring",
            model="fixture-model",
            started_at=NOW,
            finished_at=NOW,
        ),
    )


def _analysis() -> AnalysisCompleted:
    return AnalysisCompleted(
        result=AnalysisResult(
            one_sentence_summary="A compact summary.",
            core_points=(
                AnalysisPoint(
                    text="The product has a clear user need.",
                    kind=PointKind.FACT,
                    evidence_ids=("evidence-1",),
                ),
            ),
            keywords=("product",),
            evidence=(
                EvidenceExcerpt(
                    evidence_id="evidence-1",
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    excerpt="A verified excerpt.",
                ),
            ),
            provider="fixture-analysis",
            model="fixture-model",
            request_hash="d" * 64,
        ),
        call=ProviderCallMetadata(
            provider="fixture-analysis",
            model="fixture-model",
            started_at=NOW,
            finished_at=NOW,
        ),
    )


def _repository_with_claimed_note_job(
    tmp_path: Path, *, job_id: str = "note-job-1"
) -> tuple[SQLiteStateRepository, NoteWriteContext]:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(_video(), pipeline_version=PIPELINE_VERSION, now=NOW)
    for current, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
        (PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SCORED),
        (PipelineStatus.SCORED, PipelineStatus.ANALYSIS_READY),
    ):
        assert repository.advance_pipeline(
            VIDEO_ID,
            expected_status=current,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            now=NOW,
        )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{VIDEO_ID}:NOTE_WRITE",
        video_id=VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.NOTE_WRITE,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )
    claimed = repository.claim_next_job(
        owner="test-worker", lease_until=NOW + timedelta(minutes=5), now=NOW
    )
    assert claimed is not None
    return repository, NoteWriteContext(
        job_id=claimed.job_id,
        owner="test-worker",
        pipeline_version=PIPELINE_VERSION,
    )


def _sink(
    *,
    repository: SQLiteStateRepository,
    context: NoteWriteContext,
    vault_root: Path,
) -> ObsidianNoteSink:
    (vault_root / "Knowledge").mkdir(parents=True, exist_ok=True)
    return ObsidianNoteSink(
        vault_root=vault_root,
        vault_subdir="Knowledge",
        repository=repository,
        context=context,
    )


def test_sink_writes_one_managed_note_and_completes_note_stage(tmp_path: Path) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    sink = _sink(repository=repository, context=context, vault_root=tmp_path / "vault")

    note_ref = sink.upsert_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )

    note_path = tmp_path / "vault" / "Knowledge" / note_ref.relative_path
    assert note_path.is_file()
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.NOTE_WRITTEN
    assert repository.get_job(context.job_id).status is JobStatus.SUCCEEDED
    artifact = repository.get_artifact_by_key(
        f"video-note/{PIPELINE_VERSION}/{VIDEO_ID}"
    )
    assert artifact is not None
    assert artifact.kind is ArtifactKind.VIDEO_NOTE
    assert artifact.relative_path == note_ref.relative_path
    assert artifact.content_hash == note_ref.content_hash


def test_completed_note_keeps_user_bytes_and_is_not_replaced(tmp_path: Path) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    sink = _sink(repository=repository, context=context, vault_root=tmp_path / "vault")
    first = sink.upsert_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )
    path = tmp_path / "vault" / "Knowledge" / first.relative_path
    content = path.read_text(encoding="utf-8").replace(
        "## 我的思考\n\n", "## 我的思考\n\n用户保留的原始字节\n"
    )
    path.write_text(content, encoding="utf-8")
    before = path.stat().st_ino

    returned = sink.upsert_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )

    assert returned.relative_path == first.relative_path
    assert path.stat().st_ino == before
    assert "用户保留的原始字节" in path.read_text(encoding="utf-8")


def test_completed_note_keeps_its_first_path_when_the_title_changes(tmp_path: Path) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    sink = _sink(repository=repository, context=context, vault_root=tmp_path / "vault")
    first = sink.upsert_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )
    path = tmp_path / "vault" / "Knowledge" / first.relative_path
    before = path.read_bytes()
    before_inode = path.stat().st_ino
    renamed = _video(title="A renamed product note")
    repository.upsert_video_metadata(renamed, pipeline_version=PIPELINE_VERSION, now=NOW)

    returned = sink.upsert_video_note(
        video=renamed,
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )

    assert returned == first
    assert path.read_bytes() == before
    assert path.stat().st_ino == before_inode
    assert not (
        tmp_path / "vault" / "Knowledge" / "Videos" / "A renamed product note--video-123.md"
    ).exists()


@pytest.mark.parametrize(
    "candidate_names",
    (
        ("Legacy--video-123.md",),
        ("One--video-123.md", "Two--video-123.md"),
        ("A safe product note--VIDEO-123.md",),
        ("Cafe\u0301--video-123.md",),
    ),
    ids=("unmanaged", "multiple", "casefold", "nfc"),
)
def test_sink_rejects_all_conflicting_video_id_candidates_without_writing(
    tmp_path: Path, candidate_names: tuple[str, ...]
) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    vault_root = tmp_path / "vault"
    videos = vault_root / "Knowledge" / "Videos"
    videos.mkdir(parents=True)
    expected = {
        name: f"unmanaged candidate: {name}".encode("utf-8") for name in candidate_names
    }
    for name, content in expected.items():
        (videos / name).write_bytes(content)
    sink = _sink(repository=repository, context=context, vault_root=vault_root)

    with pytest.raises(NotePersistenceError):
        sink.upsert_video_note(
            video=_video(),
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version=PIPELINE_VERSION,
        )

    assert {path.name: path.read_bytes() for path in videos.iterdir()} == expected
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.ANALYSIS_READY


def test_sink_rejects_drive_style_vault_subdirectories(tmp_path: Path) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    with pytest.raises(ValueError):
        ObsidianNoteSink(
            vault_root=vault_root,
            vault_subdir="C:",
            repository=repository,
            context=context,
        )

    assert list(vault_root.iterdir()) == []


def test_sqlite_failure_after_replace_is_recovered_by_a_retried_note_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    sink = _sink(repository=repository, context=context, vault_root=tmp_path / "vault")

    def fail_after_artifacts(point: str) -> None:
        if point == "stage.after_artifacts":
            raise RuntimeError("injected sqlite failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_after_artifacts)
    with pytest.raises(NotePersistenceError):
        sink.upsert_video_note(
            video=_video(),
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version=PIPELINE_VERSION,
        )
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.ANALYSIS_READY
    note_path = tmp_path / "vault" / "Knowledge" / "Videos" / "A safe product note--video-123.md"
    assert note_path.is_file()

    monkeypatch.setattr(repository, "_inject_failure", lambda point: None)
    repository.fail_job(
        context.job_id,
        owner=context.owner,
        error_code=ErrorCode.LOCAL_RESOURCE,
        error_message="safe retryable note persistence failure",
        retry_at=NOW,
        now=NOW,
    )
    assert repository.activate_retry_jobs(now=NOW)
    claimed = repository.claim_next_job(
        owner=context.owner, lease_until=NOW + timedelta(minutes=5), now=NOW
    )
    assert claimed is not None
    retry_sink = _sink(
        repository=repository,
        context=NoteWriteContext(
            job_id=claimed.job_id,
            owner=context.owner,
            pipeline_version=PIPELINE_VERSION,
        ),
        vault_root=tmp_path / "vault",
    )

    ref = retry_sink.upsert_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )
    assert ref.relative_path == "Videos/A safe product note--video-123.md"
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.NOTE_WRITTEN


def test_sink_rejects_a_symlinked_managed_directory_without_writing_target(
    tmp_path: Path,
) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    vault_root = tmp_path / "vault"
    managed_root = vault_root / "Knowledge"
    managed_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (managed_root / "Videos").symlink_to(outside, target_is_directory=True)
    sink = _sink(repository=repository, context=context, vault_root=vault_root)

    with pytest.raises(NotePersistenceError):
        sink.upsert_video_note(
            video=_video(),
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version=PIPELINE_VERSION,
        )

    assert list(outside.iterdir()) == []
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.ANALYSIS_READY


def test_sink_rejects_a_legacy_note_without_changing_it(tmp_path: Path) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    vault_root = tmp_path / "vault"
    note_path = vault_root / "Knowledge" / "Videos" / "A safe product note--video-123.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_bytes(b"legacy user note\n")
    sink = _sink(repository=repository, context=context, vault_root=vault_root)

    with pytest.raises(NotePersistenceError):
        sink.upsert_video_note(
            video=_video(),
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version=PIPELINE_VERSION,
        )

    assert note_path.read_bytes() == b"legacy user note\n"
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.ANALYSIS_READY


@pytest.mark.parametrize(
    ("operation", "error_number", "expected_code"),
    (
        ("fsync", errno.EACCES, ErrorCode.PERMISSION_DENIED),
        ("fsync", errno.EPERM, ErrorCode.PERMISSION_DENIED),
        ("fsync", errno.EROFS, ErrorCode.PERMISSION_DENIED),
        ("fsync", errno.ENOSPC, ErrorCode.LOCAL_RESOURCE),
        ("fsync", None, ErrorCode.LOCAL_RESOURCE),
        ("replace", None, ErrorCode.LOCAL_RESOURCE),
    ),
)
def test_sink_maps_atomic_write_errors_safely_without_advancing_note_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    error_number: int | None,
    expected_code: ErrorCode,
) -> None:
    repository, context = _repository_with_claimed_note_job(tmp_path)
    vault_root = tmp_path / "vault"
    sink = _sink(repository=repository, context=context, vault_root=vault_root)
    rendered = render_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )
    original = rendered.content.encode("utf-8").replace(
        b"A compact summary.", b"An earlier compact summary."
    )
    note_path = vault_root / "Knowledge" / rendered.relative_path
    note_path.parent.mkdir(parents=True)
    note_path.write_bytes(original)

    def fail_operation(*args: object, **kwargs: object) -> None:
        del args, kwargs
        if error_number is None:
            raise OSError("injected atomic write failure")
        raise OSError(error_number, "injected fsync failure")

    monkeypatch.setattr(obsidian_module.os, operation, fail_operation)
    with pytest.raises(NotePersistenceError) as exc_info:
        sink.upsert_video_note(
            video=_video(),
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version=PIPELINE_VERSION,
        )

    videos = vault_root / "Knowledge" / "Videos"
    assert {path.name: path.read_bytes() for path in videos.iterdir()} == {
        note_path.name: original
    }
    assert exc_info.value.error.code is expected_code
    assert exc_info.value.error.message == "note persistence failed"
    assert repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.ANALYSIS_READY
    assert repository.get_job(context.job_id).status is JobStatus.RUNNING
    assert repository.get_artifact_by_key(f"video-note/{PIPELINE_VERSION}/{VIDEO_ID}") is None
