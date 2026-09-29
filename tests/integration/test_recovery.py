"""Recovery-focused integration tests for TASK-010 retry helpers."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from youtube_intel import analysis as analysis_mod
from youtube_intel.analysis import (
    AnalysisJobContext,
    CloudCallBudget,
    RepositoryBackedAnalysisService,
    build_analysis_input,
    build_summary_evidence_registry,
)
from youtube_intel.config import CloudSettings
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisSkipped,
    AppError,
    Availability,
    ErrorCode,
    EvidenceSource,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import (
    PipelineOrchestrator,
    StageDisposition,
)
from youtube_intel.providers.cloud_llm import OpenAIResponsesProvider
from youtube_intel.retry import RetryPolicy
from youtube_intel.state import (
    ArtifactKind,
    JobRecord,
    JobType,
    SQLiteStateRepository,
    VideoRecord,
)

PIPELINE_VERSION = "pipeline-v1"


@pytest.fixture(autouse=True)
def _recovery_token_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recovery tests isolate persistence from external BPE provisioning."""

    monkeypatch.setattr(analysis_mod, "_input_tokens", lambda _parts, _root: 2)


def _metadata() -> VideoMetadata:
    return VideoMetadata(
        video_id="high",
        channel_id="UC_TEST",
        channel_name="Test channel",
        title="Video high",
        description="Offline fixture",
        source_url="https://example.invalid/watch?v=high",
        published_at=datetime(2026, 7, 23, tzinfo=UTC),
        duration_seconds=60,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


ANALYSIS_CUE_TEXTS = (
    "The transcript supplies one real sentence about the topic.",
    "A second cue names the pricing model in detail.",
)


def _seed_timed_transcript(repository: SQLiteStateRepository) -> None:
    """Give ANALYSIS real cue-level transcript authority."""

    from youtube_intel.state import (
        ArtifactWrite,
        RetentionClass,
        StorageRoot,
        TimedTranscriptCueWrite,
        TimedTranscriptWrite,
    )

    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="artifact-high",
            artifact_key="transcript/high",
            video_id="high",
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path="transcripts/high/canonical.txt",
            content_hash=hashlib.sha256(
                "".join(ANALYSIS_CUE_TEXTS).encode()
            ).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=datetime.now(UTC),
    )
    repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id="high",
            canonical_artifact_id="artifact-high",
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=index * 1000,
                    end_ms=(index + 1) * 1000,
                    text=text,
                )
                for index, text in enumerate(ANALYSIS_CUE_TEXTS)
            ),
        ),
        now=datetime.now(UTC),
    )


def _analysis_registry(repository: SQLiteStateRepository):
    verified = repository.get_verified_timed_transcript(video_id="high")
    assert verified is not None
    return build_summary_evidence_registry(
        verified=verified,
        video_id="high",
        title="Video high",
        channel_name="Test channel",
        description="Offline fixture",
        transcript_text="transcript evidence",
    )


class _AnalysisTransport:
    def __init__(self, repository: SQLiteStateRepository | None = None) -> None:
        self.requests: list[dict[str, object]] = []
        self._ref = (
            next(
                candidate.ref
                for candidate in _analysis_registry(repository).candidates
                if candidate.source is EvidenceSource.TRANSCRIPT_SAMPLE
            )
            if repository is not None
            else "t0-2-unknown"
        )

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
                        "evidence_refs": [self._ref],
                    }
                ],
                "keywords": ["high"],
            },
            "input_tokens": 24,
            "output_tokens": 18,
        }


class _Resolver:
    def resolve(self, env_name: str) -> str:
        assert env_name == "OPENAI_API_KEY"
        return "synthetic-key"


def _repository_at_scored_state(tmp_path: Path, now: datetime) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=now)
    metadata = _metadata()
    repository.upsert_video_metadata(
        metadata, pipeline_version=PIPELINE_VERSION, now=now
    )
    for current, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
        (PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SCORED),
    ):
        assert repository.advance_pipeline(
            metadata.video_id,
            expected_status=current,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            now=now,
        )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET should_summarize = 1 WHERE video_id = ?",
            (metadata.video_id,),
        )
    finally:
        connection.close()
    return repository


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
        return f"recovery-job-{next_job}"

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
            video=_metadata(), transcript_text="transcript evidence", language="en"
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
            now=datetime.now(UTC),
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
            lease_seconds=30,
            retry_policy=RetryPolicy(
                base_delay_seconds=1, max_delay_seconds=8, jitter_ratio=0
            ),
            handlers={
                ProcessingStage.ANALYSIS: analyze,
                ProcessingStage.NOTE_WRITE: write_note,
            },
            clock=lambda: datetime.now(UTC),
        ),
        note_writes,
    )


def test_retry_policy_respects_provider_retry_after_and_exponential_cap() -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)
    policy = RetryPolicy(base_delay_seconds=2, max_delay_seconds=5, jitter_ratio=0)

    assert policy.retry_at(
        AppError(code=ErrorCode.TRANSIENT_NETWORK, message="temporary", retryable=True),
        attempt_count=3,
        now=now,
    ) == datetime(2026, 7, 23, 0, 0, 5, tzinfo=UTC)
    assert policy.retry_at(
        AppError(code=ErrorCode.RATE_LIMITED, message="slow down", retryable=True, retry_after_seconds=9),
        attempt_count=1,
        now=now,
    ) == datetime(2026, 7, 23, 0, 0, 9, tzinfo=UTC)
    assert policy.retry_at(
        AppError(code=ErrorCode.CONTENT_UNAVAILABLE, message="gone", retryable=False),
        attempt_count=1,
        now=now,
    ) is None


def test_cached_analysis_recovery_preserves_verified_artifacts_and_schedules_note(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    repository = _repository_at_scored_state(tmp_path, now)
    _seed_timed_transcript(repository)
    transport = _AnalysisTransport(repository)
    artifact_root = tmp_path / "analysis-data"
    repository.create_job(
        job_id="initial-analysis",
        scope_key="video:high:ANALYSIS",
        video_id="high",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.ANALYSIS,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=now,
        now=now,
    )
    initial_job = repository.claim_next_job(
        owner="initial-worker", lease_until=now + timedelta(minutes=5), now=now
    )
    assert initial_job is not None
    initial_service = RepositoryBackedAnalysisService(
        provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport),
        settings=CloudSettings(enabled=True, model="gpt-4.1-mini"),
        repository=repository,
        context=AnalysisJobContext(
            initial_job.job_id, "initial-worker", PIPELINE_VERSION
        ),
        artifact_root=artifact_root,
        credential_resolver=_Resolver(),
        budget=CloudCallBudget(limit=5),
    )
    initial_service.analyze(
        video=_metadata(), transcript_text="transcript evidence", language="en"
    )
    request_hash = build_analysis_input(
        video=_metadata(),
        transcript_text="transcript evidence",
        language="en",
        output_language="zh-CN",
        settings=initial_service.settings,
        prompt_version="analysis-prompt-v5",
        registry=_analysis_registry(repository),
    ).request_hash
    raw = repository.get_artifact_by_key(f"analysis/{request_hash}/raw")
    structured = repository.get_artifact_by_key(
        f"analysis/{request_hash}/structured"
    )
    provider_call = repository.get_provider_call(request_hash)
    assert raw is not None and structured is not None and provider_call is not None
    assert provider_call.response_artifact_id == raw.artifact_id
    assert hashlib.sha256(
        (artifact_root / raw.relative_path).read_bytes()
    ).hexdigest() == raw.content_hash
    assert hashlib.sha256(
        (artifact_root / structured.relative_path).read_bytes()
    ).hexdigest() == structured.content_hash

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, "high"),
        )
    finally:
        connection.close()
    pipeline, note_writes = _analysis_pipeline(repository, transport, artifact_root)

    pipeline.resume_video("high", now=datetime.now(UTC))

    cached_raw = repository.get_artifact_by_key(f"analysis/{request_hash}/raw")
    cached_structured = repository.get_artifact_by_key(
        f"analysis/{request_hash}/structured"
    )
    cached_call = repository.get_provider_call(request_hash)
    video = repository.get_video("high")
    assert len(transport.requests) == 1
    assert cached_raw == raw
    assert cached_structured == structured
    assert cached_call == provider_call
    assert note_writes == Counter({"high": 1})
    assert video is not None and video.pipeline_status is PipelineStatus.COMPLETE
