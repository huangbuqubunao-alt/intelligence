"""V1.x Phase 1A product-correctness closure.

Proves the accepted-input mapping invariant and a lossless public round trip:

- IF ``DeepAnalysisPhase1AModelOutput`` accepts a payload, the deterministic
  compatibility mapping MUST succeed without an uncaught ``ValidationError``.
- Every accepted claim for the five public roles survives mapping, persistence,
  restart, and public projection. Nothing is silently dropped.
- Real local HTTP error bodies retain safe machine-readable details.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_persistence import DeepAnalysisPersistenceStore
from youtube_intel.deep_analysis_phase1a_contract import (
    MAX_CLAIM_CHARS,
    MAX_CORE_CONCLUSION_CHARS,
    ROLE_MAX_CLAIMS,
    DeepAnalysisPhase1AModelOutput,
    map_phase_1a_output_to_knowledge_content,
)
from youtube_intel.deep_analysis_service import (
    DEEP_ANALYSIS_ROLES,
    DeepAnalysisCapability,
    DeepAnalysisService,
    build_local_ollama_route,
)
from youtube_intel.domain import (
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.local_api import ApiError, LocalApiApplication, _error_body
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
VIDEO_ID = "video-product-closure"
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
        scoring_job_id="job-product",
        scoring_success_provenance="PRIMARY",
    )


def claim(text: str, point_kind: str = "inference") -> dict[str, object]:
    return {"text": text, "point_kind": point_kind}


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


def _seed(repository: SQLiteStateRepository) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO videos "
            "(video_id, channel_id, channel_name, title, pipeline_status, "
            "pipeline_version, availability, discovered_at, updated_at) "
            "VALUES (?, 'UC_P', 'Fixture Channel', 'Fixture Title', 'SCORED', "
            "'fixture-v1', 'public', ?, ?)",
            (VIDEO_ID, _stamp(NOW), _stamp(NOW)),
        )
    finally:
        connection.close()
    repository.save_global_output_language(output_language="en", now=NOW)


def _service(
    repository: SQLiteStateRepository, *, payload: object | None = None
) -> DeepAnalysisService:
    return DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability(
            (
                build_local_ollama_route(
                    transport=_transport(
                        payload
                        if payload is not None
                        else {
                            "core_conclusion": [claim("The content shows a clear result.")],
                            "key_evidence": [claim("Evidence supports it.", "fact")],
                        }
                    )
                ),
            )
        ),
        scoring_reader=_scoring_read,
        transcript_reader=lambda *, video_id: None,
        evidence_reader=lambda _video_id: (REF,),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )


# ---------------------------------------------------------------------------
# FIX 1 — contract capacity
# ---------------------------------------------------------------------------


def test_max_length_conclusion_is_accepted_and_maps() -> None:
    payload = {
        "core_conclusion": [
            claim("x" * MAX_CORE_CONCLUSION_CHARS, "inference")
        ],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    assert len(content.one_sentence_summary) == MAX_CORE_CONCLUSION_CHARS


def test_one_over_max_length_conclusion_is_rejected_before_mapping() -> None:
    payload = {
        "core_conclusion": [
            claim("x" * (MAX_CORE_CONCLUSION_CHARS + 1), "inference")
        ],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
    }

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)

    # Rejection happens at the schema, so the mapper is never reached and text
    # is never silently truncated.
    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)


def test_fact_conclusion_without_inference_is_rejected_not_crashed() -> None:
    payload = {
        "core_conclusion": [claim("A stated fact with no inference anywhere.", "fact")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
    }

    with pytest.raises(ValueError) as error:
        DeepAnalysisPhase1AModelOutput.model_validate(payload)

    assert "why_it_matters" in str(error.value) or "inference" in str(error.value)


def test_fact_conclusion_with_inference_material_is_accepted_and_faithful() -> None:
    payload = {
        "core_conclusion": [claim("A stated fact conclusion.", "fact")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
        "uncertainty": [claim("This part remains unverified right now.", "inference")],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    # The fact conclusion stays a fact; why_it_matters is a real inference.
    assert {point.kind.value for point in content.core_points} == {"fact"}
    assert content.why_it_matters.kind.value == "inference"


def test_multiple_inference_relevance_claims_all_map() -> None:
    payload = {
        "core_conclusion": [claim("The content shows a clear result.")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
        "relevance_to_user": [
            claim("This changes how you should plan the next review."),
            claim("This also changes how you should measure the outcome."),
            claim("This further affects the way you report the result."),
        ],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    assert len(content.product_opportunities) == 3
    assert {point.kind.value for point in content.product_opportunities} == {"inference"}


def test_max_relevance_count_all_map_and_one_more_is_rejected() -> None:
    limit = ROLE_MAX_CLAIMS["relevance_to_user"]
    base = {
        "core_conclusion": [claim("The content shows a clear result.")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
    }

    at_limit = DeepAnalysisPhase1AModelOutput.model_validate(
        {
            **base,
            "relevance_to_user": [
                claim(f"Relevance claim number {index} is concrete and verifiable.")
                for index in range(limit)
            ],
        }
    )
    mapped = map_phase_1a_output_to_knowledge_content(
        at_limit, summary_evidence_ids=(REF,)
    )
    assert len(mapped.product_opportunities) == limit

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(
            {
                **base,
                "relevance_to_user": [
                    claim(
                        f"Relevance claim number {index} is concrete and verifiable."
                    )
                    for index in range(limit + 1)
                ],
            }
        )


@pytest.mark.parametrize(
    ("role", "kind"),
    [
        ("key_evidence", "fact"),
        ("uncertainty", "inference"),
        ("next_question", "inference"),
    ],
)
def test_role_limit_is_enforced_for_every_role(role: str, kind: str) -> None:
    limit = ROLE_MAX_CLAIMS[role]
    base = {
        "core_conclusion": [claim("The content shows a clear result.")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
    }
    if role == "key_evidence":
        base = {"core_conclusion": [claim("The content shows a clear result.")]}

    def build(count: int) -> dict[str, object]:
        return {**base, role: [claim(f"Claim {i} is concrete.", kind) for i in range(count)]}

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(build(limit))
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )
    assert content  # mapped at the limit

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(build(limit + 1))


def test_non_summary_claim_text_limit_is_the_carrier_limit() -> None:
    assert MAX_CLAIM_CHARS == 2000
    payload = {
        "core_conclusion": [claim("The content shows a clear result.")],
        "key_evidence": [claim("y" * MAX_CLAIM_CHARS, "fact")],
    }
    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )
    assert len(content.key_facts[0].text) == MAX_CLAIM_CHARS


@pytest.mark.parametrize(
    ("conclusions", "evidence", "uncertainty", "relevance", "questions"),
    [
        (1, 1, 0, 0, 0),
        (1, 1, 1, 1, 1),
        (5, 5, 5, 5, 5),
        (10, 20, 10, 10, 10),
    ],
)
def test_every_schema_valid_fixture_maps_without_uncaught_validation_error(
    conclusions: int,
    evidence: int,
    uncertainty: int,
    relevance: int,
    questions: int,
) -> None:
    payload: dict[str, object] = {
        "core_conclusion": [
            claim(f"Conclusion number {i} is concrete and verifiable.")
            for i in range(conclusions)
        ],
        "key_evidence": [
            claim(f"Evidence number {i} is concrete and verifiable.", "fact")
            for i in range(evidence)
        ],
    }
    if uncertainty:
        payload["uncertainty"] = [
            claim(f"Uncertainty number {i} is concrete.")
            for i in range(uncertainty)
        ]
    if relevance:
        payload["relevance_to_user"] = [
            claim(f"Relevance number {i} is concrete.") for i in range(relevance)
        ]
    if questions:
        payload["next_question"] = [
            claim(f"Question number {i} is concrete.") for i in range(questions)
        ]

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    # Must never raise.
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )
    assert len(content.core_points) == conclusions
    assert len(content.key_facts) == evidence
    assert len(content.counterpoints) == uncertainty
    assert len(content.product_opportunities) == relevance
    assert len(content.hypotheses_to_validate) == questions


# ---------------------------------------------------------------------------
# FIX 2 — lossless public round trip
# ---------------------------------------------------------------------------


def test_three_relevance_claims_survive_restart_and_projection(
    tmp_path: Path,
) -> None:
    """The previously reproduced claim loss: 3 relevance claims must return 3."""

    payload = {
        "core_conclusion": [claim("The content shows a clear result.")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
        "relevance_to_user": [
            claim("Relevance one changes how you should plan the review."),
            claim("Relevance two changes how you should measure the outcome."),
            claim("Relevance three changes the way you report the result."),
        ],
    }
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    before = _service(repository, payload=payload).run(content_id=VIDEO_ID)

    # Full restart.
    after = _service(SQLiteStateRepository(database)).read(content_id=VIDEO_ID)

    assert after is not None
    relevance = [c for c in after.roles if c.role == "RELEVANCE_TO_USER"]
    assert len(relevance) == 3
    assert [c.text for c in relevance] == [
        "Relevance one changes how you should plan the review.",
        "Relevance two changes how you should measure the outcome.",
        "Relevance three changes the way you report the result.",
    ]
    assert len(
        [c for c in before.roles if c.role == "RELEVANCE_TO_USER"]
    ) == 3


def test_all_five_roles_round_trip_without_claim_loss(tmp_path: Path) -> None:
    payload = {
        "core_conclusion": [
            claim("The content shows that the review process drifts over time."),
            claim("The content shows that the baseline was never versioned."),
        ],
        "key_evidence": [
            claim("The available evidence supports that review outcomes drift.", "fact"),
            claim("The recorded evidence shows that the baseline changed.", "fact"),
            claim("The measured evidence shows that drift was not detected.", "fact"),
        ],
        "uncertainty": [
            claim("This remains unverified and should not be relied on yet."),
            claim("This remains unverified and could still be contradicted."),
        ],
        "relevance_to_user": [
            claim("This changes how you should plan the next review."),
            claim("This changes how you should measure the outcome."),
        ],
        "next_question": [
            claim("Check whether the second claim is corroborated elsewhere."),
            claim("Check whether the raw data supports the stated baseline."),
        ],
    }
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    _service(repository, payload=payload).run(content_id=VIDEO_ID)

    after = _service(SQLiteStateRepository(database)).read(content_id=VIDEO_ID)
    assert after is not None

    counts = {
        "CORE_CONCLUSION": 2,
        "KEY_EVIDENCE": 3,
        "UNCERTAINTY": 2,
        "RELEVANCE_TO_USER": 2,
        "NEXT_QUESTION": 2,
    }
    for role, expected in counts.items():
        assert len([c for c in after.roles if c.role == role]) == expected, role
    # Every public role is represented and no deferred role appears.
    assert {c.role for c in after.roles} == set(DEEP_ANALYSIS_ROLES)
    # Point kind and ordering survive.
    conclusion_kinds = [
        c.point_kind for c in after.roles if c.role == "CORE_CONCLUSION"
    ]
    assert conclusion_kinds == ["inference", "inference"]
    evidence_kinds = [c.point_kind for c in after.roles if c.role == "KEY_EVIDENCE"]
    assert evidence_kinds == ["fact", "fact", "fact"]
    # Confidence is present for every claim.
    assert all(c.confidence for c in after.roles)


def test_projection_reads_each_role_from_its_own_carrier_field(
    tmp_path: Path,
) -> None:
    """The projection must not read a field the mapper does not populate."""

    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    _service(repository).run(content_id=VIDEO_ID)

    stored = DeepAnalysisPersistenceStore(
        repository
    ).read_deep_analysis_result_for_content(video_id=VIDEO_ID)
    assert stored is not None
    # Fields the projection must not read for the five roles.
    assert stored.content.actionable_directions == ()
    assert stored.content.action_recommendations == ()
    assert stored.content.key_arguments == ()
    assert stored.content.risks == ()


# ---------------------------------------------------------------------------
# FIX 3 — real HTTP error details
# ---------------------------------------------------------------------------


def test_error_body_preserves_safe_machine_details() -> None:
    error = ApiError(
        HTTPStatus.CONFLICT,
        "DEEP_ANALYSIS_NOT_QUALIFIED",
        "No Deep Analysis model is currently qualified.",
        details={
            "reason_code": "NO_QUALIFIED_MODEL",
            "availability": "NOT_QUALIFIED",
            "consent_required": False,
        },
    )

    body = _error_body(error)

    assert body["error"]["code"] == "DEEP_ANALYSIS_NOT_QUALIFIED"
    details = body["error"]["details"]
    assert details["reason_code"] == "NO_QUALIFIED_MODEL"
    assert details["availability"] == "NOT_QUALIFIED"
    assert details["consent_required"] is False


def test_error_body_drops_unsafe_details() -> None:
    error = ApiError(
        HTTPStatus.CONFLICT,
        "X",
        "message",
        details={
            "reason_code": "NO_QUALIFIED_MODEL",
            "stack_trace": "Traceback: /Users/someone/secret/path.py",
            "credential": "sk-do-not-leak",
            "path": "/Users/someone/data/state.sqlite",
        },
    )

    body = _error_body(error)

    serialized = json.dumps(body)
    assert "sk-do-not-leak" not in serialized
    assert "Traceback" not in serialized
    assert "/Users/someone" not in serialized
    # The safe key survives.
    assert body["error"]["details"]["reason_code"] == "NO_QUALIFIED_MODEL"


def test_error_body_without_details_is_unchanged() -> None:
    body = _error_body(ApiError(HTTPStatus.NOT_FOUND, "NOT_FOUND", "missing"))

    assert body == {"error": {"code": "NOT_FOUND", "message": "missing"}}


def test_real_http_post_failure_body_retains_reason_code(tmp_path: Path) -> None:
    """Exercises the real ApiError path used by the local HTTP handler."""

    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    app = LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        data_root=tmp_path / "data",
        vault_root=tmp_path / "vault",
        now=lambda: NOW,
        # No qualified route: the real rejection path runs.
        deep_analysis_service=_service(repository),
    )
    app._deep_analysis_service._capability = DeepAnalysisCapability(())  # noqa: SLF001

    with pytest.raises(ApiError) as raised:
        app.handle("POST", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    body = _error_body(raised.value)
    assert body["error"]["code"] == "DEEP_ANALYSIS_NOT_QUALIFIED"
    assert body["error"]["details"]["reason_code"] == "NO_QUALIFIED_MODEL"
    assert body["error"]["details"]["availability"] == "NOT_QUALIFIED"
