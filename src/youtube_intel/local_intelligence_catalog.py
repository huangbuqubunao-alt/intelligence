"""Finite installed-machine choices. These entries are NOT execution profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from youtube_intel.local_distillation_profile import (
    ACTUAL_RUNTIME_PROFILE_ID,
    FIXED_RUNTIME_PROFILE_ID,
    binding_for_profile,
    digest,
    resolve_profile,
)

CANDIDATE_ID = FIXED_RUNTIME_PROFILE_ID  # historical0.40.1 machine selection
CURRENT_CANDIDATE_ID = "local-intelligence-qwen35-9b-ollama-0.40.6-v1"
ACTUAL_CANDIDATE_ID = "local-intelligence-qwen35-9b-ollama-0.40.9-v2"


@dataclass(frozen=True)
class InstalledCandidate:
    candidate_id: str
    model: str
    model_digest: str
    runtime: str

    @property
    def catalog_hash(self) -> str:
        return digest(
            {"contract": "local-intelligence-installation-catalog-v1", **asdict(self)}
        )


_historical = resolve_profile(FIXED_RUNTIME_PROFILE_ID)
_actual = binding_for_profile(ACTUAL_RUNTIME_PROFILE_ID)
CATALOG = (
    InstalledCandidate(
        CANDIDATE_ID, _historical.model, _historical.model_digest, _historical.runtime
    ),
    InstalledCandidate(
        CURRENT_CANDIDATE_ID, _historical.model, _historical.model_digest, "0.40.6"
    ),
    InstalledCandidate(ACTUAL_CANDIDATE_ID, _actual.model, _actual.model_digest, _actual.runtime),
)


def resolve_candidate(identity: str) -> InstalledCandidate:
    for candidate in CATALOG:
        if identity == candidate.candidate_id:
            return candidate
    raise ValueError("unknown fixed installation candidate")
