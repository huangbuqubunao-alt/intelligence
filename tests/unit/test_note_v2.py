"""TASK-016E Note V2 authoritative-input boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from youtube_intel.domain import (
    AnalysisPoint,
    KnowledgeContent,
    KnowledgeGraph,
    PointKind,
)
from youtube_intel.note_v2 import NoteV2Error, build_note_v2


def _content() -> KnowledgeContent:
    return KnowledgeContent(
        one_sentence_summary="A verified summary.",
        summary_evidence_ids=("e1",),
        why_it_matters=AnalysisPoint(
            text="The verified inference matters.",
            kind=PointKind.INFERENCE,
            evidence_ids=("e1",),
        ),
        core_points=(
            AnalysisPoint(
                text="A verified fact.", kind=PointKind.FACT, evidence_ids=("e1",)
            ),
        ),
        knowledge_graph=KnowledgeGraph(topics=("workflow",)),
    )


def test_raw_knowledge_content_cannot_construct_a_note_v2() -> None:
    with pytest.raises(NoteV2Error, match="authoritative Deep Analysis"):
        build_note_v2(_content())


def test_runtime_success_lookalike_cannot_construct_a_note_v2() -> None:
    from youtube_intel.deep_analysis_contracts import TrustedDeepAnalysisSuccess

    lookalike = object.__new__(TrustedDeepAnalysisSuccess)
    object.__setattr__(lookalike, "_content_identity", "a" * 64)
    object.__setattr__(lookalike, "_cache_identity", "b" * 64)
    object.__setattr__(lookalike, "_provenance_identity", "c" * 64)
    object.__setattr__(lookalike, "_sealed", True)

    with pytest.raises(NoteV2Error, match="runtime success is untrusted"):
        build_note_v2(lookalike)


def test_note_v2_source_has_no_provider_or_llm_invocation() -> None:
    source = Path("src/youtube_intel/note_v2.py").read_text(encoding="utf-8").casefold()

    for forbidden in ("openai", "ollama", "http", ".dispatch(", ".finalize("):
        assert forbidden not in source
