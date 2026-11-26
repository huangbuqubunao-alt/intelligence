from __future__ import annotations

import contextlib
import json
import sqlite3
import subprocess
import threading
import time
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from youtube_intel import source_authority
from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.local_content import LocalContentProvider, MediaTranscript
from youtube_intel.offline_transcription import media_tool
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.state import TimedTranscriptCueWrite
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

NOW = datetime(2026, 11, 18, 1, 0, tzinfo=UTC)


class _MemorySecretStore:
    def __init__(self) -> None:
        self.secret: str | None = None

    def get(self) -> str | None:
        return self.secret

    def load(self) -> str | None:
        return self.secret

    def save(self, value: str) -> None:
        self.secret = value

    def delete(self) -> None:
        self.secret = None


class _DeterministicCompleter:
    def __call__(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        _ = (system_prompt, user_prompt, mode, max_tokens)
        return (
            {
                "headline_zh": "AI 大模型全栈工程师导论：从底层原理到企业级 Agent 架构全景拆解",
                "summary_zh": "系统梳理大模型演进路线、Prompt 工程、RAG 与智能体实战闭环。",
                "score": 9.3,
                "score_reason_zh": "完整的全栈大模型工程体系导学课，实操路线清晰。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "TUTORIAL",
                "topics_zh": ["大模型全栈", "Agent 架构"],
                "topic_cluster_zh": "AI Agent 工程架构",
                "core_points": [
                    {
                        "text_zh": "全栈大模型工程师需掌握评测驱动的 Agent 工具编排",
                        "cue_window_index": 0,
                    }
                ],
                "product_opportunities_zh": ["面向垂直业务团队的可验证私有知识库助手"],
                "business_opportunities_zh": ["企业内部 AI 工作流咨询与定制交付"],
                "filtered_noise_zh": ["开场设备调试"],
            },
            provider,
            model,
        )


class _SlowMediaTranscriber:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds
        self.started = threading.Event()
        self.allow_finish = threading.Event()
        if delay_seconds == 0.0:
            self.allow_finish.set()

    def transcribe(self, snapshot: Path, *, duration_seconds: float) -> MediaTranscript:
        assert snapshot.is_file()
        self.started.set()
        if self.delay_seconds > 0:
            self.allow_finish.wait(timeout=self.delay_seconds)
        end_first = max(400, min(1500, int(duration_seconds * 400)))
        end_second = max(end_first + 400, min(2800, int(duration_seconds * 850)))
        return MediaTranscript(
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=end_first,
                    text="大家好，欢迎来到 AI 大模型全栈工程师第一节导论课。",
                ),
                TimedTranscriptCueWrite(
                    start_ms=end_first,
                    end_ms=end_second,
                    text="本课程将带你从 Prompt Engineering 一路实战到生产级 Agent 系统。",
                ),
            ),
            language="zh",
            provenance='{"contract":"offline-timed-transcription-v1"}',
        )


def _create_sample_mp4(base_dir: Path, name: str = "1.简介 - AI 大模型全栈工程师_ev.mp4") -> Path:
    ffmpeg = media_tool("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg unavailable")
    mp4_path = base_dir.resolve() / name
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=3",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(mp4_path),
        ],
        check=True,
        capture_output=True,
    )
    return mp4_path


def _build_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    transcriber: _SlowMediaTranscriber,
) -> dict[str, Any]:
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_models", lambda *_a: {"models": []}
    )
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_runtime_version", lambda *_a: {}
    )
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe",
        lambda *_a: "MODEL_UNAVAILABLE",
    )

    repo_root = Path(__file__).resolve().parents[2]
    resolved_tmp = tmp_path.resolve()
    project_root = resolved_tmp / "owner"
    for folder in ("data", "logs", "templates", "vault"):
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    values = load_settings(repo_root / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    db_path = project_root / "state.sqlite3"

    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=db_path,
        credential_store=_MemorySecretStore(),
        bigmodel_credential_store=_MemorySecretStore(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        now=lambda: NOW,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=_MemorySecretStore(),
        llm_completer=_DeterministicCompleter(),
        media_transcriber=transcriber,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: NOW,
    )
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    return {
        "tmp": resolved_tmp,
        "project_root": project_root,
        "data_root": project_root / "data",
        "db_path": db_path,
        "repo": composition.repository,
        "fast_app": fast_app,
        "hub": hub,
    }


def test_fast_read_avoids_write_locks_and_rehash_after_local_video_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcriber = _SlowMediaTranscriber()
    env = _build_runtime(tmp_path, monkeypatch, transcriber=transcriber)
    fast_app: FastReadApiApplication = env["fast_app"]

    mp4_path = _create_sample_mp4(env["tmp"])
    imported = LocalContentProvider(
        env["repo"], env["data_root"], now=lambda: NOW
    ).import_file(mp4_path)

    # Opening #Content/<id> initializes LocalTranscriptionJobs via /transcription,
    # then warm read populates self._local_av_ids and memoized verified_source.
    st_tx_init, _ = fast_app.handle(
        "GET", f"/api/v1/videos/{imported.content_id}/transcription"
    )
    assert st_tx_init == HTTPStatus.OK
    status_v1, payload_v1 = fast_app.handle("GET", "/api/v1/videos")
    assert status_v1 == HTTPStatus.OK
    assert len(payload_v1["videos"]) == 1

    # Spy on hash_managed to prove subsequent GET reads do NOT re-hash the MP4 snapshot!
    real_hash_managed = source_authority.hash_managed
    hash_calls: list[str] = []

    def counting_hash_managed(root: Path, relative: str, *, maximum: int) -> tuple[int, str]:
        hash_calls.append(relative)
        return real_hash_managed(root, relative, maximum=maximum)

    monkeypatch.setattr(source_authority, "hash_managed", counting_hash_managed)

    # Hold an exclusive write transaction (BEGIN IMMEDIATE) on state.sqlite3 while
    # issuing concurrent GET /api/v1/videos and GET /api/v1/saved-intelligence!
    writer = sqlite3.connect(env["db_path"], isolation_level=None, timeout=5.0)
    try:
        writer.execute("BEGIN IMMEDIATE")
        st_videos, _ = fast_app.handle("GET", "/api/v1/videos")
        st_saved, _ = fast_app.handle("GET", "/api/v1/saved-intelligence")
        st_detail, _ = fast_app.handle("GET", f"/api/v1/videos/{imported.content_id}")
        assert st_videos == HTTPStatus.OK
        assert st_saved == HTTPStatus.OK
        assert st_detail == HTTPStatus.OK
    finally:
        writer.rollback()
        writer.close()

    assert hash_calls == [], (
        f"Expected 0 redundant MP4 SHA-256 hashes during hot GET reads, got {len(hash_calls)}"
    )


def test_async_local_video_transcribe_job_status_and_workspace_capabilities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcriber = _SlowMediaTranscriber(delay_seconds=5.0)
    env = _build_runtime(tmp_path, monkeypatch, transcriber=transcriber)
    fast_app: FastReadApiApplication = env["fast_app"]

    # Touch sidecar DB via settings update (matches real live workspace where hub.sqlite3 exists)
    st_cfg, _ = fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps({"active_mode": "local_ollama", "ollama_model": "qwen3.5:9b"}).encode(),
    )
    assert st_cfg == HTTPStatus.OK

    mp4_path = _create_sample_mp4(env["tmp"])
    imported = LocalContentProvider(
        env["repo"], env["data_root"], now=lambda: NOW
    ).import_file(mp4_path)

    # 1) Detail endpoint exposes workspace_ai_capabilities when sidecar DB exists
    st_det0, det0 = fast_app.handle("GET", f"/api/v1/videos/{imported.content_id}")
    assert st_det0 == HTTPStatus.OK
    caps0 = det0.get("workspace_ai_capabilities")
    assert isinstance(caps0, dict)
    assert caps0["ready"] is True
    assert caps0["transcriber_ready"] is True
    assert caps0["transcribe_job"] is None

    # Dedicated status endpoint also reports transcriber_ready before any job starts
    st_poll0, poll0 = fast_app.handle(
        "GET", f"/api/v1/workspace-ai/videos/{imported.content_id}/transcribe-status"
    )
    assert st_poll0 == HTTPStatus.OK
    assert poll0["transcriber_ready"] is True
    assert poll0["job"] is None

    # 2) Trigger async transcription so multi-hour lectures never block/timeout HTTP proxy
    st_start, start_body = fast_app.handle(
        "POST",
        f"/api/v1/workspace-ai/videos/{imported.content_id}/transcribe",
        json.dumps({"async": True}).encode(),
    )
    assert st_start == HTTPStatus.OK
    assert start_body["transcription_status"] == "RUNNING"
    assert transcriber.started.wait(timeout=2.0)

    # Polling while running reflects live RUNNING stage
    st_poll1, poll1 = fast_app.handle(
        "GET", f"/api/v1/workspace-ai/videos/{imported.content_id}/transcribe-status"
    )
    assert st_poll1 == HTTPStatus.OK
    assert poll1["job"]["status"] == "RUNNING"

    # Let transcription finish and verify transition to READY + persisted Chinese brief
    transcriber.allow_finish.set()
    deadline = time.monotonic() + 5.0
    final_poll: dict[str, Any] = {}
    while time.monotonic() < deadline:
        _, final_poll = fast_app.handle(
            "GET",
            f"/api/v1/workspace-ai/videos/{imported.content_id}/transcribe-status",
        )
        job_info = final_poll.get("job")
        if isinstance(job_info, dict) and job_info.get("status") == "READY":
            break
        time.sleep(0.05)

    assert final_poll["job"]["status"] == "READY"

    st_det_done, det_done = fast_app.handle(
        "GET", f"/api/v1/videos/{imported.content_id}"
    )
    assert st_det_done == HTTPStatus.OK
    assert det_done["transcript"]["status"] == "AVAILABLE"
    assert det_done["video"]["ai_brief"]["recommendation_tier"] == "MUST_WATCH"


def test_with_repository_connect_closes_file_descriptors_without_gc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import gc
    import os

    transcriber = _SlowMediaTranscriber()
    env = _build_runtime(tmp_path, monkeypatch, transcriber=transcriber)
    repo = env["repo"]

    def count_open_fds() -> int:
        return len(os.listdir("/dev/fd"))

    gc.collect()
    before_fds = count_open_fds()
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        leaked_refs = []
        for _ in range(120):
            with repo._connect() as conn:
                conn.execute("SELECT 1").fetchone()
                leaked_refs.append(conn)
            with repo._connect(read_only=True) as ro_conn:
                ro_conn.execute("SELECT 1").fetchone()
                leaked_refs.append(ro_conn)
        after_fds = count_open_fds()
    finally:
        if gc_was_enabled:
            gc.enable()

    fd_delta = after_fds - before_fds
    assert fd_delta <= 8, (
        f"`with repo._connect()` leaked {fd_delta} open file descriptors across 240 calls "
        "(would exhaust macOS 256-FD daemon soft limit and trigger OperationalError across all routes)"
    )


def test_long_duration_video_never_classified_as_short_noise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcriber = _SlowMediaTranscriber()
    env = _build_runtime(tmp_path, monkeypatch, transcriber=transcriber)
    hub: WorkspaceIntelligenceHub = env["hub"]
    repo = env["repo"]

    class _ShortMisclassifyingCompleter:
        def __call__(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            mode: str,
            provider: str,
            model: str,
            max_tokens: int = 1800,
        ) -> tuple[dict[str, Any], str, str]:
            _ = (system_prompt, user_prompt, mode, max_tokens)
            return (
                {
                    "headline_zh": "课程导学概述",
                    "summary_zh": "课程介绍视频，小模型误输出 SHORTS_PROMO 桶标签。",
                    "score": 2.5,
                    "score_reason_zh": "测试误标恢复。",
                    "recommendation_tier": "SKIP_NOISE",
                    "content_bucket": "SHORTS_PROMO",
                    "topics_zh": ["大模型全栈"],
                    "topic_cluster_zh": "AI Agent 工程架构",
                    "core_points": [],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )

    hub._llm_completer = _ShortMisclassifyingCompleter()

    from youtube_intel.domain import (
        Availability,
        LiveStatus,
        PipelineStatus,
        VideoMetadata,
    )
    from youtube_intel.source_authority import sha256, write_managed
    from youtube_intel.state import (
        ArtifactKind,
        ArtifactWrite,
        RetentionClass,
        StorageRoot,
        TimedTranscriptWrite,
    )

    video_id = "longVid001"
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UCtestlong00000000000001",
            channel_name="AI Engineering",
            title="1.简介 - AI 大模型全栈工程师_ev.mp4",
            description="Long form course introduction video over 6 minutes.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=NOW,
            duration_seconds=360,
            default_language="zh",
            available_languages=("zh",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=NOW,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=NOW,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=NOW,
    )
    cues = (
        TimedTranscriptCueWrite(
            start_ms=0,
            end_ms=4000,
            text="这是一节超过六分钟的大模型全栈工程师完整导学课。",
        ),
    )
    canonical_text = "\n".join(c.text for c in cues).encode("utf-8")
    rel = f"transcripts/canonical/{video_id}.txt"
    write_managed(env["data_root"], rel, canonical_text)
    art_id = f"canonical:{video_id}"
    repo.upsert_artifact(
        ArtifactWrite(
            artifact_id=art_id,
            artifact_key=art_id,
            video_id=video_id,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=rel,
            content_hash=sha256(canonical_text),
            provider="youtube",
            model=None,
            producer_version="v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW,
    )
    repo.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=video_id,
            canonical_artifact_id=art_id,
            cues=cues,
        ),
        now=NOW,
    )

    distilled = hub.distill_video(video_id)
    brief = distilled["ai_brief"]
    assert isinstance(brief, dict)
    assert brief["content_bucket"] != "SHORTS_PROMO"
    assert brief["is_short_noise"] is False

    video_row = repo.get_video(video_id)
    assert video_row is not None
    meta_distilled = hub._distill_metadata_only_youtube_video(
        video_row, duration_seconds=360
    )
    meta_brief = meta_distilled["ai_brief"]
    assert isinstance(meta_brief, dict)
    assert meta_brief["content_bucket"] != "SHORTS_PROMO"
    assert meta_brief["is_short_noise"] is False

    # Pre-existing persisted >180s rows wrongly tagged as SHORTS_PROMO / is_short_noise=1
    # must normalize cleanly on read without requiring hub.sqlite3 mutations.
    hub_conn = sqlite3.connect(hub.db_path)
    try:
        hub_conn.execute(
            """
            INSERT OR REPLACE INTO video_ai_briefs (
                video_id, headline_zh, summary_zh, score, score_reason_zh,
                recommendation_tier, content_bucket, is_short_noise, duration_seconds,
                topics_json, topic_cluster_zh, core_points_json,
                product_opportunities_json, business_opportunities_json, filtered_noise_json,
                intelligence_id, revision_id, provider, model, obsidian_markdown,
                updated_at, source_basis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacyLong8236",
                "历史遗留长视频误标样本",
                "旧模型在 8236 秒本地长视频上误持久化为短片。",
                2.5,
                "历史测试样本",
                "SKIP_NOISE",
                "SHORTS_PROMO",
                1,
                8236,
                "[]",
                "AI Agent 工程架构",
                "[]",
                "[]",
                "[]",
                "[]",
                None,
                None,
                "ollama",
                "qwen3.5:9b",
                "",
                NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "TRANSCRIPT",
            ),
        )
        hub_conn.commit()
    finally:
        hub_conn.close()

    read_back = hub.get_video_brief("legacyLong8236")
    assert read_back is not None
    assert read_back["is_short_noise"] is False
    assert read_back["content_bucket"] == "DEEP_DIVE"


def test_local_media_endpoint_supports_http_range_and_rejects_non_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import urllib.error
    import urllib.request

    from youtube_intel.local_api import LocalApiApplication, serve_loopback

    env = _build_runtime(tmp_path, monkeypatch, transcriber=_SlowMediaTranscriber())
    fast_app: FastReadApiApplication = env["fast_app"]
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)

    mp4_path = _create_sample_mp4(env["tmp"])
    imported = provider.import_file(mp4_path)
    mp4_bytes = mp4_path.read_bytes()

    md_path = env["tmp"] / "notes.md"
    md_path.write_text("# Hello\nJust markdown text.\n", encoding="utf-8")
    text_imported = provider.import_file(md_path)

    server = serve_loopback(fast_app, port=0)  # type: ignore[arg-type]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(
            f"{base_url}/api/v1/videos/{imported.content_id}/media"
        ) as full_resp:
            assert full_resp.status == 200
            assert full_resp.headers.get("Content-Type") == "video/mp4"
            assert full_resp.headers.get("Accept-Ranges") == "bytes"
            assert full_resp.read() == mp4_bytes

        range_req = urllib.request.Request(
            f"{base_url}/api/v1/videos/{imported.content_id}/media",
            headers={"Range": "bytes=4-19"},
        )
        with urllib.request.urlopen(range_req) as partial_resp:
            assert partial_resp.status == 206
            assert partial_resp.headers.get("Content-Range") == f"bytes 4-19/{len(mp4_bytes)}"
            assert partial_resp.read() == mp4_bytes[4:20]

        with pytest.raises(urllib.error.HTTPError) as not_found_exc:
            urllib.request.urlopen(
                f"{base_url}/api/v1/videos/{text_imported.content_id}/media"
            )
        assert not_found_exc.value.code == 404
        _ = LocalApiApplication
    finally:
        server.shutdown()
        server.server_close()


def test_local_media_host_cross_site_range_head_and_managed_root_security(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import hashlib
    import sqlite3
    from http.client import HTTPConnection

    from youtube_intel.local_api import serve_loopback

    env = _build_runtime(tmp_path, monkeypatch, transcriber=_SlowMediaTranscriber())
    fast_app: FastReadApiApplication = env["fast_app"]
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)

    mp4_path = _create_sample_mp4(env["tmp"])
    imported = provider.import_file(mp4_path)
    mp4_bytes = mp4_path.read_bytes()

    server = serve_loopback(fast_app, port=0)  # type: ignore[arg-type]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_port
        media_route = f"/api/v1/videos/{imported.content_id}/media"

        def raw_req(
            method: str, path: str, headers: dict[str, str] | None = None
        ) -> tuple[int, dict[str, str], bytes]:
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                conn.request(method, path, headers=headers or {})
                resp = conn.getresponse()
                body = resp.read()
                resp_headers = {k.lower(): v for k, v in resp.getheaders()}
                return resp.status, resp_headers, body
            finally:
                conn.close()

        # P1-01: Untrusted Host & cross-site rejections across GET/HEAD API reads
        for bad_route in (
            media_route,
            "/api/v1/videos",
            "/api/v1/workspace-ai/obsidian-bundle.zip?scope=all",
        ):
            st, hdrs, body = raw_req("GET", bad_route, {"Host": "evil.example"})
            assert st == 403
            assert hdrs.get("cross-origin-resource-policy") == "same-origin"
            assert json.loads(body)["error"]["code"] == "HOST_REJECTED"

            st_cross, _, body_cross = raw_req(
                "GET", bad_route, {"Sec-Fetch-Site": "cross-site"}
            )
            assert st_cross == 403
            assert json.loads(body_cross)["error"]["code"] == "ORIGIN_REJECTED"

        st_origin, _, _ = raw_req(
            "GET", media_route, {"Origin": "https://evil.example"}
        )
        assert st_origin == 403

        # Allowed loopback host + same-origin headers + CORP header
        st_ok, hdrs_ok, body_ok = raw_req(
            "GET",
            media_route,
            {"Host": f"localhost:{port}", "Sec-Fetch-Site": "same-origin"},
        )
        assert st_ok == 200
        assert hdrs_ok.get("cross-origin-resource-policy") == "same-origin"
        assert body_ok == mp4_bytes

        # P1-06 & P2-R02 (RFC 9110 §14.2): HEAD ignores Range (200 full metadata) and writes 0 wire bytes
        st_head, hdrs_head, body_head = raw_req("HEAD", media_route)
        assert st_head == 200
        assert body_head == b""
        assert int(hdrs_head["content-length"]) == len(mp4_bytes)
        assert hdrs_head.get("accept-ranges") == "bytes"
        assert hdrs_head.get("cross-origin-resource-policy") == "same-origin"

        st_head_404, _, body_head_404 = raw_req("HEAD", "/api/v1/videos/missing-vid/media")
        assert st_head_404 == 404
        assert body_head_404 == b""

        for head_range in ("bytes=0-3", "bytes=+4-19"):
            st_hr, hdrs_hr, body_hr = raw_req("HEAD", media_route, {"Range": head_range})
            assert st_hr == 200
            assert int(hdrs_hr["content-length"]) == len(mp4_bytes)
            assert body_hr == b""

        # Raw TCP socket proof: HTTP client does NOT silently drop server-written HEAD body
        import socket as _sock

        for wire_req in (
            f"HEAD {media_route} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n",
            f"HEAD {media_route} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nRange: bytes=0-3\r\nConnection: close\r\n\r\n",
            f"HEAD {media_route} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nRange: bytes=+4-19\r\nConnection: close\r\n\r\n",
            f"HEAD /api/v1/videos/missing-vid/media HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n",
        ):
            with _sock.create_connection(("127.0.0.1", port), timeout=5) as tcp:
                tcp.sendall(wire_req.encode("ascii"))
                chunks: list[bytes] = []
                while True:
                    chunk = tcp.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                raw_wire = b"".join(chunks)
            head_part, sep, wire_body = raw_wire.partition(b"\r\n\r\n")
            assert sep == b"\r\n\r\n"
            assert wire_body == b"", f"Server wrote non-empty wire body for HEAD: {wire_body!r}"
            assert b" 200 OK\r\n" in head_part or b" 404 Not Found\r\n" in head_part

        # P2-01 & P2-R01: Strict bounded RFC 9110 Range handling (including >4300-digit numbers)
        st_suf, hdrs_suf, body_suf = raw_req("GET", media_route, {"Range": "bytes=-16"})
        assert st_suf == 206
        assert hdrs_suf.get("content-range") == f"bytes {len(mp4_bytes) - 16}-{len(mp4_bytes) - 1}/{len(mp4_bytes)}"
        assert body_suf == mp4_bytes[-16:]

        st_open, hdrs_open, body_open = raw_req("GET", media_route, {"Range": "bytes=10-"})
        assert st_open == 206
        assert hdrs_open.get("content-range") == f"bytes 10-{len(mp4_bytes) - 1}/{len(mp4_bytes)}"
        assert body_open == mp4_bytes[10:]

        st_clamp, hdrs_clamp, body_clamp = raw_req(
            "GET", media_route, {"Range": "bytes=10-999999"}
        )
        assert st_clamp == 206
        assert hdrs_clamp.get("content-range") == f"bytes 10-{len(mp4_bytes) - 1}/{len(mp4_bytes)}"
        assert body_clamp == mp4_bytes[10:]

        huge_5000 = "9" * 5000
        st_h_end, hdrs_h_end, body_h_end = raw_req(
            "GET", media_route, {"Range": f"bytes=10-{huge_5000}"}
        )
        assert st_h_end == 206
        assert hdrs_h_end.get("content-range") == f"bytes 10-{len(mp4_bytes) - 1}/{len(mp4_bytes)}"
        assert body_h_end == mp4_bytes[10:]

        st_h_suf, hdrs_h_suf, body_h_suf = raw_req(
            "GET", media_route, {"Range": f"bytes=-{huge_5000}"}
        )
        assert st_h_suf == 206
        assert hdrs_h_suf.get("content-range") == f"bytes 0-{len(mp4_bytes) - 1}/{len(mp4_bytes)}"
        assert body_h_suf == mp4_bytes

        for bad_range in (
            "bytes=+4-19",
            "bytes=\u00b2-\u00b3",
            "bytes= 0 - 5",
            "bytes=-",
            "bytes=-0",
            "bytes=10-5",
            "bytes=0-5,10-15",
            "bytes=999999-1000005",
            f"bytes={huge_5000}-",
            "items=0-5",
        ):
            st_bad, hdrs_bad, body_bad = raw_req("GET", media_route, {"Range": bad_range})
            assert st_bad == 416, f"expected 416 for {bad_range!r}, got {st_bad}"
            assert hdrs_bad.get("content-range") == f"bytes */{len(mp4_bytes)}"
            assert hdrs_bad.get("cross-origin-resource-policy") == "same-origin"
            assert body_bad == b""

        # P1-02: Repeated seeks hit immutable-stat hash cache without re-hashing unchanged bytes
        hash_calls = 0
        real_sha256 = hashlib.sha256

        def counting_sha256(*args: object, **kwargs: object) -> object:
            nonlocal hash_calls
            hash_calls += 1
            return real_sha256(*args, **kwargs)  # type: ignore[arg-type]

        with monkeypatch.context() as mp:
            mp.setattr(hashlib, "sha256", counting_sha256)
            for offset in (0, 8, 16):
                st_r, _, _ = raw_req("GET", media_route, {"Range": f"bytes={offset}-{offset + 3}"})
                assert st_r == 206
            assert hash_calls == 0

        # Locate artifact row to test disk tamper, empty file, symlink escape, and bad storage_root
        db_file = getattr(env["repo"], "_database_path", None)
        assert isinstance(db_file, Path)
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                """
                SELECT s.snapshot_artifact_id, a.storage_root, a.relative_path
                FROM content_source_snapshots s
                JOIN artifacts a ON a.artifact_id = s.snapshot_artifact_id
                WHERE s.content_id = ?
                """,
                (imported.content_id,),
            ).fetchone()
            assert row is not None
            artifact_id = str(row["snapshot_artifact_id"])
            orig_storage_root = str(row["storage_root"])
            rel_path = str(row["relative_path"])
            src_root = getattr(env["repo"], "_source_data_root", env["data_root"])
            base_root = src_root if orig_storage_root == "SOURCE_DATA" else env["data_root"]
            target_file = base_root / rel_path

            # Tamper same size different bytes -> 409 corrupted (never falsely served)
            target_file.write_bytes(b"\xff" * len(mp4_bytes))
            st_tamper, _, body_tamper = raw_req("GET", media_route)
            assert st_tamper == 409
            assert json.loads(body_tamper)["error"]["code"] == "LOCAL_MEDIA_CORRUPTED"

            # Replace with 0-byte empty file -> 409 pre-header error (not dropped connection!)
            target_file.write_bytes(b"")
            st_empty, _, body_empty = raw_req("GET", media_route)
            assert st_empty == 409
            assert json.loads(body_empty)["error"]["code"] == "LOCAL_MEDIA_CORRUPTED"

            # Untrusted storage_root in DB -> 409 fail-closed
            target_file.write_bytes(mp4_bytes)
            conn.execute(
                "UPDATE artifacts SET storage_root = 'VAULT' WHERE artifact_id = ?",
                (artifact_id,),
            )
            conn.commit()
            st_root, _, body_root = raw_req("GET", media_route)
            assert st_root == 409
            assert json.loads(body_root)["error"]["code"] == "LOCAL_MEDIA_UNAVAILABLE"

            # Restore valid storage_root, then replace target with symlink escape -> 409
            conn.execute(
                "UPDATE artifacts SET storage_root = ? WHERE artifact_id = ?",
                (orig_storage_root, artifact_id),
            )
            conn.commit()
            outside = env["tmp"] / "outside_secret.mp4"
            outside.write_bytes(mp4_bytes)
            target_file.unlink()
            target_file.symlink_to(outside)
            with caplog.at_level("WARNING"):
                st_sym, _, body_sym = raw_req("GET", media_route)
            assert st_sym == 409
            assert json.loads(body_sym)["error"]["code"] == "LOCAL_MEDIA_UNAVAILABLE"
            # Verify warning log stays sanitized without leaking full host path
            assert str(env["tmp"]) not in caplog.text

            # Ancestor directory symlink escape -> 409 fail-closed via O_NOFOLLOW walk
            target_file.unlink()
            target_file.write_bytes(mp4_bytes)
            real_sub = target_file.parent
            escaped_dir = env["tmp"] / "escaped_parent_dir"
            escaped_dir.mkdir(exist_ok=True)
            (escaped_dir / target_file.name).write_bytes(mp4_bytes)
            backup_sub = env["tmp"] / "moved_real_sub"
            real_sub.rename(backup_sub)
            real_sub.symlink_to(escaped_dir)
            try:
                st_anc, _, body_anc = raw_req("GET", media_route)
                assert st_anc == 409
                assert json.loads(body_anc)["error"]["code"] == "LOCAL_MEDIA_UNAVAILABLE"
            finally:
                real_sub.unlink()
                backup_sub.rename(real_sub)

            # Oversize file (>2 GiB sparse simulation via MAX_MEDIA_BYTES monkeypatch) -> 413 pre-header JSON
            target_file.unlink()
            target_file.write_bytes(mp4_bytes)
            with monkeypatch.context() as mp_size:
                mp_size.setattr("youtube_intel.source_authority.MAX_MEDIA_BYTES", 8)
                mp_size.setattr("youtube_intel.fast_read_api.MAX_MEDIA_BYTES", 8)
                mp_size.setattr("youtube_intel.local_api.MAX_MEDIA_BYTES", 8)
                st_big, _, body_big = raw_req("GET", media_route)
                assert st_big == 413
                assert json.loads(body_big)["error"]["code"] == "LOCAL_FILE_TOO_LARGE"

            # Post-header interruption simulation: mutate file mid-stream -> connection aborted cleanly with sanitized warning
            caplog.clear()
            import youtube_intel.local_api as local_api_mod
            from youtube_intel.source_authority import ManagedMediaError

            with monkeypatch.context() as mp_mid:
                mp_mid.setattr(local_api_mod, "IO_CHUNK_BYTES", 4)
                original_open = local_api_mod.open_managed

                @contextlib.contextmanager
                def _mutating_midstream_open(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    with original_open(*args, **kwargs) as stream:  # type: ignore[arg-type]
                        yield stream
                        raise ManagedMediaError(409, "LOCAL_MEDIA_CHANGED", "Simulated mid-stream change")

                mp_mid.setattr(local_api_mod, "open_managed", _mutating_midstream_open)
                with caplog.at_level("WARNING"):
                    st_mid, _, _ = raw_req("GET", media_route)
                    # Wait briefly for handler thread exit post-body close before reading caplog
                    deadline = time.monotonic() + 1.0
                    while "aborted after headers" not in caplog.text and time.monotonic() < deadline:
                        time.sleep(0.02)
                assert st_mid == 200
                assert "aborted after headers" in caplog.text
                assert str(env["tmp"]) not in caplog.text
        finally:
            conn.close()
    finally:
        server.shutdown()
        server.server_close()
