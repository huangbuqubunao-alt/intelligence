"""Runtime-owned provider-neutral Deep Analysis admission boundary.

This module deliberately performs no provider dispatch.  It owns the
process-local authority that turns an already verified scoring read into an
authoritative Deep Analysis input; hashes and DTO shapes remain identities only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable, Literal, NoReturn, cast
from weakref import WeakKeyDictionary

from pydantic import BaseModel, ConfigDict, Field

from youtube_intel.deep_analysis_contracts import (
    AuthorizedProviderPayloadProjectionV1,
    CanonicalDeepAnalysisInputV1,
    ContextBudgetProfileV1,
    DeepAnalysisDispatchEnvelopeV1,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisFailureCode,
    DeepAnalysisFailureStage,
    DeepAnalysisFailureV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisRequestProjectionV1,
    DeepAnalysisStructuredOutputMode,
    PayloadConsentIdentityV1,
    SelectedEvidenceProjectionV1,
    TrustedDeepAnalysisSuccess,
    UntrustedDeepAnalysisResponseV1,
    dacs1_sha256,
)
from youtube_intel.domain import (
    EvidenceRegistry,
    KnowledgeContent,
    ScoringLanguageValidation,
    detect_scoring_language_violation,
)
from youtube_intel.scoring import VerifiedScoringRead


class VerifiedDeepAnalysisInput:
    """Opaque runtime admission for a canonical input.

    Construction and object shape never establish authority.  Consumers must
    ask the owning runtime to verify the live process-local admission.
    """

    __slots__ = ("_canonical_input", "_sealed", "__weakref__")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("VerifiedDeepAnalysisInput cannot be subclassed")

    def __init__(self) -> None:
        raise TypeError("VerifiedDeepAnalysisInput is runtime-admitted only")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("VerifiedDeepAnalysisInput is immutable")
        object.__setattr__(self, name, value)


class AuthorizedDeepAnalysisPayload:
    """Opaque proof that the runtime constructed this exact payload projection."""

    __slots__ = ("_payload", "_sealed", "__weakref__")
    _payload: AuthorizedProviderPayloadProjectionV1
    _sealed: bool

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("AuthorizedDeepAnalysisPayload cannot be subclassed")

    def __init__(self) -> None:
        raise TypeError("AuthorizedDeepAnalysisPayload is runtime-authorized only")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("AuthorizedDeepAnalysisPayload is immutable")
        object.__setattr__(self, name, value)

    @property
    def payload(self) -> AuthorizedProviderPayloadProjectionV1:
        return self._payload


class PreparedDeepAnalysisDispatch:
    """Opaque proof that a dispatch envelope passed runtime preparation."""

    __slots__ = ("_envelope", "_sealed", "__weakref__")
    _envelope: DeepAnalysisDispatchEnvelopeV1
    _sealed: bool

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("PreparedDeepAnalysisDispatch cannot be subclassed")

    def __init__(self) -> None:
        raise TypeError("PreparedDeepAnalysisDispatch is runtime-prepared only")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("PreparedDeepAnalysisDispatch is immutable")
        object.__setattr__(self, name, value)

    @property
    def envelope(self) -> DeepAnalysisDispatchEnvelopeV1:
        return self._envelope


class DeepAnalysisResponseMetadataV1(BaseModel):
    """The provider-neutral, qualified response fields needed before parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(pattern=r"\S")
    dispatch_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_id: str = Field(min_length=1, pattern=r"\S")
    adapter_identity: str = Field(min_length=1, pattern=r"\S")
    adapter_version: str = Field(min_length=1, pattern=r"\S")
    endpoint_deployment_profile_identity: str = Field(min_length=1, pattern=r"\S")
    model_id: str = Field(min_length=1, pattern=r"\S")
    resolved_revision: str | None = None
    structured_output_mode: str = Field(min_length=1, pattern=r"\S")
    a1_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    a2_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    a3_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    scoring_request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_policy_identity: str = Field(min_length=1, pattern=r"\S")
    tool_name: str | None = None


@dataclass(frozen=True)
class DeepAnalysisValidationResult:
    """Exactly one terminal result; failures never carry a trusted success."""

    success: TrustedDeepAnalysisSuccess | None = None
    failure: DeepAnalysisFailureV1 | None = None

    def __post_init__(self) -> None:
        if (self.success is None) == (self.failure is None):
            raise ValueError("validation result must contain exactly one terminal outcome")


@dataclass(frozen=True)
class _PayloadAdmission:
    payload: AuthorizedProviderPayloadProjectionV1
    evidence_registry: EvidenceRegistry


@dataclass(frozen=True)
class _PreparedAdmission:
    envelope: DeepAnalysisDispatchEnvelopeV1
    evidence_registry: EvidenceRegistry
    validation_policy_identity: str


@dataclass(frozen=True)
class _TrustedAdmission:
    content_identity: str
    cache_identity: str
    provenance_identity: str


def _make_success_admission_authority() -> tuple[
    Callable[[TrustedDeepAnalysisSuccess, _TrustedAdmission], None],
    Callable[[object], bool],
]:
    """Keep live successful-admission state out of a mutable module registry."""

    admissions: WeakKeyDictionary[TrustedDeepAnalysisSuccess, _TrustedAdmission] = (
        WeakKeyDictionary()
    )

    def record(
        value: TrustedDeepAnalysisSuccess,
        admission: _TrustedAdmission,
    ) -> None:
        admissions[value] = admission

    def verify(value: object) -> bool:
        if type(value) is not TrustedDeepAnalysisSuccess:
            return False
        admission = admissions.get(value)
        if admission is None:
            return False
        return (
            value.content_identity == admission.content_identity
            and value.cache_identity == admission.cache_identity
            and value.provenance_identity == admission.provenance_identity
            and getattr(value, "_sealed", False)
        )

    return record, verify


_record_finalized_success, _verify_finalized_success = _make_success_admission_authority()


class DeepAnalysisRuntime:
    """Owns the in-memory authority boundary for one Deep Analysis runtime."""

    def __init__(
        self,
        *,
        validation_policy_identity: str = "deep-analysis-validation-policy-v1",
    ) -> None:
        if not validation_policy_identity.strip():
            raise ValueError("validation_policy_identity must be non-empty")
        self._validation_policy_identity = validation_policy_identity
        self._admitted_inputs: WeakKeyDictionary[
            VerifiedDeepAnalysisInput, CanonicalDeepAnalysisInputV1
        ] = WeakKeyDictionary()
        self._authorized_payloads: WeakKeyDictionary[
            AuthorizedDeepAnalysisPayload, _PayloadAdmission
        ] = WeakKeyDictionary()
        self._prepared_dispatches: WeakKeyDictionary[
            PreparedDeepAnalysisDispatch, _PreparedAdmission
        ] = WeakKeyDictionary()

    def admit_verified_scoring_read(
        self,
        *,
        verified_scoring_read: object,
        canonical_input: CanonicalDeepAnalysisInputV1,
    ) -> VerifiedDeepAnalysisInput:
        """Bind an actual verified read to a rebuilt canonical input.

        The request hash is re-derived from the trusted reader result; neither a
        caller-provided hash nor a provenance label grants this admission.
        """

        if type(verified_scoring_read) is not VerifiedScoringRead:
            raise ValueError("authoritative input requires exact VerifiedScoringRead")
        rebuilt = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
            verified_scoring_read=verified_scoring_read,
            **canonical_input.model_dump(mode="python"),
        )
        if rebuilt.scoring_request_hash != verified_scoring_read.scoring_outcome.result.request_hash:
            raise ValueError("canonical input scoring request hash is not reader-bound")
        if rebuilt.scoring_success_provenance != verified_scoring_read.scoring_success_provenance:
            raise ValueError("canonical input scoring provenance is not reader-bound")

        admitted = object.__new__(VerifiedDeepAnalysisInput)
        object.__setattr__(admitted, "_canonical_input", rebuilt)
        object.__setattr__(admitted, "_sealed", True)
        self._admitted_inputs[admitted] = rebuilt
        return admitted

    def verify_authoritative_input(self, value: object) -> bool:
        """Return true only for this runtime's live admitted object."""

        if type(value) is not VerifiedDeepAnalysisInput:
            return False
        return value in self._admitted_inputs

    def authorize_payload(
        self,
        *,
        authoritative_input: object,
        evidence_registry: EvidenceRegistry,
        payload_scope: DeepAnalysisPayloadScope,
        payload_consent: PayloadConsentIdentityV1,
        video_title: str,
        channel_name: str,
        published_at: str,
        duration_seconds: int,
        source_language: str,
        public_description: str = "",
        transcript_text: str | None = None,
        transcript_content_hash: str | None = None,
        transcript_normalization_version: str | None = None,
    ) -> AuthorizedDeepAnalysisPayload:
        """Create the closed provider-visible projection from admitted state."""

        if not isinstance(authoritative_input, VerifiedDeepAnalysisInput):
            raise ValueError("payload authorization requires runtime-authoritative input")
        if not self.verify_authoritative_input(authoritative_input):
            raise ValueError("payload authorization requires runtime-authoritative input")
        if type(evidence_registry) is not EvidenceRegistry:
            raise ValueError("payload authorization requires exact EvidenceRegistry")
        canonical_input = self._admitted_inputs[authoritative_input]
        registry = EvidenceRegistry.model_validate(evidence_registry.model_dump(mode="python"))
        expected_items = canonical_input.selected_evidence
        actual_items = tuple(
            SelectedEvidenceProjectionV1(
                schema_version="selected-evidence-projection-v1",
                evidence_id=item.evidence_id,
                source=item.source.value,
                excerpt=item.excerpt,
            )
            for item in registry.items
        )
        if actual_items != expected_items:
            raise ValueError("EvidenceRegistry is not the exact canonical selected evidence")
        if payload_scope is not payload_consent.payload_scope:
            raise ValueError("payload scope does not match payload consent")
        if payload_scope is DeepAnalysisPayloadScope.FULL_TRANSCRIPT:
            if not canonical_input.coverage_complete:
                raise ValueError("FULL_TRANSCRIPT requires complete canonical coverage")
            if any(
                value is None
                for value in (
                    transcript_text,
                    transcript_content_hash,
                    transcript_normalization_version,
                )
            ):
                raise ValueError("FULL_TRANSCRIPT requires its explicit transcript fields")
        elif any(
            value is not None
            for value in (
                transcript_text,
                transcript_content_hash,
                transcript_normalization_version,
            )
        ):
            raise ValueError("SELECTED_EVIDENCE_ONLY forbids transcript fields")

        payload = AuthorizedProviderPayloadProjectionV1(
            schema_version="authorized-provider-payload-projection-v1",
            payload_scope=payload_scope,
            output_language=canonical_input.output_language,
            video_title=video_title,
            channel_name=channel_name,
            published_at=published_at,
            duration_seconds=duration_seconds,
            source_language=source_language,
            public_description=public_description,
            selected_evidence=actual_items,
            transcript_text=transcript_text,
            transcript_content_hash=transcript_content_hash,
            transcript_normalization_version=transcript_normalization_version,
        )
        authorized = object.__new__(AuthorizedDeepAnalysisPayload)
        object.__setattr__(authorized, "_payload", payload)
        object.__setattr__(authorized, "_sealed", True)
        self._authorized_payloads[authorized] = _PayloadAdmission(
            payload=payload, evidence_registry=registry
        )
        return authorized

    def prepare_dispatch(
        self,
        *,
        authoritative_input: object,
        authorized_payload: object,
        request_projection: DeepAnalysisRequestProjectionV1,
        execution_profile: DeepAnalysisExecutionProfileV1,
        payload_consent: PayloadConsentIdentityV1,
        context_budget_profile: ContextBudgetProfileV1,
        timeout_profile_identity: str,
        fallback_policy_identity: str,
    ) -> PreparedDeepAnalysisDispatch:
        """Recompute A1/A2/A3 bindings and issue a non-dispatching envelope."""

        if not isinstance(authoritative_input, VerifiedDeepAnalysisInput) or not self.verify_authoritative_input(authoritative_input):
            raise ValueError("dispatch preparation requires runtime-authoritative input")
        if not isinstance(authorized_payload, AuthorizedDeepAnalysisPayload) or authorized_payload not in self._authorized_payloads:
            raise ValueError("dispatch preparation requires runtime-authorized payload")
        canonical = self._admitted_inputs[authoritative_input]
        payload_admission = self._authorized_payloads[authorized_payload]
        request = DeepAnalysisRequestProjectionV1.model_validate(
            request_projection.model_dump(mode="python", by_alias=True)
        )
        execution = DeepAnalysisExecutionProfileV1.model_validate(execution_profile.model_dump(mode="python"))
        consent = PayloadConsentIdentityV1.model_validate(payload_consent.model_dump(mode="python"))
        context = ContextBudgetProfileV1.model_validate(context_budget_profile.model_dump(mode="python"))
        if request.a1_identity != canonical.a1_identity:
            raise ValueError("request projection A1 is not runtime-derived")
        if request.authorized_payload != payload_admission.payload:
            raise ValueError("request projection payload is not runtime-authorized")
        if request.payload_consent_identity != consent.identity:
            raise ValueError("request projection consent is not runtime-authorized")
        envelope = DeepAnalysisDispatchEnvelopeV1(
            schema_version="deep-analysis-dispatch-envelope-v1",
            canonical_input=canonical,
            request_projection=request,
            execution_profile=execution,
            payload_consent=consent,
            context_budget_profile=context,
            timeout_profile_identity=timeout_profile_identity,
            fallback_policy_identity=fallback_policy_identity,
            prompt_identity=request.prompt_identity,
            schema_identity=request.knowledge_content_schema_identity,
        )
        prepared = object.__new__(PreparedDeepAnalysisDispatch)
        object.__setattr__(prepared, "_envelope", envelope)
        object.__setattr__(prepared, "_sealed", True)
        self._prepared_dispatches[prepared] = _PreparedAdmission(
            envelope=envelope,
            evidence_registry=payload_admission.evidence_registry,
            validation_policy_identity=self._validation_policy_identity,
        )
        return prepared

    def validation_finalizer(self) -> DeepAnalysisValidationFinalizer:
        return DeepAnalysisValidationFinalizer(self)

    def _prepared_admission(self, value: object) -> _PreparedAdmission | None:
        if type(value) is not PreparedDeepAnalysisDispatch:
            return None
        return self._prepared_dispatches.get(value)


class DeepAnalysisValidationFinalizer:
    """The sole successful-admission owner for a prepared runtime dispatch."""

    def __init__(self, runtime: DeepAnalysisRuntime) -> None:
        self._runtime = runtime

    def finalize(
        self,
        *,
        prepared_dispatch: object,
        response: object,
        _record_success: Callable[[TrustedDeepAnalysisSuccess, _TrustedAdmission], None] = _record_finalized_success,
    ) -> DeepAnalysisValidationResult:
        admission = self._runtime._prepared_admission(prepared_dispatch)
        if admission is None:
            return _failure(DeepAnalysisFailureStage.PROVENANCE, DeepAnalysisFailureCode.PROVENANCE_INVALID)
        if type(response) is not UntrustedDeepAnalysisResponseV1:
            return _failure(DeepAnalysisFailureStage.RESPONSE_ENVELOPE, DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID)
        envelope = admission.envelope
        if response.delivery_certainty == "NOT_SENT":
            return _failure(DeepAnalysisFailureStage.TRANSPORT, DeepAnalysisFailureCode.NETWORK_FAILURE)
        if response.delivery_certainty != "CONFIRMED":
            return _failure(DeepAnalysisFailureStage.TRANSPORT, DeepAnalysisFailureCode.TIMEOUT)
        metadata = _validated_metadata(response.response_metadata)
        if metadata is None:
            return _failure(DeepAnalysisFailureStage.RESPONSE_ENVELOPE, DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID)
        if not _matches_early_dispatch_binding(envelope, response, metadata):
            return _failure(DeepAnalysisFailureStage.PROVENANCE, DeepAnalysisFailureCode.PROVENANCE_INVALID)
        extracted = _extract_payload(envelope, metadata, response)
        if isinstance(extracted, DeepAnalysisFailureV1):
            return DeepAnalysisValidationResult(failure=extracted)
        try:
            content = KnowledgeContent.model_validate(extracted)
        except Exception:
            return _failure(DeepAnalysisFailureStage.SCHEMA, DeepAnalysisFailureCode.SCHEMA_INVALID)
        if not _grounded_in_registry(content, admission.evidence_registry):
            return _failure(DeepAnalysisFailureStage.GROUNDING, DeepAnalysisFailureCode.GROUNDING_INVALID)
        if not _kg2_valid(content):
            return _failure(DeepAnalysisFailureStage.KG2, DeepAnalysisFailureCode.KG2_INVALID)
        if not _language_valid(content, envelope.request_projection.output_language):
            return _failure(DeepAnalysisFailureStage.LANGUAGE, DeepAnalysisFailureCode.OUTPUT_LANGUAGE_INVALID)
        content_identity = dacs1_sha256({
            "schema_version": "trusted-deep-analysis-content-v1",
            "content": content.model_dump(mode="json"),
        })
        if not _final_provenance_matches(admission, metadata, response):
            return _failure(DeepAnalysisFailureStage.PROVENANCE, DeepAnalysisFailureCode.PROVENANCE_INVALID)
        success = object.__new__(TrustedDeepAnalysisSuccess)
        cache_identity = dacs1_sha256({
            "schema_version": "deep-analysis-runtime-cache-binding-v1",
            "A1": envelope.a1_identity,
            "A2": envelope.a2_identity,
            "A3": envelope.a3_identity,
            "content_identity": content_identity,
            "response_identity": response.provider_envelope_identity,
        })
        object.__setattr__(success, "_content_identity", content_identity)
        object.__setattr__(success, "_cache_identity", cache_identity)
        object.__setattr__(success, "_provenance_identity", dacs1_sha256({
            "schema_version": "trusted-deep-analysis-provenance-v1",
            "A1": envelope.a1_identity,
            "A2": envelope.a2_identity,
            "A3": envelope.a3_identity,
            "scoring_request_hash": envelope.canonical_input.scoring_request_hash,
            "scoring_success_provenance": envelope.canonical_input.scoring_success_provenance,
            "evidence_registry_identity": envelope.canonical_input.evidence_registry_identity,
            "payload_scope": envelope.request_projection.payload_scope.value,
            "payload_consent_identity": envelope.payload_consent.identity,
            "provider_envelope_identity": response.provider_envelope_identity,
            "payload_identity": response.structured_payload_identity,
            "validation_policy_identity": admission.validation_policy_identity,
            "content_identity": content_identity,
        }))
        object.__setattr__(success, "_sealed", True)
        _record_success(success, _TrustedAdmission(
            content_identity=content_identity,
            cache_identity=cache_identity,
            provenance_identity=success.provenance_identity,
        ))
        return DeepAnalysisValidationResult(success=success)


# The successful-admission writer is captured only by the finalizer method.
# Public verification has no caller-importable registration/mint seam.
del _record_finalized_success


def _failure(stage: DeepAnalysisFailureStage, code: DeepAnalysisFailureCode) -> DeepAnalysisValidationResult:
    return DeepAnalysisValidationResult(
        failure=DeepAnalysisFailureV1(schema_version="deep-analysis-failure-v1", stage=stage, code=code)
    )


def _validated_metadata(value: object | None) -> DeepAnalysisResponseMetadataV1 | None:
    if not isinstance(value, Mapping):
        return None
    try:
        return DeepAnalysisResponseMetadataV1.model_validate(dict(value))
    except Exception:
        return None


def _matches_early_dispatch_binding(
    envelope: DeepAnalysisDispatchEnvelopeV1,
    response: UntrustedDeepAnalysisResponseV1,
    metadata: DeepAnalysisResponseMetadataV1,
) -> bool:
    model = envelope.execution_profile.model_selection
    return all((
        response.expected_dispatch_identity == envelope.semantic_identity,
        metadata.dispatch_identity == envelope.semantic_identity,
        metadata.provider_id == envelope.execution_profile.provider_id,
        metadata.adapter_identity == envelope.execution_profile.adapter_identity,
        metadata.adapter_version == envelope.execution_profile.adapter_version,
        metadata.endpoint_deployment_profile_identity == envelope.execution_profile.endpoint_deployment_profile_identity,
        metadata.model_id == model.model_id,
        metadata.resolved_revision == model.resolved_revision,
        metadata.structured_output_mode == envelope.request_projection.structured_output.mode.value,
        metadata.a1_identity == envelope.a1_identity,
        metadata.a2_identity == envelope.a2_identity,
        metadata.a3_identity == envelope.a3_identity,
        metadata.scoring_request_hash == envelope.canonical_input.scoring_request_hash,
    ))


def _extract_payload(
    envelope: DeepAnalysisDispatchEnvelopeV1,
    metadata: DeepAnalysisResponseMetadataV1,
    response: UntrustedDeepAnalysisResponseV1,
) -> object | DeepAnalysisFailureV1:
    mode = envelope.request_projection.structured_output.mode
    payload = response.structured_payload
    if mode in {DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT, DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE}:
        if not isinstance(payload, bytes):
            return _failure_value(DeepAnalysisFailureStage.STRUCTURED_OUTPUT, DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID)
        return _parse_strict_json(payload)
    if mode is DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA:
        if isinstance(payload, bytes):
            return _parse_strict_json(payload)
        if not isinstance(payload, Mapping):
            return _failure_value(DeepAnalysisFailureStage.STRUCTURED_OUTPUT, DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID)
        return dict(payload)
    expected_tool = envelope.request_projection.structured_output.tool_choice
    if not isinstance(expected_tool, str) or metadata.tool_name != expected_tool or not isinstance(payload, Mapping):
        return _failure_value(DeepAnalysisFailureStage.STRUCTURED_OUTPUT, DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID)
    return dict(payload)


def _failure_value(stage: DeepAnalysisFailureStage, code: DeepAnalysisFailureCode) -> DeepAnalysisFailureV1:
    return DeepAnalysisFailureV1(schema_version="deep-analysis-failure-v1", stage=stage, code=code)


def _parse_strict_json(payload: bytes) -> object | DeepAnalysisFailureV1:
    try:
        text = payload.decode("utf-8")
        decoder = json.JSONDecoder(parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        start = len(text) - len(text.lstrip())
        value, end = decoder.raw_decode(text, start)
        if text[end:].strip():
            raise ValueError("trailing non-whitespace data")
        return cast(object, value)
    except Exception:
        return _failure_value(DeepAnalysisFailureStage.STRUCTURED_OUTPUT, DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID)


def _grounded_in_registry(content: KnowledgeContent, registry: EvidenceRegistry) -> bool:
    allowed = {item.evidence_id for item in registry.items}
    references = set(content.summary_evidence_ids)
    for point in (content.why_it_matters, *content.core_points, *content.key_facts, *content.important_concepts, *content.key_arguments, *content.counterpoints, *content.product_opportunities, *content.business_opportunities, *content.actionable_directions, *content.hypotheses_to_validate, *content.action_recommendations, *content.risks):
        references.update(point.evidence_ids)
    return references.issubset(allowed)


def _kg2_valid(content: KnowledgeContent) -> bool:
    try:
        type(content.knowledge_graph).model_validate(content.knowledge_graph.model_dump(mode="python"))
        return True
    except Exception:
        return False


def _language_valid(content: KnowledgeContent, output_language: str) -> bool:
    if output_language not in {"en", "zh-CN"}:
        return False
    text = " ".join((
        content.one_sentence_summary,
        content.why_it_matters.text,
        *(point.text for point in content.core_points),
    ))
    language: Literal["en", "zh-CN"] = "en" if output_language == "en" else "zh-CN"
    return detect_scoring_language_violation(text, language) is ScoringLanguageValidation.VALID


def _final_provenance_matches(
    admission: _PreparedAdmission,
    metadata: DeepAnalysisResponseMetadataV1,
    response: UntrustedDeepAnalysisResponseV1,
) -> bool:
    envelope = admission.envelope
    return (
        bool(response.provider_envelope_identity)
        and bool(response.structured_payload_identity)
        and metadata.validation_policy_identity == admission.validation_policy_identity
        and _matches_early_dispatch_binding(envelope, response, metadata)
    )


def _verify_trusted_deep_analysis_success(value: object) -> bool:
    return _verify_finalized_success(value)
