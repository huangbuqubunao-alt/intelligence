"""Pure, provider-neutral Deep Analysis foundational contracts (P0).

This module deliberately contains no provider adapter, credentials, transport,
cache storage, or validator/finalizer pipeline.  It owns only immutable domain
objects, canonical identities, and fail-closed fallback-policy validation.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from enum import Enum
from types import MappingProxyType
from typing import Final, Literal, Never, NoReturn, Self
from typing import Mapping as TypingMapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from youtube_intel.h2_jcs import jcs_serialize

_FROZEN: Final = ConfigDict(extra="forbid", frozen=True)
_SHA256 = r"^[0-9a-f]{64}$"


class _ContractModel(BaseModel):
    """Frozen, closed models used only for the provider-neutral contract."""

    model_config = _FROZEN

    def model_copy(
        self,
        *,
        update: TypingMapping[str, Never] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            raise ValueError("model_copy(update=...) is disabled for Deep Analysis contracts")
        return super().model_copy(deep=deep)


class DeepAnalysisProviderKind(str, Enum):
    """The complete provider-kind set; provider kind is never a trust level."""

    LOCAL = "LOCAL"
    CLOUD_FREE = "CLOUD_FREE"
    CLOUD_USER_KEY = "CLOUD_USER_KEY"


class DeepAnalysisStructuredOutputMode(str, Enum):
    RAW_JSON_PROMPT = "RAW_JSON_PROMPT"
    PROVIDER_JSON_MODE = "PROVIDER_JSON_MODE"
    PROVIDER_JSON_SCHEMA = "PROVIDER_JSON_SCHEMA"
    TOOL_STRUCTURED_RETURN = "TOOL_STRUCTURED_RETURN"


class DeepAnalysisModelIdentityClass(str, Enum):
    IMMUTABLE = "IMMUTABLE"
    VERSIONED = "VERSIONED"
    FLOATING = "FLOATING"


class DeepAnalysisContextAuthorityKind(str, Enum):
    EXACT_LOCAL_TOKENIZER = "EXACT_LOCAL_TOKENIZER"
    PROVIDER_DOCUMENTED_TOKENIZER = "PROVIDER_DOCUMENTED_TOKENIZER"
    CONSERVATIVE_PROVIDER_CONTRACT = "CONSERVATIVE_PROVIDER_CONTRACT"


class DeepAnalysisPayloadScope(str, Enum):
    SELECTED_EVIDENCE_ONLY = "SELECTED_EVIDENCE_ONLY"
    FULL_TRANSCRIPT = "FULL_TRANSCRIPT"


class PayloadConsentMode(str, Enum):
    LOCAL_ONLY = "local_only"
    CLOUD_EXPLICIT = "cloud_explicit"
    CLOUD_PRE_AUTHORIZED = "cloud_pre_authorized"
    PER_RUN_CLOUD_APPROVAL = "per_run_cloud_approval"


class CacheEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE_FLOATING_MODEL = "INELIGIBLE_FLOATING_MODEL"


class DeepAnalysisFailureStage(str, Enum):
    PRE_DISPATCH = "PRE_DISPATCH"
    TRANSPORT = "TRANSPORT"
    PROVIDER_ACCOUNT = "PROVIDER_ACCOUNT"
    PROVIDER_MODEL = "PROVIDER_MODEL"
    RESPONSE_ENVELOPE = "RESPONSE_ENVELOPE"
    PROVENANCE = "PROVENANCE"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    SCHEMA = "SCHEMA"
    DOMAIN = "DOMAIN"
    GROUNDING = "GROUNDING"
    KG2 = "KG2"
    LANGUAGE = "LANGUAGE"
    UNKNOWN = "UNKNOWN"


class DeepAnalysisFailureCode(str, Enum):
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    TIMEOUT = "TIMEOUT"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    CAPABILITY_UNSUPPORTED = "CAPABILITY_UNSUPPORTED"
    CONTEXT_BUDGET_EXCEEDED = "CONTEXT_BUDGET_EXCEEDED"
    INVALID_FALLBACK_POLICY = "INVALID_FALLBACK_POLICY"
    PROVIDER_ENVELOPE_INVALID = "PROVIDER_ENVELOPE_INVALID"
    STRUCTURED_OUTPUT_INVALID = "STRUCTURED_OUTPUT_INVALID"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    DOMAIN_INVALID = "DOMAIN_INVALID"
    GROUNDING_INVALID = "GROUNDING_INVALID"
    KG2_INVALID = "KG2_INVALID"
    OUTPUT_LANGUAGE_INVALID = "OUTPUT_LANGUAGE_INVALID"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"
    UNKNOWN = "UNKNOWN"


_FAILURE_STAGES_BY_CODE: Final[Mapping[DeepAnalysisFailureCode, frozenset[DeepAnalysisFailureStage]]] = MappingProxyType(
    {
        DeepAnalysisFailureCode.AUTH_REQUIRED: frozenset({DeepAnalysisFailureStage.PRE_DISPATCH}),
        DeepAnalysisFailureCode.CAPABILITY_UNSUPPORTED: frozenset({DeepAnalysisFailureStage.PRE_DISPATCH}),
        DeepAnalysisFailureCode.CONTEXT_BUDGET_EXCEEDED: frozenset({DeepAnalysisFailureStage.PRE_DISPATCH}),
        DeepAnalysisFailureCode.INVALID_FALLBACK_POLICY: frozenset({DeepAnalysisFailureStage.PRE_DISPATCH}),
        DeepAnalysisFailureCode.NETWORK_FAILURE: frozenset({DeepAnalysisFailureStage.TRANSPORT}),
        DeepAnalysisFailureCode.TIMEOUT: frozenset({DeepAnalysisFailureStage.TRANSPORT}),
        DeepAnalysisFailureCode.AUTH_INVALID: frozenset({DeepAnalysisFailureStage.PROVIDER_ACCOUNT}),
        DeepAnalysisFailureCode.QUOTA_EXCEEDED: frozenset({DeepAnalysisFailureStage.PROVIDER_ACCOUNT}),
        DeepAnalysisFailureCode.RATE_LIMITED: frozenset({DeepAnalysisFailureStage.PROVIDER_ACCOUNT}),
        DeepAnalysisFailureCode.MODEL_UNAVAILABLE: frozenset({DeepAnalysisFailureStage.PROVIDER_MODEL}),
        DeepAnalysisFailureCode.PROVIDER_UNAVAILABLE: frozenset({DeepAnalysisFailureStage.PRE_DISPATCH, DeepAnalysisFailureStage.PROVIDER_MODEL}),
        DeepAnalysisFailureCode.PROVIDER_ENVELOPE_INVALID: frozenset({DeepAnalysisFailureStage.RESPONSE_ENVELOPE}),
        DeepAnalysisFailureCode.PROVENANCE_INVALID: frozenset({DeepAnalysisFailureStage.PROVENANCE}),
        DeepAnalysisFailureCode.STRUCTURED_OUTPUT_INVALID: frozenset({DeepAnalysisFailureStage.STRUCTURED_OUTPUT}),
        DeepAnalysisFailureCode.SCHEMA_INVALID: frozenset({DeepAnalysisFailureStage.SCHEMA}),
        DeepAnalysisFailureCode.DOMAIN_INVALID: frozenset({DeepAnalysisFailureStage.DOMAIN}),
        DeepAnalysisFailureCode.GROUNDING_INVALID: frozenset({DeepAnalysisFailureStage.GROUNDING}),
        DeepAnalysisFailureCode.KG2_INVALID: frozenset({DeepAnalysisFailureStage.KG2}),
        DeepAnalysisFailureCode.OUTPUT_LANGUAGE_INVALID: frozenset({DeepAnalysisFailureStage.LANGUAGE}),
        DeepAnalysisFailureCode.UNKNOWN: frozenset({DeepAnalysisFailureStage.UNKNOWN}),
    }
)
FAILURE_PRECEDENCE: Final[tuple[DeepAnalysisFailureStage, ...]] = tuple(DeepAnalysisFailureStage)


def _dacs_value(value: object) -> object:
    """Convert immutable contract data to JCS-compatible JSON without coercion."""

    if isinstance(value, BaseModel):
        return _dacs_value(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("DACS-1 object keys must be strings")
            normalized[key] = _dacs_value(item)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_dacs_value(item) for item in value]
    raise ValueError(f"DACS-1 does not support {type(value).__name__}")


def _freeze_json(value: object) -> object:
    """Make arbitrary JSON-shaped provider semantics recursively immutable."""

    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("provider-semantic object keys must be strings")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_json(item) for item in value)
    raise ValueError(f"provider-semantic value must be JSON-shaped, got {type(value).__name__}")


def canonical_dacs1_bytes(value: object) -> bytes:
    """Return DACS-1 bytes for a versioned top-level JSON object.

    DACS-1 uses the same RFC 8785 serialization algorithm as the project's
    existing dependency-free JCS implementation, while remaining a separately
    versioned Deep Analysis contract.
    """

    canonical_value = _dacs_value(value)
    if not isinstance(canonical_value, dict) or not isinstance(canonical_value.get("schema_version"), str):
        raise ValueError("DACS-1 top-level value requires string schema_version")
    if len(canonical_value["schema_version"]) == 0:
        raise ValueError("DACS-1 schema_version must be non-empty")
    return jcs_serialize(canonical_value)


def dacs1_sha256(value: object) -> str:
    return hashlib.sha256(canonical_dacs1_bytes(value)).hexdigest()


def _identity_data(model: _ContractModel) -> dict[str, object]:
    return model.model_dump(mode="python", by_alias=True)


class DeepAnalysisModelIdentityV1(_ContractModel):
    schema_version: Literal["deep-analysis-model-identity-v1"]
    model_id: str = Field(min_length=1, pattern=r"\S")
    identity_class: DeepAnalysisModelIdentityClass
    resolved_revision: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _resolved_identity_matches_class(self) -> Self:
        if self.identity_class is DeepAnalysisModelIdentityClass.FLOATING and self.resolved_revision is not None:
            raise ValueError("FLOATING model identity must not claim a resolved revision")
        if self.identity_class is not DeepAnalysisModelIdentityClass.FLOATING and self.resolved_revision is None:
            raise ValueError("IMMUTABLE and VERSIONED model identities require resolved_revision")
        return self

    @property
    def cache_eligibility(self) -> CacheEligibility:
        return CacheEligibility.INELIGIBLE_FLOATING_MODEL if self.identity_class is DeepAnalysisModelIdentityClass.FLOATING else CacheEligibility.ELIGIBLE

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class CredentialExecutionProfileIdentityV1(_ContractModel):
    """Opaque, structurally non-secret execution-profile identity.

    The trusted configuration boundary provides only a one-way profile digest;
    raw account, organization, deployment, policy, reference, and credential
    values have no field in this serializable domain model.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["credential-execution-profile-v1"]
    provider_id: str = Field(min_length=1, pattern=r"\S")
    execution_profile_identity: str = Field(pattern=_SHA256)

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class DeepAnalysisProviderCapabilities(_ContractModel):
    schema_version: Literal["deep-analysis-provider-capabilities-v1"]
    provider_kind: DeepAnalysisProviderKind
    provider_id: str = Field(min_length=1, pattern=r"\S")
    supports_raw_json_prompt: bool
    supports_json_mode: bool
    supports_json_schema: bool
    supports_tool_structured_return: bool
    declared_capability_profile_identity: str = Field(min_length=1, pattern=r"\S")
    qualified_capability_profile_identity: str | None = Field(default=None, min_length=1)

    @property
    def is_qualified(self) -> bool:
        return self.qualified_capability_profile_identity is not None


class PayloadConsentIdentityV1(_ContractModel):
    schema_version: Literal["payload-consent-identity-v1"]
    consent_mode: PayloadConsentMode
    authorization_record_identity: str = Field(min_length=1, pattern=r"\S")
    named_provider_id: str = Field(min_length=1, pattern=r"\S")
    provider_kind: DeepAnalysisProviderKind
    payload_scope: DeepAnalysisPayloadScope
    allowed_model_constraint: str = Field(min_length=1, pattern=r"\S")
    fallback_edge_identity_or_null: str | None = None
    exact_run_nonce_or_null: str | None = None

    @model_validator(mode="after")
    def _consent_is_explicit(self) -> Self:
        if self.consent_mode is PayloadConsentMode.PER_RUN_CLOUD_APPROVAL and self.exact_run_nonce_or_null is None:
            raise ValueError("per_run_cloud_approval requires exact_run_nonce_or_null")
        if self.consent_mode is PayloadConsentMode.LOCAL_ONLY and self.provider_kind is not DeepAnalysisProviderKind.LOCAL:
            raise ValueError("local_only consent permits only LOCAL")
        return self

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class SelectedEvidenceProjectionV1(_ContractModel):
    schema_version: Literal["selected-evidence-projection-v1"]
    evidence_id: str = Field(min_length=1, pattern=r"\S")
    source: str = Field(min_length=1, pattern=r"\S")
    excerpt: str = Field(min_length=1)


class AuthorizedProviderPayloadProjectionV1(_ContractModel):
    schema_version: Literal["authorized-provider-payload-projection-v1"]
    payload_scope: DeepAnalysisPayloadScope
    output_language: str = Field(min_length=1, pattern=r"\S")
    video_title: str = Field(min_length=1)
    channel_name: str = Field(min_length=1)
    published_at: str = Field(min_length=1, pattern=r"\S")
    duration_seconds: int = Field(ge=0)
    source_language: str = Field(min_length=1, pattern=r"\S")
    public_description: str = ""
    selected_evidence: tuple[SelectedEvidenceProjectionV1, ...] = Field(min_length=1)
    transcript_text: str | None = None
    transcript_content_hash: str | None = Field(default=None, pattern=_SHA256)
    transcript_normalization_version: str | None = None

    @model_validator(mode="after")
    def _scope_controls_transcript(self) -> Self:
        full_fields = (self.transcript_text, self.transcript_content_hash, self.transcript_normalization_version)
        if self.payload_scope is DeepAnalysisPayloadScope.FULL_TRANSCRIPT and any(field is None for field in full_fields):
            raise ValueError("FULL_TRANSCRIPT requires transcript text, hash, and normalization version")
        if self.payload_scope is DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY and any(field is not None for field in full_fields):
            raise ValueError("SELECTED_EVIDENCE_ONLY must not carry transcript data")
        return self


class CanonicalDeepAnalysisInputV1(_ContractModel):
    """A1 input constructed only from an authoritative scoring-read object."""

    schema_version: Literal["canonical-deep-analysis-input-v1"]
    operation: str = Field(min_length=1, pattern=r"\S")
    input_schema_version: str = Field(min_length=1, pattern=r"\S")
    video_identity: str = Field(min_length=1, pattern=r"\S")
    transcript_identity: str = Field(min_length=1, pattern=r"\S")
    transcript_language: str = Field(min_length=1, pattern=r"\S")
    transcript_normalization_version: str = Field(min_length=1, pattern=r"\S")
    evidence_registry_identity: str = Field(min_length=1, pattern=r"\S")
    selected_evidence: tuple[SelectedEvidenceProjectionV1, ...] = Field(min_length=1)
    selection_policy_identity: str = Field(min_length=1, pattern=r"\S")
    coverage_policy_identity: str = Field(min_length=1, pattern=r"\S")
    coverage_complete: bool
    scoring_request_hash: str = Field(pattern=_SHA256)
    scoring_success_provenance: Literal["PRIMARY", "REPAIR_H2C"]
    output_language: str = Field(min_length=1, pattern=r"\S")
    knowledge_content_schema_version: str = Field(min_length=1, pattern=r"\S")
    prompt_version: str = Field(min_length=1, pattern=r"\S")
    operation_version: str = Field(min_length=1, pattern=r"\S")

    @model_validator(mode="before")
    @classmethod
    def _derive_scoring_binding_only_from_verified_read(cls, value: object) -> object:
        from youtube_intel.scoring import VerifiedScoringRead

        if not isinstance(value, Mapping):
            raise ValueError("CanonicalDeepAnalysisInputV1 requires object input")
        data = dict(value)
        verified_read = data.pop("__verified_scoring_read", None)
        if type(verified_read) is not VerifiedScoringRead:
            raise ValueError("CanonicalDeepAnalysisInputV1 requires exact VerifiedScoringRead")
        provenance = verified_read.scoring_success_provenance
        if provenance not in {"PRIMARY", "REPAIR_H2C"}:
            raise ValueError("VerifiedScoringRead scoring_success_provenance is invalid")
        request_hash = verified_read.scoring_outcome.result.request_hash
        if not isinstance(request_hash, str) or len(request_hash) != 64:
            raise ValueError("VerifiedScoringRead request_hash is invalid")
        supplied_hash = data.get("scoring_request_hash")
        supplied_provenance = data.get("scoring_success_provenance")
        if supplied_hash is not None and supplied_hash != request_hash:
            raise ValueError("caller-supplied scoring request hash does not match VerifiedScoringRead")
        if supplied_provenance is not None and supplied_provenance != provenance:
            raise ValueError("caller-supplied scoring provenance does not match VerifiedScoringRead")
        return {**data, "scoring_request_hash": request_hash, "scoring_success_provenance": provenance}

    @classmethod
    def from_verified_scoring_read(cls, *, verified_scoring_read: object, **data: object) -> Self:
        # Import lazily to preserve this module's pure-domain dependency edge.
        from youtube_intel.scoring import VerifiedScoringRead

        if type(verified_scoring_read) is not VerifiedScoringRead:
            raise ValueError("CanonicalDeepAnalysisInputV1 requires exact VerifiedScoringRead")
        return cls.model_validate({**data, "__verified_scoring_read": verified_scoring_read})

    def canonical_data(self) -> dict[str, object]:
        return _identity_data(self)

    @property
    def a1_identity(self) -> str:
        return dacs1_sha256(self.canonical_data())


class DeepAnalysisMessageV1(_ContractModel):
    schema_version: Literal["deep-analysis-message-v1"]
    role: str = Field(min_length=1, pattern=r"\S")
    content: str


class DeepAnalysisStructuredOutputV1(_ContractModel):
    schema_version: Literal["deep-analysis-structured-output-v1"]
    mode: DeepAnalysisStructuredOutputMode
    dialect_id: str = Field(min_length=1, pattern=r"\S")
    dialect_version: str = Field(min_length=1, pattern=r"\S")
    settings: object
    schema_object: object | None = Field(default=None, validation_alias="schema", serialization_alias="schema")
    tools: tuple[object, ...] | None = None
    tool_choice: object | None = None

    @field_validator("settings", "schema_object", "tool_choice", mode="after")
    @classmethod
    def _freeze_structured_json(cls, value: object) -> object:
        return _freeze_json(value)

    @field_validator("tools", mode="after")
    @classmethod
    def _freeze_tools(cls, value: tuple[object, ...] | None) -> tuple[object, ...] | None:
        return None if value is None else tuple(_freeze_json(item) for item in value)

    @model_validator(mode="after")
    def _mode_shape_is_closed(self) -> Self:
        if self.mode is DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT:
            if self.schema_object is not None or self.tools is not None or self.tool_choice is not None:
                raise ValueError("RAW_JSON_PROMPT forbids schema, tools, and tool choice")
        elif self.mode is DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE:
            if self.schema_object is not None or self.tools is not None or self.tool_choice is not None:
                raise ValueError("PROVIDER_JSON_MODE forbids schema, tools, and tool choice")
        elif self.mode is DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA:
            if self.schema_object is None:
                raise ValueError("PROVIDER_JSON_SCHEMA requires an exact schema")
            if self.tools is not None or self.tool_choice is not None:
                raise ValueError("PROVIDER_JSON_SCHEMA forbids tools and tool choice")
        elif self.mode is DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN:
            if self.schema_object is not None:
                raise ValueError("TOOL_STRUCTURED_RETURN forbids provider JSON schema")
            if not self.tools or self.tool_choice is None:
                raise ValueError("TOOL_STRUCTURED_RETURN requires tools and tool choice")
        else:
            raise ValueError("unknown structured-output mode")
        return self


class DeepAnalysisRequestProjectionV1(_ContractModel):
    schema_version: Literal["deep-analysis-request-projection-v1"]
    operation: str = Field(min_length=1, pattern=r"\S")
    a1_identity: str = Field(pattern=_SHA256)
    payload_consent_identity: str = Field(pattern=_SHA256)
    payload_scope: DeepAnalysisPayloadScope
    authorized_payload: AuthorizedProviderPayloadProjectionV1
    provider_visible_messages: tuple[DeepAnalysisMessageV1, ...] = Field(min_length=1)
    provider_visible_request_shape: object
    structured_output: DeepAnalysisStructuredOutputV1
    generation_semantics: object
    prompt_identity: str = Field(min_length=1, pattern=r"\S")
    knowledge_content_schema_identity: str = Field(min_length=1, pattern=r"\S")
    output_language: str = Field(min_length=1, pattern=r"\S")
    payload_projection_version: str = Field(min_length=1, pattern=r"\S")

    @field_validator("provider_visible_request_shape", "generation_semantics", mode="after")
    @classmethod
    def _freeze_request_json(cls, value: object) -> object:
        return _freeze_json(value)

    @model_validator(mode="after")
    def _projection_is_self_consistent(self) -> Self:
        if self.payload_scope is not self.authorized_payload.payload_scope:
            raise ValueError("request projection payload scope must match authorized payload")
        if self.output_language != self.authorized_payload.output_language:
            raise ValueError("request projection output language must match authorized payload")
        if self.structured_output.mode is DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT:
            if len(self.provider_visible_messages) != 1 or self.provider_visible_messages[0].role != "user":
                raise ValueError("RAW_JSON_PROMPT requires exactly one user message")
        return self

    @property
    def a2_identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class DeepAnalysisExecutionProfileV1(_ContractModel):
    schema_version: Literal["deep-analysis-execution-profile-v1"]
    a2_identity: str = Field(pattern=_SHA256)
    provider_kind: DeepAnalysisProviderKind
    provider_id: str = Field(min_length=1, pattern=r"\S")
    adapter_identity: str = Field(min_length=1, pattern=r"\S")
    adapter_version: str = Field(min_length=1, pattern=r"\S")
    sdk_or_http_client_version: str = Field(min_length=1, pattern=r"\S")
    endpoint_deployment_profile_identity: str = Field(min_length=1, pattern=r"\S")
    model_selection: DeepAnalysisModelIdentityV1
    qualified_capability_profile_identity: str = Field(min_length=1, pattern=r"\S")
    context_authority_identity: str = Field(min_length=1, pattern=r"\S")
    generation_profile_identity: str = Field(min_length=1, pattern=r"\S")
    idempotency_support_profile_identity: str = Field(min_length=1, pattern=r"\S")
    credential_execution_profile: CredentialExecutionProfileIdentityV1
    structured_output_profile_identity: str = Field(min_length=1, pattern=r"\S")

    @property
    def a3_identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class DeepAnalysisFailureV1(_ContractModel):
    schema_version: Literal["deep-analysis-failure-v1"]
    code: DeepAnalysisFailureCode
    stage: DeepAnalysisFailureStage

    @model_validator(mode="after")
    def _stage_matches_frozen_precedence(self) -> Self:
        if self.stage not in _FAILURE_STAGES_BY_CODE[self.code]:
            raise ValueError("failure stage does not match frozen taxonomy")
        return self


def classify_failure_candidates(candidates: Sequence[DeepAnalysisFailureV1]) -> DeepAnalysisFailureV1:
    if not candidates:
        raise ValueError("at least one classified failure candidate is required")
    ranks = {stage: rank for rank, stage in enumerate(FAILURE_PRECEDENCE)}
    return min(candidates, key=lambda candidate: ranks[candidate.stage])


class DeepAnalysisFallbackNodeV1(_ContractModel):
    schema_version: Literal["deep-analysis-fallback-node-v1"]
    provider_id: str = Field(min_length=1, pattern=r"\S")
    provider_kind: DeepAnalysisProviderKind
    adapter_identity: str = Field(min_length=1, pattern=r"\S")
    endpoint_deployment_profile_identity: str = Field(min_length=1, pattern=r"\S")
    model_selection: DeepAnalysisModelIdentityV1
    credential_execution_profile_identity: str = Field(pattern=_SHA256)
    structured_output_profile_identity: str = Field(min_length=1, pattern=r"\S")
    generation_profile_identity: str = Field(min_length=1, pattern=r"\S")
    context_authority_identity: str = Field(min_length=1, pattern=r"\S")
    qualified_capability_profile_identity: str = Field(min_length=1, pattern=r"\S")
    payload_scope: DeepAnalysisPayloadScope

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class DeepAnalysisFallbackEdgeV1(_ContractModel):
    schema_version: Literal["deep-analysis-fallback-edge-v1"]
    source_node_identity: str = Field(pattern=_SHA256)
    destination_node_identity: str = Field(pattern=_SHA256)
    allowed_failure_codes: tuple[DeepAnalysisFailureCode, ...] = Field(min_length=1)
    source_payload_scope: DeepAnalysisPayloadScope
    destination_payload_scope: DeepAnalysisPayloadScope
    payload_scope_authorization_identity: str = Field(min_length=1, pattern=r"\S")
    cloud_consent_authorization_identity: str = Field(min_length=1, pattern=r"\S")
    destination_credential_execution_profile_identity: str = Field(pattern=_SHA256)

    @field_validator("allowed_failure_codes")
    @classmethod
    def _sorted_unique_failure_codes(
        cls, value: tuple[DeepAnalysisFailureCode, ...]
    ) -> tuple[DeepAnalysisFailureCode, ...]:
        if len(value) != len(set(value)):
            raise ValueError("fallback edge failure codes must be unique")
        if tuple(sorted(value, key=lambda code: canonical_dacs1_bytes({"schema_version": "failure-code-v1", "code": code.value}))) != value:
            raise ValueError("fallback edge failure codes must be DACS-1 sorted")
        return value

    @property
    def edge_identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


def _has_cycle(adjacency: Mapping[str, tuple[str, ...]], node: str, active: set[str], done: set[str]) -> bool:
    if node in active:
        return True
    if node in done:
        return False
    active.add(node)
    cyclic = any(_has_cycle(adjacency, target, active, done) for target in adjacency[node])
    active.remove(node)
    done.add(node)
    return cyclic


class DeepAnalysisFallbackPolicyV1(_ContractModel):
    schema_version: Literal["deep-analysis-fallback-policy-v1"]
    start_node_identity: str = Field(pattern=_SHA256)
    nodes: tuple[DeepAnalysisFallbackNodeV1, ...] = Field(min_length=1)
    edges: tuple[DeepAnalysisFallbackEdgeV1, ...] = ()

    @model_validator(mode="after")
    def _validate_finite_dag(self) -> Self:
        node_ids = tuple(node.identity for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("fallback policy contains duplicate semantic nodes")
        if self.start_node_identity not in node_ids:
            raise ValueError("fallback policy explicit start node is missing")
        node_set = set(node_ids)
        edge_ids = tuple(edge.edge_identity for edge in self.edges)
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("fallback policy contains duplicate edges")
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        source_codes: dict[str, set[DeepAnalysisFailureCode]] = {node_id: set() for node_id in node_ids}
        nodes_by_identity = {node.identity: node for node in self.nodes}
        for edge in self.edges:
            if edge.source_node_identity not in node_set or edge.destination_node_identity not in node_set:
                raise ValueError("fallback edge references a missing node")
            if edge.source_node_identity == edge.destination_node_identity:
                raise ValueError("fallback policy does not permit a self-loop")
            source_node = nodes_by_identity[edge.source_node_identity]
            destination_node = nodes_by_identity[edge.destination_node_identity]
            if edge.source_payload_scope is not source_node.payload_scope:
                raise ValueError("fallback edge source payload scope does not match source node")
            if edge.destination_payload_scope is not destination_node.payload_scope:
                raise ValueError("fallback edge destination payload scope does not match destination node")
            if (
                edge.destination_credential_execution_profile_identity
                != destination_node.credential_execution_profile_identity
            ):
                raise ValueError("fallback edge credential profile does not match destination node")
            overlap = source_codes[edge.source_node_identity].intersection(edge.allowed_failure_codes)
            if overlap:
                raise ValueError("fallback policy has ambiguous outgoing edges")
            source_codes[edge.source_node_identity].update(edge.allowed_failure_codes)
            adjacency[edge.source_node_identity].append(edge.destination_node_identity)
        frozen_adjacency = {source: tuple(targets) for source, targets in adjacency.items()}
        if any(_has_cycle(frozen_adjacency, node_id, set(), set()) for node_id in node_ids):
            raise ValueError("fallback policy must be acyclic")
        return self

    def canonical_data(self) -> dict[str, object]:
        canonical_nodes = sorted(self.nodes, key=lambda node: node.identity)
        canonical_edges = sorted(
            self.edges,
            key=lambda edge: (
                edge.source_node_identity,
                canonical_dacs1_bytes({"schema_version": "failure-code-set-v1", "codes": [code.value for code in edge.allowed_failure_codes]}),
                edge.destination_node_identity,
                edge.edge_identity,
            ),
        )
        return {
            "schema_version": self.schema_version,
            "start_node_identity": self.start_node_identity,
            "nodes": [_identity_data(node) for node in canonical_nodes],
            "edges": [_identity_data(edge) for edge in canonical_edges],
        }

    @property
    def identity(self) -> str:
        return dacs1_sha256(self.canonical_data())

    @property
    def maximum_semantic_attempts(self) -> int:
        return len(self.nodes)


def select_fallback_edge(
    *,
    policy: DeepAnalysisFallbackPolicyV1,
    current_node_identity: str,
    failure: DeepAnalysisFailureV1,
) -> DeepAnalysisFallbackEdgeV1 | None:
    if current_node_identity not in {node.identity for node in policy.nodes}:
        raise ValueError("current fallback node is not authorized by policy")
    matches = tuple(
        edge
        for edge in policy.edges
        if edge.source_node_identity == current_node_identity and failure.code in edge.allowed_failure_codes
    )
    if len(matches) > 1:
        raise ValueError("fallback policy has ambiguous matching edges")
    return matches[0] if matches else None


class DeepAnalysisFallbackAttemptProvenanceV1(_ContractModel):
    schema_version: Literal["deep-analysis-fallback-attempt-provenance-v1"]
    ordinal: int = Field(ge=1)
    fallback_node_identity: str = Field(pattern=_SHA256)
    provider_id: str = Field(min_length=1, pattern=r"\S")
    model_selection_identity: str = Field(pattern=_SHA256)
    triggering_prior_failure: DeepAnalysisFailureCode | None = None
    edge_authorization_identity: str | None = None
    payload_scope: DeepAnalysisPayloadScope
    consent_identity: str = Field(pattern=_SHA256)
    a1_identity: str = Field(pattern=_SHA256)
    a2_identity: str = Field(pattern=_SHA256)
    a3_identity: str = Field(pattern=_SHA256)
    transport_result_identity: str | None = Field(default=None, pattern=_SHA256)

    @model_validator(mode="after")
    def _start_or_edge_shape(self) -> Self:
        if (self.triggering_prior_failure is None) != (self.edge_authorization_identity is None):
            raise ValueError("start attempt alone may omit trigger and edge authorization")
        return self


class DeepAnalysisValidationPolicyIdentityV1(_ContractModel):
    schema_version: Literal["deep-analysis-validation-policy-identity-v1"]
    strict_json_policy_version: str = Field(min_length=1, pattern=r"\S")
    schema_policy_version: str = Field(min_length=1, pattern=r"\S")
    domain_policy_version: str = Field(min_length=1, pattern=r"\S")
    grounding_policy_version: str = Field(min_length=1, pattern=r"\S")
    kg2_policy_version: str = Field(min_length=1, pattern=r"\S")
    language_policy_version: str = Field(min_length=1, pattern=r"\S")
    provenance_policy_version: str = Field(min_length=1, pattern=r"\S")

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class DeepAnalysisCacheIdentityV1(_ContractModel):
    schema_version: Literal["deep-analysis-cache-identity-v1"]
    a1_identity: str = Field(pattern=_SHA256)
    a2_identity: str = Field(pattern=_SHA256)
    a3_identity: str = Field(pattern=_SHA256)
    validation_policy_identity: str = Field(pattern=_SHA256)

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class DeepAnalysisCacheDecisionV1(_ContractModel):
    schema_version: Literal["deep-analysis-cache-decision-v1"]
    eligibility: CacheEligibility
    cache_identity: DeepAnalysisCacheIdentityV1 | None = None

    @model_validator(mode="after")
    def _cache_identity_matches_eligibility(self) -> Self:
        if (self.eligibility is CacheEligibility.ELIGIBLE) != (self.cache_identity is not None):
            raise ValueError("cache identity must exist exactly for eligible executions")
        return self


def build_cache_decision(
    *,
    canonical_input: CanonicalDeepAnalysisInputV1,
    request_projection: DeepAnalysisRequestProjectionV1,
    execution_profile: DeepAnalysisExecutionProfileV1,
    validation_policy: DeepAnalysisValidationPolicyIdentityV1,
) -> DeepAnalysisCacheDecisionV1:
    if execution_profile.model_selection.cache_eligibility is CacheEligibility.INELIGIBLE_FLOATING_MODEL:
        return DeepAnalysisCacheDecisionV1(schema_version="deep-analysis-cache-decision-v1", eligibility=CacheEligibility.INELIGIBLE_FLOATING_MODEL)
    return DeepAnalysisCacheDecisionV1(
        schema_version="deep-analysis-cache-decision-v1",
        eligibility=CacheEligibility.ELIGIBLE,
        cache_identity=DeepAnalysisCacheIdentityV1(
            schema_version="deep-analysis-cache-identity-v1",
            a1_identity=canonical_input.a1_identity,
            a2_identity=request_projection.a2_identity,
            a3_identity=execution_profile.a3_identity,
            validation_policy_identity=validation_policy.identity,
        ),
    )


class ContextBudgetProfileV1(_ContractModel):
    schema_version: Literal["deep-analysis-context-budget-profile-v1"]
    authority_kind: DeepAnalysisContextAuthorityKind
    authority_identity: str = Field(min_length=1, pattern=r"\S")
    context_window: int = Field(gt=0)
    input_budget: int = Field(ge=0)
    structured_output_overhead_budget: int = Field(ge=0)
    tool_schema_overhead_budget: int = Field(ge=0)
    requested_output_budget: int = Field(ge=0)

    @model_validator(mode="after")
    def _budget_is_admissible(self) -> Self:
        required = (
            self.input_budget
            + self.structured_output_overhead_budget
            + self.tool_schema_overhead_budget
            + self.requested_output_budget
        )
        if required > self.context_window:
            raise ValueError("context budget exceeds the documented context window")
        return self

    @property
    def identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


class PostResponseUsageEvidenceV1(_ContractModel):
    """Observational usage evidence, explicitly not pre-dispatch authority."""

    schema_version: Literal["deep-analysis-post-response-usage-evidence-v1"]
    provider_reported_input_tokens: int | None = Field(default=None, ge=0)
    provider_reported_output_tokens: int | None = Field(default=None, ge=0)


class DeepAnalysisDispatchEnvelopeV1(_ContractModel):
    """Immutable semantic dispatch representation; it cannot send anything."""

    schema_version: Literal["deep-analysis-dispatch-envelope-v1"]
    canonical_input: CanonicalDeepAnalysisInputV1
    request_projection: DeepAnalysisRequestProjectionV1
    execution_profile: DeepAnalysisExecutionProfileV1
    payload_consent: PayloadConsentIdentityV1
    context_budget_profile: ContextBudgetProfileV1
    timeout_profile_identity: str = Field(min_length=1, pattern=r"\S")
    fallback_policy_identity: str = Field(pattern=_SHA256)
    prompt_identity: str = Field(min_length=1, pattern=r"\S")
    schema_identity: str = Field(min_length=1, pattern=r"\S")

    @model_validator(mode="after")
    def _all_semantic_bindings_match(self) -> Self:
        if self.request_projection.a1_identity != self.canonical_input.a1_identity:
            raise ValueError("dispatch envelope A1 binding is invalid")
        if self.execution_profile.a2_identity != self.request_projection.a2_identity:
            raise ValueError("dispatch envelope A2 binding is invalid")
        if self.request_projection.payload_consent_identity != self.payload_consent.identity:
            raise ValueError("dispatch envelope payload consent binding is invalid")
        if self.request_projection.payload_scope is not self.payload_consent.payload_scope:
            raise ValueError("dispatch envelope payload scope binding is invalid")
        if self.payload_consent.named_provider_id != self.execution_profile.provider_id:
            raise ValueError("dispatch envelope consent provider binding is invalid")
        if self.payload_consent.provider_kind is not self.execution_profile.provider_kind:
            raise ValueError("dispatch envelope consent provider kind binding is invalid")
        if self.payload_consent.allowed_model_constraint != self.execution_profile.model_selection.model_id:
            raise ValueError("dispatch envelope consent model binding is invalid")
        if self.context_budget_profile.authority_identity != self.execution_profile.context_authority_identity:
            raise ValueError("dispatch envelope context authority binding is invalid")
        if self.prompt_identity != self.request_projection.prompt_identity:
            raise ValueError("dispatch envelope prompt binding is invalid")
        if self.schema_identity != self.request_projection.knowledge_content_schema_identity:
            raise ValueError("dispatch envelope schema binding is invalid")
        if (
            self.request_projection.payload_scope is DeepAnalysisPayloadScope.FULL_TRANSCRIPT
            and not self.canonical_input.coverage_complete
        ):
            raise ValueError("FULL_TRANSCRIPT dispatch requires complete coverage")
        return self

    @property
    def a1_identity(self) -> str:
        return self.canonical_input.a1_identity

    @property
    def a2_identity(self) -> str:
        return self.request_projection.a2_identity

    @property
    def a3_identity(self) -> str:
        return self.execution_profile.a3_identity

    @property
    def semantic_identity(self) -> str:
        return dacs1_sha256(_identity_data(self))


def provider_envelope_identity(envelope_bytes: bytes) -> str:
    return hashlib.sha256(envelope_bytes).hexdigest()


def validated_payload_identity(
    *,
    mode: DeepAnalysisStructuredOutputMode,
    payload: bytes | object,
) -> str:
    """Return the exact mode-specific untrusted structured-payload identity."""

    if mode in {
        DeepAnalysisStructuredOutputMode.RAW_JSON_PROMPT,
        DeepAnalysisStructuredOutputMode.PROVIDER_JSON_MODE,
        DeepAnalysisStructuredOutputMode.PROVIDER_JSON_SCHEMA,
    }:
        if not isinstance(payload, bytes):
            raise ValueError("text structured-output modes require exact UTF-8 payload bytes")
        return hashlib.sha256(payload).hexdigest()
    if mode is DeepAnalysisStructuredOutputMode.TOOL_STRUCTURED_RETURN:
        if isinstance(payload, bytes):
            raise ValueError("tool structured return requires a lossless decoded object")
        return dacs1_sha256({"schema_version": "deep-analysis-tool-payload-v1", "payload": payload})
    raise ValueError("unknown structured-output mode")


class UntrustedDeepAnalysisResponseV1(_ContractModel):
    """Adapter output data only.  No conversion to a trusted value exists."""

    schema_version: Literal["untrusted-deep-analysis-response-v1"]
    expected_dispatch_identity: str = Field(pattern=_SHA256)
    provider_envelope_bytes: bytes = Field(min_length=1)
    structured_payload: bytes | object
    structured_output_mode: DeepAnalysisStructuredOutputMode
    provider_request_id: str | None = None
    finish_reason: str | None = None
    delivery_certainty: Literal["NOT_SENT", "CONFIRMED", "UNKNOWN"]
    response_metadata: object | None = None
    usage_evidence: PostResponseUsageEvidenceV1 | None = None

    @field_validator("response_metadata", mode="after")
    @classmethod
    def _freeze_response_metadata(cls, value: object | None) -> object | None:
        return None if value is None else _freeze_json(value)

    @field_validator("structured_payload", mode="after")
    @classmethod
    def _freeze_decoded_payload(cls, value: bytes | object) -> bytes | object:
        return value if isinstance(value, bytes) else _freeze_json(value)

    @property
    def provider_envelope_identity(self) -> str:
        return provider_envelope_identity(self.provider_envelope_bytes)

    @property
    def structured_payload_identity(self) -> str:
        return validated_payload_identity(mode=self.structured_output_mode, payload=self.structured_payload)


class TrustedDeepAnalysisSuccess:
    """Opaque finalizer output; callers and adapters cannot mint it directly.

    This foundational slice intentionally has no successful admission path.
    The next authorized validator/finalizer slice must introduce and own its
    runtime admission authority; semantic object shape is never authority.
    """

    __slots__ = ("_content_identity", "_cache_identity", "_sealed", "__weakref__")
    _content_identity: str
    _cache_identity: str
    _sealed: bool

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("TrustedDeepAnalysisSuccess cannot be subclassed")

    def __init__(self) -> None:
        raise TypeError(
            "TrustedDeepAnalysisSuccess does not mint values in the foundational contract slice"
        )

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("TrustedDeepAnalysisSuccess is immutable")
        object.__setattr__(self, name, value)

    @property
    def content_identity(self) -> str:
        return self._content_identity

    @property
    def cache_identity(self) -> str:
        return self._cache_identity

    def __copy__(self) -> NoReturn:
        raise TypeError("TrustedDeepAnalysisSuccess cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("TrustedDeepAnalysisSuccess cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("TrustedDeepAnalysisSuccess cannot be serialized")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("TrustedDeepAnalysisSuccess cannot be serialized")


def verify_trusted_deep_analysis_success(value: object) -> bool:
    """Verify the runtime-owned finalizer admission without minting anything."""

    # Lazy import preserves the foundational module's provider-neutral domain
    # dependency direction while delegating ownership to the authorized runtime.
    from youtube_intel.deep_analysis_runtime import (
        _verify_trusted_deep_analysis_success,
    )

    return _verify_trusted_deep_analysis_success(value)


__all__ = [
    "AuthorizedProviderPayloadProjectionV1",
    "CacheEligibility",
    "CanonicalDeepAnalysisInputV1",
    "ContextBudgetProfileV1",
    "CredentialExecutionProfileIdentityV1",
    "DeepAnalysisCacheDecisionV1",
    "DeepAnalysisCacheIdentityV1",
    "DeepAnalysisContextAuthorityKind",
    "DeepAnalysisDispatchEnvelopeV1",
    "DeepAnalysisExecutionProfileV1",
    "DeepAnalysisFailureCode",
    "DeepAnalysisFailureStage",
    "DeepAnalysisFailureV1",
    "DeepAnalysisFallbackAttemptProvenanceV1",
    "DeepAnalysisFallbackEdgeV1",
    "DeepAnalysisFallbackNodeV1",
    "DeepAnalysisFallbackPolicyV1",
    "DeepAnalysisMessageV1",
    "DeepAnalysisModelIdentityClass",
    "DeepAnalysisModelIdentityV1",
    "DeepAnalysisPayloadScope",
    "DeepAnalysisProviderCapabilities",
    "DeepAnalysisProviderKind",
    "DeepAnalysisRequestProjectionV1",
    "DeepAnalysisStructuredOutputMode",
    "DeepAnalysisStructuredOutputV1",
    "DeepAnalysisValidationPolicyIdentityV1",
    "FAILURE_PRECEDENCE",
    "PayloadConsentIdentityV1",
    "PayloadConsentMode",
    "PostResponseUsageEvidenceV1",
    "SelectedEvidenceProjectionV1",
    "TrustedDeepAnalysisSuccess",
    "UntrustedDeepAnalysisResponseV1",
    "build_cache_decision",
    "canonical_dacs1_bytes",
    "classify_failure_candidates",
    "dacs1_sha256",
    "provider_envelope_identity",
    "select_fallback_edge",
    "validated_payload_identity",
    "verify_trusted_deep_analysis_success",
]
