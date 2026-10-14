"""Prepare independent LOCAL_TEXT review evidence; no model execution route.

Importing or invoking this harness cannot contact a provider. Real LOCAL8
qualification remains BLOCKED by the failed original 9B gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from youtube_intel.distillation import (
    LocalTextDistillationProfile,
    VerifiedDistillationInput,
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def prepare_profile() -> dict[str, object]:
    profile = LocalTextDistillationProfile
    project = Path(__file__).resolve().parents[1]
    files = ("src/youtube_intel/distillation.py", "src/youtube_intel/state.py",
             "src/youtube_intel/intelligence_read.py", "src/youtube_intel/local_api.py",
             "scripts/prepare_readiness_local_text.py")
    return {"profile": "readiness-local-text-distillation-v1", "wire_version": profile.VERSION,
        "profile_sha256": profile.identity_hash(),
        "code_sha256": {name: hashlib.sha256((project / name).read_bytes()).hexdigest() for name in files},
        "content_inputs_frozen": False,
        "model": profile.MODEL, "model_digest": profile.DIGEST,
        "prompt_sha256": hashlib.sha256(profile.PROMPT.encode()).hexdigest(),
        "schema_sha256": hashlib.sha256(canonical(profile.schema())).hexdigest(),
        "production_qualified": False, "real_model_calls": 0,
        "status": "PREPARATION_ONLY_ORIGINAL_9B_QUALIFICATION_FAILED",
        "case_order": ["local-timed-en", "local-timed-zh", "local-txt-en", "local-txt-zh",
                       "local-md-en", "local-md-zh", "local-no-new", "local-injection"],
        "execution_authority": "NONE",
        "gates": ["original four-case qualification and independent semantic review PASS",
            "new exact code/profile/input freeze and independent pre-output review",
            "explicit owner instruction to start LOCAL8; one generation per case; stop on decisive failure",
            "independent semantic acceptance before a separately approved production reader"]}


def prepare_case(value: VerifiedDistillationInput) -> dict[str, object]:
    projection = LocalTextDistillationProfile.prepare(value)
    return {"profile": prepare_profile(), "verified_input_hash": value.semantic_hash,
        "context_hash": value.local_content_context_hash,
        "request_projection": projection,
        "request_sha256": hashlib.sha256(canonical(projection)).hexdigest(),
        "real_model_calls": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New, non-secret review JSON path")
    arguments = parser.parse_args()
    # Exclusive creation preserves all historical qualification evidence.
    with arguments.output.open("xb") as handle:
        handle.write(canonical(prepare_profile()) + b"\n")


if __name__ == "__main__":
    main()
