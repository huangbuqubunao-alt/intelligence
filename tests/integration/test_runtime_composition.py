"""Production composition coverage for TASK-015.

These tests call the real CLI without injecting ``Operations``.  Only the
external provider boundary is replaced; bootstrap, composition, application
service, and SQLite are production code.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import pytest

from youtube_intel.cli import ExitCode, main
from youtube_intel.config import load_app_config
from youtube_intel.distillation import MoonshotK26NonThinkingCloudDistillationTransport
from youtube_intel.domain import (
    AnalysisCompleted,
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
    ProviderCallMetadata,
    QualityJudgeOperationInput,
    ScoreResult,
    SubtitleFormat,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.providers.ollama import parse_scoring_candidate
from youtube_intel.quality import QualityProvenanceAuthority
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.scoring import PrimaryScoringAttempt, build_primary_scoring_attempt
from youtube_intel.source_policy import PolicyOverrideMode
from youtube_intel.source_run import SourceRunAttentionReason, SourceRunState
from youtube_intel.state import ArtifactKind, PipelineStatus, SQLiteStateRepository
from youtube_intel.summary_draft import SummaryDraft, SummaryDraftPoint
from youtube_intel.transcripts import (
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
)

NOW = datetime(2026, 8, 12, 8, tzinfo=UTC)
VIDEO_ID = "2A1IEBFt6Xg"
SECOND_VIDEO_ID = "5ljV0Vxu00M"
CHANNEL_ID = "UCsooa4yRKGN_zEE8iknghZA"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "subtitles"


def test_runtime_scoring_prompt_is_an_installed_package_resource() -> None:
    package_prompt = resources.files("youtube_intel").joinpath("prompts", "scoring.md")
    source_prompt = Path(__file__).resolve().parents[2] / "prompts" / "scoring.md"

    assert package_prompt.read_bytes() == source_prompt.read_bytes()


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


class _SingleVideoDiscoverySource(_DiscoverySource):
    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch:
        batch = super().discover(channel, cursor)
        return batch.model_copy(update={"video_ids": (VIDEO_ID,)})


class _FailingDiscoverySource(_DiscoverySource):
    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch:
        del channel, cursor
        self.calls += 1
        raise RuntimeError("controlled ingestion failure")


class _MetadataProvider:
    calls = 0

    def fetch(self, video_id: str) -> VideoMetadata:
        self.calls += 1
        assert video_id == VIDEO_ID
        return VideoMetadata(
            video_id=VIDEO_ID,
            channel_id=CHANNEL_ID,
            channel_name="Public test channel",
            title="A short public product lesson",
            description="Public metadata fixture.",
            source_url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
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
        assert video_id == VIDEO_ID
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


class _TimedSubtitleAdapter(_SubtitleAdapter):
    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        result = super().read_track(track)
        cues = (
            "This manual subtitle contains enough meaningful text for validation.",
            "This public product lesson explains the reliable product workflow.",
            "Useful details remain grounded in the original English transcript.",
        )
        return SubtitleReadResult(
            body=json.dumps(
                {
                    "events": [
                        {
                            "tStartMs": index * 2500,
                            "dDurationMs": 1800,
                            "segs": [{"utf8": cue}],
                        }
                        for index, cue in enumerate(cues)
                    ]
                }
            ).encode("utf-8"),
            call=result.call,
        )


class _NoSubtitleAdapter(_SubtitleAdapter):
    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        assert video_id == VIDEO_ID
        self.enumerate_calls += 1
        return SubtitleTrackListing(tracks=(), call=self._call)


class _NativeCaptionRepairAdapter(_SubtitleAdapter):
    """Synthetic source replay: plain-only first, native timing after user retry."""

    native_available = False

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        original = super().enumerate_tracks(video_id)
        if not self.native_available:
            return original
        track = original.tracks[0]
        return SubtitleTrackListing(tracks=(*original.tracks, SubtitleTrack(
            source_type=track.source_type, language=track.language,
            source_format=SubtitleFormat.VTT, name=track.name,
            url="https://example.invalid/native-vtt", provider_position=1,
        )), call=original.call)

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        self.read_calls += 1
        lines = ("The product workflow begins with clear evidence from source material.",
                 "The second meaningful source sentence explains the reliable product workflow.")
        if track.source_format is SubtitleFormat.VTT:
            body = ("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n" + lines[0]
                    + "\n\n00:00:02.000 --> 00:00:04.000\n" + lines[1] + "\n").encode()
        else:
            body = json.dumps({"events": [{"segs": [{"utf8": line}]} for line in lines]}).encode()
        return SubtitleReadResult(body=body, call=self._call)


class _ScoringProvider:
    def __init__(self) -> None:
        self.calls = 0
        self._raw_response: str | None = None

    def _raw_envelope(self) -> str:
        inner = json.dumps(
            {
                "score": 8.6,
                "reason": "该回答解释了具体的产品策略，并包含有用的权衡分析。",
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

    def score(self, scoring_input: object) -> ScoreResult:
        self.calls += 1
        self._raw_response = self._raw_envelope()
        return ScoreResult(
            schema_version="score-result-v2",
            score=8.6,
            reason="该回答解释了具体的产品策略，并包含有用的权衡分析。",
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash=getattr(scoring_input, "request_hash"),
            output_language=getattr(scoring_input, "output_language"),
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        assert request_hash
        assert self._raw_response is not None
        response = self._raw_response
        self._raw_response = None
        return response


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
                "prompt_version": operation_input.prompt_version,
                "judge_provider": operation_input.judge_provider,
                "judge_model": operation_input.judge_model,
                "judge_model_digest": operation_input.judge_model_digest,
            }
        )


class _SummaryProvider:
    """The live provider contract: a backend-authoritative Summary draft."""

    def summarize(self, analysis_input: object) -> SummaryDraft:
        payload = getattr(analysis_input, "payload")
        offer = getattr(analysis_input, "trusted_evidence")
        assert offer is not None
        # A real model can only cite refs the backend actually issued.
        ref = next(
            candidate.ref
            for candidate in offer.candidates
            if candidate.source is EvidenceSource.TRANSCRIPT_SAMPLE
        )
        return SummaryDraft(
            one_sentence_summary="该视频介绍了一个产品观点。"
            if payload.output_language == "zh-CN"
            else "The video presents a product idea.",
            core_points=(
                SummaryDraftPoint(
                    text="内容围绕产品展开。"
                    if payload.output_language == "zh-CN"
                    else "The content focuses on a product.",
                    kind="fact",
                    evidence_refs=(ref,),
                ),
            ),
            keywords=("产品" if payload.output_language == "zh-CN" else "product",),
        )

    def consume_raw_response(self, *, request_hash: str) -> str:
        return json.dumps({"model": "qwen3:8b", "request_hash": request_hash}
        )


def _project(
    tmp_path: Path,
    *,
    model: str = "qwen3:8b",
    digest: str = f"sha256:{'1' * 64}",
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
  model: {model}
  expected_model_digest: {digest}
cloud:
  enabled: false
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: {tmp_path / "vault"}
  vault_subdir: YouTube Intel
""",
        encoding="utf-8",
    )
    return tmp_path


def test_default_cli_builds_production_composition_and_persists_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    source = _DiscoverySource()
    metadata = _MetadataProvider()

    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: RuntimeDependencies(
            discovery_source=source,
            metadata_provider=metadata,
            subtitle_adapter_factory=lambda: pytest.fail(
                "subtitle stage was not requested"
            ),
            scoring_provider_factory=lambda: pytest.fail(
                "scoring stage was not requested"
            ),
            analysis_provider_factory=lambda: pytest.fail(
                "analysis stage was not requested"
            ),
        ),
    )

    exit_code = main(
        [
            "--project-root",
            str(project),
            "check",
            "--channel",
            CHANNEL_ID,
            "--limit",
            "1",
        ]
    )

    assert exit_code is ExitCode.OK
    assert (source.calls, metadata.calls) == (1, 0)
    assert (project / "data" / "state.sqlite").is_file()
    assert (project / "logs" / "operations.jsonl").is_file()
    assert (project / "vault" / "YouTube Intel").is_dir()
    saved = SQLiteStateRepository(project / "data" / "state.sqlite").get_video(VIDEO_ID)
    assert saved is not None
    assert saved.pipeline_status is PipelineStatus.DISCOVERED
    assert saved.title is None
    assert (
        SQLiteStateRepository(project / "data" / "state.sqlite").get_video(
            SECOND_VIDEO_ID
        )
        is None
    )
    output = capsys.readouterr()
    assert "Discovered 1" in output.out
    assert output.err == ""


def test_gui_runtime_scores_and_writes_summary_note_before_local_distillation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-runtime-test-only")
    project = _project(tmp_path)
    source = _SingleVideoDiscoverySource()
    metadata = _MetadataProvider()
    subtitle = _TimedSubtitleAdapter()
    dependencies = RuntimeDependencies(
        discovery_source=source,
        metadata_provider=metadata,
        subtitle_adapter_factory=lambda: subtitle,
        scoring_provider_factory=_ScoringProvider,
        analysis_provider_factory=_SummaryProvider,
        quality_judge_provider_factory=_QualityJudgeProvider,
    )
    config = load_app_config(
        project / "config" / "channels.yaml",
        project / "config" / "settings.yaml",
    )
    database = project / "gui.sqlite3"
    first = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=database,
        dependencies=dependencies,
        now=lambda: NOW,
    )
    following = first.product.add_source(
        url=f"https://www.youtube.com/channel/{CHANNEL_ID}",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    first.source_policy.update_source(
        source_id=following.source_id,
        command_id="qualification-focus-policy",
        initial_history_count=None,
        per_run_max_new_videos=None,
        focus_mode=PolicyOverrideMode.OVERRIDE,
        focus_rules=("product",),
        ignore_mode=PolicyOverrideMode.INHERIT,
        ignore_rules=(),
        distillation_style_mode=PolicyOverrideMode.INHERIT,
        distillation_style=None,
    )
    status, accepted = first.application.handle(
        "POST",
        f"/api/v1/sources/{following.source_id}/check",
        b'{"command_id":"gui-command"}',
    )
    assert status == 202
    run_id = accepted["source_run"]["run_id"]
    assert first.repository.get_source_run(run_id) is not None
    interrupted = first.repository.transition_source_run(
        run_id,
        to_state=SourceRunState.RUNNING,
        now=NOW,
    )
    assert interrupted.state is SourceRunState.RUNNING

    restarted = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=database,
        dependencies=dependencies,
        now=lambda: NOW,
    )
    assert isinstance(
        restarted.cloud_distillation._transport,
        MoonshotK26NonThinkingCloudDistillationTransport,
    )
    assert restarted.cloud_distillation._transport._authorization.production_eligible
    duplicate_status, duplicate = restarted.application.handle(
        "POST",
        f"/api/v1/sources/{following.source_id}/check",
        b'{"command_id":"gui-command-after-restart"}',
    )
    assert duplicate_status == 202
    assert duplicate["source_run"]["run_id"] == run_id
    _, settings = restarted.application.handle("GET", "/api/v1/settings")
    moonshot = next(
        provider for provider in settings["providers"]
        if provider["provider"] == "moonshot"
    )
    assert moonshot["qualification_status"] == "QUALIFIED"
    assert moonshot["authorized"] is False
    nvidia = next(
        provider
        for provider in settings["providers"]
        if provider["provider"] == "NVIDIA NIM"
    )
    assert nvidia["production_eligible"] is False
    assert nvidia["credential_status"] == "BLOCKED"

    restarted.worker.start()
    deadline = time.monotonic() + 5
    while (
        restarted.orchestrator.get_run(run_id).state is SourceRunState.RUNNING
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    restarted.worker.stop()
    progressed = restarted.orchestrator.get_run(run_id)
    assert progressed.state is SourceRunState.NEEDS_ATTENTION
    assert len(restarted.repository.list_source_runs()) == 1
    assert restarted.repository.source_has_video(following.source_id, VIDEO_ID)
    transcript = restarted.repository.latest_artifact(
        VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL
    )
    assert transcript is not None
    transcript_path = project / "data" / transcript.relative_path
    assert transcript_path.is_file()
    assert transcript_path.read_text(encoding="utf-8").strip()
    assert (source.calls, metadata.calls, subtitle.read_calls) == (1, 1, 1)
    assert restarted.repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.COMPLETE
    analysis = restarted.runtime._load_analysis(VIDEO_ID)
    assert isinstance(analysis, AnalysisCompleted)
    assert analysis.result.provider == "ollama"
    assert analysis.result.one_sentence_summary == "该视频介绍了一个产品观点。"
    notes = list((project / "vault" / "YouTube Intel" / "Videos").glob(f"*{VIDEO_ID}.md"))
    assert len(notes) == 1
    assert "该视频介绍了一个产品观点。" in notes[0].read_text(encoding="utf-8")
    detail_status, detail = restarted.application.handle(
        "GET", f"/api/v1/videos/{VIDEO_ID}"
    )
    assert detail_status == 200
    assert detail["cloud_intelligence_available"] is True
    projected_note = detail["note"]["v2"]
    assert projected_note["status"] == "AVAILABLE"
    assert projected_note["language"] == "zh-CN"
    assert projected_note["summary"] == "该视频介绍了一个产品观点。"
    assert projected_note["timestamped_key_points"] == []
    assert projected_note["evidence_references"]
    # Metadata is context, never a citation, so no title/channel/description
    # reference may appear in the persisted Summary authority.
    assert all(
        reference["source"] != "title" for reference in projected_note["evidence_references"]
    )
    assert all(
        not reference["evidence_id"].startswith(("t", "m")) or len(
            reference["evidence_id"]
        )
        == 64
        for reference in projected_note["evidence_references"]
    )
    # Every persisted Summary citation is a DURABLE Evidence identity that
    # resolves through both public repository APIs.
    cited_ids = {
        reference["evidence_id"] for reference in projected_note["evidence_references"]
    }
    assert all(len(evidence_id) == 64 for evidence_id in cited_ids)
    for evidence_id in cited_ids:
        assert restarted.repository.get_evidence(evidence_id) is not None
        assert (
            restarted.repository.resolve_verified_evidence_text(evidence_id) is not None
        )
    # And the Summary surface correlates with the Evidence surface by identity.
    presented = set(restarted.repository.list_evidence_for_presentation(VIDEO_ID))
    assert cited_ids <= presented
    evidence_ids = restarted.repository.list_available_canonical_evidence_ids(VIDEO_ID)
    assert evidence_ids
    evidence = restarted.repository.get_evidence(evidence_ids[0])
    assert evidence is not None
    assert evidence.language == "en"
    verified_text = restarted.repository.resolve_verified_evidence_text(evidence_ids[0])
    assert verified_text is not None
    assert verified_text.excerpt

    api_status, projected = restarted.application.handle(
        "GET", f"/api/v1/source-runs/{run_id}"
    )
    assert api_status == 200
    assert projected["source_run"]["state"] == "NEEDS_ATTENTION"


def test_gui_runtime_persists_truthful_attention_when_ingestion_fails(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    source = _FailingDiscoverySource()
    dependencies = RuntimeDependencies(
        discovery_source=source,
        metadata_provider=_MetadataProvider(),
        subtitle_adapter_factory=lambda: pytest.fail(
            "failed discovery must not reach transcript ingestion"
        ),
        scoring_provider_factory=lambda: pytest.fail(
            "failed discovery must not reach model dispatch"
        ),
        analysis_provider_factory=lambda: pytest.fail(
            "failed discovery must not reach cloud dispatch"
        ),
    )
    config = load_app_config(
        project / "config" / "channels.yaml",
        project / "config" / "settings.yaml",
    )
    composition = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=project / "gui.sqlite3",
        dependencies=dependencies,
        now=lambda: NOW,
    )
    following = composition.product.add_source(
        url=f"https://www.youtube.com/channel/{CHANNEL_ID}",
        processing_policy=ProcessingPolicy.STANDARD_INTELLIGENCE,
    )
    _, accepted = composition.application.handle(
        "POST",
        f"/api/v1/sources/{following.source_id}/check",
        b'{"command_id":"gui-ingestion-failure"}',
    )

    progressed = composition.worker.run_once()

    assert progressed is not None
    assert progressed.run_id == accepted["source_run"]["run_id"]
    assert progressed.state is SourceRunState.NEEDS_ATTENTION
    assert (
        progressed.attention_reason
        is SourceRunAttentionReason.EXECUTION_CONDITION_UNRESOLVED
    )
    assert source.calls == 1


def test_doctor_is_read_only_and_explains_missing_first_run_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from urllib.error import URLError

    def offline_tags(request: object, *args: object, **kwargs: object) -> None:
        assert request.get_method() == "GET"
        assert request.full_url.endswith("/api/tags")
        raise URLError("offline doctor fixture")

    monkeypatch.setattr("youtube_intel.runtime.urllib.request.urlopen", offline_tags)
    project = _project(tmp_path)

    exit_code = main(["--project-root", str(project), "doctor"])

    assert exit_code is ExitCode.LOCAL_RESOURCE
    assert not (project / "data").exists()
    assert not (project / "logs").exists()
    assert not (project / "vault" / "YouTube Intel").exists()
    output = capsys.readouterr()
    assert "SQLite" in output.out
    assert "Run `youtube-intel check`" in output.out
    assert output.err == ""


def test_default_cli_runs_persistent_caption_to_note_and_weekly_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    source = _DiscoverySource()
    metadata = _MetadataProvider()
    # Timed cues are required: canonical-only Content has no Summary Evidence
    # authority and the ANALYSIS stage now fails closed without them.
    subtitle = _TimedSubtitleAdapter()
    scoring = _ScoringProvider()
    judge = _QualityJudgeProvider()

    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: RuntimeDependencies(
            discovery_source=source,
            metadata_provider=metadata,
            subtitle_adapter_factory=lambda: subtitle,
            scoring_provider_factory=lambda: scoring,
            analysis_provider_factory=_SummaryProvider,
            quality_judge_provider_factory=lambda: judge,
        ),
    )

    assert (
        main(["--project-root", str(project), "check", "--limit", "1"]) is ExitCode.OK
    )
    capsys.readouterr()

    assert (
        main(["--project-root", str(project), "process", "--video", VIDEO_ID])
        is ExitCode.OK
    )
    process_output = capsys.readouterr()
    assert "Processed 1 video" in process_output.out
    assert process_output.err == ""

    repository = SQLiteStateRepository(project / "data" / "state.sqlite")
    saved = repository.get_video(VIDEO_ID)
    assert saved is not None
    assert saved.pipeline_status is PipelineStatus.COMPLETE
    assert saved.should_summarize is True
    assert (
        metadata.calls,
        subtitle.enumerate_calls,
        subtitle.read_calls,
        scoring.calls,
    ) == (
        1,
        1,
        1,
        1,
    )
    notes = tuple((project / "vault" / "YouTube Intel" / "Videos").glob("*.md"))
    assert len(notes) == 1
    rendered = notes[0].read_text(encoding="utf-8")
    assert "A short public product lesson" in rendered
    assert "youtube.com/watch" in rendered

    assert main(["--project-root", str(project), "weekly"]) is ExitCode.OK
    weekly_output = capsys.readouterr()
    assert "Weekly report written" in weekly_output.out
    reports = tuple((project / "vault" / "YouTube Intel" / "Weekly").glob("*.md"))
    assert len(reports) == 1
    weekly = reports[0].read_text(encoding="utf-8")
    assert "youtube-intel:weekly:v1" in weekly
    assert "[[Videos/" in weekly
    assert "A short public product lesson" in weekly


def test_no_subtitle_stops_at_named_transcription_prerequisite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    subtitle = _NoSubtitleAdapter()
    scoring = _ScoringProvider()
    judge = _QualityJudgeProvider()
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: RuntimeDependencies(
            discovery_source=_DiscoverySource(),
            metadata_provider=_MetadataProvider(),
            subtitle_adapter_factory=lambda: subtitle,
            scoring_provider_factory=lambda: scoring,
            analysis_provider_factory=lambda: pytest.fail("cloud provider was called"),
            quality_judge_provider_factory=lambda: judge,
        ),
    )
    assert (
        main(["--project-root", str(project), "check", "--limit", "1"]) is ExitCode.OK
    )
    capsys.readouterr()

    exit_code = main(["--project-root", str(project), "process", "--video", VIDEO_ID])

    assert exit_code is ExitCode.EXECUTION_FAILED
    output = capsys.readouterr()
    assert "managed audio transcription is not yet composed" in output.err
    assert (subtitle.enumerate_calls, subtitle.read_calls, scoring.calls) == (1, 0, 0)
    saved = SQLiteStateRepository(project / "data" / "state.sqlite").get_video(VIDEO_ID)
    assert saved is not None
    assert saved.pipeline_status is PipelineStatus.METADATA_READY

    assert (
        main(["--project-root", str(project), "retry", "--video", VIDEO_ID])
        is ExitCode.EXECUTION_FAILED
    )
    retry_output = capsys.readouterr()
    assert "managed audio transcription is not yet composed" in retry_output.err
    # An explicit retry advances the durable provider refresh generation.
    assert subtitle.enumerate_calls == 2


def test_runtime_operations_mints_quality_provenance_authority_from_config(
    tmp_path: Path,
) -> None:
    """Runtime composition is the sole authority-minting boundary.

    The authority is derived from the already-loaded ``AppConfig``
    ``local_scoring`` settings, not from hard-coded constants, example files or
    caller input.  The fixture config uses a non-bbbb digest to prove the
    binding is real.
    """
    project = _project(tmp_path)
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    runtime = RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
        ),
    )

    authority = runtime._quality_provenance_authority
    assert isinstance(authority, QualityProvenanceAuthority)
    assert authority.judge_model == "qwen3:8b"
    assert authority.judge_model_digest == f"sha256:{'1' * 64}"
    assert authority.judge_provider == "ollama"


def test_runtime_operations_derives_authority_from_different_model_config(
    tmp_path: Path,
) -> None:
    """Runtime minting follows the loaded AppConfig for any model/digest pair."""
    project = _project(
        tmp_path,
        model="different-model",
        digest=f"sha256:{'1' * 64}",
    )
    config = load_app_config(
        channels_path=project / "config" / "channels.yaml",
        settings_path=project / "config" / "settings.yaml",
    )
    runtime = RuntimeOperations(
        config=config,
        project_root=project,
        dependencies=RuntimeDependencies(
            discovery_source=object(),  # type: ignore[arg-type]
            metadata_provider=object(),  # type: ignore[arg-type]
            subtitle_adapter_factory=lambda: object(),  # type: ignore[arg-type]
            scoring_provider_factory=lambda: object(),  # type: ignore[arg-type]
            analysis_provider_factory=lambda: object(),  # type: ignore[arg-type]
        ),
    )

    authority = runtime._quality_provenance_authority
    assert type(authority) is QualityProvenanceAuthority
    assert authority.judge_model == "different-model"
    assert authority.judge_model_digest == f"sha256:{'1' * 64}"
    assert authority.judge_provider == "ollama"

def test_local_summary_identity_does_not_grant_intelligence_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M5 Summary qualification and a matching digest cannot grant Intelligence."""
    from youtube_intel.distillation import (
        VerifiedDistillationInput,
        VerifiedEvidenceInput,
    )

    project = _project(
        tmp_path,
        digest="sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41",
    )
    dependencies = RuntimeDependencies(
        discovery_source=_DiscoverySource(),
        metadata_provider=_MetadataProvider(),
        subtitle_adapter_factory=lambda: pytest.fail("subtitle stage was not requested"),
        scoring_provider_factory=lambda: pytest.fail("scoring stage was not requested"),
        analysis_provider_factory=lambda: pytest.fail("analysis stage was not requested"),
    )
    config = load_app_config(
        project / "config" / "channels.yaml",
        project / "config" / "settings.yaml",
    )
    database = project / "gui.sqlite3"
    composition = build_local_source_run_runtime(
        config=config,
        project_root=project,
        database=database,
        dependencies=dependencies,
        now=lambda: NOW,
    )
    transport = composition.distillation._transport
    assert transport.actual_provider == "ollama"
    assert transport.actual_model == config.settings.local_scoring.model
    verified = VerifiedDistillationInput(
        source_display_name="Public source",
        video_id=VIDEO_ID,
        video_title="A public title",
        evidence=(
            VerifiedEvidenceInput(
                evidence_id="evidence-1",
                start_ms=1_000,
                end_ms=2_000,
                excerpt="The product launched in April.",
                excerpt_hash="a" * 64,
                timed_transcript_id="transcript-1",
                timed_transcript_hash="b" * 64,
            ),
        ),
        personalization=(),
        source_focus_rules=(),
        source_ignore_rules=(),
        distillation_style=None,
        selected_provider="ollama",
        selected_model=config.settings.local_scoring.model,
        semantic_hash="c" * 64,
        output_language="zh-CN",
    )
    requests: list[object] = []
    monkeypatch.setattr(transport, "_request", lambda *args, **kwargs: requests.append(args))
    assert transport.is_authorized_for(verified) is True
    assert transport.is_authorized_for_normal_production(verified) is False
    assert requests == []


def test_explicit_user_check_atomically_repairs_completed_plain_captions(tmp_path: Path) -> None:
    project = _project(tmp_path)
    adapter = _NativeCaptionRepairAdapter()
    dependencies = RuntimeDependencies(
        discovery_source=_SingleVideoDiscoverySource(), metadata_provider=_MetadataProvider(),
        subtitle_adapter_factory=lambda: adapter,
        scoring_provider_factory=lambda: pytest.fail("Content repair must not dispatch scoring"),
        analysis_provider_factory=lambda: pytest.fail("Content repair must not dispatch analysis"),
    )
    config = load_app_config(project / "config/channels.yaml", project / "config/settings.yaml")
    runtime = build_local_source_run_runtime(config=config, project_root=project,
        database=project / "gui.sqlite3", dependencies=dependencies, now=lambda: datetime.now(UTC))
    source = runtime.product.add_source(url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
                                       processing_policy=ProcessingPolicy.DISCOVER_ONLY)
    status, first = runtime.application.handle("POST", f"/api/v1/sources/{source.source_id}/check",
                                               b'{"command_id":"synthetic-plain-caption-import"}')
    assert status == 202
    runtime.worker.run_once()
    assert runtime.repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.TRANSCRIPT_READY
    original_job = runtime.repository.latest_video_job(VIDEO_ID)
    assert original_job is not None and original_job.status.value == "SUCCEEDED"
    plain = runtime.repository.latest_artifact(VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL)
    assert plain is not None
    plain_body = (project / "data" / plain.relative_path).read_bytes()
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None
    assert runtime.application.handle("GET", f"/api/v1/videos/{VIDEO_ID}")[1]["video"]["processing_status"] == "NEEDS_ATTENTION"
    adapter.native_available = True
    status, second = runtime.application.handle("POST", f"/api/v1/sources/{source.source_id}/check",
                                                b'{"command_id":"synthetic-explicit-caption-repair"}')
    assert status == 202 and first["source_run"]["run_id"] != second["source_run"]["run_id"]
    progressed = runtime.worker.run_once()
    assert progressed is not None
    timed = runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert timed is not None and len(timed.cues) == 2
    assert runtime.repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert runtime.repository.current_local_summary_pointer(VIDEO_ID) is not None
    assert runtime.repository.get_job(original_job.job_id) == original_job
    assert (project / "data" / plain.relative_path).read_bytes() == plain_body
    assert runtime.repository.get_video(VIDEO_ID).pipeline_status is PipelineStatus.TRANSCRIPT_READY
    assert runtime.application.handle("GET", f"/api/v1/videos/{VIDEO_ID}")[1]["video"]["processing_status"] == "ORGANIZED"
    reads = adapter.read_calls
    runtime.application.handle("POST", f"/api/v1/sources/{source.source_id}/check",
                               b'{"command_id":"synthetic-idempotent-after-repair"}')
    runtime.worker.run_once()
    assert adapter.read_calls == reads


def _completed_plain_caption_runtime(tmp_path: Path):
    project = _project(tmp_path)
    adapter = _NativeCaptionRepairAdapter()
    dependencies = RuntimeDependencies(discovery_source=_SingleVideoDiscoverySource(),
        metadata_provider=_MetadataProvider(), subtitle_adapter_factory=lambda: adapter,
        scoring_provider_factory=lambda: pytest.fail("Caption repair must not dispatch scoring"),
        analysis_provider_factory=lambda: pytest.fail("Caption repair must not dispatch analysis"))
    config = load_app_config(project / "config/channels.yaml", project / "config/settings.yaml")
    runtime = build_local_source_run_runtime(config=config, project_root=project,
        database=project / "gui.sqlite3", dependencies=dependencies, now=lambda: datetime.now(UTC))
    source = runtime.product.add_source(url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
                                       processing_policy=ProcessingPolicy.DISCOVER_ONLY)
    runtime.application.handle("POST", f"/api/v1/sources/{source.source_id}/check",
                               b'{"command_id":"synthetic-plain-import"}')
    runtime.worker.run_once()
    adapter.native_available = True
    return runtime, adapter, source.source_id, config, dependencies


@pytest.mark.parametrize("restart", [False, True])
def test_successful_caption_repair_summary_exception_offers_safe_summary_only_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restart: bool) -> None:
    from youtube_intel.extractive_summary import ExtractiveSummaryService

    runtime, adapter, source_id, config, dependencies = _completed_plain_caption_runtime(tmp_path)
    original_job = runtime.repository.latest_video_job(VIDEO_ID)
    original_canonical = runtime.repository.latest_artifact(VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL)
    original_create = ExtractiveSummaryService.create

    def fail_summary(*args, **kwargs):
        raise RuntimeError("synthetic ordinary Summary failure after caption commit")

    monkeypatch.setattr(ExtractiveSummaryService, "create", fail_summary)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-summary-fails-after-repair"}')
    failed = runtime.worker.run_once()
    assert failed is not None and failed.state is SourceRunState.NEEDS_ATTENTION
    timed = runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    evidence_ids = runtime.repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert timed is not None and evidence_ids
    assert runtime.repository.current_local_summary_pointer(VIDEO_ID) is None
    repaired_job = runtime.repository.latest_video_job(VIDEO_ID)
    assert repaired_job is not None and repaired_job.status.value == "SUCCEEDED"
    reads = adapter.read_calls
    with runtime.repository._connect() as connection:
        provider_history = tuple(tuple(row) for row in connection.execute(
            "SELECT * FROM provider_calls ORDER BY request_hash"))
    if restart:
        runtime = build_local_source_run_runtime(config=config, project_root=tmp_path,
            database=tmp_path / "gui.sqlite3", dependencies=dependencies, now=lambda: datetime.now(UTC))
    status, detail = runtime.application.handle("GET", f"/api/v1/videos/{VIDEO_ID}")
    assert status == 200
    assert detail["video"]["processing_status"] == "RETRY_REQUIRED"
    assert detail["video"]["summary_preparation_status"] == "NEEDS_ATTENTION"
    assert detail["video"]["retry_allowed"] is True

    def retry_summary(service, video_id, **kwargs):
        # A real active retry remains asynchronous and protected; the settled
        # failure hint must not replace live Source Run status.
        projection = runtime.application.handle("GET", f"/api/v1/videos/{VIDEO_ID}")[1]["video"]
        assert projection["processing_status"] == "WAITING"
        assert "summary_preparation_status" not in projection
        assert not runtime.backup_restore.readiness()["ready"]
        return original_create(service, video_id, **kwargs)

    monkeypatch.setattr(ExtractiveSummaryService, "create", retry_summary)
    status, _ = runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-summary-only-retry"}')
    assert status == 202
    assert not runtime.backup_restore.readiness()["ready"]
    completed = runtime.worker.run_once()
    assert completed is not None and completed.state is SourceRunState.COMPLETED
    assert runtime.application.handle("GET", f"/api/v1/videos/{VIDEO_ID}")[1]["video"]["processing_status"] == "ORGANIZED"
    assert runtime.repository.current_local_summary_pointer(VIDEO_ID) is not None
    assert runtime.backup_restore.readiness()["ready"]
    assert adapter.read_calls == reads
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) == timed
    assert runtime.repository.list_canonical_coverage_evidence_ids(VIDEO_ID) == evidence_ids
    assert original_job is not None and runtime.repository.get_job(original_job.job_id) == original_job
    assert original_canonical is not None and runtime.repository.get_artifact(original_canonical.artifact_id) == original_canonical
    assert runtime.repository.get_job(repaired_job.job_id) == repaired_job
    assert runtime.repository.get_source_run(failed.run_id) == failed
    with runtime.repository._connect() as connection:
        assert tuple(tuple(row) for row in connection.execute(
            "SELECT * FROM provider_calls ORDER BY request_hash")) == provider_history
    assert sum(job.job_id.startswith("caption-repair-")
               for job in runtime.repository.list_video_jobs(VIDEO_ID, limit=1000)) == 1


@pytest.mark.parametrize("failure_point", ["caption_repair.after_artifacts", "caption_repair.after_authority"])
def test_caption_repair_transaction_rollback_retains_history_and_allows_explicit_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_point: str) -> None:
    runtime, adapter, source_id, _, _ = _completed_plain_caption_runtime(tmp_path)
    original_job = runtime.repository.latest_video_job(VIDEO_ID)
    old = runtime.repository.latest_artifact(VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL)
    assert old is not None and original_job is not None
    original_inject = runtime.repository._inject_failure
    def fail(point: str) -> None:
        if point == failure_point:
            raise RuntimeError("synthetic atomic failure")
    monkeypatch.setattr(runtime.repository, "_inject_failure", fail)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-failing-repair"}')
    failed = runtime.worker.run_once()
    assert failed is not None and failed.state is SourceRunState.NEEDS_ATTENTION
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None
    assert not runtime.repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert runtime.repository.current_local_summary_pointer(VIDEO_ID) is None
    assert runtime.repository.latest_artifact(VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL) == old
    assert runtime.repository.get_job(original_job.job_id) == original_job
    with runtime.repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND artifact_key LIKE 'subtitle-source-capture:%'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND artifact_key NOT LIKE 'subtitle-source-capture:%'").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM timed_transcripts").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM provider_calls WHERE status='SUCCEEDED'").fetchone()[0] == 1
    monkeypatch.setattr(runtime.repository, "_inject_failure", original_inject)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-explicit-repair-retry"}')
    runtime.worker.run_once()
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is not None
    assert runtime.repository.current_local_summary_pointer(VIDEO_ID) is not None
    assert adapter.read_calls == 5  # initial JSON3 + two bounded JSON3/VTT attempts
    # The failed repair remains history; retry derives from the original
    # successful canonical job rather than creating an unrelated stage rerun.
    jobs = runtime.repository.list_video_jobs(VIDEO_ID, limit=1000)
    assert sum(job.job_id.startswith("caption-repair-") for job in jobs) == 2
    assert not any(job.job_id.startswith("content-retry-") for job in jobs)
    assert runtime.repository.get_job(original_job.job_id) == original_job


@pytest.mark.parametrize("invalid", ["owner", "expired_lease", "foreign_run", "current_pointer", "foreign_artifact", "native_timing", "canonical_hash", "unknown_ledger"])
def test_caption_repair_rejects_unowned_foreign_changed_or_unproven_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str) -> None:
    from dataclasses import replace
    from datetime import timedelta

    from youtube_intel.state import TimedTranscriptCueWrite, TimedTranscriptWrite

    runtime, _, source_id, _, _ = _completed_plain_caption_runtime(tmp_path)
    original_job = runtime.repository.latest_video_job(VIDEO_ID)
    old = runtime.repository.latest_artifact(VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL)
    original = runtime.repository.complete_caption_repair
    def corrupt(**kwargs):
        if invalid == "owner":
            kwargs["owner"] = "foreign-worker"
        elif invalid == "expired_lease":
            kwargs["now"] += timedelta(minutes=10)
        elif invalid == "foreign_run":
            kwargs["source_run_id"] = "foreign-run"
        elif invalid == "current_pointer":
            kwargs["expected_canonical_artifact_id"] = "foreign-canonical"
        elif invalid == "foreign_artifact":
            kwargs["artifacts"] = (kwargs["artifacts"][0], replace(kwargs["artifacts"][1], video_id="foreign-video"))
        elif invalid == "native_timing":
            timed = kwargs["timed"]
            altered = tuple(TimedTranscriptCueWrite(start_ms=c.start_ms, end_ms=c.end_ms + (1 if i == 1 else 0), text=c.text) for i, c in enumerate(timed.cues))
            kwargs["timed"] = TimedTranscriptWrite.from_cues(video_id=timed.video_id, canonical_artifact_id=timed.canonical_artifact_id, cues=altered)
        elif invalid == "canonical_hash":
            (kwargs["data_root"] / kwargs["artifacts"][1].relative_path).write_bytes(b"synthetic changed text\n")
        elif invalid == "unknown_ledger":
            runtime.repository.record_provider_dispatch_intent(kwargs["provider_call"].request_hash, owner=kwargs["owner"], now=kwargs["now"])
        return original(**kwargs)
    monkeypatch.setattr(runtime.repository, "complete_caption_repair", corrupt)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-invalid-repair"}')
    runtime.worker.run_once()
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None
    assert not runtime.repository.list_canonical_coverage_evidence_ids(VIDEO_ID)
    assert runtime.repository.latest_artifact(VIDEO_ID, ArtifactKind.TRANSCRIPT_CANONICAL) == old
    assert original_job is not None and runtime.repository.get_job(original_job.job_id) == original_job
    with runtime.repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND artifact_key LIKE 'subtitle-source-capture:%'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND artifact_key NOT LIKE 'subtitle-source-capture:%'").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM timed_transcripts").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0


def test_caption_repair_concurrent_completion_commits_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from concurrent.futures import ThreadPoolExecutor

    runtime, _, source_id, _, _ = _completed_plain_caption_runtime(tmp_path)
    original = runtime.repository.complete_caption_repair
    outcomes: list[str] = []
    def concurrent(**kwargs):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(original, **kwargs) for _ in range(2)]
            results = []
            for future in futures:
                try:
                    results.append(future.result())
                    outcomes.append("committed")
                except Exception:
                    outcomes.append("rejected")
            assert len(results) == 1
            return results[0]
    monkeypatch.setattr(runtime.repository, "complete_caption_repair", concurrent)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-concurrent-repair"}')
    runtime.worker.run_once()
    assert sorted(outcomes) == ["committed", "rejected"]
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is not None
    assert runtime.repository.current_local_summary_pointer(VIDEO_ID) is not None
    with runtime.repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%'").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id LIKE 'caption-repair-%' AND artifact_key LIKE 'subtitle-source-capture:%'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM timed_transcripts").fetchone()[0] == 1


@pytest.mark.parametrize("live_lease", ["job", "provider"])
def test_caption_repair_restart_retains_command_child_and_raw_after_lease_expiry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, live_lease: str) -> None:
    from datetime import timedelta

    from youtube_intel import runtime_composition as composition_module

    class SyntheticProcessInterruption(BaseException):
        pass

    runtime, adapter, source_id, config, dependencies = _completed_plain_caption_runtime(tmp_path)
    def interrupt(point: str) -> None:
        if point == "caption_repair.after_authority":
            raise SyntheticProcessInterruption()
    monkeypatch.setattr(runtime.repository, "_inject_failure", interrupt)
    status, accepted = runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"synthetic-interrupted-repair"}')
    assert status == 202
    run_id = accepted["source_run"]["run_id"]
    with pytest.raises(SyntheticProcessInterruption):
        runtime.worker.run_once()
    job = runtime.repository.latest_video_job(VIDEO_ID)
    assert job is not None and job.status.value == "RUNNING"
    if live_lease == "provider":
        # A crash can leave a provider reservation alive after the job lease
        # ends. Reproduce that isolated SQLite state without contacting a host.
        with runtime.repository._connect() as connection:
            connection.execute("UPDATE jobs SET lease_until=? WHERE job_id=?",
                               ((datetime.now(UTC) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"), job.job_id))
    assert not runtime.backup_restore.readiness()["ready"]
    assert runtime.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is None
    reads = adapter.read_calls
    restarted = build_local_source_run_runtime(config=config, project_root=tmp_path,
        database=tmp_path / "gui.sqlite3", dependencies=dependencies, now=lambda: datetime.now(UTC))
    deferred = restarted.worker.run_once()
    assert deferred is not None and deferred.run_id == run_id and deferred.state is SourceRunState.RUNNING
    assert adapter.read_calls == reads
    future = datetime.now(UTC) + timedelta(minutes=10)
    class ExpiredLeaseClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return future
    monkeypatch.setattr(composition_module, "datetime", ExpiredLeaseClock)
    resumed = restarted.worker.run_once()
    assert resumed is not None and resumed.run_id == run_id
    saved = restarted.repository.get_job(job.job_id)
    assert saved is not None and saved.status.value == "SUCCEEDED" and saved.attempt_count == 2
    assert adapter.read_calls == reads
    assert restarted.repository.get_verified_timed_transcript(video_id=VIDEO_ID) is not None
    assert restarted.repository.current_local_summary_pointer(VIDEO_ID) is not None
    timed = restarted.repository.get_verified_timed_transcript(video_id=VIDEO_ID)
    assert restarted.backup_restore.readiness()["ready"]
    # Rebuilding ordinary runtime and explicitly checking again must retain
    # authority and avoid both a new repair child and another subtitle fetch.
    again = build_local_source_run_runtime(config=config, project_root=tmp_path,
        database=tmp_path / "gui.sqlite3", dependencies=dependencies, now=lambda: future)
    again.application.handle("POST", f"/api/v1/sources/{source_id}/check",
                             b'{"command_id":"synthetic-post-repair-restart"}')
    again.worker.run_once()
    assert again.repository.get_verified_timed_transcript(video_id=VIDEO_ID) == timed
    assert adapter.read_calls == reads
    assert sum(saved.job_id.startswith("caption-repair-")
               for saved in again.repository.list_video_jobs(VIDEO_ID, limit=1000)) == 1


def test_native_capture_backup_restore_preserves_every_table_and_every_data_file(tmp_path: Path) -> None:
    import hashlib
    import sqlite3
    runtime, adapter, source_id, _, _ = _completed_plain_caption_runtime(tmp_path)
    runtime.application.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"capture-full-restore"}')
    runtime.worker.run_once()
    service = runtime.backup_restore
    data = service.data_root
    def files():
        return {p.relative_to(data).as_posix(): (p.read_bytes(), hashlib.sha256(p.read_bytes()).hexdigest())
                for p in data.rglob("*") if p.is_file()}
    def tables():
        with sqlite3.connect(service.database) as connection:
            return {name: sorted((tuple(row) for row in connection.execute('SELECT * FROM "' + name + '"')), key=repr)
                    for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    before_files, before_tables, reads = files(), tables(), adapter.read_calls
    assert service.readiness()["ready"]
    with runtime.repository._connect() as connection:
        captures = connection.execute("SELECT * FROM artifacts WHERE artifact_key LIKE 'subtitle-source-capture:%'").fetchall()
        assert len(captures) == 3  # initial plain + repair plain/native, preserving both histories
        assert all(row["relative_path"] in before_files for row in captures)
    backup = service.create_backup()
    archive, _ = service.backup_download(backup.backup_id)
    preview = service.stage_restore(archive.read_bytes())
    service.confirm_restore(preview.restore_id)
    service.recover_and_apply_pending_restore()
    assert files() == before_files
    assert tables() == before_tables
    assert adapter.read_calls == reads
    restored = SQLiteStateRepository(service.database)
    restored.bind_source_storage(data)
    assert restored.get_verified_timed_transcript(video_id=VIDEO_ID) is not None
    assert restored.current_local_summary_pointer(VIDEO_ID) is not None
    assert service.readiness()["ready"]


def test_bigmodel_credential_di_is_configuration_only_and_independent(tmp_path, monkeypatch):
    from youtube_intel.model_settings import CredentialStoreError

    class FakeStore:
        def __init__(self):
            self.secret = None
            self.calls = []
        def get(self):
            self.calls.append("get")
            return self.secret
        def save(self, secret):
            self.calls.append("save")
            self.secret = secret
        def delete(self):
            self.calls.append("delete")
            self.secret = None

    def forbidden(*args, **kwargs):
        raise AssertionError("No native Keychain or model dispatch in configuration QA")

    old, candidate = FakeStore(), FakeStore()
    monkeypatch.setenv("MOONSHOT_API_KEY", "synthetic-old-config-only")
    monkeypatch.setattr("youtube_intel.model_settings.MacOSBigModelCredentialStore._libraries", forbidden)
    monkeypatch.setattr("youtube_intel.runtime_composition.local_models", lambda *args: {"models": []})
    monkeypatch.setattr("youtube_intel.runtime_composition.local_runtime_version", lambda *args: {})
    project = _project(tmp_path)
    config = load_app_config(project / "config/channels.yaml", project / "config/settings.yaml")
    runtime = build_local_source_run_runtime(config=config, project_root=project,
        database=project / "isolated-settings.sqlite3", credential_store=old,
        bigmodel_credential_store=candidate, now=lambda: NOW)
    old_before = list(old.calls)
    cloud_before = runtime.application._cloud_distillation_service
    old_available = runtime.application._cloud_credential_available
    path = "/api/v1/settings/bigmodel-credential"
    _, result = runtime.application.handle("PUT", path, b'{"credential":"synthetic-bigmodel-di"}')
    assert result["configured"] is True
    assert result["qualification"] == "NOT_VERIFIED" and result["budget"] == "CLOSED"
    assert candidate.calls == ["save", "get"]
    assert old.calls == old_before and old.secret is None
    assert runtime.application._cloud_distillation_service is cloud_before
    assert runtime.application._cloud_credential_available == old_available
    runtime.application.handle("POST", path + "/delete", b'{"confirm":"DELETE"}')
    assert candidate.secret is None and old.calls == old_before
    # A later native outage cannot change the legacy provider's availability.
    def unavailable():
        raise CredentialStoreError()
    candidate.get = unavailable
    assert runtime.application.handle("GET", path)[1]["source"] == "UNAVAILABLE"
    assert runtime.application._cloud_credential_available == old_available
