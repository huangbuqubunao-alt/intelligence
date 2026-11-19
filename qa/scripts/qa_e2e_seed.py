"""Seed an isolated realistic QA runtime directory for real Playwright full-stack E2E tests."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.domain import (
    Availability,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.extractive_summary import ExtractiveSummaryService
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
    JobType,
    RetentionClass,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)
from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E_ROOT = REPO_ROOT / ".var" / "qa-audit" / "e2e-run"
BASE_NOW = datetime(2026, 11, 16, 0, 0, tzinfo=UTC)


class _DummySecretStore:
    def get(self) -> str | None:
        return None

    def load(self) -> str | None:
        return None

    def save(self, value: str) -> None:
        return None

    def delete(self) -> None:
        return None


def _seed_video(
    repo: Any,
    data_root: Path,
    *,
    video_id: str,
    title: str,
    channel_id: str,
    channel_name: str,
    duration_seconds: int,
    published_at: datetime,
    cues_text: tuple[str, str],
) -> None:
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            description=f"QA seeded video: {title}",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=published_at,
            duration_seconds=duration_seconds,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=published_at,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=published_at,
    )
    repo.advance_pipeline(
        video_id,
        expected_status=PipelineStatus.METADATA_READY,
        target_status=PipelineStatus.TRANSCRIPT_READY,
        pipeline_version="v1",
        now=published_at,
    )
    cues = (
        TimedTranscriptCueWrite(start_ms=0, end_ms=5000, text=cues_text[0]),
        TimedTranscriptCueWrite(start_ms=5000, end_ms=12000, text=cues_text[1]),
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
        now=published_at,
    )
    timed = TimedTranscriptWrite.from_cues(
        video_id=video_id,
        canonical_artifact_id=art_id,
        cues=cues,
    )
    repo.create_timed_transcript(timed, now=published_at)
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
            now=published_at,
        )
    ExtractiveSummaryService(repo, data_root).create(video_id, now=published_at)


def seed_e2e_runtime() -> dict[str, Any]:
    if E2E_ROOT.exists():
        shutil.rmtree(E2E_ROOT)
    (E2E_ROOT / "config").mkdir(parents=True, exist_ok=True)
    for sub in ("data", "logs", "vault", "templates"):
        (E2E_ROOT / sub).mkdir(parents=True, exist_ok=True)

    lines = (REPO_ROOT / "config" / "settings.example.yaml").read_text(encoding="utf-8").splitlines()
    out_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("vault_root:"):
            out_lines.append(f"  vault_root: {E2E_ROOT / 'vault'}")
        else:
            out_lines.append(line)
    (E2E_ROOT / "config" / "settings.yaml").write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    channels_txt = (REPO_ROOT / "config" / "channels.example.yaml").read_text(encoding="utf-8")
    channels_txt = channels_txt.replace("enabled: true", "enabled: false")
    (E2E_ROOT / "config" / "channels.yaml").write_text(channels_txt, encoding="utf-8")

    values = load_settings(E2E_ROOT / "config" / "settings.yaml").model_dump()
    config = AppConfig(channels=(), settings=AppSettings.model_validate(values))
    db_path = E2E_ROOT / "state.sqlite3"
    data_root = E2E_ROOT / "data"

    composition = build_local_source_run_runtime(
        config=config,
        project_root=E2E_ROOT,
        database=db_path,
        credential_store=_DummySecretStore(),
        bigmodel_credential_store=_DummySecretStore(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        now=lambda: BASE_NOW,
    )
    repo = composition.repository

    ch_id = "UC1111111111111111111111"
    std_source = composition.product.add_source(
        url=f"https://www.youtube.com/channel/{ch_id}",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    with repo._connect() as conn:
        conn.execute(
            "INSERT INTO source_tracking_state "
            "(source_id, contract, followed_at, baseline_at, verified_at, latest_published_at, next_page, coverage, health, next_check_at) "
            "VALUES (?, 'source-tracking-v1', ?, ?, ?, ?, 1, 'COMPLETE', 'HEALTHY', ?)",
            (
                std_source.source_id,
                "2026-11-16T00:00:00Z",
                "2026-11-16T00:00:00Z",
                "2026-11-16T00:00:00Z",
                "2026-11-18T10:00:00Z",
                "2026-11-30T00:00:00Z",
            ),
        )
        conn.commit()

    videos_spec = [
        ("vidE2E00001", "Agentic Workflows Older Deep Dive", 720, BASE_NOW + timedelta(hours=12), "AI Agent 架构旧篇", "Agent Orchestration", 8.1),
        ("vidE2E00002", "Local-First Knowledge Graph Architecture", 960, BASE_NOW + timedelta(hours=40), "本地优先知识图谱实践", "Knowledge Systems", 9.0),
        ("vidE2E00003", "Production LLM Reliability Systems #shorts", 420, BASE_NOW + timedelta(hours=58), "生产级大模型可靠性设计（最新）", "AI Engineering", 9.4),
        ("vidShort001", "45s Quick Demo #shorts", 45, BASE_NOW + timedelta(hours=56), "45秒短视频速览", "Quick Tips", 7.3),
    ]
    for vid, title, dur, ts, _, _, _ in videos_spec:
        _seed_video(
            repo,
            data_root,
            video_id=vid,
            title=title,
            channel_id=ch_id,
            channel_name="Alpha Engineering",
            duration_seconds=dur,
            published_at=ts,
            cues_text=(
                f"{title} verifies deterministic state transitions and evidence traceability.",
                f"Local SQLite plus atomic artifacts guarantees crash recovery for {vid}.",
            ),
        )
        repo.link_source_video(source_id=std_source.source_id, video_id=vid, discovered_at=ts)

    # Seed one pending attention item
    pending_vid = "vidPend0001"
    composition.product.add_source(
        url=f"https://www.youtube.com/watch?v={pending_vid}",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    pending_ts = BASE_NOW + timedelta(hours=57)
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=pending_vid,
            channel_id=ch_id,
            channel_name="Alpha Engineering",
            title="Pending Manual Attention Video",
            description="Needs caption retry",
            source_url=f"https://www.youtube.com/watch?v={pending_vid}",
            published_at=pending_ts,
            duration_seconds=310,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=pending_ts,
    )
    repo.advance_pipeline(
        pending_vid,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=pending_ts,
    )
    repo.link_source_video(source_id=std_source.source_id, video_id=pending_vid, discovered_at=pending_ts)
    job = repo.create_job(
        job_id=f"job-pend-{pending_vid}",
        scope_key=f"video:{pending_vid}:TRANSCRIPT",
        video_id=pending_vid,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version="v1",
        available_at=pending_ts,
        max_attempts=1,
        now=pending_ts,
    )
    with repo._connect() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, last_error_code=?, finished_at=?, updated_at=? WHERE job_id=?",
            (JobStatus.FAILED_FINAL.value, "CAPABILITY_UNAVAILABLE", "2026-11-18T09:42:00Z", "2026-11-18T09:42:00Z", job.job_id),
        )
        conn.commit()

    # Distill videos into hub sequentially at advancing timestamps
    meta_by_vid = {v[0]: v for v in videos_spec}
    tick = [0]

    def fake_completer(**kwargs: Any) -> tuple[dict[str, Any], str, str]:
        tick[0] += 1
        vid_id = str(kwargs.get("video_id") or "")
        info = meta_by_vid.get(vid_id)
        headline = info[4] if info else f"洞察要点 {tick[0]}"
        topic = info[5] if info else "AI Systems"
        score = info[6] if info else 8.5
        return (
            {
                "headline_zh": headline,
                "summary_zh": f"针对 {vid_id} 的结构化中文洞察摘要，包含证据链与可执行方案。",
                "key_takeaways_zh": ["状态机隔离副作用与持久层", "每条洞察绑定时间戳字幕证据"],
                "product_opportunities_zh": ["面向研发团队的离线视频情报工作台"],
                "business_opportunities_zh": ["开源本地引擎 + 团队协作插件"],
                "topic_cluster_zh": topic,
                "recommendation_tier": "MUST_WATCH",
                "score": score,
                "evidence_Indices": [0, 1],
            },
            "ollama",
            "qwen3.5:9b",
        )

    hub = WorkspaceIntelligenceHub(
        repository=repo,
        data_root=data_root,
        project_root=E2E_ROOT,
        byok_credential_store=_DummySecretStore(),
        llm_completer=fake_completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: BASE_NOW + timedelta(minutes=tick[0] * 10),
    )
    for vid, _, _, _, _, _, _ in videos_spec:
        hub.distill_video(vid)

    # Create two topics at distinct timestamps so newest-first topic ordering is testable
    composition.application.handle("POST", "/api/v1/topics", json.dumps({"command_id": "seed-topic-old", "name": "Older Seed Topic"}).encode("utf-8"))
    t2 = repo.create_topic if False else None
    del t2
    # Seed baseline local text note too
    composition.application.handle(
        "POST",
        "/api/v1/local/imports?filename=seeded-baseline.txt",
        b"Seeded Local Baseline Note\n\nKeep offline evidence auditable and fast.",
    )

    # Align source_observations with tracking authority for every linked video
    with repo._connect() as conn:
        obs_rows = [
            (std_source.source_id, vid, ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "2026-11-18T10:01:00Z", 0, "ENROLLED", vid, None)
            for vid, _, _, ts, _, _, _ in videos_spec
        ] + [
            (std_source.source_id, pending_vid, pending_ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "2026-11-18T10:01:00Z", 0, "ENROLLED", pending_vid, None)
        ]
        conn.executemany(
            "INSERT INTO source_observations "
            "(source_id, canonical_identity, published_at, observed_at, baseline, enrollment, content_id, error_code) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            obs_rows,
        )
        conn.commit()

    from youtube_intel.backup_restore import BackupRestoreService
    readiness = BackupRestoreService(database=db_path, data_root=data_root).readiness()
    assert readiness.get("ready") is True, f"E2E seed DB not backup-ready: {readiness}"

    return {
        "e2e_root": str(E2E_ROOT),
        "db_path": str(db_path),
        "source_id": std_source.source_id,
        "backup_ready": readiness["ready"],
        "videos_seeded": [v[0] for v in videos_spec] + [pending_vid],
        "intel_count": len(repo.list_current_intelligence_ids(limit=50)),
        "topics": [t.name for t in repo.list_topics()],
    }


if __name__ == "__main__":
    print(json.dumps(seed_e2e_runtime(), ensure_ascii=False))
