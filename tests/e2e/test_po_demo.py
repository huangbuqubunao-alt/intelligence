from __future__ import annotations

import os
import shlex
import signal
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copy2

import pytest

from youtube_intel.po_demo import demo_runtime_root, prepare_demo, reset_demo_runtime
from youtube_intel.scoring import AuthoritativeScoringReader


class _UnrelatedReadyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"unrelated service")

    def log_message(self, format: str, *args: object) -> None:
        del format, args


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
    golden = runtime.application.handle("GET", "/api/v1/videos/aircAruvnKk")[1]
    unverified = runtime.application.handle("GET", "/api/v1/videos/unverified-score")[1]
    source = runtime.application.handle("GET", "/api/v1/sources/source-ai")[1]
    preferences = runtime.application.handle("GET", "/api/v1/settings/preferences")[1]
    resource_usage = runtime.application.handle("GET", "/api/v1/settings/resource-usage")[1]

    assert any(
        schedule["frequency"] == "DAILY" and schedule["local_time"] == "08:30"
        for schedule in source["schedules"]
    )

    assert dashboard["operations"]["source_count"] == 5
    assert set(dashboard) == {
        "intelligence",
        "pinned_topics",
        "weekly_v1",
        "needs_attention",
        "operations",
    }
    assert all(item["status"] != "AVAILABLE" or item["trusted"] for item in dashboard["intelligence"])
    real_data_cards = [
        item for item in dashboard["intelligence"] if item["status"] == "AVAILABLE"
    ]
    assert {item["card"]["video_id"] for item in real_data_cards} == {
        "aircAruvnKk",
        "7gtc1DW2Tgo",
        "wjZofJX0v4M",
    }
    assert {item["claim_kind"] for item in real_data_cards} == {
        "EVIDENCE_BACKED_STATEMENT",
        "OPINION",
    }
    assert all(item["card"]["source_display_name"] for item in real_data_cards)
    assert all(item["card"]["video_title"] for item in real_data_cards)
    assert all(
        item["card"]["evidence_links"][0]["original_excerpt"]
        for item in real_data_cards
    )
    assert dashboard["needs_attention"] == [
        {
            "run_id": "source-run:5709dd545ce77763b946df78fc31e287147bc27a0649159110d1c9aefc787b5c",
            "source_id": "source-startup",
            "trigger": "MANUAL_CHECK_NOW",
            "trigger_reference": "po-demo-attention",
            "priority": "P0",
            "state": "NEEDS_ATTENTION",
            "attention_reason": "MODEL_UNAVAILABLE",
            "automation_run_id": None,
            "manual_command_id": "po-demo-attention",
            "manual_analyze_override_id": None,
            "created_at": "2026-09-01T08:00:00Z",
            "updated_at": "2026-09-01T08:00:00Z",
        }
    ]
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
    assert len(videos["videos"]) == 13
    assert len(weekly["weekly"]) == 2
    assert len(automation["schedules"]) == 4
    assert len(activity["runs"]) >= 4
    assert system["runtime"]["mode"] == "PO_REVIEW_DEMO"
    assert system["runtime"]["demo_data"] is True
    assert golden["transcript"]["status"] == "AVAILABLE"
    assert "governed qualification outcome" in golden["transcript"]["text"]
    assert "No qualification transcript content is included" in golden["transcript"]["text"]
    assert golden["scoring"]["status"] == "AVAILABLE"
    assert golden["scoring"]["trusted"] is True
    assert golden["note"]["v1"]["status"] == "UNAVAILABLE"
    assert golden["note"]["v2"]["status"] == "UNAVAILABLE"
    assert golden["video"]["deep_analysis"]["status"] == "BLOCKED"
    assert golden["history"]
    assert unverified["scoring"]["status"] == "NOT_AVAILABLE"
    assert "score" not in unverified["scoring"]
    assert source["recent_videos"]
    assert source["source"]["display_name"] is None
    assert source["source"]["friendly_name"] == "3Blue1Brown"
    assert source["source"]["canonical_url"] == (
        "https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw"
    )
    skipped = next(video for video in source["recent_videos"] if video["video_id"] == "unverified-score")
    assert skipped["filter"]["outcome"] == "NOT_RELEVANT"
    assert skipped["filter"]["reason"] == "IGNORE_RULE_MATCH"
    assert "policy" in source
    assert "source_runs" in source
    assert {(item["provenance"], item["horizon"]) for item in preferences["history"]} == {
        ("EXPLICIT", "LONG_TERM"),
        ("DERIVED", "RECENT"),
        ("TEMPORARY", "TEMPORARY_FOCUS"),
    }
    assert any(item["expires_at"] for item in preferences["history"])
    assert resource_usage["usage"]
    assert all("credential" not in item and "secret" not in item for item in resource_usage["usage"])
    assert resource_usage["usage"][0]["input_tokens"] is None
    assert resource_usage["usage"][0]["cost_microunits"] is None
    assert any(run["status"] == "AMBIGUOUS" for run in activity["runs"])
    assert {schedule["frequency"] for schedule in automation["schedules"]} >= {"MANUAL", "DAILY", "WEEKLY"}
    assert any(not schedule["enabled"] for schedule in automation["schedules"])
    assert weekly["weekly"][0]["version"] == "UNKNOWN"
    assert weekly["weekly"][0]["weekly_v2"]["status"] == "UNAVAILABLE"
    assert weekly["weekly"][0]["linkage"]["status"] == "UNAVAILABLE_IN_CURRENT_AUTHORITY"

    settings = runtime.application.handle("GET", "/api/v1/settings")[1]
    local = settings["providers"][0]
    assert local == {
        "provider": "Local",
        "model": "qwen3:8b",
        "configured": False,
        "credential_status": "NOT_REQUIRED",
        "adapter_available": True,
        "qualification_status": "QUALIFIED",
        "authorized": True,
        "production_eligible": True,
        "scope": "V1_VIDEO_DISTILLATION_ONLY",
        "reason": "Qualified local Ollama model is available for V1 Video Distillation only.",
    }
    nim = settings["providers"][1]
    assert nim["provider"] == "NVIDIA NIM"
    assert nim["production_eligible"] is False

    reopened = prepare_demo(tmp_path)
    assert reopened.application.handle("GET", "/api/v1/videos/aircAruvnKk")[1][
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


def test_demo_launcher_rejects_occupied_ports_before_starting_children(
    tmp_path: Path,
) -> None:
    """Unrelated loopback services must never satisfy launcher readiness."""

    project = tmp_path / "project"
    script_dir = project / "scripts"
    python_path = project / ".venv" / "bin" / "python"
    vite_path = project / "frontend" / "node_modules" / ".bin" / "vite"
    script_dir.mkdir(parents=True)
    python_path.parent.mkdir(parents=True)
    vite_path.parent.mkdir(parents=True)
    copy2(Path(__file__).parents[2] / "scripts" / "start_po_demo.sh", script_dir)
    python_path.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f"if [ \"$1\" = \"-\" ]; then exec {shlex.quote(sys.executable)} \"$@\"; fi\n"
        "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"youtube_intel.po_demo\" ]; then\n"
        "  case \"$3\" in\n"
        "    prepare) exit 0 ;;\n"
        "    serve) sleep 30; exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        "exit 2\n",
        encoding="utf-8",
    )
    vite_path.write_text("#!/bin/sh\nsleep 30\n", encoding="utf-8")
    python_path.chmod(0o700)
    vite_path.chmod(0o700)

    servers = [
        ThreadingHTTPServer(("127.0.0.1", 0), _UnrelatedReadyHandler)
        for _ in range(2)
    ]
    threads = [threading.Thread(target=server.serve_forever) for server in servers]
    for thread in threads:
        thread.start()
    environment = os.environ.copy()
    environment.update(
        {
            "YIA_PO_DEMO_API_PORT": str(servers[0].server_port),
            "YIA_PO_DEMO_FRONTEND_PORT": str(servers[1].server_port),
        }
    )
    try:
        result = subprocess.run(
            [str(script_dir / "start_po_demo.sh")],
            cwd=project,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    finally:
        for pid_file in (
            project / ".var" / "po-demo" / "state" / "api.pid",
            project / ".var" / "po-demo" / "state" / "frontend.pid",
        ):
            if pid_file.is_file():
                os.kill(int(pid_file.read_text(encoding="utf-8")), signal.SIGTERM)
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join()

    assert result.returncode != 0
    assert "already in use" in (result.stdout + result.stderr)
    assert not (project / ".var" / "po-demo" / "state").exists()
