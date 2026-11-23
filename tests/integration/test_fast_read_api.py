from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

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
from youtube_intel.fast_read_api import FastReadApiApplication
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_authority import sha256, write_managed
from youtube_intel.source_run import (
    SourceRunChildState,
    SourceRunPriority,
    SourceRunState,
    SourceRunTrigger,
    SourceRunWrite,
    build_source_run_id,
    build_source_run_idempotency_key,
)
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
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptCueWrite,
    TimedTranscriptWrite,
    build_evidence_id,
)

NOW = datetime(2026, 11, 13, 8, 0, tzinfo=UTC)


def _seed_organized_youtube_video(
    repo: SQLiteStateRepository,
    data_root: Path,
    *,
    video_id: str,
    channel_id: str,
    channel_name: str,
    now: datetime,
) -> None:
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=channel_id,
            channel_name=channel_name,
            title=f"Title {video_id}",
            description=f"Description for {video_id}",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=now - timedelta(hours=2),
            duration_seconds=420,
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
    cues = (
        TimedTranscriptCueWrite(start_ms=0, end_ms=4000, text=f"Opening statement of {video_id}."),
        TimedTranscriptCueWrite(start_ms=4000, end_ms=9000, text=f"Second verified claim for {video_id}."),
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


class _FakeSecretStore:
    def get(self) -> str | None:
        return None

    def load(self) -> str | None:
        return None

    def save(self, value: str) -> None:
        return None

    def delete(self) -> None:
        return None


def _build_realistic_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Any, Any, FastReadApiApplication, Path]:
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
    composition = build_local_source_run_runtime(
        config=config,
        project_root=project_root,
        database=db_path,
        credential_store=_FakeSecretStore(),
        bigmodel_credential_store=_FakeSecretStore(),
        allow_environment_credentials=False,
        allow_cloud_execution=False,
        now=lambda: NOW,
    )
    raw = composition.application
    repo = composition.repository
    data_root = project_root / "data"

    # Seed STANDARD_INTELLIGENCE and DISCOVER_ONLY sources + 200 source runs + child executions
    ch_id = "UC1111111111111111111111"
    std_source = composition.product.add_source(
        url=f"https://www.youtube.com/channel/{ch_id}",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    disc_source = composition.product.add_source(
        url="https://www.youtube.com/channel/UC2222222222222222222222",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    # Mark std_source as tracked in source_tracking_state
    with repo._connect() as conn:
        conn.execute(
            "INSERT INTO source_tracking_state "
            "(source_id, contract, followed_at, baseline_at, verified_at, latest_published_at, next_page, coverage, health, next_check_at) "
            "VALUES (?, 'source-tracking-v1', ?, ?, ?, ?, 1, 'COMPLETE', 'HEALTHY', ?)",
            (
                std_source.source_id,
                "2026-11-13T07:00:00Z",
                "2026-11-13T07:00:00Z",
                "2026-11-13T07:00:00Z",
                "2026-11-13T07:00:00Z",
                "2026-11-13T09:00:00Z",
            ),
        )
        conn.commit()

    # Seed 35 organized videos + 5 unorganized / failed / waiting videos
    for idx in range(35):
        vid = f"vidOrg{idx:05d}"
        _seed_organized_youtube_video(
            repo,
            data_root,
            video_id=vid,
            channel_id=ch_id,
            channel_name="Alpha Channel",
            now=NOW + timedelta(seconds=idx),
        )
        repo.link_source_video(
            source_id=std_source.source_id,
            video_id=vid,
            discovered_at=NOW + timedelta(seconds=idx),
        )

    # Seed a video linked to tracked STANDARD_INTELLIGENCE source that has NO summary yet (WAITING_CONTENT)
    waiting_vid = "vidWait0001"
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=waiting_vid,
            channel_id=ch_id,
            channel_name="Alpha Channel",
            title="Waiting Content Video",
            description="No summary yet.",
            source_url=f"https://www.youtube.com/watch?v={waiting_vid}",
            published_at=NOW,
            duration_seconds=180,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=NOW + timedelta(minutes=2),
    )
    repo.link_source_video(
        source_id=std_source.source_id,
        video_id=waiting_vid,
        discovered_at=NOW + timedelta(minutes=2),
    )

    # Seed a video with a failed transcript job + VIDEO_URL source
    failed_vid = "vidFail0001"
    vid_url_source = composition.product.add_source(
        url=f"https://www.youtube.com/watch?v={failed_vid}",
        processing_policy=ProcessingPolicy.DISCOVER_ONLY,
    )
    repo.upsert_video_metadata(
        VideoMetadata(
            video_id=failed_vid,
            channel_id=ch_id,
            channel_name="Alpha Channel",
            title="Failed Caption Video",
            description="Failed captions.",
            source_url=f"https://www.youtube.com/watch?v={failed_vid}",
            published_at=NOW,
            duration_seconds=240,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="v1",
        now=NOW + timedelta(minutes=3),
    )
    repo.advance_pipeline(
        failed_vid,
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="v1",
        now=NOW + timedelta(minutes=3),
    )
    repo.link_source_video(
        source_id=std_source.source_id,
        video_id=failed_vid,
        discovered_at=NOW + timedelta(minutes=3),
    )
    job = repo.create_job(
        job_id=f"job-fail-{failed_vid}",
        scope_key=f"video:{failed_vid}:TRANSCRIPT",
        video_id=failed_vid,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version="v1",
        available_at=NOW,
        max_attempts=1,
        now=NOW,
    )
    with repo._connect() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, last_error_code=?, finished_at=?, updated_at=? WHERE job_id=?",
            (
                JobStatus.FAILED_FINAL.value,
                "CAPABILITY_UNAVAILABLE",
                "2026-11-13T08:04:00Z",
                "2026-11-13T08:04:00Z",
                job.job_id,
            ),
        )
        conn.commit()
    assert vid_url_source.video_id == failed_vid

    # Seed a local imported text file
    raw.handle(
        "POST",
        "/api/v1/local/imports?filename=notes.md",
        b"# Local Research Notes\n\nFirst verified paragraph.\n\nSecond verified paragraph.\n",
    )

    # Seed 200 source runs + child executions
    for idx in range(200):
        target_source = std_source if idx % 2 == 0 else disc_source
        trig_ref = f"cmd-run-{idx:04d}"
        run = repo.create_source_run(
            SourceRunWrite(
                run_id=build_source_run_id(
                    source_id=target_source.source_id,
                    trigger=SourceRunTrigger.MANUAL_CHECK_NOW,
                    trigger_reference=trig_ref,
                ),
                source_id=target_source.source_id,
                trigger=SourceRunTrigger.MANUAL_CHECK_NOW,
                trigger_reference=trig_ref,
                priority=SourceRunPriority.P1,
                idempotency_key=build_source_run_idempotency_key(
                    source_id=target_source.source_id,
                    trigger=SourceRunTrigger.MANUAL_CHECK_NOW,
                    trigger_reference=trig_ref,
                ),
                automation_run_id=None,
                manual_command_id=trig_ref,
                manual_analyze_override_id=None,
                created_at=NOW + timedelta(seconds=idx),
            )
        )
        if idx == 10:
            repo.transition_source_run(
                run.run_id,
                to_state=SourceRunState.RUNNING,
                now=NOW + timedelta(minutes=4),
            )
            child_vid = "vidChild001"
            repo.upsert_video_metadata(
                VideoMetadata(
                    video_id=child_vid,
                    channel_id=ch_id,
                    channel_name="Alpha Channel",
                    title="Child Run Active Video",
                    description="In source run child.",
                    source_url=f"https://www.youtube.com/watch?v={child_vid}",
                    published_at=NOW,
                    duration_seconds=120,
                    default_language="en",
                    available_languages=("en",),
                    live_status=LiveStatus.NONE,
                    availability=Availability.PUBLIC,
                ),
                pipeline_version="v1",
                now=NOW + timedelta(minutes=4),
            )
            repo.link_source_video(
                source_id=target_source.source_id,
                video_id=child_vid,
                discovered_at=NOW + timedelta(minutes=4),
            )
            repo.record_source_run_child(
                run.run_id,
                video_id=child_vid,
                state=SourceRunChildState.PENDING,
                distillation_execution_id=None,
                now=NOW + timedelta(minutes=4),
            )

    fast = FastReadApiApplication(raw)
    return composition, raw, fast, data_root


def test_fast_read_api_matches_raw_payloads_and_stays_within_connection_and_latency_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composition, raw, fast, data_root = _build_realistic_runtime(tmp_path, monkeypatch)
    repo = composition.repository

    raw_videos_status, raw_videos = raw.handle("GET", "/api/v1/videos")
    raw_intel_status, raw_intel = raw.handle("GET", "/api/v1/intelligence")
    raw_detail_status, raw_detail = raw.handle("GET", "/api/v1/videos/vidOrg00000")

    original_connect = repo._connect
    connect_calls = 0

    def counted_connect(*args: Any, **kwargs: Any) -> Any:
        nonlocal connect_calls
        connect_calls += 1
        return original_connect(*args, **kwargs)

    with patch.object(repo, "_connect", side_effect=counted_connect):
        t0 = time.perf_counter()
        fast_videos_status, fast_videos = fast.handle("GET", "/api/v1/videos")
        videos_ms = (time.perf_counter() - t0) * 1000.0
        videos_connects = connect_calls

        connect_calls = 0
        t1 = time.perf_counter()
        fast_intel_status, fast_intel = fast.handle("GET", "/api/v1/intelligence")
        intel_ms = (time.perf_counter() - t1) * 1000.0
        intel_connects = connect_calls

    fast_detail_status, fast_detail = fast.handle("GET", "/api/v1/videos/vidOrg00000")

    assert (fast_videos_status, fast_videos) == (raw_videos_status, raw_videos)
    assert (fast_intel_status, fast_intel) == (raw_intel_status, raw_intel)
    assert (fast_detail_status, fast_detail) == (raw_detail_status, raw_detail)

    assert videos_connects <= 5, f"Expected <= 5 SQLite connects for /videos, got {videos_connects}"
    assert intel_connects <= 5, f"Expected <= 5 SQLite connects for /intelligence, got {intel_connects}"
    assert videos_ms < 120.0, f"/api/v1/videos took {videos_ms:.1f}ms"
    assert intel_ms < 80.0, f"/api/v1/intelligence took {intel_ms:.1f}ms"

    # Fail-closed tamper check: corrupting a summary artifact file on disk must surface NEEDS_ATTENTION identically!
    pointer = repo.current_local_summary_pointer("vidOrg00001")
    assert pointer is not None
    art = repo.get_artifact(pointer.artifact_id)
    assert art is not None
    (data_root / art.relative_path).write_bytes(b'{"tampered": true}')

    assert fast.handle("GET", "/api/v1/videos") == raw.handle("GET", "/api/v1/videos")
    assert fast.handle("GET", "/api/v1/intelligence") == raw.handle("GET", "/api/v1/intelligence")
    assert fast.handle("GET", "/api/v1/videos/vidOrg00001") == raw.handle("GET", "/api/v1/videos/vidOrg00001")

    # Mutation check: adding a new VIDEO_URL source produces pending content work identically!
    fast.handle(
        "POST",
        "/api/v1/sources",
        json.dumps(
            {
                "url": "https://youtu.be/PendingV001",
                "processing_policy": "DISCOVER_ONLY",
            }
        ).encode("utf-8"),
    )
    assert fast.handle("GET", "/api/v1/videos") == raw.handle("GET", "/api/v1/videos")
    assert fast.handle("GET", "/api/v1/videos/PendingV001") == raw.handle("GET", "/api/v1/videos/PendingV001")
    with pytest.raises( Exception ):
        raw.handle("GET", "/api/v1/videos/DoesNotExist999")
    try:
        raw.handle("GET", "/api/v1/videos/DoesNotExist999")
    except Exception as raw_err:
        with pytest.raises(type(raw_err)) as fast_err:
            fast.handle("GET", "/api/v1/videos/DoesNotExist999")
        assert getattr(fast_err.value, "code", None) == getattr(raw_err, "code", None)


def test_fast_read_api_accelerates_sources_topics_dashboard_intelligence_and_noop_stale_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from youtube_intel.workspace_intelligence_hub import WorkspaceIntelligenceHub

    composition, raw, _unused_fast, data_root = _build_realistic_runtime(tmp_path, monkeypatch)
    repo = composition.repository
    project_root = data_root.parent

    def fake_completer(**kwargs: Any) -> tuple[dict[str, Any], str, str]:
        return (
            {
                "headline_zh": "高价值 AI 架构深度拆解",
                "summary_zh": "系统梳理了生产级 Agent 状态机、评测闭环与确定性工具契约。",
                "key_takeaways_zh": ["确定性状态机优于自由散漫的循环", "离线评测集决定上线下限"],
                "product_opportunities_zh": ["本地优先多源情报工作台"],
                "business_opportunities_zh": ["个人免费获客 + 专业版增值订阅"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "recommendation_tier": "MUST_WATCH",
                "score": 8.8,
                "core_points": [
                    {
                        "text_zh": "确定性状态机优于自由散漫的循环",
                        "cue_window_index": 0,
                    }
                ],
            },
            "ollama",
            "qwen3.5:9b",
        )

    hub = WorkspaceIntelligenceHub(
        repository=repo,
        data_root=data_root,
        project_root=project_root,
        byok_credential_store=_FakeSecretStore(),
        llm_completer=fake_completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: NOW,
    )
    # Distill 12 videos so intelligences, distillation_cards, topics, and memberships exist
    for idx in range(12):
        hub.distill_video(f"vidOrg{idx:05d}")

    fast_no_sidecar = FastReadApiApplication(
        raw,
        workspace_hub=WorkspaceIntelligenceHub(
            repository=repo,
            data_root=data_root,
            project_root=tmp_path / "empty_no_sidecar",
            now=lambda: NOW,
        ),
    )
    fast = FastReadApiApplication(raw, workspace_hub=hub)

    # Save one intelligence item and pin one topic so /saved-intelligence & /dashboard exercise full paths
    intel_ids = repo.list_current_intelligence_ids(limit=5)
    assert len(intel_ids) >= 2
    fast.handle(
        "POST",
        "/api/v1/saved-intelligence/save",
        json.dumps({"intelligence_id": intel_ids[0]}).encode("utf-8"),
    )
    topics_list = repo.list_topics()
    assert len(topics_list) >= 1
    topic_id = topics_list[0].topic_id
    fast.handle(
        "POST",
        f"/api/v1/topics/{topic_id}/pin",
        json.dumps({"pinned": True}).encode("utf-8"),
    )
    source_id = repo.list_source_subscriptions()[0].source_id

    # 1. Exact parity without sidecar against LocalApiApplication across ALL hot navigation routes
    for check_route in (
        "/api/v1/sources",
        f"/api/v1/sources/{source_id}",
        "/api/v1/topics",
        f"/api/v1/topics/{topic_id}",
        "/api/v1/intelligence",
        f"/api/v1/intelligence/{intel_ids[0]}",
        "/api/v1/saved-intelligence",
        "/api/v1/dashboard",
        "/api/v1/videos/vidOrg00000/evidence",
    ):
        assert fast_no_sidecar.handle("GET", check_route) == raw.handle("GET", check_route), (
            f"Parity mismatch on {check_route}"
        )

    # 404 parity on nonexistent evidence route
    try:
        raw.handle("GET", "/api/v1/videos/DoesNotExist999/evidence")
    except Exception as raw_ev_err:
        with pytest.raises(type(raw_ev_err)) as fast_ev_err:
            fast_no_sidecar.handle("GET", "/api/v1/videos/DoesNotExist999/evidence")
        assert getattr(fast_ev_err.value, "code", None) == getattr(raw_ev_err, "code", None)

    # 2. Cold snapshot connection budget (<= 3 SQLite connections per route, zero N+1 storm!)
    original_connect = repo._connect
    connect_calls = 0

    def counted_connect(*args: Any, **kwargs: Any) -> Any:
        nonlocal connect_calls
        connect_calls += 1
        return original_connect(*args, **kwargs)

    with patch.object(repo, "_connect", side_effect=counted_connect):
        for hot_route in (
            "/api/v1/sources",
            f"/api/v1/sources/{source_id}",
            "/api/v1/videos",
            "/api/v1/videos/vidOrg00000/evidence",
            "/api/v1/topics",
            f"/api/v1/topics/{topic_id}",
            "/api/v1/intelligence",
            f"/api/v1/intelligence/{intel_ids[0]}",
            "/api/v1/saved-intelligence",
            "/api/v1/dashboard",
            "/api/v1/workspace-ai/research/sessions",
        ):
            connect_calls = 0
            t_start = time.perf_counter()
            st, body = fast.handle("GET", hot_route)
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            assert st == 200, f"{hot_route} returned {st}: {body}"
            assert connect_calls <= 3, (
                f"Cold {hot_route} opened {connect_calls} SQLite connections (expected <= 3)"
            )
            assert elapsed_ms < 120.0, f"Cold {hot_route} took {elapsed_ms:.1f}ms"

        # 3. Warm cache hits must open 0 SQLite connections and finish in < 20ms
        for warm_route in (
            "/api/v1/sources",
            "/api/v1/videos",
            "/api/v1/videos/vidOrg00000/evidence",
            "/api/v1/topics",
            "/api/v1/intelligence",
            "/api/v1/saved-intelligence",
            "/api/v1/dashboard",
            "/api/v1/workspace-ai/research/sessions",
        ):
            connect_calls = 0
            t_warm = time.perf_counter()
            st_w, _ = fast.handle("GET", warm_route)
            warm_ms = (time.perf_counter() - t_warm) * 1000.0
            assert st_w == 200
            assert connect_calls == 0, f"Warm {warm_route} opened {connect_calls} connections"
            assert warm_ms < 25.0, f"Warm {warm_route} took {warm_ms:.1f}ms"

        # 4. No-op POST /api/v1/sources/check-stale (when checks == []) MUST NOT wipe warm caches!
        stale_status, stale_body = fast.handle("POST", "/api/v1/sources/check-stale", b"{}")
        assert stale_status == 202
        assert stale_body == {"checks": []}

        for post_stale_route in (
            "/api/v1/sources",
            "/api/v1/videos",
            "/api/v1/topics",
            "/api/v1/intelligence",
        ):
            connect_calls = 0
            st_after, _ = fast.handle("GET", post_stale_route)
            assert st_after == 200
            assert connect_calls == 0, (
                f"{post_stale_route} cache was wiped by no-op check-stale ({connect_calls} connects)"
            )

