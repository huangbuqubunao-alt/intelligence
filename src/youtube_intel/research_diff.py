"""Typed, bounded product projection of two trusted Research snapshots.

No repository, retrieval, provider or persistence dependency belongs here.
"""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import Field

from youtube_intel.research_contract import (
    CONTRACT,
    MAX_CONTENT,
    MAX_EVIDENCE,
    MAX_INTELLIGENCE,
    ResearchContent,
    ResearchPacket,
    ResearchValue,
    digest,
)


class DiffRevision(ResearchValue):
    revision_id: str
    execution_number: int
    assembled_at: str
    scope: list[ResearchContent]


class DiffContent(ResearchValue):
    id: str
    content_id: str
    title: str | None


class DiffEvidence(ResearchValue):
    id: str
    evidence_id: str
    content_id: str
    title: str | None
    excerpt: str
    start_ms: int | None
    end_ms: int | None
    locator_type: str = "TIMED_MEDIA"
    start_line: int | None = None
    end_line: int | None = None
    provider: str = "YOUTUBE"
    source_language: str
    lineage_kind: Literal["ORIGINAL_TRANSCRIPT", "EXTRACTION"]


class DiffCitation(ResearchValue):
    evidence_id: str
    stance: str | None


class DiffInterpretation(ResearchValue):
    id: str
    intelligence_id: str
    revision_id: str
    content_id: str
    title: str | None
    conclusion: str
    claim_kind: str
    state: str
    citations: list[DiffCitation]


Entry = TypeVar("Entry", bound=ResearchValue)


class DiffGroup(ResearchValue, Generic[Entry]):
    added: list[Entry] = Field(max_length=MAX_EVIDENCE)
    removed: list[Entry] = Field(max_length=MAX_EVIDENCE)
    unchanged_count: int


class DiffPacketChange(ResearchValue):
    id: str
    field: Literal["material_status", "evidence_candidates", "intelligence_candidates", "retrieval_truncated", "unresolved"]
    base: str | int | bool | list[str]
    target: str | int | bool | list[str]


class DiffSummary(ResearchValue):
    added: int
    removed: int
    changed: int


class ResearchDiff(ResearchValue):
    contract: Literal["research-diff-v1"] = "research-diff-v1"
    packet_contract: Literal["research-lite-v1"] = CONTRACT
    research_id: str
    question: str
    output_language: Literal["zh-CN", "en"]
    base: DiffRevision
    target: DiffRevision
    summary: DiffSummary
    no_material_changes: bool
    content: DiffGroup[DiffContent]
    evidence: DiffGroup[DiffEvidence]
    interpretations: DiffGroup[DiffInterpretation]
    packet_changes: list[DiffPacketChange] = Field(max_length=5)
    # Full packet comparison, not a comparison of the unbounded library.
    complete: Literal[True] = True
    content_limit_per_side: int = MAX_CONTENT
    evidence_limit_per_side: int = MAX_EVIDENCE
    interpretation_limit_per_side: int = MAX_INTELLIGENCE


def _group(base: dict[str, Entry], target: dict[str, Entry]) -> DiffGroup[Entry]:
    return DiffGroup[Entry](
        added=[target[key] for key in sorted(target.keys() - base.keys())],
        removed=[base[key] for key in sorted(base.keys() - target.keys())],
        unchanged_count=len(base.keys() & target.keys()),
    )


def _content(packet: ResearchPacket) -> dict[str, DiffContent]:
    referenced = {e.content_id for e in packet.evidence} | {f.content_id for f in packet.intelligence}
    return {c.content_id: DiffContent(id=f"content:{c.content_id}", content_id=c.content_id, title=c.title)
            for c in packet.scope if c.content_id in referenced}


def _evidence(packet: ResearchPacket) -> dict[str, DiffEvidence]:
    titles = {c.content_id: c.title for c in packet.scope}
    return {e.evidence_id: DiffEvidence(
        id=f"evidence:{e.evidence_id}", evidence_id=e.evidence_id,
        content_id=e.content_id, title=titles[e.content_id], excerpt=e.excerpt,
        start_ms=e.start_ms, end_ms=e.end_ms, source_language=e.source_language,
        locator_type=e.locator_type,start_line=e.start_line,end_line=e.end_line,provider=e.provider,
        lineage_kind=e.lineage_kind,
    ) for e in packet.evidence}


def _interpretations(packet: ResearchPacket) -> dict[str, DiffInterpretation]:
    titles = {c.content_id: c.title for c in packet.scope}
    entries = {}
    for finding in packet.intelligence:
        # Evidence and its stance are one relation; never sort the arrays separately.
        citations = [DiffCitation(evidence_id=eid, stance=stance) for eid, stance in
                     sorted(zip(finding.evidence_ids, finding.stances, strict=True))]
        identity = digest({
            "intelligence_id": finding.intelligence_id, "revision_id": finding.revision_id,
            "content_id": finding.content_id, "source_id": finding.source_id,
            "conclusion": finding.conclusion, "claim_kind": finding.claim_kind,
            "state": finding.state, "citations": [c.model_dump() for c in citations],
        })
        entries[identity] = DiffInterpretation(
            id=f"interpretation:{identity}", intelligence_id=finding.intelligence_id,
            revision_id=finding.revision_id, content_id=finding.content_id,
            title=titles[finding.content_id], conclusion=finding.conclusion,
            claim_kind=finding.claim_kind, state=finding.state, citations=citations,
        )
    return entries


def project_diff(base_id: str, base: ResearchPacket, target_id: str, target: ResearchPacket) -> ResearchDiff:
    """Caller must independently trust both snapshots before projecting them."""
    if (base.research_id, base.contract, base.question, base.output_language, base.scope_kind,
        sorted(c.content_id for c in base.scope)) != (
        target.research_id, target.contract, target.question, target.output_language, target.scope_kind,
        sorted(c.content_id for c in target.scope)
    ):
        raise ValueError("incompatible Research identity")
    content = _group(_content(base), _content(target))
    evidence = _group(_evidence(base), _evidence(target))
    interpretations = _group(_interpretations(base), _interpretations(target))
    changes: list[DiffPacketChange] = []
    fields: tuple[Literal["material_status", "evidence_candidates", "intelligence_candidates", "retrieval_truncated", "unresolved"], ...] = (
        "material_status", "evidence_candidates", "intelligence_candidates", "retrieval_truncated", "unresolved",
    )
    for field in fields:
        old, new = getattr(base, field), getattr(target, field)
        if field == "unresolved":
            old, new = sorted(set(old)), sorted(set(new))
        if old != new:
            changes.append(DiffPacketChange(id=f"packet:{field}", field=field, base=old, target=new))
    summary = DiffSummary(
        added=len(content.added) + len(evidence.added) + len(interpretations.added),
        removed=len(content.removed) + len(evidence.removed) + len(interpretations.removed),
        changed=len(changes),
    )
    return ResearchDiff(
        research_id=base.research_id, question=base.question, output_language=base.output_language,
        base=DiffRevision(revision_id=base_id, execution_number=base.execution_number, assembled_at=base.assembled_at, scope=base.scope),
        target=DiffRevision(revision_id=target_id, execution_number=target.execution_number, assembled_at=target.assembled_at, scope=target.scope),
        summary=summary, no_material_changes=not (summary.added or summary.removed or summary.changed),
        content=content, evidence=evidence, interpretations=interpretations, packet_changes=changes,
    )
