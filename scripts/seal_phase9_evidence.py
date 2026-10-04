"""Seal measured Phase 9 results offline; no Settings or application entrypoint."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

from youtube_intel.acoustic_qualification import (
    QualificationEvidence,
    SampleResult,
    canonical,
    current_tuple,
    qualification_status,
    seal_record,
)
from youtube_intel.acoustic_scoring import coverage, score, utterance_recalls
from youtube_intel.offline_transcription import OfflineError, validate_result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    results = root / "results-corrected-v1"
    report = json.loads((results / "qualification.json").read_text())
    manifest = json.loads((root / "model-manifest.json").read_text())
    model = root / "models" / "whisper-large-v3-turbo" / manifest["revision"]
    (model / "model-origin.json").write_bytes(canonical(manifest))
    identity = current_tuple(model, manifest["phase8_model_identity"], manifest)
    corpus = json.loads((root / "corpus" / "corpus-manifest.json").read_text())
    for sample in report["samples"]:
        specification = next(s for s in corpus["samples"] if s["id"] == ("english-clean" if sample["id"] in {"english-video", "english-repeat"} else sample["id"]))
        if sample.get("actual_text"):
            sample["utterance_recall"] = utterance_recalls([r["text"] for r in specification["speech_regions"]], sample["actual_text"], sample["language_scorer"])
            sample["no_catastrophic_omission"] = all(r >= 0.5 for r in sample["utterance_recall"])
            raw = json.loads((results / (sample["id"] + ".raw.json")).read_text())
            deviations = [{"start_deviation_seconds": min(abs(r["start"] - s["start"]) for s in raw["segments"]), "end_deviation_seconds": min(abs(r["end"] - s["end"]) for s in raw["segments"])} for r in specification["speech_regions"]]
            sample["timing_deviation"] = {"method": "nearest segment boundaries to energy-threshold OS utterance boundaries; diagnostic only, not word timing precision", "utterances": deviations}
    medium = next(s for s in corpus["samples"] if s["id"] == "medium")
    diagnostic = (root / "sdk-diagnostic.stderr.txt").read_text()
    observed = ast.literal_eval(next(line[9:] for line in diagnostic.splitlines() if line.startswith("SEGMENTS ")))
    segments = [{"start": start, "end": end, "text": text} for start, end, text in observed]
    actual = " ".join(s["text"] for s in segments)
    medium_diagnostic = {
        "source": "instrumented actual SDK return; no decoder parameters changed",
        "diagnostic_sha256": hashlib.sha256(diagnostic.encode()).hexdigest(),
        "nonfinite_fields": [line for line in diagnostic.splitlines() if line.startswith("NONFINITE ")],
        "segments": segments,
        "score": score(medium["expected"], actual, "en"),
        "coverage": coverage([(r["start"], r["end"]) for r in medium["speech_regions"]], [(s["start"], s["end"]) for s in segments]),
        "zero_duration_segments": sum(s["start"] == s["end"] for s in segments),
        "out_of_duration_segments": sum(s["end"] > medium["duration_seconds"] + 1 for s in segments),
        "last_end_seconds": segments[-1]["end"],
        "media_duration_seconds": medium["duration_seconds"],
        "trusted": False,
    }
    try:
        validate_result(canonical({"language": "en", "segments": segments}), duration_seconds=medium["duration_seconds"], provenance="diagnostic-only")
    except OfflineError as error:
        medium_diagnostic["contract_rejection"] = error.code
    else:
        raise AssertionError("known invalid medium output must be rejected")
    for measurement in report["measurements"]:
        matches = list(results.glob(f"{measurement['sample']}-{measurement['kind']}-*.resource.txt"))
        if len(matches) == 1:
            match = re.search(r"(\d+)\s+peak memory footprint", matches[0].read_text())
            measurement["peak_memory_footprint_bytes"] = int(match[1]) if match else None
    samples = tuple(SampleResult(
        name=s["id"], source_sha256=s["source_sha256"], expected_sha256=s["expected_sha256"],
        error_rate=s.get("score", {}).get("error_rate"), duration_seconds=s["duration_seconds"],
        processing_seconds=s["transcription_seconds"], completed=s["trusted_timed_transcript"],
        timestamps_valid=s["trusted_timed_transcript"], coverage_passed=s.get("coverage", {}).get("passed", False), no_omission=s.get("no_catastrophic_omission", False),
    ) for s in report["samples"])
    evidence = QualificationEvidence(corpus_sha256=report["corpus_sha256"], samples=samples, offline=True, cloud_dispatches=0, source_uploads=0)
    audit = {"qualification_tuple": identity, "model_manifest": manifest, "corpus_manifest": corpus, "acoustic_run": report, "first_load": json.loads((root / "first-load.json").read_text()), "medium_diagnostic": medium_diagnostic, "initial_failure": "Real Whisper boundary spaces rejected by Phase 8 cue type; fixed preserving exact output. Harness treated durable Evidence IDs as objects; corrected. Initial results retained.", "limitations": ["Synthetic installed OS voices only; no population-level human speech accuracy claim.", "Private-stage gates, not public distribution or scientific benchmark certification.", "First cold capability timing includes runtime import, identity hashing and actual model loading.", "SDK nonfinite medium metadata and invented trailing speech retained as hard failures; no profile tuning."]}
    payload = canonical(audit)
    output = root / "final-acoustic-evidence.json"
    output.write_bytes(payload)
    machine = root / "real-product-corrected-v1" / ".local-transcription"
    seal_record(machine, identity, evidence=evidence, audit=payload)
    (machine / "model.json").write_text(json.dumps({"model_path": str(model)}))
    status = qualification_status(machine, identity)
    (root / "qualification-state.json").write_bytes(canonical(status))
    assert status["state"] == "FAILED" and not status["production_eligible"]
    print(json.dumps({"verdict": status, "audit_sha256": hashlib.sha256(payload).hexdigest(), "medium_score": medium_diagnostic["score"], "medium_contract": medium_diagnostic["contract_rejection"], "medium_zero_duration_segments": medium_diagnostic["zero_duration_segments"], "medium_out_of_duration_segments": medium_diagnostic["out_of_duration_segments"]}, indent=2))


if __name__ == "__main__":
    main()
