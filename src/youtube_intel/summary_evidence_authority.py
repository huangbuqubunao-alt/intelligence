"""Shared backend-authoritative Summary Evidence hydration (M13 Summary P1).

This module is the single authority boundary between a provider's
:class:`~youtube_intel.summary_draft.SummaryDraft` and the hydrated,
persisted ``AnalysisResult.evidence``.

The frozen invariant:

    The LLM may interpret Evidence, select Evidence, and cite Evidence.
    The LLM may not author Evidence text, offsets, timestamps, or trusted ids.

Concretely, a draft carries only ``evidence_refs``. Every excerpt written into
the hydrated result is taken from the backend-issued
:class:`~youtube_intel.summary_evidence_candidates.TrustedEvidenceRegistry`
that was actually presented to the model for this request. A ref the backend
never issued fails closed; the model cannot widen its own authority.

The candidate ``ref`` is a *temporary model-facing* identifier. It exists only
across the model interaction boundary. This module resolves every selected ref
to the durable ``build_evidence_id`` identity that promotion persists, and the
hydrated result carries only that durable identity, so no temporary ref can
survive into a persisted or user-visible authoritative Evidence citation.

Metadata candidates (title, channel name, description) are legitimate Summary
context but have no timed-cue identity and therefore no durable Evidence
identity. Citing one as evidence fails closed as a known response validation
failure; no timestamp is fabricated and no Evidence row is minted.

Promotion of a selected timed-transcript span into the durable
``evidence`` / ``evidence_text_bindings`` substrate is expressed as a
:class:`SummaryEvidencePromotion` plan. Executing that plan against the
repository is a separate, later concern so it can be composed into the
ANALYSIS stage transaction. The durable identity is deterministic, so it is
known before any row is committed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol

from youtube_intel.domain import EvidenceExcerpt, EvidenceSource
from youtube_intel.state import (
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    build_evidence_id,
)
from youtube_intel.summary_draft import SUMMARY_DRAFT_PROMPT_VERSION, SummaryDraft
from youtube_intel.summary_evidence_candidates import (
    TrustedEvidenceCandidate,
    TrustedEvidenceRegistry,
)

SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE: Final = (
    "SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE"
)

SUMMARY_EVIDENCE_REF_NOT_CITABLE: Final = "SUMMARY_EVIDENCE_REF_NOT_CITABLE"

#: The live Summary write contract.  Only a result produced under this prompt
#: identity carries durable Evidence citations, so only this identity is
#: eligible to be *current trusted Summary authority*.
CURRENT_SUMMARY_PROMPT_VERSION: Final = SUMMARY_DRAFT_PROMPT_VERSION

#: Every Summary prompt identity the persisted parser still accepts.  This is a
#: READABILITY set only.  Widening it must never make an old citation trusted.
HISTORICAL_SUMMARY_PROMPT_VERSIONS: Final = (
    "analysis-prompt-v1",
    "analysis-prompt-v2",
    "analysis-prompt-v3",
    "analysis-prompt-v4",
    "analysis-prompt-v5",
    CURRENT_SUMMARY_PROMPT_VERSION,
)

#: Candidate sources that are legitimate Summary context but are never
#: authoritative Evidence.  They have no timed-cue identity, so no durable
#: ``evidence_id`` exists for them and none is fabricated.
_NON_CITABLE_SOURCES: Final = frozenset(
    {EvidenceSource.TITLE, EvidenceSource.CHANNEL_NAME, EvidenceSource.DESCRIPTION}
)


class SummaryEvidenceAuthorityError(ValueError):
    """The draft cannot be hydrated into authoritative Evidence. Fail closed."""


class SummaryEvidenceAuthorityUnavailable(SummaryEvidenceAuthorityError):
    """Durable Evidence authority does not exist for this Content.

    Raised for canonical-only Content: the candidate projection may exist, but
    the durable Evidence substrate requires timed-cue identity. Rather than
    fabricate timestamps or fall back to legacy model-authored excerpt
    grounding, promotion fails closed. Owner decision: no migration in V1.
    """


class SummaryEvidenceRefNotCitable(SummaryEvidenceAuthorityError):
    """The provider cited a non-citable context ref as authoritative Evidence.

    This is a known response validation failure: the model answered, the answer
    is simply illegal.  It is never a dispatch ambiguity and never a silent
    drop of the offending ref from the claim.
    """


class LegacySummaryNotCurrentAuthority(SummaryEvidenceAuthorityError):
    """A readable historical Summary is not eligible as current authority.

    Historical ``analysis-prompt-v1``..``v5`` artifacts stay parseable and
    inspectable.  They are *not* eligible to be the current trusted Summary,
    because their citations are temporary model-facing refs rather than durable
    ``evidence.evidence_id`` values.  The narrow response is a truthful
    regeneration-required state, never a rewrite of the stored artifact.
    """


class SummaryCitationNotDurable(SummaryEvidenceAuthorityError):
    """A current-identity Summary carries a citation that does not resolve.

    This is defense in depth.  Even a result whose ``prompt_version`` claims the
    current contract must prove every authoritative citation resolves through
    the repository before it may be reused as current trusted Summary authority.
    """


@dataclass(frozen=True, slots=True)
class SummaryEvidencePromotion:
    """Everything the repository needs to promote one selected span.

    ``start_cue_index`` is inclusive and ``end_cue_index`` is **exclusive**,
    matching ``evidence_text_bindings``. ``excerpt`` is the backend-built text
    for exactly that half-open cue range.
    """

    evidence_id: str
    video_id: str
    canonical_artifact_id: str
    timed_transcript_id: str
    timed_transcript_hash: str
    start_ms: int
    end_ms: int
    start_cue_index: int
    end_cue_index: int
    excerpt: str
    language: str
    lineage_kind: EvidenceLineageKind = EvidenceLineageKind.EXTRACTION
    role: EvidenceRole = EvidenceRole.PRIMARY_ORIGINAL

    @property
    def excerpt_hash(self) -> str:
        return hashlib.sha256(self.excerpt.encode("utf-8")).hexdigest()

    def as_evidence_write(self) -> EvidenceWrite:
        return EvidenceWrite(
            evidence_id=self.evidence_id,
            video_id=self.video_id,
            artifact_id=self.canonical_artifact_id,
            start_ms=self.start_ms,
            end_ms=self.end_ms,
            lineage_kind=self.lineage_kind,
            role=self.role,
            language=self.language,
            availability=EvidenceAvailability.AVAILABLE,
        )

    def as_text_binding(self) -> EvidenceTextBindingWrite:
        return EvidenceTextBindingWrite.from_timed_transcript(
            evidence=self.as_evidence_write(),
            timed_transcript_id=self.timed_transcript_id,
            start_cue_index=self.start_cue_index,
            end_cue_index=self.end_cue_index,
            excerpt=self.excerpt,
        )


@dataclass(frozen=True, slots=True)
class HydratedSummaryEvidence:
    """Backend-owned Evidence plus the exact spans that must be promoted.

    ``durable_by_ref`` is the temporary-ref to durable-identity resolution.  The
    ref exists only across the model interaction boundary; every persisted
    citation must carry the durable ``evidence_id`` from this map.
    """

    evidence: tuple[EvidenceExcerpt, ...]
    promotions: tuple[SummaryEvidencePromotion, ...]
    refs: tuple[str, ...]
    durable_by_ref: Mapping[str, str]


def _plan_promotion(
    candidate: TrustedEvidenceCandidate,
    *,
    video_id: str,
    canonical_artifact_id: str,
    timed_transcript_id: str,
    timed_transcript_hash: str,
    language: str,
) -> SummaryEvidencePromotion:
    if (
        candidate.start_ms is None
        or candidate.end_ms is None
        or candidate.start_cue_index is None
        or candidate.end_cue_index is None
    ):
        msg = SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE
        raise SummaryEvidenceAuthorityUnavailable(msg)
    if candidate.authoritative_identity != timed_transcript_hash:
        msg = "selected candidate is not bound to the verified timed transcript"
        raise SummaryEvidenceAuthorityError(msg)
    if not candidate.end_cue_index > candidate.start_cue_index:
        msg = "selected candidate cue range must be a non-empty half-open range"
        raise SummaryEvidenceAuthorityError(msg)
    return SummaryEvidencePromotion(
        evidence_id=build_evidence_id(
            video_id=video_id,
            artifact_id=canonical_artifact_id,
            start_ms=candidate.start_ms,
            end_ms=candidate.end_ms,
            lineage_kind=EvidenceLineageKind.EXTRACTION,
            role=EvidenceRole.PRIMARY_ORIGINAL,
        ),
        video_id=video_id,
        canonical_artifact_id=canonical_artifact_id,
        timed_transcript_id=timed_transcript_id,
        timed_transcript_hash=timed_transcript_hash,
        start_ms=candidate.start_ms,
        end_ms=candidate.end_ms,
        start_cue_index=candidate.start_cue_index,
        end_cue_index=candidate.end_cue_index,
        excerpt=candidate.text,
        language=language,
    )


def hydrate_summary_evidence(
    draft: SummaryDraft,
    registry: TrustedEvidenceRegistry,
    *,
    video_id: str,
    canonical_artifact_id: str,
    language: str,
    timed_transcript_id: str | None = None,
    timed_transcript_hash: str | None = None,
) -> HydratedSummaryEvidence:
    """Turn a draft's refs into backend-owned Evidence, or fail closed.

    Every excerpt originates from the issued registry. Unknown refs, foreign
    candidates, and Content with no timed-cue authority all fail closed rather
    than falling back to anything model-authored.
    """

    issued = registry.by_ref()
    cited = draft.cited_refs()
    if not cited:
        msg = "Summary draft cited no trusted evidence reference"
        raise SummaryEvidenceAuthorityError(msg)

    evidence: list[EvidenceExcerpt] = []
    promotions: list[SummaryEvidencePromotion] = []
    durable_by_ref: dict[str, str] = {}
    seen: set[str] = set()
    for ref in cited:
        candidate = issued.get(ref)
        if candidate is None:
            # The model invented an identifier the backend never issued.
            msg = f"Summary draft cited an unissued evidence ref: {ref}"
            raise SummaryEvidenceAuthorityError(msg)
        if ref in seen:
            continue
        seen.add(ref)
        if candidate.source in _NON_CITABLE_SOURCES:
            # Metadata is legitimate background context but is never
            # authoritative Evidence.  Fail closed rather than dropping the ref
            # from the claim or minting a durable row with no timed identity.
            msg = SUMMARY_EVIDENCE_REF_NOT_CITABLE
            raise SummaryEvidenceRefNotCitable(msg)
        if timed_transcript_id is None or timed_transcript_hash is None:
            msg = SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE
            raise SummaryEvidenceAuthorityUnavailable(msg)
        promotion = _plan_promotion(
            candidate,
            video_id=video_id,
            canonical_artifact_id=canonical_artifact_id,
            timed_transcript_id=timed_transcript_id,
            timed_transcript_hash=timed_transcript_hash,
            language=language,
        )
        promotions.append(promotion)
        durable_by_ref[ref] = promotion.evidence_id
        evidence.append(
            # Excerpt is backend-owned text; the identity is the durable one
            # promotion persists, never the temporary model-facing ref.
            EvidenceExcerpt(
                evidence_id=promotion.evidence_id,
                source=candidate.source,
                excerpt=candidate.text,
            )
        )
    return HydratedSummaryEvidence(
        evidence=tuple(evidence),
        promotions=tuple(promotions),
        refs=cited,
        durable_by_ref=durable_by_ref,
    )


# ---------------------------------------------------------------------------
# Historical readability vs current trusted Summary authority
# ---------------------------------------------------------------------------


class _EvidenceReader(Protocol):
    """The narrow repository surface current-authority eligibility needs."""

    def get_evidence(self, evidence_id: str) -> object | None: ...

    def resolve_verified_evidence_text(self, evidence_id: str) -> object | None: ...


def current_summary_authority_defects(
    result: object, repository: _EvidenceReader
) -> tuple[str, ...]:
    """Why ``result`` may not act as CURRENT trusted Summary authority.

    Returns an ordered, deduplicated tuple of human-readable defects.  An empty
    tuple means the result is eligible.

    The checks are deliberately layered:

    1. the live write contract must be the one that persists durable citations;
    2. every ``AnalysisPoint`` citation must belong to the result's own
       authoritative Evidence collection (the persisted-shape invariant);
    3. every authoritative citation must resolve through ``get_evidence``;
    4. every authoritative citation must resolve through
       ``resolve_verified_evidence_text``;
    5. no identifier may look like a temporary model-facing candidate ref.

    Historical artifacts are never mutated, aliased, or rewritten.  They simply
    fail step 1 and are reported as needing regeneration.
    """

    defects: list[str] = []
    prompt_version = getattr(result, "prompt_version", None)
    if prompt_version != CURRENT_SUMMARY_PROMPT_VERSION:
        defects.append(
            f"summary_prompt_identity_is_legacy:{prompt_version}"
        )

    evidence = tuple(getattr(result, "evidence", ()) or ())
    authoritative_ids: list[str] = [
        str(getattr(item, "evidence_id", "")) for item in evidence
    ]

    for group in _point_groups(result):
        for point in group:
            for cited in tuple(getattr(point, "evidence_ids", ()) or ()):
                if str(cited) not in authoritative_ids:
                    defects.append(f"summary_citation_is_not_authoritative:{cited}")

    for evidence_id in dict.fromkeys(authoritative_ids):
        if not evidence_id:
            defects.append("summary_citation_is_empty")
            continue
        # Shape and resolution are checked independently: a temporary ref is
        # exactly the diagnostic that matters for a legacy artifact, so it must
        # not be suppressed by the "does not resolve" finding.
        if evidence_id[:1] in ("t", "m"):
            defects.append(f"summary_citation_is_temporary_ref:{evidence_id}")
        if repository.get_evidence(evidence_id) is None:
            defects.append(f"summary_citation_is_not_durable:{evidence_id}")
        elif repository.resolve_verified_evidence_text(evidence_id) is None:
            defects.append(f"summary_citation_text_is_unresolvable:{evidence_id}")

    return tuple(dict.fromkeys(defects))


def require_current_summary_authority(
    result: object, repository: _EvidenceReader
) -> None:
    """Fail closed unless ``result`` is eligible as current trusted Summary.

    A legacy readable artifact raises :class:`LegacySummaryNotCurrentAuthority`
    so callers can surface a truthful regeneration-required state.  A
    current-identity result whose citations do not resolve raises
    :class:`SummaryCitationNotDurable`, which is corruption, not staleness.
    """

    defects = current_summary_authority_defects(result, repository)
    if not defects:
        return
    legacy = any(
        defect.startswith("summary_prompt_identity_is_legacy") for defect in defects
    )
    if legacy:
        raise LegacySummaryNotCurrentAuthority("; ".join(defects))
    raise SummaryCitationNotDurable("; ".join(defects))


def _point_groups(result: object) -> tuple[tuple[object, ...], ...]:
    return tuple(
        tuple(getattr(result, name, ()) or ())
        for name in (
            "core_points",
            "key_facts",
            "product_opportunities",
            "business_opportunities",
            "actionable_directions",
            "hypotheses_to_validate",
            "action_recommendations",
            "risks",
        )
    )


__all__: Final = [
    "CURRENT_SUMMARY_PROMPT_VERSION",
    "HISTORICAL_SUMMARY_PROMPT_VERSIONS",
    "SUMMARY_EVIDENCE_AUTHORITY_UNAVAILABLE",
    "SUMMARY_EVIDENCE_REF_NOT_CITABLE",
    "HydratedSummaryEvidence",
    "LegacySummaryNotCurrentAuthority",
    "SummaryCitationNotDurable",
    "SummaryEvidenceAuthorityError",
    "SummaryEvidenceAuthorityUnavailable",
    "SummaryEvidencePromotion",
    "SummaryEvidenceRefNotCitable",
    "current_summary_authority_defects",
    "hydrate_summary_evidence",
    "require_current_summary_authority",
]
