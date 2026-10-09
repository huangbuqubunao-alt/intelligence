"""D2-01 real-byte admission/projection: isolated SQLite, no model/network calls."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.local_content import LocalContentProvider, MediaTranscript
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository

NOW = datetime(2026, 10, 9, tzinfo=UTC)


@pytest.fixture
def app(tmp_path: Path) -> LocalApiApplication:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=NOW)
    return LocalApiApplication(
        repo, ProductOrchestrationService(repo, now=lambda: NOW),
        data_root=tmp_path / "data", now=lambda: NOW,
    )


@pytest.mark.parametrize("filename", ["d2-video.mp4", "d2-audio.wav", "d2-notes.txt", "d2-notes.md"])
def test_confirm_creates_restart_readable_content_with_truthful_status_and_dedup(
    app: LocalApiApplication, tmp_path: Path, filename: str,
) -> None:
    path = tmp_path / filename
    text = path.suffix in {".txt", ".md"}
    if text:
        payload = b"D2-01 synthetic source evidence. No cloud processing.\n"
    else:
        command = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i"]
        command += ["color=c=blue:s=32x32:r=5:d=1"] if path.suffix == ".mp4" else ["sine=frequency=440:sample_rate=16000:duration=1"]
        subprocess.run([*command, str(path)], capture_output=True, check=True, timeout=20)
        payload = path.read_bytes()
    code, accepted = app.handle("POST", f"/api/v1/local/imports?filename={filename}", payload)
    assert code == 201
    imported = accepted["import"]
    content_id = imported["content_id"]
    expected = "READY" if text else "TRANSCRIPTION_UNAVAILABLE"
    assert imported == {
        "content_id": content_id, "filename": filename, "status": expected,
        "duplicate": False, "provider": "LOCAL", "source_id": "local-library",
    }
    # Reconstruct the normal read boundary from the same persisted files/database.
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    restarted = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=tmp_path / "data")
    _, listing = restarted.handle("GET", "/api/v1/videos")
    assert len(listing["videos"]) == 1
    item = listing["videos"][0]
    assert item["video_id"] == content_id
    assert item["title"] == item["filename"] == filename
    assert item["processing_status"] == expected
    _, detail = restarted.handle("GET", f"/api/v1/videos/{content_id}")
    assert detail["video"]["processing_status"] == expected
    assert detail["transcript"]["status"] == ("AVAILABLE" if text else "TRANSCRIPTION_UNAVAILABLE")
    assert detail["intelligence_result"]["status"] == "NOT_PROCESSED"
    _, sources = restarted.handle("GET", "/api/v1/sources")
    assert len(sources["sources"]) == 1
    assert sources["sources"][0]["provider"] == "LOCAL"
    assert not sources["sources"][0].get("tracking")
    code, repeated = restarted.handle("POST", f"/api/v1/local/imports?filename={filename}", payload)
    assert code == 200 and repeated["import"]["duplicate"] is True
    assert repeated["import"]["content_id"] == content_id
    assert len(repo.list_videos()) == 1
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM content_source_snapshots").fetchone()[0] == 1
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_invalid_video_returns_explicit_error_without_content(app: LocalApiApplication) -> None:
    with pytest.raises(ApiError) as error:
        app.handle("POST", "/api/v1/local/imports?filename=bad.mp4", b"not a video")
    assert error.value.code == "LOCAL_INVALID_MEDIA"
    assert app.handle("GET", "/api/v1/videos")[1]["videos"] == []


def test_processing_failure_preserves_imported_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from youtube_intel import local_content

    # Deterministic processing failure, distinct from the real-media tests above.
    monkeypatch.setattr(local_content, "probe_media", lambda *_: 1.0)
    class FailedTranscriber:
        def transcribe(self, snapshot: Path, *, duration_seconds: float) -> MediaTranscript:
            raise RuntimeError("synthetic executor failure")
    repo = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repo.initialize(now=NOW)
    provider = LocalContentProvider(repo, tmp_path / "data", now=lambda: NOW)
    provider.transcriber = FailedTranscriber()
    accepted = provider.import_bytes("d2-failed.mp4", b"synthetic isolated failure bytes")
    assert accepted.status == "TRANSCRIPTION_FAILED"
    assert repo.get_video(accepted.content_id) is not None
    app = LocalApiApplication(repo, ProductOrchestrationService(repo), data_root=tmp_path / "data")
    _, detail = app.handle("GET", f"/api/v1/videos/{accepted.content_id}")
    assert detail["video"]["title"] == "d2-failed.mp4"
    assert detail["video"]["processing_status"] == "TRANSCRIPTION_FAILED"
    assert detail["transcript"]["status"] == "TRANSCRIPTION_FAILED"
    assert detail["note"]["v2"]["status"] == "UNAVAILABLE"
