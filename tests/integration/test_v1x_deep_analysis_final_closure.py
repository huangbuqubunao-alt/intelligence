"""V1.x Phase 1A final closure: trust boundaries.

Adversarial coverage for the final review fixes:

- No response-admission bypass: every model response must validate as the
  five-role contract before reaching the compatibility carrier.
- Phase-1A results are categorically ineligible as trusted Note/export authority,
  including after restart.
- The compatibility mapping never crashes on a schema-valid payload and never
  rewrites epistemic meaning.
- Production source-language wiring uses the keyword-only reader.
- Persisted trusted timestamps must be timezone-aware.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_persistence import (
    DeepAnalysisPersistenceError,
    DeepAnalysisPersistenceStore,
    is_phase_1a_result,
    require_trusted_note_eligibility,
)
from youtube_intel.deep_analysis_phase1a_contract import (
    DeepAnalysisPhase1AModelOutput,
    map_phase_1a_output_to_knowledge_content,
)
from youtube_intel.deep_analysis_service import (
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
from youtube_intel.note_v2 import NoteV2Error, build_note_v2
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
VIDEO_ID = "video-closure-1"
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
        scoring_job_id="job-closure",
        scoring_success_provenance="PRIMARY",
    )


def _five_role_payload() -> dict[str, object]:
    return {
        "schema_version": "v1x-content-deep-analysis-model-output-v1",
        "core_conclusion": [
            {
                "text": "The content shows that evaluation drifts without a versioned baseline.",
                "point_kind": "inference",
            }
        ],
        "key_evidence": [
            {"text": "The available evidence supports this conclusion.", "point_kind": "fact"}
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


def _historical_knowledge_content() -> dict[str, object]:
    """A schema-valid historical KnowledgeContent with invented graph relations."""

    def point(text: str, kind: str) -> dict[str, object]:
        return {"text": text, "kind": kind, "evidence_ids": [REF]}

    return {
        "one_sentence_summary": "The model bypassed the five-role contract.",
        "summary_evidence_ids": [REF],
        "why_it_matters": point(
            "The model asserts this matters for the reader.", "inference"
        ),
        "core_points": [point("The model asserts one core fact.", "fact")],
        "knowledge_graph": {
            "topics": ["invented-topic"],
            "entities": ["Invented Entity"],
            "related_themes": ["Invented Related Theme"],
            "future_watch_topics": ["Invented Watch Topic"],
        },
    }


def _transport(payload: object):
    body = json.dumps(payload, ensure_ascii=False)

    def call(request: dict[str, object], timeout_seconds: float) -> object:
        del request, timeout_seconds
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
            "VALUES (?, 'UC_C', 'Fixture Channel', 'Fixture Title', 'SCORED', "
            "'fixture-v1', 'public', ?, ?)",
            (video_id, _stamp(NOW), _stamp(NOW)),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="en", now=NOW)


def _service(
    repository: SQLiteStateRepository,
    *,
    payload: object | None = None,
    qualified: bool = True,
) -> DeepAnalysisService:
    capability = DeepAnalysisCapability(
        (
            build_local_ollama_route(
                transport=_transport(
                    payload if payload is not None else _five_role_payload()
                )
            ),
        )
        if qualified
        else ()
    )
    return DeepAnalysisService(
        repository=repository,
        capability=capability,
        scoring_reader=_scoring_read,
        # Production-style keyword-only signature.
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )


def _persisted_rows(repository: SQLiteStateRepository) -> int:
    connection = repository._connect()
    try:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM deep_analysis_persisted_results"
        ).fetchone()
    finally:
        connection.close()
    return int(row["count"])


# 1. Five-role payload -> accepted.
def test_five_role_payload_is_accepted(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)

    result = _service(repository).run(content_id=VIDEO_ID)

    assert result.roles
    assert _persisted_rows(repository) == 1


# 2-5. Historical / deferred field payloads -> rejected.
@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("historical_knowledge_content", _historical_knowledge_content()),
        (
            "related_themes",
            {**_five_role_payload(), "related_themes": ["invented"]},
        ),
        ("entities", {**_five_role_payload(), "entities": ["Invented"]}),
        (
            "future_watch_topics",
            {**_five_role_payload(), "future_watch_topics": ["Invented"]},
        ),
        (
            "knowledge_graph",
            {
                **_five_role_payload(),
                "knowledge_graph": {"topics": ["x"], "related_themes": ["y"]},
            },
        ),
        (
            "relation_to_knowledge",
            {**_five_role_payload(), "relation_to_knowledge": ["invented"]},
        ),
        (
            "knowledge_delta",
            {**_five_role_payload(), "knowledge_delta": ["invented"]},
        ),
    ],
)
def test_deferred_or_historical_payload_is_rejected(
    tmp_path: Path, name: str, payload: dict[str, object]
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)

    with pytest.raises(DeepAnalysisRejected) as rejection:
        _service(repository, payload=payload).run(content_id=VIDEO_ID)

    assert rejection.value.status.availability is DeepAnalysisAvailability.FAILED
    # 6. No successful row is persisted.
    assert _persisted_rows(repository) == 0
    assert _service(repository, qualified=False).read(content_id=VIDEO_ID) is None


# 7. Restart cannot resurrect a rejected response.
def test_restart_cannot_resurrect_a_rejected_response(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    with pytest.raises(DeepAnalysisRejected):
        _service(repository, payload=_historical_knowledge_content()).run(
            content_id=VIDEO_ID
        )

    restarted = _service(SQLiteStateRepository(database), qualified=False)

    assert restarted.read(content_id=VIDEO_ID) is None
    assert _persisted_rows(SQLiteStateRepository(database)) == 0


# 8. Public DA API works for a valid persisted result.
def test_public_da_projection_works_for_valid_result(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)

    result = _service(repository).run(content_id=VIDEO_ID)
    read_back = _service(repository, qualified=False).read(content_id=VIDEO_ID)

    assert read_back is not None
    assert read_back.result_identity == result.result_identity
    assert REF not in json.dumps(read_back.as_dict(), ensure_ascii=False)


# 9. Trusted Note V2 rejects the same result after restart.
def test_trusted_note_v2_rejects_phase_1a_result_after_restart(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    _service(repository).run(content_id=VIDEO_ID)

    restarted = SQLiteStateRepository(database)
    stored = DeepAnalysisPersistenceStore(
        restarted
    ).read_deep_analysis_result_for_content(video_id=VIDEO_ID)
    assert stored is not None
    # The transitional state is positively identified from durable state.
    assert is_phase_1a_result(stored) is True

    with pytest.raises(NoteV2Error):
        build_note_v2(stored)

    with pytest.raises(DeepAnalysisPersistenceError):
        require_trusted_note_eligibility(stored)


# 10. Candidate refs never appear in trusted Note / export.
def test_candidate_refs_never_appear_in_trusted_note(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    _service(repository).run(content_id=VIDEO_ID)
    stored = DeepAnalysisPersistenceStore(
        repository
    ).read_deep_analysis_result_for_content(video_id=VIDEO_ID)
    assert stored is not None

    rendered = ""
    try:
        rendered = build_note_v2(stored).__repr__()
    except NoteV2Error as error:
        rendered = str(error)
    # No candidate ref is ever exposed by a trusted projection.
    assert REF not in rendered


# 11. Compatibility topics never appear as trusted Topic metadata.
def test_compatibility_topics_are_not_trusted_topic_metadata(
    tmp_path: Path,
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    _service(repository).run(content_id=VIDEO_ID)
    stored = DeepAnalysisPersistenceStore(
        repository
    ).read_deep_analysis_result_for_content(video_id=VIDEO_ID)
    assert stored is not None

    # Present only as inert internal carrier data.
    assert stored.content.knowledge_graph.topics
    assert stored.content.knowledge_graph.entities == ()
    assert stored.content.knowledge_graph.related_themes == ()
    assert stored.content.knowledge_graph.future_watch_topics == ()

    # No Topic row may be derived from them.
    connection = repository._connect()
    try:
        topics = connection.execute("SELECT COUNT(*) AS count FROM topics").fetchone()
        memberships = connection.execute(
            "SELECT COUNT(*) AS count FROM topic_memberships"
        ).fetchone()
    finally:
        connection.close()
    assert int(topics["count"]) == 0
    assert int(memberships["count"]) == 0


# 12-13. Compatibility mapping never crashes and never relabels.
def test_multiple_inference_relevance_claims_map_without_relabeling() -> None:
    payload = {
        **_five_role_payload(),
        "relevance_to_user": [
            {
                "text": "This changes how you should plan the next review.",
                "point_kind": "inference",
            },
            {
                "text": "This also changes how you should measure the outcome.",
                "point_kind": "inference",
            },
            {
                "text": "This further affects the way you report the result.",
                "point_kind": "inference",
            },
        ],
    }
    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)

    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    kinds = {point.kind.value for point in content.product_opportunities}
    # Epistemic meaning is preserved: no relabelling to "recommendation".
    assert kinds == {"inference"}
    assert len(content.product_opportunities) == 3
    assert content.actionable_directions == ()


@pytest.mark.parametrize(
    ("relevance", "questions", "uncertainty", "conclusions", "evidence"),
    [
        (1, 1, 1, 1, 1),
        (2, 2, 2, 2, 2),
        (5, 5, 0, 3, 4),
        (10, 10, 10, 10, 10),
        # Optional collections may be empty.
        (1, 0, 0, 1, 1),
        (0, 1, 0, 1, 1),
        # Bounded maximums on the required collections.
        (20, 0, 0, 10, 20),
    ],
)
def test_every_schema_valid_payload_maps_without_validation_error(
    relevance: int,
    questions: int,
    uncertainty: int,
    conclusions: int,
    evidence: int,
) -> None:
    def claims(count: int, kind: str) -> list[dict[str, object]]:
        return [
            {
                "text": f"Claim number {index} states something concrete and verifiable.",
                "point_kind": kind,
            }
            for index in range(count)
        ]

    payload: dict[str, object] = {
        "core_conclusion": claims(conclusions, "inference"),
        "key_evidence": claims(evidence, "fact"),
    }
    if uncertainty:
        payload["uncertainty"] = claims(uncertainty, "inference")
    if relevance:
        payload["relevance_to_user"] = claims(relevance, "inference")
    if questions:
        payload["next_question"] = claims(questions, "inference")

    # Either the schema rejects it with a clear rule, or it maps faithfully.
    try:
        parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    except ValueError:
        return  # Rejected by contract rule B: acceptable and explicit.
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )
    assert content.one_sentence_summary
    assert len(content.product_opportunities) == relevance
    assert len(content.hypotheses_to_validate) == questions
    assert len(content.counterpoints) == uncertainty


def test_unrepresentable_kind_is_rejected_by_schema_with_clear_rule() -> None:
    payload = {
        **_five_role_payload(),
        "key_evidence": [
            {"text": "This is labelled inference instead of fact.", "point_kind": "inference"}
        ],
    }

    with pytest.raises(ValueError) as error:
        DeepAnalysisPhase1AModelOutput.model_validate(payload)

    assert "faithfully" in str(error.value)


# 14. Production keyword-only transcript reader.
def test_production_keyword_only_transcript_reader_works(tmp_path: Path) -> None:
    """Uses the exact signature production injects."""

    calls: list[str] = []

    def production_reader(*, video_id: str):
        calls.append(video_id)
        return None

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    service = DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability((build_local_ollama_route(
            transport=_transport(_five_role_payload())
        ),)),
        scoring_reader=_scoring_read,
        transcript_reader=production_reader,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )

    result = service.run(content_id=VIDEO_ID)

    assert result.roles
    # The keyword-only reader was actually invoked, not bypassed.
    assert calls and VIDEO_ID in calls


def test_positional_only_reader_signature_is_not_assumed(
    tmp_path: Path,
) -> None:
    """A keyword-only callable must be callable; the service must use keywords."""

    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)

    seen: list[str] = []

    def strict(*, video_id: str) -> None:
        # A positional call would raise TypeError before reaching this body.
        seen.append(video_id)
        return None

    service = DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability((build_local_ollama_route(
            transport=_transport(_five_role_payload())
        ),)),
        scoring_reader=_scoring_read,
        transcript_reader=strict,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )

    assert service.run(content_id=VIDEO_ID).roles
    assert seen == [VIDEO_ID, VIDEO_ID]


# 15-17. Timestamp strictness.
@pytest.mark.parametrize("column", ["created_at", "validated_at"])
@pytest.mark.parametrize(
    "stored",
    [
        "2035-06-07T12:34:56",
        "2035-06-07T12:34:56.000000",
        "2035-06-07 12:34:56",
        "",
        "not-a-timestamp",
    ],
)
def test_naive_or_malformed_persisted_timestamp_is_rejected(
    tmp_path: Path, column: str, stored: str
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    result = _service(repository).run(content_id=VIDEO_ID)
    connection = repository._connect()
    try:
        connection.execute(
            f"UPDATE deep_analysis_persisted_results SET {column} = ? "
            "WHERE result_identity = ?",
            (stored, result.result_identity),
        )
    finally:
        connection.close()

    # No forged generated_at is served; the row simply fails verification.
    assert _service(repository, qualified=False).read(content_id=VIDEO_ID) is None


@pytest.mark.parametrize(
    "stored", ["2035-06-07T12:34:56Z", "2035-06-07T12:34:56+00:00"]
)
def test_timezone_aware_persisted_timestamp_is_accepted(
    tmp_path: Path, stored: str
) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    result = _service(repository).run(content_id=VIDEO_ID)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE deep_analysis_persisted_results SET created_at = ? "
            "WHERE result_identity = ?",
            (stored, result.result_identity),
        )
    finally:
        connection.close()

    read_back = _service(repository, qualified=False).read(content_id=VIDEO_ID)
    assert read_back is not None
    # The stored value is honoured and normalized to UTC, never replaced by the
    # current time.
    from youtube_intel.state import format_utc_datetime

    expected = format_utc_datetime(
        datetime.fromisoformat(
            stored.removesuffix("Z") + "+00:00"
            if stored.endswith("Z")
            else stored
        )
    )
    assert read_back.generated_at == expected
    assert read_back.generated_at != _stamp(NOW)


def test_timezone_aware_timestamps_survive_restart(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    before = _service(repository).run(content_id=VIDEO_ID)

    after = _service(SQLiteStateRepository(database), qualified=False).read(
        content_id=VIDEO_ID
    )

    assert after is not None
    assert after.generated_at == before.generated_at == _stamp(NOW)


# Summary separation and qualification regression.
def test_summary_pointer_is_never_promoted(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite")
    repository.initialize(now=NOW)
    _seed(repository)
    store = DeepAnalysisPersistenceStore(repository)

    _service(repository).run(content_id=VIDEO_ID)

    assert store.read_current_content_summary_result(video_id=VIDEO_ID) is None


def test_phase_1a_result_is_not_phase_1a_ineligible_for_other_objects() -> None:
    assert is_phase_1a_result(object()) is False
