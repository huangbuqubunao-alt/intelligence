"""Provider-neutral Deep Analysis dispatch/validation boundary tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

import youtube_intel.deep_analysis_runtime as deep_analysis_runtime
from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    ContextBudgetProfileV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisContextAuthorityKind,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisFailureCode,
    DeepAnalysisMessageV1,
    DeepAnalysisModelIdentityClass,
    DeepAnalysisModelIdentityV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisProviderKind,
    DeepAnalysisRequestProjectionV1,
    DeepAnalysisStructuredOutputMode,
    DeepAnalysisStructuredOutputV1,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
    TrustedDeepAnalysisSuccess,
    UntrustedDeepAnalysisResponseV1,
    verify_trusted_deep_analysis_success,
)
from youtube_intel.deep_analysis_runtime import (
    DeepAnalysisRuntime,
    DeepAnalysisValidationResult,
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
from youtube_intel.scoring import VerifiedScoringRead


def _verified_read(request_hash: str = "c" * 64) -> VerifiedScoringRead:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8.0,
        reason="This result contains a concrete useful explanation of the score.",
        topics=("workflow",),
        should_summarize=True,
        provider="scoring-provider",
        model="scoring-model",
        prompt_version="scoring-prompt-v2",
        request_hash=request_hash,
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
        video_id="video-a",
        scoring_job_id="job-a",
        scoring_success_provenance="PRIMARY",
    )


def _canonical_input(
    read: VerifiedScoringRead, *, coverage_complete: bool = True
) -> CanonicalDeepAnalysisInputV1:
    return CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=read,
        schema_version="canonical-deep-analysis-input-v1",
        operation="deep-analysis",
        input_schema_version="deep-analysis-input-v1",
        video_identity="video-a",
        transcript_identity="d" * 64,
        transcript_language="en",
        transcript_normalization_version="transcript-v1",
        evidence_registry_identity="e" * 64,
        selected_evidence=(
            {
                "schema_version": "selected-evidence-projection-v1",
                "evidence_id": "e1",
                "source": "transcript_sample",
                "excerpt": "exact excerpt",
            },
        ),
        selection_policy_identity="selection-v1",
        coverage_policy_identity="coverage-v1",
        coverage_complete=coverage_complete,
        output_language="en",
        knowledge_content_schema_version="knowledge-result-v2",
        prompt_version="knowledge-prompt-v3",
        operation_version="deep-analysis-v1",
    )


def test_authoritative_input_requires_runtime_admission_not_identity_shape() -> None:
    verified_read = _verified_read()
    canonical = _canonical_input(verified_read)

    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=verified_read,
        canonical_input=canonical,
    )

    assert runtime.verify_authoritative_input(admitted)
    assert not runtime.verify_authoritative_input(canonical)
    assert not runtime.verify_authoritative_input(
        object.__new__(type(admitted))
    )


def test_known_scoring_hash_and_primary_do_not_admit_input() -> None:
    canonical = _canonical_input(_verified_read())

    runtime = DeepAnalysisRuntime()

    assert not runtime.verify_authoritative_input(canonical)
    with pytest.raises(ValueError, match="exact VerifiedScoringRead"):
        runtime.admit_verified_scoring_read(
            verified_scoring_read=object(), canonical_input=canonical
        )


def _registry() -> EvidenceRegistry:
    return EvidenceRegistry(
        items=(
            KnowledgeEvidence(
                evidence_id="e1",
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="exact excerpt",
                source_content_hash="f" * 64,
            ),
        )
    )


def _consent(scope: DeepAnalysisPayloadScope) -> PayloadConsentIdentityV1:
    return PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.LOCAL_ONLY,
        authorization_record_identity="local-policy-v1",
        named_provider_id="provider-a",
        provider_kind=DeepAnalysisProviderKind.LOCAL,
        payload_scope=scope,
        allowed_model_constraint="model-a",
    )


def test_selected_evidence_projection_is_runtime_owned_and_cannot_widen() -> None:
    verified_read = _verified_read()
    canonical = _canonical_input(verified_read)
    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=verified_read, canonical_input=canonical
    )

    projection = runtime.authorize_payload(
        authoritative_input=admitted,
        evidence_registry=_registry(),
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=_consent(DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY),
        video_title="Title",
        channel_name="Channel",
        published_at="2026-01-01T00:00:00Z",
        duration_seconds=42,
        source_language="en",
    )

    assert projection.payload.selected_evidence[0].evidence_id == "e1"
    assert projection.payload.transcript_text is None
    incomplete_read = _verified_read()
    incomplete = _canonical_input(incomplete_read, coverage_complete=False)
    incomplete_admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=incomplete_read, canonical_input=incomplete
    )
    with pytest.raises(ValueError, match="FULL_TRANSCRIPT"):
        runtime.authorize_payload(
            authoritative_input=incomplete_admitted,
            evidence_registry=_registry(),
            payload_scope=DeepAnalysisPayloadScope.FULL_TRANSCRIPT,
            payload_consent=_consent(DeepAnalysisPayloadScope.FULL_TRANSCRIPT),
            video_title="Title",
            channel_name="Channel",
            published_at="2026-01-01T00:00:00Z",
            duration_seconds=42,
            source_language="en",
            transcript_text="unrestricted transcript",
            transcript_content_hash="a" * 64,
            transcript_normalization_version="transcript-v1",
        )


def _credential() -> CredentialExecutionProfileIdentityV1:
    return CredentialExecutionProfileIdentityV1(
        schema_version="credential-execution-profile-v1",
        provider_id="provider-a",
        execution_profile_identity="b" * 64,
    )


def _prepared_dispatch(
    *,
    mode: DeepAnalysisStructuredOutputMode = DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT,
    fallback_policy_identity: str = "c" * 64,
) -> tuple[DeepAnalysisRuntime, PreparedDeepAnalysisDispatch]:
    read = _verified_read()
    canonical = _canonical_input(read)
    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=read, canonical_input=canonical
    )
    payload = runtime.authorize_payload(
        authoritative_input=admitted,
        evidence_registry=_registry(),
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=_consent(DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY),
        video_title="Title",
        channel_name="Channel",
        published_at="2026-01-01T00:00:00Z",
        duration_seconds=42,
        source_language="en",
    )
    structured: dict[str, object] = {
        "schema_version": "deep-analysis-structured-output-v1",
        "mode": mode,
        "dialect_id": "application-json",
        "dialect_version": "v1",
        "settings": {"strict": True},
    }
    if mode is DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA:
        structured["schema"] = {"type": "object"}
    if mode is DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN:
        structured["tools"] = ({"name": "return_knowledge", "parameters": {}},)
        structured["tool_choice"] = "return_knowledge"
    request = DeepAnalysisRequestProjectionV1(
        schema_version="deep-analysis-request-projection-v1",
        operation="deep-analysis",
        a1_identity=canonical.a1_identity,
        payload_consent_identity=_consent(DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY).identity,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        authorized_payload=payload.payload,
        provider_visible_messages=(
            DeepAnalysisMessageV1(
                schema_version="deep-analysis-message-v1", role="user", content="exact prompt"
            ),
        ),
        provider_visible_request_shape={"input": "prompt"},
        structured_output=DeepAnalysisStructuredOutputV1.model_validate(structured),
        generation_semantics={"temperature": 0.0, "max_output_tokens": 800},
        prompt_identity="knowledge-prompt-v3",
        knowledge_content_schema_identity="knowledge-result-v2",
        output_language="en",
        payload_projection_version="payload-v1",
    )
    execution = DeepAnalysisExecutionProfileV1(
        schema_version="deep-analysis-execution-profile-v1",
        a2_identity=request.a2_identity,
        provider_kind=DeepAnalysisProviderKind.LOCAL,
        provider_id="provider-a",
        adapter_identity="adapter-a",
        adapter_version="adapter-v1",
        sdk_or_http_client_version="client-v1",
        endpoint_deployment_profile_identity="deployment-a",
        model_selection=DeepAnalysisModelIdentityV1(
            schema_version="deep-analysis-model-identity-v1",
            model_id="model-a",
            identity_class=DeepAnalysisModelIdentityClass.IMMUTABLE,
            resolved_revision="sha256:" + "a" * 64,
        ),
        qualified_capability_profile_identity="qualified-a",
        context_authority_identity="context-a",
        generation_profile_identity="generation-a",
        idempotency_support_profile_identity="disabled-v1",
        credential_execution_profile=_credential(),
        structured_output_profile_identity="structured-a",
    )
    prepared = runtime.prepare_dispatch(
        authoritative_input=admitted,
        authorized_payload=payload,
        request_projection=request,
        execution_profile=execution,
        payload_consent=_consent(DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY),
        context_budget_profile=ContextBudgetProfileV1(
            schema_version="deep-analysis-context-budget-profile-v1",
            authority_kind=DeepAnalysisContextAuthorityKind.EXACT_LOCAL_TOKENIZER,
            authority_identity="context-a",
            context_window=8192,
            input_budget=100,
            structured_output_overhead_budget=100,
            tool_schema_overhead_budget=0,
            requested_output_budget=800,
        ),
        timeout_profile_identity="timeout-v1",
        fallback_policy_identity=fallback_policy_identity,
    )
    return runtime, prepared


def _content_payload(evidence_id: str = "e1") -> dict[str, object]:
    point = {"text": "Useful verified fact.", "kind": "fact", "evidence_ids": [evidence_id]}
    return {
        "one_sentence_summary": "This result contains a concrete useful explanation of the score.",
        "summary_evidence_ids": [evidence_id],
        "why_it_matters": {"text": "This result contains a concrete useful explanation of the score.", "kind": "inference", "evidence_ids": [evidence_id]},
        "core_points": [point],
        "knowledge_graph": {"topics": ["workflow"]},
    }


def _response(
    prepared: PreparedDeepAnalysisDispatch,
    *,
    payload: object | None = None,
    model_id: str = "model-a",
) -> UntrustedDeepAnalysisResponseV1:
    envelope = prepared.envelope
    mode = envelope.request_projection.structured_output.mode
    semantic_payload = payload
    if semantic_payload is None:
        semantic_payload = b'{"one_sentence_summary":"This result contains a concrete useful explanation of the score.","summary_evidence_ids":["e1"],"why_it_matters":{"text":"This result contains a concrete useful explanation of the score.","kind":"inference","evidence_ids":["e1"]},"core_points":[{"text":"This result contains a concrete useful explanation of the score.","kind":"fact","evidence_ids":["e1"]}],"knowledge_graph":{"topics":["workflow"]}}'
    metadata: dict[str, object] = {
        "schema_version": "deep-analysis-response-metadata-v1",
        "dispatch_identity": envelope.semantic_identity,
        "provider_id": "provider-a",
        "adapter_identity": "adapter-a",
        "adapter_version": "adapter-v1",
        "endpoint_deployment_profile_identity": "deployment-a",
        "model_id": model_id,
        "resolved_revision": "sha256:" + "a" * 64,
        "structured_output_mode": mode.value,
        "a1_identity": envelope.a1_identity,
        "a2_identity": envelope.a2_identity,
        "a3_identity": envelope.a3_identity,
        "scoring_request_hash": envelope.canonical_input.scoring_request_hash,
        "validation_policy_identity": "deep-analysis-validation-policy-v1",
    }
    if mode is DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN:
        metadata["tool_name"] = "return_knowledge"
    return UntrustedDeepAnalysisResponseV1(
        schema_version="untrusted-deep-analysis-response-v1",
        expected_dispatch_identity=envelope.semantic_identity,
        provider_envelope_bytes=b'{"documented":"envelope"}',
        structured_payload=semantic_payload,
        structured_output_mode=mode,
        delivery_certainty="CONFIRMED",
        response_metadata=metadata,
    )


def test_finalizer_mints_only_after_runtime_validation_happy_path() -> None:
    runtime, prepared = _prepared_dispatch()

    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared,
        response=_response(prepared),
    )

    assert result.failure is None
    assert result.success is not None
    assert verify_trusted_deep_analysis_success(result.success)


def _with_metadata(response: UntrustedDeepAnalysisResponseV1, **changes: object) -> UntrustedDeepAnalysisResponseV1:
    data = response.model_dump(mode="python")
    assert isinstance(response.response_metadata, Mapping)
    data["response_metadata"] = {**response.response_metadata, **changes}
    return UntrustedDeepAnalysisResponseV1.model_validate(data)


def _failure_code(result: DeepAnalysisValidationResult) -> DeepAnalysisFailureCode:
    assert result.success is None
    assert result.failure is not None
    return result.failure.code


def test_unbound_or_wrong_dispatch_and_model_fail_before_semantics() -> None:
    runtime, prepared_a = _prepared_dispatch()
    _, prepared_b = _prepared_dispatch(fallback_policy_identity="d" * 64)
    finalizer = runtime.validation_finalizer()

    forged = _response(prepared_a)
    assert _failure_code(finalizer.finalize(prepared_dispatch=object(), response=forged)) is DeepAnalysisFailureCode.PROVENANCE_INVALID
    assert _failure_code(finalizer.finalize(prepared_dispatch=prepared_a, response=_response(prepared_b))) is DeepAnalysisFailureCode.PROVENANCE_INVALID
    assert _failure_code(finalizer.finalize(prepared_dispatch=prepared_a, response=_response(prepared_a, model_id="model-b"))) is DeepAnalysisFailureCode.PROVENANCE_INVALID


@pytest.mark.parametrize(
    "payload",
    [
        b"```json\n{}\n```",
        b"prose {\"one_sentence_summary\": \"x\"}",
        b"{} trailing prose",
        b"{}{}",
        b"{",
        b"",
    ],
)
def test_strict_json_never_repairs_or_extracts(payload: bytes) -> None:
    runtime, prepared = _prepared_dispatch()

    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=_response(prepared, payload=payload)
    )

    assert result.success is None
    assert _failure_code(result) is DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID


def test_schema_and_tool_outputs_remain_untrusted_and_grounded() -> None:
    schema_runtime, schema_prepared = _prepared_dispatch(
        mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA
    )
    schema_result = schema_runtime.validation_finalizer().finalize(
        prepared_dispatch=schema_prepared,
        response=_response(schema_prepared, payload=_content_payload("fabricated")),
    )
    assert _failure_code(schema_result) is DeepAnalysisFailureCode.GROUNDING_INVALID

    tool_runtime, tool_prepared = _prepared_dispatch(
        mode=DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN
    )
    wrong_tool = _with_metadata(_response(tool_prepared, payload=_content_payload()), tool_name="other")
    tool_result = tool_runtime.validation_finalizer().finalize(
        prepared_dispatch=tool_prepared, response=wrong_tool
    )
    assert _failure_code(tool_result) is DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID
    fabricated_tool = tool_runtime.validation_finalizer().finalize(
        prepared_dispatch=tool_prepared,
        response=_response(tool_prepared, payload=_content_payload("outside-selected")),
    )
    assert _failure_code(fabricated_tool) is DeepAnalysisFailureCode.GROUNDING_INVALID


def test_scoring_provenance_mismatch_and_success_fabrication_fail_closed() -> None:
    runtime, prepared = _prepared_dispatch()
    bad_provenance = _with_metadata(
        _response(prepared), scoring_request_hash="d" * 64
    )
    assert _failure_code(runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=bad_provenance
    )) is DeepAnalysisFailureCode.PROVENANCE_INVALID

    result = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=_response(prepared)
    )
    assert result.success is not None
    with pytest.raises(TypeError):
        __import__("copy").copy(result.success)
    fabricated = object.__new__(TrustedDeepAnalysisSuccess)
    object.__setattr__(fabricated, "_content_identity", result.success.content_identity)
    object.__setattr__(fabricated, "_cache_identity", result.success.cache_identity)
    object.__setattr__(fabricated, "_provenance_identity", result.success.provenance_identity)
    object.__setattr__(fabricated, "_sealed", True)
    assert not verify_trusted_deep_analysis_success(fabricated)


def test_final_validation_policy_identity_is_provenance_not_a_response_claim() -> None:
    runtime, prepared = _prepared_dispatch()
    wrong_policy = _with_metadata(
        _response(prepared), validation_policy_identity="other-policy-v1"
    )

    assert _failure_code(runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=wrong_policy
    )) is DeepAnalysisFailureCode.PROVENANCE_INVALID


def test_runtime_module_exposes_no_success_registration_or_generic_mint() -> None:
    names = set(vars(deep_analysis_runtime))
    assert "_record_finalized_success" not in names
    assert not any(name in names for name in {"mint_success", "register_success"})
