"""Receipt adversaries use tiny process fixtures, never production acoustic proof."""

import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.acoustic_qualification import current_tuple, seal_record
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.offline_transcription import OfflineError, model_identity
from youtube_intel.state import SQLiteStateRepository

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "e2e"))
from offline_executor_fixture import ProcessFixtureExecutor  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))
from test_acoustic_qualification import evidence  # noqa: E402


def origin(executor):
    value = {"repository": "mlx-community/whisper-large-v3-turbo", "revision": "a" * 40, "phase8_model_identity": model_identity(executor.model_path)}
    value["manifest_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (executor.model_path / "model-origin.json").write_text(json.dumps(value))
    return value


def test_model_present_not_tested_then_weight_tamper_stales(tmp_path):
    executor = ProcessFixtureExecutor(tmp_path / "fixture")
    value = origin(executor)
    cap = executor.capability()
    assert cap.state == "READY" and cap.model_present
    assert cap.qualification_state == "NOT_TESTED" and not cap.production_eligible
    identity = current_tuple(executor.model_path, cap.model_identity, value)
    seal_record(executor.temporary_root.parent, identity, evidence=evidence(), audit=b"test-only audit")
    assert executor.capability().qualification_state == "PASSED"
    weights = executor.model_path / "weights.safetensors"
    weights.write_bytes(b"tampered-not-real-model-weights")
    assert executor.capability().qualification_state == "STALE"
    assert not executor.capability().production_eligible
    weights.unlink()
    assert executor.capability().state == "MODEL_MISSING"
    assert executor.capability().qualification_state == "STALE"


def test_model_revision_and_manifest_tamper_stale(tmp_path):
    executor = ProcessFixtureExecutor(tmp_path / "fixture")
    value = origin(executor)
    cap = executor.capability()
    identity = current_tuple(executor.model_path, cap.model_identity, value)
    seal_record(executor.temporary_root.parent, identity, evidence=evidence(), audit=b"test-only audit")
    value["revision"] = "b" * 40
    value.pop("manifest_sha256")
    value["manifest_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (executor.model_path / "model-origin.json").write_text(json.dumps(value))
    assert executor.capability().qualification_state == "STALE"


def test_incomplete_directory_is_never_qualified(tmp_path):
    executor = ProcessFixtureExecutor(tmp_path / "fixture")
    (executor.model_path / "config.json").unlink()
    cap = executor.capability()
    assert cap.state == "MODEL_MISSING" and not cap.production_eligible


def test_settings_cannot_mint_qualification_or_bypass_admission(tmp_path, monkeypatch):
    from youtube_intel import local_transcription_jobs as module
    from youtube_intel.local_api import ApiError, LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    executor = ProcessFixtureExecutor(tmp_path / "fixture")
    origin(executor)
    monkeypatch.setattr(module, "MlxTimedExecutor", lambda **kwargs: executor)
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=datetime.now(UTC))
    data = tmp_path / "data"
    jobs = LocalTranscriptionJobs(repo, data)  # ordinary production admission
    deadline = time.monotonic() + 10
    while jobs.capability()["checking"]:
        assert time.monotonic() < deadline
        time.sleep(0.02)
    import io
    import wave
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 32000)
    cid = LocalContentProvider(repo, data).import_bytes("nonpersonal.wav", buffer.getvalue()).content_id
    cap = jobs.capability()
    assert cap["model_present"] and cap["qualification_state"] == "NOT_TESTED"
    assert jobs.status(cid)["status"] == "QUALIFICATION_REQUIRED"
    assert not jobs.status(cid)["start_available"]
    with pytest.raises(OfflineError, match="ACOUSTIC_NOT_QUALIFIED"):
        jobs.start(cid, cap["execution_identity"])
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=data, transcription_jobs=jobs)
    with pytest.raises(ApiError, match="unsupported fields"):
        app.handle("PUT", "/api/v1/local/transcription/model", json.dumps({"model_path": str(executor.model_path), "qualified": True}).encode())
    assert not (jobs.machine_root / "qualification.json").exists()
    assert jobs.capability()["qualification_state"] == "NOT_TESTED"
