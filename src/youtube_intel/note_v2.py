"""Deterministic Note V2 derived only from authoritative Deep Analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum

from youtube_intel.deep_analysis_contracts import (
    CanonicalDeepAnalysisInputV1,
    DeepAnalysisExecutionProfileV1,
    DeepAnalysisRequestProjectionV1,
    DeepAnalysisValidationPolicyIdentityV1,
    TrustedDeepAnalysisSuccess,
    dacs1_sha256,
    verify_trusted_deep_analysis_success,
)
from youtube_intel.deep_analysis_persistence import (
    VerifiedPersistedDeepAnalysisRead,
    verify_persisted_deep_analysis_read,
)
from youtube_intel.deep_analysis_runtime import _capture_trusted_success_for_persistence
from youtube_intel.domain import EvidenceRegistry, KnowledgeContent, KnowledgeEvidence
from youtube_intel.notes import _safe_block, _safe_inline


class NoteV2Error(ValueError):
    """Raised when an authoritative Deep Analysis result cannot form Note V2."""


class NoteV2SectionKind(str, Enum):
    SUMMARY = "SUMMARY"
    WHY_IT_MATTERS = "WHY_IT_MATTERS"
    CORE_POINTS = "CORE_POINTS"
    KEY_FACTS = "KEY_FACTS"
    IMPORTANT_CONCEPTS = "IMPORTANT_CONCEPTS"
    KEY_ARGUMENTS = "KEY_ARGUMENTS"
    COUNTERPOINTS = "COUNTERPOINTS"
    PRODUCT_OPPORTUNITIES = "PRODUCT_OPPORTUNITIES"
    BUSINESS_OPPORTUNITIES = "BUSINESS_OPPORTUNITIES"
    ACTIONABLE_DIRECTIONS = "ACTIONABLE_DIRECTIONS"
    HYPOTHESES_TO_VALIDATE = "HYPOTHESES_TO_VALIDATE"
    ACTION_RECOMMENDATIONS = "ACTION_RECOMMENDATIONS"
    RISKS = "RISKS"
    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"
    EVIDENCE = "EVIDENCE"


@dataclass(frozen=True, slots=True)
class NoteV2Entry:
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NoteV2Section:
    kind: NoteV2SectionKind
    entries: tuple[NoteV2Entry, ...]


@dataclass(frozen=True, slots=True)
class NoteV2EvidenceReference:
    evidence_id: str
    source: str
    excerpt: str
    start_seconds: float | None
    end_seconds: float | None


@dataclass(frozen=True, slots=True)
class NoteV2Provenance:
    deep_analysis_result_identity: str
    knowledge_content_identity: str
    a1_identity: str
    a2_identity: str
    a3_identity: str
    validation_policy_identity: str
    evidence_registry_identity: str
    scoring_request_hash: str
    scoring_success_provenance: str
    payload_scope: str
    provider_id: str
    model_id: str


@dataclass(frozen=True, slots=True)
class NoteV2:
    """An ordinary immutable derived artifact; never a new authority source."""

    schema_version: str
    video_id: str
    language: str
    sections: tuple[NoteV2Section, ...]
    evidence_references: tuple[NoteV2EvidenceReference, ...]
    provenance: NoteV2Provenance
    identity: str


@dataclass(frozen=True, slots=True)
class _AuthoritativeNoteSource:
    result_identity: str
    content_identity: str
    content: KnowledgeContent
    registry: EvidenceRegistry
    canonical_input: CanonicalDeepAnalysisInputV1
    request_projection: DeepAnalysisRequestProjectionV1
    execution_profile: DeepAnalysisExecutionProfileV1
    validation_policy: DeepAnalysisValidationPolicyIdentityV1


_SECTION_FIELDS: tuple[tuple[NoteV2SectionKind, str], ...] = (
    (NoteV2SectionKind.KEY_FACTS, "key_facts"),
    (NoteV2SectionKind.IMPORTANT_CONCEPTS, "important_concepts"),
    (NoteV2SectionKind.KEY_ARGUMENTS, "key_arguments"),
    (NoteV2SectionKind.COUNTERPOINTS, "counterpoints"),
    (NoteV2SectionKind.PRODUCT_OPPORTUNITIES, "product_opportunities"),
    (NoteV2SectionKind.BUSINESS_OPPORTUNITIES, "business_opportunities"),
    (NoteV2SectionKind.ACTIONABLE_DIRECTIONS, "actionable_directions"),
    (NoteV2SectionKind.HYPOTHESES_TO_VALIDATE, "hypotheses_to_validate"),
    (NoteV2SectionKind.ACTION_RECOMMENDATIONS, "action_recommendations"),
    (NoteV2SectionKind.RISKS, "risks"),
)

_SECTION_TITLES = {
    NoteV2SectionKind.SUMMARY: "Summary",
    NoteV2SectionKind.WHY_IT_MATTERS: "Why It Matters",
    NoteV2SectionKind.CORE_POINTS: "Core Points",
    NoteV2SectionKind.KEY_FACTS: "Key Facts",
    NoteV2SectionKind.IMPORTANT_CONCEPTS: "Important Concepts",
    NoteV2SectionKind.KEY_ARGUMENTS: "Key Arguments",
    NoteV2SectionKind.COUNTERPOINTS: "Counterpoints",
    NoteV2SectionKind.PRODUCT_OPPORTUNITIES: "Product Opportunities",
    NoteV2SectionKind.BUSINESS_OPPORTUNITIES: "Business Opportunities",
    NoteV2SectionKind.ACTIONABLE_DIRECTIONS: "Actionable Directions",
    NoteV2SectionKind.HYPOTHESES_TO_VALIDATE: "Hypotheses to Validate",
    NoteV2SectionKind.ACTION_RECOMMENDATIONS: "Action Recommendations",
    NoteV2SectionKind.RISKS: "Risks",
    NoteV2SectionKind.KNOWLEDGE_GRAPH: "Knowledge Graph",
    NoteV2SectionKind.EVIDENCE: "Evidence",
}


def build_note_v2(source: object) -> NoteV2:
    """Build Note V2 from a runtime-verified or persisted-verified result only."""

    authoritative = _authoritative_source(source)
    sections = _sections(authoritative.content)
    referenced_ids = _referenced_evidence_ids(sections)
    references = _evidence_references(authoritative.registry, referenced_ids)
    provenance = _provenance(authoritative)
    note = NoteV2(
        schema_version="note-v2",
        video_id=authoritative.canonical_input.video_identity,
        language=authoritative.canonical_input.output_language,
        sections=sections,
        evidence_references=references,
        provenance=provenance,
        identity="",
    )
    note = replace(note, identity=_identity(note))
    _validate_note(note, authoritative)
    return note


def render_note_v2(note: NoteV2) -> str:
    """Render one validated Note V2 as deterministic Markdown without network or model calls."""

    _validate_note(note, None)
    frontmatter = (
        ("type", "video"),
        ("schema_version", note.schema_version),
        ("note_identity", note.identity),
        ("video_id", note.video_id),
        ("language", note.language),
        (
            "deep_analysis_result_identity",
            note.provenance.deep_analysis_result_identity,
        ),
        ("knowledge_content_identity", note.provenance.knowledge_content_identity),
        ("a1_identity", note.provenance.a1_identity),
        ("a2_identity", note.provenance.a2_identity),
        ("a3_identity", note.provenance.a3_identity),
        ("validation_policy_identity", note.provenance.validation_policy_identity),
        ("evidence_registry_identity", note.provenance.evidence_registry_identity),
        ("scoring_request_hash", note.provenance.scoring_request_hash),
        ("scoring_success_provenance", note.provenance.scoring_success_provenance),
        ("payload_scope", note.provenance.payload_scope),
    )
    lines = [
        "---",
        *(
            f"{key}: {json.dumps(value, ensure_ascii=False)}"
            for key, value in frontmatter
        ),
        "---",
        "",
        f"# Video {_safe_inline(note.video_id)}",
        "",
    ]
    for section in note.sections:
        lines.extend((f"## {_SECTION_TITLES[section.kind]}", ""))
        if section.kind is NoteV2SectionKind.KNOWLEDGE_GRAPH:
            for entry in section.entries:
                lines.append(f"- {_safe_inline(entry.text)}")
        elif section.kind is NoteV2SectionKind.EVIDENCE:
            for reference in note.evidence_references:
                timing = _timing(reference)
                lines.append(
                    f"- {_safe_inline(reference.evidence_id)} [{_safe_inline(reference.source)}]{timing}: {_safe_inline(reference.excerpt)}"
                )
        elif section.kind is NoteV2SectionKind.SUMMARY:
            entry = section.entries[0]
            lines.extend((_safe_block(entry.text), _citation_line(entry.evidence_ids)))
        else:
            for entry in section.entries:
                lines.append(
                    f"- {_safe_inline(entry.text)}{_citation_suffix(entry.evidence_ids)}"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _authoritative_source(source: object) -> _AuthoritativeNoteSource:
    if type(source) is TrustedDeepAnalysisSuccess:
        if not verify_trusted_deep_analysis_success(source):
            raise NoteV2Error(
                "authoritative Deep Analysis runtime success is untrusted"
            )
        material = _capture_trusted_success_for_persistence(source)
        if material is None:
            raise NoteV2Error(
                "authoritative Deep Analysis runtime material is unavailable"
            )
        return _AuthoritativeNoteSource(
            result_identity=source.provenance_identity,
            content_identity=source.content_identity,
            content=material.content,
            registry=material.evidence_registry,
            canonical_input=material.envelope.canonical_input,
            request_projection=material.envelope.request_projection,
            execution_profile=material.envelope.execution_profile,
            validation_policy=material.validation_policy,
        )
    if type(source) is VerifiedPersistedDeepAnalysisRead:
        if not verify_persisted_deep_analysis_read(source):
            raise NoteV2Error("authoritative Deep Analysis persisted read is untrusted")
        return _AuthoritativeNoteSource(
            result_identity=source.result_identity,
            content_identity=source.content_identity,
            content=source.content,
            registry=source.evidence_registry,
            canonical_input=source.canonical_input,
            request_projection=source.request_projection,
            execution_profile=source.execution_profile,
            validation_policy=source.validation_policy,
        )
    raise NoteV2Error("Note V2 requires authoritative Deep Analysis input")


def _sections(content: KnowledgeContent) -> tuple[NoteV2Section, ...]:
    sections = [
        NoteV2Section(
            NoteV2SectionKind.SUMMARY,
            (NoteV2Entry(content.one_sentence_summary, content.summary_evidence_ids),),
        ),
        NoteV2Section(
            NoteV2SectionKind.WHY_IT_MATTERS, (_entry(content.why_it_matters),)
        ),
        NoteV2Section(
            NoteV2SectionKind.CORE_POINTS,
            tuple(_entry(point) for point in content.core_points),
        ),
    ]
    for kind, field_name in _SECTION_FIELDS:
        points = getattr(content, field_name)
        if points:
            sections.append(
                NoteV2Section(kind, tuple(_entry(point) for point in points))
            )
    graph_entries = tuple(
        NoteV2Entry(f"{label}: {value}", ())
        for label, values in (
            ("Topics", content.knowledge_graph.topics),
            ("Entities", content.knowledge_graph.entities),
            ("Related themes", content.knowledge_graph.related_themes),
            ("Future watch topics", content.knowledge_graph.future_watch_topics),
        )
        for value in values
    )
    sections.extend(
        (
            NoteV2Section(NoteV2SectionKind.KNOWLEDGE_GRAPH, graph_entries),
            NoteV2Section(NoteV2SectionKind.EVIDENCE, ()),
        )
    )
    return tuple(sections)


def _entry(point: object) -> NoteV2Entry:
    return NoteV2Entry(
        text=getattr(point, "text"), evidence_ids=tuple(getattr(point, "evidence_ids"))
    )


def _referenced_evidence_ids(sections: tuple[NoteV2Section, ...]) -> frozenset[str]:
    return frozenset(
        evidence_id
        for section in sections
        for entry in section.entries
        for evidence_id in entry.evidence_ids
    )


def _evidence_references(
    registry: EvidenceRegistry, referenced_ids: frozenset[str]
) -> tuple[NoteV2EvidenceReference, ...]:
    found = {item.evidence_id for item in registry.items}
    missing = referenced_ids - found
    if missing:
        raise NoteV2Error(f"evidence provenance mismatch: {sorted(missing)}")
    return tuple(
        _reference(item)
        for item in registry.items
        if item.evidence_id in referenced_ids
    )


def _reference(item: KnowledgeEvidence) -> NoteV2EvidenceReference:
    return NoteV2EvidenceReference(
        item.evidence_id,
        item.source.value,
        item.excerpt,
        item.start_seconds,
        item.end_seconds,
    )


def _provenance(source: _AuthoritativeNoteSource) -> NoteV2Provenance:
    return NoteV2Provenance(
        deep_analysis_result_identity=source.result_identity,
        knowledge_content_identity=source.content_identity,
        a1_identity=source.canonical_input.a1_identity,
        a2_identity=source.request_projection.a2_identity,
        a3_identity=source.execution_profile.a3_identity,
        validation_policy_identity=source.validation_policy.identity,
        evidence_registry_identity=source.canonical_input.evidence_registry_identity,
        scoring_request_hash=source.canonical_input.scoring_request_hash,
        scoring_success_provenance=source.canonical_input.scoring_success_provenance,
        payload_scope=source.request_projection.payload_scope.value,
        provider_id=source.execution_profile.provider_id,
        model_id=source.execution_profile.model_selection.model_id,
    )


def _identity(note: NoteV2) -> str:
    return dacs1_sha256(
        {
            "schema_version": note.schema_version,
            "video_id": note.video_id,
            "language": note.language,
            "sections": [
                {
                    "kind": section.kind.value,
                    "entries": [
                        {"text": entry.text, "evidence_ids": list(entry.evidence_ids)}
                        for entry in section.entries
                    ],
                }
                for section in note.sections
            ],
            "evidence_references": [
                {
                    "evidence_id": ref.evidence_id,
                    "source": ref.source,
                    "excerpt": ref.excerpt,
                    "start_seconds": ref.start_seconds,
                    "end_seconds": ref.end_seconds,
                }
                for ref in note.evidence_references
            ],
            "provenance": {
                "deep_analysis_result_identity": note.provenance.deep_analysis_result_identity,
                "knowledge_content_identity": note.provenance.knowledge_content_identity,
                "a1_identity": note.provenance.a1_identity,
                "a2_identity": note.provenance.a2_identity,
                "a3_identity": note.provenance.a3_identity,
                "validation_policy_identity": note.provenance.validation_policy_identity,
                "evidence_registry_identity": note.provenance.evidence_registry_identity,
                "scoring_request_hash": note.provenance.scoring_request_hash,
                "scoring_success_provenance": note.provenance.scoring_success_provenance,
                "payload_scope": note.provenance.payload_scope,
                "provider_id": note.provenance.provider_id,
                "model_id": note.provenance.model_id,
            },
        }
    )


def _validate_note(note: NoteV2, source: _AuthoritativeNoteSource | None) -> None:
    if type(note) is not NoteV2 or note.schema_version != "note-v2":
        raise NoteV2Error("Note V2 schema is invalid")
    if not note.video_id or not note.language:
        raise NoteV2Error("Note V2 source metadata is invalid")
    expected = [
        NoteV2SectionKind.SUMMARY,
        NoteV2SectionKind.WHY_IT_MATTERS,
        NoteV2SectionKind.CORE_POINTS,
    ]
    expected.extend(
        kind
        for kind, field_name in _SECTION_FIELDS
        if any(section.kind is kind for section in note.sections)
    )
    expected.extend((NoteV2SectionKind.KNOWLEDGE_GRAPH, NoteV2SectionKind.EVIDENCE))
    if [section.kind for section in note.sections] != expected:
        raise NoteV2Error("Note V2 section ordering is invalid")
    if any(
        not section.entries
        for section in note.sections
        if section.kind not in {NoteV2SectionKind.EVIDENCE}
    ):
        raise NoteV2Error("Note V2 required section is empty")
    evidence_ids = {reference.evidence_id for reference in note.evidence_references}
    cited = _referenced_evidence_ids(note.sections)
    if cited != evidence_ids:
        raise NoteV2Error("Note V2 evidence references are invalid")
    if note.identity != _identity(note):
        raise NoteV2Error("Note V2 semantic identity is invalid")
    if source is not None:
        if (
            note.video_id != source.canonical_input.video_identity
            or note.language != source.canonical_input.output_language
            or note.provenance != _provenance(source)
            or note.provenance.knowledge_content_identity != source.content_identity
            or note.sections != _sections(source.content)
            or note.evidence_references
            != _evidence_references(
                source.registry,
                _referenced_evidence_ids(note.sections),
            )
        ):
            raise NoteV2Error("Note V2 provenance binding is invalid")


def _citation_suffix(evidence_ids: tuple[str, ...]) -> str:
    return (
        ""
        if not evidence_ids
        else " (Evidence: "
        + ", ".join(_safe_inline(item) for item in evidence_ids)
        + ")"
    )


def _citation_line(evidence_ids: tuple[str, ...]) -> str:
    return "Evidence: " + ", ".join(_safe_inline(item) for item in evidence_ids)


def _timing(reference: NoteV2EvidenceReference) -> str:
    if reference.start_seconds is None:
        return ""
    assert reference.end_seconds is not None
    return f" ({reference.start_seconds:g}s–{reference.end_seconds:g}s)"
