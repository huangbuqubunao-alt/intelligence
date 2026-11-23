"""End-to-end regression suite covering all Codex review findings (P1-01..P1-14, P2-01..P2-07)."""

from __future__ import annotations

import email.message
import hashlib
import io
import json
import subprocess
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
from youtube_intel.distillation import _NoCloudRedirect
from youtube_intel.domain import Availability, LiveStatus, PipelineStatus, VideoMetadata
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.fast_read_api import FastReadApiApplication, _data_root_token
from youtube_intel.local_api import ApiError
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
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub
from youtube_intel.workspace_launcher import (
    WorkspacePreflight,
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
    res_code, res_body = runtime.fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "Ollama 在火星大气层的实测温度是多少？"}).encode("utf-8"),
    )
    assert res_code == HTTPStatus.OK
    session = res_body["session"]
    assert session["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert session["refused"] is True
    assert session["citations"] == []

    ok_code, ok_body = runtime.fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "为什么要用确定性状态机和可追溯证据引用？"}).encode("utf-8"),
    )
    assert ok_code == HTTPStatus.OK
    assert ok_body["session"]["answer_status"] == "GROUNDED"
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

    class _Mock302Handler(urllib.request.HTTPSHandler):
        def https_open(self, req: urllib.request.Request) -> Any:
            requests_seen.append(req.full_url)
            headers = email.message.Message()
            headers["Location"] = "https://attacker.invalid/steal-key"
            fp = io.BytesIO(b"redirect")
            raise urllib.error.HTTPError(
                req.full_url, 302, "Found", headers, fp
            )

    opener = urllib.request.build_opener(_Mock302Handler(), _NoCloudRedirect())
    env = _build_env(tmp_path, monkeypatch, http_opener=opener)
    hub: WorkspaceIntelligenceHub = env["hub"]
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
    env = _build_env(tmp_path, monkeypatch)
    fast_app: FastReadApiApplication = env["fast_app"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    _seed_video_with_cues(env, "vidBk01", title="Backup Target", cues=((0, 4000, "Ground anchor"),))

    with hub._db_lock:
        conn = hub._connect_write()
        try:
            with conn:
                for idx in range(22):
                    conn.execute(
                        """
                        INSERT INTO research_qa_sessions (
                            session_id, question, answer_zh, key_takeaways_json, action_items_json,
                            citations_json, video_count, provider, model, obsidian_markdown, created_at, scope_json
                        ) VALUES (?, ?, ?, '[]', '[]', '[]', 1, 'local_ollama', 'qwen3.5:9b', ?, ?, ?)
                        """,
                        (
                            f"sess-bk-{idx:02d}",
                            f"Large Q&A #{idx} " + ("x" * 600),
                            "Long answer payload " + ("y" * 1200),
                            "# Markdown " + ("z" * 400),
                            "2026-11-23T12:00:00Z",
                            json.dumps({"scope_label_zh": "全库"}),
                        ),
                    )
        finally:
            conn.close()

    exported = json.dumps(hub.export_backup_snapshot(), ensure_ascii=False).encode("utf-8")
    assert len(exported) > 41_545

    res_code, res_body = fast_app.handle("POST", "/api/v1/workspace-ai/restore", exported)
    assert res_code == HTTPStatus.OK
    assert res_body["restored"]["research_sessions"] == 22

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

    dummy_jpg = env_txt["tmp"] / "dummy.jpg"
    dummy_jpg.write_bytes(MINIMAL_JPEG)
    env_txt["hub"]._vision_completer = None
    with pytest.raises(ApiError) as vis_gate:
        env_txt["hub"]._complete_vision_json(
            system_prompt="sys",
            user_prompt="usr",
            image_paths=[dummy_jpg],
            max_tokens=300,
            allow_cloud=False,
        )
    assert vis_gate.value.code == "LOCAL_VISION_MODEL_UNSUPPORTED"

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
