"""V1.x Content-level Deep Analysis service.

This module activates the existing dormant Deep Analysis path (ADR-027
contracts, admission runtime, append-only persistence, provider adapters) as a
real Content-level product action.  It deliberately reuses those components
rather than rebuilding them.

Scope and honesty rules enforced here, from ``V1X-DR-001``:

- Deep Analysis is a **Content-level** action.  It is not a Summary
  replacement, so it never writes Summary / Video Notes authority.
- The first-version product contract is **five roles** only:
  ``CORE_CONCLUSION``, ``KEY_EVIDENCE``, ``UNCERTAINTY``,
  ``RELEVANCE_TO_USER``, ``NEXT_QUESTION``.  ``RELATION_TO_KNOWLEDGE`` and
  ``KNOWLEDGE_DELTA`` are deferred and are never projected.
- **Model qualification is an activation gate, not an architecture gate.**  No
  route is qualified unless a qualification record says so, and an unqualified
  route yields a truthful unavailable state rather than a weaker model.
- **No paid or cloud call happens without explicit per-run consent.**
- Canonical-only Content (no verified timed transcript) **fails closed**: it can
  never mint durable Evidence, so Deep Analysis reports an honest unavailable
  state instead of degrading to metadata-only citation.

Phase 1A rows remain transitional and withhold citation refs. Explicitly
injected Phase 1B routes persist native five-role claims through the shared
Evidence authority; only verified durable reads expose citation ids.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any
from uuid import uuid4

from youtube_intel.analysis import EnvironmentCredentialResolver
from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    ContextBudgetProfileV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisProviderKind,
    DeepAnalysisRequestProjectionV1,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
    UntrustedDeepAnalysisResponseV1,
    dacs1_sha256,
)
from youtube_intel.deep_analysis_evidence import (
    candidate_projection,
    deep_analysis_candidates,
)
from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceError,
    DeepAnalysisPersistenceStore,
    VerifiedPersistedDeepAnalysisRead,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.deep_analysis_phase1a_contract import (
    DeepAnalysisPhase1AModelOutput,
    map_phase_1a_output_to_knowledge_content,
)
from youtube_intel.deep_analysis_phase1b_contract import (
    PHASE_1B_MODEL_SCHEMA,
    PHASE_1B_PROMPT_IDENTITY,
    PHASE_1B_VALIDATION_POLICY,
)
from youtube_intel.deep_analysis_qualification import (
    QualificationAuthority,
    qualification_digest,
)
from youtube_intel.deep_analysis_runtime import (
    DeepAnalysisRuntime,
    PreparedDeepAnalysisDispatch,
)
from youtube_intel.domain import (
    EvidenceRegistry,
    EvidenceSource,
    KnowledgeContent,
    KnowledgeEvidence,
)
from youtube_intel.ollama_deep_analysis import (
    OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE,
    OllamaDeepAnalysisProviderAdapter,
    _OllamaTransport,
    build_ollama_local_context_budget,
    build_ollama_local_execution_profile,
    build_ollama_local_phase1a_request_projection,
    build_ollama_local_phase1b_request_projection,
)
from youtube_intel.openai_deep_analysis import (
    OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE,
    OpenAIDeepAnalysisProviderAdapter,
    _OpenAITransport,
    build_openai_phase1b_request_projection,
    build_openai_reference_context_budget,
    build_openai_reference_execution_profile,
    probe_openai_model,
)
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import (
    ProviderCallRequest,
    ProviderDispatchStatus,
    SQLiteStateRepository,
    format_utc_datetime,
)

#: V1.x Deep Analysis prompt/policy identities.  These are part of the A1/A2
#: request identity, so changing them cannot alias an older cached result.
_DEEP_ANALYSIS_PROMPT_IDENTITY = "v1x-content-deep-analysis-prompt-v1"
_SELECTION_POLICY_IDENTITY = "v1x-content-deep-analysis-selection-v1"
_COVERAGE_POLICY_IDENTITY = "v1x-content-deep-analysis-coverage-v1"
_OPERATION_VERSION = "v1x-content-deep-analysis-v1"
_INPUT_SCHEMA_VERSION = "v1x-content-deep-analysis-input-v1"
_REGISTRY_IDENTITY_PREFIX = "v1x-content-deep-analysis-registry-v1"
_REGISTRY_IDENTITY_SUFFIX = "transient-candidate-refs"

#: Deterministic selection bound.  A long Content is represented by a bounded
#: number of real transcript spans so the request stays inside the qualified
#: provider input budget without sending an unrestricted full transcript.
_MAX_SELECTED_EVIDENCE = 24
_MAX_EXCERPT_CHARS = 2000

#: User-facing Evidence citation state.
#:
#: Phase 1A is transitional: internal candidate refs exist only inside the
#: admission boundary and are **not** durable Evidence identity. They are never
#: projected to the user, so no citation can be presented as authoritative.
#: Phase 1B resolves transient ref -> backend validation -> durable
#: ``evidence.evidence_id`` before any persisted authoritative citation exists.
EVIDENCE_CITATION_STATUS_PENDING = "PENDING_DURABLE_EVIDENCE_CONVERGENCE"

#: Explicit non-authoritative marker for compatibility persistence.
#:
#: The frozen dormant contract persists the model-visible Evidence registry
#: internally. Those ids are backend-issued candidate refs scoped to one request,
#: not durable Evidence, so this constant records that transitional status and is
#: what every trusted read path must treat them as.
TRANSIENT_EVIDENCE_REF_AUTHORITY = "TRANSITIONAL_NON_AUTHORITATIVE"

#: The five first-version product roles.  Order is the user-facing order.
DEEP_ANALYSIS_ROLES: tuple[str, ...] = (
    "CORE_CONCLUSION",
    "KEY_EVIDENCE",
    "UNCERTAINTY",
    "RELEVANCE_TO_USER",
    "NEXT_QUESTION",
)

#: Explicitly deferred roles.  Asserted absent from every projection so they
#: cannot be silently reintroduced.
DEFERRED_DEEP_ANALYSIS_ROLES: frozenset[str] = frozenset(
    {"RELATION_TO_KNOWLEDGE", "KNOWLEDGE_DELTA"}
)


class DeepAnalysisCostState(str, Enum):
    KNOWN = "KNOWN"
    ESTIMATED = "ESTIMATED"
    FREE = "FREE"
    UNKNOWN = "UNKNOWN"


class DeepAnalysisAvailability(str, Enum):
    """Truthful availability states for the Deep Analysis action."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    SCORING_UNAVAILABLE = "SCORING_UNAVAILABLE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    CLOUD_CONSENT_REQUIRED = "CLOUD_CONSENT_REQUIRED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class DeepAnalysisRoute:
    """One narrow Deep Analysis candidate with a concrete provider/model profile.

    This is deliberately **not** a generic router.  A route is a concrete
    (provider, model) pairing pinned by ADR-027 identities. Qualification is
    granted separately by reviewed Phase 1C authority. There is no escalation, no
    implicit fallback, and no silent local-to-cloud switch.
    """

    route_id: str
    provider_kind: DeepAnalysisProviderKind
    provider_id: str
    model_id: str
    qualified_capability_profile_identity: str
    is_local: bool
    dispatch: Callable[..., UntrustedDeepAnalysisResponseV1]
    build_request_projection: Callable[..., DeepAnalysisRequestProjectionV1]
    build_execution_profile: Callable[..., DeepAnalysisExecutionProfileV1]
    build_context_budget: Callable[..., ContextBudgetProfileV1]
    input_budget: int
    model_output_schema_identity: str = "v1x-content-deep-analysis-model-output-v1"
    profile_identity: str = "legacy-developer-injection"
    configured: Callable[[], bool] = lambda: True
    reachability: Callable[[], str] = lambda: "REACHABLE"
    credential_configured: Callable[[], bool] = lambda: True
    timeout_profile_identity: str | None = None

    def describe(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "provider_kind": self.provider_kind.value,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "qualified_capability_profile_identity": (
                self.qualified_capability_profile_identity
            ),
            "requires_consent": not self.is_local,
        }


def build_local_ollama_route(
    *, transport: _OllamaTransport | None = None
) -> DeepAnalysisRoute:
    """Build the pinned local Ollama route.

    ``qwen2.5-coder:7b`` remains **dev/test only** and is not assumed
    production-qualified.  Callers must pass an explicit qualification record
    before this route becomes available; see
    :class:`DeepAnalysisCapability`.
    """

    adapter = (
        OllamaDeepAnalysisProviderAdapter()
        if transport is None
        else OllamaDeepAnalysisProviderAdapter(transport=transport)
    )
    profile = OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE
    return DeepAnalysisRoute(
        route_id="local-ollama-qwen25-coder-7b",
        provider_kind=profile.provider_kind,
        provider_id=profile.provider_id,
        model_id=profile.model_id,
        qualified_capability_profile_identity=profile.qualified_capability_profile_identity,
        is_local=True,
        dispatch=adapter.dispatch,
        build_request_projection=build_ollama_local_phase1a_request_projection,
        build_execution_profile=build_ollama_local_execution_profile,
        build_context_budget=build_ollama_local_context_budget,
        input_budget=8192,
    )


def build_local_ollama_phase1b_route(
    *, transport: _OllamaTransport | None = None,
) -> DeepAnalysisRoute:
    """Explicit dev/test injection only; this does not qualify production."""
    return replace(
        build_local_ollama_route(transport=transport),
        route_id="local-ollama-phase1b-dev-test",
        build_request_projection=build_ollama_local_phase1b_request_projection,
        model_output_schema_identity=PHASE_1B_MODEL_SCHEMA,
        profile_identity=qualification_digest(asdict(OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE)),
    )


def build_openai_phase1b_route(
    *, transport: _OpenAITransport | None = None,
    credential_resolver: Callable[[], str | None] | None = None,
    reachability: Callable[[], str] | None = None,
) -> DeepAnalysisRoute:
    """Reuse the isolated no-retry SDK adapter and committed environment resolver."""
    resolve = credential_resolver or (lambda: EnvironmentCredentialResolver().resolve("OPENAI_API_KEY"))
    adapter = OpenAIDeepAnalysisProviderAdapter() if transport is None else OpenAIDeepAnalysisProviderAdapter(transport=transport)
    profile = OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE
    def dispatch(*, prepared_dispatch: PreparedDeepAnalysisDispatch) -> UntrustedDeepAnalysisResponseV1:
        secret = resolve()
        if not secret:
            raise ValueError("credential unavailable")
        return adapter.dispatch(prepared_dispatch=prepared_dispatch, credential=secret)
    return DeepAnalysisRoute(
        route_id="openai-content-deep-analysis-phase1b", provider_kind=profile.provider_kind,
        provider_id=profile.provider_id, model_id=profile.model_id,
        qualified_capability_profile_identity=profile.qualified_capability_profile_identity,
        is_local=False, dispatch=dispatch, build_request_projection=build_openai_phase1b_request_projection,
        build_execution_profile=build_openai_reference_execution_profile,
        build_context_budget=build_openai_reference_context_budget, input_budget=8192,
        model_output_schema_identity=PHASE_1B_MODEL_SCHEMA,
        profile_identity=qualification_digest(asdict(profile)),
        configured=lambda: bool(resolve()), credential_configured=lambda: bool(resolve()),
        reachability=reachability or (lambda: probe_openai_model(resolve())),
        timeout_profile_identity=profile.timeout_profile_identity,
    )


class DeepAnalysisCapability:
    """One DA capability registry, with an explicit production authority boundary.

    The authority-free constructor is the historical *developer injection* seam
    for Phase 1A/1B fixtures, never used by production composition. A governed
    registry reports every candidate separately and exposes only eligible routes.
    """
    def __init__(self, routes: tuple[DeepAnalysisRoute, ...] = (), *,
                 authority: QualificationAuthority | None = None) -> None:
        identifiers = [route.route_id for route in routes]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Deep Analysis route identities must be unique")
        self._candidates = routes
        self.authority = authority

    def route_state(self, route: DeepAnalysisRoute) -> dict[str, object]:
        try:
            configured = route.configured()
            credential = route.is_local or route.credential_configured()
            live = self.authority is not None and self.authority.qualified(route)
            reachable = route.reachability() if configured and credential and (route.is_local or live) else "NOT_CHECKED"
        except Exception:
            configured, credential, reachable = False, False, "UNREACHABLE"
        contract = route.model_output_schema_identity == PHASE_1B_MODEL_SCHEMA
        qualification = self.authority.state(route) if self.authority else "DEVELOPER_INJECTION"
        qualified = self.authority.qualified(route) if self.authority else False
        eligible = configured and credential and reachable == "REACHABLE" and contract and qualified
        reason = ("CREDENTIAL_MISSING" if not credential else "NOT_CONFIGURED" if not configured
                  else "ROUTE_UNREACHABLE" if reachable == "UNREACHABLE"
                  else "REACHABILITY_NOT_CHECKED" if reachable != "REACHABLE"
                  else "CONTRACT_UNSUPPORTED" if not contract
                  else "QUALIFICATION_" + qualification if not qualified else "PRODUCTION_ELIGIBLE")
        return {**route.describe(), "configured": configured, "credential_configured": credential,
                "reachability": reachable, "contract_capable": contract, "qualification_status": qualification,
                "qualified": qualified, "production_eligible": eligible, "reason_code": reason,
                "data_egress_mode": "NONE" if route.is_local else "SELECTED_EVIDENCE_ONLY",
                "cost_state": DeepAnalysisCostState.FREE.value if route.is_local else DeepAnalysisCostState.UNKNOWN.value,
                "hard_monetary_cap": False}

    @property
    def routes(self) -> tuple[DeepAnalysisRoute, ...]:
        if self.authority is None:
            # Historical fixture execution is local only. Cloud always needs
            # reviewed qualification, even in an injected product service.
            return tuple(r for r in self._candidates if r.is_local)
        return tuple(r for r in self._candidates if self.route_state(r)["production_eligible"])

    def local_route(self) -> DeepAnalysisRoute | None:
        return next((r for r in self.routes if r.is_local), None)

    def execution_route(self, route_id: str | None = None) -> DeepAnalysisRoute | None:
        if route_id is not None:
            return next((r for r in self.routes if r.route_id == route_id), None)
        return self.local_route() or next(iter(self.routes), None)

    def describe(self) -> list[dict[str, object]]:
        return [self.route_state(route) for route in self._candidates]


@dataclass(frozen=True)
class _CloudPreflight:
    content_id: str
    route: DeepAnalysisRoute
    prepared: PreparedDeepAnalysisDispatch
    runtime: DeepAnalysisRuntime
    selected_refs: tuple[str, ...]
    context_identity: str
    cost: dict[str, object]
    expires_at: datetime


class DeepAnalysisReasonCode(str, Enum):
    """Stable machine reason codes for Deep Analysis states.

    The user interface localizes on these codes. Free-form English prose is a
    developer diagnostic only and must never be the Chinese product text.
    """

    NO_QUALIFIED_MODEL = "NO_QUALIFIED_MODEL"
    CREDENTIAL_MISSING = "CREDENTIAL_MISSING"
    ROUTE_UNREACHABLE = "ROUTE_UNREACHABLE"
    PRODUCTION_ROUTE_UNAVAILABLE = "PRODUCTION_ROUTE_UNAVAILABLE"
    CONTENT_NOT_FOUND = "CONTENT_NOT_FOUND"
    NOT_REQUESTED = "NOT_REQUESTED"
    RESULT_AVAILABLE = "RESULT_AVAILABLE"
    SCORING_UNAVAILABLE = "SCORING_UNAVAILABLE"
    NO_TIMED_TRANSCRIPT_EVIDENCE = "NO_TIMED_TRANSCRIPT_EVIDENCE"
    CLOUD_CONSENT_REQUIRED = "CLOUD_CONSENT_REQUIRED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    PREFLIGHT_CHANGED = "PREFLIGHT_CHANGED"
    DISPATCH_AMBIGUOUS = "DISPATCH_AMBIGUOUS"
    EXECUTION_ALREADY_DISPATCHED = "EXECUTION_ALREADY_DISPATCHED"
    COST_ACKNOWLEDGEMENT_REQUIRED = "COST_ACKNOWLEDGEMENT_REQUIRED"


@dataclass(frozen=True, slots=True)
class DeepAnalysisStatus:
    """One truthful, user-facing Deep Analysis state for a Content."""

    availability: DeepAnalysisAvailability
    reason: str | None = None
    reason_code: DeepAnalysisReasonCode | None = None
    route_id: str | None = None
    model_id: str | None = None
    provider_id: str | None = None
    qualified: bool = False
    consent_required: bool = False
    production_eligible: bool = False
    routes: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "availability": self.availability.value,
            # Machine code drives localized user-facing copy.
            "reason_code": (
                None if self.reason_code is None else self.reason_code.value
            ),
            # English diagnostic text for developers; not product copy.
            "reason": self.reason,
            "route_id": self.route_id,
            "model_id": self.model_id,
            "provider_id": self.provider_id,
            "qualified": self.qualified,
            "consent_required": self.consent_required,
            "production_eligible": self.production_eligible,
            "routes": list(self.routes),
        }


@dataclass(frozen=True, slots=True)
class DeepAnalysisClaim:
    """One claim in a user-facing role.

    ``evidence_ids`` is intentionally always empty in Phase 1A.  Durable
    Evidence convergence is Phase 1B; until then no transient candidate ref is
    ever presented to the user as an authoritative citation.
    """

    text: str
    role: str
    point_kind: str
    confidence: str
    evidence_ids: tuple[str, ...] = ()
    language_validation: str | None = None


@dataclass(frozen=True, slots=True)
class DeepAnalysisResultView:
    """User-facing projection of one verified Deep Analysis result."""

    content_id: str
    result_identity: str
    content_identity: str
    output_language: str
    roles: tuple[DeepAnalysisClaim, ...]
    generated_at: str
    evidence_citation_status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "content_id": self.content_id,
            "result_identity": self.result_identity,
            "content_identity": self.content_identity,
            "output_language": self.output_language,
            "generated_at": self.generated_at,
            "evidence_citation_status": self.evidence_citation_status,
            "roles": [
                {
                    "role": claim.role,
                    "text": claim.text,
                    "point_kind": claim.point_kind,
                    "confidence": claim.confidence,
                    **({"evidence_ids": list(claim.evidence_ids), "language_validation": claim.language_validation}
                       if self.evidence_citation_status == "DURABLE_EVIDENCE_VERIFIED" else {}),
                }
                for claim in self.roles
            ],
        }


#: Confidence codes the Phase-1A projection may emit. These are stable machine
#: codes; the user interface localizes them and must never display the raw enum.
CONFIDENCE_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _confidence_label(point: KnowledgeEvidence | Any) -> str:
    """Return a stable confidence code for one projected claim.

    The frozen carrier carries no per-claim confidence value, so Phase 1A
    honestly reports ``INSUFFICIENT_EVIDENCE`` rather than inventing a
    precision. Never returns a percentage.
    """

    raw = getattr(point, "confidence", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return CONFIDENCE_INSUFFICIENT_EVIDENCE


def project_deep_analysis_result(
    result: VerifiedPersistedDeepAnalysisRead,
) -> DeepAnalysisResultView:
    """Project a verified result into the five first-version product roles.

    The projection is deterministic and derived only from the already-verified
    ``KnowledgeContent``.  It introduces no new claim authority and does not
    restate or reinterpret the model output beyond role selection and honest
    confidence labeling.

    ``RELATION_TO_KNOWLEDGE`` and ``KNOWLEDGE_DELTA`` are never projected.
    """

    content: KnowledgeContent = result.content
    output_language = result.request_projection.output_language
    claims: list[DeepAnalysisClaim] = []
    if not verify_persisted_deep_analysis_read(result):
        raise DeepAnalysisPersistenceError("projection requires a verified result")
    if result.durable_result is not None:
        return DeepAnalysisResultView(
            content_id=result.canonical_input.video_identity,
            result_identity=result.result_identity,
            content_identity=result.content_identity,
            output_language=output_language,
            roles=tuple(DeepAnalysisClaim(
                text=c.text, role=c.role, point_kind=c.point_kind,
                confidence=CONFIDENCE_INSUFFICIENT_EVIDENCE,
                evidence_ids=c.evidence_refs, language_validation=c.language_validation,
            ) for c in result.durable_result.claims),
            generated_at=format_utc_datetime(result.created_at),
            evidence_citation_status="DURABLE_EVIDENCE_VERIFIED",
        )

    def add(text: str, role: str, point: Any) -> None:
        # No projection-time trimming: claim text was canonicalized once at the
        # Phase-1A admission boundary, so the accepted value is projected
        # verbatim. Re-stripping here would silently change accepted content.
        if not text:
            return
        kind = getattr(point, "kind", None)
        kind_value = getattr(kind, "value", None)
        point_kind = kind_value if isinstance(kind_value, str) else ""
        claims.append(
            DeepAnalysisClaim(
                text=text,
                role=role,
                point_kind=str(point_kind),
                confidence=_confidence_label(point),
            )
        )

    # Every role is projected from exactly one carrier field, so the projection
    # is a lossless 1:1 view of what the model authored. Reading a role from a
    # field the mapper does not populate would silently drop claims.
    for point in content.core_points:
        add(point.text, "CORE_CONCLUSION", point)
    for point in content.key_facts:
        add(point.text, "KEY_EVIDENCE", point)
    for point in content.counterpoints:
        add(point.text, "UNCERTAINTY", point)
    for point in content.product_opportunities:
        add(point.text, "RELEVANCE_TO_USER", point)
    for point in content.hypotheses_to_validate:
        add(point.text, "NEXT_QUESTION", point)

    presented = {claim.role for claim in claims}
    if presented & DEFERRED_DEEP_ANALYSIS_ROLES:
        msg = "deferred Deep Analysis roles must never be projected"
        raise ValueError(msg)
    unknown = presented - set(DEEP_ANALYSIS_ROLES)
    if unknown:
        msg = f"unsupported Deep Analysis roles: {sorted(unknown)}"
        raise ValueError(msg)

    return DeepAnalysisResultView(
        content_id=result.canonical_input.video_identity,
        result_identity=result.result_identity,
        content_identity=result.content_identity,
        output_language=output_language,
        roles=tuple(claims),
        # Authoritative: the durable row's own persisted creation time. It is
        # never derived from the current read time, so repeated reads and a full
        # restart always report the same generation time.
        generated_at=format_utc_datetime(result.created_at),
        evidence_citation_status=EVIDENCE_CITATION_STATUS_PENDING,
    )


def _map_phase_1a_response(
    response: UntrustedDeepAnalysisResponseV1,
    *,
    evidence_refs: tuple[str, ...],
) -> UntrustedDeepAnalysisResponseV1 | None:
    """Translate the five-concept model payload into the frozen carrier.

    Every model response entering the Phase-1A live path **must** validate as
    :class:`DeepAnalysisPhase1AModelOutput` first. There is deliberately no
    pass-through for a historical ``KnowledgeContent`` payload: such a response
    could carry model-authored ``entities``, ``related_themes``,
    ``future_watch_topics``, or other deferred structure and would bypass the
    five-role boundary.

    Correct flow:

        raw provider response
        -> five-role parsing/validation (extra fields rejected)
        -> deterministic backend compatibility mapping
        -> historical KnowledgeContent carrier
        -> existing runtime finalizer

    The carrier is *output* of this mapper and is never an alternate admission
    contract. A rejected payload is forwarded unchanged so the runtime produces
    its own authoritative failure; it is never repaired or passed through.

    Returns ``None`` when the payload fails five-role admission. The caller must
    then fail the run; the response is never forwarded, because a historical
    ``KnowledgeContent`` payload is itself schema-valid for the frozen carrier
    and would otherwise be admitted.

    It performs no trust decision: the mapping is pure, the returned object is
    still untrusted, and the runtime finalizer remains the sole minter of
    ``TrustedDeepAnalysisSuccess``.
    """

    if isinstance(response.structured_payload, bytes):
        try:
            decoded = json.loads(response.structured_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
    else:
        decoded = response.structured_payload
    if not isinstance(decoded, Mapping):
        return None
    try:
        # Strict five-role admission: extra="forbid" rejects any historical or
        # deferred field the model must not author.
        model_output = DeepAnalysisPhase1AModelOutput.model_validate(decoded)
    except ValueError:
        # Explicitly rejected: the payload is NOT passed through, so a historical
        # KnowledgeContent shape cannot survive into persistence.
        return None
    content = map_phase_1a_output_to_knowledge_content(
        model_output, summary_evidence_ids=evidence_refs
    )
    mapped = content.model_dump(mode="json")
    return UntrustedDeepAnalysisResponseV1(
        schema_version="untrusted-deep-analysis-response-v1",
        expected_dispatch_identity=response.expected_dispatch_identity,
        provider_envelope_bytes=response.provider_envelope_bytes,
        structured_payload=json.dumps(
            mapped, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8"),
        structured_output_mode=response.structured_output_mode,
        provider_request_id=response.provider_request_id,
        finish_reason=response.finish_reason,
        delivery_certainty=response.delivery_certainty,
        response_metadata=response.response_metadata,
        usage_evidence=response.usage_evidence,
    )


class DeepAnalysisRejected(RuntimeError):
    """An honest refusal: Deep Analysis cannot run for this Content right now."""

    def __init__(self, status: DeepAnalysisStatus) -> None:
        super().__init__(status.reason or status.availability.value)
        self.status = status


class DeepAnalysisService:
    """Orchestrate one Content-level Deep Analysis run and its verified read.

    The service owns no model authority of its own.  It delegates admission to
    the existing :class:`DeepAnalysisRuntime`, dispatch to an explicitly
    qualified route, and persistence to the existing append-only store.
    """

    def __init__(
        self,
        *,
        repository: SQLiteStateRepository,
        capability: DeepAnalysisCapability,
        scoring_reader: Callable[[str], VerifiedScoringRead],
        transcript_reader: Callable[..., Any],
        evidence_reader: Callable[[str], tuple[str, ...]],
        evidence_text_reader: Callable[[str], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._capability = capability
        self._scoring_reader = scoring_reader
        self._transcript_reader = transcript_reader
        self._evidence_reader = evidence_reader
        self._evidence_text_reader = evidence_text_reader
        self._clock = now or (lambda: datetime.now(UTC))
        self._store = DeepAnalysisPersistenceStore(repository)
        # The Phase-1A validation policy carries an explicit marker so persisted
        # Phase-1A results stay identifiable as transitional after restart, and
        # can be kept out of trusted Evidence-bearing projections. Every other
        # dimension stays identical to the frozen default, so the qualified
        # adapter's provenance binding continues to hold.
        # The frozen default validation policy is used unchanged: the qualified
        # adapter binds its identity, so substituting a policy here would break
        # provenance. Phase-1A transitional state is instead derived from the
        # persisted Phase-1A prompt identity (see ``is_phase_1a_result``).
        self._runtime = DeepAnalysisRuntime()
        self._preflights: dict[str, _CloudPreflight] = {}
        self._preflight_lock = Lock()

    # -- status ------------------------------------------------------------

    def capability_report(self) -> dict[str, object]:
        routes = self._capability.describe()
        qualified = any(r["qualified"] for r in routes)
        eligible = bool(self._capability.routes)
        return {
            "qualified": qualified,
            "production_eligible": eligible,
            "routes": routes,
            "reason": (
                None
                if eligible
                else "No production-eligible Deep Analysis route is available."
                if qualified
                else "No Deep Analysis model is currently qualified. "
                "Deep Analysis stays unavailable until one qualifies."
            ),
        }

    def status(self, *, content_id: str) -> DeepAnalysisStatus:
        """Return the truthful current Deep Analysis state for one Content."""

        content = self._repository.get_video(content_id)
        if content is None:
            return DeepAnalysisStatus(
                availability=DeepAnalysisAvailability.CONTENT_UNAVAILABLE,
                reason_code=DeepAnalysisReasonCode.CONTENT_NOT_FOUND,
                reason="Content does not exist.",
            )
        route = self._capability.execution_route()
        if route is None:
            states = tuple(self._capability.describe())
            qualified_route = next((r for r in states if r["qualified"]), None)
            reason = DeepAnalysisReasonCode.NO_QUALIFIED_MODEL
            if qualified_route is not None:
                reason = {
                    "CREDENTIAL_MISSING": DeepAnalysisReasonCode.CREDENTIAL_MISSING,
                    "ROUTE_UNREACHABLE": DeepAnalysisReasonCode.ROUTE_UNREACHABLE,
                }.get(str(qualified_route["reason_code"]), DeepAnalysisReasonCode.PRODUCTION_ROUTE_UNAVAILABLE)
            return DeepAnalysisStatus(
                availability=DeepAnalysisAvailability.UNAVAILABLE if qualified_route else DeepAnalysisAvailability.NOT_QUALIFIED,
                reason_code=reason,
                qualified=qualified_route is not None,
                routes=states,
                reason=(
                    "A qualified Deep Analysis route cannot execute in this environment."
                    if qualified_route is not None else
                    "No Deep Analysis model is currently qualified. "
                    "Deep Analysis is unavailable; Summary and Evidence remain usable."
                ),
            )
        existing = self._read(content_id)
        if existing is not None:
            return DeepAnalysisStatus(
                availability=DeepAnalysisAvailability.AVAILABLE,
                reason_code=DeepAnalysisReasonCode.RESULT_AVAILABLE,
                route_id=route.route_id,
                model_id=route.model_id,
                provider_id=route.provider_id,
                qualified=True,
                production_eligible=self._capability.authority is not None,
                consent_required=not route.is_local,
                routes=tuple(self._capability.describe()),
            )
        return DeepAnalysisStatus(
            availability=DeepAnalysisAvailability.NOT_REQUESTED,
            reason_code=DeepAnalysisReasonCode.NOT_REQUESTED,
            route_id=route.route_id,
            model_id=route.model_id,
            provider_id=route.provider_id,
            qualified=True,
            production_eligible=self._capability.authority is not None,
            consent_required=not route.is_local,
            routes=tuple(self._capability.describe()),
        )

    def read(self, *, content_id: str) -> DeepAnalysisResultView | None:
        """Read the verified Deep Analysis result for one Content, if any."""

        result = self._read(content_id)
        return None if result is None else project_deep_analysis_result(result)

    def _read(self, content_id: str) -> VerifiedPersistedDeepAnalysisRead | None:
        try:
            result = self._store.read_deep_analysis_result_for_content(
                video_id=content_id
            )
        except DeepAnalysisPersistenceError:
            return None
        if result is None or not verify_persisted_deep_analysis_read(result):
            return None
        return result

    # -- execution ---------------------------------------------------------

    def _reject(self, code: DeepAnalysisReasonCode) -> DeepAnalysisRejected:
        return DeepAnalysisRejected(DeepAnalysisStatus(
            availability=DeepAnalysisAvailability.FAILED, reason_code=code,
            reason="Deep Analysis execution was refused safely.",
        ))

    def _prepare(self, content_id: str, route: DeepAnalysisRoute,
                 authorization_identity: str | None = None) -> tuple[DeepAnalysisRuntime, PreparedDeepAnalysisDispatch, tuple[str, ...]]:
        try:
            read = self._scoring_reader(content_id)
        except Exception:
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.SCORING_UNAVAILABLE,
                    reason_code=DeepAnalysisReasonCode.SCORING_UNAVAILABLE,
                    reason=(
                        "Deep Analysis requires a verified scoring read for this "
                        "Content. It is unavailable right now."
                    ),
                )
            ) from None

        phase1b = route.model_output_schema_identity == PHASE_1B_MODEL_SCHEMA
        runtime = DeepAnalysisRuntime(validation_policy=PHASE_1B_VALIDATION_POLICY) if phase1b else self._runtime
        transcript = self._repository.get_verified_timed_transcript(video_id=content_id) if phase1b else None
        candidates = deep_analysis_candidates(transcript) if transcript is not None else None
        native_registry = candidate_projection(candidates) if candidates is not None else None
        selection = ([{"evidence_id": c.evidence_id, "excerpt": c.excerpt, "excerpt_hash": c.source_content_hash}
                      for c in native_registry.items] if native_registry is not None else []) if phase1b else self._select_evidence(content_id)
        if not selection:
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.EVIDENCE_UNAVAILABLE,
                    reason_code=DeepAnalysisReasonCode.NO_TIMED_TRANSCRIPT_EVIDENCE,
                    reason=(
                        "This Content has no trusted timed transcript Evidence, "
                        "so Deep Analysis cannot cite anything durably. No "
                        "timestamp is invented and no result is produced."
                    ),
                )
            )

        output_language = self._output_language()
        selected_refs = tuple(item["evidence_id"] for item in selection)
        registry = EvidenceRegistry(
            items=tuple(
                KnowledgeEvidence(
                    evidence_id=item["evidence_id"],
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    excerpt=item["excerpt"],
                    source_content_hash=item["excerpt_hash"],
                )
                for item in selection
            )
        )
        registry_identity = f"{_REGISTRY_IDENTITY_PREFIX}-{content_id}-"\
            f"{_REGISTRY_IDENTITY_SUFFIX}"
        if candidates is not None:
            registry_identity = candidates.identity_hash()
        canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
            verified_scoring_read=read,
            schema_version="canonical-deep-analysis-input-v1",
            operation="content-deep-analysis",
            input_schema_version=_INPUT_SCHEMA_VERSION,
            video_identity=content_id,
            transcript_identity=transcript.timed_transcript_id if transcript is not None else registry_identity,
            transcript_language=self._source_language(content_id),
            transcript_normalization_version="v1x-content-deep-analysis-norm-v1",
            evidence_registry_identity=registry_identity,
            selected_evidence=tuple(
                {
                    "schema_version": "selected-evidence-projection-v1",
                    "evidence_id": item["evidence_id"],
                    "source": EvidenceSource.TRANSCRIPT_SAMPLE.value,
                    "excerpt": item["excerpt"],
                }
                for item in selection
            ),
            selection_policy_identity=_SELECTION_POLICY_IDENTITY,
            coverage_policy_identity=_COVERAGE_POLICY_IDENTITY,
            coverage_complete=False,
            output_language=output_language,
            knowledge_content_schema_version=PHASE_1B_MODEL_SCHEMA if phase1b else "knowledge-content-pydantic-v1",
            prompt_version=PHASE_1B_PROMPT_IDENTITY if phase1b else _DEEP_ANALYSIS_PROMPT_IDENTITY,
            operation_version=_OPERATION_VERSION,
        )

        admitted = runtime.admit_verified_scoring_read(
            verified_scoring_read=read, canonical_input=canonical
        )
        consent = PayloadConsentIdentityV1(
            schema_version="payload-consent-identity-v1",
            consent_mode=(
                PayloadConsentMode.LOCAL_ONLY
                if route.is_local
                else PayloadConsentMode.PER_RUN_CLOUD_APPROVAL
            ),
            authorization_record_identity=authorization_identity or (f"v1x-deep-analysis-{content_id}-" f"{canonical.a1_identity[:16]}"),
            named_provider_id=route.provider_id,
            provider_kind=route.provider_kind,
            payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
            allowed_model_constraint=route.model_id,
            exact_run_nonce_or_null=None if route.is_local else (authorization_identity or "preflight-preview-only"),
        )
        content = self._repository.get_video(content_id)
        payload = runtime.authorize_payload(
            authoritative_input=admitted,
            evidence_registry=registry,
            payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
            payload_consent=consent,
            video_title=(content.title if route.is_local and content and content.title else "Content"),
            channel_name=(
                content.channel_name if route.is_local and content and content.channel_name else "Source"
            ),
            published_at=(
                content.published_at.isoformat()
                if route.is_local and content is not None and content.published_at is not None
                else "UNKNOWN"
            ),
            duration_seconds=0,
            source_language=self._source_language(content_id),
        )
        request = route.build_request_projection(
            canonical_input=canonical,
            authorized_payload=payload.payload,
            payload_consent=consent,
        )
        execution = route.build_execution_profile(
            request_projection=request,
            credential_execution_profile=CredentialExecutionProfileIdentityV1(
                schema_version="credential-execution-profile-v1",
                provider_id=route.provider_id,
                # Structural, non-secret profile digest for the local process
                # runtime. It carries no credential material.
                execution_profile_identity=dacs1_sha256(
                    {
                        "schema_version": "v1x-deep-analysis-credential-profile-v1",
                        "provider_id": route.provider_id,
                        "route_id": route.route_id,
                        "process": "local-process-v1",
                    }
                ),
            ),
        )
        prepared = runtime.prepare_dispatch(
            authoritative_input=admitted,
            authorized_payload=payload,
            request_projection=request,
            execution_profile=execution,
            payload_consent=consent,
            context_budget_profile=route.build_context_budget(
                input_budget=route.input_budget
            ),
            timeout_profile_identity=route.timeout_profile_identity or f"{route.route_id}-timeout-v1",
            # A V1.x Content Deep Analysis run is a single explicit execution:
            # there is no fallback DAG, so the policy identity records "no
            # fallback" rather than describing any escalation plan.
            fallback_policy_identity=dacs1_sha256(
                {
                    "schema_version": "v1x-deep-analysis-fallback-policy-v1",
                    "route_id": route.route_id,
                    "fallback": "NONE",
                }
            ),
        )
        return runtime, prepared, selected_refs

    def _context_identity(self, content_id: str, route: DeepAnalysisRoute) -> str:
        runtime, prepared, _ = self._prepare(content_id, route)
        del runtime
        return self._prepared_context_identity(prepared, route)

    def _prepared_context_identity(self, prepared: PreparedDeepAnalysisDispatch,
                                   route: DeepAnalysisRoute) -> str:
        # Compare complete immutable input/request/profile semantics. Normalize
        # only the consent digest and its derived A2 link, which differ between
        # the preview nonce and the final per-execution authorization nonce.
        context = prepared.envelope.model_dump(mode="python")
        context.pop("payload_consent")
        context["request_projection"].pop("payload_consent_identity")
        context["execution_profile"].pop("a2_identity")
        return qualification_digest({
            "dispatch_context": context,
            "route_profile": route.profile_identity,
            "provider": route.provider_id, "model": route.model_id,
            "qualification": self._capability.authority.state(route) if self._capability.authority else "DEVELOPER_INJECTION",
        })

    def preflight(self, *, content_id: str, route_id: str) -> dict[str, object]:
        route = self._capability.execution_route(route_id)
        if route is None or route.is_local:
            status = self.status(content_id=content_id)
            if route is None and status.availability is DeepAnalysisAvailability.UNAVAILABLE:
                raise DeepAnalysisRejected(status)
            raise self._reject(DeepAnalysisReasonCode.NO_QUALIFIED_MODEL)
        execution_id = uuid4().hex
        cost: dict[str, object] = {"state": DeepAnalysisCostState.UNKNOWN.value, "hard_monetary_cap": False,
                                  "amount": None, "currency": None}
        _, preview, _ = self._prepare(content_id, route)
        context_identity = self._prepared_context_identity(preview, route)
        cost["input_characters"] = sum(len(m.content) for m in preview.envelope.request_projection.provider_visible_messages)
        authorization = qualification_digest({"execution_id": execution_id,
            "content_id": content_id, "context": context_identity, "cost": cost,
            "provider": route.provider_id, "model": route.model_id, "operation": "content-deep-analysis",
            "egress": "SELECTED_EVIDENCE_ONLY"})
        runtime, prepared, refs = self._prepare(content_id, route, f"phase1c:{execution_id}:{authorization}")
        if self._prepared_context_identity(prepared, route) != context_identity:
            raise self._reject(DeepAnalysisReasonCode.PREFLIGHT_CHANGED)
        entry = _CloudPreflight(content_id, route, prepared, runtime, refs, context_identity, cost, self._clock() + timedelta(minutes=10))
        with self._preflight_lock:
            self._preflights = {k: v for k, v in self._preflights.items() if v.expires_at > self._clock()}
            if len(self._preflights) >= 256:
                raise self._reject(DeepAnalysisReasonCode.SERVICE_UNAVAILABLE)
            self._preflights[execution_id] = entry
        return {"execution_id": execution_id, "content_id": content_id,
                "provider_id": route.provider_id, "model_id": route.model_id, "route_id": route.route_id,
                "operation": "content-deep-analysis", "credential_configured": route.credential_configured(),
                "qualification_status": "QUALIFIED", "data_egress_mode": "SELECTED_EVIDENCE_ONLY",
                "cost": dict(cost), "consent_required": True, "reason_code": "EXPLICIT_CLOUD_SELECTION",
                "expires_at": format_utc_datetime(entry.expires_at)}

    def run(self, *, content_id: str, cloud_consent: bool = False,
            route_id: str | None = None, execution_id: str | None = None,
            acknowledge_unknown_cost: bool = False, egress_mode: str = "SELECTED_EVIDENCE_ONLY") -> DeepAnalysisResultView:
        status = self.status(content_id=content_id)
        route = self._capability.execution_route(route_id)
        if route is None or status.availability is DeepAnalysisAvailability.CONTENT_UNAVAILABLE:
            if route is None and status.availability not in {DeepAnalysisAvailability.NOT_QUALIFIED, DeepAnalysisAvailability.UNAVAILABLE, DeepAnalysisAvailability.CONTENT_UNAVAILABLE}:
                raise self._reject(DeepAnalysisReasonCode.NO_QUALIFIED_MODEL)
            raise DeepAnalysisRejected(status)
        if execution_id is not None and (route_id is None or route.is_local):
            raise self._reject(DeepAnalysisReasonCode.PREFLIGHT_CHANGED)
        if egress_mode != "SELECTED_EVIDENCE_ONLY":
            raise self._reject(DeepAnalysisReasonCode.PREFLIGHT_CHANGED)
        if route.is_local:
            runtime, prepared, refs = self._prepare(content_id, route)
            response = route.dispatch(prepared_dispatch=prepared)
            return self._persist_response(route, runtime, prepared, refs, response)
        # A bare boolean never authorizes cloud traffic. Preflight binds all data.
        if cloud_consent is not True or execution_id is None:
            raise self._reject(DeepAnalysisReasonCode.CLOUD_CONSENT_REQUIRED)
        if acknowledge_unknown_cost is not True:
            raise self._reject(DeepAnalysisReasonCode.COST_ACKNOWLEDGEMENT_REQUIRED)
        with self._preflight_lock:
            entry = self._preflights.get(execution_id)
        try:
            unchanged = (entry is not None and entry.content_id == content_id and entry.route == route
                         and entry.expires_at > self._clock()
                         and entry.context_identity == self._context_identity(content_id, route))
        except Exception:
            unchanged = False
        if not unchanged or entry is None:
            raise self._reject(DeepAnalysisReasonCode.PREFLIGHT_CHANGED)
        request = ProviderCallRequest(operation="content-deep-analysis-cloud", normalized_input_hash=qualification_digest({"execution_id": execution_id}),
            provider=route.provider_id, model=route.model_id, prompt_version=PHASE_1B_PROMPT_IDENTITY,
            schema_version=PHASE_1B_MODEL_SCHEMA, deterministic_artifact_key=f"deep-analysis-cloud/{execution_id}")
        owner = uuid4().hex
        now = self._clock()
        reservation = self._repository.reserve_provider_call(request, owner=owner,
            lease_until=now+timedelta(minutes=5), available_at=now, now=now, fail_closed_on_ambiguous_dispatch=True)
        if not reservation.acquired:
            dispatch = self._repository.get_provider_dispatch(request.request_hash)
            code = DeepAnalysisReasonCode.EXECUTION_ALREADY_DISPATCHED if dispatch and dispatch.status is ProviderDispatchStatus.SUCCESS_DURABLY_RECORDED else DeepAnalysisReasonCode.DISPATCH_AMBIGUOUS
            raise self._reject(code)
        self._repository.record_provider_dispatch_intent(request.request_hash, owner=owner, now=now)
        try:
            response = route.dispatch(prepared_dispatch=entry.prepared)
            self._repository.record_provider_dispatch_result_unknown(request.request_hash, owner=owner, now=self._clock())
            usage = response.usage_evidence
            self._repository.record_deep_analysis_usage(request.request_hash, owner=owner,
                input_tokens=usage.provider_reported_input_tokens if usage else None,
                output_tokens=usage.provider_reported_output_tokens if usage else None, now=self._clock())
            result = self._persist_response(route, entry.runtime, entry.prepared, entry.selected_refs, response)
            self._repository.complete_deep_analysis_dispatch(request.request_hash, owner=owner, result_identity=result.result_identity, authorization_identity=entry.prepared.envelope.payload_consent.authorization_record_identity, now=self._clock())
            return result
        except Exception:
            # Even local parsing/persistence failures cannot trigger a paid retry.
            try:
                self._repository.mark_provider_dispatch_ambiguous(request.request_hash, owner=owner, now=self._clock())
            except Exception:
                pass  # Durable intent is already fail-closed across restart.
            raise self._reject(DeepAnalysisReasonCode.DISPATCH_AMBIGUOUS) from None

    def _persist_response(self, route: DeepAnalysisRoute, runtime: DeepAnalysisRuntime,
                          prepared: PreparedDeepAnalysisDispatch, selected_refs: tuple[str, ...],
                          response: UntrustedDeepAnalysisResponseV1) -> DeepAnalysisResultView:
        phase1b = route.model_output_schema_identity == PHASE_1B_MODEL_SCHEMA
        admitted_response = response if phase1b else _map_phase_1a_response(
            response, evidence_refs=selected_refs
        )
        if admitted_response is None:
            # The model response failed five-role admission. Fail closed before
            # the runtime sees it: a historical KnowledgeContent payload is
            # schema-valid for the frozen carrier and must never be admitted.
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.FAILED,
                    reason_code=DeepAnalysisReasonCode.VALIDATION_FAILED,
                    reason=(
                        "The model response did not satisfy the five-role "
                        "Deep Analysis contract and was rejected. Nothing was "
                        "persisted."
                    ),
                )
            )
        validation = runtime.validation_finalizer().finalize(
            prepared_dispatch=prepared,
            response=admitted_response,
        )
        if validation.success is None:
            failure = validation.failure
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.FAILED,
                    reason_code=DeepAnalysisReasonCode.VALIDATION_FAILED,
                    reason=(
                        "Deep Analysis did not produce a trusted result. "
                        f"{failure.stage.value if failure else 'VALIDATION_FAILED'}"
                    ),
                )
            )
        persisted = self._store.persist_trusted_deep_analysis_success(
            success=validation.success,
            now=self._clock(),
            # Deep Analysis must never replace Summary / Video Notes authority.
            promote_current_summary=False,
        )
        return project_deep_analysis_result(persisted)

    # -- helpers -----------------------------------------------------------

    def _select_evidence(self, content_id: str) -> list[dict[str, str]]:
        """Select bounded, verified transcript spans for one Content.

        Only Evidence whose text re-verifies against the authoritative timed
        transcript is eligible.  Metadata is never included, so it can never
        become citation authority.
        """

        selected: list[dict[str, str]] = []
        for evidence_id in self._evidence_reader(content_id):
            verified = self._evidence_text_reader(evidence_id)
            if verified is None:
                continue
            excerpt = str(getattr(verified, "excerpt", "")).strip()
            if not excerpt:
                continue
            excerpt_hash = str(getattr(verified, "excerpt_hash", ""))
            if len(excerpt_hash) != 64:
                continue
            selected.append(
                {
                    "evidence_id": evidence_id,
                    "excerpt": excerpt[:_MAX_EXCERPT_CHARS],
                    "excerpt_hash": excerpt_hash,
                }
            )
            if len(selected) >= _MAX_SELECTED_EVIDENCE:
                break
        return selected

    def _output_language(self) -> str:
        settings = self._repository.get_global_user_settings()
        language = settings.output_language if settings is not None else "zh-CN"
        return language if language in {"zh-CN", "en"} else "zh-CN"

    def _source_language(self, content_id: str) -> str:
        # The repository reader is keyword-only; calling it positionally would
        # raise TypeError on the real production path.
        transcript = self._transcript_reader(video_id=content_id)
        language = getattr(transcript, "language", None) if transcript else None
        return language if isinstance(language, str) and language.strip() else "und"

    def canonical_snapshot(self, *, content_id: str) -> str | None:
        """Deterministic JSON snapshot of the verified result, or ``None``."""

        view = self.read(content_id=content_id)
        if view is None:
            return None
        payload = {
            "result_identity": view.result_identity,
            "content_identity": view.content_identity,
            "output_language": view.output_language,
            "evidence_citation_status": view.evidence_citation_status,
            "roles": [
                {
                    "role": claim.role,
                    "text": claim.text,
                    "point_kind": claim.point_kind,
                    "confidence": claim.confidence,
                    **({"evidence_ids": list(claim.evidence_ids), "language_validation": claim.language_validation}
                       if view.evidence_citation_status == "DURABLE_EVIDENCE_VERIFIED" else {}),
                }
                for claim in view.roles
            ],
        }
        return json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    def capability_matches(self, expected: Mapping[str, object]) -> bool:
        """Test/dev helper: does the registered capability match expectations?"""

        routes = self._capability.routes
        if not routes:
            return False
        route = routes[0]
        return all(
            route_field == expected_field
            for route_field, expected_field in (
                (route.route_id, expected.get("route_id")),
                (route.model_id, expected.get("model_id")),
                (route.provider_id, expected.get("provider_id")),
            )
            if expected_field is not None
        )
