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
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    @model_validator(mode="after")
    def _carrier_compatible(self) -> Self:
        """Enforce carrier representability at the model-contract boundary.

        The frozen persistence carrier constrains epistemic kinds more strictly
        than this schema. Rejecting an unrepresentable combination here guarantees
        every accepted payload maps without an uncaught ``ValidationError`` and
        without ever rewriting a claim's ``point_kind``.
        """

        _validate_carrier_compatibility(self)
        return self


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


#: Epistemic kinds accepted by the Phase-1A model schema.
PHASE_1A_POINT_KINDS: tuple[str, ...] = ("fact", "inference", "recommendation")

#: Carrier-field rules per Phase-1A role.
#:
#: Each Phase-1A role is routed to a historical carrier field chosen so the
#: frozen ``KnowledgeContent`` validator can represent that role **honestly**.
#: The historical fields impose stricter epistemic constraints than the Phase-1A
#: schema, so a role is only routed to a field that accepts every kind the role
#: permits. ``point_kind`` is never rewritten to satisfy a validator.
#:
#: ``key_evidence`` routes to ``key_facts``, which requires ``fact``. A Phase-1A
#: payload may legitimately declare key evidence as ``inference`` or
#: ``recommendation``, so the schema itself rejects that combination with a clear
#: contract rule rather than the mapper crashing or silently relabelling it.
_CARRIER_RULES: dict[str, tuple[str, frozenset[str]]] = {
    "core_conclusion": ("core_points", frozenset({"fact", "inference"})),
    "uncertainty": ("counterpoints", frozenset({"inference"})),
    "relevance_to_user": ("product_opportunities", frozenset({"inference"})),
    "next_question": ("hypotheses_to_validate", frozenset({"inference"})),
}

#: Maximum number of claims each role may carry.
#:
#: These match the frozen carrier field limits, so an accepted payload can
#: always be mapped in full. Truncating silently would drop model content and
#: misrepresent the response, so an oversized role is rejected by contract rule
#: instead.
ROLE_MAX_CLAIMS: dict[str, int] = {
    "core_conclusion": 10,
    "key_evidence": 20,
    "uncertainty": 10,
    "relevance_to_user": 10,
    "next_question": 10,
}


def _validate_carrier_compatibility(output: DeepAnalysisPhase1AModelOutput) -> None:
    """Reject payloads the carrier cannot represent faithfully.

    This is a contract rule at the Phase-1A schema boundary, not a silent
    rewrite. It guarantees that every accepted payload maps without an uncaught
    ``ValidationError`` and without changing any claim's epistemic meaning.
    """

    for role, limit in ROLE_MAX_CLAIMS.items():
        count = len(getattr(output, role))
        if count > limit:
            msg = (
                f"{role} carries {count} claims but the compatibility carrier "
                f"field holds at most {limit}; extra claims are never dropped "
                "silently"
            )
            raise ValueError(msg)
    for role, (field_name, allowed) in _CARRIER_RULES.items():
        for index, claim in enumerate(getattr(output, role)):
            if claim.point_kind not in allowed:
                permitted = ", ".join(sorted(allowed))
                msg = (
                    f"{role}[{index}] point_kind {claim.point_kind!r} cannot be "
                    f"represented faithfully; the compatibility carrier field "
                    f"{field_name} requires one of: {permitted}"
                )
                raise ValueError(msg)
    for index, claim in enumerate(output.key_evidence):
        if claim.point_kind != "fact":
            msg = (
                f"key_evidence[{index}] point_kind {claim.point_kind!r} cannot be "
                "represented faithfully; the compatibility carrier field key_facts "
                "requires 'fact'"
            )
            raise ValueError(msg)



def map_phase_1a_output_to_knowledge_content(
    output: DeepAnalysisPhase1AModelOutput,
    *,
    summary_evidence_ids: tuple[str, ...],
) -> KnowledgeContent:
    """Map the five-concept output into the frozen persistence carrier.

    This is a **compatibility mapping**, not a second content contract:

    - Each role is routed to a carrier field whose frozen validator accepts that
      role's epistemic kinds, so no ``point_kind`` is ever rewritten.
    - ``knowledge_graph.topics`` is populated from the content's own conclusion
      text because the frozen validator requires it. These are **internal carrier
      data only**: they are not a product Topic, not Intelligence, and not
      Knowledge Delta. Trusted Note/export eligibility is disabled for Phase-1A,
      so they never reach any trusted projection.
    - ``entities``, ``related_themes``, and ``future_watch_topics`` stay empty
      and are never model-authored or presented.

    Raises ``ValueError`` for any payload the carrier cannot represent
    faithfully; callers validate that rule before reaching this function.
    """

    if not summary_evidence_ids:
        msg = "compatibility mapping requires at least one selected Evidence ref"
        raise ValueError(msg)
    _validate_carrier_compatibility(output)

    def point(claim: DeepAnalysisClaimV1) -> AnalysisPoint:
        return AnalysisPoint(
            text=claim.text,
            kind=PointKind(claim.point_kind),
            evidence_ids=summary_evidence_ids,
        )

    return KnowledgeContent(
        one_sentence_summary=output.core_conclusion[0].text,
        summary_evidence_ids=summary_evidence_ids,
        # Relevance to the user is an inference about the reader, represented by
        # the same inference-typed carrier fields the frozen contract allows.
        why_it_matters=point(
            output.relevance_to_user[0]
            if output.relevance_to_user
            else output.core_conclusion[0]
        ),
        core_points=tuple(point(claim) for claim in output.core_conclusion),
        key_facts=tuple(point(claim) for claim in output.key_evidence),
        key_arguments=(),
        important_concepts=(),
        counterpoints=tuple(point(claim) for claim in output.uncertainty),
        risks=(),
        product_opportunities=tuple(
            point(claim) for claim in output.relevance_to_user
        ),
        business_opportunities=(),
        actionable_directions=(),
        action_recommendations=(),
        hypotheses_to_validate=tuple(point(claim) for claim in output.next_question),
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