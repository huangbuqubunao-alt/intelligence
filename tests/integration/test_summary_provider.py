"""Offline integration tests for the isolated OpenAI Responses adapter."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import youtube_intel.providers.cloud_llm as cloud_llm
from youtube_intel import analysis as analysis_mod
from youtube_intel.analysis import (
    AnalysisJobContext,
    AnalysisPolicyError,
    CloudCallBudget,
    RepositoryBackedAnalysisService,
    build_analysis_input,
)
from youtube_intel.config import CloudSettings
from youtube_intel.domain import (
    AnalysisSkipReason,
    Availability,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.providers.cloud_llm import (
    CloudProviderError,
    OpenAIResponsesProvider,
)
from youtube_intel.state import (
    JobType,
    ProviderCallStatus,
    ProviderDispatchStatus,
    SQLiteStateRepository,
)


@pytest.fixture(autouse=True)
def _persistence_token_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persistence tests exercise provider state, not external BPE provisioning."""

    monkeypatch.setattr(analysis_mod, "_input_tokens", lambda _parts, _root: 2)


def _input() -> object:
    video = VideoMetadata(
        video_id="video-123", channel_id="channel-123", channel_name="Example Channel",
        title="Useful title", description="public description",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 7, 20, tzinfo=UTC), duration_seconds=120,
        default_language="en", live_status=LiveStatus.NONE, availability=Availability.PUBLIC,
    )
    return build_analysis_input(
        video=video, transcript_text="transcript evidence", language="en",
        output_language="zh-CN", settings=CloudSettings(enabled=True, model="gpt-4.1-mini"),
    )


def _video() -> VideoMetadata:
    return VideoMetadata(video_id="video-123", channel_id="channel-123", channel_name="Example Channel",
        title="Useful title", description="public description", source_url="https://example.invalid/v",
        published_at=datetime(2026, 7, 20, tzinfo=UTC), duration_seconds=120, default_language="en",
        live_status=LiveStatus.NONE, availability=Availability.PUBLIC)


class _Transport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def __call__(self, request: dict[str, object], credential: str) -> dict[str, object]:
        assert credential == "synthetic-key"
        self.requests.append(request)
        return self.response


def _valid_response() -> dict[str, object]:
    return {
        "output_text": {
            "one_sentence_summary": "The transcript supplies evidence.",
            "core_points": [{"text": "Useful title is named.", "kind": "fact", "evidence_ids": ["title-1"]}],
            "keywords": ["useful"],
            "evidence": [{"evidence_id": "title-1", "source": "title", "excerpt": "Useful title"}],
        },
        "input_tokens": 24,
        "output_tokens": 18,
    }


def test_fake_transport_uses_one_strict_non_stored_responses_request() -> None:
    transport = _Transport(_valid_response())
    provider = OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport)

    result = provider.summarize_with_credential(_input(), "synthetic-key")

    assert result.provider == "openai"
    request = transport.requests[0]
    assert request["store"] is False
    assert request["max_retries"] == 0
    assert request["truncation"] == "disabled"
    assert request["text"]["format"]["strict"] is True
    assert "base_url" not in request


@pytest.mark.parametrize("response, code", [
    ({"refusal": True}, ErrorCode.PERMISSION_DENIED),
    ({"output_text": {}}, ErrorCode.INVALID_RESPONSE),
    ({"error": {"status": 429}}, ErrorCode.RATE_LIMITED),
    ({"error": {"status": 503}}, ErrorCode.PROVIDER_UNAVAILABLE),
])
def test_fake_transport_maps_failures_to_named_safe_errors(response: dict[str, object], code: ErrorCode) -> None:
    provider = OpenAIResponsesProvider(model="gpt-4.1-mini", transport=_Transport(response))

    with pytest.raises(CloudProviderError) as exc_info:
        provider.summarize_with_credential(_input(), "synthetic-key")

    assert exc_info.value.error.code is code


def test_evidence_must_be_an_exact_substring_of_the_outbound_payload() -> None:
    response = _valid_response()
    response["output_text"] = {**response["output_text"], "evidence": [
        {"evidence_id": "bad", "source": "title", "excerpt": "private path /tmp/nope"},
    ], "core_points": [
        {"text": "Unsupported.", "kind": "fact", "evidence_ids": ["bad"]},
    ]}
    provider = OpenAIResponsesProvider(model="gpt-4.1-mini", transport=_Transport(response))

    with pytest.raises(CloudProviderError) as exc_info:
        provider.summarize_with_credential(_input(), "synthetic-key")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


class _Resolver:
    def __init__(self, value: str | None = "synthetic-key") -> None:
        self.value = value
        self.calls = 0

    def resolve(self, env_name: str) -> str | None:
        self.calls += 1
        return self.value


def _repository_service(tmp_path: Path) -> tuple[SQLiteStateRepository, RepositoryBackedAnalysisService, _Transport]:
    now = datetime.now(UTC)
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=now)
    metadata = _video()
    repository.upsert_video_metadata(metadata, pipeline_version="pipeline-v1", now=now)
    for before, after in ((PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY), (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY), (PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SCORED)):
        assert repository.advance_pipeline(metadata.video_id, expected_status=before, target_status=after, pipeline_version="pipeline-v1", now=now)
    connection = repository._connect()
    try:
        connection.execute("UPDATE videos SET should_summarize = 1 WHERE video_id = ?", (metadata.video_id,))
    finally:
        connection.close()
    repository.create_job(job_id="analysis-job", scope_key="video:video-123:ANALYSIS", video_id=metadata.video_id,
        job_type=JobType.VIDEO_STAGE, target_stage=ProcessingStage.ANALYSIS, pipeline_version="pipeline-v1", max_attempts=3, available_at=now, now=now)
    assert repository.claim_next_job(owner="worker", lease_until=now + timedelta(minutes=5), now=now)
    transport = _Transport(_valid_response())
    service = RepositoryBackedAnalysisService(provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport),
        settings=CloudSettings(enabled=True, model="gpt-4.1-mini"), repository=repository,
        context=AnalysisJobContext("analysis-job", "worker", "pipeline-v1"), artifact_root=tmp_path / "data",
        credential_resolver=_Resolver(), budget=CloudCallBudget(limit=5))
    return repository, service, transport


def test_repository_completion_persists_both_artifacts_and_exact_raw_retention(tmp_path: Path) -> None:
    repository, service, _ = _repository_service(tmp_path)
    service.analyze(video=_video(), transcript_text="transcript evidence", language="en")
    request_hash = build_analysis_input(video=_video(), transcript_text="transcript evidence", language="en", output_language="zh-CN", settings=CloudSettings(enabled=True, model="gpt-4.1-mini")).request_hash
    raw = repository.get_artifact_by_key(f"analysis/{request_hash}/raw")
    assert raw is not None and raw.expires_at == raw.created_at + timedelta(days=30)


def test_persistent_token_limit_has_no_credential_provider_or_sqlite_side_effect(
    tmp_path: Path,
) -> None:
    repository, service, transport = _repository_service(tmp_path)
    resolver = _Resolver()
    limited = RepositoryBackedAnalysisService(
        provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport),
        settings=CloudSettings(
            enabled=True, model="gpt-4.1-mini", max_local_input_tokens_per_video=1
        ),
        repository=repository,
        context=AnalysisJobContext("analysis-job", "worker", "pipeline-v1"),
        artifact_root=tmp_path / "data",
        credential_resolver=resolver,
        budget=CloudCallBudget(limit=5),
    )

    outcome = limited.analyze(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en"
    )

    assert outcome.reason.value == "INPUT_TOO_LARGE"
    assert resolver.calls == 0
    assert transport.requests == []
    request_hash = build_analysis_input(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en",
        output_language="zh-CN", settings=limited.settings,
    ).request_hash
    assert repository.get_provider_call(request_hash) is None
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status.value == "RUNNING"


def test_persistent_exhausted_budget_has_no_credential_provider_or_sqlite_side_effect(
    tmp_path: Path,
) -> None:
    repository, _, transport = _repository_service(tmp_path)
    resolver = _Resolver()
    budget = CloudCallBudget(limit=1)
    assert budget.try_consume()
    exhausted = RepositoryBackedAnalysisService(
        provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport),
        settings=CloudSettings(enabled=True, model="gpt-4.1-mini"),
        repository=repository,
        context=AnalysisJobContext("analysis-job", "worker", "pipeline-v1"),
        artifact_root=tmp_path / "data",
        credential_resolver=resolver,
        budget=budget,
    )

    outcome = exhausted.analyze(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en"
    )

    assert outcome.reason.value == "BUDGET_EXHAUSTED"
    assert outcome.call is None
    assert resolver.calls == 0
    assert transport.requests == []
    request_hash = build_analysis_input(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en",
        output_language="zh-CN", settings=exhausted.settings,
    ).request_hash
    assert repository.get_provider_call(request_hash) is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/raw") is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/structured") is None
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status.value == "RUNNING"


def test_persistent_disabled_policy_has_no_side_effects(tmp_path: Path) -> None:
    repository, _, transport = _repository_service(tmp_path)
    resolver = _Resolver()
    disabled = RepositoryBackedAnalysisService(
        provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport),
        settings=CloudSettings(enabled=False, model="gpt-4.1-mini"), repository=repository,
        context=AnalysisJobContext("analysis-job", "worker", "pipeline-v1"),
        artifact_root=tmp_path / "data", credential_resolver=resolver,
        budget=CloudCallBudget(limit=5),
    )

    outcome = disabled.analyze(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en"
    )

    assert outcome.reason is AnalysisSkipReason.CLOUD_DISABLED
    assert resolver.calls == 0
    assert transport.requests == []
    request_hash = build_analysis_input(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en",
        output_language="zh-CN", settings=disabled.settings,
    ).request_hash
    assert repository.get_provider_call(request_hash) is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/raw") is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/structured") is None
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status.value == "RUNNING"


def test_persistent_low_value_policy_has_no_side_effects(tmp_path: Path) -> None:
    repository, service, transport = _repository_service(tmp_path)
    connection = repository._connect()
    try:
        connection.execute("UPDATE videos SET should_summarize = 0 WHERE video_id = ?", ("video-123",))
    finally:
        connection.close()

    outcome = service.analyze(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en"
    )

    assert outcome is None
    assert service.credential_resolver.calls == 0
    assert transport.requests == []
    request_hash = build_analysis_input(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en",
        output_language="zh-CN", settings=service.settings,
    ).request_hash
    assert repository.get_provider_call(request_hash) is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/raw") is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/structured") is None
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status.value == "RUNNING"


def test_persistent_missing_credential_has_no_side_effects(tmp_path: Path) -> None:
    repository, _, transport = _repository_service(tmp_path)
    resolver = _Resolver(value=None)
    unavailable = RepositoryBackedAnalysisService(
        provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=transport),
        settings=CloudSettings(enabled=True, model="gpt-4.1-mini"), repository=repository,
        context=AnalysisJobContext("analysis-job", "worker", "pipeline-v1"),
        artifact_root=tmp_path / "data", credential_resolver=resolver,
        budget=CloudCallBudget(limit=5),
    )

    outcome = unavailable.analyze(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en"
    )

    assert outcome.reason is AnalysisSkipReason.CREDENTIAL_UNAVAILABLE
    assert resolver.calls == 1
    assert transport.requests == []
    request_hash = build_analysis_input(
        video=_video(), transcript_text="ordinary synthetic transcript", language="en",
        output_language="zh-CN", settings=unavailable.settings,
    ).request_hash
    assert repository.get_provider_call(request_hash) is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/raw") is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/structured") is None
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status.value == "RUNNING"


def test_stage_transaction_failure_rolls_back_indexes_and_cleans_new_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, service, transport = _repository_service(tmp_path)

    def fail_after_provider_call(point: str) -> None:
        if point == "stage.after_provider_call":
            raise RuntimeError("injected transaction failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_after_provider_call)
    with pytest.raises(RuntimeError, match="injected transaction failure"):
        service.analyze(video=_video(), transcript_text="transcript evidence", language="en")

    request_hash = build_analysis_input(video=_video(), transcript_text="transcript evidence", language="en", output_language="zh-CN", settings=CloudSettings(enabled=True, model="gpt-4.1-mini")).request_hash
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/raw") is None
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/structured") is None
    assert repository.get_provider_call(request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert repository.get_provider_dispatch(request_hash).status is ProviderDispatchStatus.AMBIGUOUS
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-job").status.value == "RUNNING"
    assert not (tmp_path / "data" / "analysis" / request_hash / "raw.json").exists()
    assert len(transport.requests) == 1


def test_crashed_returned_cloud_result_is_not_redispatched_or_credential_rechecked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, service, transport = _repository_service(tmp_path)
    original = repository.record_provider_dispatch_result_unknown

    def crash_after_durable_unknown(*args: object, **kwargs: object) -> object:
        original(*args, **kwargs)
        raise SystemExit("simulated process crash")

    monkeypatch.setattr(repository, "record_provider_dispatch_result_unknown", crash_after_durable_unknown)
    with pytest.raises(SystemExit, match="simulated process crash"):
        service.analyze(video=_video(), transcript_text="transcript evidence", language="en")

    request_hash = build_analysis_input(
        video=_video(), transcript_text="transcript evidence", language="en",
        output_language="zh-CN", settings=service.settings,
    ).request_hash
    assert len(transport.requests) == 1
    assert repository.get_provider_dispatch(request_hash).status is ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN
    assert service.credential_resolver.calls == 1

    monkeypatch.setattr(repository, "record_provider_dispatch_result_unknown", original)
    later = datetime.now(UTC) + timedelta(minutes=6)
    monkeypatch.setattr(analysis_mod, "_utcnow", lambda: later)
    with pytest.raises(AnalysisPolicyError) as raised:
        service.analyze(video=_video(), transcript_text="transcript evidence", language="en")

    assert raised.value.error.code is ErrorCode.PROVIDER_UNAVAILABLE
    assert raised.value.error.retryable is False
    assert service.credential_resolver.calls == 1
    assert len(transport.requests) == 1
    assert repository.get_provider_call(request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert repository.get_provider_dispatch(request_hash).status is ProviderDispatchStatus.AMBIGUOUS


def test_explicit_provider_refusal_is_recorded_as_known_failure_not_ambiguity(
    tmp_path: Path
) -> None:
    repository, service, transport = _repository_service(tmp_path)
    transport.response = {"refusal": True}

    with pytest.raises(CloudProviderError):
        service.analyze(video=_video(), transcript_text="transcript evidence", language="en")

    request_hash = build_analysis_input(
        video=_video(), transcript_text="transcript evidence", language="en",
        output_language="zh-CN", settings=service.settings,
    ).request_hash
    assert len(transport.requests) == 1
    assert repository.get_provider_call(request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert repository.get_provider_dispatch(request_hash).status is ProviderDispatchStatus.FAILED_KNOWN


def test_reordered_job_reuses_succeeded_provider_call_without_transport(
    tmp_path: Path,
) -> None:
    repository, service, transport = _repository_service(tmp_path)
    service.analyze(video=_video(), transcript_text="transcript evidence", language="en")
    request_hash = build_analysis_input(
        video=_video(), transcript_text="transcript evidence", language="en",
        output_language="zh-CN", settings=service.settings,
    ).request_hash
    cached_call = repository.get_provider_call(request_hash)
    cached_raw = repository.get_artifact_by_key(f"analysis/{request_hash}/raw")
    cached_structured = repository.get_artifact_by_key(f"analysis/{request_hash}/structured")
    now = datetime.now(UTC)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, "video-123"),
        )
    finally:
        connection.close()
    repository.create_job(job_id="analysis-reordered", scope_key="video:video-123:ANALYSIS", video_id="video-123", job_type=JobType.VIDEO_STAGE, target_stage=ProcessingStage.ANALYSIS, pipeline_version="pipeline-v1", max_attempts=3, available_at=now, now=now)
    assert repository.claim_next_job(owner="worker", lease_until=now + timedelta(minutes=5), now=now)
    reordered_transport = _Transport(_valid_response())
    reordered_resolver = _Resolver()
    reordered = RepositoryBackedAnalysisService(provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=reordered_transport), settings=CloudSettings(enabled=True, model="gpt-4.1-mini"), repository=repository, context=AnalysisJobContext("analysis-reordered", "worker", "pipeline-v1"), artifact_root=tmp_path / "data", credential_resolver=reordered_resolver, budget=CloudCallBudget(limit=5))
    result = reordered.analyze(video=_video(), transcript_text="transcript evidence", language="en")
    assert result.result.provider == "openai"
    assert len(transport.requests) == 1
    assert reordered_transport.requests == []
    assert reordered_resolver.calls == 0
    assert repository.get_provider_call(request_hash) == cached_call
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/raw") == cached_raw
    assert repository.get_artifact_by_key(f"analysis/{request_hash}/structured") == cached_structured


@pytest.mark.parametrize(
    "tamper",
    (
        "structured_result_identity",
        "raw_file_contents",
        "structured_file_contents",
        "raw_index_hash",
        "structured_index_hash",
        "provider_call_model",
        "structured_artifact_provider",
        "raw_artifact_model",
        "missing_raw_artifact",
        "missing_structured_artifact",
    ),
)
def test_reordered_job_fails_closed_when_persisted_cache_is_not_complete_and_matching(
    tmp_path: Path, tamper: str
) -> None:
    repository, service, transport = _repository_service(tmp_path)
    service.analyze(video=_video(), transcript_text="transcript evidence", language="en")
    request_hash = build_analysis_input(
        video=_video(), transcript_text="transcript evidence", language="en",
        output_language="zh-CN", settings=service.settings,
    ).request_hash
    raw_key = f"analysis/{request_hash}/raw"
    structured_key = f"analysis/{request_hash}/structured"
    raw = repository.get_artifact_by_key(raw_key)
    structured = repository.get_artifact_by_key(structured_key)
    assert raw is not None and structured is not None

    connection = repository._connect()
    try:
        if tamper == "structured_result_identity":
            path = tmp_path / "data" / structured.relative_path
            payload = json.loads(path.read_text())
            payload["request_hash"] = "0" * 64
            contents = json.dumps(payload).encode()
            path.write_bytes(contents)
            connection.execute(
                "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                (hashlib.sha256(contents).hexdigest(), structured_key),
            )
        elif tamper == "raw_file_contents":
            (tmp_path / "data" / raw.relative_path).write_bytes(b"tampered raw")
        elif tamper == "structured_file_contents":
            (tmp_path / "data" / structured.relative_path).write_bytes(b"tampered structured")
        elif tamper == "raw_index_hash":
            connection.execute(
                "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                ("0" * 64, raw_key),
            )
        elif tamper == "structured_index_hash":
            connection.execute(
                "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                ("0" * 64, structured_key),
            )
        elif tamper == "provider_call_model":
            connection.execute(
                "UPDATE provider_calls SET model = ? WHERE request_hash = ?",
                ("tampered-model", request_hash),
            )
        elif tamper == "structured_artifact_provider":
            connection.execute(
                "UPDATE artifacts SET provider = ? WHERE artifact_key = ?",
                ("tampered-provider", structured_key),
            )
        elif tamper == "raw_artifact_model":
            connection.execute(
                "UPDATE artifacts SET model = ? WHERE artifact_key = ?",
                ("tampered-model", raw_key),
            )
        elif tamper == "missing_raw_artifact":
            connection.execute(
                "UPDATE artifacts SET artifact_key = ? WHERE artifact_key = ?",
                (f"{raw_key}-missing", raw_key),
            )
        else:
            assert tamper == "missing_structured_artifact"
            connection.execute(
                "UPDATE artifacts SET artifact_key = ? WHERE artifact_key = ?",
                (f"{structured_key}-missing", structured_key),
            )
    finally:
        connection.close()

    now = datetime.now(UTC)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.SCORED.value, "video-123"),
        )
    finally:
        connection.close()
    repository.create_job(job_id="analysis-cache-invalid", scope_key="video:video-123:ANALYSIS",
        video_id="video-123", job_type=JobType.VIDEO_STAGE, target_stage=ProcessingStage.ANALYSIS,
        pipeline_version="pipeline-v1", max_attempts=3, available_at=now, now=now)
    assert repository.claim_next_job(owner="worker", lease_until=now + timedelta(minutes=5), now=now)
    resolver = _Resolver()
    reordered_transport = _Transport(_valid_response())
    reordered = RepositoryBackedAnalysisService(
        provider=OpenAIResponsesProvider(model="gpt-4.1-mini", transport=reordered_transport),
        settings=service.settings, repository=repository,
        context=AnalysisJobContext("analysis-cache-invalid", "worker", "pipeline-v1"),
        artifact_root=tmp_path / "data", credential_resolver=resolver,
        budget=CloudCallBudget(limit=5),
    )

    with pytest.raises(AnalysisPolicyError) as exc_info:
        reordered.analyze(video=_video(), transcript_text="transcript evidence", language="en")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert resolver.calls == 0
    assert reordered_transport.requests == []
    assert len(transport.requests) == 1
    assert repository.get_video("video-123").pipeline_status is PipelineStatus.SCORED
    assert repository.get_job("analysis-cache-invalid").status.value == "RUNNING"


class _FakeChild:
    def __init__(
        self,
        output: bytes,
        *,
        returncode: int | None = None,
        keep_stdout_open: bool = False,
    ) -> None:
        stdin_read, stdin_write = os.pipe()
        stdout_read, stdout_write = os.pipe()
        self.stdin = os.fdopen(stdin_write, "wb", buffering=0)
        self.stdout = os.fdopen(stdout_read, "rb", buffering=0)
        self._stdin_read = stdin_read
        self._stdout_write: int | None = stdout_write
        self.returncode = returncode
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_timeouts: list[float | None] = []
        if output:
            os.write(stdout_write, output)
        if not keep_stdout_open:
            os.close(stdout_write)
            self._stdout_write = None

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.returncode = -15
        self._close_child_fds()

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9
        self._close_child_fds()

    def wait(self, timeout: float | None = None) -> int:
        self.wait_timeouts.append(timeout)
        if self.returncode is None:
            raise subprocess.TimeoutExpired(["fake-child"], timeout)
        return self.returncode

    def _close_child_fds(self) -> None:
        if self._stdout_write is not None:
            os.close(self._stdout_write)
            self._stdout_write = None
        os.close(self._stdin_read)


def _isolated_provider() -> OpenAIResponsesProvider:
    return OpenAIResponsesProvider(model="gpt-4.1-mini")


@pytest.mark.parametrize(
    ("child", "must_terminate"),
    (
        (_FakeChild(b"", keep_stdout_open=True), True),
        (_FakeChild(b'{"kind":"ready"}\n', keep_stdout_open=True), True),
        (_FakeChild(b'{"kind":"ready"}\n', keep_stdout_open=False), True),
        (_FakeChild(b'{"kind":"ready"}\n{not-json}\n', keep_stdout_open=True), True),
        (_FakeChild(b'{"kind":"ready"}\n{}\n', returncode=1), False),
    ),
    ids=("never-handshake", "never-response", "eof", "malformed-json", "nonzero-exit"),
)
def test_isolated_transport_failures_are_bounded_reaped_and_safely_mapped(
    child: _FakeChild,
    must_terminate: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cloud_llm, "_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(cloud_llm.subprocess, "Popen", lambda *args, **kwargs: child)

    with pytest.raises(CloudProviderError) as exc_info:
        _isolated_provider().summarize_with_credential(_input(), "synthetic-key")

    assert exc_info.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert "synthetic-key" not in str(exc_info.value)
    assert child.stdin.closed and child.stdout.closed
    assert child.wait_timeouts and all(timeout is not None for timeout in child.wait_timeouts)
    if must_terminate:
        assert child.terminate_calls + child.kill_calls >= 1
    else:
        assert child.wait_timeouts[0] <= 0.01


def test_isolated_transport_returns_normal_response_and_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _FakeChild(
        b'{"kind":"ready"}\n'
        b'{"output_text":{"one_sentence_summary":"The transcript supplies evidence.",'
        b'"core_points":[{"text":"Useful title is named.","kind":"fact",'
        b'"evidence_ids":["title-1"]}],"keywords":["useful"],'
        b'"evidence":[{"evidence_id":"title-1","source":"title",'
        b'"excerpt":"Useful title"}]},"input_tokens":24,"output_tokens":18}\n',
        returncode=0,
    )
    monkeypatch.setattr(cloud_llm, "_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(cloud_llm.subprocess, "Popen", lambda *args, **kwargs: child)

    result = _isolated_provider().summarize_with_credential(_input(), "synthetic-key")

    assert result.provider == "openai"
    assert child.wait_timeouts == [pytest.approx(0.01, abs=0.01)]
    assert child.terminate_calls == 0 and child.kill_calls == 0
    assert child.stdin.closed and child.stdout.closed
