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
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
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


def _knowledge_content() -> dict[str, object]:
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
        "key_arguments": [point("The fixture advances one central argument.", "inference")],
        "counterpoints": [point("The fixture notes one real counterpoint.", "inference")],
        "risks": [point("The fixture names one genuine risk.", "inference")],
        "actionable_directions": [
            point("The fixture suggests one concrete next direction.", "recommendation")
        ],
        "hypotheses_to_validate": [
            point("The fixture leaves one hypothesis to validate.", "inference")
        ],
        "knowledge_graph": {"topics": ["workflow"]},
    }


def _seed_content(repository: SQLiteStateRepository, video_id: str = VIDEO_ID) -> None:
    """Seed one scored Content with an explicit English output language.

    The fixture's model output is English, so the authoritative output language
    must be English. The product default is zh-CN; this sets the real
    authoritative preference rather than weakening language validation.
    """

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
        transcript_reader=lambda _video_id: None,
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
        transcript_reader=lambda _video_id: None,
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

    from tests.integration.test_deep_analysis_persistence import (  # noqa: PLC0415
        _trusted_success,
    )

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed_content(repository, video_id="video-1")
    store = DeepAnalysisPersistenceStore(repository)

    persisted = store.persist_trusted_deep_analysis_success(
        success=_trusted_success(video_id="video-1"), now=NOW
    )

    current = store.read_current_content_summary_result(video_id="video-1")
    assert current is not None
    assert current.result_identity == persisted.result_identity


def test_deep_analysis_does_not_overwrite_an_existing_summary_pointer(
    tmp_path: Path,
) -> None:
    from tests.integration.test_deep_analysis_persistence import (  # noqa: PLC0415
        _trusted_success,
    )

    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed_content(repository, video_id="video-1")
    store = DeepAnalysisPersistenceStore(repository)
    summary = store.persist_trusted_deep_analysis_success(
        success=_trusted_success(video_id="video-1"), now=NOW
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
