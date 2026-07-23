from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel.domain import (
    AnalysisPoint,
    AnalysisResult,
    Availability,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    PointKind,
    ScoreResult,
)
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    PipelineStatus,
    RetentionClass,
    StorageRoot,
    VideoRecord,
    WeeklyCandidateRecord,
)

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)


@dataclass
class _Repository:
    candidates: tuple[WeeklyCandidateRecord, ...]
    reports: list[object] = field(default_factory=list)
    fail_next_upsert: bool = False

    def list_weekly_candidates(
        self, *, start_utc: datetime, end_utc: datetime
    ) -> tuple[WeeklyCandidateRecord, ...]:
        del start_utc, end_utc
        return self.candidates

    def upsert_report(self, report: object, *, now: datetime) -> object:
        del now
        if self.fail_next_upsert:
            self.fail_next_upsert = False
            raise RuntimeError("injected repository failure")
        self.reports.append(report)
        return report


def _candidate(root: Path, *, video_id: str, score: float, topic: str) -> WeeklyCandidateRecord:
    score_result = ScoreResult(
        schema_version="score-result-v1",
        score=score,
        reason=f"{video_id} is useful.",
        topics=(topic,),
        should_summarize=True,
        provider="fixture-score",
        model="fixture-model",
        prompt_version="scoring-prompt-v1",
        request_hash=("a" if video_id == "video-a" else "b") * 64,
    )
    analysis_result = AnalysisResult(
        one_sentence_summary=f"Summary for {video_id}.",
        core_points=(
            AnalysisPoint(
                text="Verified local fact.",
                kind=PointKind.FACT,
                evidence_ids=("evidence-1",),
            ),
        ),
        keywords=(topic,),
        evidence=(
            EvidenceExcerpt(
                evidence_id="evidence-1",
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="Verified excerpt.",
            ),
        ),
        provider="fixture-analysis",
        model="fixture-model",
        request_hash=("c" if video_id == "video-a" else "d") * 64,
    )
    score_bytes = score_result.model_dump_json().encode()
    analysis_bytes = analysis_result.model_dump_json().encode()
    score_path = f"scoring/{score_result.request_hash}/structured.json"
    analysis_path = f"analysis/{analysis_result.request_hash}/structured.json"
    for relative_path, content in ((score_path, score_bytes), (analysis_path, analysis_bytes)):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    video = VideoRecord(
        video_id=video_id,
        channel_id="channel-1",
        channel_name="Channel",
        title=f"Title {video_id}",
        description="",
        source_url=f"https://example.invalid/{video_id}",
        published_at=NOW,
        duration_seconds=60,
        default_language="en",
        available_languages=("en",),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
        pipeline_status=PipelineStatus.COMPLETE,
        pipeline_version="pipeline-v1",
        score=score,
        should_summarize=True,
        discovered_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
    )
    return WeeklyCandidateRecord(
        video=video,
        score_artifact=_artifact(
            video_id, ArtifactKind.SCORING_STRUCTURED, score_path, score_bytes,
            f"scoring/{score_result.request_hash}/structured", "fixture-score",
        ),
        analysis_artifact=_artifact(
            video_id, ArtifactKind.ANALYSIS_STRUCTURED, analysis_path, analysis_bytes,
            f"analysis/{analysis_result.request_hash}/structured", "fixture-analysis",
        ),
        note_artifact=_artifact(
            video_id, ArtifactKind.VIDEO_NOTE, f"Videos/{video_id}.md", b"note",
            f"video-note/pipeline-v1/{video_id}", None, root_type=StorageRoot.VAULT,
        ),
    )


def _artifact(
    video_id: str,
    kind: ArtifactKind,
    relative_path: str,
    content: bytes,
    artifact_key: str,
    provider: str | None,
    *,
    root_type: StorageRoot = StorageRoot.DATA,
) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=f"{kind.value}-{video_id}", artifact_key=artifact_key, video_id=video_id,
        job_id="job-1", kind=kind, storage_root=root_type, relative_path=relative_path,
        content_hash=hashlib.sha256(content).hexdigest(), provider=provider,
        model="fixture-model" if provider else None, producer_version="fixture-v1",
        retention_class=RetentionClass.LONG_LIVED, created_at=NOW, expires_at=None, deleted_at=None,
    )


def _service(tmp_path: Path, candidates: tuple[WeeklyCandidateRecord, ...]) -> tuple[WeeklyReportService, _Repository, Path]:
    repository = _Repository(candidates)
    vault_root = tmp_path / "vault"
    (vault_root / "Knowledge").mkdir(parents=True)
    sink = ObsidianNoteSink(
        vault_root=vault_root, vault_subdir="Knowledge", repository=repository,
        context=NoteWriteContext(job_id="unused-job", owner="test", pipeline_version="pipeline-v1"),
    )
    return (
        WeeklyReportService(repository=repository, sink=sink, artifact_root=tmp_path / "artifacts", timezone="Asia/Shanghai", top_n=1),
        repository,
        vault_root,
    )


def test_weekly_report_is_stable_top_n_and_upserts_one_temporary_vault_file(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    first = _candidate(artifact_root, video_id="video-a", score=9, topic="Product")
    second = _candidate(artifact_root, video_id="video-b", score=8, topic="Strategy")
    service, repository, vault_root = _service(tmp_path, (first, second))

    first_run = service.generate(now=NOW)
    content = (vault_root / "Knowledge" / first_run.note_ref.relative_path).read_bytes()
    second_run = service.generate(now=NOW)

    assert first_run.note_ref.relative_path == "Weekly/2026-W01.md"
    assert second_run.note_ref.content_hash == first_run.note_ref.content_hash
    assert (vault_root / "Knowledge" / first_run.note_ref.relative_path).read_bytes() == content
    assert len(repository.reports) == 2
    assert "[[Videos/video-a.md|Title video-a]]" in content.decode()
    assert "video-b" not in content.decode()


def test_weekly_report_writes_a_stable_empty_week(tmp_path: Path) -> None:
    service, repository, vault_root = _service(tmp_path, ())

    generated = service.generate(now=NOW)

    content = (vault_root / "Knowledge" / generated.note_ref.relative_path).read_text()
    assert generated.report.items == ()
    assert "本周没有符合条件的高价值视频。" in content
    assert "本周暂无可持续关注方向。" in content
    assert len(repository.reports) == 1


def test_weekly_report_retries_after_database_failure_without_duplicate_files(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(artifact_root, video_id="video-a", score=9, topic="Product")
    service, repository, vault_root = _service(tmp_path, (candidate,))
    repository.fail_next_upsert = True

    with pytest.raises(Exception, match="weekly report could not be committed"):
        service.generate(now=NOW)

    generated = service.generate(now=NOW)
    report_path = vault_root / "Knowledge" / generated.note_ref.relative_path
    assert report_path.is_file()
    assert list(report_path.parent.glob(".youtube-intel-*.tmp")) == []
    assert len(repository.reports) == 1
