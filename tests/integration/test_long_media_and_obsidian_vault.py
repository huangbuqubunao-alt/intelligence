"""Integration tests for 4h media, 300KB Markdown, and Obsidian Vault ZIP export."""

from __future__ import annotations

import io
import json
import re
import struct
import wave
import zipfile
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
import yaml

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
from youtube_intel.local_content import (
    LocalContentProvider,
    LocalImportError,
    MediaTranscript,
)
from youtube_intel.offline_transcription import OfflineError
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.providers.bilibili import (
    BilibiliAdapter,
    BilibiliIdentity,
    BilibiliMetadata,
    CaptionAcquisition,
    parse_captions,
)
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_authority import MAX_TEXT_BYTES, sha256, write_managed
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

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 22, 10, 0, tzinfo=UTC)


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


class _HardeningCompleter:
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
            sec_indices = [int(x) for x in re.findall(r"\[S(\d+)\]", user_prompt)]
            first_idx = sec_indices[0] if sec_indices else 0
            last_idx = sec_indices[-1] if sec_indices else first_idx
            return (
                {
                    "headline_zh": "超长 Markdown 文档全篇均匀采样提炼（覆盖开篇与结尾边界）",
                    "summary_zh": "对超长多语种 Markdown 笔记完成均匀章节覆盖提炼，并生成不可变段落偏移引用。",
                    "score": 8.9,
                    "score_reason_zh": "兼具系统深度与可审计段落定位。",
                    "recommendation_tier": "MUST_WATCH",
                    "content_bucket": "DEEP_DIVE",
                    "topics_zh": ["超长文本边界", "Obsidian导出"],
                    "topic_cluster_zh": "AI Agent 与自动化架构",
                    "core_points": [
                        {"text_zh": "开篇确立 WAL 确定性事务边界", "section_index": first_idx},
                        {"text_zh": "尾章验证 96% 处核心不变量索引", "section_index": last_idx},
                    ],
                    "product_opportunities_zh": ["超长本地研究文档全篇均匀覆盖"],
                    "business_opportunities_zh": ["深度研究员高可靠性笔记导出"],
                    "filtered_noise_zh": [],
                },
                provider,
                model,
            )

        if "WEEKLY_BRIEF_SCHEMA" in system_prompt:
            return (
                {
                    "title_zh": '本周 "Agent 运行时" 专题与长文档归档周报',
                    "executive_summary_zh": "聚焦 4 小时长课程、超长 Markdown 文档全篇覆盖及 Obsidian Vault 安全导出。",
                    "top_shifts_zh": [
                        {
                            "title_zh": "长媒体与超长文本证据均匀覆盖",
                            "detail_zh": "从头至尾覆盖长音频与 300KB+ Markdown 文档关键不变量。",
                            "topic_name": "AI Agent 与自动化架构",
                        }
                    ],
                    "product_opportunities_zh": ["一键导出无损 Obsidian Vault .zip"],
                    "business_opportunities_zh": ["本地知识工作台可信度护城河"],
                },
                provider,
                model,
            )

        if "RESEARCH_QA_SCHEMA" in system_prompt:
            matches = re.findall(r"\[(E\d+)\]\s*(视频|本地文档)《([^》]+)》", user_prompt)
            picked: list[str] = []
            for ref, _kind, _title in matches:
                if ref not in picked:
                    picked.append(ref)
                if len(picked) >= 2:
                    break
            tags = "、".join(f"[{r}]" for r in picked)
            return (
                {
                    "answerable": bool(picked),
                    "answer_zh": (
                        f"已从可核验原话/原文证据（{tags}）定位关键工程不变量并绑定精确位置。"
                    ),
                    "key_takeaways_zh": [
                        "4 小时课程支持精确到小时级 HH:MM:SS 时间戳证据链",
                        "超长 Markdown 文档尾段经 FTS5 与均匀采样可稳定召回",
                    ],
                    "action_items_zh": [
                        "导出 Obsidian Vault ZIP 包验证双链与 YAML Frontmatter",
                    ],
                    "citations": [
                        {"ref": ref, "note_zh": f"基于核验引用 {ref} 的原始记录"}
                        for ref in picked
                    ],
                },
                provider,
                model,
            )

        win_indices = [int(x) for x in re.findall(r"\[W(\d+)\]", user_prompt)]
        win_idx = win_indices[-1] if win_indices else 0
        return (
            {
                "headline_zh": '深入拆解 "Runtime" 状态机与可移植引用归档',
                "summary_zh": "聚焦确定性时间轴证据抽取、安全标题清洗与 Obsidian 双链笔记沉淀。",
                "score": 9.1,
                "score_reason_zh": "结构严谨且具备可验证时间锚点。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["AI Agent 与自动化架构", "Obsidian 归档"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [
                    {
                        "text_zh": "关键论点锚定至确定性媒体时间戳",
                        "cue_window_index": win_idx,
                    }
                ],
                "product_opportunities_zh": ["长视频关键锚点全自动双链导出"],
                "business_opportunities_zh": ["本地知识库高价值订阅工作流"],
                "filtered_noise_zh": [],
            },
            provider,
            model,
        )


class _ObsidianBiliAdapter(BilibiliAdapter):
    def __init__(self, *, now: datetime) -> None:
        super().__init__(fetch=lambda *_args: b"{}")
        self._now = now

    def fetch_metadata(self, identity: BilibiliIdentity) -> BilibiliMetadata:
        return BilibiliMetadata(
            identity=identity,
            cid=71009999,
            title="CON",
            uploader_id="998877",
            uploader_name="B站测评组",
            published_at=self._now - timedelta(minutes=5),
            duration=600.0,
            acquired_at=self._now,
        )

    def fetch_caption(self, metadata: BilibiliMetadata) -> CaptionAcquisition:
        raw = json.dumps(
            {
                "body": [
                    {
                        "from": 42.0,
                        "to": 55.0,
                        "content": "BetaGuard neutralizes reserved Windows stems before ZIP extraction.",
                    }
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
        return CaptionAcquisition(
            status="READY",
            transcript=parse_captions(raw, language="zh-Hans", duration=metadata.duration),
            subtitle_id="3002",
            language_name="中文（人工校准）",
            source_url="https://aisubtitle.hdslb.com/bfs/subtitle/obsidian_b1.json",
        )


def _make_tiny_wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<" + "h" * 1600, *([0] * 1600)))
    return buf.getvalue()


def _seed_timed_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    source_id: str,
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str,
    source_url: str,
    provider: str,
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
            description=f"{title} overview.",
            source_url=source_url,
            published_at=now,
            duration_seconds=duration_seconds,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=now,
    )
    repo.link_source_video(source_id=source_id, video_id=video_id, discovered_at=now)
    canonical_bytes = "\n".join(c.text for c in cues).encode("utf-8")
    rel_path = f"transcripts/canonical/{video_id}.txt"
    write_managed(data_root, rel_path, canonical_bytes)
    art_id = f"canonical:{video_id}"
    repo.upsert_artifact(
        ArtifactWrite(
            artifact_id=art_id,
            artifact_key=art_id,
            video_id=video_id,
            job_id=None,
            kind=ArtifactKind.TRANSCRIPT_CANONICAL,
            storage_root=StorageRoot.DATA,
            relative_path=rel_path,
            content_hash=sha256(canonical_bytes),
            provider=provider.lower(),
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
    ExtractiveSummaryService(repo, data_root).create(video_id, now=now)


def _build_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    monkeypatch.setattr(
        "youtube_intel.deep_analysis_activation._local_probe", lambda *args: "MODEL_UNAVAILABLE"
    )
    project_root = (tmp_path / "isolated_workspace").resolve()
    for sub in ("data", "logs", "templates", "vault"):
        (project_root / sub).mkdir(parents=True, exist_ok=True)
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
        url="https://www.youtube.com/channel/UC7777777777777777777777",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    hub = WorkspaceIntelligenceHub(
        repository=composition.repository,
        data_root=project_root / "data",
        project_root=project_root,
        byok_credential_store=_MemorySecret(),
        llm_completer=_HardeningCompleter(),
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


def _parse_frontmatter(markdown_text: str) -> tuple[dict[str, Any], str]:
    assert markdown_text.startswith("---\n"), "Missing YAML frontmatter start"
    parts = markdown_text.split("\n---\n", 1)
    assert len(parts) == 2, "Missing YAML frontmatter closing delimiter"
    parsed = yaml.safe_load(parts[0][4:])
    assert isinstance(parsed, dict)
    return parsed, parts[1]


def test_four_hour_lecture_boundary_normalization_distill_and_qa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    duration_sec = 14390.0  # 03:59:50 (just below 4-hour 14400s limit)
    raw_segments: list[dict[str, object]] = []
    step = duration_sec / 3200.0
    for idx in range(3200):
        s_val = idx * step
        e_val = s_val + (step * 0.85)
        text = (
            "HyperionEpoch 03:52 deterministic checkpoint guarantees zero-loss lecture recovery."
            if abs(s_val - 13930.0) < step
            else f"Lecture chapter {idx} explaining local verification architecture."
        )
        raw_segments.append({"start": s_val, "end": e_val, "text": text})

    with pytest.raises(OfflineError) as err_over:
        _normalize_mlx_lecture_segments(
            raw_segments[:10],
            duration_seconds=14401.0,
            language="en",
            provenance="test-4h",
        )
    assert err_over.value.code == "TRANSCRIPT_INVALID"

    transcript = _normalize_mlx_lecture_segments(
        raw_segments,
        duration_seconds=duration_sec,
        language="en",
        provenance="test-4h-norm",
    )
    assert 1 <= len(transcript.cues) <= 2400
    assert any("HyperionEpoch" in cue.text for cue in transcript.cues)

    env = _build_env(tmp_path, monkeypatch)
    repo: SQLiteStateRepository = env["repo"]
    fast_app: FastReadApiApplication = env["fast_app"]
    wav_bytes = _make_tiny_wav_bytes()

    probed_duration = [14401.0]
    monkeypatch.setattr(
        "youtube_intel.offline_transcription.media_tool",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "youtube_intel.offline_transcription.run_bounded",
        lambda *_args, **_kwargs: json.dumps(
            {
                "streams": [{"codec_type": "audio"}],
                "format": {"format_name": "wav", "duration": str(probed_duration[0])},
            }
        ).encode("utf-8"),
    )

    class _Stub4hTranscriber:
        def transcribe(self, snapshot: Path, *, duration_seconds: float) -> MediaTranscript:
            assert snapshot.is_file()
            assert abs(duration_seconds - 14390.0) < 0.01
            return transcript

    provider = LocalContentProvider(
        repo,
        env["data_root"],
        now=lambda: NOW,
        transcriber=_Stub4hTranscriber(),
    )

    with pytest.raises(LocalImportError) as err_too_long:
        provider.import_bytes("over_four_hours.wav", wav_bytes)
    assert err_too_long.value.code == "LOCAL_MEDIA_TOO_LONG"

    probed_duration[0] = duration_sec
    res = provider.import_bytes("distributed_systems_4h_lecture.wav", wav_bytes)
    assert res.status == "READY"
    lecture_id = res.content_id

    dist_code, dist_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{lecture_id}/distill", b"{}"
    )
    assert dist_code == HTTPStatus.OK
    brief_md = str(dist_body["ai_brief"]["obsidian_markdown"])
    assert 'duration: "03:59:50"' in brief_md

    ask_code, ask_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {"question": "What does HyperionEpoch 03:52 deterministic checkpoint guarantee?"}
        ).encode("utf-8"),
    )
    assert ask_code == HTTPStatus.OK
    session = ask_body["session"]
    assert session["refused"] is False
    cites = [c for c in session["citations"] if c["video_id"] == lecture_id]
    assert cites
    assert cites[0]["locator_type"] == "TIME_RANGE"
    assert cites[0]["timestamp_label"].startswith("03:5")
    assert "HyperionEpoch" in cites[0]["excerpt"]


def test_large_300kb_mixed_markdown_boundary_uniform_distill_and_tail_qa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    repo: SQLiteStateRepository = env["repo"]
    hub: WorkspaceIntelligenceHub = env["hub"]
    fast_app: FastReadApiApplication = env["fast_app"]

    provider = LocalContentProvider(repo, env["data_root"], now=lambda: NOW)

    with pytest.raises(LocalImportError) as err_empty:
        provider.import_bytes("empty.md", b"")
    assert err_empty.value.code == "LOCAL_EMPTY_FILE"

    with pytest.raises(LocalImportError) as err_ws:
        provider.import_bytes("whitespace.md", b"   \n")
    assert err_ws.value.code == "LOCAL_INVALID_TEXT"

    with pytest.raises(LocalImportError) as err_nul:
        provider.import_bytes("nul.md", b"# Heading\n\x00bad")
    assert err_nul.value.code == "LOCAL_INVALID_TEXT"

    with pytest.raises(LocalImportError) as err_large:
        provider.import_bytes("huge.md", b"a" * (MAX_TEXT_BYTES + 1))
    assert err_large.value.code == "LOCAL_FILE_TOO_LARGE"

    lines: list[str] = [
        "# 系统设计长篇手记 (300KB Boundary Corpus)",
        "",
        "OpeningMarker: WAL 确定性事务在所有异构数据源入库前必须完成原子提交与哈希锁定。",
    ]
    for idx in range(2900):
        if idx == 1450:
            lines.append(
                "MidSectionAnchor: 第 50% 中段章节聚焦 FTS5 Unicode61 分词与增量索引一致性。"
            )
        elif idx == 2790:
            lines.append(
                "ObsidianCanopy 96pct tail invariant guarantees full-document coverage past 2048 lines."
            )
        else:
            lines.append(
                f"- 第 {idx:04d} 条技术笔记记录：{idx} 号批次包含本地 Markdown 与流式状态归档检查点。"
            )
    doc_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    assert len(doc_bytes) > 300_000

    res = provider.import_bytes("architecture_long_notes_300kb.md", doc_bytes)
    assert res.status == "READY"
    doc_id = res.content_id

    segments = hub._load_verified_local_text_segments(doc_id)
    assert len(segments) > 120
    sections = hub._build_text_evidence_sections(segments)
    assert len(sections) == 8
    total_chars = len(doc_bytes.decode("utf-8"))
    assert sections[0].start_offset < int(total_chars * 0.05)
    assert any(
        int(total_chars * 0.40) <= sec.start_offset <= int(total_chars * 0.65)
        for sec in sections
    )
    assert sections[-1].end_offset > int(total_chars * 0.85)
    for sec in sections:
        assert sec.start_offset < sec.end_offset
        assert sec.evidence_ids
        assert str(sec.start_offset) in sec.locator_label
        assert str(sec.end_offset) in sec.locator_label

    dist_code, dist_body = fast_app.handle(
        "POST", f"/api/v1/workspace-ai/videos/{doc_id}/distill", b"{}"
    )
    assert dist_code == HTTPStatus.OK
    brief_md = str(dist_body["ai_brief"]["obsidian_markdown"])
    assert "[00:00]" not in brief_md

    ask_code, ask_body = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps({"question": "What does ObsidianCanopy 96pct tail invariant guarantee?"}).encode(
            "utf-8"
        ),
    )
    assert ask_code == HTTPStatus.OK
    session = ask_body["session"]
    assert session["refused"] is False
    doc_cites = [c for c in session["citations"] if c["video_id"] == doc_id]
    assert doc_cites
    cite = doc_cites[0]
    assert cite["locator_type"] == "TEXT_RANGE"
    assert cite["start_ms"] is None
    assert cite["paragraph_index"] > 100
    assert "00:00" not in cite["timestamp_label"]

    verified_tail = repo.resolve_verified_evidence_text(cite["evidence_id"])
    assert verified_tail is not None
    assert "ObsidianCanopy 96pct tail invariant" in verified_tail.excerpt

    ev_code, ev_body = fast_app.handle("GET", f"/api/v1/videos/{doc_id}/evidence")
    assert ev_code == HTTPStatus.OK
    assert ev_body["evidence"]


def test_obsidian_vault_zip_real_extraction_yaml_blank_lines_and_wikilinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _build_env(tmp_path, monkeypatch)
    repo: SQLiteStateRepository = env["repo"]
    fast_app: FastReadApiApplication = env["fast_app"]
    source_id = env["source"].source_id

    long_cjk_title = (
        "深度架构分析：" + ("超长中文知识库归档稳定性评测" * 9) + ' "Quoted" / Col:on [Test]'
    )
    assert len(long_cjk_title.encode("utf-8")) > 340

    seeded_videos = [
        (
            "vidYT000001",
            "https://www.youtube.com/watch?v=vidYT000001&list=PLtest",
            "YOUTUBE",
            "Deep Dive Channel",
            long_cjk_title,
            (
                TimedTranscriptCueWrite(
                    start_ms=65000,
                    end_ms=78000,
                    text="AlphaSignal architecture pins immutable citations to timestamps.",
                ),
            ),
            NOW,
        ),
        (
            "vidCaseA003",
            "https://www.youtube.com/watch?v=vidCaseA003",
            "YOUTUBE",
            "Case Channel",
            "Agent Runtime Guide",
            (
                TimedTranscriptCueWrite(
                    start_ms=10000,
                    end_ms=22000,
                    text="Uppercase title runtime guide discussion.",
                ),
            ),
            NOW - timedelta(minutes=10),
        ),
        (
            "vidCaseB004",
            "https://www.youtube.com/watch?v=vidCaseB004",
            "YOUTUBE",
            "Case Channel",
            "agent runtime guide",
            (
                TimedTranscriptCueWrite(
                    start_ms=15000,
                    end_ms=26000,
                    text="Lowercase title case-collision verification.",
                ),
            ),
            NOW - timedelta(minutes=15),
        ),
        (
            "vidDupA0005",
            "https://www.youtube.com/watch?v=vidDupA0005",
            "YOUTUBE",
            "Dup Channel",
            "Weekly Architecture Review",
            (
                TimedTranscriptCueWrite(
                    start_ms=20000,
                    end_ms=32000,
                    text="First duplicate title verification video.",
                ),
            ),
            NOW - timedelta(minutes=20),
        ),
        (
            "vidDupB0006",
            "https://www.youtube.com/watch?v=vidDupB0006",
            "YOUTUBE",
            "Dup Channel",
            "Weekly Architecture Review",
            (
                TimedTranscriptCueWrite(
                    start_ms=25000,
                    end_ms=38000,
                    text="Second duplicate title verification video.",
                ),
            ),
            NOW - timedelta(minutes=25),
        ),
    ]

    for vid, url, prov, ch_name, title, cues, ts in seeded_videos:
        _seed_timed_video(
            repo,
            env["data_root"],
            source_id=source_id,
            video_id=vid,
            channel_id=f"UC_{prov}",
            channel_name=ch_name,
            title=title,
            source_url=url,
            provider=prov,
            duration_seconds=600,
            cues=cues,
            now=ts,
        )
        d_code, _ = fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{vid}/distill", b"{}")
        assert d_code == HTTPStatus.OK

    bili_provider = BilibiliContentProvider(
        repo,
        env["data_root"],
        adapter=_ObsidianBiliAdapter(now=NOW - timedelta(minutes=5)),
        now=lambda: NOW - timedelta(minutes=5),
    )
    bili_res = bili_provider.import_input("https://www.bilibili.com/video/BV1Crs3Mdxk1/")
    bili_id = bili_res.content_id
    assert (
        fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{bili_id}/distill", b"{}")[0]
        == HTTPStatus.OK
    )

    local_provider = LocalContentProvider(repo, env["data_root"], now=lambda: NOW)
    md_res = local_provider.import_bytes(
        "local_runtime_notes.md",
        b"# Local Runtime Notes\n\nAlphaSignal must match immutable TEXT_RANGE offsets without synthetic 00:00.\n",
    )
    assert md_res.status == "READY"
    md_id = md_res.content_id
    assert (
        fast_app.handle("POST", f"/api/v1/workspace-ai/videos/{md_id}/distill", b"{}")[0]
        == HTTPStatus.OK
    )

    wb_code, _ = fast_app.handle("POST", "/api/v1/workspace-ai/weekly-brief/generate", b"{}")
    assert wb_code == HTTPStatus.OK
    qa_code, _ = fast_app.handle(
        "POST",
        "/api/v1/workspace-ai/research/ask",
        json.dumps(
            {"question": 'How do "AlphaSignal" & BetaGuard verify runtime notes?'}
        ).encode("utf-8"),
    )
    assert qa_code == HTTPStatus.OK

    zip_dl = fast_app.backup_download("/api/v1/workspace-ai/obsidian-bundle.zip?scope=all")
    assert zip_dl is not None
    dl_status, _, dl_payload = zip_dl
    assert dl_status == HTTPStatus.OK
    raw_zip = dl_payload if isinstance(dl_payload, bytes) else Path(dl_payload).read_bytes()

    extract_dir = tmp_path / "extracted_vault"
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        archive_names = zf.namelist()
        for entry_name in archive_names:
            basename = Path(entry_name).name
            assert len(basename.encode("utf-8")) <= 240
            assert not basename.upper().startswith("CON.")
        zf.extractall(extract_dir)

    extracted_files = sorted(p for p in extract_dir.rglob("*.md") if p.is_file())
    assert len(extracted_files) == len(archive_names)
    extracted_stems = {p.stem for p in extracted_files}

    index_text = (extract_dir / "00-AI情报知识库总览 Index.md").read_text(encoding="utf-8")
    _, index_body = _parse_frontmatter(index_text)
    for target in re.findall(r"\[\[([^\]]+)\]\]", index_body):
        assert target in extracted_stems

    video_notes = sorted((extract_dir / "03-视频深度笔记").glob("*.md"))
    assert len(video_notes) == 7

    found_local_md_note = False
    found_yt_deep_link = False
    found_bili_deep_link = False
    for md_path in extracted_files:
        content = md_path.read_text(encoding="utf-8")
        assert content.endswith("\n")
        assert "javascript:" not in content.lower()
        assert "file://" not in content.lower()
        fm, body = _parse_frontmatter(content)
        assert isinstance(fm.get("title"), str) and fm["title"]
        assert isinstance(fm.get("tags"), list) and fm["tags"]

        if md_path.parent.name == "03-视频深度笔记":
            assert content.startswith("---\n")
            assert "\n---\n\n# " in content
            assert "\n\n**关联主题双链**：" in content or "\n\n**来源频道**：" in content
            assert "\n\n## 1. 精炼中文摘要\n" in content
            if fm.get("video_id") == md_id:
                found_local_md_note = True
                assert "[00:00]" not in body
                assert "`00:00`" not in body
                assert "http://" not in body and "https://" not in body
            elif fm.get("video_id") == "vidYT000001":
                found_yt_deep_link = True
                assert "youtube.com/watch?v=vidYT000001&list=PLtest&t=65" in body
            elif fm.get("video_id") == bili_id:
                found_bili_deep_link = True
                assert md_path.stem == "_CON"
                assert "bilibili.com/video/BV1Crs3Mdxk1/?t=42" in body

    assert found_local_md_note
    assert found_yt_deep_link
    assert found_bili_deep_link
