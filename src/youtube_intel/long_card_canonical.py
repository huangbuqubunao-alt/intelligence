"""Pure, unregistered historical timed-card representation; never admission.

The caller supplies positive decoded long-codec UTF-8 JSON (original Evidence
IDs, not aliases) and must retain its public/decoded wires and hashes separately.
This projection binds every historical card field, not source/summary/policy or
execution provenance. Those remain caller-owned proof requirements. NO_NEW has
no card revision and is deliberately unsupported, as is LOCAL_TEXT.

Oracle: distillation.PersonalizedDistillationService._parse_candidate and
intelligence_read.AuthoritativeIntelligenceReader._read_card: remove the local result
marker, sort original IDs by Python string order, then compact sort_keys JSON
with the historical default ensure_ascii=True and SHA-256 of its UTF-8 bytes.
There is no import of those IO-bearing modules; production de-duplication and
wiring must be a later shared task.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import cast

MAX_INPUT_BYTES = 1_000_000  # Accepted long codec decoded-output safety bound.
# The exact shape maximum is 2,093,375B: all 174,240 text/ID code points
# escaped to 12 ASCII bytes, plus 2,495B maximal syntax/enums/timestamps.
# Thus this redundant guard never excludes shape-valid input. A per-wire 3x
# argument would be wrong: raw DEL can expand from one byte to six.
MAX_CANONICAL_BYTES = 3_000_000
MAX_REFERENCES = 20
MAX_ID_CHARS = 512
MAX_CORE_CHARS = 4_000
MAX_TEXT_CHARS = 2_000
MAX_TEXT_ITEMS = 20
MAX_TIMESTAMP = 2**63 - 1
_TEXT_LISTS = (
    "user_relevant_information",
    "important_new_information",
    "meaningful_details",
    "filtered_noise",
)
# Exact finite values from the accepted timed-card schema and state enums.
_CLAIMS = frozenset({
    "FACT", "EVIDENCE_BACKED_STATEMENT", "OPINION", "PREDICTION", "RUMOR",
    "SYSTEM_INFERENCE",
})
_STANCES = frozenset({"supporting", "contradicting", "conditional"})
_CARD_FIELDS = frozenset({
    "result", "core_conclusion", "claim_kind", "evidence", *_TEXT_LISTS,
})
_REFERENCE_FIELDS = frozenset({"evidence_id", "start_ms", "end_ms", "stance"})


@dataclass(frozen=True, slots=True)
class CanonicalLongCard:
    """Immutable historical revision bytes; a hash proves consistency only."""

    canonical_content: bytes

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content).hexdigest()


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("card JSON has duplicate keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("card JSON has a nonfinite number")


def _object(value: object, fields: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or value.keys() != fields:
        raise ValueError("card object fields differ")
    return cast(dict[str, object], value)


def _text(value: object, maximum: int, *, prose: bool = False) -> str:
    if type(value) is not str or not 0 < len(value) <= maximum:
        raise ValueError("card string is missing or exceeds its character bound")
    if prose and (not value.strip() or value != value.strip()):
        raise ValueError("card prose violates existing admission shape")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ValueError("card string is not valid Unicode") from error
    return value


def _integer(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_TIMESTAMP:
        raise ValueError("card timestamp is invalid")
    return value


def canonicalize_long_card(decoded_wire: bytes) -> CanonicalLongCard:
    """Validate exact positive decoded shape and return historical bytes/hash.

    Only exact immutable bytes are supported: mappings, scalar objects, cycles,
    custom encoders and mutable aliases cannot cross this boundary. Accepted
    JSON has a fixed maximum depth of three below the root object. No field is
    repaired, normalized, trimmed, sampled or silently truncated. This does not
    validate Evidence ownership, alias decoding, source authority, semantics,
    language, model qualification or execution; callers must enforce those.
    """
    if type(decoded_wire) is not bytes or not 0 < len(decoded_wire) <= MAX_INPUT_BYTES:
        raise ValueError("card wire is empty or exceeds its byte bound")
    try:
        payload = _object(json.loads(
            decoded_wire.decode("utf-8", errors="strict"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        ), _CARD_FIELDS)
    except (UnicodeError, RecursionError, ValueError) as error:
        raise ValueError("card wire is not strict bounded UTF-8 JSON") from error
    if payload["result"] != "INTELLIGENCE":
        raise ValueError("card requires the positive decoded result marker")
    claim = _text(payload["claim_kind"], 64)
    if claim not in _CLAIMS:
        raise ValueError("card claim classification is invalid")
    _text(payload["core_conclusion"], MAX_CORE_CHARS, prose=True)
    for field in _TEXT_LISTS:
        texts = payload[field]
        if type(texts) is not list or len(texts) > MAX_TEXT_ITEMS:
            raise ValueError("card text list exceeds its shape bound")
        for text in texts:
            _text(text, MAX_TEXT_CHARS, prose=True)
    refs = payload["evidence"]
    if type(refs) is not list or not 0 < len(refs) <= MAX_REFERENCES:
        raise ValueError("card references are empty or exceed their shape bound")
    by_id: dict[str, dict[str, object]] = {}
    supporting = False
    for raw in refs:
        ref = _object(raw, _REFERENCE_FIELDS)
        evidence_id = _text(ref["evidence_id"], MAX_ID_CHARS)
        start, end = _integer(ref["start_ms"]), _integer(ref["end_ms"])
        stance = _text(ref["stance"], 64)
        if evidence_id in by_id or end <= start or stance not in _STANCES:
            raise ValueError("card reference identity, interval or stance is invalid")
        supporting |= stance == "supporting"
        by_id[evidence_id] = ref
    if not supporting:
        raise ValueError("card requires at least one supporting Evidence")
    projected = {key: value for key, value in payload.items() if key != "result"}
    projected["evidence"] = [by_id[eid] for eid in sorted(by_id)]
    canonical_content = json.dumps(
        projected, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(canonical_content) > MAX_CANONICAL_BYTES:
        raise ValueError("card canonical content exceeds its byte bound")
    return CanonicalLongCard(canonical_content)
