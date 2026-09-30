from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field, replace
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
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
)
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.scoring import VerifiedScoringRead
from youtube_intel.state import (
    ArtifactKind,
    ArtifactRecord,
    PipelineStatus,
    RetentionClass,
    StorageRoot,
    VideoRecord,
    WeeklyCandidateRecord,
)
from youtube_intel.summary_evidence_authority import CURRENT_SUMMARY_PROMPT_VERSION

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)


#: A durable Evidence identity, exactly as the shared current-Summary gate
#: requires: 64 hex characters that resolve through both repository readers.
DURABLE_EVIDENCE_ID = "a" * 64


class _Evidence:
    """The minimum a current-authority check needs from an Evidence record."""

    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self.availability = "AVAILABLE"


class _VerifiedText:
    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self.excerpt = "Verified excerpt."


@dataclass
class _Repository:
    candidates: tuple[WeeklyCandidateRecord, ...]
    reports: list[object] = field(default_factory=list)
    fail_next_upsert: bool = False
    durable_evidence_ids: frozenset[str] = frozenset({DURABLE_EVIDENCE_ID})

    def list_weekly_candidates(
        self, *, start_utc: datetime, end_utc: datetime
    ) -> tuple[WeeklyCandidateRecord, ...]:
        del start_utc, end_utc
        return self.candidates

    def get_evidence(self, evidence_id: str) -> _Evidence | None:
        return (
            _Evidence(evidence_id)
            if evidence_id in self.durable_evidence_ids
            else None
        )

    def resolve_verified_evidence_text(self, evidence_id: str) -> _VerifiedText | None:
        return (
            _VerifiedText(evidence_id)
            if evidence_id in self.durable_evidence_ids
            else None
        )

    def upsert_report(self, report: object, *, now: datetime) -> object:
        del now
        if self.fail_next_upsert:
            self.fail_next_upsert = False
            raise RuntimeError("injected repository failure")
        self.reports.append(report)
        return report


def _candidate(
    root: Path,
    *,
    video_id: str,
    score: float,
    topic: str,
    analysis_keyword: str | None = None,
    analysis_keywords: tuple[str, ...] | None = None,
    direction: str = "Use the verified direction.",
    with_analysis: bool = True,
) -> WeeklyCandidateRecord:
    score_result = ScoreResult(
        schema_version="score-result-v2",
        score=score,
        reason="This video provides useful practical guidance.",
        topics=(topic,),
        should_summarize=True,
        provider="fixture-score",
        model="fixture-model",
        prompt_version="scoring-prompt-v2",
        request_hash=hashlib.sha256(f"score:{video_id}".encode()).hexdigest(),
        output_language="en",
    )
    analysis_result = AnalysisResult(
        one_sentence_summary=f"Summary for {video_id}.",
        core_points=(
            AnalysisPoint(
                text="Verified local fact.",
                kind=PointKind.FACT,
                evidence_ids=(DURABLE_EVIDENCE_ID,),
            ),
        ),
        actionable_directions=(
            AnalysisPoint(
                text=direction,
                kind=PointKind.RECOMMENDATION,
                evidence_ids=(DURABLE_EVIDENCE_ID,),
            ),
        ),
        keywords=analysis_keywords or (analysis_keyword or topic,),
        evidence=(
            EvidenceExcerpt(
                evidence_id=DURABLE_EVIDENCE_ID,
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="Verified excerpt.",
            ),
        ),
        provider="fixture-analysis",
        model="fixture-model",
        prompt_version=CURRENT_SUMMARY_PROMPT_VERSION,
        request_hash=hashlib.sha256(f"analysis:{video_id}".encode()).hexdigest(),
    )
    score_bytes = score_result.model_dump_json().encode()
    analysis_bytes = analysis_result.model_dump_json().encode()
    score_path = f"scoring/{score_result.request_hash}/structured.json"
    analysis_path = f"analysis/{analysis_result.request_hash}/structured.json"
    artifacts = [(score_path, score_bytes)]
    if with_analysis:
        artifacts.append((analysis_path, analysis_bytes))
    for relative_path, content in artifacts:
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
        analysis_artifact=(
            _artifact(
                video_id, ArtifactKind.ANALYSIS_STRUCTURED, analysis_path, analysis_bytes,
                f"analysis/{analysis_result.request_hash}/structured", "fixture-analysis",
            )
            if with_analysis
            else None
        ),
        note_artifact=_artifact(
            video_id, ArtifactKind.VIDEO_NOTE, f"Videos/note--{video_id}.md", b"note",
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


def _scoring_reader(
    candidates: tuple[WeeklyCandidateRecord, ...], artifact_root: Path
):
    """VerifiedScoringRead stub for post-verification formatting tests.

    These tests exercise weekly rendering/top-n/upsert behavior, not scoring
    authority, so the reader resolves each candidate's pre-verified fixture
    score exactly as the authoritative reader would hand it back.
    """

    threshold = 7.0
    by_video = {candidate.video.video_id: candidate for candidate in candidates}

    def read(video_id: str) -> VerifiedScoringRead:
        candidate = by_video[video_id]
        body = (artifact_root / candidate.score_artifact.relative_path).read_bytes()
        result = ScoreResult.model_validate_json(body)
        final = result.score >= threshold
        decision = ScoringDecision(
            threshold=threshold,
            final_should_summarize=final,
            model_disagrees=(result.should_summarize != final),
        )
        call = ProviderCallMetadata(
            provider=result.provider,
            started_at=NOW,
            finished_at=NOW,
            model=result.model,
        )
        outcome = ScoringOutcome(result=result, decision=decision, call=call)
        return VerifiedScoringRead(
            scoring_outcome=outcome,
            video_id=video_id,
            scoring_job_id="job-1",
            scoring_success_provenance=None,
        )

    return read


def _service(
    tmp_path: Path, candidates: tuple[WeeklyCandidateRecord, ...], *, top_n: int = 1
) -> tuple[WeeklyReportService, _Repository, Path]:
    repository = _Repository(candidates)
    vault_root = tmp_path / "vault"
    (vault_root / "Knowledge").mkdir(parents=True)
    for candidate in candidates:
        note_path = vault_root / "Knowledge" / candidate.note_artifact.relative_path
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_bytes(b"note")
    sink = ObsidianNoteSink(
        vault_root=vault_root, vault_subdir="Knowledge", repository=repository,
        context=NoteWriteContext(job_id="unused-job", owner="test", pipeline_version="pipeline-v1"),
    )
    artifact_root = tmp_path / "artifacts"
    return (
        WeeklyReportService(
            repository=repository,
            sink=sink,
            artifact_root=artifact_root,
            timezone="Asia/Shanghai",
            top_n=top_n,
            scoring_reader=_scoring_reader(candidates, artifact_root),
        ),
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
    assert "[[Videos/note--video-a.md|Title video-a]]" in content.decode()
    assert "video-b" not in content.decode()


def test_weekly_report_writes_a_stable_empty_week(tmp_path: Path) -> None:
    service, repository, vault_root = _service(tmp_path, ())

    generated = service.generate(now=NOW)

    content = (vault_root / "Knowledge" / generated.note_ref.relative_path).read_text()
    assert generated.report.items == ()
    assert "本周没有符合条件的高价值视频。" in content
    assert "本周暂无可持续关注方向。" in content
    assert len(repository.reports) == 1


def test_cloud_disabled_candidate_still_appears_without_analysis_trends(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(
        artifact_root,
        video_id="video-local",
        score=9,
        topic="local-topic",
        with_analysis=False,
    )
    service, _, vault_root = _service(tmp_path, (candidate,))

    generated = service.generate(now=NOW)

    content = (vault_root / "Knowledge" / generated.note_ref.relative_path).read_text()
    assert "[[Videos/note--video-local.md|Title video-local]]" in content
    assert "云端深度分析未启用；请查看视频笔记。" in content
    assert "local-topic" not in content
    assert "本周暂无可持续关注方向。" in content


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


def test_weekly_trends_keywords_and_directions_only_use_verified_analysis(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    first = _candidate(
        artifact_root,
        video_id="video-a",
        score=9,
        topic="shared-score-topic",
        analysis_keyword="Alpha",
        direction="Explore Alpha demand.",
    )
    second = _candidate(
        artifact_root,
        video_id="video-b",
        score=8,
        topic="shared-score-topic",
        analysis_keyword="Beta",
        direction="Validate Beta demand.",
    )
    service, _, vault_root = _service(tmp_path, (first, second), top_n=2)

    generated = service.generate(now=NOW)

    content = (vault_root / "Knowledge" / generated.note_ref.relative_path).read_text()
    assert "Alpha（1）" in content
    assert "Beta（1）" in content
    assert "趋势：Alpha（1）" in content
    assert "趋势：Beta（1）" in content
    assert "持续关注：Explore Alpha demand." in content
    assert "持续关注：Validate Beta demand." in content
    assert "shared-score-topic" not in content


def test_tampered_analysis_fails_closed_before_writing_weekly_report(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(artifact_root, video_id="video-a", score=9, topic="Product")
    service, repository, vault_root = _service(tmp_path, (candidate,))
    (artifact_root / candidate.analysis_artifact.relative_path).write_text("tampered")

    with pytest.raises(ValueError, match="analysis"):
        service.generate(now=NOW)

    assert not (vault_root / "Knowledge" / "Weekly").exists()
    assert repository.reports == []


def test_missing_or_identity_mismatched_analysis_fails_closed(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(artifact_root, video_id="video-a", score=9, topic="Product")
    analysis_path = artifact_root / candidate.analysis_artifact.relative_path
    analysis_bytes = analysis_path.read_bytes()
    analysis_path.unlink()
    service, repository, vault_root = _service(tmp_path, (candidate,))

    with pytest.raises(ValueError, match="analysis"):
        service.generate(now=NOW)

    mismatched = replace(
        candidate,
        analysis_artifact=replace(candidate.analysis_artifact, artifact_key="analysis/not-the-result/structured"),
    )
    service, repository, _ = _service(tmp_path / "mismatched", (mismatched,))
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_bytes(analysis_bytes)

    with pytest.raises(ValueError, match="analysis"):
        service.generate(now=NOW)

    assert not (vault_root / "Knowledge" / "Weekly").exists()
    assert repository.reports == []


def test_analysis_aggregation_normalizes_frequency_and_tie_order(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    first = _candidate(
        artifact_root, video_id="video-a", score=9, topic="shared", analysis_keyword=" Alpha\n", direction="Follow Alpha."
    )
    second = _candidate(
        artifact_root, video_id="video-b", score=8, topic="shared", analysis_keyword="Beta", direction="Follow Beta."
    )
    third = _candidate(
        artifact_root, video_id="video-c", score=7, topic="shared", analysis_keyword="alpha", direction=" Follow Alpha. "
    )
    service, _, vault_root = _service(tmp_path, (first, second, third), top_n=3)

    generated = service.generate(now=NOW)

    content = (vault_root / "Knowledge" / generated.note_ref.relative_path).read_text()
    assert "Alpha（2）" in content
    assert "Beta（1）" in content
    assert content.index("趋势：Alpha（2）") < content.index("趋势：Beta（1）")
    assert content.count("持续关注：Follow Alpha.") == 1


def test_analysis_keyword_normalization_deduplicates_one_video_before_counting(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(
        artifact_root,
        video_id="video-a",
        score=9,
        topic="shared",
        analysis_keywords=("Alpha", " alpha "),
    )
    service, _, vault_root = _service(tmp_path, (candidate,))

    generated = service.generate(now=NOW)

    content = (vault_root / "Knowledge" / generated.note_ref.relative_path).read_text()
    assert "Alpha（1）" in content
    assert "Alpha（2）" not in content


@pytest.mark.parametrize(
    "failure", ("missing", "tampered", "symlink", "directory_symlink")
)
def test_unverified_managed_note_ref_fails_closed_before_weekly_writes(
    tmp_path: Path, failure: str
) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(artifact_root, video_id="video-a", score=9, topic="Product")
    service, repository, vault_root = _service(tmp_path, (candidate,))
    note_path = vault_root / "Knowledge" / candidate.note_artifact.relative_path
    if failure == "missing":
        note_path.unlink()
    elif failure == "tampered":
        note_path.write_bytes(b"tampered note")
    elif failure == "symlink":
        note_path.unlink()
        outside = tmp_path / "outside.md"
        outside.write_bytes(b"note")
        os.symlink(outside, note_path)
    else:
        note_path.unlink()
        note_path.parent.rmdir()
        outside_dir = tmp_path / "outside-videos"
        outside_dir.mkdir()
        (outside_dir / note_path.name).write_bytes(b"note")
        os.symlink(outside_dir, note_path.parent, target_is_directory=True)

    with pytest.raises(ValueError, match="note"):
        service.generate(now=NOW)

    assert not (vault_root / "Knowledge" / "Weekly").exists()
    assert repository.reports == []


def test_note_ref_path_escape_or_provenance_mismatch_fails_closed(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    candidate = _candidate(artifact_root, video_id="video-a", score=9, topic="Product")
    service, repository, vault_root = _service(tmp_path, (candidate,))
    escaped = replace(
        candidate,
        note_artifact=replace(
            candidate.note_artifact, relative_path="Videos/../outside--video-a.md"
        ),
    )
    repository.candidates = (escaped,)

    with pytest.raises(ValueError, match="note"):
        service.generate(now=NOW)

    mismatched = replace(
        candidate,
        note_artifact=replace(
            candidate.note_artifact, artifact_key="video-note/wrong/video-a"
        ),
    )
    repository.candidates = (mismatched,)

    with pytest.raises(ValueError, match="note"):
        service.generate(now=NOW)

    assert not (vault_root / "Knowledge" / "Weekly").exists()
    assert repository.reports == []
