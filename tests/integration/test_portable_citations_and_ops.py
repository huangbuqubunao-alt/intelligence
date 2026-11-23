"""Tests for portable deep-linked citations, Markdown provenance, and daily ops report generation."""

from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

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
from youtube_intel.workspace_intelligence_hub import (
    WorkspaceIntelligenceHub,
    _build_citation_deep_url,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 23, 6, 0, tzinfo=UTC)


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


class _PortableBiliAdapter(BilibiliAdapter):
    def __init__(self, *, now: datetime) -> None:
        super().__init__(fetch=lambda *_args: b"{}")
        self._now = now

    def fetch_metadata(self, identity: BilibiliIdentity) -> BilibiliMetadata:
        return BilibiliMetadata(
            identity=identity,
            cid=71005544,
            title="B站可携带深链引用实战说明",
            uploader_id="889911",
            uploader_name="研究工程频道",
            published_at=self._now - timedelta(hours=3),
            duration=860.0,
            acquired_at=self._now,
        )

    def fetch_caption(self, metadata: BilibiliMetadata) -> CaptionAcquisition:
        raw = json.dumps(
            {
                "body": [
                    {
                        "from": 65.0,
                        "to": 82.0,
                        "content": "导出到 Obsidian 时每条引用都应附带可直达原片对应秒数的 URL。",
                    },
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        return CaptionAcquisition(
            status="READY",
            transcript=parse_captions(raw, language="zh-Hans", duration=metadata.duration),
            subtitle_id="4001",
            language_name="中文（精选字幕）",
            source_url="https://aisubtitle.hdslb.com/bfs/subtitle/portable_b1.json",
        )


class _PortableCompleter:
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
                    "headline_zh": "本地笔记使用段落与字符区间定位，禁止伪造秒数链接",
                    "summary_zh": "确认本地文本不输出任何视频时间戳链接。",
                    "score": 8.4,
                    "score_reason_zh": "边界清晰。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["可携带引用"],
                    "topic_cluster_zh": "AI Agent 与自动化架构",
                    "core_points": [
                        {"text_zh": "文档引用使用 TEXT_RANGE 字符范围", "section_index": 1},
                    ],
                },
                provider,
                model,
            )

        if "RESEARCH_QA_SCHEMA" in system_prompt:
            matches = re.findall(r"\[(E\d+)\]\s*(视频|本地文档)《", user_prompt)
            refs = [ref for ref, _ in matches[:3]]
            tags = "、".join(f"[{r}]" for r in refs)
            return (
                {
                    "answerable": bool(refs),
                    "answer_zh": f"导出研究笔记保留可点击时间戳深链与本地段落位置（{tags}）。",
                    "key_takeaways_zh": ["导出到 Obsidian 后点击时间标签可直接回到原视频位置"],
                    "action_items_zh": ["复制或下载导出笔记检验跳转链接"],
                    "citations": [{"ref": r, "note_zh": f"核验引用 {r}"} for r in refs],
                },
                provider,
                model,
            )

        return (
            {
                "headline_zh": "YouTube 视频单条洞察导出保留深链时间戳",
                "summary_zh": "验证单视频与跨源问答导出均为外部可用状态。",
                "score": 8.9,
                "score_reason_zh": "可核验跳转。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["可携带引用"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [{"text_zh": "于第 75 秒点出关键架构约束", "cue_window_index": 0}],
            },
            provider,
            model,
        )


def _seed_yt(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    source_id: str,
    video_id: str,
    title: str,
    now: datetime,
) -> None:
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC4444444444444444444444",
            channel_name="DeepLink Lab",
            title=title,
            description="Test description",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=now - timedelta(hours=4),
            duration_seconds=900,
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
    cues = (
        TimedTranscriptCueWrite(
            start_ms=75000,
            end_ms=92000,
            text="Portable citations encode verified start offsets in HTTPS links.",
        ),
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
    ev = EvidenceWrite(
        evidence_id=build_evidence_id(
            video_id=video_id,
            artifact_id=art_id,
            start_ms=75000,
            end_ms=92000,
            lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
            role=EvidenceRole.PRIMARY_ORIGINAL,
        ),
        video_id=video_id,
        artifact_id=art_id,
        start_ms=75000,
        end_ms=92000,
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
            start_cue_index=0,
            end_cue_index=1,
            excerpt=cues[0].text,
        ),
        now=now,
    )
    ExtractiveSummaryService(repo, data_root).create(video_id, now=now)


def test_build_citation_deep_url_builds_safe_links_and_rejects_unsafe_schemes() -> None:
    assert (
        _build_citation_deep_url(
            "https://www.youtube.com/watch?v=abc123XYZ00&t=9s",
            provider="YOUTUBE",
            start_seconds=75.9,
        )
        == "https://www.youtube.com/watch?v=abc123XYZ00&t=75s"
    )
    assert (
        _build_citation_deep_url(
            "https://youtu.be/abc123XYZ00",
            provider="",
            start_seconds=12,
        )
        == "https://youtu.be/abc123XYZ00?t=12s"
    )
    assert (
        _build_citation_deep_url(
            "https://www.bilibili.com/video/BV1Prt4Mdxk1/",
            provider="BILIBILI",
            start_seconds=65.0,
        )
        == "https://www.bilibili.com/video/BV1Prt4Mdxk1/?t=65"
    )
    assert (
        _build_citation_deep_url(
            "javascript:alert(1)",
            provider="YOUTUBE",
            start_seconds=10,
        )
        is None
    )
    assert (
        _build_citation_deep_url(
            "http://www.youtube.com/watch?v=abc123XYZ00",
            provider="YOUTUBE",
            start_seconds=10,
        )
        is None
    )
    assert (
        _build_citation_deep_url(
            "https://www.youtube.com/watch?v=abc123XYZ00",
            provider="LOCAL",
            start_seconds=None,
        )
        is None
    )


def test_portable_deep_linked_citations_in_distill_and_cross_source_qa_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=project_root / "state.sqlite3",
        credential_store=_MemorySecret(),
        bigmodel_credential_store=_MemorySecret(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        probe_local_runtime=False,
        now=lambda: NOW,
    )
    source = composition.product.add_source(
        url="https://www.youtube.com/channel/UC4444444444444444444444",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=_MemorySecret(),
        llm_completer=_PortableCompleter(),
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: NOW,
    )
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)

    _seed_yt(
        composition.repository,
        project_root / "data",
        source_id=source.source_id,
        video_id="vidPortYT01",
        title="Portable Evidence Architecture",
        now=NOW,
    )
    bili_provider = BilibiliContentProvider(
        composition.repository,
        project_root / "data",
        adapter=_PortableBiliAdapter(now=NOW),
        now=lambda: NOW,
    )
    bili_res = bili_provider.import_input("https://www.bilibili.com/video/BV1Prt4Mdxk1/")
    _, md_imp = fast_app.handle(
        "POST",
        "/api/v1/local/imports?filename=portable-notes.md",
        b"# Notes\nParagraph 2: Keep character range citations clean without fake timestamps.\n",
    )
    md_id = str(md_imp["import"]["content_id"])

    _, yt_dist = fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidPortYT01/distill", b"{}")
    _, bi_dist = fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{bili_res.content_id}/distill", b"{}")
    _, md_dist = fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{md_id}/distill", b"{}")

    assert (
        "[01:15 ↗](https://www.youtube.com/watch?v=vidPortYT01&t=75s)"
        in str(yt_dist["ai_brief"]["obsidian_markdown"])
    )
    assert (
        "[01:05 ↗](https://www.bilibili.com/video/BV1Prt4Mdxk1?t=65)"
        in str(bi_dist["ai_brief"]["obsidian_markdown"])
    ) or (
        "https://www.bilibili.com/video/BV1Prt4Mdxk1"
        in str(bi_dist["ai_brief"]["obsidian_markdown"])
        and "t=65" in str(bi_dist["ai_brief"]["obsidian_markdown"])
    )
    assert "[00:00]" not in str(md_dist["ai_brief"]["obsidian_markdown"])
    assert "http" not in str(md_dist["ai_brief"]["obsidian_markdown"]).split("---", 2)[-1]

    ask_code, ask_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "Compare YouTube timestamps and Markdown TEXT_RANGE portable citations.",
                "video_ids": ["vidPortYT01", md_id],
            }
        ).encode("utf-8"),
    )
    assert ask_code == HTTPStatus.OK
    session = ask_body["session"]
    cites_by_vid = {c["video_id"]: c for c in session["citations"]}
    assert cites_by_vid["vidPortYT01"]["citation_url"] == "https://www.youtube.com/watch?v=vidPortYT01&t=75s"
    assert cites_by_vid[md_id]["citation_url"] is None

    qa_md = str(session["obsidian_markdown"])
    assert "核验覆盖材料（2 份）" in qa_md
    assert "https://www.youtube.com/watch?v=vidPortYT01&t=75s" in qa_md
    assert "`ev:" in qa_md
    assert "`00:00`" not in qa_md


def test_daily_ops_report_generator_is_readonly_deterministic_and_non_clobbering(
    tmp_path: Path,
) -> None:
    script_path = REPO_ROOT / "scripts" / "generate_daily_ops_report.py"
    spec = importlib.util.spec_from_file_location("generate_daily_ops_report", script_path)
    assert spec is not None and spec.loader is not None
    mod: Any = importlib.util.module_from_spec(spec)
    sys.modules["generate_daily_ops_report"] = mod
    spec.loader.exec_module(mod)

    hub_db = tmp_path / "hub.sqlite3"
    conn = sqlite3.connect(hub_db)
    with conn:
        conn.execute("CREATE TABLE video_ai_briefs (video_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE research_qa_sessions (session_id TEXT PRIMARY KEY, scope_json TEXT)")
        conn.execute("CREATE TABLE weekly_ai_briefs (brief_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO video_ai_briefs VALUES ('v1'), ('v2')")
        conn.execute(
            "INSERT INTO research_qa_sessions VALUES ('s1', '{\"refused\": false}'), ('s2', '{\"refused\": true}')"
        )
        conn.execute("INSERT INTO weekly_ai_briefs VALUES ('w1')")
    conn.close()

    out_file = tmp_path / "reports" / "2026-11-23.md"
    summary = mod.generate_report(
        repo_root=REPO_ROOT,
        report_date="2026-11-23",
        hub_db=hub_db,
        output_path=out_file,
        overwrite=False,
    )
    assert summary.written is True
    assert summary.skipped_existing is False
    assert summary.hub_usage.distilled_briefs == 2
    assert summary.hub_usage.qa_sessions == 2
    assert summary.hub_usage.qa_grounded == 1
    assert summary.hub_usage.qa_refused == 1
    assert summary.hub_usage.weekly_briefs == 1

    rendered = out_file.read_text(encoding="utf-8")
    for heading in (
        "# 产品自主运营日报｜2026-11-23",
        "### 1. 产品整体状态",
        "### 2. 今日完成",
        "### 3. 市场与竞品新情报",
        "### 4. 用户及产品数据",
        "### 5. 今日关键决策",
        "### 6. 风险及阻塞",
        "### 7. 需要创始人决定的事项",
        "### 8. 明日计划",
        "### 9. 本周目标进度",
    ):
        assert heading in rendered

    # Idempotency check: second run without overwrite=True preserves custom edits
    out_file.write_text("# custom manual report\n", encoding="utf-8")
    second = mod.generate_report(
        repo_root=REPO_ROOT,
        report_date="2026-11-23",
        hub_db=None,
        output_path=out_file,
        overwrite=False,
    )
    assert second.written is False
    assert second.skipped_existing is True
    assert second.hub_usage.available is False
    assert out_file.read_text(encoding="utf-8") == "# custom manual report\n"


def test_daily_ops_report_generator_cpo_template_enforces_internal_stage_sections(
    tmp_path: Path,
) -> None:
    script_path = REPO_ROOT / "scripts" / "generate_daily_ops_report.py"
    spec = importlib.util.spec_from_file_location("generate_daily_ops_report_cpo", script_path)
    assert spec is not None and spec.loader is not None
    mod: Any = importlib.util.module_from_spec(spec)
    sys.modules["generate_daily_ops_report_cpo"] = mod
    spec.loader.exec_module(mod)

    out_file = tmp_path / "reports" / "cpo-2026-11-23.md"
    summary = mod.generate_report(
        repo_root=REPO_ROOT,
        report_date="2026-11-23",
        hub_db=None,
        output_path=out_file,
        overwrite=False,
        template="cpo",
    )
    assert summary.written is True
    rendered = out_file.read_text(encoding="utf-8")
    for heading in (
        "# AI 产品负责人日报｜2026-11-23",
        "## 1. 产品整体状态",
        "## 2. 今日工作完成情况",
        "## 3. 市场与竞品新情报",
        "## 4. 产品与测试数据",
        "## 5. 测试与质量情况",
        "## 6. 今日关键决策",
        "## 7. 风险与阻塞",
        "## 8. 需要你决策的事项",
        "## 9. 明日计划",
    ):
        assert heading in rendered
    assert "当前不可评估" in rendered
    assert "内部自主迭代与产品完善阶段" in rendered
    assert "/Users/" not in rendered
