"""Contract tests for the frozen Kimi R2 Deep Analysis adapter."""

from __future__ import annotations

import json
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
from youtube_intel.kimi_deep_analysis import (
    KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2,
    KimiDeepAnalysisProviderAdapter,
    KimiDeepAnalysisProviderError,
    build_kimi_reference_context_budget,
    build_kimi_reference_execution_profile,
    build_kimi_reference_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead


def _prepared() -> tuple[DeepAnalysisRuntime, PreparedDeepAnalysisDispatch]:
    read = VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=ScoreResult(
                schema_version="score-result-v2", score=8.0,
                reason="The selected evidence contains a concrete useful explanation.",
                topics=("workflow",), should_summarize=True, provider="scoring",
                model="scoring-model", prompt_version="v2", request_hash="a" * 64,
                output_language="en",
            ),
            decision=ScoringDecision(threshold=7.0, final_should_summarize=True, model_disagrees=False),
            call=ProviderCallMetadata(provider="scoring", model="scoring-model", started_at=datetime(2026, 1, 1, tzinfo=UTC), finished_at=datetime(2026, 1, 1, tzinfo=UTC)),
        ), video_id="video-1", scoring_job_id="job-1", scoring_success_provenance="PRIMARY",
    )
    registry = EvidenceRegistry(items=(KnowledgeEvidence(evidence_id="e1", source=EvidenceSource.DESCRIPTION, excerpt="Selected evidence.", source_content_hash="d" * 64),))
    canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=read, schema_version="canonical-deep-analysis-input-v1", operation="deep-analysis",
        input_schema_version="input-v1", video_identity="video-1", transcript_identity="transcript-1",
        transcript_language="en", transcript_normalization_version="normalized-v1", evidence_registry_identity="registry-v1",
        selected_evidence=({"schema_version": "selected-evidence-projection-v1", "evidence_id": "e1", "source": "description", "excerpt": "Selected evidence."},),
        selection_policy_identity="selection-v1", coverage_policy_identity="coverage-v1", coverage_complete=False,
        output_language="en", knowledge_content_schema_version="knowledge-v1", prompt_version="prompt-v1", operation_version="operation-v1",
    )
    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(verified_scoring_read=read, canonical_input=canonical)
    profile = KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1", consent_mode=PayloadConsentMode.CLOUD_EXPLICIT,
        authorization_record_identity="kimi-test-consent-r2", named_provider_id=profile.provider_id,
        provider_kind=profile.provider_kind, payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint=profile.model_id,
    )
    authorized = runtime.authorize_payload(
        authoritative_input=admitted, evidence_registry=registry, payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=consent, video_title="Title", channel_name="Channel", published_at="2026-01-01T00:00:00Z",
        duration_seconds=42, source_language="en", public_description="Selected evidence.",
    )
    request = build_kimi_reference_request_projection(canonical_input=canonical, authorized_payload=authorized.payload, payload_consent=consent)
    execution = build_kimi_reference_execution_profile(
        request_projection=request,
        credential_execution_profile=CredentialExecutionProfileIdentityV1(
            schema_version="credential-execution-profile-v1", provider_id=profile.provider_id,
            execution_profile_identity="b" * 64,
        ),
    )
    return runtime, runtime.prepare_dispatch(
        authoritative_input=admitted, authorized_payload=authorized, request_projection=request,
        execution_profile=execution, payload_consent=consent,
        context_budget_profile=build_kimi_reference_context_budget(input_budget=1024),
        timeout_profile_identity=profile.timeout_profile_identity, fallback_policy_identity="c" * 64,
    )


def _content(evidence_id: str = "e1") -> dict[str, object]:
    statement = "The selected evidence contains a concrete useful explanation."
    return {
        "one_sentence_summary": statement, "summary_evidence_ids": [evidence_id],
        "why_it_matters": {"text": statement, "kind": "inference", "evidence_ids": [evidence_id]},
        "core_points": [{"text": statement, "kind": "fact", "evidence_ids": [evidence_id]}],
        "knowledge_graph": {"topics": ["workflow"]},
    }


class _Transport:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[dict[str, object], str, float, int]] = []

    def __call__(self, request: dict[str, object], credential: str, timeout: float, retries: int) -> object:
        self.calls.append((request, credential, timeout, retries))
        return self.response


def _response(*, content: str | None = None, model: str | None = None, request_id: str = "kimi_request_1", usage: object | None = None) -> dict[str, object]:
    return {
        "kind": "response",
        "response": {
            "id": request_id, "model": model or KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2.model_id,
            "choices": [{"message": {"content": content or json.dumps(_content())}, "finish_reason": "stop"}],
            "usage": usage if usage is not None else {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
        },
    }


def test_r2_request_a2_a3_timeout_and_selected_evidence_only() -> None:
    runtime, prepared = _prepared()
    transport = _Transport(_response())
    response = KimiDeepAnalysisProviderAdapter(transport=transport).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")

    request, credential, timeout, retries = transport.calls[0]
    assert request["model"] == "kimi-k3"
    assert request["response_format"] == {"type": "json_object"}
    assert request["stream"] is False
    assert request["max_completion_tokens"] == 4096
    assert request["reasoning_effort"] == "low"
    messages = request["messages"]
    assert isinstance(messages, list) and messages
    assert isinstance(messages[0], dict) and messages[0]["role"] == "system"
    assert "unselected full transcript" not in json.dumps(request)
    assert credential not in json.dumps(request)
    assert timeout == 120.0 and retries == 0
    assert prepared.envelope.timeout_profile_identity == "moonshot-chat-timeout-120s-v2"
    assert prepared.envelope.execution_profile.qualified_capability_profile_identity == "kimi-deep-analysis-reference-capabilities-r2-timeout-120s-v1"
    assert runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=response).success is not None


def test_provider_request_id_and_usage_are_observational() -> None:
    _, prepared = _prepared()
    first = KimiDeepAnalysisProviderAdapter(transport=_Transport(_response())).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    second = KimiDeepAnalysisProviderAdapter(transport=_Transport(_response(request_id="kimi_request_2", usage={"prompt_tokens": 999, "completion_tokens": 888, "total_tokens": 1887}))).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    assert first.provider_request_id != second.provider_request_id
    assert first.usage_evidence != second.usage_evidence
    assert first.provider_envelope_identity == second.provider_envelope_identity


def test_fenced_output_and_fabricated_evidence_stay_untrusted() -> None:
    runtime, prepared = _prepared()
    fenced = KimiDeepAnalysisProviderAdapter(transport=_Transport(_response(content="```json\n{}\n```"))).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    fenced_result = runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=fenced)
    assert fenced_result.failure is not None and fenced_result.failure.code.value == "STRUCTURED_OUTPUT_INVALID"

    fabricated = KimiDeepAnalysisProviderAdapter(transport=_Transport(_response(content=json.dumps(_content("fabricated"))))).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    fabricated_result = runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=fabricated)
    assert fabricated_result.failure is not None and fabricated_result.failure.code.value == "GROUNDING_INVALID"


def test_model_mismatch_and_malformed_envelope_reject_without_retry() -> None:
    runtime, prepared = _prepared()
    mismatch = KimiDeepAnalysisProviderAdapter(transport=_Transport(_response(model="other-model"))).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    result = runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=mismatch)
    assert result.failure is not None and result.failure.code.value == "PROVENANCE_INVALID"

    malformed = _Transport({"kind": "response", "response": {"model": "kimi-k3", "choices": []}})
    with pytest.raises(KimiDeepAnalysisProviderError) as raised:
        KimiDeepAnalysisProviderAdapter(transport=malformed).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    assert raised.value.failure.code.value == "PROVIDER_ENVELOPE_INVALID"
    assert len(malformed.calls) == 1 and malformed.calls[0][3] == 0


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"kind": "error", "status": 401, "category": "STATUS"}, "AUTH_INVALID"),
        ({"kind": "error", "status": 429, "category": "STATUS"}, "RATE_LIMITED"),
        ({"kind": "error", "status": 404, "category": "STATUS"}, "MODEL_UNAVAILABLE"),
        ({"kind": "error", "status": 503, "category": "STATUS"}, "PROVIDER_UNAVAILABLE"),
        ({"kind": "error", "category": "TIMEOUT"}, "TIMEOUT"),
    ],
)
def test_error_mapping_has_no_sdk_or_semantic_retry(response: object, expected: str) -> None:
    _, prepared = _prepared()
    transport = _Transport(response)
    with pytest.raises(KimiDeepAnalysisProviderError) as raised:
        KimiDeepAnalysisProviderAdapter(transport=transport).dispatch(prepared_dispatch=prepared, credential="sk-kimi-TASK016-FAKE-DO-NOT-PERSIST")
    assert raised.value.failure.code.value == expected
    assert len(transport.calls) == 1 and transport.calls[0][3] == 0


def test_credential_sentinel_never_enters_adapter_error_or_authority_surface() -> None:
    _, prepared = _prepared()
    sentinel = "sk-kimi-TASK016-FAKE-DO-NOT-PERSIST"
    transport = _Transport({"kind": "error", "category": "TIMEOUT"})
    adapter = KimiDeepAnalysisProviderAdapter(transport=transport)
    with pytest.raises(KimiDeepAnalysisProviderError) as raised:
        adapter.dispatch(prepared_dispatch=prepared, credential=sentinel)
    serialized = json.dumps(raised.value.failure.model_dump(mode="json"))
    assert sentinel not in repr(adapter)
    assert sentinel not in repr(raised.value)
    assert sentinel not in serialized
    assert sentinel not in repr(prepared.envelope)
    assert transport.calls[0][1] == sentinel


def test_adapter_exports_no_trust_mint_or_provider_fallback() -> None:
    import youtube_intel.kimi_deep_analysis as module

    assert "TrustedDeepAnalysisSuccess" not in vars(module)
    exported = " ".join(module.__all__).lower()
    assert "mint" not in exported and "openai" not in exported and "fallback" not in exported
