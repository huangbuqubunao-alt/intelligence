"""Bounded synthetic qualification harness using the actual durable DA pipeline.

No evaluation promotes a route. Cloud callers must supply separately authorized
execution; this harness has no credential source or paid-call CLI option.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

from youtube_intel.deep_analysis_qualification import (
    QualificationCheck,
    QualificationFixture,
    QualificationRecord,
    qualification_binding,
    qualification_cases,
)
from youtube_intel.deep_analysis_service import (
    DeepAnalysisCapability,
    DeepAnalysisRejected,
    DeepAnalysisRoute,
    DeepAnalysisService,
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
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
)


def _seed(
    root: Path, fixture: QualificationFixture, language: str, now: datetime
) -> SQLiteStateRepository:
    root.mkdir(parents=True, exist_ok=True)
    repository = SQLiteStateRepository(root / "state.sqlite3")
    repository.initialize(now=now)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=fixture.case_id,
            channel_id="qualification-synthetic",
            channel_name="Synthetic source",
            title="Guaranteed profit"
            if fixture.case_id == "metadata-trap"
            else "Synthetic qualification source",
            description="Synthetic data only",
            source_url=f"https://www.youtube.com/watch?v={fixture.case_id}",
            published_at=now,
            duration_seconds=60,
            default_language=fixture.source_language,
            available_languages=(fixture.source_language,),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="qualification-fixture-v1",
        now=now,
    )
    text = "".join(fixture.cues)
    directory = root / "data" / "transcripts" / fixture.case_id
    directory.mkdir(parents=True)
    (directory / "canonical.txt").write_text(text)
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="qualification-transcript",
            artifact_key="qualification/transcript",
            video_id=fixture.case_id,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{fixture.case_id}/canonical.txt",
            content_hash=sha256(text.encode()).hexdigest(),
            provider="synthetic-fixture",
            model=None,
            producer_version="qualification-fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=now,
    )
    repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=fixture.case_id,
            canonical_artifact_id="qualification-transcript",
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=i * 1000, end_ms=(i + 1) * 1000, text=cue
                )
                for i, cue in enumerate(fixture.cues)
            ),
        ),
        now=now,
    )
    repository.save_global_output_language(output_language=language, now=now)
    return repository


def _scoring(video_id: str, now: datetime) -> VerifiedScoringRead:
    return VerifiedScoringRead(
        video_id=video_id,
        scoring_job_id="synthetic-scoring",
        scoring_success_provenance="PRIMARY",
        scoring_outcome=ScoringOutcome(
            result=ScoreResult(
                schema_version="score-result-v2",
                score=8,
                reason="This fixture provides a concrete useful explanation of the score.",
                topics=("qualification",),
                should_summarize=True,
                provider="fixture",
                model="fixture",
                prompt_version="fixture-v1",
                request_hash="a" * 64,
                output_language="en",
            ),
            decision=ScoringDecision(
                threshold=7, final_should_summarize=True, model_disagrees=False
            ),
            call=ProviderCallMetadata(
                provider="fixture", model="fixture", started_at=now, finished_at=now
            ),
        ),
    )


def evaluate_route(
    *,
    route: DeepAnalysisRoute,
    root: Path,
    mode: Literal["FIXTURE_CONTRACT", "LIVE_MODEL"],
    stop_on_failure: bool = False,
    cloud_evaluation_authorized: bool = False,
) -> QualificationRecord:
    """One attempt/case; actual five-role validation, Evidence binding and restart.

    Evaluation is a nonproduction injection seam. Cloud adapters are provided
    by the caller only after separate paid authorization, never selected here.
    """
    if not route.is_local and mode == "LIVE_MODEL" and not cloud_evaluation_authorized:
        raise ValueError(
            "Live cloud evaluation requires separately authorized paid execution"
        )
    now = datetime.now(UTC)
    checks: list[QualificationCheck] = []
    stopped = False
    for fixture, language in qualification_cases():
        passed, code = False, "NOT_RUN_AFTER_FAILURE"
        if not stopped:
            try:
                directory = root / f"{fixture.case_id}-{language}"
                repository = _seed(directory, fixture, language, now)
                service = DeepAnalysisService(
                    repository=repository,
                    capability=DeepAnalysisCapability((route,)),
                    scoring_reader=lambda video: _scoring(video, now),
                    transcript_reader=lambda **_: SimpleNamespace(
                        language=fixture.source_language
                    ),
                    evidence_reader=lambda _: (),
                    evidence_text_reader=lambda _: None,
                )
                # Exercise the actual preparation, adapter, validation and durable
                # promotion without turning an evaluation into a production grant.
                runtime, prepared, refs = service._prepare(
                    fixture.case_id,
                    route,
                    f"qualification:{fixture.case_id}:{language}",
                )
                if len(refs) < fixture.minimum_selected_candidates:
                    raise ValueError("fixture did not exercise candidate selection")
                response = route.dispatch(prepared_dispatch=prepared)
                result = service._persist_response(
                    route, runtime, prepared, refs, response
                )
                restarted = DeepAnalysisService(
                    repository=SQLiteStateRepository(directory / "state.sqlite3"),
                    capability=DeepAnalysisCapability(),
                    scoring_reader=lambda video: _scoring(video, now),
                    transcript_reader=lambda **_: None,
                    evidence_reader=lambda _: (),
                    evidence_text_reader=lambda _: None,
                )
                read = restarted.read(content_id=fixture.case_id)
                if (
                    read is None
                    or read.as_dict() != result.as_dict()
                    or result.evidence_citation_status != "DURABLE_EVIDENCE_VERIFIED"
                ):
                    raise ValueError("durable restart mismatch")
                roles = {claim.role for claim in result.roles}
                if (
                    not {
                        "CORE_CONCLUSION",
                        "KEY_EVIDENCE",
                        "RELEVANCE_TO_USER",
                        "NEXT_QUESTION",
                    }
                    <= roles
                ):
                    raise ValueError("missing evaluation roles")
                conclusion = " ".join(
                    c.text for c in result.roles if c.role == "CORE_CONCLUSION"
                )
                if not re.search(r"energy|能耗|能源", conclusion, re.I):
                    raise ValueError("source-specific conclusion missing")
                if fixture.uncertainty_required:
                    uncertainty = " ".join(
                        c.text for c in result.roles if c.role == "UNCERTAINTY"
                    )
                    if not re.search(
                        r"uncertain|unresolved|insufficient|preliminary|limited|cannot|not|可能|不足|不确定|未|仅|待",
                        uncertainty,
                        re.I,
                    ):
                        raise ValueError("required uncertainty missing")
                if any(
                    term in conclusion.lower() for term in fixture.forbidden_claim_terms
                ):
                    raise ValueError("unsupported metadata claim")
                passed, code = True, "PASSED_DURABLE_RESTART_AND_EXPECTATIONS"
            except DeepAnalysisRejected as error:
                code = (
                    error.status.reason_code.value
                    if error.status.reason_code
                    else "PRODUCT_CONTRACT_FAILED"
                )
                stopped = stop_on_failure
            except Exception as error:
                failure = getattr(error, "failure", None)
                code = (
                    failure.code.value
                    if failure is not None
                    else "PRODUCT_CONTRACT_OR_EXPECTATION_FAILED"
                )
                stopped = stop_on_failure
        checks.append(
            QualificationCheck(
                case_id=fixture.case_id,
                output_language=language,
                passed=passed,
                reason_code=code,
            )
        )
    return QualificationRecord.create(
        binding=qualification_binding(route),
        mode=mode,
        generated_at=now,
        checks=tuple(checks),
        limitations=(
            "14 bounded synthetic source/language cases; no general reasoning guarantee.",
            "Automated source-specific expectations supplement exact schema, candidate, language and durable-restart checks; semantic review is required before registry activation.",
            "A proposal is not production authority; only a reviewed repository registry record may activate a route.",
        ),
    )
