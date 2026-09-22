"""Fail-closed, provider-free personalized distillation admission service."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from http.client import HTTPException, HTTPSConnection
from typing import Protocol

from youtube_intel.domain import Availability
from youtube_intel.source_policy import SourcePolicyApplicationService
from youtube_intel.state import (
    ArtifactKind,
    DistillationCardWrite,
    DistillationExecutionRecord,
    DistillationExecutionWrite,
    EvidenceAvailability,
    EvidenceStance,
    FilterOutcome,
    IntegrityConflict,
    IntelligenceClaimKind,
    SQLiteStateRepository,
    StateStoreError,
)


class DistillationExecutionStatus(str, Enum):
    WAITING_BUDGET = "WAITING_BUDGET"
    WAITING_MODEL = "WAITING_MODEL"
    REJECTED_INELIGIBLE = "REJECTED_INELIGIBLE"
    REJECTED_EVIDENCE = "REJECTED_EVIDENCE"
    REJECTED_OUTPUT = "REJECTED_OUTPUT"
    AMBIGUOUS = "AMBIGUOUS"
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_NO_NEW_INTELLIGENCE = "SUCCEEDED_NO_NEW_INTELLIGENCE"


class DistillationTransportKind(str, Enum):
    """The complete finite set of V1 distillation transport authorities."""

    OFFLINE_TEST = "OFFLINE_TEST"
    CLOUD_PRODUCTION = "CLOUD_PRODUCTION"


class DistillationCapabilityScope(str, Enum):
    """Finite capability names that can be checked by production authority."""

    V1_VIDEO_DISTILLATION = "V1_VIDEO_DISTILLATION"
    DEEP_ANALYSIS = "DEEP_ANALYSIS"
    INVESTIGATION = "INVESTIGATION"
    ASK = "ASK"
    DAILY = "DAILY"
    EVIDENCE_EXPANSION = "EVIDENCE_EXPANSION"
    TASK_016G = "TASK_016G"
    V2 = "V2"


_PRODUCTION_ELIGIBILITY_SEAL = object()


@dataclass(frozen=True, slots=True, init=False)
class ProviderProductionEligibility:
    """Backend-minted provider/model/capability production decision."""

    provider: str
    model: str
    capability_scope: DistillationCapabilityScope
    available: bool
    qualified: bool
    authorized: bool
    production_eligible: bool
    _seal: object

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise TypeError("provider production eligibility is backend-authoritative")

    def _is_authoritative(self) -> bool:
        return self._seal is _PRODUCTION_ELIGIBILITY_SEAL


class NormalV1ProductionAuthorizationAuthority:
    """The complete TASK-022D authorization allowlist."""

    _PROVIDER = "nvidia_nim"
    _MODEL = "moonshotai/kimi-k3"
    _CAPABILITY = DistillationCapabilityScope.V1_VIDEO_DISTILLATION

    @classmethod
    def resolve(
        cls,
        *,
        provider: str,
        model: str,
        capability_scope: DistillationCapabilityScope,
        available: bool,
    ) -> ProviderProductionEligibility:
        if (
            not isinstance(provider, str)
            or not isinstance(model, str)
            or not isinstance(capability_scope, DistillationCapabilityScope)
            or type(available) is not bool
        ):
            raise TypeError("provider production eligibility input is invalid")
        authorized = (
            provider == cls._PROVIDER
            and model == cls._MODEL
            and capability_scope is cls._CAPABILITY
        )
        eligibility = object.__new__(ProviderProductionEligibility)
        object.__setattr__(eligibility, "provider", provider)
        object.__setattr__(eligibility, "model", model)
        object.__setattr__(eligibility, "capability_scope", capability_scope)
        object.__setattr__(eligibility, "available", available)
        object.__setattr__(eligibility, "qualified", authorized)
        object.__setattr__(eligibility, "authorized", authorized)
        object.__setattr__(eligibility, "production_eligible", available and authorized)
        object.__setattr__(eligibility, "_seal", _PRODUCTION_ELIGIBILITY_SEAL)
        return eligibility


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    allowed: bool
    state: str

    def __post_init__(self) -> None:
        if not self.state.strip() or len(self.state) > 160:
            raise ValueError("budget state is invalid")


@dataclass(frozen=True, slots=True)
class ActivePreferenceProjection:
    """Legal, immutable personalization input passed to the offline transport."""

    preference_id: str
    horizon: str
    provenance: str
    scope: str
    target_id: str | None
    statement: str


@dataclass(frozen=True, slots=True)
class DistillationCommand:
    execution_id: str
    source_id: str
    video_id: str
    evidence_ids: tuple[str, ...]
    reason: str
    use_case: str
    selected_provider: str
    selected_model: str
    preference_ids: tuple[str, ...] = ()
    active_preferences: tuple[ActivePreferenceProjection, ...] = ()
    source_focus_rules: tuple[str, ...] = ()
    source_ignore_rules: tuple[str, ...] = ()
    source_policy_revision_id: str | None = None
    distillation_style: str | None = None


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceInput:
    """Exact TASK-018B Evidence projection permitted to reach a transport."""

    evidence_id: str
    start_ms: int
    end_ms: int
    excerpt: str
    excerpt_hash: str
    timed_transcript_id: str
    timed_transcript_hash: str


@dataclass(frozen=True, slots=True)
class VerifiedDistillationInput:
    """Sealed, minimum-disclosure semantic input for one V1 distillation call.

    This is source provenance, not an admission decision.  Source evidence is
    deliberately a separate field from task/personalization instructions so a
    future provider adapter cannot treat transcript text as system authority.
    """

    source_display_name: str | None
    video_id: str
    video_title: str | None
    evidence: tuple[VerifiedEvidenceInput, ...]
    personalization: tuple[str, ...]
    source_focus_rules: tuple[str, ...]
    source_ignore_rules: tuple[str, ...]
    distillation_style: str | None
    selected_provider: str
    selected_model: str
    semantic_hash: str

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.evidence)


@dataclass(frozen=True, slots=True)
class DistillationTransportResult:
    raw: str
    actual_provider: str
    actual_model: str
    input_tokens: int | None
    output_tokens: int | None
    cost_microunits: int | None
    duration_ms: int | None


class CloudDistillationAuthorization:
    """Backend-owned gates for the finite V1 cloud transport routes.

    This carries no credential and deliberately has no endpoint override.  A
    qualification execution is scoped to one immutable verified-input hash;
    ordinary production instead requires the qualified+authorized pair.
    """

    cloud_enabled: bool
    provider: str | None
    model: str | None
    credential_available: bool
    provider_available: bool
    qualification_input_hash: str | None
    qualification_max_calls: int
    qualification_response_wait_timeout_seconds: int | None
    _normal_eligibility: ProviderProductionEligibility | None
    _sealed: bool

    __slots__ = (
        "cloud_enabled",
        "provider",
        "model",
        "credential_available",
        "provider_available",
        "qualification_input_hash",
        "qualification_max_calls",
        "qualification_response_wait_timeout_seconds",
        "_normal_eligibility",
        "_sealed",
    )

    def __init__(
        self,
        *,
        cloud_enabled: bool = False,
        provider: str | None = None,
        model: str | None = None,
        credential_available: bool = False,
        provider_available: bool = False,
        qualification_input_hash: str | None = None,
        qualification_max_calls: int = 1,
        qualification_response_wait_timeout_seconds: int | None = None,
    ) -> None:
        object.__setattr__(self, "cloud_enabled", cloud_enabled)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "credential_available", credential_available)
        object.__setattr__(self, "provider_available", provider_available)
        object.__setattr__(self, "qualification_input_hash", qualification_input_hash)
        object.__setattr__(self, "qualification_max_calls", qualification_max_calls)
        object.__setattr__(
            self,
            "qualification_response_wait_timeout_seconds",
            qualification_response_wait_timeout_seconds,
        )
        object.__setattr__(self, "_normal_eligibility", None)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("cloud distillation authorization is immutable")

    @classmethod
    def for_normal_production(
        cls,
        *,
        eligibility: ProviderProductionEligibility,
        cloud_enabled: bool,
        credential_available: bool,
    ) -> CloudDistillationAuthorization:
        if (
            type(eligibility) is not ProviderProductionEligibility
            or not eligibility._is_authoritative()
        ):
            raise TypeError("normal production requires backend provider eligibility")
        authorization = cls(
            cloud_enabled=cloud_enabled,
            provider=eligibility.provider,
            model=eligibility.model,
            credential_available=credential_available,
            provider_available=eligibility.available,
        )
        object.__setattr__(authorization, "_normal_eligibility", eligibility)
        return authorization

    @property
    def qualified(self) -> bool:
        eligibility = self._normal_eligibility
        return eligibility is not None and eligibility.qualified

    @property
    def authorized(self) -> bool:
        eligibility = self._normal_eligibility
        return eligibility is not None and eligibility.authorized

    @property
    def production_eligible(self) -> bool:
        eligibility = self._normal_eligibility
        return eligibility is not None and eligibility.production_eligible

    def permits(self, verified_input: VerifiedDistillationInput) -> bool:
        if not (
            self.cloud_enabled
            and self.provider in {"openai", "nvidia_nim"}
            and isinstance(self.model, str)
            and bool(self.model.strip())
            and self.credential_available
            and self.provider_available
            and verified_input.selected_provider == self.provider
            and verified_input.selected_model == self.model
        ):
            return False
        normal = (
            self.production_eligible
            and self._normal_eligibility is not None
            and self._normal_eligibility.capability_scope
            is DistillationCapabilityScope.V1_VIDEO_DISTILLATION
        )
        qualification = (
            isinstance(self.qualification_input_hash, str)
            and len(self.qualification_input_hash) == 64
            and all(
                character in "0123456789abcdef"
                for character in self.qualification_input_hash
            )
            and isinstance(verified_input.semantic_hash, str)
            and self.qualification_input_hash == verified_input.semantic_hash
            and self.qualification_max_calls == 1
        )
        return normal or qualification


class CloudDistillationPreDispatchError(Exception):
    """A known no-dispatch failure which must not be reclassified as ambiguity."""


class _OpenAICloudWireTransport(Protocol):
    def __call__(
        self,
        request: Mapping[str, object],
        credential: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> Mapping[str, object]: ...


class _NvidiaNimCloudWireTransport(Protocol):
    def __call__(
        self,
        endpoint: str,
        request: Mapping[str, object],
        credential: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> Mapping[str, object]: ...


_NVIDIA_NIM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
_NVIDIA_NIM_HOST = "integrate.api.nvidia.com"
_NVIDIA_NIM_PATH = "/v1/chat/completions"
_NVIDIA_NIM_PROVIDER = "nvidia_nim"
_NVIDIA_NIM_MODEL = "moonshotai/kimi-k3"
_NVIDIA_NIM_MAX_RESPONSE_BYTES = 2_000_000


def _nvidia_nim_http_transport(
    endpoint: str,
    request: Mapping[str, object],
    credential: str,
    timeout_seconds: float,
    max_retries: int,
) -> Mapping[str, object]:
    """Perform one bounded POST to the fixed official NVIDIA NIM authority."""

    if endpoint != _NVIDIA_NIM_ENDPOINT or max_retries != 0:
        raise RuntimeError("NVIDIA NIM transport policy is invalid")
    body = json.dumps(
        request, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    connection = HTTPSConnection(_NVIDIA_NIM_HOST, timeout=timeout_seconds)
    try:
        connection.request(
            "POST",
            _NVIDIA_NIM_PATH,
            body=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {credential}",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError("NVIDIA NIM response was not complete")
        response_bytes = response.read(_NVIDIA_NIM_MAX_RESPONSE_BYTES + 1)
    except (HTTPException, OSError, TimeoutError):
        raise RuntimeError("NVIDIA NIM transport outcome is not confirmed") from None
    finally:
        connection.close()
    if len(response_bytes) > _NVIDIA_NIM_MAX_RESPONSE_BYTES:
        raise RuntimeError("NVIDIA NIM response exceeded the capture bound")
    try:
        decoded = json.loads(response_bytes.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("NVIDIA NIM response envelope is invalid") from None
    if not isinstance(decoded, Mapping):
        raise RuntimeError("NVIDIA NIM response envelope is invalid")
    return decoded


class OpenAICloudDistillationTransport:
    """One fixed-endpoint OpenAI adapter for the sealed V1 input boundary.

    The injected wire boundary is intentionally the only potentially-networked
    operation.  It receives zero retry budget; callers cannot supply an URL,
    provider, model, transcript, or arbitrary provider messages.
    """

    transport_kind = DistillationTransportKind.CLOUD_PRODUCTION
    is_offline_test_transport = False
    _OFFICIAL_ENDPOINT_IDENTITY = "openai-responses-v1"
    _TIMEOUT_SECONDS = 30.0

    def __init__(
        self,
        *,
        authorization: CloudDistillationAuthorization,
        credential_resolver: Callable[[], str],
        wire_transport: _OpenAICloudWireTransport,
    ) -> None:
        self._authorization = authorization
        self._credential_resolver = credential_resolver
        self._wire_transport = wire_transport

    @property
    def available(self) -> bool:
        return self._authorization.provider_available

    @property
    def actual_provider(self) -> str:
        return "openai"

    @property
    def actual_model(self) -> str:
        return self._authorization.model or ""

    def is_authorized_for(self, verified_input: VerifiedDistillationInput) -> bool:
        return (
            self._authorization.provider == "openai"
            and verified_input.selected_provider == "openai"
            and self._authorization.permits(verified_input)
        )

    def is_authorized_for_qualification(
        self, verified_input: VerifiedDistillationInput
    ) -> bool:
        return not self._authorization.production_eligible and self.is_authorized_for(
            verified_input
        )

    def generate(self, verified_input: VerifiedDistillationInput) -> DistillationTransportResult:
        if not self.is_authorized_for(verified_input):
            raise CloudDistillationPreDispatchError("cloud distillation is not authorized")
        credential = self._credential_resolver()
        if not credential:
            raise CloudDistillationPreDispatchError("cloud credential is unavailable")
        try:
            response = self._wire_transport(
                self._request(verified_input), credential, self._TIMEOUT_SECONDS, 0
            )
        finally:
            credential = ""
        output = response.get("output_text")
        model = response.get("model")
        if not isinstance(output, str) or not isinstance(model, str) or not model:
            raise ValueError("cloud provider response envelope is invalid")
        usage = response.get("usage")
        input_tokens = usage.get("input_tokens") if isinstance(usage, Mapping) else None
        output_tokens = usage.get("output_tokens") if isinstance(usage, Mapping) else None
        return DistillationTransportResult(
            raw=output,
            actual_provider="openai",
            actual_model=model,
            input_tokens=input_tokens if isinstance(input_tokens, int) and input_tokens >= 0 else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) and output_tokens >= 0 else None,
            cost_microunits=None,
            duration_ms=None,
        )

    @classmethod
    def _request(cls, verified_input: VerifiedDistillationInput) -> dict[str, object]:
        evidence = [
            {
                "evidence_id": item.evidence_id,
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
                "excerpt": item.excerpt,
            }
            for item in verified_input.evidence
        ]
        source_payload = json.dumps(
            {"video_id": verified_input.video_id, "video_title": verified_input.video_title, "evidence": evidence},
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        )
        task_payload = json.dumps(
            {"personalization": verified_input.personalization, "focus": verified_input.source_focus_rules,
             "ignore": verified_input.source_ignore_rules, "style": verified_input.distillation_style},
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        )
        return {
            "endpoint_identity": cls._OFFICIAL_ENDPOINT_IDENTITY,
            "model": verified_input.selected_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "Return only one exact TASK-022 JSON result. Use the existing "
                        "Intelligence object schema when Intelligence should be admitted. "
                        "Only when nothing meets the admission threshold, return exactly "
                        "result=NO_NEW_INTELLIGENCE plus every supplied Evidence identity "
                        "and timestamp; never use an empty object or empty evidence list."
                    ),
                },
                {"role": "developer", "content": f"TASK_AND_PERSONALIZATION={task_payload}"},
                {"role": "user", "content": f"UNTRUSTED_SOURCE_EVIDENCE={source_payload}"},
            ],
            "store": False,
            "truncation": "disabled",
            "stream": False,
            "max_retries": 0,
        }


class NvidiaNimCloudDistillationTransport:
    """Fixed-authority NVIDIA NIM adapter for one sealed V1 distillation input."""

    transport_kind = DistillationTransportKind.CLOUD_PRODUCTION
    is_offline_test_transport = False
    _TIMEOUT_SECONDS = 120.0
    _QUALIFICATION_TIMEOUT_SECONDS = 300.0

    def __init__(
        self,
        *,
        authorization: CloudDistillationAuthorization,
        credential_resolver: Callable[[], str],
        wire_transport: _NvidiaNimCloudWireTransport = _nvidia_nim_http_transport,
    ) -> None:
        self._authorization = authorization
        self._credential_resolver = credential_resolver
        self._wire_transport = wire_transport

    @property
    def available(self) -> bool:
        return self._authorization.provider_available

    @property
    def actual_provider(self) -> str:
        return _NVIDIA_NIM_PROVIDER

    @property
    def actual_model(self) -> str:
        return _NVIDIA_NIM_MODEL

    def is_authorized_for(self, verified_input: VerifiedDistillationInput) -> bool:
        return (
            type(verified_input) is VerifiedDistillationInput
            and bool(verified_input.evidence)
            and self._authorization.provider == _NVIDIA_NIM_PROVIDER
            and self._authorization.model == _NVIDIA_NIM_MODEL
            and verified_input.selected_provider == _NVIDIA_NIM_PROVIDER
            and verified_input.selected_model == _NVIDIA_NIM_MODEL
            and self._authorization.permits(verified_input)
            and self._qualification_timeout_is_authorized(verified_input)
        )

    def is_authorized_for_normal_production(
        self, verified_input: VerifiedDistillationInput
    ) -> bool:
        return self._authorization.production_eligible and self.is_authorized_for(
            verified_input
        )

    def is_authorized_for_qualification(
        self, verified_input: VerifiedDistillationInput
    ) -> bool:
        return not self._authorization.production_eligible and self.is_authorized_for(
            verified_input
        )

    def _qualification_timeout_is_authorized(
        self, verified_input: VerifiedDistillationInput
    ) -> bool:
        timeout = self._authorization.qualification_response_wait_timeout_seconds
        if timeout is None:
            return True
        return (
            timeout == self._QUALIFICATION_TIMEOUT_SECONDS
            and self._authorization.qualification_input_hash == verified_input.semantic_hash
            and self._authorization.qualification_max_calls == 1
        )

    def generate(self, verified_input: VerifiedDistillationInput) -> DistillationTransportResult:
        if not self.is_authorized_for(verified_input):
            raise CloudDistillationPreDispatchError("cloud distillation is not authorized")
        try:
            credential = self._credential_resolver()
        except Exception:
            raise CloudDistillationPreDispatchError("cloud credential is unavailable") from None
        if not credential:
            raise CloudDistillationPreDispatchError("cloud credential is unavailable")
        try:
            try:
                response = self._wire_transport(
                    _NVIDIA_NIM_ENDPOINT,
                    self._request(verified_input),
                    credential,
                    self._response_wait_timeout_seconds(),
                    0,
                )
            except Exception:
                raise RuntimeError("NVIDIA NIM transport outcome is not confirmed") from None
        finally:
            credential = ""
        model = response.get("model")
        choices = response.get("choices")
        if (
            not isinstance(model, str)
            or not model
            or not isinstance(choices, Sequence)
            or isinstance(choices, (str, bytes, bytearray))
            or not choices
            or not isinstance(choices[0], Mapping)
        ):
            raise ValueError("cloud provider response envelope is invalid")
        message = choices[0].get("message")
        output = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(output, str):
            raise ValueError("cloud provider response envelope is invalid")
        usage = response.get("usage")
        input_tokens = usage.get("prompt_tokens") if isinstance(usage, Mapping) else None
        output_tokens = usage.get("completion_tokens") if isinstance(usage, Mapping) else None
        return DistillationTransportResult(
            raw=output,
            actual_provider=_NVIDIA_NIM_PROVIDER,
            actual_model=model,
            input_tokens=input_tokens if isinstance(input_tokens, int) and input_tokens >= 0 else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) and output_tokens >= 0 else None,
            cost_microunits=None,
            duration_ms=None,
        )

    def _response_wait_timeout_seconds(self) -> float:
        if (
            self._authorization.qualification_response_wait_timeout_seconds
            == self._QUALIFICATION_TIMEOUT_SECONDS
        ):
            return self._QUALIFICATION_TIMEOUT_SECONDS
        return self._TIMEOUT_SECONDS

    @staticmethod
    def _request(verified_input: VerifiedDistillationInput) -> dict[str, object]:
        evidence = [
            {
                "evidence_id": item.evidence_id,
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
                "excerpt": item.excerpt,
                "excerpt_hash": item.excerpt_hash,
                "timed_transcript_id": item.timed_transcript_id,
                "timed_transcript_hash": item.timed_transcript_hash,
            }
            for item in verified_input.evidence
        ]
        task_payload = json.dumps(
            {
                "distillation_style": verified_input.distillation_style,
                "focus": verified_input.source_focus_rules,
                "ignore": verified_input.source_ignore_rules,
                "personalization": verified_input.personalization,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        source_payload = json.dumps(
            {
                "evidence": evidence,
                "source_display_name": verified_input.source_display_name,
                "video_id": verified_input.video_id,
                "video_title": verified_input.video_title,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        schema_contract = (
            "Return exactly one of two JSON results. For admitted Intelligence, return "
            "one object with exactly these keys: core_conclusion, "
            "user_relevant_information, important_new_information, meaningful_details, "
            "filtered_noise, claim_kind, evidence. core_conclusion must be a non-empty "
            "string. The four information/noise fields must be arrays of strings. "
            "claim_kind must be exactly one of FACT, EVIDENCE_BACKED_STATEMENT, OPINION, "
            "PREDICTION, RUMOR, SYSTEM_INFERENCE. evidence must cite every supplied "
            "evidence item exactly once using only evidence_id, start_ms, end_ms copied "
            "exactly from the source payload. If no candidate meets the Intelligence "
            "admission threshold, instead return exactly result=NO_NEW_INTELLIGENCE and "
            "evidence containing every supplied evidence_id, start_ms, and end_ms once, "
            "with no stance or claim fields. Do not use markdown fences or extra text."
        )
        return {
            "model": _NVIDIA_NIM_MODEL,
            "messages": [
                {"role": "system", "content": schema_contract},
                {"role": "system", "content": f"TASK_AND_PERSONALIZATION={task_payload}"},
                {"role": "user", "content": f"UNTRUSTED_SOURCE_EVIDENCE={source_payload}"},
            ],
            "max_tokens": 4_096,
            "reasoning_effort": "low",
            "seed": 0,
            "stream": False,
            "temperature": 0.0,
        }


@dataclass(frozen=True, slots=True)
class DistillationResult:
    execution_id: str
    status: DistillationExecutionStatus
    invocation_count: int
    intelligence_id: str | None
    revision_id: str | None


@dataclass(frozen=True, slots=True)
class DistillationReservation:
    """Canonical TASK-022 execution identity safe to bind before dispatch."""

    execution_id: str
    source_id: str
    video_id: str


class DistillationBudget(Protocol):
    def check(self, command: DistillationCommand) -> BudgetDecision: ...


class DistillationTransport(Protocol):
    """A deliberately offline deterministic transport used only in this task."""

    @property
    def is_offline_test_transport(self) -> bool: ...

    @property
    def available(self) -> bool: ...

    @property
    def actual_provider(self) -> str: ...

    @property
    def actual_model(self) -> str: ...

    def generate(self, verified_input: VerifiedDistillationInput) -> DistillationTransportResult: ...


@dataclass(frozen=True, slots=True)
class _Candidate:
    claim_kind: IntelligenceClaimKind
    evidence_ids: tuple[str, ...]
    evidence_stances: tuple[tuple[str, EvidenceStance], ...]
    card: DistillationCardWrite
    canonical_content: bytes


@dataclass(frozen=True, slots=True)
class _NoNewCandidate:
    """Explicit positive-zero result bound to the complete Evidence set."""

    evidence_ids: tuple[str, ...]


class PersonalizedDistillationService:
    """Admits only evidence-bound output from an injected offline/test transport."""

    _RESERVED_NOT_DISPATCHED = "RESERVED_NOT_DISPATCHED"
    _DISPATCH_CLAIMED = "DISPATCH_CLAIMED"
    _RESERVATION_REASON = "SOURCE_RUN_PERSONALIZED_DISTILLATION"
    _RESERVATION_USE_CASE = "PERSONALIZED_INTELLIGENCE"

    def __init__(
        self,
        repository: SQLiteStateRepository,
        source_policy: SourcePolicyApplicationService,
        transport: DistillationTransport,
        budget: DistillationBudget,
        *,
        now: Callable[[], datetime],
    ) -> None:
        kind = getattr(transport, "transport_kind", None)
        if kind is None and transport.is_offline_test_transport:
            kind = DistillationTransportKind.OFFLINE_TEST
        if kind not in {DistillationTransportKind.OFFLINE_TEST, DistillationTransportKind.CLOUD_PRODUCTION}:
            raise ValueError("TASK-022 transport kind is not legal")
        if kind is DistillationTransportKind.OFFLINE_TEST and not transport.is_offline_test_transport:
            raise ValueError("offline transport authority is invalid")
        if kind is DistillationTransportKind.CLOUD_PRODUCTION and transport.is_offline_test_transport:
            raise ValueError("cloud transport authority is invalid")
        if not transport.actual_provider.strip() or not transport.actual_model.strip():
            raise ValueError("offline transport identity is invalid")
        self._repository = repository
        self._source_policy = source_policy
        self._transport = transport
        self._budget = budget
        self._now = now
        self._selected_provider = transport.actual_provider
        self._selected_model = transport.actual_model

    def _transport_permits(
        self,
        verified_input: VerifiedDistillationInput,
        *,
        normal_production: bool = False,
    ) -> bool:
        cloud_transport = (
            getattr(self._transport, "transport_kind", None)
            is DistillationTransportKind.CLOUD_PRODUCTION
        )
        if cloud_transport:
            method_name = (
                "is_authorized_for_normal_production"
                if normal_production
                else "is_authorized_for_qualification"
            )
        else:
            method_name = "is_authorized_for"
        permits = getattr(self._transport, method_name, None)
        if cloud_transport and permits is None:
            return False
        return True if permits is None else bool(permits(verified_input))

    def manual_command(
        self,
        *,
        execution_id: str,
        source_id: str,
        video_id: str,
        evidence_ids: tuple[str, ...],
    ) -> DistillationCommand:
        """Build an API-safe manual command without caller-selected model inputs."""
        return DistillationCommand(
            execution_id=execution_id,
            source_id=source_id,
            video_id=video_id,
            evidence_ids=evidence_ids,
            reason="MANUAL_PERSONALIZED_DISTILLATION",
            use_case="PERSONALIZED_INTELLIGENCE",
            selected_provider=self._selected_provider,
            selected_model=self._selected_model,
        )

    @staticmethod
    def _reservation_id(
        *,
        source_id: str,
        video_id: str,
        evidence_ids: tuple[str, ...],
        selected_provider: str,
        selected_model: str,
        verified_input_hash: str,
    ) -> str:
        canonical = json.dumps(
            {
                "evidence_ids": evidence_ids,
                "reason": PersonalizedDistillationService._RESERVATION_REASON,
                "selected_model": selected_model,
                "selected_provider": selected_provider,
                "source_id": source_id,
                "use_case": PersonalizedDistillationService._RESERVATION_USE_CASE,
                "video_id": video_id,
                "verified_input_hash": verified_input_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"distillation:reservation:v2:{hashlib.sha256(canonical).hexdigest()}"

    def _canonical_reservation_evidence(
        self, *, video_id: str, evidence_ids: tuple[str, ...]
    ) -> tuple[str, ...]:
        if (
            not isinstance(evidence_ids, tuple)
            or not evidence_ids
            or any(
                not isinstance(evidence_id, str)
                or not evidence_id.strip()
                or evidence_id != evidence_id.strip()
                or len(evidence_id) > 512
                for evidence_id in evidence_ids
            )
        ):
            raise ValueError("reservation evidence is invalid")
        normalized = tuple(sorted(evidence_ids))
        if len(normalized) > 20 or len(set(normalized)) != len(normalized):
            raise ValueError("reservation evidence is invalid")
        canonical = self._repository.list_available_canonical_evidence_ids(video_id)
        if normalized != canonical:
            raise ValueError("reservation requires the current canonical evidence set")
        return canonical

    def _reserved_command(
        self, *, source_id: str, video_id: str, evidence_ids: tuple[str, ...]
    ) -> tuple[DistillationCommand, VerifiedDistillationInput]:
        base = DistillationCommand(
            execution_id="",
            source_id=source_id,
            video_id=video_id,
            evidence_ids=evidence_ids,
            reason=self._RESERVATION_REASON,
            use_case=self._RESERVATION_USE_CASE,
            selected_provider=self._selected_provider,
            selected_model=self._selected_model,
        )
        projection = self._projection(base)
        verified_input = self._compose_verified_input(projection)
        return (
            replace(
                projection,
                execution_id=self._reservation_id(
                    source_id=source_id,
                    video_id=video_id,
                    evidence_ids=evidence_ids,
                    selected_provider=self._selected_provider,
                    selected_model=self._selected_model,
                    verified_input_hash=verified_input.semantic_hash,
                ),
            ),
            verified_input,
        )

    @staticmethod
    def _same_execution_identity(
        record: DistillationExecutionRecord, command: DistillationCommand
    ) -> bool:
        return (
            record.execution_id == command.execution_id
            and record.source_id == command.source_id
            and record.video_id == command.video_id
            and record.reason == command.reason
            and record.use_case == command.use_case
            and record.selected_provider == command.selected_provider
            and record.selected_model == command.selected_model
        )

    def reserve_distillation_execution(
        self, *, source_id: str, video_id: str, evidence_ids: tuple[str, ...]
    ) -> DistillationReservation:
        """Mint the sole canonical execution identity before any dispatch exists.

        The supplied evidence set must equal the current persisted canonical
        transcript evidence set.  That lets a later process rebuild and verify
        the exact command from m010/Evidence persistence rather than memory.
        """
        canonical_evidence = self._canonical_reservation_evidence(
            video_id=video_id, evidence_ids=evidence_ids
        )
        provisional = DistillationCommand(
            execution_id="",
            source_id=source_id,
            video_id=video_id,
            evidence_ids=canonical_evidence,
            reason=self._RESERVATION_REASON,
            use_case=self._RESERVATION_USE_CASE,
            selected_provider=self._selected_provider,
            selected_model=self._selected_model,
        )
        if not self._eligible(provisional):
            raise ValueError("reservation source/video is not eligible")
        if not self._legal_evidence(provisional):
            raise ValueError("reservation evidence is not legal")
        command, _ = self._reserved_command(
            source_id=source_id, video_id=video_id, evidence_ids=canonical_evidence
        )
        existing = self._repository.get_distillation_execution(command.execution_id)
        if existing is None:
            try:
                existing = self._repository.reserve_distillation_execution(
                    DistillationExecutionWrite(
                        execution_id=command.execution_id,
                        source_id=command.source_id,
                        video_id=command.video_id,
                        reason=command.reason,
                        use_case=command.use_case,
                        selected_provider=command.selected_provider,
                        selected_model=command.selected_model,
                    ),
                    now=self._now(),
                )
            except IntegrityConflict:
                existing = self._repository.get_distillation_execution(command.execution_id)
        if existing is None or not self._same_execution_identity(existing, command):
            raise StateStoreError("distillation reservation identity conflicts")
        if not (
            existing.status == "PENDING"
            and existing.budget_state == self._RESERVED_NOT_DISPATCHED
            and existing.invocation_count == 0
        ):
            raise StateStoreError("existing execution is no longer a safe reservation")
        return DistillationReservation(
            execution_id=existing.execution_id,
            source_id=existing.source_id,
            video_id=existing.video_id,
        )

    @staticmethod
    def _result(record: DistillationExecutionRecord) -> DistillationResult:
        try:
            status = DistillationExecutionStatus(record.status)
        except ValueError as error:
            raise StateStoreError("distillation execution persistence is invalid") from error
        return DistillationResult(
            execution_id=record.execution_id,
            status=status,
            invocation_count=record.invocation_count,
            intelligence_id=record.intelligence_id,
            revision_id=record.revision_id,
        )

    def _begin(self, command: DistillationCommand) -> None:
        self._repository.begin_distillation_execution(
            DistillationExecutionWrite(
                execution_id=command.execution_id,
                source_id=command.source_id,
                video_id=command.video_id,
                reason=command.reason,
                use_case=command.use_case,
                selected_provider=command.selected_provider,
                selected_model=command.selected_model,
            ),
            now=self._now(),
        )

    def _finish(
        self,
        command: DistillationCommand,
        *,
        status: DistillationExecutionStatus,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        result: DistillationTransportResult | None = None,
    ) -> DistillationResult:
        return self._finish_execution(
            execution_id=command.execution_id,
            status=status,
            budget_state=budget_state,
            outcome=outcome,
            invocation_count=invocation_count,
            result=result,
        )

    def _finish_execution(
        self,
        *,
        execution_id: str,
        status: DistillationExecutionStatus,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        result: DistillationTransportResult | None = None,
    ) -> DistillationResult:
        record = self._repository.finish_distillation_without_admission(
            execution_id=execution_id,
            status=status.value,
            budget_state=budget_state,
            outcome=outcome,
            invocation_count=invocation_count,
            actual_provider=None if result is None else result.actual_provider,
            actual_model=None if result is None else result.actual_model,
            input_tokens=None if result is None else result.input_tokens,
            output_tokens=None if result is None else result.output_tokens,
            cost_microunits=None if result is None else result.cost_microunits,
            duration_ms=None if result is None else result.duration_ms,
            now=self._now(),
        )
        return self._result(record)

    def _finish_or_recover(
        self,
        command: DistillationCommand,
        *,
        status: DistillationExecutionStatus,
        budget_state: str,
        outcome: str,
        invocation_count: int,
        result: DistillationTransportResult | None = None,
    ) -> DistillationResult:
        try:
            return self._finish(
                command,
                status=status,
                budget_state=budget_state,
                outcome=outcome,
                invocation_count=invocation_count,
                result=result,
            )
        except StateStoreError:
            persisted = self._repository.get_distillation_execution(command.execution_id)
            if persisted is not None and persisted.status != "PENDING":
                return self._result(persisted)
            raise

    def _projection(self, command: DistillationCommand) -> DistillationCommand:
        policy = self._source_policy.effective_policy(command.source_id)
        projection = replace(
            command,
            evidence_ids=tuple(sorted(command.evidence_ids)),
            active_preferences=tuple(
                ActivePreferenceProjection(
                    preference_id=item.preference_id,
                    horizon=item.horizon.value,
                    provenance=item.provenance.value,
                    scope=item.scope.value,
                    target_id=item.target_id,
                    statement=item.statement,
                )
                for item in self._repository.list_active_preferences(now=self._now())
            ),
            source_focus_rules=policy.focus_rules,
            source_ignore_rules=policy.ignore_rules,
            source_policy_revision_id=policy.source_policy_revision_id,
            distillation_style=policy.distillation_style.value,
        )
        return replace(
            projection,
            preference_ids=tuple(item.preference_id for item in projection.active_preferences),
        )

    def _compose_verified_input(
        self, projection: DistillationCommand
    ) -> VerifiedDistillationInput:
        """Resolve the sole provider-visible source content through TASK-018B.

        The command remains identity/policy-only.  This boundary never reads an
        Artifact body, filesystem path, subtitle source, or caller-provided
        text: every excerpt comes from the m015 exact Evidence resolver.
        """
        if not self._legal_evidence(projection):
            raise ValueError("verified provider input evidence is not legal")
        source = self._repository.get_source_subscription(projection.source_id)
        video = self._repository.get_video(projection.video_id)
        if source is None or video is None:
            raise ValueError("verified provider input target is unavailable")
        evidence: list[VerifiedEvidenceInput] = []
        for evidence_id in tuple(sorted(projection.evidence_ids)):
            resolved = self._repository.resolve_verified_evidence_text(evidence_id)
            if resolved is None or resolved.video_id != projection.video_id:
                raise ValueError("verified provider input evidence is unbound or foreign")
            evidence.append(
                VerifiedEvidenceInput(
                    evidence_id=resolved.evidence_id,
                    start_ms=resolved.start_ms,
                    end_ms=resolved.end_ms,
                    excerpt=resolved.excerpt,
                    excerpt_hash=resolved.excerpt_hash,
                    timed_transcript_id=resolved.timed_transcript_id,
                    timed_transcript_hash=resolved.timed_transcript_hash,
                )
            )
        personalization = tuple(item.statement for item in projection.active_preferences)
        semantic_payload = {
            "distillation_style": projection.distillation_style,
            "evidence": [
                {
                    "end_ms": item.end_ms,
                    "evidence_id": item.evidence_id,
                    "excerpt_hash": item.excerpt_hash,
                    "start_ms": item.start_ms,
                    "timed_transcript_hash": item.timed_transcript_hash,
                    "timed_transcript_id": item.timed_transcript_id,
                }
                for item in evidence
            ],
            "personalization": personalization,
            "selected_model": projection.selected_model,
            "selected_provider": projection.selected_provider,
            "source_focus_rules": projection.source_focus_rules,
            "source_id": projection.source_id,
            "source_ignore_rules": projection.source_ignore_rules,
            "source_display_name": source.display_name,
            "video_id": projection.video_id,
            "video_title": video.title,
        }
        semantic_hash = hashlib.sha256(
            json.dumps(
                semantic_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        return VerifiedDistillationInput(
            source_display_name=source.display_name,
            video_id=projection.video_id,
            video_title=video.title,
            evidence=tuple(evidence),
            personalization=personalization,
            source_focus_rules=projection.source_focus_rules,
            source_ignore_rules=projection.source_ignore_rules,
            distillation_style=projection.distillation_style,
            selected_provider=projection.selected_provider,
            selected_model=projection.selected_model,
            semantic_hash=semantic_hash,
        )

    def _dispatch_and_admit(
        self,
        projection: DistillationCommand,
        verified_input: VerifiedDistillationInput,
        decision: BudgetDecision,
    ) -> DistillationResult:
        try:
            response = self._transport.generate(verified_input)
        except Exception:
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.AMBIGUOUS,
                budget_state=decision.state,
                outcome="TRANSPORT_OUTCOME_UNKNOWN",
                invocation_count=1,
            )
        if (
            response.actual_provider != projection.selected_provider
            or response.actual_model != projection.selected_model
        ):
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.REJECTED_OUTPUT,
                budget_state=decision.state,
                outcome="ACTUAL_MODEL_MISMATCH",
                invocation_count=1,
                result=response,
            )
        try:
            candidate = self._parse_candidate(response.raw, projection, verified_input)
            if isinstance(candidate, _NoNewCandidate):
                record = self._repository.record_distillation_no_new_intelligence(
                    execution_id=projection.execution_id,
                    evidence_ids=candidate.evidence_ids,
                    budget_state=decision.state,
                    actual_provider=response.actual_provider,
                    actual_model=response.actual_model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_microunits=response.cost_microunits,
                    duration_ms=response.duration_ms,
                    now=self._now(),
                )
            else:
                record = self._repository.admit_distillation(
                    execution_id=projection.execution_id,
                    intelligence_id=f"intelligence:distillation:{projection.execution_id}",
                    revision_id=f"revision:distillation:{projection.execution_id}",
                    claim_kind=candidate.claim_kind,
                    content_hash=hashlib.sha256(candidate.canonical_content).hexdigest(),
                    evidence_ids=candidate.evidence_ids,
                    evidence_stances=candidate.evidence_stances,
                    card=candidate.card,
                    actual_provider=response.actual_provider,
                    actual_model=response.actual_model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_microunits=response.cost_microunits,
                    duration_ms=response.duration_ms,
                    now=self._now(),
                )
        except (IntegrityConflict, StateStoreError, ValueError):
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.REJECTED_OUTPUT,
                budget_state=decision.state,
                outcome="STRUCTURED_OR_EVIDENCE_VALIDATION_REJECTED",
                invocation_count=1,
                result=response,
            )
        return self._result(record)

    def _reserved_command_from_record(
        self, record: DistillationExecutionRecord
    ) -> tuple[DistillationCommand, VerifiedDistillationInput]:
        if (
            record.selected_provider != self._selected_provider
            or record.selected_model != self._selected_model
        ):
            raise ValueError("reserved execution model identity does not match TASK-022 transport")
        evidence_ids = self._repository.list_available_canonical_evidence_ids(record.video_id)
        command, verified_input = self._reserved_command(
            source_id=record.source_id,
            video_id=record.video_id,
            evidence_ids=evidence_ids,
        )
        if not self._same_execution_identity(record, command):
            raise StateStoreError("reserved execution context is not persistently reconstructible")
        return command, verified_input

    def _close_claimed_reservation_as_ambiguous(
        self, record: DistillationExecutionRecord
    ) -> DistillationResult:
        if (
            record.selected_provider != self._selected_provider
            or record.selected_model != self._selected_model
        ):
            raise ValueError("reserved execution model identity does not match TASK-022 transport")
        try:
            return self._finish_execution(
                execution_id=record.execution_id,
                status=DistillationExecutionStatus.AMBIGUOUS,
                budget_state="UNKNOWN",
                outcome="RESERVED_DISPATCH_OUTCOME_UNKNOWN",
                invocation_count=1,
            )
        except StateStoreError:
            persisted = self._repository.get_distillation_execution(record.execution_id)
            if persisted is not None and persisted.status != "PENDING":
                return self._result(persisted)
            raise

    def _recover_reserved_execution(self, execution_id: str) -> DistillationResult:
        record = self._repository.get_distillation_execution(execution_id)
        if record is None:
            raise StateStoreError("reserved execution disappeared")
        if record.status != "PENDING":
            return self._result(record)
        if (
            record.budget_state == self._DISPATCH_CLAIMED
            and record.invocation_count == 1
        ):
            return self._close_claimed_reservation_as_ambiguous(record)
        raise StateStoreError("distillation execution is not a safely reserved pre-dispatch state")

    def continue_reserved_distillation(self, execution_id: str) -> DistillationResult:
        """Continue exactly one persisted reservation through the TASK-022 path.

        The public seam accepts only the canonical execution identity.  It rebuilds
        the command from persisted m010/Evidence rows, applies normal policy and
        budget gates, and atomically records a possible dispatch before calling
        the transport.  A claimed record is AMBIGUOUS, never redispatchable.
        """
        if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id) > 512:
            raise ValueError("reserved execution identity is invalid")
        record = self._repository.get_distillation_execution(execution_id)
        if record is None:
            raise ValueError("reserved execution does not exist")
        if record.status != "PENDING":
            return self._result(record)
        if (
            record.budget_state == self._DISPATCH_CLAIMED
            and record.invocation_count == 1
        ):
            return self._close_claimed_reservation_as_ambiguous(record)
        if not (
            record.budget_state == self._RESERVED_NOT_DISPATCHED
            and record.invocation_count == 0
        ):
            raise StateStoreError("distillation execution is not a safely reserved pre-dispatch state")
        if (
            record.selected_provider != self._selected_provider
            or record.selected_model != self._selected_model
        ):
            raise ValueError("reserved execution model identity does not match TASK-022 transport")
        try:
            command, verified_input = self._reserved_command_from_record(record)
        except (StateStoreError, ValueError):
            return self._finish_execution(
                execution_id=record.execution_id,
                status=DistillationExecutionStatus.REJECTED_EVIDENCE,
                budget_state="NOT_CHECKED",
                outcome="VERIFIED_INPUT_MISMATCH_OR_UNBOUND",
                invocation_count=0,
                result=None,
            )
        if not self._eligible(command):
            return self._finish_or_recover(
                command,
                status=DistillationExecutionStatus.REJECTED_INELIGIBLE,
                budget_state="NOT_CHECKED",
                outcome="SOURCE_POLICY_INELIGIBLE",
                invocation_count=0,
            )
        if not self._legal_evidence(command):
            return self._finish_or_recover(
                command,
                status=DistillationExecutionStatus.REJECTED_EVIDENCE,
                budget_state="NOT_CHECKED",
                outcome="EVIDENCE_UNAVAILABLE_OR_FOREIGN",
                invocation_count=0,
            )
        projection = self._projection(command)
        decision = self._budget.check(projection)
        if not decision.allowed:
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.WAITING_BUDGET,
                budget_state=decision.state,
                outcome="BUDGET_BLOCKED_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        if (
            not self._transport_permits(verified_input, normal_production=True)
            or not self._transport.available
        ):
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.WAITING_MODEL,
                budget_state=decision.state,
                outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        claimed = self._repository.claim_reserved_distillation_execution(
            execution_id=projection.execution_id,
            source_id=projection.source_id,
            video_id=projection.video_id,
            reason=projection.reason,
            use_case=projection.use_case,
            selected_provider=projection.selected_provider,
            selected_model=projection.selected_model,
            now=self._now(),
        )
        if not claimed:
            return self._recover_reserved_execution(projection.execution_id)
        return self._dispatch_and_admit(projection, verified_input, decision)

    def _eligible(self, command: DistillationCommand) -> bool:
        source = self._repository.get_source_subscription(command.source_id)
        if source is None or not source.enabled:
            return False
        decision = self._repository.current_filter_decision(command.source_id, command.video_id)
        return decision is not None and decision.outcome is FilterOutcome.RELEVANT

    def _legal_evidence(self, command: DistillationCommand) -> bool:
        if (
            not isinstance(command.evidence_ids, tuple)
            or not command.evidence_ids
            or len(command.evidence_ids) > 20
            or any(
                not isinstance(evidence_id, str)
                or not evidence_id.strip()
                or len(evidence_id) > 512
                for evidence_id in command.evidence_ids
            )
        ):
            return False
        evidence_ids = tuple(sorted(command.evidence_ids))
        if len(set(evidence_ids)) != len(evidence_ids):
            return False
        video = self._repository.get_video(command.video_id)
        if video is None or video.availability is not Availability.PUBLIC:
            return False
        if not self._repository.source_has_video(command.source_id, command.video_id):
            return False
        for evidence_id in evidence_ids:
            evidence = self._repository.get_evidence(evidence_id)
            if (
                evidence is None
                or evidence.video_id != command.video_id
                or evidence.availability is not EvidenceAvailability.AVAILABLE
            ):
                return False
            artifact = self._repository.get_artifact(evidence.artifact_id)
            if (
                artifact is None
                or artifact.video_id != command.video_id
                or artifact.deleted_at is not None
                or artifact.kind is not ArtifactKind.TRANSCRIPT_CANONICAL
            ):
                return False
        return True

    @staticmethod
    def _text(value: object, *, field_name: str, maximum: int = 2_000) -> str:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > maximum:
            raise ValueError(f"{field_name} is invalid")
        return value

    @classmethod
    def _texts(cls, value: object, *, field_name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or len(value) > 20:
            raise ValueError(f"{field_name} is invalid")
        return tuple(cls._text(item, field_name=field_name) for item in value)

    def _parse_candidate(
        self,
        raw: str,
        command: DistillationCommand,
        verified_input: VerifiedDistillationInput,
    ) -> _Candidate | _NoNewCandidate:
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("structured distillation output is malformed") from error
        if isinstance(payload, dict) and set(payload) == {"result", "evidence"}:
            if payload["result"] != "NO_NEW_INTELLIGENCE":
                raise ValueError("positive zero-result marker is invalid")
            evidence = payload["evidence"]
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("no-new Intelligence evidence is missing")
            expected_evidence = {
                item.evidence_id: item for item in verified_input.evidence
            }
            if tuple(sorted(expected_evidence)) != tuple(
                sorted(command.evidence_ids)
            ):
                raise ValueError(
                    "no-new Intelligence requires the verified Evidence set"
                )
            cited: set[str] = set()
            for item in evidence:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"evidence_id", "start_ms", "end_ms"}
                ):
                    raise ValueError("no-new Intelligence evidence schema is invalid")
                evidence_id = item["evidence_id"]
                start_ms = item["start_ms"]
                end_ms = item["end_ms"]
                if (
                    not isinstance(evidence_id, str)
                    or isinstance(start_ms, bool)
                    or isinstance(end_ms, bool)
                    or not isinstance(start_ms, int)
                    or not isinstance(end_ms, int)
                    or evidence_id in cited
                    or evidence_id not in expected_evidence
                ):
                    raise ValueError(
                        "no-new Intelligence evidence reference is invalid"
                    )
                expected = expected_evidence[evidence_id]
                if expected.start_ms != start_ms or expected.end_ms != end_ms:
                    raise ValueError("no-new Intelligence evidence binding is invalid")
                cited.add(evidence_id)
            if cited != set(expected_evidence):
                raise ValueError("no-new Intelligence evidence set is incomplete")
            return _NoNewCandidate(evidence_ids=tuple(sorted(cited)))
        expected_keys = {
            "core_conclusion", "user_relevant_information", "important_new_information",
            "meaningful_details", "filtered_noise", "claim_kind", "evidence",
        }
        if not isinstance(payload, dict) or set(payload) != expected_keys:
            raise ValueError("structured distillation schema is invalid")
        try:
            claim_kind = IntelligenceClaimKind(payload["claim_kind"])
        except (TypeError, ValueError) as error:
            raise ValueError("distillation claim kind is invalid") from error
        if claim_kind is IntelligenceClaimKind.UNCLASSIFIED:
            raise ValueError("distillation claim kind is unclassified")
        evidence = payload["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("distillation evidence is missing")
        expected_evidence_ids = set(verified_input.evidence_ids)
        cited_evidence_ids: set[str] = set()
        canonical_supports: dict[str, dict[str, int | str]] = {}
        evidence_stances: dict[str, EvidenceStance] = {}
        for support in evidence:
            if not isinstance(support, dict) or set(support) != {"evidence_id", "start_ms", "end_ms", "stance"}:
                raise ValueError("distillation evidence schema is invalid")
            evidence_id = support["evidence_id"]
            start_ms = support["start_ms"]
            end_ms = support["end_ms"]
            try:
                stance = EvidenceStance(support["stance"])
            except (TypeError, ValueError) as error:
                raise ValueError("distillation evidence stance is invalid") from error
            if (
                not isinstance(evidence_id, str)
                or isinstance(start_ms, bool)
                or isinstance(end_ms, bool)
                or not isinstance(start_ms, int)
                or not isinstance(end_ms, int)
                or evidence_id in cited_evidence_ids
                or evidence_id not in expected_evidence_ids
            ):
                raise ValueError("distillation evidence reference is invalid")
            evidence_record = self._repository.get_evidence(evidence_id)
            if (
                evidence_record is None
                or evidence_record.video_id != command.video_id
                or evidence_record.start_ms != start_ms
                or evidence_record.end_ms != end_ms
            ):
                raise ValueError("distillation evidence support is invalid")
            cited_evidence_ids.add(evidence_id)
            evidence_stances[evidence_id] = stance
            canonical_supports[evidence_id] = {
                "evidence_id": evidence_id,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "stance": stance.value,
            }
        if cited_evidence_ids != expected_evidence_ids:
            raise ValueError("distillation evidence support is incomplete")
        if EvidenceStance.SUPPORTING not in evidence_stances.values():
            raise ValueError("distillation requires at least one supporting Evidence")
        card = DistillationCardWrite(
            source_id=command.source_id,
            video_id=command.video_id,
            core_conclusion=self._text(payload["core_conclusion"], field_name="core conclusion", maximum=4_000),
            user_relevant_information=self._texts(payload["user_relevant_information"], field_name="user relevance"),
            important_new_information=self._texts(payload["important_new_information"], field_name="important information"),
            meaningful_details=self._texts(payload["meaningful_details"], field_name="meaningful details"),
            filtered_noise=self._texts(payload["filtered_noise"], field_name="filtered noise"),
            preference_ids=command.preference_ids,
            source_policy_revision_id=command.source_policy_revision_id,
        )
        canonical_payload = {
            **payload,
            "evidence": [
                canonical_supports[evidence_id]
                for evidence_id in sorted(cited_evidence_ids)
            ],
        }
        canonical_content = json.dumps(
            canonical_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return _Candidate(
            claim_kind=claim_kind,
            evidence_ids=tuple(sorted(cited_evidence_ids)),
            evidence_stances=tuple(
                (evidence_id, evidence_stances[evidence_id])
                for evidence_id in sorted(cited_evidence_ids)
            ),
            card=card,
            canonical_content=canonical_content,
        )

    def distill(self, command: DistillationCommand) -> DistillationResult:
        existing = self._repository.get_distillation_execution(command.execution_id)
        if existing is not None:
            if existing.status == "PENDING":
                invocation_count = (
                    1
                    if existing.budget_state == self._DISPATCH_CLAIMED
                    and existing.invocation_count == 1
                    else 0
                )
                return self._finish(
                    command,
                    status=DistillationExecutionStatus.AMBIGUOUS,
                    budget_state="UNKNOWN",
                    outcome="PRIOR_ATTEMPT_STATE_UNKNOWN",
                    invocation_count=invocation_count,
                )
            return self._result(existing)
        if not self._eligible(command):
            self._begin(command)
            return self._finish(
                command,
                status=DistillationExecutionStatus.REJECTED_INELIGIBLE,
                budget_state="NOT_CHECKED",
                outcome="SOURCE_POLICY_INELIGIBLE",
                invocation_count=0,
            )
        if not self._legal_evidence(command):
            self._begin(command)
            return self._finish(
                command,
                status=DistillationExecutionStatus.REJECTED_EVIDENCE,
                budget_state="NOT_CHECKED",
                outcome="EVIDENCE_UNAVAILABLE_OR_FOREIGN",
                invocation_count=0,
            )
        projection = self._projection(command)
        try:
            verified_input = self._compose_verified_input(projection)
        except ValueError:
            self._begin(projection)
            return self._finish(
                projection,
                status=DistillationExecutionStatus.REJECTED_EVIDENCE,
                budget_state="NOT_CHECKED",
                outcome="VERIFIED_INPUT_UNBOUND_OR_INVALID",
                invocation_count=0,
            )
        self._begin(projection)
        decision = self._budget.check(projection)
        if not decision.allowed:
            return self._finish(
                projection,
                status=DistillationExecutionStatus.WAITING_BUDGET,
                budget_state=decision.state,
                outcome="BUDGET_BLOCKED_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        if not self._transport_permits(verified_input) or not self._transport.available:
            return self._finish(
                projection,
                status=DistillationExecutionStatus.WAITING_MODEL,
                budget_state=decision.state,
                outcome="MODEL_UNAVAILABLE_BEFORE_TRANSPORT",
                invocation_count=0,
            )
        claimed = self._repository.claim_distillation_execution(
            execution_id=projection.execution_id,
            source_id=projection.source_id,
            video_id=projection.video_id,
            reason=projection.reason,
            use_case=projection.use_case,
            selected_provider=projection.selected_provider,
            selected_model=projection.selected_model,
            now=self._now(),
        )
        if not claimed:
            persisted = self._repository.get_distillation_execution(
                projection.execution_id
            )
            if persisted is not None and persisted.status != "PENDING":
                return self._result(persisted)
            return self._finish_or_recover(
                projection,
                status=DistillationExecutionStatus.AMBIGUOUS,
                budget_state="UNKNOWN",
                outcome="DISPATCH_CLAIM_STATE_UNKNOWN",
                invocation_count=(
                    1
                    if persisted is not None
                    and persisted.budget_state == self._DISPATCH_CLAIMED
                    and persisted.invocation_count == 1
                    else 0
                ),
            )
        return self._dispatch_and_admit(projection, verified_input, decision)
