"""TASK-016E/F verified Note V2 aggregation handoff contract."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.integration.test_deep_analysis_persistence import _trusted_success
from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.note_v2 import build_note_v2
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import VideoRecord
from youtube_intel.verified_note_v2 import (
    VerifiedNoteV2ArtifactError,
    build_verified_note_v2_artifact,
    verify_verified_note_v2_artifact,
)

NOW = datetime(2026, 8, 30, 12, tzinfo=UTC)


class _Repository:
    def __init__(self, record: VideoRecord) -> None:
        self._record = record

    def get_video(self, video_id: str) -> VideoRecord | None:
        return self._record if video_id == self._record.video_id else None


def _score_read(*, video_id: str = "video-1", score: float = 8.0) -> VerifiedScoringRead:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=score,
        reason="This result contains a concrete useful explanation of the score.",
        topics=("workflow",),
        should_summarize=True,
        provider="scoring-provider",
        model="scoring-model",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )
    return VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=7.0, final_should_summarize=True, model_disagrees=False
            ),
            call=ProviderCallMetadata(
                provider="scoring-provider", model="scoring-model", started_at=NOW, finished_at=NOW
            ),
        ),
        video_id=video_id,
        scoring_job_id="job-1",
        scoring_success_provenance="PRIMARY",
    )


def _record(
    *, video_id: str = "video-1", completed_at: datetime = NOW, score: float = 8.0
) -> VideoRecord:
    return VideoRecord(
        video_id=video_id,
        channel_id="channel-1",
        channel_name="Channel",
        title="Verified video",
        description="not aggregation input",
        source_url=f"https://example.invalid/{video_id}",
        published_at=NOW,
        duration_seconds=42,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
        pipeline_status=PipelineStatus.COMPLETE,
        pipeline_version="pipeline-v1",
        score=score,
        should_summarize=True,
        discovered_at=NOW,
        updated_at=NOW,
        completed_at=completed_at,
        authoritative_scoring_job_id="job-1",
    )


def _artifact(
    *, video_id: str = "video-1", completed_at: datetime = NOW, score: float = 8.0
) -> Any:
    return build_verified_note_v2_artifact(
        _trusted_success(video_id=video_id, score=score),
        repository=_Repository(_record(video_id=video_id, completed_at=completed_at, score=score)),
        scoring_reader=lambda _video_id: _score_read(video_id=video_id, score=score),
    )


def test_authoritative_builder_binds_note_and_weekly_metadata_without_changing_note_identity() -> None:
    source = _trusted_success()
    note = build_note_v2(source)
    first = build_verified_note_v2_artifact(
        source, repository=_Repository(_record(completed_at=NOW)), scoring_reader=lambda _video_id: _score_read()
    )
    second = build_verified_note_v2_artifact(
        source,
        repository=_Repository(_record(completed_at=datetime(2026, 8, 31, 12, tzinfo=UTC))),
        scoring_reader=lambda _video_id: _score_read(),
    )

    assert first.note == note
    assert first.note_identity == note.identity
    assert second.note.identity == note.identity
    assert first.identity != second.identity
    assert verify_verified_note_v2_artifact(first)


def test_lookalike_and_tampered_artifacts_are_not_admitted() -> None:
    artifact = _artifact()

    assert not verify_verified_note_v2_artifact(replace(artifact))
    tampered = replace(artifact, source_url="https://attacker.invalid/forged")
    assert not verify_verified_note_v2_artifact(tampered)


def test_caller_cannot_supply_a_forged_score_or_week_date_to_the_authoritative_builder() -> None:
    source = _trusted_success()

    with pytest.raises(VerifiedNoteV2ArtifactError, match="score"):
        build_verified_note_v2_artifact(
            source,
            repository=_Repository(_record(score=8.0)),
            scoring_reader=lambda _video_id: _score_read(score=9.9),
        )
    artifact = _artifact()
    assert artifact.completed_at == NOW
    assert "completed_at" not in build_verified_note_v2_artifact.__annotations__


def test_live_and_integrity_verified_persisted_sources_produce_the_same_artifact(
    tmp_path: Path,
) -> None:
    from youtube_intel.state import SQLiteStateRepository

    source = _trusted_success()
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    persisted = DeepAnalysisPersistenceStore(repository).persist_trusted_deep_analysis_success(
        success=source, now=NOW
    )
    weekly_repository = _Repository(_record())
    live = build_verified_note_v2_artifact(
        source, repository=weekly_repository, scoring_reader=lambda _video_id: _score_read()
    )
    rehydrated = build_verified_note_v2_artifact(
        persisted, repository=weekly_repository, scoring_reader=lambda _video_id: _score_read()
    )

    assert rehydrated == live
    assert rehydrated.identity == live.identity


def test_selected_evidence_only_sentinel_cannot_leak_into_the_note_or_weekly_handoff() -> None:
    sentinel = "SECRET_WEEKLY_UNSELECTED_TEXT"
    artifact = build_verified_note_v2_artifact(
        _trusted_success(public_description=sentinel),
        repository=_Repository(_record()),
        scoring_reader=lambda _video_id: _score_read(),
    )

    assert sentinel not in repr(artifact.note)
    assert sentinel not in repr(artifact)
