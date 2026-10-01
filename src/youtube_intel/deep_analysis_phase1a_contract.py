"""Phase-1A Deep Analysis model contract and compatibility mapping.

The frozen ADR-027 runtime persists a full ``KnowledgeContent`` object, and the
qualified local adapter renders ``KnowledgeContent.model_json_schema()`` into its
prompt. That contract still contains fields which model-answerable Phase-1A work
must not request:

- ``knowledge_graph.related_themes`` and ``knowledge_graph.future_watch_topics``
  ask the model to infer relations to a personal knowledge context that is not
  supplied, which is exactly the deferred ``RELATION_TO_KNOWLEDGE`` /
  ``KNOWLEDGE_DELTA`` territory.

Hiding those fields in the UI is not sufficient. This module fixes the **live
model boundary**: the model is asked only for the five first-version concepts and
the compatibility fields are filled deterministically by the backend.

``RELATION_TO_KNOWLEDGE`` and ``KNOWLEDGE_DELTA`` remain deferred. Phase 1B owns
the final versioned five-role durable contract; this is the smallest seam that
makes the activated production path honest today.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from youtube_intel.domain import (
    AnalysisPoint,
    EvidenceSource,
    KnowledgeContent,
    KnowledgeGraph,
    PointKind,
)

#: The only concepts the Phase-1A model may author.
PHASE_1A_MODEL_CONCEPTS: tuple[str, ...] = (
    "core_conclusion",
    "key_evidence",
    "uncertainty",
    "relevance_to_user",
    "next_question",
)

#: Field names the model must never be asked to author. These correspond to the
#: deferred roles and to knowledge-graph relation inference.
DEFERRED_MODEL_FIELDS: frozenset[str] = frozenset(
    {
        "relation_to_knowledge",
        "knowledge_delta",
        "related_themes",
        "future_watch_topics",
    }
)


class DeepAnalysisClaimV1(BaseModel):
    """One model-authored claim: text plus an honest epistemic type."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    point_kind: Literal["fact", "inference", "recommendation"]


class DeepAnalysisPhase1AModelOutput(BaseModel):
    """The complete Phase-1A model response.

    Every field here maps to one of the five frozen first-version concepts. There
    is deliberately no knowledge-graph or knowledge-relation field, so the model
    cannot be asked to infer them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["v1x-content-deep-analysis-model-output-v1"] = (
        "v1x-content-deep-analysis-model-output-v1"
    )
    core_conclusion: tuple[DeepAnalysisClaimV1, ...] = Field(min_length=1, max_length=10)
    key_evidence: tuple[DeepAnalysisClaimV1, ...] = Field(min_length=1, max_length=20)
    uncertainty: tuple[DeepAnalysisClaimV1, ...] = Field(default=(), max_length=20)
    relevance_to_user: tuple[DeepAnalysisClaimV1, ...] = Field(
        default=(), max_length=20
    )
    next_question: tuple[DeepAnalysisClaimV1, ...] = Field(default=(), max_length=20)


def phase_1a_model_schema_json() -> str:
    """The exact JSON Schema shown to the model.

    The runtime validates this against :class:`DeepAnalysisPhase1AModelOutput`, so
    a request containing a deferred field is impossible to satisfy legitimately.
    """

    return json.dumps(
        DeepAnalysisPhase1AModelOutput.model_json_schema(),
        separators=(",", ":"),
        sort_keys=True,
    )


def build_phase_1a_prompt(*, output_language: str, payload_json: str) -> str:
    """Render the live Phase-1A provider prompt.

    The prompt names only the five permitted concepts and states the exclusions
    explicitly, so the model is never asked for relation-to-knowledge or
    knowledge-delta content.
    """

    return (
        "Analyze the provided Content and return exactly one JSON object in the "
        "requested output language. Use only the authorized payload below. Do not "
        "add Markdown, commentary, or surrounding text.\n"
        f"Output language: {output_language}.\n"
        "Report exactly these five concepts and nothing else:\n"
        "1. core_conclusion - the main conclusions this content supports.\n"
        "2. key_evidence - the specific evidence supporting those conclusions.\n"
        "3. uncertainty - what is uncertain, contested, or unverified.\n"
        "4. relevance_to_user - what this means for the reader.\n"
        "5. next_question - what should be investigated next.\n"
        "Do NOT infer or report the relation of this content to the user's existing "
        "knowledge, any knowledge delta, related themes, entities, or future watch "
        "topics. Those are deliberately excluded and are not derivable from the "
        "provided payload. Omit them entirely.\n"
        f"JSON Schema: {phase_1a_model_schema_json()}\n"
        f"Authorized payload: {payload_json}"
    )


def _point(claim: DeepAnalysisClaimV1, evidence_ids: tuple[str, ...]) -> AnalysisPoint:
    return AnalysisPoint(
        text=claim.text,
        kind=PointKind(claim.point_kind),
        evidence_ids=evidence_ids,
    )


def map_phase_1a_output_to_knowledge_content(
    output: DeepAnalysisPhase1AModelOutput,
    *,
    summary_evidence_ids: tuple[str, ...],
) -> KnowledgeContent:
    """Map the five-concept output into the frozen persistence structure.

    This is a **compatibility mapping**, not a second content contract:

    - ``knowledge_graph.topics`` is populated from the content's own conclusion
      text so the frozen KG2 validator has a required value.
    - ``entities``, ``related_themes``, and ``future_watch_topics`` are set empty
      and are never model-authored. They are compatibility fields only and are
      never projected to the user.
    """

    if not summary_evidence_ids:
        msg = "compatibility mapping requires at least one selected Evidence ref"
        raise ValueError(msg)
    core = [_point(claim, summary_evidence_ids) for claim in output.core_conclusion]
    key_evidence = [
        _point(claim, summary_evidence_ids) for claim in output.key_evidence
    ]
    why_it_matters = (
        _point(output.relevance_to_user[0], summary_evidence_ids)
        if output.relevance_to_user
        else _point(output.core_conclusion[0], summary_evidence_ids)
    )
    return KnowledgeContent(
        one_sentence_summary=output.core_conclusion[0].text,
        summary_evidence_ids=summary_evidence_ids,
        why_it_matters=why_it_matters,
        core_points=tuple(core),
        key_facts=tuple(key_evidence),
        key_arguments=(),
        important_concepts=(),
        counterpoints=tuple(
            _point(claim, summary_evidence_ids) for claim in output.uncertainty
        ),
        risks=(),
        actionable_directions=tuple(
            _point(claim, summary_evidence_ids)
            for claim in output.relevance_to_user[1:]
        ),
        action_recommendations=(),
        hypotheses_to_validate=tuple(
            _point(claim, summary_evidence_ids) for claim in output.next_question
        ),
        product_opportunities=(),
        business_opportunities=(),
        knowledge_graph=KnowledgeGraph(
            topics=(output.core_conclusion[0].text,),
            entities=(),
            related_themes=(),
            future_watch_topics=(),
        ),
    )


def model_visible_evidence_source() -> EvidenceSource:
    """The Evidence source class the Phase-1A model may cite.

    Transcript-only, matching the frozen rule that metadata is context and never
    citation authority.
    """

    return EvidenceSource.TRANSCRIPT_SAMPLE