"""V1.x Phase 1A semantic closure.

Proves the final product-semantics rules:

- ``why_it_matters`` derives **only** from ``relevance_to_user``; no other role
  is ever relabelled to fill it.
- ``relevance_to_user`` is required and must be non-empty.
- Claim text is canonicalized once at the Phase-1A admission boundary and then
  preserved verbatim through mapping, persistence, restart, and projection.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_phase1a_contract import (
    MAX_CORE_CONCLUSION_CHARS,
    DeepAnalysisPhase1AModelOutput,
    map_phase_1a_output_to_knowledge_content,
)
from youtube_intel.deep_analysis_service import (
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
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
VIDEO_ID = "video-semantic-closure"
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
        scoring_job_id="job-semantic",
        scoring_success_provenance="PRIMARY",
    )


def claim(text: str, point_kind: str = "inference") -> dict[str, object]:
    return {"text": text, "point_kind": point_kind}


def _base() -> dict[str, object]:
    return {
        "core_conclusion": [claim("The content shows that review outcomes drift.")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
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


def _seed(repository: SQLiteStateRepository) -> None:
    connection = repository._connect()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO videos "
            "(video_id, channel_id, channel_name, title, pipeline_status, "
            "pipeline_version, availability, discovered_at, updated_at) "
            "VALUES (?, 'UC_S', 'Fixture Channel', 'Fixture Title', 'SCORED', "
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
                            **_base(),
                            "relevance_to_user": [
                                claim("This changes how you should plan the review.")
                            ],
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
# FIX 1 — relevance is the only source of why_it_matters
# ---------------------------------------------------------------------------


def test_empty_relevance_is_rejected() -> None:
    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(_base())


def test_uncertainty_does_not_substitute_for_missing_relevance() -> None:
    payload = {
        **_base(),
        "uncertainty": [claim("This remains unverified and should not be relied on.")],
    }

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)


def test_next_question_does_not_substitute_for_missing_relevance() -> None:
    payload = {
        **_base(),
        "next_question": [claim("Check whether the second claim is corroborated.")],
    }

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)


def test_conclusion_does_not_substitute_for_missing_relevance() -> None:
    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(_base())


def test_fact_conclusion_with_one_relevance_inference_is_accepted() -> None:
    payload = {
        "core_conclusion": [claim("A stated fact about the content.", "fact")],
        "key_evidence": [claim("The available evidence supports this.", "fact")],
        "relevance_to_user": [claim("This changes how you should plan the review.")],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    assert {point.kind.value for point in content.core_points} == {"fact"}
    assert content.why_it_matters.kind.value == "inference"


def test_why_it_matters_text_equals_relevance_first_claim() -> None:
    relevance = "This changes how you should plan the review."
    payload = {
        **_base(),
        "relevance_to_user": [claim(relevance)],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    assert content.why_it_matters.text == relevance


def test_why_it_matters_uses_first_relevance_not_another_role() -> None:
    payload = {
        **_base(),
        "uncertainty": [claim("Uncertainty text must not back why_it_matters.")],
        "next_question": [claim("Next question text must not back why_it_matters.")],
        "relevance_to_user": [
            claim("Relevance one is the only valid source."),
            claim("Relevance two is a later claim."),
        ],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    assert content.why_it_matters.text == "Relevance one is the only valid source."


# ---------------------------------------------------------------------------
# FIX 2 — canonical text at admission
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [
        "core_conclusion",
        "key_evidence",
        "uncertainty",
        "relevance_to_user",
        "next_question",
    ],
)
def test_every_role_canonicalizes_whitespace_at_admission(role: str) -> None:
    kind = "fact" if role == "key_evidence" else "inference"
    payload = {
        **_base(),
        "relevance_to_user": [claim("Fallback relevance that must be replaced.")],
        role: [claim("  Padded claim text  ", kind)],
    }
    if role == "relevance_to_user":
        payload = {**_base(), role: [claim("  Padded claim text  ", kind)]}

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    stored = getattr(parsed, role)

    assert stored[0].text == "Padded claim text"


def test_whitespace_only_text_is_rejected() -> None:
    payload = {**_base(), "relevance_to_user": [claim("      ")]}

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)


def test_max_length_conclusion_wrapped_in_whitespace_is_accepted() -> None:
    payload = {
        **_base(),
        "core_conclusion": [claim(" " + "x" * MAX_CORE_CONCLUSION_CHARS + " ")],
        "relevance_to_user": [claim("This changes how you should plan the review.")],
    }

    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)

    # Length is evaluated on the canonical value, not the padded raw text.
    assert len(parsed.core_conclusion[0].text) == MAX_CORE_CONCLUSION_CHARS


def test_over_max_length_canonical_conclusion_is_rejected() -> None:
    payload = {
        **_base(),
        "core_conclusion": [claim("x" * (MAX_CORE_CONCLUSION_CHARS + 1))],
        "relevance_to_user": [claim("This changes how you should plan the review.")],
    }

    with pytest.raises(ValueError):
        DeepAnalysisPhase1AModelOutput.model_validate(payload)


def test_whitespace_text_survives_persistence_restart_and_projection(
    tmp_path: Path,
) -> None:
    payload = {
        "core_conclusion": [claim("  The content shows that drift accumulates.  ")],
        "key_evidence": [claim("  The evidence supports the drift claim.  ", "fact")],
        "uncertainty": [claim("  This remains unverified right now.  ")],
        "relevance_to_user": [
            claim("  This changes how you should plan the review.  "),
            claim("\t This changes how you measure the outcome.\t"),
        ],
        "next_question": [claim("  Check whether another source agrees.  ")],
    }
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)

    # The admitted model object already holds canonical text.
    admitted = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    canonical = {
        role: [c.text for c in getattr(admitted, role)]
        for role in (
            "core_conclusion",
            "key_evidence",
            "uncertainty",
            "relevance_to_user",
            "next_question",
        )
    }

    _service(repository, payload=payload).run(content_id=VIDEO_ID)
    after = _service(SQLiteStateRepository(database)).read(content_id=VIDEO_ID)
    assert after is not None

    for role, texts in canonical.items():
        public_role = role.upper()
        projected = [c.text for c in after.roles if c.role == public_role]
        # Identical accepted text, no whitespace transformation at any stage.
        assert projected == texts, role
        for text in projected:
            assert text == text.strip()


def test_multiple_claims_preserve_count_order_and_role(tmp_path: Path) -> None:
    payload = {
        **_base(),
        "relevance_to_user": [
            claim("  Relevance first is concrete.  "),
            claim("  Relevance second is concrete.  "),
            claim("  Relevance third is concrete.  "),
        ],
    }
    database = tmp_path / "state.sqlite"
    repository = SQLiteStateRepository(database)
    repository.initialize(now=NOW)
    _seed(repository)
    _service(repository, payload=payload).run(content_id=VIDEO_ID)

    after = _service(SQLiteStateRepository(database)).read(content_id=VIDEO_ID)
    assert after is not None
    relevance = [c.text for c in after.roles if c.role == "RELEVANCE_TO_USER"]

    assert relevance == [
        "Relevance first is concrete.",
        "Relevance second is concrete.",
        "Relevance third is concrete.",
    ]


def test_projection_does_not_transform_accepted_text() -> None:
    """A canonical value containing internal spacing stays exactly as accepted."""

    payload = {
        **_base(),
        "relevance_to_user": [claim("  A  B\tC  ")],
    }
    parsed = DeepAnalysisPhase1AModelOutput.model_validate(payload)
    content = map_phase_1a_output_to_knowledge_content(
        parsed, summary_evidence_ids=(REF,)
    )

    # Only outer whitespace is canonicalized; internal characters are untouched.
    assert content.product_opportunities[0].text == "A  B\tC"
