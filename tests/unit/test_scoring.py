"""Offline unit tests for scoring sampling, cache, and threshold policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Any

import pytest

import youtube_intel.scoring as scoring_module
from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ScoreResult,
    VideoMetadata,
)
from youtube_intel.scoring import (
    InMemoryScoringCache,
    RepositoryBackedScoringService,
    ScoringJobContext,
    ScoringPersistenceError,
    ScoringService,
    build_scoring_input,
    sample_transcript,
)
from youtube_intel.state import (
    ArtifactKind,
    JobStatus,
    JobType,
    ProviderCallStatus,
    RetentionClass,
    SQLiteStateRepository,
)


def _settings(
    *,
    model: str = "qwen3:8b",
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    max_transcript_chars: int = 8,
    max_description_chars: int = 5,
) -> LocalScoringSettings:
    return LocalScoringSettings(
        model=model,
        expected_model_digest="sha256:" + ("a" * 64),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_transcript_chars=max_transcript_chars,
        max_description_chars=max_description_chars,
    )


def _video(
    *,
    title: str = "A useful title",
    channel_name: str = "Example Channel",
    description: str = "abcdef",
    published_at: datetime = datetime(2026, 7, 19, tzinfo=UTC),
    duration_seconds: int = 120,
    default_language: str | None = "en",
) -> VideoMetadata:
    return VideoMetadata(
        video_id="video-123",
        channel_id="channel-123",
        channel_name=channel_name,
        title=title,
        description=description,
        source_url="https://example.invalid/watch?v=video-123",
        published_at=published_at,
        duration_seconds=duration_seconds,
        default_language=default_language,
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


class _CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def score(self, scoring_input: object) -> ScoreResult:
        self.calls += 1
        request_hash = getattr(scoring_input, "request_hash")
        return ScoreResult(
            schema_version="score-result-v1",
            score=6.5,
            reason="Useful but below the configured summary threshold.",
            topics=("product",),
            should_summarize=True,
            provider="fake-scoring",
            model="fake-model",
            prompt_version="scoring-prompt-v1",
            request_hash=request_hash,
        )


class _PersistentCountingProvider(_CountingProvider):
    def __init__(self) -> None:
        super().__init__()
        self._raw_response: str | None = None
        self.raw_payload = (
            '{"score":6.5,"reason":"Useful","topics":["product"],'
            '"should_summarize":true}'
        )

    def score(self, scoring_input: object) -> ScoreResult:
        self.calls += 1
        result = ScoreResult(
            schema_version="score-result-v1",
            score=6.5,
            reason="Useful but below the configured summary threshold.",
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v1",
            request_hash=getattr(scoring_input, "request_hash"),
        )
        self._raw_response = self.raw_payload
        return result

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert self._raw_response is not None
        response = self._raw_response
        self._raw_response = None
        return response


def _repository_with_claimed_scoring_job(
    tmp_path: Path,
    *,
    now: datetime,
    job_id: str = "scoring-job-1",
) -> tuple[SQLiteStateRepository, ScoringJobContext]:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=now)
    repository.upsert_video_metadata(_video(), pipeline_version="pipeline-v1", now=now)
    assert repository.advance_pipeline(
        "video-123",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    assert repository.advance_pipeline(
        "video-123",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    repository.create_job(
        job_id=job_id,
        scope_key="video:video-123:SCORING",
        video_id="video-123",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    claimed = repository.claim_next_job(
        owner="test-worker",
        lease_until=now + timedelta(minutes=5),
        now=now,
    )
    assert claimed is not None
    return repository, ScoringJobContext(
        job_id=claimed.job_id,
        owner="test-worker",
        pipeline_version="pipeline-v1",
    )


def _reset_video_for_scoring_retry(
    repository: SQLiteStateRepository,
    *,
    now: datetime,
    job_id: str,
) -> ScoringJobContext:
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ?, score = NULL, "
            "should_summarize = NULL, updated_at = ? WHERE video_id = ?",
            (PipelineStatus.TRANSCRIPT_READY.value, now.isoformat(), "video-123"),
        )
    finally:
        connection.close()
    repository.create_job(
        job_id=job_id,
        scope_key="video:video-123:SCORING",
        video_id="video-123",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    claimed = repository.claim_next_job(
        owner="test-worker",
        lease_until=now + timedelta(minutes=5),
        now=now,
    )
    assert claimed is not None
    return ScoringJobContext(
        job_id=claimed.job_id,
        owner="test-worker",
        pipeline_version="pipeline-v1",
    )


def _assert_library_exception_graph_is_redacted(
    error: BaseException,
    sentinel: str,
) -> None:
    seen: set[int] = set()

    def visit(value: Any) -> None:
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        if isinstance(value, str):
            assert sentinel not in value
            return
        if isinstance(value, BaseException):
            visit(value.args)
            visit(value.__cause__)
            visit(value.__context__)
            visit(vars(value))
            visit_traceback(value.__traceback__)
            return
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
            return
        if isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)

    def visit_traceback(traceback: TracebackType | None) -> None:
        while traceback is not None:
            module_name = str(traceback.tb_frame.f_globals.get("__name__", ""))
            if module_name.startswith("youtube_intel"):
                for local in traceback.tb_frame.f_locals.values():
                    visit(local)
            traceback = traceback.tb_next

    visit(error)


def test_sample_transcript_uses_bounded_head_center_tail_segments() -> None:
    sample = sample_transcript("0123456789", max_chars=8)

    assert (sample.head, sample.body, sample.tail) == ("012", "456", "89")
    assert sample.selected_char_count == 8
    assert sample.sampling_version == "sampling-v1"


def test_scoring_input_hash_covers_truncated_description_and_sample() -> None:
    settings = _settings()

    first = build_scoring_input(
        video=_video(description="abcdef"),
        transcript_text="0123456789",
        language="en",
        settings=settings,
    )
    same_prefix = build_scoring_input(
        video=_video(description="abcdeZ"),
        transcript_text="0123456789",
        language="en",
        settings=settings,
    )
    changed_sample = build_scoring_input(
        video=_video(description="abcdef"),
        transcript_text="012345678X",
        language="en",
        settings=settings,
    )

    assert first.request_hash == same_prefix.request_hash
    assert first.request_hash != changed_sample.request_hash
    assert first.sample.source_content_hash == first.transcript_content_hash


def test_scoring_input_hash_separates_every_frozen_cache_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    baseline = build_scoring_input(
        video=_video(),
        transcript_text="0123456789",
        language="en",
        settings=settings,
    ).request_hash

    variants = (
        build_scoring_input(
            video=_video(title="A different title"),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(channel_name="Another Channel"),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(published_at=datetime(2026, 7, 20, tzinfo=UTC)),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(duration_seconds=121),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(default_language="zh"),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123X56789",
            language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="zh",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            settings=_settings(model="another-model"),
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            settings=_settings(temperature=0.1),
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            settings=_settings(max_output_tokens=1201),
        ),
    )

    assert all(item.request_hash != baseline for item in variants)

    monkeypatch.setattr(scoring_module, "PROMPT_VERSION", "scoring-prompt-v2")
    assert (
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ).request_hash
        != baseline
    )
    monkeypatch.setattr(scoring_module, "SCHEMA_VERSION", "score-result-v2")
    assert (
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ).request_hash
        != baseline
    )
    monkeypatch.setattr(scoring_module, "_SCORING_OPERATION", "local-scoring-v2")
    assert (
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            settings=settings,
        ).request_hash
        != baseline
    )


def test_scoring_service_caches_canonical_input_and_records_policy_disagreement() -> None:
    provider = _CountingProvider()
    service = ScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7.0,
        cache=InMemoryScoringCache(),
    )

    first = service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
    )
    second = service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
    )

    assert provider.calls == 1
    assert first.result == second.result
    assert first.decision.final_should_summarize is False
    assert first.decision.model_disagrees is True
    assert [item.code for item in first.call.diagnostics] == [
        "MODEL_POLICY_DISAGREEMENT"
    ]
    assert [item.code for item in second.call.diagnostics] == [
        "CACHE_HIT",
        "MODEL_POLICY_DISAGREEMENT",
    ]


def test_sample_transcript_rejects_text_too_short_for_frozen_contract() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        sample_transcript("hi", max_chars=8)


def test_repository_backed_scoring_commits_artifacts_call_summary_and_reuses_verified_result(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 19, tzinfo=UTC)
    repository, context = _repository_with_claimed_scoring_job(tmp_path, now=now)
    provider = _PersistentCountingProvider()
    service = RepositoryBackedScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7.0,
        repository=repository,
        context=context,
        artifact_root=tmp_path / "artifacts",
        clock=lambda: now,
    )

    first = service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
    )

    request_hash = build_scoring_input(
        video=_video(),
        transcript_text="0123456789",
        language="en",
        settings=_settings(),
    ).request_hash
    raw_artifact = repository.get_artifact_by_key(f"scoring/{request_hash}/raw")
    structured_artifact = repository.get_artifact_by_key(
        f"scoring/{request_hash}/structured"
    )
    provider_call = repository.get_provider_call(request_hash)
    video = repository.get_video("video-123")
    job = repository.get_job(context.job_id)

    assert provider.calls == 1
    assert first.decision.final_should_summarize is False
    assert raw_artifact is not None
    assert raw_artifact.kind is ArtifactKind.SCORING_RAW
    assert raw_artifact.retention_class is RetentionClass.RAW_RESPONSE_30D
    assert structured_artifact is not None
    assert structured_artifact.kind is ArtifactKind.SCORING_STRUCTURED
    assert structured_artifact.retention_class is RetentionClass.LONG_LIVED
    assert provider_call is not None
    assert provider_call.status is ProviderCallStatus.SUCCEEDED
    assert provider_call.response_artifact_id == raw_artifact.artifact_id
    assert video is not None
    assert video.pipeline_status is PipelineStatus.SCORED
    assert video.score == 6.5
    assert video.should_summarize is False
    assert job is not None
    assert job.status is JobStatus.SUCCEEDED

    retry_context = _reset_video_for_scoring_retry(
        repository,
        now=now + timedelta(minutes=1),
        job_id="scoring-job-2",
    )
    retry_service = RepositoryBackedScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7.0,
        repository=repository,
        context=retry_context,
        artifact_root=tmp_path / "artifacts",
        clock=lambda: now + timedelta(minutes=1),
    )

    second = retry_service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
    )

    assert provider.calls == 1
    assert second.result == first.result
    assert [item.code for item in second.call.diagnostics] == [
        "PERSISTED_CACHE_HIT",
        "MODEL_POLICY_DISAGREEMENT",
    ]


@pytest.mark.parametrize(
    "failure_point",
    [
        "stage.after_artifacts",
        "stage.after_provider_call",
        "stage.after_scoring_summary",
        "stage.after_pipeline",
    ],
)
def test_repository_backed_scoring_rolls_back_success_writes_after_injected_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    now = datetime(2026, 7, 19, tzinfo=UTC)
    repository, context = _repository_with_claimed_scoring_job(tmp_path, now=now)

    def fail_at_requested_boundary(point: str) -> None:
        if point == failure_point:
            raise RuntimeError("injected scoring persistence failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_at_requested_boundary)
    service = RepositoryBackedScoringService(
        provider=_PersistentCountingProvider(),
        settings=_settings(),
        summary_threshold=7.0,
        repository=repository,
        context=context,
        artifact_root=tmp_path / "artifacts",
        clock=lambda: now,
    )

    with pytest.raises(ScoringPersistenceError):
        service.score(
            video=_video(),
            transcript_text="0123456789",
            language="en",
        )

    request_hash = build_scoring_input(
        video=_video(),
        transcript_text="0123456789",
        language="en",
        settings=_settings(),
    ).request_hash
    video = repository.get_video("video-123")
    job = repository.get_job(context.job_id)
    provider_call = repository.get_provider_call(request_hash)

    assert repository.get_artifact_by_key(f"scoring/{request_hash}/raw") is None
    assert repository.get_artifact_by_key(f"scoring/{request_hash}/structured") is None
    assert not list((tmp_path / "artifacts").rglob("*.json"))
    assert video is not None
    assert video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    assert video.score is None
    assert video.should_summarize is None
    assert job is not None
    assert job.status is JobStatus.RUNNING
    assert provider_call is not None
    assert provider_call.status is ProviderCallStatus.FAILED_RETRYABLE


def test_repository_backed_scoring_redacts_raw_provider_response_after_artifact_failure(
    tmp_path: Path,
) -> None:
    sentinel = "/private/raw-scoring-response"
    now = datetime(2026, 7, 19, tzinfo=UTC)
    repository, context = _repository_with_claimed_scoring_job(tmp_path, now=now)
    provider = _PersistentCountingProvider()
    provider.raw_payload = sentinel
    service = RepositoryBackedScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7.0,
        repository=repository,
        context=context,
        artifact_root=tmp_path / "artifacts",
        clock=lambda: now,
    )
    request_hash = build_scoring_input(
        video=_video(),
        transcript_text="0123456789",
        language="en",
        settings=_settings(),
    ).request_hash
    conflicting_path = tmp_path / "artifacts" / "scoring" / request_hash / "raw.json"
    conflicting_path.parent.mkdir(parents=True)
    conflicting_path.write_text("different", encoding="utf-8")

    with pytest.raises(ScoringPersistenceError) as exc_info:
        service.score(
            video=_video(),
            transcript_text="0123456789",
            language="en",
        )

    _assert_library_exception_graph_is_redacted(exc_info.value, sentinel)
