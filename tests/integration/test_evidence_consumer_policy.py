"""Card F: explicit Evidence consumer policy.

``ORIGINAL_TRANSCRIPT`` canonical coverage and Summary-promoted
``EXTRACTION`` spans coexist in one table. Every consumer must have a
deliberate, tested policy so that promoting Summary Evidence cannot silently
change what Intelligence, reservation, translation, or the UI consume.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from youtube_intel.domain import EvidenceSource
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
    VideoMetadata,
)
from youtube_intel.summary_evidence_authority import hydrate_summary_evidence
from youtube_intel.summary_evidence_candidates import build_trusted_evidence_registry

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
VIDEO_ID = "ausLKMojXaY"
# Long enough that both the coarse durable partition and the fine Summary
# cue-group policy produce several spans, so ordering can be compared.
CUE_TEXTS = tuple(
    (f"cue{index} " + f"sentence{index} " * 15).strip() for index in range(12)
)


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
    timed = repository.create_timed_transcript(
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
    # Use the real ingestion helper so the coarse ORIGINAL_TRANSCRIPT
    # canonical-coverage Evidence exists exactly as production creates it.
    from youtube_intel.transcripts import _persist_original_transcript_evidence

    _persist_original_transcript_evidence(
        repository, timed=timed, language="en", now=NOW
    )
    assert repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    return repository


def _promote_summary_span(repository: SQLiteStateRepository) -> str:
    """Promote one fine Summary-selected span as EXTRACTION."""
    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="t",
        channel_name="c",
        description="d",
        input_identity="a" * 64,
    )
    ref = next(
        c.ref for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    from youtube_intel.summary_draft import SummaryDraft, SummaryDraftPoint

    hydrated = hydrate_summary_evidence(
        SummaryDraft(
            one_sentence_summary="s",
            core_points=(
                SummaryDraftPoint(text="t", kind="fact", evidence_refs=(ref,)),
            ),
            keywords=("k",),
        ),
        registry,
        video_id=VIDEO_ID,
        canonical_artifact_id="artifact-1",
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    )
    promotion = hydrated.promotions[0]
    record = repository.promote_summary_evidence(
        promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
    )
    return record.evidence_id


# --- F1 -------------------------------------------------------------------


def test_F1_original_and_extraction_coexist(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promoted = _promote_summary_span(repository)
    assert promoted in repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    coverage = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert coverage  # coarse canonical partition still present
    assert promoted not in coverage
    record = repository.get_evidence(promoted)
    assert record is not None
    assert record.lineage_kind is EvidenceLineageKind.EXTRACTION
    assert record.role is EvidenceRole.PRIMARY_ORIGINAL


# --- F2 -------------------------------------------------------------------


def test_F2_content_evidence_presentation_policy_is_deterministic(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    promoted = _promote_summary_span(repository)
    presented = repository.list_evidence_for_presentation(VIDEO_ID)
    extracted = repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    coverage = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    # Summary-selected first (the citations a reader followed), then coverage.
    assert presented == extracted + coverage
    assert presented[0] == promoted
    # No lineage leakage between the groups.
    assert set(extracted).isdisjoint(set(coverage))
    # Restart-stable.
    reopened = SQLiteStateRepository(tmp_path / "state.sqlite3")
    assert reopened.list_evidence_for_presentation(VIDEO_ID) == presented


def _promote_all_summary_spans(repository: SQLiteStateRepository) -> None:
    """Promote every fine candidate so ordering can be compared to SHA order."""

    verified = repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert verified is not None
    registry = build_trusted_evidence_registry(
        transcript=verified,
        title="t",
        channel_name="c",
        description="d",
        input_identity="a" * 64,
    )
    refs = tuple(
        c.ref for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    )
    from youtube_intel.summary_draft import SummaryDraft, SummaryDraftPoint

    points = tuple(
        SummaryDraftPoint(text=f"p{i}", kind="fact", evidence_refs=(ref,))
        for i, ref in enumerate(refs)
    )
    hydrated = hydrate_summary_evidence(
        SummaryDraft(
            one_sentence_summary="s", core_points=points, keywords=("k",)
        ),
        registry,
        video_id=VIDEO_ID,
        canonical_artifact_id="artifact-1",
        language="en",
        timed_transcript_id=verified.timed_transcript_id,
        timed_transcript_hash=verified.timed_transcript_hash,
    )
    for promotion in hydrated.promotions:
        repository.promote_summary_evidence(
            promotion.as_evidence_write(), promotion.as_text_binding(), now=NOW
        )


def test_F2b_presentation_is_not_lexically_sha_ordered(tmp_path: Path) -> None:
    """Ordering within a lineage is by source range, never by SHA lexicity."""

    repository = _seed(tmp_path)
    _promote_all_summary_spans(repository)
    extracted = repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    assert len(extracted) > 1
    records = [repository.get_evidence(eid) for eid in extracted]
    assert all(record is not None for record in records)
    starts = [record.start_ms for record in records if record is not None]
    # Range-ascending, and demonstrably not id-lexicographic.
    assert starts == sorted(starts)
    assert list(extracted) != sorted(extracted)


# --- F3 / F4: Intelligence semantics preserved ---------------------------


def test_F3_intelligence_canonical_candidate_semantics_preserved(tmp_path: Path) -> None:
    """The set local/cloud Intelligence has always seen must not change.

    ``distillation`` performs an exact set-equality reservation check against
    this set, so promoting Summary EXTRACTION rows must not enter it.
    """

    repository = _seed(tmp_path)
    before = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert before
    _promote_summary_span(repository)
    after = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert after == before
    # The legacy shared helper still sees the union (its semantics unchanged),
    # which is exactly why the consumers must move to the explicit reader.
    legacy = repository.list_available_canonical_evidence_ids(VIDEO_ID)
    assert set(legacy) == set(before) | set(
        repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    )


def test_F4_cloud_reservation_evidence_set_is_unaffected(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    before = tuple(sorted(repository.list_canonical_coverage_evidence_ids(VIDEO_ID)))
    _promote_summary_span(repository)
    reservation_set = tuple(sorted(repository.list_canonical_coverage_evidence_ids(VIDEO_ID)))
    assert reservation_set == before
    assert len(reservation_set) == len(set(reservation_set))


# --- F5 -------------------------------------------------------------------


def test_F5_translation_path_accepts_valid_promoted_evidence(tmp_path: Path) -> None:
    """Promoted EXTRACTION Evidence is verifiable source text, so it qualifies."""

    repository = _seed(tmp_path)
    promoted = _promote_summary_span(repository)
    resolved = repository.resolve_verified_evidence_text(promoted)
    assert resolved is not None
    assert resolved.excerpt
    assert sha256(resolved.excerpt.encode()).hexdigest() == resolved.excerpt_hash


# --- F6: capped queries --------------------------------------------------


def test_F6_capped_query_is_not_starved_by_extraction_rows(tmp_path: Path) -> None:
    """EXTRACTION rows must not consume another lineage's candidate budget."""

    repository = _seed(tmp_path)
    coverage_before = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    for _ in range(5):
        _promote_summary_span(repository)
    extracted = repository.list_summary_promoted_evidence_ids(VIDEO_ID)
    coverage_after = repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    # Repeated promotion is idempotent, so the fine set stays stable...
    assert len(set(extracted)) == len(extracted)
    # ...and canonical coverage is entirely unaffected by EXTRACTION presence.
    assert coverage_after == coverage_before


def test_F6b_cap_bound_is_enforced_per_lineage(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    assert len(repository.list_canonical_coverage_evidence_ids(VIDEO_ID)) <= 21
    _promote_summary_span(repository)
    assert len(repository.list_summary_promoted_evidence_ids(VIDEO_ID)) <= 21
    assert len(repository.list_evidence_for_presentation(VIDEO_ID)) <= 42


# --- F7 -------------------------------------------------------------------


def test_F7_ordering_is_restart_stable(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    repository = _seed(tmp_path)
    _promote_summary_span(repository)
    first = repository.list_evidence_for_presentation(VIDEO_ID)
    second = SQLiteStateRepository(path).list_evidence_for_presentation(VIDEO_ID)
    assert second == first
    assert first  # non-empty


# --- F8: the shared legacy helper is unchanged ---------------------------


def test_F8_legacy_helper_semantics_remain_unchanged(tmp_path: Path) -> None:
    """``list_available_canonical_evidence_ids`` must not silently change.

    It is a public repository API with existing tests. It still returns every
    available canonical-transcript Evidence id ordered lexically by id; the
    lineage split lives in the new purpose-specific readers instead.
    """

    import inspect

    from youtube_intel.state import SQLiteStateRepository as Repo

    source = inspect.getsource(Repo.list_available_canonical_evidence_ids)
    assert "ORDER BY evidence.evidence_id ASC LIMIT 21" in source
    assert "lineage_kind" not in source

    repository = _seed(tmp_path)
    _promote_summary_span(repository)
    legacy = repository.list_available_canonical_evidence_ids(VIDEO_ID)
    assert list(legacy) == sorted(legacy)


def test_unknown_video_readers_return_empty(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    assert repository.list_canonical_coverage_evidence_ids("nope") == ()
    assert repository.list_summary_promoted_evidence_ids("nope") == ()
    assert repository.list_evidence_for_presentation("nope") == ()
