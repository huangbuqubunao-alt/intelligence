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
from .state import StateStoreError


def prepared_input(value: VerifiedDistillationInput) -> persistence.PreparedSynthesis:
    if (
        type(value) is not VerifiedDistillationInput
        or value.wire_version not in profile.PROFILE_IDS
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
        proof["transport"]["id"] != value.wire_version
        or
        proof["command"]["video_id"] != value.video_id
        or proof["command"]["output_language"] != value.output_language
        or sorted(r["evidence_id"] for r in proof["capture"]["source_refs"]) != sorted(value.evidence_ids)
    ):
        raise ValueError("Synthesis input binding differs")
    if value.wire_version in profile.SOURCE_LEVEL_PROFILE_IDS:
        try:
            capture = proof["capture"]
            if (proof["source_scope"] != "PUBLIC_YOUTUBE_TIMED_MEDIA"
                or capture["source"]["provider"] != "YOUTUBE" or capture["video"]["provider"] != "YOUTUBE"
                or capture["video"]["availability"] != "public"
                or persistence._assemble(proof["command"], capture, profile_id=value.wire_version) != prepared):
                raise ValueError("Synthesis public timed scope or complete capture differs")
        except (KeyError, TypeError, StateStoreError):
            raise ValueError("Synthesis public timed scope or complete capture is invalid") from None
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
            if verified_input.wire_version != cls.synthesis_profile_id:
                raise ValueError("Synthesis transport profile differs")
            prepared = prepared_input(verified_input)
            request = persistence.request_from_proof(prepared)
            wire, _ = profile.provider_wire(request, cls.synthesis_profile_id)
            body: dict[str, object] = json.loads(wire)
        except (ValueError, KeyError):
            raise CloudDistillationPreDispatchError("Synthesis prepared request is invalid") from None
        return {**body, "endpoint_identity": _MOONSHOT_ENDPOINT_IDENTITY, "max_retries": 0}

    def is_authorized_for(self, verified_input: VerifiedDistillationInput) -> bool:
        try:
            self._request(verified_input)
        except CloudDistillationPreDispatchError:
            return False
        return super().is_authorized_for(verified_input)


class MoonshotAttributionSynthesisTransport(MoonshotSystemSynthesisTransport):
    """Explicit v2 contract; no inherited qualification or new HTTP engine."""

    _REQUEST_PROFILE_VERSION = profile.ATTRIBUTION_PROFILE_ID
    _PROMPT_VERSION = "system-synthesis-v2-attribution"
    synthesis_profile_id = profile.ATTRIBUTION_PROFILE_ID

    def is_authorized_for(self, verified_input: VerifiedDistillationInput) -> bool:
        if type(verified_input) is not VerifiedDistillationInput:
            return False
        if self._authorization.production_eligible and not self._authorization.reviewed_synthesis_qualified(verified_input.output_language, profile_id=self.synthesis_profile_id):
            return False
        return super().is_authorized_for(verified_input)


class MoonshotSourceLevelSynthesisTransport(MoonshotAttributionSynthesisTransport):
    """Finite v3 source-level policy, sharing the exact guarded send boundary."""

    _REQUEST_PROFILE_VERSION = profile.SOURCE_LEVEL_PROFILE_ID
    _PROMPT_VERSION = "system-synthesis-v3-source-level"
    synthesis_profile_id = profile.SOURCE_LEVEL_PROFILE_ID


class MoonshotReadableSummarySynthesisTransport(MoonshotAttributionSynthesisTransport):
    """Finite v4 literal Summary view with unchanged source-level policy and gates."""

    _REQUEST_PROFILE_VERSION = profile.READABLE_SUMMARY_PROFILE_ID
    _PROMPT_VERSION = "system-synthesis-v4-readable-summary"
    synthesis_profile_id = profile.READABLE_SUMMARY_PROFILE_ID


class MoonshotJudgmentSynthesisTransport(MoonshotAttributionSynthesisTransport):
    """Finite v5: v4 rules plus restored Intelligence/field definition; same send boundary."""

    _REQUEST_PROFILE_VERSION = profile.JUDGMENT_PROFILE_ID
    _PROMPT_VERSION = "system-synthesis-v5-judgment"
    synthesis_profile_id = profile.JUDGMENT_PROFILE_ID
