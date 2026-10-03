"""Phase 8 durable offline contract with actual ffprobe and immutable WAV media."""

import io
import json
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.local_content import LocalContentProvider
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.offline_transcription import (
    OfflineError,
    TranscriptionCapability,
    validate_result,
)
from youtube_intel.source_authority import sha256
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 3, tzinfo=UTC)
PROVENANCE = json.dumps(
    {
        "contract": "offline-timed-transcription-v1",
        "executor": "isolated-fixture",
        "model": "sha256:" + "a" * 64,
        "profile": "source-auto-t0-fixture",
    },
    sort_keys=True,
)
IDENTITY = sha256(PROVENANCE.encode())


def audio_bytes():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 32000)
    return buf.getvalue()


class Executor:
    def __init__(self, *, state="READY", failure=None):
        self.state = state
        self.failure = failure
        self.calls = 0
        self.release = threading.Event()
        self.release.set()
        self.started = threading.Event()

    def capability(self):
        return TranscriptionCapability(
            self.state,
            True,
            self.state != "RUNTIME_UNAVAILABLE",
            self.state == "READY",
            self.state == "READY",
            executor="isolated-fixture",
            model_identity="sha256:" + "a" * 64 if self.state == "READY" else None,
            execution_identity=IDENTITY if self.state == "READY" else None,
            reason_code=None if self.state == "READY" else self.state,
        )

    validate_result = staticmethod(validate_result)

    def transcribe(self, snapshot, *, duration_seconds):
        self.calls += 1
        assert snapshot.read_bytes() == audio_bytes()
        self.started.set()
        assert self.release.wait(3)
        if self.failure:
            raise OfflineError(self.failure)
        return validate_result(
            json.dumps(
                {
                    "language": "zh",
                    "segments": [
                        {
                            "start": 0.125,
                            "end": 1.75,
                            "text": "Sentence1 你好 café local media.",
                        }
                    ],
                }
            ).encode(),
            duration_seconds=duration_seconds,
            provenance=PROVENANCE,
        )


def wait_for(predicate):
    deadline = time.monotonic() + 10
    while not predicate():
        assert time.monotonic() < deadline
        time.sleep(0.01)


@pytest.fixture
def setup(tmp_path):
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=NOW)
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    imported = provider.import_bytes("voice.wav", audio_bytes())
    return repo, provider, imported.content_id


def service(setup, executor):
    repo, provider, cid = setup
    jobs = LocalTranscriptionJobs(
        repo, provider.data_root, executor=executor, now=lambda: NOW
    )
    wait_for(lambda: not jobs.capability()["checking"])
    return jobs


@pytest.mark.parametrize(
    "state", ["RUNTIME_UNAVAILABLE", "MODEL_MISSING", "UNSUPPORTED"]
)
def test_truthful_unavailability(setup, state):
    executor = Executor(state=state)
    jobs = service(setup, executor)
    assert jobs.status(setup[2])["status"] == state
    with pytest.raises(OfflineError):
        jobs.start(setup[2], IDENTITY)
    assert executor.calls == 0


def test_success_restart_summary_evidence_and_idempotency(setup):
    executor = Executor()
    jobs = service(setup, executor)
    cid = setup[2]
    jobs.start(cid, IDENTITY)
    wait_for(lambda: jobs.status(cid)["status"] == "READY")
    repo, provider, _ = setup
    restarted = SQLiteStateRepository(repo._database_path)
    restarted.bind_source_storage(provider.data_root)
    timed = restarted.get_verified_timed_transcript(video_id=cid)
    assert (
        timed
        and timed.cues[0].start_ms == 125
        and timed.cues[0].text == "Sentence1 你好 café local media."
    )
    assert repo.current_local_summary_pointer(cid)
    evidence = repo.list_evidence_for_presentation(cid)
    assert evidence
    assert (
        repo.resolve_verified_evidence_text(evidence[0]).locator_type == "TIMED_MEDIA"
    )
    jobs.start(cid, "different-selection")
    assert executor.calls == 1
    with repo._connect() as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM timed_transcripts WHERE video_id=?", (cid,)
            ).fetchone()[0]
            == 1
        )
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_failure_retry_new_attempt_no_fallback(setup):
    executor = Executor(failure="EXECUTOR_TIMEOUT")
    jobs = service(setup, executor)
    cid = setup[2]
    first = jobs.start(cid, IDENTITY)["attempt_id"]
    wait_for(lambda: jobs.status(cid)["status"] == "FAILED")
    assert jobs.status(cid)["last_failure_category"] == "EXECUTOR_TIMEOUT"
    assert jobs.repository.get_verified_timed_transcript(video_id=cid) is None
    executor.failure = None
    second = jobs.start(cid, IDENTITY)["attempt_id"]
    assert first != second
    wait_for(lambda: jobs.status(cid)["status"] == "READY")
    assert executor.calls == 2
    with jobs.repository._connect() as connection:
        assert {
            r[0] for r in connection.execute("SELECT pipeline_version FROM jobs")
        } == {"offline-timed-v1:" + IDENTITY}


def test_concurrent_clicks_one_job_and_no_scheduler_steal(setup):
    executor = Executor()
    executor.release.clear()
    jobs = service(setup, executor)
    cid = setup[2]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: jobs.start(cid, IDENTITY), range(12)))
    assert len({r["attempt_id"] for r in results}) == 1
    assert executor.started.wait(2)
    assert executor.calls == 1
    assert (
        jobs.repository.claim_next_job(
            owner="other", lease_until=NOW.replace(year=2027), now=NOW
        )
        is None
    )
    executor.release.set()
    wait_for(lambda: jobs.status(cid)["status"] == "READY")


def test_snapshot_and_transcript_tamper_fail_closed(setup):
    executor = Executor()
    jobs = service(setup, executor)
    repo, provider, cid = setup
    with repo._connect() as connection:
        row = connection.execute(
            "SELECT relative_path FROM artifacts WHERE artifact_id=(SELECT snapshot_artifact_id FROM content_source_snapshots WHERE content_id=?)",
            (cid,),
        ).fetchone()
    path = provider.data_root / row[0]
    original = path.read_bytes()
    path.write_bytes(b"bad")
    with pytest.raises(OfflineError, match="LOCAL_SOURCE_UNTRUSTED"):
        jobs.start(cid, IDENTITY)
    path.write_bytes(original)
    jobs.start(cid, IDENTITY)
    wait_for(lambda: jobs.status(cid)["status"] == "READY")
    with repo._connect() as connection:
        raw = connection.execute(
            "SELECT relative_path FROM artifacts WHERE video_id=? AND relative_path LIKE '%executor-output%'",
            (cid,),
        ).fetchone()[0]
    (provider.data_root / raw).write_bytes(b"bad")
    assert repo.get_verified_timed_transcript(video_id=cid) is None
    assert (
        repo.resolve_verified_evidence_text(repo.list_evidence_for_presentation(cid)[0])
        is None
    )
    with pytest.raises(OfflineError):
        jobs.status(cid)


def test_stale_restart_and_ready_without_runtime(setup):
    jobs = service(setup, Executor())
    cid = setup[2]
    with jobs.repository._connect() as c:
        stamp = "2026-10-03T00:00:00.000000Z"
        c.execute(
            "INSERT INTO jobs(job_id,scope_key,video_id,job_type,target_stage,pipeline_version,status,max_attempts,lease_owner,lease_until,available_at,created_at,updated_at) VALUES('dead','dead',?,'VIDEO_STAGE','TRANSCRIPT',?,'RUNNING',1,'dead',?,?,?,?)",
            (cid, "offline-timed-v1:" + IDENTITY, stamp, stamp, stamp, stamp),
        )
    jobs = service(setup, Executor())
    assert jobs.status(cid)["status"] == "INTERRUPTED"
    assert jobs.status(cid)["retry_available"]
    jobs.start(cid, IDENTITY)
    wait_for(lambda: jobs.status(cid)["status"] == "READY")
    absent = service(setup, Executor(state="MODEL_MISSING"))
    assert absent.status(cid)["status"] == "READY"
    assert absent.repository.get_verified_timed_transcript(video_id=cid)


def test_changed_selection_rejected(setup):
    executor = Executor()
    jobs = service(setup, executor)
    with pytest.raises(OfflineError, match="EXECUTOR_IDENTITY_CHANGED"):
        jobs.start(setup[2], "other")
    assert executor.calls == 0


def process_fixture(tmp_path):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "e2e"))
    from offline_executor_fixture import ProcessFixtureExecutor

    return ProcessFixtureExecutor(tmp_path / "fixture-executor")


@pytest.mark.parametrize("extension", [".wav", ".mp4"])
def test_real_preprocessing_and_isolated_process_contract(tmp_path, extension):
    import subprocess

    from youtube_intel.local_content import probe_media

    executor = process_fixture(tmp_path)
    source = tmp_path / "voice.wav"
    source.write_bytes(audio_bytes())
    if extension == ".mp4":
        video = tmp_path / "video.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=32x32:r=5:d=2",
                "-i",
                str(source),
                "-shortest",
                "-c:v",
                "mpeg4",
                str(video),
            ],
            check=True,
            timeout=20,
            capture_output=True,
        )
        source = video
    cap = executor.capability()
    assert cap.state == "READY" and cap.model_present
    result = executor.transcribe(
        source, duration_seconds=probe_media(source, extension)
    )
    assert (
        result.language == "zh" and result.raw_output and result.cues[0].start_ms == 125
    )
    assert list(executor.temporary_root.iterdir()) == []


@pytest.mark.parametrize(
    ("mode", "code"),
    [
        ("failure", "EXECUTOR_FAILED"),
        ("timeout", "EXECUTOR_TIMEOUT"),
        ("flood", "EXECUTOR_OUTPUT_LIMIT"),
        ("malformed", "TRANSCRIPT_INVALID"),
    ],
)
def test_isolated_process_failure_cleanup(tmp_path, mode, code):
    executor = process_fixture(tmp_path)
    executor.timeout = 0.2 if mode == "timeout" else 5
    (executor.root / "result-mode.txt").write_text(mode)
    source = tmp_path / "voice.wav"
    source.write_bytes(audio_bytes())
    with pytest.raises(OfflineError) as caught:
        executor.transcribe(source, duration_seconds=2)
    assert caught.value.code == code
    assert list(executor.temporary_root.iterdir()) == []


def test_no_discovery_readiness_or_unsafe_model_assets(tmp_path, monkeypatch):
    from youtube_intel import offline_transcription as module
    from youtube_intel.offline_transcription import MlxTimedExecutor, model_identity

    monkeypatch.setattr(module.importlib.util, "find_spec", lambda _: None)
    assert (
        MlxTimedExecutor(temporary_root=tmp_path / "temp").capability().state
        == "RUNTIME_UNAVAILABLE"
    )
    monkeypatch.undo()
    executor = process_fixture(tmp_path)
    original = model_identity(executor.model_path)
    (executor.model_path / "weights.safetensors").write_bytes(b"changed-model")
    assert model_identity(executor.model_path) != original
    (executor.model_path / "weights.safetensors").unlink()
    assert executor.capability().state == "MODEL_MISSING"
    (executor.model_path / "weights.safetensors").symlink_to(tmp_path / "outside")
    (tmp_path / "outside").write_bytes(b"weights")
    with pytest.raises(OSError):
        model_identity(executor.model_path)
    assert executor.capability().state != "READY"


def test_api_safe_diagnostics_no_paths_and_stale_selection(setup):
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService

    executor = Executor()
    jobs = service(setup, executor)
    app = LocalApiApplication(
        setup[0],
        ProductOrchestrationService(setup[0]),
        data_root=setup[1].data_root,
        transcription_jobs=jobs,
    )
    status, body = app.handle("GET", "/api/v1/local/transcription/capability")
    assert status == 200 and body["capability"]["state"] == "READY"
    assert str(setup[1].data_root) not in json.dumps(body)
    status, body = app.handle(
        "POST",
        f"/api/v1/videos/{setup[2]}/transcription",
        json.dumps({"execution_identity": "stale"}).encode(),
    )
    assert status == 409 and body["error"]["code"] == "EXECUTOR_IDENTITY_CHANGED"
    assert "/Users/" not in json.dumps(body)
    status, body = app.handle(
        "POST",
        f"/api/v1/videos/{setup[2]}/transcription",
        json.dumps({"execution_identity": IDENTITY}).encode(),
    )
    assert status == 202
    wait_for(lambda: jobs.status(setup[2])["status"] == "READY")
    status, body = app.handle("GET", f"/api/v1/videos/{setup[2]}")
    assert status == 200 and body["transcript"]["timed_segments"][0]["start_ms"] == 125


def test_backup_restore_without_runtime_and_no_model_weights(setup, tmp_path):
    import zipfile

    from youtube_intel.backup_restore import BackupRestoreService

    jobs = service(setup, Executor())
    jobs.start(setup[2], IDENTITY)
    wait_for(lambda: jobs.status(setup[2])["status"] == "READY")
    wait_for(
        lambda: jobs.repository.latest_video_job(setup[2]).status.value == "SUCCEEDED"
    )
    (jobs.machine_root / "private-model-weights.npz").write_bytes(
        b"not-product-authority"
    )
    backup = BackupRestoreService(
        database=setup[0]._database_path, data_root=setup[1].data_root
    )
    created = backup.create_backup()
    path, _ = backup.backup_download(created.backup_id)
    with zipfile.ZipFile(path) as archive:
        assert not any(
            "weights" in name or ".local-transcription" in name
            for name in archive.namelist()
        )
    target = tmp_path / "restored"
    target.mkdir()
    restore = BackupRestoreService(
        database=target / "state.sqlite3", data_root=target / "data"
    )
    stage = restore.stage_restore(path.read_bytes())
    restore.confirm_restore(stage.restore_id)
    restore.recover_and_apply_pending_restore()
    repo = SQLiteStateRepository(target / "state.sqlite3")
    repo.bind_source_storage(target / "data")
    absent = LocalTranscriptionJobs(
        repo, target / "data", executor=Executor(state="MODEL_MISSING")
    )
    wait_for(lambda: not absent.capability()["checking"])
    assert absent.status(setup[2])["status"] == "READY"
    assert repo.get_verified_timed_transcript(video_id=setup[2])
    assert repo.current_local_summary_pointer(setup[2])
    second = LocalContentProvider(repo, target / "data").import_bytes(
        "new.wav", audio_bytes() + b"new"
    )
    assert absent.status(second.content_id)["status"] == "MODEL_MISSING"
    with pytest.raises(OfflineError):
        absent.start(second.content_id, IDENTITY)


def test_original_media_removed_or_modified_still_uses_snapshot(setup, tmp_path):
    original = tmp_path / "original.wav"
    original.write_bytes(audio_bytes())
    original.unlink()
    original.write_bytes(b"different user-owned bytes")
    executor = Executor()
    jobs = service(setup, executor)
    jobs.start(setup[2], IDENTITY)
    wait_for(lambda: jobs.status(setup[2])["status"] == "READY")
    assert original.read_bytes() == b"different user-owned bytes"
    assert executor.calls == 1


def test_temp_symlink_escape_rejected(tmp_path):
    executor = process_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    executor.temporary_root.symlink_to(outside, target_is_directory=True)
    source = tmp_path / "voice.wav"
    source.write_bytes(audio_bytes())
    with pytest.raises(OfflineError):
        executor.transcribe(source, duration_seconds=2)
    assert list(outside.iterdir()) == []


def test_local_media_presentation_verifies_source_once(setup, monkeypatch):
    from youtube_intel import source_authority

    jobs = service(setup, Executor())
    jobs.start(setup[2], IDENTITY)
    wait_for(lambda: jobs.status(setup[2])["status"] == "READY")
    original = source_authority.verify_source
    calls = []

    def check(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(source_authority, "verify_source", check)
    pairs = jobs.repository.get_verified_local_media_evidence(setup[2])
    assert pairs and len(pairs) >= 2 and len(calls) == 1
    assert all(v.video_id == setup[2] for _, v in pairs)


def test_stale_temporary_cleanup_keeps_foreign_and_symlink_targets(setup, tmp_path):
    jobs = service(setup, Executor())
    stale = jobs.machine_root / "source-attempt-abcdefgh"
    stale.mkdir()
    (stale / "audio.wav").write_bytes(b"stale")
    foreign = jobs.machine_root / "foreign"
    foreign.mkdir()
    (foreign / "keep").write_bytes(b"keep")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_bytes(b"keep")
    (jobs.machine_root / "source-attempt-abcdefgi").symlink_to(
        outside, target_is_directory=True
    )
    jobs.status(setup[2])
    assert (
        not stale.exists()
        and (foreign / "keep").read_bytes() == b"keep"
        and (outside / "keep").read_bytes() == b"keep"
    )


def test_invalid_model_dimensions_never_launch_model_loader(tmp_path, monkeypatch):
    executor = process_fixture(tmp_path)
    config = executor.model_path / "config.json"
    data = json.loads(config.read_text())
    data["n_audio_state"] = 1000000000
    config.write_text(json.dumps(data))
    assert executor.capability().state == "UNSUPPORTED"
    assert not executor.capability().executor_compatible
