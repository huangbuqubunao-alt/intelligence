"""Pure, unregistered full native request candidate; never execution authority.

32768 is an unverified context expectation, not a token/capacity claim. Source
authority, native template/slots, resources, qualification, strict semantics,
proof/receipt persistence and dispatch all remain subsequent caller obligations.
Old failed profiles remain closed. No verified input is rebound or resealed here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import cast

from youtube_intel import long_grounding_projection as projection
from youtube_intel.distillation import (
    VerifiedDistillationInput,
    local_profile_for_scope,
)
from youtube_intel.local_distillation_profile import PROFILE_ID as SOURCE_PROFILE_ID
from youtube_intel.local_distillation_profile import canonical, resolve_profile
from youtube_intel.long_grounding_codec import (
    CODEC_VERSION,
    MAX_EVIDENCE,
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    MAX_POSITIVE_REFERENCES,
    EncodedGrounding,
)

PROFILE_ID = "local-grounding-qwen35-9b-lossless-rle-thinking-v1"
SCHEMA_VERSION = "long-grounding-alias-exact-timed-schema-v1"
FREEZE_VERSION = "long-grounding-complete-native-request-freeze-v1"
MAX_REQUEST_BYTES = 8_000_000

# Serialize immediately: neither the legacy shared dictionaries nor a caller's
# returned dictionaries may mutate this profile or any subsequent request.
_SOURCE = resolve_profile(SOURCE_PROFILE_ID)
_BASE_SCHEMA_WIRE = canonical(
    local_profile_for_scope(SOURCE_PROFILE_ID, "YT_TIMED")["schema"]
)
_OPTIONS_WIRE = canonical({**_SOURCE.options(), "num_ctx": 32768})
_PROMPT_WIRE = (_SOURCE.prompt("YT_TIMED") + projection._RLE_INSTRUCTIONS).encode(
    "utf-8"
)


def _hash(wire: bytes) -> str:
    return hashlib.sha256(wire).hexdigest()


@dataclass(frozen=True, slots=True)
class LongDistillationProfile:
    """Frozen identity bytes, without registry, capacity or qualification APIs."""

    profile_wire: bytes

    @property
    def profile_id(self) -> str:
        return PROFILE_ID

    @property
    def profile_hash(self) -> str:
        return _hash(self.profile_wire)


_PROFILE = LongDistillationProfile(
    canonical(
        {
            "profile_id": PROFILE_ID,
            "scope": "YT_TIMED",
            "model": _SOURCE.model,
            "model_digest": _SOURCE.model_digest,
            "runtime": _SOURCE.runtime,
            "timeout_seconds": _SOURCE.timeout_seconds,
            "codec_version": CODEC_VERSION,
            "projection_version": projection.PROJECTION_VERSION,
            "prompt_version": projection.PROMPT_VERSION,
            "prompt_hash": _hash(_PROMPT_WIRE),
            "schema_version": SCHEMA_VERSION,
            "base_schema": json.loads(_BASE_SCHEMA_WIRE),
            "base_schema_hash": _hash(_BASE_SCHEMA_WIRE),
            "schema_contract": "exact-alias-range-alternatives-positive20-no-new-complete-N-v1",
            "freeze_version": FREEZE_VERSION,
            "options": json.loads(_OPTIONS_WIRE),
            "stream": False,
            "think": True,
            "truncate": False,
            "shift": False,
            "capacity_status": "UNVERIFIED_CANDIDATE",
            "max_request_bytes": MAX_REQUEST_BYTES,
            "max_messages_bytes": projection.MAX_MESSAGES_BYTES,
            "max_model_context_bytes": projection.MAX_MODEL_CONTEXT_BYTES,
            "max_semantic_bytes": projection.MAX_SEMANTIC_BYTES,
            "max_value_bytes": projection.MAX_VALUE_BYTES,
            "max_context_items": projection.MAX_CONTEXT_ITEMS,
            "max_snapshot_bytes": projection.MAX_SNAPSHOT_BYTES,
            "max_snapshot_depth": projection.MAX_JSON_DEPTH,
            "max_packet_bytes": MAX_INPUT_BYTES,
            "max_response_bytes": MAX_OUTPUT_BYTES,
            "max_evidence": MAX_EVIDENCE,
            "max_positive_references": MAX_POSITIVE_REFERENCES,
        }
    )
)


def resolve_long_profile(profile_id: str) -> LongDistillationProfile:
    if type(profile_id) is not str or profile_id != PROFILE_ID:
        raise ValueError("unknown long request candidate profile")
    return _PROFILE


@dataclass(frozen=True, slots=True)
class PreparedLongRequest:
    """Reproducible bytes and distinct identities; not a dispatch capability.

    request_hash binds the complete native body. freeze_hash additionally binds
    the fixed candidate and every side input, including original semantic and
    old-profile identity. A source-side change can leave request_hash unchanged.
    """

    profile_hash: str
    source_semantic_hash: str
    source_profile_id: str | None
    source_profile_hash: str | None
    projection: projection.PreparedLongProjection
    schema_hash: str
    request_wire: bytes

    @property
    def request_hash(self) -> str:
        return _hash(self.request_wire)

    @property
    def freeze_hash(self) -> str:
        return _hash(
            canonical(
                {
                    "version": FREEZE_VERSION,
                    "profile_hash": self.profile_hash,
                    "request_hash": self.request_hash,
                    "semantic_snapshot_hash": self.projection.semantic_snapshot_hash,
                }
            )
        )

    def request(self) -> dict[str, object]:
        """Fresh JSON data for inspection; cannot mutate the frozen bytes."""
        return cast(dict[str, object], json.loads(self.request_wire))


def _preflight(wire: bytes, maximum: int) -> None:
    """Bound before decoding/copying; ignore brackets inside JSON strings.

    This cheap nesting scan rejects malicious depth before the accepted JSON
    decoder runs. The accepted projection/codec still enforce full JSON/type,
    duplicate-key, Unicode, finite-number and exact business-shape validation.
    """
    if type(wire) is not bytes or not 0 < len(wire) <= maximum:
        raise ValueError("long request input wire exceeds its byte bound or type")
    depth = 0
    quoted = escaped = False
    for byte in wire:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > projection.MAX_JSON_DEPTH + 1:
                raise ValueError("long request input nesting exceeds its bound")
        elif byte in (93, 125):
            depth -= 1


def _schema(packet: EncodedGrounding) -> dict[str, object]:
    # Called only after actual accepted projection has revalidated the packet.
    # JSON round-trip gives an independent deep copy of the original branches.
    schema = json.loads(_BASE_SCHEMA_WIRE)
    rows = json.loads(packet.canonical_wire)["evidence"]
    for branch, positive in zip(schema["anyOf"], (True, False)):
        alternatives = []
        for row in rows:
            reference = json.loads(canonical(branch["properties"]["evidence"]["items"]))
            for key, value in (
                ("evidence_id", row["alias"]),
                ("start_ms", row["start_ms"]),
                ("end_ms", row["end_ms"]),
            ):
                reference["properties"][key]["enum"] = [value]
            alternatives.append(reference)
        branch["properties"]["evidence"] = {
            "type": "array",
            "items": {"anyOf": alternatives},
            "minItems": 1 if positive else len(rows),
            "maxItems": min(MAX_POSITIVE_REFERENCES, len(rows))
            if positive
            else len(rows),
        }
        if positive:
            branch["properties"]["core_conclusion"].update(minLength=1, maxLength=4000)
            for key in (
                "user_relevant_information",
                "important_new_information",
                "meaningful_details",
                "filtered_noise",
            ):
                branch["properties"][key].update(maxItems=20)
                branch["properties"][key]["items"].update(minLength=1, maxLength=2000)
    # Uniqueness/order, at least one supporting stance and strict prose remain
    # mandatory accepted decode/admission checks; schema alone grants no trust.
    return cast(dict[str, object], schema)


def prepare_long_request(
    packet: EncodedGrounding,
    value: VerifiedDistillationInput,
    *,
    source_snapshot: bytes,
    summary_snapshot: bytes,
    policy_snapshot: bytes,
) -> PreparedLongRequest:
    """Freeze the actual complete projection and native request, without IO.

    All source-side fields remain unchanged in the projection's side bytes.
    Source profile fields are historical semantic identity, not this candidate's
    authority. Neither their hashes nor the VerifiedInput type prove authority.
    """
    if type(packet) is not EncodedGrounding:
        raise ValueError("long request requires the actual accepted codec packet")
    _preflight(packet.canonical_wire, MAX_INPUT_BYTES)
    for snapshot in (source_snapshot, summary_snapshot, policy_snapshot):
        _preflight(snapshot, projection.MAX_SNAPSHOT_BYTES)
    if (
        type(value) is not VerifiedDistillationInput
        or type(value.selected_model) is not str
        or value.selected_model != _SOURCE.model
    ):
        raise ValueError("long request model/input differs from the candidate")
    prepared = projection.prepare_long_projection(
        packet,
        value,
        source_snapshot=source_snapshot,
        summary_snapshot=summary_snapshot,
        policy_snapshot=policy_snapshot,
    )
    messages = json.loads(prepared.messages_wire)
    if messages[0]["content"].encode("utf-8") != _PROMPT_WIRE:
        raise ValueError("long request accepted prompt differs from frozen profile")
    schema = _schema(packet)
    request = {
        "model": _SOURCE.model,
        "messages": messages,
        "format": schema,
        "stream": False,
        "think": True,
        "options": json.loads(_OPTIONS_WIRE),
        "truncate": False,
        "shift": False,
    }
    request_wire = canonical(request)
    if len(request_wire) > MAX_REQUEST_BYTES:
        raise ValueError("long request exceeds complete request byte bound")
    return PreparedLongRequest(
        _PROFILE.profile_hash,
        value.semantic_hash,
        value.local_profile_id,
        value.local_profile_hash,
        prepared,
        _hash(canonical(schema)),
        request_wire,
    )
