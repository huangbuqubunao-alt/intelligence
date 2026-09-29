"""Contract tests for configuration and domain models (TASK-002)."""

from __future__ import annotations

import ast
import importlib
import importlib.metadata
import inspect
import json
import re
import socket
import subprocess
import sys
import textwrap
import tomllib
import traceback
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from youtube_intel import analysis as analysis_mod
from youtube_intel import config as config_mod
from youtube_intel import domain as domain_mod
from youtube_intel import transcripts as transcripts_mod
from youtube_intel.config import (
    ChannelConfig,
    CloudSettings,
    ConfigError,
    ExecutionSettings,
    LocalScoringSettings,
    RetrySettings,
    SettingsOverrides,
    StorageSettings,
    ThresholdSettings,
    TimeoutSettings,
    TranscriptionSettings,
    WeeklySettings,
    load_app_config,
    load_channels,
    load_settings,
)
from youtube_intel.domain import (
    JOB_TRANSITIONS,
    PIPELINE_TRANSITIONS,
    SCORE_DIMENSION_NAMES,
    AnalysisCompleted,
    AnalysisContent,
    AnalysisInput,
    AnalysisOutcome,
    AnalysisPayload,
    AnalysisPoint,
    AnalysisResult,
    AnalysisSkipped,
    AnalysisSkipReason,
    AppError,
    Availability,
    ChannelRef,
    DiagnosticEntry,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    EvidenceExcerpt,
    EvidenceSource,
    InvalidTransitionError,
    JobStatus,
    KnowledgeSink,
    LiveStatus,
    MetadataProvider,
    NotAvailable,
    NotAvailableReason,
    NoteKind,
    NoteRef,
    PipelineStatus,
    PointKind,
    ProcessingStage,
    ProviderCallMetadata,
    ScoreDimensions,
    ScoreResult,
    ScoringDecision,
    ScoringInput,
    ScoringOutcome,
    ScoringProvider,
    SourceProvider,
    SubtitleFormat,
    SummaryProvider,
    TranscriptArtifact,
    TranscriptFetchResult,
    TranscriptionReason,
    TranscriptionRequired,
    TranscriptProvider,
    TranscriptQualityFlag,
    TranscriptReady,
    TranscriptSample,
    TranscriptSourceType,
    TrustedEvidenceCandidateView,
    TrustedEvidenceOffer,
    VideoMetadata,
    WeeklyReportInput,
    WeeklyReportItem,
    can_transition_job,
    can_transition_pipeline,
    pipeline_after_job_failure,
    transition_job,
    transition_pipeline,
)
from youtube_intel.providers import subtitles as subtitles_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANNELS_EXAMPLE = REPO_ROOT / "config" / "channels.example.yaml"
SETTINGS_EXAMPLE = REPO_ROOT / "config" / "settings.example.yaml"
NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
TRANSCRIPT_HASH = "a" * 64
MODEL_DIGEST = "sha256:500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def _minimal_settings_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "general": {
            "timezone": "Asia/Shanghai",
            "output_language": "zh-CN",
            "transcript_languages": ["zh", "en"],
        },
        "local_scoring": {
            "model": "qwen3:8b",
            "expected_model_digest": MODEL_DIGEST,
        },
        "storage": {
            "vault_root": "/tmp/yia-test-vault",
            "vault_subdir": "YouTube Intel",
        },
    }
    base.update(overrides)
    return base


def _write_settings(tmp_path: Path, data: dict[str, object] | None = None) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump(data or _minimal_settings_dict()), encoding="utf-8")
    return path


def _write_channels(tmp_path: Path, channels: list[dict[str, object]] | None = None) -> Path:
    path = tmp_path / "channels.yaml"
    payload = {
        "channels": channels
        or [
            {"channel_id": "UC_B", "priority": 50},
            {"channel_id": "UC_A", "priority": 50},
            {"channel_id": "UC_HIGH", "priority": 90},
        ]
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _video(*, video_id: str = "vid1") -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        channel_id="UC_x",
        channel_name="Example",
        title="Title",
        description="",
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=NOW,
        duration_seconds=600,
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _call() -> ProviderCallMetadata:
    return ProviderCallMetadata(
        provider="test",
        started_at=NOW,
        finished_at=NOW,
    )


def _score(**kwargs: object) -> ScoreResult:
    data: dict[str, object] = {
        "schema_version": "1",
        "score": 8.0,
        "reason": "This provides solid product insight.",
        "topics": ("ai", "product"),
        "should_summarize": True,
        "provider": "ollama",
        "model": "qwen2.5:14b",
        "prompt_version": "v1",
        "request_hash": "abc",
        "output_language": "en",
    }
    data.update(kwargs)
    return ScoreResult.model_validate(data)


def _sample(**kwargs: object) -> TranscriptSample:
    data: dict[str, object] = {
        "head": "head",
        "body": "body",
        "tail": "tail",
        "selected_char_count": 12,
        "source_content_hash": TRANSCRIPT_HASH,
        "sampling_version": "sampling-v1",
    }
    data.update(kwargs)
    return TranscriptSample.model_validate(data)


def _analysis_payload(**kwargs: object) -> AnalysisPayload:
    data: dict[str, object] = {
        "video_id": "vid1",
        "title": "Public title",
        "channel_name": "Public channel",
        "published_at": NOW,
        "duration_seconds": 600,
        "default_language": "en",
        "description": "Public description",
        "transcript_language": "en",
        "output_language": "zh-CN",
        "transcript_sample": "head body tail",
    }
    data.update(kwargs)
    return AnalysisPayload.model_validate(data)


# ---------------------------------------------------------------------------
# Example config and defaults / priority
# ---------------------------------------------------------------------------


def test_example_configs_load() -> None:
    channels = load_channels(CHANNELS_EXAMPLE)
    settings = load_settings(SETTINGS_EXAMPLE)
    assert len(channels) == 3
    assert channels[0].priority >= channels[1].priority
    assert settings.general.timezone == "Asia/Shanghai"
    assert settings.execution.worker_concurrency == 1
    assert settings.retry.max_attempts == 3
    assert settings.retry.base_delay_seconds == 2
    assert settings.retry.max_delay_seconds == 60
    assert settings.retry.jitter_ratio == 0.2
    assert settings.timeouts.http_seconds == 30
    assert settings.timeouts.local_model_seconds == 300
    assert settings.timeouts.cloud_model_seconds == 120
    assert settings.local_scoring.temperature == 0.0
    assert settings.local_scoring.max_output_tokens == 1200
    assert settings.local_scoring.max_transcript_chars == 30000
    assert settings.local_scoring.max_description_chars == 4000
    assert settings.local_scoring.expected_model_digest == MODEL_DIGEST
    assert settings.transcription.model_revision == "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"
    assert settings.transcription.parameter_policy_version == "mlx-whisper-v1"
    assert settings.transcription.min_free_disk_gib == 8
    assert settings.transcription.min_available_memory_gib == 6
    assert settings.transcription.max_audio_bytes == 2_000_000_000
    assert settings.cloud.enabled is False
    assert settings.cloud.api_key_env == "OPENAI_API_KEY"
    assert settings.cloud.max_calls_per_run == 5
    assert settings.cloud.max_input_tokens_per_video == 30000
    assert settings.thresholds.summary_score == 7.0
    assert settings.weekly.top_n == 10


def test_defaults_yaml_overrides_priority(tmp_path: Path) -> None:
    settings_path = _write_settings(
        tmp_path,
        _minimal_settings_dict(
            thresholds={"summary_score": 6.5},
            weekly={"top_n": 5},
        ),
    )
    base = load_settings(settings_path)
    assert base.thresholds.summary_score == 6.5
    assert base.weekly.top_n == 5
    # defaults for retry untouched by YAML
    assert base.retry.max_attempts == 3

    overrides = SettingsOverrides(
        thresholds=ThresholdSettings(summary_score=9.0),
        weekly=WeeklySettings(top_n=20),
    )
    merged = load_settings(settings_path, overrides=overrides)
    assert merged.thresholds.summary_score == 9.0
    assert merged.weekly.top_n == 20
    # YAML value still wins over defaults when no override for that section
    assert merged.retry.max_attempts == 3


@pytest.mark.parametrize("output_language", ["fr", "en-US"])
def test_scoring_output_language_fails_during_config_loading(
    tmp_path: Path,
    output_language: str,
) -> None:
    data = _minimal_settings_dict()
    data["general"] = {
        "timezone": "Asia/Shanghai",
        "output_language": output_language,
        "transcript_languages": ["zh", "en"],
    }

    with pytest.raises(ConfigError, match="settings validation failed"):
        load_settings(_write_settings(tmp_path, data))


def test_channel_stable_sort_by_priority_then_id(tmp_path: Path) -> None:
    path = _write_channels(tmp_path)
    channels = load_channels(path)
    assert [c.channel_id for c in channels] == ["UC_HIGH", "UC_A", "UC_B"]


# ---------------------------------------------------------------------------
# Unknown fields, duplicates, timezone, numeric bounds
# ---------------------------------------------------------------------------


def test_unknown_root_and_nested_fields_rejected(tmp_path: Path) -> None:
    bad_root = _write_settings(tmp_path, {**_minimal_settings_dict(), "extra_root": 1})
    with pytest.raises(ConfigError, match="settings validation failed"):
        load_settings(bad_root)

    nested = _minimal_settings_dict()
    nested["general"] = {
        "timezone": "Asia/Shanghai",
        "output_language": "zh-CN",
        "transcript_languages": ["zh"],
        "mystery": True,
    }
    bad_nested = _write_settings(tmp_path, nested)
    with pytest.raises(ConfigError):
        load_settings(bad_nested)


def test_duplicate_channel_and_language_rejected(tmp_path: Path) -> None:
    ch = _write_channels(
        tmp_path,
        [
            {"channel_id": "UC_SAME", "priority": 10},
            {"channel_id": "UC_SAME", "priority": 20},
        ],
    )
    with pytest.raises(ConfigError, match="unique"):
        load_channels(ch)

    data = _minimal_settings_dict()
    data["general"] = {
        "timezone": "Asia/Shanghai",
        "output_language": "zh-CN",
        "transcript_languages": ["zh", "zh"],
    }
    path = _write_settings(tmp_path, data)
    with pytest.raises(ConfigError, match="duplicate"):
        load_settings(path)


def test_invalid_iana_timezone(tmp_path: Path) -> None:
    data = _minimal_settings_dict()
    data["general"] = {
        "timezone": "Not/A_Zone",
        "output_language": "zh-CN",
        "transcript_languages": ["zh"],
    }
    path = _write_settings(tmp_path, data)
    with pytest.raises(ConfigError, match="timezone"):
        load_settings(path)


@pytest.mark.parametrize(
    ("field", "value", "ok"),
    [
        ("priority", 0, True),
        ("priority", 100, True),
        ("priority", -1, False),
        ("priority", 101, False),
    ],
)
def test_priority_bounds(field: str, value: int, ok: bool) -> None:
    if ok:
        ChannelConfig(channel_id="UC_x", priority=value)
    else:
        with pytest.raises(ValidationError):
            ChannelConfig(channel_id="UC_x", priority=value)


@pytest.mark.parametrize(
    ("score", "ok"),
    [(0.0, True), (10.0, True), (-0.1, False), (10.1, False)],
)
def test_summary_score_bounds(score: float, ok: bool) -> None:
    if ok:
        ThresholdSettings(summary_score=score)
    else:
        with pytest.raises(ValidationError):
            ThresholdSettings(summary_score=score)


@pytest.mark.parametrize(
    ("top_n", "ok"),
    [(1, True), (100, True), (0, False), (101, False)],
)
def test_top_n_bounds(top_n: int, ok: bool) -> None:
    if ok:
        WeeklySettings(top_n=top_n)
    else:
        with pytest.raises(ValidationError):
            WeeklySettings(top_n=top_n)


def test_concurrency_must_be_one() -> None:
    ExecutionSettings(worker_concurrency=1)
    with pytest.raises(ValidationError, match="1"):
        ExecutionSettings(worker_concurrency=2)
    with pytest.raises(ValidationError):
        ExecutionSettings(worker_concurrency=0)


# ---------------------------------------------------------------------------
# Retry, timeouts, local scoring, cloud
# ---------------------------------------------------------------------------


def test_retry_defaults_and_constraints() -> None:
    retry = RetrySettings()
    assert retry.max_attempts == 3
    assert retry.base_delay_seconds == 2
    assert retry.max_delay_seconds == 60
    assert retry.jitter_ratio == 0.2
    with pytest.raises(ValidationError):
        RetrySettings(max_attempts=0)
    with pytest.raises(ValidationError):
        RetrySettings(base_delay_seconds=0)
    with pytest.raises(ValidationError):
        RetrySettings(base_delay_seconds=10, max_delay_seconds=5)
    with pytest.raises(ValidationError):
        RetrySettings(jitter_ratio=1.1)


def test_timeouts_must_be_positive() -> None:
    TimeoutSettings()
    with pytest.raises(ValidationError):
        TimeoutSettings(http_seconds=0)
    with pytest.raises(ValidationError):
        TimeoutSettings(local_model_seconds=-1)


def test_local_scoring_defaults_and_bounds() -> None:
    scoring = LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest=MODEL_DIGEST,
    )
    assert scoring.temperature == 0.0
    assert scoring.max_output_tokens == 1200
    assert scoring.max_transcript_chars == 30000
    assert scoring.max_description_chars == 4000
    assert scoring.base_url == "http://127.0.0.1:11434"
    with pytest.raises(ValidationError):
        LocalScoringSettings(
            model="qwen",
            expected_model_digest=MODEL_DIGEST,
            temperature=2.1,
        )
    with pytest.raises(ValidationError):
        LocalScoringSettings(
            model="qwen",
            expected_model_digest=MODEL_DIGEST,
            max_output_tokens=0,
        )

    for base_url in (
        "https://127.0.0.1:11434",
        "http://example.com:11434",
        "http://user@127.0.0.1:11434",
        "http://127.0.0.1:11434/api",
        "http://127.0.0.1:11434?debug=true",
        "http://127.0.0.1:11434#fragment",
    ):
        with pytest.raises(ValidationError):
            LocalScoringSettings(
                model="qwen3:8b",
                expected_model_digest=MODEL_DIGEST,
                base_url=base_url,
            )
    with pytest.raises(ValidationError):
        LocalScoringSettings(
            model="qwen3:8b",
            expected_model_digest="sha256:" + "A" * 64,
        )
    with pytest.raises(ValidationError):
        LocalScoringSettings(
            model="qwen3:8b",
            expected_model_digest=MODEL_DIGEST,
            max_transcript_chars=2,
        )
    with pytest.raises(ValidationError):
        LocalScoringSettings(
            model="qwen3:8b",
            expected_model_digest=MODEL_DIGEST,
            max_description_chars=20_001,
        )


def test_transcription_settings_freeze_revision_decode_policy_and_resources() -> None:
    transcription = TranscriptionSettings()

    assert transcription.model == "mlx-community/whisper-large-v3-turbo"
    assert transcription.model_revision == "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"
    assert transcription.model_weights_bytes == 1_613_977_612
    assert (
        transcription.model_weights_sha256
        == "951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6"
    )
    assert transcription.parameter_policy_version == "mlx-whisper-v1"
    assert transcription.task == "transcribe"
    assert transcription.temperature == 0.0
    assert transcription.compression_ratio_threshold == 2.4
    assert transcription.logprob_threshold == -1.0
    assert transcription.no_speech_threshold == 0.6
    assert transcription.condition_on_previous_text is True
    assert transcription.word_timestamps is False
    assert transcription.initial_prompt is None
    assert transcription.fp16 is True
    assert transcription.min_free_disk_gib == 8
    assert transcription.min_available_memory_gib == 6
    assert transcription.max_audio_bytes == 2_000_000_000

    with pytest.raises(ValidationError):
        TranscriptionSettings(parameter_policy_version="mlx-whisper-v2")
    with pytest.raises(ValidationError):
        TranscriptionSettings(task="translate")
    with pytest.raises(ValidationError, match="decode parameters"):
        TranscriptionSettings(temperature=0.1)
    with pytest.raises(ValidationError):
        TranscriptionSettings(min_free_disk_gib=0)


def test_cloud_enabled_requires_model_and_budget_caps() -> None:
    CloudSettings(enabled=False)
    with pytest.raises(ValidationError, match="cloud.model"):
        CloudSettings(enabled=True, model=None)
    with pytest.raises(ValidationError):
        CloudSettings(enabled=True, model="   ")
    ok = CloudSettings(enabled=True, model="gpt-4.1-mini")
    assert ok.model == "gpt-4.1-mini"
    with pytest.raises(ValidationError):
        CloudSettings(max_calls_per_run=6)
    with pytest.raises(ValidationError):
        CloudSettings(max_input_tokens_per_video=30001)
    with pytest.raises(ValidationError):
        CloudSettings(provider="anthropic")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        CloudSettings(api_key_env="bad-name!")


def test_cloud_settings_freeze_safe_defaults_and_contract_versions() -> None:
    cloud = CloudSettings()

    assert cloud.enabled is False
    assert cloud.provider == "openai"
    assert cloud.model is None
    assert cloud.api_key_env == "OPENAI_API_KEY"
    assert cloud.tokenizer_encoding == "o200k_base"
    assert cloud.max_calls_per_run == 5
    assert cloud.max_local_input_tokens_per_video == 28_000
    assert cloud.max_input_tokens_per_video == 30_000
    assert cloud.max_description_chars == 4_000
    assert cloud.max_output_tokens == 4_000
    assert cloud.prompt_version == "analysis-prompt-v1"
    assert cloud.schema_version == "analysis-result-v1"
    assert cloud.sampling_version == "cloud-token-sampling-v1"
    assert cloud.privacy_version == "cloud-privacy-v1"
    assert TimeoutSettings().cloud_model_seconds == 120


def test_cloud_model_requires_an_explicit_tokenizer_mapping() -> None:
    for model in ("gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"):
        cloud = CloudSettings(enabled=True, model=model)
        assert cloud.tokenizer_encoding == "o200k_base"

    with pytest.raises(ValidationError, match="tokenizer"):
        CloudSettings(enabled=True, model="unknown-model")
    with pytest.raises(ValidationError):
        CloudSettings(
            enabled=True,
            model="gpt-4.1-mini",
            tokenizer_encoding="cl100k_base",
        )


def test_cloud_local_input_budget_cannot_exceed_provider_budget() -> None:
    CloudSettings(
        max_local_input_tokens_per_video=27_999,
        max_input_tokens_per_video=27_999,
    )
    with pytest.raises(ValidationError, match="local input"):
        CloudSettings(
            max_local_input_tokens_per_video=28_000,
            max_input_tokens_per_video=27_999,
        )


def test_cloud_numeric_and_version_boundaries_are_strict() -> None:
    CloudSettings(max_local_input_tokens_per_video=1)
    CloudSettings(max_local_input_tokens_per_video=28_000)
    CloudSettings(max_input_tokens_per_video=28_000)
    CloudSettings(max_input_tokens_per_video=30_000)
    CloudSettings(max_description_chars=0)
    CloudSettings(max_description_chars=20_000)
    CloudSettings(max_output_tokens=256)
    CloudSettings(max_output_tokens=8_000)

    invalid_values = (
        {"max_calls_per_run": 0},
        {"max_calls_per_run": 6},
        {"max_local_input_tokens_per_video": 0},
        {"max_local_input_tokens_per_video": 28_001},
        {"max_input_tokens_per_video": 0},
        {"max_input_tokens_per_video": 30_001},
        {"max_description_chars": -1},
        {"max_description_chars": 20_001},
        {"max_output_tokens": 255},
        {"max_output_tokens": 8_001},
        {"prompt_version": "analysis-prompt-v2"},
        {"schema_version": "analysis-result-v2"},
        {"sampling_version": "cloud-token-sampling-v2"},
        {"privacy_version": "cloud-privacy-v2"},
        {"temperature": 0.0},
    )
    for values in invalid_values:
        with pytest.raises(ValidationError):
            CloudSettings.model_validate(values)


def test_cloud_example_is_complete_and_contains_no_secret_value() -> None:
    raw = yaml.safe_load(SETTINGS_EXAMPLE.read_text(encoding="utf-8"))
    cloud = raw["cloud"]

    assert cloud == {
        "enabled": False,
        "provider": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "tokenizer_encoding": "o200k_base",
        "max_calls_per_run": 5,
        "max_local_input_tokens_per_video": 28_000,
        "max_input_tokens_per_video": 30_000,
        "max_description_chars": 4_000,
        "max_output_tokens": 4_000,
        "prompt_version": "analysis-prompt-v1",
        "schema_version": "analysis-result-v1",
        "sampling_version": "cloud-token-sampling-v1",
        "privacy_version": "cloud-privacy-v1",
    }
    assert "sk-" not in repr(raw)
    assert raw["storage"]["vault_root"] == "/absolute/path/to/obsidian/vault"


def test_cloud_dependencies_are_direct_offline_importable_and_licensed() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(project["project"]["dependencies"])

    assert "openai>=2.46.0,<2.47" in dependencies
    assert "tiktoken>=0.13.0,<0.14" in dependencies
    assert importlib.metadata.version("openai") == "2.46.0"
    assert importlib.metadata.version("tiktoken") == "0.13.0"
    assert importlib.metadata.metadata("openai")["License"] == "Apache-2.0"
    assert importlib.metadata.metadata("tiktoken")["License"].startswith("MIT License")


def test_obsidian_template_dependency_is_direct_offline_importable_and_licensed() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(project["project"]["dependencies"])

    assert "jinja2>=3.1.6,<3.2" in dependencies
    assert importlib.metadata.version("jinja2") == "3.1.6"
    assert importlib.import_module("jinja2").__version__ == "3.1.6"
    assert any(
        requirement.startswith("MarkupSafe")
        for requirement in importlib.metadata.requires("jinja2") or ()
    )
    assert importlib.metadata.metadata("markupsafe")["License-Expression"] == "BSD-3-Clause"


def test_correction_p1_4_tokenizer_resource_is_local_verified_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    empty_cache = tmp_path / "empty-tiktoken-cache"
    empty_cache.mkdir()
    assert not tuple(empty_cache.iterdir())
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(empty_cache))
    requests_module = importlib.import_module("requests")

    def deny_http(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access is forbidden for tokenizer provisioning checks")

    monkeypatch.setattr(requests_module, "get", deny_http)
    monkeypatch.setattr(socket, "create_connection", deny_http)
    assert not analysis_mod.PACKAGED_O200K_RESOURCE.exists()
    assert analysis_mod.O200K_BASE_SHA256 == (
        "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
    )
    with pytest.raises(analysis_mod.LocalTokenizerResourceError, match="missing"):
        analysis_mod.load_provisioned_o200k_encoding(tmp_path)
    assert analysis_mod.tokenizer_resource_status(tmp_path) == "MISSING"


def test_correction_p1_5_openai_import_is_isolated_from_pytest_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "openai" not in sys.modules
    for source_path in (REPO_ROOT / "src").rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_roots.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert "openai" not in imported_roots

    synthetic_parent_names = (
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_AD_TOKEN",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "PYTHONPATH",
        "SYNTHETIC_TOKEN",
        "SYNTHETIC_KEY",
        "SYNTHETIC_SECRET",
        "SYNTHETIC_PASSWORD",
    )
    synthetic_value = "synthetic-parent-environment-sentinel"
    for name in synthetic_parent_names:
        monkeypatch.setenv(name, synthetic_value)

    child_source = textwrap.dedent(
        """
        import importlib.metadata
        import json
        import os

        def blocked_names():
            exact = {
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "NO_PROXY",
                "PYTHONPATH",
            }
            suffixes = ("_TOKEN", "_KEY", "_SECRET", "_PASSWORD")
            return sorted(
                name
                for name in os.environ
                if name.startswith(("OPENAI_", "AZURE_"))
                or name in exact
                or name.endswith(suffixes)
            )

        before = blocked_names()
        import openai
        after = blocked_names()
        print(
            json.dumps(
                {
                    "module": openai.__name__,
                    "version": importlib.metadata.version("openai"),
                    "blocked_before": before,
                    "blocked_after": after,
                },
                sort_keys=True,
            )
        )
        """
    )
    executable = Path(sys.executable)
    assert executable.is_absolute()
    isolated_env = {
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
    }
    completed = subprocess.run(
        [str(executable), "-I", "-c", child_source],
        check=False,
        capture_output=True,
        env=isolated_env,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert synthetic_value not in completed.stdout
    assert synthetic_value not in completed.stderr
    child_result = json.loads(completed.stdout)
    assert child_result == {
        "blocked_after": [],
        "blocked_before": [],
        "module": "openai",
        "version": "2.46.0",
    }
    assert "openai" not in sys.modules


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def test_project_paths_reject_absolute_and_escape() -> None:
    root = "/tmp/yia-vault-root"
    StorageSettings(
        data_dir="data",
        logs_dir="logs",
        templates_dir="templates",
        vault_root=root,
        vault_subdir="notes",
    )
    with pytest.raises(ValidationError, match="project-root-relative"):
        StorageSettings(
            data_dir="/abs/data",
            logs_dir="logs",
            templates_dir="templates",
            vault_root=root,
            vault_subdir="notes",
        )
    with pytest.raises(ValidationError, match="\\.\\."):
        StorageSettings(
            data_dir="../escape",
            logs_dir="logs",
            templates_dir="templates",
            vault_root=root,
            vault_subdir="notes",
        )
    with pytest.raises(ValidationError, match="\\.\\."):
        StorageSettings(
            data_dir="data/../../etc",
            logs_dir="logs",
            templates_dir="templates",
            vault_root=root,
            vault_subdir="notes",
        )


def test_vault_root_and_subdir_rules(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    StorageSettings(
        vault_root=str(vault),
        vault_subdir="YouTube Intel",
    )
    with pytest.raises(ValidationError, match="absolute"):
        StorageSettings(vault_root="relative/vault", vault_subdir="sub")
    with pytest.raises(ValidationError, match="relative"):
        StorageSettings(vault_root=str(vault), vault_subdir="/abs/sub")
    with pytest.raises(ValidationError, match="\\.\\."):
        StorageSettings(vault_root=str(vault), vault_subdir="../escape")


def test_vault_symlink_escape_rejected(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = vault / "escape_link"
    link.symlink_to(outside)
    with pytest.raises(ValidationError):
        StorageSettings(
            vault_root=str(vault),
            vault_subdir="escape_link/secret",
        )


# ---------------------------------------------------------------------------
# YAML safety and secret redaction
# ---------------------------------------------------------------------------


def test_safe_load_rejects_python_tags(tmp_path: Path) -> None:
    evil = tmp_path / "evil.yaml"
    evil.write_text(
        "!!python/object/apply:os.system ['echo pwned']\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="invalid YAML|YAML"):
        load_settings(evil)


def test_secrets_never_loaded_or_shown() -> None:
    cloud = CloudSettings(
        enabled=True,
        model="gpt-4.1-mini",
        api_key_env="OPENAI_API_KEY",
    )
    text = repr(cloud)
    assert "OPENAI_API_KEY" in text
    assert "sk-" not in text
    with pytest.raises(ValidationError) as exc_info:
        CloudSettings(api_key_env="not valid!!")
    err = str(exc_info.value)
    assert "not valid!!" not in err
    assert "api_key_env" in err


def test_api_key_env_secret_shaped_input_redacted_in_errors(tmp_path: Path) -> None:
    """AC-8: sentinel secret-shaped input must appear as input and never leak."""
    sentinel = "sk-redaction-probe-123"

    with pytest.raises(ValidationError) as ve:
        CloudSettings(api_key_env=sentinel)
    ve_text = str(ve.value)
    ve_repr = repr(ve.value)
    assert sentinel not in ve_text
    assert sentinel not in ve_repr
    assert "api_key_env" in ve_text
    for err in ve.value.errors():
        assert err.get("input") != sentinel
        assert sentinel not in str(err)

    data = _minimal_settings_dict()
    data["cloud"] = {
        "enabled": False,
        "provider": "openai",
        "api_key_env": sentinel,
        "max_calls_per_run": 5,
        "max_input_tokens_per_video": 30000,
    }
    path = _write_settings(tmp_path, data)
    with pytest.raises(ConfigError) as ce:
        load_settings(path)
    ce_text = str(ce.value)
    assert sentinel not in ce_text
    assert "api_key_env" in ce_text or "settings validation failed" in ce_text


def test_correction_p1_3_config_error_releases_secret_from_exception_graph(
    tmp_path: Path,
) -> None:
    sentinel = "-".join(("sk", "correction", "config", "graph", "sentinel"))
    data = _minimal_settings_dict()
    data["cloud"] = {
        "enabled": False,
        "provider": "openai",
        "api_key_env": sentinel,
        "max_calls_per_run": 5,
        "max_input_tokens_per_video": 30_000,
    }
    path = _write_settings(tmp_path, data)

    with pytest.raises(ConfigError) as exc_info:
        load_settings(path)

    pending: list[BaseException] = [exc_info.value]
    seen: set[int] = set()
    while pending:
        error = pending.pop()
        if id(error) in seen:
            continue
        seen.add(id(error))
        assert sentinel not in str(error)
        assert sentinel not in repr(error)
        assert sentinel not in "".join(traceback.format_exception(error))
        if isinstance(error, ValidationError):
            assert sentinel not in repr(error.errors())

        current_tb = error.__traceback__
        while current_tb is not None:
            frame = current_tb.tb_frame
            frame_path = Path(frame.f_code.co_filename).resolve()
            source_root = (REPO_ROOT / "src/youtube_intel").resolve()
            if frame_path.is_relative_to(source_root):
                for value in frame.f_locals.values():
                    assert sentinel not in repr(value)
            current_tb = current_tb.tb_next

        for linked in (error.__cause__, error.__context__):
            if linked is not None:
                pending.append(linked)

    assert sentinel not in str(exc_info.getrepr())


def test_app_settings_repr_has_no_secret_values(tmp_path: Path) -> None:
    settings = load_settings(SETTINGS_EXAMPLE)
    dumped = settings.model_dump()
    blob = repr(settings) + repr(dumped)
    assert "sk-" not in blob
    assert "OPENAI_API_KEY" in blob


# ---------------------------------------------------------------------------
# Domain objects and provider contracts
# ---------------------------------------------------------------------------


def test_analysis_payload_serializes_only_the_approved_cloud_fields() -> None:
    payload_type = AnalysisPayload
    payload = _analysis_payload()

    assert set(payload.model_dump(mode="json")) == {
        "video_id",
        "title",
        "channel_name",
        "published_at",
        "duration_seconds",
        "default_language",
        "description",
        "transcript_language",
        "output_language",
        "transcript_sample",
    }
    with pytest.raises(ValidationError):
        payload_type.model_validate(
            {
                **payload.model_dump(),
                "source_url": "/private/local/path",
            }
        )
    with pytest.raises(ValidationError):
        payload_type(
            **{
                **payload.model_dump(),
                "description": "d" * 4001,
            }
        )


def test_correction_p1_1_analysis_audit_hashes_are_lowercase_sha256() -> None:
    evidence = EvidenceExcerpt(
        evidence_id="e1",
        source=EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt="sample",
    )
    point = AnalysisPoint(
        text="Grounded point",
        kind=PointKind.INFERENCE,
        evidence_ids=("e1",),
    )
    valid_hash = "a" * 64

    def analysis_input_transcript(value: str) -> AnalysisInput:
        return AnalysisInput(
            payload=_analysis_payload(),
            transcript_content_hash=value,
            request_hash="b" * 64,
        )

    def analysis_input_request(value: str) -> AnalysisInput:
        return AnalysisInput(
            payload=_analysis_payload(),
            transcript_content_hash=valid_hash,
            request_hash=value,
        )

    def analysis_result_request(value: str) -> AnalysisResult:
        return AnalysisResult(
            one_sentence_summary="Summary",
            core_points=(point,),
            keywords=("ai",),
            evidence=(evidence,),
            provider="openai",
            model="gpt-4.1-mini",
            request_hash=value,
        )

    builders = (
        analysis_input_transcript,
        analysis_input_request,
        analysis_result_request,
    )
    invalid_hashes = (
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        f" {valid_hash}",
        f"{valid_hash} ",
    )
    for build in builders:
        assert build(valid_hash)
        for invalid_hash in invalid_hashes:
            with pytest.raises(ValidationError):
                build(invalid_hash)


def test_correction_p1_2_analysis_semantic_strings_reject_only_whitespace() -> None:
    payload_fields = (
        "video_id",
        "title",
        "channel_name",
        "transcript_language",
        "output_language",
        "transcript_sample",
        "default_language",
    )
    for field_name in payload_fields:
        with pytest.raises(ValidationError):
            _analysis_payload(**{field_name: " \t "})

    payload = _analysis_payload(title=" Public title ", default_language=None, description="")
    assert payload.title == " Public title "
    assert payload.default_language is None
    assert payload.description == ""

    with pytest.raises(ValidationError):
        EvidenceExcerpt(
            evidence_id=" \t ",
            source=EvidenceSource.TRANSCRIPT_SAMPLE,
            excerpt="sample",
        )
    with pytest.raises(ValidationError):
        EvidenceExcerpt(
            evidence_id="e1",
            source=EvidenceSource.TRANSCRIPT_SAMPLE,
            excerpt=" \t ",
        )
    with pytest.raises(ValidationError):
        AnalysisPoint(
            text=" \t ",
            kind=PointKind.INFERENCE,
            evidence_ids=("e1",),
        )
    with pytest.raises(ValidationError):
        AnalysisPoint(
            text="Grounded",
            kind=PointKind.INFERENCE,
            evidence_ids=(" \t ",),
        )

    evidence = EvidenceExcerpt(
        evidence_id="e1",
        source=EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt=" sample ",
    )
    point = AnalysisPoint(
        text=" Grounded ",
        kind=PointKind.INFERENCE,
        evidence_ids=("e1",),
    )
    for content_update in (
        {"one_sentence_summary": " \t "},
        {"keywords": (" \t ",)},
    ):
        with pytest.raises(ValidationError):
            AnalysisContent.model_validate(
                {
                    "one_sentence_summary": "Summary",
                    "core_points": (point,),
                    "keywords": ("ai",),
                    "evidence": (evidence,),
                    **content_update,
                }
            )

    result_data = {
        "one_sentence_summary": " Summary ",
        "core_points": (point,),
        "keywords": (" ai ",),
        "evidence": (evidence,),
        "provider": " openai ",
        "model": " gpt-4.1-mini ",
        "request_hash": "a" * 64,
    }
    result = AnalysisResult.model_validate(result_data)
    assert result.one_sentence_summary == " Summary "
    assert result.keywords == (" ai ",)
    assert result.provider == " openai "
    assert result.model == " gpt-4.1-mini "

    for field_name in ("provider", "model"):
        with pytest.raises(ValidationError):
            AnalysisResult.model_validate({**result_data, field_name: " \t "})

    valid_result = AnalysisResult.model_validate(
        {
            **result_data,
            "provider": "openai",
            "model": "gpt-4.1-mini",
        }
    )
    blank_provider_call = ProviderCallMetadata(
        provider=" \t ",
        model="gpt-4.1-mini",
        started_at=NOW,
        finished_at=NOW,
    )
    blank_model_call = ProviderCallMetadata(
        provider="openai",
        model=" \t ",
        started_at=NOW,
        finished_at=NOW,
    )
    with pytest.raises(ValidationError):
        AnalysisCompleted(result=valid_result, call=blank_provider_call)
    with pytest.raises(ValidationError):
        AnalysisCompleted(result=valid_result, call=blank_model_call)


def test_analysis_input_is_limited_to_payload_and_local_audit_fields() -> None:
    analysis_input = AnalysisInput(
        payload=_analysis_payload(),
        transcript_content_hash="a" * 64,
        request_hash="b" * 64,
    )

    assert set(AnalysisInput.model_fields) == {
        "payload",
        "transcript_content_hash",
        "request_hash",
        "prompt_version",
        "schema_version",
        "sampling_version",
        "privacy_version",
        # The backend-issued candidate set bound to this request identity.
        # It carries only refs and trusted text: no offset, timestamp, or
        # excerpt authority of its own.
        "trusted_evidence",
    }
    assert analysis_input.prompt_version == "analysis-prompt-v1"
    assert analysis_input.schema_version == "analysis-result-v1"
    assert analysis_input.sampling_version == "cloud-token-sampling-v1"
    assert analysis_input.privacy_version == "cloud-privacy-v1"
    assert analysis_input.trusted_evidence is None
    assert set(TrustedEvidenceOffer.model_fields) == {
        "registry_identity",
        "cue_group_policy",
        "metadata_span_policy",
        "candidates",
    }
    assert set(TrustedEvidenceCandidateView.model_fields) == {
        "ref",
        "source",
        "text",
    }
    for forbidden in ("video", "transcript_text", "score", "language"):
        assert not hasattr(analysis_input, forbidden)

    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        analysis_input.model_copy(update={"request_hash": "unvalidated"})
    copied = analysis_input.model_copy()
    assert copied == analysis_input
    assert copied is not analysis_input


def test_analysis_content_is_provider_neutral_and_requires_evidence() -> None:
    evidence = domain_mod.EvidenceExcerpt(
        evidence_id="e1",
        source=domain_mod.EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt="sample",
    )
    point = domain_mod.AnalysisPoint(
        text="Grounded point",
        kind=domain_mod.PointKind.FACT,
        evidence_ids=("e1",),
    )
    content = domain_mod.AnalysisContent(
        one_sentence_summary="Summary",
        core_points=(point,),
        keywords=("ai",),
        evidence=(evidence,),
    )

    assert set(content.model_dump()) == {
        "one_sentence_summary",
        "core_points",
        "key_facts",
        "product_opportunities",
        "business_opportunities",
        "actionable_directions",
        "hypotheses_to_validate",
        "action_recommendations",
        "risks",
        "keywords",
        "evidence",
    }
    for local_audit_field in (
        "provider",
        "model",
        "prompt_version",
        "request_hash",
        "call",
    ):
        assert local_audit_field not in type(content).model_fields

    with pytest.raises(ValidationError):
        domain_mod.AnalysisPoint(
            text="Ungrounded point",
            kind=domain_mod.PointKind.INFERENCE,
            evidence_ids=(),
        )


def test_analysis_evidence_sources_timestamps_and_point_kinds_are_fixed() -> None:
    assert {source.value for source in domain_mod.EvidenceSource} == {
        "title",
        "channel_name",
        "description",
        "transcript_sample",
    }
    evidence = domain_mod.EvidenceExcerpt(
        evidence_id="e1",
        source=domain_mod.EvidenceSource.TITLE,
        excerpt="Public title",
    )

    with pytest.raises(ValidationError):
        domain_mod.EvidenceExcerpt(
            evidence_id="e1",
            source=domain_mod.EvidenceSource.TRANSCRIPT_SAMPLE,
            excerpt="sample",
            start_seconds=1.0,
        )
    with pytest.raises(ValidationError):
        domain_mod.EvidenceExcerpt(
            evidence_id="e1",
            source=domain_mod.EvidenceSource.TRANSCRIPT_SAMPLE,
            excerpt="sample",
            end_seconds=2.0,
        )

    fact = domain_mod.AnalysisPoint(
        text="Fact",
        kind=domain_mod.PointKind.FACT,
        evidence_ids=("e1",),
    )
    inference = domain_mod.AnalysisPoint(
        text="Inference",
        kind=domain_mod.PointKind.INFERENCE,
        evidence_ids=("e1",),
    )
    recommendation = domain_mod.AnalysisPoint(
        text="Recommendation",
        kind=domain_mod.PointKind.RECOMMENDATION,
        evidence_ids=("e1",),
    )
    content_data = {
        "one_sentence_summary": "Summary",
        "core_points": (fact, inference),
        "key_facts": (fact,),
        "product_opportunities": (inference,),
        "business_opportunities": (inference,),
        "actionable_directions": (recommendation,),
        "hypotheses_to_validate": (inference,),
        "action_recommendations": (recommendation,),
        "risks": (inference,),
        "keywords": ("ai",),
        "evidence": (evidence,),
    }
    domain_mod.AnalysisContent.model_validate(content_data)

    invalid_kinds = (
        ("core_points", (recommendation,)),
        ("key_facts", (inference,)),
        ("product_opportunities", (recommendation,)),
        ("business_opportunities", (fact,)),
        ("actionable_directions", (inference,)),
        ("hypotheses_to_validate", (fact,)),
        ("action_recommendations", (inference,)),
        ("risks", (recommendation,)),
    )
    for field_name, points in invalid_kinds:
        with pytest.raises(ValidationError, match=field_name):
            domain_mod.AnalysisContent.model_validate(
                {
                    **content_data,
                    field_name: points,
                }
            )


def test_analysis_outcome_distinguishes_completed_from_fixed_skip_reasons() -> None:
    evidence = domain_mod.EvidenceExcerpt(
        evidence_id="e1",
        source=domain_mod.EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt="sample",
    )
    result = domain_mod.AnalysisResult(
        one_sentence_summary="Summary",
        core_points=(
            domain_mod.AnalysisPoint(
                text="Grounded inference",
                kind=domain_mod.PointKind.INFERENCE,
                evidence_ids=("e1",),
            ),
        ),
        keywords=("ai",),
        evidence=(evidence,),
        provider="openai",
        model="gpt-4.1-mini",
        request_hash="a" * 64,
    )
    completed = domain_mod.AnalysisCompleted(
        result=result,
        call=ProviderCallMetadata(
            provider="openai",
            model="gpt-4.1-mini",
            started_at=NOW,
            finished_at=NOW,
        ),
    )
    skipped = domain_mod.AnalysisSkipped(
        reason=domain_mod.AnalysisSkipReason.CLOUD_DISABLED,
        call=None,
        safe_message="Cloud analysis is disabled.",
    )

    assert AnalysisOutcome == (AnalysisCompleted | AnalysisSkipped)
    assert completed.result.schema_version == "analysis-result-v1"
    assert completed.result.prompt_version == "analysis-prompt-v1"
    assert skipped.reason is domain_mod.AnalysisSkipReason.CLOUD_DISABLED
    assert {reason.value for reason in domain_mod.AnalysisSkipReason} == {
        "CLOUD_DISABLED",
        "CREDENTIAL_UNAVAILABLE",
        "BUDGET_EXHAUSTED",
        "INPUT_TOO_LARGE",
        "PROVIDER_REFUSAL",
    }
    with pytest.raises(ValidationError):
        domain_mod.AnalysisSkipped(
            reason="LOW_VALUE",
            call=None,
            safe_message="Not an approved analysis skip reason.",
        )
    with pytest.raises(ValidationError):
        domain_mod.AnalysisSkipped(
            reason=domain_mod.AnalysisSkipReason.BUDGET_EXHAUSTED,
            call=None,
            safe_message="",
        )
    with pytest.raises(ValidationError):
        domain_mod.AnalysisSkipped(
            reason=domain_mod.AnalysisSkipReason.BUDGET_EXHAUSTED,
            call=None,
            safe_message="   ",
        )


def test_correction_p1_6_completed_metadata_is_consistent_and_copy_safe() -> None:
    sensitive_content = "transcript-sentinel /private/sensitive/path sk-not-a-real-key"
    evidence = EvidenceExcerpt(
        evidence_id="e1",
        source=EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt=sensitive_content,
    )
    result = AnalysisResult(
        one_sentence_summary=sensitive_content,
        core_points=(
            AnalysisPoint(
                text=sensitive_content,
                kind=PointKind.INFERENCE,
                evidence_ids=("e1",),
            ),
        ),
        keywords=("ai",),
        evidence=(evidence,),
        provider="openai",
        model="gpt-4.1-mini",
        request_hash="a" * 64,
    )
    matching_call = ProviderCallMetadata(
        provider="openai",
        model="gpt-4.1-mini",
        started_at=NOW,
        finished_at=NOW,
    )
    completed = AnalysisCompleted(result=result, call=matching_call)
    for copied in (completed.model_copy(), completed.model_copy(deep=True)):
        assert copied == completed
        assert copied.result.provider == copied.call.provider
        assert copied.result.model == copied.call.model

    invalid_calls = (
        ProviderCallMetadata(
            provider="different-provider",
            model="gpt-4.1-mini",
            started_at=NOW,
            finished_at=NOW,
        ),
        ProviderCallMetadata(
            provider="openai",
            model="different-model",
            started_at=NOW,
            finished_at=NOW,
        ),
        ProviderCallMetadata(
            provider="openai",
            model=None,
            started_at=NOW,
            finished_at=NOW,
        ),
        ProviderCallMetadata(
            provider="openai",
            model=" \t ",
            started_at=NOW,
            finished_at=NOW,
        ),
    )
    for invalid_call in invalid_calls:
        with pytest.raises(ValidationError) as exc_info:
            AnalysisCompleted(result=result, call=invalid_call)
        error_blob = str(exc_info.value) + repr(exc_info.value.errors())
        assert sensitive_content not in error_blob


def test_analysis_contract_model_copy_rejects_all_unvalidated_updates() -> None:
    payload = _analysis_payload()
    analysis_input = AnalysisInput(
        payload=payload,
        transcript_content_hash=TRANSCRIPT_HASH,
        request_hash="b" * 64,
    )
    evidence = EvidenceExcerpt(
        evidence_id="e1",
        source=EvidenceSource.TRANSCRIPT_SAMPLE,
        excerpt="head",
    )
    point = AnalysisPoint(
        text="Grounded inference",
        kind=PointKind.INFERENCE,
        evidence_ids=("e1",),
    )
    content = AnalysisContent(
        one_sentence_summary="Summary",
        core_points=(point,),
        keywords=("ai",),
        evidence=(evidence,),
    )
    result = AnalysisResult(
        **content.model_dump(),
        provider="openai",
        model="gpt-4.1-mini",
        request_hash="a" * 64,
    )
    completed = AnalysisCompleted(
        result=result,
        call=ProviderCallMetadata(
            provider="openai",
            model="gpt-4.1-mini",
            started_at=NOW,
            finished_at=NOW,
        ),
    )
    skipped = AnalysisSkipped(
        reason=AnalysisSkipReason.CLOUD_DISABLED,
        call=None,
        safe_message="Cloud analysis is disabled.",
    )
    objects_and_updates = (
        (payload, {"title": ""}),
        (analysis_input, {"request_hash": ""}),
        (evidence, {"start_seconds": 1.0}),
        (point, {"evidence_ids": ()}),
        (content, {"core_points": ()}),
        (result, {"provider": ""}),
        (completed, {"result": "unvalidated"}),
        (skipped, {"reason": "LOW_VALUE"}),
    )

    for contract, update in objects_and_updates:
        with pytest.raises(
            ValueError,
            match=r"model_copy\(update=\.\.\.\) is disabled",
        ):
            contract.model_copy(update=update)
        copied = contract.model_copy()
        assert copied == contract
        assert copied is not contract
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        payload.model_copy(update={})


def test_score_result_dimensions_and_cardinalities() -> None:
    assert SCORE_DIMENSION_NAMES == (
        "technical",
        "business",
        "product",
        "originality",
        "practicality",
        "industry_impact",
    )
    dims = ScoreDimensions(technical=9, business=None, product=7)
    result = _score(dimensions=dims)
    assert result.dimensions is not None
    assert result.dimensions.technical == 9
    with pytest.raises(ValidationError):
        _score(topics=())
    with pytest.raises(ValidationError):
        _score(topics=tuple(f"t{i}" for i in range(11)))
    with pytest.raises(ValidationError):
        _score(topics=("dup", "dup"))
    with pytest.raises(ValidationError):
        _score(reason="   ")
    with pytest.raises(ValidationError):
        ScoreDimensions(technical=10.1)


def test_scoring_sample_and_outcome_bind_hash_and_final_policy() -> None:
    sample = _sample()
    scoring_input = ScoringInput(
        video=_video(),
        sample=sample,
        transcript_content_hash=TRANSCRIPT_HASH,
        language="en",
        output_language="en",
        request_hash="request-hash",
    )
    assert scoring_input.sample == sample
    with pytest.raises(ValidationError, match="selected_char_count"):
        _sample(selected_char_count=11)
    with pytest.raises(ValidationError, match="sampling_version"):
        _sample(sampling_version="sampling-v2")
    with pytest.raises(ValidationError, match="transcript_content_hash"):
        ScoringInput(
            video=_video(),
            sample=sample,
            transcript_content_hash="c" * 64,
            language="en",
            output_language="en",
            request_hash="request-hash",
        )

    result = _score(score=6.5, should_summarize=True)
    decision = ScoringDecision(
        threshold=7.0,
        final_should_summarize=False,
        model_disagrees=True,
    )
    outcome = ScoringOutcome(result=result, decision=decision, call=_call())
    assert outcome.decision.final_should_summarize is False
    with pytest.raises(ValidationError, match="final_should_summarize"):
        ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=7.0,
                final_should_summarize=True,
                model_disagrees=False,
            ),
            call=_call(),
        )
    with pytest.raises(ValidationError, match="model_disagrees"):
        ScoringOutcome(
            result=result,
            decision=ScoringDecision(
                threshold=7.0,
                final_should_summarize=False,
                model_disagrees=False,
            ),
            call=_call(),
        )


def test_scoring_contract_model_copy_rejects_all_updates() -> None:
    sample = _sample()
    scoring_input = ScoringInput(
        video=_video(),
        sample=sample,
        transcript_content_hash=TRANSCRIPT_HASH,
        language="en",
        output_language="en",
        request_hash="request-hash",
    )
    decision = ScoringDecision(
        threshold=7.0,
        final_should_summarize=True,
        model_disagrees=False,
    )
    outcome = ScoringOutcome(result=_score(), decision=decision, call=_call())

    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        sample.model_copy(update={"head": "", "selected_char_count": 0})
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        scoring_input.model_copy(update={"transcript_content_hash": "c" * 64})
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        decision.model_copy(update={"final_should_summarize": "not-a-boolean"})
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        outcome.model_copy(
            update={
                "decision": ScoringDecision(
                    threshold=7.0,
                    final_should_summarize=False,
                    model_disagrees=True,
                )
            }
        )
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        sample.model_copy(update={"unknown": "value"})
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        decision.model_copy(update={"threshold": 7.5})
    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        sample.model_copy(update={})

    copied_sample = sample.model_copy()
    assert copied_sample == sample
    assert copied_sample is not sample


def test_analysis_result_structure_and_evidence_refs() -> None:
    evidence = (
        EvidenceExcerpt(
            evidence_id="e1",
            source=EvidenceSource.TRANSCRIPT_SAMPLE,
            excerpt="quoted text",
        ),
    )
    point = AnalysisPoint(
        text="A fact",
        kind=PointKind.FACT,
        evidence_ids=("e1",),
    )
    result = AnalysisResult(
        one_sentence_summary="Summary",
        core_points=(
            AnalysisPoint(text="Core", kind=PointKind.INFERENCE, evidence_ids=("e1",)),
        ),
        key_facts=(point,),
        keywords=("ai",),
        evidence=evidence,
        provider="openai",
        model="gpt",
        request_hash="a" * 64,
    )
    assert len(result.core_points) == 1

    with pytest.raises(ValidationError, match="unknown evidence"):
        AnalysisResult(
            one_sentence_summary="Summary",
            core_points=(
                AnalysisPoint(text="Core", kind=PointKind.INFERENCE, evidence_ids=("missing",)),
            ),
            keywords=("ai",),
            evidence=evidence,
            provider="openai",
            model="gpt",
            request_hash="a" * 64,
        )

    with pytest.raises(ValidationError, match="key_facts"):
        AnalysisResult(
            one_sentence_summary="Summary",
            core_points=(
                AnalysisPoint(
                    text="Core",
                    kind=PointKind.INFERENCE,
                    evidence_ids=("e1",),
                ),
            ),
            key_facts=(
                AnalysisPoint(
                    text="Not fact",
                    kind=PointKind.INFERENCE,
                    evidence_ids=("e1",),
                ),
            ),
            keywords=("ai",),
            evidence=evidence,
            provider="openai",
            model="gpt",
            request_hash="a" * 64,
        )

    with pytest.raises(ValidationError):
        EvidenceExcerpt(
            evidence_id="e2",
            source=EvidenceSource.DESCRIPTION,
            excerpt="x",
            start_seconds=5,
            end_seconds=1,
        )


def test_cross_module_io_objects() -> None:
    cursor = DiscoveryCursor(channel_id="UC_x")
    batch = DiscoveryBatch(
        channel_id="UC_x",
        video_ids=("a", "b"),
        next_cursor=cursor,
        call=_call(),
    )
    assert batch.video_ids == ("a", "b")
    with pytest.raises(ValidationError):
        DiscoveryBatch(
            channel_id="UC_x",
            video_ids=("a", "a"),
            next_cursor=cursor,
            call=_call(),
        )

    scoring_in = ScoringInput(
        video=_video(),
        sample=_sample(),
        transcript_content_hash=TRANSCRIPT_HASH,
        language="zh",
        output_language="zh-CN",
        request_hash="rh",
    )
    analysis_in = AnalysisInput(
        payload=_analysis_payload(),
        transcript_content_hash=TRANSCRIPT_HASH,
        request_hash="b" * 64,
    )
    assert scoring_in.language == "zh"
    assert analysis_in.payload.output_language == "zh-CN"

    na = NotAvailable(
        reason_code=NotAvailableReason.NO_CONTENT,
        message="empty",
        retryable=False,
        call=_call(),
    )
    assert na.reason_code is NotAvailableReason.NO_CONTENT

    note = NoteRef(
        kind=NoteKind.VIDEO,
        relative_path="Videos/x.md",
        content_hash="c" * 64,
    )
    with pytest.raises(ValidationError):
        NoteRef(kind=NoteKind.VIDEO, relative_path="../escape.md", content_hash="c")

    item = WeeklyReportItem(
        video=_video(video_id="v1"),
        score=_score(score=9.0),
        note_ref=note,
        one_sentence_summary="s",
    )
    item_low = WeeklyReportItem(
        video=_video(video_id="v2"),
        score=_score(score=5.0),
        note_ref=note,
        one_sentence_summary="s2",
    )
    WeeklyReportInput(
        iso_year=2026,
        iso_week=28,
        timezone="Asia/Shanghai",
        items=(item, item_low),
        generated_at=NOW,
    )
    with pytest.raises(ValidationError, match="sorted"):
        WeeklyReportInput(
            iso_year=2026,
            iso_week=28,
            timezone="Asia/Shanghai",
            items=(item_low, item),
            generated_at=NOW,
        )


def test_error_codes_and_structured_app_error() -> None:
    codes = {c.value for c in ErrorCode}
    # Exact set from System Design §12 plus the approved staged-build capability
    # member and the approved H2-C trust-integrity member — the final taxonomy is
    # exactly ten codes, no unapproved extras.  The assertion stays an exact set.
    assert codes == {
        "TRANSIENT_NETWORK",
        "RATE_LIMITED",
        "PROVIDER_UNAVAILABLE",
        "INVALID_RESPONSE",
        "CONTENT_UNAVAILABLE",
        "CONFIG_INVALID",
        "PERMISSION_DENIED",
        "LOCAL_RESOURCE",
        "CAPABILITY_UNAVAILABLE",
        "TRUST_INTEGRITY_INVALID",
    }
    assert "INVALID_TRANSITION" not in codes
    err = AppError(
        code=ErrorCode.RATE_LIMITED,
        message="limited",
        retryable=True,
        retry_after_seconds=30,
        stage=ProcessingStage.SCORING,
    )
    assert err.retryable is True
    assert err.retry_after_seconds == 30
    with pytest.raises(ValidationError):
        AppError(
            code=ErrorCode.CONFIG_INVALID,
            message="bad",
            retryable=False,
            retry_after_seconds=1,
        )


def test_provider_protocols_are_structural() -> None:
    class FakeSource:
        def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch:
            return DiscoveryBatch(
                channel_id=channel.channel_id,
                video_ids=(),
                next_cursor=cursor,
                call=_call(),
            )

    assert isinstance(FakeSource(), SourceProvider)

    class FakeMeta:
        def fetch(self, video_id: str) -> VideoMetadata:
            return _video(video_id=video_id)

    assert isinstance(FakeMeta(), MetadataProvider)

    class FakeTranscript:
        def fetch(
            self,
            video: VideoMetadata,
            language_preferences: tuple[str, ...],
        ) -> TranscriptFetchResult:
            return TranscriptionRequired(
                reason=TranscriptionReason.NO_MATCHING_LANGUAGE,
                call=_call(),
                attempted_track_count=0,
            )

    assert isinstance(FakeTranscript(), TranscriptProvider)

    class FakeScore:
        def score(self, scoring_input: ScoringInput) -> ScoreResult:
            return _score(request_hash=scoring_input.request_hash)

    assert isinstance(FakeScore(), ScoringProvider)

    class FakeSummary:
        def summarize(self, analysis_input: AnalysisInput) -> AnalysisResult:
            evidence = EvidenceExcerpt(
                evidence_id="e1",
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="head",
            )
            return AnalysisResult(
                one_sentence_summary="s",
                core_points=(
                    AnalysisPoint(
                        text="c",
                        kind=PointKind.INFERENCE,
                        evidence_ids=("e1",),
                    ),
                ),
                keywords=("k",),
                evidence=(evidence,),
                provider="p",
                model="m",
                request_hash=analysis_input.request_hash,
            )

    assert isinstance(FakeSummary(), SummaryProvider)

    high_value_scoring: ScoringOutcome = ScoringOutcome(
        result=_score(score=8.0, should_summarize=True),
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=True,
            model_disagrees=False,
        ),
        call=_call(),
    )
    skipped_analysis: AnalysisOutcome = AnalysisSkipped(
        reason=AnalysisSkipReason.CLOUD_DISABLED,
        call=None,
        safe_message="Cloud analysis is disabled.",
    )

    class FakeSink(KnowledgeSink):
        def _upsert_video_note(
            self,
            *,
            video: VideoMetadata,
            transcript: TranscriptArtifact,
            scoring: ScoringOutcome,
            analysis: AnalysisOutcome,
            processed_at: datetime,
            pipeline_version: str,
        ) -> NoteRef:
            assert scoring.decision.final_should_summarize is True
            assert isinstance(analysis, AnalysisSkipped)
            assert processed_at.tzinfo is not None
            assert pipeline_version == "pipeline-v1"
            return NoteRef(
                kind=NoteKind.VIDEO,
                relative_path="a.md",
                content_hash="a" * 64,
            )

        def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef:
            return NoteRef(
                kind=NoteKind.WEEKLY,
                relative_path="w.md",
                content_hash="a" * 64,
            )

    sink = FakeSink()
    assert isinstance(sink, KnowledgeSink)
    signature = inspect.signature(KnowledgeSink.upsert_video_note)
    assert [parameter.name for parameter in signature.parameters.values()] == [
        "self",
        "video",
        "transcript",
        "scoring",
        "analysis",
        "processed_at",
        "pipeline_version",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in tuple(signature.parameters.values())[1:]
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in tuple(signature.parameters.values())[1:]
    )
    assert inspect.get_annotations(KnowledgeSink.upsert_video_note) == {
        "video": "VideoMetadata",
        "transcript": "TranscriptArtifact",
        "scoring": "ScoringOutcome",
        "analysis": "AnalysisOutcome",
        "processed_at": "datetime",
        "pipeline_version": "str",
        "return": "NoteRef",
    }
    assert high_value_scoring.decision.final_should_summarize is True
    assert isinstance(skipped_analysis, AnalysisSkipped)
    assert (
        sink.upsert_video_note(
            video=_video(),
            transcript=TranscriptArtifact(
                video_id="vid1",
                language="en",
                source_type=TranscriptSourceType.MANUAL_SUBTITLE,
                requested_language="en",
                source_format=SubtitleFormat.JSON3,
                text_path="transcripts/vid1/canonical.txt",
                timed_text_path="transcripts/vid1/source.json3",
                source_content_hash="a" * 64,
                source_byte_count=128,
                content_hash="b" * 64,
                char_count=10,
                segment_count=1,
                normalization_version="subtitle-normalization-v1",
                provider="youtube",
                created_at=NOW,
            ),
            scoring=high_value_scoring,
            analysis=skipped_analysis,
            processed_at=NOW,
            pipeline_version="pipeline-v1",
        ).relative_path
        == "a.md"
    )


def test_knowledge_sink_fails_closed_before_calling_its_protected_hook() -> None:
    transcript = TranscriptArtifact(
        video_id="vid1",
        language="en",
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="en",
        source_format=SubtitleFormat.JSON3,
        text_path="transcripts/vid1/canonical.txt",
        timed_text_path="transcripts/vid1/source.json3",
        source_content_hash="a" * 64,
        source_byte_count=128,
        content_hash="b" * 64,
        char_count=10,
        segment_count=1,
        normalization_version="subtitle-normalization-v1",
        provider="youtube",
        created_at=NOW,
    )
    high_value_scoring = ScoringOutcome(
        result=_score(score=8.0, should_summarize=True),
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=True,
            model_disagrees=False,
        ),
        call=_call(),
    )
    low_value_scoring = ScoringOutcome(
        result=_score(score=6.5, should_summarize=True),
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=False,
            model_disagrees=True,
        ),
        call=_call(),
    )
    completed_analysis = AnalysisCompleted(
        result=AnalysisResult(
            one_sentence_summary="Summary",
            core_points=(
                AnalysisPoint(
                    text="Grounded point",
                    kind=PointKind.INFERENCE,
                    evidence_ids=("e1",),
                ),
            ),
            keywords=("ai",),
            evidence=(
                EvidenceExcerpt(
                    evidence_id="e1",
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    excerpt="excerpt",
                ),
            ),
            provider="openai",
            model="gpt-4.1-mini",
            request_hash="a" * 64,
        ),
        call=ProviderCallMetadata(
            provider="openai",
            model="gpt-4.1-mini",
            started_at=NOW,
            finished_at=NOW,
        ),
    )
    skipped_analysis = AnalysisSkipped(
        reason=AnalysisSkipReason.CLOUD_DISABLED,
        call=None,
        safe_message="Cloud analysis is disabled.",
    )

    class FakeSink(KnowledgeSink):
        def __init__(self) -> None:
            self.hook_calls = 0

        def _upsert_video_note(
            self,
            *,
            video: VideoMetadata,
            transcript: TranscriptArtifact,
            scoring: ScoringOutcome,
            analysis: AnalysisOutcome,
            processed_at: datetime,
            pipeline_version: str,
        ) -> NoteRef:
            self.hook_calls += 1
            return NoteRef(
                kind=NoteKind.VIDEO,
                relative_path="Videos/vid1.md",
                content_hash="c" * 64,
            )

        def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef:
            return NoteRef(
                kind=NoteKind.WEEKLY,
                relative_path="Weekly/2026-W29.md",
                content_hash="d" * 64,
            )

    sink = FakeSink()
    valid_kwargs = {
        "video": _video(),
        "transcript": transcript,
        "scoring": high_value_scoring,
        "analysis": skipped_analysis,
        "processed_at": NOW,
        "pipeline_version": "pipeline-v1",
    }

    assert sink.upsert_video_note(**valid_kwargs).relative_path == "Videos/vid1.md"
    assert sink.hook_calls == 1
    assert (
        sink.upsert_video_note(
            **{**valid_kwargs, "analysis": completed_analysis}
        ).relative_path
        == "Videos/vid1.md"
    )
    assert sink.hook_calls == 2

    invalid_kwargs = (
        {**valid_kwargs, "processed_at": datetime(2026, 7, 14, 12, 0, 0)},
        {
            **valid_kwargs,
            "processed_at": datetime(
                2026,
                7,
                14,
                20,
                0,
                0,
                tzinfo=timezone(timedelta(hours=8)),
            ),
        },
        {**valid_kwargs, "pipeline_version": ""},
        {**valid_kwargs, "pipeline_version": " pipeline-v1"},
        {**valid_kwargs, "pipeline_version": "pipeline-v1 "},
        {**valid_kwargs, "scoring": low_value_scoring},
    )
    for invalid in invalid_kwargs:
        with pytest.raises(ValueError):
            sink.upsert_video_note(**invalid)
        assert sink.hook_calls == 2

    with pytest.raises(TypeError):
        sink.upsert_video_note(
            _video(),
            transcript,
            high_value_scoring,
            skipped_analysis,
            NOW,
            "pipeline-v1",
        )
    assert sink.hook_calls == 2


def test_note_ref_requires_a_verified_posix_markdown_identity() -> None:
    note = NoteRef(
        kind=NoteKind.VIDEO,
        relative_path="Videos/insight--abc123.md",
        content_hash="a" * 64,
    )
    assert note.relative_path == "Videos/insight--abc123.md"

    for relative_path in (
        "/absolute.md",
        r"Videos\\windows.md",
        "C:drive.md",
        "C:/drive.md",
        ".",
        "..",
        "Videos//empty.md",
        "Videos/./current.md",
        "Videos/../parent.md",
        "Videos/not-markdown.txt",
        " Videos/leading.md",
        "Videos/trailing.md ",
        "Videos/\x00nul.md",
    ):
        with pytest.raises(ValidationError):
            NoteRef(
                kind=NoteKind.VIDEO,
                relative_path=relative_path,
                content_hash="a" * 64,
            )

    for content_hash in ("", "a" * 63, "A" * 64, "g" * 64):
        with pytest.raises(ValidationError):
            NoteRef(
                kind=NoteKind.VIDEO,
                relative_path="Videos/insight--abc123.md",
                content_hash=content_hash,
            )

    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        note.model_copy(update={"relative_path": "Videos/other.md"})


def test_domain_module_has_no_concrete_sdk_imports() -> None:
    source = Path(inspect.getfile(config_mod)).parent / "domain.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    banned = {
        "openai",
        "httpx",
        "yt_dlp",
        "mlx_whisper",
        "ollama",
        "sqlite3",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned


def test_cloud_contract_files_do_not_read_environment_or_construct_clients() -> None:
    for module in (config_mod, domain_mod):
        source = Path(inspect.getfile(module))
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_roots.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert "openai" not in imported_roots
        assert "tiktoken" not in imported_roots
        if module is config_mod:
            assert "os" not in imported_roots


def _annotation_is_free_form_dict(annotation: object) -> bool:
    text = str(annotation)
    lowered = text.lower().replace(" ", "")
    if lowered in {"dict", "typing.dict", "builtins.dict"}:
        return True
    if re.search(r"\bdict\[", lowered):
        return True
    if "dict[str,typing.any]" in lowered or "dict[str,any]" in lowered:
        return True
    return False


def _annotation_is_wide(annotation: object) -> bool:
    text = str(annotation).lower().replace(" ", "")
    return (
        _annotation_is_free_form_dict(annotation)
        or text in {"any", "typing.any", "object", "builtins.object"}
        or re.search(r"(^|[|,\[])object([|,\]]|$)", text) is not None
        or re.search(r"(^|[|,\[])any([|,\]]|$)", text) is not None
    )


def test_public_contracts_avoid_free_form_dict() -> None:
    """Public exports must not expose free-form dict loaders or model fields."""
    assert "load_yaml_mapping" not in config_mod.__all__
    assert getattr(config_mod, "load_yaml_mapping", None) is None

    for mod in (config_mod, domain_mod):
        for name in mod.__all__:
            obj = getattr(mod, name)
            if inspect.isfunction(obj):
                hints = getattr(obj, "__annotations__", {})
                for ann_name, ann in hints.items():
                    assert not _annotation_is_free_form_dict(ann), (
                        f"{mod.__name__}.{name} annotation {ann_name}: {ann}"
                    )
            if inspect.isclass(obj) and hasattr(obj, "model_fields"):
                for field_name, field in obj.model_fields.items():
                    ann = field.annotation
                    assert not _annotation_is_free_form_dict(ann), (
                        f"{obj.__name__}.{field_name} uses free-form dict: {ann}"
                    )

    # Public loaders return typed contracts, not mappings.
    channels = load_channels(CHANNELS_EXAMPLE)
    settings = load_settings(SETTINGS_EXAMPLE)
    assert isinstance(channels, tuple)
    assert not isinstance(channels, dict)
    assert not isinstance(settings, dict)


def test_task_005_public_annotations_avoid_any_object_and_free_dict() -> None:
    for mod in (domain_mod, transcripts_mod, subtitles_mod):
        for name in mod.__all__:
            exported = getattr(mod, name)
            objects: list[tuple[str, object]] = [(name, exported)]
            if inspect.isclass(exported):
                objects.extend(
                    (f"{name}.{member_name}", member)
                    for member_name, member in exported.__dict__.items()
                    if (
                        member_name == "__init__"
                        or not member_name.startswith("_")
                    )
                    and (
                        inspect.isfunction(member)
                        or isinstance(member, property)
                    )
                )
            for qualified_name, obj in objects:
                target = obj.fget if isinstance(obj, property) else obj
                annotations = getattr(target, "__annotations__", {})
                for annotation_name, annotation in annotations.items():
                    assert not _annotation_is_wide(annotation), (
                        f"{mod.__name__}.{qualified_name} annotation "
                        f"{annotation_name}: {annotation}"
                    )


def test_task_005_runtime_modules_do_not_use_subprocess_or_ffmpeg() -> None:
    for module_path in (
        REPO_ROOT / "src" / "youtube_intel" / "transcripts.py",
        REPO_ROOT / "src" / "youtube_intel" / "providers" / "subtitles.py",
    ):
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_roots.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert "subprocess" not in imported_roots
        assert "ffmpeg" not in source.casefold()


# ---------------------------------------------------------------------------
# State machines
# ---------------------------------------------------------------------------


def test_pipeline_and_job_are_distinct_enums() -> None:
    assert set(PipelineStatus) != set(JobStatus)
    assert set(PipelineStatus) != set(ProcessingStage)
    assert "RETRY_PENDING" not in {s.value for s in PipelineStatus}
    assert "FAILED_FINAL" not in {s.value for s in PipelineStatus}
    assert JobStatus.RETRY_PENDING.value == "RETRY_PENDING"
    assert JobStatus.FAILED_FINAL.value == "FAILED_FINAL"


def test_transition_maps_are_runtime_immutable() -> None:
    assert isinstance(PIPELINE_TRANSITIONS, type(domain_mod.PIPELINE_TRANSITIONS))
    with pytest.raises(TypeError):
        PIPELINE_TRANSITIONS[PipelineStatus.DISCOVERED] = frozenset()  # type: ignore[index]
    with pytest.raises(TypeError):
        JOB_TRANSITIONS[JobStatus.PENDING] = frozenset()  # type: ignore[index]
    with pytest.raises((TypeError, AttributeError)):
        PIPELINE_TRANSITIONS.clear()  # type: ignore[attr-defined]
    with pytest.raises((TypeError, AttributeError)):
        JOB_TRANSITIONS.clear()  # type: ignore[attr-defined]
    # Values remain immutable frozensets.
    discovered = PIPELINE_TRANSITIONS[PipelineStatus.DISCOVERED]
    assert isinstance(discovered, frozenset)
    with pytest.raises(AttributeError):
        discovered.add(PipelineStatus.COMPLETE)  # type: ignore[attr-defined]


def test_legal_and_illegal_pipeline_transitions() -> None:
    assert can_transition_pipeline(
        PipelineStatus.DISCOVERED, PipelineStatus.METADATA_READY
    )
    assert transition_pipeline(
        PipelineStatus.SCORED, PipelineStatus.ANALYSIS_READY
    ) is PipelineStatus.ANALYSIS_READY
    with pytest.raises(InvalidTransitionError):
        transition_pipeline(PipelineStatus.DISCOVERED, PipelineStatus.COMPLETE)
    with pytest.raises(InvalidTransitionError):
        transition_pipeline(PipelineStatus.COMPLETE, PipelineStatus.DISCOVERED)


def test_legal_and_illegal_job_transitions() -> None:
    assert can_transition_job(JobStatus.PENDING, JobStatus.RUNNING)
    assert transition_job(JobStatus.RUNNING, JobStatus.RETRY_PENDING) is JobStatus.RETRY_PENDING
    assert transition_job(JobStatus.RETRY_PENDING, JobStatus.PENDING) is JobStatus.PENDING
    with pytest.raises(InvalidTransitionError):
        transition_job(JobStatus.PENDING, JobStatus.SUCCEEDED)
    with pytest.raises(InvalidTransitionError):
        transition_job(JobStatus.SUCCEEDED, JobStatus.RUNNING)


def test_failed_job_preserves_pipeline_status() -> None:
    status = PipelineStatus.TRANSCRIPT_READY
    assert (
        pipeline_after_job_failure(status, JobStatus.RETRY_PENDING)
        is PipelineStatus.TRANSCRIPT_READY
    )
    assert (
        pipeline_after_job_failure(status, JobStatus.FAILED_FINAL)
        is PipelineStatus.TRANSCRIPT_READY
    )
    with pytest.raises(InvalidTransitionError):
        pipeline_after_job_failure(status, JobStatus.SUCCEEDED)


def test_provider_returns_new_objects_not_mutated_input() -> None:
    video = _video()
    scoring_input = ScoringInput(
        video=video,
        sample=_sample(),
        transcript_content_hash=TRANSCRIPT_HASH,
        language="en",
        output_language="en",
        request_hash="r",
    )

    class MutatingScore:
        def score(self, scoring_input: ScoringInput) -> ScoreResult:
            # Must return new object; frozen input cannot be mutated
            with pytest.raises(Exception):
                scoring_input.language = "mutated"  # type: ignore[misc]
            return _score()

    result = MutatingScore().score(scoring_input)
    assert result is not scoring_input
    assert scoring_input.language == "en"


def test_diagnostic_entry_and_transcript_artifact() -> None:
    diag = DiagnosticEntry(code="INFO", message="ok")
    call = ProviderCallMetadata(
        provider="p",
        started_at=NOW,
        finished_at=NOW,
        diagnostics=(diag,),
    )
    artifact = TranscriptArtifact(
        video_id="v1",
        language="en",
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="en",
        source_format=SubtitleFormat.JSON3,
        text_path="transcripts/v1/request/canonical.txt",
        timed_text_path="transcripts/v1/request/source.json3",
        source_content_hash="a" * 64,
        source_byte_count=128,
        content_hash="b" * 64,
        char_count=10,
        segment_count=1,
        normalization_version="subtitle-normalization-v1",
        provider="youtube",
        created_at=NOW,
        quality_flags=(TranscriptQualityFlag.SPEAKER_LABELS_PRESENT,),
    )
    assert call.diagnostics[0].code == "INFO"
    assert artifact.source_type is TranscriptSourceType.MANUAL_SUBTITLE
    assert artifact.quality_flags == (TranscriptQualityFlag.SPEAKER_LABELS_PRESENT,)

    ready = TranscriptReady(artifact=artifact, call=call)
    assert ready.outcome == "ready"
    required = TranscriptionRequired(
        reason=TranscriptionReason.ALL_CANDIDATES_INVALID,
        call=call,
        attempted_track_count=3,
    )
    assert required.outcome == "transcription_required"


def test_transcript_artifact_source_specific_contract() -> None:
    common = {
        "video_id": "v1",
        "language": "en-US",
        "text_path": "transcripts/v1/request/canonical.txt",
        "source_content_hash": "a" * 64,
        "source_byte_count": 128,
        "content_hash": "b" * 64,
        "char_count": 42,
        "segment_count": 2,
        "normalization_version": "subtitle-normalization-v1",
        "created_at": NOW,
    }

    subtitle = TranscriptArtifact(
        **common,
        source_type=TranscriptSourceType.AUTO_SUBTITLE,
        requested_language="en",
        source_format=SubtitleFormat.VTT,
        timed_text_path="transcripts/v1/request/source.vtt",
        provider="youtube",
    )
    assert subtitle.requested_language == "en"

    whisper = TranscriptArtifact(
        **common,
        source_type=TranscriptSourceType.WHISPER,
        requested_language=None,
        source_format=None,
        timed_text_path=None,
        provider="mlx-whisper",
        model="mlx-community/whisper-large-v3-turbo",
    )
    assert whisper.source_format is None

    with pytest.raises(ValidationError, match="requested_language"):
        TranscriptArtifact(
            **common,
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            requested_language=None,
            source_format=SubtitleFormat.SRT,
            timed_text_path="transcripts/v1/request/source.srt",
            provider="youtube",
        )
    with pytest.raises(ValidationError, match="source_format"):
        TranscriptArtifact(
            **common,
            source_type=TranscriptSourceType.AUTO_SUBTITLE,
            requested_language="en",
            source_format=None,
            timed_text_path="transcripts/v1/request/source.vtt",
            provider="youtube",
        )
    with pytest.raises(ValidationError, match="timed_text_path"):
        TranscriptArtifact(
            **common,
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            requested_language="en",
            source_format=SubtitleFormat.JSON3,
            timed_text_path=None,
            provider="youtube",
        )
    with pytest.raises(ValidationError, match="must be None"):
        TranscriptArtifact(
            **common,
            source_type=TranscriptSourceType.WHISPER,
            requested_language="en",
            source_format=None,
            timed_text_path=None,
            provider="mlx-whisper",
        )
    with pytest.raises(ValidationError):
        TranscriptArtifact(
            **common,
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            requested_language="en",
            source_format=SubtitleFormat.JSON3,
            timed_text_path="../source.json3",
            provider="youtube",
        )
    with pytest.raises(ValidationError, match="unique"):
        TranscriptArtifact(
            **common,
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            requested_language="en",
            source_format=SubtitleFormat.JSON3,
            timed_text_path="transcripts/v1/request/source.json3",
            provider="youtube",
            quality_flags=(
                TranscriptQualityFlag.NON_SPEECH_MARKERS_PRESENT,
                TranscriptQualityFlag.NON_SPEECH_MARKERS_PRESENT,
            ),
        )


def test_transcript_public_contract_is_named_and_narrow() -> None:
    assert TranscriptFetchResult == TranscriptReady | TranscriptionRequired
    assert {item.value for item in SubtitleFormat} == {"json3", "vtt", "srt"}
    assert {item.value for item in TranscriptQualityFlag} == {
        "ROLLING_CUES_DEDUPED",
        "SPEAKER_LABELS_PRESENT",
        "NON_SPEECH_MARKERS_PRESENT",
    }
    assert {item.value for item in TranscriptionReason} == {
        "NO_TRACKS",
        "NO_MATCHING_LANGUAGE",
        "ALL_CANDIDATES_INVALID",
    }
    assert inspect.signature(TranscriptProvider.fetch).return_annotation == (
        "TranscriptFetchResult"
    )


def test_load_app_config_integration(tmp_path: Path) -> None:
    channels = _write_channels(tmp_path)
    settings = _write_settings(tmp_path)
    cfg = load_app_config(channels, settings)
    assert cfg.channels
    assert cfg.settings.local_scoring.model == "qwen3:8b"


def test_manual_invalid_threshold_and_timezone_error_paths(tmp_path: Path) -> None:
    """Manual-style checks: field paths present, secrets absent."""
    data = _minimal_settings_dict(thresholds={"summary_score": 11})
    path = _write_settings(tmp_path, data)
    with pytest.raises(ConfigError) as exc_info:
        load_settings(path)
    message = str(exc_info.value)
    assert "summary_score" in message or "thresholds" in message
    assert "sk-" not in message

    data2 = _minimal_settings_dict()
    data2["general"] = {
        "timezone": "Mars/Phobos",
        "output_language": "zh-CN",
        "transcript_languages": ["zh"],
    }
    path2 = _write_settings(tmp_path, data2)
    with pytest.raises(ConfigError) as exc_info2:
        load_settings(path2)
    msg2 = str(exc_info2.value)
    assert re.search(r"timezone|IANA", msg2, re.I)
    assert "sk-" not in msg2


# ---------------------------------------------------------------------------
# TASK-016A: intelligence configuration and provider-neutral Knowledge V2
# ---------------------------------------------------------------------------


def _knowledge_evidence(
    *,
    evidence_id: str = "e1",
    source: domain_mod.EvidenceSource = domain_mod.EvidenceSource.TRANSCRIPT_SAMPLE,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    timestamp_basis: str | None = None,
) -> domain_mod.KnowledgeEvidence:
    return domain_mod.KnowledgeEvidence(
        evidence_id=evidence_id,
        source=source,
        excerpt="Verified source excerpt",
        source_content_hash="a" * 64,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        timestamp_basis=timestamp_basis,
    )


def _knowledge_provenance(
    *,
    requested_mode: domain_mod.IntelligenceMode = domain_mod.IntelligenceMode.LOCAL_ONLY,
    executed_mode: domain_mod.KnowledgeExecutionMode = domain_mod.KnowledgeExecutionMode.LOCAL,
    provider: str = "ollama",
    model: str = "qwen3:8b",
    model_digest: str | None = MODEL_DIGEST,
    fallback_reason: domain_mod.KnowledgeFallbackReason | None = None,
) -> domain_mod.KnowledgeProvenance:
    return domain_mod.KnowledgeProvenance(
        requested_mode=requested_mode,
        executed_mode=executed_mode,
        fallback_reason=fallback_reason,
        provider=provider,
        model=model,
        model_digest=model_digest,
        output_language="zh-CN",
        transcript_content_hash="a" * 64,
        request_hash="b" * 64,
    )


def _knowledge_result(
    *,
    provenance: domain_mod.KnowledgeProvenance | None = None,
) -> domain_mod.KnowledgeResult:
    point = domain_mod.AnalysisPoint(
        text="Grounded product conclusion",
        kind=domain_mod.PointKind.INFERENCE,
        evidence_ids=("e1",),
    )
    content = domain_mod.KnowledgeContent(
        one_sentence_summary="一句话总结",
        summary_evidence_ids=("e1",),
        why_it_matters=point,
        core_points=(point,),
        knowledge_graph=domain_mod.KnowledgeGraph(
            topics=("AI 产品",),
            entities=("Example",),
        ),
    )
    return domain_mod.KnowledgeResult(
        content=content,
        evidence_registry=domain_mod.EvidenceRegistry(
            items=(_knowledge_evidence(),),
        ),
        provenance=provenance or _knowledge_provenance(),
    )


def test_intelligence_config_defaults_to_local_only_and_resolves_local_identity() -> None:
    settings = config_mod.AppSettings.model_validate(_minimal_settings_dict())

    assert settings.intelligence.mode is domain_mod.IntelligenceMode.LOCAL_ONLY
    assert settings.cloud.enabled is False
    assert settings.local_analysis.model == settings.local_scoring.model
    assert settings.local_analysis.base_url == settings.local_scoring.base_url
    assert (
        settings.local_analysis.expected_model_digest
        == settings.local_scoring.expected_model_digest
    )
    assert settings.local_analysis.model != ""

    example = load_settings(SETTINGS_EXAMPLE)
    assert example.intelligence.mode is domain_mod.IntelligenceMode.LOCAL_ONLY
    assert example.local_analysis.model == "qwen3:8b"
    assert example.local_analysis.expected_model_digest == MODEL_DIGEST


def test_local_analysis_can_diverge_from_scoring_with_concrete_cache_identity() -> None:
    analysis_digest = "sha256:" + "c" * 64
    settings = config_mod.AppSettings.model_validate(
        _minimal_settings_dict(
            intelligence={"mode": "local-only"},
            local_analysis={
                "model": "qwen3:14b",
                "expected_model_digest": analysis_digest,
                "max_output_tokens": 5000,
            },
        )
    )

    assert settings.local_scoring.model == "qwen3:8b"
    assert settings.local_analysis.model == "qwen3:14b"
    assert settings.local_analysis.expected_model_digest == analysis_digest
    assert settings.local_analysis.base_url == settings.local_scoring.base_url


def test_legacy_cloud_mapping_is_explicit_and_never_silently_expands_egress() -> None:
    legacy_cloud = config_mod.AppSettings.model_validate(
        _minimal_settings_dict(
            cloud={"enabled": True, "model": "gpt-4.1-mini"},
        )
    )
    assert legacy_cloud.intelligence.mode is domain_mod.IntelligenceMode.HYBRID

    with pytest.raises(ValidationError, match="cloud.enabled"):
        config_mod.AppSettings.model_validate(
            _minimal_settings_dict(
                intelligence={"mode": "local-only"},
                cloud={"enabled": True, "model": "gpt-4.1-mini"},
            )
        )
    with pytest.raises(ValidationError, match="cloud.enabled"):
        config_mod.AppSettings.model_validate(
            _minimal_settings_dict(
                intelligence={"mode": "hybrid"},
                cloud={"enabled": False},
            )
        )
    with pytest.raises(ValidationError):
        config_mod.AppSettings.model_validate(
            _minimal_settings_dict(intelligence={"mode": "LOCAL_ONLY"})
        )


def test_config_contracts_reject_unchecked_model_copy_updates() -> None:
    settings = config_mod.AppSettings.model_validate(_minimal_settings_dict())
    for contract in (
        settings,
        settings.intelligence,
        settings.local_analysis,
    ):
        with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
            contract.model_copy(update={})
        assert contract.model_copy() == contract


def test_named_overrides_revalidate_and_keep_legacy_cloud_mapping_unambiguous(
    tmp_path: Path,
) -> None:
    path = _write_settings(tmp_path)
    cloud_model = config_mod.CloudSettings(enabled=True, model="gpt-4.1-mini")

    by_mode = load_settings(
        path,
        overrides=config_mod.SettingsOverrides(
            intelligence=config_mod.IntelligenceSettings(mode="hybrid"),
            cloud=cloud_model,
        ),
    )
    assert by_mode.intelligence.mode is domain_mod.IntelligenceMode.HYBRID
    assert by_mode.cloud.enabled is True

    legacy_only = load_settings(
        path,
        overrides=config_mod.SettingsOverrides(cloud=cloud_model),
    )
    assert legacy_only.intelligence.mode is domain_mod.IntelligenceMode.HYBRID
    assert legacy_only.cloud.enabled is True

    with pytest.raises(ValidationError, match="cloud.enabled"):
        load_settings(
            path,
            overrides=config_mod.SettingsOverrides(
                intelligence=config_mod.IntelligenceSettings(mode="local-only"),
                cloud=cloud_model,
            ),
        )


def test_knowledge_v2_is_provider_neutral_grounded_and_opportunities_may_be_empty() -> None:
    result = _knowledge_result()

    assert result.schema_version == "knowledge-result-v2"
    assert result.provenance.executed_mode is domain_mod.KnowledgeExecutionMode.LOCAL
    assert result.content.product_opportunities == ()
    assert result.content.business_opportunities == ()
    assert result.content.action_recommendations == ()
    assert result.evidence_registry.items[0].evidence_id == "e1"
    assert "provider" not in domain_mod.KnowledgeContent.model_fields
    assert "evidence_registry" not in domain_mod.KnowledgeContent.model_fields

    content_payload = result.content.model_dump()
    content = domain_mod.KnowledgeContent.model_validate(content_payload)
    assert content.summary_evidence_ids == ("e1",)
    with pytest.raises(ValidationError):
        domain_mod.KnowledgeContent.model_validate(
            {**content_payload, "evidence_registry": result.evidence_registry.model_dump()}
        )
    with pytest.raises(ValidationError):
        domain_mod.KnowledgeContent.model_validate(result)
    with pytest.raises(ValidationError):
        domain_mod.KnowledgeContent.model_validate_json(result.model_dump_json())
    assert domain_mod.KnowledgeContent.model_validate(result.content) is result.content

    payload = result.model_dump()
    payload["content"]["summary_evidence_ids"] = ("missing",)
    with pytest.raises(ValidationError, match="unknown evidence"):
        domain_mod.KnowledgeResult.model_validate(payload)


def test_knowledge_v2_provenance_cross_validates_mode_model_and_versions() -> None:
    local = _knowledge_provenance()
    assert local.schema_version == "knowledge-result-v2"
    assert local.prompt_version == "knowledge-prompt-v2"
    assert local.sampling_version == "knowledge-sampling-v2"
    assert local.privacy_version == "knowledge-privacy-v2"

    with pytest.raises(ValidationError, match="local-only"):
        _knowledge_provenance(
            executed_mode=domain_mod.KnowledgeExecutionMode.CLOUD,
            provider="openai",
            model="gpt-4.1-mini",
            model_digest=None,
        )
    with pytest.raises(ValidationError, match="model_digest"):
        _knowledge_provenance(model_digest=None)

    cloud = _knowledge_provenance(
        requested_mode=domain_mod.IntelligenceMode.CLOUD,
        executed_mode=domain_mod.KnowledgeExecutionMode.CLOUD,
        provider="openai",
        model="gpt-4.1-mini",
        model_digest=None,
    )
    assert cloud.executed_mode is domain_mod.KnowledgeExecutionMode.CLOUD

    hybrid_fallback = _knowledge_provenance(
        requested_mode=domain_mod.IntelligenceMode.HYBRID,
        fallback_reason=domain_mod.KnowledgeFallbackReason.PROVIDER_UNAVAILABLE,
    )
    assert hybrid_fallback.fallback_reason is (
        domain_mod.KnowledgeFallbackReason.PROVIDER_UNAVAILABLE
    )
    with pytest.raises(ValidationError, match="fallback_reason"):
        _knowledge_provenance(requested_mode=domain_mod.IntelligenceMode.HYBRID)
    with pytest.raises(ValidationError, match="fallback_reason"):
        _knowledge_provenance(
            fallback_reason=domain_mod.KnowledgeFallbackReason.PROVIDER_TIMEOUT,
        )


def test_knowledge_evidence_timestamps_are_registered_and_never_half_present() -> None:
    timed = _knowledge_evidence(
        start_seconds=10.0,
        end_seconds=12.5,
        timestamp_basis="timed-subtitle",
    )
    assert timed.start_seconds == 10.0
    assert timed.end_seconds == 12.5

    with pytest.raises(ValidationError, match="together"):
        _knowledge_evidence(start_seconds=10.0, timestamp_basis="timed-subtitle")
    with pytest.raises(ValidationError, match="transcript"):
        _knowledge_evidence(
            source=domain_mod.EvidenceSource.TITLE,
            start_seconds=10.0,
            end_seconds=12.5,
            timestamp_basis="timed-subtitle",
        )
    with pytest.raises(ValidationError, match="end_seconds"):
        _knowledge_evidence(
            start_seconds=12.5,
            end_seconds=10.0,
            timestamp_basis="timed-subtitle",
        )
    with pytest.raises(ValidationError, match="timed-subtitle"):
        _knowledge_evidence(start_seconds=10.0, end_seconds=12.5)


def test_knowledge_evidence_rejects_non_finite_timestamps_at_all_boundaries() -> None:
    for field_name in ("start_seconds", "end_seconds"):
        for value in (float("nan"), float("inf"), float("-inf")):
            values = {
                "start_seconds": 10.0,
                "end_seconds": 12.5,
                field_name: value,
            }
            with pytest.raises(ValidationError):
                _knowledge_evidence(
                    start_seconds=values["start_seconds"],
                    end_seconds=values["end_seconds"],
                    timestamp_basis="timed-subtitle",
                )

    overflow_json = (
        '{"evidence_id":"e1","source":"transcript_sample",'
        '"excerpt":"verified","source_content_hash":"'
        + "a" * 64
        + '","start_seconds":0.0,"end_seconds":1e999,'
        '"timestamp_basis":"timed-subtitle"}'
    )
    with pytest.raises(ValidationError):
        domain_mod.KnowledgeEvidence.model_validate_json(overflow_json)

    valid = _knowledge_evidence(
        start_seconds=10.0,
        end_seconds=12.5,
        timestamp_basis="timed-subtitle",
    )
    restored = domain_mod.KnowledgeEvidence.model_validate_json(valid.model_dump_json())
    assert restored == valid


def test_weekly_knowledge_v2_is_provider_neutral_and_source_grounded() -> None:
    source = domain_mod.WeeklyKnowledgeSource(
        video_id="video-1",
        evidence_ids=("e1",),
    )
    conclusion = domain_mod.WeeklyKnowledgePoint(
        text="本周产品方向正在收敛",
        sources=(source,),
    )
    weekly = domain_mod.WeeklyKnowledgeResult(
        key_conclusions=(conclusion,),
        repeated_themes=(conclusion,),
        next_week_questions=("下周需要验证什么？",),
        provenance=domain_mod.WeeklyKnowledgeProvenance(
            requested_mode=domain_mod.IntelligenceMode.LOCAL_ONLY,
            executed_mode=domain_mod.KnowledgeExecutionMode.LOCAL,
            provider="ollama",
            model="qwen3:8b",
            model_digest=MODEL_DIGEST,
            output_language="zh-CN",
            input_knowledge_hash="c" * 64,
            request_hash="d" * 64,
        ),
    )

    assert weekly.schema_version == "weekly-knowledge-result-v2"
    assert weekly.product_opportunities == ()
    assert weekly.business_opportunities == ()
    assert weekly.key_conclusions[0].sources[0].video_id == "video-1"
    with pytest.raises(ValidationError, match="unique"):
        domain_mod.WeeklyKnowledgeSource(
            video_id="video-1",
            evidence_ids=("e1", "e1"),
        )


def test_knowledge_v2_contracts_reject_unchecked_updates() -> None:
    result = _knowledge_result()
    source = domain_mod.WeeklyKnowledgeSource(video_id="video-1", evidence_ids=("e1",))
    weekly_point = domain_mod.WeeklyKnowledgePoint(text="Conclusion", sources=(source,))
    weekly = domain_mod.WeeklyKnowledgeResult(
        key_conclusions=(weekly_point,),
        provenance=domain_mod.WeeklyKnowledgeProvenance(
            requested_mode=domain_mod.IntelligenceMode.CLOUD,
            executed_mode=domain_mod.KnowledgeExecutionMode.CLOUD,
            provider="openai",
            model="gpt-4.1-mini",
            model_digest=None,
            output_language="zh-CN",
            input_knowledge_hash="c" * 64,
            request_hash="d" * 64,
        ),
    )
    for contract in (result, result.provenance, result.evidence_registry, weekly):
        with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
            contract.model_copy(update={})


def test_weekly_knowledge_v2_rejects_ambiguous_routing_provenance() -> None:
    common = {
        "provider": "ollama",
        "model": "qwen3:8b",
        "model_digest": MODEL_DIGEST,
        "output_language": "zh-CN",
        "input_knowledge_hash": "c" * 64,
        "request_hash": "d" * 64,
    }
    with pytest.raises(ValidationError, match="local-only"):
        domain_mod.WeeklyKnowledgeProvenance(
            requested_mode=domain_mod.IntelligenceMode.LOCAL_ONLY,
            executed_mode=domain_mod.KnowledgeExecutionMode.CLOUD,
            **common,
        )
    with pytest.raises(ValidationError, match="fallback_reason"):
        domain_mod.WeeklyKnowledgeProvenance(
            requested_mode=domain_mod.IntelligenceMode.HYBRID,
            executed_mode=domain_mod.KnowledgeExecutionMode.LOCAL,
            **common,
        )
    hybrid = domain_mod.WeeklyKnowledgeProvenance(
        requested_mode=domain_mod.IntelligenceMode.HYBRID,
        executed_mode=domain_mod.KnowledgeExecutionMode.LOCAL,
        fallback_reason=domain_mod.KnowledgeFallbackReason.BUDGET_EXHAUSTED,
        **common,
    )
    assert hybrid.fallback_reason is domain_mod.KnowledgeFallbackReason.BUDGET_EXHAUSTED
