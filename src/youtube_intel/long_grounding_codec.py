"""Lossless timed-Evidence values only: no authority, execution or qualification.

Callers must supply the already verified, unambiguous complete source snapshot.
Hashes prove consistency, never source authority. This version is deliberately
separate from every existing short-input wire/profile and is not registered.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TypeAlias, cast

from youtube_intel.state import (
    EvidenceStance,
    IntelligenceClaimKind,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    VerifiedEvidenceText,
    VerifiedTimedTranscript,
    VerifiedTimedTranscriptCue,
)

CODEC_VERSION = "long-grounding-lossless-timed-v1"
# Conservative intersection of existing subtitle and local-media read bounds;
# these are storage/codec safety bounds, never a model context allowance.
MAX_CUES = 32_768
MAX_EVIDENCE = 4_102
MAX_EXCERPT_CHARS = 4_000
MAX_CANONICAL_CHARS = 1_000_000
MAX_CANONICAL_BYTES = 4_000_000
MAX_INPUT_BYTES = 5_000_000
MAX_OUTPUT_BYTES = 1_000_000
MAX_POSITIVE_REFERENCES = 20
_MAX_INT = 2**63 - 1
_MAX_DEPTH = 16
_TEXT_LISTS = (
    "user_relevant_information",
    "important_new_information",
    "meaningful_details",
    "filtered_noise",
)
Json: TypeAlias = None | bool | int | float | str | list["Json"] | dict[str, "Json"]


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    evidence: VerifiedEvidenceText
    start_cue_index: int
    end_cue_index: int


@dataclass(frozen=True, slots=True)
class EncodedGrounding:
    canonical_wire: bytes

    @property
    def input_hash(self) -> str:
        return _hash(self.canonical_wire)


@dataclass(frozen=True, slots=True)
class ExpandedGrounding:
    source_id: str
    content_provider: str
    source_content_hash: str
    canonical_text_hash: str
    transcript: VerifiedTimedTranscript
    evidence: tuple[EvidenceSpan, ...]


@dataclass(frozen=True, slots=True)
class DecodedOutput:
    input_hash: str
    public_wire: bytes
    decoded_wire: bytes

    @property
    def public_wire_hash(self) -> str:
        return _hash(self.public_wire)

    @property
    def decoded_hash(self) -> str:
        return _hash(self.decoded_wire)

    @property
    def decoded_value(self) -> dict[str, Json]:
        # A fresh value prevents mutable aliases from changing stored bindings.
        return _object(_loads(self.decoded_wire, MAX_OUTPUT_BYTES))


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("codec value is not strict UTF-8 JSON") from error


def _object(value: Json, keys: set[str] | None = None) -> dict[str, Json]:
    if not isinstance(value, dict) or (keys is not None and set(value) != keys):
        raise ValueError("codec object fields differ")
    return value


def _array(value: Json, maximum: int) -> list[Json]:
    if not isinstance(value, list) or not 0 < len(value) <= maximum:
        raise ValueError("codec array is empty or exceeds its bound")
    return value


def _integer(value: object) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_INT:
        raise ValueError("codec integer is invalid")
    return value


def _string(value: object, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ValueError("codec string is missing or exceeds its bound")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ValueError("codec string is not UTF-8") from error
    return value


def _digest(value: object) -> str:
    text = _string(value, 64)
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ValueError("codec SHA-256 is invalid")
    return text


def _strict_object(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _no_constant(value: str) -> Json:
    raise ValueError("nonfinite JSON number")


def _depth(value: Json, level: int = 0) -> None:
    if level > _MAX_DEPTH:
        raise ValueError("codec JSON nesting exceeds its bound")
    if isinstance(value, dict):
        for item in value.values():
            _depth(item, level + 1)
    elif isinstance(value, list):
        for item in value:
            _depth(item, level + 1)


def _loads(wire: bytes, maximum: int) -> Json:
    if type(wire) is not bytes or not 0 < len(wire) <= maximum:
        raise ValueError("codec wire is empty or exceeds its byte bound")
    try:
        value = cast(
            Json,
            json.loads(
                wire.decode("utf-8", errors="strict"),
                object_pairs_hook=_strict_object,
                parse_constant=_no_constant,
            ),
        )
        _depth(value)
        _canonical(value)  # Also rejects overflow-to-infinity and lone surrogates.
        return value
    except (UnicodeError, RecursionError) as error:
        raise ValueError("codec JSON encoding or nesting is invalid") from error


def encode_grounding(
    *,
    source_id: str,
    content_provider: str,
    source_content_hash: str,
    canonical_text_hash: str,
    transcript: VerifiedTimedTranscript,
    evidence: tuple[EvidenceSpan, ...],
) -> EncodedGrounding:
    """Freeze complete ordered spans, RLE only equal adjacent texts within a span.

    Source/canonical hashes are supplied verified identities, not reconstructed
    from guessed file serialization. Every cue/excerpt/timed hash is recomputed.
    """
    _string(source_id)
    if type(content_provider) is not str or content_provider not in {
        "YOUTUBE",
        "LOCAL",
    }:
        raise ValueError("codec timed provider is unsupported")
    _digest(source_content_hash)
    _digest(canonical_text_hash)
    if (
        type(transcript) is not VerifiedTimedTranscript
        or type(transcript.cues) is not tuple
    ):
        raise ValueError("codec requires immutable timed values")
    for identity in (
        transcript.video_id,
        transcript.canonical_artifact_id,
        transcript.timed_transcript_id,
    ):
        _string(identity)
    if not 0 < len(transcript.cues) <= MAX_CUES:
        raise ValueError("codec cue count exceeds its bound")
    chars, byte_count, previous_end = 0, 0, -1
    writes: list[TimedTranscriptCueWrite] = []
    for index, cue in enumerate(transcript.cues):
        if (
            type(cue) is not VerifiedTimedTranscriptCue
            or _integer(cue.cue_index) != index
        ):
            raise ValueError("codec cue index is not contiguous")
        start, end = _integer(cue.start_ms), _integer(cue.end_ms)
        text = _string(cue.text, MAX_EXCERPT_CHARS)
        chars += len(text) + 1
        byte_count += len(text.encode()) + 1
        if (
            start < previous_end
            or end <= start
            or not text.strip()
            or _digest(cue.text_hash) != _hash(text.encode())
            or chars > MAX_CANONICAL_CHARS
            or byte_count > MAX_CANONICAL_BYTES
        ):
            raise ValueError("codec cue timing, text hash or source bound is invalid")
        previous_end = end
        writes.append(TimedTranscriptCueWrite(start, end, text))
    rebuilt = TimedTranscriptWrite.from_cues(
        video_id=transcript.video_id,
        canonical_artifact_id=transcript.canonical_artifact_id,
        cues=tuple(writes),
    )
    if (
        rebuilt.timed_transcript_hash != transcript.timed_transcript_hash
        or rebuilt.timed_transcript_id != transcript.timed_transcript_id
    ):
        raise ValueError("codec ordered transcript hash/identity differs")
    if type(evidence) is not tuple or not 0 < len(evidence) <= MAX_EVIDENCE:
        raise ValueError("codec Evidence count/container is invalid")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    first = 0
    for position, span in enumerate(evidence, 1):
        if (
            type(span) is not EvidenceSpan
            or type(span.evidence) is not VerifiedEvidenceText
        ):
            raise ValueError("codec Evidence values are invalid")
        item = span.evidence
        _string(item.evidence_id)
        last = _integer(span.end_cue_index)
        if (
            _integer(span.start_cue_index) != first
            or not first < last <= len(transcript.cues)
            or last - first > MAX_EXCERPT_CHARS
            or item.evidence_id in seen
        ):
            raise ValueError("codec spans are not unique ordered complete coverage")
        seen.add(item.evidence_id)
        cues = transcript.cues[first:last]
        excerpt = "\n".join(c.text for c in cues)
        if (
            item.video_id != transcript.video_id
            or item.timed_transcript_id != transcript.timed_transcript_id
            or item.timed_transcript_hash != transcript.timed_transcript_hash
            or item.locator_type != "TIMED_MEDIA"
            or any(
                v is not None
                for v in (
                    item.start_offset,
                    item.end_offset,
                    item.start_line,
                    item.end_line,
                )
            )
            or (
                item.source_content_hash is not None
                and item.source_content_hash != source_content_hash
            )
            or _integer(item.start_ms) != cues[0].start_ms
            or _integer(item.end_ms) != cues[-1].end_ms
            or type(item.excerpt) is not str
            or excerpt != item.excerpt
            or len(excerpt) > MAX_EXCERPT_CHARS
            or _digest(item.excerpt_hash) != _hash(excerpt.encode())
        ):
            raise ValueError("codec Evidence locator/source/excerpt binding differs")
        runs: list[dict[str, object]] = []
        run_cues: list[list[int | str]] = []
        previous_text: str | None = None
        for cue in cues:
            if cue.text != previous_text:
                run_cues = []
                runs.append({"text": cue.text, "cues": run_cues})
                previous_text = cue.text
            run_cues.append([cue.cue_index, cue.start_ms, cue.end_ms, cue.text_hash])
        rows.append(
            {
                "alias": f"E{position}",
                "evidence_id": item.evidence_id,
                "locator_type": "TIMED_MEDIA",
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
                "start_cue_index": first,
                "end_cue_index": last,
                "excerpt_hash": item.excerpt_hash,
                "source_content_hash": item.source_content_hash,
                "runs": runs,
            }
        )
        first = last
    if first != len(transcript.cues):
        raise ValueError("codec Evidence coverage is incomplete")
    body = _canonical(
        {
            "codec_version": CODEC_VERSION,
            "source_id": source_id,
            "content_provider": content_provider,
            "source_content_hash": source_content_hash,
            "canonical_text_hash": canonical_text_hash,
            "video_id": transcript.video_id,
            "canonical_artifact_id": transcript.canonical_artifact_id,
            "timed_transcript_id": transcript.timed_transcript_id,
            "timed_transcript_hash": transcript.timed_transcript_hash,
            "evidence": rows,
        }
    )
    if len(body) > MAX_INPUT_BYTES:
        raise ValueError("codec canonical input exceeds its byte bound")
    return EncodedGrounding(body)


def expand_grounding(encoded: EncodedGrounding) -> ExpandedGrounding:
    """Rebuild from RLE, then verify every binding and canonical version again."""
    if type(encoded) is not EncodedGrounding:
        raise ValueError("codec packet type is invalid")
    root = _object(
        _loads(encoded.canonical_wire, MAX_INPUT_BYTES),
        {
            "codec_version",
            "source_id",
            "content_provider",
            "source_content_hash",
            "canonical_text_hash",
            "video_id",
            "canonical_artifact_id",
            "timed_transcript_id",
            "timed_transcript_hash",
            "evidence",
        },
    )
    if root["codec_version"] != CODEC_VERSION:
        raise ValueError("codec version is unsupported")
    cues: list[VerifiedTimedTranscriptCue] = []
    spans: list[EvidenceSpan] = []
    characters = 0
    for position, raw in enumerate(_array(root["evidence"], MAX_EVIDENCE), 1):
        row = _object(
            raw,
            {
                "alias",
                "evidence_id",
                "locator_type",
                "start_ms",
                "end_ms",
                "start_cue_index",
                "end_cue_index",
                "excerpt_hash",
                "source_content_hash",
                "runs",
            },
        )
        if row["alias"] != f"E{position}" or row["locator_type"] != "TIMED_MEDIA":
            raise ValueError("codec alias/locator differs")
        first = len(cues)
        for raw_run in _array(row["runs"], MAX_EXCERPT_CHARS):
            run = _object(raw_run, {"text", "cues"})
            text = _string(run["text"], MAX_EXCERPT_CHARS)
            markers = _array(run["cues"], MAX_EXCERPT_CHARS)
            characters += (len(text) + 1) * len(markers)
            if len(cues) + len(markers) > MAX_CUES or characters > MAX_CANONICAL_CHARS:
                raise ValueError("codec expansion exceeds source bounds")
            for raw_marker in markers:
                marker = _array(raw_marker, 4)
                if len(marker) != 4:
                    raise ValueError("codec cue marker fields differ")
                cues.append(
                    VerifiedTimedTranscriptCue(
                        _integer(marker[0]),
                        _integer(marker[1]),
                        _integer(marker[2]),
                        text,
                        _digest(marker[3]),
                    )
                )
        excerpt = "\n".join(c.text for c in cues[first:])
        source_hash = row["source_content_hash"]
        item = VerifiedEvidenceText(
            _string(row["evidence_id"]),
            _string(root["video_id"]),
            _string(root["timed_transcript_id"]),
            _digest(root["timed_transcript_hash"]),
            _integer(row["start_ms"]),
            _integer(row["end_ms"]),
            excerpt,
            _digest(row["excerpt_hash"]),
            source_content_hash=None if source_hash is None else _digest(source_hash),
        )
        spans.append(
            EvidenceSpan(
                item, _integer(row["start_cue_index"]), _integer(row["end_cue_index"])
            )
        )
    result = ExpandedGrounding(
        _string(root["source_id"]),
        _string(root["content_provider"]),
        _digest(root["source_content_hash"]),
        _digest(root["canonical_text_hash"]),
        VerifiedTimedTranscript(
            _string(root["timed_transcript_id"]),
            _string(root["video_id"]),
            _string(root["canonical_artifact_id"]),
            _digest(root["timed_transcript_hash"]),
            tuple(cues),
        ),
        tuple(spans),
    )
    rebuilt = encode_grounding(
        source_id=result.source_id,
        content_provider=result.content_provider,
        source_content_hash=result.source_content_hash,
        canonical_text_hash=result.canonical_text_hash,
        transcript=result.transcript,
        evidence=result.evidence,
    )
    if rebuilt.canonical_wire != encoded.canonical_wire:
        raise ValueError("codec packet is not the unique canonical RLE encoding")
    return result


def _claim_text(value: Json, maximum: int) -> None:
    text = _string(value, maximum)
    if not text.strip() or text != text.strip():
        raise ValueError("codec claim text violates existing admission shape")


def decode_output(public_wire: bytes, encoded: EncodedGrounding) -> DecodedOutput:
    """Validate public final shape; only replace exact alias IDs, never prose.

    This is not semantic, language, source-authority or execution validation.
    The future long protocol must still enforce all of those before admission.
    """
    expanded = expand_grounding(encoded)
    value = _object(_loads(public_wire, MAX_OUTPUT_BYTES))
    zero = value.get("result") == "NO_NEW_INTELLIGENCE"
    keys = (
        {"result", "evidence"}
        if zero
        else {"result", "evidence", "core_conclusion", "claim_kind", *_TEXT_LISTS}
    )
    if set(value) != keys or (not zero and value.get("result") != "INTELLIGENCE"):
        raise ValueError("codec public final branch/fields differ")
    if not zero:
        _claim_text(value["core_conclusion"], 4_000)
        if _string(value["claim_kind"]) not in {
            c.value
            for c in IntelligenceClaimKind
            if c is not IntelligenceClaimKind.UNCLASSIFIED
        }:
            raise ValueError("codec claim classification is invalid")
        for key in _TEXT_LISTS:
            texts = value[key]
            if not isinstance(texts, list) or len(texts) > 20:
                raise ValueError(
                    "codec claim text list violates existing admission shape"
                )
            for text in texts:
                _claim_text(text, 2_000)
    # Preserve the accepted positive schema's reference limit. Only this new
    # codec's NO_NEW branch has the complete-source reference cardinality;
    # neither branch changes or registers the old short-input schema/profile.
    reference_limit = (
        len(expanded.evidence)
        if zero
        else min(MAX_POSITIVE_REFERENCES, len(expanded.evidence))
    )
    refs = _array(value["evidence"], reference_limit)
    if zero and len(refs) != len(expanded.evidence):
        raise ValueError("codec NO_NEW coverage length differs")
    aliases = {f"E{i}": span.evidence for i, span in enumerate(expanded.evidence, 1)}
    seen: set[str] = set()
    supporting = False
    decoded_refs: list[Json] = []
    for position, raw in enumerate(refs, 1):
        ref = _object(
            raw, {"evidence_id", "start_ms", "end_ms"} | (set() if zero else {"stance"})
        )
        alias = _string(ref["evidence_id"])
        if alias not in aliases or alias in seen or (zero and alias != f"E{position}"):
            raise ValueError(
                "codec alias is unknown, repeated or out of canonical order"
            )
        seen.add(alias)
        item = aliases[alias]
        if (
            _integer(ref["start_ms"]) != item.start_ms
            or _integer(ref["end_ms"]) != item.end_ms
        ):
            raise ValueError("codec reference timestamps differ")
        if not zero:
            stance = _string(ref["stance"])
            if stance not in {s.value for s in EvidenceStance}:
                raise ValueError("codec Evidence stance is invalid")
            supporting |= stance == EvidenceStance.SUPPORTING.value
        decoded_refs.append({**ref, "evidence_id": item.evidence_id})
    if not zero and not supporting:
        raise ValueError("codec Intelligence requires supporting Evidence")
    decoded = _canonical({**value, "evidence": decoded_refs})
    if len(decoded) > MAX_OUTPUT_BYTES:
        raise ValueError("codec expanded output exceeds its byte bound")
    return DecodedOutput(encoded.input_hash, public_wire, decoded)
