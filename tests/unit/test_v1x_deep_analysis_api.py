"""V1.x Phase 1A: Deep Analysis HTTP surface.

Pins that Deep Analysis is reachable as a real Content-level action, that it is
distinct from Summary, that it exposes no durable citation in Phase 1A, and that
it never claims qualification or consent it does not have.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

import pytest

from youtube_intel.deep_analysis_service import (
    DeepAnalysisCapability,
    DeepAnalysisService,
    build_local_ollama_route,
)
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
    VideoMetadata,
)
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 1, tzinfo=UTC)
VIDEO_ID = "video-api-da"


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _scoring_read(_video_id: str) -> VerifiedScoringRead:
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
        video_id=VIDEO_ID,
        scoring_job_id="job-api-da",
        scoring_success_provenance="PRIMARY",
    )


def _content() -> dict[str, object]:
    def point(text: str, kind: str) -> dict[str, object]:
        return {"text": text, "kind": kind, "evidence_ids": ["e1"]}

    return {
        "one_sentence_summary": "The API fixture states one clear conclusion.",
        "summary_evidence_ids": ["e1"],
        "why_it_matters": point("The API fixture explains why it matters.", "inference"),
        "core_points": [point("The API fixture asserts one core fact.", "fact")],
        "key_facts": [point("The API fixture records one key fact.", "fact")],
        "key_arguments": [point("The API fixture advances one argument.", "inference")],
        "counterpoints": [point("The API fixture notes one counterpoint.", "inference")],
        "risks": [point("The API fixture names one risk.", "inference")],
        "actionable_directions": [
            point("The API fixture suggests one direction.", "recommendation")
        ],
        "hypotheses_to_validate": [
            point("The API fixture leaves one hypothesis open.", "inference")
        ],
        "knowledge_graph": {"topics": ["workflow"]},
    }


class _VerifiedEvidence:
    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self.excerpt = "A verified transcript excerpt for the API fixture."
        self.excerpt_hash = "d" * 64


def _transport(request: dict[str, object], timeout_seconds: float) -> object:
    del request, timeout_seconds
    return {
        "model": "qwen2.5-coder:7b",
        "done": True,
        "done_reason": "stop",
        "message": {"content": json.dumps(_content(), ensure_ascii=False)},
    }


def _app(tmp_path: Path, *, qualified: bool = True) -> LocalApiApplication:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=VIDEO_ID,
            channel_id="UC1234567890123456789012",
            channel_name="Fixture channel",
            title="Fixture title",
            description="Fixture only.",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=datetime(2026, 9, 1, tzinfo=UTC),
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.save_global_output_language(output_language="en", now=NOW)
    deep_analysis = DeepAnalysisService(
        repository=repository,
        capability=DeepAnalysisCapability(
            (build_local_ollama_route(transport=_transport),) if qualified else ()
        ),
        scoring_reader=_scoring_read,
        transcript_reader=lambda _video_id: None,
        evidence_reader=lambda _video_id: ("e1",),
        evidence_text_reader=lambda evidence_id: _VerifiedEvidence(evidence_id),
        now=lambda: NOW,
    )
    return LocalApiApplication(
        repository,
        ProductOrchestrationService(repository, now=lambda: NOW),
        data_root=tmp_path / "data",
        vault_root=tmp_path / "vault",
        now=lambda: NOW,
        deep_analysis_service=deep_analysis,
    )


def test_capability_route_reports_no_route_when_unqualified(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, qualified=False)

    status, payload = app.handle("GET", "/api/v1/deep-analysis/capability")

    assert status == HTTPStatus.OK
    assert payload["capability"]["qualified"] is False
    assert payload["capability"]["routes"] == []
    assert "is currently qualified" in payload["capability"]["reason"]


def test_deep_analysis_status_is_not_requested_before_a_run(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    status, payload = app.handle("GET", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    assert status == HTTPStatus.OK
    assert payload["deep_analysis"]["status"]["availability"] == "NOT_REQUESTED"
    assert payload["deep_analysis"]["result"] is None


def test_deep_analysis_run_returns_the_five_role_projection(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    status, payload = app.handle(
        "POST", f"/api/v1/videos/{VIDEO_ID}/deep-analysis"
    )

    assert status == HTTPStatus.CREATED
    result = payload["deep_analysis"]["result"]
    roles = {claim["role"] for claim in result["roles"]}
    assert roles == {
        "CORE_CONCLUSION",
        "KEY_EVIDENCE",
        "UNCERTAINTY",
        "RELEVANCE_TO_USER",
        "NEXT_QUESTION",
    }
    assert "RELATION_TO_KNOWLEDGE" not in roles
    assert "KNOWLEDGE_DELTA" not in roles
    # Phase 1A does not present transient refs as durable citations.
    assert result["evidence_citation_status"] == (
        "PENDING_DURABLE_EVIDENCE_CONVERGENCE"
    )
    serialized = json.dumps(result, ensure_ascii=False)
    assert "evidence_ids" not in serialized
    assert "evidence_refs" not in serialized


def test_deep_analysis_result_is_readable_after_the_run(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    app.handle("POST", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    status, payload = app.handle("GET", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    assert status == HTTPStatus.OK
    assert payload["deep_analysis"]["status"]["availability"] == "AVAILABLE"
    assert payload["deep_analysis"]["result"] is not None


def test_deep_analysis_run_is_refused_when_no_route_qualifies(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, qualified=False)

    with pytest.raises(ApiError) as error:
        app.handle("POST", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    assert error.value.status == HTTPStatus.CONFLICT
    assert error.value.code == "DEEP_ANALYSIS_NOT_QUALIFIED"
    # Nothing was written, so no result is offered afterwards.
    _, payload = app.handle("GET", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")
    assert payload["deep_analysis"]["result"] is None


def test_unknown_content_deep_analysis_is_not_found(tmp_path: Path) -> None:
    app = _app(tmp_path)

    with pytest.raises(ApiError) as error:
        app.handle("GET", "/api/v1/videos/does-not-exist/deep-analysis")

    assert error.value.status == HTTPStatus.NOT_FOUND


def test_deep_analysis_run_requires_explicit_consent_keys(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)

    with pytest.raises(ApiError):
        app.handle(
            "POST",
            f"/api/v1/videos/{VIDEO_ID}/deep-analysis",
            b'{"unexpected": true}',
        )


def test_content_list_reports_deep_analysis_without_claiming_qualification(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, qualified=False)

    _, payload = app.handle("GET", "/api/v1/videos")

    video = next(
        item for item in payload["videos"] if item["video_id"] == VIDEO_ID
    )
    assert video["deep_analysis"]["status"] == "NOT_QUALIFIED"
    assert video["deep_analysis"]["reason"]


def test_content_detail_keeps_summary_and_deep_analysis_distinct(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    app.handle("POST", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    _, payload = app.handle("GET", f"/api/v1/videos/{VIDEO_ID}")

    # Summary is a separate capability with its own authority.
    assert "note" in payload
    assert payload["video"]["deep_analysis"]["status"] == "AVAILABLE"


def test_api_exposes_stable_reason_code_for_localization(tmp_path: Path) -> None:
    app = _app(tmp_path, qualified=False)

    _, payload = app.handle("GET", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    status = payload["deep_analysis"]["status"]
    assert status["reason_code"] == "NO_QUALIFIED_MODEL"
    assert status["availability"] == "NOT_QUALIFIED"
    # The English prose remains available as a developer diagnostic only.
    assert isinstance(status["reason"], str)


def test_api_never_exposes_candidate_refs_or_citations(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app.handle("POST", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    _, payload = app.handle("GET", f"/api/v1/videos/{VIDEO_ID}/deep-analysis")

    result = payload["deep_analysis"]["result"]
    serialized = json.dumps(result, ensure_ascii=False)
    # No Evidence identifier may be exposed at all: the candidate ref must not
    # appear as a value, and no citation field may exist.
    assert '"e1"' not in serialized
    assert "evidence_ids" not in serialized
    assert "evidence_refs" not in serialized
    assert "evidence_id" not in serialized
    assert result["evidence_citation_status"] == (
        "PENDING_DURABLE_EVIDENCE_CONVERGENCE"
    )
