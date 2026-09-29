"""G — regression harness for the confirmed Summary P1 failure class.

The original M13 Summary P1 was a single real incident. The model was handed a
structural Summary schema that *required* it to author an authoritative Evidence
excerpt, and on one real 44-second video it returned a mostly fabricated quote.
The response was well-formed JSON and satisfied the persisted ``AnalysisResult``
contract, so it failed only at the last gate:

    JSON_VALID
    DOMAIN_VALID
    GROUNDING_INVALID

Recorded incident identity (public content only; no raw model output is
retained anywhere in this repository):

    video_id            ausLKMojXaY
    channel             3Blue1Brown
    title               The Phone Number puzzle
    canonical sha256    0f31bca10826dd69b231b61a5944006f92eff43c699258fc21df69f92d440490
    historical request  149866fc30d53279a7352c83e607b51a7fd25df1a8eace5581bc603a7651fedc
    failure class       JSON_VALID / DOMAIN_VALID / GROUNDING_INVALID

The regression does **not** retain or replay that raw response. It represents
the failure *mechanism* — a model that tries to author authoritative Evidence
text — and proves the ``analysis-prompt-v5`` path cannot recreate it:

    the model selects refs, the backend owns every excerpt, and any attempt to
    emit an excerpt field fails closed instead of being grounded, ignored, or
    persisted.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from youtube_intel.analysis import (
    SUMMARY_DRAFT_PROMPT_VERSION,
    AnalysisJobContext,
    AnalysisPolicyError,
    CloudCallBudget,
    KnownLocalSummaryResponseError,
    RepositoryBackedAnalysisService,
    build_analysis_input,
    build_summary_evidence_registry,
    summary_draft_request,
)
from youtube_intel.config import LocalAnalysisSettings
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisResult,
    Availability,
    ErrorCode,
    EvidenceSource,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    JobType,
    ProviderCallStatus,
    ProviderDispatchStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
)
from youtube_intel.summary_draft import (
    SUMMARY_DRAFT_SCHEMA_VERSION,
    SummaryDraft,
    SummaryDraftError,
    SummaryDraftPoint,
    parse_summary_draft,
)

# --- recorded incident identity -------------------------------------------

HISTORICAL_VIDEO_ID = "ausLKMojXaY"
HISTORICAL_CHANNEL = "3Blue1Brown"
HISTORICAL_TITLE = "The Phone Number puzzle"
HISTORICAL_TRANSCRIPT_SHA256 = (
    "0f31bca10826dd69b231b61a5944006f92eff43c699258fc21df69f92d440490"
)
HISTORICAL_REQUEST_HASH = (
    "149866fc30d53279a7352c83e607b51a7fd25df1a8eace5581bc603a7651fedc"
)
HISTORICAL_FAILURE_CLASS = ("JSON_VALID", "DOMAIN_VALID", "GROUNDING_INVALID")

#: A synthesized stand-in for the historical failure shape. The real transcript
#: body and the real provider envelope are deliberately not committed.
FABRICATED_EXCERPT = (
    "and the resulting product will contain only ones and zeros forever and ever"
)

#: A synthesized transcript with the same shape as the original Content. The real
#: canonical body is not committed; only its recorded identity is.
CUE_TEXTS = (
    "Here is a surprising fact about phone numbers and what follows next.",
    "If you take your own phone number there is a trick that always works.",
    "The trick relies on finding a multiplier made only of ones and zeros.",
    "Brute force search finds the multiplier but understanding is much faster.",
)

TRANSCRIPT_TEXT = "canonical transcript for the regression harness"


class _Provider:
    """A provider that records what the live service handed it."""

    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls = 0
        self.seen: list[object] = []
        self._raw: str | None = None
        self._request_hash: str | None = None

    def summarize(self, analysis_input: object) -> SummaryDraft:
        self.calls += 1
        self.seen.append(analysis_input)
        self._request_hash = getattr(analysis_input, "request_hash")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        self._raw = json.dumps({"model": "qwen3:8b", "done": True})
        return response  # type: ignore[return-value]

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert self._request_hash == request_hash
        assert self._raw is not None
        return self._raw


def _metadata() -> VideoMetadata:
    return VideoMetadata(
        video_id=HISTORICAL_VIDEO_ID,
        channel_id="UCYO_jab_esuFRV4b17AJtAw",
        channel_name=HISTORICAL_CHANNEL,
        title=HISTORICAL_TITLE,
        description="Part of a monthly series of puzzles.",
        source_url=f"https://www.youtube.com/watch?v={HISTORICAL_VIDEO_ID}",
        published_at=datetime(2026, 9, 20, tzinfo=UTC),
        duration_seconds=44,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _settings() -> LocalAnalysisSettings:
    return LocalAnalysisSettings(
        model="qwen3:8b", expected_model_digest="sha256:" + "1" * 64
    )


def _seed(tmp_path: Path) -> SQLiteStateRepository:
    now = datetime.now(UTC)
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=now)
    repository.upsert_video_metadata(_metadata(), pipeline_version="pipeline-v1", now=now)
    for before, after in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
    ):
        assert repository.advance_pipeline(
            HISTORICAL_VIDEO_ID,
            expected_status=before,
            target_status=after,
            pipeline_version="pipeline-v1",
            now=now,
        )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="artifact-1",
            artifact_key=f"transcript/{HISTORICAL_VIDEO_ID}",
            video_id=HISTORICAL_VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{HISTORICAL_VIDEO_ID}/canonical.txt",
            content_hash=sha256(TRANSCRIPT_TEXT.encode()).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=now,
    )
    repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=HISTORICAL_VIDEO_ID,
            canonical_artifact_id="artifact-1",
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=index * 1000,
                    end_ms=(index + 1) * 1000,
                    text=text,
                )
                for index, text in enumerate(CUE_TEXTS)
            ),
        ),
        now=now,
    )
    assert repository.advance_pipeline(
        HISTORICAL_VIDEO_ID,
        expected_status=PipelineStatus.TRANSCRIPT_READY,
        target_status=PipelineStatus.SCORED,
        pipeline_version="pipeline-v1",
        now=now,
    )
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET should_summarize = 1 WHERE video_id = ?",
            (HISTORICAL_VIDEO_ID,),
        )
    finally:
        connection.close()
    repository.create_job(
        job_id="analysis-job",
        scope_key=f"video:{HISTORICAL_VIDEO_ID}:ANALYSIS",
        video_id=HISTORICAL_VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.ANALYSIS,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    assert repository.claim_next_job(
        owner="worker", lease_until=now + timedelta(minutes=10), now=now
    )
    return repository


def _service(
    repository: SQLiteStateRepository, provider: object, tmp_path: Path
) -> RepositoryBackedAnalysisService:
    return RepositoryBackedAnalysisService(
        provider=provider,
        settings=_settings(),
        repository=repository,
        context=AnalysisJobContext("analysis-job", "worker", "pipeline-v1"),
        artifact_root=tmp_path / "data",
        credential_resolver=object(),
        budget=CloudCallBudget(limit=5),
    )


def _analyze(service: RepositoryBackedAnalysisService) -> object:
    return service.analyze(
        video=_metadata(),
        transcript_text=TRANSCRIPT_TEXT,
        language="en",
        output_language="zh-CN",
    )


def _registry(repository: SQLiteStateRepository):
    verified = repository.get_verified_timed_transcript(video_id=HISTORICAL_VIDEO_ID)
    assert verified is not None
    record = repository.get_video(HISTORICAL_VIDEO_ID)
    return build_summary_evidence_registry(
        verified=verified,
        video_id=HISTORICAL_VIDEO_ID,
        title=record.title or "",
        channel_name=record.channel_name or "",
        description=record.description or "",
        transcript_text=TRANSCRIPT_TEXT,
    )


def _refs_by_source(repository: SQLiteStateRepository) -> dict[EvidenceSource, str]:
    return {
        source: next(
            candidate.ref
            for candidate in _registry(repository).candidates
            if candidate.source is source
        )
        for source in (EvidenceSource.TITLE, EvidenceSource.TRANSCRIPT_SAMPLE)
    }


def _draft(*refs: str) -> SummaryDraft:
    return SummaryDraft(
        one_sentence_summary="摘要",
        core_points=(
            SummaryDraftPoint(text="要点", kind="fact", evidence_refs=refs),
        ),
        keywords=("puzzle",),
    )


def _fabricated_v4_response(ref: str) -> str:
    """A synthesized v4-shaped response of the historical failure class.

    It is valid JSON and it would satisfy the persisted ``AnalysisResult``
    contract, so the *only* gate that could reject it was grounding. The excerpt
    below is deliberately not a substring of any source.
    """

    return json.dumps(
        {
            "one_sentence_summary": "The video explains a phone number puzzle.",
            "core_points": [
                {
                    "text": "A multiplier of only ones and zeros always exists.",
                    "kind": "fact",
                    "evidence_ids": [ref],
                }
            ],
            "keywords": ["phone number", "puzzle"],
            "evidence": [
                {
                    "evidence_id": ref,
                    "source": "transcript_sample",
                    "excerpt": FABRICATED_EXCERPT,
                }
            ],
        }
    )


# --- the failure class is structurally unreachable now ---------------------


def test_historical_failure_shape_is_rejected_before_it_can_be_grounded(
    tmp_path: Path,
) -> None:
    """``GROUNDING_INVALID`` can no longer be the outcome.

    The v4 shape is valid JSON and would be domain-valid, so the historical
    classification was decided by the grounding gate. The v5 contract has no
    ``evidence``/``excerpt`` field at all, so the same response becomes a hard
    contract rejection and never reaches grounding at all.
    """

    repository = _seed(tmp_path)
    ref = _refs_by_source(repository)[EvidenceSource.TRANSCRIPT_SAMPLE]
    raw = _fabricated_v4_response(ref)

    # The response is otherwise perfectly well formed.
    payload = json.loads(raw)
    assert payload["one_sentence_summary"]
    assert payload["evidence"][0]["excerpt"] not in TRANSCRIPT_TEXT
    assert payload["evidence"][0]["excerpt"] not in "".join(CUE_TEXTS)

    with pytest.raises(SummaryDraftError) as rejection:
        parse_summary_draft(raw)
    assert "author authoritative Evidence text" in str(rejection.value)

    # The live service records it as a known bad response, not a grounding
    # pass/fail decision, and never marks the dispatch ambiguous.
    ambiguous: list[str] = []
    known: list[str] = []
    real_ambiguous = repository.mark_provider_dispatch_ambiguous
    real_known = repository.record_provider_dispatch_known_failure
    repository.mark_provider_dispatch_ambiguous = (  # type: ignore[method-assign]
        lambda *a, _inner=real_ambiguous, **k: (
            ambiguous.append("ambiguous"), _inner(*a, **k)
        )[1]
    )
    repository.record_provider_dispatch_known_failure = (  # type: ignore[method-assign]
        lambda *a, _inner=real_known, **k: (
            known.append("known"), _inner(*a, **k)
        )[1]
    )
    provider = _Provider(
        [
            KnownLocalSummaryResponseError(
                f"Summary draft contract rejected: {rejection.value}"
            )
        ]
    )

    with pytest.raises(AnalysisPolicyError) as raised:
        _analyze(_service(repository, provider, tmp_path))

    assert raised.value.error.code is ErrorCode.INVALID_RESPONSE
    assert raised.value.error.retryable is False
    assert ambiguous == []
    assert known == ["known"]
    assert repository.list_summary_promoted_evidence_ids(HISTORICAL_VIDEO_ID) == ()


def test_the_same_selection_now_succeeds_with_backend_owned_excerpts(
    tmp_path: Path,
) -> None:
    """The historical selection, expressed as a ref, produces a trusted Summary."""

    repository = _seed(tmp_path)
    ref = _refs_by_source(repository)[EvidenceSource.TRANSCRIPT_SAMPLE]
    provider = _Provider([_draft(ref)])

    outcome = _analyze(_service(repository, provider, tmp_path))

    assert isinstance(outcome, AnalysisCompleted)
    issued = _registry(repository).by_ref()[ref]
    # The excerpt is the backend's text, byte for byte.
    assert outcome.result.evidence[0].excerpt == issued.text
    assert FABRICATED_EXCERPT not in outcome.result.evidence[0].excerpt
    # The model's own selection was honoured exactly.
    assert outcome.result.core_points[0].evidence_ids == (ref,)


def test_no_model_authored_excerpt_can_reach_a_persisted_artifact(
    tmp_path: Path,
) -> None:
    """Every persisted excerpt is a member of the issued candidate set."""

    repository = _seed(tmp_path)
    registry = _registry(repository)
    provider = _Provider(
        [
            _draft(*tuple(candidate.ref for candidate in registry.candidates))
        ]
    )

    outcome = _analyze(_service(repository, provider, tmp_path))
    assert isinstance(outcome, AnalysisCompleted)
    issued = {candidate.text for candidate in registry.candidates}
    for evidence in outcome.result.evidence:
        assert evidence.excerpt in issued

    artifact = repository.get_artifact_by_key(
        f"analysis/{outcome.result.request_hash}/structured"
    )
    assert artifact is not None
    body = (tmp_path / "data" / artifact.relative_path).read_bytes()
    assert artifact.content_hash == sha256(body).hexdigest()
    persisted = AnalysisResult.model_validate_json(body)
    for evidence in persisted.evidence:
        assert evidence.excerpt in issued
    assert FABRICATED_EXCERPT.encode() not in body
    # A point carries only a ref; the excerpt lives only on backend Evidence.
    assert all(point.evidence_ids for point in persisted.core_points)
    assert "excerpt" not in persisted.core_points[0].model_dump_json()


def test_model_selects_refs_and_the_backend_owns_every_excerpt(
    tmp_path: Path,
) -> None:
    """The repaired contract in one assertion, driven through the live service."""

    repository = _seed(tmp_path)
    registry = _registry(repository)
    ref = _refs_by_source(repository)[EvidenceSource.TRANSCRIPT_SAMPLE]
    provider = _Provider([_draft(ref)])

    outcome = _analyze(_service(repository, provider, tmp_path))

    assert isinstance(outcome, AnalysisCompleted)
    offer = getattr(provider.seen[0], "trusted_evidence")
    assert offer is not None
    # The model received refs and trusted text, and no range authority.
    assert [candidate.ref for candidate in offer.candidates] == [
        candidate.ref for candidate in registry.candidates
    ]
    assert SUMMARY_DRAFT_SCHEMA_VERSION == "summary-draft-v1"
    request_schema = summary_draft_request(provider.seen[0]).schema
    assert "excerpt" not in json.dumps(request_schema)
    # The backend resolved the excerpt it never received from the model.
    promoted = repository.list_summary_promoted_evidence_ids(HISTORICAL_VIDEO_ID)
    assert len(promoted) == 1
    resolved = repository.resolve_verified_evidence_text(promoted[0])
    assert resolved is not None
    assert resolved.excerpt == registry.by_ref()[ref].text
    call = repository.get_provider_call(outcome.result.request_hash)
    assert call is not None
    assert call.status is ProviderCallStatus.SUCCEEDED
    dispatch = repository.get_provider_dispatch(outcome.result.request_hash)
    assert dispatch is not None
    assert dispatch.status is ProviderDispatchStatus.SUCCESS_DURABLY_RECORDED


def test_historical_request_identity_can_never_be_reused(
    tmp_path: Path,
) -> None:
    """The pre-cutover cache entry is not reachable from the v5 request."""

    repository = _seed(tmp_path)
    common = dict(
        video=_metadata(),
        transcript_text=TRANSCRIPT_TEXT,
        language="en",
        output_language="zh-CN",
        settings=_settings(),
        provider="ollama",
        operation="local-analysis",
    )
    v5 = build_analysis_input(
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        registry=_registry(repository),
        **common,
    )
    legacy = build_analysis_input(prompt_version="analysis-prompt-v4", **common)

    assert v5.request_hash != legacy.request_hash
    assert v5.request_hash != HISTORICAL_REQUEST_HASH
    assert legacy.prompt_version == "analysis-prompt-v4"


def test_incident_identity_is_recorded_without_retained_raw_model_output() -> None:
    """The harness represents the mechanism, not a captured provider envelope.

    Repository policy for this goal: do not commit the retained historical raw
    model response. This asserts the repository holds only the incident
    *identity* — the public video/transcript/request hashes and the failure
    classification — and no recorded provider envelope keyed to it.
    """

    assert HISTORICAL_FAILURE_CLASS == (
        "JSON_VALID",
        "DOMAIN_VALID",
        "GROUNDING_INVALID",
    )
    assert len(HISTORICAL_TRANSCRIPT_SHA256) == 64
    assert len(HISTORICAL_REQUEST_HASH) == 64
    assert FABRICATED_EXCERPT not in TRANSCRIPT_TEXT
    assert FABRICATED_EXCERPT not in "".join(CUE_TEXTS)

    tracked = subprocess.run(
        ["git", "ls-files", "src", "tests"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    # No tracked artifact under src/ or tests/ is a retained historical
    # provider response for the incident request.
    raw_artifacts = [
        path
        for path in tracked
        if path.endswith(("raw.json", "raw.jsonl", "provider_response.json"))
    ]
    assert raw_artifacts == []
    # The incident request hash appears only as an identity constant here, never
    # inside a recorded response body.
    holders = {
        path
        for path in tracked
        if HISTORICAL_REQUEST_HASH
        in Path(path).read_text(encoding="utf-8", errors="ignore")
    }
    assert holders <= {"tests/integration/test_summary_p1_regression_harness.py"}
