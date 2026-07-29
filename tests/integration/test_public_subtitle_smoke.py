"""Offline integration tests for the restricted public subtitle smoke entry."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from youtube_intel import public_subtitle_smoke as smoke_mod
from youtube_intel.cli import CommandOutcome, ExitCode, main
from youtube_intel.domain import (
    AppError,
    Availability,
    DiagnosticEntry,
    ErrorCode,
    LiveStatus,
    ProviderCallMetadata,
    SubtitleFormat,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.providers import subtitles as subtitles_mod
from youtube_intel.public_subtitle_smoke import PublicSubtitleSmoke
from youtube_intel.transcripts import (
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
    TranscriptError,
)

NOW = datetime(2026, 7, 26, tzinfo=UTC)
VIDEO_IDS = ("video001", "video002")
SUBTITLE_BODY = b"private subtitle body must not persist"
_DIRECTORY_CONTRACT_FIELDS = (
    "video_identity_shape",
    "manual_directory_shape",
    "automatic_directory_shape",
    "caption_bucket_shape",
    "track_entry_shape",
    "required_members_shape",
)
_DIRECTORY_CONTRACT_STATE = (
    "string",
    "mapping",
    "mapping",
    "sequence",
    "mapping",
    "missing",
)


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


@dataclass
class _InvalidDirectorySubtitleAdapter(_FakeSubtitleAdapter):
    last_call: ProviderCallMetadata | None = None
    diagnostic_code: str | None = "directory_shape_unsupported_entry"
    directory_origin: object | None = "directory_origin_mapping"
    directory_fingerprint: object | None = "directory_fingerprint_track_entry_not_mapping"
    directory_key_names: object | None = None
    directory_contract_state: object | None = None

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        self.enumerate_calls.append(video_id)
        self.last_call = ProviderCallMetadata(
            provider="fake",
            started_at=NOW,
            finished_at=NOW,
            diagnostics=(
                ()
                if self.diagnostic_code is None
                else (
                    DiagnosticEntry(
                        code=self.diagnostic_code,
                        message=self.diagnostic_code.replace("_", " "),
                    ),
                )
            ),
        )
        error = TranscriptError(
            AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message=ErrorCode.INVALID_RESPONSE.value,
                retryable=False,
                video_id=video_id,
            )
        )
        if self.directory_origin is not None:
            error.directory_origin = self.directory_origin
        error.directory_fingerprint = self.directory_fingerprint
        if self.directory_key_names is not None:
            error.directory_key_names = self.directory_key_names
        if self.directory_contract_state is not None:
            error.directory_contract_state = self.directory_contract_state
        raise error


@dataclass
class _ContractStateDirectorySubtitleAdapter(_InvalidDirectorySubtitleAdapter):
    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        self.enumerate_calls.append(video_id)
        self.last_call = ProviderCallMetadata(
            provider="fake",
            started_at=NOW,
            finished_at=NOW,
            diagnostics=(
                DiagnosticEntry(
                    code="directory_shape_unsupported_entry",
                    message="directory shape unsupported entry",
                ),
            ),
        )
        contract_state = subtitles_mod._directory_contract_state(
            subtitles_mod._VideoIdentityShape.STRING,
            subtitles_mod._DirectoryShape.MAPPING,
            subtitles_mod._DirectoryShape.MAPPING,
            subtitles_mod._CaptionBucketShape.SEQUENCE,
            subtitles_mod._TrackEntryShape.MAPPING,
            subtitles_mod._RequiredMembersShape.MISSING,
        )
        raise subtitles_mod._directory_structure_error(
            subtitles_mod._DirectoryStructureState.REQUIRED_FIELD_MISSING,
            "directory_shape_unsupported_entry",
            ErrorCode.INVALID_RESPONSE.value,
            video_id=video_id,
            contract_state=contract_state,
        )


@dataclass
class _InvalidBodySubtitleAdapter(_FakeSubtitleAdapter):
    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        self.read_calls.append(track)
        error = TranscriptError(
            AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message=ErrorCode.INVALID_RESPONSE.value,
                retryable=False,
                video_id="video001",
            )
        )
        error.directory_origin = "directory_origin_mapping"
        error.directory_fingerprint = "directory_fingerprint_track_entry_not_mapping"
        error.directory_contract_state = _DIRECTORY_CONTRACT_STATE
        raise error


@dataclass
class _ContentUnavailableSubtitleAdapter(_FakeSubtitleAdapter):
    content_error: Exception | None = None

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        self.enumerate_calls.append(video_id)
        error: Exception = TranscriptError(
            AppError(
                code=ErrorCode.CONTENT_UNAVAILABLE,
                message=ErrorCode.CONTENT_UNAVAILABLE.value,
                retryable=False,
                video_id=video_id,
            )
        )
        raise self.content_error if self.content_error is not None else error


@dataclass
class _FakeOperations:
    calls: list[tuple[str, object]] = field(default_factory=list)

    def check(self, *, channel: str | None, limit: int | None) -> CommandOutcome:
        self.calls.append(("check", (channel, limit)))
        return CommandOutcome()

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome:
        self.calls.append(("process", (video, resume)))
        return CommandOutcome()

    def retry(self, *, video: str | None, failed_only: bool) -> CommandOutcome:
        self.calls.append(("retry", (video, failed_only)))
        return CommandOutcome()

    def weekly(self, *, week: str | None) -> CommandOutcome:
        self.calls.append(("weekly", week))
        return CommandOutcome()


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


def _args(root: Path, *video_ids: str, directory_only: bool = False) -> list[str]:
    arguments = [
        "smoke-public-subtitles",
        "--temporary-root",
        str(root),
        *[part for video_id in video_ids for part in ("--video-id", video_id)],
    ]
    if directory_only:
        arguments.append("--directory-only")
    return arguments


def _project(root: Path) -> Path:
    (root / "config").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "vault").mkdir()
    (root / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: channel-a\n",
        encoding="utf-8",
    )
    (root / "config" / "settings.yaml").write_text(
        """\
general:
  transcript_languages: [en]
local_scoring:
  model: local-model
  base_url: http://127.0.0.1:11434
  expected_model_digest: sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
storage:
  data_dir: data
  logs_dir: logs
  templates_dir: templates
  vault_root: PLACEHOLDER
  vault_subdir: YouTube Intel
""".replace("PLACEHOLDER", str(root / "vault")),
        encoding="utf-8",
    )
    return root


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


def test_directory_only_isolated_to_new_root_without_reading_track_bodies(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _FakeSubtitleAdapter()
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, *VIDEO_IDS, directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.OK
    assert metadata.calls == list(VIDEO_IDS)
    assert subtitles.enumerate_calls == list(VIDEO_IDS)
    assert subtitles.read_calls == []
    summaries = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert summaries == [
        {
            "video_id": video_id,
            "metadata": 1,
            "enumerate": 1,
            "read": 0,
            "error_code": "OK",
        }
        for video_id in VIDEO_IDS
    ]
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    assert "read_track_calls=0" in log_text
    assert SUBTITLE_BODY.decode() not in log_text


def test_default_smoke_emits_only_safe_summary_after_one_body_read(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _FakeSubtitleAdapter()
    root = tmp_path / "smoke-root"

    exit_code = main(_args(root, "video001"), smoke_runner=_smoke(metadata, subtitles))

    assert exit_code is ExitCode.OK
    assert len(subtitles.read_calls) == 1
    output = capsys.readouterr()
    assert [json.loads(line) for line in output.out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 1,
            "error_code": "OK",
        }
    ]
    assert output.err == ""
    for forbidden in (
        "https://example.invalid",
        "temporary-url",
        SUBTITLE_BODY.decode(),
        "Title",
        "English",
        str(root),
        "Cookie",
        "token",
        "payload",
    ):
        assert forbidden not in output.out


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


def test_directory_only_rejects_global_configuration_before_initialization(
    tmp_path: Path,
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _FakeSubtitleAdapter()
    root = tmp_path / "smoke-root"

    exit_code = main(
        [
            "--project-root",
            str(tmp_path / "configuration"),
            *_args(root, "video001", directory_only=True),
        ],
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.USAGE_OR_CONFIGURATION
    assert metadata.calls == []
    assert subtitles.enumerate_calls == []
    assert not root.exists()


def test_check_treats_smoke_name_as_an_option_value(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")
    operations = _FakeOperations()

    exit_code = main(
        [
            "--project-root",
            str(project),
            "check",
            "--channel",
            "smoke-public-subtitles",
        ],
        operations=operations,
    )

    assert exit_code is ExitCode.OK
    assert operations.calls == [("check", ("smoke-public-subtitles", None))]


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


def test_smoke_appends_only_fixed_directory_diagnostic_before_body_read(
    tmp_path: Path,
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidDirectorySubtitleAdapter(
        directory_key_names=("Alpha", "Bravo_2"),
        directory_contract_state=_DIRECTORY_CONTRACT_STATE,
    )
    root = tmp_path / "smoke-root"

    exit_code = main(_args(root, "video001"), smoke_runner=_smoke(metadata, subtitles))

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert metadata.calls == ["video001"]
    assert subtitles.enumerate_calls == ["video001"]
    assert subtitles.read_calls == []
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    failed_record = next(
        json.loads(line)
        for line in log_text.splitlines()
        if json.loads(line)["event"] == "smoke.target.failed"
    )
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=0 "
        "directory_diagnostic=directory_shape_unsupported_entry "
        "directory_origin=directory_origin_mapping "
        "directory_fingerprint=directory_fingerprint_track_entry_not_mapping"
    )
    assert set(failed_record) == {
        "timestamp",
        "level",
        "event",
        "run_id",
        "stage",
        "safe_message",
        "video_id",
        "error_code",
        "duration_ms",
    }
    for forbidden in ("message=", "error="):
        assert forbidden not in log_text
    assert "directory_key_names" not in failed_record["safe_message"]
    assert all(
        field not in failed_record["safe_message"]
        for field in _DIRECTORY_CONTRACT_FIELDS
    )
    assert "smoke.target.directory_contract_state" not in log_text


def test_directory_only_appends_only_fixed_directory_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidDirectorySubtitleAdapter(directory_key_names=("Alpha", "Bravo_2"))
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, "video001", directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert metadata.calls == ["video001"]
    assert subtitles.enumerate_calls == ["video001"]
    assert subtitles.read_calls == []
    output = capsys.readouterr()
    assert [json.loads(line) for line in output.out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 0,
            "error_code": "INVALID_RESPONSE",
            "directory_diagnostic": "directory_shape_unsupported_entry",
            "directory_origin": "directory_origin_mapping",
            "directory_fingerprint": "directory_fingerprint_track_entry_not_mapping",
        }
    ]
    assert output.err == ""
    for forbidden in ("message=", "error=", str(root)):
        assert forbidden not in output.out
    records = [
        json.loads(line)
        for line in (root / "logs" / "smoke-public-subtitles.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    failed_record = next(record for record in records if record["event"] == "smoke.target.failed")
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=0 "
        "directory_diagnostic=directory_shape_unsupported_entry "
        "directory_origin=directory_origin_mapping "
        "directory_fingerprint=directory_fingerprint_track_entry_not_mapping"
    )
    assert "directory_key_names" not in failed_record["safe_message"]


def test_directory_only_emits_frozen_directory_contract_state_matrix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _ContractStateDirectorySubtitleAdapter()
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, VIDEO_IDS[0], directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    summary = json.loads(capsys.readouterr().out)
    assert tuple(summary)[-6:] == _DIRECTORY_CONTRACT_FIELDS
    assert tuple(summary[field] for field in _DIRECTORY_CONTRACT_FIELDS) == (
        _DIRECTORY_CONTRACT_STATE
    )
    contract_record = next(
        json.loads(line)
        for line in (root / "logs" / "smoke-public-subtitles.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if json.loads(line)["event"] == "smoke.target.directory_contract_state"
    )
    assert contract_record["safe_message"] == (
        "video_identity_shape=string manual_directory_shape=mapping "
        "automatic_directory_shape=mapping caption_bucket_shape=sequence "
        "track_entry_shape=mapping required_members_shape=missing"
    )
    assert set(contract_record) == {
        "timestamp",
        "level",
        "event",
        "run_id",
        "stage",
        "safe_message",
        "video_id",
        "error_code",
        "duration_ms",
    }


@pytest.mark.parametrize(
    (
        "directory_only",
        "metadata_calls",
        "enumerate_calls",
        "read_calls",
        "code",
        "origin",
    ),
    [
        (False, 1, 1, 0, ErrorCode.INVALID_RESPONSE, "directory_origin_mapping"),
        (True, 0, 1, 0, ErrorCode.INVALID_RESPONSE, "directory_origin_mapping"),
        (True, 1, 0, 0, ErrorCode.INVALID_RESPONSE, "directory_origin_mapping"),
        (True, 1, 1, 1, ErrorCode.INVALID_RESPONSE, "directory_origin_mapping"),
        (True, 1, 1, 0, ErrorCode.CONTENT_UNAVAILABLE, "directory_origin_mapping"),
        (True, 1, 1, 0, ErrorCode.INVALID_RESPONSE, "directory_origin_unknown"),
    ],
)
def test_directory_contract_state_requires_every_frozen_output_gate(
    directory_only: bool,
    metadata_calls: int,
    enumerate_calls: int,
    read_calls: int,
    code: ErrorCode,
    origin: str,
) -> None:
    error = TranscriptError(
        AppError(
            code=code,
            message=code.value,
            retryable=False,
        )
    )
    error.directory_origin = origin
    error.directory_contract_state = _DIRECTORY_CONTRACT_STATE

    assert smoke_mod._directory_contract_state(
        error,
        directory_only=directory_only,
        metadata_calls=metadata_calls,
        enumerate_calls=enumerate_calls,
        read_calls=read_calls,
    ) is None


def test_directory_contract_state_rejects_untrusted_internal_state() -> None:
    error = TranscriptError(
        AppError(
            code=ErrorCode.INVALID_RESPONSE,
            message=ErrorCode.INVALID_RESPONSE.value,
            retryable=False,
        )
    )
    error.directory_origin = "directory_origin_mapping"
    error.directory_contract_state = object()

    assert smoke_mod._directory_contract_state(
        error,
        directory_only=True,
        metadata_calls=1,
        enumerate_calls=1,
        read_calls=0,
    ) is None


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (
            "VIDEO_UNAVAILABLE",
            "content_availability_video_unavailable",
        ),
        (
            "ENVIRONMENT_RESTRICTED",
            "content_availability_environment_restricted",
        ),
        (
            "EXTRACTOR_COMPATIBILITY",
            "content_availability_extractor_compatibility",
        ),
        (None, "content_availability_unknown"),
    ],
)
def test_directory_only_emits_only_closed_content_availability_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    state: str | None,
    expected: str,
) -> None:
    metadata = _FakeMetadataProvider()
    content_error = (
        None
        if state is None
        else subtitles_mod._content_unavailable_error(
            getattr(subtitles_mod._ContentAvailabilityState, state),
            video_id="video001",
        )
    )
    subtitles = _ContentUnavailableSubtitleAdapter(content_error=content_error)
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, "video001", directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert subtitles.enumerate_calls == ["video001"]
    assert subtitles.read_calls == []
    assert [json.loads(line) for line in capsys.readouterr().out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 0,
            "error_code": "CONTENT_UNAVAILABLE",
            "content_availability": expected,
        }
    ]
    failed_record = next(
        json.loads(line)
        for line in (root / "logs" / "smoke-public-subtitles.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if json.loads(line)["event"] == "smoke.target.failed"
    )
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=0 "
        f"content_availability={expected}"
    )
    assert set(failed_record) == {
        "timestamp",
        "level",
        "event",
        "run_id",
        "stage",
        "safe_message",
        "video_id",
        "error_code",
        "duration_ms",
    }


def test_directory_only_uses_exact_unknown_shape_fallback_without_leaking(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidDirectorySubtitleAdapter(
        diagnostic_code=None,
        directory_origin=object(),
        directory_fingerprint=object(),
    )
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, "video001", directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert metadata.calls == ["video001"]
    assert subtitles.enumerate_calls == ["video001"]
    assert subtitles.read_calls == []
    output = capsys.readouterr()
    assert [json.loads(line) for line in output.out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 0,
            "error_code": "INVALID_RESPONSE",
            "directory_diagnostic": "directory_shape_unknown",
            "directory_origin": "directory_origin_unknown",
            "directory_fingerprint": "directory_fingerprint_unknown",
        }
    ]
    records = [
        json.loads(line)
        for line in (root / "logs" / "smoke-public-subtitles.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    failed_record = next(record for record in records if record["event"] == "smoke.target.failed")
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=0 "
        "directory_diagnostic=directory_shape_unknown "
        "directory_origin=directory_origin_unknown "
        "directory_fingerprint=directory_fingerprint_unknown"
    )
    for forbidden in (
        "directory_unknown_invalid_response",
        "message=",
        "error=",
        str(root),
    ):
        assert forbidden not in output.out
        assert forbidden not in (root / "logs" / "smoke-public-subtitles.jsonl").read_text(
            encoding="utf-8"
        )


def test_directory_only_can_omit_a_fingerprint_when_only_the_origin_is_safe(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidDirectorySubtitleAdapter(
        directory_origin="directory_origin_extractor",
        directory_fingerprint=None,
        directory_key_names=("Alpha", "Bravo_2"),
    )
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, "video001", directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert [json.loads(line) for line in capsys.readouterr().out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 0,
            "error_code": "INVALID_RESPONSE",
            "directory_diagnostic": "directory_shape_unsupported_entry",
            "directory_origin": "directory_origin_extractor",
        }
    ]
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    failed_record = next(
        json.loads(line)
        for line in log_text.splitlines()
        if json.loads(line)["event"] == "smoke.target.failed"
    )
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=0 "
        "directory_diagnostic=directory_shape_unsupported_entry "
        "directory_origin=directory_origin_extractor"
    )
    assert "directory_fingerprint" not in failed_record["safe_message"]
    assert "directory_key_names" not in failed_record["safe_message"]


def test_directory_only_emits_restricted_safe_directory_key_names(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidDirectorySubtitleAdapter(
        directory_fingerprint="directory_fingerprint_unknown",
        directory_key_names=("Alpha", "Bravo_2"),
    )
    root = tmp_path / "smoke-root"

    exit_code = main(
        _args(root, "video001", directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    output = capsys.readouterr()
    assert [json.loads(line) for line in output.out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 0,
            "error_code": "INVALID_RESPONSE",
            "directory_diagnostic": "directory_shape_unsupported_entry",
            "directory_origin": "directory_origin_mapping",
            "directory_fingerprint": "directory_fingerprint_unknown",
            "directory_key_names": ["Alpha", "Bravo_2"],
        }
    ]
    assert output.err == ""
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    failed_record = next(
        json.loads(line)
        for line in log_text.splitlines()
        if json.loads(line)["event"] == "smoke.target.failed"
    )
    assert failed_record["safe_message"].endswith(
        'directory_key_names=["Alpha","Bravo_2"]'
    )
    for forbidden in ("message=", "error=", str(root)):
        assert forbidden not in output.out
        assert forbidden not in output.err
        assert forbidden not in log_text


@pytest.mark.parametrize(
    "directory_key_names",
    [
        object(),
        tuple(f"Key{index:02d}" for index in range(17)),
        ("Bravo_2", "Alpha"),
    ],
)
def test_directory_only_omits_untrusted_or_noncanonical_key_name_sets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    directory_key_names: object,
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidDirectorySubtitleAdapter(
        directory_fingerprint="directory_fingerprint_unknown",
        directory_key_names=directory_key_names,
    )
    root = tmp_path / "smoke-root"

    assert main(
        _args(root, "video001", directory_only=True),
        smoke_runner=_smoke(metadata, subtitles),
    ) is ExitCode.EXECUTION_FAILED
    summary = json.loads(capsys.readouterr().out)
    assert "directory_key_names" not in summary
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    assert "directory_key_names=" not in log_text


def test_body_invalid_response_never_emits_directory_origin_or_fingerprint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    metadata = _FakeMetadataProvider()
    subtitles = _InvalidBodySubtitleAdapter()
    root = tmp_path / "smoke-root"

    exit_code = main(_args(root, "video001"), smoke_runner=_smoke(metadata, subtitles))

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert metadata.calls == ["video001"]
    assert subtitles.enumerate_calls == ["video001"]
    assert len(subtitles.read_calls) == 1
    assert [json.loads(line) for line in capsys.readouterr().out.splitlines()] == [
        {
            "video_id": "video001",
            "metadata": 1,
            "enumerate": 1,
            "read": 1,
            "error_code": "INVALID_RESPONSE",
        }
    ]
    log_text = (root / "logs" / "smoke-public-subtitles.jsonl").read_text(encoding="utf-8")
    failed_record = next(
        json.loads(line)
        for line in log_text.splitlines()
        if json.loads(line)["event"] == "smoke.target.failed"
    )
    assert failed_record["safe_message"] == (
        "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=1"
    )
    for forbidden in (
        "directory_origin",
        "directory_fingerprint",
        *_DIRECTORY_CONTRACT_FIELDS,
        "message=",
        "error=",
    ):
        assert forbidden not in log_text
    assert "smoke.target.directory_contract_state" not in log_text
