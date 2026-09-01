"""Offline v4 dispatch tests for the fixed OpenAI qualification package."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from youtube_intel.deep_analysis_contracts import (
    DeepAnalysisFailureCode,
    DeepAnalysisFailureStage,
    DeepAnalysisFailureV1,
)
from youtube_intel.openai_deep_analysis import OpenAIDeepAnalysisProviderError
from youtube_intel.openai_qualification import (
    FROZEN_OPENAI_QUALIFICATION_MANIFESTS,
    OpenAIQualificationDispatchError,
    OpenAIQualificationExecutor,
    openai_qualification_request_for_manifest,
)
from youtube_intel.state import (
    ProviderCallStatus,
    ProviderDispatchStatus,
    SQLiteStateRepository,
)

NOW = datetime(2026, 8, 31, tzinfo=UTC)


class _Adapter:
    def __init__(self) -> None:
        self.calls = 0
        self.transport_timeouts: list[float] = []
        self.transport_retries: list[int] = []

    def dispatch(self, *, prepared_dispatch: object, credential: str) -> object:
        self.calls += 1
        evidence_id = prepared_dispatch.envelope.canonical_input.selected_evidence[0].evidence_id
        content = {
            "one_sentence_summary": "A synthetic qualification response explains its selected evidence.",
            "summary_evidence_ids": [evidence_id],
            "why_it_matters": {
                "text": "A synthetic qualification response explains its selected evidence.",
                "kind": "inference",
                "evidence_ids": [evidence_id],
            },
            "core_points": [
                {
                    "text": "A synthetic qualification response explains its selected evidence.",
                    "kind": "fact",
                    "evidence_ids": [evidence_id],
                }
            ],
            "knowledge_graph": {"topics": ["qualification"]},
        }
        from youtube_intel.openai_deep_analysis import OpenAIDeepAnalysisProviderAdapter

        def transport(_request, _credential, timeout_seconds, max_retries):
            self.transport_timeouts.append(timeout_seconds)
            self.transport_retries.append(max_retries)
            return {
                "kind": "response",
                "response": {
                    "id": "synthetic-response-id",
                    "model": "gpt-5.4-mini-2026-03-17",
                    "status": "completed",
                    "output_text": json.dumps(content),
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            }

        return OpenAIDeepAnalysisProviderAdapter(transport=transport).dispatch(
            prepared_dispatch=prepared_dispatch, credential=credential
        )


def test_package_success_uses_v4_durable_dispatch_for_both_fixed_cases(tmp_path) -> None:
    repository = SQLiteStateRepository(tmp_path / "qualification.sqlite")
    repository.initialize(now=NOW)
    adapter = _Adapter()

    results = OpenAIQualificationExecutor(
        repository=repository,
        adapter=adapter,
        credential_resolver=lambda: "synthetic-credential",
    ).execute_package(owner="qualification-worker", now=NOW)

    assert len(results) == 2
    assert adapter.calls == 2
    assert adapter.transport_timeouts == [30.0, 30.0]
    assert adapter.transport_retries == [0, 0]
    assert all(result.success is not None for result in results)
    assert all(
        repository.get_provider_dispatch(result.request_hash).status
        is ProviderDispatchStatus.SUCCESS_DURABLY_RECORDED
        for result in results
    )


def test_restart_from_durable_intent_becomes_ambiguous_without_credential_reresolution(
    tmp_path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "qualification.sqlite")
    repository.initialize(now=NOW)
    request = openai_qualification_request_for_manifest(
        FROZEN_OPENAI_QUALIFICATION_MANIFESTS[0]
    )
    repository.reserve_provider_call(
        request,
        owner="first-worker",
        lease_until=NOW + timedelta(minutes=5),
        available_at=NOW,
        now=NOW,
        fail_closed_on_ambiguous_dispatch=True,
    )
    repository.record_provider_dispatch_intent(request.request_hash, owner="first-worker", now=NOW)
    resolver_calls = 0

    def resolver() -> str:
        nonlocal resolver_calls
        resolver_calls += 1
        return "synthetic-credential"

    with pytest.raises(OpenAIQualificationDispatchError, match="ambiguous"):
        OpenAIQualificationExecutor(
            repository=repository,
            adapter=_Adapter(),
            credential_resolver=resolver,
        ).execute_package(owner="recovery-worker", now=NOW + timedelta(minutes=6))

    assert resolver_calls == 0
    assert repository.get_provider_call(request.request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert repository.get_provider_dispatch(request.request_hash).status is ProviderDispatchStatus.AMBIGUOUS


def test_explicit_provider_refusal_is_known_failure_and_cannot_substitute_case(
    tmp_path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "qualification.sqlite")
    repository.initialize(now=NOW)

    class RefusingAdapter:
        calls = 0

        def dispatch(self, *, prepared_dispatch: object, credential: str) -> object:
            del prepared_dispatch, credential
            self.calls += 1
            raise OpenAIDeepAnalysisProviderError(
                DeepAnalysisFailureV1(
                    schema_version="deep-analysis-failure-v1",
                    code=DeepAnalysisFailureCode.AUTH_INVALID,
                    stage=DeepAnalysisFailureStage.PROVIDER_ACCOUNT,
                )
            )

    refusing_adapter = RefusingAdapter()
    executor = OpenAIQualificationExecutor(
        repository=repository,
        adapter=refusing_adapter,
        credential_resolver=lambda: "synthetic-credential",
    )

    with pytest.raises(OpenAIQualificationDispatchError, match="provider refusal"):
        executor.execute_package(owner="qualification-worker", now=NOW)

    first = openai_qualification_request_for_manifest(
        FROZEN_OPENAI_QUALIFICATION_MANIFESTS[0]
    )
    second = openai_qualification_request_for_manifest(
        FROZEN_OPENAI_QUALIFICATION_MANIFESTS[1]
    )
    assert refusing_adapter.calls == 1
    assert repository.get_provider_call(first.request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert repository.get_provider_dispatch(first.request_hash).status is ProviderDispatchStatus.FAILED_KNOWN
    assert repository.get_provider_call(second.request_hash) is None

    with pytest.raises(OpenAIQualificationDispatchError, match="terminal"):
        executor.execute_package(owner="qualification-worker", now=NOW + timedelta(minutes=1))
    assert refusing_adapter.calls == 1


def test_crash_before_durable_intent_is_the_only_safe_takeover_case(tmp_path) -> None:
    repository = SQLiteStateRepository(tmp_path / "qualification.sqlite")
    repository.initialize(now=NOW)
    request = openai_qualification_request_for_manifest(
        FROZEN_OPENAI_QUALIFICATION_MANIFESTS[0]
    )
    repository.reserve_provider_call(
        request,
        owner="crashed-before-intent",
        lease_until=NOW + timedelta(minutes=5),
        available_at=NOW,
        now=NOW,
        fail_closed_on_ambiguous_dispatch=True,
    )
    adapter = _Adapter()

    OpenAIQualificationExecutor(
        repository=repository,
        adapter=adapter,
        credential_resolver=lambda: "synthetic-credential",
    ).execute_package(owner="recovery-worker", now=NOW + timedelta(minutes=6))

    assert adapter.calls == 2
    assert repository.get_provider_dispatch(request.request_hash).status is ProviderDispatchStatus.SUCCESS_DURABLY_RECORDED


def test_returned_result_crash_cannot_be_redispatched_or_promoted_from_artifact(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SQLiteStateRepository(tmp_path / "qualification.sqlite")
    repository.initialize(now=NOW)
    adapter = _Adapter()
    original_complete = repository.complete_provider_call

    def crash_before_local_success(*args, **kwargs):
        del args, kwargs
        raise SystemExit("simulated process crash")

    monkeypatch.setattr(repository, "complete_provider_call", crash_before_local_success)
    with pytest.raises(SystemExit, match="simulated process crash"):
        OpenAIQualificationExecutor(
            repository=repository,
            adapter=adapter,
            credential_resolver=lambda: "synthetic-credential",
        ).execute_package(owner="first-worker", now=NOW)
    monkeypatch.setattr(repository, "complete_provider_call", original_complete)

    request = openai_qualification_request_for_manifest(
        FROZEN_OPENAI_QUALIFICATION_MANIFESTS[0]
    )
    assert repository.get_provider_dispatch(request.request_hash).status is ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN
    assert repository.get_artifact_by_key(request.deterministic_artifact_key) is not None
    resolver_calls = 0

    def resolver() -> str:
        nonlocal resolver_calls
        resolver_calls += 1
        return "synthetic-credential"

    with pytest.raises(OpenAIQualificationDispatchError, match="ambiguous"):
        OpenAIQualificationExecutor(
            repository=repository,
            adapter=adapter,
            credential_resolver=resolver,
        ).execute_package(owner="recovery-worker", now=NOW + timedelta(minutes=6))

    assert adapter.calls == 1
    assert resolver_calls == 0
    assert repository.get_provider_call(request.request_hash).status is ProviderCallStatus.FAILED_FINAL
    assert repository.get_provider_dispatch(request.request_hash).status is ProviderDispatchStatus.AMBIGUOUS
