"""Finite schema44 adapter; reuses the ordinary Moonshot lifecycle and HTTP boundary."""

from __future__ import annotations

import json

from . import system_synthesis_persistence as persistence
from . import system_synthesis_profile as profile
from .distillation import (
    _MOONSHOT_ENDPOINT_IDENTITY,
    CloudDistillationPreDispatchError,
    MoonshotK26CloudDistillationTransport,
    VerifiedDistillationInput,
)


def prepared_input(value: VerifiedDistillationInput) -> persistence.PreparedSynthesis:
    if (
        type(value) is not VerifiedDistillationInput
        or value.wire_version != profile.PROFILE_ID
        or (value.selected_provider, value.selected_model) != profile.PAIR
        or value.input_json is None
        or profile.sha(value.input_json) != value.semantic_hash
    ):
        raise ValueError("Synthesis input lacks the exact prepared proof")
    prepared = persistence.PreparedSynthesis(
        persistence.PREFIX + value.semantic_hash, value.input_json, value.semantic_hash
    )
    proof = persistence.loads(prepared.proof_json)
    if (
        proof["command"]["video_id"] != value.video_id
        or proof["command"]["output_language"] != value.output_language
        or sorted(r["evidence_id"] for r in proof["capture"]["source_refs"]) != sorted(value.evidence_ids)
    ):
        raise ValueError("Synthesis input binding differs")
    persistence.request_from_proof(prepared)
    return prepared


class MoonshotSystemSynthesisTransport(MoonshotK26CloudDistillationTransport):
    """New fixed profile only; inheriting transport code grants no qualification."""

    _PROVIDER, _MODEL = profile.PAIR
    _REQUEST_PROFILE_VERSION = profile.PROFILE_ID
    _PROMPT_VERSION = "system-synthesis-v1"
    synthesis_profile_id = profile.PROFILE_ID

    @classmethod
    def _request(cls, verified_input: VerifiedDistillationInput) -> dict[str, object]:
        try:
            prepared = prepared_input(verified_input)
            request = persistence.request_from_proof(prepared)
            wire, _ = profile.provider_wire(request)
            body: dict[str, object] = json.loads(wire)
        except (ValueError, KeyError):
            raise CloudDistillationPreDispatchError("Synthesis prepared request is invalid") from None
        return {**body, "endpoint_identity": _MOONSHOT_ENDPOINT_IDENTITY, "max_retries": 0}
