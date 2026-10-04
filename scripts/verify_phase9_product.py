"""Fresh process: verify real persisted authority, absence, timeout and restore."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import time
import wave
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.offline_transcription import MlxTimedExecutor, OfflineError
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.runtime_composition import _deep_analysis_production_capability
from youtube_intel.source_authority import verify_source
from youtube_intel.state import SQLiteStateRepository


def wait(predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() >= deadline:
            raise TimeoutError("bounded verification")
        time.sleep(0.1)


def trusted(repo, sample):
    timed = repo.get_verified_timed_transcript(video_id=sample["content_id"])
    assert timed is not None
    actual = [{"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in timed.cues]
    assert actual == sample["cues"]
    assert repo.current_local_summary_pointer(sample["content_id"])
    pairs = repo.get_verified_local_media_evidence(sample["content_id"])
    assert pairs
    for evidence, resolved in pairs:
        assert not evidence.evidence_id.startswith("candidate")
        assert resolved.video_id == sample["content_id"] and resolved.locator_type == "TIMED_MEDIA"
        selected = [c for c in timed.cues if c.start_ms >= resolved.start_ms and c.end_ms <= resolved.end_ms]
        assert selected and selected[0].start_ms == resolved.start_ms and selected[-1].end_ms == resolved.end_ms
        assert resolved.excerpt == "\n".join(c.text for c in selected)
    with repo._connect() as connection:
        source = verify_source(repo, connection, sample["content_id"])
        assert source is not None
    return {"content_id": sample["content_id"], "cue_count": len(actual), "language": source["language"], "timed_hash": timed.timed_transcript_hash, "evidence_count": len(pairs), "summary": True, "exact_cues": True, "exact_evidence_times_and_text": True}


def database(repo):
    with repo._connect() as connection:
        quick = connection.execute("PRAGMA quick_check").fetchall()
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
        migrations = [dict(row) for row in connection.execute("SELECT * FROM schema_migrations ORDER BY version")]
    assert [r[0] for r in quick] == ["ok"] and [r[0] for r in integrity] == ["ok"] and not foreign
    return {"quick_check": "ok", "integrity_check": "ok", "foreign_key_check": [], "migrations": migrations}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    product = root / "real-product-corrected-v1"
    report = json.loads((root / "results-corrected-v1" / "qualification.json").read_text())
    samples = [s for s in report["samples"] if s["trusted_timed_transcript"]]
    repo = SQLiteStateRepository(product / "state.sqlite3")
    repo.initialize(now=datetime.now(UTC))
    repo.bind_source_storage(product / "data")
    jobs = LocalTranscriptionJobs(repo, product / "data")
    wait(lambda: not jobs.capability()["checking"])
    capability = jobs.capability()
    assert capability["state"] == "READY" and capability["qualification_state"] == "FAILED"
    assert not capability["production_eligible"]
    output = {"restart": [trusted(repo, s) for s in samples], "qualification_after_restart": capability, "production_da": "NONE", "model_unavailable": [], "timeout": {}, "backup_restore": {}}
    assert _deep_analysis_production_capability().execution_route() is None
    # Distinct nonpersonal speech snapshot; no private media or microphone.
    with wave.open(str(root / "corpus" / "very-short.wav")) as audio:
        frames = audio.readframes(audio.getnframes())
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(frames + b"\0\0" * 4000)
    cid = LocalContentProvider(repo, product / "data").import_bytes("fresh-short.wav", buffer.getvalue()).content_id
    assert jobs.status(cid)["status"] == "QUALIFICATION_REQUIRED"
    try:
        jobs.start(cid, capability["execution_identity"])
    except OfflineError as error:
        assert error.code == "ACOUSTIC_NOT_QUALIFIED"
    else:
        raise AssertionError("unqualified production admission")
    output["unqualified_production_blocked"] = True
    model_path = jobs.executor.model_path
    jobs.configure(None)
    wait(lambda: not jobs.capability()["checking"])
    assert jobs.capability()["state"] == "MODEL_MISSING"
    for sample in samples:
        assert jobs.status(sample["content_id"])["status"] == "READY"
        output["model_unavailable"].append(trusted(repo, sample))
    assert jobs.status(cid)["status"] == "MODEL_MISSING"
    try:
        jobs.start(cid, "absent")
    except OfflineError as error:
        assert error.code == "MODEL_MISSING"
    else:
        raise AssertionError("no fallback when model absent")
    jobs.configure(str(model_path))
    wait(lambda: not jobs.capability()["checking"])
    assert jobs.capability()["qualification_state"] == "FAILED"
    # Real worker timeout and explicit recovery through the accepted supervisor.
    safety = root / "safety-product"
    safety.mkdir(exist_ok=True)
    safety_repo = SQLiteStateRepository(safety / "state.sqlite3")
    safety_repo.initialize(now=datetime.now(UTC))
    imported = LocalContentProvider(safety_repo, safety / "data").import_bytes("short-timeout.wav", buffer.getvalue())
    executor = MlxTimedExecutor(model_path=model_path, temporary_root=safety / ".local-transcription" / "temporary", timeout=0.2)
    test_jobs = LocalTranscriptionJobs(safety_repo, safety / "data", executor=executor)
    wait(lambda: not test_jobs.capability()["checking"])
    app = LocalApiApplication(safety_repo, ProductOrchestrationService(safety_repo), data_root=safety / "data", transcription_jobs=test_jobs)
    start = time.monotonic()
    first = test_jobs.start(imported.content_id, test_jobs.capability()["execution_identity"])["attempt_id"]
    latencies = []
    while test_jobs.status(imported.content_id)["status"] == "RUNNING":
        before = time.monotonic()
        assert app.handle("GET", "/api/v1/local/transcription/capability")[0] == 200
        latencies.append(time.monotonic() - before)
        assert time.monotonic() - start < 15
        time.sleep(0.05)
    status = test_jobs.status(imported.content_id)
    assert status["status"] == "FAILED" and status["last_failure_category"] == "EXECUTOR_TIMEOUT"
    assert list(executor.temporary_root.iterdir()) == []
    output["timeout"] = {"configured_test_deadline_seconds": 0.2, "production_deadline_seconds": 1800, "terminal": status["status"], "failure": status["last_failure_category"], "whole_attempt_seconds": time.monotonic() - start, "max_api_seconds": max(latencies, default=0), "temporary_cleaned": True}
    executor.timeout = 1800
    second = test_jobs.start(imported.content_id, test_jobs.capability()["execution_identity"])["attempt_id"]
    assert second != first
    wait(lambda: test_jobs.status(imported.content_id)["status"] == "READY")
    wait(lambda: safety_repo.latest_video_job(imported.content_id).status.value == "SUCCEEDED")
    output["timeout"]["real_retry"] = "SUCCEEDED"
    output["timeout"]["real_retry_cues"] = [c.text for c in safety_repo.get_verified_timed_transcript(video_id=imported.content_id).cues]
    backups = BackupRestoreService(database=product / "state.sqlite3", data_root=product / "data")
    created = backups.create_backup()
    archive_path, _ = backups.backup_download(created.backup_id)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert not any("weights" in n or ".local-transcription" in n or "qualification.seal" in n for n in names)
    target = root / "restored-product"
    target.mkdir(exist_ok=True)
    restore = BackupRestoreService(database=target / "state.sqlite3", data_root=target / "data")
    staged = restore.stage_restore(archive_path.read_bytes())
    restore.confirm_restore(staged.restore_id)
    restore.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(target / "state.sqlite3")
    restored.bind_source_storage(target / "data")
    absent = LocalTranscriptionJobs(restored, target / "data")
    wait(lambda: not absent.capability()["checking"])
    assert absent.capability()["state"] == "MODEL_MISSING"
    assert absent.capability()["qualification_state"] == "NOT_TESTED"
    output["backup_restore"] = {"model_and_receipt_excluded": True, "restored_without_model": [trusted(restored, s) for s in samples], "qualification_not_inherited": True, "new_transcription": absent.status(cid)["status"]}
    output["databases"] = {"real": database(repo), "safety": database(safety_repo), "restored": database(restored)}
    probe = subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)", str(Path(".venv/bin/python").absolute()), "-c", "import socket,json; s=socket.socket();\ntry: s.connect(('127.0.0.1',9))\nexcept OSError as e: print(json.dumps({'denied':e.errno in (1,13),'errno':e.errno}))\nelse: raise AssertionError('network allowed')"], capture_output=True, check=True, timeout=10)
    output["native_network_denial"] = json.loads(probe.stdout)
    assert output["native_network_denial"]["denied"]
    (root / "product-verification.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"restart_real_transcripts": len(samples), "model_absence_preserves_authority": True, "timeout": output["timeout"], "backup_restore": "passed", "network_denial": output["native_network_denial"], "production_da": "NONE"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
