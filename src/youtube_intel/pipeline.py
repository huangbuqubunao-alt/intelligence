"""Thin, recoverable orchestration over the existing stage services and state store."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Protocol

from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisSkipped,
    AppError,
    ErrorCode,
    JobStatus,
    PipelineStatus,
    ProcessingStage,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.retry import RetryPolicy
from youtube_intel.scoring import (
    H2CAuthoritativeGraphConflict,
    H2CStaleScoringLease,
)
from youtube_intel.scoring_admission import UnknownProviderState
from youtube_intel.state import (
    ArtifactWrite,
    JobRecord,
    ProviderCallCompletion,
    VideoRecord,
)


class StageDisposition(str, Enum):
    """Tell the orchestrator whether a successful handler should schedule again."""

    CONTINUE = "CONTINUE"
    DEFERRED = "DEFERRED"
    TERMINAL = "TERMINAL"


class PipelineInterrupted(Exception):
    """Testable process interruption: deliberately leave the claimed Job untouched."""


StageResult = AnalysisCompleted | StageDisposition | AnalysisSkipped | None
StageHandler = Callable[[JobRecord, VideoRecord], StageResult]


class PipelineRepository(Protocol):
    def get_video(self, video_id: str) -> VideoRecord | None: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...

    def claim_next_job(
        self,
        *,
        owner: str,
        lease_until: datetime,
        now: datetime,
        video_id: str | None = None,
    ) -> JobRecord | None: ...

    def complete_job(self, job_id: str, *, owner: str, now: datetime) -> JobRecord: ...

    def complete_stage(
        self,
        *,
        job_id: str,
        owner: str,
        video_id: str,
        expected_status: PipelineStatus,
        target_status: PipelineStatus,
        pipeline_version: str,
        artifacts: tuple[ArtifactWrite, ...],
        provider_call: ProviderCallCompletion | None,
        now: datetime,
    ) -> object: ...

    def fail_job(
        self,
        job_id: str,
        *,
        owner: str,
        error_code: ErrorCode,
        error_message: str,
        retry_at: datetime | None,
        now: datetime,
    ) -> JobRecord: ...

    def finalize_unknown_provider_state(
        self,
        job_id: str,
        *,
        owner: str,
        error_message: str,
        now: datetime,
    ) -> JobRecord: ...


@dataclass(slots=True)
class PipelineOrchestrator:
    """Dispatch claimed Jobs while preserving the repository's atomic stage contract."""

    repository: PipelineRepository
    planner: PipelineJobPlanner
    owner: str
    lease_seconds: int
    retry_policy: RetryPolicy
    handlers: Mapping[ProcessingStage, StageHandler]
    clock: Callable[[], datetime]

    def __post_init__(self) -> None:
        if not self.owner.strip():
            raise ValueError("pipeline owner must be non-empty")
        if self.lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")

    def run_batch(self, video_ids: tuple[str, ...], *, now: datetime | None = None) -> None:
        timestamp = self._now(now)
        self.planner.recover(now=timestamp)
        for video_id in video_ids:
            self.planner.ensure_next_job(video_id, now=timestamp)
        self._drain(timestamp, video_id=None)

    def resume_video(self, video_id: str, *, now: datetime | None = None) -> None:
        timestamp = self._now(now)
        self.planner.recover(now=timestamp)
        self.planner.ensure_next_job(video_id, now=timestamp)
        self._drain(timestamp, video_id=video_id)

    def resume_video_through_transcript(
        self, video_id: str, *, now: datetime | None = None
    ) -> None:
        """Run only the ingestion stages needed to persist a transcript body."""

        current = self.repository.get_video(video_id)
        if current is not None and current.pipeline_status not in {
            PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY, PipelineStatus.DEFERRED
        }:
            return
        timestamp = self._now(now)
        self.planner.recover(now=timestamp)
        self.planner.ensure_next_job(video_id, now=timestamp)
        self._drain(
            timestamp,
            video_id=video_id,
            stop_at_status=PipelineStatus.TRANSCRIPT_READY,
        )

    def _drain(
        self,
        now: datetime,
        *,
        video_id: str | None = None,
        stop_at_status: PipelineStatus | None = None,
    ) -> None:
        while True:
            if video_id is not None and stop_at_status is not None:
                current = self.repository.get_video(video_id)
                if current is not None and current.pipeline_status is stop_at_status:
                    return
            claimed = self.repository.claim_next_job(
                owner=self.owner,
                lease_until=now + timedelta(seconds=self.lease_seconds),
                now=now,
                video_id=video_id,
            )
            if claimed is None:
                return
            self._execute(claimed, now=now, stop_at_status=stop_at_status)

    def _execute(self, job: JobRecord, *, now: datetime,
                 stop_at_status: PipelineStatus | None = None) -> None:
        if job.video_id is None or job.pipeline_version != self.planner.pipeline_version:
            self._fail(job, self._invalid_job_error(job), now=now)
            return
        video = self.repository.get_video(job.video_id)
        if video is None:
            self._fail(job, self._invalid_job_error(job), now=now)
            return
        try:
            expected_stage = self.planner.next_stage(video)
        except ValueError:
            self._fail(job, self._invalid_job_error(job), now=now)
            return
        if expected_stage is not job.target_stage:
            # A previous worker completed this state transition before this stale job ran.
            self.repository.complete_job(job.job_id, owner=self.owner, now=now)
            return
        try:
            disposition = self._run_stage(job, video, now=now)
        except PipelineInterrupted:
            raise
        except (H2CStaleScoringLease, H2CAuthoritativeGraphConflict):
            # Frozen H2-C no-mutation handling: one side-effect-free read-back
            # decides the safe return.  Never fail_job, never generic _fail.
            self._h2c_no_mutation_return(job, now=now)
            return
        except UnknownProviderState as error:
            self.repository.finalize_unknown_provider_state(
                job.job_id,
                owner=self.owner,
                error_message=str(error),
                now=now,
            )
            return
        except Exception as error:
            self._fail(job, self._as_app_error(error, job), now=now)
            return
        if disposition is StageDisposition.TERMINAL:
            # The H2-B known-terminal path has already committed a non-retryable
            # FAILED_FINAL transition.  Verify it through a side-effect-free
            # repository read-back before suppressing the generic failure; a
            # fake or unrelated TERMINAL never suppresses generic failure unless
            # the repository already records FAILED_FINAL.  The disposition is
            # ordinary orchestration information and grants no authority.
            saved_terminal = self.repository.get_job(job.job_id)
            if (
                saved_terminal is not None
                and saved_terminal.status is JobStatus.FAILED_FINAL
            ):
                return
            self._fail(job, self._invalid_job_error(job), now=now)
            return
        saved_job = self.repository.get_job(job.job_id)
        if saved_job is None or saved_job.status is not JobStatus.SUCCEEDED:
            self._fail(job, self._invalid_job_error(job), now=now)
            return
        if disposition is StageDisposition.CONTINUE:
            current = self.repository.get_video(video.video_id)
            if stop_at_status is not None and current is not None and current.pipeline_status is stop_at_status:
                return
            self.planner.ensure_next_job(video.video_id, now=now)

    def _run_stage(
        self, job: JobRecord, video: VideoRecord, *, now: datetime
    ) -> StageDisposition:
        if (
            video.pipeline_status is PipelineStatus.SCORED
            and video.should_summarize is False
        ):
            self.repository.complete_stage(
                job_id=job.job_id,
                owner=self.owner,
                video_id=video.video_id,
                expected_status=PipelineStatus.SCORED,
                target_status=PipelineStatus.LOW_VALUE_READY,
                pipeline_version=self.planner.pipeline_version,
                artifacts=(),
                provider_call=None,
                now=now,
            )
            return StageDisposition.CONTINUE
        if video.pipeline_status in {
            PipelineStatus.LOW_VALUE_READY,
            PipelineStatus.NOTE_WRITTEN,
        }:
            self.repository.complete_stage(
                job_id=job.job_id,
                owner=self.owner,
                video_id=video.video_id,
                expected_status=video.pipeline_status,
                target_status=PipelineStatus.COMPLETE,
                pipeline_version=self.planner.pipeline_version,
                artifacts=(),
                provider_call=None,
                now=now,
            )
            return StageDisposition.CONTINUE
        handler = self.handlers.get(job.target_stage)
        if handler is None:
            raise ValueError("no handler is configured for the claimed processing stage")
        result = handler(job, video)
        if isinstance(result, AnalysisCompleted):
            if job.target_stage is not ProcessingStage.ANALYSIS:
                raise ValueError("only the analysis stage may return AnalysisCompleted")
            return StageDisposition.CONTINUE
        if isinstance(result, AnalysisSkipped):
            if job.target_stage is not ProcessingStage.ANALYSIS:
                raise ValueError("only the analysis stage may return AnalysisSkipped")
            self.repository.complete_stage(
                job_id=job.job_id,
                owner=self.owner,
                video_id=video.video_id,
                expected_status=PipelineStatus.SCORED,
                target_status=PipelineStatus.ANALYSIS_READY,
                pipeline_version=self.planner.pipeline_version,
                artifacts=(),
                provider_call=None,
                now=now,
            )
            return StageDisposition.CONTINUE
        if result is None:
            return StageDisposition.CONTINUE
        return result

    def _h2c_no_mutation_return(self, job: JobRecord, *, now: datetime) -> None:
        """Side-effect-free disposition for H2-C stale-lease/graph-conflict.

        Exactly one read-only ``get_job`` decides the safe return: a missing
        row, a RUNNING row owned by a different worker or with an
        expired/non-active lease, a FAILED_FINAL row, or a SUCCEEDED row all
        return without any mutation.  Any other observed state (including a
        RUNNING row still actively owned by this worker) is an interruption.
        """

        saved = self.repository.get_job(job.job_id)
        if saved is None:
            return
        if saved.status in {JobStatus.FAILED_FINAL, JobStatus.SUCCEEDED}:
            return
        if saved.status is JobStatus.RUNNING:
            lease_active = (
                saved.lease_until is not None and saved.lease_until > now
            )
            if saved.lease_owner != self.owner or not lease_active:
                return
        raise PipelineInterrupted()

    def _fail(self, job: JobRecord, error: AppError, *, now: datetime) -> None:
        self.repository.fail_job(
            job.job_id,
            owner=self.owner,
            error_code=error.code,
            error_message=error.message,
            retry_at=self.retry_policy.retry_at(
                error, attempt_count=job.attempt_count, now=now
            ),
            now=now,
        )

    @staticmethod
    def _invalid_job_error(job: JobRecord) -> AppError:
        return AppError(
            code=ErrorCode.INVALID_RESPONSE,
            message="claimed job is incompatible with the persisted pipeline state",
            retryable=False,
            video_id=job.video_id,
            stage=job.target_stage,
        )

    @staticmethod
    def _as_app_error(error: Exception, job: JobRecord) -> AppError:
        candidate = getattr(error, "error", None)
        if isinstance(candidate, AppError):
            return candidate
        return AppError(
            code=ErrorCode.LOCAL_RESOURCE,
            message="pipeline stage failed before completion",
            retryable=True,
            video_id=job.video_id,
            stage=job.target_stage,
        )

    def _now(self, supplied: datetime | None) -> datetime:
        now = self.clock() if supplied is None else supplied
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ValueError("pipeline clock must return a UTC datetime")
        return now.astimezone(UTC)
