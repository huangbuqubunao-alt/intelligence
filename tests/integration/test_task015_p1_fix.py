"""P1 Correction coverage for TASK-015.

- Scoped single-video processing must not claim jobs for other videos.
- Persisted scoring/analysis recovery must validate full provenance.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from youtube_intel.cli import ExitCode, main
from youtube_intel.config import load_app_config
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisResult,
    Availability,
    ChannelRef,
    ContentQualityConfidence,
    ContentQualityDecisionSource,
    ContentQualityInput,
    ContentQualityResult,
    ContentQualitySignal,
    ContentQualityStatus,
    DiscoveryBatch,
    DiscoveryCursor,
    EvidenceSource,
    LiveStatus,
    PointKind,
    ProviderCallMetadata,
    QualityJudgeOperationInput,
    ScoringInput,
    SubtitleFormat,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.providers.ollama import parse_scoring_candidate
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.scoring import (
    PhaseFTrustedScoringSuccess,
    PrimaryScoringAttempt,
    ScoringPersistenceError,
    build_primary_scoring_attempt,
    build_scoring_input,
)
from youtube_intel.scoring_admission import ScoringDispatchAdmission
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    IntegrityConflict,
    JobStatus,
    JobType,
    PipelineStatus,
    ProcessingStage,
    ProviderCallRequest,
    ProviderCallStatus,
    RetentionClass,
    ScoringSummaryWrite,
    SQLiteStateRepository,
    StorageRoot,
)
from youtube_intel.transcripts import (
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
)

NOW = datetime(2026, 8, 12, 8, tzinfo=UTC)
VIDEO_ID = "2A1IEBFt6Xg"
SECOND_VIDEO_ID = "5ljV0Vxu00M"
CHANNEL_ID = "UCsooa4yRKGN_zEE8iknghZA"


class _AdmissionRepository:
    def get_job(self, job_id: str) -> object | None:
        if job_id != "task015-admission-job":
            return None
        return type(
            "_AdmissionJob",
            (),
            {
                "target_stage": ProcessingStage.SCORING,
                "status": JobStatus.RUNNING,
                "lease_owner": "task015-test",
                "lease_until": datetime.now(UTC) + timedelta(minutes=5),
            },
        )()

    def get_provider_call(self, request_hash: str) -> None:
        del request_hash
        return None


def _h1_admission() -> ScoringDispatchAdmission:
    return ScoringDispatchAdmission(
        repository=_AdmissionRepository(),  # type: ignore[arg-type]
        job_id="task015-admission-job",
        owner="task015-test",
    )
PIPELINE_VERSION = "runtime-v1"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "subtitles"


def _project(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "vault").mkdir()
    (tmp_path / "config" / "channels.yaml").write_text(
        f"channels:\n  - channel_id: {CHANNEL_ID}\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
local_scoring:
  model: qwen3:8b
  expected_model_digest: sha256:{'1' * 64}
cloud:
  enabled: true
  model: gpt-4.1-mini
  api_key_env: OPENAI_API_KEY
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {tmp_path / 'vault'}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )
    return tmp_path


class _DiscoverySource:
    calls = 0

    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch:
        self.calls += 1
        assert channel.channel_id == CHANNEL_ID
        return DiscoveryBatch(
            channel_id=channel.channel_id,
            video_ids=(VIDEO_ID, SECOND_VIDEO_ID),
            next_cursor=DiscoveryCursor(
                channel_id=channel.channel_id,
                last_checked_at=NOW,
                latest_published_at=NOW,
                latest_video_id=VIDEO_ID,
            ),
            call=ProviderCallMetadata(
                provider="controlled-rss-boundary",
                started_at=NOW,
                finished_at=NOW,
            ),
        )


class _MetadataProvider:
    calls = 0

    def fetch(self, video_id: str) -> VideoMetadata:
        self.calls += 1
        return VideoMetadata(
            video_id=video_id,
            channel_id=CHANNEL_ID,
            channel_name="Public test channel",
            title=f"A short public product lesson {video_id}",
            description="Public metadata fixture.",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=NOW,
            duration_seconds=120,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        )


class _SubtitleAdapter:
    provider_name = "controlled-subtitle-boundary"
    provider_version = "fixture-v1"

    def __init__(self) -> None:
        self.enumerate_calls = 0
        self.read_calls = 0
        self._call = ProviderCallMetadata(
            provider=self.provider_name,
            provider_version=self.provider_version,
            started_at=NOW,
            finished_at=NOW,
        )

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        self.enumerate_calls += 1
        return SubtitleTrackListing(
            tracks=(
                SubtitleTrack(
                    source_type=TranscriptSourceType.MANUAL_SUBTITLE,
                    language="en",
                    source_format=SubtitleFormat.JSON3,
                    name="English",
                    url="https://example.invalid/subtitle",
                    provider_position=0,
                ),
            ),
            call=self._call,
        )

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        assert track.language == "en"
        self.read_calls += 1
        return SubtitleReadResult(
            body=(FIXTURES / "manual_en.json3").read_bytes(),
            call=self._call,
        )


class _ScoringProvider:
    def __init__(self) -> None:
        self.calls = 0
        self._raw_response: str | None = None

    def _raw_envelope(self) -> str:
        inner = json.dumps(
            {
                "score": 8.6,
                "reason": "受控本地评分覆盖了正式运行时组合。",
                "topics": ["product"],
                "should_summarize": True,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return json.dumps(
            {"model": "qwen3:8b", "response": inner, "done": True},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def primary_attempt(self, scoring_input: object) -> PrimaryScoringAttempt:
        self.calls += 1
        self._raw_response = self._raw_envelope()
        candidate = parse_scoring_candidate(self._raw_response)
        return build_primary_scoring_attempt(
            scoring_input=scoring_input,  # type: ignore[arg-type]
            candidate=candidate,
            final_raw_response=self._raw_response,
            provider="ollama",
            model="qwen3:8b",
            model_digest="sha256:" + "1" * 64,
            temperature=0.0,
            max_output_tokens=1200,
            max_description_chars=32,
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert request_hash
        assert self._raw_response is not None
        response = self._raw_response
        self._raw_response = None
        return response


class _AnalysisProvider:
    def __init__(self) -> None:
        self.calls = 0

    def summarize_with_credential(
        self, analysis_input: object, credential: str
    ) -> AnalysisResult:
        self.calls += 1
        assert credential == "synthetic-key"
        return AnalysisResult(
            one_sentence_summary="Fixture analysis.",
            core_points=[
                {
                    "text": "A core point.",
                    "kind": "fact",
                    "evidence_ids": ["title-1"],
                }
            ],
            keywords=["fixture"],
            evidence=[
                {
                    "evidence_id": "title-1",
                    "source": "title",
                    "excerpt": "Fixture title",
                }
            ],
            provider="openai",
            model="gpt-4.1-mini",
            request_hash=getattr(analysis_input, "request_hash"),
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert request_hash
        return json.dumps({"output_text": {"one_sentence_summary": "Fixture."}})


class _QualityJudgeProvider:
    """Controlled Judge boundary that always PASSes the fixture candidate."""

    def judge(
        self,
        operation_input: QualityJudgeOperationInput,
        *,
        content_input: ContentQualityInput | None,
    ) -> ContentQualityResult:
        del content_input
        return ContentQualityResult.model_validate(
            {
                "status": ContentQualityStatus.PASS,
                "decision_source": ContentQualityDecisionSource.LOCAL_JUDGE,
                "decision_confidence": ContentQualityConfidence.HIGH,
                "grounding_confidence": ContentQualityConfidence.MEDIUM,
                "usefulness_confidence": ContentQualityConfidence.MEDIUM,
                "signals": [
                    ContentQualitySignal.MINIMAL_CLAIM_PRESENT,
                    ContentQualitySignal.GROUNDING_PRESENT,
                ],
                "reason": None,
                "evidence_ids": ["title-1"],
                "candidate_hash": operation_input.candidate_hash,
                "quality_input_hash": operation_input.quality_input_hash,
                "scoring_request_hash": operation_input.scoring_request_hash,
                "judge_provider": operation_input.judge_provider,
                "judge_model": operation_input.judge_model,
                "judge_model_digest": operation_input.judge_model_digest,
            }
        )


def _dependencies(
    subtitle: _SubtitleAdapter | None = None,
    scoring: _ScoringProvider | None = None,
    analysis: _AnalysisProvider | None = None,
    judge: _QualityJudgeProvider | None = None,
) -> RuntimeDependencies:
    return RuntimeDependencies(
        discovery_source=_DiscoverySource(),
        metadata_provider=_MetadataProvider(),
        subtitle_adapter_factory=lambda: subtitle or _SubtitleAdapter(),
        scoring_provider_factory=lambda: scoring or _ScoringProvider(),
        analysis_provider_factory=lambda: analysis or _AnalysisProvider(),
        quality_judge_provider_factory=lambda: judge or _QualityJudgeProvider(),
    )


def _insert_pending_b_job(repository: SQLiteStateRepository) -> None:
    repository.create_job(
        job_id="pending-b-job",
        scope_key=f"video:{SECOND_VIDEO_ID}:{ProcessingStage.METADATA.value}",
        video_id=SECOND_VIDEO_ID,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.METADATA,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=NOW,
        now=NOW,
    )


def test_process_video_scopes_claim_to_selected_video_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    subtitle = _SubtitleAdapter()
    scoring = _ScoringProvider()
    analysis = _AnalysisProvider()

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(subtitle, scoring, analysis),
    )

    assert main(["--project-root", str(project), "check", "--limit", "2"]) is ExitCode.OK
    capsys.readouterr()

    repository = SQLiteStateRepository(project / "data" / "state.sqlite")
    _insert_pending_b_job(repository)
    b_before = repository.get_job("pending-b-job")
    assert b_before is not None

    assert main(["--project-root", str(project), "process", "--video", VIDEO_ID]) is ExitCode.OK
    output = capsys.readouterr()
    assert "Processed 1 video" in output.out

    a_video = repository.get_video(VIDEO_ID)
    assert a_video is not None
    assert a_video.pipeline_status is PipelineStatus.COMPLETE

    b_after = repository.get_job("pending-b-job")
    assert b_after is not None
    assert b_after.status is JobStatus.PENDING
    assert b_after.attempt_count == b_before.attempt_count
    assert b_after.lease_owner == b_before.lease_owner
    assert b_after.lease_until == b_before.lease_until

    b_video = repository.get_video(SECOND_VIDEO_ID)
    assert b_video is not None
    assert b_video.pipeline_status is PipelineStatus.DISCOVERED

    assert repository.latest_artifact(SECOND_VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL) is None
    assert repository.latest_artifact(SECOND_VIDEO_ID, ArtifactKind.SCORING_STRUCTURED) is None
    assert repository.latest_artifact(SECOND_VIDEO_ID, ArtifactKind.ANALYSIS_STRUCTURED) is None

    assert main(["--project-root", str(project), "process"]) is ExitCode.OK
    b_video = repository.get_video(SECOND_VIDEO_ID)
    assert b_video is not None
    assert b_video.pipeline_status is PipelineStatus.COMPLETE


def test_process_video_without_pending_job_ends_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(),
    )

    assert main(["--project-root", str(project), "check", "--limit", "2"]) is ExitCode.OK
    capsys.readouterr()

    repository = SQLiteStateRepository(project / "data" / "state.sqlite")
    _insert_pending_b_job(repository)

    assert main(["--project-root", str(project), "process", "--video", VIDEO_ID]) is ExitCode.OK
    output = capsys.readouterr()
    assert "Processed 1 video" in output.out

    b_after = repository.get_job("pending-b-job")
    assert b_after is not None
    assert b_after.status is JobStatus.PENDING
    assert b_after.attempt_count == 0


def _config(project: Path) -> Any:
    return load_app_config(
        project / "config" / "channels.yaml",
        project / "config" / "settings.yaml",
    )


def _runtime_ops(project: Path, monkeypatch: pytest.MonkeyPatch) -> RuntimeOperations:
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(),
    )
    return RuntimeOperations(config=_config(project), project_root=project)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _trusted_scoring_success(
    ops: RuntimeOperations,
    video_id: str,
) -> tuple[ScoringInput, PhaseFTrustedScoringSuccess]:
    scoring_input = build_scoring_input(
        video=VideoMetadata(
            video_id=video_id,
            channel_id=CHANNEL_ID,
            channel_name="Test channel",
            title=f"Video {video_id}",
            description="Fixture",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=NOW,
            duration_seconds=120,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        transcript_text="Trusted scoring fixture transcript evidence.",
        language="en",
        output_language=ops._config.settings.general.output_language,
        settings=ops._config.settings.local_scoring,
    )
    provider = ops._dependencies.scoring_provider_factory()
    success = ops._run_primary_trusted_scoring(
        attempt=provider.primary_attempt(scoring_input),
        scoring_input=scoring_input,
        admission=_h1_admission(),
    )
    assert type(success) is PhaseFTrustedScoringSuccess
    return scoring_input, success


def _persist_trusted_scoring_success(
    ops: RuntimeOperations,
    video_id: str,
    job_id: str,
    now: datetime,
) -> tuple[ArtifactWrite, ArtifactWrite, str]:
    scoring_input, success = _trusted_scoring_success(ops, video_id)
    entry = ops._trusted_persistence_entry(
        job_id=job_id,
        owner="test-owner",
        pipeline_version=PIPELINE_VERSION,
    )
    entry._clock = lambda: now  # type: ignore[method-assign]
    persisted = entry.persist_success(success)
    artifacts = {artifact.kind: artifact for artifact in persisted.artifacts}
    return (
        artifacts[ArtifactKind.SCORING_RAW],
        artifacts[ArtifactKind.SCORING_STRUCTURED],
        scoring_input.request_hash,
    )


def _setup_scoring_video_and_job(
    repository: SQLiteStateRepository,
    video_id: str,
    job_id: str,
    now: datetime,
) -> None:
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=CHANNEL_ID,
            channel_name="Test channel",
            title=f"Video {video_id}",
            description="Fixture",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=now,
            duration_seconds=120,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version=PIPELINE_VERSION,
        now=now,
    )
    for current, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
    ):
        repository.advance_pipeline(
            video_id,
            expected_status=current,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            now=now,
        )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{video_id}:{ProcessingStage.SCORING.value}",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.SCORING,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=now,
        now=now,
    )
    repository.claim_next_job(
        owner="test-owner",
        lease_until=now + timedelta(minutes=5),
        now=now,
        video_id=video_id,
    )


def _assert_no_scoring_success(
    repository: SQLiteStateRepository, video_id: str, job_id: str
) -> None:
    assert repository.latest_artifact(video_id, ArtifactKind.SCORING_RAW) is None
    assert repository.latest_artifact(video_id, ArtifactKind.SCORING_STRUCTURED) is None
    connection = repository._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE video_id = ?", (video_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM provider_calls WHERE status = 'SUCCEEDED'"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()
    video = repository.get_video(video_id)
    assert video is not None
    assert video.pipeline_status is PipelineStatus.TRANSCRIPT_READY
    assert video.score is None
    assert video.should_summarize is None
    job = repository.get_job(job_id)
    assert job is not None
    assert job.status is JobStatus.RUNNING


def test_legacy_scoring_complete_stage_fails_closed_without_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    job_id = "scoring-job-legacy-attack"
    _setup_scoring_video_and_job(ops._repository, VIDEO_ID, job_id, NOW)

    with pytest.raises(IntegrityConflict, match="runtime trusted persistence entry"):
        ops._repository.complete_stage(
            job_id=job_id,
            owner="test-owner",
            video_id=VIDEO_ID,
            expected_status=PipelineStatus.TRANSCRIPT_READY,
            target_status=PipelineStatus.SCORED,
            pipeline_version=PIPELINE_VERSION,
            artifacts=(),
            provider_call=None,
            now=NOW,
            scoring_summary=ScoringSummaryWrite(score=8.0, should_summarize=True),
        )

    _assert_no_scoring_success(ops._repository, VIDEO_ID, job_id)
    assert not tuple((ops._data_root / "scoring").rglob("*.json"))


def test_trusted_scoring_failure_has_no_registered_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    job_id = "scoring-job-atomic-failure"
    _setup_scoring_video_and_job(ops._repository, VIDEO_ID, job_id, NOW)
    _, success = _trusted_scoring_success(ops, VIDEO_ID)
    entry = ops._trusted_persistence_entry(
        job_id=job_id,
        owner="test-owner",
        pipeline_version=PIPELINE_VERSION,
    )
    entry._clock = lambda: NOW  # type: ignore[method-assign]

    def fail_after_pipeline(point: str) -> None:
        if point == "atomic_register.after_pipeline":
            raise RuntimeError("injected trusted registration failure")

    ops._repository._inject_failure = fail_after_pipeline  # type: ignore[method-assign]
    try:
        with pytest.raises(
            ScoringPersistenceError, match="injected trusted registration failure"
        ):
            entry.persist_success(success)
    finally:
        ops._repository._inject_failure = None  # type: ignore[method-assign]

    _assert_no_scoring_success(ops._repository, VIDEO_ID, job_id)


def test_trusted_scoring_repeat_has_no_duplicate_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    job_id = "scoring-job-idempotent"
    _setup_scoring_video_and_job(ops._repository, VIDEO_ID, job_id, NOW)
    scoring_input, success = _trusted_scoring_success(ops, VIDEO_ID)
    entry = ops._trusted_persistence_entry(
        job_id=job_id,
        owner="test-owner",
        pipeline_version=PIPELINE_VERSION,
    )
    entry._clock = lambda: NOW  # type: ignore[method-assign]

    first = entry.persist_success(success)
    second = entry.persist_success(success)

    assert second == first
    assert len(first.artifacts) == 2
    assert {artifact.kind for artifact in first.artifacts} == {
        ArtifactKind.SCORING_RAW,
        ArtifactKind.SCORING_STRUCTURED,
    }
    assert first.provider_call.status is ProviderCallStatus.SUCCEEDED
    assert first.video.pipeline_status is PipelineStatus.SCORED
    assert first.job.status is JobStatus.SUCCEEDED
    connection = ops._repository._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE video_id = ?", (VIDEO_ID,)
            ).fetchone()[0]
            == 2
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM provider_calls").fetchone()[0]
            == 2
        )
    finally:
        connection.close()
    assert len(tuple((ops._data_root / "scoring").rglob("*.json"))) == 2
    assert (
        ops._repository.get_provider_call(scoring_input.request_hash).status
        is ProviderCallStatus.SUCCEEDED
    )


def _build_analysis_fixture(
    repository: SQLiteStateRepository,
    data_root: Path,
    video_id: str,
    job_id: str,
    request_hash: str,
    now: datetime,
) -> tuple[ArtifactWrite, ArtifactWrite, AnalysisResult]:
    result = AnalysisResult(
        one_sentence_summary="Fixture analysis summary.",
        core_points=[
            {
                "text": "A core point.",
                "kind": PointKind.FACT.value,
                "evidence_ids": ["title-1"],
            }
        ],
        keywords=["fixture"],
        evidence=[
            {
                "evidence_id": "title-1",
                "source": EvidenceSource.TITLE.value,
                "excerpt": "Fixture title",
            }
        ],
        provider="openai",
        model="gpt-4.1-mini",
        request_hash=request_hash,
    )
    raw_content = _canonical_json({"raw": "fixture analysis response"}).encode("utf-8")
    raw_hash = hashlib.sha256(raw_content).hexdigest()
    structured_content = _canonical_json(result.model_dump(mode="json")).encode("utf-8")
    structured_hash = hashlib.sha256(structured_content).hexdigest()

    raw_relative = f"analysis/{request_hash}/raw.json"
    structured_relative = f"analysis/{request_hash}/structured.json"
    (data_root / f"analysis/{request_hash}").mkdir(parents=True, exist_ok=True)
    (data_root / raw_relative).write_bytes(raw_content)
    (data_root / structured_relative).write_bytes(structured_content)

    raw = ArtifactWrite(
        artifact_id=f"analysis-raw-{hashlib.sha256((f'analysis/{request_hash}/raw' + raw_hash).encode()).hexdigest()}",
        artifact_key=f"analysis/{request_hash}/raw",
        video_id=video_id,
        job_id=job_id,
        kind=ArtifactKind.ANALYSIS_RAW,
        storage_root=StorageRoot.DATA,
        relative_path=raw_relative,
        content_hash=raw_hash,
        provider="openai",
        model="gpt-4.1-mini",
        producer_version="analysis-raw-v1",
        retention_class=RetentionClass.RAW_RESPONSE_30D,
        expires_at=now + timedelta(days=30),
    )
    structured = ArtifactWrite(
        artifact_id=f"analysis-structured-{hashlib.sha256((f'analysis/{request_hash}/structured' + structured_hash).encode()).hexdigest()}",
        artifact_key=f"analysis/{request_hash}/structured",
        video_id=video_id,
        job_id=job_id,
        kind=ArtifactKind.ANALYSIS_STRUCTURED,
        storage_root=StorageRoot.DATA,
        relative_path=structured_relative,
        content_hash=structured_hash,
        provider="openai",
        model="gpt-4.1-mini",
        producer_version="analysis-structured-v1",
        retention_class=RetentionClass.LONG_LIVED,
        expires_at=None,
    )
    return raw, structured, result


def _persist_analysis_provenance(
    repository: SQLiteStateRepository,
    data_root: Path,
    video_id: str,
    job_id: str,
    request_hash: str,
    now: datetime,
) -> tuple[ArtifactWrite, ArtifactWrite, AnalysisResult]:
    request = ProviderCallRequest(
        operation="cloud-analysis",
        normalized_input_hash=request_hash,
        provider="openai",
        model="gpt-4.1-mini",
        prompt_version="analysis-prompt-v1",
        schema_version="analysis-result-v1",
        deterministic_artifact_key=f"analysis/{request_hash}/raw",
    )
    raw, structured, result = _build_analysis_fixture(
        repository, data_root, video_id, job_id, request.request_hash, now
    )
    repository.upsert_artifact(raw, now=now)
    repository.upsert_artifact(structured, now=now)

    repository.reserve_provider_call(
        request,
        owner="test-owner",
        lease_until=now + timedelta(minutes=5),
        available_at=now,
        now=now,
    )
    repository.complete_provider_call(
        request_hash=request.request_hash,
        owner="test-owner",
        response_artifact_id=raw.artifact_id,
        input_tokens=None,
        output_tokens=None,
        cost_microusd=None,
        now=now,
    )
    return raw, structured, result


def _setup_analysis_video_and_job(
    repository: SQLiteStateRepository,
    video_id: str,
    job_id: str,
    now: datetime,
) -> None:
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id=video_id,
            channel_id=CHANNEL_ID,
            channel_name="Test channel",
            title=f"Video {video_id}",
            description="Fixture",
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=now,
            duration_seconds=120,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version=PIPELINE_VERSION,
        now=now,
    )
    for current, target in (
        (PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY),
        (PipelineStatus.METADATA_READY, PipelineStatus.TRANSCRIPT_READY),
        (PipelineStatus.TRANSCRIPT_READY, PipelineStatus.SCORED),
    ):
        repository.advance_pipeline(
            video_id,
            expected_status=current,
            target_status=target,
            pipeline_version=PIPELINE_VERSION,
            now=now,
        )
    repository.create_job(
        job_id=job_id,
        scope_key=f"video:{video_id}:{ProcessingStage.ANALYSIS.value}",
        video_id=video_id,
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.ANALYSIS,
        pipeline_version=PIPELINE_VERSION,
        max_attempts=3,
        available_at=now,
        now=now,
    )
    repository.claim_next_job(
        owner="test-owner",
        lease_until=now + timedelta(minutes=5),
        now=now,
        video_id=video_id,
    )


def _complete_analysis_job(
    repository: SQLiteStateRepository,
    video_id: str,
    job_id: str,
    artifacts: tuple[ArtifactWrite, ArtifactWrite],
    now: datetime,
) -> None:
    repository.complete_stage(
        job_id=job_id,
        owner="test-owner",
        video_id=video_id,
        expected_status=PipelineStatus.SCORED,
        target_status=PipelineStatus.ANALYSIS_READY,
        pipeline_version=PIPELINE_VERSION,
        artifacts=artifacts,
        provider_call=None,
        now=now,
    )


def test_valid_scoring_artifact_is_reused_without_calling_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    job_id = "scoring-job-1"

    _setup_scoring_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, request_hash = _persist_trusted_scoring_success(
        ops, VIDEO_ID, job_id, NOW
    )

    scoring_provider = _ScoringProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(scoring=scoring_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    outcome = ops2._load_scoring(VIDEO_ID)
    assert outcome.result.score == 8.6
    assert outcome.result.request_hash == request_hash
    assert scoring_provider.calls == 0
    provider_call = repository.get_provider_call(outcome.result.request_hash)
    assert provider_call is not None
    assert provider_call.status is ProviderCallStatus.SUCCEEDED


def test_valid_analysis_artifact_is_reused_without_calling_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    request_hash = "a" * 64
    job_id = "analysis-job-1"

    _setup_analysis_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, result = _persist_analysis_provenance(
        repository, ops._data_root, VIDEO_ID, job_id, request_hash, NOW
    )
    _complete_analysis_job(repository, VIDEO_ID, job_id, (raw, structured), NOW)

    analysis_provider = _AnalysisProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(analysis=analysis_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    outcome = ops2._load_analysis(VIDEO_ID)
    assert isinstance(outcome, AnalysisCompleted)
    assert outcome.result.request_hash == result.request_hash
    assert analysis_provider.calls == 0
    provider_call = repository.get_provider_call(outcome.result.request_hash)
    assert provider_call is not None
    assert provider_call.status is ProviderCallStatus.SUCCEEDED


def _mutate_scoring(
    mutation: str,
    repository: SQLiteStateRepository,
    data_root: Path,
    raw: ArtifactWrite,
    structured: ArtifactWrite,
    request_hash: str,
    video_id: str,
    job_id: str,
    now: datetime,
) -> None:
    conn = repository._connect()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        match mutation:
            case "job_id_none":
                conn.execute(
                    "UPDATE artifacts SET job_id = NULL WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_missing":
                conn.execute(
                    "UPDATE artifacts SET job_id = 'missing-job-id' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_wrong_video":
                wrong_video_id = SECOND_VIDEO_ID
                repository.upsert_video_metadata(
                    VideoMetadata(
                        video_id=wrong_video_id,
                        channel_id=CHANNEL_ID,
                        channel_name="Other channel",
                        title="Other video",
                        description="Fixture",
                        source_url=f"https://www.youtube.com/watch?v={wrong_video_id}",
                        published_at=now,
                        duration_seconds=120,
                        default_language="en",
                        available_languages=("en",),
                        live_status=LiveStatus.NONE,
                        availability=Availability.PUBLIC,
                    ),
                    pipeline_version=PIPELINE_VERSION,
                    now=now,
                )
                repository.create_job(
                    job_id="wrong-video-job",
                    scope_key=f"video:{wrong_video_id}:{ProcessingStage.SCORING.value}",
                    video_id=wrong_video_id,
                    job_type=JobType.VIDEO_STAGE,
                    target_stage=ProcessingStage.SCORING,
                    pipeline_version=PIPELINE_VERSION,
                    max_attempts=3,
                    available_at=now,
                    now=now,
                )
                conn.execute(
                    "UPDATE artifacts SET job_id = 'wrong-video-job' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_wrong_stage":
                repository.create_job(
                    job_id="wrong-stage-job",
                    scope_key=f"video:{video_id}:{ProcessingStage.METADATA.value}",
                    video_id=video_id,
                    job_type=JobType.VIDEO_STAGE,
                    target_stage=ProcessingStage.METADATA,
                    pipeline_version=PIPELINE_VERSION,
                    max_attempts=3,
                    available_at=now,
                    now=now,
                )
                conn.execute(
                    "UPDATE artifacts SET job_id = 'wrong-stage-job' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_not_succeeded":
                conn.execute(
                    "UPDATE jobs SET status = 'PENDING', lease_owner = NULL, "
                    "lease_until = NULL, finished_at = NULL WHERE job_id = ?",
                    (job_id,),
                )
            case "provider_call_missing":
                conn.execute(
                    "DELETE FROM provider_calls WHERE request_hash = ?",
                    (request_hash,),
                )
            case "provider_call_failed":
                conn.execute(
                    "UPDATE provider_calls SET status = 'FAILED_FINAL', "
                    "reservation_owner = NULL, lease_until = NULL WHERE request_hash = ?",
                    (request_hash,),
                )
            case "provider_mismatch":
                conn.execute(
                    "UPDATE provider_calls SET provider = 'wrong-provider' WHERE request_hash = ?",
                    (request_hash,),
                )
            case "model_mismatch":
                conn.execute(
                    "UPDATE provider_calls SET model = 'wrong-model' WHERE request_hash = ?",
                    (request_hash,),
                )
            case "request_hash_mismatch":
                conn.execute(
                    "UPDATE provider_calls SET request_hash = ? WHERE request_hash = ?",
                    ("b" * 64, request_hash),
                )
            case "artifact_key_mismatch":
                conn.execute(
                    "UPDATE artifacts SET artifact_key = 'wrong/key' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "producer_version_mismatch":
                conn.execute(
                    "UPDATE artifacts SET producer_version = 'wrong-version' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "structured_provider_mismatch":
                conn.execute(
                    "UPDATE artifacts SET provider = 'wrong-provider' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "structured_model_mismatch":
                conn.execute(
                    "UPDATE artifacts SET model = 'wrong-model' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "file_hash_mismatch":
                path = data_root / structured.relative_path
                path.write_bytes(b'{"corrupted": true}')
            case "schema_version_mismatch":
                path = data_root / structured.relative_path
                data = json.loads(path.read_text(encoding="utf-8"))
                data["schema_version"] = "wrong-version"
                new_content = _canonical_json(data).encode("utf-8")
                path.write_bytes(new_content)
                conn.execute(
                    "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                    (hashlib.sha256(new_content).hexdigest(), structured.artifact_key),
                )
            case "output_language_mismatch":
                path = data_root / structured.relative_path
                data = json.loads(path.read_text(encoding="utf-8"))
                data["output_language"] = "en"
                data["reason"] = "This fixture verifies current-language provenance."
                new_content = _canonical_json(data).encode("utf-8")
                path.write_bytes(new_content)
                conn.execute(
                    "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                    (hashlib.sha256(new_content).hexdigest(), structured.artifact_key),
                )
            case "legacy_missing_output_language":
                path = data_root / structured.relative_path
                data = json.loads(path.read_text(encoding="utf-8"))
                del data["output_language"]
                new_content = _canonical_json(data).encode("utf-8")
                path.write_bytes(new_content)
                conn.execute(
                    "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                    (hashlib.sha256(new_content).hexdigest(), structured.artifact_key),
                )
            case _:
                raise ValueError(f"unknown scoring mutation: {mutation}")
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "job_id_none",
        "job_missing",
        "job_wrong_video",
        "job_wrong_stage",
        "job_not_succeeded",
        "provider_call_missing",
        "provider_call_failed",
        "provider_mismatch",
        "model_mismatch",
        "request_hash_mismatch",
        "artifact_key_mismatch",
        "producer_version_mismatch",
        "structured_provider_mismatch",
        "structured_model_mismatch",
        "file_hash_mismatch",
        "schema_version_mismatch",
        "output_language_mismatch",
        "legacy_missing_output_language",
    ],
)
def test_scoring_provenance_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    job_id = "scoring-job-fail"

    _setup_scoring_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, request_hash = _persist_trusted_scoring_success(
        ops, VIDEO_ID, job_id, NOW
    )

    _mutate_scoring(
        mutation, repository, ops._data_root, raw, structured, request_hash, VIDEO_ID, job_id, NOW
    )

    scoring_provider = _ScoringProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(scoring=scoring_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    with pytest.raises(ValueError):
        ops2._load_scoring(VIDEO_ID)
    assert scoring_provider.calls == 0


def _mutate_analysis(
    mutation: str,
    repository: SQLiteStateRepository,
    data_root: Path,
    raw: ArtifactWrite,
    structured: ArtifactWrite,
    request_hash: str,
    video_id: str,
    job_id: str,
    now: datetime,
) -> None:
    conn = repository._connect()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        match mutation:
            case "job_id_none":
                conn.execute(
                    "UPDATE artifacts SET job_id = NULL WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_missing":
                conn.execute(
                    "UPDATE artifacts SET job_id = 'missing-job-id' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_wrong_video":
                wrong_video_id = SECOND_VIDEO_ID
                repository.upsert_video_metadata(
                    VideoMetadata(
                        video_id=wrong_video_id,
                        channel_id=CHANNEL_ID,
                        channel_name="Other channel",
                        title="Other video",
                        description="Fixture",
                        source_url=f"https://www.youtube.com/watch?v={wrong_video_id}",
                        published_at=now,
                        duration_seconds=120,
                        default_language="en",
                        available_languages=("en",),
                        live_status=LiveStatus.NONE,
                        availability=Availability.PUBLIC,
                    ),
                    pipeline_version=PIPELINE_VERSION,
                    now=now,
                )
                repository.create_job(
                    job_id="wrong-video-job",
                    scope_key=f"video:{wrong_video_id}:{ProcessingStage.ANALYSIS.value}",
                    video_id=wrong_video_id,
                    job_type=JobType.VIDEO_STAGE,
                    target_stage=ProcessingStage.ANALYSIS,
                    pipeline_version=PIPELINE_VERSION,
                    max_attempts=3,
                    available_at=now,
                    now=now,
                )
                conn.execute(
                    "UPDATE artifacts SET job_id = 'wrong-video-job' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_wrong_stage":
                repository.create_job(
                    job_id="wrong-stage-job",
                    scope_key=f"video:{video_id}:{ProcessingStage.METADATA.value}",
                    video_id=video_id,
                    job_type=JobType.VIDEO_STAGE,
                    target_stage=ProcessingStage.METADATA,
                    pipeline_version=PIPELINE_VERSION,
                    max_attempts=3,
                    available_at=now,
                    now=now,
                )
                conn.execute(
                    "UPDATE artifacts SET job_id = 'wrong-stage-job' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "job_not_succeeded":
                conn.execute(
                    "UPDATE jobs SET status = 'PENDING', lease_owner = NULL, "
                    "lease_until = NULL, finished_at = NULL WHERE job_id = ?",
                    (job_id,),
                )
            case "provider_call_missing":
                conn.execute(
                    "DELETE FROM provider_calls WHERE request_hash = ?",
                    (request_hash,),
                )
            case "provider_call_failed":
                conn.execute(
                    "UPDATE provider_calls SET status = 'FAILED_FINAL', "
                    "reservation_owner = NULL, lease_until = NULL WHERE request_hash = ?",
                    (request_hash,),
                )
            case "provider_mismatch":
                conn.execute(
                    "UPDATE provider_calls SET provider = 'wrong-provider' WHERE request_hash = ?",
                    (request_hash,),
                )
            case "model_mismatch":
                conn.execute(
                    "UPDATE provider_calls SET model = 'wrong-model' WHERE request_hash = ?",
                    (request_hash,),
                )
            case "request_hash_mismatch":
                conn.execute(
                    "UPDATE provider_calls SET request_hash = ? WHERE request_hash = ?",
                    ("b" * 64, request_hash),
                )
            case "artifact_key_mismatch":
                conn.execute(
                    "UPDATE artifacts SET artifact_key = 'wrong/key' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "producer_version_mismatch":
                conn.execute(
                    "UPDATE artifacts SET producer_version = 'wrong-version' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "structured_provider_mismatch":
                conn.execute(
                    "UPDATE artifacts SET provider = 'wrong-provider' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "structured_model_mismatch":
                conn.execute(
                    "UPDATE artifacts SET model = 'wrong-model' WHERE artifact_key = ?",
                    (structured.artifact_key,),
                )
            case "file_hash_mismatch":
                path = data_root / structured.relative_path
                path.write_bytes(b'{"corrupted": true}')
            case "schema_version_mismatch":
                path = data_root / structured.relative_path
                data = json.loads(path.read_text(encoding="utf-8"))
                data["schema_version"] = "wrong-version"
                new_content = _canonical_json(data).encode("utf-8")
                path.write_bytes(new_content)
                conn.execute(
                    "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
                    (hashlib.sha256(new_content).hexdigest(), structured.artifact_key),
                )
            case _:
                raise ValueError(f"unknown analysis mutation: {mutation}")
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "job_id_none",
        "job_missing",
        "job_wrong_video",
        "job_wrong_stage",
        "job_not_succeeded",
        "provider_call_missing",
        "provider_call_failed",
        "provider_mismatch",
        "model_mismatch",
        "request_hash_mismatch",
        "artifact_key_mismatch",
        "producer_version_mismatch",
        "structured_provider_mismatch",
        "structured_model_mismatch",
        "file_hash_mismatch",
        "schema_version_mismatch",
    ],
)
def test_analysis_provenance_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    project = _project(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    request_hash = "a" * 64
    job_id = "analysis-job-fail"

    _setup_analysis_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, result = _persist_analysis_provenance(
        repository, ops._data_root, VIDEO_ID, job_id, request_hash, NOW
    )
    _complete_analysis_job(repository, VIDEO_ID, job_id, (raw, structured), NOW)

    _mutate_analysis(
        mutation, repository, ops._data_root, raw, structured, result.request_hash, VIDEO_ID, job_id, NOW
    )

    analysis_provider = _AnalysisProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(analysis=analysis_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    with pytest.raises(ValueError):
        ops2._load_analysis(VIDEO_ID)
    assert analysis_provider.calls == 0


def _project_with_models(
    tmp_path: Path,
    *,
    local_scoring_model: str = "qwen3:8b",
    cloud_model: str = "gpt-4.1-mini",
) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "vault").mkdir()
    (tmp_path / "config" / "channels.yaml").write_text(
        f"channels:\n  - channel_id: {CHANNEL_ID}\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "settings.yaml").write_text(
        f"""\
general:
  transcript_languages: [en]
local_scoring:
  model: {local_scoring_model}
  expected_model_digest: sha256:{'1' * 64}
cloud:
  enabled: true
  model: {cloud_model}
  api_key_env: OPENAI_API_KEY
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {tmp_path / 'vault'}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )
    return tmp_path


def test_scoring_current_config_model_mismatch_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project_with_models(tmp_path, local_scoring_model="qwen3:8b")
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    job_id = "scoring-job-config"

    _setup_scoring_video_and_job(repository, VIDEO_ID, job_id, NOW)
    _persist_trusted_scoring_success(
        ops, VIDEO_ID, job_id, NOW
    )
    settings_path = project / "config" / "settings.yaml"
    settings_path.write_text(
        settings_path.read_text(encoding="utf-8").replace(
            "  model: qwen3:8b\n", "  model: qwen3:8b-current\n"
        ),
        encoding="utf-8",
    )

    scoring_provider = _ScoringProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(scoring=scoring_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    with pytest.raises(ValueError):
        ops2._load_scoring(VIDEO_ID)
    assert scoring_provider.calls == 0


def test_scoring_valid_recovery_matches_current_config_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project_with_models(tmp_path, local_scoring_model="qwen3:8b")
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    job_id = "scoring-job-config-valid"

    _setup_scoring_video_and_job(repository, VIDEO_ID, job_id, NOW)
    _persist_trusted_scoring_success(
        ops, VIDEO_ID, job_id, NOW
    )

    scoring_provider = _ScoringProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(scoring=scoring_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    outcome = ops2._load_scoring(VIDEO_ID)
    assert outcome.result.score == 8.6
    assert outcome.result.model == "qwen3:8b"
    assert scoring_provider.calls == 0


def test_analysis_current_config_model_mismatch_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project_with_models(tmp_path, cloud_model="gpt-4.1")
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    request_hash = "a" * 64
    job_id = "analysis-job-config"

    _setup_analysis_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, result = _persist_analysis_provenance(
        repository, ops._data_root, VIDEO_ID, job_id, request_hash, NOW
    )
    _complete_analysis_job(repository, VIDEO_ID, job_id, (raw, structured), NOW)

    analysis_provider = _AnalysisProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(analysis=analysis_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    with pytest.raises(ValueError):
        ops2._load_analysis(VIDEO_ID)
    assert analysis_provider.calls == 0


def test_analysis_current_config_provider_mismatch_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project_with_models(tmp_path)
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    request_hash = "a" * 64
    job_id = "analysis-job-config-provider"

    _setup_analysis_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, result = _persist_analysis_provenance(
        repository, ops._data_root, VIDEO_ID, job_id, request_hash, NOW
    )
    _complete_analysis_job(repository, VIDEO_ID, job_id, (raw, structured), NOW)

    # Keep JSON consistent with DB mutations so the failure is against the
    # current cloud.provider="openai" binding rather than internal consistency.
    conn = repository._connect()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "UPDATE artifacts SET provider = 'anthropic' WHERE artifact_key IN (?, ?)",
            (structured.artifact_key, raw.artifact_key),
        )
        conn.execute(
            "UPDATE provider_calls SET provider = 'anthropic' WHERE request_hash = ?",
            (request_hash,),
        )
        data = json.loads(
            (ops._data_root / structured.relative_path).read_text(encoding="utf-8")
        )
        data["provider"] = "anthropic"
        new_content = _canonical_json(data).encode("utf-8")
        (ops._data_root / structured.relative_path).write_bytes(new_content)
        conn.execute(
            "UPDATE artifacts SET content_hash = ? WHERE artifact_key = ?",
            (hashlib.sha256(new_content).hexdigest(), structured.artifact_key),
        )
        conn.commit()
    finally:
        conn.close()

    analysis_provider = _AnalysisProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(analysis=analysis_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    with pytest.raises(ValueError):
        ops2._load_analysis(VIDEO_ID)
    assert analysis_provider.calls == 0


def test_analysis_valid_recovery_matches_current_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project_with_models(tmp_path, cloud_model="gpt-4.1-mini")
    ops = _runtime_ops(project, monkeypatch)
    repository = ops._repository
    request_hash = "a" * 64
    job_id = "analysis-job-config-valid"

    _setup_analysis_video_and_job(repository, VIDEO_ID, job_id, NOW)
    raw, structured, result = _persist_analysis_provenance(
        repository, ops._data_root, VIDEO_ID, job_id, request_hash, NOW
    )
    _complete_analysis_job(repository, VIDEO_ID, job_id, (raw, structured), NOW)

    analysis_provider = _AnalysisProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: _dependencies(analysis=analysis_provider),
    )
    ops2 = RuntimeOperations(config=_config(project), project_root=project)

    outcome = ops2._load_analysis(VIDEO_ID)
    assert isinstance(outcome, AnalysisCompleted)
    assert outcome.result.model == "gpt-4.1-mini"
    assert outcome.result.provider == "openai"
    assert analysis_provider.calls == 0
