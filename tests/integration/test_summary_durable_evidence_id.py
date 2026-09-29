"""P0: persisted Summary citations must use durable Evidence identities.

Temporary model-facing candidate refs (``t0-20-…`` / ``mtitle-…``) exist only
across the model interaction boundary.  Before this repair they survived into
the persisted ``AnalysisResult``, the Note V2 evidence references, and the
Obsidian Summary evidence output, where they fail both ``get_evidence`` and
``resolve_verified_evidence_text``.

Frozen invariant proven here:

    Every persisted Summary citation carries the durable
    ``build_evidence_id`` identity that promotion persists, and metadata is
    context that may never be cited as authoritative Evidence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from youtube_intel.analysis import (
    KnownSummaryResponseError,
    build_analysis_input,
    require_trusted_evidence_offer,
    summary_draft_request,
)
from youtube_intel.domain import EvidenceSource
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    Availability,
    LiveStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VideoMetadata,
)
from youtube_intel.summary_draft import (
    SUMMARY_DRAFT_PROMPT_VERSION,
    SUMMARY_DRAFT_SCHEMA_VERSION,
    SummaryDraft,
    SummaryDraftPoint,
)
from youtube_intel.summary_evidence_authority import (
    SUMMARY_EVIDENCE_REF_NOT_CITABLE,
    SummaryEvidenceAuthorityError,
    SummaryEvidenceAuthorityUnavailable,
    SummaryEvidenceRefNotCitable,
    hydrate_summary_evidence,
)
from youtube_intel.summary_evidence_candidates import build_trusted_evidence_registry

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
VIDEO_ID = "ausLKMojXaY"
ARTIFACT_ID = "artifact-p0"
TRANSCRIPT_HASH = "b" * 64
CUE_TEXTS = tuple(f"cue{index} source sentence about the puzzle" for index in range(8))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _verified():
    from youtube_intel.state import VerifiedTimedTranscript, VerifiedTimedTranscriptCue

    return VerifiedTimedTranscript(
        timed_transcript_id="tt-p0",
        video_id=VIDEO_ID,
        canonical_artifact_id=ARTIFACT_ID,
        timed_transcript_hash=TRANSCRIPT_HASH,
        cues=tuple(
            VerifiedTimedTranscriptCue(
                cue_index=index,
                start_ms=index * 1000,
                end_ms=(index + 1) * 1000,
                text=text,
                text_hash=sha256(text.encode()).hexdigest(),
            )
            for index, text in enumerate(CUE_TEXTS)
        ),
    )


def _registry():
    return build_trusted_evidence_registry(
        transcript=_verified(),
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="short description",
        input_identity="a" * 64,
    )


def _transcript_ref() -> str:
    return next(
        c.ref for c in _registry().candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )


def _metadata_ref(source: EvidenceSource = EvidenceSource.TITLE) -> str:
    return next(c.ref for c in _registry().candidates if c.source is source)


def _draft(*refs: str) -> SummaryDraft:
    return SummaryDraft(
        one_sentence_summary="摘要",
        core_points=(SummaryDraftPoint(text="要点", kind="fact", evidence_refs=refs),),
        keywords=("k",),
    )


def _hydrate(draft, **kwargs):
    base = dict(
        video_id=VIDEO_ID,
        canonical_artifact_id=ARTIFACT_ID,
        language="en",
        timed_transcript_id="tt-p0",
        timed_transcript_hash=TRANSCRIPT_HASH,
    )
    base.update(kwargs)
    return hydrate_summary_evidence(draft, _registry(), **base)


def _seed(tmp_path: Path) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=VIDEO_ID,
            channel_id="UC_TEST",
            channel_name="3Blue1Brown",
            title="The Phone Number puzzle",
            description="d",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
            published_at=NOW,
            duration_seconds=44,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.ENDED,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=NOW,
    )
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=ARTIFACT_ID,
            artifact_key=f"transcript/{VIDEO_ID}",
            video_id=VIDEO_ID,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=f"transcripts/{VIDEO_ID}/canonical.txt",
            content_hash=sha256("".join(CUE_TEXTS).encode()).hexdigest(),
            provider="fixture",
            model=None,
            producer_version="fixture-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    repository.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=VIDEO_ID,
            canonical_artifact_id=ARTIFACT_ID,
            cues=tuple(
                TimedTranscriptCueWrite(
                    start_ms=index * 1000,
                    end_ms=(index + 1) * 1000,
                    text=text,
                )
                for index, text in enumerate(CUE_TEXTS)
            ),
        ),
        now=NOW,
    )
    return repository


# --- 1-4: the temporary ref is accepted, then resolved to durable --------


def test_01_temporary_timed_ref_is_accepted_from_the_model() -> None:
    ref = _transcript_ref()
    result = _hydrate(_draft(ref))
    assert result.refs == (ref,)


def test_02_backend_resolves_it_to_the_promoted_durable_id() -> None:
    ref = _transcript_ref()
    result = _hydrate(_draft(ref))
    promotion = result.promotions[0]
    assert result.durable_by_ref[ref] == promotion.evidence_id
    assert promotion.as_evidence_write().evidence_id == promotion.evidence_id
    assert promotion.as_text_binding().evidence_id == promotion.evidence_id


def test_03_and_04_hydrated_evidence_and_points_are_durable() -> None:
    from youtube_intel.analysis import _summary_result_from_draft

    ref = _transcript_ref()
    draft = _draft(ref)
    hydrated = _hydrate(draft)
    result = _summary_result_from_draft(
        draft,
        hydrated.evidence,
        durable_by_ref=hydrated.durable_by_ref,
        provider="ollama",
        model="qwen3:8b",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        request_hash="0" * 64,
    )
    durable = hydrated.promotions[0].evidence_id
    assert result.evidence[0].evidence_id == durable
    assert result.core_points[0].evidence_ids == (durable,)
    assert all(len(eid) == 64 for eid in result.core_points[0].evidence_ids)


# --- 5-6: the persisted ids resolve through the public repository APIs ---


def _hydrate_from_repository(repository: SQLiteStateRepository, *refs: str):
    """Hydrate exactly as production does, from the persisted authority."""

    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="short description",
        input_identity="a" * 64,
    )
    draft = SummaryDraft(
        one_sentence_summary="摘要",
        core_points=(
            SummaryDraftPoint(text="要点", kind="fact", evidence_refs=refs),
        ),
        keywords=("k",),
    )
    return hydrate_summary_evidence(
        draft,
        registry,
        video_id=VIDEO_ID,
        canonical_artifact_id=ARTIFACT_ID,
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    )


def _first_timed_ref(repository: SQLiteStateRepository) -> str:
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="short description",
        input_identity="a" * 64,
    )
    return next(
        c.ref for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )


def test_05_and_06_persisted_ids_resolve_after_promotion(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    ref = _first_timed_ref(repository)
    hydrated = _hydrate_from_repository(repository, ref)
    durable = hydrated.promotions[0].evidence_id
    repository.promote_summary_evidence(
        hydrated.promotions[0].as_evidence_write(),
        hydrated.promotions[0].as_text_binding(),
        now=NOW,
    )
    record = repository.get_evidence(durable)
    assert record is not None
    assert record.evidence_id == durable
    verified_text = repository.resolve_verified_evidence_text(durable)
    assert verified_text is not None
    assert verified_text.excerpt == hydrated.promotions[0].excerpt
    # The temporary ref still resolves to nothing.  That is the whole defect.
    assert repository.get_evidence(ref) is None
    assert repository.resolve_verified_evidence_text(ref) is None


def test_05b_persisted_ids_resolve_after_repository_restart(tmp_path: Path) -> None:
    first = _seed(tmp_path)
    ref = _first_timed_ref(first)
    hydrated = _hydrate_from_repository(first, ref)
    durable = hydrated.promotions[0].evidence_id
    first.promote_summary_evidence(
        hydrated.promotions[0].as_evidence_write(),
        hydrated.promotions[0].as_text_binding(),
        now=NOW,
    )
    del first
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    reopened.initialize(now=NOW)
    assert reopened.get_evidence(durable) is not None
    assert reopened.resolve_verified_evidence_text(durable) is not None


# --- 7-9: no temporary ref survives into any user-visible surface --------


def _serialized_result():
    from youtube_intel.analysis import _summary_result_from_draft

    ref = _transcript_ref()
    draft = _draft(ref)
    hydrated = _hydrate(draft)
    result = _summary_result_from_draft(
        draft,
        hydrated.evidence,
        durable_by_ref=hydrated.durable_by_ref,
        provider="ollama",
        model="qwen3:8b",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        request_hash="0" * 64,
    )
    return result, hydrated, ref


def test_07_no_temporary_ref_in_the_serialized_structured_artifact() -> None:
    result, _hydrated, ref = _serialized_result()
    body = result.model_dump_json().encode()
    assert ref.encode() not in body
    for candidate in _registry().candidates:
        assert candidate.ref.encode() not in body


def test_08_summary_evidence_projection_carries_durable_ids() -> None:
    """The Summary UI surface is a pure projection of AnalysisResult.evidence."""

    result, _hydrated, ref = _serialized_result()
    projected = [
        {
            "evidence_id": item.evidence_id,
            "source": item.source.value,
            "excerpt": item.excerpt,
            "start_seconds": item.start_seconds,
            "end_seconds": item.end_seconds,
        }
        for item in result.evidence
    ]
    assert all(len(item["evidence_id"]) == 64 for item in projected)
    assert ref not in json.dumps(projected)
    # And the ids the Summary shows are exactly the ids Evidence shows.
    assert {item["evidence_id"] for item in projected} == {
        item.evidence_id for item in result.evidence
    }


def test_09_obsidian_evidence_output_carries_durable_ids(tmp_path: Path) -> None:
    """The Obsidian Summary note renders AnalysisResult.evidence verbatim."""

    from youtube_intel.domain import (
        AnalysisCompleted,
        EvidenceExcerpt,
        ProviderCallMetadata,
    )
    from youtube_intel.notes import render_video_note

    result, _hydrated, ref = _serialized_result()
    rendered = render_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=AnalysisCompleted(
            result=result,
            call=ProviderCallMetadata(
                provider="ollama",
                model="qwen3:8b",
                started_at=NOW,
                finished_at=NOW,
            ),
        ),
        processed_at=NOW,
        pipeline_version="pipeline-v1",
    )
    assert ref not in rendered.content
    for item in result.evidence:
        assert item.evidence_id in rendered.content
    assert isinstance(result.evidence[0], EvidenceExcerpt)
    # The Obsidian note and the Summary surface agree on identity.
    assert result.evidence[0].evidence_id in rendered.content


def _video():
    from youtube_intel.domain import VideoMetadata as VM

    return VM(
        video_id=VIDEO_ID,
        channel_id="UC_TEST",
        channel_name="3Blue1Brown",
        title="The Phone Number puzzle",
        description="d",
        source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
        published_at=NOW,
        duration_seconds=44,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.ENDED,
        availability=Availability.PUBLIC,
    )


def _transcript():
    from youtube_intel.domain import (
        SubtitleFormat,
        TranscriptArtifact,
        TranscriptSourceType,
    )

    return TranscriptArtifact(
        video_id=VIDEO_ID,
        language="en",
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="en",
        source_format=SubtitleFormat.VTT,
        text_path=f"transcripts/{VIDEO_ID}.txt",
        timed_text_path=f"transcripts/{VIDEO_ID}.vtt",
        source_content_hash="a" * 64,
        source_byte_count=100,
        content_hash="c" * 64,
        char_count=100,
        segment_count=3,
        normalization_version="subtitle-normalization-v1",
        provider="fixture",
        created_at=NOW,
    )


def _scoring():
    from youtube_intel.domain import (
        ProviderCallMetadata,
        ScoreResult,
        ScoringDecision,
        ScoringOutcome,
    )

    return ScoringOutcome(
        result=ScoreResult(
            schema_version="score-result-v2",
            score=8.5,
            reason="This insight directly supports product strategy.",
            topics=("product", "strategy"),
            should_summarize=True,
            provider="fixture-scoring",
            model="fixture-model",
            prompt_version="scoring-prompt-v2",
            request_hash="c" * 64,
            output_language="en",
        ),
        decision=ScoringDecision(
            threshold=7.0, final_should_summarize=True, model_disagrees=False
        ),
        call=ProviderCallMetadata(
            provider="fixture-scoring",
            model="fixture-model",
            started_at=NOW,
            finished_at=NOW,
        ),
    )


# --- 10-13: metadata is context, never a citation ----------------------


def test_10_metadata_is_never_offered_as_a_citation_target() -> None:
    """Metadata must not be offered as a ref the backend would have to refuse."""

    offer = _registry().offer()
    refs = {candidate.ref for candidate in offer.candidates}
    assert _metadata_ref() not in refs
    assert _metadata_ref(EvidenceSource.CHANNEL_NAME) not in refs
    assert _metadata_ref(EvidenceSource.DESCRIPTION) not in refs
    assert _transcript_ref() in refs
    # Metadata text is still available to inform generation.
    assert all(candidate.text for candidate in offer.candidates)


def test_10b_metadata_still_reaches_the_model_as_task_context() -> None:
    from youtube_intel.config import LocalAnalysisSettings
    from youtube_intel.domain import TrustedEvidenceOffer

    settings = LocalAnalysisSettings(
        model="qwen3:8b", expected_model_digest="sha256:" + "5" * 64
    )
    analysis_input = build_analysis_input(
        video=_video(),
        transcript_text="\n".join(CUE_TEXTS),
        language="en",
        output_language="zh-CN",
        settings=settings,
        provider="ollama",
        operation="local-analysis",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        registry=_registry(),
    )
    request = summary_draft_request(analysis_input)
    task = json.loads(request.content_json)
    assert task["title"] == "The Phone Number puzzle"
    assert task["channel_name"] == "3Blue1Brown"
    assert task["description"]
    # The metadata *ref* is never offered, but the metadata *content* is present.
    assert _metadata_ref() not in request.trusted_evidence_json
    assert isinstance(
        analysis_input.trusted_evidence, TrustedEvidenceOffer
    )


def test_10c_canonical_only_content_still_projects_a_wellformed_offer() -> None:
    """No citable candidate must not become a schema error at request build."""

    canonical_only = build_trusted_evidence_registry(
        transcript=None,
        canonical_text="a plain canonical transcript without timed cues",
        canonical_content_hash="c" * 64,
        title="T",
        channel_name="C",
        description="D",
        input_identity="a" * 64,
    )
    assert canonical_only.citable_refs() == ()
    offer = canonical_only.offer()
    assert offer.candidates
    # And hydration still refuses it with the honest existing error.
    ref = canonical_only.candidates[0].ref
    draft = SummaryDraft(
        one_sentence_summary="s",
        core_points=(SummaryDraftPoint(text="t", kind="fact", evidence_refs=(ref,)),),
        keywords=("k",),
    )
    with pytest.raises(SummaryEvidenceAuthorityError):
        hydrate_summary_evidence(
            draft,
            canonical_only,
            video_id=VIDEO_ID,
            canonical_artifact_id=ARTIFACT_ID,
            language="en",
            timed_transcript_id=None,
            timed_transcript_hash=None,
        )


def test_10d_the_prompt_separates_citable_refs_from_context_refs() -> None:
    from youtube_intel.analysis import LOCAL_ANALYSIS_CONTEXT_TOKENS  # noqa: F401
    from youtube_intel.summary_draft import summary_draft_instructions

    citable = _registry().citable_refs()
    context = _registry().context_refs()
    text = summary_draft_instructions(citable_refs=citable, context_refs=context)
    assert _transcript_ref() in text
    assert _metadata_ref() in text
    assert "ONLY refs allowed in evidence_refs" in text
    assert "never evidence" in text


@pytest.mark.parametrize(
    "source",
    [
        EvidenceSource.TITLE,
        EvidenceSource.CHANNEL_NAME,
        EvidenceSource.DESCRIPTION,
    ],
)
def test_11_metadata_cannot_be_emitted_as_evidence_refs(source: EvidenceSource) -> None:
    assert _metadata_ref(source) not in _registry().citable_refs()
    assert _metadata_ref(source) in _registry().context_refs()


@pytest.mark.parametrize(
    "source",
    [
        EvidenceSource.TITLE,
        EvidenceSource.CHANNEL_NAME,
        EvidenceSource.DESCRIPTION,
    ],
)
def test_12_a_metadata_evidence_ref_fails_closed(source: EvidenceSource) -> None:
    with pytest.raises(SummaryEvidenceRefNotCitable) as caught:
        _hydrate(_draft(_metadata_ref(source)))
    assert SUMMARY_EVIDENCE_REF_NOT_CITABLE in str(caught.value)


def test_12b_metadata_citation_mints_no_evidence_and_drops_nothing(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    before = repository.list_evidence_for_presentation(VIDEO_ID)
    with pytest.raises(SummaryEvidenceRefNotCitable):
        _hydrate(_draft(_metadata_ref(), _transcript_ref()))
    assert repository.list_evidence_for_presentation(VIDEO_ID) == before


def test_13_metadata_failure_is_known_response_not_dispatch_ambiguity() -> None:
    """The refusal family is a hydration failure, i.e. a known response."""

    assert issubclass(SummaryEvidenceRefNotCitable, SummaryEvidenceAuthorityError)
    # KnownSummaryResponseError is what the analyzer converts it into; an
    # ambiguous dispatch is a different, terminal family entirely.
    assert not issubclass(SummaryEvidenceAuthorityError, RuntimeError)
    assert not issubclass(SummaryEvidenceRefNotCitable, TimeoutError)


# --- 14-16: only selected timed Evidence is promoted -------------------


def test_14_only_selected_timed_evidence_is_promoted() -> None:
    registry = _registry()
    citable = registry.citable_refs()
    hydrated = _hydrate(_draft(citable[0]))
    assert len(hydrated.promotions) == 1
    assert {p.evidence_id for p in hydrated.promotions} == {
        hydrated.durable_by_ref[citable[0]]
    }


def test_15_unselected_timed_candidates_are_not_promoted() -> None:
    registry = _registry()
    citable = registry.citable_refs()
    selected = citable[0]
    hydrated = _hydrate(_draft(selected))
    promoted = {p.evidence_id for p in hydrated.promotions}
    for ref in citable:
        if ref == selected:
            continue
        assert ref not in hydrated.durable_by_ref
        assert ref not in promoted
        # The unselected ref is still a legal candidate, just not promoted.
        assert ref in registry.citable_refs()


def test_16_original_transcript_and_extraction_ids_stay_distinct(
    tmp_path: Path,
) -> None:
    from youtube_intel.state import EvidenceLineageKind, EvidenceRole, build_evidence_id

    hydrated = _hydrate(_draft(_transcript_ref()))
    promotion = hydrated.promotions[0]
    original_id = build_evidence_id(
        video_id=promotion.video_id,
        artifact_id=promotion.canonical_artifact_id,
        start_ms=promotion.start_ms,
        end_ms=promotion.end_ms,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    assert promotion.evidence_id != original_id


# --- 19-20: cache identity and historical artifacts -------------------


def test_19_prompt_identity_changed_so_the_v5_cache_cannot_be_reused() -> None:
    assert SUMMARY_DRAFT_PROMPT_VERSION == "analysis-prompt-v6"
    assert SUMMARY_DRAFT_PROMPT_VERSION != "analysis-prompt-v5"


def test_20_the_wire_schema_is_unchanged_by_the_v6_repair() -> None:
    assert SUMMARY_DRAFT_SCHEMA_VERSION == "summary-draft-v1"


@pytest.mark.parametrize(
    "historical",
    [
        "analysis-prompt-v1",
        "analysis-prompt-v2",
        "analysis-prompt-v3",
        "analysis-prompt-v4",
        "analysis-prompt-v5",
        "analysis-prompt-v6",
    ],
)
def test_20b_historical_prompt_versions_remain_parseable(historical: str) -> None:
    from youtube_intel.domain import AnalysisResult

    payload = {
        "one_sentence_summary": "s",
        "core_points": [
            {"text": "t", "kind": "fact", "evidence_ids": ["a" * 64]}
        ],
        "keywords": ["k"],
        "evidence": [
            {
                "evidence_id": "a" * 64,
                "source": "transcript_sample",
                "excerpt": "x",
            }
        ],
        "provider": "ollama",
        "model": "qwen3:8b",
        "prompt_version": historical,
        "schema_version": "analysis-result-v1",
        "request_hash": "0" * 64,
    }
    parsed = AnalysisResult.model_validate(payload)
    assert parsed.prompt_version == historical


def test_20c_the_prompt_identity_set_remains_closed() -> None:
    from pydantic import ValidationError

    from youtube_intel.domain import (
        AnalysisInput,
        AnalysisPayload,
        TrustedEvidenceOffer,
    )

    payload = AnalysisPayload(
        video_id=VIDEO_ID,
        title="t",
        channel_name="c",
        published_at=NOW,
        duration_seconds=44,
        description="d",
        transcript_language="en",
        transcript_sample="s",
        output_language="zh-CN",
    )
    from youtube_intel.summary_evidence_candidates import TrustedEvidenceCandidateView

    offer = TrustedEvidenceOffer(
        registry_identity="0" * 64,
        cue_group_policy="c",
        metadata_span_policy="m",
        candidates=(
            TrustedEvidenceCandidateView(
                ref="t0-2-abc", source="transcript_sample", text="t"
            ),
        ),
    )
    with pytest.raises(ValidationError):
        AnalysisInput(
            payload=payload,
            transcript_content_hash="0" * 64,
            request_hash="0" * 64,
            prompt_version="analysis-prompt-v7",
            trusted_evidence=offer,
        )


# --- fail-closed behaviour that must survive -----------------------------


def test_unissued_ref_still_fails_closed() -> None:
    with pytest.raises(SummaryEvidenceAuthorityError, match="unissued evidence ref"):
        _hydrate(_draft("t0-4-deadbeefdeadbeef"))


def test_missing_timed_authority_still_fails_closed() -> None:
    from youtube_intel.summary_evidence_authority import (
        SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE,
    )

    with pytest.raises(SummaryEvidenceAuthorityUnavailable) as caught:
        _hydrate(_draft(_transcript_ref()), timed_transcript_id=None, timed_transcript_hash=None)
    assert SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE in str(caught.value)


def test_known_response_error_diagnostic_is_not_an_ambiguity() -> None:
    error = KnownSummaryResponseError(SUMMARY_EVIDENCE_REF_NOT_CITABLE)
    assert "known response rejected" in error.diagnostic()
    assert "ambiguous" not in error.diagnostic().lower()


# --- request wiring ------------------------------------------------------


def test_live_request_only_offers_citable_refs_as_evidence() -> None:
    from youtube_intel.config import LocalAnalysisSettings

    registry = _registry()
    offer = registry.offer()
    from youtube_intel.domain import (
        AnalysisInput,
        AnalysisPayload,
        TrustedEvidenceCandidateView,
        TrustedEvidenceOffer,
    )

    payload = AnalysisPayload(
        video_id=VIDEO_ID,
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        published_at=NOW,
        duration_seconds=44,
        description="short description",
        transcript_language="en",
        transcript_sample="\n".join(CUE_TEXTS),
        output_language="zh-CN",
    )
    bounded = TrustedEvidenceOffer(
        registry_identity=offer.registry_identity,
        cue_group_policy=offer.cue_group_policy,
        metadata_span_policy=offer.metadata_span_policy,
        candidates=offer.candidates,
    )
    analysis_input = AnalysisInput(
        payload=payload,
        transcript_content_hash="0" * 64,
        request_hash="0" * 64,
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        trusted_evidence=bounded,
    )
    assert require_trusted_evidence_offer(analysis_input) is bounded
    request = summary_draft_request(analysis_input)
    assert isinstance(bounded.candidates[0], TrustedEvidenceCandidateView)
    # Metadata text still reaches the provider through the task context.
    assert json.loads(request.content_json)["title"]
    # But the instructions forbid citing it.
    assert "Never cite a context ref as evidence" in request.instructions
    assert LocalAnalysisSettings is not None


def test_analysis_input_is_built_with_the_v6_prompt_identity() -> None:
    from youtube_intel.config import LocalAnalysisSettings

    settings = LocalAnalysisSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + "5" * 64,
    )
    analysis_input = build_analysis_input(
        video=_video(),
        transcript_text="\n".join(CUE_TEXTS),
        language="en",
        output_language="zh-CN",
        settings=settings,
        provider="ollama",
        operation="local-analysis",
        prompt_version=SUMMARY_DRAFT_PROMPT_VERSION,
        registry=_registry(),
    )
    assert analysis_input.prompt_version == "analysis-prompt-v6"
    assert analysis_input.trusted_evidence is not None
    # Only citable candidates are offered; the registry identity still covers
    # the complete canonical form including metadata.
    assert {c.ref for c in analysis_input.trusted_evidence.candidates} == set(
        _registry().citable_refs()
    )
    assert analysis_input.trusted_evidence.registry_identity == (
        _registry().identity_hash()
    )
