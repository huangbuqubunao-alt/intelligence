"""Job planning and lease recovery for the Pipeline state machine."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol
from uuid import uuid4

from youtube_intel.domain import PipelineStatus, ProcessingStage
from youtube_intel.state import (
    IntegrityConflict,
    JobRecord,
    JobType,
    VideoRecord,
)


class PipelineJobRepository(Protocol):
    def get_video(self, video_id: str) -> VideoRecord | None: ...

    def create_job(
        self,
        *,
        job_id: str,
        scope_key: str,
        video_id: str | None,
        job_type: JobType,
        target_stage: ProcessingStage,
        pipeline_version: str,
        max_attempts: int,
        available_at: datetime,
        now: datetime,
    ) -> JobRecord: ...

    def reclaim_expired_jobs(self, *, now: datetime) -> tuple[JobRecord, ...]: ...

    def activate_retry_jobs(self, *, now: datetime) -> tuple[JobRecord, ...]: ...


def _new_job_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class PipelineJobPlanner:
    """Map a video's last successful state to its sole next video-stage Job."""

    repository: PipelineJobRepository
    pipeline_version: str
    max_attempts: int
    job_id_factory: Callable[[], str] = field(default=_new_job_id)

    def __post_init__(self) -> None:
        if not self.pipeline_version.strip():
            raise ValueError("pipeline_version must be non-empty")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")

    @staticmethod
    def next_stage(video: VideoRecord) -> ProcessingStage | None:
        """Return the next stage without inferring success from files or jobs."""

        status = video.pipeline_status
        if status in {PipelineStatus.DISCOVERED, PipelineStatus.DEFERRED}:
            return ProcessingStage.METADATA
        if status is PipelineStatus.METADATA_READY:
            return ProcessingStage.TRANSCRIPT
        if status in {PipelineStatus.TRANSCRIPT_READY, PipelineStatus.LOW_VALUE_READY}:
            return ProcessingStage.SCORING
        if status is PipelineStatus.SCORED:
            if video.should_summarize is None:
                raise ValueError("SCORED video is missing its persisted value decision")
            return (
                ProcessingStage.ANALYSIS
                if video.should_summarize
                else ProcessingStage.SCORING
            )
        if status in {PipelineStatus.ANALYSIS_READY, PipelineStatus.NOTE_WRITTEN}:
            return ProcessingStage.NOTE_WRITE
        if status in {PipelineStatus.COMPLETE, PipelineStatus.SKIPPED_DURATION_LIMIT}:
            return None
        raise ValueError(f"unsupported pipeline status: {status.value}")

    def ensure_next_job(self, video_id: str, *, now: datetime) -> JobRecord | None:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ValueError("job planner clock must return a UTC datetime")
        video = self.repository.get_video(video_id)
        if video is None:
            raise ValueError("video does not exist")
        if video.pipeline_version != self.pipeline_version:
            raise ValueError("video pipeline version does not match the planner")
        target_stage = self.next_stage(video)
        if target_stage is None:
            return None
        try:
            return self.repository.create_job(
                job_id=self.job_id_factory(),
                scope_key=f"video:{video.video_id}:{target_stage.value}",
                video_id=video.video_id,
                job_type=JobType.VIDEO_STAGE,
                target_stage=target_stage,
                pipeline_version=self.pipeline_version,
                max_attempts=self.max_attempts,
                available_at=now,
                now=now,
            )
        except IntegrityConflict:
            # The partial unique index already owns an active equivalent Job.
            return None

    def recover(self, *, now: datetime) -> tuple[JobRecord, ...]:
        """Recover expired leases and make due retries claimable again."""

        self.repository.reclaim_expired_jobs(now=now)
        return self.repository.activate_retry_jobs(now=now)
