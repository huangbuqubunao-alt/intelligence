"""Production composition coverage for TASK-015.

These tests call the real CLI without injecting ``Operations``.  Only the
external provider boundary is replaced; bootstrap, composition, application
service, and SQLite are production code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import pytest

from youtube_intel.cli import ExitCode, main
from youtube_intel.domain import (
    Availability,
    ChannelRef,
    DiscoveryBatch,
    DiscoveryCursor,
    LiveStatus,
    ProviderCallMetadata,
    ScoreResult,
    SubtitleFormat,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.runtime import RuntimeDependencies
from youtube_intel.state import PipelineStatus, SQLiteStateRepository
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
    package_prompt = resources.files("youtube_intel").joinpath(
        "prompts", "scoring.md"
    )
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

    def score(self, scoring_input: object) -> ScoreResult:
        self.calls += 1
        self._raw_response = (
            '{"score":8.6,"reason":"controlled local result",'
            '"topics":["product"],"should_summarize":true}'
        )
        return ScoreResult(
            schema_version="score-result-v2",
            score=8.6,
            reason="受控本地评分覆盖了正式运行时组合。",
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
  enabled: false
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
            subtitle_adapter_factory=lambda: pytest.fail("subtitle stage was not requested"),
            scoring_provider_factory=lambda: pytest.fail("scoring stage was not requested"),
            analysis_provider_factory=lambda: pytest.fail("analysis stage was not requested"),
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
        ),
    )

    assert main(["--project-root", str(project), "check", "--limit", "1"]) is ExitCode.OK
    capsys.readouterr()

    assert main(["--project-root", str(project), "process", "--video", VIDEO_ID]) is ExitCode.OK
    process_output = capsys.readouterr()
    assert "Processed 1 video" in process_output.out
    assert process_output.err == ""

    repository = SQLiteStateRepository(project / "data" / "state.sqlite")
    saved = repository.get_video(VIDEO_ID)
    assert saved is not None
    assert saved.pipeline_status is PipelineStatus.COMPLETE
    assert saved.should_summarize is True
    assert (metadata.calls, subtitle.enumerate_calls, subtitle.read_calls, scoring.calls) == (
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
    monkeypatch.setattr(
        "youtube_intel.runtime._production_dependencies",
        lambda _config: RuntimeDependencies(
            discovery_source=_DiscoverySource(),
            metadata_provider=_MetadataProvider(),
            subtitle_adapter_factory=lambda: subtitle,
            scoring_provider_factory=lambda: scoring,
            analysis_provider_factory=lambda: pytest.fail("cloud provider was called"),
        ),
    )
    assert main(["--project-root", str(project), "check", "--limit", "1"]) is ExitCode.OK
    capsys.readouterr()

    exit_code = main(
        ["--project-root", str(project), "process", "--video", VIDEO_ID]
    )

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
