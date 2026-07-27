"""Offline integration tests for the restricted public subtitle smoke entry."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from youtube_intel.cli import ExitCode, main
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    ProviderCallMetadata,
    SubtitleFormat,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.public_subtitle_smoke import PublicSubtitleSmoke
from youtube_intel.transcripts import (
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
)

NOW = datetime(2026, 7, 26, tzinfo=UTC)
VIDEO_IDS = ("video001", "video002")
SUBTITLE_BODY = b"private subtitle body must not persist"


def _call() -> ProviderCallMetadata:
    return ProviderCallMetadata(provider="fake", started_at=NOW, finished_at=NOW)


def _metadata(video_id: str) -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        channel_id="channel",
        channel_name="Channel",
        title="Title",
        source_url=f"https://example.invalid/{video_id}",
        published_at=NOW,
        duration_seconds=1,
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


@dataclass
class _FakeMetadataProvider:
    calls: list[str] = field(default_factory=list)
    fail_for: str | None = None

    def fetch(self, video_id: str) -> VideoMetadata:
        self.calls.append(video_id)
        if video_id == self.fail_for:
            raise RuntimeError("metadata failure containing /sensitive/path")
        return _metadata(video_id)


@dataclass
class _FakeSubtitleAdapter:
    enumerate_calls: list[str] = field(default_factory=list)
    read_calls: list[SubtitleTrack] = field(default_factory=list)
    fail_for: str | None = None

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        self.enumerate_calls.append(video_id)
        if video_id == self.fail_for:
            raise RuntimeError("enumerate failure")
        return SubtitleTrackListing(
            tracks=(
                SubtitleTrack(
                    source_type=TranscriptSourceType.AUTO_SUBTITLE,
                    language="en",
                    source_format=SubtitleFormat.VTT,
                    name="English",
                    url="https://example.invalid/temporary-url",
                    provider_position=1,
                ),
                SubtitleTrack(
                    source_type=TranscriptSourceType.MANUAL_SUBTITLE,
                    language="en",
                    source_format=SubtitleFormat.JSON3,
                    name="English",
                    url="https://example.invalid/another-temporary-url",
                    provider_position=2,
                ),
            ),
            call=_call(),
        )

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        self.read_calls.append(track)
        if track.url.endswith("another-temporary-url") and track.name == "fail":
            raise RuntimeError("read failure")
        return SubtitleReadResult(body=SUBTITLE_BODY, call=_call())


def _smoke(
    metadata: _FakeMetadataProvider,
    subtitles: _FakeSubtitleAdapter,
    *,
    metadata_timeouts: list[float] | None = None,
    subtitle_timeouts: list[float] | None = None,
) -> PublicSubtitleSmoke:
    def metadata_factory(timeout_seconds: float) -> _FakeMetadataProvider:
        if metadata_timeouts is not None:
            metadata_timeouts.append(timeout_seconds)
        return metadata

    def subtitle_factory(timeout_seconds: float) -> _FakeSubtitleAdapter:
        if subtitle_timeouts is not None:
            subtitle_timeouts.append(timeout_seconds)
        return subtitles

    return PublicSubtitleSmoke(
        metadata_provider_factory=metadata_factory,
        subtitle_adapter_factory=subtitle_factory,
        now=lambda: NOW,
    )


def _args(root: Path, *video_ids: str) -> list[str]:
    return [
        "smoke-public-subtitles",
        "--temporary-root",
        str(root),
        *[part for video_id in video_ids for part in ("--video-id", video_id)],
    ]


def test_smoke_isolated_to_new_root_and_reads_each_selected_track_once(tmp_path: Path) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _FakeSubtitleAdapter()
    metadata_timeouts: list[float] = []
    subtitle_timeouts: list[float] = []
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, *VIDEO_IDS),
        smoke_runner=_smoke(
            metadata,
            subtitles,
            metadata_timeouts=metadata_timeouts,
            subtitle_timeouts=subtitle_timeouts,
        ),
    )

    assert exit_code is ExitCode.OK
    assert metadata.calls == list(VIDEO_IDS)
    assert subtitles.enumerate_calls == list(VIDEO_IDS)
    assert len(subtitles.read_calls) == len(VIDEO_IDS)
    assert all(track.source_type is TranscriptSourceType.MANUAL_SUBTITLE for track in subtitles.read_calls)
    assert metadata_timeouts == [30.0]
    assert subtitle_timeouts == [30.0]
    assert {path.name for path in root.iterdir()} == {"state.sqlite", "data", "test-vault", "logs"}
    assert list((root / "data").iterdir()) == []
    assert list((root / "test-vault").iterdir()) == []

    with sqlite3.connect(root / "state.sqlite") as connection:
        for table in ("videos", "jobs", "provider_calls", "artifacts"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (0,)

    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    assert SUBTITLE_BODY.decode() not in log_text
    assert "temporary-url" not in log_text
    assert str(root) not in log_text
    assert all(
        SUBTITLE_BODY not in path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    )
    records = [json.loads(line) for line in log_text.splitlines()]
    assert {record["video_id"] for record in records if "video_id" in record} == set(VIDEO_IDS)
    assert all(record["stage"] == "smoke-public-subtitles" for record in records)


def test_smoke_rejects_nonnew_root_invalid_or_duplicate_ids_without_calls(tmp_path: Path) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _FakeSubtitleAdapter()
    smoke = _smoke(metadata, subtitles)
    root = tmp_path / "already-exists"
    root.mkdir()

    assert main(_args(root, "video001"), smoke_runner=smoke) is ExitCode.USAGE_OR_CONFIGURATION
    assert main(_args(tmp_path / "bad", "bad"), smoke_runner=smoke) is ExitCode.USAGE_OR_CONFIGURATION
    assert main(_args(tmp_path / "duplicate", "video001", "video001"), smoke_runner=smoke) is ExitCode.USAGE_OR_CONFIGURATION
    assert main(_args(tmp_path / "too-many", "video001", "video002", "video003", "video004"), smoke_runner=smoke) is ExitCode.USAGE_OR_CONFIGURATION
    assert metadata.calls == []
    assert subtitles.enumerate_calls == []
    assert not (tmp_path / "bad").exists()
    assert not (tmp_path / "duplicate").exists()
    assert not (tmp_path / "too-many").exists()


def test_smoke_rejects_global_configuration_inputs_before_initialization(tmp_path: Path) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _FakeSubtitleAdapter()
    smoke = _smoke(metadata, subtitles)
    configuration_options = ("--project-root", "--settings", "--channels")

    for option in configuration_options:
        for option_form in (option, f"{option}={tmp_path / 'configuration'}"):
            for position in ("before", "after"):
                root = tmp_path / f"{option.removeprefix('--')}-{position}-{option_form.startswith(option + '=')}"
                arguments = _args(root, "video001")
                configuration_input = (
                    [option_form, str(tmp_path / "configuration")]
                    if option_form == option
                    else [option_form]
                )
                if position == "before":
                    arguments = [*configuration_input, *arguments]
                else:
                    arguments.extend(configuration_input)

                assert main(arguments, smoke_runner=smoke) is ExitCode.USAGE_OR_CONFIGURATION
                assert not root.exists()

    assert metadata.calls == []
    assert subtitles.enumerate_calls == []


def test_smoke_records_failure_without_retrying_or_persisting_body(tmp_path: Path) -> None:
    metadata = _FakeMetadataProvider(fail_for="video002")
    subtitles = _FakeSubtitleAdapter()
    root = tmp_path / "smoke-root"

    exit_code = main(_args(root, *VIDEO_IDS), smoke_runner=_smoke(metadata, subtitles))

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert metadata.calls == list(VIDEO_IDS)
    assert subtitles.enumerate_calls == ["video001"]
    assert len(subtitles.read_calls) == 1
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    assert "sensitive" not in log_text
    assert SUBTITLE_BODY.decode() not in log_text
    failed_record = next(
        json.loads(line)
        for line in log_text.splitlines()
        if json.loads(line)["event"] == "smoke.target.failed"
    )
    assert failed_record["error_code"] == "PROVIDER_UNAVAILABLE"
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=0 read_track_calls=0"
    )
