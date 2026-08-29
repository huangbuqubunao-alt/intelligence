"""Provider-neutral Deep Analysis P0 contract tests (RED before GREEN)."""

from __future__ import annotations

import copy
import pickle
from datetime import UTC, datetime

import pytest

from youtube_intel.deep_analysis_contracts import (
    AuthorizedProviderPayloadProjectionV1,
    CacheEligibility,
    CanonicalDeepAnalysisInputV1,
    ContextBudgetProfileV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisCacheIdentityV1,
    DeepAnalysisContextAuthorityKind,
    DeepAnalysisDispatchEnvelopeV1,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisFailureCode,
    DeepAnalysisFailureStage,
    DeepAnalysisFailureV1,
    DeepAnalysisFallbackEdgeV1,
    DeepAnalysisFallbackNodeV1,
    DeepAnalysisFallbackPolicyV1,
    DeepAnalysisMessageV1,
    DeepAnalysisModelIdentityClass,
    DeepAnalysisModelIdentityV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisProviderCapabilities,
    DeepAnalysisProviderKind,
    DeepAnalysisRequestProjectionV1,
    DeepAnalysisStructuredOutputMode,
    DeepAnalysisStructuredOutputV1,
    DeepAnalysisValidationPolicyIdentityV1,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
    SelectedEvidenceProjectionV1,
    TrustedDeepAnalysisSuccess,
    UntrustedDeepAnalysisResponseV1,
    _admit_authoritative_input_for_finalizer,
    _mint_trusted_deep_analysis_success_for_finalizer,
    build_cache_decision,
    canonical_dacs1_bytes,
    select_fallback_edge,
    validated_payload_identity,
    verify_authoritative_deep_analysis_input,
    verify_trusted_deep_analysis_success,
)
from youtube_intel.domain import (
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.scoring import VerifiedScoringRead


def test_dacs1_is_versioned_canonical_utf8_json() -> None:
    assert canonical_dacs1_bytes(
        {"schema_version": "dacs-test-v1", "z": None, "a": [True, "中"]}
    ) == b'{"a":[true,"\xe4\xb8\xad"],"schema_version":"dacs-test-v1","z":null}'


def test_provider_kind_is_finite() -> None:
    assert DeepAnalysisProviderKind.LOCAL.value == "LOCAL"
    with pytest.raises(ValueError):
        DeepAnalysisProviderKind("OTHER")


def _credential() -> CredentialExecutionProfileIdentityV1:
    return CredentialExecutionProfileIdentityV1(
        schema_version="credential-execution-profile-v1",
        provider_id="provider-a",
        execution_profile_identity="c" * 64,
    )


def _node(model: str = "model-a") -> DeepAnalysisFallbackNodeV1:
    return DeepAnalysisFallbackNodeV1(
        schema_version="deep-analysis-fallback-node-v1",
        provider_id="provider-a",
        provider_kind=DeepAnalysisProviderKind.LOCAL,
        adapter_identity="adapter-a",
        endpoint_deployment_profile_identity="deployment-a",
        model_selection=DeepAnalysisModelIdentityV1(
            schema_version="deep-analysis-model-identity-v1",
            model_id=model,
            identity_class=DeepAnalysisModelIdentityClass.IMMUTABLE,
            resolved_revision="sha256:" + "a" * 64,
        ),
        credential_execution_profile_identity=_credential().identity,
        structured_output_profile_identity="structured-a",
        generation_profile_identity="generation-a",
        context_authority_identity="context-a",
        qualified_capability_profile_identity="qualified-a",
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
    )


def test_model_identity_and_credential_contract_fail_closed() -> None:
    with pytest.raises(ValueError):
        DeepAnalysisModelIdentityV1(
            schema_version="deep-analysis-model-identity-v1",
            model_id="floating",
            identity_class=DeepAnalysisModelIdentityClass.FLOATING,
            resolved_revision="sha256:" + "a" * 64,
        )
    with pytest.raises(Exception):
        CredentialExecutionProfileIdentityV1.model_validate(
            {
                "schema_version": "credential-execution-profile-v1",
                "provider_id": "provider-a",
                "execution_profile_identity": "c" * 64,
                "api_key": "do-not-accept",
            }
        )


def test_fallback_policy_rejects_cycles_and_ambiguous_edges() -> None:
    node_a = _node("model-a")
    node_b = _node("model-b")
    edge_ab = DeepAnalysisFallbackEdgeV1(
        schema_version="deep-analysis-fallback-edge-v1",
        source_node_identity=node_a.identity,
        destination_node_identity=node_b.identity,
        allowed_failure_codes=(DeepAnalysisFailureCode.TIMEOUT,),
        source_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        destination_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_scope_authorization_identity="scope-auth",
        cloud_consent_authorization_identity="consent-auth",
        destination_credential_execution_profile_identity=_credential().identity,
    )
    edge_ba = DeepAnalysisFallbackEdgeV1.model_validate(
        {
            **edge_ab.model_dump(),
            "source_node_identity": node_b.identity,
            "destination_node_identity": node_a.identity,
        }
    )
    with pytest.raises(ValueError, match="acyclic"):
        DeepAnalysisFallbackPolicyV1(
            schema_version="deep-analysis-fallback-policy-v1",
            start_node_identity=node_a.identity,
            nodes=(node_a, node_b),
            edges=(edge_ab, edge_ba),
        )


def test_trusted_success_cannot_be_directly_fabricated() -> None:
    with pytest.raises(ValueError, match="only be minted"):
        TrustedDeepAnalysisSuccess(content_identity="a" * 64, cache_identity="b" * 64, sentinel=object())


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
    outcome = ScoringOutcome(
        result=result,
        decision=ScoringDecision(
            threshold=7.0, final_should_summarize=True, model_disagrees=False
        ),
        call=ProviderCallMetadata(
            provider="scoring-provider",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, tzinfo=UTC),
            model="scoring-model",
        ),
    )
    return VerifiedScoringRead(
        scoring_outcome=outcome,
        video_id="video-a",
        scoring_job_id="job-a",
        scoring_success_provenance="PRIMARY",
    )


def _canonical_input() -> CanonicalDeepAnalysisInputV1:
    return CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=_verified_read(),
        schema_version="canonical-deep-analysis-input-v1",
        operation="deep-analysis",
        input_schema_version="deep-analysis-input-v1",
        video_identity="video-a",
        transcript_identity="d" * 64,
        transcript_language="en",
        transcript_normalization_version="transcript-v1",
        evidence_registry_identity="e" * 64,
        selected_evidence=(
            {"schema_version": "selected-evidence-projection-v1", "evidence_id": "e1", "source": "transcript_sample", "excerpt": "exact excerpt"},
        ),
        selection_policy_identity="selection-v1",
        coverage_policy_identity="coverage-v1",
        coverage_complete=True,
        output_language="zh-CN",
        knowledge_content_schema_version="knowledge-result-v2",
        prompt_version="knowledge-prompt-v3",
        operation_version="deep-analysis-v1",
    )


def _request_and_execution() -> tuple[CanonicalDeepAnalysisInputV1, DeepAnalysisRequestProjectionV1, DeepAnalysisExecutionProfileV1]:
    input_value = _canonical_input()
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.LOCAL_ONLY,
        authorization_record_identity="local-policy-v1",
        named_provider_id="provider-a",
        provider_kind=DeepAnalysisProviderKind.LOCAL,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint="model-a",
    )
    payload = AuthorizedProviderPayloadProjectionV1(
        schema_version="authorized-provider-payload-projection-v1",
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        output_language="zh-CN",
        video_title="Title",
        channel_name="Channel",
        published_at="2026-01-01T00:00:00Z",
        duration_seconds=42,
        source_language="en",
        selected_evidence=(
            SelectedEvidenceProjectionV1(
                schema_version="selected-evidence-projection-v1",
                evidence_id="e1",
                source="transcript_sample",
                excerpt="exact excerpt",
            ),
        ),
    )
    request = DeepAnalysisRequestProjectionV1(
        schema_version="deep-analysis-request-projection-v1",
        operation="deep-analysis",
        a1_identity=input_value.a1_identity,
        payload_consent_identity=consent.identity,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        authorized_payload=payload,
        provider_visible_messages=(
            DeepAnalysisMessageV1(
                schema_version="deep-analysis-message-v1",
                role="system",
                content="produce Chinese JSON",
            ),
            DeepAnalysisMessageV1(
                schema_version="deep-analysis-message-v1",
                role="user",
                content="exact excerpt",
            ),
        ),
        provider_visible_request_shape={"messages": "chat", "input_field": "messages"},
        structured_output=DeepAnalysisStructuredOutputV1.model_validate(
            {
                "schema_version": "deep-analysis-structured-output-v1",
                "mode": DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA,
                "dialect_id": "json-schema",
                "dialect_version": "2020-12",
                "settings": {"strict": True},
                "schema": {
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                },
            }
        ),
        generation_semantics={"temperature": 0.0, "max_output_tokens": 800},
        prompt_identity="knowledge-prompt-v3",
        knowledge_content_schema_identity="knowledge-result-v2",
        output_language="zh-CN",
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
            schema_version="deep-analysis-model-identity-v1", model_id="model-a",
            identity_class=DeepAnalysisModelIdentityClass.IMMUTABLE,
            resolved_revision="sha256:" + "a" * 64,
        ),
        qualified_capability_profile_identity="qualified-a",
        context_authority_identity="context-a",
        generation_profile_identity="generation-a",
        idempotency_support_profile_identity="idempotency-disabled-v1",
        credential_execution_profile=_credential(),
        structured_output_profile_identity="structured-a",
    )
    return input_value, request, execution


def test_a1_binds_verified_request_hash_not_scoring_provenance() -> None:
    canonical = _canonical_input()
    assert canonical.scoring_request_hash == "c" * 64
    assert canonical.scoring_success_provenance == "PRIMARY"
    with pytest.raises(ValueError, match="VerifiedScoringRead"):
        CanonicalDeepAnalysisInputV1.model_validate(canonical.model_dump())
    changed = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=_verified_read("f" * 64),
        **{key: value for key, value in canonical.model_dump().items() if key not in {"scoring_request_hash", "scoring_success_provenance"}},
    )
    assert changed.a1_identity != canonical.a1_identity
    with pytest.raises(ValueError, match="model_copy"):
        canonical.model_copy(update={})


@pytest.mark.parametrize(
    "field, changed_value",
    [
        ("provider_visible_messages", ({"schema_version": "deep-analysis-message-v1", "role": "user", "content": "changed"},)),
        ("provider_visible_request_shape", {"messages": "responses"}),
        ("generation_semantics", {"temperature": 0.2, "max_output_tokens": 800}),
        ("structured_output", {"schema_version": "deep-analysis-structured-output-v1", "mode": DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA, "dialect_id": "json-schema", "dialect_version": "2020-12", "settings": {"strict": False}, "schema": {"type": "object"}}),
    ],
)
def test_a2_changes_for_every_provider_visible_semantic_mutation(field: str, changed_value: object) -> None:
    _, request, _ = _request_and_execution()
    changed = DeepAnalysisRequestProjectionV1.model_validate(
        {**request.model_dump(by_alias=True), field: changed_value}
    )
    assert changed.a2_identity != request.a2_identity


@pytest.mark.parametrize("field, changed_value", [("provider_id", "provider-b"), ("endpoint_deployment_profile_identity", "deployment-b"), ("adapter_version", "adapter-v2")])
def test_a3_changes_for_execution_profile_mutations(field: str, changed_value: str) -> None:
    _, _, execution = _request_and_execution()
    changed = DeepAnalysisExecutionProfileV1.model_validate(
        {**execution.model_dump(), field: changed_value}
    )
    assert changed.a3_identity != execution.a3_identity


def test_cache_identity_binds_a1_a2_a3_and_validation_policy() -> None:
    canonical, request, execution = _request_and_execution()
    policy = DeepAnalysisValidationPolicyIdentityV1(
        schema_version="deep-analysis-validation-policy-identity-v1",
        strict_json_policy_version="json-v1", schema_policy_version="schema-v1",
        domain_policy_version="domain-v1", grounding_policy_version="grounding-v1",
        kg2_policy_version="kg2-v1", language_policy_version="language-v1",
        provenance_policy_version="provenance-v1",
    )
    decision = build_cache_decision(canonical_input=canonical, request_projection=request, execution_profile=execution, validation_policy=policy)
    assert decision.eligibility is CacheEligibility.ELIGIBLE
    assert decision.cache_identity is not None
    base = decision.cache_identity.identity
    assert DeepAnalysisCacheIdentityV1(schema_version="deep-analysis-cache-identity-v1", a1_identity=canonical.a1_identity, a2_identity=request.a2_identity, a3_identity=execution.a3_identity, validation_policy_identity="f" * 64).identity != base


def test_dispatch_envelope_is_semantic_and_has_no_observational_fields() -> None:
    canonical, request, execution = _request_and_execution()
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1", consent_mode=PayloadConsentMode.LOCAL_ONLY,
        authorization_record_identity="local-policy-v1", named_provider_id="provider-a",
        provider_kind=DeepAnalysisProviderKind.LOCAL, payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint="model-a",
    )
    envelope = DeepAnalysisDispatchEnvelopeV1(
        schema_version="deep-analysis-dispatch-envelope-v1", canonical_input=canonical,
        request_projection=request, execution_profile=execution, payload_consent=consent,
        context_budget_profile=ContextBudgetProfileV1(schema_version="deep-analysis-context-budget-profile-v1", authority_kind=DeepAnalysisContextAuthorityKind.EXACT_LOCAL_TOKENIZER, authority_identity="context-a", context_window=8192, input_budget=100, structured_output_overhead_budget=100, tool_schema_overhead_budget=0, requested_output_budget=800),
        timeout_profile_identity="timeout-v1", fallback_policy_identity="a" * 64,
        prompt_identity="knowledge-prompt-v3", schema_identity="knowledge-result-v2",
    )
    assert envelope.a1_identity == canonical.a1_identity
    with pytest.raises(Exception):
        DeepAnalysisDispatchEnvelopeV1.model_validate({**envelope.model_dump(), "provider_request_id": "observational"})
    for duplicated_field, value in (
        ("scoring_request_hash", "f" * 64),
        ("structured_output_mode", DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT),
        ("payload_scope", DeepAnalysisPayloadScope.FULL_TRANSCRIPT),
    ):
        with pytest.raises(ValueError):
            DeepAnalysisDispatchEnvelopeV1.model_validate(
                {**envelope.model_dump(), duplicated_field: value}
            )


def test_fallback_adversarial_matrix_rejects_self_long_cycle_duplicate_and_ambiguous_edges() -> None:
    node_a, node_b, node_c = _node("model-a"), _node("model-b"), _node("model-c")

    def edge(source: DeepAnalysisFallbackNodeV1, destination: DeepAnalysisFallbackNodeV1, code: DeepAnalysisFailureCode) -> DeepAnalysisFallbackEdgeV1:
        return DeepAnalysisFallbackEdgeV1(
            schema_version="deep-analysis-fallback-edge-v1", source_node_identity=source.identity,
            destination_node_identity=destination.identity, allowed_failure_codes=(code,),
            source_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
            destination_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
            payload_scope_authorization_identity="scope-auth", cloud_consent_authorization_identity="consent-auth",
            destination_credential_execution_profile_identity=_credential().identity,
        )

    with pytest.raises(ValueError, match="self-loop"):
        DeepAnalysisFallbackPolicyV1(schema_version="deep-analysis-fallback-policy-v1", start_node_identity=node_a.identity, nodes=(node_a,), edges=(edge(node_a, node_a, DeepAnalysisFailureCode.TIMEOUT),))
    with pytest.raises(ValueError, match="acyclic"):
        DeepAnalysisFallbackPolicyV1(schema_version="deep-analysis-fallback-policy-v1", start_node_identity=node_a.identity, nodes=(node_a, node_b, node_c), edges=(edge(node_a, node_b, DeepAnalysisFailureCode.TIMEOUT), edge(node_b, node_c, DeepAnalysisFailureCode.RATE_LIMITED), edge(node_c, node_b, DeepAnalysisFailureCode.QUOTA_EXCEEDED)))
    with pytest.raises(ValueError, match="duplicate semantic"):
        DeepAnalysisFallbackPolicyV1(schema_version="deep-analysis-fallback-policy-v1", start_node_identity=node_a.identity, nodes=(node_a, _node("model-a")))
    with pytest.raises(ValueError, match="ambiguous"):
        DeepAnalysisFallbackPolicyV1(schema_version="deep-analysis-fallback-policy-v1", start_node_identity=node_a.identity, nodes=(node_a, node_b, node_c), edges=(edge(node_a, node_b, DeepAnalysisFailureCode.TIMEOUT), edge(node_a, node_c, DeepAnalysisFailureCode.TIMEOUT)))


def test_valid_fallback_graph_has_one_matching_edge_and_bounded_attempts() -> None:
    node_a, node_b, node_c = _node("model-a"), _node("model-b"), _node("model-c")
    edge_ab = DeepAnalysisFallbackEdgeV1(
        schema_version="deep-analysis-fallback-edge-v1", source_node_identity=node_a.identity,
        destination_node_identity=node_b.identity, allowed_failure_codes=(DeepAnalysisFailureCode.TIMEOUT,),
        source_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        destination_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_scope_authorization_identity="scope-auth", cloud_consent_authorization_identity="consent-auth",
        destination_credential_execution_profile_identity=_credential().identity,
    )
    edge_bc = DeepAnalysisFallbackEdgeV1(
        schema_version="deep-analysis-fallback-edge-v1", source_node_identity=node_b.identity,
        destination_node_identity=node_c.identity, allowed_failure_codes=(DeepAnalysisFailureCode.RATE_LIMITED,),
        source_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        destination_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_scope_authorization_identity="scope-auth", cloud_consent_authorization_identity="consent-auth",
        destination_credential_execution_profile_identity=_credential().identity,
    )
    policy = DeepAnalysisFallbackPolicyV1(schema_version="deep-analysis-fallback-policy-v1", start_node_identity=node_a.identity, nodes=(node_c, node_a, node_b), edges=(edge_bc, edge_ab))
    failure = DeepAnalysisFailureV1(schema_version="deep-analysis-failure-v1", code=DeepAnalysisFailureCode.TIMEOUT, stage=DeepAnalysisFailureStage.TRANSPORT)
    assert select_fallback_edge(policy=policy, current_node_identity=node_a.identity, failure=failure) == edge_ab
    assert policy.maximum_semantic_attempts == 3


def test_floating_model_is_explicitly_cache_ineligible() -> None:
    canonical, request, execution = _request_and_execution()
    floating_execution = DeepAnalysisExecutionProfileV1.model_validate(
        {
            **execution.model_dump(),
            "model_selection": {"schema_version": "deep-analysis-model-identity-v1", "model_id": "floating", "identity_class": "FLOATING", "resolved_revision": None},
        }
    )
    policy = DeepAnalysisValidationPolicyIdentityV1(schema_version="deep-analysis-validation-policy-identity-v1", strict_json_policy_version="json-v1", schema_policy_version="schema-v1", domain_policy_version="domain-v1", grounding_policy_version="grounding-v1", kg2_policy_version="kg2-v1", language_policy_version="language-v1", provenance_policy_version="provenance-v1")
    decision = build_cache_decision(canonical_input=canonical, request_projection=request, execution_profile=floating_execution, validation_policy=policy)
    assert decision.eligibility is CacheEligibility.INELIGIBLE_FLOATING_MODEL
    assert decision.cache_identity is None


def test_untrusted_response_identity_preserves_mode_specific_bytes() -> None:
    raw = b'{"summary":"exact"}'
    response = UntrustedDeepAnalysisResponseV1(
        schema_version="untrusted-deep-analysis-response-v1", expected_dispatch_identity="a" * 64,
        provider_envelope_bytes=b'{"response":1}', structured_payload=raw,
        structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
        delivery_certainty="CONFIRMED",
    )
    assert response.structured_payload_identity == validated_payload_identity(mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE, payload=raw)
    assert not hasattr(response, "to_trusted")


def test_contract_golden_identities_are_pinned() -> None:
    canonical, request, execution = _request_and_execution()
    node = _node()
    fallback = DeepAnalysisFallbackPolicyV1(
        schema_version="deep-analysis-fallback-policy-v1",
        start_node_identity=node.identity,
        nodes=(node,),
    )
    policy = DeepAnalysisValidationPolicyIdentityV1(schema_version="deep-analysis-validation-policy-identity-v1", strict_json_policy_version="json-v1", schema_policy_version="schema-v1", domain_policy_version="domain-v1", grounding_policy_version="grounding-v1", kg2_policy_version="kg2-v1", language_policy_version="language-v1", provenance_policy_version="provenance-v1")
    cache = build_cache_decision(canonical_input=canonical, request_projection=request, execution_profile=execution, validation_policy=policy)
    assert canonical.a1_identity == "42801915abea400227872c38c6a7eadac84d4c5b2e39d881898811dc50be205b"
    assert request.a2_identity == "3400e1d9ea227526315398c3312e446d6bb29094801c38160ba724e1c2c0db61"
    assert execution.a3_identity == "2e7b5659deb4002a613f245fc20824d92a74490d8adf7cac4eb14c8c9502109f"
    assert node.identity == "0cd62c005c9c4048e1dfcf3c6fcbdf09a1d215cf77ea5df2569e99114ea93cf1"
    assert fallback.identity == "cc2e9f10d65b011a48b66ea734aa64f90b1494bdd4ef502358ad56229cbfa540"
    assert cache.cache_identity is not None
    assert cache.cache_identity.identity == "776bd26cd65b78fbebef16a41b438b4aec26643cb32fbeac7f6f4a77edad8998"


def test_unknown_output_mode_bad_provenance_and_auto_consent_fail_closed() -> None:
    with pytest.raises(ValueError):
        DeepAnalysisStructuredOutputMode("AUTO")
    bad_read = _verified_read()
    bad_read = VerifiedScoringRead(
        scoring_outcome=bad_read.scoring_outcome,
        video_id=bad_read.video_id,
        scoring_job_id=bad_read.scoring_job_id,
        scoring_success_provenance=None,
    )
    with pytest.raises(ValueError, match="provenance"):
        CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
            verified_scoring_read=bad_read,
            **{key: value for key, value in _canonical_input().model_dump().items() if key not in {"scoring_request_hash", "scoring_success_provenance"}},
        )
    with pytest.raises(ValueError):
        PayloadConsentMode("auto")


def test_declared_capability_is_not_qualified_or_trusted_output() -> None:
    capabilities = DeepAnalysisProviderCapabilities(
        schema_version="deep-analysis-provider-capabilities-v1",
        provider_kind=DeepAnalysisProviderKind.CLOUD_FREE,
        provider_id="provider-a",
        supports_raw_json_prompt=True,
        supports_json_mode=True,
        supports_json_schema=True,
        supports_tool_structured_return=False,
        declared_capability_profile_identity="declared-a",
    )
    assert not capabilities.is_qualified


def test_runtime_owned_admission_not_instance_shape_confers_trust() -> None:
    canonical = _canonical_input()
    assert not verify_authoritative_deep_analysis_input(canonical)
    with pytest.raises(ValueError, match="admitted"):
        _mint_trusted_deep_analysis_success_for_finalizer(
            canonical_input=canonical,
            content_identity="a" * 64,
            cache_identity="b" * 64,
        )

    _admit_authoritative_input_for_finalizer(canonical)
    trusted = _mint_trusted_deep_analysis_success_for_finalizer(
        canonical_input=canonical,
        content_identity="a" * 64,
        cache_identity="b" * 64,
    )
    assert verify_authoritative_deep_analysis_input(canonical)
    assert verify_trusted_deep_analysis_success(trusted)

    fake = object.__new__(TrustedDeepAnalysisSuccess)
    object.__setattr__(fake, "_content_identity", "a" * 64)
    object.__setattr__(fake, "_cache_identity", "b" * 64)
    object.__setattr__(fake, "_sealed", True)
    assert not verify_trusted_deep_analysis_success(fake)
    with pytest.raises(TypeError):
        copy.copy(trusted)
    with pytest.raises(TypeError):
        pickle.dumps(trusted)
    object.__setattr__(trusted, "_content_identity", "c" * 64)
    assert not verify_trusted_deep_analysis_success(trusted)


def test_unchecked_a1_lookalikes_remain_unadmitted() -> None:
    canonical = _canonical_input()
    constructed = CanonicalDeepAnalysisInputV1.model_construct(
        **{**canonical.__dict__, "scoring_request_hash": "f" * 64}
    )
    assert constructed.a1_identity != canonical.a1_identity
    assert not verify_authoritative_deep_analysis_input(constructed)
    assert not verify_authoritative_deep_analysis_input(canonical.model_copy())


@pytest.mark.parametrize(
    ("mode", "data"),
    [
        (
            DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT,
            {"settings": {"instructions": "return JSON"}},
        ),
        (
            DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
            {"settings": {"response_format": "json_object"}},
        ),
        (
            DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA,
            {
                "settings": {"strict": True},
                "schema": {"type": "object"},
            },
        ),
        (
            DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN,
            {
                "settings": {"parallel_tool_calls": False},
                "tools": ({"name": "return_result", "parameters": {}},),
                "tool_choice": {"name": "return_result"},
            },
        ),
    ],
)
def test_structured_output_mode_matrix_accepts_only_valid_minimums(
    mode: DeepAnalysisStructuredOutputMode, data: object
) -> None:
    assert isinstance(data, dict)
    output = DeepAnalysisStructuredOutputV1.model_validate(
        {
            "schema_version": "deep-analysis-structured-output-v1",
            "mode": mode,
            "dialect_id": "dialect",
            "dialect_version": "v1",
            **data,
        }
    )
    assert output.mode is mode


@pytest.mark.parametrize(
    "mode, invalid_data",
    [
        (
            DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT,
            {"settings": {}, "schema": {"type": "object"}},
        ),
        (
            DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
            {"settings": {}, "tools": ({"name": "wrong"},)},
        ),
        (
            DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA,
            {"settings": {}},
        ),
        (
            DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN,
            {"settings": {}, "tools": ({"name": "return_result"},)},
        ),
    ],
)
def test_structured_output_mode_matrix_rejects_cross_mode_or_missing_fields(
    mode: DeepAnalysisStructuredOutputMode, invalid_data: object
) -> None:
    assert isinstance(invalid_data, dict)
    with pytest.raises(ValueError):
        DeepAnalysisStructuredOutputV1.model_validate(
            {
                "schema_version": "deep-analysis-structured-output-v1",
                "mode": mode,
                "dialect_id": "dialect",
                "dialect_version": "v1",
                **invalid_data,
            }
        )


def test_raw_json_prompt_requires_exactly_one_user_message() -> None:
    _, request, _ = _request_and_execution()
    raw_output = DeepAnalysisStructuredOutputV1.model_validate(
        {
            "schema_version": "deep-analysis-structured-output-v1",
            "mode": DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT,
            "dialect_id": "prompt",
            "dialect_version": "v1",
            "settings": {"instructions": "return JSON"},
        }
    )
    with pytest.raises(ValueError, match="one user message"):
        DeepAnalysisRequestProjectionV1.model_validate(
            {**request.model_dump(by_alias=True), "structured_output": raw_output}
        )
    valid = DeepAnalysisRequestProjectionV1.model_validate(
        {
            **request.model_dump(by_alias=True),
            "structured_output": raw_output,
            "provider_visible_messages": (
                {
                    "schema_version": "deep-analysis-message-v1",
                    "role": "user",
                    "content": "return JSON",
                },
            ),
        }
    )
    assert valid.structured_output.mode is DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT


def test_a2_binds_tool_definition_and_selection_semantics() -> None:
    _, request, _ = _request_and_execution()
    tool_output = DeepAnalysisStructuredOutputV1.model_validate(
        {
            "schema_version": "deep-analysis-structured-output-v1",
            "mode": DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN,
            "dialect_id": "tools",
            "dialect_version": "v1",
            "settings": {"parallel_tool_calls": False},
            "tools": (
                {
                    "name": "return_result",
                    "description": "original",
                    "parameters": {"type": "object"},
                },
            ),
            "tool_choice": {"name": "return_result"},
        }
    )
    baseline = DeepAnalysisRequestProjectionV1.model_validate(
        {**request.model_dump(by_alias=True), "structured_output": tool_output}
    )
    changed_definition = DeepAnalysisRequestProjectionV1.model_validate(
        {
            **baseline.model_dump(by_alias=True),
            "structured_output": {
                **tool_output.model_dump(by_alias=True),
                "tools": (
                    {
                        "name": "return_result",
                        "description": "changed",
                        "parameters": {"type": "object"},
                    },
                ),
            },
        }
    )
    changed_selection = DeepAnalysisRequestProjectionV1.model_validate(
        {
            **baseline.model_dump(by_alias=True),
            "structured_output": {
                **tool_output.model_dump(by_alias=True),
                "tool_choice": {"name": "another_result"},
            },
        }
    )
    assert changed_definition.a2_identity != baseline.a2_identity
    assert changed_selection.a2_identity != baseline.a2_identity


@pytest.mark.parametrize("forbidden_field", ["api_key", "token", "password", "authorization", "headers"])
def test_credential_execution_identity_has_no_secret_material_surface(forbidden_field: str) -> None:
    with pytest.raises(ValueError) as error:
        CredentialExecutionProfileIdentityV1.model_validate(
            {
                **_credential().model_dump(),
                forbidden_field: "credential-material-must-not-be-retained",
            }
        )
    assert "credential-material-must-not-be-retained" not in str(error.value)
    with pytest.raises(ValueError):
        CredentialExecutionProfileIdentityV1.model_validate(
            {
                **_credential().model_dump(),
                "project_identity": "credential-material-must-not-be-retained",
            }
        )
    rendered = repr(_credential()) + str(_credential().model_dump())
    assert "credential-material-must-not-be-retained" not in rendered
    assert set(_credential().model_dump()) == {
        "schema_version",
        "provider_id",
        "execution_profile_identity",
    }


def test_dispatch_and_fallback_cross_bindings_fail_closed() -> None:
    canonical, request, execution = _request_and_execution()
    contradictory_consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.LOCAL_ONLY,
        authorization_record_identity="local-policy-v1",
        named_provider_id="provider-b",
        provider_kind=DeepAnalysisProviderKind.LOCAL,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint="model-a",
    )
    contradictory_request = DeepAnalysisRequestProjectionV1.model_validate(
        {
            **request.model_dump(by_alias=True),
            "payload_consent_identity": contradictory_consent.identity,
        }
    )
    contradictory_execution = DeepAnalysisExecutionProfileV1.model_validate(
        {**execution.model_dump(), "a2_identity": contradictory_request.a2_identity}
    )
    with pytest.raises(ValueError, match="provider"):
        DeepAnalysisDispatchEnvelopeV1(
            schema_version="deep-analysis-dispatch-envelope-v1",
            canonical_input=canonical,
            request_projection=contradictory_request,
            execution_profile=contradictory_execution,
            payload_consent=contradictory_consent,
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
            fallback_policy_identity="a" * 64,
            prompt_identity="knowledge-prompt-v3",
            schema_identity="knowledge-result-v2",
        )

    source = _node("model-a")
    destination = DeepAnalysisFallbackNodeV1.model_validate(
        {
            **_node("model-b").model_dump(),
            "payload_scope": DeepAnalysisPayloadScope.FULL_TRANSCRIPT,
            "credential_execution_profile_identity": "f" * 64,
        }
    )
    edge = DeepAnalysisFallbackEdgeV1(
        schema_version="deep-analysis-fallback-edge-v1",
        source_node_identity=source.identity,
        destination_node_identity=destination.identity,
        allowed_failure_codes=(DeepAnalysisFailureCode.TIMEOUT,),
        source_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        destination_payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_scope_authorization_identity="scope-auth",
        cloud_consent_authorization_identity="consent-auth",
        destination_credential_execution_profile_identity=_credential().identity,
    )
    with pytest.raises(ValueError, match="payload scope"):
        DeepAnalysisFallbackPolicyV1(
            schema_version="deep-analysis-fallback-policy-v1",
            start_node_identity=source.identity,
            nodes=(source, destination),
            edges=(edge,),
        )

    credential_edge = DeepAnalysisFallbackEdgeV1.model_validate(
        {
            **edge.model_dump(),
            "destination_payload_scope": DeepAnalysisPayloadScope.FULL_TRANSCRIPT,
        }
    )
    with pytest.raises(ValueError, match="credential profile"):
        DeepAnalysisFallbackPolicyV1(
            schema_version="deep-analysis-fallback-policy-v1",
            start_node_identity=source.identity,
            nodes=(source, destination),
            edges=(credential_edge,),
        )


def test_failure_taxonomy_accepts_pre_dispatch_provider_unavailable() -> None:
    failure = DeepAnalysisFailureV1(
        schema_version="deep-analysis-failure-v1",
        code=DeepAnalysisFailureCode.PROVIDER_UNAVAILABLE,
        stage=DeepAnalysisFailureStage.PRE_DISPATCH,
    )
    assert failure.stage is DeepAnalysisFailureStage.PRE_DISPATCH
