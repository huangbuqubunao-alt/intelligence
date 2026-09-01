import json
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.local_api import _LOCAL_ORIGIN, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository


def _app(tmp_path: Path) -> LocalApiApplication:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=datetime(2026, 9, 1, tzinfo=UTC))
    service = ProductOrchestrationService(
        repository, now=lambda: datetime(2026, 9, 1, tzinfo=UTC)
    )
    return LocalApiApplication(repository, service)


def test_safe_source_write_and_read_do_not_start_check(tmp_path: Path) -> None:
    app = _app(tmp_path)
    status, payload = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtu.be/abcdefghijk",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    assert status == 201
    assert payload["source"]["last_checked_at"] is None
    assert (
        app.handle("GET", "/api/v1/sources")[1]["sources"][0]["video_id"]
        == "abcdefghijk"
    )


def test_safe_provider_projection_has_no_secret_or_active_model(tmp_path: Path) -> None:
    status, payload = _app(tmp_path).handle("GET", "/api/v1/settings")
    assert status == 200
    assert payload["model_preference"]["active_production_default"] is None
    assert payload["providers"][1]["reason"] == "1/2; SCHEMA_INVALID"


def test_manual_check_is_explicitly_blocked_by_runtime_guard(tmp_path: Path) -> None:
    app = _app(tmp_path)
    _, created = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtube.com/channel/UC1234567890123456789012",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    status, checked = app.handle(
        "POST", f"/api/v1/sources/{created['source']['source_id']}/check"
    )
    assert status == 200
    assert checked["status"] == "BLOCKED"


def test_loopback_origin_rule_accepts_only_local_ui_origins() -> None:
    assert _LOCAL_ORIGIN.fullmatch("http://127.0.0.1:5173") is not None
    assert _LOCAL_ORIGIN.fullmatch("http://localhost:5173") is not None
    assert _LOCAL_ORIGIN.fullmatch("https://example.test") is None
