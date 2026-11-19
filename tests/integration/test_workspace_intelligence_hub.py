from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    VideoMetadata,
)
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
from youtube_intel.local_content import (
    LocalContentProvider,
    MediaTranscript,
    validate_media_transcript,
)
from youtube_intel.offline_transcription import media_tool
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_authority import sha256, write_managed
from youtube_intel.source_policy import DistillationStyle
from youtube_intel.source_run import (
    SourceRunAttentionReason,
    SourceRunChildState,
    SourceRunPriority,
    SourceRunState,
    SourceRunWrite,
)
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
    _normalize_mlx_lecture_segments,
)

NOW = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)


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


class _FakeDualTrackCompleter:
    """Deterministic JSON LLM responder recording prompts without network calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "mode": mode,
                "provider": provider,
                "model": model,
                "max_tokens": max_tokens,
            }
        )
        if "RESEARCH_QA_SCHEMA" in system_prompt:
            return (
                {
                    "answer_zh": (
                        "综合 OpenAI 架构访谈与本地 Agent 实战课，AI Agent 产品落地的核心共识是"
                        "先收敛确定性工具契约与评测闭环 [E1]，再结合垂类工作流做状态持久化与人机协同 [E2]。"
                    ),
                    "key_takeaways_zh": [
                        "工具边界与可验证状态机比盲目堆叠多 Agent 更关键",
                        "高价值 B2B 工作流切口比通用聊天壳更容易变现",
                    ],
                    "action_items_zh": [
                        "为每个核心工具定义输入输出契约与回放测试集",
                        "优先围绕单人高频痛点封装端到端闭环交付",
                    ],
                    "citations": [
                        {"ref": "E1", "note_zh": "OpenAI 强调可靠性与评测先行"},
                        {"ref": "E2", "note_zh": "本地 Agent 课程演示状态机落地"},
                        {"ref": "E999", "note_zh": "刻意注入未授权引用以验证后端过滤"},
                    ],
                },
                provider,
                model,
            )
        if "WEEKLY_BRIEF_SCHEMA" in system_prompt:
            return (
                {
                    "title_zh": "《本周 AI 产品与商业情报周报》",
                    "executive_summary_zh": (
                        "本周核心信号聚焦于可验证 AI Agent 工程化落地与垂直场景一人公司商业化路径，"
                        "已自动折叠短视频宣发噪音，提炼出高价值长视频干货。"
                    ),
                    "top_shifts_zh": [
                        {
                            "title_zh": "Agent 从 Demo 走向受控状态机与离线评测",
                            "detail_zh": "头部实验室与实战课程一致强调工具沙箱、可回溯证据与确定性编排。",
                            "topic_name": "AI Agent 与自动化架构",
                        }
                    ],
                    "product_opportunities_zh": [
                        "面向创作者与研究者的本地优先多源情报工作台",
                    ],
                    "business_monetization_zh": [
                        "采用本机零成本推理获客 + 高阶云端 BYOK / 团队知识库增值变现",
                    ],
                },
                provider,
                model,
            )
        if "METADATA_DISTILL_SCHEMA" in system_prompt:
            is_short = "duration_seconds: 35" in user_prompt
            return (
                {
                    "headline_zh": (
                        "ChatGPT Images 2.6 35 秒功能预热短片（官方无字幕，基于简介速览）"
                        if is_short
                        else "围绕真实付费意愿构建高转化 AI 产品思路（官方无字幕，基于简介速览）"
                    ),
                    "summary_zh": (
                        "官方简介显示本次更新新增参考图与 GIF 支持，属功能预告短片。"
                        if is_short
                        else "基于官方标题与简介梳理：探讨如何利用新一代模型构建用户愿意直接付费购买的实用型 AI 产品。"
                    ),
                    "score": 2.8 if is_short else 6.8,
                    "score_reason_zh": (
                        "35 秒无字幕功能预告短片，自动归入 Shorts 噪音抽屉。"
                        if is_short
                        else "当前源站暂无公开字幕，仅基于标题与官方简介评估参考价值。"
                    ),
                    "recommendation_tier": "SKIP_NOISE" if is_short else "WORTH_SKIMMING",
                    "content_bucket": "SHORTS_PROMO" if is_short else "DEEP_DIVE",
                    "topics_zh": ["多模态生成"] if is_short else ["AI 产品变现", "商业验证"],
                    "topic_cluster_zh": (
                        "大模型演进与多模态实战" if is_short else "AI 产品机会与一人公司变现"
                    ),
                    "product_opportunities_zh": [] if is_short else ["从用户明确付费痛点倒推最小可用 AI 工具"],
                    "business_opportunities_zh": [] if is_short else ["先验证真实客单价再投入复杂工程"],
                    "filtered_noise_zh": ["官方未提供时间轴字幕，未生成原话证据点"],
                },
                provider,
                model,
            )
        if "Short promo" in user_prompt or "duration_seconds: 45" in user_prompt:
            return (
                {
                    "headline_zh": "Sora 45 秒社媒宣发预热短片，无实质技术与产品细节",
                    "summary_zh": "该视频为 45 秒功能预热宣传片，仅展示视觉片段，不包含架构、API 或商业落地信息。",
                    "score": 2.5,
                    "score_reason_zh": "纯品牌宣发 Short 短片，信息密度极低，建议直接跳过。",
                    "recommendation_tier": "SKIP_NOISE",
                    "content_bucket": "SHORTS_PROMO",
                    "topics_zh": ["品牌宣发短片"],
                    "topic_cluster_zh": "AI 产品机会与一人公司变现",
                    "core_points": [
                        {
                            "text_zh": "展示宣传画面但无技术细节披露",
                            "cue_window_index": 0,
                        }
                    ],
                    "product_opportunities_zh": [],
                    "business_opportunities_zh": [],
                    "filtered_noise_zh": ["全程品牌视觉预热与口号宣传"],
                },
                provider,
                model,
            )
        if "Monetization Playbook" in user_prompt:
            return (
                {
                    "headline_zh": "一人公司高毛利 AI 产品需优先锁定可量化 ROI 的 B2B 垂直工作流",
                    "summary_zh": "围绕真实企业预算与明确交付指标切入微 SaaS，避免做无壁垒通用套壳工具。",
                    "score": 8.9,
                    "score_reason_zh": "给出清晰的定价阶梯与获客闭环。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["一人公司变现", "B2B 定价"],
                    "topic_cluster_zh": "AI 产品机会与一人公司变现",
                    "core_points": [
                        {
                            "text_zh": "按可衡量的时间节省或线索转化结果定价",
                            "cue_window_index": 0,
                        }
                    ],
                    "product_opportunities_zh": ["面向细分行业顾问的自动化交付报告引擎"],
                    "business_opportunities_zh": ["先用高客单价代运营验证需求再沉淀自助订阅"],
                    "filtered_noise_zh": ["赞助商口播"],
                },
                provider,
                model,
            )
        return (
            {
                "headline_zh": "可商用 AI Agent 必须建立在受控工具边界与可回溯证据链之上",
                "summary_zh": (
                    "深入拆解生产级 Agent 的状态机架构、工具权限收敛与真实业务闭环，"
                    "指出个人开发者最稳妥的切入点是高频垂直工作流自动化。"
                ),
                "score": 9.2,
                "score_reason_zh": "兼具底层架构原则与可直接复用的产品化拆解，信息密度极高。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "TUTORIAL" if "Agent.mp4" in user_prompt else "DEEP_DIVE",
                "topics_zh": ["AI Agent 架构", "垂直工作流产品化"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [
                    {
                        "text_zh": "先收敛工具调用契约与失败回退策略，再扩展多步自治规划",
                        "cue_window_index": 0,
                    },
                    {
                        "text_zh": "围绕可量化交付结果设计产品交互，而非暴露底层提示词复杂度",
                        "cue_window_index": 1,
                    },
                ],
                "product_opportunities_zh": [
                    "在垂直信息过载场景提供带时间戳原话溯源的结构化决策卡片",
                ],
                "business_opportunities_zh": [
                    "通过本地免费模型降低边际成本，以高信噪比周报建立付费留存",
                ],
                "filtered_noise_zh": [
                    "开场寒暄与频道订阅口播引导",
                ],
            },
            provider,
            model,
        )


class _FakeMediaTranscriber:
    def transcribe(self, snapshot: Path, *, duration_seconds: float) -> MediaTranscript:
        assert snapshot.is_file()
        end_first = min(1500, int(duration_seconds * 500))
        end_second = min(2900, int(duration_seconds * 950))
        return MediaTranscript(
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=max(400, end_first),
                    text="第一部分讲解生产级 AI Agent 的状态机拆解与工具契约验证。",
                ),
                TimedTranscriptCueWrite(
                    start_ms=max(400, end_first),
                    end_ms=max(800, end_second),
                    text="第二部分演示如何把多步研究工作流封装成稳定交付的产品体验。",
                ),
            ),
            language="zh",
            provenance='{"contract":"offline-timed-transcription-v1"}',
        )


def _seed_youtube_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    source_id: str,
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str,
    duration_seconds: int,
    cues: tuple[TimedTranscriptCueWrite, ...],
    now: datetime,
) -> None:
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            description=f"Description for {title}",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=now - timedelta(hours=4),
            duration_seconds=duration_seconds,
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
        video_id=video_id,
        canonical_artifact_id=art_id,
        cues=cues,
    )
    repo.create_timed_transcript(timed, now=now)
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
            now=now,
        )
    ExtractiveSummaryService(repo, data_root).create(video_id, now=now)


def _build_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    monkeypatch.setattr("youtube_intel.deep_analysis_activation._local_probe", lambda *args: "MODEL_UNAVAILABLE")

    repo_root = Path(__file__).resolve().parents[2]
    project_root = (tmp_path / "owner").resolve()
    for name in ("data", "logs", "templates", "vault"):
        (project_root / name).mkdir(parents=True, exist_ok=True)
    values = load_settings(repo_root / "config" / "settings.example.yaml").model_dump()
    values["storage"]["vault_root"] = str(project_root / "vault")
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    db_path = project_root / "state.sqlite3"
    byok_store = _MemorySecretStore()
    completer = _FakeDualTrackCompleter()
    transcriber = _FakeMediaTranscriber()

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
    source = composition.product.add_source(
        url="https://www.youtube.com/channel/UC1111111111111111111111",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=byok_store,
        llm_completer=completer,
        media_transcriber=transcriber,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b", "qwen2.5:7b")),
        now=lambda: NOW,
    )
    fast_app = FastReadApiApplication(composition.application, workspace_hub=hub)
    return {
        "project_root": project_root,
        "data_root": project_root / "data",
        "vault_root": project_root / "vault",
        "db_path": db_path,
        "composition": composition,
        "repo": composition.repository,
        "raw_app": composition.application,
        "fast_app": fast_app,
        "hub": hub,
        "source": source,
        "byok_store": byok_store,
        "completer": completer,
    }


def test_unenriched_fast_read_preserves_exact_local_api_parity_and_creates_no_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidLong0001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Building Reliable AI Agents in Production",
        duration_seconds=1820,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=6000,
                text="Hello everyone, today we discuss reliable tool contracts for agents.",
            ),
            TimedTranscriptCueWrite(
                start_ms=6000,
                end_ms=14000,
                text="Production deployments need deterministic state machines and evals.",
            ),
        ),
        now=NOW,
    )
    raw_app = env["raw_app"]
    fast_app = env["fast_app"]

    assert not (env["project_root"] / ".workspace-ai" / "hub.sqlite3").exists()
    assert fast_app.handle("GET", "/api/v1/videos") == raw_app.handle("GET", "/api/v1/videos")
    assert fast_app.handle("GET", "/api/v1/videos/vidLong0001") == raw_app.handle(
        "GET", "/api/v1/videos/vidLong0001"
    )
    assert not (env["project_root"] / ".workspace-ai" / "hub.sqlite3").exists()


def test_settings_dual_track_routing_and_keychain_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    status, initial = fast_app.handle("GET", "/api/v1/workspace-ai/settings")
    assert status == HTTPStatus.OK
    assert initial["active_mode"] == "local_ollama"
    assert initial["ollama_model"] == "qwen3.5:9b"
    assert initial["ollama_reachable"] is True
    assert "qwen3.5:9b" in initial["installed_ollama_models"]
    assert initial["cloud_key_configured"] is False

    # Anti-SSRF validation: reject non-loopback Ollama URL and non-HTTPS cloud URL
    bad_status, _ = fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps({"ollama_base_url": "http://192.168.1.9:11434"}).encode("utf-8"),
    )
    assert bad_status == HTTPStatus.UNPROCESSABLE_ENTITY

    bad_cloud_status, _ = fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps({"cloud_base_url": "http://api.deepseek.com/v1"}).encode("utf-8"),
    )
    assert bad_cloud_status == HTTPStatus.UNPROCESSABLE_ENTITY

    # Cloud mode without BYOK key must fail closed on distillation
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidCloud001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Agent Evals Deep Dive",
        duration_seconds=1200,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=5000, text="Evals are mandatory."),
            TimedTranscriptCueWrite(start_ms=5000, end_ms=10000, text="Measure tool accuracy."),
        ),
        now=NOW,
    )
    upd_status, updated = fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps(
            {
                "active_mode": "cloud_byok",
                "cloud_provider": "deepseek",
                "cloud_base_url": "https://api.deepseek.com/v1",
                "cloud_model": "deepseek-chat",
            }
        ).encode("utf-8"),
    )
    assert upd_status == HTTPStatus.OK
    assert updated["active_mode"] == "cloud_byok"
    assert updated["cloud_key_configured"] is False

    fail_status, fail_body = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidCloud001/distill", b"{}"
    )
    assert fail_status == HTTPStatus.CONFLICT
    assert fail_body["error"]["code"] == "CLOUD_CREDENTIAL_MISSING"

    # Saving BYOK secret stores it in CredentialStore only, never in SQLite files
    secret_val = "sk-test-super-secret-byok-987654"
    key_status, key_body = fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps({"cloud_api_key": secret_val}).encode("utf-8"),
    )
    assert key_status == HTTPStatus.OK
    assert key_body["cloud_key_configured"] is True
    assert secret_val not in json.dumps(key_body)
    assert env["byok_store"].get() == secret_val
    hub_bytes = (env["project_root"] / ".workspace-ai" / "hub.sqlite3").read_bytes()
    state_bytes = env["db_path"].read_bytes()
    assert secret_val.encode("utf-8") not in hub_bytes
    assert secret_val.encode("utf-8") not in state_bytes


def test_distill_video_persists_chinese_ai_brief_score_verified_intelligence_topic_and_passes_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidLong0001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Building Reliable AI Agents in Production",
        duration_seconds=2450,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=8000,
                text="First we lock down tool schemas and deterministic error recovery.",
            ),
            TimedTranscriptCueWrite(
                start_ms=600000,
                end_ms=612000,
                text="Next we design product UX around auditable outcomes rather than prompts.",
            ),
        ),
        now=NOW,
    )
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidShort001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Short promo clip for Sora",
        duration_seconds=45,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=4000,
                text="Introducing a quick visual teaser.",
            ),
        ),
        now=NOW,
    )

    status, distilled = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidLong0001/distill", b"{}"
    )
    assert status == HTTPStatus.OK
    brief = distilled["ai_brief"]
    assert brief["score"] == pytest.approx(9.2)
    assert brief["recommendation_tier"] == "MUST_WATCH"
    assert brief["content_bucket"] == "DEEP_DIVE"
    assert brief["is_short_noise"] is False
    assert "AI Agent" in brief["headline_zh"]
    assert brief["intelligence_id"] == "intelligence:workspace-ai:vidLong0001"

    # AuthoritativeIntelligenceReader must verify the persisted card cleanly!
    verified_card = AuthoritativeIntelligenceReader(env["repo"]).read_current_card(
        "intelligence:workspace-ai:vidLong0001"
    )
    assert verified_card.core_conclusion == brief["headline_zh"]

    # Re-distilling the same video must cleanly advance to revision v2 (UPDATED)
    status_v2, distilled_v2 = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidLong0001/distill", b"{}"
    )
    assert status_v2 == HTTPStatus.OK
    assert distilled_v2["ai_brief"]["revision_id"].endswith(":v2")
    verified_card_v2 = AuthoritativeIntelligenceReader(env["repo"]).read_current_card(
        "intelligence:workspace-ai:vidLong0001"
    )
    assert verified_card_v2.verified.revision_id.endswith(":v2")

    # Distilling a 45s Short marks it as SHORTS_PROMO / SKIP_NOISE without polluting intelligences
    short_status, short_res = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidShort001/distill", b"{}"
    )
    assert short_status == HTTPStatus.OK
    assert short_res["ai_brief"]["content_bucket"] == "SHORTS_PROMO"
    assert short_res["ai_brief"]["recommendation_tier"] == "SKIP_NOISE"
    assert short_res["ai_brief"]["is_short_noise"] is True
    assert short_res["ai_brief"]["intelligence_id"] is None

    # Check /api/v1/videos enrichment
    v_status, videos_payload = fast_app.handle("GET", "/api/v1/videos")
    assert v_status == HTTPStatus.OK
    by_id = {v["video_id"]: v for v in videos_payload["videos"]}
    assert by_id["vidLong0001"]["ai_brief"]["score"] == pytest.approx(9.2)
    assert by_id["vidLong0001"]["duration_seconds"] == 2450
    assert by_id["vidLong0001"]["scoring"]["status"] == "AVAILABLE"
    assert by_id["vidShort001"]["ai_brief"]["is_short_noise"] is True

    # Check /api/v1/videos/<id> enrichment (Chinese MODEL_SUMMARY + scoring + Obsidian markdown)
    d_status, detail_payload = fast_app.handle("GET", "/api/v1/videos/vidLong0001")
    assert d_status == HTTPStatus.OK
    assert detail_payload["scoring"]["status"] == "AVAILABLE"
    assert detail_payload["scoring"]["score"] == pytest.approx(9.2)
    assert detail_payload["note"]["v2"]["status"] == "AVAILABLE"
    assert detail_payload["note"]["v2"]["method"] == "MODEL_SUMMARY"
    assert detail_payload["note"]["v2"]["language"] == "zh-CN"
    assert len(detail_payload["note"]["v2"]["timestamped_key_points"]) == 2
    assert "[[AI Agent 与自动化架构]]" in detail_payload["obsidian_markdown"]

    # Check native /api/v1/intelligence, /api/v1/topics, and /api/v1/dashboard light up!
    i_status, intel_payload = fast_app.handle("GET", "/api/v1/intelligence")
    assert i_status == HTTPStatus.OK
    assert len(intel_payload["intelligence"]) == 1
    assert intel_payload["intelligence"][0]["intelligence_id"] == "intelligence:workspace-ai:vidLong0001"

    t_status, topics_payload = fast_app.handle("GET", "/api/v1/topics")
    assert t_status == HTTPStatus.OK
    assert len(topics_payload["topics"]) >= 1
    assert topics_payload["topics"][0]["name"] == "AI Agent 与自动化架构"
    assert topics_payload["topics"][0]["pinned"] is True

    dash_status, dash_payload = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_status == HTTPStatus.OK
    assert len(dash_payload["intelligence"]) == 1
    assert len(dash_payload["pinned_topics"]) >= 1

    # BackupRestoreService.create_backup must pass 100% with .workspace-ai present!
    bk_status, bk_payload = fast_app.handle("POST", "/api/v1/backup-restore/backups", b"{}")
    assert bk_status == HTTPStatus.CREATED
    assert bk_payload["backup"]["preview"]["intelligence_count"] == 1
    assert bk_payload["backup"]["preview"]["topic_count"] >= 1


def test_transcribe_local_mp4_course_video_publishes_timed_transcript_and_chinese_intelligence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ffmpeg = media_tool("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg unavailable")
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    mp4_path = tmp_path / "3. Agent.mp4"
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
    provider = LocalContentProvider(env["repo"], env["data_root"], now=lambda: NOW)
    imported = provider.import_file(mp4_path)
    assert imported.status == "TRANSCRIPTION_UNAVAILABLE"

    tx_status, tx_payload = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{imported.content_id}/transcribe", b"{}"
    )
    assert tx_status == HTTPStatus.OK
    assert tx_payload["transcription_status"] == "READY"
    assert tx_payload["ai_brief"]["content_bucket"] == "TUTORIAL"
    assert tx_payload["ai_brief"]["intelligence_id"] == f"intelligence:workspace-ai:{imported.content_id}"

    detail_status, detail = fast_app.handle("GET", f"/api/v1/videos/{imported.content_id}")
    assert detail_status == HTTPStatus.OK
    assert detail["video"]["processing_status"] == "READY"
    assert detail["transcript"]["status"] == "AVAILABLE"
    assert len(detail["transcript"]["timed_segments"]) == 2
    assert detail["note"]["v2"]["language"] == "zh-CN"


def test_cross_video_grounded_research_qa_and_weekly_brief_with_obsidian_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidOpenAI01",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="OpenAI Agent Architecture Roundtable",
        duration_seconds=1900,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=15000,
                end_ms=28000,
                text="Tool contracts and deterministic evals are foundational for agents.",
            ),
            TimedTranscriptCueWrite(
                start_ms=120000,
                end_ms=135000,
                text="Human-in-the-loop checkpoints keep high-stakes actions safe.",
            ),
        ),
        now=NOW,
    )
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidCourse02",
        channel_id="UC1111111111111111111111",
        channel_name="AI 实战课",
        title="3. Agent.mp4",
        duration_seconds=5052,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=60000,
                end_ms=75000,
                text="状态机拆解能让垂直行业 Agent 落地成功率提升三倍。",
            ),
            TimedTranscriptCueWrite(
                start_ms=300000,
                end_ms=318000,
                text="一人公司做垂直工作流比做通用问答更容易收年费。",
            ),
        ),
        now=NOW,
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidOpenAI01/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidCourse02/distill", b"{}")

    ask_status, ask_payload = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "OpenAI 与本地 Agent 课程对 AI Agent 产品落地有什么共识？",
            }
        ).encode("utf-8"),
    )
    assert ask_status == HTTPStatus.OK
    session = ask_payload["session"]
    assert "AI Agent" in session["answer_zh"]
    # Hallucinated E999 must be stripped; only backend-issued E1 & E2 survive!
    refs = [c["ref_label"] for c in session["citations"]]
    assert "E999" not in refs
    assert len(session["citations"]) == 2
    assert all(c["video_id"] in {"vidOpenAI01", "vidCourse02"} for c in session["citations"])
    assert all(c["evidence_id"].startswith("ev_") or len(c["evidence_id"]) > 8 for c in session["citations"])
    assert "[[" in session["obsidian_markdown"]

    hist_status, hist_payload = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert hist_status == HTTPStatus.OK
    assert len(hist_payload["sessions"]) == 1
    assert len(hist_payload["suggested_questions"]) >= 3

    wb_status, wb_payload = fast_app.handle(
        "POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}"
    )
    assert wb_status == HTTPStatus.OK
    brief = wb_payload["weekly_brief"]
    assert brief["title_zh"] == "《本周 AI 产品与商业情报周报》"
    assert brief["funnel_stats"]["must_watch_count"] == 2
    assert "[[AI Agent 与自动化架构]]" in brief["obsidian_markdown"]

    wb_get_status, wb_get = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    assert wb_get_status == HTTPStatus.OK
    assert wb_get["weekly_brief"]["brief_id"] == brief["brief_id"]

    # Dashboard native weekly_v1 + piggybacked workspace_weekly_brief should be available!
    dash_status, dash = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_status == HTTPStatus.OK
    assert dash["weekly_v1"] is not None
    assert dash["workspace_weekly_brief"]["brief_id"] == brief["brief_id"]

    set_status, set_payload = fast_app.handle("GET", "/api/v1/settings")
    assert set_status == HTTPStatus.OK
    assert set_payload["workspace_ai"]["active_mode"] == "local_ollama"

    obs_status, obs = fast_app.handle(
        "GET", "/api/v1/workspace-ai/videos/vidOpenAI01/obsidian"
    )
    assert obs_status == HTTPStatus.OK
    assert obs["filename"].endswith(".md")
    assert "[[AI Agent 与自动化架构]]" in obs["markdown"]

    # Red-line check: zero files written into external vault directory!
    assert [p for p in env["vault_root"].rglob("*") if p.is_file()] == []


def test_normalize_mlx_lecture_segments_merges_over_4096_and_satisfies_media_transcript_contract() -> None:
    duration_seconds = 5637.549
    raw_segments: list[dict[str, object]] = []
    # Simulate 4,500 short clauses across a 94-minute Chinese course lecture,
    # including slight floating-point overlaps, empty strings, and end jitter.
    step = duration_seconds / 4500.0
    for idx in range(4500):
        start = max(0.0, idx * step - (0.015 if idx % 7 == 0 else 0.0))
        end = (idx + 1) * step + (0.08 if idx == 4499 else 0.0)
        text = "" if idx % 100 == 50 else f"第{idx + 1}句实战讲解：Agent工具契约与多模态状态机设计\ufffd\x07。"
        raw_segments.append({"start": start, "end": end, "text": text})

    transcript = _normalize_mlx_lecture_segments(
        raw_segments,
        duration_seconds=duration_seconds,
        language="zh",
        provenance='{"contract":"offline-mlx-lecture-v1"}',
    )
    validate_media_transcript(transcript, duration_seconds)
    assert 1 <= len(transcript.cues) <= 2600
    assert transcript.language == "zh"
    assert "\ufffd" not in transcript.cues[0].text
    assert "\x07" not in transcript.cues[0].text


def _seed_metadata_only_youtube_video(
    repo: SQLiteStateRepository,
    *,
    source_id: str,
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str,
    description: str,
    duration_seconds: int,
    now: datetime,
) -> None:
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            description=description,
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=now - timedelta(hours=2),
            duration_seconds=duration_seconds,
            default_language="en",
            available_languages=(),
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
    with repo._connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO source_video_links (source_id, video_id, discovered_at) VALUES (?, ?, ?)",
            (source_id, video_id, now.strftime("%Y-%m-%dT%H:%M:%SZ")),
        )


def test_metadata_only_youtube_distillation_and_incremental_sync_pending_with_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    _seed_metadata_only_youtube_video(
        env["repo"],
        source_id=env["source"].source_id,
        video_id="vidMetaSh35",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Introducing ChatGPT Images 2.6",
        description="Images, upgraded—introducing ChatGPT Images 2.6 with GIFs and reference images.",
        duration_seconds=35,
        now=NOW,
    )
    _seed_metadata_only_youtube_video(
        env["repo"],
        source_id=env["source"].source_id,
        video_id="vidMetaLg01",
        channel_id="UC1111111111111111111111",
        channel_name="Greg Isenberg",
        title="Make cool things with AI that people buy",
        description="Deep dive on building practical AI products that customers actually pay for.",
        duration_seconds=1850,
        now=NOW,
    )
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidNewTx001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="How Mozilla uses GPT-6 Cyber to find and fix Firefox vulnerabilities",
        duration_seconds=1219,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=9000,
                text="Mozilla uses GPT-6 Cyber to find and patch Firefox vulnerabilities.",
            ),
            TimedTranscriptCueWrite(
                start_ms=9000,
                end_ms=20000,
                text="Automated reproduction harnesses verify security fixes deterministically.",
            ),
        ),
        now=NOW,
    )

    st_code, sync_st = fast_app.handle("GET", "/api/v1/workspace-ai/sync-status")
    assert st_code == HTTPStatus.OK
    assert sync_st["pending_count"] == 3
    assert sync_st["pending_transcript_count"] == 1
    assert sync_st["pending_metadata_only_count"] == 2

    run_code, run_res = fast_app.handle(
        "POST", "/api/v1/workspace-ai/sync-pending", json.dumps({"limit": 10}).encode("utf-8")
    )
    assert run_code == HTTPStatus.OK
    assert run_res["synced_count"] == 3
    assert run_res["remaining_count"] == 0

    # Captionless 35s Short folds cleanly without fabricating transcript evidence or Intelligence cards
    sh_brief = env["hub"].get_video_brief("vidMetaSh35")
    assert sh_brief is not None
    assert sh_brief["source_basis"] == "METADATA_ONLY"
    assert sh_brief["is_short_noise"] is True
    assert sh_brief["core_points"] == []
    assert sh_brief["intelligence_id"] is None

    # Captionless 1850s podcast gets honest metadata brief without fabricating note.v2 MODEL_SUMMARY
    lg_code, lg_detail = fast_app.handle("GET", "/api/v1/videos/vidMetaLg01")
    assert lg_code == HTTPStatus.OK
    assert lg_detail["video"]["ai_brief"]["source_basis"] == "METADATA_ONLY"
    assert lg_detail["ai_brief"]["core_points"] == []
    assert lg_detail["ai_brief"]["intelligence_id"] is None
    assert lg_detail["note"]["v2"]["status"] != "AVAILABLE"

    # When captions later arrive for vidMetaLg01, sync-pending automatically upgrades it to TRANSCRIPT!
    env["repo"].advance_pipeline(
        "vidMetaLg01",
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=NOW + timedelta(minutes=5),
    )
    rel = "transcripts/canonical/vidMetaLg01.txt"
    cues = (
        TimedTranscriptCueWrite(start_ms=0, end_ms=6000, text="Customers pay for clear workflow ROI."),
        TimedTranscriptCueWrite(start_ms=6000, end_ms=15000, text="Ship vertical AI SaaS with fast onboarding."),
    )
    raw_txt = "\n".join(c.text for c in cues).encode("utf-8")
    write_managed(env["data_root"], rel, raw_txt)
    env["repo"].upsert_artifact(
        ArtifactWrite(
            artifact_id="canonical:vidMetaLg01",
            artifact_key="canonical:vidMetaLg01",
            video_id="vidMetaLg01",
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=rel,
            content_hash=sha256(raw_txt),
            provider="youtube",
            model=None,
            producer_version="v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=NOW + timedelta(minutes=5),
    )
    env["repo"].create_timed_transcript(
        TimedTranscriptWrite.from_cues(
            video_id="vidMetaLg01",
            canonical_artifact_id="canonical:vidMetaLg01",
            cues=cues,
        ),
        now=NOW + timedelta(minutes=5),
    )

    st_after_code, sync_after = fast_app.handle("GET", "/api/v1/workspace-ai/sync-status")
    assert st_after_code == HTTPStatus.OK
    assert sync_after["pending_count"] == 1
    assert sync_after["pending_transcript_upgrade_count"] == 1

    up_code, up_res = fast_app.handle("POST", "/api/v1/workspace-ai/sync-pending", b"{}")
    assert up_code == HTTPStatus.OK
    assert up_res["synced_count"] == 1
    upgraded = env["hub"].get_video_brief("vidMetaLg01")
    assert upgraded["source_basis"] == "TRANSCRIPT"
    assert upgraded["intelligence_id"] == "intelligence:workspace-ai:vidMetaLg01"
    assert len(upgraded["core_points"]) >= 1


def test_bilingual_fts5_research_retrieval_matches_english_cues_from_chinese_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    # Seed 9 distractor videos + 1 target English security video WITHOUT distilling Chinese briefs first!
    for idx in range(9):
        _seed_youtube_video(
            env["repo"],
            env["data_root"],
            source_id=env["source"].source_id,
            video_id=f"vidFiller0{idx}",
            channel_id="UC1111111111111111111111",
            channel_name="General Channel",
            title=f"Weekly Office Vlog Episode {idx}",
            duration_seconds=1500,
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=8000,
                    text="Welcome back to our casual coffee chat and travel diary.",
                ),
            ),
            now=NOW,
        )

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="PkAmyub12K8",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Engineering Deep Dive with Brian Grinstead",
        duration_seconds=1219,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=10000,
                text="Thanks for joining our engineering conversation today.",
            ),
            TimedTranscriptCueWrite(
                start_ms=300000,
                end_ms=310000,
                text="We started reviewing legacy modules across the repository.",
            ),
            TimedTranscriptCueWrite(
                start_ms=860000,
                end_ms=875000,
                text=(
                    "Firefox browser memory safety vulnerabilities are automatically "
                    "discovered by fuzzing harnesses and patched before release."
                ),
            ),
            TimedTranscriptCueWrite(
                start_ms=1180000,
                end_ms=1195000,
                text="Thanks everyone for watching.",
            ),
        ),
        now=NOW,
    )

    # Pure Chinese query sharing ZERO literal English tokens with the transcript!
    ask_code, ask_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "浏览器安全漏洞是如何自动发现和打补丁修复的？"}).encode("utf-8"),
    )
    assert ask_code == HTTPStatus.OK
    citations = ask_res["session"]["citations"]
    cited_videos = {c["video_id"] for c in citations}
    assert "PkAmyub12K8" in cited_videos
    firefox_cite = next(c for c in citations if c["video_id"] == "PkAmyub12K8")
    # Must match the exact 860s (14:20) cue window via FTS5 cue search rather than only 00:00!
    assert firefox_cite["start_seconds"] == pytest.approx(860.0)
    assert "vulnerabilities" in firefox_cite["excerpt"]


def test_dashboard_filters_superseded_execution_condition_attention_and_sidecar_backup_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidHist0001",
        channel_id="UC1111111111111111111111",
        channel_name="Greg Isenberg",
        title="AI Startup Playbook",
        duration_seconds=1600,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=5000, text="Focus on niche B2B workflows."),
        ),
        now=NOW,
    )

    run = repo.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=env["source"].source_id,
            command_id="cmd-old-unresolved",
            priority=SourceRunPriority.P1,
            created_at=NOW - timedelta(days=1),
        )
    )
    repo.transition_source_run(run.run_id, to_state=SourceRunState.RUNNING, now=NOW - timedelta(days=1))
    repo.record_source_run_child(
        run.run_id,
        video_id="vidHist0001",
        state=SourceRunChildState.PENDING,
        distillation_execution_id=None,
        now=NOW - timedelta(days=1),
    )
    repo.transition_source_run_child(
        run.run_id,
        video_id="vidHist0001",
        to_state=SourceRunChildState.WAITING,
        now=NOW - timedelta(days=1),
    )
    repo.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED,
        now=NOW - timedelta(days=1),
    )

    # Distill video so sidecar DB exists
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidHist0001/distill", b"{}")

    # While focus_rules are still empty AND child is WAITING, warning MUST still surface!
    _, dash_before = fast_app.handle("GET", "/api/v1/dashboard")
    assert len(dash_before["needs_attention"]) == 1

    # Settle child to terminal FAILED and configure global focus_rules -> superseded warning clears!
    repo.transition_source_run_child(
        run.run_id,
        video_id="vidHist0001",
        to_state=SourceRunChildState.FAILED,
        now=NOW,
    )
    policy_svc = env["raw_app"]._source_policy_service
    policy_svc.update_global(
        command_id="cmd-set-global-focus",
        initial_history_count=5,
        per_run_max_new_videos=5,
        focus_rules=("AI Agent", "Startup Ideas"),
        ignore_rules=("#shorts",),
        distillation_style=DistillationStyle.BALANCED,
    )
    _, dash_after = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_after["needs_attention"] == []

    # Sidecar backup & restore roundtrip (must never include BYOK secret!)
    secret_val = "sk-never-export-in-sidecar-backup"
    fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps({"cloud_api_key": secret_val, "ollama_model": "qwen2.5:7b"}).encode("utf-8"),
    )
    bk_code, bk_snap = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    assert bk_code == HTTPStatus.OK
    assert bk_snap["schema_version"] == "workspace-ai-backup-v1"
    assert bk_snap["counts"]["briefs"] == 1
    assert secret_val not in json.dumps(bk_snap)

    # Simulate fresh/wiped sidecar DB and restore from snapshot
    (env["project_root"] / ".workspace-ai" / "hub.sqlite3").unlink()
    assert env["hub"].get_video_brief("vidHist0001") is None

    rs_code, rs_body = fast_app.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(bk_snap).encode("utf-8")
    )
    assert rs_code == HTTPStatus.OK
    assert rs_body["restored"]["briefs"] == 1
    assert env["hub"].get_video_brief("vidHist0001") is not None
    assert env["hub"].get_settings()["ollama_model"] == "qwen2.5:7b"


def test_scoped_and_comparative_research_qa_filters_by_channel_topic_and_multi_video_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    llm: Any = env["completer"]

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidOpenAI01",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="OpenAI Agent Architecture Deep Dive",
        duration_seconds=1800,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=10000,
                end_ms=25000,
                text="Deterministic tool contracts keep multi-step agents reliable.",
            ),
        ),
        now=NOW - timedelta(hours=3),
    )
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidGreg0002",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="Solo Founder $1M AI Workflow Playbook",
        duration_seconds=2100,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=45000,
                end_ms=60000,
                text="Niche B2B workflow automation beats horizontal wrappers.",
            ),
        ),
        now=NOW - timedelta(hours=1),
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidOpenAI01/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidGreg0002/distill", b"{}")
    # Place vidGreg0002 into a distinct topic cluster for topic-scoping verification
    with env["hub"]._connect_write() as conn:
        conn.execute(
            "UPDATE video_ai_briefs SET topic_cluster_zh = ? WHERE video_id = ?",
            ("AI 产品机会与一人公司变现", "vidGreg0002"),
        )

    # 1) Scope options endpoint exposes channels, topic_clusters, and grounded videos
    opt_code, opt_body = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert opt_code == HTTPStatus.OK
    scope_opts = opt_body["scope_options"]
    channel_keys = {c["key"]: c for c in scope_opts["channels"]}
    assert "OpenAI" in channel_keys
    assert channel_keys["OpenAI"]["video_count"] == 1
    assert "Greg Isenberg" in channel_keys
    assert channel_keys["Greg Isenberg"]["video_count"] == 1
    cluster_names = {c["name"]: c for c in scope_opts["topic_clusters"]}
    assert cluster_names["AI Agent 与自动化架构"]["video_count"] == 1
    assert cluster_names["AI 产品机会与一人公司变现"]["video_count"] == 1
    assert {v["video_id"] for v in scope_opts["videos"]} == {"vidOpenAI01", "vidGreg0002"}

    # 2) Channel-scoped query restricts retrieval strictly to Greg Isenberg
    ch_code, ch_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "一人公司应该切入什么 AI 方向？",
                "channel_key": "Greg Isenberg",
            }
        ).encode("utf-8"),
    )
    assert ch_code == HTTPStatus.OK
    ch_session = ch_res["session"]
    assert {c["video_id"] for c in ch_session["citations"]} == {"vidGreg0002"}
    assert "Greg Isenberg" in ch_session["scope_label_zh"]

    # 3) Topic-cluster-scoped query restricts retrieval strictly to AI Agent 与自动化架构
    tp_code, tp_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "Agent 可靠性的核心前提是什么？",
                "topic_cluster": "AI Agent 与自动化架构",
            }
        ).encode("utf-8"),
    )
    assert tp_code == HTTPStatus.OK
    tp_session = tp_res["session"]
    assert {c["video_id"] for c in tp_session["citations"]} == {"vidOpenAI01"}
    assert "AI Agent 与自动化架构" in tp_session["scope_label_zh"]

    # 4) Multi-video comparative selection guarantees both chosen videos feed E1 & E2
    cmp_code, cmp_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "对比 OpenAI 与 Greg Isenberg 的侧重点异同",
                "video_ids": ["vidOpenAI01", "vidGreg0002"],
            }
        ).encode("utf-8"),
    )
    assert cmp_code == HTTPStatus.OK
    cmp_session = cmp_res["session"]
    assert {c["video_id"] for c in cmp_session["citations"]} == {"vidOpenAI01", "vidGreg0002"}
    assert "2" in cmp_session["scope_label_zh"]
    assert "Solo Founder $1M AI Workflow Playbook" in llm.calls[-1]["user_prompt"]
    assert "OpenAI Agent Architecture Deep Dive" in llm.calls[-1]["user_prompt"]

    # 5) Unmatched scope returns honest 409 NO_GROUNDED_CONTENT
    empty_code, empty_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "不存在的频道内容",
                "channel_key": "GhostChannel",
            }
        ).encode("utf-8"),
    )
    assert empty_code == HTTPStatus.CONFLICT
    assert empty_res["error"]["code"] == "NO_GROUNDED_CONTENT"

    # 6) Backup & restore roundtrips scope_label_zh cleanly
    _, snap = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    (env["project_root"] / ".workspace-ai" / "hub.sqlite3").unlink()
    rs_status, _ = fast_app.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(snap).encode("utf-8")
    )
    assert rs_status == HTTPStatus.OK
    _, restored_sessions = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    by_sid = {s["session_id"]: s for s in restored_sessions["sessions"]}
    assert "Greg Isenberg" in by_sid[ch_session["session_id"]]["scope_label_zh"]


def test_topics_and_dashboard_pinned_topics_enriched_with_chronological_ai_evolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidOlder001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Agent Foundations Part 1",
        duration_seconds=1500,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=8000, text="Early tool-use baseline."),
        ),
        now=NOW - timedelta(days=3),
    )
    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidNewer002",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="Agent Production Workflows Part 2",
        duration_seconds=2200,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=8000, text="Production multi-step workflows."),
        ),
        now=NOW,
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidOlder001/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidNewer002/distill", b"{}")

    list_code, list_body = fast_app.handle("GET", "/api/v1/topics")
    assert list_code == HTTPStatus.OK
    agent_topic = next(
        t for t in list_body["topics"] if t["name"] == "AI Agent 与自动化架构"
    )
    evo = agent_topic["ai_evolution"]
    assert evo["video_count"] == 2
    assert evo["must_watch_count"] == 2
    assert evo["avg_score"] == pytest.approx(9.2)
    assert set(evo["source_channels"]) == {"OpenAI", "Greg Isenberg"}
    assert evo["latest_headline_zh"]

    det_code, det_body = fast_app.handle(
        "GET", f"/api/v1/topics/{agent_topic['topic_id']}"
    )
    assert det_code == HTTPStatus.OK
    entries = det_body["topic"]["ai_evolution"]["entries"]
    assert [e["video_id"] for e in entries] == ["vidNewer002", "vidOlder001"]
    assert entries[0]["title"] == "Agent Production Workflows Part 2"
    assert entries[0]["channel_name"] == "Greg Isenberg"
    assert entries[0]["score"] == pytest.approx(9.2)
    assert entries[0]["headline_zh"]
    assert len(entries[0]["product_opportunities_zh"]) >= 1

    dash_code, dash_body = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_code == HTTPStatus.OK
    pinned_agent = next(
        t for t in dash_body["pinned_topics"] if t["name"] == "AI Agent 与自动化架构"
    )
    assert pinned_agent["ai_evolution"]["video_count"] == 2


def test_video_curation_star_and_read_states_enrich_videos_and_roundtrip_backup_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidCur00001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Agent Curation Episode 1",
        duration_seconds=1800,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=8000, text="Reliable agent evals."),
        ),
        now=NOW,
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidCur00001/distill", b"{}")

    _, initial_list = fast_app.handle("GET", "/api/v1/videos")
    item0 = next(v for v in initial_list["videos"] if v["video_id"] == "vidCur00001")
    assert item0["ai_brief"]["starred"] is False
    assert item0["ai_brief"]["is_read"] is False

    # Partial update: star first, then mark read -> both stay True
    s_code, s_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/vidCur00001/curation",
        json.dumps({"starred": True}).encode("utf-8"),
    )
    assert s_code == HTTPStatus.OK
    assert s_res["starred"] is True
    assert s_res["is_read"] is False

    r_code, r_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/vidCur00001/curation",
        json.dumps({"is_read": True}).encode("utf-8"),
    )
    assert r_code == HTTPStatus.OK
    assert r_res["starred"] is True
    assert r_res["is_read"] is True

    # Unknown video returns 404; empty/non-boolean payload returns 422
    miss_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/missingVid99/curation",
        json.dumps({"starred": True}).encode("utf-8"),
    )
    assert miss_code == HTTPStatus.NOT_FOUND

    bad_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/vidCur00001/curation",
        b"{}",
    )
    assert bad_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Enriched list and detail immediately reflect curated state
    _, after_list = fast_app.handle("GET", "/api/v1/videos")
    item1 = next(v for v in after_list["videos"] if v["video_id"] == "vidCur00001")
    assert item1["ai_brief"]["starred"] is True
    assert item1["ai_brief"]["is_read"] is True

    _, after_det = fast_app.handle("GET", "/api/v1/videos/vidCur00001")
    assert after_det["video"]["ai_brief"]["starred"] is True
    assert after_det["video"]["ai_brief"]["is_read"] is True
    assert after_det["ai_brief"]["starred"] is True
    assert after_det["ai_brief"]["is_read"] is True

    # Backup & restore roundtrips curation states and stays backward-compatible when omitted
    _, snap = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    assert snap["counts"]["curation_states"] == 1
    assert len(snap["video_curation_states"]) == 1

    (env["project_root"] / ".workspace-ai" / "hub.sqlite3").unlink()
    rs_code, rs_body = fast_app.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(snap).encode("utf-8")
    )
    assert rs_code == HTTPStatus.OK
    assert rs_body["restored"]["curation_states"] == 1

    _, restored_det = fast_app.handle("GET", "/api/v1/videos/vidCur00001")
    assert restored_det["ai_brief"]["starred"] is True
    assert restored_det["ai_brief"]["is_read"] is True

    legacy_snap = {k: v for k, v in snap.items() if k != "video_curation_states"}
    leg_code, leg_body = fast_app.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(legacy_snap).encode("utf-8")
    )
    assert leg_code == HTTPStatus.OK
    assert leg_body["restored"]["curation_states"] == 0


def test_topic_detail_obsidian_moc_markdown_and_dashboard_saved_ids_plus_fully_distilled_attention_hygiene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidOlder012",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Agent Archive Deep Dive",
        duration_seconds=1600,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=8000, text="Historical agent architecture."),
        ),
        now=NOW - timedelta(days=12),
    )
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidRecent02",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="Agent Recent Deep Dive",
        duration_seconds=2100,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=8000, text="Fresh weekly workflow playbook."),
        ),
        now=NOW - timedelta(days=2),
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidOlder012/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidRecent02/distill", b"{}")

    # 1) Topics list exposes recent_7d_count and Topic detail exposes Obsidian MOC markdown
    _, list_body = fast_app.handle("GET", "/api/v1/topics")
    agent_topic = next(
        t for t in list_body["topics"] if t["name"] == "AI Agent 与自动化架构"
    )
    assert agent_topic["ai_evolution"]["recent_7d_count"] == 1

    _, det_body = fast_app.handle("GET", f"/api/v1/topics/{agent_topic['topic_id']}")
    det_evo = det_body["topic"]["ai_evolution"]
    assert det_evo["recent_7d_count"] == 1
    moc_md = det_evo["obsidian_markdown"]
    assert "youtube-intel/topic-moc" in moc_md
    assert "[[AI Agent 与自动化架构]]" in moc_md
    assert "[[Agent Recent Deep Dive]]" in moc_md
    assert "[[Agent Archive Deep Dive]]" in moc_md
    assert [p for p in env["vault_root"].rglob("*") if p.is_file()] == []

    # 2) Dashboard exposes saved_intelligence_ids matching persisted saved_intelligences
    intel_id = "intelligence:workspace-ai:vidRecent02"
    _, dash0 = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash0["saved_intelligence_ids"] == []

    sv_code, _ = fast_app.handle(
        "POST",
        "/api/v1/saved-intelligence/save",
        json.dumps({"intelligence_id": intel_id}).encode("utf-8"),
    )
    assert sv_code == HTTPStatus.OK
    _, dash1 = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash1["saved_intelligence_ids"] == [intel_id]

    un_code, _ = fast_app.handle(
        "POST",
        "/api/v1/saved-intelligence/unsave",
        json.dumps({"intelligence_id": intel_id}).encode("utf-8"),
    )
    assert un_code == HTTPStatus.OK
    _, dash2 = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash2["saved_intelligence_ids"] == []

    # 3) Empty-child EXECUTION_CONDITION_UNRESOLVED run (e.g. >20 evidence chunks on a healthy channel)
    # is suppressed when Workspace AI has already distilled all linked videos of that source,
    # yet still surfaces if a linked video remains undistilled!
    run = repo.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=env["source"].source_id,
            command_id="cmd-empty-child-unresolved",
            priority=SourceRunPriority.P1,
            created_at=NOW - timedelta(minutes=10),
        )
    )
    repo.transition_source_run(
        run.run_id, to_state=SourceRunState.RUNNING, now=NOW - timedelta(minutes=10)
    )
    repo.transition_source_run(
        run.run_id,
        to_state=SourceRunState.NEEDS_ATTENTION,
        attention_reason=SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED,
        now=NOW - timedelta(minutes=9),
    )

    _, dash_clean = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_clean["needs_attention"] == []

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidUndist03",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="New Undistilled Episode",
        duration_seconds=1500,
        cues=(
            TimedTranscriptCueWrite(start_ms=0, end_ms=8000, text="Brand new episode."),
        ),
        now=NOW,
    )
    _, dash_pending = fast_app.handle("GET", "/api/v1/dashboard")
    assert len(dash_pending["needs_attention"]) == 1

    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidUndist03/distill", b"{}")
    _, dash_healed = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_healed["needs_attention"] == []


def test_round4_intelligence_activity_convergence_topic_synthesis_and_weekly_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    source_id: str = env["source"].source_id

    # Seed two Agent videos from distinct channels + one Monetization video + one captionless terminal FAILED video
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidDone0001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Agent Reliability Architecture",
        duration_seconds=1800,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0, end_ms=8000, text="Reliable tool contracts and deterministic state."
            ),
        ),
        now=NOW - timedelta(days=3),
    )
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidDone0004",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="Monetization Playbook for Solo Founders",
        duration_seconds=1650,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0, end_ms=8000, text="Price on measurable B2B ROI rather than seats."
            ),
        ),
        now=NOW - timedelta(days=2),
    )
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidRealFail",
        channel_id="UC3333333333333333333333",
        channel_name="Latent Space",
        title="Agent Evals Deep Dive",
        duration_seconds=1950,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0, end_ms=8000, text="Benchmark harnesses for multi-step agents."
            ),
        ),
        now=NOW - timedelta(days=1),
    )

    # Seed captionless YouTube video in METADATA_READY pipeline_status linked to tracked STANDARD_INTELLIGENCE source
    _seed_metadata_only_youtube_video(
        repo,
        source_id=source_id,
        video_id="vidNoCap002",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Captionless Product Keynote",
        description="Official keynote overview without captions.",
        duration_seconds=920,
        now=NOW - timedelta(days=4),
    )
    conn = repo._connect()
    try:
        ts = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO source_tracking_state "
            "(source_id, contract, followed_at, next_page, coverage, health, next_check_at) "
            "VALUES (?, 'source-tracking-v1', ?, 1, 'COMPLETE', 'HEALTHY', ?)",
            (source_id, ts, ts),
        )
    finally:
        conn.close()

    # Legacy run left FAILED child executions on vidDone0001 and vidRealFail
    run = repo.create_source_run(
        SourceRunWrite.manual_check_now(
            source_id=source_id,
            command_id="cmd-r4-legacy-fail",
            priority=SourceRunPriority.P1,
            created_at=NOW - timedelta(hours=2),
        )
    )
    with repo._connect() as conn:
        for vid_child in ("vidDone0001", "vidRealFail"):
            conn.execute(
                "INSERT INTO source_run_video_executions "
                "(run_id, video_id, state, created_at, updated_at) VALUES (?, ?, 'FAILED', ?, ?)",
                (
                    run.run_id,
                    vid_child,
                    (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
            )

    # Before sidecar DB exists: raw parity keeps all legacy FAILED / WAITING_CONTENT activity items
    _, intel_before = fast_app.handle("GET", "/api/v1/intelligence")
    before_act_ids = {item["video_id"] for item in intel_before["activity"]}
    assert {"vidDone0001", "vidRealFail", "vidNoCap002"}.issubset(before_act_ids)

    # Distill vidDone0001 (AVAILABLE card), vidDone0004 (second topic), and vidNoCap002 (METADATA_ONLY brief);
    # leave vidRealFail undistilled!
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidDone0001/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidDone0004/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidNoCap002/distill", b"{}")

    # 1) R4-1: Superseded FAILED (vidDone0001) and settled captionless WAITING_CONTENT (vidNoCap002)
    # are suppressed from activity, while genuinely undistilled vidRealFail remains visible!
    _, intel_after = fast_app.handle("GET", "/api/v1/intelligence")
    avail_card_vids = {
        item["card"]["video_id"]
        for item in intel_after["intelligence"]
        if item.get("status") == "AVAILABLE" and isinstance(item.get("card"), dict)
    }
    assert {"vidDone0001", "vidDone0004"}.issubset(avail_card_vids)
    after_act_by_vid = {item["video_id"]: item["status"] for item in intel_after["activity"]}
    assert "vidDone0001" not in after_act_by_vid
    assert "vidNoCap002" not in after_act_by_vid
    assert after_act_by_vid.get("vidRealFail") == "FAILED"

    # 2) R4-4: Generate Weekly Brief #1 (distilled_count == 3), then distill vidRealFail (2nd source on Agent topic)
    # and generate Weekly Brief #2 (distilled_count == 4); verify history list & ?brief_id= lookup!
    wb1_code, wb1 = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    assert wb1_code == HTTPStatus.OK
    first_brief_id = wb1["weekly_brief"]["brief_id"]
    assert wb1["weekly_brief"]["funnel_stats"]["distilled_count"] == 3

    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidRealFail/distill", b"{}")
    wb2_code, wb2 = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    assert wb2_code == HTTPStatus.OK
    second_brief_id = wb2["weekly_brief"]["brief_id"]
    assert second_brief_id != first_brief_id
    assert [h["brief_id"] for h in wb2["history"]] == [second_brief_id, first_brief_id]
    assert [h["brief_id"] for h in wb2["weekly_brief"]["history"]] == [
        second_brief_id,
        first_brief_id,
    ]

    hist_code, hist_wb1 = fast_app.handle(
        "GET", f"/api/v1/workspace-ai/weekly-brief?brief_id={first_brief_id}"
    )
    assert hist_code == HTTPStatus.OK
    assert hist_wb1["weekly_brief"]["brief_id"] == first_brief_id
    assert hist_wb1["weekly_brief"]["funnel_stats"]["distilled_count"] == 3

    miss_wb_code, _ = fast_app.handle(
        "GET", "/api/v1/workspace-ai/weekly-brief?brief_id=wb-does-not-exist"
    )
    assert miss_wb_code == HTTPStatus.NOT_FOUND

    # 3) R4-2: Topic detail exposes cross-video synthesis_zh, multi-source independence_summary_zh,
    # top_opportunities_zh, and clickable sibling related_topics (+ MOC wikilinks)
    _, topics_body = fast_app.handle("GET", "/api/v1/topics")
    agent_topic = next(
        t for t in topics_body["topics"] if t["name"] == "AI Agent 与自动化架构"
    )
    _, agent_det = fast_app.handle("GET", f"/api/v1/topics/{agent_topic['topic_id']}")
    evo = agent_det["topic"]["ai_evolution"]
    assert evo["video_count"] == 2
    assert isinstance(evo.get("synthesis_zh"), str) and len(evo["synthesis_zh"]) >= 12
    assert "2 个独立来源" in evo["independence_summary_zh"]
    assert "OpenAI" in evo["independence_summary_zh"]
    assert "Latent Space" in evo["independence_summary_zh"]
    assert len(evo["top_opportunities_zh"]) >= 1
    rel_topics = evo["related_topics"]
    assert any(rt["name"] == "AI 产品机会与一人公司变现" for rt in rel_topics)
    assert "[[AI 产品机会与一人公司变现]]" in evo["obsidian_markdown"]


def test_round5_weekly_brief_freshness_and_obsidian_vault_zip_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import io
    import zipfile

    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    source_id: str = env["source"].source_id

    clock = [NOW]
    hub._now = lambda: clock[0]

    # Store a sensitive BYOK secret in memory store to verify zero secret leakage in zip exports
    secret_marker = "sk-r5-top-secret-key-998877"
    fast_app.handle(
        "PUT",
        "/api/v1/workspace-ai/settings",
        json.dumps(
            {
                "active_mode": "local_ollama",
                "cloud_provider": "deepseek",
                "cloud_base_url": "https://api.deepseek.com/v1",
                "cloud_model": "deepseek-chat",
                "cloud_api_key": secret_marker,
            }
        ).encode("utf-8"),
    )

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR5Agent01",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Deterministic Agent Loops",
        duration_seconds=1820,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=8000,
                text="Deterministic tool loops eliminate silent retries.",
            ),
        ),
        now=clock[0],
    )
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR5Biz0002",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="Vertical AI Pricing Monetization Playbook",
        duration_seconds=1640,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=8000,
                text="Monetize vertical workflows with annual outcome contracts.",
            ),
        ),
        now=clock[0],
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR5Agent01/distill", b"{}")
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR5Biz0002/distill", b"{}")
    fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "Agent 架构与垂直定价怎么结合？"}).encode("utf-8"),
    )

    # Generate Weekly Brief #1 at t = NOW + 5m
    clock[0] = NOW + timedelta(minutes=5)
    wb1_status, wb1_res = fast_app.handle(
        "POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}"
    )
    assert wb1_status == HTTPStatus.OK
    wb1_id = wb1_res["weekly_brief"]["brief_id"]
    fresh0 = wb1_res["weekly_brief"]["freshness"]
    assert fresh0["is_stale"] is False
    assert fresh0["new_videos_count"] == 0
    assert fresh0["new_must_watch_count"] == 0

    # Distilling a <=90s Short promo after Weekly Brief #1 MUST NOT trigger false staleness!
    clock[0] = NOW + timedelta(minutes=12)
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR5Short99",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Quick 30s Teaser #shorts",
        duration_seconds=30,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0, end_ms=4000, text="Short promo clip."
            ),
        ),
        now=clock[0],
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR5Short99/distill", b"{}")
    _, after_short = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    assert after_short["weekly_brief"]["freshness"]["is_stale"] is False
    assert after_short["weekly_brief"]["freshness"]["new_videos_count"] == 0

    # Distill a new high-value Must-Watch long video at t = NOW + 25m -> marks Weekly Brief stale!
    clock[0] = NOW + timedelta(minutes=25)
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR5NewDeep",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Autonomous Security Verification",
        duration_seconds=2150,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=9000,
                text="Automated security verification catches memory bugs pre-merge.",
            ),
        ),
        now=clock[0],
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR5NewDeep/distill", b"{}")

    _, stale_wb = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    fresh_stale = stale_wb["weekly_brief"]["freshness"]
    assert fresh_stale["is_stale"] is True
    assert fresh_stale["new_videos_count"] == 1
    assert fresh_stale["new_must_watch_count"] == 1
    assert "Autonomous Security Verification" in fresh_stale["new_titles"]

    _, dash_stale = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_stale["workspace_weekly_brief"]["freshness"]["is_stale"] is True
    assert dash_stale["workspace_weekly_brief"]["freshness"]["new_videos_count"] == 1

    # Regenerate Weekly Brief #2 at t = NOW + 35m -> clears staleness; archived wb1 marks is_archive=True
    clock[0] = NOW + timedelta(minutes=35)
    _, wb2_res = fast_app.handle(
        "POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}"
    )
    assert wb2_res["weekly_brief"]["freshness"]["is_stale"] is False
    assert wb2_res["weekly_brief"]["freshness"]["new_videos_count"] == 0

    _, wb1_arch = fast_app.handle(
        "GET", f"/api/v1/workspace-ai/weekly-brief?brief_id={wb1_id}"
    )
    assert wb1_arch["weekly_brief"]["freshness"]["is_archive"] is True
    assert wb1_arch["weekly_brief"]["freshness"]["is_stale"] is False

    # Star vidR5NewDeep and export Obsidian Vault Pack (.zip) with scope=starred
    fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/vidR5NewDeep/curation",
        json.dumps({"starred": True}).encode("utf-8"),
    )

    bundle_code, bundle_json = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=starred"
    )
    assert bundle_code == HTTPStatus.OK
    assert bundle_json["scope"] == "starred"
    assert bundle_json["filename"].endswith(".zip")
    assert bundle_json["counts"]["videos"] == 1
    assert bundle_json["counts"]["video_notes"] == 1
    assert bundle_json["counts"]["topics"] == 2
    assert bundle_json["counts"]["topic_mocs"] == 2
    assert bundle_json["counts"]["weekly_briefs"] >= 1
    assert bundle_json["counts"]["research_sessions"] == 1

    raw_zip = base64.b64decode(bundle_json["archive_base64"])
    assert secret_marker.encode("utf-8") not in raw_zip
    with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert all(not n.startswith("/") and ".." not in n for n in names)
        assert "00-AI情报知识库总览 Index.md" in names
        moc_files = sorted(n for n in names if n.startswith("02-专题演化MOC/"))
        assert moc_files == [
            "02-专题演化MOC/AI Agent 与自动化架构.md",
            "02-专题演化MOC/AI 产品机会与一人公司变现.md",
        ]
        assert "03-视频深度笔记/Autonomous Security Verification.md" in names
        assert not any("Deterministic Agent Loops" in n for n in names if n.startswith("03-"))
        assert not any("Quick 30s Teaser" in n for n in names)
        index_md = zf.read("00-AI情报知识库总览 Index.md").decode("utf-8")
        assert "[[AI Agent 与自动化架构]]" in index_md
        assert "[[Autonomous Security Verification]]" in index_md

    # Binary .zip download via backup_download(scope=all) includes all 3 non-Short videos & 0 Shorts
    bin_dl = fast_app.backup_download("/api/v1/workspace-ai/obsidian-bundle.zip?scope=all")
    assert bin_dl is not None
    dl_status, dl_headers, dl_bytes = bin_dl
    assert dl_status == int(HTTPStatus.OK)
    assert dl_headers["Content-Type"] == "application/zip"
    assert "attachment; filename=" in dl_headers["Content-Disposition"]
    assert isinstance(dl_bytes, bytes)
    assert secret_marker.encode("utf-8") not in dl_bytes
    with zipfile.ZipFile(io.BytesIO(dl_bytes), "r") as zf_all:
        assert zf_all.testzip() is None
        video_notes = [n for n in zf_all.namelist() if n.startswith("03-视频深度笔记/")]
        assert len(video_notes) == 3
        assert "03-视频深度笔记/Deterministic Agent Loops.md" in video_notes
        assert "03-视频深度笔记/Vertical AI Pricing Monetization Playbook.md" in video_notes
        assert "03-视频深度笔记/Autonomous Security Verification.md" in video_notes

    # Invalid scope returns 422 VALIDATION_ERROR cleanly
    bad_code, _ = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=bad_scope"
    )
    assert bad_code == HTTPStatus.UNPROCESSABLE_ENTITY
    bad_bin = fast_app.backup_download(
        "/api/v1/workspace-ai/obsidian-bundle.zip?scope=bad_scope"
    )
    assert bad_bin is not None
    assert bad_bin[0] == int(HTTPStatus.UNPROCESSABLE_ENTITY)

    # Concurrent curation write + /api/v1/videos read stress check (zero 500s / lock errors)
    from concurrent.futures import ThreadPoolExecutor

    def _worker(idx: int) -> int:
        if idx % 2 == 0:
            code, _ = fast_app.handle(
                "POST",
                "/api/v1/workspace-ai/videos/vidR5NewDeep/curation",
                json.dumps({"is_read": bool(idx % 4 == 0)}).encode("utf-8"),
            )
            return int(code)
        code, _ = fast_app.handle("GET", "/api/v1/videos")
        return int(code)

    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(_worker, range(24)))
    assert all(s == int(HTTPStatus.OK) for s in statuses)

    # Strict Red Line: external vault directory remains 100% untouched on disk!
    assert [p for p in env["vault_root"].rglob("*") if p.is_file()] == []


def test_round6_funnel_accuracy_weekly_delta_starred_research_and_batch_curation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    source_id: str = env["source"].source_id

    clock = [NOW]
    hub._now = lambda: clock[0]

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR6Deep001",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Production Agent Eval Harness",
        duration_seconds=1800,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=9000,
                text="Deterministic eval harnesses keep agent releases safe.",
            ),
        ),
        now=clock[0] - timedelta(hours=3),
    )
    # 35s Short whose cue does NOT say 'Short promo', so raw LLM output returns MUST_WATCH 9.2
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR6Short01",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Model Launch 35s Clip",
        duration_seconds=35,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=6000,
                text="Breakthrough launch demo teaser.",
            ),
        ),
        now=clock[0] - timedelta(hours=2),
    )

    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR6Deep001/distill", b"{}")
    _, short_distilled = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidR6Short01/distill", b"{}"
    )
    assert short_distilled["ai_brief"]["is_short_noise"] is True
    assert short_distilled["ai_brief"]["recommendation_tier"] == "SKIP_NOISE"

    # Simulate legacy DB row where a Short had recommendation_tier='MUST_WATCH' alongside is_short_noise=1
    with env["hub"]._connect_write() as conn:
        conn.execute(
            "UPDATE video_ai_briefs SET recommendation_tier = 'MUST_WATCH' WHERE video_id = ?",
            ("vidR6Short01",),
        )

    _, pre_wb = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    assert pre_wb["funnel_stats"]["total_videos"] == 2
    assert pre_wb["funnel_stats"]["shorts_filtered_count"] == 1
    assert pre_wb["funnel_stats"]["must_watch_count"] == 1

    # Generate Weekly Brief #1 -> first edition has delta=None
    clock[0] = NOW + timedelta(minutes=5)
    wb1_code, wb1_res = fast_app.handle(
        "POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}"
    )
    assert wb1_code == HTTPStatus.OK
    wb1_id = wb1_res["weekly_brief"]["brief_id"]
    assert wb1_res["weekly_brief"]["delta"] is None
    assert wb1_res["weekly_brief"]["funnel_stats"]["must_watch_count"] == 1

    # Simulate legacy inflated funnel_stats_json stored on wb1 where total_videos had undistilled items
    # (mirrors live archive rows: total_videos=5, shorts=1 -> cap=4, raw must_watch=5, true non-Short must_watch at wb1=1)
    with env["hub"]._connect_write() as conn:
        conn.execute(
            "UPDATE weekly_ai_briefs SET funnel_stats_json = ? WHERE brief_id = ?",
            (
                json.dumps(
                    {
                        "total_videos": 5,
                        "distilled_count": 2,
                        "must_watch_count": 5,
                        "worth_skimming_count": 0,
                        "shorts_filtered_count": 1,
                        "topics_count": 1,
                    }
                ),
                wb1_id,
            ),
        )
    _, wb1_sanitized = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    assert wb1_sanitized["weekly_brief"]["funnel_stats"]["must_watch_count"] == 1
    assert wb1_sanitized["history"][0]["must_watch_count"] == 1

    # Distill a second Must-Watch video and generate Weekly Brief #2 -> delta compares #2 vs #1
    clock[0] = NOW + timedelta(minutes=25)
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_id,
        video_id="vidR6Biz0002",
        channel_id="UC2222222222222222222222",
        channel_name="Greg Isenberg",
        title="Vertical SaaS Monetization Playbook",
        duration_seconds=2100,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=10000,
                text="Outcome-based pricing unlocks high-margin solo AI workflows.",
            ),
        ),
        now=clock[0],
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR6Biz0002/distill", b"{}")

    clock[0] = NOW + timedelta(minutes=35)
    wb2_code, wb2_res = fast_app.handle(
        "POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}"
    )
    assert wb2_code == HTTPStatus.OK
    delta = wb2_res["weekly_brief"]["delta"]
    assert isinstance(delta, dict)
    assert delta["previous_brief_id"] == wb1_id
    assert delta["distilled_delta"] == 1
    assert delta["must_watch_delta"] == 1
    assert "vidR6Biz0002" in [p["video_id"] for p in delta["new_picks"]]
    assert delta["summary_zh"]

    _, dash_res = fast_app.handle("GET", "/api/v1/dashboard")
    assert dash_res["workspace_weekly_brief"]["delta"]["previous_brief_id"] == wb1_id

    _, wb1_arch = fast_app.handle(
        "GET", f"/api/v1/workspace-ai/weekly-brief?brief_id={wb1_id}"
    )
    assert wb1_arch["weekly_brief"]["delta"] is None
    assert wb1_arch["weekly_brief"]["funnel_stats"]["must_watch_count"] == 1

    # Starred-only research when 0 videos are starred -> 409 NO_GROUNDED_CONTENT
    empty_star_code, empty_star_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "一人公司怎么定价？", "starred_only": True}).encode(
            "utf-8"
        ),
    )
    assert empty_star_code == HTTPStatus.CONFLICT
    assert empty_star_res["error"]["code"] == "NO_GROUNDED_CONTENT"

    # Batch curation validation errors
    for bad_payload in (
        {},
        {"video_ids": [], "is_read": True},
        {"video_ids": ["vidR6Deep001"]},
        {"video_ids": ["vidR6Deep001"], "is_read": "yes"},
        {"video_ids": ["vidR6Deep001"], "is_read": True, "extra": 1},
    ):
        bad_code, _ = fast_app.handle(
            "POST",
            "/api/v1/workspace-ai/curation/batch",
            json.dumps(bad_payload).encode("utf-8"),
        )
        assert bad_code == HTTPStatus.UNPROCESSABLE_ENTITY

    miss_batch_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/curation/batch",
        json.dumps({"video_ids": ["vidR6Deep001", "ghostVid999"], "is_read": True}).encode(
            "utf-8"
        ),
    )
    assert miss_batch_code == HTTPStatus.NOT_FOUND

    # Batch mark read + reversible batch undo
    b_read_code, b_read_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/curation/batch",
        json.dumps(
            {"video_ids": ["vidR6Deep001", "vidR6Biz0002"], "is_read": True}
        ).encode("utf-8"),
    )
    assert b_read_code == HTTPStatus.OK
    assert b_read_res["updated_count"] == 2
    _, vids_after_read = fast_app.handle("GET", "/api/v1/videos")
    by_vid = {v["video_id"]: v for v in vids_after_read["videos"]}
    assert by_vid["vidR6Deep001"]["ai_brief"]["is_read"] is True
    assert by_vid["vidR6Biz0002"]["ai_brief"]["is_read"] is True

    b_undo_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/curation/batch",
        json.dumps(
            {"video_ids": ["vidR6Deep001", "vidR6Biz0002"], "is_read": False}
        ).encode("utf-8"),
    )
    assert b_undo_code == HTTPStatus.OK
    _, vids_after_undo = fast_app.handle("GET", "/api/v1/videos")
    by_vid_undo = {v["video_id"]: v for v in vids_after_undo["videos"]}
    assert by_vid_undo["vidR6Deep001"]["ai_brief"]["is_read"] is False
    assert by_vid_undo["vidR6Biz0002"]["ai_brief"]["is_read"] is False

    # Star vidR6Biz0002 via batch curation and run starred_only Cross-Video Research Q&A
    b_star_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/curation/batch",
        json.dumps({"video_ids": ["vidR6Biz0002"], "starred": True}).encode("utf-8"),
    )
    assert b_star_code == HTTPStatus.OK

    _, sessions_meta = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert sessions_meta["scope_options"]["starred_count"] == 1
    opt_vids = {v["video_id"]: v for v in sessions_meta["scope_options"]["videos"]}
    assert opt_vids["vidR6Biz0002"]["starred"] is True
    assert opt_vids["vidR6Deep001"]["starred"] is False

    star_qa_code, star_qa_res = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {"question": "一人公司应该如何切入高毛利定价？", "starred_only": True}
        ).encode("utf-8"),
    )
    assert star_qa_code == HTTPStatus.OK
    star_session = star_qa_res["session"]
    assert star_session["scope"]["starred_only"] is True
    assert "仅限已收藏" in star_session["scope_label_zh"]
    assert {c["video_id"] for c in star_session["citations"]} == {"vidR6Biz0002"}


def test_round7_weekly_markdown_delta_sync_and_source_signal_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import io
    import zipfile

    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    composition: Any = env["composition"]
    source_openai_id: str = env["source"].source_id

    source_greg = composition.product.add_source(
        url="https://www.youtube.com/channel/UC2222222222222222222222",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    source_greg_id: str = source_greg.source_id

    clock = [NOW]
    hub._now = lambda: clock[0]

    # Before sidecar DB exists, GET /api/v1/sources preserves unenriched parity
    _, pre_sources_res = fast_app.handle("GET", "/api/v1/sources")
    assert "ai_signal_by_source" not in pre_sources_res

    # Seed OpenAI: 1 deep dive + 3 short promo clips (25% signal rate)
    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_openai_id,
        video_id="vidR7OpenDeep1",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Agentic Architecture Deep Dive",
        duration_seconds=1860,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=0,
                end_ms=9000,
                text="Long-horizon agent execution relies on deterministic tool sandboxes.",
            ),
        ),
        now=clock[0] - timedelta(hours=4),
    )
    for idx in range(1, 4):
        _seed_youtube_video(
            repo,
            env["data_root"],
            source_id=source_openai_id,
            video_id=f"vidR7OpenSh0{idx}",
            channel_id="UC1111111111111111111111",
            channel_name="OpenAI",
            title=f"OpenAI Promo Clip {idx}",
            duration_seconds=30 + idx,
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=5000,
                    text=f"Quick teaser clip {idx}.",
                ),
            ),
            now=clock[0] - timedelta(hours=3, minutes=idx),
        )

    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR7OpenDeep1/distill", b"{}")
    for idx in range(1, 4):
        fast_app.handle(
            "POST", f"/api/v1/workspace-ai/videos/vidR7OpenSh0{idx}/distill", b"{}"
        )

    # Generate Weekly Brief #1 and simulate legacy inflated funnel + markdown ('精选 `48` 条必看干货')
    clock[0] = NOW + timedelta(minutes=10)
    _, wb1_res = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    wb1_id = wb1_res["weekly_brief"]["brief_id"]
    stale_md = wb1_res["weekly_brief"]["obsidian_markdown"].replace(
        "精选 `1` 条必看干货", "精选 `48` 条必看干货"
    )
    assert "精选 `48` 条必看干货" in stale_md
    with hub._connect_write() as conn:
        conn.execute(
            "UPDATE weekly_ai_briefs SET funnel_stats_json = ?, obsidian_markdown = ? WHERE brief_id = ?",
            (
                json.dumps(
                    {
                        "total_videos": 6,
                        "distilled_count": 4,
                        "must_watch_count": 48,
                        "worth_skimming_count": 0,
                        "shorts_filtered_count": 3,
                        "topics_count": 1,
                    }
                ),
                stale_md,
                wb1_id,
            ),
        )

    _, wb1_calibrated = fast_app.handle("GET", "/api/v1/workspace-ai/weekly-brief")
    wb1_md = wb1_calibrated["weekly_brief"]["obsidian_markdown"]
    assert "精选 `48` 条必看干货" not in wb1_md
    assert "精选 `1` 条必看干货" in wb1_md

    # Seed Greg Isenberg: 2 deep dives, 0 shorts (100% signal rate), mark one read
    clock[0] = NOW + timedelta(minutes=25)
    for idx, title in (
        (1, "Vertical SaaS Monetization Playbook"),
        (2, "Solo Founder AI Distribution Loops"),
    ):
        _seed_youtube_video(
            repo,
            env["data_root"],
            source_id=source_greg_id,
            video_id=f"vidR7GregDp0{idx}",
            channel_id="UC2222222222222222222222",
            channel_name="Greg Isenberg",
            title=title,
            duration_seconds=2100 + idx * 60,
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=10000,
                    text=f"High-margin B2B workflow insight {idx}.",
                ),
            ),
            now=clock[0] + timedelta(minutes=idx),
        )
        fast_app.handle(
            "POST", f"/api/v1/workspace-ai/videos/vidR7GregDp0{idx}/distill", b"{}"
        )

    fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/vidR7GregDp01/curation",
        json.dumps({"is_read": True}).encode("utf-8"),
    )

    # Verify GET /api/v1/sources returns top-level ai_signal_by_source without mutating sources[i]
    src_code, src_res = fast_app.handle("GET", "/api/v1/sources")
    assert src_code == HTTPStatus.OK
    raw_code, raw_src_res = env["raw_app"].handle("GET", "/api/v1/sources")
    assert raw_code == HTTPStatus.OK
    assert src_res["sources"] == raw_src_res["sources"]
    sig_map = src_res["ai_signal_by_source"]
    assert sig_map[source_openai_id] == {
        "source_id": source_openai_id,
        "channel_key": "OpenAI",
        "channel_label": "OpenAI",
        "total_videos": 4,
        "distilled_count": 4,
        "long_form_count": 1,
        "shorts_count": 3,
        "must_watch_count": 1,
        "worth_skimming_count": 0,
        "unread_long_count": 1,
        "avg_long_score": 9.2,
        "signal_rate_pct": 25,
    }
    assert sig_map[source_greg_id] == {
        "source_id": source_greg_id,
        "channel_key": "Greg Isenberg",
        "channel_label": "Greg Isenberg",
        "total_videos": 2,
        "distilled_count": 2,
        "long_form_count": 2,
        "shorts_count": 0,
        "must_watch_count": 2,
        "worth_skimming_count": 0,
        "unread_long_count": 1,
        "avg_long_score": 9.1,
        "signal_rate_pct": 100,
    }

    # Generate Weekly Brief #2 -> verify obsidian_markdown & Vault .zip include delta + calibrated funnel
    clock[0] = NOW + timedelta(minutes=45)
    _, wb2_res = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    wb2_md = wb2_res["weekly_brief"]["obsidian_markdown"]
    assert "精选 `3` 条必看干货" in wb2_md
    assert "较上期演进对比" in wb2_md
    assert "[[Vertical SaaS Monetization Playbook]]" in wb2_md

    _, dash_res = fast_app.handle("GET", "/api/v1/dashboard")
    assert "较上期演进对比" in dash_res["workspace_weekly_brief"]["obsidian_markdown"]

    _, bundle_res = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=must_watch"
    )
    zip_bytes = base64.b64decode(bundle_res["archive_base64"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        weekly_files = sorted(
            name for name in zf.namelist() if name.startswith("01-AI情报周报/")
        )
        assert len(weekly_files) == 2
        all_weekly_md = "\n".join(
            zf.read(name).decode("utf-8") for name in weekly_files
        )
        assert "精选 `48` 条必看干货" not in all_weekly_md
        assert "较上期演进对比" in all_weekly_md
        assert "[[Vertical SaaS Monetization Playbook]]" in all_weekly_md


def test_round8_weekly_delta_shifts_markdown_and_topic_channel_breakdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import io
    import zipfile

    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    composition: Any = env["composition"]
    source_openai_id: str = env["source"].source_id

    source_greg = composition.product.add_source(
        url="https://www.youtube.com/channel/UC2222222222222222222222",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    source_greg_id: str = source_greg.source_id

    clock = [NOW]
    hub._now = lambda: clock[0]

    # Seed 2 OpenAI videos + 1 Greg Isenberg video in the same topic cluster ('AI Agent 与自动化架构')
    for idx, (vid, src_id, cid, cname, title) in enumerate(
        (
            (
                "vidR8Open01",
                source_openai_id,
                "UC1111111111111111111111",
                "OpenAI",
                "Stateful Agent Orchestration Part 1",
            ),
            (
                "vidR8Open02",
                source_openai_id,
                "UC1111111111111111111111",
                "OpenAI",
                "Stateful Agent Orchestration Part 2",
            ),
            (
                "vidR8Greg01",
                source_greg_id,
                "UC2222222222222222222222",
                "Greg Isenberg",
                "Building Reliable AI Agent Businesses",
            ),
        ),
        start=1,
    ):
        _seed_youtube_video(
            repo,
            env["data_root"],
            source_id=src_id,
            video_id=vid,
            channel_id=cid,
            channel_name=cname,
            title=title,
            duration_seconds=1800 + idx * 60,
            cues=(
                TimedTranscriptCueWrite(
                    start_ms=0,
                    end_ms=9000,
                    text=f"Deterministic agent workflows unlock enterprise reliability {idx}.",
                ),
            ),
            now=clock[0] + timedelta(minutes=idx),
        )
        fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{vid}/distill", b"{}")

    # Mark one OpenAI video as read so unread_count differs across channels
    fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/videos/vidR8Open01/curation",
        json.dumps({"is_read": True}).encode("utf-8"),
    )

    # 1) Verify Topic Evolution unread_count & channel_breakdown on /topics and /topics/<id>
    topics_code, topics_res = fast_app.handle("GET", "/api/v1/topics")
    assert topics_code == HTTPStatus.OK
    agent_topic = next(
        t for t in topics_res["topics"] if t["name"] == "AI Agent 与自动化架构"
    )
    list_evo = agent_topic["ai_evolution"]
    assert list_evo["video_count"] == 3
    assert list_evo["unread_count"] == 2
    assert list_evo["channel_breakdown"] == [
        {
            "channel_key": "OpenAI",
            "channel_label": "OpenAI",
            "video_count": 2,
            "must_watch_count": 2,
            "unread_count": 1,
        },
        {
            "channel_key": "Greg Isenberg",
            "channel_label": "Greg Isenberg",
            "video_count": 1,
            "must_watch_count": 1,
            "unread_count": 1,
        },
    ]

    det_code, det_res = fast_app.handle(
        "GET", f"/api/v1/topics/{agent_topic['topic_id']}"
    )
    assert det_code == HTTPStatus.OK
    det_evo = det_res["topic"]["ai_evolution"]
    assert det_evo["unread_count"] == 2
    assert det_evo["channel_breakdown"] == list_evo["channel_breakdown"]
    assert "来源构成" in det_evo["obsidian_markdown"]
    assert "OpenAI" in det_evo["obsidian_markdown"]
    assert "Greg Isenberg" in det_evo["obsidian_markdown"]

    # 2) Generate Weekly Brief #1 and Weekly Brief #2 with IDENTICAL top-6 must_watch_picks (new_picks == [])
    #    but new trend shifts & product opportunities (matching real production wb-6e7a4d04edfb65d0)
    clock[0] = NOW + timedelta(minutes=20)
    _, wb1_res = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    wb1_id = wb1_res["weekly_brief"]["brief_id"]
    with hub._connect_write() as conn:
        conn.execute(
            "UPDATE weekly_ai_briefs SET top_shifts_json = ?, product_opportunities_json = ? WHERE brief_id = ?",
            (
                json.dumps(
                    [
                        {
                            "title_zh": "旧周期：单轮提示词与人工脚本拼接",
                            "detail_zh": "早期工作流依赖人工手工串联。",
                        }
                    ],
                    ensure_ascii=False,
                ),
                json.dumps(["旧期通用聊天机器人模板"], ensure_ascii=False),
                wb1_id,
            ),
        )

    clock[0] = NOW + timedelta(minutes=45)
    _, wb2_res = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    wb2 = wb2_res["weekly_brief"]
    assert wb2["delta"]["new_picks"] == []
    assert wb2["delta"]["new_shifts_zh"] == ["Agent 从 Demo 走向受控状态机与离线评测"]
    assert wb2["delta"]["new_opportunities_zh"] == ["面向创作者与研究者的本地优先多源情报工作台"]
    wb2_md = wb2["obsidian_markdown"]
    assert "本期新趋势风向" in wb2_md
    assert "Agent 从 Demo 走向受控状态机与离线评测" in wb2_md
    assert "本期新产品切口" in wb2_md
    assert "面向创作者与研究者的本地优先多源情报工作台" in wb2_md

    # Idempotency check: re-synchronizing markdown must never duplicate delta bullets
    resynced_md = WorkspaceIntelligenceHub._synchronize_weekly_obsidian_markdown(
        wb2_md,
        funnel_stats=wb2["funnel_stats"],
        delta=wb2["delta"],
    )
    assert resynced_md == wb2_md
    assert resynced_md.count("本期新趋势风向") == 1
    assert resynced_md.count("本期新产品切口") == 1

    # Verify /dashboard and Vault .zip export carry the synchronized shift & opportunity bullets
    _, dash_res = fast_app.handle("GET", "/api/v1/dashboard")
    assert "本期新趋势风向" in dash_res["workspace_weekly_brief"]["obsidian_markdown"]

    _, bundle_res = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=must_watch"
    )
    zip_bytes = base64.b64decode(bundle_res["archive_base64"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        weekly_files = sorted(
            name for name in zf.namelist() if name.startswith("01-AI情报周报/")
        )
        all_weekly_md = "\n".join(
            zf.read(name).decode("utf-8") for name in weekly_files
        )
        assert "本期新趋势风向" in all_weekly_md
        assert "Agent 从 Demo 走向受控状态机与离线评测" in all_weekly_md
        assert "本期新产品切口" in all_weekly_md


def test_round9_research_session_pin_delete_backup_and_vault_zip_ordering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import io
    import zipfile

    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    source_openai_id: str = env["source"].source_id

    clock = [NOW]
    hub._now = lambda: clock[0]

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_openai_id,
        video_id="vidR9Open01",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Reliable Stateful Agent Architecture",
        duration_seconds=2400,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=15000,
                end_ms=42000,
                text="Explicit state machines and deterministic evals prevent cascading agent failures.",
            ),
        ),
        now=NOW - timedelta(hours=2),
    )
    fast_app.handle("POST", "/api/v1/workspace-ai/videos/vidR9Open01/distill", b"{}")

    # Create 3 research Q&A sessions at ascending timestamps
    clock[0] = NOW + timedelta(minutes=1)
    _, res_q1 = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {
                "question": "核心共识架构：Agent 状态机如何防崩溃？",
                "channel_key": "OpenAI",
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )
    q1_id = res_q1["session"]["session_id"]
    assert res_q1["session"]["pinned"] is False
    q1_scope_label = res_q1["session"]["scope_label_zh"]
    assert "OpenAI" in q1_scope_label

    clock[0] = NOW + timedelta(minutes=2)
    _, res_q2 = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "临时实验测试提问 123"}, ensure_ascii=False).encode("utf-8"),
    )
    q2_id = res_q2["session"]["session_id"]

    clock[0] = NOW + timedelta(minutes=3)
    _, res_q3 = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "最新商业化定价模型拆解"}, ensure_ascii=False).encode("utf-8"),
    )
    q3_id = res_q3["session"]["session_id"]

    # Initially chronological newest-first: [q3, q2, q1], all unpinned
    _, init_list = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert [s["session_id"] for s in init_list["sessions"]] == [q3_id, q2_id, q1_id]
    assert all(s["pinned"] is False for s in init_list["sessions"])

    # Pin oldest session q1 -> floats to #1 while preserving scope_label_zh
    pin_code, pin_body = fast_app.handle(
        "POST",
        f"/api/v1/workspace-ai/research/sessions/{q1_id}/pin",
        json.dumps({"pinned": True}).encode("utf-8"),
    )
    assert pin_code == HTTPStatus.OK
    assert pin_body["session"]["session_id"] == q1_id
    assert pin_body["session"]["pinned"] is True
    assert pin_body["session"]["scope_label_zh"] == q1_scope_label

    _, pinned_list = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert [s["session_id"] for s in pinned_list["sessions"]] == [q1_id, q3_id, q2_id]
    assert pinned_list["sessions"][0]["pinned"] is True
    assert pinned_list["sessions"][0]["scope_label_zh"] == q1_scope_label

    # Validation & missing-ID guards
    nf_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/sessions/qa-nonexistent/pin",
        json.dumps({"pinned": True}).encode("utf-8"),
    )
    assert nf_code == HTTPStatus.NOT_FOUND
    bad_code, _ = fast_app.handle(
        "POST",
        f"/api/v1/workspace-ai/research/sessions/{q1_id}/pin",
        json.dumps({"pinned": "yes"}).encode("utf-8"),
    )
    assert bad_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Zero-DDL backup & restore preserves pinned state inside scope_json
    _, bk_snap = fast_app.handle("GET", "/api/v1/workspace-ai/backup")
    (env["project_root"] / ".workspace-ai" / "hub.sqlite3").unlink()
    rs_code, _ = fast_app.handle(
        "POST", "/api/v1/workspace-ai/restore", json.dumps(bk_snap).encode("utf-8")
    )
    assert rs_code == HTTPStatus.OK
    _, after_restore = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert [s["session_id"] for s in after_restore["sessions"]] == [q1_id, q3_id, q2_id]
    assert after_restore["sessions"][0]["pinned"] is True

    # Delete throwaway session q2 -> removed from list & Vault .zip; repeat delete -> 404
    del_code, del_body = fast_app.handle(
        "POST",
        f"/api/v1/workspace-ai/research/sessions/{q2_id}/delete",
        b"{}",
    )
    assert del_code == HTTPStatus.OK
    assert del_body == {"deleted": True, "session_id": q2_id}

    del_again_code, _ = fast_app.handle(
        "DELETE",
        f"/api/v1/workspace-ai/research/sessions/{q2_id}",
        b"",
    )
    assert del_again_code == HTTPStatus.NOT_FOUND

    _, after_del = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert [s["session_id"] for s in after_del["sessions"]] == [q1_id, q3_id]

    # Vault .zip export places pinned q1 first with **[置顶]** marker and excludes deleted q2
    _, bundle_res = fast_app.handle(
        "GET", "/api/v1/workspace-ai/obsidian-bundle?scope=must_watch"
    )
    assert bundle_res["counts"]["research_sessions"] == 2
    idx_md = bundle_res["index_markdown"]
    assert "临时实验测试提问 123" not in idx_md
    pos_q1 = idx_md.index("**[置顶]**")
    assert "核心共识架构：Agent 状态机如何防崩溃？" in idx_md[pos_q1:]
    pos_q3 = idx_md.index("最新商业化定价模型拆解")
    assert pos_q1 < pos_q3
    zip_bytes = base64.b64decode(bundle_res["archive_base64"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        qa_files = sorted(
            name for name in zf.namelist() if name.startswith("04-跨视频深度问答/")
        )
        assert len(qa_files) == 2
        assert all("临时实验测试提问" not in name for name in qa_files)

    # Unpin q1 -> chronological order [q3, q1] restored
    unpin_code, unpin_body = fast_app.handle(
        "POST",
        f"/api/v1/workspace-ai/research/sessions/{q1_id}/pin",
        json.dumps({"pinned": False}).encode("utf-8"),
    )
    assert unpin_code == HTTPStatus.OK
    assert unpin_body["session"]["pinned"] is False
    _, final_list = fast_app.handle("GET", "/api/v1/workspace-ai/research/sessions")
    assert [s["session_id"] for s in final_list["sessions"]] == [q3_id, q1_id]


def test_round10_intelligence_list_and_detail_expose_linked_topics_when_sidecar_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]
    repo: SQLiteStateRepository = env["repo"]
    source_openai_id: str = env["source"].source_id

    _seed_youtube_video(
        repo,
        env["data_root"],
        source_id=source_openai_id,
        video_id="vidR10Open01",
        channel_id="UC1111111111111111111111",
        channel_name="OpenAI",
        title="Stateful Multi-Agent Tool Contracts",
        duration_seconds=2100,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=12000,
                end_ms=36000,
                text="Deterministic state machines and schema-validated tool contracts keep agent loops reliable.",
            ),
        ),
        now=NOW - timedelta(hours=1),
    )
    distill_code, _ = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidR10Open01/distill", b"{}"
    )
    assert distill_code == HTTPStatus.OK

    list_code, list_payload = fast_app.handle("GET", "/api/v1/intelligence")
    assert list_code == HTTPStatus.OK
    available = [
        item
        for item in list_payload["intelligence"]
        if item.get("status") == "AVAILABLE" and item.get("trusted") is True
    ]
    assert len(available) == 1
    intel_item = available[0]
    intel_id = str(intel_item["intelligence_id"])

    assert "linked_topics" in intel_item
    assert len(intel_item["linked_topics"]) == 1
    assert intel_item["linked_topics"][0]["name"] == "AI Agent 与自动化架构"
    assert intel_item["linked_topics"][0]["topic_id"].startswith("topic:")

    detail_code, detail_payload = fast_app.handle(
        "GET", f"/api/v1/intelligence/{intel_id}"
    )
    assert detail_code == HTTPStatus.OK
    assert detail_payload["intelligence"]["linked_topics"] == intel_item["linked_topics"]

    # Without sidecar DB, /api/v1/intelligence preserves exact raw LocalApiApplication parity
    sidecar_db = env["project_root"] / ".workspace-ai" / "hub.sqlite3"
    sidecar_backup = sidecar_db.read_bytes()
    sidecar_db.unlink()
    try:
        fast_app._bump_mutation_epoch()
        _, raw_list = fast_app.handle("GET", "/api/v1/intelligence")
        assert "linked_topics" not in raw_list["intelligence"][0]
    finally:
        sidecar_db.write_bytes(sidecar_backup)


def test_ux_audit_d1_local_markdown_distill_omits_fake_timestamps_while_video_requires_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    md_code, md_imp = fast_app.handle(
        "POST",
        "/api/v1/local/imports?filename=agent-notes.md",
        b"# Agent Notes\n\nDeterministic tool contracts prevent silent failures in agent workflows.\n",
    )
    assert md_code == HTTPStatus.CREATED
    md_id = md_imp["import"]["content_id"]

    distill_code, distill_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{md_id}/distill", b"{}"
    )
    assert distill_code == HTTPStatus.OK
    assert "[00:00]" not in distill_body["ai_brief"]["obsidian_markdown"]

    detail_code, detail_payload = fast_app.handle("GET", f"/api/v1/videos/{md_id}")
    assert detail_code == HTTPStatus.OK
    assert "[00:00]" not in detail_payload["obsidian_markdown"]
    assert all(
        not pt.get("timestamp") and pt.get("start_ms") is None
        for pt in detail_payload["note"]["v2"]["timestamped_key_points"]
    )

    mp4_path = tmp_path / "no-captions.mp4"
    subprocess.run(
        [
            media_tool("ffmpeg"),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x32:r=5:d=1",
            str(mp4_path),
        ],
        check=True,
        capture_output=True,
        timeout=20,
    )
    vid_code, vid_imp = fast_app.handle(
        "POST",
        "/api/v1/local/imports?filename=no-captions.mp4",
        mp4_path.read_bytes(),
    )
    assert vid_code == HTTPStatus.CREATED
    vid_id = vid_imp["import"]["content_id"]

    fail_code, fail_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{vid_id}/distill", b"{}"
    )
    assert fail_code == HTTPStatus.CONFLICT
    assert fail_body["error"]["code"] == "TRANSCRIPT_REQUIRED"


def test_ux_audit_g1_research_suggested_questions_grounded_without_hardcoded_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    fast_app: Any = env["fast_app"]

    empty_code, empty_payload = fast_app.handle(
        "GET", "/api/v1/workspace-ai/research/sessions"
    )
    assert empty_code == HTTPStatus.OK
    empty_questions = empty_payload["suggested_questions"]
    assert len(empty_questions) >= 2
    assert all(
        "Greg Isenberg" not in q and "GPT-6 Cyber" not in q for q in empty_questions
    )

    _seed_youtube_video(
        env["repo"],
        env["data_root"],
        source_id=env["source"].source_id,
        video_id="vidG1Karp01",
        channel_id="UC2222222222222222222222",
        channel_name="Andrej Karpathy",
        title="Tokenization and Transformer Internals",
        duration_seconds=2400,
        cues=(
            TimedTranscriptCueWrite(
                start_ms=1000,
                end_ms=20000,
                text="Byte pair encoding and deterministic evals shape model behavior.",
            ),
        ),
        now=NOW - timedelta(hours=1),
    )
    distill_code, _ = fast_app.handle(
        "POST", "/api/v1/workspace-ai/videos/vidG1Karp01/distill", b"{}"
    )
    assert distill_code == HTTPStatus.OK

    seeded_code, seeded_payload = fast_app.handle(
        "GET", "/api/v1/workspace-ai/research/sessions"
    )
    assert seeded_code == HTTPStatus.OK
    seeded_questions = seeded_payload["suggested_questions"]
    assert all(
        "Greg Isenberg" not in q and "GPT-6 Cyber" not in q for q in seeded_questions
    )
    assert any(
        "Andrej Karpathy" in q or "AI Agent 与自动化架构" in q
        for q in seeded_questions
    )




