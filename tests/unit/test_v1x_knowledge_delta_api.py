"""Knowledge Delta stays a read-only local API with safe partial failure."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from youtube_intel import knowledge_delta
from youtube_intel.knowledge_delta import KnowledgeDeltaService
from youtube_intel.local_api import LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.state import SQLiteStateRepository, StateStoreError

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def test_api_works_without_deep_analysis_or_model(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    app = LocalApiApplication(
        repository, ProductOrchestrationService(repository), now=lambda: NOW
    )
    with patch(
        "socket.create_connection", side_effect=AssertionError("No network or model")
    ):
        status, body = app.handle("GET", "/api/v1/knowledge-delta")
    assert status == 200
    assert body == {
        "knowledge_delta": KnowledgeDeltaService(repository, now=lambda: NOW)
        .read()
        .as_dict()
    }
    assert set(body["knowledge_delta"]) == {  # type: ignore[arg-type]
        "window_start",
        "window_end",
        "timezone",
        "status",
        "categories",
        "detail_limit",
    }


def test_one_failed_source_is_explicit_partial_not_zero(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    app = LocalApiApplication(
        repository, ProductOrchestrationService(repository), now=lambda: NOW
    )
    with patch.object(
        knowledge_delta, "_TOPICS", "SELECT private_diagnostic FROM missing_table"
    ):
        status, body = app.handle("GET", "/api/v1/knowledge-delta")
    assert status == 200
    delta = body["knowledge_delta"]
    assert delta["status"] == "partial"  # type: ignore[index]
    unavailable = next(
        item for item in delta["categories"] if item["kind"] == "topic_updated"
    )  # type: ignore[index]
    assert unavailable == {
        "kind": "topic_updated",
        "status": "unavailable",
        "count": None,
        "items": [],
    }
    assert "private_diagnostic" not in str(body)
    assert "missing_table" not in str(body)


def test_unavailable_database_is_safe_not_empty(tmp_path: Path) -> None:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    with patch.object(
        repository, "_connect", side_effect=StateStoreError("PRIVATE path and token")
    ):
        result = KnowledgeDeltaService(repository, now=lambda: NOW).read().as_dict()
    assert result["status"] == "unavailable"
    assert all(category["count"] is None for category in result["categories"])  # type: ignore[union-attr]
    assert "PRIVATE" not in str(result)


def test_missing_database_read_does_not_create_a_database(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite3"
    repository = SQLiteStateRepository(database)
    assert not database.exists()
    result = KnowledgeDeltaService(repository, now=lambda: NOW).read().as_dict()
    assert result["status"] == "unavailable"
    assert not database.exists()
