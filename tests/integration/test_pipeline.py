"""Integration coverage for TASK-010's state-machine orchestration."""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel.analysis import (
    AnalysisJobContext,
    CloudCallBudget,
    RepositoryBackedAnalysisService,
)
from youtube_intel.config import CloudSettings
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisSkipped,
    AppError,
    Availability,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import (
    PipelineInterrupted,
    PipelineOrchestrator,
    StageDisposition,
)
from youtube_intel.providers.cloud_llm import OpenAIResponsesProvider
from youtube_intel.retry import RetryPolicy
from youtube_intel.state import (
    JobRecord,
    ScoringSummaryWrite,
    SQLiteStateRepository,
    VideoRecord,
)

NOW = datetime(2026, 7, 23, 8, 0, tzinfo=UTC)
PIPELINE_VERSION = "pipeline-v1"


def _metadata(video_id: str) -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        channel_id="UC_TEST",
        channel_name="Test channel",
        title=f"Video {video_id}",
        description="Offline fixture",
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=NOW,
        duration_seconds=60,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _repository(tmp_path: Path, *video_ids: str) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    for video_id in video_ids:
        repository.upsert_video_metadata(
            _metadata(video_id), pipeline_version=PIPELINE_VERSION, now=NOW
        )
    return repository


class _FakeStages:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        interruption: tuple[ProcessingStage, str] | None = None,
        failure_video: str | None = None,
    ) -> None:
        self.repository = repository
        self.interruption = interruption
        self.failure_video = failure_video
        self.calls: Counter[tuple[str, ProcessingStage]] = Counter()
        self._cached_calls: set[tuple[str, ProcessingStage]] = set()
        self._deferred_once: set[str] = set()

    def __call__(self, job, video):  # type: ignore[no-untyped-def]
        stage = job.target_stage
        if video.video_id == self.failure_video:
            raise _StageFailure(
                AppError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="offline fake provider is unavailable",
                    retryable=True,
                    video_id=video.video_id,
                    stage=stage,
                )
            )
        cache_key = (video.video_id, stage)
        point = (
            self.interruption[1]
            if self.interruption is not None and self.interruption[0] is stage
            else None
        )
        if point == "before":
            self.interruption = None
            raise PipelineInterrupted("injected before external call")
        if cache_key not in self._cached_calls:
            self._cached_calls.add(cache_key)
            self.calls[cache_key] += 1
        if point == "after_call":
            self.interruption = None
            raise PipelineInterrupted("injected after external call")

        if video.video_id == "unavailable" and stage is ProcessingStage.METADATA:
            self.repository.mark_video_unavailable(
                video.video_id, availability=Availability.PRIVATE, now=NOW
            )
            self.repository.complete_job(job.job_id, owner=job.lease_owner or "", now=NOW)
            return StageDisposition.TERMINAL

        if video.video_id == "deferred" and stage is ProcessingStage.METADATA:
            target = (
                PipelineStatus.DEFERRED
                if video.video_id not in self._deferred_once
                else PipelineStatus.METADATA_READY
            )
            self._deferred_once.add(video.video_id)
        elif stage is ProcessingStage.METADATA:
            target = PipelineStatus.METADATA_READY
        elif stage is ProcessingStage.TRANSCRIPT:
            target = PipelineStatus.TRANSCRIPT_READY
        elif stage is ProcessingStage.SCORING:
            target = PipelineStatus.SCORED
        elif stage is ProcessingStage.ANALYSIS:
            target = PipelineStatus.ANALYSIS_READY
        elif stage is ProcessingStage.NOTE_WRITE:
            target = PipelineStatus.NOTE_WRITTEN
        else:  # pragma: no cover - all V1 video stages are listed above
            raise AssertionError(stage)

        self.repository.complete_stage(
            job_id=job.job_id,
            owner=job.lease_owner or "",
            video_id=video.video_id,
            expected_status=video.pipeline_status,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            artifacts=(),
            provider_call=None,
            scoring_summary=(
                ScoringSummaryWrite(
                    score=3.0 if video.video_id == "low" else 9.0,
                    should_summarize=video.video_id != "low",
                )
                if target is PipelineStatus.SCORED
                else None
            ),
            now=NOW,
        )
        if point == "after_db":
            self.interruption = None
            raise PipelineInterrupted("injected after database completion")
        return StageDisposition.DEFERRED if target is PipelineStatus.DEFERRED else StageDisposition.CONTINUE


class _StageFailure(Exception):
    def __init__(self, error: AppError) -> None:
        self.error = error
        super().__init__(error.message)


class _AnalysisTransport:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def __call__(
        self, request: dict[str, object], credential: str
    ) -> dict[str, object]:
        assert credential == "synthetic-key"
        self.requests.append(request)
        return {
            "output_text": {
                "one_sentence_summary": "The transcript supplies evidence.",
                "core_points": [
                    {
                        "text": "Video high is named.",
                        "kind": "fact",
                        "evidence_ids": ["title-1"],
                    }
                ],
                "keywords": ["high"],
                "evidence": [
                    {
                        "evidence_id": "title-1",
                        "source": "title",
                        "excerpt": "Video high",
                    }
                ],
            },
            "input_tokens": 24,
            "output_tokens": 18,
        }


class _Resolver:
    def resolve(self, env_name: str) -> str:
        assert env_name == "OPENAI_API_KEY"
        return "synthetic-key"


def _orchestrator(repository: SQLiteStateRepository, stages: _FakeStages) -> PipelineOrchestrator:
    next_job = 0

    def job_id() -> str:
        nonlocal next_job
        next_job += 1
        return f"job-{next_job:04d}"

    planner = PipelineJobPlanner(
        repository=repository,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        job_id_factory=job_id,
    )
    return PipelineOrchestrator(
        repository=repository,
        planner=planner,
        owner="worker-1",
        lease_seconds=5,
        retry_policy=RetryPolicy(base_delay_seconds=1, max_delay_seconds=8, jitter_ratio=0),
        handlers={stage: stages for stage in ProcessingStage if stage not in {ProcessingStage.DISCOVERY, ProcessingStage.WEEKLY_REPORT}},
        clock=lambda: NOW,
    )


def _counts(path: Path) -> tuple[int, int]:
    connection = sqlite3.connect(path)
    try:
        return tuple(
            int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in ("jobs", "artifacts")
        )
    finally:
        connection.close()


def _job_status(path: Path, video_id: str) -> tuple[str, int]:
    connection = sqlite3.connect(path)
    try:
        row = connection.execute(
            "SELECT status, attempt_count FROM jobs WHERE video_id = ?", (video_id,)
        ).fetchone()
        assert row is not None
        return str(row[0]), int(row[1])
    finally:
        connection.close()


def _prepare_high_value_analysis(
    repository: SQLiteStateRepository, video_id: str
) -> None:
    for current, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
        (PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SCORED),
    ):
        assert repository.advance_pipeline(
            video_id,
            expected_status=current,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            now=NOW,
        )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET should_summarize = 1 WHERE video_id = ?", (video_id,)
        )
    finally:
        connection.close()


def _analysis_pipeline(
    repository: SQLiteStateRepository,
    transport: _AnalysisTransport,
    artifact_root: Path,
) -> tuple[PipelineOrchestrator, Counter[str]]:
    note_writes: Counter[str] = Counter()
    next_job = 0

    def job_id() -> str:
        nonlocal next_job
        next_job += 1
        return f"analysis-job-{next_job}"

    def analyze(
        job: JobRecord, video: VideoRecord
    ) -> AnalysisCompleted | AnalysisSkipped | None:
        assert job.lease_owner is not None
        service = RepositoryBackedAnalysisService(
            provider=OpenAIResponsesProvider(
                model="gpt-4.1-mini", transport=transport
            ),
            settings=CloudSettings(enabled=True, model="gpt-4.1-mini"),
            repository=repository,
            context=AnalysisJobContext(
                job.job_id, job.lease_owner, PIPELINE_VERSION
            ),
            artifact_root=artifact_root,
            credential_resolver=_Resolver(),
            budget=CloudCallBudget(limit=5),
        )
        return service.analyze(
            video=_metadata(video.video_id),
            transcript_text="transcript evidence",
            language="en",
        )

    def write_note(job: JobRecord, video: VideoRecord) -> StageDisposition:
        note_writes[video.video_id] += 1
        repository.complete_stage(
            job_id=job.job_id,
            owner=job.lease_owner or "",
            video_id=video.video_id,
            expected_status=PipelineStatus.ANALYSIS_READY,
            target_status=PipelineStatus.NOTE_WRITTEN,
            pipeline_version=PIPELINE_VERSION,
            artifacts=(),
            provider_call=None,
            now=NOW,
        )
        return StageDisposition.CONTINUE

    return (
        PipelineOrchestrator(
            repository=repository,
            planner=PipelineJobPlanner(
                repository=repository,
                pipeline_version=PIPELINE_VERSION,
                max_attempts=3,
                job_id_factory=job_id,
            ),
            owner="worker-1",
            lease_seconds=5,
            retry_policy=RetryPolicy(
                base_delay_seconds=1, max_delay_seconds=8, jitter_ratio=0
            ),
            handlers={
                ProcessingStage.ANALYSIS: analyze,
                ProcessingStage.NOTE_WRITE: write_note,
            },
            clock=lambda: NOW,
        ),
        note_writes,
    )


def test_pipeline_completes_high_low_no_subtitle_deferred_and_unavailable_idempotently(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path, "high", "low", "no-subtitle", "deferred", "unavailable")
    stages = _FakeStages(repository)
    pipeline = _orchestrator(repository, stages)

    pipeline.run_batch(("high", "low", "no-subtitle", "deferred", "unavailable"))

    assert repository.get_video("high").pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
    assert repository.get_video("low").pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
    assert repository.get_video("no-subtitle").pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
    assert repository.get_video("deferred").pipeline_status is PipelineStatus.DEFERRED  # type: ignore[union-attr]
    unavailable = repository.get_video("unavailable")
    assert unavailable is not None and unavailable.availability is Availability.PRIVATE

    pipeline.resume_video("deferred")
    assert repository.get_video("deferred").pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]

    before = (_counts(tmp_path / "state.sqlite3"), stages.calls.copy())
    pipeline.run_batch(("high", "low", "no-subtitle", "deferred", "unavailable"))
    assert _counts(tmp_path / "state.sqlite3") == before[0]
    assert stages.calls == before[1]


def test_repository_backed_analysis_completion_schedules_one_note_write(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path, "high")
    _prepare_high_value_analysis(repository, "high")
    pipeline, note_writes = _analysis_pipeline(
        repository, _AnalysisTransport(), tmp_path / "analysis-data"
    )

    pipeline.resume_video("high", now=datetime.now(UTC))

    video = repository.get_video("high")
    assert video is not None and video.pipeline_status is PipelineStatus.COMPLETE
    assert note_writes == Counter({"high": 1})


@pytest.mark.parametrize("stage", (ProcessingStage.TRANSCRIPT, ProcessingStage.SCORING, ProcessingStage.ANALYSIS, ProcessingStage.NOTE_WRITE))
@pytest.mark.parametrize("point", ("before", "after_call", "after_db"))
def test_pipeline_recovers_interruptions_without_repeating_cached_calls(
    tmp_path: Path, stage: ProcessingStage, point: str
) -> None:
    repository = _repository(tmp_path, "high")
    stages = _FakeStages(repository, interruption=(stage, point))
    pipeline = _orchestrator(repository, stages)

    with pytest.raises(PipelineInterrupted):
        pipeline.resume_video("high")

    pipeline.resume_video("high", now=NOW + timedelta(seconds=6))

    assert repository.get_video("high").pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
    assert stages.calls[("high", stage)] == 1


def test_pipeline_isolates_retryable_failures_and_preserves_the_last_successful_state(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path, "broken", "good")
    stages = _FakeStages(repository, failure_video="broken")
    pipeline = _orchestrator(repository, stages)
    database = tmp_path / "state.sqlite3"

    pipeline.run_batch(("broken", "good"))
    assert repository.get_video("good").pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
    assert _job_status(database, "broken") == ("RETRY_PENDING", 1)
    assert repository.get_video("broken").pipeline_status is PipelineStatus.DISCOVERED  # type: ignore[union-attr]

    pipeline.resume_video("broken", now=NOW + timedelta(seconds=1))
    assert _job_status(database, "broken") == ("RETRY_PENDING", 2)
    pipeline.resume_video("broken", now=NOW + timedelta(seconds=3))

    assert _job_status(database, "broken") == ("FAILED_FINAL", 3)
    assert repository.get_video("broken").pipeline_status is PipelineStatus.DISCOVERED  # type: ignore[union-attr]
