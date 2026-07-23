"""Offline MVP acceptance flow using fixed data and temporary local resources."""

from __future__ import annotations

import hashlib
import json
import socket
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisPoint,
    AnalysisResult,
    Availability,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    PipelineStatus,
    PointKind,
    ProcessingStage,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
    SubtitleFormat,
    TranscriptArtifact,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import PipelineOrchestrator, StageDisposition
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.retry import RetryPolicy
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    RetentionClass,
    ScoringSummaryWrite,
    SQLiteStateRepository,
    StorageRoot,
)

NOW = datetime(2026, 7, 23, 8, 0, tzinfo=UTC)
PIPELINE_VERSION = "pipeline-v1"
SCENARIOS_PATH = Path(__file__).parent / "fixtures" / "mvp_scenarios.json"


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("offline acceptance tests must not use the network")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def _scenarios() -> tuple[dict[str, Any], ...]:
    loaded = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, list) and len(loaded) == 5
    return tuple(loaded)


def _metadata(scenario: dict[str, Any]) -> VideoMetadata:
    video_id = str(scenario["id"])
    return VideoMetadata(
        video_id=video_id,
        channel_id="UC_OFFLINE",
        channel_name="Offline Fixture Channel",
        title=str(scenario["title"]),
        description="Synthetic public description used only by this offline acceptance test.",
        source_url=f"https://example.invalid/watch?v={video_id}",
        published_at=NOW,
        duration_seconds=120,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _transcript(scenario: dict[str, Any]) -> TranscriptArtifact:
    video_id = str(scenario["id"])
    source = TranscriptSourceType(str(scenario["transcript_source"]))
    is_whisper = source is TranscriptSourceType.WHISPER
    return TranscriptArtifact(
        video_id=video_id,
        language="en",
        source_type=source,
        requested_language=None if is_whisper else "en",
        source_format=None if is_whisper else SubtitleFormat.VTT,
        text_path=f"transcripts/{video_id}/canonical.txt",
        timed_text_path=None if is_whisper else f"transcripts/{video_id}/source.vtt",
        source_content_hash=_digest(f"source:{video_id}"),
        source_byte_count=100,
        content_hash=_digest(f"canonical:{video_id}"),
        char_count=100,
        segment_count=3,
        normalization_version="fixture-normalization-v1",
        provider="offline-fixture",
        model="fake-whisper" if is_whisper else None,
        created_at=NOW,
    )


def _score(scenario: dict[str, Any]) -> ScoreResult:
    video_id = str(scenario["id"])
    high_value = float(scenario["score"]) >= 7.0
    return ScoreResult(
        schema_version="score-result-v1",
        score=float(scenario["score"]),
        reason="Fixed offline score for acceptance coverage.",
        topics=("product",),
        should_summarize=high_value,
        provider="fixture-scoring",
        model="fixture-local-model",
        prompt_version="scoring-prompt-v1",
        request_hash=_digest(f"score:{video_id}"),
    )


def _scoring_outcome(scenario: dict[str, Any]) -> ScoringOutcome:
    result = _score(scenario)
    return ScoringOutcome(
        result=result,
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=result.score >= 7.0,
            model_disagrees=False,
        ),
        call=ProviderCallMetadata(
            provider=result.provider,
            model=result.model,
            started_at=NOW,
            finished_at=NOW,
        ),
    )


def _analysis(scenario: dict[str, Any]) -> AnalysisCompleted:
    video_id = str(scenario["id"])
    title = str(scenario["title"])
    result = AnalysisResult(
        one_sentence_summary=f"Offline insight for {video_id}.",
        core_points=(
            AnalysisPoint(
                text="The fixture has a verified product-learning point.",
                kind=PointKind.FACT,
                evidence_ids=("title-1",),
            ),
        ),
        actionable_directions=(
            AnalysisPoint(
                text="Validate the fixture insight with a small user interview.",
                kind=PointKind.RECOMMENDATION,
                evidence_ids=("title-1",),
            ),
        ),
        keywords=("product",),
        evidence=(
            EvidenceExcerpt(
                evidence_id="title-1", source=EvidenceSource.TITLE, excerpt=title
            ),
        ),
        provider="fixture-analysis",
        model="fixture-cloud-model",
        request_hash=_digest(f"analysis:{video_id}"),
    )
    return AnalysisCompleted(
        result=result,
        call=ProviderCallMetadata(
            provider=result.provider,
            model=result.model,
            started_at=NOW,
            finished_at=NOW,
        ),
    )


class _OfflineStages:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        scenarios: tuple[dict[str, Any], ...],
        vault_root: Path,
    ) -> None:
        self.repository = repository
        self.scenarios = {str(scenario["id"]): scenario for scenario in scenarios}
        self.vault_root = vault_root
        self.calls: Counter[tuple[str, ProcessingStage]] = Counter()
        self.cloud_calls: Counter[str] = Counter()
        self.note_job_ids: dict[str, str] = {}

    def __call__(self, job: object, video: object) -> StageDisposition:
        stage = getattr(job, "target_stage")
        video_id = str(getattr(video, "video_id"))
        scenario = self.scenarios[video_id]
        self.calls[(video_id, stage)] += 1
        owner = str(getattr(job, "lease_owner"))

        if stage is ProcessingStage.NOTE_WRITE:
            self.note_job_ids[video_id] = str(getattr(job, "job_id"))
            sink = ObsidianNoteSink(
                vault_root=self.vault_root,
                vault_subdir="Knowledge",
                repository=self.repository,
                context=NoteWriteContext(
                    job_id=str(getattr(job, "job_id")),
                    owner=owner,
                    pipeline_version=PIPELINE_VERSION,
                ),
            )
            sink.upsert_video_note(
                video=_metadata(scenario),
                transcript=_transcript(scenario),
                scoring=_scoring_outcome(scenario),
                analysis=_analysis(scenario),
                processed_at=NOW,
                pipeline_version=PIPELINE_VERSION,
            )
            return StageDisposition.CONTINUE

        target = {
            ProcessingStage.METADATA: PipelineStatus.METADATA_READY,
            ProcessingStage.TRANSCRIPT: PipelineStatus.TRANSCRIPT_READY,
            ProcessingStage.SCORING: PipelineStatus.SCORED,
            ProcessingStage.ANALYSIS: PipelineStatus.ANALYSIS_READY,
        }[stage]
        if stage is ProcessingStage.ANALYSIS:
            self.cloud_calls[video_id] += 1
        self.repository.complete_stage(
            job_id=str(getattr(job, "job_id")),
            owner=owner,
            video_id=video_id,
            expected_status=getattr(video, "pipeline_status"),
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            artifacts=(),
            provider_call=None,
            scoring_summary=(
                ScoringSummaryWrite(
                    score=_score(scenario).score,
                    should_summarize=_score(scenario).score >= 7.0,
                )
                if stage is ProcessingStage.SCORING
                else None
            ),
            now=NOW,
        )
        return StageDisposition.CONTINUE


def _pipeline(
    repository: SQLiteStateRepository, stages: _OfflineStages
) -> PipelineOrchestrator:
    next_job = 0

    def job_id() -> str:
        nonlocal next_job
        next_job += 1
        return f"e2e-job-{next_job:03d}"

    return PipelineOrchestrator(
        repository=repository,
        planner=PipelineJobPlanner(
            repository=repository,
            pipeline_version=PIPELINE_VERSION,
            max_attempts=3,
            job_id_factory=job_id,
        ),
        owner="offline-e2e-worker",
        lease_seconds=60,
        retry_policy=RetryPolicy(
            base_delay_seconds=1, max_delay_seconds=8, jitter_ratio=0
        ),
        handlers={
            stage: stages
            for stage in ProcessingStage
            if stage not in {ProcessingStage.DISCOVERY, ProcessingStage.WEEKLY_REPORT}
        },
        clock=lambda: NOW,
    )


def _write_report_inputs(
    repository: SQLiteStateRepository,
    scenarios: tuple[dict[str, Any], ...],
    data_root: Path,
    note_job_ids: dict[str, str],
) -> None:
    for scenario in scenarios:
        if _score(scenario).score < 7.0:
            continue
        video_id = str(scenario["id"])
        for result, kind, prefix in (
            (_score(scenario), ArtifactKind.SCORING_STRUCTURED, "scoring"),
            (_analysis(scenario).result, ArtifactKind.ANALYSIS_STRUCTURED, "analysis"),
        ):
            content = result.model_dump_json().encode("utf-8")
            relative_path = f"{prefix}/{result.request_hash}/structured.json"
            path = data_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            repository.upsert_artifact(
                ArtifactWrite(
                    artifact_id=f"{prefix}-{video_id}",
                    artifact_key=f"{prefix}/{result.request_hash}/structured",
                    video_id=video_id,
                    job_id=note_job_ids[video_id],
                    kind=kind,
                    storage_root=StorageRoot.DATA,
                    relative_path=relative_path,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    provider=result.provider,
                    model=result.model,
                    producer_version="offline-e2e-fixture-v1",
                    retention_class=RetentionClass.LONG_LIVED,
                    expires_at=None,
                ),
                now=NOW,
            )


def _table_counts(database: Path) -> tuple[int, int, int, int]:
    connection = sqlite3.connect(database)
    try:
        return tuple(
            int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            for table in ("videos", "jobs", "artifacts", "reports")
        )
    finally:
        connection.close()


def test_fixed_offline_mvp_flow_is_idempotent_and_preserves_user_knowledge(
    tmp_path: Path,
) -> None:
    scenarios = _scenarios()
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=NOW)
    for scenario in scenarios:
        repository.upsert_video_metadata(
            _metadata(scenario), pipeline_version=PIPELINE_VERSION, now=NOW
        )
    vault_root = tmp_path / "vault"
    (vault_root / "Knowledge").mkdir(parents=True)
    stages = _OfflineStages(repository, scenarios, vault_root)
    pipeline = _pipeline(repository, stages)
    video_ids = tuple(str(scenario["id"]) for scenario in scenarios)

    pipeline.run_batch(video_ids)

    statuses = {
        video_id: repository.get_video(video_id).pipeline_status
        for video_id in video_ids
    }
    assert set(statuses.values()) == {PipelineStatus.COMPLETE}, statuses
    assert stages.calls[("manual", ProcessingStage.TRANSCRIPT)] == 1
    assert stages.calls[("automatic", ProcessingStage.TRANSCRIPT)] == 1
    assert stages.calls[("whisper", ProcessingStage.TRANSCRIPT)] == 1
    assert stages.cloud_calls["low001"] == 0
    assert sum(stages.cloud_calls.values()) == 4

    high_artifact = repository.get_artifact_by_key(
        f"video-note/{PIPELINE_VERSION}/high001"
    )
    assert high_artifact is not None
    high_path = vault_root / "Knowledge" / high_artifact.relative_path
    high_content = high_path.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(high_content.split("---\n", 2)[1])
    assert frontmatter["video_id"] == "high001"
    assert "<!-- youtube-intel:user:start:v1 -->" in high_content

    _write_report_inputs(repository, scenarios, tmp_path / "data", stages.note_job_ids)
    sink = ObsidianNoteSink(
        vault_root=vault_root,
        vault_subdir="Knowledge",
        repository=repository,
        context=NoteWriteContext(
            job_id="weekly-e2e-job", owner="offline-e2e-worker", pipeline_version=PIPELINE_VERSION
        ),
    )
    weekly = WeeklyReportService(
        repository=repository,
        sink=sink,
        artifact_root=tmp_path / "data",
        timezone="Asia/Shanghai",
        top_n=10,
    )
    first_report = weekly.generate(now=NOW)
    weekly_path = vault_root / "Knowledge" / first_report.note_ref.relative_path
    first_weekly = weekly_path.read_bytes()
    assert "[[Videos/" in first_weekly.decode("utf-8")
    assert high_artifact.relative_path in first_weekly.decode("utf-8")

    before = (_table_counts(tmp_path / "state.sqlite3"), stages.calls.copy(), stages.cloud_calls.copy())
    pipeline.run_batch(video_ids)
    second_report = weekly.generate(now=NOW)
    assert _table_counts(tmp_path / "state.sqlite3") == before[0]
    assert stages.calls == before[1]
    assert stages.cloud_calls == before[2]
    assert second_report.note_ref.content_hash == first_report.note_ref.content_hash
    assert weekly_path.read_bytes() == first_weekly
    assert len(list((vault_root / "Knowledge" / "Videos").glob("*.md"))) == 4
    assert len(list((vault_root / "Knowledge" / "Weekly").glob("*.md"))) == 1
    assert not list((vault_root / "Knowledge").rglob(".youtube-intel-*.tmp"))

    high_path.write_text(
        high_content.replace("## 我的思考\n\n", "## 我的思考\n\n用户保留的离线笔记\n"),
        encoding="utf-8",
    )
    high_scenario = next(s for s in scenarios if s["id"] == "high001")
    ObsidianNoteSink(
        vault_root=vault_root,
        vault_subdir="Knowledge",
        repository=repository,
        context=NoteWriteContext(
            job_id="verify-completed-note",
            owner="offline-e2e-worker",
            pipeline_version=PIPELINE_VERSION,
        ),
    ).upsert_video_note(
        video=_metadata(high_scenario),
        transcript=_transcript(high_scenario),
        scoring=_scoring_outcome(high_scenario),
        analysis=_analysis(high_scenario),
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )
    assert "用户保留的离线笔记" in high_path.read_text(encoding="utf-8")
