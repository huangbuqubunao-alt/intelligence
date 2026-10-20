"""TASK-018B red contracts for immutable cue-level Evidence text authority."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.domain import SubtitleFormat
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    IntegrityConflict,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)
from youtube_intel.transcripts import normalize_timed_subtitle

NOW = datetime(2026, 9, 12, 9, 0, tzinfo=UTC)


def _repository(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert repository.initialize(now=NOW).version == 41
    return repository


def _seed_video_and_artifact(repository: SQLiteStateRepository, video_id: str = "video-018b") -> str:
    now = "2026-09-12T09:00:00.000000Z"
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT INTO videos (video_id, channel_id, pipeline_status, pipeline_version, discovered_at, updated_at) VALUES (?, 'UC_TEST', 'DISCOVERED', 'v1', ?, ?)",
            (video_id, now, now),
        )
    finally:
        connection.close()
    artifact = ArtifactWrite(
        artifact_id=f"artifact-{video_id}", artifact_key=f"key-{video_id}", video_id=video_id,
        job_id=None, kind=ArtifactKind.TRANSCRIPT_CANONICAL, storage_root=StorageRoot.DATA,
        relative_path=f"transcripts/{video_id}/canonical.txt", content_hash="a" * 64,
        provider="fixture", model=None, producer_version="v1", retention_class=RetentionClass.LONG_LIVED, expires_at=None,
    )
    repository.upsert_artifact(artifact, now=NOW)
    return artifact.artifact_id


def _timed(repository: SQLiteStateRepository, *, video_id: str = "video-018b") -> tuple[str, str]:
    artifact_id = _seed_video_and_artifact(repository, video_id)
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id, canonical_artifact_id=artifact_id,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=1000, text="First canonical cue."),
            TimedTranscriptCueWrite(start_ms=1000, end_ms=2000, text="Second canonical cue."),
        ),
    )
    repository.create_timed_transcript(timed, now=NOW)
    return artifact_id, timed.timed_transcript_id


def test_v014_upgrade_reaches_v19_without_backfilling_legacy_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    migrations = repository._load_migrations()
    monkeypatch.setattr(repository, "_load_migrations", lambda: migrations[:14])
    assert repository.initialize(now=NOW).version == 14
    monkeypatch.undo()
    artifact_id = _seed_video_and_artifact(repository)
    evidence = EvidenceWrite(
        evidence_id=build_evidence_id(video_id="video-018b", artifact_id=artifact_id, start_ms=0, end_ms=1000,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL),
        video_id="video-018b", artifact_id=artifact_id, start_ms=0, end_ms=1000,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en", availability=EvidenceAvailability.AVAILABLE,
    )
    connection = repository._connect()
    try:
        connection.execute(
            """
            INSERT INTO evidence (
                evidence_id, video_id, artifact_id, start_ms, end_ms,
                lineage_kind, role, language, availability, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence.evidence_id,
                evidence.video_id,
                evidence.artifact_id,
                evidence.start_ms,
                evidence.end_ms,
                evidence.lineage_kind.value,
                evidence.role.value,
                evidence.language,
                evidence.availability.value,
                "2026-09-12T09:00:00.000000Z",
            ),
        )
    finally:
        connection.close()
    assert repository.initialize(now=NOW).version == 41
    assert repository.resolve_verified_evidence_text(evidence.evidence_id) is None


def test_exact_cue_aligned_binding_is_hash_verified_and_immutable(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    artifact_id, timed_id = _timed(repository)
    evidence = EvidenceWrite(
        evidence_id=build_evidence_id(video_id="video-018b", artifact_id=artifact_id, start_ms=0, end_ms=2000,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL),
        video_id="video-018b", artifact_id=artifact_id, start_ms=0, end_ms=2000,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en", availability=EvidenceAvailability.AVAILABLE,
    )
    binding = EvidenceTextBindingWrite.from_timed_transcript(evidence=evidence, timed_transcript_id=timed_id, start_cue_index=0, end_cue_index=2, excerpt="First canonical cue.\nSecond canonical cue.")
    repository.create_evidence_with_text_binding(evidence, binding, now=NOW)
    resolved = repository.resolve_verified_evidence_text(evidence.evidence_id)
    assert resolved is not None
    assert resolved.excerpt == binding.excerpt
    assert resolved.excerpt_hash == binding.excerpt_hash
    with pytest.raises(IntegrityConflict):
        repository.create_evidence_text_binding(binding, now=NOW)


def test_foreign_or_partial_cue_binding_fails_closed(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    artifact_id, timed_id = _timed(repository)
    evidence = EvidenceWrite(
        evidence_id=build_evidence_id(video_id="video-018b", artifact_id=artifact_id, start_ms=10, end_ms=1000,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL),
        video_id="video-018b", artifact_id=artifact_id, start_ms=10, end_ms=1000,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT, role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en", availability=EvidenceAvailability.AVAILABLE,
    )
    binding = EvidenceTextBindingWrite.from_timed_transcript(evidence=evidence, timed_transcript_id=timed_id, start_cue_index=0, end_cue_index=1, excerpt="First canonical cue.")
    with pytest.raises((IntegrityConflict, ValueError)):
        repository.create_evidence_with_text_binding(evidence, binding, now=NOW)
    assert repository.get_evidence(evidence.evidence_id) is None


def test_timed_subtitle_projection_matches_existing_canonical_plain_text() -> None:
    raw = b"WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nFirst canonical cue.\n\n00:00:01.000 --> 00:00:02.000\nSecond canonical cue.\n"
    normalized = normalize_timed_subtitle(raw, SubtitleFormat.VTT)
    assert normalized.text == "First canonical cue.\nSecond canonical cue.\n"
    assert [(cue.start_ms, cue.end_ms, cue.text) for cue in normalized.timed_cues] == [
        (0, 1000, "First canonical cue."),
        (1000, 2000, "Second canonical cue."),
    ]
