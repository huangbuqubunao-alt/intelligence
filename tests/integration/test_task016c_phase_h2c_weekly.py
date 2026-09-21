"""TASK-016C Phase H2-C — Correction Round 1, Fix 4.

Weekly reporting must consume scoring exclusively through the
AuthoritativeScoringReader / VerifiedScoringRead path.  There is no
latest-artifact authority fallback in WeeklyReportService.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.domain import PipelineStatus
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    StorageRoot,
)

_NOW = datetime(2026, 8, 26, 9, tzinfo=UTC)
_PIPELINE_VERSION = "runtime-v1"
_MODEL = "qwen3:8b"


def _load_module(name: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    base = Path(__file__).resolve().parents[1]
    for sub in ("unit", "integration"):
        candidate = base / sub / f"{name}.py"
        if candidate.exists():
            specification = importlib.util.spec_from_file_location(name, candidate)
            assert specification is not None and specification.loader is not None
            support = importlib.util.module_from_spec(specification)
            sys.modules[name] = support
            specification.loader.exec_module(support)
            return support
    raise FileNotFoundError(f"test support module not found: {name}")


def _complete_video_for_weekly(
    repository: Any,
    *,
    video_id: str,
    vault_root: Path,
    vault_subdir: str,
) -> None:
    """Advance a SCORED video to COMPLETE and register the managed note."""

    # Weekly reporting requires complete video metadata.
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE videos SET channel_name = 'Channel', title = 'Title', "
            "description = 'Description', source_url = 'https://example.invalid/w', "
            "published_at = '2026-08-26T08:00:00.000000Z', duration_seconds = 60, "
            "default_language = 'en', live_status = 'none', availability = 'public' "
            "WHERE video_id = :video_id",
            {"video_id": video_id},
        )
    finally:
        connection.close()
    for expected, target in (
        (PipelineStatus.SCORED, PipelineStatus.ANALYSIS_READY),
        (PipelineStatus.ANALYSIS_READY, PipelineStatus.NOTE_WRITTEN),
        (PipelineStatus.NOTE_WRITTEN, PipelineStatus.COMPLETE),
    ):
        assert repository.advance_pipeline(
            video_id,
            expected_status=expected,
            target_status=target,
            pipeline_version=_PIPELINE_VERSION,
            now=_NOW,
        )
    note_rel = f"Videos/note--{video_id}.md"
    note_bytes = b"note"
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id=f"video-note-{video_id}",
            artifact_key=f"video-note/{_PIPELINE_VERSION}/{video_id}",
            video_id=video_id,
            job_id=None,
            kind=ArtifactKind.VIDEO_NOTE,
            storage_root=StorageRoot.VAULT,
            relative_path=note_rel,
            content_hash=hashlib.sha256(note_bytes).hexdigest(),
            provider=None,
            model=None,
            producer_version="video-note-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=_NOW,
    )
    note_path = vault_root / vault_subdir / note_rel
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_bytes(note_bytes)


def _weekly_service(
    repository: Any,
    *,
    data_root: Path,
    vault_root: Path,
    scoring_reader: Any,
    vault_subdir: str = "Knowledge",
) -> WeeklyReportService:
    return WeeklyReportService(
        repository=repository,
        sink=ObsidianNoteSink(
            vault_root=vault_root,
            vault_subdir=vault_subdir,
            repository=repository,
            context=NoteWriteContext(
                job_id="weekly", owner="weekly-test", pipeline_version=_PIPELINE_VERSION
            ),
        ),
        artifact_root=data_root,
        timezone="Asia/Shanghai",
        top_n=10,
        scoring_reader=scoring_reader,
    )


def _authoritative_reader(repository: Any, data_root: Path) -> AuthoritativeScoringReader:
    return AuthoritativeScoringReader(
        repository=repository,
        data_root=data_root,
        summary_threshold=7.0,
        pipeline_version=_PIPELINE_VERSION,
        current_model=_MODEL,
    )


# ---------------------------------------------------------------------------
# Reader is mandatory — no latest-artifact authority fallback
# ---------------------------------------------------------------------------


def test_weekly_service_requires_scoring_reader(tmp_path: Path) -> None:
    persistence = _load_module("test_task016c_phase_h2c_persistence")
    repository = persistence._setup_repository(tmp_path)
    with pytest.raises(TypeError):
        WeeklyReportService(
            repository=repository,
            sink=ObsidianNoteSink(
                vault_root=tmp_path / "vault",
                vault_subdir="Knowledge",
                repository=repository,
                context=NoteWriteContext(
                    job_id="weekly", owner="t", pipeline_version=_PIPELINE_VERSION
                ),
            ),
            artifact_root=tmp_path / "data",
            timezone="Asia/Shanghai",
            top_n=10,
        )


def test_corrupted_latest_artifact_cannot_influence_weekly(tmp_path: Path) -> None:
    persistence = _load_module("test_task016c_phase_h2c_persistence")
    repository = persistence._setup_repository(tmp_path)
    persistence._claim_scoring_job(repository)
    entry = persistence._entry(repository, tmp_path)
    entry.persist_success(persistence._repair_success())
    video_id = persistence._VIDEO_ID
    data_root = tmp_path / "data"
    vault_root = tmp_path / "vault"
    vault_subdir = "Knowledge"
    _complete_video_for_weekly(
        repository, video_id=video_id, vault_root=vault_root, vault_subdir=vault_subdir
    )

    # Register a NEWER, corrupted SCORING_STRUCTURED artifact so the
    # latest-artifact candidate selection resolves it; the authoritative
    # reader must still resolve the pointer artifact.
    corrupt_bytes = b"corrupted latest bytes"
    repository.upsert_artifact(
        ArtifactWrite(
            artifact_id="corrupt-latest",
            artifact_key="scoring/corrupt/structured",
            video_id=video_id,
            job_id="h2c-persist-job",
            kind=ArtifactKind.SCORING_STRUCTURED,
            storage_root=StorageRoot.DATA,
            relative_path="scoring/corrupt/structured.json",
            content_hash=hashlib.sha256(corrupt_bytes).hexdigest(),
            provider="ollama",
            model=_MODEL,
            producer_version="scoring-structured-content-quality-repair-v1",
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        ),
        now=datetime(2026, 8, 26, 10, tzinfo=UTC),
    )
    (data_root / "scoring" / "corrupt").mkdir(parents=True, exist_ok=True)
    (data_root / "scoring" / "corrupt" / "structured.json").write_bytes(corrupt_bytes)

    reader = _authoritative_reader(repository, data_root)
    service = _weekly_service(
        repository, data_root=data_root, vault_root=vault_root, scoring_reader=reader.read
    )
    report = service.generate(now=_NOW)

    # The authoritative artifact (not the corrupted latest) produced the score.
    assert len(report.report.items) == 1
    assert report.report.items[0].score.score == 8


def test_v1_repair_weekly_uses_verified_scoring_read(tmp_path: Path) -> None:
    persistence = _load_module("test_task016c_phase_h2c_persistence")
    repository = persistence._setup_repository(tmp_path)
    persistence._claim_scoring_job(repository)
    entry = persistence._entry(repository, tmp_path)
    entry.persist_success(persistence._repair_success())
    video_id = persistence._VIDEO_ID
    data_root = tmp_path / "data"
    vault_root = tmp_path / "vault"
    vault_subdir = "Knowledge"
    _complete_video_for_weekly(
        repository, video_id=video_id, vault_root=vault_root, vault_subdir=vault_subdir
    )

    reader = _authoritative_reader(repository, data_root)
    calls: list[str] = []

    def recording_reader(video_id: str) -> Any:
        calls.append(video_id)
        return reader.read(video_id)

    service = _weekly_service(
        repository, data_root=data_root, vault_root=vault_root, scoring_reader=recording_reader
    )
    report = service.generate(now=_NOW)

    assert calls == [video_id]
    assert report.report.items[0].score.score == 8


def test_v1_primary_weekly_uses_verified_scoring_read(tmp_path: Path) -> None:
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    repository = runtime._repository
    video_id = "video-weekly-primary"
    job_id = "job-weekly-primary"
    phase_g._setup_transcript_ready_video(
        repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(repository, video_id=video_id, job_id=job_id)
    committer, plan = phase_g._committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.persist_success(plan.success)

    vault_root = tmp_path / "project" / "vault"
    vault_subdir = "Knowledge"
    _complete_video_for_weekly(
        repository, video_id=video_id, vault_root=vault_root, vault_subdir=vault_subdir
    )
    reader = _authoritative_reader(repository, runtime._data_root)
    calls: list[str] = []

    def recording_reader(video_id: str) -> Any:
        calls.append(video_id)
        return reader.read(video_id)

    service = _weekly_service(
        repository,
        data_root=runtime._data_root,
        vault_root=vault_root,
        scoring_reader=recording_reader,
    )
    report = service.generate(now=_NOW)

    assert calls == [video_id]
    assert len(report.report.items) == 1


def test_legacy_null_pointer_weekly_succeeds_through_reader(
    tmp_path: Path,
) -> None:
    phase_g = _load_module("test_task016c_phase_g")
    runtime, _ = phase_g._judge_runtime(tmp_path / "project")
    repository = runtime._repository
    video_id = "video-weekly-legacy"
    job_id = "job-weekly-legacy"
    phase_g._setup_transcript_ready_video(
        repository, runtime._data_root, video_id=video_id
    )
    phase_g._setup_scoring_job(repository, video_id=video_id, job_id=job_id)
    connection = repository._connect()
    try:
        connection.execute(
            "UPDATE jobs SET scoring_lineage_version = NULL WHERE job_id = ?",
            (job_id,),
        )
    finally:
        connection.close()
    committer, plan = phase_g._committer_and_plan(
        runtime, job_id=job_id, video_id=video_id, owner="test-owner"
    )
    committer.persist_success(plan.success)
    # No authoritative pointer for a pre-lineage success.
    assert repository.get_video(video_id).authoritative_scoring_job_id is None

    vault_root = tmp_path / "project" / "vault"
    vault_subdir = "Knowledge"
    _complete_video_for_weekly(
        repository, video_id=video_id, vault_root=vault_root, vault_subdir=vault_subdir
    )
    reader = _authoritative_reader(repository, runtime._data_root)
    service = _weekly_service(
        repository, data_root=runtime._data_root, vault_root=vault_root,
        scoring_reader=reader.read, vault_subdir=vault_subdir,
    )
    report = service.generate(now=_NOW)

    # Legacy compatibility lives INSIDE the authoritative reader.
    assert len(report.report.items) == 1


def test_production_weekly_wiring_provides_reader(tmp_path: Path) -> None:
    flow = _load_module("test_task016c_phase_h2b_repair_flow")
    runtime = flow._runtime(tmp_path, flow._FakeTransport([]))

    captured: dict[str, Any] = {}
    original_service = __import__(
        "youtube_intel.runtime", fromlist=["WeeklyReportService"]
    ).WeeklyReportService

    class _CapturingService:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self._inner = original_service(
                **{**kwargs, "scoring_reader": kwargs.get("scoring_reader")}
            ) if kwargs.get("scoring_reader") else None

        def generate(self, *, now: datetime) -> Any:
            class _Ref:
                relative_path = "Weekly/2026-W35.md"

            class _Report:
                note_ref = _Ref()

            return _Report()

    import youtube_intel.runtime as runtime_module

    runtime_module.WeeklyReportService = _CapturingService
    try:
        runtime.weekly(week=None)
    finally:
        runtime_module.WeeklyReportService = original_service

    assert captured.get("scoring_reader") is not None
    assert callable(captured["scoring_reader"])
