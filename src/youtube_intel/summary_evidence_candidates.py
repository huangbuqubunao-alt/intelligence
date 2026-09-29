"""Deterministic trusted Evidence candidate registry (M13 Summary P1 Foundation).

This is an **ephemeral, backend-owned, read-only projection**. It is not a new
database, not durable Evidence, and it never writes. A later authority-wiring
phase promotes the candidates a model actually selects into the existing
``evidence`` / ``evidence_text_bindings`` substrate; nothing here does that.

Every candidate is assembled from trusted source text by the backend and
carries a deterministic, identity-bound ``ref``. The model receives
``ref`` + ``text`` and later returns only ``ref`` — it never supplies an
offset, a timestamp, or an authoritative quote.

Granularity policy
------------------
``SUMMARY_CUE_GROUP_V1`` groups whole contiguous canonical cues up to
``CUE_GROUP_MAX_CHARS``. The bound is deliberately the project's *existing*
bound for a bounded contiguous transcript span (``transcripts.py`` packs
durable Evidence at 800 characters). It is inherited from the codebase, not
reverse-engineered from the single 44-second reproduction sample, and it keeps
every candidate representable as an ``EvidenceExcerpt`` without re-chunking.

``METADATA_SPAN_V1`` bounds each metadata candidate at the shared
``EVIDENCE_EXCERPT_MAX_LENGTH`` so a long description is deterministically
split rather than assumed to fit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final, Iterable, Mapping

from youtube_intel.domain import EvidenceSource
from youtube_intel.state import VerifiedTimedTranscript, VerifiedTimedTranscriptCue
from youtube_intel.summary_draft import EVIDENCE_EXCERPT_MAX_LENGTH

#: Grouping policy identity for timed-transcript candidates.
SUMMARY_CUE_GROUP_V1: Final = "summary-cue-group-v1"

#: Segmentation policy identity for metadata candidates.
METADATA_SPAN_V1: Final = "metadata-span-v1"

#: Inherited from the durable transcript Evidence partition policy; not tuned to
#: any single observed sample.
CUE_GROUP_MAX_CHARS: Final = 800

_SHORT_HASH_CHARS: Final = 16


def _short_digest(parts: Iterable[object]) -> str:
    canonical = json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_SHORT_HASH_CHARS]


@dataclass(frozen=True, slots=True)
class TrustedEvidenceCandidate:
    """One backend-owned citation target.

    ``text`` is assembled by the backend from trusted source. The model is
    shown this text and may only echo ``ref``. All range fields are backend
    authority and are never accepted from a model.

    Cue indexes follow the existing ``evidence_text_bindings`` convention:
    ``start_cue_index`` is inclusive and ``end_cue_index`` is **exclusive**
    (the table constrains ``end_cue_index > start_cue_index`` and the
    resolver selects ``cue_index >= start AND cue_index < end``). Keeping
    that convention here means a promoted candidate binds exactly the cues
    its text was assembled from, with no off-by-one truncation.
    """

    ref: str
    source: EvidenceSource
    text: str
    authoritative_identity: str
    start_ms: int | None = None
    end_ms: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    start_cue_index: int | None = None
    end_cue_index: int | None = None

    def sort_key(self) -> tuple[str, int, int, str]:
        first = self.start_ms if self.start_ms is not None else (self.start_offset or 0)
        last = self.end_ms if self.end_ms is not None else (self.end_offset or 0)
        return (self.source.value, first, last, self.ref)

    def canonical_form(self) -> dict[str, object]:
        return {
            "ref": self.ref,
            "source": self.source.value,
            "text": self.text,
            "identity": self.authoritative_identity,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "start_cue_index": self.start_cue_index,
            "end_cue_index": self.end_cue_index,
        }


@dataclass(frozen=True, slots=True)
class TrustedEvidenceRegistry:
    """An immutable, deterministically ordered candidate set for one request."""

    candidates: tuple[TrustedEvidenceCandidate, ...]
    cue_group_policy: str = SUMMARY_CUE_GROUP_V1
    metadata_span_policy: str = METADATA_SPAN_V1

    def __post_init__(self) -> None:
        refs = [candidate.ref for candidate in self.candidates]
        if len(refs) != len(set(refs)):
            msg = "trusted Evidence candidate refs must be unique"
            raise ValueError(msg)
        if refs != sorted(refs, key=lambda ref: ref):
            ordered = tuple(sorted(self.candidates, key=lambda c: c.sort_key()))
            object.__setattr__(self, "candidates", ordered)

    def __len__(self) -> int:
        return len(self.candidates)

    def by_ref(self) -> Mapping[str, TrustedEvidenceCandidate]:
        return {candidate.ref: candidate for candidate in self.candidates}

    def canonical_serialization(self) -> str:
        """Deterministic serialization suitable for future request identity."""

        return json.dumps(
            {
                "cue_group_policy": self.cue_group_policy,
                "metadata_span_policy": self.metadata_span_policy,
                "candidates": [
                    candidate.canonical_form() for candidate in self.candidates
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def identity_hash(self) -> str:
        """Stable identity of exactly what the model was shown."""

        return hashlib.sha256(
            self.canonical_serialization().encode("utf-8")
        ).hexdigest()

    def presentation(self) -> list[dict[str, str]]:
        """The ``ref`` + ``text`` pairs a provider is allowed to receive."""

        return [
            {"ref": candidate.ref, "text": candidate.text}
            for candidate in self.candidates
        ]


# ---------------------------------------------------------------------------
# Timed transcript candidates
# ---------------------------------------------------------------------------


def _group_cues(
    cues: tuple[VerifiedTimedTranscriptCue, ...],
) -> tuple[tuple[VerifiedTimedTranscriptCue, ...], ...]:
    groups: list[tuple[VerifiedTimedTranscriptCue, ...]] = []
    current: list[VerifiedTimedTranscriptCue] = []
    current_chars = 0
    for cue in cues:
        # A group always contains whole cues. A single cue longer than the
        # bound becomes its own group; it is never split mid-cue.
        if current and current_chars + 1 + len(cue.text) > CUE_GROUP_MAX_CHARS:
            groups.append(tuple(current))
            current = [cue]
            current_chars = len(cue.text)
            continue
        current.append(cue)
        current_chars = current_chars + 1 + len(cue.text) if len(current) > 1 else len(cue.text)
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def timed_transcript_candidates(
    transcript: VerifiedTimedTranscript,
) -> tuple[TrustedEvidenceCandidate, ...]:
    """Derive fine-grained candidates from a verified canonical timed transcript.

    Every candidate maps to one real contiguous cue range of the authoritative
    transcript, so no candidate can span a synthetic sampling seam.
    """

    candidates: list[TrustedEvidenceCandidate] = []
    for group in _group_cues(transcript.cues):
        first, last = group[0], group[-1]
        # Exclusive end, matching evidence_text_bindings.
        end_cue_index = last.cue_index + 1
        text = "\n".join(cue.text for cue in group)
        identity = _short_digest(
            (
                "transcript",
                transcript.video_id,
                transcript.canonical_artifact_id,
                transcript.timed_transcript_hash,
                first.cue_index,
                end_cue_index,
            )
        )
        candidates.append(
            TrustedEvidenceCandidate(
                ref=f"t{first.cue_index}-{end_cue_index}-{identity}",
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                text=text,
                authoritative_identity=transcript.timed_transcript_hash,
                start_ms=first.start_ms,
                end_ms=last.end_ms,
                start_cue_index=first.cue_index,
                end_cue_index=end_cue_index,
            )
        )
    return tuple(candidates)


# ---------------------------------------------------------------------------
# Canonical-only (no timed cues) candidates
# ---------------------------------------------------------------------------


def canonical_text_candidates(
    *, canonical_text: str, artifact_content_hash: str
) -> tuple[TrustedEvidenceCandidate, ...]:
    """Deterministic char-window candidates for a canonical-only transcript.

    This is a pure projection over immutable, hash-bound artifact text. It
    performs no fuzzy matching and accepts no model-supplied range. Durably
    promoting these spans is deliberately **not** implemented here: the durable
    Evidence substrate requires timed-cue identity, so promotion for this path
    fails closed in a later phase rather than inventing authority.
    """

    if not isinstance(canonical_text, str) or not canonical_text.strip():
        msg = "canonical transcript text is required"
        raise ValueError(msg)
    if not artifact_content_hash.strip():
        msg = "canonical artifact content hash is required"
        raise ValueError(msg)
    text = " ".join(canonical_text.split())
    candidates: list[TrustedEvidenceCandidate] = []
    start = 0
    while start < len(text):
        end = min(start + CUE_GROUP_MAX_CHARS, len(text))
        window = text[start:end]
        if window.strip():
            identity = _short_digest(
                ("canonical", artifact_content_hash, start, end)
            )
            candidates.append(
                TrustedEvidenceCandidate(
                    ref=f"c{start}-{end}-{identity}",
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    text=window,
                    authoritative_identity=artifact_content_hash,
                    start_offset=start,
                    end_offset=end,
                )
            )
        if end >= len(text):
            break
        start = end
    return tuple(candidates)


# ---------------------------------------------------------------------------
# Metadata candidates
# ---------------------------------------------------------------------------

_METADATA_ORDER: Final = (
    EvidenceSource.TITLE,
    EvidenceSource.CHANNEL_NAME,
    EvidenceSource.DESCRIPTION,
)


def _metadata_candidates_for(
    source: EvidenceSource, value: str, input_identity: str
) -> tuple[TrustedEvidenceCandidate, ...]:
    if not isinstance(value, str) or not value.strip():
        return ()
    text = " ".join(value.split())
    candidates: list[TrustedEvidenceCandidate] = []
    start = 0
    while start < len(text):
        end = min(start + EVIDENCE_EXCERPT_MAX_LENGTH, len(text))
        window = text[start:end]
        if window.strip():
            identity = _short_digest(
                ("metadata", source.value, input_identity, start, end)
            )
            candidates.append(
                TrustedEvidenceCandidate(
                    ref=f"m{source.value}-{start}-{end}-{identity}",
                    source=source,
                    text=window,
                    authoritative_identity=input_identity,
                    start_offset=start,
                    end_offset=end,
                )
            )
        if end >= len(text):
            break
        start = end
    return tuple(candidates)


def metadata_candidates(
    *,
    title: str,
    channel_name: str,
    description: str,
    input_identity: str,
) -> tuple[TrustedEvidenceCandidate, ...]:
    """Deterministic, bounded metadata candidates.

    A description longer than ``EVIDENCE_EXCERPT_MAX_LENGTH`` is split into
    bounded windows rather than assumed to fit. The model never supplies an
    offset.
    """

    if not input_identity.strip():
        msg = "authoritative input identity is required"
        raise ValueError(msg)
    values = {
        EvidenceSource.TITLE: title,
        EvidenceSource.CHANNEL_NAME: channel_name,
        EvidenceSource.DESCRIPTION: description,
    }
    candidates: list[TrustedEvidenceCandidate] = []
    for source in _METADATA_ORDER:
        candidates.extend(
            _metadata_candidates_for(source, values[source], input_identity)
        )
    return tuple(candidates)


# ---------------------------------------------------------------------------
# Registry assembly
# ---------------------------------------------------------------------------


def build_trusted_evidence_registry(
    *,
    transcript: VerifiedTimedTranscript | None = None,
    canonical_text: str | None = None,
    canonical_content_hash: str | None = None,
    title: str = "",
    channel_name: str = "",
    description: str = "",
    input_identity: str,
) -> TrustedEvidenceRegistry:
    """Assemble the deterministic registry a provider would receive.

    Transcript authority is preferred when a verified timed transcript exists;
    otherwise the canonical-only projection is used. Metadata is always
    included. This function performs no database access and no writes.
    """

    candidates: list[TrustedEvidenceCandidate] = []
    if transcript is not None:
        candidates.extend(timed_transcript_candidates(transcript))
    elif canonical_text and canonical_content_hash:
        candidates.extend(
            canonical_text_candidates(
                canonical_text=canonical_text,
                artifact_content_hash=canonical_content_hash,
            )
        )
    candidates.extend(
        metadata_candidates(
            title=title,
            channel_name=channel_name,
            description=description,
            input_identity=input_identity,
        )
    )
    return TrustedEvidenceRegistry(candidates=tuple(candidates))


def select_length_bounded_candidates(
    registry: TrustedEvidenceRegistry,
    *,
    character_budget: int,
) -> TrustedEvidenceRegistry:
    """Select candidates for a long input using head / middle / tail.

    Selection operates on the ordered candidate list, never on concatenated
    transcript text, so every retained candidate keeps its real authoritative
    span identity and none can cross a synthetic seam.
    """

    if character_budget <= 0:
        msg = "candidate character budget must be positive"
        raise ValueError(msg)
    transcript_candidates = [
        candidate
        for candidate in registry.candidates
        if candidate.source is EvidenceSource.TRANSCRIPT_SAMPLE
    ]
    metadata_candidates_ = [
        candidate
        for candidate in registry.candidates
        if candidate.source is not EvidenceSource.TRANSCRIPT_SAMPLE
    ]
    total = sum(len(candidate.text) for candidate in transcript_candidates)
    if total <= character_budget or not transcript_candidates:
        return registry

    head_share = character_budget // 2
    tail_share = character_budget - head_share
    head: list[TrustedEvidenceCandidate] = []
    tail: list[TrustedEvidenceCandidate] = []
    used = 0
    for candidate in transcript_candidates:
        if used + len(candidate.text) <= head_share:
            head.append(candidate)
            used += len(candidate.text)
    used = 0
    for candidate in reversed(transcript_candidates):
        if used + len(candidate.text) <= tail_share:
            tail.append(candidate)
            used += len(candidate.text)
        if used >= tail_share:
            break
    if not head and not tail:
        head = [transcript_candidates[0]]
    retained = list(reversed(tail)) + head
    combined = tuple(
        sorted(retained + metadata_candidates_, key=lambda c: c.sort_key())
    )
    return TrustedEvidenceRegistry(
        candidates=combined,
        cue_group_policy=registry.cue_group_policy,
        metadata_span_policy=registry.metadata_span_policy,
    )


__all__: Final = [
    "CUE_GROUP_MAX_CHARS",
    "METADATA_SPAN_V1",
    "SUMMARY_CUE_GROUP_V1",
    "TrustedEvidenceCandidate",
    "TrustedEvidenceRegistry",
    "build_trusted_evidence_registry",
    "canonical_text_candidates",
    "metadata_candidates",
    "select_length_bounded_candidates",
    "timed_transcript_candidates",
]
