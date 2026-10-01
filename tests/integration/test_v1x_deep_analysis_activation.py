"""V1.x Phase 1A: Content-level Deep Analysis activation.

These tests pin the activated production path and its honesty guarantees:

- Deep Analysis is a real, reachable Content-level action.
- It never replaces or rewrites Summary / Video Notes authority.
- No route is qualified by default, and the unavailable state is truthful.
- Canonical-only Content (no verified timed transcript) fails closed.
- No transient candidate ref is ever presented as a user-facing citation.
- ``RELATION_TO_KNOWLEDGE`` / ``KNOWLEDGE_DELTA`` are never projected.
- A persisted result survives restart and stays byte-identical.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    CredentialExecutionProfileIdentityV1,
    DeepAnalysisPayloadScope,
    DeepAnalysisProviderKind,
    PayloadConsentIdentityV1,
    PayloadConsentMode,
)
from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.deep_analysis_service import (
    DEEP_ANALYSIS_ROLES,
    DEFERRED_DEEP_ANALYSIS_ROLES,
    DeepAnalysisAvailability,
    DeepAnalysisCapability,
    DeepAnalysisRejected,
    DeepAnalysisService,
    build_local_ollama_route,
)
from youtube_intel.domain import (
    EvidenceRegistry,
    EvidenceSource,
    KnowledgeEvidence,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.ollama_deep_analysis import (
    OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE,
    OllamaDeepAnalysisProviderAdapter,
    build_ollama_local_context_budget,
    build_ollama_local_execution_profile,
    build_ollama_local_request_projection,
)
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 1, tzinfo=UTC)
VIDEO_ID = "video-da-1"


def _stamp(value: datetime) -> str:
    """Repository timestamp format: a trailing Z, not a doubled offset."""

    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _scoring_read(video_id: str = VIDEO_ID) -> VerifiedScoringRead:
    return VerifiedScoringRead(
        scoring_outcome=ScoringOutcome(
            result=ScoreResult(
                schema_version="score-result-v2",
                score=8.0,
                reason="This fixture provides a concrete useful explanation of the score.",
                topics=("workflow",),
                should_summarize=True,
                provider="scoring-provider",
                model="scoring-model",
                prompt_version="scoring-prompt-v2",
                request_hash="a" * 64,
                output_language="en",
            ),
            decision=ScoringDecision(
                threshold=7.0, final_should_summarize=True, model_disagrees=False
            ),
            call=ProviderCallMetadata(
                provider="scoring-provider",
                model="scoring-model",
                started_at=NOW,
                finished_at=NOW,
            ),
        ),
        video_id=video_id,
        scoring_job_id="job-da-1",
        scoring_success_provenance="PRIMARY",
    )


def _summary_knowledge_content() -> dict[str, object]:
    """A valid KnowledgeContent payload in the fixture output language (en)."""

    def point(text: str, kind: str) -> dict[str, object]:
        return {"text": text, "kind": kind, "evidence_ids": ["e1"]}

    return {
        "one_sentence_summary": "The fixture states one clear conclusion for testing.",
        "summary_evidence_ids": ["e1"],
        "why_it_matters": point(
            "The fixture explains why this matters to the reader.", "inference"
        ),
        "core_points": [point("The fixture asserts one core supporting fact.", "fact")],
        "key_facts": [point("The fixture records one key measured fact.", "fact")],
        "counterpoints": [point("The fixture notes one real counterpoint.", "inference")],
        "knowledge_graph": {"topics": ["workflow"]},
    }


def _knowledge_content() -> dict[str, object]:
    """A Phase-1A five-role model response in the fixture output language (en)."""

    def claim(text: str, point_kind: str) -> dict[str, object]:
        return {"text": text, "point_kind": point_kind}

    return {
        "schema_version": "v1x-content-deep-analysis-model-output-v1",
        "core_conclusion": [
            claim(
                "The fixture shows that this content supports one clear conclusion.",
                "inference",
            )
        ],
        "key_evidence": [
            claim("The available evidence supports this conclusion.", "fact")
        ],
        "uncertainty": [
            claim("This remains unverified and should not be relied on yet.", "inference")
        ],
        "relevance_to_user": [
            claim(
                "This matters because it changes how you should plan the next review.",
                "inference",
            )
        ],
        "next_question": [
            claim(
                "Check whether the second claim is corroborated by another source.",
                "inference",
            )
        ],
    }


def _summary_knowledge_content() -> dict[str, object]:
    """A frozen-contract KnowledgeContent payload in the fixture language (en)."""

    def point(text: str, kind: str) -> dict[str, object]:
        return {"text": text, "kind": kind, "evidence_ids": ["e1"]}

    return {
        "one_sentence_summary": "The fixture states one clear conclusion for testing.",
        "summary_evidence_ids": ["e1"],
        "why_it_matters": point(
            "The fixture explains why this matters to the reader.", "inference"
        ),
        "core_points": [point("The fixture asserts one core supporting fact.", "fact")],
        "key_facts": [point("The fixture records one key measured fact.", "fact")],
        "counterpoints": [point("The fixture notes one real counterpoint.", "inference")],
        "knowledge_graph": {"topics": ["workflow"]},
    }


def _summary_promoting_success(video_id: str):
    """Build a runtime-admitted success through the frozen ADR-027 contract.

    Proves Summary-separation behavior. It deliberately uses the frozen request
    projection, so the result is *not* a Phase-1A transitional result. Built
    locally rather than by importing another test module, because ``tests`` is
    not an importable package.
    """

    from youtube_intel.deep_analysis_runtime import DeepAnalysisRuntime

    runtime = DeepAnalysisRuntime()
    read = _scoring_read(video_id)
    canonical = CanonicalDeepAnalysisInputV1.from_verified_scoring_read(
        verified_scoring_read=read,
        schema_version="canonical-deep-analysis-input-v1",
        operation="deep-analysis",
        input_schema_version="input-v1",
        video_identity=video_id,
        transcript_identity="transcript-summary-fixture",
        transcript_language="en",
        transcript_normalization_version="normalized-v1",
        evidence_registry_identity="registry-summary-fixture-v1",
        selected_evidence=(
            {
                "schema_version": "selected-evidence-projection-v1",
                "evidence_id": "e1",
                "source": EvidenceSource.TRANSCRIPT_SAMPLE.value,
                "excerpt": "A verified transcript excerpt for the fixture.",
            },
        ),
        selection_policy_identity="selection-v1",
        coverage_policy_identity="coverage-v1",
        coverage_complete=False,
        output_language="en",
        knowledge_content_schema_version="knowledge-v1",
        prompt_version="prompt-v1",
        operation_version="operation-v1",
    )
    admitted = runtime.admit_verified_scoring_read(
        verified_scoring_read=read, canonical_input=canonical
    )
    consent = PayloadConsentIdentityV1(
        schema_version="payload-consent-identity-v1",
        consent_mode=PayloadConsentMode.LOCAL_ONLY,
        authorization_record_identity="summary-fixture-consent-v1",
        named_provider_id="ollama-local",
        provider_kind=DeepAnalysisProviderKind.LOCAL,
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        allowed_model_constraint=OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE.model_id,
    )
    payload = runtime.authorize_payload(
        authoritative_input=admitted,
        evidence_registry=EvidenceRegistry(
            items=(
                KnowledgeEvidence(
                    evidence_id="e1",
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    excerpt="A verified transcript excerpt for the fixture.",
                    source_content_hash="d" * 64,
                ),
            )
        ),
        payload_scope=DeepAnalysisPayloadScope.SELECTED_EVIDENCE_ONLY,
        payload_consent=consent,
        video_title="Fixture title",
        channel_name="Fixture channel",
        published_at="2026-10-01T00:00:00Z",
        duration_seconds=60,
        source_language="en",
    )
    request = build_ollama_local_request_projection(
        canonical_input=canonical,
        authorized_payload=payload.payload,
        payload_consent=consent,
    )
    execution = build_ollama_local_execution_profile(
        request_projection=request,
        credential_execution_profile=CredentialExecutionProfileIdentityV1(
            schema_version="credential-execution-profile-v1",
            provider_id="ollama-local",
            execution_profile_identity="b" * 64,
        ),
    )
    prepared = runtime.prepare_dispatch(
        authoritative_input=admitted,
        authorized_payload=payload,
        request_projection=request,
        execution_profile=execution,
        payload_consent=consent,
        context_budget_profile=build_ollama_local_context_budget(input_budget=1024),
        timeout_profile_identity="fixture-timeout-v1",
        fallback_policy_identity="c" * 64,
    )
    response = OllamaDeepAnalysisProviderAdapter(
        transport=_transport(_summary_knowledge_content())
    ).dispatch(prepared_dispatch=prepared)
    validation = runtime.validation_finalizer().finalize(
        prepared_dispatch=prepared, response=response
    )
    assert validation.success is not None
    return validation.success


def _seed_content(repository: SQLiteStateRepository, video_id: str = VIDEO_ID) -> None:
    """Seed one scored Content with an explicit English output language."""

    connection = repository._connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO videos "
            "(video_id, channel_id, channel_name, title, pipeline_status, "
            "pipeline_version, availability, discovered_at, updated_at) "
            "VALUES (?, 'UC_DA', 'Fixture Channel', 'Fixture Title', 'SCORED', "
            "'fixture-v1', 'public', ?, ?)",
            (video_id, _stamp(NOW), _stamp(NOW)),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="en", now=NOW)


def _transport(content: dict[str, object] | None = None):
    """Deterministic local transport; no network, no paid call."""

    body = content if content is not None else _knowledge_content()

    def call(request: dict[str, object], timeout_seconds: float) -> object:
        del request, timeout_seconds
        return {
            "model": "qwen2.5-coder:7b",
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(body, ensure_ascii=False)},
        }

    return call


class _VerifiedEvidence:
    def __init__(self, evidence_id: str, excerpt: str) -> None:
        self.evidence_id = evidence_id
        self.excerpt = excerpt
        self.excerpt_hash = "d" * 64


def _service(
    repository: SQLiteStateRepository,
    *,
    qualified: bool = True,
    evidence_ids: tuple[str, ...] = ("e1",),
) -> DeepAnalysisService:
    capability = DeepAnalysisCapability(
        (build_local_ollama_route(transport=_transport()),) if qualified else ()
    )
    return DeepAnalysisService(
        repository=repository,
        capability=capability,
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: evidence_ids,
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(
            evidence_id, "A verified transcript excerpt for the fixture."
        ),
        now=lambda: NOW,
    )


# ---------------------------------------------------------------------------
# Qualification / availability
# ---------------------------------------------------------------------------


def test_no_qualified_route_reports_truthful_not_qualified(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository, qualified=False)

    status = service.status(content_id=VIDEO_ID)

    assert status.availability is DeepAnalysisAvailability.NOT_QUALIFIED
    assert status.qualified is False
    assert status.reason is not None
    assert "is currently qualified" in status.reason
    assert "Summary and Evidence remain usable" in status.reason
    assert service.capability_report()["qualified"] is False


def test_unqualified_route_refuses_to_run_without_dispatch(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository, qualified=False)

    with pytest.raises(DeepAnalysisRejected) as rejection:
        service.run(content_id=VIDEO_ID)

    assert (
        rejection.value.status.availability
        is DeepAnalysisAvailability.NOT_QUALIFIED
    )
    # Nothing was persisted, so no result can be read back.
    assert service.read(content_id=VIDEO_ID) is None


def test_missing_content_reports_content_unavailable(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    service = _service(repository)

    status = service.status(content_id="does-not-exist")

    assert status.availability is DeepAnalysisAvailability.CONTENT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Real execution path
# ---------------------------------------------------------------------------


def test_qualified_route_runs_and_persists_a_real_result(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository)

    status = service.status(content_id=VIDEO_ID)
    assert status.availability is DeepAnalysisAvailability.NOT_REQUESTED
    assert status.qualified is True

    result = service.run(content_id=VIDEO_ID)

    assert result.content_id == VIDEO_ID
    assert result.roles
    assert result.evidence_citation_status == (
        "PENDING_DURABLE_EVIDENCE_CONVERGENCE"
    )
    # The result is now readable through the same verified read seam.
    read_back = service.read(content_id=VIDEO_ID)
    assert read_back is not None
    assert read_back.result_identity == result.result_identity


def test_projection_uses_only_the_five_first_version_roles(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository)

    result = service.run(content_id=VIDEO_ID)

    presented = {claim.role for claim in result.roles}
    assert presented
    assert presented <= set(DEEP_ANALYSIS_ROLES)
    assert not presented & DEFERRED_DEEP_ANALYSIS_ROLES
    for claim in result.roles:
        assert claim.text.strip()
        assert claim.confidence
    # Each of the five product concepts is represented.
    assert presented == set(DEEP_ANALYSIS_ROLES)


def test_projection_never_exposes_transient_evidence_refs_as_citations(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository)

    payload = service.run(content_id=VIDEO_ID).as_dict()

    serialized = json.dumps(payload, ensure_ascii=False)
    # The model cited "e1"; it must not surface as a user-facing citation.
    assert "evidence_ids" not in serialized
    assert "evidence_refs" not in serialized
    assert '"e1"' not in serialized


# ---------------------------------------------------------------------------
# Summary authority must not be disturbed
# ---------------------------------------------------------------------------


def test_deep_analysis_never_promotes_to_current_summary_authority(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    store = DeepAnalysisPersistenceStore(repository)
    service = _service(repository)

    service.run(content_id=VIDEO_ID)

    # Deep Analysis wrote its own durable record...
    assert (
        store.read_deep_analysis_result_for_content(video_id=VIDEO_ID) is not None
    )
    # ...but Summary / Video Notes authority is untouched.
    assert store.read_current_content_summary_result(video_id=VIDEO_ID) is None
    connection = repository._connect()
    try:
        rows = connection.execute(
            "SELECT COUNT(*) AS count FROM current_content_summaries"
        ).fetchone()
    finally:
        connection.close()
    assert int(rows["count"]) == 0


def test_deep_analysis_read_is_independent_of_the_summary_pointer(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository)

    service.run(content_id=VIDEO_ID)

    # Reading Deep Analysis must not require, or consume, a Summary pointer.
    assert service.read(content_id=VIDEO_ID) is not None
    assert service.read(content_id="other-video") is None


# ---------------------------------------------------------------------------
# Fail-closed behavior
# ---------------------------------------------------------------------------


def test_canonical_only_content_fails_closed_without_timed_evidence(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = _service(repository, evidence_ids=())

    with pytest.raises(DeepAnalysisRejected) as rejection:
        service.run(content_id=VIDEO_ID)

    status = rejection.value.status
    assert status.availability is DeepAnalysisAvailability.EVIDENCE_UNAVAILABLE
    assert "no trusted timed transcript Evidence" in (status.reason or "")
    assert "No timestamp is invented" in (status.reason or "")
    assert service.read(content_id=VIDEO_ID) is None


def test_unverifiable_evidence_text_is_not_offered_to_the_provider(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    service = DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability(
            (build_local_ollama_route(transport=_transport()),)
        ),
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: ("e1",),
        # Legacy or unbound Evidence resolves to None and must not be used.
        evidence_text_reader=lambda _evidence_id: None,
        now=lambda: NOW,
    )

    with pytest.raises(DeepAnalysisRejected) as rejection:
        service.run(content_id=VIDEO_ID)

    assert (
        rejection.value.status.availability
        is DeepAnalysisAvailability.EVIDENCE_UNAVAILABLE
    )


def test_invalid_model_output_fails_instead_of_producing_a_result(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository)
    # The model returns content that is not valid KnowledgeContent.
    service = _service(repository)
    service._capability = DeepAnalysisCapability(  # noqa: SLF001
        (build_local_ollama_route(transport=_transport({"nonsense": True})),)
    )

    with pytest.raises(DeepAnalysisRejected) as rejection:
        service.run(content_id=VIDEO_ID)

    assert rejection.value.status.availability is DeepAnalysisAvailability.FAILED
    assert service.read(content_id=VIDEO_ID) is None


# ---------------------------------------------------------------------------
# Persistence / restart behavior
# ---------------------------------------------------------------------------


def test_persisted_result_survives_restart_and_stays_identical(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed_content(repository)
    before = _service(repository).run(content_id=VIDEO_ID)
    first_snapshot = _service(repository).canonical_snapshot(content_id=VIDEO_ID)

    # Simulate a full process restart: brand-new repository and service.
    restarted_repository = SQLiteStateRepository(database)
    restarted = _service(restarted_repository)
    after = restarted.read(content_id=VIDEO_ID)

    assert after is not None
    assert after.result_identity == before.result_identity
    assert after.content_identity == before.content_identity
    assert after.output_language == before.output_language
    assert [claim.text for claim in after.roles] == [
        claim.text for claim in before.roles
    ]
    assert restarted.canonical_snapshot(content_id=VIDEO_ID) == first_snapshot


def test_tampered_persisted_row_is_not_served_as_a_result(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed_content(repository)
    result = _service(repository).run(content_id=VIDEO_ID)

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE deep_analysis_persisted_results "
            "SET knowledge_content_json = ? WHERE result_identity = ?",
            (json.dumps({"one_sentence_summary": "tampered"}), result.result_identity),
        )
    finally:
        connection.close()

    # A tampered artifact is never projected.
    assert _service(repository).read(content_id=VIDEO_ID) is None


def test_default_persistence_behavior_still_promotes_current_summary(
    tmp_path: Path,
) -> None:
    """The Phase 1A seam must not change the frozen Summary cutover default."""

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository, video_id="video-1")
    store = DeepAnalysisPersistenceStore(repository)

    persisted = store.persist_trusted_deep_analysis_success(
        success=_summary_promoting_success("video-1"), now=NOW
    )

    current = store.read_current_content_summary_result(video_id="video-1")
    assert current is not None
    assert current.result_identity == persisted.result_identity


def test_deep_analysis_does_not_overwrite_an_existing_summary_pointer(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed_content(repository, video_id="video-1")
    store = DeepAnalysisPersistenceStore(repository)
    summary = store.persist_trusted_deep_analysis_success(
        success=_summary_promoting_success("video-1"), now=NOW
    )
    assert store.read_current_content_summary_result(video_id="video-1") is not None

    # Run Deep Analysis against the very same Content identity.
    service = _service(repository, qualified=True)
    service._scoring_reader = (  # noqa: SLF001
        lambda _video_id: _scoring_read("video-1")
    )
    service.run(content_id="video-1")

    # The existing Summary pointer is unchanged.
    current = store.read_current_content_summary_result(video_id="video-1")
    assert current is not None
    assert current.result_identity == summary.result_identity
