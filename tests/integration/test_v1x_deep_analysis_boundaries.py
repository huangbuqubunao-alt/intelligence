"""V1.x Phase 1A remediation: activation boundaries.

These tests pin the review fixes:

- Qualification is never minted by configuration, including the retired
  ``YIA_DEEP_ANALYSIS_LOCAL_QUALIFIED`` environment flag.
- The **live** model boundary requests only the five first-version concepts.
- Candidate refs never become user-facing or authoritative citations.
- ``generated_at`` is authoritative, not read-time derived.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.deep_analysis_phase1a_contract import (
    DEFERRED_MODEL_FIELDS,
    DeepAnalysisPhase1AModelOutput,
    map_phase_1a_output_to_knowledge_content,
    phase_1a_model_schema_json,
)
from youtube_intel.deep_analysis_service import (
    DEEP_ANALYSIS_ROLES,
    EVIDENCE_CITATION_STATUS_PENDING,
    TRANSIENT_EVIDENCE_REF_AUTHORITY,
    DeepAnalysisAvailability,
    DeepAnalysisCapability,
    DeepAnalysisReasonCode,
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
from youtube_intel.runtime_composition import _deep_analysis_production_capability
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
VIDEO_ID = "video-remediation-1"
REF = "t0-3-abc123"


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


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
        scoring_job_id="job-remediation",
        scoring_success_provenance="PRIMARY",
    )


def _five_role_payload() -> dict[str, object]:
    """A Phase-1A model response containing only the five permitted concepts."""

    return {
        "schema_version": "v1x-content-deep-analysis-model-output-v1",
        "core_conclusion": [
            {
                "text": "The content shows that evaluation drifts without a versioned baseline.",
                "point_kind": "inference",
            }
        ],
        "key_evidence": [
            {
                "text": "The available evidence supports this conclusion.",
                "point_kind": "fact",
            }
        ],
        "uncertainty": [
            {
                "text": "This remains unverified and should not be relied on yet.",
                "point_kind": "inference",
            }
        ],
        "relevance_to_user": [
            {
                "text": "This matters because it changes how you should plan the next review.",
                "point_kind": "inference",
            }
        ],
        "next_question": [
            {
                "text": "Check whether the second claim is corroborated by another source.",
                "point_kind": "inference",
            }
        ],
    }


def _transport(payload: object, *, record: list[str] | None = None):
    body = json.dumps(payload, ensure_ascii=False)

    def call(request: dict[str, object], timeout_seconds: float) -> object:
        del timeout_seconds
        if record is not None:
            record.append(str(request.get("messages", "")))
        return {
            "model": "qwen2.5-coder:7b",
            "done": True,
            "done_reason": "stop",
            "message": {"content": body},
        }

    return call


class _VerifiedEvidence:
    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self.excerpt = "A verified transcript excerpt for the fixture."
        self.excerpt_hash = "d" * 64


def _seed(repository: SQLiteStateRepository, video_id: str = VIDEO_ID) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO videos "
            "(video_id, channel_id, channel_name, title, pipeline_status, "
            "pipeline_version, availability, discovered_at, updated_at) "
            "VALUES (?, 'UC_R', 'Fixture Channel', 'Fixture Title', 'SCORED', "
            "'fixture-v1', 'public', ?, ?)",
            (video_id, _stamp(NOW), _stamp(NOW)),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="en", now=NOW)


def _service(
    repository: SQLiteStateRepository,
    *,
    qualified: bool = True,
    payload: object | None = None,
    record: list[str] | None = None,
) -> DeepAnalysisService:
    capability = DeepAnalysisCapability(
        (build_local_ollama_route(transport=_transport(
            payload if payload is not None else _five_role_payload(),
            record=record,
        )),)
        if qualified
        else ()
    )
    return DeepAnalysisService(
        repository=repository,
        capability=capability,
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )


# ---------------------------------------------------------------------------
# FIX 1 — qualification must not be configuration truth
# ---------------------------------------------------------------------------


def test_production_composition_is_not_qualified_by_default() -> None:
    capability = _deep_analysis_production_capability()

    assert capability.routes == ()
    assert capability.local_route() is None


def test_retired_environment_flag_cannot_qualify_a_production_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old flag alone must never mint qualification truth."""

    monkeypatch.setenv("YIA_DEEP_ANALYSIS_LOCAL_QUALIFIED", "1")

    capability = _deep_analysis_production_capability()

    assert capability.routes == ()
    assert capability.local_route() is None


def test_production_status_is_truthfully_not_qualified_even_with_the_old_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("YIA_DEEP_ANALYSIS_LOCAL_QUALIFIED", "1")
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    # Production composition capability, not the injected dev/test one.
    service = DeepAnalysisService(
        repository=repository,
        capability=_deep_analysis_production_capability(),
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )

    status = service.status(content_id=VIDEO_ID)

    assert status.availability is DeepAnalysisAvailability.NOT_QUALIFIED
    assert status.reason_code is DeepAnalysisReasonCode.NO_QUALIFIED_MODEL
    assert status.qualified is False


def test_unqualified_production_post_never_dispatches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("YIA_DEEP_ANALYSIS_LOCAL_QUALIFIED", "1")
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    dispatched: list[str] = []
    service = DeepAnalysisService(
        repository=repository,
        capability=_deep_analysis_production_capability(),
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )

    with pytest.raises(DeepAnalysisRejected) as rejection:
        service.run(content_id=VIDEO_ID)

    assert rejection.value.status.availability is DeepAnalysisAvailability.NOT_QUALIFIED
    assert dispatched == []
    assert service.read(content_id=VIDEO_ID) is None


def test_dev_test_injection_can_still_exercise_the_path(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)

    result = service.run(content_id=VIDEO_ID)

    assert result.roles
    assert service.read(content_id=VIDEO_ID) is not None


def test_reads_never_dispatch(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    dispatched: list[str] = []
    service = _service(repository, qualified=True, record=dispatched)

    # Status and read are pure projections.
    service.status(content_id=VIDEO_ID)
    service.read(content_id=VIDEO_ID)

    assert dispatched == []
    assert service.read(content_id=VIDEO_ID) is None
    # Only an explicit run dispatches.
    service.run(content_id=VIDEO_ID)
    assert len(dispatched) == 1


def test_only_the_local_route_is_available(tmp_path: Path) -> None:
    """No cloud/provider fallback may exist in the activated path."""

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)

    route = service._capability.local_route()  # noqa: SLF001
    assert route is not None
    assert route.is_local is True
    assert route.provider_id == "ollama-local"
    for cloud in ("openai", "kimi", "moonshot"):
        assert cloud not in route.provider_id
        assert cloud not in route.dispatch.__qualname__.lower()


# ---------------------------------------------------------------------------
# FIX 2 — the live model boundary must hold B1-a
# ---------------------------------------------------------------------------


def test_model_schema_requests_no_deferred_field() -> None:
    schema = phase_1a_model_schema_json()

    for deferred in DEFERRED_MODEL_FIELDS:
        assert f'"{deferred}"' not in schema
    assert "related_themes" not in schema
    assert "knowledge_graph" not in schema
    assert "knowledge_delta" not in schema
    assert "relation_to_knowledge" not in schema


def test_model_output_contract_rejects_deferred_fields() -> None:
    payload = dict(_five_role_payload())
    payload["knowledge_delta"] = [{"text": "invented", "point_kind": "inference"}]

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)

    payload = dict(_five_role_payload())
    payload["knowledge_graph"] = {"topics": ["x"], "related_themes": ["y"]}
    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)


def test_five_permitted_concepts_remain_available() -> None:
    parsed = DeepAnalysisPhase1AModelOutput.model_validate(_five_role_payload())

    assert parsed.core_conclusion
    assert parsed.key_evidence
    assert parsed.uncertainty
    assert parsed.relevance_to_user
    assert parsed.next_question


def test_live_provider_prompt_excludes_deferred_requests(tmp_path: Path) -> None:
    """Inspect the real prompt sent to the provider, not just the UI."""

    record: list[str] = []
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True, record=record)

    service.run(content_id=VIDEO_ID)

    assert record, "the provider must have been called"
    sent = record[0]
    # The five concepts are requested.
    for concept in (
        "core_conclusion",
        "key_evidence",
        "uncertainty",
        "relevance_to_user",
        "next_question",
    ):
        assert concept in sent
    # Deferred knowledge requests are absent.
    assert "knowledge_delta" not in sent
    assert "relation_to_knowledge" not in sent
    assert "related_themes" not in sent
    assert "future_watch_topics" not in sent
    assert "knowledge_graph" not in sent
    assert "KnowledgeContent schema" not in sent


def test_compatibility_mapping_fills_deferred_fields_deterministically() -> None:
    parsed = DeepAnalysisPhase1AModelOutput.model_validate(_five_role_payload())

    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    # Compatibility fields only: never model-authored.
    assert content.knowledge_graph.entities == ()
    assert content.knowledge_graph.related_themes == ()
    assert content.knowledge_graph.future_watch_topics == ()
    # The five concepts survive the mapping.
    assert content.one_sentence_summary
    assert content.key_facts
    assert content.counterpoints
    assert content.hypotheses_to_validate


def test_deferred_fields_never_reach_the_user_projection(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)

    payload = service.run(content_id=VIDEO_ID).as_dict()
    serialized = json.dumps(payload, ensure_ascii=False)

    assert {claim["role"] for claim in payload["roles"]} <= set(DEEP_ANALYSIS_ROLES)
    for leaked in ("related_themes", "knowledge_graph", "future_watch_topics"):
        assert leaked not in serialized


# ---------------------------------------------------------------------------
# FIX 3 — candidate refs must never become authority
# ---------------------------------------------------------------------------


def test_candidate_ref_absent_from_public_api_projection(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)

    result = service.run(content_id=VIDEO_ID)
    serialized = json.dumps(result.as_dict(), ensure_ascii=False)

    assert REF not in serialized
    assert "evidence_ids" not in serialized
    assert "evidence_refs" not in serialized
    assert "evidence_id" not in serialized
    assert result.evidence_citation_status == EVIDENCE_CITATION_STATUS_PENDING


def test_transitional_ref_authority_is_explicitly_non_authoritative() -> None:
    assert TRANSIENT_EVIDENCE_REF_AUTHORITY == "TRANSITIONAL_NON_AUTHORITATIVE"


def test_persisted_compatibility_refs_are_not_treated_as_durable_evidence(
    tmp_path: Path,
) -> None:
    """The stored registry holds candidate refs and must not be read as authority."""

    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)
    result = service.run(content_id=VIDEO_ID)

    stored = DeepAnalysisPersistenceStore(repository).read_deep_analysis_result_for_content(
        video_id=VIDEO_ID
    )
    assert stored is not None
    # The ref is present only inside the transitional registry.
    assert stored.evidence_registry.items[0].evidence_id == REF
    assert (
        stored.evidence_registry.items[0].source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    # It is a candidate ref, not a durable evidence_id, so no durable Evidence
    # row exists for it.
    assert repository.get_evidence(REF) is None
    # And it never surfaces in the user-facing projection.
    assert REF not in json.dumps(result.as_dict(), ensure_ascii=False)


def test_registry_identity_marks_the_transitional_scope(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)
    service.run(content_id=VIDEO_ID)

    stored = DeepAnalysisPersistenceStore(repository).read_deep_analysis_result_for_content(
        video_id=VIDEO_ID
    )
    assert stored is not None
    assert "transient-candidate-refs" in stored.canonical_input.evidence_registry_identity


def test_deep_analysis_does_not_write_note_or_artifact_publication(
    tmp_path: Path,
) -> None:
    """Phase 1A must not publish any Obsidian/Note artifact."""

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)
    service.run(content_id=VIDEO_ID)

    connection = repository._connect()
    try:
        rows = connection.execute(
            "SELECT COUNT(*) AS count FROM artifacts WHERE kind IN "
            "('video_note', 'weekly_report')"
        ).fetchone()
    finally:
        connection.close()
    assert int(rows["count"]) == 0


# ---------------------------------------------------------------------------
# FIX 4 — generated_at must be authoritative
# ---------------------------------------------------------------------------


def test_generated_at_comes_from_the_persisted_row(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)

    result = service.run(content_id=VIDEO_ID)

    assert result.generated_at == _stamp(NOW)
    assert result.generated_at.endswith("Z")


def test_repeated_get_returns_the_same_generated_at(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)
    first = service.run(content_id=VIDEO_ID)

    later = DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability(()),
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        # A different clock must not change the reported generation time.
        now=lambda: datetime(2030, 1, 1, tzinfo=UTC),
    )
    second = later.read(content_id=VIDEO_ID)
    third = later.read(content_id=VIDEO_ID)

    assert second is not None and third is not None
    assert second.generated_at == first.generated_at
    assert third.generated_at == first.generated_at


def test_restart_returns_the_same_generated_at(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    before = _service(repository, qualified=True).run(content_id=VIDEO_ID)

    # Full process restart with a brand-new repository and clock.
    restarted = DeepAnalysisService(
        repository=SQLiteStateRepository(database),
        capability=DeepAnalysisCapability(()),
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: datetime(2031, 6, 6, tzinfo=UTC),
    )
    after = restarted.read(content_id=VIDEO_ID)

    assert after is not None
    assert after.generated_at == before.generated_at
    assert after.result_identity == before.result_identity


def test_malformed_persisted_timestamp_is_not_silently_replaced(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    result = _service(repository, qualified=True).run(content_id=VIDEO_ID)

    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE deep_analysis_persisted_results SET created_at = ? "
            "WHERE result_identity = ?",
            ("not-a-timestamp", result.result_identity),
        )
    finally:
        connection.close()

    # No fabricated substitute time is served.
    assert _service(repository, qualified=False).read(content_id=VIDEO_ID) is None


def test_summary_pointer_is_never_created_by_deep_analysis(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    store = DeepAnalysisPersistenceStore(repository)

    _service(repository, qualified=True).run(content_id=VIDEO_ID)

    assert store.read_current_content_summary_result(video_id=VIDEO_ID) is None
    connection = repository._connect()
    try:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM current_content_summaries"
        ).fetchone()
    finally:
        connection.close()
    assert int(count["count"]) == 0


def test_registry_and_content_stay_consistent(tmp_path: Path) -> None:
    """Sanity: the compatibility mapping keeps grounding intact."""

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = _service(repository, qualified=True)
    service.run(content_id=VIDEO_ID)

    stored = DeepAnalysisPersistenceStore(repository).read_deep_analysis_result_for_content(
        video_id=VIDEO_ID
    )
    assert stored is not None
    allowed = {item.evidence_id for item in stored.evidence_registry.items}
    assert stored.content.summary_evidence_ids
    for ref in stored.content.summary_evidence_ids:
        assert ref in allowed
    registry = EvidenceRegistry(
        items=(
            KnowledgeEvidence(
                evidence_id=REF,
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="A verified transcript excerpt for the fixture.",
                source_content_hash="d" * 64,
            ),
        )
    )
    assert {item.evidence_id for item in registry.items} == allowed
