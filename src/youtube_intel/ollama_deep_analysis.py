"""Qualified single-attempt loopback Ollama adapter for Deep Analysis."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.request import Request, urlopen

from youtube_intel.deep_analysis_contracts import (
    AuthorizedProviderPayloadProjectionV1,
    ContextBudgetProfileV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisContextAuthorityKind,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisFailureCode,
    DeepAnalysisFailureStage,
    DeepAnalysisFailureV1,
    DeepAnalysisMessageV1,
    DeepAnalysisModelIdentityClass,
    DeepAnalysisModelIdentityV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisProviderKind,
    DeepAnalysisRequestProjectionV1,
    DeepAnalysisStructuredOutputMode,
    DeepAnalysisStructuredOutputV1,
    PayloadConsentIdentityV1,
    PostResponseUsageEvidenceV1,
    UntrustedDeepAnalysisResponseV1,
)
from youtube_intel.deep_analysis_phase1a_contract import build_phase_1a_prompt
from youtube_intel.deep_analysis_phase1b_contract import (
    PHASE_1B_MODEL_SCHEMA,
    PHASE_1B_PROMPT_IDENTITY,
    PHASE_1B_VALIDATION_POLICY,
    DeepAnalysisPhase1BModelOutput,
)
from youtube_intel.deep_analysis_runtime import (
    DEFAULT_DEEP_ANALYSIS_VALIDATION_POLICY_IDENTITY,
    DeepAnalysisResponseMetadataV1,
    PreparedDeepAnalysisDispatch,
)
from youtube_intel.domain import KnowledgeContent

_TIMEOUT_SECONDS: Final = 120.0
_MODEL_ID: Final = "qwen2.5-coder:7b"
_DIGEST: Final = "sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"
_CONTEXT_WINDOW: Final = 32_768
_INPUT_LIMIT: Final = 8_192
_STRUCTURED_OVERHEAD: Final = 2_048
_MAX_OUTPUT: Final = 1_024


@dataclass(frozen=True)
class OllamaLocalDeepAnalysisProfile:
    provider_kind: DeepAnalysisProviderKind = DeepAnalysisProviderKind.LOCAL
    provider_id: str = "ollama-local"
    adapter_identity: str = "ollama-local-deep-analysis"
    adapter_version: str = "1"
    sdk_or_http_client_version: str = "stdlib-urllib-qualification-v1"
    endpoint_deployment_profile_identity: str = "ollama-loopback-api-chat-v1"
    model_id: str = _MODEL_ID
    model_digest: str = _DIGEST
    qualified_capability_profile_identity: str = "ollama-local-reference-capabilities-v1"
    context_authority_identity: str = "ollama-qwen25-coder-7b-local-tags-context-v1"
    generation_profile_identity: str = "ollama-qwen25-coder-json-generation-v1"
    idempotency_support_profile_identity: str = "ollama-no-retry-v1"
    structured_output_profile_identity: str = "ollama-provider-json-mode-v1"
    timeout_profile_identity: str = "ollama-timeout-120s-v1"


OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE: Final = OllamaLocalDeepAnalysisProfile()


class _OllamaTransport(Protocol):
    def __call__(self, request: dict[str, object], timeout_seconds: float) -> object: ...


class OllamaDeepAnalysisProviderError(Exception):
    def __init__(self, failure: DeepAnalysisFailureV1) -> None:
        super().__init__(f"Ollama Deep Analysis failed: {failure.code.value}")
        self.failure = failure


def _failure(code: DeepAnalysisFailureCode, stage: DeepAnalysisFailureStage) -> OllamaDeepAnalysisProviderError:
    return OllamaDeepAnalysisProviderError(DeepAnalysisFailureV1(schema_version="deep-analysis-failure-v1", code=code, stage=stage))


def _loopback_transport(request: dict[str, object], timeout_seconds: float) -> object:
    """Issue the one bounded request to the qualified loopback endpoint."""
    message = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(request, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(message, timeout=timeout_seconds) as response:
        decoded = json.loads(response.read())
    return decoded if isinstance(decoded, dict) else None


def _request_shape() -> dict[str, object]:
    return {"api": "ollama-chat-v1", "method": "POST", "path": "/api/chat", "model": _MODEL_ID, "format": "json", "stream": False, "think": False}


def _generation() -> dict[str, object]:
    return {"temperature": 0, "seed": 0, "num_ctx": _INPUT_LIMIT, "num_predict": _MAX_OUTPUT}


def build_ollama_local_request_projection(*, canonical_input: object, authorized_payload: AuthorizedProviderPayloadProjectionV1, payload_consent: PayloadConsentIdentityV1) -> DeepAnalysisRequestProjectionV1:
    if authorized_payload.payload_scope is not DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY:
        raise ValueError("the qualified Ollama profile permits selected evidence only")
    a1_identity = getattr(canonical_input, "a1_identity", None)
    if not isinstance(a1_identity, str):
        raise ValueError("canonical input must provide a Deep Analysis A1 identity")
    prompt = (
        "Return exactly one JSON KnowledgeContent object in the requested output language. "
        "Use only the authorized provider payload; do not add Markdown or surrounding text. "
        "The JSON Schema is an output instruction; application validation remains authoritative.\n"
        f"Output language: {authorized_payload.output_language}.\n"
        f"KnowledgeContent schema: {json.dumps(KnowledgeContent.model_json_schema(), separators=(',', ':'), sort_keys=True)}\n"
        + json.dumps(authorized_payload.model_dump(mode="json"), separators=(",", ":"), sort_keys=True)
    )
    return DeepAnalysisRequestProjectionV1(
        schema_version="deep-analysis-request-projection-v1", operation="deep-analysis", a1_identity=a1_identity,
        payload_consent_identity=payload_consent.identity, payload_scope=authorized_payload.payload_scope,
        authorized_payload=authorized_payload,
        provider_visible_messages=(DeepAnalysisMessageV1(schema_version="deep-analysis-message-v1", role="user", content=prompt),),
        provider_visible_request_shape=_request_shape(),
        structured_output=DeepAnalysisStructuredOutputV1(schema_version="deep-analysis-structured-output-v1", mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE, dialect_id="ollama-json", dialect_version="0.32.1", settings={"format": "json"}),
        generation_semantics=_generation(), prompt_identity="ollama-local-deep-analysis-prompt-v1",
        knowledge_content_schema_identity="knowledge-content-pydantic-v1", output_language=authorized_payload.output_language,
        payload_projection_version="authorized-provider-payload-projection-v1",
    )


def build_ollama_local_phase1a_request_projection(*, canonical_input: object, authorized_payload: AuthorizedProviderPayloadProjectionV1, payload_consent: PayloadConsentIdentityV1) -> DeepAnalysisRequestProjectionV1:
    """Render the V1.x Phase-1A five-concept request.

    This is the live model boundary for the activated Content Deep Analysis
    path.  It differs from the frozen ADR-027 qualified projection in exactly one
    respect: the model is asked only for the five first-version concepts and is
    explicitly told not to infer relation-to-knowledge or knowledge-delta
    content.  The frozen builder above is left untouched for the existing
    qualification path.
    """

    if authorized_payload.payload_scope is not DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY:
        raise ValueError("the qualified Ollama profile permits selected evidence only")
    a1_identity = getattr(canonical_input, "a1_identity", None)
    if not isinstance(a1_identity, str):
        raise ValueError("canonical input must provide a Deep Analysis A1 identity")
    prompt = build_phase_1a_prompt(
        output_language=authorized_payload.output_language,
        payload_json=json.dumps(authorized_payload.model_dump(mode="json"), separators=(",", ":"), sort_keys=True),
    )
    return DeepAnalysisRequestProjectionV1(
        schema_version="deep-analysis-request-projection-v1", operation="content-deep-analysis", a1_identity=a1_identity,
        payload_consent_identity=payload_consent.identity, payload_scope=authorized_payload.payload_scope,
        authorized_payload=authorized_payload,
        provider_visible_messages=(DeepAnalysisMessageV1(schema_version="deep-analysis-message-v1", role="user", content=prompt),),
        provider_visible_request_shape=_request_shape(),
        structured_output=DeepAnalysisStructuredOutputV1(schema_version="deep-analysis-structured-output-v1", mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE, dialect_id="ollama-json", dialect_version="0.32.1", settings={"format": "json"}),
        generation_semantics=_generation(), prompt_identity="v1x-content-deep-analysis-phase1a-prompt-v1",
        knowledge_content_schema_identity="v1x-content-deep-analysis-model-output-v1", output_language=authorized_payload.output_language,
        payload_projection_version="authorized-provider-payload-projection-v1",
    )


def build_ollama_local_phase1b_request_projection(*, canonical_input: object, authorized_payload: AuthorizedProviderPayloadProjectionV1, payload_consent: PayloadConsentIdentityV1) -> DeepAnalysisRequestProjectionV1:
    """Five roles plus candidate refs; no model-owned Evidence construction."""
    base = build_ollama_local_phase1a_request_projection(
        canonical_input=canonical_input, authorized_payload=authorized_payload, payload_consent=payload_consent,
    )
    prompt = (
        "Analyze one Content using exactly the five roles in the JSON Schema. "
        "Return one JSON object in the requested output language. Each evidence_ref "
        "must select an id from selected_evidence. These are temporary backend "
        "candidates, not durable Evidence ids. Do not author excerpts, offsets, "
        "timestamps, Evidence ids, knowledge relations, or knowledge delta. "
        "Title, description and source labels are context only and cannot be cited.\n"
        f"Output language: {authorized_payload.output_language}.\n"
        f"JSON Schema: {json.dumps(DeepAnalysisPhase1BModelOutput.model_json_schema(), sort_keys=True)}\n"
        f"Authorized payload: {json.dumps(authorized_payload.model_dump(mode='json'), ensure_ascii=False, sort_keys=True)}"
    )
    return DeepAnalysisRequestProjectionV1.model_validate({
        **base.model_dump(mode="python", by_alias=True), "prompt_identity": PHASE_1B_PROMPT_IDENTITY,
        "knowledge_content_schema_identity": PHASE_1B_MODEL_SCHEMA,
        "provider_visible_messages": [DeepAnalysisMessageV1(schema_version="deep-analysis-message-v1", role="user", content=prompt)],
    })


def build_ollama_local_execution_profile(*, request_projection: DeepAnalysisRequestProjectionV1, credential_execution_profile: CredentialExecutionProfileIdentityV1) -> DeepAnalysisExecutionProfileV1:
    profile = OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE
    if credential_execution_profile.provider_id != profile.provider_id:
        raise ValueError("credential execution profile provider does not match Ollama")
    return DeepAnalysisExecutionProfileV1(
        schema_version="deep-analysis-execution-profile-v1", a2_identity=request_projection.a2_identity,
        provider_kind=profile.provider_kind, provider_id=profile.provider_id, adapter_identity=profile.adapter_identity,
        adapter_version=profile.adapter_version, sdk_or_http_client_version=profile.sdk_or_http_client_version,
        endpoint_deployment_profile_identity=profile.endpoint_deployment_profile_identity,
        model_selection=DeepAnalysisModelIdentityV1(schema_version="deep-analysis-model-identity-v1", model_id=profile.model_id, identity_class=DeepAnalysisModelIdentityClass.IMMUTABLE, resolved_revision=profile.model_digest),
        qualified_capability_profile_identity=profile.qualified_capability_profile_identity, context_authority_identity=profile.context_authority_identity,
        generation_profile_identity=profile.generation_profile_identity, idempotency_support_profile_identity=profile.idempotency_support_profile_identity,
        credential_execution_profile=credential_execution_profile, structured_output_profile_identity=profile.structured_output_profile_identity,
    )


def build_ollama_local_context_budget(*, input_budget: int) -> ContextBudgetProfileV1:
    if input_budget > _INPUT_LIMIT:
        raise ValueError("Ollama local input exceeds the qualified conservative budget")
    return ContextBudgetProfileV1(schema_version="deep-analysis-context-budget-profile-v1", authority_kind=DeepAnalysisContextAuthorityKind.CONSERVATIVE_PROVIDER_CONTRACT,
        authority_identity=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.context_authority_identity, context_window=_CONTEXT_WINDOW,
        input_budget=input_budget, structured_output_overhead_budget=_STRUCTURED_OVERHEAD, tool_schema_overhead_budget=0, requested_output_budget=_MAX_OUTPUT)


class OllamaDeepAnalysisProviderAdapter:
    """One loopback attempt which returns an untrusted response only."""
    def __init__(self, *, transport: _OllamaTransport = _loopback_transport) -> None:
        self._transport = transport

    def dispatch(self, *, prepared_dispatch: object) -> UntrustedDeepAnalysisResponseV1:
        if type(prepared_dispatch) is not PreparedDeepAnalysisDispatch:
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        envelope = prepared_dispatch.envelope
        request = self._request_for(envelope)
        try:
            raw = self._transport(request, _TIMEOUT_SECONDS)
        except TimeoutError as error:
            raise _failure(DeepAnalysisFailureCode.TIMEOUT, DeepAnalysisFailureStage.TRANSPORT) from error
        except OSError as error:
            raise _failure(DeepAnalysisFailureCode.NETWORK_FAILURE, DeepAnalysisFailureStage.TRANSPORT) from error
        if not isinstance(raw, Mapping):
            raise _failure(DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID, DeepAnalysisFailureStage.RESPONSE_ENVELOPE)
        model, done, message = raw.get("model"), raw.get("done"), raw.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(model, str) or not isinstance(content, str) or done is not True:
            raise _failure(DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID, DeepAnalysisFailureStage.RESPONSE_ENVELOPE)
        profile = envelope.execution_profile
        metadata = DeepAnalysisResponseMetadataV1(schema_version="deep-analysis-response-metadata-v1", dispatch_identity=envelope.semantic_identity,
            provider_id=profile.provider_id, adapter_identity=profile.adapter_identity, adapter_version=profile.adapter_version,
            endpoint_deployment_profile_identity=profile.endpoint_deployment_profile_identity, model_id=model,
            resolved_revision=profile.model_selection.resolved_revision, structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE.value,
            a1_identity=envelope.a1_identity, a2_identity=envelope.a2_identity, a3_identity=envelope.a3_identity,
            scoring_request_hash=envelope.canonical_input.scoring_request_hash, validation_policy_identity=(PHASE_1B_VALIDATION_POLICY.identity if envelope.request_projection.knowledge_content_schema_identity == PHASE_1B_MODEL_SCHEMA else DEFAULT_DEEP_ANALYSIS_VALIDATION_POLICY_IDENTITY))
        usage = _usage(raw)
        semantic = json.dumps({"schema_version":"ollama-chat-semantic-envelope-v1", "model":model, "done":done, "done_reason":raw.get("done_reason"), "content":content}, separators=(",", ":"), sort_keys=True).encode()
        return UntrustedDeepAnalysisResponseV1(schema_version="untrusted-deep-analysis-response-v1", expected_dispatch_identity=envelope.semantic_identity,
            provider_envelope_bytes=semantic, structured_payload=content.encode("utf-8"), structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
            finish_reason=raw.get("done_reason") if isinstance(raw.get("done_reason"), str) else None, delivery_certainty="CONFIRMED",
            response_metadata=metadata.model_dump(mode="json"), usage_evidence=usage)

    @staticmethod
    def _request_for(envelope: object) -> dict[str, object]:
        if not hasattr(envelope, "request_projection") or not hasattr(envelope, "execution_profile"):
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        request = envelope.request_projection
        execution = envelope.execution_profile
        profile = OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE
        expected = (execution.provider_kind is profile.provider_kind and execution.provider_id == profile.provider_id and execution.adapter_identity == profile.adapter_identity and execution.adapter_version == profile.adapter_version and execution.model_selection.model_id == profile.model_id and execution.model_selection.resolved_revision == profile.model_digest and request.provider_visible_request_shape == _request_shape() and request.generation_semantics == _generation() and request.structured_output.mode is DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE and request.payload_scope is DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY and len(request.provider_visible_messages) == 1 and request.provider_visible_messages[0].role == "user")
        if not expected:
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        return {"model": profile.model_id, "messages": [{"role":"user", "content":request.provider_visible_messages[0].content}], "format":"json", "stream":False, "think":False, "options":_generation()}


def _usage(response: Mapping[str, object]) -> PostResponseUsageEvidenceV1 | None:
    prompt, output = response.get("prompt_eval_count"), response.get("eval_count")
    if prompt is not None and (not isinstance(prompt, int) or prompt < 0):
        return None
    if output is not None and (not isinstance(output, int) or output < 0):
        return None
    return PostResponseUsageEvidenceV1(schema_version="deep-analysis-post-response-usage-evidence-v1", provider_reported_input_tokens=prompt, provider_reported_output_tokens=output)


__all__ = ["OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE", "OllamaDeepAnalysisProviderAdapter", "OllamaDeepAnalysisProviderError", "build_ollama_local_context_budget", "build_ollama_local_execution_profile", "build_ollama_local_request_projection"]
