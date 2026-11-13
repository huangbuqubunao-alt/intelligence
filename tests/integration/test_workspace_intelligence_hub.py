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
from youtube_intel.local_content import LocalContentProvider, MediaTranscript
from youtube_intel.offline_transcription import media_tool
from youtube_intel.orchestration import ProcessingPolicy
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
