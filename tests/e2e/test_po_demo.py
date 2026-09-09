from __future__ import annotations

import socket
from pathlib import Path

import pytest

from youtube_intel.po_demo import demo_runtime_root, prepare_demo, reset_demo_runtime
from youtube_intel.scoring import AuthoritativeScoringReader


def test_demo_runtime_is_isolated_and_projects_current_product_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The PO demo seeds only its designated root and never needs a network."""

    monkeypatch.setattr(
        socket, "create_connection", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network"))
    )
    outside = tmp_path / "real-user-data.sqlite3"
    outside.write_text("must survive demo reset", encoding="utf-8")

    runtime = prepare_demo(tmp_path)

    assert runtime.root == demo_runtime_root(tmp_path)
    assert runtime.database == runtime.root / "state.sqlite3"
    assert isinstance(runtime.scoring_reader, AuthoritativeScoringReader)
    assert outside.read_text(encoding="utf-8") == "must survive demo reset"

    dashboard = runtime.application.handle("GET", "/api/v1/dashboard")[1]
    videos = runtime.application.handle("GET", "/api/v1/videos")[1]
    weekly = runtime.application.handle("GET", "/api/v1/weekly")[1]
    weekly_v1 = runtime.application.handle("GET", "/api/v1/weekly/v1")[1]
    automation = runtime.application.handle("GET", "/api/v1/automation")[1]
    activity = runtime.application.handle("GET", "/api/v1/activity")[1]
    system = runtime.application.handle("GET", "/api/v1/system")[1]
    golden = runtime.application.handle("GET", "/api/v1/videos/golden-ai-roadmap")[1]
    unverified = runtime.application.handle("GET", "/api/v1/videos/unverified-score")[1]
    source = runtime.application.handle("GET", "/api/v1/sources/source-ai")[1]

    assert dashboard["operations"]["source_count"] == 5
    assert set(dashboard) == {
        "intelligence",
        "pinned_topics",
        "weekly_v1",
        "needs_attention",
        "operations",
    }
    assert all(item["status"] != "AVAILABLE" or item["trusted"] for item in dashboard["intelligence"])
    available = next(item for item in dashboard["intelligence"] if item["status"] == "AVAILABLE")
    intelligence_id = available["intelligence_id"]
    assert available["trusted"] is True
    assert available["card"]["evidence_links"]
    assert weekly_v1["weekly_v1"]
    assert weekly_v1["weekly_v1"][0]["items"]
    assert weekly_v1["weekly_v1"][0]["items"][0]["markers"]
    assert weekly_v1["weekly_v1"][0]["items"][0]["markers"][0]["kind"] == "SUPERSEDED"

    saved_before = runtime.application.handle("GET", "/api/v1/saved-intelligence")[1]
    assert saved_before["saved"] == [
        {
            "intelligence_id": "po-demo-unavailable-saved",
            "saved_at": "2026-09-09T08:00:00Z",
            "intelligence": {
                "status": "UNAVAILABLE",
                "trusted": False,
                "code": "CURRENT_NOT_ACTIVE",
            },
        }
    ]
    save_status, saved_after = runtime.application.handle(
        "POST",
        "/api/v1/saved-intelligence/save",
        ('{"intelligence_id":"' + intelligence_id + '"}').encode(),
    )
    assert save_status == 200
    assert saved_after["saved"]["intelligence_id"] == intelligence_id
    saved_listing = runtime.application.handle("GET", "/api/v1/saved-intelligence")[1]
    assert {item["intelligence_id"] for item in saved_listing["saved"]} == {
        intelligence_id,
        "po-demo-unavailable-saved",
    }
    assert next(
        item for item in saved_listing["saved"] if item["intelligence_id"] == intelligence_id
    )["intelligence"]["trusted"] is True
    unsave_status, _ = runtime.application.handle(
        "POST",
        "/api/v1/saved-intelligence/unsave",
        ('{"intelligence_id":"' + intelligence_id + '"}').encode(),
    )
    assert unsave_status == 200
    assert runtime.application.handle("GET", "/api/v1/saved-intelligence")[1]["saved"] == saved_before["saved"]
    assert len(videos["videos"]) == 12
    assert len(weekly["weekly"]) == 2
    assert len(automation["schedules"]) == 4
    assert len(activity["runs"]) >= 4
    assert system["runtime"]["mode"] == "PO_REVIEW_DEMO"
    assert system["runtime"]["demo_data"] is True
    assert golden["transcript"]["status"] == "AVAILABLE"
    assert "decision log" in golden["transcript"]["text"]
    assert golden["scoring"]["status"] == "AVAILABLE"
    assert golden["scoring"]["trusted"] is True
    assert golden["note"]["v1"]["status"] == "UNAVAILABLE"
    assert golden["note"]["v2"]["status"] == "UNAVAILABLE"
    assert golden["video"]["deep_analysis"]["status"] == "BLOCKED"
    assert golden["history"]
    assert unverified["scoring"]["status"] == "NOT_AVAILABLE"
    assert "score" not in unverified["scoring"]
    assert source["recent_videos"]
    assert "policy" in source
    assert "source_runs" in source
    assert any(run["status"] == "AMBIGUOUS" for run in activity["runs"])
    assert {schedule["frequency"] for schedule in automation["schedules"]} >= {"MANUAL", "DAILY", "WEEKLY"}
    assert any(not schedule["enabled"] for schedule in automation["schedules"])
    assert weekly["weekly"][0]["version"] == "UNKNOWN"
    assert weekly["weekly"][0]["weekly_v2"]["status"] == "UNAVAILABLE"
    assert weekly["weekly"][0]["linkage"]["status"] == "UNAVAILABLE_IN_CURRENT_AUTHORITY"

    reopened = prepare_demo(tmp_path)
    assert reopened.application.handle("GET", "/api/v1/videos/golden-ai-roadmap")[1][
        "scoring"
    ] == golden["scoring"]

    reset_demo_runtime(tmp_path)
    assert not runtime.root.exists()
    assert outside.read_text(encoding="utf-8") == "must survive demo reset"


def test_demo_reset_refuses_a_symlinked_runtime_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = demo_runtime_root(tmp_path)
    root.parent.mkdir()
    root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="must not be a symlink"):
        reset_demo_runtime(tmp_path)

    assert outside.is_dir()
