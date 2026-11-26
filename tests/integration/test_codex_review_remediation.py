"""End-to-end regression suite covering all Codex review findings (P1-01..P1-14, P2-01..P2-07)."""

from __future__ import annotations

import copy
import email.message
import hashlib
import io
import json
import socket
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.demo_showcase import prepare_demo_showcase
from youtube_intel.domain import Availability, LiveStatus, PipelineStatus, VideoMetadata
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.fast_read_api import FastReadApiApplication, _data_root_token
from youtube_intel.local_api import MAX_WORKSPACE_AI_BACKUP_BYTES, ApiError
from youtube_intel.local_content import LocalContentProvider
from youtube_intel.offline_transcription import media_tool
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_authority import sha256, write_managed
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
)
from youtube_intel.workspace_intelligence_hub import (
    MAX_BACKUP_EXPORT_JSON_BYTES,
    MAX_BACKUP_VISUAL_RAW_BYTES,
    SUGGESTED_RESEARCH_QUESTIONS,
    WorkspaceIntelligenceHub,
    _infer_ollama_model_vision_by_name,
)
from youtube_intel.workspace_launcher import (
    WorkspacePreflight,
    collect_workspace_preflight,
    format_startup_banner,
    prepare_local_workspace,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 23, 16, 0, tzinfo=UTC)
MINIMAL_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


class _MemorySecret:
    def __init__(self, initial: str | None = None) -> None:
        self.secret = initial

    def get(self) -> str | None:
        return self.secret

    def load(self) -> str | None:
        return self.secret

    def save(self, value: str) -> None:
        self.secret = value

    def delete(self) -> None:
        self.secret = None


class _StubCompleter:
    def __init__(self, fn: Any = None) -> None:
        self.fn = fn
        self.calls = 0

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
        self.calls += 1
        if self.fn is not None:
            return self.fn(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                mode=mode,
                provider=provider,
                model=model,
                max_tokens=max_tokens,
            )
        return (
            {
                "headline_zh": "默认合成摘要标题",
                "summary_zh": "基于验证来源的结构化摘要。",
                "score": 8.6,
                "score_reason_zh": "信息密度高。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["架构"],
                "topic_cluster_zh": "工程实践",
                "core_points": [{"text_zh": "默认核心要点", "cue_window_index": 0}],
                "product_opportunities_zh": [],
                "business_opportunities_zh": [],
                "filtered_noise_zh": [],
            },
            provider,
            model,
        )


def _build_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    name: str = "owner",
    completer: Any = None,
    vision_completer: Any = None,
    ollama_models: tuple[str, ...] = ("gemma3:4b", "qwen3.5:9b"),
    http_opener: Any = None,
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

    resolved_tmp = tmp_path.resolve()
    project_root = resolved_tmp / name
    for folder in ("data", "logs", "templates", "vault"):
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    values = load_settings(REPO_ROOT / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    db_path = project_root / "state.sqlite3"
    byok_store = _MemorySecret()

    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=db_path,
        credential_store=_MemorySecret(),
        bigmodel_credential_store=_MemorySecret(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
        now=lambda: NOW,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=byok_store,
        llm_completer=completer or _StubCompleter(),
        vision_completer=vision_completer,
        installed_ollama_probe=lambda _url: (True, ollama_models),
        http_opener=http_opener,
        now=lambda: NOW,
    )
    hub.ensure_ready()
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    return {
        "tmp": resolved_tmp,
        "project_root": project_root,
        "data_root": project_root / "data",
        "db_path": db_path,
        "repo": composition.repository,
        "byok_store": byok_store,
        "hub": hub,
        "raw_app": composition.application,
        "fast_app": fast_app,
    }


def _seed_video_metadata_only(
    env: dict[str, Any],
    video_id: str,
    *,
    title: str,
    channel_name: str = "Synthesis Channel",
    updated_at: datetime = NOW,
) -> None:
    repo = env["repo"]
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC_REMED_111111111111111",
            channel_name=channel_name,
            title=title,
            description="Synthetic remediation test video",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=updated_at,
            duration_seconds=360,
            default_language="zh",
            available_languages=("zh",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=updated_at,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=updated_at,
    )


def _seed_video_with_cues(
    env: dict[str, Any],
    video_id: str,
    *,
    title: str,
    cues: tuple[tuple[int, int, str], ...],
    channel_name: str = "Synthesis Channel",
    updated_offset_min: int = 0,
) -> None:
    repo = env["repo"]
    data_root = env["data_root"]
    published = NOW - timedelta(hours=2) + timedelta(minutes=updated_offset_min)
    _seed_video_metadata_only(
        env,
        video_id,
        title=title,
        channel_name=channel_name,
        updated_at=published,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=published,
    )
    rel = f"transcripts/canonical/{video_id}.txt"
    raw = "\n".join(text for _s, _e, text in cues).encode("utf-8")
    write_managed(data_root, rel, raw)
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
            content_hash=sha256(raw),
            provider="youtube",
            model=None,
            producer_version="v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=published,
    )
    cue_objs = tuple(
        TimedTranscriptCueWrite(start_ms=s, end_ms=e, text=text)
        for s, e, text in cues
    )
    repo.create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id=video_id, canonical_artifact_id=art_id, cues=cue_objs
        ),
        now=published,
    )
    ExtractiveSummaryService(repo, data_root).create(video_id, now=published)


def _create_tiny_mp4(base_dir: Path, name: str = "remed.mp4") -> Path:
    ffmpeg = media_tool("ffmpeg")
    assert ffmpeg is not None
    mp4_path = base_dir.resolve() / name
    filter_complex = (
        "[1:v]drawbox=x=20:y=20:w=200:h=60:color=white:t=fill[v0];"
        "[2:v]scale=320:180[v1];"
        "[3:v]scale=320:180[v2];"
        "[v0][v1][v2]concat=n=3:v=1:a=0,format=yuv420p[vout]"
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=4.5",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x180:d=1.5:r=10",
            "-f",
            "lavfi",
            "-i",
            "rgbtestsrc=s=320x180:d=1.5:r=10",
            "-f",
            "lavfi",
            "-i",
            "smptebars=s=320x180:d=1.5:r=10",
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "0:a",
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


def test_p1_01_mixed_ungrounded_claims_are_stripped_and_pure_ungrounded_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            if "only_ungrounded" in user_prompt:
                return (
                    {
                        "answer_status": "GROUNDED",
                        "answerable": True,
                        "answer_zh": "外部传闻称该方案零成本落地[E88]。",
                        "key_takeaways_zh": ["外部传闻增长百倍[E99]"],
                        "action_items_zh": ["无根据建议[E88]"],
                        "citations": [{"ref": "E88", "why_relevant_zh": "伪造引用"}],
                    },
                    provider,
                    model,
                )
            return (
                {
                    "answer_status": "GROUNDED",
                    "answerable": True,
                    "answer_zh": "核心方案采用本地优先双库隔离架构[E1]。另外库存已翻三倍[E88]。",
                    "key_takeaways_zh": [
                        "核心方案采用本地优先双库隔离[E1]",
                        "未核验传闻销售额暴涨十倍[E99]",
                    ],
                    "action_items_zh": [
                        "复核双库隔离逻辑[E1]",
                        "核实传闻数字[E88]",
                    ],
                    "citations": [
                        {"ref": "E1", "why_relevant_zh": "原文明确提及双库隔离"},
                        {"ref": "E88", "why_relevant_zh": "未签发编号"},
                    ],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    fast_app: FastReadApiApplication = env["fast_app"]

    _seed_video_with_cues(
        env,
        "vidP101",
        title="双库隔离架构实录",
        cues=((0, 8000, "核心方案采用本地优先双库隔离架构来保证数据完整。"),),
    )

    mixed_res = hub.ask_research_question({"question": "请问核心方案架构及库存情况？"})
    mixed = mixed_res["session"]
    assert isinstance(mixed, dict)
    assert mixed["answer_status"] == "GROUNDED"
    assert "本地优先双库隔离" in str(mixed["answer_zh"])
    assert "[E1]" in str(mixed["answer_zh"])
    for marker in ("库存已翻三倍", "[E88]", "[E99]", "销售额暴涨十倍", "核实传闻数字"):
        assert marker not in str(mixed["answer_zh"])
        assert marker not in " ".join(mixed["key_takeaways_zh"])
        assert marker not in " ".join(mixed["action_items_zh"])
        assert marker not in str(mixed["obsidian_markdown"])

    hist_code, hist_body = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert hist_code == HTTPStatus.OK
    saved = next(s for s in hist_body["sessions"] if s["session_id"] == mixed["session_id"])
    assert "库存已翻三倍" not in saved["answer_zh"]
    assert "[E88]" not in " ".join(saved["action_items_zh"])

    refused_res = hub.ask_research_question({"question": "only_ungrounded 零成本落地依据是什么？"})
    refused = refused_res["session"]
    assert isinstance(refused, dict)
    assert refused["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert refused["refused"] is True
    assert refused["citations"] == []


def test_p1_02_text_note_distill_binds_exact_segment_and_preserves_null_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "LOCAL_TEXT_DISTILL_SCHEMA" in system_prompt:
            return (
                {
                    "headline_zh": "仓储盘点实时记录",
                    "summary_zh": "笔记第二行明确指出当前库存只剩七件。",
                    "score": 8.4,
                    "score_reason_zh": "含明确盘点数据。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["库存"],
                    "topic_cluster_zh": "运营盘点",
                    "core_points": [
                        {
                            "text_zh": "盘点显示核心 SKU 库存只剩七件",
                            "section_index": 0,
                            "evidence_quote": "库存只剩七件",
                        }
                    ],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_completer))
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)
    note_text = "\n\n".join(
        [
            "周一会议",
            "库存只剩七件",
            "周二巡检记录无异常",
            "周三补充打包耗材",
            "周四供应商确认到货周期",
            "周五整理财务凭证",
            "周六盘点货架标签",
            "周日归档本周流水",
            "下周计划核对退货",
        ]
    )
    imp = provider.import_bytes("inventory_log.txt", note_text.encode("utf-8"))
    cid = imp.content_id
    hub: WorkspaceIntelligenceHub = env["hub"]
    hub.distill_video(cid)
    brief = hub.get_video_brief(cid)
    assert brief is not None
    pts = brief["core_points"]
    assert len(pts) == 1
    pt = pts[0]
    assert pt["locator_type"] == "TEXT_RANGE"
    assert pt["start_ms"] is None
    assert pt["end_ms"] is None
    assert pt["start_seconds"] is None
    assert pt["end_seconds"] is None
    assert "库存只剩七件" in str(pt["excerpt"])
    assert "周一会议" not in str(pt["excerpt"])

    ev_id = pt["evidence_ids"][0]
    ev_code, ev_body = env["fast_app"].handle(
        "GET", f"/api/v1/videos/{cid}/evidence?evidence_id={ev_id}"
    )
    assert ev_code == HTTPStatus.OK
    matched_ev = next(e for e in ev_body["evidence"] if e["evidence_id"] == ev_id)
    assert "库存只剩七件" in matched_ev["original_excerpt"]
    assert matched_ev["locator_type"] == "TEXT_RANGE"
    assert matched_ev["start_ms"] is None
    assert matched_ev["end_ms"] is None


def test_p1_03_restored_sidecar_reverification_enforces_current_core_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answer_status": "GROUNDED",
                    "answerable": True,
                    "answer_zh": "笔记记录零信任凭证必须放行前核验[E1]。",
                    "key_takeaways_zh": ["零信任凭证必须核验[E1]"],
                    "action_items_zh": [],
                    "citations": [{"ref": "E1", "why_relevant_zh": "原话佐证"}],
                },
                provider,
                model,
            )
        return (
            {
                "headline_zh": "零信任核验笔记",
                "summary_zh": "凭证放行前必须在主库复核。",
                "score": 8.8,
                "score_reason_zh": "核心安全策略。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["安全"],
                "topic_cluster_zh": "安全边界",
                "core_points": [
                    {
                        "text_zh": "凭证放行前必须在主库复核",
                        "section_index": 0,
                        "evidence_quote": "零信任凭证必须放行前在当前主库重新核验。",
                    }
                ],
                "product_opportunities_zh": [],
                "business_opportunities_zh": [],
                "filtered_noise_zh": [],
            },
            provider,
            model,
        )

    env_src = _build_env(tmp_path, monkeypatch, name="ws_src", completer=_StubCompleter(_completer))
    note = "零信任凭证必须放行前在当前主库重新核验。"
    imp = LocalContentProvider(env_src["repo"], env_src["data_root"], now=lambda: NOW).import_bytes(
        "trust.md", note.encode("utf-8")
    )
    vid = imp.content_id
    env_src["hub"].distill_video(vid)
    env_src["hub"].ask_research_question({"question": "零信任凭证如何处理？", "video_ids": [vid]})
    snapshot = env_src["hub"].export_backup_snapshot()

    legacy_snapshot = json.loads(json.dumps(snapshot))
    legacy_scope = json.loads(str(legacy_snapshot["research_qa_sessions"][0]["scope_json"]))
    legacy_scope.pop("answer_status", None)
    legacy_snapshot["research_qa_sessions"][0]["scope_json"] = json.dumps(legacy_scope)

    # (a) Restore into empty workspace missing source note -> NEEDS_REVERIFICATION
    env_empty = _build_env(tmp_path, monkeypatch, name="ws_empty")
    env_empty["hub"].restore_backup_snapshot(legacy_snapshot)
    sessions_empty = env_empty["hub"].list_research_sessions()["sessions"]
    assert sessions_empty[0]["answer_status"] == "NEEDS_REVERIFICATION"
    assert all(not c.get("verified") for c in sessions_empty[0]["citations"])
    brief_empty = env_empty["hub"].get_video_brief(vid)
    assert brief_empty is not None
    assert brief_empty["core_points"][0]["evidence_verified"] is False
    assert brief_empty["core_points"][0]["evidence_ids"] == []

    # (b) Restore into workspace where same video_id has mutated text
    env_mut = _build_env(tmp_path, monkeypatch, name="ws_mut")
    _seed_video_with_cues(
        env_mut,
        vid,
        title="已被篡改的新视频",
        cues=((0, 5000, "完全无关的被替换原文。"),),
    )
    env_mut["hub"].restore_backup_snapshot(snapshot)
    sessions_mut = env_mut["hub"].list_research_sessions()["sessions"]
    assert sessions_mut[0]["answer_status"] == "NEEDS_REVERIFICATION"
    assert all(not c.get("verified") for c in sessions_mut[0]["citations"])
    brief_mut = env_mut["hub"].get_video_brief(vid)
    assert brief_mut is not None
    assert brief_mut["core_points"][0]["evidence_verified"] is False

    # (c) Restore into original intact workspace -> re-verifies as GROUNDED
    env_src["hub"].restore_backup_snapshot(snapshot)
    sessions_ok = env_src["hub"].list_research_sessions()["sessions"]
    assert sessions_ok[0]["answer_status"] == "GROUNDED"
    assert all(bool(c.get("verified")) for c in sessions_ok[0]["citations"])


def test_p1_04_demo_showcase_refuses_mixed_premise_question(tmp_path: Path) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo_remed", reset=True)
    for mixed_trap in (
        "Ollama 在火星大气层的实测温度是多少？",
        "Ollama 本地模型的价格是多少？",
        "Ollama本地模型价格是多少？",
        "Obsidian 双链的市值是多少？",
        "基于当前内容库，Ollama 本地模型价格是多少？",
    ):
        res_code, res_body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": mixed_trap}).encode("utf-8"),
        )
        assert res_code == HTTPStatus.OK
        session = res_body["session"]
        assert session["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE", mixed_trap
        assert session["refused"] is True
        assert session["citations"] == []

    for valid_q in (
        "为什么要用确定性状态机和可追溯证据引用？",
        *SUGGESTED_RESEARCH_QUESTIONS,
    ):
        ok_code, ok_body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": valid_q}).encode("utf-8"),
        )
        assert ok_code == HTTPStatus.OK
        assert ok_body["session"]["answer_status"] == "GROUNDED", valid_q
        assert len(ok_body["session"]["citations"]) >= 1


def test_p1_05_cjk_full_library_qa_hits_note9_paragraph121(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            assert "旋涡实验记录" in user_prompt
            return (
                {
                    "answer_status": "GROUNDED",
                    "answerable": True,
                    "answer_zh": "第9份笔记记录明天将开始旋涡实验记录[E1]。",
                    "key_takeaways_zh": ["明天开始旋涡实验记录[E1]"],
                    "action_items_zh": [],
                    "citations": [{"ref": "E1", "why_relevant_zh": "命中第121段原文"}],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_completer))
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)
    note9_id = ""
    for i in range(1, 10):
        paras = [f"第{i}份样本第{p}段常规日志条目占位描述。" for p in range(1, 125)]
        if i == 9:
            paras[120] = "明天将开始旋涡实验记录"
        content = "\n\n".join(paras)
        imp = provider.import_bytes(f"note_{i:02d}.md", content.encode("utf-8"))
        if i == 9:
            note9_id = imp.content_id

    hub: WorkspaceIntelligenceHub = env["hub"]
    full_res = hub.ask_research_question({"question": "旋涡"})["session"]
    scoped_res = hub.ask_research_question({"question": "旋涡", "video_ids": [note9_id]})["session"]
    assert full_res["answer_status"] == "GROUNDED"
    assert scoped_res["answer_status"] == "GROUNDED"
    assert full_res["citations"][0]["video_id"] == note9_id
    assert "旋涡实验记录" in full_res["citations"][0]["excerpt"]


def test_p1_06_evidence_endpoint_loads_tail_segment_and_reports_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    lines_31 = "\n\n".join(
        f"Segment number {idx + 1:02d} content line for tail lookup."
        for idx in range(31)
    )
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "tail31.txt", lines_31.encode("utf-8")
    )
    cid = imp.content_id

    fast_app: FastReadApiApplication = env["fast_app"]
    c_def, b_def = fast_app.handle("GET", f"/api/v1/videos/{cid}/evidence")
    assert c_def == HTTPStatus.OK
    assert len(b_def["evidence"]) == 21

    with env["repo"]._connect(read_only=True) as conn:
        rows = conn.execute(
            "SELECT evidence_id FROM evidence WHERE video_id = ? ORDER BY rowid ASC",
            (cid,),
        ).fetchall()
    tail_eid = str(rows[-1][0])
    assert tail_eid not in {e["evidence_id"] for e in b_def["evidence"]}

    c_tail, b_tail = fast_app.handle(
        "GET", f"/api/v1/videos/{cid}/evidence?evidence_id={tail_eid}"
    )
    assert c_tail == HTTPStatus.OK
    assert b_tail["target_evidence_status"] == "FOUND"
    assert any(
        e["evidence_id"] == tail_eid and "Segment number 31" in e["original_excerpt"]
        for e in b_tail["evidence"]
    )

    c_stale, b_stale = fast_app.handle(
        "GET", f"/api/v1/videos/{cid}/evidence?evidence_id=ev-stale-999"
    )
    assert c_stale == HTTPStatus.OK
    assert b_stale["target_evidence_status"] == "MISSING_OR_STALE"


def test_p1_07_byok_text_and_vision_dispatch_block_http_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests_seen: list[str] = []

    class _Mock302Response(io.BytesIO):
        def __init__(self, url: str, headers: email.message.Message) -> None:
            super().__init__(b"redirect")
            self.url = url
            self.status = 302
            self.code = 302
            self.msg = "Found"
            self.reason = "Found"
            self.headers = headers

        def info(self) -> email.message.Message:
            return self.headers

        def geturl(self) -> str:
            return self.url

    env = _build_env(tmp_path, monkeypatch)
    hub: WorkspaceIntelligenceHub = env["hub"]
    assert hub._http_opener is None

    # Prove N8/N9: even if third-party code patches stdlib urllib.request.urlopen,
    # production cloud dispatch never bypasses _default_no_redirect_opener.
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_k: pytest.fail("Production dispatch must not call urllib.request.urlopen"),
    )
    https_handlers = [
        h
        for h in hub._default_no_redirect_opener.handlers
        if isinstance(h, urllib.request.HTTPSHandler)
    ]
    assert https_handlers

    def _fake_https_open(req: urllib.request.Request) -> _Mock302Response:
        requests_seen.append(req.full_url)
        headers = email.message.Message()
        headers["Location"] = "https://attacker.invalid/steal-key"
        return _Mock302Response(req.full_url, headers)

    monkeypatch.setattr(https_handlers[0], "https_open", _fake_https_open)

    _seed_video_with_cues(env, "vidByokRedir", title="Redirect Check", cues=((0, 3000, "Test content"),))
    hub.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_provider": "openai_compatible",
            "cloud_base_url": "https://api.openai.com/v1",
            "cloud_model": "gpt-4o-mini",
            "cloud_daily_call_limit": 5,
            "cloud_api_key": "fake_key_value",
        }
    )

    hub._llm_completer = None
    with pytest.raises(ApiError) as text_err:
        hub.distill_video("vidByokRedir")
    assert text_err.value.code == "CLOUD_REDIRECT_BLOCKED"

    img_file = env["tmp"] / "frame.jpg"
    img_file.write_bytes(MINIMAL_JPEG)
    hub._vision_completer = None
    with pytest.raises(ApiError) as vis_err:
        hub._complete_vision_json(
            system_prompt="sys",
            user_prompt="usr",
            image_paths=[img_file],
            max_tokens=300,
            allow_cloud=True,
        )
    assert vis_err.value.code == "CLOUD_REDIRECT_BLOCKED"
    assert len(requests_seen) == 2
    assert all("attacker.invalid" not in u for u in requests_seen)
    settings = hub.get_settings()
    assert int(settings["cloud_calls_used_today"]) == 2


def test_p1_08_large_backup_restore_capacity_above_32k_and_2mib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _long_qa_completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answerable": True,
                    "answer_zh": ("依据核心证据定位分析：" + ("长篇幅实测内容" * 180) + " [E1]。"),
                    "key_takeaways_zh": ["基于真实产品流程生成的持久化要点 [E1]"],
                    "action_items_zh": ["验证备份还原后仍保留已核验引用 [E1]"],
                    "citations": [{"ref": "E1", "note_zh": "真实核心依据"}],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_long_qa_completer))
    fast_app: FastReadApiApplication = env["fast_app"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    _seed_video_with_cues(env, "vidBk01", title="Backup Target", cues=((0, 4000, "Ground anchor"),))
    hub.distill_video("vidBk01")

    for idx in range(22):
        res_ask = hub.ask_research_question(
            {"question": f"Large Q&A #{idx} Ground anchor " + ("x" * 200), "video_ids": ["vidBk01"]}
        )
        assert res_ask["session"]["answer_status"] == "GROUNDED"

    exported = json.dumps(hub.export_backup_snapshot(), ensure_ascii=False).encode("utf-8")
    assert len(exported) > 41_545

    res_code, res_body = fast_app.handle("POST", "/api/v1/workspace-ai/restore", exported)
    assert res_code == HTTPStatus.OK
    assert res_body["restored"]["research_sessions"] == 22
    restored_sessions = hub.list_research_sessions()["sessions"]
    assert len(restored_sessions) == 22
    assert all(s["answer_status"] == "GROUNDED" for s in restored_sessions)

    over_2mib = hub.export_backup_snapshot()
    over_2mib["video_ai_briefs"] = [
        {
            "video_id": "vidBk01",
            "headline_zh": "超长摘要",
            "summary_zh": "S" * 500,
            "score": 8.5,
            "score_reason_zh": "Valid",
            "recommendation_tier": "MUST_WATCH",
            "content_bucket": "DEEP_DIVE",
            "is_short_noise": 0,
            "duration_seconds": 120,
            "topics_json": "[]",
            "topic_cluster_zh": "Backup",
            "core_points_json": "[]",
            "product_opportunities_json": "[]",
            "business_opportunities_json": "[]",
            "filtered_noise_json": "[]",
            "intelligence_id": None,
            "revision_id": None,
            "provider": "local_ollama",
            "model": "qwen3.5:9b",
            "obsidian_markdown": "# Huge\n" + ("M" * 2_200_000),
            "updated_at": "2026-11-23T12:00:00Z",
            "source_basis": "TRANSCRIPT",
        }
    ]
    over_2mib_bytes = json.dumps(over_2mib, ensure_ascii=False).encode("utf-8")
    assert len(over_2mib_bytes) > 2 * 1024 * 1024
    big_code, _ = fast_app.handle("POST", "/api/v1/workspace-ai/restore", over_2mib_bytes)
    assert big_code == HTTPStatus.OK

    oversized_std = json.dumps({"ollama_model": "a" * 40_000}).encode("utf-8")
    std_code, std_body = fast_app.handle(
        "PUT", "/api/v1/workspace-ai/settings", oversized_std
    )
    assert std_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert std_body["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_p1_09_keyframe_backup_restore_and_legacy_missing_asset_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_a = _build_env(tmp_path, monkeypatch, name="kf_a")
    _seed_video_with_cues(env_a, "vidKf09", title="视觉关键帧测试", cues=((0, 3000, "架构图"),))
    hub_a: WorkspaceIntelligenceHub = env_a["hub"]
    vid_hash = hashlib.sha256(b"vidKf09").hexdigest()[:16]
    gen_dir = env_a["project_root"] / ".workspace-ai" / "keyframes" / vid_hash / "gen-aaaabbbbcccc1111"
    gen_dir.mkdir(parents=True, exist_ok=True)
    img_path = gen_dir / "frame_01_00000500.jpg"
    img_path.write_bytes(MINIMAL_JPEG)
    img_sha = hashlib.sha256(MINIMAL_JPEG).hexdigest()
    frame_meta = [
        {
            "frame_index": 1,
            "frame_id": "f01-00000500",
            "filename": "frame_01_00000500.jpg",
            "storage_subdir": "gen-aaaabbbbcccc1111",
            "obsidian_asset_name": "visual-kf09-f01-00000500.jpg",
            "timestamp_ms": 500,
            "timestamp_label": "00:00",
            "selection_reason": "scene",
            "frame_kind": "ARCHITECTURE",
            "has_visual_info": True,
            "title_zh": "架构总览",
            "visual_detail_zh": "三层框图",
            "transcript_fusion_zh": "对应开篇讲解",
            "nearby_transcript": "架构图",
            "byte_count": len(MINIMAL_JPEG),
            "sha256": img_sha,
        }
    ]
    with hub_a._db_lock:
        conn = hub_a._connect_write()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO video_visual_analyses (
                        video_id, source_hash, visual_summary_zh, visual_takeaways_json,
                        frames_json, frame_count, informative_frame_count, provider, model, updated_at
                    ) VALUES (?, ?, ?, '["要点"]', ?, 1, 1, 'local_ollama', 'gemma3:4b', '2026-11-23T12:00:00Z')
                    """,
                    ("vidKf09", "src", "视觉摘要", json.dumps(frame_meta, ensure_ascii=False)),
                )
        finally:
            conn.close()

    snapshot = hub_a.export_backup_snapshot()
    assert len(snapshot["visual_keyframe_assets"]) == 1  # type: ignore[arg-type]

    env_b = _build_env(tmp_path, monkeypatch, name="kf_b")
    _seed_video_with_cues(env_b, "vidKf09", title="视觉关键帧测试", cues=((0, 3000, "架构图"),))
    res_b = env_b["hub"].restore_backup_snapshot(snapshot)
    assert res_b["restored"]["visual_images"] == 1
    assert res_b["missing_visual_images"] == 0
    vis_b = env_b["hub"].get_video_visual_analysis("vidKf09")
    assert vis_b is not None
    assert vis_b["frames"][0]["image_available"] is True
    dl = env_b["fast_app"].backup_download(vis_b["frames"][0]["image_url"])
    assert dl is not None and dl[0] == HTTPStatus.OK and dl[2] == MINIMAL_JPEG

    legacy_snap = dict(snapshot)
    legacy_snap.pop("visual_keyframe_assets", None)
    env_c = _build_env(tmp_path, monkeypatch, name="kf_c")
    _seed_video_with_cues(env_c, "vidKf09", title="视觉关键帧测试", cues=((0, 3000, "架构图"),))
    res_c = env_c["hub"].restore_backup_snapshot(legacy_snap)
    assert res_c["restored"]["visual_images"] == 0
    assert res_c["missing_visual_images"] == 1
    assert res_c["warnings"]
    vis_c = env_c["hub"].get_video_visual_analysis("vidKf09")
    assert vis_c is not None and vis_c["frames"][0]["image_available"] is False
    _, zip_bytes, _ = env_c["hub"].build_video_visual_obsidian_zip("vidKf09")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        md_name = next(n for n in zf.namelist() if n.endswith(".md"))
        md_text = zf.read(md_name).decode("utf-8")
    assert "![[assets/" not in md_text


@pytest.mark.skipif(media_tool("ffmpeg") is None, reason="ffmpeg required for mp4 test")
def test_p1_10_failed_visual_reanalysis_preserves_prior_jpegs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = {"fail": False}

    def _vis_completer(
        *,
        system_prompt: str,
        user_prompt: str,
        image_paths: Any,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 2200,
    ) -> tuple[dict[str, Any], str, str]:
        del system_prompt, user_prompt, mode, max_tokens
        if state["fail"]:
            raise RuntimeError("boom on reanalysis")
        return (
            {
                "visual_summary_zh": "首轮关键帧分析成功",
                "visual_takeaways_zh": ["首轮有效帧"],
                "frames": [
                    {
                        "frame_index": idx,
                        "frame_kind": "ARCHITECTURE",
                        "has_visual_info": True,
                        "title_zh": f"画面 {idx}",
                        "visual_detail_zh": "图表",
                        "transcript_fusion_zh": "融合",
                    }
                    for idx in range(1, len(list(image_paths)) + 1)
                ],
            },
            provider,
            model,
        )

    env = _build_env(tmp_path, monkeypatch, vision_completer=_vis_completer)
    mp4 = _create_tiny_mp4(env["tmp"])
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_file(mp4)
    vid = imp.content_id

    hub: WorkspaceIntelligenceHub = env["hub"]
    first = hub.analyze_video_keyframes(vid)
    first_fid = first["analysis"]["frames"][0]["frame_id"]  # type: ignore[index]
    first_url = first["analysis"]["frames"][0]["image_url"]  # type: ignore[index]

    state["fail"] = True
    with pytest.raises((ApiError, RuntimeError)):
        hub.analyze_video_keyframes(vid)

    assert hub.read_video_keyframe_image(vid, first_fid) is not None
    dl = env["fast_app"].backup_download(first_url)
    assert dl is not None and dl[0] == HTTPStatus.OK


def test_p1_11_symlink_guards_in_data_root_and_keyframe_serving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    outside = env["tmp"] / "secret_outside.jpg"
    outside.write_bytes(MINIMAL_JPEG + b"OUTSIDE")

    link_in_data = env["data_root"] / "notes"
    link_in_data.mkdir(parents=True, exist_ok=True)
    symlink_path = link_in_data / "evil_link.txt"
    symlink_path.symlink_to(outside)
    token = _data_root_token(env["data_root"])
    assert any(
        isinstance(item, tuple) and len(item) >= 2 and item[1] == "SYMLINK"
        for item in token
    )

    _seed_video_with_cues(env, "vidSymlink", title="Symlink Keyframe", cues=((0, 2000, "txt"),))
    vid_hash = hashlib.sha256(b"vidSymlink").hexdigest()[:16]
    gen_dir = env["project_root"] / ".workspace-ai" / "keyframes" / vid_hash / "gen-1111222233334444"
    gen_dir.mkdir(parents=True, exist_ok=True)
    kf_link = gen_dir / "frame_01_00000100.jpg"
    kf_link.symlink_to(outside)
    frame_meta = [
        {
            "frame_index": 1,
            "frame_id": "f01-00000100",
            "filename": "frame_01_00000100.jpg",
            "storage_subdir": "gen-1111222233334444",
            "timestamp_ms": 0,
            "timestamp_label": "00:00",
            "selection_reason": "scene",
            "frame_kind": "SLIDE",
            "has_visual_info": True,
            "title_zh": "Link",
            "visual_detail_zh": "",
            "transcript_fusion_zh": "",
            "nearby_transcript": "",
        }
    ]
    with env["hub"]._db_lock:
        conn = env["hub"]._connect_write()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO video_visual_analyses (
                        video_id, source_hash, visual_summary_zh, visual_takeaways_json,
                        frames_json, frame_count, informative_frame_count, provider, model, updated_at
                    ) VALUES (?, 'h', 's', '[]', ?, 1, 1, 'local', 'm', '2026-11-23T12:00:00Z')
                    """,
                    ("vidSymlink", json.dumps(frame_meta)),
                )
        finally:
            conn.close()

    assert env["hub"].read_video_keyframe_image("vidSymlink", "f01-00000100") is None
    dl = env["fast_app"].backup_download("/api/v1/workspace-ai/videos/vidSymlink/keyframes/f01-00000100.jpg")
    assert dl is not None and dl[0] == HTTPStatus.NOT_FOUND


def test_p1_12_and_p1_13_full_library_search_and_sync_beyond_300(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    hub: WorkspaceIntelligenceHub = env["hub"]
    for idx in range(320):
        vid = f"vidScale{idx:03d}"
        title = "星云特别标记长视频" if idx == 230 else f"常规内容样本 {idx:03d}"
        ts = NOW - timedelta(minutes=idx)
        if idx == 315:
            _seed_video_with_cues(
                env,
                vid,
                title=title,
                cues=((0, 2000, "第315条待同步字幕"),),
                channel_name="Scale Channel",
                updated_offset_min=-idx,
            )
        else:
            _seed_video_metadata_only(
                env,
                vid,
                title=title,
                channel_name="Scale Channel",
                updated_at=ts,
            )

    fast_app: FastReadApiApplication = env["fast_app"]
    q_code, q_body = fast_app.handle(
        "GET", "/api/v1/videos?q=%E6%98%9F%E4%BA%91%E7%89%B9%E5%88%AB%E6%A0%87%E8%AE%B0"
    )
    assert q_code == HTTPStatus.OK
    assert q_body["pagination"]["total_count"] == 1
    assert [v["video_id"] for v in q_body["videos"]] == ["vidScale230"]

    p2_code, p2_body = fast_app.handle("GET", "/api/v1/videos?limit=200&offset=200")
    assert p2_code == HTTPStatus.OK
    assert p2_body["pagination"]["total_count"] == 320
    assert "vidScale230" in {v["video_id"] for v in p2_body["videos"]}

    sync_status = hub.get_sync_status()
    assert sync_status["total_videos"] == 320
    assert "vidScale315" in sync_status["pending_video_ids"]  # type: ignore[operator]


def test_p1_14_and_p2_07_cache_barrier_and_cold_read_timings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    for i in range(40):
        vid = f"vidPerf{i:02d}"
        _seed_video_with_cues(
            env,
            vid,
            title=f"Performance Item {i:02d}",
            cues=((0, 2000, f"Cue text for {i:02d}"),),
            updated_offset_min=i,
        )
        env["hub"].distill_video(vid)

    fast_app: FastReadApiApplication = env["fast_app"]
    timings_ms: list[float] = []
    for _ in range(5):
        fast_app._bump_mutation_epoch()
        c, body = fast_app.handle("GET", "/api/v1/videos")
        assert c == HTTPStatus.OK
        assert len(body["videos"]) == 40
        meta = fast_app.get_last_read_timings("/api/v1/videos")
        assert meta is not None
        assert meta["published_to_cache"] is True
        timings_ms.append(float(meta["total_ms"]))  # type: ignore[arg-type]
    assert len(timings_ms) == 5
    assert statistics.median(timings_ms) < 500.0
    assert max(timings_ms) < 1500.0

    brief_subset = env["hub"].get_video_briefs_map_for_ids(
        ["vidPerf00", "vidPerf01"], include_markdown=False
    )
    assert set(brief_subset.keys()) == {"vidPerf00", "vidPerf01"}
    assert brief_subset["vidPerf00"]["obsidian_markdown"] == ""

    fast_app._bump_mutation_epoch()
    wrote = {"done": False}

    def _raced_compute() -> dict[str, object]:
        payload = fast_app._fast_get_videos()
        if not wrote["done"]:
            wrote["done"] = True
            _seed_video_with_cues(
                env,
                "vidConcurrentNew",
                title="Written During Compute",
                cues=((0, 1000, "Fresh item"),),
                updated_offset_min=100,
            )
        return payload

    first_payload = fast_app._cached_or_compute("/api/v1/videos", _raced_compute)
    assert "vidConcurrentNew" not in {v["video_id"] for v in first_payload["videos"]}  # type: ignore[attr-defined]
    raced_timing = fast_app.get_last_read_timings("/api/v1/videos")
    assert raced_timing is not None and raced_timing["published_to_cache"] is False

    c_after, b_after = fast_app.handle("GET", "/api/v1/videos")
    assert c_after == HTTPStatus.OK
    assert "vidConcurrentNew" in {v["video_id"] for v in b_after["videos"]}


def test_p2_01_p2_02_p2_06_vision_gate_cloud_race_and_windows_zip_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_txt = _build_env(tmp_path, monkeypatch, name="ws_text_only", ollama_models=("llama3.1:8b",))
    runtime = prepare_local_workspace(
        REPO_ROOT,
        workspace_root=tmp_path / "ws_preflight_txt",
        ollama_probe=lambda _url: (True, ("llama3.1:8b",)),
        byok_credential_store=_MemorySecret(),
    )
    pf_txt = WorkspacePreflight(
        platform_supported=True,
        frontend_ready=True,
        ollama_reachable=True,
        ollama_models=("llama3.1:8b",),
        yt_dlp_available=True,
        ffmpeg_available=True,
        web_dir=(REPO_ROOT / "frontend" / "dist").resolve(),
    )
    banner = format_startup_banner(
        replace(runtime, preflight=pf_txt),
        port=8794,
        serve_web=True,
        check_only=True,
    )
    assert "visual keyframes ready" not in banner
    assert "[WARN] Vision" in banner

    class _OfflineNoShowOpener:
        def open(self, req: Any, timeout: float = 2.0) -> Any:
            del timeout
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if url.endswith("/api/show"):
                raise urllib.error.URLError("offline /api/show probe")
            raise AssertionError(f"Text-only model must be blocked before chat call: {url}")

    dummy_jpg = env_txt["tmp"] / "dummy.jpg"
    dummy_jpg.write_bytes(MINIMAL_JPEG)
    env_txt["hub"].update_settings({"active_mode": "local_ollama", "ollama_model": "llama3.1:8b"})
    env_txt["hub"]._vision_completer = None
    env_txt["hub"]._http_opener = _OfflineNoShowOpener()
    try:
        with pytest.raises(ApiError) as vis_gate:
            env_txt["hub"]._complete_vision_json(
                system_prompt="sys",
                user_prompt="usr",
                image_paths=[dummy_jpg],
                max_tokens=300,
                allow_cloud=False,
            )
        assert vis_gate.value.code == "LOCAL_VISION_MODEL_UNSUPPORTED"
    finally:
        env_txt["hub"]._http_opener = None

    hub_race: WorkspaceIntelligenceHub = env_txt["hub"]

    def _attempt_reserve(_i: int) -> str:
        return hub_race._reserve_cloud_call(
            provider="openai_compatible",
            model="gpt-4o-mini",
            endpoint="https://api.openai.com/v1/chat/completions",
            daily_limit=1,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_attempt_reserve, i) for i in range(2)]
        outcomes: list[str] = []
        errors: list[str] = []
        for fut in futures:
            try:
                outcomes.append(fut.result())
            except ApiError as err:
                errors.append(err.code)
    assert len(outcomes) == 1
    assert errors == ["CLOUD_DAILY_BUDGET_EXCEEDED"]

    # Also verify full product dispatch path (_complete_json -> _authorize_cloud_dispatch) under race.
    env_dispatch = _build_env(tmp_path, monkeypatch, name="ws_dispatch_race")
    hub_disp: WorkspaceIntelligenceHub = env_dispatch["hub"]
    hub_disp._byok_store.save("sk-fake-race")
    hub_disp.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_provider": "openai_compatible",
            "cloud_base_url": "https://api.openai.com/v1",
            "cloud_model": "gpt-4o-mini",
            "cloud_daily_call_limit": 1,
        }
    )

    def _attempt_complete(_i: int) -> str:
        _, prov, _m = hub_disp._complete_json(
            system_prompt="sys", user_prompt="usr", allow_cloud=True
        )
        return prov

    with ThreadPoolExecutor(max_workers=2) as pool:
        disp_futs = [pool.submit(_attempt_complete, i) for i in range(2)]
        disp_ok: list[str] = []
        disp_err: list[str] = []
        for fut in disp_futs:
            try:
                disp_ok.append(fut.result())
            except ApiError as err:
                disp_err.append(err.code)
    assert len(disp_ok) == 1
    assert disp_err == ["CLOUD_DAILY_BUDGET_EXCEEDED"]

    for bad_vid, bad_title in (("vidWinCon", "CON"), ("vidWinAux", "AUX.md"), ("vidWinNul", "NUL")):
        _seed_video_with_cues(env_txt, bad_vid, title=bad_title, cues=((0, 2000, "Windows reserved"),))
        hub_race.distill_video(bad_vid)

    _fn, vault_zip, _counts, _readme = hub_race.build_obsidian_vault_zip(scope="all")
    with zipfile.ZipFile(io.BytesIO(vault_zip)) as zf:
        names = [Path(n).name.upper() for n in zf.namelist() if n.endswith(".md")]
        for reserved in ("CON.MD", "AUX.MD", "NUL.MD"):
            assert reserved not in names
        assert any(n.startswith("_CON") for n in names)
        assert any(n.startswith("_AUX") for n in names)
        assert any(n.startswith("_NUL") for n in names)


def test_n1_p1_01_comma_brackets_bare_ref_and_uncited_sentence_pruning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenarios: dict[str, dict[str, Any]] = {
        "comma_split_mix": {
            "answerable": True,
            "answer_zh": (
                "核心方案已落地双库隔离[E1]。"
                "另外该方案由 Google 官方开发，参见[E88]。"
                "此外年营收已达十亿美元。"
            ),
            "key_takeaways_zh": ["双库隔离保障一致性[E1]", "销售额暴涨十倍，[E99]"],
            "action_items_zh": ["核验隔离逻辑[E1]", "核对传闻 E88"],
            "citations": [{"ref": "E1", "note_zh": "有效依据"}, {"ref": "E88", "note_zh": "假"}],
        },
        "same_sentence_comma_ride": {
            "answerable": True,
            "answer_zh": "核心方案采用双库隔离[E1]，而且该方案由 Google 开发，参见[E88]。",
            "key_takeaways_zh": ["包含全角【E77】", "包含空格[ E88 ]", "复合[E88,E1]"],
            "action_items_zh": ["复核裸引用 E88"],
            "citations": [{"ref": "E1", "note_zh": "有效依据"}],
        },
        "variant_brackets_only": {
            "answerable": True,
            "answer_zh": "系统由独立团队研发【E77】。此外具备[ E88 ]及[E88,E1]与裸引用E88支撑。",
            "key_takeaways_zh": ["有效要点[E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "仅占位"}],
        },
        "comma_stub_ref_only": {
            "answerable": True,
            "answer_zh": "核心方案采用双库隔离，参见[E1]，而且该方案由 Google 开发，参见[E88]。",
            "key_takeaways_zh": [],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "仅占位"}],
        },
    }

    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            for key, payload in scenarios.items():
                if key in user_prompt:
                    return dict(payload), provider, model
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    _seed_video_with_cues(
        env,
        "vidN1",
        title="双库隔离架构实录",
        cues=((0, 8000, "核心方案已落地双库隔离并锁定证据。"),),
    )

    s1 = hub.ask_research_question({"question": "comma_split_mix 请回答"})["session"]
    assert s1["answer_status"] == "GROUNDED"
    assert "核心方案已落地双库隔离[E1]" in str(s1["answer_zh"])
    for forbidden in ("Google", "十亿美元", "销售额暴涨十倍", "E88", "E99"):
        assert forbidden not in str(s1["answer_zh"])
        assert forbidden not in " ".join(s1["key_takeaways_zh"])
        assert forbidden not in " ".join(s1["action_items_zh"])
        assert forbidden not in str(s1["obsidian_markdown"])

    hist_s1 = next(
        s for s in hub.list_research_sessions()["sessions"] if s["session_id"] == s1["session_id"]
    )
    assert "Google" not in str(hist_s1["answer_zh"])
    assert "十亿美元" not in str(hist_s1["answer_zh"])

    s2 = hub.ask_research_question({"question": "same_sentence_comma_ride 请回答"})["session"]
    assert s2["answer_status"] == "GROUNDED"
    assert "核心方案采用双库隔离[E1]" in str(s2["answer_zh"])
    assert len(s2["citations"]) == 1 and s2["citations"][0]["ref_label"] == "E1"
    for forbidden in ("Google", "E77", "E88", "E99"):
        assert forbidden not in str(s2["answer_zh"])
        assert forbidden not in " ".join(s2["key_takeaways_zh"])
        assert forbidden not in " ".join(s2["action_items_zh"])
        assert forbidden not in str(s2["obsidian_markdown"])

    s3 = hub.ask_research_question({"question": "variant_brackets_only 请回答"})["session"]
    assert s3["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert s3["refused"] is True
    assert s3["citations"] == []

    s4 = hub.ask_research_question({"question": "comma_stub_ref_only 请回答"})["session"]
    assert s4["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert s4["refused"] is True
    assert s4["citations"] == []
    assert "Google" not in str(s4["answer_zh"])
    assert "Google" not in str(s4["obsidian_markdown"])


def test_n2_p1_03_restored_obsidian_markdown_reverified_on_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "LOCAL_TEXT_DISTILL_SCHEMA" in system_prompt:
            return (
                {
                    "headline_zh": "可验证记录",
                    "summary_zh": "摘要依赖主库核验。",
                    "score": 9.1,
                    "score_reason_zh": "结构完整。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["核验"],
                    "topic_cluster_zh": "安全边界",
                    "core_points": [
                        {
                            "text_zh": "恢复记录必须重新核验",
                            "section_index": 0,
                            "evidence_quote": "主库原始文本不可伪造。",
                        }
                    ],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answerable": True,
                    "answer_zh": "主库原始文本明确声明不可伪造[E1]。",
                    "key_takeaways_zh": ["主库文本核验[E1]"],
                    "action_items_zh": [],
                    "citations": [{"ref": "E1", "note_zh": "主库原文出处"}],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env_src = _build_env(tmp_path, monkeypatch, name="n2_src", completer=_StubCompleter(_completer))
    imp = LocalContentProvider(env_src["repo"], env_src["data_root"], now=lambda: NOW).import_bytes(
        "n2_source.md", "主库原始文本不可伪造。".encode("utf-8")
    )
    vid = imp.content_id
    env_src["hub"].distill_video(vid)
    env_src["hub"].ask_research_question({"question": "主库原文说了什么？", "video_ids": [vid]})
    snapshot = json.loads(json.dumps(env_src["hub"].export_backup_snapshot()))

    snapshot["video_ai_briefs"][0]["obsidian_markdown"] = (
        "---\ntitle: \"Tampered\"\n---\n\n> 原话摘录：TAMPERED_BRIEF_QUOTE\n"
    )
    pts = json.loads(snapshot["video_ai_briefs"][0]["core_points_json"])
    pts[0]["excerpt"] = "TAMPERED_BRIEF_QUOTE"
    snapshot["video_ai_briefs"][0]["core_points_json"] = json.dumps(pts, ensure_ascii=False)

    snapshot["research_qa_sessions"][0]["obsidian_markdown"] = (
        "---\ntitle: \"Tampered QA\"\n---\n\n> TAMPERED_QA_QUOTE\n"
    )
    cites = json.loads(snapshot["research_qa_sessions"][0]["citations_json"])
    cites[0]["excerpt"] = "TAMPERED_QA_QUOTE"
    snapshot["research_qa_sessions"][0]["citations_json"] = json.dumps(cites, ensure_ascii=False)

    snapshot["video_visual_analyses"] = [
        {
            "video_id": vid,
            "source_hash": "src",
            "visual_summary_zh": "视觉摘要",
            "visual_takeaways_json": '["要点"]',
            "frames_json": "[]",
            "frame_count": 0,
            "informative_frame_count": 0,
            "provider": "ollama",
            "model": "gemma3:4b",
            "updated_at": "2026-11-23T12:00:00Z",
        }
    ]

    env_dst = _build_env(tmp_path, monkeypatch, name="n2_dst")
    dst_hub: WorkspaceIntelligenceHub = env_dst["hub"]
    dst_hub.restore_backup_snapshot(snapshot)

    brief = dst_hub.get_video_brief(vid)
    assert brief is not None
    assert brief["verification_status"] == "NEEDS_REVERIFICATION"
    assert "待核验" in str(brief["obsidian_markdown"])
    assert "TAMPERED_BRIEF_QUOTE" not in str(brief["obsidian_markdown"])
    assert brief["core_points"][0]["excerpt"] == ""

    single_md = str(dst_hub.get_video_obsidian_export(vid)["markdown"])
    assert "待核验" in single_md and "TAMPERED_BRIEF_QUOTE" not in single_md

    _, vis_zip, _ = dst_hub.build_video_visual_obsidian_zip(vid)
    with zipfile.ZipFile(io.BytesIO(vis_zip)) as zf:
        vis_md = zf.read(next(n for n in zf.namelist() if n.endswith(".md"))).decode("utf-8")
    assert "待核验" in vis_md and "TAMPERED_BRIEF_QUOTE" not in vis_md

    sess = dst_hub.list_research_sessions()["sessions"][0]
    assert sess["answer_status"] == "NEEDS_REVERIFICATION"
    assert "待核验" in str(sess["obsidian_markdown"])
    assert "TAMPERED_QA_QUOTE" not in str(sess["obsidian_markdown"])

    _, vault_zip, _, _ = dst_hub.build_obsidian_vault_zip(scope="all")
    with zipfile.ZipFile(io.BytesIO(vault_zip)) as zf:
        vault_texts = "\n".join(
            zf.read(n).decode("utf-8") for n in zf.namelist() if n.endswith(".md")
        )
    assert "TAMPERED_BRIEF_QUOTE" not in vault_texts
    assert "TAMPERED_QA_QUOTE" not in vault_texts
    assert "待核验" in vault_texts


def test_n3_backup_graceful_degradation_above_40mib_and_64mib_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame_blob = MINIMAL_JPEG + (b"\x00" * (500_000 - len(MINIMAL_JPEG)))
    frame_sha = hashlib.sha256(frame_blob).hexdigest()

    def _seed_many_keyframes(env: dict[str, Any], *, vid_count: int, frames_per_vid: int) -> None:
        hub: WorkspaceIntelligenceHub = env["hub"]
        for v_idx in range(vid_count):
            vid = f"vidBkLarge{v_idx:02d}"
            _seed_video_with_cues(
                env, vid, title=f"Large Keyframe Video {v_idx:02d}", cues=((0, 2000, f"Cue {v_idx}"),)
            )
            hub.distill_video(vid)
            vid_hash = hashlib.sha256(vid.encode("utf-8")).hexdigest()[:16]
            gen_id = f"gen-{v_idx:016x}"
            gen_dir = env["project_root"] / ".workspace-ai" / "keyframes" / vid_hash / gen_id
            gen_dir.mkdir(parents=True, exist_ok=True)
            frames_meta = []
            for f_idx in range(1, frames_per_vid + 1):
                fid = f"f{f_idx:02d}-{f_idx * 1000}"
                fname = f"frame_{f_idx:02d}_{f_idx * 1000:08d}.jpg"
                (gen_dir / fname).write_bytes(frame_blob)
                frames_meta.append(
                    {
                        "frame_index": f_idx,
                        "frame_id": fid,
                        "filename": fname,
                        "storage_subdir": gen_id,
                        "obsidian_asset_name": f"kf-{v_idx}-{fid}.jpg",
                        "timestamp_ms": f_idx * 1000,
                        "timestamp_label": f"00:{f_idx:02d}",
                        "selection_reason": "uniform",
                        "frame_kind": "SLIDE",
                        "has_visual_info": True,
                        "title_zh": f"帧 {f_idx}",
                        "visual_detail_zh": "大图帧",
                        "transcript_fusion_zh": "融合",
                        "nearby_transcript": f"Cue {v_idx}",
                        "byte_count": len(frame_blob),
                        "sha256": frame_sha,
                    }
                )
            with hub._db_lock:
                conn = hub._connect_write()
                try:
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO video_visual_analyses (
                                video_id, source_hash, visual_summary_zh, visual_takeaways_json,
                                frames_json, frame_count, informative_frame_count, provider, model, updated_at
                            ) VALUES (?, 'src', '视觉摘要', '["要点"]', ?, ?, ?, 'ollama', 'gemma3:4b', '2026-11-24T00:00:00Z')
                            """,
                            (vid, json.dumps(frames_meta, ensure_ascii=False), frames_per_vid, frames_per_vid),
                        )
                finally:
                    conn.close()

    # Case (a): Keyframe JPEGs > 40 MiB (9 * 10 * 500KB = 45MB > 40 MiB) still exports & restores briefs/Q&A
    env_a = _build_env(tmp_path, monkeypatch, name="n3_over_40m")
    _seed_many_keyframes(env_a, vid_count=9, frames_per_vid=10)
    env_a["hub"].ask_research_question({"question": "Large Keyframe Cue 0?", "video_ids": ["vidBkLarge00"]})

    snap_a = env_a["hub"].export_backup_snapshot()
    assert snap_a["counts"]["briefs"] == 9  # type: ignore[index]
    assert snap_a["counts"]["research_sessions"] == 1  # type: ignore[index]
    assert snap_a["counts"]["skipped_visual_assets"] > 0  # type: ignore[index]
    assert snap_a["warnings"]
    assert sum(int(a["byte_count"]) for a in snap_a["visual_keyframe_assets"]) <= MAX_BACKUP_VISUAL_RAW_BYTES  # type: ignore[attr-defined]
    snap_a_bytes = json.dumps(snap_a, ensure_ascii=False).encode("utf-8")
    assert len(snap_a_bytes) <= MAX_BACKUP_EXPORT_JSON_BYTES

    env_a_dst = _build_env(tmp_path, monkeypatch, name="n3_over_40m_dst")
    rs_a_code, rs_a_body = env_a_dst["fast_app"].handle("POST", "/api/v1/workspace-ai/restore", snap_a_bytes)
    assert rs_a_code == HTTPStatus.OK
    assert rs_a_body["restored"]["briefs"] == 9
    assert rs_a_body["restored"]["research_sessions"] == 1

    # Case (b): Visual assets near 40 MiB (~39 MiB raw -> ~52 MiB b64) PLUS > 10 MiB text -> trimmed <= 64 MiB & restores HTTP 200
    env_b = _build_env(tmp_path, monkeypatch, name="n3_over_64m")
    _seed_many_keyframes(env_b, vid_count=8, frames_per_vid=9)  # 72 * 500KB = 36MB raw (~48MB b64)
    large_md_block = "大文本笔记内容段落。" * 35_000  # ~1.0 MiB in answer_zh + ~1.0 MiB rebuilt MD
    with env_b["hub"]._db_lock:
        conn = env_b["hub"]._connect_write()
        try:
            with conn:
                for q_i in range(12):  # ~24 MiB text total
                    conn.execute(
                        """
                        INSERT INTO research_qa_sessions (
                            session_id, question, answer_zh, key_takeaways_json, action_items_json,
                            citations_json, video_count, provider, model, obsidian_markdown, created_at, scope_json
                        ) VALUES (?, ?, ?, '[]', '[]', '[]', 1, 'local_ollama', 'qwen3.5:9b', ?, '2026-11-24T01:00:00Z', '{}')
                        """,
                        (f"big-qa-{q_i:02d}", f"Q{q_i}", large_md_block, large_md_block),
                    )
        finally:
            conn.close()

    snap_b = env_b["hub"].export_backup_snapshot()
    snap_b_bytes = json.dumps(snap_b, ensure_ascii=False).encode("utf-8")
    assert len(snap_b_bytes) <= MAX_WORKSPACE_AI_BACKUP_BYTES
    assert snap_b["counts"]["skipped_visual_assets"] > 0  # type: ignore[index]
    assert snap_b["warnings"]

    env_b_dst = _build_env(tmp_path, monkeypatch, name="n3_over_64m_dst")
    rs_b_code, rs_b_body = env_b_dst["fast_app"].handle("POST", "/api/v1/workspace-ai/restore", snap_b_bytes)
    assert rs_b_code == HTTPStatus.OK
    assert rs_b_body["restored"]["research_sessions"] == 12


def test_n4_p1_02_unmatched_paraphrase_does_not_fallback_to_segment_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "LOCAL_TEXT_DISTILL_SCHEMA" in system_prompt:
            return (
                {
                    "headline_zh": "仓储英文意译",
                    "summary_zh": "Summary rewritten with zero Chinese overlap.",
                    "score": 8.0,
                    "score_reason_zh": "Paraphrased.",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["盘点"],
                    "topic_cluster_zh": "运营盘点",
                    "core_points": [
                        {
                            "text_zh": "Warehouse safety reserve stands at single digits",
                            "section_index": 0,
                            "evidence_quote": "completely unmatched english paraphrase",
                        }
                    ],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_completer))
    note_text = "\n\n".join(
        [
            "周一会议纪要",
            "库存只剩七件",
            "周二巡检记录无异常",
            "周三补充打包耗材",
            "周四供应商确认到货周期",
            "周五整理财务凭证",
            "周六盘点货架标签",
            "周日归档本周流水",
            "下周计划核对退货",
        ]
    )
    imp = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_bytes(
        "paraphrase_note.txt", note_text.encode("utf-8")
    )
    env["hub"].distill_video(imp.content_id)
    brief = env["hub"].get_video_brief(imp.content_id)
    assert brief is not None
    pt = brief["core_points"][0]
    assert pt["evidence_ids"] == []
    assert pt["excerpt"] == ""
    assert "周一会议纪要" not in str(pt["excerpt"])
    assert pt["verification_status"] == "NEEDS_REVERIFICATION"
    assert pt["start_ms"] is None


def test_n6_p2_01_vision_inference_edge_cases_show_override_and_beyond_8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _infer_ollama_model_vision_by_name("gemma3:1b") is False
    assert _infer_ollama_model_vision_by_name("gemma3:270m") is False
    assert _infer_ollama_model_vision_by_name("gemma3n:latest") is False
    assert _infer_ollama_model_vision_by_name("gemma3:4b") is True
    assert _infer_ollama_model_vision_by_name("mistral-small3.1:24b") is True
    assert _infer_ollama_model_vision_by_name("mistral-small3.2:latest") is True
    assert _infer_ollama_model_vision_by_name("deepseek-ocr:latest") is True

    # /api/show capability result overrides name heuristics in both directions
    class _ShowOverrideOpener:
        def open(self, req: Any, timeout: float = 2.0) -> Any:
            del timeout
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if url.endswith("/api/show"):
                payload = json.loads(req.data.decode("utf-8"))
                name = payload["name"]
                caps = ["completion", "vision"] if name == "custom-ocr-v1" else ["completion"]
                return io.BytesIO(json.dumps({"capabilities": caps}).encode("utf-8"))
            raise AssertionError(f"Unexpected chat call for {url}")

    env = _build_env(tmp_path, monkeypatch, ollama_models=("gemma3:4b", "custom-ocr-v1"))
    hub: WorkspaceIntelligenceHub = env["hub"]
    hub._http_opener = _ShowOverrideOpener()
    hub._vision_completer = None
    assert hub._probe_ollama_model_vision("http://127.0.0.1:11434", "gemma3:4b") is False
    assert hub._probe_ollama_model_vision("http://127.0.0.1:11434", "custom-ocr-v1") is True

    hub.update_settings({"active_mode": "local_ollama", "ollama_model": "gemma3:4b"})
    jpg = env["tmp"] / "vis.jpg"
    jpg.write_bytes(MINIMAL_JPEG)
    with pytest.raises(ApiError) as err:
        hub._complete_vision_json(
            system_prompt="sys",
            user_prompt="usr",
            image_paths=[jpg],
            max_tokens=200,
            allow_cloud=False,
        )
    assert err.value.code == "LOCAL_VISION_MODEL_UNSUPPORTED"

    # collect_workspace_preflight discovers a vision model beyond index 8
    models_10 = tuple(f"llama3.1:{i}b" for i in range(9)) + ("gemma3:4b",)
    pf = collect_workspace_preflight(
        REPO_ROOT,
        ollama_probe=lambda _url: (True, models_10),
    )
    assert pf.ollama_vision_ready is True
    assert "gemma3:4b" in pf.ollama_vision_models


@pytest.mark.skipif(media_tool("ffmpeg") is None, reason="ffmpeg required for concurrent test")
def test_n7_concurrent_visual_reanalysis_preserves_committed_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    def _slow_vis_completer(
        *,
        system_prompt: str,
        user_prompt: str,
        image_paths: Any,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 2200,
    ) -> tuple[dict[str, Any], str, str]:
        del system_prompt, user_prompt, mode, max_tokens
        time.sleep(0.04)
        return (
            {
                "visual_summary_zh": "并发抽帧分析成功",
                "visual_takeaways_zh": ["有效帧保留"],
                "frames": [
                    {
                        "frame_index": idx,
                        "frame_kind": "ARCHITECTURE",
                        "has_visual_info": True,
                        "title_zh": f"并发画面 {idx}",
                        "visual_detail_zh": "图表",
                        "transcript_fusion_zh": "融合",
                    }
                    for idx in range(1, len(list(image_paths)) + 1)
                ],
            },
            provider,
            model,
        )

    env = _build_env(tmp_path, monkeypatch, vision_completer=_slow_vis_completer)
    mp4 = _create_tiny_mp4(env["tmp"], name="concurrent_vis.mp4")
    vid = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW).import_file(mp4).content_id
    hub: WorkspaceIntelligenceHub = env["hub"]

    barrier = threading.Barrier(2)

    def _worker(_idx: int) -> dict[str, object]:
        barrier.wait(timeout=5)
        return hub.analyze_video_keyframes(vid)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result() for f in [pool.submit(_worker, i) for i in range(2)]]
    assert len(results) == 2

    final_vis = hub.get_video_visual_analysis(vid)
    assert final_vis is not None and len(final_vis["frames"]) >= 1
    for fr in final_vis["frames"]:
        assert fr["image_available"] is True
        img = hub.read_video_keyframe_image(vid, fr["frame_id"])
        assert img is not None and img[0][:2] == b"\xff\xd8"
    gen_dirs = [p for p in hub._video_keyframes_dir(vid).iterdir() if p.is_dir()]
    assert len(gen_dirs) == 1


def test_n9_p2_02_cross_instance_barrier_cloud_budget_concurrency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_a = _build_env(tmp_path, monkeypatch, name="shared_budget_ws")
    hub_a: WorkspaceIntelligenceHub = env_a["hub"]
    hub_b = WorkspaceIntelligenceHub(
        repository=env_a["repo"],
        data_root=env_a["data_root"],
        project_root=env_a["project_root"],
        byok_credential_store=env_a["byok_store"],
        llm_completer=_StubCompleter(),
        now=lambda: NOW,
    )

    n_threads = 8
    barrier = threading.Barrier(n_threads)

    def _race(i: int) -> str:
        target = hub_a if i % 2 == 0 else hub_b
        barrier.wait(timeout=5)
        return target._reserve_cloud_call(
            provider="openai_compatible",
            model="gpt-4o-mini",
            endpoint="https://api.openai.com/v1/chat/completions",
            daily_limit=3,
        )

    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = [pool.submit(_race, i) for i in range(n_threads)]
        outcomes: list[str] = []
        errors: list[str] = []
        for fut in futures:
            try:
                outcomes.append(fut.result())
            except ApiError as err:
                errors.append(err.code)

    assert len(outcomes) == 3
    assert errors == ["CLOUD_DAILY_BUDGET_EXCEEDED"] * 5


def test_r2_d1_demo_showcase_ui_suggested_chips_grounded_and_traps_refused(
    tmp_path: Path,
) -> None:
    from youtube_intel.demo_showcase import prepare_demo_showcase

    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo_r2_d1", reset=True)
    res_code, sess_body = runtime.fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert res_code == HTTPStatus.OK
    default_chips = sess_body["suggested_questions"]
    assert len(default_chips) >= 3
    scope_opts = sess_body["scope_options"]

    star_code, _ = runtime.fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/curation/batch",
        json.dumps({"video_ids": ["vidDemoAgt1", "vidDemoSol2"], "starred": True}).encode("utf-8"),
    )
    assert star_code == HTTPStatus.OK

    grounded_requests: list[tuple[str, dict[str, Any]]] = [
        (f"default:{i}", {"question": q}) for i, q in enumerate(default_chips)
    ]
    for topic in [t["name"] for t in scope_opts["topic_clusters"]]:
        for q in (
            f"围绕「{topic}」专题，不同创作者的核心共识与关键分歧是什么？",
            f"综合「{topic}」专题原话，提炼最具确定性的落地路径与产品机会",
            f"「{topic}」专题在工程落地或商业验证中有哪些高频避坑点？",
            f'What are the key consensus and disagreements across creators on "{topic}"?',
            f'Synthesize the highest-conviction implementation paths and product opportunities in "{topic}"',
            f'What are the top engineering or business pitfalls highlighted in "{topic}"?',
        ):
            grounded_requests.append((f"topic:{topic}", {"question": q, "topic_cluster": topic}))

    grounded_requests.extend(
        [
            (
                "ch_topic_zh",
                {
                    "question": "Atlas Agent Lab (Demo) 在「AI Agent 工程架构」专题下有哪些核心判断与代表性实战案例？",
                    "channel_key": "Atlas Agent Lab (Demo)",
                    "topic_cluster": "AI Agent 工程架构",
                },
            ),
            (
                "ch_topic_en",
                {
                    "question": 'What are Atlas Agent Lab (Demo)\'s core claims and practical cases in "AI Agent 工程架构"?',
                    "channel_key": "Atlas Agent Lab (Demo)",
                    "topic_cluster": "AI Agent 工程架构",
                },
            ),
        ]
    )

    for ch in scope_opts["channels"]:
        lbl = ch["label"]
        key = ch["key"]
        for q in (
            f"总结 {lbl} 近期内容的核心方法论、高频主题与关键判断变化",
            f"{lbl} 提出了哪些可直接复用的产品设计、工程实践或商业变现动作？",
            f"{lbl} 重点强调了哪些反直觉结论与实战避坑建议？",
            f"Summarize {lbl}'s core methodology, recurring themes, and key shifts",
            f"What reusable product, engineering, or monetization actions does {lbl} recommend?",
            f"What counter-intuitive conclusions and practical pitfalls does {lbl} emphasize?",
        ):
            grounded_requests.append((f"channel:{key}", {"question": q, "channel_key": key}))

    first_video = scope_opts["videos"][0]
    first_title = first_video["title"]
    for q in (
        f"围绕《{first_title}》提炼最核心的方法论、关键论据与可落地步骤",
        f"《{first_title}》提出了哪些反直觉判断、数据指标与避坑警示？",
        "提炼这篇指定视频最核心的方法论、关键论据与可落地步骤",
        "这篇指定视频提出了哪些反直觉判断与实战避坑警示？",
        f'Extract the core methodology, evidence, and actionable steps from "{first_title}"',
        f'What counter-intuitive claims, metrics, and pitfalls appear in "{first_title}"?',
        "Extract the core methodology, evidence, and actionable steps from this selected video",
        "What counter-intuitive claims and practical pitfalls appear in this selected video?",
    ):
        grounded_requests.append(("single", {"question": q, "video_ids": [first_video["video_id"]]}))

    for q in (
        "横向对比这 2 篇指定视频（Atlas Agent Lab (Demo) vs Local-First Foundry (Demo)）的核心共识、观点分歧与演进脉络",
        "综合这 2 篇视频的时间轴原话，提炼最值得立即执行的 3 个实操动作与产品切入点",
        "这 2 篇视频揭示了哪些容易踩坑的误区、边界条件或商业化前提？",
        "Compare core consensus, disagreements, and evolution across these 2 selected videos",
        "Synthesize the top 3 actionable steps and product opportunities grounded in these 2 videos",
        "What key pitfalls, boundary conditions, or monetization prerequisites emerge across these 2 videos?",
    ):
        grounded_requests.append(
            ("multi", {"question": q, "video_ids": ["vidDemoAgt1", "vidDemoSol2"]})
        )

    for q in (
        "综合我收藏的高价值视频，提炼最值得优先落地的核心洞察与行动清单",
        "我收藏的这些视频在技术路线与商业判断上有哪些互补与碰撞？",
        "Synthesize top insights and priority action items across my starred videos",
        "How do my starred videos complement or challenge each other on tech and business?",
    ):
        grounded_requests.append(("starred", {"question": q, "starred_only": True}))

    for tag, payload in grounded_requests:
        ask_code, ask_body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps(payload).encode("utf-8"),
        )
        assert ask_code == HTTPStatus.OK, tag
        sess = ask_body["session"]
        assert sess["answer_status"] == "GROUNDED", (tag, payload["question"], sess["answer_zh"])
        assert len(sess["citations"]) >= 1, (tag, payload["question"])

    for trap_q in (
        "Ollama 在火星大气层的实测温度是多少？",
        "Ollama 本地模型的价格是多少？",
        "Ollama本地模型价格是多少？",
        "Obsidian 双链的市值是多少？",
        "基于当前内容库，Ollama 本地模型价格是多少？",
        "Atlas Agent Lab 的年营收和股价是多少？",
        "AI Agent 工程架构的融资估值是多少？",
        "Summarize Ollama's pricing and market cap across these videos",
        "综合我收藏的视频，Ollama 的股价是多少？",
    ):
        t_code, t_body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": trap_q}).encode("utf-8"),
        )
        assert t_code == HTTPStatus.OK, trap_q
        t_sess = t_body["session"]
        assert t_sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE", trap_q
        assert t_sess["refused"] is True
        assert t_sess["citations"] == []


def test_r2_d2_restored_refused_session_related_excerpts_reverified_and_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answer_status": "REFUSED_INSUFFICIENT_EVIDENCE",
                    "answerable": False,
                    "refusal_reason_zh": "原文未提及火星大气温度。",
                    "answer_zh": "",
                    "key_takeaways_zh": [],
                    "action_items_zh": [],
                    "citations": [],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env_src = _build_env(tmp_path, monkeypatch, name="r2d2_src", completer=_StubCompleter(_completer))
    hub_src: WorkspaceIntelligenceHub = env_src["hub"]
    imp = LocalContentProvider(env_src["repo"], env_src["data_root"], now=lambda: NOW).import_bytes(
        "r2d2_note.md",
        "真实权威主库严格校验每一条原文摘录。\n\n第二段记录隔离恢复策略。".encode("utf-8"),
    )
    hub_src.distill_video(imp.content_id)

    refused_sess = hub_src.ask_research_question(
        {"question": "真实权威主库在火星的温度是多少？", "video_ids": [imp.content_id]}
    )["session"]
    assert refused_sess["refused"] is True
    assert len(refused_sess["related_excerpts"]) >= 1

    clean_backup = hub_src.export_backup_snapshot()
    # 1) Intact backup restored into the SAME intact core DB keeps genuine related_excerpts verified.
    hub_src.restore_backup_snapshot(clean_backup)
    intact_dto = next(
        s for s in hub_src.list_research_sessions()["sessions"] if s["session_id"] == refused_sess["session_id"]
    )
    assert all(c["verified"] is True for c in intact_dto["related_excerpts"])

    # 2) Tamper scope_json.related_excerpts + obsidian_markdown and restore into same DB.
    tampered_backup = copy.deepcopy(clean_backup)
    sess_row = tampered_backup["research_qa_sessions"][0]
    scope_obj = json.loads(str(sess_row["scope_json"]))
    for rel in scope_obj["related_excerpts"]:
        rel["excerpt"] = "TAMPERED_RELATED_EXCERPT_IN_VAULT"
        rel["evidence_id"] = "ev-forged-00000000"
    sess_row["scope_json"] = json.dumps(scope_obj, ensure_ascii=False)
    sess_row["obsidian_markdown"] = "# Tampered\n> TAMPERED_RELATED_EXCERPT_IN_VAULT\nev:ev-forged-00\n"

    hub_src.restore_backup_snapshot(tampered_backup)
    dto_tampered = next(
        s for s in hub_src.list_research_sessions()["sessions"] if s["session_id"] == refused_sess["session_id"]
    )
    for rel in dto_tampered["related_excerpts"]:
        assert rel["verified"] is False
        assert rel["verification_status"] == "NEEDS_REVERIFICATION"
        assert rel["excerpt"] == ""
        assert rel["evidence_id"] == ""
    for rel_in_scope in dto_tampered["scope"]["related_excerpts"]:
        assert rel_in_scope["verified"] is False
        assert rel_in_scope["excerpt"] == ""
        assert rel_in_scope["evidence_id"] == ""
    assert "TAMPERED_RELATED_EXCERPT_IN_VAULT" not in str(dto_tampered["obsidian_markdown"])
    assert "ev-forged-00" not in str(dto_tampered["obsidian_markdown"])
    assert "未通过当前主库核验的相关片段" in str(dto_tampered["obsidian_markdown"])

    _, vault_bytes, _, _ = hub_src.build_obsidian_vault_zip(scope="all")
    with zipfile.ZipFile(io.BytesIO(vault_bytes)) as zf:
        qa_mds = [n for n in zf.namelist() if n.startswith("04-跨视频深度问答/") and n.endswith(".md")]
        assert len(qa_mds) >= 1
        for md_name in qa_mds:
            md_text = zf.read(md_name).decode("utf-8")
            assert "TAMPERED_RELATED_EXCERPT_IN_VAULT" not in md_text
            assert "ev-forged-00" not in md_text
            assert "未通过当前主库核验的相关片段" in md_text

    # 3) Clean untampered backup restored into an empty DB lacking source text also flags & strips excerpts.
    env_empty = _build_env(tmp_path, monkeypatch, name="r2d2_missing_core", completer=_StubCompleter(_completer))
    hub_empty: WorkspaceIntelligenceHub = env_empty["hub"]
    hub_empty.restore_backup_snapshot(clean_backup)
    dto_missing = hub_empty.list_research_sessions()["sessions"][0]
    for rel in dto_missing["related_excerpts"]:
        assert rel["verified"] is False
        assert rel["excerpt"] == ""
        assert rel["evidence_id"] == ""
    _, empty_vault_bytes, _, _ = hub_empty.build_obsidian_vault_zip(scope="all")
    with zipfile.ZipFile(io.BytesIO(empty_vault_bytes)) as zf:
        for md_name in [n for n in zf.namelist() if n.startswith("04-跨视频深度问答/") and n.endswith(".md")]:
            md_text = zf.read(md_name).decode("utf-8")
            assert "真实权威主库严格校验" not in md_text
            assert "未通过当前主库核验的相关片段" in md_text


def test_round2_p0_01_unconditional_grounding_variants_and_history_resanitize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenarios: dict[str, dict[str, Any]] = {
        "silent_ungrounded_sentence": {
            "answerable": True,
            "answer_zh": "核心架构为双库隔离[E1]。此外该公司年营收已达十亿美元并将于明年上市。",
            "key_takeaways_zh": ["双库隔离保障可回溯[E1]", "无引用编造要点"],
            "action_items_zh": ["点击引用核对时间轴[E1]", "未绑定引用建议"],
            "citations": [{"ref": "E1", "note_zh": "有效来源"}],
        },
        "inline_numbered_list_mix": {
            "answerable": True,
            "answer_zh": "1) 双库隔离[E1] 2) 已获红杉 2 亿美元投资",
            "key_takeaways_zh": ["保留编号1[E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "有效来源"}],
        },
        "markdown_table_mix": {
            "answerable": True,
            "answer_zh": (
                "| 维度 | 结论 |\n"
                "| --- | --- |\n"
                "| 架构 | 双库隔离 [E1] |\n"
                "| 融资 | 已完成 C 轮 3 亿美元 |"
            ),
            "key_takeaways_zh": ["保留有据表格行[E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "有效来源"}],
        },
        "inline_pipe_row": {
            "answerable": True,
            "answer_zh": "核心架构双库隔离[E1]。\n融资 | 已完成 C 轮 3 亿美元",
            "key_takeaways_zh": ["保留正句[E1]"],
            "action_items_zh": [],
            "citations": [{"ref": "E1", "note_zh": "有效来源"}],
        },
        "fullwidth_and_lowercase_refs": {
            "answerable": True,
            "answer_zh": "核心架构为双库隔离[E1]。另有外部传闻［Ｅ８８］与补充数字(见 e88)以及空格[E 88]。",
            "key_takeaways_zh": ["仅有效[E1]", "全角要点［Ｅ８８］", "小写(见 e88)"],
            "action_items_zh": ["空格建议[E 88]"],
            "citations": [{"ref": "E1", "note_zh": "有效来源"}],
        },
        "string_false_answerable": {
            "answerable": "false",
            "answer_zh": "核心架构为双库隔离[E1]。",
            "key_takeaways_zh": ["应当拒答清空[E1]"],
            "action_items_zh": ["应当拒答清空[E1]"],
            "citations": [{"ref": "E1", "note_zh": "假通过"}],
        },
    }

    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            for key, payload in scenarios.items():
                if key in user_prompt:
                    return dict(payload), provider, model
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    _seed_video_with_cues(
        env,
        "vidR2P0",
        title="双库隔离架构实录",
        cues=((0, 6000, "核心架构为双库隔离与严格可回溯证据。"),),
    )

    s1 = hub.ask_research_question({"question": "silent_ungrounded_sentence 测试"})["session"]
    assert s1["answer_status"] == "GROUNDED"
    assert "十亿美元" not in s1["answer_zh"]
    assert "十亿美元" not in s1["obsidian_markdown"]
    assert s1["key_takeaways_zh"] == ["双库隔离保障可回溯[E1]"]
    assert s1["action_items_zh"] == ["点击引用核对时间轴[E1]"]
    assert "无引用编造要点" not in s1["obsidian_markdown"]
    assert "未绑定引用建议" not in s1["obsidian_markdown"]

    s2 = hub.ask_research_question({"question": "inline_numbered_list_mix 测试"})["session"]
    assert s2["answer_status"] == "GROUNDED"
    assert "双库隔离[E1]" in s2["answer_zh"]
    assert "红杉" not in s2["answer_zh"]

    s3 = hub.ask_research_question({"question": "markdown_table_mix 测试"})["session"]
    assert s3["answer_status"] == "GROUNDED"
    assert "双库隔离 [E1]" in s3["answer_zh"]
    assert "3 亿美元" not in s3["answer_zh"]

    s4 = hub.ask_research_question({"question": "inline_pipe_row 测试"})["session"]
    assert s4["answer_status"] == "GROUNDED"
    assert "3 亿美元" not in s4["answer_zh"]

    s5 = hub.ask_research_question({"question": "fullwidth_and_lowercase_refs 测试"})["session"]
    assert s5["answer_status"] == "GROUNDED"
    for leak in ("Ｅ８８", "E88", "e88", "E 88", "外部传闻", "补充数字"):
        assert leak not in s5["answer_zh"]
        assert leak not in " ".join(s5["key_takeaways_zh"])
        assert leak not in " ".join(s5["action_items_zh"])
        assert leak not in s5["obsidian_markdown"]

    s6 = hub.ask_research_question({"question": "string_false_answerable 测试"})["session"]
    assert s6["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert s6["refused"] is True
    assert s6["citations"] == []

    # Historical row written with un-cited extra claims must be sanitized on read-back AND restore.
    with hub._db_lock:
        conn = hub._connect_write()
        try:
            with conn:
                conn.execute(
                    "UPDATE research_qa_sessions SET answer_zh = ?, key_takeaways_json = ?, action_items_json = ? WHERE session_id = ?",
                    (
                        "核心架构为双库隔离[E1]。历史遗留无据营收百亿。",
                        json.dumps(["合法要点[E1]", "遗留无引用要点"], ensure_ascii=False),
                        json.dumps(["遗留无引用建议"], ensure_ascii=False),
                        s1["session_id"],
                    ),
                )
        finally:
            conn.close()

    read_back = next(
        s for s in hub.list_research_sessions()["sessions"] if s["session_id"] == s1["session_id"]
    )
    assert "营收百亿" not in str(read_back["answer_zh"])
    assert read_back["key_takeaways_zh"] == ["合法要点[E1]"]
    assert read_back["action_items_zh"] == []
    assert "营收百亿" not in str(read_back["obsidian_markdown"])

    snap = hub.export_backup_snapshot()
    hub.restore_backup_snapshot(snap)
    after_restore = next(
        s for s in hub.list_research_sessions()["sessions"] if s["session_id"] == s1["session_id"]
    )
    assert "营收百亿" not in str(after_restore["answer_zh"])
    assert "遗留无引用" not in str(after_restore["obsidian_markdown"])


def test_round2_p1_01_session_list_scaling_benchmark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _bench_completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answerable": True,
                    "answer_zh": "Benchmark Verified segment reply [E1].",
                    "key_takeaways_zh": ["Takeaway [E1]"],
                    "action_items_zh": ["Verify [E1]"],
                    "citations": [{"ref": "E1", "note_zh": "Valid"}],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, completer=_StubCompleter(_bench_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    _seed_video_with_cues(
        env,
        "vidScaleQa",
        title="Q&A Benchmark Source",
        cues=tuple((i * 2000, i * 2000 + 1800, f"Verified segment #{i} details.") for i in range(10)),
    )
    base_res = hub.ask_research_question({"question": "Benchmark Verified segment", "video_ids": ["vidScaleQa"]})["session"]
    sample_cites = base_res["citations"]
    assert len(sample_cites) >= 1

    def _insert_until(target_total: int) -> None:
        with hub._db_lock:
            conn = hub._connect_write()
            try:
                cur_cnt = int(conn.execute("SELECT COUNT(*) FROM research_qa_sessions").fetchone()[0])
                with conn:
                    for idx in range(cur_cnt, target_total):
                        conn.execute(
                            """
                            INSERT INTO research_qa_sessions (
                                session_id, question, answer_zh, key_takeaways_json, action_items_json,
                                citations_json, video_count, provider, model, obsidian_markdown, created_at, scope_json
                            ) VALUES (?, ?, ?, ?, '[]', ?, 1, 'local_ollama', 'qwen3.5:9b', ?, ?, ?)
                            """,
                            (
                                f"sess-scale-{idx:04d}",
                                f"Scaled Q#{idx}",
                                f"Verified segment reply [E1] #{idx}.",
                                json.dumps([f"Takeaway [E1] #{idx}"], ensure_ascii=False),
                                json.dumps(sample_cites, ensure_ascii=False),
                                f"# Scaled {idx}\n",
                                f"2026-11-24T00:{idx // 60:02d}:{idx % 60:02d}Z",
                                json.dumps({"answer_status": "GROUNDED", "refused": False}),
                            ),
                        )
            finally:
                conn.close()

    for total_sessions in (100, 600):
        _insert_until(total_sessions)
        with hub._evidence_verify_cache_lock:
            hub._evidence_verify_cache.clear()
        t0 = time.perf_counter()
        res_cold = hub.list_research_sessions()
        cold_ms = (time.perf_counter() - t0) * 1000.0
        assert len(res_cold["sessions"]) == 30
        assert all(s["answer_status"] == "GROUNDED" for s in res_cold["sessions"])
        assert cold_ms < 300.0, f"{total_sessions} sessions cold list took {cold_ms:.1f}ms"

        t1 = time.perf_counter()
        res_warm = hub.list_research_sessions()
        warm_ms = (time.perf_counter() - t1) * 1000.0
        assert len(res_warm["sessions"]) == 30
        assert warm_ms < 150.0, f"{total_sessions} sessions warm list took {warm_ms:.1f}ms"


def test_round2_p1_03_special_char_workspace_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for folder_name in ("C#notes", "Q?A"):
        env = _build_env(tmp_path, monkeypatch, name=folder_name)
        hub: WorkspaceIntelligenceHub = env["hub"]
        project_root: Path = env["project_root"]
        hub.update_settings({"ollama_model": "llama3.1:8b", "cloud_daily_call_limit": 7})
        settings = hub.get_settings()
        assert settings["ollama_model"] == "llama3.1:8b"
        assert settings["cloud_daily_call_limit"] == 7

        _seed_video_with_cues(env, "vidSpecPath", title="Special Path Note", cues=((0, 2000, "Safe URI test"),))
        dist = hub.distill_video("vidSpecPath")
        assert dist["ai_brief"]["video_id"] == "vidSpecPath"

        snap = hub.export_backup_snapshot()
        assert len(snap["video_ai_briefs"]) == 1  # type: ignore[arg-type]
        assert not (project_root / ".workspace-ai" / folder_name.split("#")[0].split("?")[0]).exists()


def test_round2_p2_01_demo_gate_pricing_inverted_premise_and_concepts(tmp_path: Path) -> None:
    runtime = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo_r2", reset=True)
    for should_refuse in (
        "Ollama 本地模型多少钱？",
        "Ollama 本地模型的价格是多少？",
        "为什么本地模型不需要证据引用？",
        "为什么 Agent 不需要状态机？",
    ):
        st, body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": should_refuse}).encode("utf-8"),
        )
        assert st == 200
        sess = body["session"]
        assert sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE", should_refuse
        assert sess["refused"] is True
        assert sess["citations"] == []
        assert should_refuse not in str(sess["answer_zh"])

    for should_ground in ("状态机是什么意思？", "帮我总结一下"):
        st, body = runtime.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": should_ground}).encode("utf-8"),
        )
        assert st == 200
        sess = body["session"]
        assert sess["answer_status"] == "GROUNDED", should_ground
        assert len(sess["citations"]) >= 1
        assert len(sess["key_takeaways_zh"]) >= 1
        assert len(sess["action_items_zh"]) >= 1


def test_round2_p2_02_p2_03_p2_04_atomic_restore_limit_and_structured_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_a = _build_env(tmp_path, monkeypatch, name="restore_a")
    hub_a: WorkspaceIntelligenceHub = env_a["hub"]
    hub_a.update_settings({"ollama_model": "qwen3.5:9b", "cloud_daily_call_limit": 3})
    snap = hub_a.export_backup_snapshot()
    assert snap["engine_config"]["cloud_daily_call_limit"] == 3  # type: ignore[index]

    env_b = _build_env(tmp_path, monkeypatch, name="restore_b")
    hub_b: WorkspaceIntelligenceHub = env_b["hub"]
    app_b: FastReadApiApplication = env_b["fast_app"]
    hub_b.restore_backup_snapshot(snap)
    assert hub_b.get_settings()["cloud_daily_call_limit"] == 3

    # Failing restore with tampered config MUST NOT persist partial settings changes or leak raw Python tracebacks.
    bad_snap = copy.deepcopy(snap)
    bad_snap["engine_config"]["ollama_model"] = "attacker-model:latest"  # type: ignore[index]
    bad_snap["engine_config"]["cloud_daily_call_limit"] = 500  # type: ignore[index]
    bad_snap["research_qa_sessions"] = [
        {"session_id": "s-bad-1", "video_count": "not-an-integer"}
    ]
    code, err_body = app_b.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(bad_snap).encode("utf-8")
    )
    assert code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert err_body["error"]["code"] == "RESTORE_INVALID_PAYLOAD"
    assert "invalid literal" not in err_body["error"]["message"]
    assert "ValueError" not in err_body["error"]["message"]
    after_fail = hub_b.get_settings()
    assert after_fail["ollama_model"] == "qwen3.5:9b"
    assert after_fail["cloud_daily_call_limit"] == 3


def test_round2_p2_05_p2_06_p2_07_p2_08_ssrf_proxy_and_local_decoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch, name="r2_sec")
    hub: WorkspaceIntelligenceHub = env["hub"]

    for ssrf_url in (
        "https://2130706433/v1",
        "https://0x7f000001/v1",
        "https://127.0.0.1.nip.io/v1",
        "https://127-0-0-1.sslip.io/v1",
        "https://foo.localhost/v1",
        "https://100.64.0.1/v1",
        "https://sub.localtest.me/v1",
    ):
        with pytest.raises(ValueError):
            hub.update_settings({"cloud_base_url": ssrf_url})

    # Connect-time DNS rebinding protection blocks private/CGNAT resolved IPs before dispatch.
    with monkeypatch.context() as dns_mp:
        dns_mp.setattr(
            socket,
            "getaddrinfo",
            lambda *_a, **_k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("100.64.0.1", 443))],
        )
        hub._byok_store.save("sk-fake-dns-check")
        hub.update_settings(
            {
                "active_mode": "cloud_byok",
                "cloud_provider": "openai_compatible",
                "cloud_base_url": "https://rebind-check.example/v1",
                "cloud_model": "gpt-4o-mini",
                "cloud_daily_call_limit": 5,
            }
        )
        hub._llm_completer = None
        hub._http_opener = None
        with pytest.raises(ApiError) as dns_err:
            hub._complete_json(system_prompt="s", user_prompt="u", allow_cloud=True)
        assert dns_err.value.code == "CLOUD_ENDPOINT_BLOCKED"

    # Loopback Ollama requests bypass http_proxy/HTTP_PROXY even when env proxies are set.
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class _LocalOllamaStubHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            body = json.dumps({"capabilities": ["completion", "vision"]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return None

    srv = HTTPServer(("127.0.0.1", 0), _LocalOllamaStubHandler)
    srv_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    srv_thread.start()
    try:
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
        hub._http_opener = None
        assert hub._probe_ollama_model_vision(f"http://127.0.0.1:{srv.server_port}", "qwen3.5:9b") is True
    finally:
        srv.shutdown()
        srv.server_close()
        srv_thread.join(timeout=5)

    # P2-6 bounded HTTP response cap blocks oversized streams.
    class _HugeResp:
        def read(self, n: int = -1) -> bytes:
            return b"x" * n

        def __enter__(self) -> "_HugeResp":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    class _HugeOpener:
        def open(self, _req: Any, timeout: float = 10.0) -> _HugeResp:
            del timeout
            return _HugeResp()

    hub.update_settings({"active_mode": "local_ollama", "ollama_model": "qwen3.5:9b"})
    hub._http_opener = _HugeOpener()
    with pytest.raises(ApiError) as size_err:
        hub._complete_json(system_prompt="s", user_prompt="u")
    assert size_err.value.code == "LOCAL_OLLAMA_UNAVAILABLE"

    # P2-8 GBK, UTF-16 BOM, and 400-char extension-preserving filenames import cleanly.
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)
    gbk_res = provider.import_bytes("gbk-note.txt", "中文双库隔离笔记".encode("gb18030"))
    assert gbk_res.status == "READY"
    utf16_res = provider.import_bytes("utf16-note.md", "# 标题\n\nUTF16 原文".encode("utf-16"))
    assert utf16_res.status == "READY"
    long_name = ("a" * 396) + ".txt"
    long_res = provider.import_bytes(long_name, "长文件名验证文本".encode("utf-8"))
    assert long_res.status == "READY"
    assert len(long_res.filename) <= 240 and long_res.filename.endswith(".txt")


def test_exp002_takeaway_and_action_inline_citations_hydrated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _completer(
        *,
        system_prompt: str,
        user_prompt: str,
        mode: str,
        provider: str,
        model: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], str, str]:
        del user_prompt, mode, max_tokens
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answerable": True,
                    "answer_zh": "正文核心结论仅标注首条证据 [E1]。",
                    "key_takeaways_zh": ["要点补充引用第二条证据 [E2]"],
                    "action_items_zh": ["建议补充引用第三条证据 [E3]"],
                    "citations": [{"ref": "E1", "note_zh": "主句依据"}],
                },
                provider,
                model,
            )
        return _StubCompleter()(
            system_prompt=system_prompt,
            user_prompt="",
            mode="local_ollama",
            provider=provider,
            model=model,
        )

    env = _build_env(tmp_path, monkeypatch, name="exp002_bullets", completer=_StubCompleter(_completer))
    hub: WorkspaceIntelligenceHub = env["hub"]
    _seed_video_with_cues(
        env,
        "vidBullets1",
        title="多句证据水合验证一",
        cues=(
            (0, 5000, "第一段核心机制说明与 WAL 读取隔离。"),
            (60000, 65000, "第二段补充实测冷读耗时数据。"),
        ),
    )
    _seed_video_with_cues(
        env,
        "vidBullets2",
        title="多句证据水合验证二",
        cues=(
            (0, 5000, "第三段给出可落地导出校验证明。"),
            (60000, 65000, "第四段说明跨源对比边界。"),
        ),
    )

    sess = hub.ask_research_question(
        {"question": "多句证据水合", "video_ids": ["vidBullets1", "vidBullets2"]}
    )["session"]
    assert sess["answer_status"] == "GROUNDED"
    labels = {c["ref_label"] for c in sess["citations"]}
    assert {"E1", "E2", "E3"}.issubset(labels)
    md_text = str(sess["obsidian_markdown"])
    assert "**[E1]**" in md_text and "**[E2]**" in md_text and "**[E3]**" in md_text
