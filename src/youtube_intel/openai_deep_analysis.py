"""Qualified OpenAI Responses adapter for the provider-neutral Deep Analysis boundary.

The adapter is intentionally limited to one prepared dispatch and one provider
attempt.  It neither validates content nor owns the trusted-success mint.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

from youtube_intel.deep_analysis_contracts import (
    AuthorizedProviderPayloadProjectionV1,
    ContextBudgetProfileV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisContextAuthorityKind,
    DeepAnalysisDispatchEnvelopeV1,
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
from youtube_intel.deep_analysis_runtime import (
    DEFAULT_DEEP_ANALYSIS_VALIDATION_POLICY_IDENTITY,
    DeepAnalysisResponseMetadataV1,
    PreparedDeepAnalysisDispatch,
)
from youtube_intel.domain import KnowledgeContent

_TIMEOUT_SECONDS: Final = 30.0
_MAX_RETRIES: Final = 0
_MODEL_ID: Final = "gpt-5.4-mini-2026-03-17"
_CONTEXT_WINDOW: Final = 400_000
_STRUCTURED_OUTPUT_OVERHEAD: Final = 16_384
_MAX_OUTPUT_TOKENS: Final = 4_096
_CHILD_ENV: Final = {
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUTF8": "1",
}
_CHILD_PROGRAM: Final = r'''
import json
import sys
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

def fail(category, status=None, code=None):
    print(json.dumps({"kind": "error", "category": category, "status": status, "code": code}), flush=True)

message = json.loads(sys.stdin.read())
credential = message.pop("credential")
request = message.pop("request")
timeout = message.pop("timeout_seconds")
max_retries = message.pop("max_retries")
try:
    client = OpenAI(api_key=credential, timeout=timeout, max_retries=max_retries)
    response = client.responses.create(**request)
    print(json.dumps({"kind": "response", "response": response.model_dump(mode="json")}), flush=True)
except APITimeoutError:
    fail("TIMEOUT")
except APIConnectionError:
    fail("NETWORK")
except APIStatusError as error:
    body = error.body if isinstance(error.body, dict) else {}
    code = body.get("code")
    fail("STATUS", error.status_code, code if isinstance(code, str) else None)
except Exception:
    fail("UNKNOWN")
'''


@dataclass(frozen=True)
class OpenAIDeepAnalysisReferenceProfile:
    """The frozen non-secret identity of this first reference provider."""

    provider_kind: DeepAnalysisProviderKind = DeepAnalysisProviderKind.CLOUD_USER_KEY
    provider_id: str = "openai"
    adapter_identity: str = "openai-deep-analysis-responses"
    adapter_version: str = "1"
    sdk_or_http_client_version: str = "openai-2.46.0"
    endpoint_deployment_profile_identity: str = "openai-responses-v1"
    model_id: str = _MODEL_ID
    qualified_capability_profile_identity: str = "openai-deep-analysis-reference-capabilities-v1"
    context_authority_identity: str = "openai-gpt-5.4-mini-conservative-context-v1"
    generation_profile_identity: str = "openai-gpt-5.4-mini-generation-v1"
    idempotency_support_profile_identity: str = "openai-responses-no-retry-v1"
    structured_output_profile_identity: str = "openai-responses-json-schema-strict-v1"
    timeout_profile_identity: str = "openai-responses-timeout-30s-v1"


OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE: Final = OpenAIDeepAnalysisReferenceProfile()


class _OpenAITransport(Protocol):
    def __call__(
        self,
        request: Mapping[str, object],
        credential: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> Mapping[str, object]: ...


class OpenAIDeepAnalysisProviderError(Exception):
    """A non-secret terminal provider failure; it never carries a response body."""

    def __init__(self, failure: DeepAnalysisFailureV1) -> None:
        super().__init__(f"OpenAI Deep Analysis failed: {failure.code.value}")
        self.failure = failure


def _failure(code: DeepAnalysisFailureCode, stage: DeepAnalysisFailureStage) -> OpenAIDeepAnalysisProviderError:
    return OpenAIDeepAnalysisProviderError(
        DeepAnalysisFailureV1(
            schema_version="deep-analysis-failure-v1", code=code, stage=stage
        )
    )


def _thaw_json(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_thaw_json(item) for item in value]
    raise ValueError("OpenAI provider semantics must be JSON-shaped")


def _strict_openai_schema(schema: Mapping[str, object]) -> dict[str, object]:
    """Make Pydantic's application schema satisfy OpenAI strict-object rules.

    Requiring all object properties only narrows the provider output constraint;
    the provider-neutral application schema remains the success authority.
    """

    def transform(value: object) -> object:
        if isinstance(value, Mapping):
            result = {key: transform(item) for key, item in value.items()}
            properties = result.get("properties")
            if isinstance(properties, dict):
                result["additionalProperties"] = False
                result["required"] = list(properties)
            return result
        if isinstance(value, list):
            return [transform(item) for item in value]
        return value

    transformed = transform(schema)
    if not isinstance(transformed, dict):  # defensive: Pydantic returns an object schema
        raise ValueError("KnowledgeContent schema must be an object")
    return transformed


def _request_shape() -> dict[str, object]:
    return {
        "api": "openai-responses-v1",
        "method": "POST",
        "path": "/v1/responses",
        "model": _MODEL_ID,
        "store": False,
        "truncation": "disabled",
        "stream": False,
        "parallel_tool_calls": False,
        "service_tier": "default",
        "max_output_tokens": _MAX_OUTPUT_TOKENS,
        "reasoning": {"effort": "low"},
    }


def _generation_semantics() -> dict[str, object]:
    return {
        "max_output_tokens": _MAX_OUTPUT_TOKENS,
        "reasoning": {"effort": "low"},
        "service_tier": "default",
    }


def build_openai_reference_request_projection(
    *,
    canonical_input: object,
    authorized_payload: AuthorizedProviderPayloadProjectionV1,
    payload_consent: PayloadConsentIdentityV1,
) -> DeepAnalysisRequestProjectionV1:
    """Build the entire A2-visible OpenAI request projection from approved data."""

    if authorized_payload.payload_scope is not DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY:
        raise ValueError("the reference OpenAI profile permits selected evidence only")
    payload_json = json.dumps(
        authorized_payload.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
    )
    messages = (
        DeepAnalysisMessageV1(
            schema_version="deep-analysis-message-v1",
            role="developer",
            content="Return only the requested structured KnowledgeContent in the requested output language.",
        ),
        DeepAnalysisMessageV1(
            schema_version="deep-analysis-message-v1",
            role="user",
            content=(
                f"Output language: {authorized_payload.output_language}.\n"
                "Authorized provider payload follows; do not use information outside it.\n"
                f"{payload_json}"
            ),
        ),
    )
    a1_identity = getattr(canonical_input, "a1_identity", None)
    if not isinstance(a1_identity, str):
        raise ValueError("canonical input must provide a Deep Analysis A1 identity")
    return DeepAnalysisRequestProjectionV1(
        schema_version="deep-analysis-request-projection-v1",
        operation="deep-analysis",
        a1_identity=a1_identity,
        payload_consent_identity=payload_consent.identity,
        payload_scope=authorized_payload.payload_scope,
        authorized_payload=authorized_payload,
        provider_visible_messages=messages,
        provider_visible_request_shape=_request_shape(),
        structured_output=DeepAnalysisStructuredOutputV1.model_validate(
            {
                "schema_version": "deep-analysis-structured-output-v1",
                "mode": DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA,
                "dialect_id": "openai-responses-text-json-schema",
                "dialect_version": "v1",
                "settings": {"name": "deep_analysis_knowledge_content_v1", "strict": True},
                "schema": _strict_openai_schema(KnowledgeContent.model_json_schema()),
            }
        ),
        generation_semantics=_generation_semantics(),
        prompt_identity="openai-deep-analysis-prompt-v1",
        knowledge_content_schema_identity="knowledge-content-pydantic-v1",
        output_language=authorized_payload.output_language,
        payload_projection_version="authorized-provider-payload-projection-v1",
    )


def build_openai_reference_execution_profile(
    *,
    request_projection: DeepAnalysisRequestProjectionV1,
    credential_execution_profile: CredentialExecutionProfileIdentityV1,
) -> DeepAnalysisExecutionProfileV1:
    """Bind the frozen provider qualification profile into A3 without a secret."""

    profile = OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE
    if credential_execution_profile.provider_id != profile.provider_id:
        raise ValueError("credential execution profile provider does not match OpenAI")
    return DeepAnalysisExecutionProfileV1(
        schema_version="deep-analysis-execution-profile-v1",
        a2_identity=request_projection.a2_identity,
        provider_kind=profile.provider_kind,
        provider_id=profile.provider_id,
        adapter_identity=profile.adapter_identity,
        adapter_version=profile.adapter_version,
        sdk_or_http_client_version=profile.sdk_or_http_client_version,
        endpoint_deployment_profile_identity=profile.endpoint_deployment_profile_identity,
        model_selection=DeepAnalysisModelIdentityV1(
            schema_version="deep-analysis-model-identity-v1",
            model_id=profile.model_id,
            identity_class=DeepAnalysisModelIdentityClass.VERSIONED,
            resolved_revision=profile.model_id,
        ),
        qualified_capability_profile_identity=profile.qualified_capability_profile_identity,
        context_authority_identity=profile.context_authority_identity,
        generation_profile_identity=profile.generation_profile_identity,
        idempotency_support_profile_identity=profile.idempotency_support_profile_identity,
        credential_execution_profile=credential_execution_profile,
        structured_output_profile_identity=profile.structured_output_profile_identity,
    )


def build_openai_reference_context_budget(*, input_budget: int) -> ContextBudgetProfileV1:
    """Use a conservative contract budget, reserving undocumented schema overhead."""

    if input_budget > _CONTEXT_WINDOW - _STRUCTURED_OUTPUT_OVERHEAD - _MAX_OUTPUT_TOKENS:
        raise ValueError("OpenAI reference input budget exceeds its conservative admission")
    return ContextBudgetProfileV1(
        schema_version="deep-analysis-context-budget-profile-v1",
        authority_kind=DeepAnalysisContextAuthorityKind.CONSERVATIVE_PROVIDER_CONTRACT,
        authority_identity=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.context_authority_identity,
        context_window=_CONTEXT_WINDOW,
        input_budget=input_budget,
        structured_output_overhead_budget=_STRUCTURED_OUTPUT_OVERHEAD,
        tool_schema_overhead_budget=0,
        requested_output_budget=_MAX_OUTPUT_TOKENS,
    )


def _isolated_openai_transport(
    request: Mapping[str, object],
    credential: str,
    timeout_seconds: float,
    max_retries: int,
) -> Mapping[str, object]:
    """Invoke the SDK in an empty-environment child; credentials never persist."""

    payload = json.dumps(
        {
            "credential": credential,
            "request": _thaw_json(request),
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
        },
        separators=(",", ":"),
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", _CHILD_PROGRAM],
            input=payload,
            capture_output=True,
            check=False,
            env=dict(_CHILD_ENV),
            text=True,
            timeout=timeout_seconds + 2.0,
        )
    except subprocess.TimeoutExpired:
        return {"kind": "error", "category": "TIMEOUT"}
    if completed.returncode != 0:
        return {"kind": "error", "category": "NETWORK"}
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"kind": "error", "category": "UNKNOWN"}
    return result if isinstance(result, dict) else {"kind": "error", "category": "UNKNOWN"}


def _provider_error(result: Mapping[str, object]) -> OpenAIDeepAnalysisProviderError:
    category = result.get("category")
    if category == "TIMEOUT":
        return _failure(DeepAnalysisFailureCode.TIMEOUT, DeepAnalysisFailureStage.TRANSPORT)
    if category == "NETWORK":
        return _failure(DeepAnalysisFailureCode.NETWORK_FAILURE, DeepAnalysisFailureStage.TRANSPORT)
    status = result.get("status")
    code = result.get("code")
    if status in {401, 403}:
        return _failure(DeepAnalysisFailureCode.AUTH_INVALID, DeepAnalysisFailureStage.PROVIDER_ACCOUNT)
    if status == 429 and code == "insufficient_quota":
        return _failure(DeepAnalysisFailureCode.QUOTA_EXCEEDED, DeepAnalysisFailureStage.PROVIDER_ACCOUNT)
    if status == 429:
        return _failure(DeepAnalysisFailureCode.RATE_LIMITED, DeepAnalysisFailureStage.PROVIDER_ACCOUNT)
    if status == 404 or code in {"model_not_found", "model_not_available"}:
        return _failure(DeepAnalysisFailureCode.MODEL_UNAVAILABLE, DeepAnalysisFailureStage.PROVIDER_MODEL)
    if isinstance(status, int) and 500 <= status <= 599:
        return _failure(DeepAnalysisFailureCode.PROVIDER_UNAVAILABLE, DeepAnalysisFailureStage.PROVIDER_MODEL)
    return _failure(DeepAnalysisFailureCode.UNKNOWN, DeepAnalysisFailureStage.UNKNOWN)


def _response_metadata(prepared: PreparedDeepAnalysisDispatch, response: Mapping[str, object]) -> DeepAnalysisResponseMetadataV1:
    envelope = prepared.envelope
    model = response.get("model")
    if not isinstance(model, str) or not model:
        raise _failure(
            DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID,
            DeepAnalysisFailureStage.RESPONSE_ENVELOPE,
        )
    profile = envelope.execution_profile
    return DeepAnalysisResponseMetadataV1(
        schema_version="deep-analysis-response-metadata-v1",
        dispatch_identity=envelope.semantic_identity,
        provider_id=profile.provider_id,
        adapter_identity=profile.adapter_identity,
        adapter_version=profile.adapter_version,
        endpoint_deployment_profile_identity=profile.endpoint_deployment_profile_identity,
        model_id=model,
        resolved_revision=model,
        structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA.value,
        a1_identity=envelope.a1_identity,
        a2_identity=envelope.a2_identity,
        a3_identity=envelope.a3_identity,
        scoring_request_hash=envelope.canonical_input.scoring_request_hash,
        validation_policy_identity=DEFAULT_DEEP_ANALYSIS_VALIDATION_POLICY_IDENTITY,
    )


def _usage(response: Mapping[str, object]) -> PostResponseUsageEvidenceV1 | None:
    usage = response.get("usage")
    if not isinstance(usage, Mapping):
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if input_tokens is not None and (not isinstance(input_tokens, int) or input_tokens < 0):
        return None
    if output_tokens is not None and (not isinstance(output_tokens, int) or output_tokens < 0):
        return None
    return PostResponseUsageEvidenceV1(
        schema_version="deep-analysis-post-response-usage-evidence-v1",
        provider_reported_input_tokens=input_tokens,
        provider_reported_output_tokens=output_tokens,
    )


def _semantic_response_envelope(response: Mapping[str, object]) -> bytes:
    """Canonicalize semantic response fields without request IDs or usage evidence.

    Provider request IDs and usage are captured in their dedicated observational
    fields; neither is allowed to perturb response/cache identity.
    """

    return json.dumps(
        {
            "schema_version": "openai-responses-semantic-envelope-v1",
            "model": response["model"],
            "status": response["status"],
            "output_text": response["output_text"],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class OpenAIDeepAnalysisProviderAdapter:
    """One qualified OpenAI attempt producing only an untrusted response."""

    def __init__(self, *, transport: _OpenAITransport = _isolated_openai_transport) -> None:
        self._transport = transport

    def dispatch(
        self, *, prepared_dispatch: object, credential: str
    ) -> UntrustedDeepAnalysisResponseV1:
        if not credential:
            raise _failure(DeepAnalysisFailureCode.AUTH_REQUIRED, DeepAnalysisFailureStage.PRE_DISPATCH)
        if type(prepared_dispatch) is not PreparedDeepAnalysisDispatch:
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        envelope = prepared_dispatch.envelope
        request = self._request_for(envelope)
        result = self._transport(request, credential, _TIMEOUT_SECONDS, _MAX_RETRIES)
        if result.get("kind") != "response":
            raise _provider_error(result)
        raw_response = result.get("response")
        if not isinstance(raw_response, Mapping):
            raise _failure(
                DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID,
                DeepAnalysisFailureStage.RESPONSE_ENVELOPE,
            )
        if raw_response.get("status") != "completed":
            raise _failure(
                DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID,
                DeepAnalysisFailureStage.RESPONSE_ENVELOPE,
            )
        output_text = raw_response.get("output_text")
        response_id = raw_response.get("id")
        if not isinstance(output_text, str) or not isinstance(response_id, str) or not response_id:
            raise _failure(
                DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID,
                DeepAnalysisFailureStage.RESPONSE_ENVELOPE,
            )
        metadata = _response_metadata(prepared_dispatch, raw_response)
        envelope_bytes = _semantic_response_envelope(raw_response)
        return UntrustedDeepAnalysisResponseV1(
            schema_version="untrusted-deep-analysis-response-v1",
            expected_dispatch_identity=envelope.semantic_identity,
            provider_envelope_bytes=envelope_bytes,
            structured_payload=output_text.encode("utf-8"),
            structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA,
            provider_request_id=response_id,
            finish_reason="completed",
            delivery_certainty="CONFIRMED",
            response_metadata=metadata.model_dump(mode="json"),
            usage_evidence=_usage(raw_response),
        )

    @staticmethod
    def _request_for(envelope: DeepAnalysisDispatchEnvelopeV1) -> dict[str, object]:
        request_projection = envelope.request_projection
        execution_profile = envelope.execution_profile
        context = envelope.context_budget_profile
        profile = OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE
        expected = (
            execution_profile.provider_kind is profile.provider_kind
            and execution_profile.provider_id == profile.provider_id
            and execution_profile.adapter_identity == profile.adapter_identity
            and execution_profile.adapter_version == profile.adapter_version
            and execution_profile.sdk_or_http_client_version == profile.sdk_or_http_client_version
            and execution_profile.endpoint_deployment_profile_identity == profile.endpoint_deployment_profile_identity
            and execution_profile.model_selection.model_id == profile.model_id
            and execution_profile.model_selection.identity_class is DeepAnalysisModelIdentityClass.VERSIONED
            and execution_profile.model_selection.resolved_revision == profile.model_id
            and execution_profile.qualified_capability_profile_identity == profile.qualified_capability_profile_identity
            and execution_profile.context_authority_identity == profile.context_authority_identity
            and execution_profile.generation_profile_identity == profile.generation_profile_identity
            and execution_profile.idempotency_support_profile_identity == profile.idempotency_support_profile_identity
            and execution_profile.structured_output_profile_identity == profile.structured_output_profile_identity
            and execution_profile.credential_execution_profile.provider_id == profile.provider_id
            and envelope.timeout_profile_identity == profile.timeout_profile_identity
            and context.authority_kind is DeepAnalysisContextAuthorityKind.CONSERVATIVE_PROVIDER_CONTRACT
            and context.authority_identity == profile.context_authority_identity
            and context.context_window == _CONTEXT_WINDOW
            and context.structured_output_overhead_budget == _STRUCTURED_OUTPUT_OVERHEAD
            and context.tool_schema_overhead_budget == 0
            and context.requested_output_budget == _MAX_OUTPUT_TOKENS
            and request_projection.provider_visible_request_shape == _request_shape()
            and request_projection.generation_semantics == _generation_semantics()
            and request_projection.structured_output.mode is DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA
            and request_projection.structured_output.dialect_id == "openai-responses-text-json-schema"
            and request_projection.structured_output.dialect_version == "v1"
            and request_projection.structured_output.settings == {"name": "deep_analysis_knowledge_content_v1", "strict": True}
            and request_projection.structured_output.schema_object is not None
            and _thaw_json(request_projection.structured_output.schema_object)
            == _strict_openai_schema(KnowledgeContent.model_json_schema())
            and request_projection.payload_scope is DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY
            and request_projection.authorized_payload.payload_scope
            is DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY
            and request_projection.authorized_payload.transcript_text is None
            and request_projection.authorized_payload.transcript_content_hash is None
            and request_projection.authorized_payload.transcript_normalization_version is None
        )
        if not expected:
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        return {
            "model": profile.model_id,
            "input": [
                {"role": message.role, "content": message.content}
                for message in request_projection.provider_visible_messages
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "deep_analysis_knowledge_content_v1",
                    "strict": True,
                    "schema": _thaw_json(request_projection.structured_output.schema_object),
                }
            },
            "store": False,
            "truncation": "disabled",
            "stream": False,
            "parallel_tool_calls": False,
            "service_tier": "default",
            "max_output_tokens": _MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "low"},
        }


__all__ = [
    "OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE",
    "OpenAIDeepAnalysisProviderAdapter",
    "OpenAIDeepAnalysisProviderError",
    "build_openai_reference_context_budget",
    "build_openai_reference_execution_profile",
    "build_openai_reference_request_projection",
]
