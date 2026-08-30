"""Kimi R2 Chat Completions adapter for the Deep Analysis trust boundary.

It performs exactly one prepared provider attempt and returns untrusted data.
All validation and trusted-success authority remain in the provider-neutral
runtime finalizer.
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

_BASE_URL: Final = "https://api.moonshot.cn/v1"
_MODEL_ID: Final = "kimi-k3"
_TIMEOUT_SECONDS: Final = 120.0
_MAX_RETRIES: Final = 0
_CONTEXT_WINDOW: Final = 1_000_000
_STRUCTURED_OUTPUT_OVERHEAD: Final = 16_384
_MAX_COMPLETION_TOKENS: Final = 4_096
_CHILD_ENV: Final = {"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
_CHILD_PROGRAM: Final = r'''
import json
import sys
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

def fail(category, status=None, code=None):
    print(json.dumps({"kind": "error", "category": category, "status": status, "code": code}), flush=True)

message = json.loads(sys.stdin.read())
credential = message.pop("credential")
request = message.pop("request")
base_url = message.pop("base_url")
timeout = message.pop("timeout_seconds")
max_retries = message.pop("max_retries")
try:
    client = OpenAI(api_key=credential, base_url=base_url, timeout=timeout, max_retries=max_retries)
    response = client.chat.completions.create(**request)
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
class KimiDeepAnalysisReferenceProfileR2:
    """The accepted Kimi R2 non-secret provider execution profile."""

    provider_kind: DeepAnalysisProviderKind = DeepAnalysisProviderKind.CLOUD_USER_KEY
    provider_id: str = "kimi"
    adapter_identity: str = "kimi-deep-analysis-chat-completions"
    adapter_version: str = "1"
    sdk_or_http_client_version: str = "openai-2.46.0"
    endpoint_deployment_profile_identity: str = "moonshot-cn-chat-completions-v1"
    model_id: str = _MODEL_ID
    qualified_capability_profile_identity: str = "kimi-deep-analysis-reference-capabilities-r2-timeout-120s-v1"
    context_authority_identity: str = "moonshot-kimi-k3-conservative-context-v1"
    generation_profile_identity: str = "moonshot-kimi-k3-low-reasoning-v1"
    idempotency_support_profile_identity: str = "moonshot-chat-no-retry-v1"
    structured_output_profile_identity: str = "moonshot-chat-json-object-v1"
    timeout_profile_identity: str = "moonshot-chat-timeout-120s-v2"


KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2: Final = KimiDeepAnalysisReferenceProfileR2()


class _KimiTransport(Protocol):
    def __call__(self, request: dict[str, object], credential: str, timeout: float, retries: int) -> object: ...


class KimiDeepAnalysisProviderError(Exception):
    """A redacted, terminal provider failure."""

    def __init__(self, failure: DeepAnalysisFailureV1) -> None:
        super().__init__(f"Kimi Deep Analysis failed: {failure.code.value}")
        self.failure = failure


def _failure(code: DeepAnalysisFailureCode, stage: DeepAnalysisFailureStage) -> KimiDeepAnalysisProviderError:
    return KimiDeepAnalysisProviderError(DeepAnalysisFailureV1(schema_version="deep-analysis-failure-v1", code=code, stage=stage))


def _thaw_json(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_thaw_json(item) for item in value]
    raise ValueError("Kimi provider semantics must be JSON-shaped")


def _request_shape() -> dict[str, object]:
    return {
        "api": "moonshot-chat-completions-v1", "method": "POST", "path": "/v1/chat/completions",
        "model": _MODEL_ID, "response_format": {"type": "json_object"}, "stream": False,
        "max_completion_tokens": _MAX_COMPLETION_TOKENS, "reasoning_effort": "low",
    }


def _generation_semantics() -> dict[str, object]:
    return {"max_completion_tokens": _MAX_COMPLETION_TOKENS, "reasoning_effort": "low"}


def build_kimi_reference_request_projection(
    *, canonical_input: object, authorized_payload: AuthorizedProviderPayloadProjectionV1, payload_consent: PayloadConsentIdentityV1,
) -> DeepAnalysisRequestProjectionV1:
    """Build the complete Kimi R2 A2 request projection."""

    if authorized_payload.payload_scope is not DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY:
        raise ValueError("the Kimi R2 profile permits selected evidence only")
    a1_identity = getattr(canonical_input, "a1_identity", None)
    if not isinstance(a1_identity, str):
        raise ValueError("canonical input must provide a Deep Analysis A1 identity")
    schema = json.dumps(KnowledgeContent.model_json_schema(), separators=(",", ":"), sort_keys=True)
    payload = json.dumps(authorized_payload.model_dump(mode="json"), separators=(",", ":"), sort_keys=True)
    messages = (
        DeepAnalysisMessageV1(
            schema_version="deep-analysis-message-v1", role="system",
            content=(
                "Return exactly one JSON KnowledgeContent object in the requested output language. "
                "Use only the authorized provider payload. Do not add Markdown or surrounding text. "
                "The following is an output instruction only; application validation remains authoritative. "
                "why_it_matters.kind must be inference and every evidence id must be from the supplied evidence registry.\n"
                f"KnowledgeContent schema instruction: {schema}"
            ),
        ),
        DeepAnalysisMessageV1(
            schema_version="deep-analysis-message-v1", role="user",
            content=f"Output language: {authorized_payload.output_language}.\nAuthorized provider payload follows; do not use information outside it.\n{payload}",
        ),
    )
    return DeepAnalysisRequestProjectionV1(
        schema_version="deep-analysis-request-projection-v1", operation="deep-analysis", a1_identity=a1_identity,
        payload_consent_identity=payload_consent.identity, payload_scope=authorized_payload.payload_scope,
        authorized_payload=authorized_payload, provider_visible_messages=messages, provider_visible_request_shape=_request_shape(),
        structured_output=DeepAnalysisStructuredOutputV1(
            schema_version="deep-analysis-structured-output-v1", mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
            dialect_id="moonshot-chat-json-object", dialect_version="2026-08-30",
            settings={"response_format": {"type": "json_object"}},
        ),
        generation_semantics=_generation_semantics(), prompt_identity="kimi-deep-analysis-prompt-v1",
        knowledge_content_schema_identity="knowledge-content-pydantic-v1", output_language=authorized_payload.output_language,
        payload_projection_version="authorized-provider-payload-projection-v1",
    )


def build_kimi_reference_execution_profile(
    *, request_projection: DeepAnalysisRequestProjectionV1, credential_execution_profile: CredentialExecutionProfileIdentityV1,
) -> DeepAnalysisExecutionProfileV1:
    """Bind the R2 capability qualification into A3 without credentials."""

    profile = KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2
    if credential_execution_profile.provider_id != profile.provider_id:
        raise ValueError("credential execution profile provider does not match Kimi")
    return DeepAnalysisExecutionProfileV1(
        schema_version="deep-analysis-execution-profile-v1", a2_identity=request_projection.a2_identity,
        provider_kind=profile.provider_kind, provider_id=profile.provider_id, adapter_identity=profile.adapter_identity,
        adapter_version=profile.adapter_version, sdk_or_http_client_version=profile.sdk_or_http_client_version,
        endpoint_deployment_profile_identity=profile.endpoint_deployment_profile_identity,
        model_selection=DeepAnalysisModelIdentityV1(
            schema_version="deep-analysis-model-identity-v1", model_id=profile.model_id,
            identity_class=DeepAnalysisModelIdentityClass.FLOATING, resolved_revision=None,
        ),
        qualified_capability_profile_identity=profile.qualified_capability_profile_identity,
        context_authority_identity=profile.context_authority_identity,
        generation_profile_identity=profile.generation_profile_identity,
        idempotency_support_profile_identity=profile.idempotency_support_profile_identity,
        credential_execution_profile=credential_execution_profile,
        structured_output_profile_identity=profile.structured_output_profile_identity,
    )


def build_kimi_reference_context_budget(*, input_budget: int) -> ContextBudgetProfileV1:
    """Apply the qualified conservative K3 context admission bound."""

    if input_budget > _CONTEXT_WINDOW - _STRUCTURED_OUTPUT_OVERHEAD - _MAX_COMPLETION_TOKENS:
        raise ValueError("Kimi R2 input budget exceeds its conservative admission")
    return ContextBudgetProfileV1(
        schema_version="deep-analysis-context-budget-profile-v1",
        authority_kind=DeepAnalysisContextAuthorityKind.CONSERVATIVE_PROVIDER_CONTRACT,
        authority_identity=KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2.context_authority_identity,
        context_window=_CONTEXT_WINDOW, input_budget=input_budget,
        structured_output_overhead_budget=_STRUCTURED_OUTPUT_OVERHEAD, tool_schema_overhead_budget=0,
        requested_output_budget=_MAX_COMPLETION_TOKENS,
    )


def _isolated_kimi_transport(request: dict[str, object], credential: str, timeout: float, retries: int) -> object:
    payload = json.dumps({"credential": credential, "request": _thaw_json(request), "base_url": _BASE_URL, "timeout_seconds": timeout, "max_retries": retries}, separators=(",", ":"))
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", _CHILD_PROGRAM], input=payload, capture_output=True, check=False,
            env=dict(_CHILD_ENV), text=True, timeout=timeout + 2.0,
        )
    except subprocess.TimeoutExpired:
        return {"kind": "error", "category": "TIMEOUT"}
    if completed.returncode != 0:
        return {"kind": "error", "category": "NETWORK"}
    try:
        decoded = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"kind": "error", "category": "UNKNOWN"}
    return decoded if isinstance(decoded, dict) else {"kind": "error", "category": "UNKNOWN"}


def _provider_error(result: Mapping[str, object]) -> KimiDeepAnalysisProviderError:
    category = result.get("category")
    if category == "TIMEOUT":
        return _failure(DeepAnalysisFailureCode.TIMEOUT, DeepAnalysisFailureStage.TRANSPORT)
    if category == "NETWORK":
        return _failure(DeepAnalysisFailureCode.NETWORK_FAILURE, DeepAnalysisFailureStage.TRANSPORT)
    status, code = result.get("status"), result.get("code")
    if status in {401, 403}:
        return _failure(DeepAnalysisFailureCode.AUTH_INVALID, DeepAnalysisFailureStage.PROVIDER_ACCOUNT)
    if status == 429 and code in {"insufficient_quota", "quota_exceeded"}:
        return _failure(DeepAnalysisFailureCode.QUOTA_EXCEEDED, DeepAnalysisFailureStage.PROVIDER_ACCOUNT)
    if status == 429:
        return _failure(DeepAnalysisFailureCode.RATE_LIMITED, DeepAnalysisFailureStage.PROVIDER_ACCOUNT)
    if status == 404 or code in {"model_not_found", "model_not_available"}:
        return _failure(DeepAnalysisFailureCode.MODEL_UNAVAILABLE, DeepAnalysisFailureStage.PROVIDER_MODEL)
    if isinstance(status, int) and 500 <= status <= 599:
        return _failure(DeepAnalysisFailureCode.PROVIDER_UNAVAILABLE, DeepAnalysisFailureStage.PROVIDER_MODEL)
    return _failure(DeepAnalysisFailureCode.UNKNOWN, DeepAnalysisFailureStage.UNKNOWN)


def _usage(response: Mapping[str, object]) -> PostResponseUsageEvidenceV1 | None:
    usage = response.get("usage")
    if not isinstance(usage, Mapping):
        return None
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if prompt is not None and (not isinstance(prompt, int) or prompt < 0):
        return None
    if completion is not None and (not isinstance(completion, int) or completion < 0):
        return None
    return PostResponseUsageEvidenceV1(
        schema_version="deep-analysis-post-response-usage-evidence-v1",
        provider_reported_input_tokens=prompt, provider_reported_output_tokens=completion,
    )


class KimiDeepAnalysisProviderAdapter:
    """One R2 Kimi provider attempt returning only an untrusted response."""

    def __init__(self, *, transport: _KimiTransport = _isolated_kimi_transport) -> None:
        self._transport = transport

    def dispatch(self, *, prepared_dispatch: object, credential: str) -> UntrustedDeepAnalysisResponseV1:
        if not credential:
            raise _failure(DeepAnalysisFailureCode.AUTH_REQUIRED, DeepAnalysisFailureStage.PRE_DISPATCH)
        if type(prepared_dispatch) is not PreparedDeepAnalysisDispatch:
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        envelope = prepared_dispatch.envelope
        result = self._transport(self._request_for(envelope), credential, _TIMEOUT_SECONDS, _MAX_RETRIES)
        if not isinstance(result, Mapping) or result.get("kind") != "response":
            raise _provider_error(result if isinstance(result, Mapping) else {"kind": "error", "category": "UNKNOWN"})
        raw = result.get("response")
        if not isinstance(raw, Mapping):
            raise _failure(DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID, DeepAnalysisFailureStage.RESPONSE_ENVELOPE)
        model, request_id, choices = raw.get("model"), raw.get("id"), raw.get("choices")
        if not isinstance(model, str) or not isinstance(request_id, str) or not request_id or not isinstance(choices, Sequence) or isinstance(choices, (str, bytes, bytearray)) or not choices or not isinstance(choices[0], Mapping):
            raise _failure(DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID, DeepAnalysisFailureStage.RESPONSE_ENVELOPE)
        choice = choices[0]
        message = choice.get("message")
        content, finish_reason = (message.get("content") if isinstance(message, Mapping) else None), choice.get("finish_reason")
        if not isinstance(content, str) or (finish_reason is not None and not isinstance(finish_reason, str)):
            raise _failure(DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID, DeepAnalysisFailureStage.RESPONSE_ENVELOPE)
        metadata = self._response_metadata(prepared_dispatch, model)
        semantic = json.dumps({"schema_version": "moonshot-chat-semantic-envelope-v1", "model": model, "finish_reason": finish_reason, "content": content}, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return UntrustedDeepAnalysisResponseV1(
            schema_version="untrusted-deep-analysis-response-v1", expected_dispatch_identity=envelope.semantic_identity,
            provider_envelope_bytes=semantic, structured_payload=content.encode("utf-8"),
            structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
            provider_request_id=request_id, finish_reason=finish_reason, delivery_certainty="CONFIRMED",
            response_metadata=metadata.model_dump(mode="json"), usage_evidence=_usage(raw),
        )

    @staticmethod
    def _response_metadata(prepared: PreparedDeepAnalysisDispatch, model: str) -> DeepAnalysisResponseMetadataV1:
        envelope = prepared.envelope
        profile = envelope.execution_profile
        return DeepAnalysisResponseMetadataV1(
            schema_version="deep-analysis-response-metadata-v1", dispatch_identity=envelope.semantic_identity,
            provider_id=profile.provider_id, adapter_identity=profile.adapter_identity, adapter_version=profile.adapter_version,
            endpoint_deployment_profile_identity=profile.endpoint_deployment_profile_identity, model_id=model, resolved_revision=None,
            structured_output_mode=DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE.value,
            a1_identity=envelope.a1_identity, a2_identity=envelope.a2_identity, a3_identity=envelope.a3_identity,
            scoring_request_hash=envelope.canonical_input.scoring_request_hash,
            validation_policy_identity=DEFAULT_DEEP_ANALYSIS_VALIDATION_POLICY_IDENTITY,
        )

    @staticmethod
    def _request_for(envelope: DeepAnalysisDispatchEnvelopeV1) -> dict[str, object]:
        profile = KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2
        request = envelope.request_projection
        expected_request = build_kimi_reference_request_projection(
            canonical_input=envelope.canonical_input, authorized_payload=request.authorized_payload,
            payload_consent=envelope.payload_consent,
        )
        expected_execution = build_kimi_reference_execution_profile(
            request_projection=expected_request, credential_execution_profile=envelope.execution_profile.credential_execution_profile,
        )
        context = envelope.context_budget_profile
        valid = (
            request == expected_request and envelope.execution_profile == expected_execution
            and envelope.timeout_profile_identity == profile.timeout_profile_identity
            and context.authority_kind is DeepAnalysisContextAuthorityKind.CONSERVATIVE_PROVIDER_CONTRACT
            and context.authority_identity == profile.context_authority_identity and context.context_window == _CONTEXT_WINDOW
            and context.structured_output_overhead_budget == _STRUCTURED_OUTPUT_OVERHEAD
            and context.tool_schema_overhead_budget == 0 and context.requested_output_budget == _MAX_COMPLETION_TOKENS
            and request.payload_scope is DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY
            and request.authorized_payload.transcript_text is None and request.authorized_payload.transcript_content_hash is None
            and request.authorized_payload.transcript_normalization_version is None
        )
        if not valid:
            raise _failure(DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED, DeepAnalysisFailureStage.PRE_DISPATCH)
        return {
            "model": profile.model_id,
            "messages": [{"role": message.role, "content": message.content} for message in request.provider_visible_messages],
            "response_format": {"type": "json_object"}, "stream": False,
            "max_completion_tokens": _MAX_COMPLETION_TOKENS, "reasoning_effort": "low",
        }


__all__ = [
    "KIMI_DEEP_ANALYSIS_REFERENCE_PROFILE_R2", "KimiDeepAnalysisProviderAdapter", "KimiDeepAnalysisProviderError",
    "build_kimi_reference_context_budget", "build_kimi_reference_execution_profile", "build_kimi_reference_request_projection",
]
