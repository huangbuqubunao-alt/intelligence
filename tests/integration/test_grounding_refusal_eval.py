"""20-case labeled evaluation benchmark for strict grounding, reliable refusal & anchor bounds."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
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
            duration_seconds=1200,
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
