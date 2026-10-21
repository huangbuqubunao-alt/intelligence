"""Finite installed-machine choices. These entries are NOT execution profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from youtube_intel.local_distillation_profile import (
    FIXED_RUNTIME_PROFILE_ID,
    digest,
    resolve_profile,
)

CANDIDATE_ID = FIXED_RUNTIME_PROFILE_ID  # historical0.40.1 machine selection
CURRENT_CANDIDATE_ID = "local-intelligence-qwen35-9b-ollama-0.40.6-v1"


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
CATALOG = (
    InstalledCandidate(
        CANDIDATE_ID, _historical.model, _historical.model_digest, _historical.runtime
    ),
    InstalledCandidate(
        CURRENT_CANDIDATE_ID, _historical.model, _historical.model_digest, "0.40.6"
    ),
)


def resolve_candidate(identity: str) -> InstalledCandidate:
    for candidate in CATALOG:
        if identity == candidate.candidate_id:
            return candidate
    raise ValueError("unknown fixed installation candidate")
