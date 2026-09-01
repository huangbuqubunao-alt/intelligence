"""Frozen synthetic inputs for the future OpenAI live-qualification package.

It is the single tracked source of the two permitted qualification cases. Its
v4-backed executor resolves an injected credential only after durable dispatch
intent; callers control whether a real or fake adapter is supplied.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable, Final, Literal, Protocol, cast

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisFailureCode,
    DeepAnalysisPayloadScope,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
    TrustedDeepAnalysisSuccess,
    UntrustedDeepAnalysisResponseV1,
    dacs1_sha256,
)
from youtube_intel.deep_analysis_runtime import (
    DeepAnalysisRuntime,
    PreparedDeepAnalysisDispatch,
)
from youtube_intel.domain import (
    ErrorCode,
    EvidenceRegistry,
    EvidenceSource,
    KnowledgeEvidence,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.openai_deep_analysis import (
    OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE,
    OpenAIDeepAnalysisProviderError,
    build_openai_reference_context_budget,
    build_openai_reference_execution_profile,
    build_openai_reference_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderDispatchStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)


@dataclass(frozen=True, slots=True)
class OpenAIQualificationManifest:
    """One non-secret, selected-evidence-only qualification input."""

    manifest_id: str
    semantic_purpose: str
    video_id: str
    video_title: str
    channel_name: str
    published_at: str
    duration_seconds: int
    output_language: str
    scoring_request_hash: str
    evidence_id: str
    evidence_source: str
    evidence_excerpt: str
    evidence_content_hash: str
    expected_schema_contract: str
    expected_validation_policy: str
    expected_provider: str
    expected_model: str
    expected_profile: str
    expected_structured_output_mode: str
    timeout_seconds: int
    sdk_retries: int
    semantic_retries: int
    fallback_allowed: bool
    substitution_allowed: bool
    is_synthetic: bool = True

    @property
    def identity(self) -> str:
        return dacs1_sha256(
            {
                "schema_version": "openai-live-qualification-manifest-v1",
                "manifest_id": self.manifest_id,
                "semantic_purpose": self.semantic_purpose,
                "video_id": self.video_id,
                "video_title": self.video_title,
                "channel_name": self.channel_name,
                "published_at": self.published_at,
                "duration_seconds": self.duration_seconds,
                "output_language": self.output_language,
                "scoring_request_hash": self.scoring_request_hash,
                "evidence_id": self.evidence_id,
                "evidence_source": self.evidence_source,
                "evidence_excerpt": self.evidence_excerpt,
                "evidence_content_hash": self.evidence_content_hash,
                "expected_schema_contract": self.expected_schema_contract,
                "expected_validation_policy": self.expected_validation_policy,
                "expected_provider": self.expected_provider,
                "expected_model": self.expected_model,
                "expected_profile": self.expected_profile,
                "expected_structured_output_mode": self.expected_structured_output_mode,
                "timeout_seconds": self.timeout_seconds,
                "sdk_retries": self.sdk_retries,
                "semantic_retries": self.semantic_retries,
                "fallback_allowed": self.fallback_allowed,
                "substitution_allowed": self.substitution_allowed,
                "is_synthetic": self.is_synthetic,
            }
        )


def _manifest(
    *,
    manifest_id: str,
    semantic_purpose: str,
    video_id: str,
    video_title: str,
    scoring_request_hash: str,
    evidence_id: str,
    evidence_excerpt: str,
    evidence_content_hash: str,
) -> OpenAIQualificationManifest:
    return OpenAIQualificationManifest(
        manifest_id=manifest_id,
        semantic_purpose=semantic_purpose,
        video_id=video_id,
        video_title=video_title,
        channel_name="Synthetic Qualification Channel",
        published_at="2026-01-01T00:00:00Z",
        duration_seconds=42,
        output_language="en",
        scoring_request_hash=scoring_request_hash,
        evidence_id=evidence_id,
        evidence_source="description",
        evidence_excerpt=evidence_excerpt,
        evidence_content_hash=evidence_content_hash,
        expected_schema_contract="knowledge-content-pydantic-v1",
        expected_validation_policy="strict-json-v1/knowledge-schema-v1/evidence-registry-grounding-v1/knowledge-graph-v2/scoring-language-v1/deep-analysis-provenance-v1",
        expected_provider="openai",
        expected_model="gpt-5.4-mini-2026-03-17",
        expected_profile="openai-deep-analysis-reference-capabilities-v1",
        expected_structured_output_mode="PROVIDER_JSON_SCHEMA",
        timeout_seconds=30,
        sdk_retries=0,
        semantic_retries=0,
        fallback_allowed=False,
        substitution_allowed=False,
    )

FROZEN_OPENAI_QUALIFICATION_MANIFESTS: Final[tuple[OpenAIQualificationManifest, ...]] = (
    _manifest(
        manifest_id="openai-live-qualification-1",
        semantic_purpose="synthetic selected-evidence grounding and strict-schema qualification",
        video_id="qualification-video-1",
        video_title="Synthetic evidence workflow",
        scoring_request_hash="1" * 64,
        evidence_id="qualification-1-evidence-1",
        evidence_excerpt="A synthetic workflow records evidence before drafting a conclusion.",
        evidence_content_hash="2" * 64,
    ),
    _manifest(
        manifest_id="openai-live-qualification-2",
        semantic_purpose="synthetic independent evidence timeline and strict-schema qualification",
        video_id="qualification-video-2",
        video_title="Synthetic incident handoff",
        scoring_request_hash="3" * 64,
        evidence_id="qualification-2-evidence-1",
        evidence_excerpt="A synthetic incident handoff records a sequenced evidence-linked timeline.",
        evidence_content_hash="4" * 64,
    ),
)


def require_frozen_openai_qualification_manifest(
    manifest: object,
) -> OpenAIQualificationManifest:
    """Accept only one unchanged member of the fixed two-case package."""

    if type(manifest) is not OpenAIQualificationManifest:
        raise ValueError("OpenAI qualification manifest is not an exact frozen manifest")
    for frozen in FROZEN_OPENAI_QUALIFICATION_MANIFESTS:
        if manifest.manifest_id == frozen.manifest_id and manifest.identity == frozen.identity:
            return frozen
    raise ValueError("OpenAI qualification manifest is not an exact frozen manifest")


class _OpenAIQualificationAdapter(Protocol):
    def dispatch(
        self, *, prepared_dispatch: object, credential: str
    ) -> UntrustedDeepAnalysisResponseV1: ...


class OpenAIQualificationDispatchError(RuntimeError):
    """A redacted terminal result for the fixed qualification package."""


@dataclass(frozen=True, slots=True)
class OpenAIQualificationResult:
    manifest_id: str
    request_hash: str
    success: TrustedDeepAnalysisSuccess | None


def _prepared_dispatch(
    manifest: OpenAIQualificationManifest,
) -> tuple[DeepAnalysisRuntime, PreparedDeepAnalysisDispatch]:
    """Build the exact provider-neutral dispatch for one frozen synthetic case."""

    read = VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=ScoreResult(
                schema_version="score-result-v2",
                score=8.0,
                reason="This result contains a concrete useful explanation of the score.",
                topics=("qualification",),
                should_summarize=True,
                provider="synthetic-qualification",
                model="synthetic-qualification",
                prompt_version="openai-live-qualification-manifest-v1",
                request_hash=manifest.scoring_request_hash,
                output_language=cast(Literal["zh-CN", "en"], manifest.output_language),
            ),
            decision=ScoringDecision(
                threshold=7.0, final_should_summarize=True, model_disagrees=False
            ),
            call=ProviderCallMetadata(
                provider="synthetic-qualification",
                model="synthetic-qualification",
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                finished_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ),
        video_id=manifest.video_id,
        scoring_job_id=f"qualification-{manifest.manifest_id}",
        scoring_success_provenance="PRIMARY",
    )
    canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=read,
        schema_version="canonical-deep-analysis-input-v1",
        operation="deep-analysis",
        input_schema_version="input-v1",
        video_identity=manifest.video_id,
        transcript_identity=f"synthetic-{manifest.manifest_id}",
        transcript_language="en",
        transcript_normalization_version="synthetic-v1",
        evidence_registry_identity=f"qualification-{manifest.manifest_id}-registry-v1",
        selected_evidence=(
            {
                "schema_version": "selected-evidence-projection-v1",
                "evidence_id": manifest.evidence_id,
                "source": manifest.evidence_source,
                "excerpt": manifest.evidence_excerpt,
            },
        ),
        selection_policy_identity="openai-live-qualification-selection-v1",
        coverage_policy_identity="openai-live-qualification-coverage-v1",
        coverage_complete=False,
        output_language=manifest.output_language,
        knowledge_content_schema_version=manifest.expected_schema_contract,
        prompt_version="openai-live-qualification-manifest-v1",
        operation_version="openai-live-qualification-v1",
    )
    runtime = DeepAnalysisRuntime()
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=read, canonical_input=canonical
    )
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.CLOUD_EXPLICIT,
        authorization_record_identity=manifest.identity,
        named_provider_id=manifest.expected_provider,
        provider_kind=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.provider_kind,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint=manifest.expected_model,
    )
    registry = EvidenceRegistry(
        items=(
            KnowledgeEvidence(
                evidence_id=manifest.evidence_id,
                source=EvidenceSource(manifest.evidence_source),
                excerpt=manifest.evidence_excerpt,
                source_content_hash=manifest.evidence_content_hash,
            ),
        )
    )
    payload = runtime.authorize_payload(
        authoritative_input=admitted,
        evidence_registry=registry,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=consent,
        video_title=manifest.video_title,
        channel_name=manifest.channel_name,
        published_at=manifest.published_at,
        duration_seconds=manifest.duration_seconds,
        source_language="en",
        public_description=manifest.evidence_excerpt,
    )
    request = build_openai_reference_request_projection(
        canonical_input=canonical,
        authorized_payload=payload.payload,
        payload_consent=consent,
    )
    execution = build_openai_reference_execution_profile(
        request_projection=request,
        credential_execution_profile=CredentialExecutionProfileIdentityV1(
            schema_version="credential-execution-profile-v1",
            provider_id=manifest.expected_provider,
            execution_profile_identity=manifest.identity,
        ),
    )
    return runtime, runtime.prepare_dispatch(
        authoritative_input=admitted,
        authorized_payload=payload,
        request_projection=request,
        execution_profile=execution,
        payload_consent=consent,
        context_budget_profile=build_openai_reference_context_budget(input_budget=1024),
        timeout_profile_identity=OPENAI_DEEP_ANALYSIS_REFERENCE_PROFILE.timeout_profile_identity,
        fallback_policy_identity=manifest.identity,
    )


def openai_qualification_request_for_manifest(
    manifest: object,
) -> ProviderCallRequest:
    """Return the v4 request identity for one unchanged frozen manifest."""

    frozen = require_frozen_openai_qualification_manifest(manifest)
    return ProviderCallRequest(
        operation="openai-live-qualification-v1",
        normalized_input_hash=frozen.identity,
        provider=frozen.expected_provider,
        model=frozen.expected_model,
        prompt_version="openai-live-qualification-manifest-v1",
        schema_version=frozen.expected_schema_contract,
        deterministic_artifact_key=f"qualification/{frozen.manifest_id}/trusted-receipt",
    )


class OpenAIQualificationExecutor:
    """Run only the fixed two-case package through v4 fail-closed dispatch.

    The injected resolver is intentionally invoked only after a durable intent
    record. It is never called when recovery finds an uncertain prior request.
    """

    def __init__(
        self,
        *,
        repository: SQLiteStateRepository,
        adapter: _OpenAIQualificationAdapter,
        credential_resolver: Callable[[], str],
    ) -> None:
        self._repository = repository
        self._adapter = adapter
        self._credential_resolver = credential_resolver

    def execute_package(
        self, *, owner: str, now: datetime
    ) -> tuple[OpenAIQualificationResult, ...]:
        """Execute the two frozen cases in order without retry or substitution."""

        results: list[OpenAIQualificationResult] = []
        for position, manifest in enumerate(FROZEN_OPENAI_QUALIFICATION_MANIFESTS):
            self._require_prior_success(position)
            request = openai_qualification_request_for_manifest(manifest)
            existing = self._repository.get_provider_call(request.request_hash)
            if existing is not None and existing.status is ProviderCallStatus.SUCCEEDED:
                continue
            results.append(self._execute_one(manifest=manifest, request=request, owner=owner, now=now))
        return tuple(results)

    def _require_prior_success(self, position: int) -> None:
        for prior in FROZEN_OPENAI_QUALIFICATION_MANIFESTS[:position]:
            prior_call = self._repository.get_provider_call(
                openai_qualification_request_for_manifest(prior).request_hash
            )
            if prior_call is None or prior_call.status is not ProviderCallStatus.SUCCEEDED:
                raise OpenAIQualificationDispatchError(
                    "OpenAI qualification package cannot substitute a later manifest"
                )

    def _execute_one(
        self,
        *,
        manifest: OpenAIQualificationManifest,
        request: ProviderCallRequest,
        owner: str,
        now: datetime,
    ) -> OpenAIQualificationResult:
        require_frozen_openai_qualification_manifest(manifest)
        dispatch = self._repository.recover_provider_dispatch(request.request_hash, now=now)
        if dispatch is not None and dispatch.status in {
            ProviderDispatchStatus.AMBIGUOUS,
            ProviderDispatchStatus.DISPATCH_INTENT_DURABLE,
            ProviderDispatchStatus.DISPATCHED_RESULT_UNKNOWN,
        }:
            raise OpenAIQualificationDispatchError(
                "OpenAI qualification dispatch outcome is ambiguous; operator resolution required"
            )
        existing = self._repository.get_provider_call(request.request_hash)
        if existing is not None and existing.status in {
            ProviderCallStatus.FAILED_FINAL,
            ProviderCallStatus.FAILED_RETRYABLE,
        }:
            raise OpenAIQualificationDispatchError("OpenAI qualification manifest is terminal")
        reservation = self._repository.reserve_provider_call(
            request,
            owner=owner,
            lease_until=now + timedelta(seconds=300),
            available_at=now,
            now=now,
            fail_closed_on_ambiguous_dispatch=True,
        )
        if not reservation.acquired:
            raise OpenAIQualificationDispatchError("OpenAI qualification manifest is already reserved")
        self._repository.record_provider_dispatch_intent(
            request.request_hash, owner=owner, now=now
        )
        credential = self._credential_resolver()
        if not credential:
            self._record_known_failure(request=request, owner=owner, now=now)
            raise OpenAIQualificationDispatchError("OpenAI qualification credential is unavailable")
        try:
            runtime, prepared = _prepared_dispatch(manifest)
            response = self._adapter.dispatch(prepared_dispatch=prepared, credential=credential)
            self._repository.record_provider_dispatch_result_unknown(
                request.request_hash, owner=owner, now=now
            )
            validation = runtime.validation_finalizer().finalize(
                prepared_dispatch=prepared, response=response
            )
            if validation.success is None:
                self._repository.mark_provider_dispatch_ambiguous(
                    request.request_hash, owner=owner, now=now
                )
                raise OpenAIQualificationDispatchError(
                    "OpenAI qualification response did not produce trusted success"
                )
            artifact = ArtifactWrite(
                artifact_id=f"qualification-{manifest.identity[:32]}",
                artifact_key=request.deterministic_artifact_key,
                video_id=None,
                job_id=None,
                kind=ArtifactKind.ANALYSIS_STRUCTURED,
                storage_root=StorageRoot.DATA,
                relative_path=f"qualification/{manifest.manifest_id}/trusted-receipt.json",
                content_hash=hashlib.sha256(
                    validation.success.provenance_identity.encode("utf-8")
                ).hexdigest(),
                provider=manifest.expected_provider,
                model=manifest.expected_model,
                producer_version="openai-live-qualification-receipt-v1",
                retention_class=RetentionClass.LONG_LIVED,
                expires_at=None,
            )
            self._repository.upsert_artifact(artifact, now=now)
            self._repository.complete_provider_call(
                request.request_hash,
                owner=owner,
                response_artifact_id=artifact.artifact_id,
                input_tokens=response.usage_evidence.provider_reported_input_tokens
                if response.usage_evidence is not None
                else None,
                output_tokens=response.usage_evidence.provider_reported_output_tokens
                if response.usage_evidence is not None
                else None,
                cost_microusd=None,
                now=now,
            )
        except OpenAIQualificationDispatchError:
            raise
        except OpenAIDeepAnalysisProviderError as error:
            if error.failure.code in {
                DeepAnalysisFailureCode.AUTH_INVALID,
                DeepAnalysisFailureCode.QUOTA_EXCEEDED,
                DeepAnalysisFailureCode.RATE_LIMITED,
                DeepAnalysisFailureCode.MODEL_UNAVAILABLE,
            }:
                self._record_known_failure(request=request, owner=owner, now=now)
                raise OpenAIQualificationDispatchError(
                    "OpenAI qualification provider refusal is terminal"
                ) from None
            self._repository.mark_provider_dispatch_ambiguous(
                request.request_hash, owner=owner, now=now
            )
            raise OpenAIQualificationDispatchError(
                "OpenAI qualification provider outcome is ambiguous"
            ) from None
        except Exception:
            self._repository.mark_provider_dispatch_ambiguous(
                request.request_hash, owner=owner, now=now
            )
            raise
        finally:
            credential = ""
        return OpenAIQualificationResult(
            manifest_id=manifest.manifest_id,
            request_hash=request.request_hash,
            success=validation.success,
        )

    def _record_known_failure(
        self, *, request: ProviderCallRequest, owner: str, now: datetime
    ) -> None:
        self._repository.record_provider_dispatch_known_failure(
            request.request_hash, owner=owner, now=now
        )
        self._repository.fail_provider_call(
            request.request_hash,
            owner=owner,
            retryable=False,
            available_at=now,
            error_code=ErrorCode.PERMISSION_DENIED,
            error_message="OpenAI qualification provider refusal",
            now=now,
        )


__all__ = [
    "FROZEN_OPENAI_QUALIFICATION_MANIFESTS",
    "OpenAIQualificationDispatchError",
    "OpenAIQualificationExecutor",
    "OpenAIQualificationManifest",
    "OpenAIQualificationResult",
    "openai_qualification_request_for_manifest",
    "require_frozen_openai_qualification_manifest",
]
