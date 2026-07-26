"""Offline MVP acceptance through the production service boundaries."""

from __future__ import annotations

import gc
import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from youtube_intel.analysis import (
    AnalysisJobContext,
    CloudCallBudget,
    RepositoryBackedAnalysisService,
)
from youtube_intel.config import CloudSettings, LocalScoringSettings
from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisPoint,
    AnalysisResult,
    Availability,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    PointKind,
    ProcessingStage,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
    SubtitleFormat,
    TranscriptArtifact,
    TranscriptionRequired,
    TranscriptReady,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.jobs import PipelineJobPlanner
from youtube_intel.pipeline import PipelineOrchestrator
from youtube_intel.providers.obsidian import NoteWriteContext, ObsidianNoteSink
from youtube_intel.providers.whisper import (
    MlxWhisperAdapter,
    WhisperDecodePolicy,
    WhisperResponse,
)
from youtube_intel.reporting import WeeklyReportService
from youtube_intel.retry import RetryPolicy
from youtube_intel.scoring import RepositoryBackedScoringService, ScoringJobContext
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    PipelineStatus,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
)
from youtube_intel.transcription import AudioResourceSnapshot
from youtube_intel.transcripts import (
    LocalTranscriptionService,
    SubtitleAcquisitionService,
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
    TranscriptJobContext,
)

NOW = datetime(2100, 1, 1, 8, 0, tzinfo=UTC)
PIPELINE_VERSION = "acceptance-v1"
OWNER = "e2e-worker"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "subtitles"


@dataclass(frozen=True)
class _Scenario:
    video_id: str
    subtitle_source: TranscriptSourceType | None
    score: float


SCENARIOS = (
    _Scenario("manual-high", TranscriptSourceType.MANUAL_SUBTITLE, 8.8),
    _Scenario("auto-high", TranscriptSourceType.AUTO_SUBTITLE, 8.2),
    _Scenario("whisper-high", None, 9.1),
    _Scenario("low-value", TranscriptSourceType.MANUAL_SUBTITLE, 4.0),
    _Scenario("high-value", TranscriptSourceType.AUTO_SUBTITLE, 9.4),
)


class _SubtitleAdapter:
    provider_name = "offline-subtitles"
    provider_version = "fixture-v1"

    def __init__(self, scenario: _Scenario, *, fail_once: bool = False) -> None:
        self._scenario = scenario
        self._fail_once = fail_once
        self.enumerate_calls = 0
        self.read_calls = 0
        self._call = ProviderCallMetadata(
            provider=self.provider_name,
            provider_version=self.provider_version,
            started_at=NOW,
            finished_at=NOW,
        )

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        assert video_id == self._scenario.video_id
        self.enumerate_calls += 1
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("injected subtitle adapter outage")
        if self._scenario.subtitle_source is None:
            return SubtitleTrackListing(tracks=(), call=self._call)
        source_format = (
            SubtitleFormat.JSON3
            if self._scenario.subtitle_source is TranscriptSourceType.MANUAL_SUBTITLE
            else SubtitleFormat.VTT
        )
        return SubtitleTrackListing(
            tracks=(
                SubtitleTrack(
                    source_type=self._scenario.subtitle_source,
                    language="en",
                    source_format=source_format,
                    name="English",
                    url=f"https://example.invalid/subtitles/{video_id}",
                    provider_position=0,
                ),
            ),
            call=self._call,
        )

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        self.read_calls += 1
        filename = (
            "manual_en.json3"
            if track.source_type is TranscriptSourceType.MANUAL_SUBTITLE
            else "auto_zh.vtt"
        )
        return SubtitleReadResult(body=(FIXTURES / filename).read_bytes(), call=self._call)


class _WhisperExecutor:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.calls = 0

    def transcribe(self, audio_path: Path, policy: WhisperDecodePolicy) -> WhisperResponse:
        assert audio_path.name == "fixture.wav"
        assert policy.language_hint == "en"
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("injected Whisper executor outage")
        return WhisperResponse(
            text="A verified local transcription supports a useful product insight.",
            language="en",
        )


class _ScoringProvider:
    def __init__(self, scores: dict[str, float], *, fail_once: bool = False) -> None:
        self._scores = scores
        self.fail_once = fail_once
        self.calls = 0
        self._raw: str | None = None

    def score(self, scoring_input: object) -> ScoreResult:
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("injected local scoring outage")
        video_id = getattr(scoring_input, "video").video_id
        score = self._scores[video_id]
        self._raw = (
            '{"score":' + str(score) + ',"reason":"offline fixture",'
            '"topics":["product"],"should_summarize":true}'
        )
        return ScoreResult(
            schema_version="score-result-v1",
            score=score,
            reason="Offline fixture score for the service-flow acceptance test.",
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v1",
            request_hash=getattr(scoring_input, "request_hash"),
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert request_hash
        assert self._raw is not None
        raw = self._raw
        self._raw = None
        return raw


class _AnalysisProvider:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.calls = 0
        self._raw: str | None = None

    def summarize_with_credential(self, analysis_input: object, credential: str) -> AnalysisResult:
        assert credential == "offline-test-credential"
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("injected cloud analysis outage")
        payload = getattr(analysis_input, "payload")
        self._raw = '{"offline":"analysis"}'
        return AnalysisResult(
            one_sentence_summary="The offline fixture identifies one useful product direction.",
            core_points=(
                AnalysisPoint(
                    text="The title states the user-facing product topic.",
                    kind=PointKind.FACT,
                    evidence_ids=("title-1",),
                ),
            ),
            actionable_directions=(
                AnalysisPoint(
                    text="Validate the product direction with users.",
                    kind=PointKind.RECOMMENDATION,
                    evidence_ids=("title-1",),
                ),
            ),
            keywords=("product",),
            evidence=(
                EvidenceExcerpt(
                    evidence_id="title-1",
                    source=EvidenceSource.TITLE,
                    excerpt=payload.title,
                ),
            ),
            provider="openai",
            model="gpt-4.1-mini",
            request_hash=getattr(analysis_input, "request_hash"),
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert request_hash
        assert self._raw is not None
        raw = self._raw
        self._raw = None
        return raw


class _CredentialResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, env_name: str) -> str:
        assert env_name == "OPENAI_API_KEY"
        self.calls += 1
        return "offline-test-credential"


class _FailingOnceNoteSink(ObsidianNoteSink):
    def __init__(self, *, fail_once: bool, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._fail_once = fail_once

    def _write_or_verify(self, rendered: object, video_id: str):  # type: ignore[no-untyped-def,override]
        if self._fail_once:
            self._fail_once = False
            raise OSError("injected note write outage")
        return super()._write_or_verify(rendered, video_id)  # type: ignore[arg-type]


class _FailingReportRepository:
    def __init__(self, repository: SQLiteStateRepository, *, fail_once: bool) -> None:
        self._repository = repository
        self._fail_once = fail_once

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._repository, name)

    def upsert_report(self, report: object, *, now: datetime) -> object:
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("injected weekly report database outage")
        return self._repository.upsert_report(report, now=now)  # type: ignore[arg-type]


class _OfflineMvpFlow:
    def __init__(
        self,
        tmp_path: Path,
        *,
        failure: str | None = None,
        cloud_enabled: bool = True,
        restore: bool = False,
    ) -> None:
        self.root = tmp_path
        self._job_prefix = "recovered" if restore else "initial"
        self.data_root = tmp_path / "data"
        self.vault_root = tmp_path / "vault"
        (self.vault_root / "Knowledge").mkdir(parents=True, exist_ok=True)
        self.repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
        self.repository.initialize(now=NOW)
        self.scenarios = {scenario.video_id: scenario for scenario in SCENARIOS}
        self.videos = {scenario.video_id: self._video(scenario) for scenario in SCENARIOS}
        self.transcripts: dict[str, TranscriptReady] = {}
        self.scores: dict[str, object] = {}
        self.analyses: dict[str, object] = {}
        self.note_sinks: dict[str, ObsidianNoteSink] = {}
        self.subtitle_adapters = {
            scenario.video_id: _SubtitleAdapter(
                scenario,
                fail_once=failure == "subtitle" and scenario.video_id == "manual-high",
            )
            for scenario in SCENARIOS
        }
        self.whisper = _WhisperExecutor(fail_once=failure == "transcription")
        self.scoring = _ScoringProvider(
            {scenario.video_id: scenario.score for scenario in SCENARIOS},
            fail_once=failure == "scoring",
        )
        self.analysis = _AnalysisProvider(fail_once=failure == "analysis")
        self.credentials = _CredentialResolver()
        self._note_failure = failure == "note"
        self._cloud_enabled = cloud_enabled
        if not restore:
            self._setup_initial_fixture()
        self.orchestrator = PipelineOrchestrator(
            repository=self.repository,
            planner=PipelineJobPlanner(
                repository=self.repository,
                pipeline_version=PIPELINE_VERSION,
                max_attempts=3,
                job_id_factory=self._job_id,
            ),
            owner=OWNER,
            lease_seconds=300,
            retry_policy=RetryPolicy(base_delay_seconds=1, max_delay_seconds=1, jitter_ratio=0),
            handlers={
                ProcessingStage.TRANSCRIPT: self._transcript_stage,
                ProcessingStage.SCORING: self._scoring_stage,
                ProcessingStage.ANALYSIS: self._analysis_stage,
                ProcessingStage.NOTE_WRITE: self._note_stage,
            },
            clock=lambda: NOW,
        )

    def _job_id(self) -> str:
        count = getattr(self, "_job_count", 0) + 1
        self._job_count = count
        return f"e2e-job-{self._job_prefix}-{count}"

    @staticmethod
    def _video(scenario: _Scenario) -> VideoMetadata:
        return VideoMetadata(
            video_id=scenario.video_id,
            channel_id="UC_OFFLINE",
            channel_name="Offline acceptance channel",
            title=f"Offline {scenario.video_id} product lesson",
            description="A public fixture description.",
            source_url=f"https://example.invalid/watch?v={scenario.video_id}",
            published_at=NOW,
            duration_seconds=120,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        )

    def _setup_initial_fixture(self) -> None:
        for scenario in SCENARIOS:
            video = self.videos[scenario.video_id]
            self.repository.upsert_video_metadata(video, pipeline_version=PIPELINE_VERSION, now=NOW)
            assert self.repository.advance_pipeline(
                video.video_id,
                expected_status=PipelineStatus.DISCOVERED,
                target_status=PipelineStatus.METADATA_READY,
                pipeline_version=PIPELINE_VERSION,
                now=NOW,
            )
            if scenario.subtitle_source is None:
                self._register_audio(video.video_id)

    def _register_audio(self, video_id: str) -> None:
        content = f"offline audio for {video_id}".encode()
        path = self.data_root / "audio" / video_id / "fixture.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.repository.upsert_artifact(
            ArtifactWrite(
                artifact_id=f"audio-{video_id}",
                artifact_key=f"audio/{video_id}",
                video_id=video_id,
                job_id=None,
                kind=ArtifactKind.AUDIO,
                storage_root=StorageRoot.DATA,
                relative_path=f"audio/{video_id}/fixture.wav",
                content_hash=hashlib.sha256(content).hexdigest(),
                provider="offline-audio",
                model=None,
                producer_version="offline-fixture-v1",
                retention_class=RetentionClass.EPHEMERAL_AUDIO,
                expires_at=NOW + timedelta(days=7),
            ),
            now=NOW,
        )

    def run(self, *, now: datetime = NOW) -> None:
        self.orchestrator.run_batch(tuple(self.scenarios), now=now)

    def _transcript_stage(self, job: object, video: object) -> None:
        video_id = getattr(video, "video_id")
        service = SubtitleAcquisitionService(
            adapter=self.subtitle_adapters[video_id],
            repository=self.repository,
            data_root=self.data_root,
            context=TranscriptJobContext(
                job_id=getattr(job, "job_id"), owner=OWNER, pipeline_version=PIPELINE_VERSION
            ),
            clock=lambda: NOW,
        )
        result = service.fetch(self.videos[video_id], ("en",))
        if isinstance(result, TranscriptReady):
            self.transcripts[video_id] = result
            return
        assert isinstance(result, TranscriptionRequired)
        audio = self.repository.get_artifact_by_key(f"audio/{video_id}")
        assert audio is not None
        policy = WhisperDecodePolicy(language_hint="en")
        self.transcripts[video_id] = LocalTranscriptionService(
            adapter=MlxWhisperAdapter(executor=self.whisper, decode_policy=policy, clock=lambda: NOW),
            repository=self.repository,
            context=TranscriptJobContext(
                job_id=getattr(job, "job_id"), owner=OWNER, pipeline_version=PIPELINE_VERSION
            ),
            data_root=self.data_root,
            resources=AudioResourceSnapshot(free_disk_gib=100, available_memory_gib=100),
            decode_policy=policy,
            clock=lambda: NOW,
        ).transcribe(audio)

    def _persisted_artifact(
        self, video_id: str, kind: ArtifactKind
    ) -> tuple[bytes, str, str, str | None, str | None]:
        with sqlite3.connect(self.root / "state.sqlite3") as connection:
            row = connection.execute(
                """
                SELECT relative_path, content_hash, storage_root, provider, model
                FROM artifacts
                WHERE video_id = ? AND kind = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (video_id, kind.value),
            ).fetchone()
        assert row is not None
        relative_path, content_hash, storage_root, provider, model = row
        assert storage_root == StorageRoot.DATA.value
        path = (self.data_root / relative_path).resolve()
        assert path.is_relative_to(self.data_root.resolve())
        body = path.read_bytes()
        assert hashlib.sha256(body).hexdigest() == content_hash
        return body, relative_path, content_hash, provider, model

    def _transcript_for(self, video_id: str) -> TranscriptReady:
        cached = self.transcripts.get(video_id)
        if cached is not None:
            return cached
        body, relative_path, content_hash, provider, model = self._persisted_artifact(
            video_id, ArtifactKind.TRANSCRIPT_CANONICAL
        )
        text = body.decode("utf-8")
        scenario = self.scenarios[video_id]
        source_type = scenario.subtitle_source or TranscriptSourceType.WHISPER
        source_format = (
            SubtitleFormat.JSON3
            if source_type is TranscriptSourceType.MANUAL_SUBTITLE
            else SubtitleFormat.VTT
            if source_type is TranscriptSourceType.AUTO_SUBTITLE
            else None
        )
        return TranscriptReady(
            artifact=TranscriptArtifact(
                video_id=video_id,
                language="en",
                source_type=source_type,
                requested_language="en" if source_format is not None else None,
                source_format=source_format,
                text_path=relative_path,
                timed_text_path=None if source_format is None else relative_path,
                source_content_hash=content_hash,
                source_byte_count=len(body),
                content_hash=content_hash,
                char_count=len(text),
                segment_count=len(text.splitlines()),
                normalization_version="offline-persisted-recovery-v1",
                provider=provider or "offline-persisted-recovery",
                model=model,
                created_at=NOW,
            ),
            call=ProviderCallMetadata(
                provider=provider or "offline-persisted-recovery",
                model=model,
                started_at=NOW,
                finished_at=NOW,
            ),
        )

    def _score_for(self, video_id: str) -> ScoringOutcome:
        cached = self.scores.get(video_id)
        if isinstance(cached, ScoringOutcome):
            return cached
        body, _, _, _, _ = self._persisted_artifact(video_id, ArtifactKind.SCORING_STRUCTURED)
        result = ScoreResult.model_validate_json(body)
        final_should_summarize = result.score >= 7.0
        return ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=7.0,
                final_should_summarize=final_should_summarize,
                model_disagrees=result.should_summarize is not final_should_summarize,
            ),
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=NOW,
                finished_at=NOW,
            ),
        )

    def _analysis_for(self, video_id: str) -> object:
        cached = self.analyses.get(video_id)
        if cached is not None:
            return cached
        body, _, _, _, _ = self._persisted_artifact(video_id, ArtifactKind.ANALYSIS_STRUCTURED)
        result = AnalysisResult.model_validate_json(body)
        return AnalysisCompleted(
            result=result,
            call=ProviderCallMetadata(
                provider=result.provider,
                model=result.model,
                started_at=NOW,
                finished_at=NOW,
            ),
        )

    def _scoring_stage(self, job: object, video: object) -> None:
        video_id = getattr(video, "video_id")
        transcript = self._transcript_for(video_id).artifact
        text = (self.data_root / transcript.text_path).read_text(encoding="utf-8")
        self.scores[video_id] = RepositoryBackedScoringService(
            provider=self.scoring,
            settings=LocalScoringSettings(
                model="qwen3:8b",
                expected_model_digest="sha256:" + "a" * 64,
                max_transcript_chars=30_000,
                max_description_chars=4_000,
            ),
            summary_threshold=7.0,
            repository=self.repository,
            context=ScoringJobContext(
                job_id=getattr(job, "job_id"), owner=OWNER, pipeline_version=PIPELINE_VERSION
            ),
            artifact_root=self.data_root,
            clock=lambda: NOW,
        ).score(video=self.videos[video_id], transcript_text=text, language=transcript.language)

    def _analysis_stage(self, job: object, video: object) -> object | None:
        video_id = getattr(video, "video_id")
        transcript = self._transcript_for(video_id).artifact
        text = (self.data_root / transcript.text_path).read_text(encoding="utf-8")
        outcome = RepositoryBackedAnalysisService(
            provider=self.analysis,
            settings=CloudSettings(
                enabled=self._cloud_enabled,
                model="gpt-4.1-mini" if self._cloud_enabled else None,
            ),
            repository=self.repository,
            context=AnalysisJobContext(
                job_id=getattr(job, "job_id"), owner=OWNER, pipeline_version=PIPELINE_VERSION
            ),
            artifact_root=self.data_root,
            credential_resolver=self.credentials,
            budget=CloudCallBudget(limit=5),
        ).analyze(video=self.videos[video_id], transcript_text=text, language=transcript.language)
        assert outcome is not None
        self.analyses[video_id] = outcome
        return outcome

    def _note_stage(self, job: object, video: object) -> None:
        video_id = getattr(video, "video_id")
        sink = _FailingOnceNoteSink(
            fail_once=self._note_failure,
            vault_root=self.vault_root,
            vault_subdir="Knowledge",
            repository=self.repository,
            context=NoteWriteContext(
                job_id=getattr(job, "job_id"), owner=OWNER, pipeline_version=PIPELINE_VERSION
            ),
        )
        self._note_failure = False
        sink.upsert_video_note(
            video=self.videos[video_id],
            transcript=self._transcript_for(video_id).artifact,
            scoring=self._score_for(video_id),
            analysis=self._analysis_for(video_id),
            processed_at=NOW,
            pipeline_version=PIPELINE_VERSION,
        )
        self.note_sinks[video_id] = sink

    def weekly_service(self, *, fail_once: bool = False) -> WeeklyReportService:
        repository = _FailingReportRepository(self.repository, fail_once=fail_once)
        return WeeklyReportService(
            repository=repository,
            sink=ObsidianNoteSink(
                vault_root=self.vault_root,
                vault_subdir="Knowledge",
                repository=repository,
                context=NoteWriteContext(job_id="weekly", owner=OWNER, pipeline_version=PIPELINE_VERSION),
            ),
            artifact_root=self.data_root,
            timezone="Asia/Shanghai",
            top_n=10,
        )

    def counts(self) -> tuple[int, int, int, int]:
        with sqlite3.connect(self.root / "state.sqlite3") as connection:
            return tuple(
                int(connection.execute(query).fetchone()[0])
                for query in (
                    "SELECT count(*) FROM provider_calls",
                    "SELECT count(*) FROM artifacts",
                    "SELECT count(*) FROM reports",
                    "SELECT count(*) FROM jobs",
                )
            )  # type: ignore[return-value]


def test_mvp_service_flow_covers_five_user_scenarios_and_is_idempotent(tmp_path: Path) -> None:
    flow = _OfflineMvpFlow(tmp_path)

    flow.run()

    assert all(
        flow.repository.get_video(scenario.video_id).pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
        for scenario in SCENARIOS
    )
    assert flow.transcripts["manual-high"].artifact.source_type is TranscriptSourceType.MANUAL_SUBTITLE
    assert flow.transcripts["auto-high"].artifact.source_type is TranscriptSourceType.AUTO_SUBTITLE
    assert flow.transcripts["whisper-high"].artifact.source_type is TranscriptSourceType.WHISPER
    assert flow.whisper.calls == 1
    assert flow.analysis.calls == 4
    assert flow.credentials.calls == 4
    assert flow.repository.get_video("low-value").should_summarize is False  # type: ignore[union-attr]

    report = flow.weekly_service().generate(now=NOW)
    report_path = flow.vault_root / "Knowledge" / report.note_ref.relative_path
    assert "[[Videos/" in report_path.read_text(encoding="utf-8")

    first_counts = flow.counts()
    first_report = report_path.read_bytes()
    first_report_hash = report.note_ref.content_hash
    del report
    del flow
    gc.collect()

    recovered = _OfflineMvpFlow(tmp_path, restore=True)
    assert recovered.transcripts == {}
    assert recovered.scores == {}
    assert recovered.analyses == {}
    assert recovered.note_sinks == {}
    assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 0, 0)
    assert recovered.credentials.calls == 0
    recovered.run(now=NOW + timedelta(minutes=5))
    repeated = recovered.weekly_service().generate(now=NOW + timedelta(minutes=5))

    assert recovered.counts() == first_counts
    assert report_path.read_bytes() == first_report
    assert repeated.note_ref.content_hash == first_report_hash
    assert (recovered.whisper.calls, recovered.scoring.calls, recovered.analysis.calls) == (0, 0, 0)
    assert recovered.credentials.calls == 0
    assert all(
        (adapter.enumerate_calls, adapter.read_calls) == (0, 0)
        for adapter in recovered.subtitle_adapters.values()
    )


def test_video_note_preserves_user_section(tmp_path: Path) -> None:
    flow = _OfflineMvpFlow(tmp_path)
    flow.run()

    note_path = flow.vault_root / "Knowledge" / "Videos" / next(
        path.name for path in (flow.vault_root / "Knowledge" / "Videos").glob("*manual-high.md")
    )
    edited_note = note_path.read_text(encoding="utf-8").replace(
        "## 我的思考\n\n", "## 我的思考\n\n保留的用户思考\n"
    )
    note_path.write_text(edited_note, encoding="utf-8")
    flow.note_sinks["manual-high"].upsert_video_note(
        video=flow.videos["manual-high"],
        transcript=flow.transcripts["manual-high"].artifact,
        scoring=flow.scores["manual-high"],  # type: ignore[arg-type]
        analysis=flow.analyses["manual-high"],  # type: ignore[arg-type]
        processed_at=NOW,
        pipeline_version=PIPELINE_VERSION,
    )

    persisted = note_path.read_text(encoding="utf-8")
    frontmatter = persisted.split("---", 2)[1]
    assert yaml.safe_load(frontmatter)["video_id"] == "manual-high"
    assert "保留的用户思考" in persisted


def test_cloud_disabled_keeps_the_offline_flow_complete_without_cloud_side_effects(
    tmp_path: Path,
) -> None:
    flow = _OfflineMvpFlow(tmp_path, cloud_enabled=False)

    flow.run()

    assert flow.analysis.calls == 0
    assert flow.credentials.calls == 0
    assert all(
        flow.repository.get_video(scenario.video_id).pipeline_status is PipelineStatus.COMPLETE  # type: ignore[union-attr]
        for scenario in SCENARIOS
    )
