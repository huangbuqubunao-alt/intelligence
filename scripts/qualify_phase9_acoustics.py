"""Real bounded acoustic run through Phase 8 Local jobs, never a fake executor.

Only adds /usr/bin/time measurement around the unchanged sandboxed worker and
observes preprocessing wall time. Decoder never sees ground truth. No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import threading
import time
from pathlib import Path

from youtube_intel import offline_transcription as boundary
from youtube_intel.acoustic_scoring import POLICY, coverage, score, text_units
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository


def retained(reference: str, observed: str, language: str) -> float:
    expected, actual = text_units(reference, language), text_units(observed, language)
    row = [0] * (len(actual) + 1)
    for unit in expected:
        next_row = [0]
        for i, candidate in enumerate(actual, 1):
            next_row.append(row[i - 1] + 1 if unit == candidate else max(row[i], next_row[-1]))
        row = next_row
    return row[-1] / len(expected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    corpus = root / "corpus"
    manifest_bytes = (corpus / "corpus-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    model_info = json.loads((root / "model-manifest.json").read_text())
    model = root / "models" / "whisper-large-v3-turbo" / model_info["revision"]
    product = root / "real-product"
    product.mkdir(parents=True, exist_ok=True)
    results = root / "results"
    results.mkdir(exist_ok=True)
    if (results / "qualification.json").exists():
        raise ValueError("retain existing results; use a distinct run identity")
    measurements, mutex = [], threading.Lock()
    original = boundary.run_bounded
    active_sample = {"id": "initial-probe"}

    def measured(args, **kwargs):
        kind = "transcribe" if "--transcribe" in args else "load" if "--validate-model" in args else "probe" if "--probe" in args else "preprocess" if "-c:a" in args else "ffprobe"
        index = len(measurements)
        metrics = results / f"{active_sample['id']}-{kind}-{index}.resource.txt"
        command = ["/usr/bin/time", "-l", "-o", str(metrics), *args] if kind in {"transcribe", "load", "probe"} else args
        started = time.monotonic()
        outcome = "FAILED"
        try:
            raw = original(command, **kwargs)
            outcome = "SUCCEEDED"
            if kind == "transcribe":
                (results / (active_sample["id"] + ".raw.json")).write_bytes(raw)
            return raw
        finally:
            record = {"sample": active_sample["id"], "kind": kind, "wall_seconds": time.monotonic() - started, "outcome": outcome}
            if metrics.exists():
                match = re.search(r"(\d+)\s+maximum resident set size", metrics.read_text())
                record["peak_rss_bytes"] = int(match[1]) if match else None
            with mutex:
                measurements.append(record)

    boundary.run_bounded = measured
    executor = boundary.MlxTimedExecutor(model_path=model, temporary_root=product / "worker-temporary")
    repo = SQLiteStateRepository(product / "state.sqlite3")
    from datetime import UTC, datetime
    repo.initialize(now=datetime.now(UTC))
    provider = LocalContentProvider(repo, product / "data")
    jobs = LocalTranscriptionJobs(repo, product / "data", executor=executor)
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=product / "data", transcription_jobs=jobs)
    deadline = time.monotonic() + 90
    while jobs.capability()["checking"]:
        if time.monotonic() >= deadline:
            raise TimeoutError("model compatibility deadline")
        time.sleep(0.1)
    capability = jobs.capability()
    print(json.dumps({"capability": capability}), flush=True)
    samples = list(manifest["samples"])
    english = next(s for s in samples if s["id"] == "english-clean")
    video = corpus / "english-video.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:r=5:d={english['duration_seconds']}", "-i", str(corpus / english["file"]), "-shortest", "-c:v", "mpeg4", "-c:a", "aac", str(video)], check=True, timeout=30)
    samples += [{**english, "id": "english-video", "file": video.name, "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "bytes": video.stat().st_size}, {**english, "id": "english-repeat"}]
    report = {"model": model_info, "corpus_sha256": manifest["corpus_sha256"], "corpus_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "scoring_policy": POLICY, "capability": capability, "samples": [], "measurements": measurements, "offline": {"native_worker_sandbox": "deny network*", "worker_hf_download_and_socket_connect": "denied", "HF_HUB_OFFLINE": True, "cloud_dispatch": 0, "source_uploads": 0}}
    for sample in samples:
        active_sample["id"] = sample["id"]
        source = corpus / sample["file"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != sample["sha256"]:
            raise ValueError("frozen corpus changed")
        imported = provider.import_bytes(sample["id"] + source.suffix, source.read_bytes())
        start = time.monotonic()
        entry = {"id": sample["id"], "content_id": imported.content_id, "media_kind": "VIDEO" if source.suffix == ".mp4" else "AUDIO", "duration_seconds": sample["duration_seconds"], "language_scorer": sample["language"], "expected_sha256": sample["expected_sha256"], "source_sha256": sample["sha256"], "responsiveness_seconds": []}
        if capability["state"] == "READY":
            jobs.start(imported.content_id, capability["execution_identity"])
            deadline = time.monotonic() + 1950
            while True:
                read_start = time.monotonic()
                code, data = app.handle("GET", "/api/v1/local/transcription/capability")
                entry["responsiveness_seconds"].append(time.monotonic() - read_start)
                assert code == 200
                status = jobs.status(imported.content_id)
                if status["status"] not in {"RUNNING", "PENDING"}:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("accepted worker timeout failed")
                time.sleep(0.3)
            entry["job_status"] = status
        else:
            entry["job_status"] = {"status": capability["state"]}
        entry["product_wall_seconds"] = time.monotonic() - start
        relevant = [m for m in measurements if m["sample"] == sample["id"]]
        entry["preprocessing_seconds"] = sum(m["wall_seconds"] for m in relevant if m["kind"] in {"preprocess", "ffprobe"})
        transcription = [m for m in relevant if m["kind"] == "transcribe"]
        entry["transcription_seconds"] = sum(m["wall_seconds"] for m in transcription)
        entry["rtf"] = entry["transcription_seconds"] / sample["duration_seconds"] if transcription else None
        entry["peak_rss_bytes"] = max((m.get("peak_rss_bytes") or 0 for m in transcription), default=0) or None
        raw_path = results / (sample["id"] + ".raw.json")
        if raw_path.exists():
            raw = raw_path.read_bytes()
            response = json.loads(raw)
            segments = response["segments"]
            actual = " ".join(s["text"] for s in segments)
            entry["raw_sha256"] = hashlib.sha256(raw).hexdigest()
            entry["actual_text"] = actual
            entry["detected_language"] = response.get("language")
            entry["score"] = score(sample["expected"], actual, sample["language"])
            entry["score_repeat_identical"] = entry["score"] == score(sample["expected"], actual, sample["language"])
            entry["coverage"] = coverage([(r["start"], r["end"]) for r in sample["speech_regions"]], [(s["start"], s["end"]) for s in segments])
            # LCS recall catches complete meaningful utterance omission even when
            # a broad timestamp spans missing speech and aggregate WER is low.
            recalls = [retained(r["text"], actual, sample["language"]) for r in sample["speech_regions"]]
            entry["utterance_recall"] = recalls
            entry["no_catastrophic_omission"] = all(r >= 0.5 for r in recalls)
            entry["accuracy_gate"] = entry["score"]["error_rate"] <= (0.20 if sample["language"] == "mixed" else 0.15)
        timed = repo.get_verified_timed_transcript(video_id=imported.content_id)
        entry["trusted_timed_transcript"] = timed is not None
        if timed:
            entry["cues"] = [{"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in timed.cues]
            entry["summary"] = repo.current_local_summary_pointer(imported.content_id) is not None
            evidence = repo.list_evidence_for_presentation(imported.content_id)
            entry["durable_evidence"] = [e.model_dump(mode="json") for e in evidence]
            entry["evidence_resolves"] = bool(evidence) and all(repo.resolve_verified_evidence_text(e) is not None for e in evidence)
        entry["passed"] = bool(entry.get("accuracy_gate") and entry.get("no_catastrophic_omission") and entry.get("coverage", {}).get("passed") and timed and entry.get("summary") and entry.get("evidence_resolves") and entry["product_wall_seconds"] < 1800)
        report["samples"].append(entry)
        (results / "qualification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"sample": sample["id"], "status": entry["job_status"]["status"], "score": entry.get("score"), "coverage": entry.get("coverage", {}).get("passed"), "seconds": entry["transcription_seconds"], "rtf": entry["rtf"], "passed": entry["passed"]}), flush=True)
    report["verdict"] = "PASSED" if all(s["passed"] for s in report["samples"]) else "FAILED"
    (results / "qualification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"]}), flush=True)


if __name__ == "__main__":
    main()
