"""Offline unit tests for scoring inputs, behavior, and trusted persistence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import youtube_intel.scoring as scoring_module
from youtube_intel.config import LocalScoringSettings, load_app_config
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ScoreResult,
    ScoringInput,
    VideoMetadata,
)
from youtube_intel.providers.ollama import (
    OllamaQualityJudgeProvider,
    parse_scoring_candidate,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import (
    AuthoritativeScoringReader,
    InMemoryScoringCache,
    PhaseFTrustedScoringSuccess,
    PrimaryScoringAttempt,
    RepositoryBackedScoringService,
    ScoringJobContext,
    ScoringPersistenceError,
    ScoringService,
    build_primary_scoring_attempt,
    build_scoring_input,
    sample_transcript,
)
from youtube_intel.scoring_admission import (
    ScoringAdmissionRegistry,
    ScoringDispatchAdmission,
    ScoringDispatchIdentity,
    ScoringDispatchRole,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    JobStatus,
    JobType,
    ProviderCallStatus,
    RetentionClass,
    StorageRoot,
)

_NOW = datetime(2026, 8, 23, 12, tzinfo=UTC)
_MODEL = "qwen3:8b"
_DIGEST = "sha256:" + ("a" * 64)
_TRANSCRIPT = "This transcript contains enough text for a stable sample."


class _AdmissionRepository:
    def get_job(self, job_id: str) -> object | None:
        if job_id != "scoring-test-admission-job":
            return None
        return type(
            "_AdmissionJob",
            (),
            {
                "target_stage": ProcessingStage.SCORING,
                "status": JobStatus.RUNNING,
                "lease_owner": "scoring-test",
                "lease_until": datetime.now(UTC) + timedelta(minutes=5),
            },
        )()

    def get_provider_call(self, request_hash: str) -> None:
        del request_hash
        return None


def _h1_admission() -> ScoringDispatchAdmission:
    return ScoringDispatchAdmission(
        repository=_AdmissionRepository(),  # type: ignore[arg-type]
        job_id="scoring-test-admission-job",
        owner="scoring-test",
    )


def _settings(
    *,
    model: str = _MODEL,
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    max_transcript_chars: int = 64,
    max_description_chars: int = 32,
) -> LocalScoringSettings:
    return LocalScoringSettings(
        model=model,
        expected_model_digest=_DIGEST,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_transcript_chars=max_transcript_chars,
        max_description_chars=max_description_chars,
    )


def _video(
    *,
    video_id: str = "video-123",
    title: str = "A useful title",
    channel_name: str = "Example Channel",
    description: str = "abcdef",
    published_at: datetime = datetime(2026, 7, 19, tzinfo=UTC),
    duration_seconds: int = 120,
    default_language: str | None = "en",
) -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        channel_id=f"channel-{video_id}",
        channel_name=channel_name,
        title=title,
        description=description,
        source_url=f"https://example.invalid/watch?v={video_id}",
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
        return ScoreResult(
            schema_version="score-result-v2",
            score=6.5,
            reason="This result has a score below the configured summary threshold.",
            topics=("product",),
            should_summarize=True,
            provider="fake-scoring",
            model="fake-model",
            prompt_version="scoring-prompt-v2",
            request_hash=getattr(scoring_input, "request_hash"),
            output_language=getattr(scoring_input, "output_language"),
        )


class _LegacyProvider(_CountingProvider):
    """Compatibility fake used only to prove the retired path cannot succeed."""

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert request_hash
        return _raw_response(_candidate_fields())


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self, size: int = -1) -> bytes:
        del size
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        pass


class _FakeTransport:
    def __init__(self) -> None:
        self._responses: list[object] = [
            {"models": [{"name": _MODEL, "digest": "a" * 64}]},
            {"response": json.dumps(_judge_pass(), separators=(",", ":"))},
        ]

    def __call__(self, request: object, timeout: float) -> _Response:
        del request, timeout
        return _Response(self._responses.pop(0))


def _candidate_fields(*, score: float = 8.0) -> dict[str, object]:
    return {
        "score": score,
        "reason": "This result contains a concrete useful explanation of the score.",
        "topics": ["product", "strategy"],
        "should_summarize": True,
        "dimensions": {"product": 9.0, "practicality": 8.0},
    }


def _raw_response(candidate: dict[str, object] | str) -> str:
    response = (
        candidate
        if isinstance(candidate, str)
        else json.dumps(
            candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    )
    return json.dumps(
        {"model": _MODEL, "response": response, "done": True},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _judge_pass() -> dict[str, object]:
    return {
        "status": "PASS",
        "decision_confidence": "HIGH",
        "grounding_confidence": "MEDIUM",
        "usefulness_confidence": "MEDIUM",
        "signals": ["MINIMAL_CLAIM_PRESENT", "GROUNDING_PRESENT"],
        "reason": None,
        "evidence_ids": ["title-1"],
    }


def _runtime(project: Path) -> RuntimeOperations:
    (project / "config").mkdir(parents=True)
    (project / "vault").mkdir()
    (project / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: UCtest000000000000000000000000000\n",
        encoding="utf-8",
    )
    (project / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
  output_language: en
local_scoring:
  model: {_MODEL}
  expected_model_digest: {_DIGEST}
  temperature: 0.0
  max_output_tokens: 1200
  max_transcript_chars: 64
  max_description_chars: 32
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {project / "vault"}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )
    config = load_app_config(
        project / "config" / "channels.yaml", project / "config" / "settings.yaml"
    )
    transport = _FakeTransport()
    return RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
            quality_judge_provider_factory=lambda: OllamaQualityJudgeProvider(
                settings=config.settings.local_scoring, transport=transport
            ),
        ),
    )


def _scoring_input(video_id: str) -> ScoringInput:
    return build_scoring_input(
        video=_video(video_id=video_id),
        transcript_text=_TRANSCRIPT,
        language="en",
        output_language="en",
        settings=_settings(),
    )


def _primary_attempt(scoring_input: ScoringInput, raw: str) -> PrimaryScoringAttempt:
    return build_primary_scoring_attempt(
        scoring_input=scoring_input,
        candidate=parse_scoring_candidate(raw),
        final_raw_response=raw,
        provider="ollama",
        model=_MODEL,
        model_digest=_DIGEST,
        temperature=0.0,
        max_output_tokens=1200,
        max_description_chars=32,
    )


def _prepare_scoring_job(
    runtime: RuntimeOperations, *, video_id: str, job_id: str
) -> None:
    """Create only the normal pre-scoring transcript prerequisite."""

    repository = runtime._repository
    repository.upsert_video_metadata(
        _video(video_id=video_id), pipeline_version="runtime-v1", now=_NOW
    )
    assert repository.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="runtime-v1",
        now=_NOW,
    )
    transcript_job_id = f"transcript-{video_id}"
    repository.create_job(
        job_id=transcript_job_id,
        scope_key=f"video:{video_id}:TRANSCRIPT",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version="runtime-v1",
        max_attempts=1,
        available_at=_NOW,
        now=_NOW,
    )
    assert (
        repository.claim_next_job(
            owner="transcript-worker",
            lease_until=_NOW + timedelta(minutes=10),
            now=_NOW,
            video_id=video_id,
        )
        is not None
    )
    transcript_bytes = _TRANSCRIPT.encode("utf-8")
    artifact = ArtifactWrite(
        artifact_id=f"transcript-{video_id}",
        artifact_key=f"video:{video_id}:transcript:canonical",
        video_id=video_id,
        job_id=transcript_job_id,
        kind=ArtifactKind.TRANSCRIPT_CANONICAL,
        storage_root=StorageRoot.DATA,
        relative_path=f"transcripts/{video_id}.txt",
        content_hash=hashlib.sha256(transcript_bytes).hexdigest(),
        provider="subtitle",
        model=None,
        producer_version="transcript-v1",
        retention_class=RetentionClass.LONG_LIVED,
        expires_at=None,
    )
    transcript_path = runtime._data_root / artifact.relative_path
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_bytes(transcript_bytes)
    repository.complete_stage(
        job_id=transcript_job_id,
        owner="transcript-worker",
        video_id=video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="runtime-v1",
        artifacts=(artifact,),
        provider_call=None,
        now=_NOW,
    )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{video_id}:SCORING",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version="runtime-v1",
        max_attempts=1,
        available_at=_NOW,
        now=_NOW,
    )
    assert (
        repository.claim_next_job(
            owner="test-owner",
            lease_until=_NOW + timedelta(minutes=10),
            now=_NOW,
            video_id=video_id,
        )
        is not None
    )


def _trusted_success(
    runtime: RuntimeOperations, *, video_id: str
) -> PhaseFTrustedScoringSuccess:
    scoring_input = _scoring_input(video_id)
    return runtime._run_primary_trusted_scoring(
        attempt=_primary_attempt(scoring_input, _raw_response(_candidate_fields())),
        scoring_input=scoring_input,
        admission=_h1_admission(),
    )


def test_runtime_refreshes_output_language_only_for_new_processing_batch(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    assert runtime._effective_output_language == "en"
    assert runtime._trusted_scoring_context.output_language == "en"

    runtime._repository.save_global_output_language(
        output_language="zh-CN", now=_NOW
    )

    # Persisting a preference does not mutate an already-sealed batch context.
    assert runtime._effective_output_language == "en"
    assert runtime._trusted_scoring_context.output_language == "en"

    runtime._refresh_output_language_for_new_batch()

    assert runtime._effective_output_language == "zh-CN"
    assert runtime._trusted_scoring_context.output_language == "zh-CN"


def test_downstream_generation_keeps_completed_scoring_language(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    runtime._effective_output_language = "zh-CN"
    runtime._load_scoring = lambda _video_id: type(  # type: ignore[method-assign]
        "_Outcome",
        (),
        {"result": type("_Result", (), {"output_language": "en"})()},
    )()

    assert runtime._downstream_output_language("video-1") == "en"


def test_historical_scoring_language_is_not_compared_to_current_preference(
    tmp_path: Path,
) -> None:
    reader = AuthoritativeScoringReader(
        repository=object(),
        data_root=tmp_path,
        summary_threshold=5.0,
        pipeline_version="runtime-v1",
        current_model="fake-model",
    )
    historical = ScoreResult(
        schema_version="score-result-v2",
        score=7.0,
        reason="Historical result keeps the language it was generated with.",
        topics=("history",),
        should_summarize=True,
        provider="ollama",
        model="fake-model",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )

    reader._check_current_model(historical)


def test_sample_transcript_uses_bounded_head_center_tail_segments() -> None:
    sample = sample_transcript("0123456789", max_chars=8)
    assert (sample.head, sample.body, sample.tail) == ("012", "456", "89")
    assert sample.selected_char_count == 8
    assert sample.sampling_version == "sampling-v1"


def test_scoring_input_hash_covers_truncated_description_and_sample() -> None:
    settings = _settings(max_transcript_chars=8, max_description_chars=5)
    first = build_scoring_input(
        video=_video(description="abcdef"),
        transcript_text="0123456789",
        language="en",
        output_language="en",
        settings=settings,
    )
    same_prefix = build_scoring_input(
        video=_video(description="abcdeZ"),
        transcript_text="0123456789",
        language="en",
        output_language="en",
        settings=settings,
    )
    changed_sample = build_scoring_input(
        video=_video(description="abcdef"),
        transcript_text="012345678X",
        language="en",
        output_language="en",
        settings=settings,
    )
    assert first.request_hash == same_prefix.request_hash
    assert first.request_hash != changed_sample.request_hash
    assert first.sample.source_content_hash == first.transcript_content_hash


def test_scoring_input_hash_separates_every_frozen_cache_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(max_transcript_chars=8, max_description_chars=5)
    baseline = build_scoring_input(
        video=_video(),
        transcript_text="0123456789",
        language="en",
        output_language="en",
        settings=settings,
    ).request_hash
    variants = (
        build_scoring_input(
            video=_video(title="A different title"),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(channel_name="Another Channel"),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(published_at=datetime(2026, 7, 20, tzinfo=UTC)),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(duration_seconds=121),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(default_language="zh"),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123X56789",
            language="en",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="zh",
            output_language="en",
            settings=settings,
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=_settings(
                model="another-model", max_transcript_chars=8, max_description_chars=5
            ),
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=_settings(
                temperature=0.1, max_transcript_chars=8, max_description_chars=5
            ),
        ),
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=_settings(
                max_output_tokens=1201, max_transcript_chars=8, max_description_chars=5
            ),
        ),
    )
    assert all(item.request_hash != baseline for item in variants)
    monkeypatch.setattr(scoring_module, "PROMPT_VERSION", "scoring-prompt-v3")
    assert (
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            output_language="en",
            settings=settings,
        ).request_hash
        != baseline
    )
    monkeypatch.setattr(scoring_module, "SCHEMA_VERSION", "score-result-v3")
    assert (
        build_scoring_input(
            video=_video(),
            transcript_text="0123456789",
            language="en",
            output_language="en",
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
            output_language="en",
            settings=settings,
        ).request_hash
        != baseline
    )


def test_scoring_service_caches_canonical_input_and_records_policy_disagreement() -> (
    None
):
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
        output_language="en",
    )
    second = service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
        output_language="en",
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


def test_legacy_repository_backed_score_cannot_produce_trusted_scoring_success(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    video_id, job_id = "legacy-isolated", "legacy-job"
    _prepare_scoring_job(runtime, video_id=video_id, job_id=job_id)
    service = RepositoryBackedScoringService(
        provider=_LegacyProvider(),
        settings=_settings(),
        summary_threshold=7.0,
        repository=runtime._repository,
        context=ScoringJobContext(job_id, "test-owner", "runtime-v1"),
        artifact_root=runtime._data_root,
        clock=lambda: _NOW,
    )
    with pytest.raises(ScoringPersistenceError):
        service.score(
            video=_video(video_id=video_id),
            transcript_text=_TRANSCRIPT,
            language="en",
            output_language="en",
        )
    video, job = (
        runtime._repository.get_video(video_id),
        runtime._repository.get_job(job_id),
    )
    request_hash = _scoring_input(video_id).request_hash
    assert (
        runtime._repository.get_artifact_by_key(f"scoring/{request_hash}/raw") is None
    )
    assert (
        runtime._repository.get_artifact_by_key(f"scoring/{request_hash}/structured")
        is None
    )
    assert (
        video is not None and video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    )
    assert job is not None and job.status is JobStatus.RUNNING


def test_trusted_runtime_scoring_persists_artifacts_provider_call_video_and_job(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    video_id, job_id = "trusted-success", "trusted-job"
    _prepare_scoring_job(runtime, video_id=video_id, job_id=job_id)
    success = _trusted_success(runtime, video_id=video_id)
    entry = runtime._trusted_persistence_entry(
        job_id=job_id, owner="test-owner", pipeline_version="runtime-v1"
    )
    entry._clock = lambda: _NOW  # type: ignore[method-assign]
    completion = entry.persist_success(success)
    raw, structured = completion.artifacts
    assert type(success) is PhaseFTrustedScoringSuccess
    assert raw.kind is ArtifactKind.SCORING_RAW
    assert structured.kind is ArtifactKind.SCORING_STRUCTURED
    assert (
        hashlib.sha256(
            (runtime._data_root / raw.relative_path).read_bytes()
        ).hexdigest()
        == raw.content_hash
    )
    assert (
        hashlib.sha256(
            (runtime._data_root / structured.relative_path).read_bytes()
        ).hexdigest()
        == structured.content_hash
    )
    assert completion.provider_call.status is ProviderCallStatus.SUCCEEDED
    assert completion.provider_call.request_hash == success.scoring_request_hash
    assert completion.provider_call.response_artifact_id == raw.artifact_id
    assert completion.video.pipeline_status is PipelineStatus.SCORED
    assert completion.video.score == success.trusted_result.result.score
    assert completion.job.status is JobStatus.SUCCEEDED


def test_successful_phase_g_commit_releases_runtime_admission_state(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    video_id, job_id = "registry-release", "registry-release-job"
    _prepare_scoring_job(runtime, video_id=video_id, job_id=job_id)
    success = _trusted_success(runtime, video_id=video_id)
    runtime._runtime_owner = "test-owner"
    job = runtime._repository.get_job(job_id)
    assert job is not None
    runtime._scoring_admission_for(job_id).admit(
        ScoringDispatchIdentity(
            role=ScoringDispatchRole.PRIMARY,
            operation="local-scoring-v1",
            normalized_input_hash="a" * 64,
            request_hash="b" * 64,
        ),
        now=_NOW,
    )
    database_scope = str((tmp_path / "project" / "data" / "state.sqlite").resolve())
    assert any(
        key.repository_scope == database_scope and key.job_id == job_id
        for key in ScoringAdmissionRegistry._states
    )
    entry = runtime._trusted_persistence_entry(
        job_id=job_id, owner="test-owner", pipeline_version="runtime-v1"
    )
    entry._clock = lambda: _NOW  # type: ignore[method-assign]
    runtime._trusted_persistence_entry = lambda **_kwargs: entry  # type: ignore[method-assign]

    completion = runtime._persist_trusted_scoring_success(
        success=success,
        job=job,
        owner="test-owner",
        pipeline_version="runtime-v1",
    )

    assert completion.job.status is JobStatus.SUCCEEDED
    assert not any(
        key.repository_scope == database_scope and key.job_id == job_id
        for key in ScoringAdmissionRegistry._states
    )


def test_invalid_scoring_response_rejects_before_trusted_persistence(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    video_id, job_id = "invalid-response", "invalid-job"
    _prepare_scoring_job(runtime, video_id=video_id, job_id=job_id)
    scoring_input = _scoring_input(video_id)
    with pytest.raises(ValueError):
        _primary_attempt(scoring_input, _raw_response("not valid scoring json"))
    video, job = (
        runtime._repository.get_video(video_id),
        runtime._repository.get_job(job_id),
    )
    assert (
        runtime._repository.get_artifact_by_key(
            f"scoring/{scoring_input.request_hash}/raw"
        )
        is None
    )
    assert (
        runtime._repository.get_artifact_by_key(
            f"scoring/{scoring_input.request_hash}/structured"
        )
        is None
    )
    assert runtime._repository.get_provider_call(scoring_input.request_hash) is None
    assert video is not None and video.pipeline_status is not PipelineStatus.SCORED
    assert job is not None and job.status is JobStatus.RUNNING


def test_trusted_persistence_duplicate_execution_creates_no_duplicate_output(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "project")
    video_id, job_id = "duplicate-success", "duplicate-job"
    _prepare_scoring_job(runtime, video_id=video_id, job_id=job_id)
    success = _trusted_success(runtime, video_id=video_id)
    entry = runtime._trusted_persistence_entry(
        job_id=job_id, owner="test-owner", pipeline_version="runtime-v1"
    )
    entry._clock = lambda: _NOW
    first, second = entry.persist_success(success), entry.persist_success(success)
    assert second == first
    connection = runtime._repository._connect()
    try:
        artifact_count = connection.execute(
            "SELECT COUNT(*) FROM artifacts WHERE video_id = ? AND kind IN (?, ?)",
            (
                video_id,
                ArtifactKind.SCORING_RAW.value,
                ArtifactKind.SCORING_STRUCTURED.value,
            ),
        ).fetchone()[0]
        call_count = connection.execute(
            "SELECT COUNT(*) FROM provider_calls"
        ).fetchone()[0]
    finally:
        connection.close()
    assert artifact_count == 2
    assert call_count == 2
