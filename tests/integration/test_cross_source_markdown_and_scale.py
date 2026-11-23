"""Integration tests for Video + Markdown cross-source Q&A, 7-day weekly window, and 250/600-item scale."""

from __future__ import annotations

import gc
import io
import json
import re
import sqlite3
import time
import zipfile
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    VideoMetadata,
)
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.local_api import ApiError
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.providers.bilibili import (
    BilibiliAdapter,
    BilibiliIdentity,
    BilibiliMetadata,
    CaptionAcquisition,
    parse_captions,
)
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_authority import sha256, write_managed
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 20, 14, 0, tzinfo=UTC)


class _MemorySecret:
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


class _CrossSourceBiliAdapter(BilibiliAdapter):
    def __init__(self, *, now: datetime) -> None:
        super().__init__(fetch=lambda *_args: b"{}")
        self._now = now

    def fetch_metadata(self, identity: BilibiliIdentity) -> BilibiliMetadata:
        return BilibiliMetadata(
            identity=identity,
            cid=71009988,
            title="B站工程对照：本地与云端路由一致性评估",
            uploader_id="998877",
            uploader_name="评测对照频道 B",
            published_at=self._now - timedelta(hours=6),
            duration=980.0,
            acquired_at=self._now,
        )

    def fetch_caption(self, metadata: BilibiliMetadata) -> CaptionAcquisition:
        raw = json.dumps(
            {
                "body": [
                    {
                        "from": 0.0,
                        "to": 14.0,
                        "content": "B站对照指出所有异步写操作前都要先完成确定性事务落盘。",
                    },
                    {
                        "from": 14.0,
                        "to": 30.0,
                        "content": "不能在未落盘文本范围之前直接返回摘要结论。",
                    },
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        return CaptionAcquisition(
            status="READY",
            transcript=parse_captions(raw, language="zh-Hans", duration=metadata.duration),
            subtitle_id="3001",
            language_name="中文（人工校准）",
            source_url="https://aisubtitle.hdslb.com/bfs/subtitle/cross_b1.json",
        )


class _Batch3Completer:
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
        del mode, max_tokens
        if "LOCAL_TEXT_DISTILL_SCHEMA" in system_prompt:
            return (
                {
                    "headline_zh": "本地研究笔记强调 WAL 预落盘与段落级不可变范围引用",
                    "summary_zh": "记录本地文本研究规范：先固化段落偏移哈希，再结合视频时间轴做跨源对比。",
                    "score": 8.7,
                    "score_reason_zh": "包含清晰可验证工程边界。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["可审计引用", "本地知识库"],
                    "topic_cluster_zh": "AI Agent 与自动化架构",
                    "core_points": [
                        {"text_zh": "Markdown 笔记通过字符起止范围生成不可变 TEXT_RANGE 引用", "section_index": 1},
                        {"text_zh": "跨源对比要求视频时间轴与文档段落证据同时可点检", "section_index": 2},
                    ],
                    "product_opportunities_zh": ["统一视频时间轴与 Markdown 段落证据索引"],
                    "business_opportunities_zh": ["面向研究者的本地 Obsidian 工作台"],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )

        if "WEEKLY_BRIEF_SCHEMA" in system_prompt:
            return (
                {
                    "title_zh": "《本周 AI 产品与商业情报周报》",
                    "executive_summary_zh": "本周 7 天窗口聚焦确定性状态机与可追溯证据。",
                    "top_shifts_zh": [
                        {
                            "title_zh": "严格时间窗口过滤陈旧榜单",
                            "detail_zh": "仅收录近 7 天窗口内的新鲜干货。",
                            "topic_name": "AI Agent 与自动化架构",
                        }
                    ],
                    "product_opportunities_zh": ["时间窗口感知的每周情报过滤"],
                    "business_opportunities_zh": ["高时效垂直研究周刊"],
                },
                provider,
                model,
            )

        if "RESEARCH_QA_SCHEMA" in system_prompt:
            matches = re.findall(r"\[(E\d+)\]\s*(视频|本地文档)《([^》]+)》", user_prompt)
            video_refs = [ref for ref, kind, _ in matches if kind == "视频"]
            doc_refs = [ref for ref, kind, _ in matches if kind == "本地文档"]
            picked: list[str] = []
            if video_refs:
                picked.append(video_refs[0])
            if doc_refs:
                picked.append(doc_refs[0])
            if not picked and matches:
                picked = [matches[0][0]]
            tags = "、".join(f"[{r}]" for r in picked)
            return (
                {
                    "answerable": bool(picked),
                    "answer_zh": (
                        f"综合可核验视频时间轴与本地文档段落（{tags}），两者均支持确定性状态落盘与可回溯原文引用。"
                    ),
                    "key_takeaways_zh": [
                        "视频通过 TIME_RANGE 定位，本地 Markdown 通过 TEXT_RANGE 段落偏移定位",
                    ],
                    "action_items_zh": [
                        "在 Obsidian 笔记中同时保留视频时间戳与文档段落位置",
                    ],
                    "citations": [
                        {"ref": ref, "note_zh": f"来自候选 {ref} 的核验依据"}
                        for ref in picked
                    ],
                },
                provider,
                model,
            )

        score = 8.5
        if "Old Legacy Video" in user_prompt:
            score = 9.8
        elif "Fresh Weekly Video" in user_prompt:
            score = 8.2
        return (
            {
                "headline_zh": "测试视频洞察摘要",
                "summary_zh": "用于验证时间窗口与跨来源引用的高分摘要。",
                "score": score,
                "score_reason_zh": "清晰可测。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["AI Agent", "可靠性"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [{"text_zh": "核心确定性状态机论点", "cue_window_index": 0}],
            },
            provider,
            model,
        )


def _seed_timed_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    source_id: str,
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str,
    cues: tuple[TimedTranscriptCueWrite, ...],
    now: datetime,
    published_at: datetime | None = None,
    create_extractive_summary: bool = True,
) -> list[str]:
    pub = published_at or (now - timedelta(hours=2))
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            description=f"Summary of {title}",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=pub,
            duration_seconds=1500,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=now,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=now,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=now,
    )
    with repo._connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO source_video_links (source_id, video_id, discovered_at) VALUES (?, ?, ?)",
            (source_id, video_id, now.strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
    canonical_text = "\n".join(c.text for c in cues).encode("utf-8")
    rel = f"transcripts/canonical/{video_id}.txt"
    write_managed(data_root, rel, canonical_text)
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
        now=now,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id, canonical_artifact_id=art_id, cues=cues
    )
    repo.create_timed_transcript(timed, now=now)
    created_ev_ids: list[str] = []
    for idx, cue in enumerate(cues):
        ev_id = build_evidence_id(
            video_id=video_id,
            artifact_id=art_id,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
        )
        ev = EvidenceWrite(
            evidence_id=ev_id,
            video_id=video_id,
            artifact_id=art_id,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
            language="en",
            availability=EvidenceAvailability.AVAILABLE,
        )
        repo.create_evidence_with_text_binding(
            ev,
            EvidenceTextBindingWrite.from_timed_transcript(
                evidence=ev,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=idx,
                end_cue_index=idx + 1,
                excerpt=cue.text,
            ),
            now=now,
        )
        created_ev_ids.append(ev_id)
    if create_extractive_summary:
        ExtractiveSummaryService(repo, data_root).create(video_id, now=now)
    return created_ev_ids


def _seed_fast_timed_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    source_id: str,
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str,
    cues: tuple[TimedTranscriptCueWrite, ...],
    now: datetime,
    published_at: datetime | None = None,
) -> list[str]:
    return _seed_timed_video(
        repo,
        data_root,
        source_id=source_id,
        video_id=video_id,
        channel_id=channel_id,
        channel_name=channel_name,
        title=title,
        cues=cues,
        now=now,
        published_at=published_at,
        create_extractive_summary=False,
    )


def _build_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe", lambda *args: "MODEL_UNAVAILABLE"
    )
    project_root = (tmp_path / "owner").resolve()
    for name in ("data", "logs", "templates", "vault"):
        (project_root / name).mkdir(parents=True, exist_ok=True)
    values = load_settings(REPO_ROOT / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    clock = [NOW]
    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=project_root / "state.sqlite3",
        credential_store=_MemorySecret(),
        bigmodel_credential_store=_MemorySecret(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
        now=lambda: clock[0],
    )
    source = composition.product.add_source(
        url="https://www.youtube.com/channel/UC3333333333333333333333",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    completer = _Batch3Completer()
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=_MemorySecret(),
        llm_completer=completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: clock[0],
    )
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    return {
        "clock": clock,
        "data_root": project_root / "data",
        "repo": composition.repository,
        "source": source,
        "hub": hub,
        "fast_app": fast_app,
    }


def test_cross_source_video_and_local_markdown_qa_with_text_range_citations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: FastReadApiApplication = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]

    _seed_timed_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidCrossYT1",
        channel_id="UC3333333333333333333333",
        channel_name="Alpha Engineering",
        title="Deterministic State Machines in Production",
        cues=(
            TimedTranscriptCueWrite(
                start_ms=10000,
                end_ms=26000,
                text="Durable SQLite state checkpoints prevent split-brain tool execution.",
            ),
        ),
        now=NOW - timedelta(hours=3),
    )

    bili_provider = BilibiliContentProvider(
        repo,
        env["data_root"],
        adapter=_CrossSourceBiliAdapter(now=NOW - timedelta(hours=2)),
        now=lambda: NOW - timedelta(hours=2),
    )
    bili_res = bili_provider.import_input("https://www.bilibili.com/video/BV1Crs3Mdxk1/")

    md_bytes = (
        "# Local Architecture Notes\n"
        "Paragraph 2: Every Markdown note produces TEXT_RANGE evidence before summarization.\n"
        "Paragraph 3: Cross-source comparison binds both TIME_RANGE video cues and TEXT_RANGE offsets.\n"
    ).encode("utf-8")
    imp_status, imp_payload = fast_app.handle(
        "POST",
        "/api/v1/local/imports?filename=field-notes.md",
        md_bytes,
    )
    assert imp_status == HTTPStatus.CREATED
    md_id = str(imp_payload["import"]["content_id"])

    assert fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidCrossYT1/distill", b"{}")[0] == HTTPStatus.OK
    assert fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{bili_res.content_id}/distill", b"{}")[0] == HTTPStatus.OK
    md_dist_code, md_dist_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{md_id}/distill", b"{}"
    )
    assert md_dist_code == HTTPStatus.OK
    assert "[00:00]" not in str(md_dist_body["ai_brief"]["obsidian_markdown"])

    # Verify core_points on local Markdown now bind real TEXT_RANGE evidence_ids (no fake start_seconds)
    md_brief = env["hub"].get_video_brief(md_id)
    assert md_brief is not None
    assert md_brief["core_points"]
    assert all(pt.get("evidence_ids") for pt in md_brief["core_points"])
    assert all(pt.get("start_seconds") is None for pt in md_brief["core_points"])

    # Verify scope_options exposes local Markdown alongside timed videos
    list_code, list_body = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert list_code == HTTPStatus.OK
    scope_vids = {v["video_id"]: v for v in list_body["scope_options"]["videos"]}
    assert md_id in scope_vids
    assert scope_vids[md_id]["locator_kind"] == "TEXT_RANGE"
    assert scope_vids["vidCrossYT1"]["locator_kind"] == "TIME_RANGE"

    # Ask one cross-source question comparing YouTube + Markdown explicitly
    ask_code, ask_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "Compare durable state checkpoints and TEXT_RANGE offsets across the video and local Markdown note.",
                "video_ids": ["vidCrossYT1", md_id],
            }
        ).encode("utf-8"),
    )
    assert ask_code == HTTPStatus.OK
    session = ask_body["session"]
    assert session["refused"] is False
    assert session["covered_source_count"] == 2
    assert {s["video_id"] for s in session["covered_sources"]} == {"vidCrossYT1", md_id}

    cites_by_vid = {c["video_id"]: c for c in session["citations"]}
    assert set(cites_by_vid.keys()) == {"vidCrossYT1", md_id}

    md_cite = cites_by_vid[md_id]
    assert md_cite["locator_type"] == "TEXT_RANGE"
    assert md_cite["start_ms"] is None
    assert md_cite["paragraph_index"] >= 1
    assert md_cite["start_offset"] is not None
    assert md_cite["end_offset"] > md_cite["start_offset"]
    assert md_cite["timestamp_label"].startswith("P")
    assert "00:00" not in md_cite["timestamp_label"]
    assert "`00:00`" not in session["obsidian_markdown"]
    assert "## 原文证据链（时间戳 / 段落定位）" in session["obsidian_markdown"]

    yt_cite = cites_by_vid["vidCrossYT1"]
    assert yt_cite["locator_type"] == "TIME_RANGE"
    assert yt_cite["start_ms"] is not None

    # Every cited evidence_id must resolve in core /api/v1/videos/<id>/evidence
    for cid, cite in cites_by_vid.items():
        ev_code, ev_body = fast_app.handle("GET", f"/api/v1/videos/{cid}/evidence")
        assert ev_code == HTTPStatus.OK
        available_ids = {item["evidence_id"] for item in ev_body["evidence"]}
        assert cite["evidence_id"] in available_ids

    # Persisted listing must preserve covered_sources cleanly
    hist_code, hist_body = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert hist_code == HTTPStatus.OK
    assert hist_body["sessions"][0]["covered_source_count"] == 2
    assert {s["video_id"] for s in hist_body["sessions"][0]["covered_sources"]} == {"vidCrossYT1", md_id}


def test_weekly_brief_enforces_7_day_window_and_handles_empty_window_honestly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: FastReadApiApplication = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    clock: list[datetime] = env["clock"]

    # Seed older high-score (9.8) video published 35 days ago
    _seed_timed_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidOldHigh98",
        channel_id="UC3333333333333333333333",
        channel_name="Archive Channel",
        title="Old Legacy Video From Last Month",
        cues=(TimedTranscriptCueWrite(start_ms=0, end_ms=9000, text="Legacy architecture deep dive."),),
        now=NOW - timedelta(hours=1),
        published_at=NOW - timedelta(days=35),
    )
    # Seed current-week (8.2) video published 2 days ago
    _seed_timed_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidFreshWk82",
        channel_id="UC3333333333333333333333",
        channel_name="Weekly Channel",
        title="Fresh Weekly Video Within Window",
        cues=(TimedTranscriptCueWrite(start_ms=0, end_ms=9000, text="Fresh agent state verification patterns."),),
        now=NOW,
        published_at=NOW - timedelta(days=2),
    )

    assert fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidOldHigh98/distill", b"{}")[0] == HTTPStatus.OK
    assert fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidFreshWk82/distill", b"{}")[0] == HTTPStatus.OK

    wb_code, wb_body = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    assert wb_code == HTTPStatus.OK
    brief = wb_body["weekly_brief"]
    pick_ids = [p["video_id"] for p in brief["must_watch_picks"]]
    assert pick_ids == ["vidFreshWk82"]
    assert "vidOldHigh98" not in pick_ids
    assert brief["window"]["in_window_count"] == 1
    assert brief["window"]["excluded_older_count"] == 1
    assert brief["window"]["window_empty"] is False

    _, fetched = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    assert fetched["weekly_brief"]["window"]["excluded_older_count"] == 1

    # Advance 20 days -> all existing items are older than 7-day rolling window
    clock[0] = NOW + timedelta(days=20)
    empty_code, empty_body = fast_app.handle(
        "POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}"
    )
    assert empty_code == HTTPStatus.OK
    empty_brief = empty_body["weekly_brief"]
    assert empty_brief["must_watch_picks"] == []
    assert empty_brief["window"]["window_empty"] is True
    assert empty_brief["window"]["in_window_count"] == 0
    assert empty_brief["window"]["excluded_older_count"] == 2
    assert empty_brief["provider"] == "local-rule"
    assert "暂无新" in empty_brief["executive_summary_zh"]


def test_250_item_library_retrieves_buried_fact_beyond_old_200_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: FastReadApiApplication = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]

    buried_idx = 234  # 235th newest item — completely invisible under the old 200-item cap
    buried_id = f"vidScale{buried_idx:03d}"

    for idx in range(250):
        vid = f"vidScale{idx:03d}"
        item_time = NOW - timedelta(hours=idx)
        text = (
            "ZetaQuorum uses a 47ms deterministic WAL barrier before flushing sidecar commits."
            if idx == buried_idx
            else f"General engineering episode {idx} covering workflow logging and routine retries."
        )
        _seed_timed_video(
            repo,
            env["data_root"],
            source_id=env["source"].source_id,
            video_id=vid,
            channel_id="UC3333333333333333333333",
            channel_name="Scale Bench Channel",
            title=f"Scale Corpus Entry {idx:03d}",
            cues=(TimedTranscriptCueWrite(start_ms=12000, end_ms=28000, text=text),),
            now=item_time,
            published_at=item_time,
        )

    t0 = time.perf_counter()
    ask_code, ask_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "What does ZetaQuorum 47ms WAL barrier do?"}).encode("utf-8"),
    )
    elapsed = time.perf_counter() - t0

    assert ask_code == HTTPStatus.OK
    session = ask_body["session"]
    assert session["refused"] is False
    assert session["scope"]["matched_video_count"] == 250
    cited_ids = {c["video_id"] for c in session["citations"]}
    assert buried_id in cited_ids
    buried_cite = next(c for c in session["citations"] if c["video_id"] == buried_id)
    assert "ZetaQuorum" in buried_cite["excerpt"]
    ev_code, ev_body = fast_app.handle("GET", f"/api/v1/videos/{buried_id}/evidence")
    assert ev_code == HTTPStatus.OK
    assert buried_cite["evidence_id"] in {item["evidence_id"] for item in ev_body["evidence"]}
    assert elapsed < 10.0

    # Explicit video_ids selection must also locate buried entries directly
    exp_code, exp_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "Summarize the WAL barrier mechanism.",
                "video_ids": [buried_id],
            }
        ).encode("utf-8"),
    )
    assert exp_code == HTTPStatus.OK
    assert exp_body["session"]["refused"] is False
    assert [c["video_id"] for c in exp_body["session"]["citations"]] == [buried_id]


def test_600_item_library_pagination_buried_retrieval_and_sqlite_hot_backups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: FastReadApiApplication = env["fast_app"]
    hub = env["hub"]
    repo: SQLiteStateRepository = env["repo"]

    buried_idx = 560  # Past both 200 (default page) and old 300/500 caps
    buried_id = f"vidBig{buried_idx:03d}"

    t_seed_start = time.perf_counter()
    for idx in range(600):
        vid = f"vidBig{idx:03d}"
        item_time = NOW - timedelta(hours=idx)
        is_buried = idx == buried_idx
        text = (
            "KestrelVault uses a 91ms deterministic WAL barrier before committing archive checkpoints."
            if is_buried
            else f"Routine engineering broadcast {idx} covering telemetry queues and batch compaction."
        )
        seeder = _seed_timed_video if is_buried else _seed_fast_timed_video
        seeder(
            repo,
            env["data_root"],
            source_id=env["source"].source_id,
            video_id=vid,
            channel_id="UC3333333333333333333333",
            channel_name="Large Corpus Channel",
            title=f"Big Scale Entry {idx:03d}",
            cues=(TimedTranscriptCueWrite(start_ms=14000, end_ms=30000, text=text),),
            now=item_time,
            published_at=item_time,
        )
    seed_elapsed = time.perf_counter() - t_seed_start

    distill_code, _ = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{buried_id}/distill", b"{}"
    )
    assert distill_code == HTTPStatus.OK

    # 1. Backward-compatible unpaginated GET /api/v1/videos
    t_unpaged = time.perf_counter()
    unpaged_code, unpaged_body = fast_app.handle("GET", "/api/v1/videos")
    unpaged_ms = (time.perf_counter() - t_unpaged) * 1000.0
    assert unpaged_code == HTTPStatus.OK
    assert set(unpaged_body.keys()) == {"videos"}
    assert len(unpaged_body["videos"]) == 200
    assert buried_id not in {v["video_id"] for v in unpaged_body["videos"]}

    # 2. Paginated GET /api/v1/videos?limit=200&offset={0,200,400} covers all 600 items
    seen_ids: set[str] = set()
    page3_ids: set[str] = set()
    page_timings_ms: list[float] = []
    for page_idx, (offset, expected_has_more) in enumerate(
        ((0, True), (200, True), (400, False))
    ):
        t_page = time.perf_counter()
        p_code, p_body = fast_app.handle(
            "GET", f"/api/v1/videos?limit=200&offset={offset}"
        )
        page_timings_ms.append((time.perf_counter() - t_page) * 1000.0)
        assert p_code == HTTPStatus.OK
        assert p_body["pagination"] == {
            "limit": 200,
            "offset": offset,
            "total_count": 600,
            "returned_count": 200,
            "has_more": expected_has_more,
        }
        batch_ids = [v["video_id"] for v in p_body["videos"]]
        assert len(batch_ids) == 200
        seen_ids.update(batch_ids)
        if page_idx == 2:
            page3_ids.update(batch_ids)

    assert len(seen_ids) == 600
    assert seen_ids == {f"vidBig{idx:03d}" for idx in range(600)}
    assert buried_id in page3_ids

    # 3. Pagination validation rejects out-of-range limit and unknown params with 400 INVALID_QUERY
    for bad_route in ("/api/v1/videos?limit=999", "/api/v1/videos?unknown=1"):
        with pytest.raises(ApiError) as err_info:
            fast_app.handle("GET", bad_route)
        assert err_info.value.status == HTTPStatus.BAD_REQUEST
        assert err_info.value.code == "INVALID_QUERY"

    # 4. Cross-library research Q&A retrieves item #561 across all 600 items
    t_ask = time.perf_counter()
    ask_code, ask_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "What does KestrelVault 91ms deterministic WAL barrier do?"}).encode(
            "utf-8"
        ),
    )
    ask_elapsed = time.perf_counter() - t_ask
    assert ask_code == HTTPStatus.OK
    session = ask_body["session"]
    assert session["refused"] is False
    assert session["scope"]["matched_video_count"] == 600
    cited_ids = {c["video_id"] for c in session["citations"]}
    assert buried_id in cited_ids
    buried_cite = next(c for c in session["citations"] if c["video_id"] == buried_id)
    assert "KestrelVault" in buried_cite["excerpt"]
    assert ask_elapsed < 15.0

    # 5. Obsidian bundle JSON & ZIP include item #561 when scope=all
    bundle_code, bundle_body = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=all"
    )
    assert bundle_code == HTTPStatus.OK
    assert int(bundle_body["counts"]["videos"]) >= 1

    zip_dl = fast_app.backup_download("/api/v1/workspace-ai/obsidian-bundle.zip?scope=all")
    assert zip_dl is not None
    dl_status, _, dl_payload = zip_dl
    assert dl_status == HTTPStatus.OK
    raw_zip = (
        dl_payload
        if isinstance(dl_payload, bytes)
        else Path(dl_payload).read_bytes()
    )
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        zip_texts = [
            zf.read(name).decode("utf-8", errors="replace")
            for name in zf.namelist()
            if name.endswith(".md")
        ]
    assert any(buried_id in text or "Big Scale Entry 560" in text for text in zip_texts)

    # 6. Core SQLite backup + Workspace AI zero-secret hot SQLite snapshot
    project_root = env["data_root"].parent
    t_core_bak = time.perf_counter()
    core_backup = BackupRestoreService(
        database=project_root / "state.sqlite3",
        data_root=env["data_root"],
        control_root=project_root / "control",
    ).create_backup()
    core_bak_ms = (time.perf_counter() - t_core_bak) * 1000.0
    assert core_backup.preview["content_count"] == 600
    assert core_backup.size_bytes > 0

    t_hub_snap = time.perf_counter()
    hot_snap = hub.create_sqlite_hot_snapshot()
    hub_snap_ms = (time.perf_counter() - t_hub_snap) * 1000.0
    assert hot_snap["integrity_ok"] is True
    assert hot_snap["zero_secret"] is True
    snap_path = Path(str(hot_snap["path"]))
    assert snap_path.is_file()
    assert snap_path.name == "hub-snapshot.sqlite3"

    ro_conn = sqlite3.connect(f"file:{snap_path}?mode=ro", uri=True)
    try:
        integrity_row = ro_conn.execute("PRAGMA integrity_check").fetchone()
        assert integrity_row == ("ok",)
        brief_count_row = ro_conn.execute(
            "SELECT COUNT(*) FROM video_ai_briefs WHERE video_id = ?",
            (buried_id,),
        ).fetchone()
        assert brief_count_row == (1,)
        cfg_cols = [
            str(row[1]).lower()
            for row in ro_conn.execute("PRAGMA table_info(engine_config)").fetchall()
        ]
        assert cfg_cols
        assert not any(
            secret_tok in col
            for col in cfg_cols
            for secret_tok in ("key", "secret", "token", "password")
        )
    finally:
        ro_conn.close()

    print(
        f"\n[BL-008 600-item Benchmark] seed={seed_elapsed:.2f}s "
        f"unpaged_200={unpaged_ms:.1f}ms pages_ms={[round(x, 1) for x in page_timings_ms]} "
        f"research_ask={ask_elapsed:.2f}s core_backup={core_bak_ms:.1f}ms "
        f"hub_hot_snap={hub_snap_ms:.1f}ms ({hot_snap['size_bytes']}B)"
    )
    env.clear()
    del fast_app, hub, repo, zip_texts, raw_zip
    gc.collect()
