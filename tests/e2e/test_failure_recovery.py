"""Offline recovery acceptance coverage for every user-visible pipeline stage."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.domain import (
    AppError,
    Availability,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import PipelineOrchestrator, StageDisposition
from youtube_intel.retry import RetryPolicy
from youtube_intel.state import ScoringSummaryWrite, SQLiteStateRepository

NOW = datetime(2026, 7, 23, 9, 0, tzinfo=UTC)
PIPELINE_VERSION = "pipeline-v1"
STAGES = (
    ProcessingStage.METADATA,
    ProcessingStage.TRANSCRIPT,
    ProcessingStage.SCORING,
    ProcessingStage.ANALYSIS,
    ProcessingStage.NOTE_WRITE,
)


def _metadata() -> VideoMetadata:
    return VideoMetadata(
        video_id="recoverable",
        channel_id="UC_OFFLINE",
        channel_name="Offline Fixture Channel",
        title="Recoverable fixed fixture",
        description="Synthetic fixture only.",
        source_url="https://example.invalid/watch?v=recoverable",
        published_at=NOW,
        duration_seconds=120,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


class _InjectedStageFailure(Exception):
    def __init__(self, stage: ProcessingStage) -> None:
        self.error = AppError(
            code=ErrorCode.PROVIDER_UNAVAILABLE,
            message=f"offline injected failure at {stage.value}",
            retryable=True,
            video_id="recoverable",
            stage=stage,
        )
        super().__init__(self.error.message)


class _RecoveringStages:
    def __init__(self, repository: SQLiteStateRepository, failure: ProcessingStage) -> None:
        self.repository = repository
        self.failure = failure
        self.failed = False
        self.calls: Counter[ProcessingStage] = Counter()

    def __call__(self, job: object, video: object) -> StageDisposition:
        stage = getattr(job, "target_stage")
        self.calls[stage] += 1
        if stage is self.failure and not self.failed:
            self.failed = True
            raise _InjectedStageFailure(stage)
        target = {
            ProcessingStage.METADATA: PipelineStatus.METADATA_READY,
            ProcessingStage.TRANSCRIPT: PipelineStatus.TRANSCRIPT_READY,
            ProcessingStage.SCORING: PipelineStatus.SCORED,
            ProcessingStage.ANALYSIS: PipelineStatus.ANALYSIS_READY,
            ProcessingStage.NOTE_WRITE: PipelineStatus.NOTE_WRITTEN,
        }[stage]
        self.repository.complete_stage(
            job_id=str(getattr(job, "job_id")),
            owner=str(getattr(job, "lease_owner")),
            video_id="recoverable",
            expected_status=getattr(video, "pipeline_status"),
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            artifacts=(),
            provider_call=None,
            scoring_summary=(
                ScoringSummaryWrite(score=9.0, should_summarize=True)
                if stage is ProcessingStage.SCORING
                else None
            ),
            now=NOW,
        )
        return StageDisposition.CONTINUE


def _pipeline(repository: SQLiteStateRepository, stages: _RecoveringStages) -> PipelineOrchestrator:
    next_job = 0

    def job_id() -> str:
        nonlocal next_job
        next_job += 1
        return f"recovery-e2e-{next_job:03d}"

    return PipelineOrchestrator(
        repository=repository,
        planner=PipelineJobPlanner(
            repository=repository,
            pipeline_version=PIPELINE_VERSION,
            max_attempts=3,
            job_id_factory=job_id,
        ),
        owner="offline-recovery-worker",
        lease_seconds=60,
        retry_policy=RetryPolicy(base_delay_seconds=1, max_delay_seconds=8, jitter_ratio=0),
        handlers={stage: stages for stage in STAGES},
        clock=lambda: NOW,
    )


@pytest.mark.parametrize(
    ("failure_name", "failure_stage"),
    (
        ("subtitle", ProcessingStage.TRANSCRIPT),
        ("whisper", ProcessingStage.TRANSCRIPT),
        ("scoring", ProcessingStage.SCORING),
        ("cloud_analysis", ProcessingStage.ANALYSIS),
        ("note_write", ProcessingStage.NOTE_WRITE),
    ),
)
def test_each_offline_failure_recovers_without_repeating_completed_expensive_stages(
    tmp_path: Path, failure_name: str, failure_stage: ProcessingStage
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        _metadata(), pipeline_version=PIPELINE_VERSION, now=NOW
    )
    stages = _RecoveringStages(repository, failure_stage)
    pipeline = _pipeline(repository, stages)

    pipeline.run_batch(("recoverable",))

    failed_job = repository.get_job(
        f"recovery-e2e-{STAGES.index(failure_stage) + 1:03d}"
    )
    assert failure_name
    assert failed_job is not None and failed_job.status.value == "RETRY_PENDING"
    assert stages.calls[failure_stage] == 1

    pipeline.resume_video("recoverable", now=NOW + timedelta(seconds=1))

    video = repository.get_video("recoverable")
    assert video is not None and video.pipeline_status is PipelineStatus.COMPLETE
    assert stages.calls[failure_stage] == 2
    failed_index = STAGES.index(failure_stage)
    assert all(stages.calls[stage] == 1 for stage in STAGES[:failed_index])
    assert all(stages.calls[stage] == 1 for stage in STAGES[failed_index + 1 :])
