"""32-case labeled evaluation benchmark for strict grounding, reliable refusal & conflict attribution."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.demo_showcase import prepare_demo_showcase
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    VideoMetadata,
)
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.local_content import LocalContentProvider
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


class _EvalBilibiliAdapter(BilibiliAdapter):
    def __init__(self, *, now: datetime) -> None:
        super().__init__(fetch=lambda *_args: b"{}")
        self._now = now

    def fetch_metadata(self, identity: BilibiliIdentity) -> BilibiliMetadata:
        return BilibiliMetadata(
            identity=identity,
            cid=71002341,
            title="小型本地模型在结构化打分场景的表现评测（公开对照材料）",
            uploader_id="991234",
            uploader_name="评测对照频道 B",
            published_at=self._now - timedelta(hours=5),
            duration=920.0,
            acquired_at=self._now,
        )

    def fetch_caption(self, metadata: BilibiliMetadata) -> CaptionAcquisition:
        raw = json.dumps(
            {
                "body": [
                    {
                        "from": 0.0,
                        "to": 14.0,
                        "content": "观点对照：对于单条视频初筛和 Shorts 折叠打分，本地 8B 量化模型已经足够稳定且零边际成本。",
                    },
                    {
                        "from": 14.0,
                        "to": 28.0,
                        "content": "但当跨越多于五篇异构材料做相反论点对比时，低参数本地模型往往漏掉条件前置假设。",
                    },
                    {
                        "from": 28.0,
                        "to": 42.0,
                        "content": "本地资料还强调把所有事实引用和起止毫秒时间范围预先锁定在本地 SQLite 中。",
                    },
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        return CaptionAcquisition(
            status="READY",
            transcript=parse_captions(raw, language="zh-Hans", duration=metadata.duration),
            subtitle_id="2001",
            language_name="中文（评测对照）",
            source_url="https://aisubtitle.hdslb.com/bfs/subtitle/eval_b1.json",
        )


class _EvalCompleter:
    """Controlled evaluator completer returning scenario-specific responses."""

    def __init__(self) -> None:
        self.behavior: str = "normal"

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
            if self.behavior == "bad_local_section":
                return (
                    {
                        "headline_zh": "超界文本段落测试",
                        "summary_zh": "测试超界 section_index 严禁夹逼。",
                        "score": 7.5,
                        "score_reason_zh": "测试",
                        "recommendation_tier": "WORTH_SKIMMING",
                        "content_bucket": "DEEP_DIVE",
                        "topics_zh": ["测试"],
                        "topic_cluster_zh": "AI Agent 与自动化架构",
                        "core_points": [
                            {"text_zh": "不存在的段落 42", "section_index": 42},
                            {"text_zh": "布尔值越界", "section_index": True},
                        ],
                    },
                    provider,
                    model,
                )

        if "VIDEO_DISTILL_SCHEMA" in system_prompt:
            if self.behavior == "mixed_oob_windows":
                return (
                    {
                        "headline_zh": "部分越界窗口应只保留合法窗口",
                        "summary_zh": "合法窗口 0 保留，越界 99 / -1 / 非整数剔除。",
                        "score": 8.2,
                        "score_reason_zh": "测试部分越界",
                        "recommendation_tier": "MUST_WATCH",
                        "content_bucket": "DEEP_DIVE",
                        "topics_zh": ["边界检查"],
                        "topic_cluster_zh": "AI Agent 与自动化架构",
                        "core_points": [
                            {"text_zh": "唯一合法的第 0 窗口要点", "cue_window_index": 0},
                            {"text_zh": "越界大下标 99", "cue_window_index": 99},
                            {"text_zh": "负下标 -1", "cue_window_index": -1},
                            {"text_zh": "布尔假下标", "cue_window_index": False},
                            {"text_zh": "非数字下标", "cue_window_index": "bad"},
                        ],
                    },
                    provider,
                    model,
                )
            if self.behavior == "all_oob_windows":
                return (
                    {
                        "headline_zh": "全部越界应拒绝绑定假窗口 0",
                        "summary_zh": "若全部要点下标无效，则不得回退伪造第 0 窗口证据。",
                        "score": 8.0,
                        "score_reason_zh": "全越界测试",
                        "recommendation_tier": "MUST_WATCH",
                        "content_bucket": "DEEP_DIVE",
                        "topics_zh": ["边界检查"],
                        "topic_cluster_zh": "AI Agent 与自动化架构",
                        "core_points": [
                            {"text_zh": "越界 99", "cue_window_index": 99},
                            {"text_zh": "越界 -2", "cue_window_index": -2},
                        ],
                    },
                    provider,
                    model,
                )

        if "RESEARCH_QA_SCHEMA" in system_prompt:
            refs = re.findall(r"\[(E\d+)\]\s*视频《([^》]+)》", user_prompt)
            if self.behavior == "refuse_explicit":
                return (
                    {
                        "answerable": False,
                        "refusal_reason_zh": "候选证据仅讨论 Agent 状态机与评测模型对比，未包含所问财务或医疗结论。",
                        "answer_zh": "无法从当前材料中找到依据。",
                        "key_takeaways_zh": ["应当被后端清空的未验证要点"],
                        "action_items_zh": ["应当被后端清空的行动项"],
                        "citations": [],
                    },
                    provider,
                    model,
                )
            if self.behavior == "bluff_no_citations":
                return (
                    {
                        "answerable": True,
                        "answer_zh": "据传 2026 年营收翻了三倍 [E99]。",
                        "key_takeaways_zh": ["无合法引用的伪造结论"],
                        "action_items_zh": ["伪造行动项"],
                        "citations": [{"ref": "E99", "note_zh": "不存在的引用编号"}],
                    },
                    provider,
                    model,
                )
            if self.behavior == "bluff_empty_citations":
                return (
                    {
                        "answerable": True,
                        "answer_zh": "强行编造但未给出任何引用标记的结论。",
                        "key_takeaways_zh": ["不应保留的无支撑结论"],
                        "action_items_zh": [],
                        "citations": [],
                    },
                    provider,
                    model,
                )
            if self.behavior == "conflict":
                yt_refs = [r for r, title in refs if "Alpha" in title or "Agent" in title]
                bi_refs = [r for r, title in refs if "评测" in title or "小型" in title]
                r1 = yt_refs[0] if yt_refs else refs[0][0]
                r2 = bi_refs[0] if bi_refs else refs[-1][0]
                return (
                    {
                        "answerable": True,
                        "answer_zh": (
                            f"两位作者在不同前提条件下给出对比判断：一方面材料 [{r1}] 指出生产环境下复杂工具链需要强约束状态机与云端前沿评测；"
                            f"另一方面 B 站材料 [{r2}] 指出在单条初筛与折叠降噪任务上本地 8B 量化模型已足够稳定。"
                        ),
                        "key_takeaways_zh": ["任务难度决定本机小模型与强模型的边界条件"],
                        "action_items_zh": ["先按单条初筛 vs 多篇对比拆分路由条件"],
                        "citations": [
                            {"ref": r1, "note_zh": "复杂工具编排与前沿评测观点"},
                            {"ref": r2, "note_zh": "单条初筛本地 8B 够用条件"},
                        ],
                    },
                    provider,
                    model,
                )

            selected = [r for r, _ in refs[:2]]
            tags = "、".join(f"[{r}]" for r in selected)
            return (
                {
                    "answerable": bool(selected),
                    "answer_zh": f"根据已验证原话片段（{tags}），核心判断已直接绑定到可点击时间轴。",
                    "key_takeaways_zh": ["全部陈述均有对应原话定位支持"],
                    "action_items_zh": ["点击引用卡片跳转原片时间段核验"],
                    "citations": [{"ref": r, "note_zh": f"对应片段 {r}"} for r in selected],
                },
                provider,
                model,
            )

        return (
            {
                "headline_zh": "测试标准摘要",
                "summary_zh": "测试标准摘要正文。",
                "score": 8.5,
                "score_reason_zh": "标准测试摘要",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["Agent", "Eval"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [{"text_zh": "核心论点一", "cue_window_index": 0}],
            },
            provider,
            model,
        )


def _seed_yt_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    video_id: str,
    title: str,
    cues: tuple[TimedTranscriptCueWrite, ...],
    offset_hours: int,
    duration_seconds: int = 1200,
) -> None:
    t = NOW - timedelta(hours=offset_hours)
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id="UC_EVAL_YT_111111111111",
            channel_name="Eval Channel A",
            title=title,
            description=f"Eval corpus video {title}",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=t,
            duration_seconds=duration_seconds,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=t,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=t,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=t,
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
        now=t,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id, canonical_artifact_id=art_id, cues=cues
    )
    repo.create_timed_transcript(timed, now=t)
    for idx, cue in enumerate(cues):
        ev = EvidenceWrite(
            evidence_id=build_evidence_id(
                video_id=video_id,
                artifact_id=art_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
            ),
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
            now=t,
        )
    ExtractiveSummaryService(repo, data_root).create(video_id, now=t)


def test_20_case_grounding_refusal_and_anchor_bounds_benchmark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_models", lambda *args: {"models": []}
    )
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_runtime_version", lambda *args: {}
    )
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe",
        lambda *args: "MODEL_UNAVAILABLE",
    )

    project_root = (tmp_path / "eval_root").resolve()
    for sub in ("data", "logs", "templates", "vault"):
        (project_root / sub).mkdir(parents=True, exist_ok=True)
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
    repo = composition.repository
    data_root = project_root / "data"

    # Seed 2 YouTube sources + 1 Bilibili source + 1 Distractor YouTube source + 1 Local Markdown note
    _seed_yt_video(
        repo,
        data_root,
        video_id="vidEvalYt01",
        title="Alpha Agent Production Architecture",
        offset_hours=2,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=15000,
                text="Complex multi-tool workflows demand frontier-class evaluation and deterministic SQLite checkpoints.",
            ),
            TimedTranscriptCueWrite(
                start_ms=15000,
                end_ms=30000,
                text="Silent retries must never trigger unapproved cloud model spend without explicit confirmation.",
            ),
        ),
    )
    _seed_yt_video(
        repo,
        data_root,
        video_id="vidEvalYt02",
        title="Distractor Gardening & Cooking Vlog",
        offset_hours=3,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=12000,
                text="Water tomato seedlings every morning during spring weather in backyard pots.",
            ),
        ),
    )
    _seed_yt_video(
        repo,
        data_root,
        video_id="vidEvalYt03",
        title="Unresolved Anchor Boundary Target",
        offset_hours=4,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=12000,
                text="Window zero legitimate evidence text for boundary checks.",
            ),
            TimedTranscriptCueWrite(
                start_ms=12000,
                end_ms=24000,
                text="Window one second segment for boundary checks.",
            ),
        ),
    )

    bili = BilibiliContentProvider(
        repo,
        data_root,
        adapter=_EvalBilibiliAdapter(now=NOW),
        now=lambda: NOW,
    )
    bili_res = bili.import_input("https://www.bilibili.com/video/BV1Eva2Bixy1/")

    local_provider = LocalContentProvider(repo, data_root, now=lambda: NOW)
    local_res = local_provider.import_bytes(
        filename="eval-local-notes.md",
        payload=b"# Evaluation Notes\n\nParagraph 0 on local verification.\n\nParagraph 1 on refusal checks.\n",
    )

    completer = _EvalCompleter()
    hub = WorkspaceIntelligenceHub(
        repository=repo,
        data_root=data_root,
        project_root=project_root,
        byok_credential_store=_MemorySecret(),
        llm_completer=completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: NOW,
    )
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)

    # Distill primary videos normally so Q&A scope covers rich corpus
    hub.distill_video("vidEvalYt01")
    hub.distill_video("vidEvalYt02")
    hub.distill_video(bili_res.content_id)

    def _verify_citation_in_repo(citation: dict[str, Any]) -> bool:
        vid = str(citation.get("video_id") or "")
        ev_id = str(citation.get("evidence_id") or "")
        start_ms = citation.get("start_ms")
        timed = repo.get_verified_timed_transcript(video_id=vid)
        if timed is None:
            return False
        _, ev_items = fast_app.handle("GET", f"/api/v1/videos/{vid}/evidence")
        known_ids = {str(item["evidence_id"]): item for item in ev_items.get("evidence", [])}
        if ev_id not in known_ids:
            return False
        ev_obj = known_ids[ev_id]
        return start_ms is None or ev_obj.get("start_ms") == start_ms

    # --- Group 1: 8 Answerable questions (single-source & cross-source) ---
    answerable_questions = [
        "为什么生产级多工具 Agent 需要 SQLite 持久化检查点？",
        "如何避免后台任务在未授权情况下产生云端模型扣费？",
        "本地 8B 量化模型在什么任务条件下表现足够稳定？",
        "低参数本地模型跨越五篇以上异构材料时容易出现什么局限？",
        "为何本地资料要求将起止毫秒范围预先锁定在 SQLite？",
        "结合 Alpha Agent 与评测对照材料，总结状态机边界与局部初筛分工",
        "番茄幼苗在春季户外盆栽应当在一天中何时浇水？",
        "总结跨来源评测语料中关于评测闭环与时间轴锁定的核心结论",
    ]
    completer.behavior = "normal"
    locator_hits = 0
    locator_total = 0
    grounded_supported = 0
    for q in answerable_questions:
        res = hub.ask_research_question({"question": q})
        sess = res["session"]
        assert sess["answer_status"] == "GROUNDED"
        assert sess["refused"] is False
        cites = sess["citations"]
        assert len(cites) >= 1
        all_ok = all(_verify_citation_in_repo(c) for c in cites)
        locator_total += len(cites)
        locator_hits += sum(1 for c in cites if _verify_citation_in_repo(c))
        assert all_ok
        if all_ok and sess["answer_zh"].strip():
            grounded_supported += 1

    # --- Group 2: 6 Unanswerable questions -> MUST 100% refuse cleanly ---
    unanswerable_cases = [
        ("refuse_explicit", "这份语料中提到的公司 2026 Q3 净利润与股价是多少？"),
        ("refuse_explicit", "视频里推荐的糖尿病胰岛素临床剂量方案是什么？"),
        ("bluff_no_citations", "强行伪造不存在的 E99 编号回答 2026 营收翻三倍的问题"),
        ("bluff_no_citations", "模型编造未签发引用 E99 时是否必须拦截拒答？"),
        ("bluff_empty_citations", "模型给出答非所问文本但 citations 为空数组时该如何处理？"),
        ("bluff_empty_citations", "语料未涉及量子计算低温稀释制冷机参数，空引用必须拒答"),
    ]
    refusals_caught = 0
    for behavior, q in unanswerable_cases:
        completer.behavior = behavior
        res = hub.ask_research_question({"question": q})
        sess = res["session"]
        assert sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
        assert sess["refused"] is True
        assert sess["citations"] == []
        assert sess["key_takeaways_zh"] == []
        assert sess["action_items_zh"] == []
        assert sess["answer_zh"].startswith("证据不足，无法基于当前资料库可靠回答")
        rel = sess["related_excerpts"]
        assert len(rel) >= 1
        assert all(_verify_citation_in_repo(item) for item in rel)
        md = str(sess["obsidian_markdown"])
        assert "## 核验结论（证据不足拒答）" in md
        assert "## 相关原始片段（仅供参考查阅，未作为支持引用）" in md
        assert "## 时间戳原话证据链" not in md
        assert "[E99]" not in md
        refusals_caught += 1

    # Reload via GET /api/v1/workspace-ai/research/sessions confirms persistence of refusal metadata
    _, reloaded = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    refused_rows = [s for s in reloaded["sessions"] if s.get("refused") is True]
    assert len(refused_rows) == 6

    # --- Group 3: 3 Conflicting-viewpoint questions citing BOTH disagreeing sources ---
    completer.behavior = "conflict"
    conflict_questions = [
        "两位作者对‘小模型是否足够胜任智能工作流’的分歧条件分别是什么？",
        "对比 YouTube Alpha Agent 与 B 站评测材料对本地 vs 云端能力的条件判断",
        "不同来源在‘何种任务规模下需要更强评测或模型’上如何各执一词？",
    ]
    for q in conflict_questions:
        res = hub.ask_research_question({"question": q})
        sess = res["session"]
        assert sess["answer_status"] == "GROUNDED"
        assert sess["refused"] is False
        cited_vids = {c["video_id"] for c in sess["citations"]}
        assert "vidEvalYt01" in cited_vids
        assert bili_res.content_id in cited_vids
        assert all(_verify_citation_in_repo(c) for c in sess["citations"])
        locator_total += len(sess["citations"])
        locator_hits += len(sess["citations"])
        grounded_supported += 1

    # --- Group 4: 3 Out-of-range / invalid-anchor boundary cases ---
    # 19) Mixed valid window 0 + out-of-range windows -> strictly drops invalid without clamping
    completer.behavior = "mixed_oob_windows"
    mixed_res = hub.distill_video("vidEvalYt03")
    mixed_points = mixed_res["ai_brief"]["core_points"]
    assert len(mixed_points) == 1
    assert mixed_points[0]["text"] == "唯一合法的第 0 窗口要点"

    # 20a) All out-of-range windows -> 0 core_points, 0 forged windows[0] bindings, no ungrounded IntelligenceCard
    completer.behavior = "all_oob_windows"
    oob_res = hub.distill_video("vidEvalYt03")
    assert oob_res["ai_brief"]["core_points"] == []
    assert oob_res["ai_brief"]["intelligence_id"] is None

    # 20b) Local Markdown out-of-range section_index -> strictly dropped without clamping to section 0
    completer.behavior = "bad_local_section"
    md_res = hub.distill_video(local_res.content_id)
    assert md_res["ai_brief"]["core_points"] == []

    # Final aggregate benchmark thresholds
    assert locator_hits == locator_total and locator_total > 0
    assert refusals_caught == 6
    assert grounded_supported == 11  # 8 answerable + 3 conflict = 11/11 (100% >= 90%)


class _EvalV2Completer:
    """Extended evaluator supporting Markdown TEXT_RANGE, conflict & mixed-ref traps."""

    def __init__(self) -> None:
        self.behavior: str = "normal"

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
                    "headline_zh": "本地优先文档证据规范与草稿区分原则",
                    "summary_zh": "核心规范要求有字幕或源码才落盘权威证据，否则严格拒答；探索草稿不得冒充可信引用。",
                    "score": 8.6,
                    "score_reason_zh": "包含可落地的失效闭合条件与文档范围设计",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["Local-First", "Evidence Spec"],
                    "topic_cluster_zh": "AI Agent 与自动化架构",
                    "core_points": [
                        {"text_zh": "无源码或字幕时必须 fail-closed 拒答", "section_index": 0},
                        {"text_zh": "交互式头脑风暴草稿不得进入权威证据账本", "section_index": 1},
                    ],
                },
                provider,
                model,
            )

        if "VIDEO_DISTILL_SCHEMA" in system_prompt:
            if "45s Keynote Teaser" in user_prompt or self.behavior == "shorts_flag":
                return (
                    {
                        "headline_zh": "45秒发布会预热短片（低信噪比推广）",
                        "summary_zh": "短平快活动预告短片，不含长期架构深度证据。",
                        "score": 3.5,
                        "score_reason_zh": "低于3分钟的宣传预告短片",
                        "recommendation_tier": "SKIP_NOISE",
                        "content_bucket": "SHORTS_PROMO",
                        "topics_zh": ["Teaser"],
                        "topic_cluster_zh": "AI Agent 与自动化架构",
                        "core_points": [{"text_zh": "发布会宣传短片与折扣码", "cue_window_index": 0}],
                    },
                    provider,
                    model,
                )
            return (
                {
                    "headline_zh": "确定性状态机与多源证据归因实践",
                    "summary_zh": "把数据摄取和模型推理彻底解耦，并通过 SQLite 检查点实现崩溃恢复。",
                    "score": 8.9,
                    "score_reason_zh": "高信息密度工程架构长片",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["Agent", "SQLite"],
                    "topic_cluster_zh": "AI Agent 与自动化架构",
                    "core_points": [{"text_zh": "摄取与推理阶段必须边界分离", "cue_window_index": 0}],
                },
                provider,
                model,
            )

        if "RESEARCH_QA_SCHEMA" in system_prompt:
            refs = re.findall(r"\[(E\d+)\]\s*(?:视频|本地文档)《([^》]+)》", user_prompt)
            md_refs = re.findall(r"\[(E\d+)\]\s*本地文档《([^》]+)》", user_prompt)
            yt_refs = [r for r, title in refs if "State Machines" in title or "Alpha" in title]
            bi_refs = [r for r, title in refs if "评测" in title or "小型" in title]
            doc_refs = [r for r, _ in md_refs]

            if self.behavior == "refuse_partial_premise":
                return (
                    {
                        "answerable": False,
                        "refusal_reason_zh": "材料虽讨论了 Agent 状态机与检查点，但完全未提及 2027 AWS 企业 SaaS 定价或毛利率数据。",
                        "answer_zh": "证据不足。",
                        "key_takeaways_zh": ["应当被后端清空"],
                        "action_items_zh": ["应当被后端清空"],
                        "citations": [],
                    },
                    provider,
                    model,
                )
            if self.behavior == "refuse_numeric_trap":
                return (
                    {
                        "answerable": False,
                        "refusal_reason_zh": "语料未公布 M4 Pro 上运行 Qwen3.5-9B 的实测 P99 延迟毫秒数或 tokens/sec 吞吐数值。",
                        "answer_zh": "未检索到具体数值基准。",
                        "key_takeaways_zh": ["应清空"],
                        "action_items_zh": ["应清空"],
                        "citations": [],
                    },
                    provider,
                    model,
                )
            if self.behavior == "mixed_valid_invalid_refs":
                valid_ref = refs[0][0]
                return (
                    {
                        "answerable": True,
                        "answer_zh": f"已确认状态机落盘原则 [{valid_ref}]；另有未核验传闻数字 [E88]。",
                        "key_takeaways_zh": ["保留真实绑定来源，剔除幽灵引用编号"],
                        "action_items_zh": ["点击已保留的时间戳引用进行抽查"],
                        "citations": [
                            {"ref": valid_ref, "note_zh": "真实已验证来源"},
                            {"ref": "E88", "note_zh": "不存在的编造引用"},
                        ],
                    },
                    provider,
                    model,
                )
            if self.behavior == "all_invalid_refs":
                return (
                    {
                        "answerable": True,
                        "answer_zh": "据外部未提供来源称吞吐提升十倍 [E77][E88]。",
                        "key_takeaways_zh": ["非法强行结论"],
                        "action_items_zh": ["非法行动项"],
                        "citations": [
                            {"ref": "E77", "note_zh": "未签发编号 77"},
                            {"ref": "E88", "note_zh": "未签发编号 88"},
                        ],
                    },
                    provider,
                    model,
                )
            if self.behavior == "cross_yt":
                pick = yt_refs[0] if yt_refs else refs[0][0]
                return (
                    {
                        "answerable": True,
                        "answer_zh": f"英文 YouTube 讲座指出将摄取与推理拆解后才能保证崩溃重放可复现 [{pick}]。",
                        "key_takeaways_zh": ["跨语言检索已直接对齐英文视频时间轴锚点"],
                        "action_items_zh": ["打开原视频时间戳片段精读"],
                        "citations": [{"ref": pick, "note_zh": "摄取与推理分离英文原话"}],
                    },
                    provider,
                    model,
                )
            if self.behavior == "cross_bi":
                pick = bi_refs[0] if bi_refs else refs[0][0]
                return (
                    {
                        "answerable": True,
                        "answer_zh": f"中文 B 站评测对照材料指出 8B 量化模型在单条初筛足够稳，但跨五篇以上异构材料容易漏掉前提假设 [{pick}]。",
                        "key_takeaways_zh": ["英文提问可准确命中中文 B 站视频时间戳片段"],
                        "action_items_zh": ["核对 B 站分段能力边界"],
                        "citations": [{"ref": pick, "note_zh": "本地 8B 能力边界中文片段"}],
                    },
                    provider,
                    model,
                )
            if self.behavior == "conflict_yt_bi":
                r1 = yt_refs[0] if yt_refs else refs[0][0]
                r2 = bi_refs[0] if bi_refs else refs[-1][0]
                return (
                    {
                        "answerable": True,
                        "answer_zh": f"两者适用前提存在明确边界分歧：YouTube 材料 [{r1}] 主张复杂外部工具调用必须依赖严格状态机与检查点；而 B 站评测 [{r2}] 说明单纯单条初筛任务可用轻量 8B 本机完成。",
                        "key_takeaways_zh": ["按任务复杂度拆分路由：单条初筛 vs 多工具闭环"],
                        "action_items_zh": ["保持两者条件对比归因"],
                        "citations": [
                            {"ref": r1, "note_zh": "复杂工具编排需强状态机约束"},
                            {"ref": r2, "note_zh": "单条初筛场景轻量本地够用"},
                        ],
                    },
                    provider,
                    model,
                )
            if self.behavior == "conflict_md_video":
                r_doc = doc_refs[0]
                r_vid = yt_refs[0] if yt_refs else next(r for r, _ in refs if r != r_doc)
                return (
                    {
                        "answerable": True,
                        "answer_zh": f"本地规范文档 [{r_doc}] 界定了‘无依据即 fail-closed 拒答，草稿态可探索但不落库’，与视频演讲 [{r_vid}] 的‘外部副作用必经 schema 校验才入库’形成互补约束。",
                        "key_takeaways_zh": ["文本段区间 TEXT_RANGE 与视频时间轴 TIME_RANGE 协同互证"],
                        "action_items_zh": ["核对文档字符范围与视频对应时间点"],
                        "citations": [
                            {"ref": r_doc, "note_zh": "本地 Markdown 文本区间依据"},
                            {"ref": r_vid, "note_zh": "视频原话时间轴依据"},
                        ],
                    },
                    provider,
                    model,
                )
            if self.behavior == "cross_all":
                picks = []
                for group in (yt_refs, bi_refs, doc_refs):
                    if group and group[0] not in picks:
                        picks.append(group[0])
                for r, _ in refs:
                    if len(picks) < 3 and r not in picks:
                        picks.append(r)
                tags = "、".join(f"[{p}]" for p in picks)
                return (
                    {
                        "answerable": True,
                        "answer_zh": f"综合 YouTube 工程实践、B 站对照评测与本地 Markdown 规范（{tags}），三类来源均通过不可篡改的原文哈希与锚点保证可回溯性。",
                        "key_takeaways_zh": ["YT/B站/本地文档三源证据结构统一核验"],
                        "action_items_zh": ["逐条核查深链与文档段落偏移量"],
                        "citations": [{"ref": p, "note_zh": f"跨平台来源依据 {p}"} for p in picks],
                    },
                    provider,
                    model,
                )

            selected = [r for r, _ in refs[:2]]
            tags = "、".join(f"[{r}]" for r in selected)
            return (
                {
                    "answerable": bool(selected),
                    "answer_zh": f"已严格基于范围限定内可信原话作答（{tags}）。",
                    "key_takeaways_zh": ["全部结论绑定范围内有效原文定位"],
                    "action_items_zh": ["按需展开原片时间段或文档段落复核"],
                    "citations": [{"ref": r, "note_zh": f"限定范围内依据 {r}"} for r in selected],
                },
                provider,
                model,
            )

        return (
            {
                "headline_zh": "评测通用摘要",
                "summary_zh": "评测通用摘要内容。",
                "score": 8.0,
                "score_reason_zh": "通用摘要",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["Eval"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [{"text_zh": "关键事实片段", "cue_window_index": 0}],
            },
            provider,
            model,
        )


def test_12_case_bilingual_multisource_conflict_and_edge_eval_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Expanded Cases 21-32: cross-lingual retrieval, Markdown+Video conflicts, sanitizers & shorts exclusion."""

    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_models", lambda *args: {"models": []}
    )
    monkeypatch.setattr(
        "youtube_intel.runtime_composition.local_runtime_version", lambda *args: {}
    )
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe",
        lambda *args: "MODEL_UNAVAILABLE",
    )

    project_root = (tmp_path / "eval_v2_root").resolve()
    for sub in ("data", "logs", "templates", "vault"):
        (project_root / sub).mkdir(parents=True, exist_ok=True)
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
    repo = composition.repository
    data_root = project_root / "data"

    _seed_yt_video(
        repo,
        data_root,
        video_id="vidEvalB21Yt",
        title="Deterministic Agent State Machines & Recovery",
        offset_hours=2,
        duration_seconds=1500,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=10000,
                end_ms=26000,
                text="Separating deterministic ingestion from optional model inference guarantees reproducible recovery after crashes.",
            ),
            TimedTranscriptCueWrite(
                start_ms=26000,
                end_ms=44000,
                text="Every external API side effect must pass fail-closed schema validation and persist SQLite checkpoints.",
            ),
        ),
    )
    _seed_yt_video(
        repo,
        data_root,
        video_id="vidEvalDist2",
        title="Backyard Tomato & Herb Gardening Guide",
        offset_hours=3,
        duration_seconds=1100,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=15000,
                text="Prune basil leaves weekly and water heirloom tomatoes every dawn in warm soil.",
            ),
        ),
    )
    _seed_yt_video(
        repo,
        data_root,
        video_id="vidEvalShort45",
        title="45s Keynote Teaser! #shorts",
        offset_hours=1,
        duration_seconds=45,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=14000,
                text="Exclusive 45-second keynote promo coupon code X99Z — subscribe now for updates!",
            ),
        ),
    )

    bili = BilibiliContentProvider(
        repo,
        data_root,
        adapter=_EvalBilibiliAdapter(now=NOW),
        now=lambda: NOW,
    )
    bili_res = bili.import_input("https://www.bilibili.com/video/BV1Eva2Bixy1/")

    local_provider = LocalContentProvider(repo, data_root, now=lambda: NOW)
    local_res = local_provider.import_bytes(
        filename="arch-design-note.md",
        payload=(
            b"# Local-First Evidence Engineering Spec\n\n"
            b"Whenever source captions are unavailable, fail closed instead of extrapolating claims.\n\n"
            b"Whereas interactive brainstorming drafts may explore options without persisting authoritative Evidence.\n"
        ),
    )

    completer = _EvalV2Completer()
    hub = WorkspaceIntelligenceHub(
        repository=repo,
        data_root=data_root,
        project_root=project_root,
        byok_credential_store=_MemorySecret(),
        llm_completer=completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: NOW,
    )
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)

    hub.distill_video("vidEvalB21Yt")
    hub.distill_video("vidEvalDist2")
    hub.distill_video(bili_res.content_id)
    hub.distill_video(local_res.content_id)
    completer.behavior = "shorts_flag"
    short_distill = hub.distill_video("vidEvalShort45")
    assert short_distill["ai_brief"]["is_short_noise"] is True

    def _verify_any_citation(citation: dict[str, Any]) -> bool:
        vid = str(citation.get("video_id") or "")
        ev_id = str(citation.get("evidence_id") or "")
        _, ev_payload = fast_app.handle("GET", f"/api/v1/videos/{vid}/evidence")
        ev_map = {str(item["evidence_id"]): item for item in ev_payload.get("evidence", [])}
        if ev_id not in ev_map:
            return False
        ev_obj = ev_map[ev_id]
        if citation.get("locator_type") == "TEXT_RANGE":
            s_off = citation.get("start_offset")
            e_off = citation.get("end_offset")
            return (
                citation.get("citation_url") is None
                and ev_obj.get("locator_type") == "TEXT_RANGE"
                and isinstance(s_off, int)
                and isinstance(e_off, int)
                and e_off > s_off
            )
        timed = repo.get_verified_timed_transcript(video_id=vid)
        if timed is None:
            return False
        start_ms = citation.get("start_ms")
        return start_ms is None or ev_obj.get("start_ms") == start_ms

    # Case 21: CN question grounded cleanly on EN YouTube talk + deep link timestamp
    completer.behavior = "cross_yt"
    s21 = hub.ask_research_question(
        {"question": "为什么在生产级工作流中要把确定性数据摄取与模型推理拆开？"}
    )["session"]
    assert s21["answer_status"] == "GROUNDED"
    assert any(
        c["video_id"] == "vidEvalB21Yt"
        and str(c.get("citation_url") or "").startswith("https://www.youtube.com/watch?v=vidEvalB21Yt")
        and "t=" in str(c.get("citation_url") or "")
        for c in s21["citations"]
    )
    assert all(_verify_any_citation(c) for c in s21["citations"])

    # Case 22: EN question grounded cleanly on ZH Bilibili video + Bilibili deep link
    completer.behavior = "cross_bi"
    s22 = hub.ask_research_question(
        {"question": "When does an 8B quantized local model work reliably versus miss assumptions across 5 heterogeneous talks?"}
    )["session"]
    assert s22["answer_status"] == "GROUNDED"
    assert any(
        c["video_id"] == bili_res.content_id
        and "bilibili.com" in str(c.get("citation_url") or "")
        and "t=" in str(c.get("citation_url") or "")
        for c in s22["citations"]
    )
    assert all(_verify_any_citation(c) for c in s22["citations"])

    # Case 23: Multi-source synthesis spanning YouTube + Bilibili + Local Markdown TEXT_RANGE
    completer.behavior = "cross_all"
    s23 = hub.ask_research_question(
        {
            "question": "Compare YouTube state machine checkpoints, Bilibili 8B scope boundaries, and Local-First Evidence Spec fail-closed rules.",
            "video_ids": ["vidEvalB21Yt", bili_res.content_id, local_res.content_id],
        }
    )["session"]
    assert s23["answer_status"] == "GROUNDED"
    cited_vids_23 = {c["video_id"] for c in s23["citations"]}
    assert cited_vids_23 == {"vidEvalB21Yt", bili_res.content_id, local_res.content_id}
    assert any(c.get("locator_type") == "TEXT_RANGE" for c in s23["citations"])
    assert any(c.get("locator_type") == "TIME_RANGE" for c in s23["citations"])
    assert all(_verify_any_citation(c) for c in s23["citations"])

    # Case 24: Conditional conflict attribution (YouTube vs Bilibili)
    completer.behavior = "conflict_yt_bi"
    s24 = hub.ask_research_question(
        {"question": "YouTube 工程视频与 B 站评测对照在‘何种任务需要复杂状态机 vs 本机 8B 足够’上的条件分歧是什么？"}
    )["session"]
    assert s24["answer_status"] == "GROUNDED"
    cited_24 = {c["video_id"] for c in s24["citations"]}
    assert {"vidEvalB21Yt", bili_res.content_id}.issubset(cited_24)
    assert all(_verify_any_citation(c) for c in s24["citations"])

    # Case 25: Conflict/complementarity attribution (Local Markdown TEXT_RANGE vs Video TIME_RANGE)
    completer.behavior = "conflict_md_video"
    s25 = hub.ask_research_question(
        {
            "question": "本地 Markdown 证据规范在‘fail-closed 拒答与草稿边界’与视频演讲侧重点如何区分？",
            "video_ids": [local_res.content_id, "vidEvalB21Yt"],
        }
    )["session"]
    assert s25["answer_status"] == "GROUNDED"
    assert {c["video_id"] for c in s25["citations"]} == {local_res.content_id, "vidEvalB21Yt"}
    assert all(_verify_any_citation(c) for c in s25["citations"])

    # Case 26: Strict 2-source scope isolation excludes out-of-scope distractor & Bilibili
    completer.behavior = "normal"
    s26 = hub.ask_research_question(
        {
            "question": "仅围绕状态机与本地规范总结恢复原则与草稿边界",
            "video_ids": ["vidEvalB21Yt", local_res.content_id],
        }
    )["session"]
    assert s26["covered_source_count"] == 2
    assert {s["video_id"] for s in s26["covered_sources"]} == {"vidEvalB21Yt", local_res.content_id}
    assert {c["video_id"] for c in s26["citations"]}.issubset({"vidEvalB21Yt", local_res.content_id})

    # Case 27: Partial-premise trap (real Agent topic + fabricated 2027 AWS pricing) -> REFUSED
    completer.behavior = "refuse_partial_premise"
    s27 = hub.ask_research_question(
        {"question": "Agent 状态机方案的 2027 AWS 企业 SaaS 年费定价与毛利率是多少？"}
    )["session"]
    assert s27["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert s27["refused"] is True
    assert s27["citations"] == []
    assert s27["key_takeaways_zh"] == []
    assert s27["action_items_zh"] == []
    assert len(s27["related_excerpts"]) >= 1

    # Case 28: Numeric hardware metric trap -> REFUSED + clean refusal Obsidian markdown
    completer.behavior = "refuse_numeric_trap"
    s28 = hub.ask_research_question(
        {"question": "Qwen3.5-9B 在 M4 Pro 上的实测 P99 延迟是多少毫秒？"}
    )["session"]
    assert s28["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert s28["refused"] is True
    assert s28["citations"] == []
    assert "## 核验结论（证据不足拒答）" in str(s28["obsidian_markdown"])

    # Case 29: Mixed valid [E1] + fabricated [E88] -> keeps verified E1, strips dangling [E88]
    completer.behavior = "mixed_valid_invalid_refs"
    s29 = hub.ask_research_question(
        {"question": "状态机崩溃恢复机制有什么可靠依据？"}
    )["session"]
    assert s29["answer_status"] == "GROUNDED"
    assert s29["refused"] is False
    assert len(s29["citations"]) == 1
    assert s29["citations"][0]["ref_label"] == "E1"
    assert "[E88]" not in s29["answer_zh"]
    assert "[E88]" not in str(s29["obsidian_markdown"])

    # Case 30: All-invalid refs ([E77], [E88]) even when model claims answerable=True -> FAIL-CLOSED REFUSAL
    completer.behavior = "all_invalid_refs"
    s30 = hub.ask_research_question(
        {"question": "吞吐量是否如传闻一样提升了十倍？"}
    )["session"]
    assert s30["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
    assert s30["refused"] is True
    assert s30["citations"] == []
    assert s30["key_takeaways_zh"] == []
    assert "[E77]" not in s30["answer_zh"]
    assert "[E88]" not in s30["obsidian_markdown"]

    # Case 31: 45s #shorts promo noise stays excluded from default corpus Q&A retrieval
    completer.behavior = "normal"
    s31 = hub.ask_research_question(
        {"question": "发布会 45 秒预热短片优惠券码 X99Z 和确定性恢复检查点有哪些内容？"}
    )["session"]
    assert all(src["video_id"] != "vidEvalShort45" for src in s31["covered_sources"])
    assert all(cit["video_id"] != "vidEvalShort45" for cit in s31["citations"])

    # Case 32: Offline Public Beta Demo Showcase refuses both CN and EN unstated-fact traps cleanly
    demo_rt = prepare_demo_showcase(REPO_ROOT, demo_root=tmp_path / "demo_eval_pack", reset=True)
    for demo_trap in (
        "这份在线知识库展示里提到的 2026 Q3 胰岛素剂量表与企业并购估值倍数分别是多少？",
        "What exact CUDA TFLOPS throughput and kilowatt-hour power draw were benchmarked on NVIDIA H200 clusters?",
    ):
        st_code, st_payload = demo_rt.fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/research/ask",
            json.dumps({"question": demo_trap}).encode("utf-8"),
        )
        assert st_code == 200
        demo_sess = st_payload["session"]
        assert demo_sess["answer_status"] == "REFUSED_INSUFFICIENT_EVIDENCE"
        assert demo_sess["refused"] is True
        assert demo_sess["citations"] == []
        assert len(demo_sess["related_excerpts"]) >= 1
