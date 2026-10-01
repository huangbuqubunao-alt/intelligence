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

Phase 1A boundary: this module does not add ``deep_analysis_evidence`` and does
not converge transient refs into durable Evidence identity.  Because of that,
user-facing evidence citations are withheld here; see
:func:`project_deep_analysis_result`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

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
from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceError,
    DeepAnalysisPersistenceStore,
    VerifiedPersistedDeepAnalysisRead,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.deep_analysis_runtime import DeepAnalysisRuntime
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
    build_ollama_local_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

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


class DeepAnalysisAvailability(str, Enum):
    """Truthful availability states for the Deep Analysis action."""

    AVAILABLE = "AVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    SCORING_UNAVAILABLE = "SCORING_UNAVAILABLE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    CLOUD_CONSENT_REQUIRED = "CLOUD_CONSENT_REQUIRED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class DeepAnalysisRoute:
    """One narrow, explicitly qualified Deep Analysis execution route.

    This is deliberately **not** a generic router.  A route is a concrete
    (provider, model) pairing that has already passed qualification and is
    pinned by ADR-027 identities.  There is no policy-driven escalation, no
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
        build_request_projection=build_ollama_local_request_projection,
        build_execution_profile=build_ollama_local_execution_profile,
        build_context_budget=build_ollama_local_context_budget,
        input_budget=8192,
    )


class DeepAnalysisCapability:
    """Narrow Deep Analysis qualification authority.

    Routes become available only when an explicit qualification record is
    registered.  There is no generic router and no automatic model search: an
    empty registry is the correct default and produces a truthful
    ``NOT_QUALIFIED`` state.
    """

    def __init__(self, routes: tuple[DeepAnalysisRoute, ...] = ()) -> None:
        identifiers = [route.route_id for route in routes]
        if len(identifiers) != len(set(identifiers)):
            msg = "Deep Analysis route identities must be unique"
            raise ValueError(msg)
        self._routes = routes

    @property
    def routes(self) -> tuple[DeepAnalysisRoute, ...]:
        return self._routes

    def local_route(self) -> DeepAnalysisRoute | None:
        for route in self._routes:
            if route.is_local:
                return route
        return None

    def describe(self) -> list[dict[str, object]]:
        return [route.describe() for route in self._routes]


@dataclass(frozen=True, slots=True)
class DeepAnalysisStatus:
    """One truthful, user-facing Deep Analysis state for a Content."""

    availability: DeepAnalysisAvailability
    reason: str | None = None
    route_id: str | None = None
    model_id: str | None = None
    provider_id: str | None = None
    qualified: bool = False
    consent_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "availability": self.availability.value,
            "reason": self.reason,
            "route_id": self.route_id,
            "model_id": self.model_id,
            "provider_id": self.provider_id,
            "qualified": self.qualified,
            "consent_required": self.consent_required,
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
                }
                for claim in self.roles
            ],
        }


def _confidence_label(point: KnowledgeEvidence | Any) -> str:
    """Map a bounded internal confidence value to honest language.

    Never invents a percentage.  Anything unrecognized stays unknown.
    """

    raw = getattr(point, "confidence", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "INSUFFICIENT_EVIDENCE"


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

    def add(text: str, role: str, point: Any) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        kind = getattr(point, "kind", None)
        kind_value = getattr(kind, "value", None)
        point_kind = kind_value if isinstance(kind_value, str) else ""
        claims.append(
            DeepAnalysisClaim(
                text=cleaned,
                role=role,
                point_kind=str(point_kind),
                confidence=_confidence_label(point),
            )
        )

    add(content.one_sentence_summary, "CORE_CONCLUSION", content.why_it_matters)
    for point in content.core_points:
        add(point.text, "CORE_CONCLUSION", point)
    for point in (*content.key_facts, *content.key_arguments):
        add(point.text, "KEY_EVIDENCE", point)
    for point in (*content.counterpoints, *content.risks):
        add(point.text, "UNCERTAINTY", point)
    add(content.why_it_matters.text, "RELEVANCE_TO_USER", content.why_it_matters)
    for point in (
        *content.actionable_directions,
        *content.action_recommendations,
    ):
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
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        evidence_citation_status="PENDING_DURABLE_EVIDENCE_CONVERGENCE",
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
        self._runtime = DeepAnalysisRuntime()

    # -- status ------------------------------------------------------------

    def capability_report(self) -> dict[str, object]:
        routes = self._capability.describe()
        return {
            "qualified": bool(routes),
            "routes": routes,
            "reason": (
                None
                if routes
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
                reason="Content does not exist.",
            )
        route = self._capability.local_route()
        if route is None:
            return DeepAnalysisStatus(
                availability=DeepAnalysisAvailability.NOT_QUALIFIED,
                reason=(
                    "No Deep Analysis model is currently qualified. "
                    "Deep Analysis is unavailable; Summary and Evidence remain usable."
                ),
            )
        existing = self._read(content_id)
        if existing is not None:
            return DeepAnalysisStatus(
                availability=DeepAnalysisAvailability.AVAILABLE,
                route_id=route.route_id,
                model_id=route.model_id,
                provider_id=route.provider_id,
                qualified=True,
            )
        return DeepAnalysisStatus(
            availability=DeepAnalysisAvailability.NOT_REQUESTED,
            route_id=route.route_id,
            model_id=route.model_id,
            provider_id=route.provider_id,
            qualified=True,
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

    def run(
        self, *, content_id: str, cloud_consent: bool = False
    ) -> DeepAnalysisResultView:
        """Run Deep Analysis for one Content after an explicit user request.

        The call fails closed with a truthful status rather than dispatching
        through an unqualified route, omitting a required consent, or degrading
        Evidence authority.
        """

        status = self.status(content_id=content_id)
        if status.availability in {
            DeepAnalysisAvailability.CONTENT_UNAVAILABLE,
            DeepAnalysisAvailability.NOT_QUALIFIED,
        }:
            raise DeepAnalysisRejected(status)
        route = self._capability.local_route()
        if route is None:
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.NOT_QUALIFIED,
                    reason="No qualified Deep Analysis route is available.",
                )
            )
        if not route.is_local and not cloud_consent:
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.CLOUD_CONSENT_REQUIRED,
                    reason=(
                        "This route would send bounded data to a cloud provider "
                        "and requires explicit per-run consent."
                    ),
                    route_id=route.route_id,
                    model_id=route.model_id,
                    provider_id=route.provider_id,
                    consent_required=True,
                )
            )

        try:
            read = self._scoring_reader(content_id)
        except Exception:
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.SCORING_UNAVAILABLE,
                    reason=(
                        "Deep Analysis requires a verified scoring read for this "
                        "Content. It is unavailable right now."
                    ),
                )
            ) from None

        selection = self._select_evidence(content_id)
        if not selection:
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.EVIDENCE_UNAVAILABLE,
                    reason=(
                        "This Content has no trusted timed transcript Evidence, "
                        "so Deep Analysis cannot cite anything durably. No "
                        "timestamp is invented and no result is produced."
                    ),
                )
            )

        output_language = self._output_language()
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
        canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
            verified_scoring_read=read,
            schema_version="canonical-deep-analysis-input-v1",
            operation="content-deep-analysis",
            input_schema_version=_INPUT_SCHEMA_VERSION,
            video_identity=content_id,
            transcript_identity=registry_identity,
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
            knowledge_content_schema_version="knowledge-content-pydantic-v1",
            prompt_version=_DEEP_ANALYSIS_PROMPT_IDENTITY,
            operation_version=_OPERATION_VERSION,
        )

        admitted = self._runtime.admit_verified_scoring_read(
            verified_scoring_read=read, canonical_input=canonical
        )
        consent = PayloadConsentIdentityV1(
            schema_version="payload-consent-identity-v1",
            consent_mode=(
                PayloadConsentMode.LOCAL_ONLY
                if route.is_local
                else PayloadConsentMode.PER_RUN_CLOUD_APPROVAL
            ),
            authorization_record_identity=f"v1x-deep-analysis-{content_id}-"
            f"{canonical.a1_identity[:16]}",
            named_provider_id=route.provider_id,
            provider_kind=route.provider_kind,
            payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
            allowed_model_constraint=route.model_id,
        )
        content = self._repository.get_video(content_id)
        payload = self._runtime.authorize_payload(
            authoritative_input=admitted,
            evidence_registry=registry,
            payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
            payload_consent=consent,
            video_title=(content.title if content and content.title else ""),
            channel_name=(
                content.channel_name if content and content.channel_name else ""
            ),
            published_at=(
                content.published_at.isoformat()
                if content is not None and content.published_at is not None
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
        prepared = self._runtime.prepare_dispatch(
            authoritative_input=admitted,
            authorized_payload=payload,
            request_projection=request,
            execution_profile=execution,
            payload_consent=consent,
            context_budget_profile=route.build_context_budget(
                input_budget=route.input_budget
            ),
            timeout_profile_identity=f"{route.route_id}-timeout-v1",
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
        response = route.dispatch(prepared_dispatch=prepared)
        validation = self._runtime.validation_finalizer().finalize(
            prepared_dispatch=prepared, response=response
        )
        if validation.success is None:
            failure = validation.failure
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.FAILED,
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
        transcript = self._transcript_reader(content_id)
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
