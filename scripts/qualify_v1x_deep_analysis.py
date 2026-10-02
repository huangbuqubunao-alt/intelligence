"""Local-only qualification proposal; no cloud dispatch option."""

import argparse
from dataclasses import replace
from pathlib import Path

from youtube_intel.deep_analysis_activation import _fresh_local_probe
from youtube_intel.deep_analysis_evaluation import evaluate_route
from youtube_intel.deep_analysis_service import build_local_ollama_phase1b_route

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--data", required=True, type=Path)
args = parser.parse_args()
if _fresh_local_probe() != "REACHABLE":
    parser.error(
        "Pinned local model is unavailable or its digest changed; no generation was attempted."
    )
if args.data.exists() or args.output.exists():
    parser.error(
        "Use fresh isolated output/data paths; existing data is never overwritten."
    )
candidate = build_local_ollama_phase1b_route()


def checked_dispatch(*, prepared_dispatch):
    if _fresh_local_probe() != "REACHABLE":
        raise ValueError("Pinned local model changed during qualification")
    return candidate.dispatch(prepared_dispatch=prepared_dispatch)


record = evaluate_route(
    route=replace(candidate, dispatch=checked_dispatch),
    root=args.data,
    mode="LIVE_MODEL",
    stop_on_failure=True,
)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(record.model_dump_json(indent=2) + "\n")
print(
    "QUALIFIED_PROPOSAL_PENDING_REVIEW"
    if record.passes()
    else "FAILED_NOT_PRODUCTION_ELIGIBLE"
)
