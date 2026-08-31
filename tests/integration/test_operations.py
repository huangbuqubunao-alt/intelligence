"""Offline integration tests for TASK-012 command operations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from youtube_intel import cli
from youtube_intel.cli import CommandOutcome, ExitCode, main
from youtube_intel.logging import JsonlLogger
from youtube_intel.state import SQLiteStateRepository


@dataclass
class FakeOperations:
    calls: list[tuple[str, object]] = field(default_factory=list)
    outcome: CommandOutcome = field(default_factory=CommandOutcome)

    def check(self, *, channel: str | None, limit: int | None) -> CommandOutcome:
        self.calls.append(("check", (channel, limit)))
        return self.outcome

    def process(self, *, video: str | None, resume: bool) -> CommandOutcome:
        self.calls.append(("process", (video, resume)))
        return self.outcome

    def retry(self, *, video: str | None, failed_only: bool) -> CommandOutcome:
        self.calls.append(("retry", (video, failed_only)))
        return self.outcome

    def weekly(self, *, week: str | None) -> CommandOutcome:
        self.calls.append(("weekly", week))
        return self.outcome


def _project(tmp_path: Path, *, create_vault: bool = True) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    if create_vault:
        (tmp_path / "vault").mkdir()
    (tmp_path / "config" / "channels.yaml").write_text(
        "channels:\n  - channel_id: channel-a\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "settings.yaml").write_text(
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
""".replace("PLACEHOLDER", str(tmp_path / "vault")),
        encoding="utf-8",
    )
    return tmp_path


def _args(project: Path, *command: str) -> list[str]:
    return ["--project-root", str(project), *command]


def test_commands_dispatch_with_uuid4_jsonl_and_partial_failure(tmp_path: Path) -> None:
    project = _project(tmp_path)
    operations = FakeOperations(outcome=CommandOutcome(attempted=2, failed=1))

    exit_code = main(
        _args(project, "check", "--channel", "channel-a", "--limit", "2"),
        operations=operations,
    )

    assert exit_code is ExitCode.EXECUTION_FAILED
    assert operations.calls == [("check", ("channel-a", 2))]
    records = [
        json.loads(line)
        for line in (project / "logs" / "operations.jsonl").read_text().splitlines()
    ]
    assert [record["event"] for record in records] == ["command.started", "command.failed"]
    assert {record["run_id"] for record in records} == {records[0]["run_id"]}
    assert UUID(records[0]["run_id"]).version == 4
    assert all(
        {"timestamp", "level", "event", "run_id", "stage", "safe_message"}
        <= record.keys()
        for record in records
    )
    assert all(str(project) not in json.dumps(record) for record in records)


def test_logging_failure_is_visible_and_prevents_business_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    operations = FakeOperations()

    def fail_log(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise OSError("private path")

    monkeypatch.setattr(JsonlLogger, "emit", fail_log)

    assert main(_args(project, "check"), operations=operations) is ExitCode.LOCAL_RESOURCE
    assert operations.calls == []
    output = capsys.readouterr()
    assert "operations log is unavailable" in output.err
    assert "private path" not in output.err


def test_process_retry_and_weekly_preserve_arguments(tmp_path: Path) -> None:
    project = _project(tmp_path)
    operations = FakeOperations()

    assert main(_args(project, "process", "--video", "video-a", "--resume"), operations=operations) is ExitCode.OK
    assert main(_args(project, "retry", "--failed-only"), operations=operations) is ExitCode.OK
    assert main(_args(project, "weekly", "--week", "2026-W30"), operations=operations) is ExitCode.OK

    assert operations.calls == [
        ("process", ("video-a", True)),
        ("retry", (None, True)),
        ("weekly", "2026-W30"),
    ]


def test_usage_and_configuration_fail_with_exit_code_two(tmp_path: Path) -> None:
    project = _project(tmp_path)

    assert main(_args(project, "check", "--limit", "0")) is ExitCode.USAGE_OR_CONFIGURATION
    (project / "config" / "settings.yaml").write_text("not: valid: yaml", encoding="utf-8")
    assert main(_args(project, "doctor")) is ExitCode.USAGE_OR_CONFIGURATION


def test_default_operations_use_production_composition_and_report_provider_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)

    assert main(_args(project, "check")) is ExitCode.EXECUTION_FAILED
    assert "channel(s) failed" in capsys.readouterr().err


def test_non_smoke_commands_reject_directory_only_before_constructing_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_runner() -> None:
        raise AssertionError("smoke runner must not be constructed")

    monkeypatch.setattr(cli, "PublicSubtitleSmoke", forbidden_runner)

    for command in ("check", "process", "retry", "weekly", "doctor"):
        assert main([command, "--directory-only"]) is ExitCode.USAGE_OR_CONFIGURATION


def test_doctor_only_reads_initialized_temporary_resources(tmp_path: Path) -> None:
    project = _project(tmp_path)
    database = project / "data" / "state.sqlite"
    SQLiteStateRepository(database).initialize(now=datetime(2026, 7, 23, tzinfo=UTC))
    before = database.read_bytes()
    operations = FakeOperations()

    exit_code = main(_args(project, "doctor"), operations=operations)

    assert exit_code is ExitCode.LOCAL_RESOURCE
    assert database.read_bytes() == before
    assert operations.calls == []
    assert not (project / "logs").exists()
    assert not (project / "vault" / "YouTube Intel").exists()


def test_doctor_reports_missing_database_as_local_resource(tmp_path: Path) -> None:
    project = _project(tmp_path)

    assert main(_args(project, "doctor")) is ExitCode.LOCAL_RESOURCE


def test_doctor_reports_missing_explicit_cloud_tokenizer_without_path_leakage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)
    settings = project / "config" / "settings.yaml"
    settings.write_text(
        settings.read_text(encoding="utf-8")
        + "\ncloud:\n  enabled: true\n  provider: openai\n  model: gpt-4.1-mini\n"
        + "  api_key_env: OPENAI_API_KEY\n",
        encoding="utf-8",
    )

    assert main(_args(project, "doctor")) is ExitCode.LOCAL_RESOURCE

    output = capsys.readouterr()
    assert "Cloud tokenizer" in output.out
    assert "missing or invalid" in output.out
    assert str(project) not in output.out


def test_doctor_unexpected_failure_is_visible_and_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path)

    def fail_doctor(config: object, project_root: Path) -> None:
        del config, project_root
        raise RuntimeError("internal detail must not be shown")

    monkeypatch.setattr("youtube_intel.runtime.doctor", fail_doctor)

    assert main(_args(project, "doctor")) is ExitCode.EXECUTION_FAILED
    output = capsys.readouterr()
    assert "failed safely" in output.err
    assert "internal detail" not in output.err


def test_doctor_with_missing_vault_does_not_create_local_paths(tmp_path: Path) -> None:
    project = _project(tmp_path, create_vault=False)
    database = project / "data" / "state.sqlite"
    SQLiteStateRepository(database).initialize(now=datetime(2026, 7, 23, tzinfo=UTC))
    operations = FakeOperations()

    assert main(_args(project, "doctor"), operations=operations) is ExitCode.LOCAL_RESOURCE
    assert operations.calls == []
    assert not (project / "logs").exists()
    assert not (project / "vault").exists()


def test_jsonl_logger_redacts_paths_and_secret_shaped_values(tmp_path: Path) -> None:
    path = tmp_path / "operations.jsonl"
    JsonlLogger(path).emit(
        level="ERROR",
        event="command.failed",
        run_id="123e4567-e89b-42d3-a456-426614174000",
        stage="process",
        safe_message="api_key=/Users/example/secret-token failed",
    )

    record = json.loads(path.read_text())
    assert record["safe_message"] == "[REDACTED] failed"
