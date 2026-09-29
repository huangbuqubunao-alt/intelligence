"""Card D: shared hydrator and promote-on-selection planning."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from youtube_intel.domain import AnalysisPoint, AnalysisResult, EvidenceSource
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    Availability,
    EvidenceLineageKind,
    EvidenceRole,
    LiveStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VerifiedTimedTranscript,
    VerifiedTimedTranscriptCue,
    VideoMetadata,
)
from youtube_intel.summary_draft import SummaryDraft, SummaryDraftPoint
from youtube_intel.summary_evidence_authority import (
    SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE,
    SummaryEvidenceAuthorityError,
    SummaryEvidenceAuthorityUnavailable,
    hydrate_summary_evidence,
)
from youtube_intel.summary_evidence_candidates import (
    build_trusted_evidence_registry,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
VIDEO_ID = "ausLKMojXaY"
TRANSCRIPT_HASH = "b" * 64
CUE_TEXTS = tuple(f"cue{index} source sentence" for index in range(8))


def _verified() -> VerifiedTimedTranscript:
    return VerifiedTimedTranscript(
        timed_transcript_id="tt-1",
        video_id=VIDEO_ID,
        canonical_artifact_id="artifact-1",
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


def _draft(*refs: str) -> SummaryDraft:
    return SummaryDraft(
        one_sentence_summary="摘要",
        core_points=(
            SummaryDraftPoint(text="要点", kind="fact", evidence_refs=refs or ("x",)),
        ),
        keywords=("k",),
    )


def _transcript_ref() -> str:
    return next(
        c.ref for c in _registry().candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )


def _metadata_ref() -> str:
    return next(
        c.ref for c in _registry().candidates if c.source is EvidenceSource.TITLE
    )


def _hydrate(draft, **kwargs):
    base = dict(
        video_id=VIDEO_ID,
        canonical_artifact_id="artifact-1",
        language="en",
        timed_transcript_id="tt-1",
        timed_transcript_hash=TRANSCRIPT_HASH,
    )
    base.update(kwargs)
    return hydrate_summary_evidence(draft, _registry(), **base)


# --- D1 -------------------------------------------------------------------


def test_D1_known_ref_hydrates_backend_owned_excerpt() -> None:
    ref = _transcript_ref()
    issued = _registry().by_ref()[ref]
    result = _hydrate(_draft(ref))
    assert [item.evidence_id for item in result.evidence] == [ref]
    # The excerpt is byte-identical to the backend-issued candidate text.
    assert result.evidence[0].excerpt == issued.text
    assert result.refs == (ref,)


# --- D2 / D3: unissued and foreign refs fail closed -----------------------


def test_D2_unknown_ref_fails_closed() -> None:
    with pytest.raises(SummaryEvidenceAuthorityError, match="unissued evidence ref"):
        _hydrate(_draft("t0-4-deadbeefdeadbeef"))


def test_D2b_empty_refs_fail_closed() -> None:
    draft = SummaryDraft.model_construct(
        one_sentence_summary="x",
        core_points=(),
        keywords=("k",),
    )
    with pytest.raises(SummaryEvidenceAuthorityError, match="cited no trusted evidence"):
        hydrate_summary_evidence(
            draft,
            _registry(),
            video_id=VIDEO_ID,
            canonical_artifact_id="artifact-1",
            language="en",
            timed_transcript_id="tt-1",
            timed_transcript_hash=TRANSCRIPT_HASH,
        )


def test_D3_foreign_video_ref_fails_closed() -> None:
    """A candidate issued for this registry but bound to another transcript."""

    foreign = build_trusted_evidence_registry(
        transcript=VerifiedTimedTranscript(
            timed_transcript_id="tt-foreign",
            video_id="another-video",
            canonical_artifact_id="artifact-foreign",
            timed_transcript_hash="c" * 64,
            cues=_verified().cues,
        ),
        title="T",
        channel_name="C",
        description="D",
        input_identity="a" * 64,
    )
    ref = next(
        c.ref for c in foreign.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    with pytest.raises(SummaryEvidenceAuthorityError, match="unissued evidence ref"):
        _hydrate(_draft(ref))


# --- D4: metadata --------------------------------------------------------


def test_D4_metadata_ref_hydrates_only_backend_candidate_text() -> None:
    ref = _metadata_ref()
    issued = _registry().by_ref()[ref]
    result = _hydrate(_draft(ref))
    assert result.evidence[0].source is EvidenceSource.TITLE
    assert result.evidence[0].excerpt == issued.text == "The Phone Number puzzle"
    # Metadata never needs a durable promotion.
    assert result.promotions == ()


# --- D5 -------------------------------------------------------------------


def test_D5_model_text_can_never_become_evidence() -> None:
    """A draft carrying an excerpt is impossible; a stray ref is rejected."""

    ref = _transcript_ref()
    issued = _registry().by_ref()[ref]
    result = _hydrate(_draft(ref))
    assert result.evidence[0].excerpt == issued.text
    # No path lets claim text become the excerpt.
    assert "要点" not in result.evidence[0].excerpt


# --- D6 / D7: promotion plan --------------------------------------------


def test_D6_promotion_uses_extraction_and_primary_original() -> None:
    ref = _transcript_ref()
    result = _hydrate(_draft(ref))
    assert len(result.promotions) == 1
    promotion = result.promotions[0]
    assert promotion.lineage_kind is EvidenceLineageKind.EXTRACTION
    assert promotion.role is EvidenceRole.PRIMARY_ORIGINAL
    assert promotion.role is not EvidenceRole.ANALYSIS_COMMENTARY
    assert promotion.timed_transcript_hash == TRANSCRIPT_HASH


def test_D7_half_open_cue_range_matches_candidate_text() -> None:
    ref = _transcript_ref()
    issued = _registry().by_ref()[ref]
    promotion = _hydrate(_draft(ref)).promotions[0]
    assert promotion.start_cue_index == issued.start_cue_index
    assert promotion.end_cue_index == issued.end_cue_index
    assert promotion.end_cue_index > promotion.start_cue_index
    window = _verified().cues[promotion.start_cue_index : promotion.end_cue_index]
    # Exactly the half-open range, neither dropped nor duplicated.
    assert len(window) == promotion.end_cue_index - promotion.start_cue_index
    assert promotion.excerpt == "\n".join(cue.text for cue in window)
    assert promotion.excerpt == issued.text
    assert promotion.start_ms == window[0].start_ms
    assert promotion.end_ms == window[-1].end_ms


def test_D7b_promotion_write_and_binding_agree() -> None:
    ref = _transcript_ref()
    promotion = _hydrate(_draft(ref)).promotions[0]
    write = promotion.as_evidence_write()
    binding = promotion.as_text_binding()
    assert write.evidence_id == binding.evidence_id == promotion.evidence_id
    assert binding.start_cue_index == promotion.start_cue_index
    assert binding.end_cue_index == promotion.end_cue_index
    assert binding.excerpt == promotion.excerpt
    assert binding.excerpt_hash == promotion.excerpt_hash
    assert sha256(binding.excerpt.encode()).hexdigest() == binding.excerpt_hash


# --- D10 -----------------------------------------------------------------


def test_D10_hydrated_evidence_is_analysis_result_compatible() -> None:
    from youtube_intel.domain import AnalysisResult

    ref = _transcript_ref()
    result = _hydrate(_draft(ref))
    draft = _draft(ref)
    analysis = AnalysisResult(
        one_sentence_summary=draft.one_sentence_summary,
        core_points=tuple(
            AnalysisPoint(text=point.text, kind=point.kind, evidence_ids=(ref,))
            for point in draft.core_points
        ),
        keywords=draft.keywords,
        evidence=result.evidence,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="analysis-prompt-v4",
        schema_version="analysis-result-v1",
        request_hash="0" * 64,
    )
    # Downstream consumers render evidence_id / source / excerpt unchanged.
    assert analysis.evidence[0].evidence_id == ref
    assert analysis.evidence[0].excerpt


# --- canonical-only fail closed ------------------------------------------


def test_canonical_only_content_fails_closed_without_timed_authority() -> None:
    ref = _transcript_ref()
    with pytest.raises(SummaryEvidenceAuthorityUnavailable) as caught:
        _hydrate(_draft(ref), timed_transcript_id=None, timed_transcript_hash=None)
    assert SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE in str(caught.value)


def test_foreign_transcript_hash_fails_closed() -> None:
    ref = _transcript_ref()
    with pytest.raises(SummaryEvidenceAuthorityError, match="not bound to the verified"):
        _hydrate(_draft(ref), timed_transcript_hash="f" * 64)


# --- D8 / D9: repository idempotency -------------------------------------


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
            artifact_id="artifact-1",
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
        now=NOW,
    )
    return repository


def _promotion(repository: SQLiteStateRepository):
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="d",
        input_identity="a" * 64,
    )
    ref = next(
        c.ref for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    draft = _draft(ref)
    return hydrate_summary_evidence(
        draft,
        registry,
        video_id=VIDEO_ID,
        canonical_artifact_id="artifact-1",
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    ).promotions[0]


def test_D8_get_create_verify_is_idempotent(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    first = repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    second = repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    assert first.evidence_id == second.evidence_id == promotion.evidence_id
    assert second.created_at == first.created_at
    # Idempotent: no duplicate row, and the trusted resolver agrees.
    resolved = repository.resolve_verified_evidence_text(promotion.evidence_id)
    assert resolved is not None
    assert resolved.excerpt == promotion.excerpt


def test_D9_pre_existing_conflicting_evidence_fails_closed(tmp_path: Path) -> None:
    from youtube_intel.state import IntegrityConflict

    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    # Persist a *different* span under the same identity: same id, other text.
    conflicting = promotion.as_evidence_write()
    bad_binding = promotion.as_text_binding()
    repository.promote_summary_evidence(conflicting, bad_binding, now=NOW)
    # A second promotion claiming the same identity but a different excerpt
    # must fail closed rather than be accepted or silently overwritten.
    with pytest.raises((IntegrityConflict, ValueError)):
        repository.promote_summary_evidence(
            conflicting,
            type(bad_binding)(
                evidence_id=conflicting.evidence_id,
                timed_transcript_id=bad_binding.timed_transcript_id,
                start_cue_index=bad_binding.start_cue_index,
                end_cue_index=bad_binding.end_cue_index,
                excerpt="a completely different excerpt",
                excerpt_hash=sha256(b"a completely different excerpt").hexdigest(),
            ),
            now=NOW,
        )


def test_promotion_rejects_non_extraction_lineage(tmp_path: Path) -> None:
    from youtube_intel.state import EvidenceWrite

    repository = _seed(tmp_path)
    promotion = _promotion(repository)
    from youtube_intel.state import build_evidence_id

    wrong_lineage_id = build_evidence_id(
        video_id=promotion.video_id,
        artifact_id=promotion.canonical_artifact_id,
        start_ms=promotion.start_ms,
        end_ms=promotion.end_ms,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
    )
    bad = EvidenceWrite(
        evidence_id=wrong_lineage_id,
        video_id=promotion.video_id,
        artifact_id=promotion.canonical_artifact_id,
        start_ms=promotion.start_ms,
        end_ms=promotion.end_ms,
        lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
        role=EvidenceRole.PRIMARY_ORIGINAL,
        language="en",
        availability=promotion.as_evidence_write().availability,
    )
    with pytest.raises(ValueError, match="EXTRACTION lineage"):
        repository.promote_summary_evidence(bad, promotion.as_text_binding(), now=NOW)


def test_promoted_analysis_result_cannot_carry_prompt_v5_yet() -> None:
    """Documents a live-cutover blocker discovered during Authority Wiring.

    ``AnalysisResult.prompt_version`` is a Literal capped at
    ``analysis-prompt-v4``. A hydrated result produced under
    ``analysis-prompt-v5`` therefore cannot yet be constructed, so the
    production cutover must widen this persisted identity in the same change
    that actually performs the cutover. Foundation deliberately did not widen
    it, because a v5-capable persisted contract with no v5 producer would be
    a half-migrated runtime.
    """

    import pytest as _pytest
    from pydantic import ValidationError as _ValidationError

    ref = _transcript_ref()
    result = _hydrate(_draft(ref))
    with _pytest.raises(_ValidationError, match="prompt_version"):
        AnalysisResult(
            one_sentence_summary="s",
            core_points=(AnalysisPoint(text="t", kind="fact", evidence_ids=(ref,)),),
            keywords=("k",),
            evidence=result.evidence,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="analysis-prompt-v5",
            schema_version="analysis-result-v1",
            request_hash="0" * 64,
        )
