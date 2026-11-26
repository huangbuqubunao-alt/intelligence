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

from youtube_intel import cli
from youtube_intel.demo_showcase import prepare_demo_showcase
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.operations import ExitCode

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
    channels = {str(v.get("channel_name") or "") for v in videos}
    assert "OpenAI Developers" not in channels
    assert "Atlas Agent Lab (Demo)" in channels
    assert "Local-First Foundry (Demo)" in channels

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

    intel_code, intel_body = app.handle("GET", "/api/v1/intelligence")
    assert intel_code == 200
    intel_items = cast(list[dict[str, object]], intel_body.get("items") or intel_body.get("intelligence") or [])
    bili_intel = next(
        (
            it
            for it in intel_items
            if isinstance(it.get("card"), dict)
            and cast(dict[str, object], it["card"]).get("video_id") == "bilibili-BV1DemoBili99"
        ),
        None,
    )
    if bili_intel is not None:
        bili_card = cast(dict[str, object], bili_intel["card"])
        assert bili_card["source_display_name"] == "极客架构演示室（Demo）"

    delta_code, delta_body = app.handle("GET", "/api/v1/knowledge-delta")
    assert delta_code == 200
    delta = cast(dict[str, object], delta_body["knowledge_delta"])
    assert delta["status"] == "available"
    cats = cast(list[dict[str, object]], delta["categories"])
    assert sum(int(c.get("count") or 0) for c in cats) >= 1

    res_code, res_body = app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert res_code == 200
    seeded_sessions = cast(list[dict[str, object]], res_body["sessions"])
    assert len(seeded_sessions) == 2
    assert all("离线合成样例回放" in str(s.get("answer_zh") or "") for s in seeded_sessions)
    assert all(s.get("provider") == "demo-replay" for s in seeded_sessions)

    ask_code, ask_body = app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "为什么要用确定性状态机和可追溯证据引用？"}).encode("utf-8"),
    )
    assert ask_code == 200
    session = cast(dict[str, object], ask_body["session"])
    citations = cast(list[object], session["citations"])
    assert len(citations) >= 1
    assert "【离线合成样例回放】" in str(session["answer_zh"])
    assert "为什么要用确定性状态机和可追溯证据引用" in str(session["answer_zh"])
    assert session["provider"] == "demo-replay"

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



def test_demo_showcase_refuses_unknown_nonempty_directory_and_preserves_files(
    tmp_path: Path,
) -> None:
    user_dir = tmp_path / "user-existing-dir"
    user_dir.mkdir()
    user_note = user_dir / "notes.txt"
    user_note.write_text("important personal research notes", encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty"):
        prepare_demo_showcase(REPO_ROOT, demo_root=user_dir, reset=False)
    assert user_note.read_text(encoding="utf-8") == "important personal research notes"

    with pytest.raises(ValueError, match="demo showcase marker"):
        prepare_demo_showcase(REPO_ROOT, demo_root=user_dir, reset=True)
    assert user_note.read_text(encoding="utf-8") == "important personal research notes"

    exit_code = cli.main(["demo", "--demo-root", str(user_dir)])
    assert exit_code == ExitCode.USAGE_OR_CONFIGURATION
    assert user_note.read_text(encoding="utf-8") == "important personal research notes"


def test_demo_showcase_corrupted_workspace_preserves_user_files_on_refusal_and_reset(
    tmp_path: Path,
) -> None:
    demo_dir = tmp_path / "seeded-demo-dir"
    prepare_demo_showcase(REPO_ROOT, demo_root=demo_dir, reset=True)

    keep_file = demo_dir / "keep-me.txt"
    keep_file.write_text("keep-this-file-safe", encoding="utf-8")
    (demo_dir / "state.sqlite3").unlink()

    with pytest.raises(ValueError, match="incomplete or corrupted"):
        prepare_demo_showcase(REPO_ROOT, demo_root=demo_dir, reset=False)
    assert keep_file.read_text(encoding="utf-8") == "keep-this-file-safe"

    rebuilt = prepare_demo_showcase(REPO_ROOT, demo_root=demo_dir, reset=True)
    assert rebuilt.seeded_videos == 6
    assert keep_file.read_text(encoding="utf-8") == "keep-this-file-safe"


def test_demo_showcase_refuses_unanswerable_off_topic_question_without_fabricated_citations(
    tmp_path: Path,
) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo-refuse", reset=True)
    for off_topic in (
        "量子引力场在火星大气层的实测数值是多少？",
        "What is the boiling point of liquid methane on Titan?",
    ):
        status, body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": off_topic}).encode("utf-8"),
        )
        assert status == 200
        session = cast(dict[str, object], body["session"])
        assert session["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
        assert session["refused"] is True
        assert session["citations"] == []
        assert len(cast(list[object], session["related_excerpts"])) >= 1
        assert session["provider"] == "demo-replay"


def test_demo_showcase_answers_bilingual_local_first_marginal_cost_query_without_repetition(
    tmp_path: Path,
) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo-iter1", reset=True)

    # Seeded Q&A sessions must not repeat identical takeaway sentences.
    res_code, res_body = runtime.fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert res_code == 200
    for seeded in cast(list[dict[str, object]], res_body["sessions"]):
        takeaways = [str(x) for x in cast(list[object], seeded.get("key_takeaways_zh") or [])]
        normalized = [t.split("[", 1)[0].strip() for t in takeaways]
        assert len(normalized) == len(set(normalized))

    # In-library bilingual query that previously triggered a false refusal.
    status, body = runtime.fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "本地优先 AI 工具如何兼顾零边际成本和可信引用？"}).encode("utf-8"),
    )
    assert status == 200
    session = cast(dict[str, object], body["session"])
    assert session["refused"] is False
    assert session["provider"] == "demo-replay"
    citations = cast(list[dict[str, object]], session["citations"])
    assert len(citations) >= 2
    distinct_videos = {str(c.get("video_id") or "") for c in citations}
    assert len(distinct_videos) >= 2
    takeaways = [str(x) for x in cast(list[object], session["key_takeaways_zh"])]
    normalized_t = [t.split("[", 1)[0].strip() for t in takeaways]
    assert len(normalized_t) == len(set(normalized_t))


def test_demo_showcase_topic_detail_provides_cross_source_synthesis_and_perspectives(
    tmp_path: Path,
) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo-iter4", reset=True)
    list_code, list_body = runtime.fast_app.handle("GET", "/api/v1/topics")
    assert list_code == 200
    topics = cast(list[dict[str, object]], list_body["topics"])
    target = next(
        t
        for t in topics
        if int(cast(dict[str, object], t.get("ai_evolution") or {}).get("video_count") or 0) >= 2
    )
    det_code, det_body = runtime.fast_app.handle(
        "GET", f"/api/v1/topics/{target['topic_id']}"
    )
    assert det_code == 200
    topic = cast(dict[str, object], det_body["topic"])
    evo = cast(dict[str, object], topic["ai_evolution"])
    synthesis = str(evo.get("synthesis_zh") or "")
    assert "独立来源" in synthesis or "持续演进" in synthesis
    perspectives = cast(list[dict[str, object]], evo.get("source_perspectives") or [])
    assert len(perspectives) >= 2
    assert len({str(p.get("channel_name") or "") for p in perspectives}) >= 2
