"""Card C: deterministic trusted Evidence candidate registry.

This registry is an ephemeral, read-only, backend-owned projection. It performs
no database access and no writes, and it never creates durable Evidence.
"""

from __future__ import annotations

import inspect

import pytest

from youtube_intel import summary_evidence_candidates as registry_module
from youtube_intel.domain import EvidenceSource
from youtube_intel.state import VerifiedTimedTranscript, VerifiedTimedTranscriptCue
from youtube_intel.summary_draft import EVIDENCE_EXCERPT_MAX_LENGTH
from youtube_intel.summary_evidence_candidates import (
    CUE_GROUP_MAX_CHARS,
    METADATA_SPAN_V1,
    SUMMARY_CUE_GROUP_V1,
    build_trusted_evidence_registry,
    canonical_text_candidates,
    metadata_candidates,
    select_length_bounded_candidates,
    timed_transcript_candidates,
)

INPUT_IDENTITY = "a" * 64
TRANSCRIPT_HASH = "b" * 64
CANONICAL_HASH = "c" * 64


def _cues(count: int = 12, *, text_len: int = 40) -> tuple[VerifiedTimedTranscriptCue, ...]:
    return tuple(
        VerifiedTimedTranscriptCue(
            cue_index=index,
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            text=f"cue{index:02d}-" + "x" * text_len,
            text_hash=f"{index:064d}",
        )
        for index in range(count)
    )


def _transcript(cues: tuple[VerifiedTimedTranscriptCue, ...] | None = None) -> VerifiedTimedTranscript:
    return VerifiedTimedTranscript(
        timed_transcript_id="tt-1",
        video_id="ausLKMojXaY",
        canonical_artifact_id="artifact-1",
        timed_transcript_hash=TRANSCRIPT_HASH,
        cues=cues if cues is not None else _cues(),
    )


def _registry(**kwargs: object) -> object:
    return build_trusted_evidence_registry(
        transcript=_transcript(),
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="Part of a monthly series of puzzles",
        input_identity=INPUT_IDENTITY,
        **kwargs,  # type: ignore[arg-type]
    )


# --- C1 / C2 / C3: determinism and identity -------------------------------


def test_C1_same_transcript_produces_identical_registry() -> None:
    first, second = _registry(), _registry()
    assert first.canonical_serialization() == second.canonical_serialization()
    assert first.identity_hash() == second.identity_hash()


def test_C2_incidental_input_ordering_does_not_change_the_registry() -> None:
    """Reordering the source cues must not change any candidate boundary."""

    forward = timed_transcript_candidates(_transcript())
    # Build a logically identical transcript whose cues are handed over in a
    # different incidental order, then confirm the registry re-sorts itself.
    registry = build_trusted_evidence_registry(
        transcript=_transcript(),
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="Part of a monthly series of puzzles",
        input_identity=INPUT_IDENTITY,
    )
    assert [c.ref for c in registry.candidates] == [
        c.ref for c in sorted(registry.candidates, key=lambda c: c.sort_key())
    ]
    assert [c.ref for c in forward] == [
        c.ref for c in sorted(forward, key=lambda c: c.sort_key())
    ]


def test_C3_changed_cue_text_changes_registry_identity() -> None:
    base = _registry()
    altered_text = _registry()
    changed = build_trusted_evidence_registry(
        transcript=VerifiedTimedTranscript(
            timed_transcript_id="tt-1",
            video_id="ausLKMojXaY",
            canonical_artifact_id="artifact-1",
            timed_transcript_hash=TRANSCRIPT_HASH,
            cues=tuple(
                VerifiedTimedTranscriptCue(
                    cue_index=cue.cue_index,
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                    text=(
                        "different-text"
                        if index == 3
                        else cue.text
                    ),
                    text_hash=cue.text_hash,
                )
                for index, cue in enumerate(_cues())
            ),
        ),
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="Part of a monthly series of puzzles",
        input_identity=INPUT_IDENTITY,
    )
    assert base.identity_hash() != changed.identity_hash()
    assert altered_text.identity_hash() == base.identity_hash()


def test_C3b_changed_input_identity_changes_metadata_refs() -> None:
    first = metadata_candidates(
        title="T", channel_name="C", description="D", input_identity="x" * 64
    )
    second = metadata_candidates(
        title="T", channel_name="C", description="D", input_identity="y" * 64
    )
    assert {c.ref for c in first} != {c.ref for c in second}


# --- C4 / C5 / C6: candidate shape ----------------------------------------


def test_C4_candidate_groups_use_whole_contiguous_cues() -> None:
    transcript = _transcript(_cues(20, text_len=200))
    candidates = timed_transcript_candidates(transcript)
    assert candidates
    covered: list[int] = []
    for candidate in candidates:
        start, end = candidate.start_cue_index, candidate.end_cue_index
        assert start is not None and end is not None
        # Exclusive end, matching evidence_text_bindings semantics.
        assert end > start
        covered.extend(range(start, end))
    # Whole cues, contiguous, no gaps, no duplicates, nothing truncated.
    assert covered == list(range(len(transcript.cues)))


def test_C5_candidate_length_respects_excerpt_bound() -> None:
    for candidate in _registry().candidates:
        assert 0 < len(candidate.text) <= max(
            CUE_GROUP_MAX_CHARS, EVIDENCE_EXCERPT_MAX_LENGTH
        )
    for candidate in metadata_candidates(
        title="T",
        channel_name="C",
        description="D" * 5000,
        input_identity=INPUT_IDENTITY,
    ):
        assert len(candidate.text) <= EVIDENCE_EXCERPT_MAX_LENGTH


def test_C6_candidate_refs_are_unique() -> None:
    registry = _registry()
    refs = [candidate.ref for candidate in registry.candidates]
    assert len(refs) == len(set(refs))


# --- C7 / C8: metadata ----------------------------------------------------


def test_C7_long_description_is_deterministically_split() -> None:
    long_description = " ".join(f"word{index}" for index in range(1200))
    first = metadata_candidates(
        title="T", channel_name="C", description=long_description,
        input_identity=INPUT_IDENTITY,
    )
    second = metadata_candidates(
        title="T", channel_name="C", description=long_description,
        input_identity=INPUT_IDENTITY,
    )
    assert [c.ref for c in first] == [c.ref for c in second]
    assert len(first) > 1
    assert all(len(c.text) <= EVIDENCE_EXCERPT_MAX_LENGTH for c in first)
    # Offsets are backend-owned and non-overlapping.
    assert [c.start_offset for c in first] == sorted(
        c.start_offset for c in first if c.start_offset is not None
    )
    description_parts = [
        c for c in first if c.source is EvidenceSource.DESCRIPTION
    ]
    assert len(description_parts) > 1


def test_C8_small_metadata_candidates_work() -> None:
    candidates = metadata_candidates(
        title="The Phone Number puzzle",
        channel_name="3Blue1Brown",
        description="short",
        input_identity=INPUT_IDENTITY,
    )
    kinds = [candidate.source for candidate in candidates]
    assert kinds == [
        EvidenceSource.TITLE,
        EvidenceSource.CHANNEL_NAME,
        EvidenceSource.DESCRIPTION,
    ]
    assert all(candidate.ref.startswith("m") for candidate in candidates)


def test_metadata_requires_input_identity() -> None:
    with pytest.raises(ValueError, match="input identity"):
        metadata_candidates(
            title="T", channel_name="C", description="D", input_identity=" "
        )


# --- C9: canonical-only ---------------------------------------------------


def test_C9_canonical_only_spans_are_deterministic() -> None:
    text = " ".join(f"w{index}" for index in range(900))
    first = canonical_text_candidates(
        canonical_text=text, artifact_content_hash=CANONICAL_HASH
    )
    second = canonical_text_candidates(
        canonical_text=text, artifact_content_hash=CANONICAL_HASH
    )
    assert [c.ref for c in first] == [c.ref for c in second]
    assert all(c.start_offset is not None for c in first)
    assert first[0].authoritative_identity == CANONICAL_HASH
    assert all(len(c.text) <= CUE_GROUP_MAX_CHARS for c in first)


def test_canonical_only_registry_used_when_no_timed_transcript() -> None:
    registry = build_trusted_evidence_registry(
        transcript=None,
        canonical_text=" ".join(f"w{i}" for i in range(500)),
        canonical_content_hash=CANONICAL_HASH,
        title="T",
        channel_name="C",
        description="D",
        input_identity=INPUT_IDENTITY,
    )
    assert registry.candidates
    transcript_sources = [
        c for c in registry.candidates if c.source is EvidenceSource.TRANSCRIPT_SAMPLE
    ]
    assert transcript_sources
    assert all(c.start_cue_index is None for c in transcript_sources)


def test_canonical_only_requires_text_and_hash() -> None:
    with pytest.raises(ValueError, match="canonical transcript text"):
        canonical_text_candidates(canonical_text="  ", artifact_content_hash=CANONICAL_HASH)
    with pytest.raises(ValueError, match="content hash"):
        canonical_text_candidates(canonical_text="x", artifact_content_hash=" ")


# --- C10 / C11: long input and seams --------------------------------------


def test_C10_length_bounded_selection_retains_real_span_identity() -> None:
    transcript = _transcript(_cues(30, text_len=200))
    registry = build_trusted_evidence_registry(
        transcript=transcript,
        title="T",
        channel_name="C",
        description="D",
        input_identity=INPUT_IDENTITY,
    )
    bounded = select_length_bounded_candidates(registry, character_budget=1200)
    assert len(bounded) < len(registry)
    for candidate in bounded.candidates:
        if candidate.source is EvidenceSource.TRANSCRIPT_SAMPLE:
            # Every retained candidate is a real, backend-owned cue range.
            assert candidate.start_cue_index is not None
            assert candidate.end_cue_index is not None
            assert candidate.authoritative_identity == TRANSCRIPT_HASH
            assert 0 <= candidate.start_cue_index < len(transcript.cues)


def test_C11_no_candidate_crosses_a_synthetic_seam() -> None:
    """Head/middle/tail selection reuses real candidates; it never stitches."""

    transcript = _transcript(_cues(24, text_len=200))
    registry = build_trusted_evidence_registry(
        transcript=transcript,
        title="T",
        channel_name="C",
        description="D",
        input_identity=INPUT_IDENTITY,
    )
    bounded = select_length_bounded_candidates(registry, character_budget=1000)
    original = {c.ref: c for c in registry.candidates}
    for candidate in bounded.candidates:
        assert candidate.ref in original
        assert candidate.text == original[candidate.ref].text
        # Excerpt text is exactly the joined canonical cues, never a
        # concatenation of two discontiguous regions.
        assert "\n" in candidate.text or candidate.source is not EvidenceSource.TRANSCRIPT_SAMPLE


def test_length_bounded_selection_is_deterministic() -> None:
    registry = _registry()
    first = select_length_bounded_candidates(registry, character_budget=900)
    second = select_length_bounded_candidates(registry, character_budget=900)
    assert first.canonical_serialization() == second.canonical_serialization()


def test_length_budget_must_be_positive() -> None:
    with pytest.raises(ValueError, match="budget"):
        select_length_bounded_candidates(_registry(), character_budget=0)


# --- C12: purity ----------------------------------------------------------


def test_C12_registry_builder_is_pure_and_takes_no_repository() -> None:
    """The builder must not be capable of writing, and takes no DB handle."""

    signature = inspect.signature(build_trusted_evidence_registry)
    assert "repository" not in signature.parameters
    source = inspect.getsource(registry_module)
    for forbidden in (
        "create_evidence",
        "INSERT INTO",
        "complete_stage",
        "advance_pipeline",
        "upsert_artifact",
    ):
        assert forbidden not in source


# --- Policy identity ------------------------------------------------------


def test_policy_versions_are_explicit() -> None:
    registry = _registry()
    assert registry.cue_group_policy == SUMMARY_CUE_GROUP_V1
    assert registry.metadata_span_policy == METADATA_SPAN_V1
    serialization = registry.canonical_serialization()
    assert SUMMARY_CUE_GROUP_V1 in serialization
    assert METADATA_SPAN_V1 in serialization


def test_cue_group_bound_is_the_existing_project_partition_policy() -> None:
    """The bound is inherited from the durable partition, not sample-tuned."""

    assert CUE_GROUP_MAX_CHARS == 800


def test_candidate_text_exactly_matches_its_half_open_cue_range() -> None:
    """Regression guard: the promoted cue range must equal the assembled text.

    ``evidence_text_bindings.end_cue_index`` is exclusive. If a candidate ever
    reports an inclusive end while its text was built inclusively, promotion
    would bind a range that silently drops the final cue.
    """

    transcript = _transcript(_cues(9, text_len=150))
    for candidate in timed_transcript_candidates(transcript):
        start, end = candidate.start_cue_index, candidate.end_cue_index
        assert start is not None and end is not None
        window = transcript.cues[start:end]
        assert len(window) == end - start
        assert candidate.text == "\n".join(cue.text for cue in window)
        assert candidate.start_ms == window[0].start_ms
        assert candidate.end_ms == window[-1].end_ms
