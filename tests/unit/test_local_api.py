import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from youtube_intel.local_api import _LOCAL_ORIGIN, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.state import SQLiteStateRepository


def _app(tmp_path: Path) -> LocalApiApplication:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=datetime(2026, 9, 1, tzinfo=UTC))
    service = ProductOrchestrationService(
        repository, now=lambda: datetime(2026, 9, 1, tzinfo=UTC)
    )
    return LocalApiApplication(
        repository,
        service,
        now=lambda: datetime(2026, 9, 1, tzinfo=UTC),
    )


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


def test_schedule_time_and_weekday_are_persisted_and_projected_for_future_only(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    _, created = app.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtu.be/abcdefghijk",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode(),
    )
    source_id = created["source"]["source_id"]
    status, daily = app.handle(
        "POST",
        "/api/v1/automation",
        json.dumps(
            {
                "target_type": "SOURCE_CHECK",
                "target_id": source_id,
                "frequency": "DAILY",
                "weekday": None,
                "local_time": "08:30",
                "enabled": True,
            }
        ).encode(),
    )
    assert status == 201
    assert daily["schedule"]["next_run"] == "2026-09-01T00:30:00Z"
    assert daily["schedule"]["timezone"] == "Asia/Shanghai"
    status, weekly = app.handle(
        "POST",
        "/api/v1/automation",
        json.dumps(
            {
                "schedule_id": daily["schedule"]["schedule_id"],
                "target_type": "SOURCE_CHECK",
                "target_id": source_id,
                "frequency": "WEEKLY",
                "weekday": 6,
                "local_time": "20:00",
                "enabled": True,
            }
        ).encode(),
    )
    assert status == 201
    assert weekly["schedule"]["next_run"] == "2026-09-06T12:00:00Z"
    assert app.handle("GET", "/api/v1/activity")[1]["runs"] == []


def test_loopback_origin_rule_accepts_only_local_ui_origins() -> None:
    assert _LOCAL_ORIGIN.fullmatch("http://127.0.0.1:5173") is not None
    assert _LOCAL_ORIGIN.fullmatch("http://localhost:5173") is not None
    assert _LOCAL_ORIGIN.fullmatch("https://example.test") is None


def test_verified_scoring_projection_only_exposes_safe_verified_fields(
    tmp_path: Path,
) -> None:
    class Reader:
        def read(self, video_id: str) -> object:
            assert video_id == "abcdefghijk"
            return SimpleNamespace(
                scoring_outcome=SimpleNamespace(
                    result=SimpleNamespace(
                        score=8.5,
                        reason="Clear product evidence.",
                        topics=("product", "strategy"),
                        provider="local",
                        model="fixture-model",
                        prompt_version="v1",
                    ),
                    decision=SimpleNamespace(final_should_summarize=True),
                    call=SimpleNamespace(finished_at=datetime(2026, 9, 1, tzinfo=UTC)),
                ),
                scoring_success_provenance="VERIFIED_LINEAGE",
            )

    app = _app(tmp_path)
    app._scoring_reader = cast(AuthoritativeScoringReader, Reader())
    projection = app._scoring_projection("abcdefghijk")
    assert projection == {
        "status": "AVAILABLE",
        "score": 8.5,
        "reason": "Clear product evidence.",
        "topics": ["product", "strategy"],
        "should_summarize": True,
        "trusted": True,
        "completed_at": "2026-09-01T00:00:00Z",
        "provenance": {
            "provider": "local",
            "model": "fixture-model",
            "prompt_version": "v1",
            "success_provenance": "VERIFIED_LINEAGE",
        },
    }
    assert "request_hash" not in projection


def test_reader_rejection_fails_closed_without_unverified_content(
    tmp_path: Path,
) -> None:
    class RejectingReader:
        def read(self, video_id: str) -> object:
            raise ValueError("forged raw result")

    app = _app(tmp_path)
    app._scoring_reader = cast(AuthoritativeScoringReader, RejectingReader())
    projection = app._scoring_projection("abcdefghijk")
    assert projection["status"] == "NOT_AVAILABLE"
    assert "forged" not in str(projection)
