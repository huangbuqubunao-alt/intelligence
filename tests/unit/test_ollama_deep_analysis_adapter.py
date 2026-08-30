"""Contract tests for the qualified loopback Ollama Deep Analysis adapter."""

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
from youtube_intel.deep_analysis_runtime import DeepAnalysisRuntime
from youtube_intel.domain import (
    EvidenceRegistry,
    EvidenceSource,
    KnowledgeEvidence,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.ollama_deep_analysis import (
    OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE,
    OllamaDeepAnalysisProviderAdapter,
    OllamaDeepAnalysisProviderError,
    build_ollama_local_context_budget,
    build_ollama_local_execution_profile,
    build_ollama_local_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead


def _prepared() -> tuple[DeepAnalysisRuntime, object]:
    read = VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=ScoreResult(
                schema_version="score-result-v2", score=8.0, reason="This result contains a concrete useful explanation of the score.",
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
    consent = PayloadConsentIdentityV1(schema_version="payload-consent-identity-v1", consent_mode=PayloadConsentMode.LOCAL_ONLY,
        authorization_record_identity="local-test-v1", named_provider_id=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.provider_id,
        provider_kind=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.provider_kind, payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.model_id)
    payload = runtime.authorize_payload(authoritative_input=admitted, evidence_registry=registry,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY, payload_consent=consent,
        video_title="Title", channel_name="Channel", published_at="2026-01-01T00:00:00Z", duration_seconds=42, source_language="en")
    request = build_ollama_local_request_projection(canonical_input=canonical, authorized_payload=payload.payload, payload_consent=consent)
    execution = build_ollama_local_execution_profile(request_projection=request, credential_execution_profile=CredentialExecutionProfileIdentityV1(schema_version="credential-execution-profile-v1", provider_id=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.provider_id, execution_profile_identity="b" * 64))
    return runtime, runtime.prepare_dispatch(authoritative_input=admitted, authorized_payload=payload, request_projection=request,
        execution_profile=execution, payload_consent=consent, context_budget_profile=build_ollama_local_context_budget(input_budget=1024),
        timeout_profile_identity=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.timeout_profile_identity, fallback_policy_identity="c" * 64)


def _content() -> dict[str, object]:
    statement = "This result contains a concrete useful explanation."
    return {"one_sentence_summary": statement, "summary_evidence_ids": ["e1"],
        "why_it_matters": {"text": statement, "kind": "inference", "evidence_ids": ["e1"]},
        "core_points": [{"text": statement, "kind": "fact", "evidence_ids": ["e1"]}],
        "knowledge_graph": {"topics": ["workflow"]}}


class _Transport:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[dict[str, object], float]] = []

    def __call__(self, request: dict[str, object], timeout_seconds: float) -> object:
        self.calls.append((request, timeout_seconds))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def _response(*, content: str | None = None, model: str | None = None) -> dict[str, object]:
    return {"model": model or OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.model_id, "done": True,
        "done_reason": "stop", "message": {"role": "assistant", "content": content or json.dumps(_content())},
        "prompt_eval_count": 12, "eval_count": 34}


def test_request_a2_a3_identity_timeout_no_retry_and_finalizer_ownership() -> None:
    runtime, prepared = _prepared()
    transport = _Transport(_response())
    response = OllamaDeepAnalysisProviderAdapter(transport=transport).dispatch(prepared_dispatch=prepared)
    request, timeout = transport.calls[0]
    assert request["model"] == OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.model_id
    assert request["format"] == "json" and request["stream"] is False and request["think"] is False
    assert request["options"] == {"temperature": 0, "seed": 0, "num_ctx": 8192, "num_predict": 1024}
    assert timeout == 120.0
    assert response.response_metadata is not None
    assert response.delivery_certainty == "CONFIRMED"
    assert runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=response).success is not None


def test_fenced_output_is_untrusted_and_never_repaired() -> None:
    runtime, prepared = _prepared()
    response = OllamaDeepAnalysisProviderAdapter(transport=_Transport(_response(content="```json\\n{}\\n```"))).dispatch(prepared_dispatch=prepared)
    result = runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=response)
    assert result.failure is not None and result.failure.code.value == "STRUCTURED_OUTPUT_INVALID"


def test_model_mismatch_remains_untrusted_for_finalizer_provenance_rejection() -> None:
    runtime, prepared = _prepared()
    response = OllamaDeepAnalysisProviderAdapter(transport=_Transport(_response(model="other-model"))).dispatch(prepared_dispatch=prepared)
    result = runtime.validation_finalizer().finalize(prepared_dispatch=prepared, response=response)
    assert result.failure is not None and result.failure.code.value == "PROVENANCE_INVALID"


def test_malformed_response_and_transport_failure_do_not_retry_or_fallback() -> None:
    _, prepared = _prepared()
    malformed = _Transport({"model": OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.model_id, "done": True, "message": {"content": 1}})
    with pytest.raises(OllamaDeepAnalysisProviderError) as raised:
        OllamaDeepAnalysisProviderAdapter(transport=malformed).dispatch(prepared_dispatch=prepared)
    assert raised.value.failure.code.value == "PROVIDER_ENVELOPE_INVALID" and len(malformed.calls) == 1
    failed = _Transport(TimeoutError())
    with pytest.raises(OllamaDeepAnalysisProviderError) as raised:
        OllamaDeepAnalysisProviderAdapter(transport=failed).dispatch(prepared_dispatch=prepared)
    assert raised.value.failure.code.value == "TIMEOUT" and len(failed.calls) == 1


def test_adapter_exports_no_trust_mint_or_cloud_fallback() -> None:
    import youtube_intel.ollama_deep_analysis as module
    assert "TrustedDeepAnalysisSuccess" not in vars(module)
    assert "cloud" not in " ".join(module.__all__).lower()
