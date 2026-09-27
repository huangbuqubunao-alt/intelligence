from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from youtube_intel.analysis import (
    AnalysisJobContext,
    AnalysisPolicyError,
    CloudCallBudget,
    KnownLocalSummaryResponseError,
    RepositoryBackedAnalysisService,
)
from youtube_intel.config import LocalAnalysisSettings
from youtube_intel.domain import (
    Availability,
    ErrorCode,
    LiveStatus,
    VideoMetadata,
)
from youtube_intel.state import ProviderCallStatus, ProviderDispatchStatus


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-local-analysis",
        channel_id="channel-local-analysis",
        channel_name="Example Channel",
        title="A real and substantive topic",
        description="A public description",
        source_url="https://example.invalid/watch?v=video-local-analysis",
        published_at=datetime(2026, 9, 24, tzinfo=UTC),
        duration_seconds=240,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _settings() -> LocalAnalysisSettings:
    return LocalAnalysisSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + "0" * 64,
    )


class _Repository:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.dispatch_status: ProviderDispatchStatus | None = None
        self.failed_final = False

    def get_provider_call(self, _request_hash: str) -> SimpleNamespace | None:
        self.events.append("read-provider-call")
        if self.failed_final:
            return SimpleNamespace(status=ProviderCallStatus.FAILED_FINAL)
        return None

    def recover_provider_dispatch(
        self, _request_hash: str, *, now: datetime
    ) -> SimpleNamespace | None:
        self.events.append("read-dispatch")
        if self.dispatch_status is None:
            return None
        return SimpleNamespace(status=self.dispatch_status)

    def reserve_provider_call(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
        self.events.append("reserve")
        if self.failed_final:
            return SimpleNamespace(
                acquired=False,
                record=SimpleNamespace(
                    status=ProviderCallStatus.FAILED_FINAL,
                    last_error_code=ErrorCode.INVALID_RESPONSE.value,
                ),
            )
        return SimpleNamespace(acquired=True, record=None)

    def record_provider_dispatch_intent(self, *_args: object, **_kwargs: object) -> None:
        self.events.append("dispatch-intent")
        self.dispatch_status = ProviderDispatchStatus.DISPATCH_INTENT_DURABLE

    def mark_provider_dispatch_ambiguous(
        self, *_args: object, **_kwargs: object
    ) -> None:
        self.events.append("dispatch-ambiguous")
        self.dispatch_status = ProviderDispatchStatus.AMBIGUOUS

    def record_provider_dispatch_known_failure(
        self, *_args: object, **_kwargs: object
    ) -> None:
        self.events.append("dispatch-known-failure")
        self.dispatch_status = ProviderDispatchStatus.FAILED_KNOWN

    def fail_provider_call(self, *_args: object, **kwargs: object) -> None:
        self.events.append("provider-call-failed-final")
        assert kwargs["retryable"] is False
        assert kwargs["error_code"] is ErrorCode.INVALID_RESPONSE
        self.failed_final = True


class _LocalProvider:
    def __init__(self, events: list[str], *, fail_preflight: bool) -> None:
        self.events = events
        self.fail_preflight = fail_preflight
        self.preflight_calls = 0
        self.generation_calls = 0

    def preflight(self) -> None:
        self.events.append("preflight")
        self.preflight_calls += 1
        if self.fail_preflight:
            raise ConnectionError("local model is unavailable")

    def summarize(self, _analysis_input: object) -> None:
        self.events.append("generation-request")
        self.generation_calls += 1
        raise TimeoutError("the local generation result is unknown")


def _service(
    repository: _Repository,
    provider: _LocalProvider,
    budget: CloudCallBudget,
    monkeypatch: pytest.MonkeyPatch,
) -> RepositoryBackedAnalysisService:
    service = RepositoryBackedAnalysisService(
        provider=provider,
        settings=_settings(),
        repository=repository,
        context=AnalysisJobContext(
            job_id="job-local-analysis",
            owner="worker-local-analysis",
            pipeline_version="pipeline-local-analysis-v1",
        ),
        artifact_root=Path("/tmp/local-analysis-test-artifacts"),
        credential_resolver=SimpleNamespace(),
        budget=budget,
    )
    monkeypatch.setattr(service, "_validate_upstream", lambda **_kwargs: True)
    return service


def _analyze(service: RepositoryBackedAnalysisService) -> object:
    return service.analyze(
        video=_video(),
        transcript_text="A substantive local transcript about a useful topic.",
        language="en",
        output_language="zh-CN",
    )


def test_local_model_preflight_failure_is_known_before_provider_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _Repository()
    provider = _LocalProvider(repository.events, fail_preflight=True)
    budget = CloudCallBudget(limit=1)
    service = _service(repository, provider, budget, monkeypatch)

    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(service)

    assert raised.value.error.code is ErrorCode.PROVIDER_UNAVAILABLE
    assert raised.value.error.retryable is True
    assert repository.events == [
        "read-provider-call",
        "read-dispatch",
        "preflight",
    ]
    assert repository.dispatch_status is None
    assert provider.generation_calls == 0
    assert budget.remaining == 1


def test_post_dispatch_unknown_result_stays_ambiguous_across_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _Repository()
    provider = _LocalProvider(repository.events, fail_preflight=False)
    service = _service(repository, provider, CloudCallBudget(limit=1), monkeypatch)

    with pytest.raises(TimeoutError):
        _analyze(service)

    assert repository.dispatch_status is ProviderDispatchStatus.AMBIGUOUS
    assert repository.events[-3:] == [
        "dispatch-intent",
        "generation-request",
        "dispatch-ambiguous",
    ]
    preflight_calls = provider.preflight_calls
    generation_calls = provider.generation_calls

    restarted_service = _service(
        repository, provider, CloudCallBudget(limit=1), monkeypatch
    )
    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(restarted_service)

    assert raised.value.error.retryable is False
    assert repository.dispatch_status is ProviderDispatchStatus.AMBIGUOUS
    assert provider.preflight_calls == preflight_calls
    assert provider.generation_calls == generation_calls
    assert repository.events.count("reserve") == 1


def test_definite_invalid_summary_response_is_known_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _Repository()
    provider = _LocalProvider(repository.events, fail_preflight=False)
    def invalid_response(_input: object) -> None:
        provider.generation_calls += 1
        repository.events.append("generation-response-received")
        raise KnownLocalSummaryResponseError(
            "generation truncated", prompt_eval_count=3_850,
            eval_count=1_200, done=True, done_reason="length", response_length=24,
        )
    provider.summarize = invalid_response  # type: ignore[method-assign]
    service = _service(repository, provider, CloudCallBudget(limit=1), monkeypatch)

    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(service)

    assert raised.value.error.code is ErrorCode.INVALID_RESPONSE
    assert raised.value.error.retryable is False
    assert repository.dispatch_status is ProviderDispatchStatus.FAILED_KNOWN
    assert repository.events[-3:] == [
        "generation-response-received", "dispatch-known-failure", "provider-call-failed-final",
    ]
    generation_calls = provider.generation_calls
    with pytest.raises(AnalysisPolicyError) as replay:
        _analyze(_service(repository, provider, CloudCallBudget(limit=1), monkeypatch))
    assert replay.value.error.retryable is False
    assert replay.value.error.code is ErrorCode.INVALID_RESPONSE
    assert provider.generation_calls == generation_calls
