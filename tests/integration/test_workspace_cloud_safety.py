"""Security & cost-guard tests for background auto-sync, BYOK cap, snapshot re-auth & portability."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from youtube_intel import fast_read_api
from youtube_intel.config import AppConfig, AppSettings, load_settings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    PipelineStatus,
    VideoMetadata,
)
from youtube_intel.extractive_summary import ExtractiveSummaryService
from youtube_intel.local_api import ApiError
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

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


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


class _RecordingCompleter:
    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_with = fail_with

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
        del system_prompt, user_prompt, max_tokens
        self.calls.append({"mode": mode, "provider": provider, "model": model})
        if self.fail_with is not None:
            raise self.fail_with
        return (
            {
                "headline_zh": "基于验证字幕生成的摘要标题",
                "summary_zh": "完整结构化中文总结。",
                "score": 8.4,
                "score_reason_zh": "逻辑严谨，含实操步骤。",
                "recommendation_tier": "MUST_WATCH",
                "content_bucket": "DEEP_DIVE",
                "topics_zh": ["工程架构", "安全护栏"],
                "topic_cluster_zh": "AI Agent 与自动化架构",
                "core_points": [{"text_zh": "先锁原文，再做引用。", "cue_window_index": 0}],
                "product_opportunities_zh": [],
                "business_opportunities_zh": [],
                "filtered_noise_zh": [],
            },
            provider,
            model,
        )


def _setup_hub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    completer: _RecordingCompleter,
    video_ids: tuple[str, ...] = ("vidSafety01",),
) -> tuple[WorkspaceIntelligenceHub, _MemorySecret]:
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

    project_root = (tmp_path / "owner").resolve()
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
    for idx, vid in enumerate(video_ids):
        t = NOW - timedelta(hours=idx + 1)
        repo.upsert_video_metadata(
            VideoMetadata(
                video_id=vid,
                channel_id="UC_SAFETY_11111111111111",
                channel_name="Safety Lab",
                title=f"Safety Video {vid}",
                description="Safety testing",
                source_url=f"https://www.youtube.com/watch?v={vid}",
                published_at=t,
                duration_seconds=900,
                default_language="en",
                available_languages=("en",),
                live_status=LiveStatus.NONE,
                availability=Availability.PUBLIC,
            ),
            pipeline_version="v1",
            now=t,
        )
        repo.advance_pipeline(
            vid,
            expected_status=PipelineStatus.DISCOVERED,
            target_status=PipelineStatus.METADATA_READY,
            pipeline_version="v1",
            now=t,
        )
        repo.advance_pipeline(
            vid,
            expected_status=PipelineStatus.METADATA_READY,
            target_status=PipelineStatus.TRANSCRIPT_READY,
            pipeline_version="v1",
            now=t,
        )
        cue = TimedTranscriptCueWrite(start_ms=0, end_ms=10000, text="Bounded deterministic safety checks.")
        rel = f"transcripts/canonical/{vid}.txt"
        raw = cue.text.encode("utf-8")
        write_managed(data_root, rel, raw)
        art_id = f"canonical:{vid}"
        repo.upsert_artifact(
            ArtifactWrite(
                artifact_id=art_id,
                artifact_key=art_id,
                video_id=vid,
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
            now=t,
        )
        repo.create_timed_transcript(
            TimedTranscriptWrite.from_cues(video_id=vid, canonical_artifact_id=art_id, cues=(cue,)),
            now=t,
        )
        ExtractiveSummaryService(repo, data_root).create(vid, now=t)

    secret_store = _MemorySecret("sk-valid-test-byok-key")
    hub = WorkspaceIntelligenceHub(
        repository=repo,
        data_root=data_root,
        project_root=project_root,
        byok_credential_store=secret_store,
        llm_completer=completer,
        installed_ollama_probe=lambda _url: (True, ("qwen3.5:9b",)),
        now=lambda: NOW,
    )
    return hub, secret_store


def test_background_auto_sync_never_calls_cloud_byok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completer = _RecordingCompleter()
    hub, _ = _setup_hub(tmp_path, monkeypatch, completer=completer, video_ids=("vidBg000001",))

    # Default local mode works locally with zero cloud calls
    res_local = hub.sync_pending_videos(limit=3, background=True)
    assert res_local["synced_count"] == 1
    assert [c["mode"] for c in completer.calls] == ["local_ollama"]

    # Switch to cloud_byok -> background auto-sync must block outbound cloud calls cleanly
    completer.calls.clear()
    settings = hub.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_provider": "deepseek",
            "cloud_base_url": "https://api.deepseek.com/v1",
            "cloud_model": "deepseek-chat",
        }
    )
    assert settings["background_auto_sync_cloud_allowed"] is False

    res_bg = hub.sync_pending_videos(limit=3, background=True)
    assert res_bg["synced_count"] == 0
    assert res_bg["skipped_reason"] == "BACKGROUND_CLOUD_BLOCKED"
    assert completer.calls == []

    # Direct low-level distill with allow_cloud=False also fails closed
    with pytest.raises(ApiError) as exc:
        hub.distill_video("vidBg000001", allow_cloud=False)
    assert exc.value.code == "BACKGROUND_CLOUD_NOT_AUTHORIZED"
    assert completer.calls == []


def test_cloud_daily_cap_timeout_reservation_and_concurrency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vids = tuple(f"vidCap0000{i}" for i in range(1, 9))
    completer = _RecordingCompleter()
    hub, _ = _setup_hub(tmp_path, monkeypatch, completer=completer, video_ids=vids)
    hub.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_base_url": "https://api.deepseek.com/v1",
            "cloud_daily_call_limit": 2,
        }
    )

    hub.distill_video(vids[0])
    hub.distill_video(vids[1])
    assert len(completer.calls) == 2

    with pytest.raises(ApiError) as over_exc:
        hub.distill_video(vids[2])
    assert over_exc.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert over_exc.value.code == "CLOUD_DAILY_BUDGET_EXCEEDED"
    assert len(completer.calls) == 2

    # Concurrent burst with fresh hub capped at 2 strictly allows only 2 outbound calls
    burst_completer = _RecordingCompleter()
    burst_hub, _ = _setup_hub(
        tmp_path / "burst", monkeypatch, completer=burst_completer, video_ids=vids
    )
    burst_hub.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_base_url": "https://api.deepseek.com/v1",
            "cloud_daily_call_limit": 2,
        }
    )

    def _run_one(vid: str) -> str:
        try:
            burst_hub.distill_video(vid)
            return "OK"
        except ApiError as err:
            return err.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(_run_one, vids))
    assert outcomes.count("OK") == 2
    assert outcomes.count("CLOUD_DAILY_BUDGET_EXCEEDED") == 6
    assert len(burst_completer.calls) == 2

    # Timeout/ambiguous failure retains ledger reservation so retry does not bypass limit=1
    to_completer = _RecordingCompleter(fail_with=TimeoutError("upstream timed out"))
    to_hub, _ = _setup_hub(
        tmp_path / "timeout", monkeypatch, completer=to_completer, video_ids=("vidTo000001",)
    )
    to_hub.update_settings(
        {
            "active_mode": "cloud_byok",
            "cloud_base_url": "https://api.deepseek.com/v1",
            "cloud_daily_call_limit": 1,
        }
    )
    with pytest.raises(ApiError) as first_err:
        to_hub.distill_video("vidTo000001")
    assert first_err.value.code == "CLOUD_MODEL_CALL_FAILED"
    assert len(to_completer.calls) == 1

    with pytest.raises(ApiError) as retry_err:
        to_hub.distill_video("vidTo000001")
    assert retry_err.value.code == "CLOUD_DAILY_BUDGET_EXCEEDED"
    assert len(to_completer.calls) == 1


def test_snapshot_restore_revokes_cloud_authorization_until_reconfirmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completer = _RecordingCompleter()
    hub, _ = _setup_hub(tmp_path, monkeypatch, completer=completer, video_ids=("vidSnap0001",))

    snapshot = hub.export_backup_snapshot()
    snapshot["engine_config"] = {
        "active_mode": "cloud_byok",
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_model": "qwen3.5:9b",
        "cloud_provider": "openai_compatible",
        "cloud_base_url": "https://evil.example/v1",
        "cloud_model": "evil-model",
    }

    restored = hub.restore_backup_snapshot(snapshot)
    assert restored["cloud_reauth_required"] is True

    after = hub.get_settings()
    assert after["active_mode"] == "local_ollama"
    assert after["cloud_base_url"] == "https://evil.example/v1"
    assert after["cloud_reauth_required"] is True

    # Even toggling active_mode without re-confirming endpoint must remain blocked
    toggled = hub.update_settings({"active_mode": "cloud_byok"})
    assert toggled["cloud_reauth_required"] is True
    with pytest.raises(ApiError) as blocked:
        hub.distill_video("vidSnap0001")
    assert blocked.value.code == "CLOUD_ENDPOINT_REAUTH_REQUIRED"
    assert completer.calls == []

    # Explicit user save with confirmed endpoint re-authorizes cloud calls
    confirmed = hub.update_settings(
        {"active_mode": "cloud_byok", "cloud_base_url": "https://api.deepseek.com/v1"}
    )
    assert confirmed["cloud_reauth_required"] is False
    hub.distill_video("vidSnap0001")
    assert len(completer.calls) == 1


def test_raise_open_file_limit_safely_noops_without_resource_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fast_read_api, "_resource", None)
    fast_read_api._raise_open_file_limit()
