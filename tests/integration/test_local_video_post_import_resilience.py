from __future__ import annotations

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

