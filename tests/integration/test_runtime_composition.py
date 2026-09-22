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
from youtube_intel.domain import (
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
from youtube_intel.source_run import SourceRunAttentionReason, SourceRunState
from youtube_intel.state import ArtifactKind, PipelineStatus, SQLiteStateRepository
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


class _NoSubtitleAdapter(_SubtitleAdapter):
    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        assert video_id == VIDEO_ID
        self.enumerate_calls += 1
        return SubtitleTrackListing(tracks=(), call=self._call)


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
                "judge_provider": operation_input.judge_provider,
                "judge_model": operation_input.judge_model,
                "judge_model_digest": operation_input.judge_model_digest,
            }
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


def test_gui_runtime_uses_durable_run_and_ingests_body_before_model_work(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    source = _SingleVideoDiscoverySource()
    metadata = _MetadataProvider()
    subtitle = _SubtitleAdapter()
    dependencies = RuntimeDependencies(
        discovery_source=source,
        metadata_provider=metadata,
        subtitle_adapter_factory=lambda: subtitle,
        scoring_provider_factory=lambda: pytest.fail(
            "GUI ingestion must stop before local model dispatch"
        ),
        analysis_provider_factory=lambda: pytest.fail(
            "GUI ingestion must not call a cloud provider"
        ),
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
    duplicate_status, duplicate = restarted.application.handle(
        "POST",
        f"/api/v1/sources/{following.source_id}/check",
        b'{"command_id":"gui-command-after-restart"}',
    )
    assert duplicate_status == 202
    assert duplicate["source_run"]["run_id"] == run_id
    _, settings = restarted.application.handle("GET", "/api/v1/settings")
    nvidia = next(
        provider
        for provider in settings["providers"]
        if provider["provider"] == "NVIDIA NIM"
    )
    assert nvidia["production_eligible"] is False
    assert nvidia["credential_status"] == "NOT_CONFIGURED"

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
) -> None:
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
    subtitle = _SubtitleAdapter()
    scoring = _ScoringProvider()
    judge = _QualityJudgeProvider()

    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: RuntimeDependencies(
            discovery_source=source,
            metadata_provider=metadata,
            subtitle_adapter_factory=lambda: subtitle,
            scoring_provider_factory=lambda: scoring,
            analysis_provider_factory=lambda: pytest.fail(
                "cloud-disabled composition called the cloud provider"
            ),
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
