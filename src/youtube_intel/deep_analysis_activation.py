"""Machine-local discovery and reviewed production activation, DA only."""

from __future__ import annotations

import json
from dataclasses import replace
from functools import lru_cache
from time import monotonic
from urllib.request import urlopen

from youtube_intel.deep_analysis_contracts import UntrustedDeepAnalysisResponseV1
from youtube_intel.deep_analysis_qualification import (
    PRODUCTION_QUALIFICATION_RECORDS,
    QualificationAuthority,
)
from youtube_intel.deep_analysis_runtime import PreparedDeepAnalysisDispatch
from youtube_intel.deep_analysis_service import (
    DeepAnalysisAvailability,
    DeepAnalysisCapability,
    DeepAnalysisReasonCode,
    DeepAnalysisRejected,
    DeepAnalysisStatus,
    build_local_ollama_phase1b_route,
    build_openai_phase1b_route,
)
from youtube_intel.ollama_deep_analysis import OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE


def _fresh_local_probe() -> str:
    profile = OLLAMA_LOCAL_DEEP_ANALYSIS_PROFILE
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            value = json.loads(response.read(1_000_000))
        matches = [m for m in value["models"] if m.get("name") == profile.model_id]
        if not matches:
            return "MODEL_UNAVAILABLE"
        return (
            "REACHABLE"
            if "sha256:" + matches[0].get("digest", "") == profile.model_digest
            else "PROFILE_MISMATCH"
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return "UNREACHABLE"


@lru_cache(maxsize=2)
def _local_probe(bucket: int) -> str:
    del bucket
    return _fresh_local_probe()


def production_deep_analysis_capability() -> DeepAnalysisCapability:
    # Cloud connectivity probes run only for a current live qualification.
    # Composition never generates a model response or pulls a local model.
    candidate = build_local_ollama_phase1b_route()

    def dispatch(
        *, prepared_dispatch: PreparedDeepAnalysisDispatch
    ) -> UntrustedDeepAnalysisResponseV1:
        # Cached discovery is suitable for UI, but execution rechecks the pinned
        # model digest immediately before sending any generation request.
        if _fresh_local_probe() != "REACHABLE":
            raise DeepAnalysisRejected(
                DeepAnalysisStatus(
                    availability=DeepAnalysisAvailability.NOT_QUALIFIED,
                    reason_code=DeepAnalysisReasonCode.NO_QUALIFIED_MODEL,
                )
            )
        return candidate.dispatch(prepared_dispatch=prepared_dispatch)

    local = replace(
        candidate,
        dispatch=dispatch,
        reachability=lambda: _local_probe(int(monotonic() // 30)),
    )
    return DeepAnalysisCapability(
        (local, build_openai_phase1b_route()),
        authority=QualificationAuthority(PRODUCTION_QUALIFICATION_RECORDS),
    )
