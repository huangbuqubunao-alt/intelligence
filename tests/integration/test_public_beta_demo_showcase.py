"""Integration checks for Public Beta Apache-2.0 metadata and offline demo showcase."""

from __future__ import annotations

import http.client
import json
import socket
import threading
import tomllib
from pathlib import Path
from typing import cast

import pytest

from youtube_intel.demo_showcase import prepare_demo_showcase
from youtube_intel.local_api import LocalApiApplication, serve_loopback

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_apache2_license_notice_and_optional_mac_whisper_metadata() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text

    notice_text = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "Apache License, Version 2.0" in notice_text
    assert "No permission is granted" not in notice_text

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["license"] == {"file": "LICENSE"}

    base_deps = list(pyproject["project"]["dependencies"])
    assert not any("mlx-whisper" in dep for dep in base_deps)

    opt_deps = pyproject["project"]["optional-dependencies"]
    assert any("mlx-whisper" in dep for dep in opt_deps["mac-whisper"])


def test_demo_showcase_prepare_is_offline_and_populates_multi_source_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _deny_network(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("demo showcase preparation must be 100% offline")

    monkeypatch.setattr(socket, "create_connection", _deny_network)
    demo_root = tmp_path / "demo-root"

    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=demo_root, reset=True)
    app = runtime.fast_app

    sys_code, sys_body = app.handle("GET", "/api/v1/system")
    assert sys_code == 200
    assert sys_body["release_posture"] == "PUBLIC_BETA"
    assert sys_body["deep_analysis_tier"] == "EXPERIMENTAL"
    assert sys_body["runtime"] == {"mode": "PUBLIC_DEMO", "demo_data": True}

    vid_code, vid_body = app.handle("GET", "/api/v1/videos")
    assert vid_code == 200
    videos = cast(list[dict[str, object]], vid_body["videos"])
    assert len(videos) == 6
    providers = {str(v.get("provider")) for v in videos}
    assert providers == {"YOUTUBE", "BILIBILI", "LOCAL"}

    md_video = next(v for v in videos if v.get("provider") == "LOCAL")
    md_id = str(md_video["video_id"])
    det_code, det_body = app.handle("GET", f"/api/v1/videos/{md_id}")
    assert det_code == 200
    assert "[00:00]" not in str(det_body.get("obsidian_markdown") or "")

    short_video = next(v for v in videos if v.get("video_id") == "vidDemoSh05")
    short_brief = cast(dict[str, object], short_video["ai_brief"])
    assert short_brief["is_short_noise"] is True

    dash_code, dash_body = app.handle("GET", "/api/v1/dashboard")
    assert dash_code == 200
    assert dash_body.get("workspace_weekly_brief") is not None
    assert len(cast(list[object], dash_body["pinned_topics"])) >= 2

    res_code, res_body = app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert res_code == 200
    assert len(cast(list[object], res_body["sessions"])) == 2

    ask_code, ask_body = app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "为什么要用确定性状态机和可追溯证据引用？"}).encode("utf-8"),
    )
    assert ask_code == 200
    session = cast(dict[str, object], ask_body["session"])
    citations = cast(list[object], session["citations"])
    assert len(citations) >= 1
    assert "为什么要用确定性状态机和可追溯证据引用" in str(session["answer_zh"])

    # Re-opening without reset preserves interactive Q&A session state
    reopened = prepare_demo_showcase(REPO_ROOT, demo_root=demo_root, reset=False)
    _, reopened_res = reopened.fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert len(cast(list[object], reopened_res["sessions"])) == 3


def test_single_port_static_spa_server_serves_assets_and_enforces_api_guards(
    tmp_path: Path,
) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo", reset=True)
    static_dir = tmp_path / "dist"
    (static_dir / "assets").mkdir(parents=True)
    index_bytes = b"<!doctype html><html><script>1</script><body>YIA Demo</body></html>"
    asset_bytes = b"console.log('yia-asset');\n"
    (static_dir / "index.html").write_bytes(index_bytes)
    (static_dir / "assets" / "app.js").write_bytes(asset_bytes)
    (tmp_path / "outside.txt").write_bytes(b"SECRET_OUTSIDE_FILE")

    server = serve_loopback(
        cast(LocalApiApplication, runtime.fast_app),
        port=0,
        static_dir=static_dir,
    )
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)

        conn.request("GET", "/")
        r_root = conn.getresponse()
        body_root = r_root.read()
        assert r_root.status == 200
        assert r_root.getheader("Content-Type") == "text/html; charset=utf-8"
        assert r_root.getheader("X-Content-Type-Options") == "nosniff"
        csp_html = r_root.getheader("Content-Security-Policy") or ""
        assert "script-src 'self' 'unsafe-inline'" in csp_html
        assert body_root == index_bytes

        conn.request("GET", "/Content/vidDemoAgt1")
        r_spa = conn.getresponse()
        assert r_spa.status == 200
        assert r_spa.read() == index_bytes

        conn.request("GET", "/assets/app.js")
        r_js = conn.getresponse()
        assert r_js.status == 200
        assert r_js.getheader("Content-Type") == "application/javascript; charset=utf-8"
        assert "immutable" in (r_js.getheader("Cache-Control") or "")
        assert r_js.read() == asset_bytes

        conn.request("HEAD", "/assets/app.js")
        r_head = conn.getresponse()
        assert r_head.status == 200
        assert r_head.getheader("Content-Length") == str(len(asset_bytes))
        assert r_head.read() == b""

        conn.request("GET", "/../outside.txt")
        r_trav = conn.getresponse()
        trav_body = r_trav.read()
        assert r_trav.status == 404
        assert b"SECRET_OUTSIDE_FILE" not in trav_body

        conn.request("GET", "/api/v1/system")
        r_api = conn.getresponse()
        api_body = json.loads(r_api.read().decode("utf-8"))
        assert r_api.status == 200
        assert api_body["release_posture"] == "PUBLIC_BETA"
        assert r_api.getheader("Content-Security-Policy") == "default-src 'self'; connect-src 'self'"

        conn.request(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            body=b'{"question":"test"}',
            headers={"Content-Type": "application/json"},
        )
        r_guard = conn.getresponse()
        guard_body = json.loads(r_guard.read().decode("utf-8"))
        assert r_guard.status == 403
        assert guard_body["error"]["code"] == "ORIGIN_REJECTED"
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
