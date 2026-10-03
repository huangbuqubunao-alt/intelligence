"""Semantic identity and ordering of the pure product projection."""

import pytest

from youtube_intel.research_contract import (
    ResearchContent,
    ResearchEvidence,
    ResearchIntelligence,
    ResearchPacket,
)
from youtube_intel.research_diff import project_diff


def packet(**updates):
    data = dict(research_id="a" * 64, execution_id="0" * 32, execution_number=1,
        question="Question", output_language="en", assembled_at="2026-10-03T08:00:00Z",
        scope=[ResearchContent(content_id="one", title="Same label"), ResearchContent(content_id="two", title="Same label")],
        material_status="EVIDENCE_AVAILABLE", evidence=[evidence("b"), evidence("a")], intelligence=[],
        evidence_candidates=2, intelligence_candidates=0, retrieval_truncated=False, unresolved=["NO_SYNTHESIS", "LEXICAL_RETRIEVAL"])
    data.update(updates)
    return ResearchPacket(**data)


def evidence(identity):
    return ResearchEvidence(evidence_id=identity, content_id="one", artifact_id="artifact", excerpt="Original source.",
        excerpt_hash="e" * 64, timed_transcript_hash="t" * 64, start_ms=1, end_ms=2, source_language="en",
        lineage_kind="ORIGINAL_TRANSCRIPT", role="PRIMARY_ORIGINAL", created_at="2026-10-02T08:00:00Z")


def interpretation(identity="i", **updates):
    data = dict(intelligence_id=identity, revision_id="r" + identity, content_id="one", source_id="s",
        conclusion="Original interpretation", claim_kind="OPINION", state="NEW", evidence_ids=["a", "b"], stances=["supporting", "contradicting"])
    data.update(updates)
    return ResearchIntelligence(**data)


def test_all_order_only_changes_are_ignored_and_stances_stay_paired():
    first = packet(intelligence=[interpretation("i"), interpretation("j")], intelligence_candidates=2)
    target = packet(scope=list(reversed(first.scope)), evidence=list(reversed(first.evidence)),
        intelligence=[f.model_copy(update={"evidence_ids": list(reversed(f.evidence_ids)), "stances": list(reversed(f.stances))}) for f in reversed(first.intelligence)],
        intelligence_candidates=2, unresolved=list(reversed(first.unresolved)), execution_id="1" * 32, execution_number=2)
    assert project_diff("base", first, "target", target).no_material_changes
    unpaired = target.model_copy(update={"intelligence": [interpretation("i", stances=["contradicting", "supporting"]), interpretation("j")]})
    diff = project_diff("base", first, "target", unpaired)
    assert len(diff.interpretations.added) == len(diff.interpretations.removed) == 1
    assert not diff.packet_changes  # Truthfully replace an interpretation.


@pytest.mark.parametrize("field,value", [("conclusion", "New interpretation"), ("state", "UPDATED"), ("claim_kind", "SYSTEM_INFERENCE"), ("revision_id", "newer-r")])
def test_structured_interpretation_changes_are_remove_and_add(field, value):
    first = packet(intelligence=[interpretation()], intelligence_candidates=1)
    target = first.model_copy(update={"intelligence": [interpretation(**{field: value})]})
    diff = project_diff("base", first, "target", target)
    assert len(diff.interpretations.added) == len(diff.interpretations.removed) == 1
    assert diff.interpretations.added[0].id != diff.interpretations.removed[0].id
    assert diff.summary.changed == 0


@pytest.mark.parametrize("update", [{"question": "Other"}, {"output_language": "zh-CN"}, {"scope": [ResearchContent(content_id="foreign", title="Same label")]}, {"research_id": "b" * 64}])
def test_identity_contract_cannot_be_normalized_away(update):
    first = packet()
    with pytest.raises(ValueError, match="incompatible Research identity"):
        project_diff("base", first, "target", first.model_copy(update=update))


def test_max_disjoint_sets_are_complete_and_deterministically_sorted():
    first = packet(evidence=[evidence(f"old-{i:02d}") for i in range(24)], evidence_candidates=24)
    target = packet(evidence=[evidence(f"new-{i:02d}") for i in reversed(range(24))], evidence_candidates=24)
    diff = project_diff("base", first, "target", target)
    assert diff.complete and len(diff.evidence.added) == len(diff.evidence.removed) == 24
    assert [e.evidence_id for e in diff.evidence.added] == sorted(e.evidence_id for e in target.evidence)
    assert project_diff("base", first, "target", target) == diff
    reversed_diff = project_diff("target", target, "base", first)
    assert reversed_diff.evidence.removed == diff.evidence.added
    assert reversed_diff.evidence.added == diff.evidence.removed
