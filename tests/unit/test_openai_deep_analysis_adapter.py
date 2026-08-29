"""Tests for the qualified OpenAI reference Deep Analysis adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisPayloadScope,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
)
from youtube_intel.deep_analysis_runtime import (
    DeepAnalysisRuntime,
    PreparedDeepAnalysisDispatch,
)
from youtube_intel.domain import (
    EvidenceRegistry,
    EvidenceSource,
    KnowledgeEvidence,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.openai_deep_analysis import (
    OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE,
    OpenAIDeepAnalysisProviderAdapter,
    OpenAIDeepAnalysisProviderError,
    build_openai_reference_context_budget,
    build_openai_reference_execution_profile,
    build_openai_reference_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead


def _read() -> VerifiedScoringRead:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8.0,
        reason="This result contains a concrete useful explanation of the score.",
        topics=("workflow",),
        should_summarize=True,
        provider="scoring-provider",
        model="scoring-model",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )
    return VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=7.0, final_should_summarize=True, model_disagrees=False
            ),
            call=ProviderCallMetadata(
                provider="scoring-provider",
                model="scoring-model",
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                finished_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ),
        video_id="video-1",
        scoring_job_id="job-1",
        scoring_success_provenance="PRIMARY",
    )


def _registry() -> EvidenceRegistry:
    return EvidenceRegistry(
        items=(
            KnowledgeEvidence(
                evidence_id="e1",
                source=EvidenceSource.DESCRIPTION,
                excerpt="Selected evidence only.",
                source_content_hash="d" * 64,
            ),
        )
    )


def _prepared(*, full_transcript: str = "unselected full transcript") -> tuple[DeepAnalysisRuntime, PreparedDeepAnalysisDispatch]:
    read = _read()
    canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=read,
        schema_version="canonical-deep-analysis-input-v1",
        operation="deep-analysis",
        input_schema_version="input-v1",
        video_identity="video-1",
        transcript_identity="transcript-1",
        transcript_language="en",
        transcript_normalization_version="normalized-v1",
        evidence_registry_identity="registry-v1",
        selected_evidence=(
            {
                "schema_version": "selected-evidence-projection-v1",
                "evidence_id": "e1",
                "source": "description",
                "excerpt": "Selected evidence only.",
            },
        ),
        selection_policy_identity="selection-v1",
        coverage_policy_identity="coverage-v1",
        coverage_complete=False,
        output_language="en",
        knowledge_content_schema_version="knowledge-v1",
        prompt_version="prompt-v1",
        operation_version="operation-v1",
    )
    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=read, canonical_input=canonical
    )
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.CLOUD_EXPLICIT,
        authorization_record_identity="openai-test-consent-v1",
        named_provider_id=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.provider_id,
        provider_kind=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.provider_kind,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.model_id,
    )
    payload = runtime.authorize_payload(
        authoritative_input=admitted,
        evidence_registry=_registry(),
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=consent,
        video_title="Title",
        channel_name="Channel",
        published_at="2026-01-01T00:00:00Z",
        duration_seconds=42,
        source_language="en",
        public_description="Selected evidence only.",
    )
    request = build_openai_reference_request_projection(
        canonical_input=canonical,
        authorized_payload=payload.payload,
        payload_consent=consent,
    )
    credential_profile = CredentialExecutionProfileIdentityV1(
        schema_version="credential-execution-profile-v1",
        provider_id="openai",
        execution_profile_identity="b" * 64,
    )
    execution = build_openai_reference_execution_profile(
        request_projection=request,
        credential_execution_profile=credential_profile,
    )
    return runtime, runtime.prepare_dispatch(
        authoritative_input=admitted,
        authorized_payload=payload,
        request_projection=request,
        execution_profile=execution,
        payload_consent=consent,
        context_budget_profile=build_openai_reference_context_budget(input_budget=1_024),
        timeout_profile_identity=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.timeout_profile_identity,
        fallback_policy_identity="c" * 64,
    )


def _content(evidence_id: str = "e1") -> dict[str, object]:
    statement = "This result contains a concrete useful explanation of the score."
    return {
        "one_sentence_summary": statement,
        "summary_evidence_ids": [evidence_id],
        "why_it_matters": {"text": statement, "kind": "inference", "evidence_ids": [evidence_id]},
        "core_points": [{"text": statement, "kind": "fact", "evidence_ids": [evidence_id]}],
        "knowledge_graph": {"topics": ["workflow"]},
    }


class _FakeTransport:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []
        self.credentials: list[str] = []
        self.timeouts: list[float] = []
        self.retries: list[int] = []

    def __call__(
        self,
        request: Mapping[str, object],
        credential: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> Mapping[str, object]:
        self.requests.append(dict(request))
        self.credentials.append(credential)
        self.timeouts.append(timeout_seconds)
        self.retries.append(max_retries)
        return self.response


def _provider_response(*, payload: object | None = None, model: str | None = None) -> dict[str, object]:
    return {
        "kind": "response",
        "response": {
            "id": "resp_qualified_test",
            "model": model or OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.model_id,
            "status": "completed",
            "output_text": json.dumps(payload if payload is not None else _content()),
            "usage": {"input_tokens": 41, "output_tokens": 17},
        },
    }


def test_provider_request_id_and_usage_do_not_enter_response_identity() -> None:
    _, prepared = _prepared()
    first = _provider_response()
    second = _provider_response()
    second_response = second["response"]
    assert isinstance(second_response, dict)
    second_response["id"] = "resp_different_request_id"
    second_response["usage"] = {"input_tokens": 999, "output_tokens": 999}

    first_untrusted = OpenAIDeepAnalysisProviderAdapter(
        transport=_FakeTransport(first)
    ).dispatch(prepared_dispatch=prepared, credential="sentinel-openai-api-key")
    second_untrusted = OpenAIDeepAnalysisProviderAdapter(
        transport=_FakeTransport(second)
    ).dispatch(prepared_dispatch=prepared, credential="sentinel-openai-api-key")

    assert first_untrusted.provider_request_id != second_untrusted.provider_request_id
    assert first_untrusted.usage_evidence != second_untrusted.usage_evidence
    assert first_untrusted.provider_envelope_identity == second_untrusted.provider_envelope_identity


def test_request_projection_is_explicit_and_selected_evidence_only() -> None:
    runtime, prepared = _prepared()
    transport = _FakeTransport(_provider_response())
    response = OpenAIDeepAnalysisProviderAdapter(transport=transport).dispatch(
        prepared_dispatch=prepared, credential="sentinel-openai-api-key"
    )

    assert response.delivery_certainty == "CONFIRMED"
    assert response.structured_output_mode.value == "PROVIDER_JSON_SCHEMA"
    assert response.usage_evidence is not None
    assert response.usage_evidence.provider_reported_input_tokens == 41
    assert runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=response
    ).success is not None

    request = transport.requests[0]
    assert request["model"] == OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.model_id
    assert request["store"] is False
    assert request["truncation"] == "disabled"
    assert request["stream"] is False
    assert request["parallel_tool_calls"] is False
    assert request["service_tier"] == "default"
    assert request["max_output_tokens"] == 4096
    assert request["reasoning"] == {"effort": "low"}
    assert isinstance(request["text"], Mapping)
    text = request["text"]
    assert isinstance(text["format"], Mapping)
    text_format = text["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["name"] == "deep_analysis_knowledge_content_v1"
    assert text_format["strict"] is True
    assert isinstance(text_format["schema"], Mapping)
    schema = text_format["schema"]
    assert schema == {
        key: value
        for key, value in schema.items()
    }
    assert "unselected full transcript" not in json.dumps(request)
    assert "sentinel-openai-api-key" not in json.dumps(request)
    assert transport.timeouts == [30.0]
    assert transport.retries == [0]


def test_schema_valid_fabricated_evidence_remains_untrusted_and_is_rejected() -> None:
    runtime, prepared = _prepared()
    transport = _FakeTransport(_provider_response(payload=_content("fabricated-evidence")))
    response = OpenAIDeepAnalysisProviderAdapter(transport=transport).dispatch(
        prepared_dispatch=prepared, credential="sentinel-openai-api-key"
    )

    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=response
    )
    assert result.failure is not None
    assert result.failure.code.value == "GROUNDING_INVALID"


def test_adapter_extracts_only_output_text_and_never_repairs_fenced_json() -> None:
    runtime, prepared = _prepared()
    provider_response = _provider_response()
    raw = provider_response["response"]
    assert isinstance(raw, dict)
    raw["output_text"] = "```json\n" + json.dumps(_content()) + "\n```"
    raw["output"] = [{"content": [{"text": json.dumps(_content())}]}]

    response = OpenAIDeepAnalysisProviderAdapter(
        transport=_FakeTransport(provider_response)
    ).dispatch(prepared_dispatch=prepared, credential="sentinel-openai-api-key")

    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=response
    )
    assert result.failure is not None
    assert result.failure.code.value == "STRUCTURED_OUTPUT_INVALID"


def test_model_echo_mismatch_is_left_untrusted_for_provenance_rejection() -> None:
    runtime, prepared = _prepared()
    transport = _FakeTransport(_provider_response(model="gpt-other-snapshot"))
    response = OpenAIDeepAnalysisProviderAdapter(transport=transport).dispatch(
        prepared_dispatch=prepared, credential="sentinel-openai-api-key"
    )

    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=response
    )
    assert result.failure is not None
    assert result.failure.code.value == "PROVENANCE_INVALID"


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (401, None, "AUTH_INVALID"),
        (429, "insufficient_quota", "QUOTA_EXCEEDED"),
        (429, None, "RATE_LIMITED"),
        (404, "model_not_found", "MODEL_UNAVAILABLE"),
        (503, None, "PROVIDER_UNAVAILABLE"),
        (400, None, "UNKNOWN"),
    ],
)
def test_provider_errors_are_mapped_without_retry(
    status: int, code: str | None, expected: str
) -> None:
    _, prepared = _prepared()
    transport = _FakeTransport(
        {"kind": "error", "status": status, "code": code, "category": "STATUS"}
    )

    with pytest.raises(OpenAIDeepAnalysisProviderError) as raised:
        OpenAIDeepAnalysisProviderAdapter(transport=transport).dispatch(
            prepared_dispatch=prepared, credential="sentinel-openai-api-key"
        )

    assert raised.value.failure.code.value == expected
    assert transport.retries == [0]


def test_credential_is_not_persisted_or_exposed_in_adapter_error_or_response() -> None:
    _, prepared = _prepared()
    sentinel = "sentinel-openai-api-key"
    transport = _FakeTransport({"kind": "error", "category": "TIMEOUT"})
    adapter = OpenAIDeepAnalysisProviderAdapter(transport=transport)

    with pytest.raises(OpenAIDeepAnalysisProviderError) as raised:
        adapter.dispatch(prepared_dispatch=prepared, credential=sentinel)

    serialized = json.dumps(raised.value.failure.model_dump(mode="json"))
    assert sentinel not in repr(adapter)
    assert sentinel not in repr(raised.value)
    assert sentinel not in serialized
    assert sentinel not in repr(prepared.envelope)
    assert transport.credentials == [sentinel]
    assert raised.value.failure.code.value == "TIMEOUT"


def test_missing_credential_fails_before_transport() -> None:
    _, prepared = _prepared()
    transport = _FakeTransport(_provider_response())

    with pytest.raises(OpenAIDeepAnalysisProviderError) as raised:
        OpenAIDeepAnalysisProviderAdapter(transport=transport).dispatch(
            prepared_dispatch=prepared, credential=""
        )

    assert raised.value.failure.code.value == "AUTH_REQUIRED"
    assert transport.requests == []


def test_adapter_module_exposes_no_trusted_success_mint() -> None:
    import youtube_intel.openai_deep_analysis as adapter_module

    assert "TrustedDeepAnalysisSuccess" not in vars(adapter_module)
    assert "mint" not in " ".join(adapter_module.__all__).lower()
