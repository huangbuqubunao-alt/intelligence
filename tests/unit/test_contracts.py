"""Contract tests for configuration and domain models (TASK-002)."""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from youtube_intel import config as config_mod
from youtube_intel import domain as domain_mod
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
    WeeklySettings,
    load_app_config,
    load_channels,
    load_settings,
)
from youtube_intel.domain import (
    JOB_TRANSITIONS,
    PIPELINE_TRANSITIONS,
    SCORE_DIMENSION_NAMES,
    AnalysisInput,
    AnalysisPoint,
    AnalysisResult,
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
    ScoringInput,
    ScoringProvider,
    SourceProvider,
    SummaryProvider,
    TranscriptArtifact,
    TranscriptProvider,
    TranscriptSourceType,
    VideoMetadata,
    WeeklyReportInput,
    WeeklyReportItem,
    can_transition_job,
    can_transition_pipeline,
    pipeline_after_job_failure,
    transition_job,
    transition_pipeline,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANNELS_EXAMPLE = REPO_ROOT / "config" / "channels.example.yaml"
SETTINGS_EXAMPLE = REPO_ROOT / "config" / "settings.example.yaml"
NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)


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
        "local_scoring": {"model": "qwen2.5:14b"},
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
        "reason": "solid product insight",
        "topics": ("ai", "product"),
        "should_summarize": True,
        "provider": "ollama",
        "model": "qwen2.5:14b",
        "prompt_version": "v1",
        "request_hash": "abc",
    }
    data.update(kwargs)
    return ScoreResult.model_validate(data)


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
    scoring = LocalScoringSettings(model="qwen2.5:14b")
    assert scoring.temperature == 0.0
    assert scoring.max_output_tokens == 1200
    assert scoring.max_transcript_chars == 30000
    with pytest.raises(ValidationError):
        LocalScoringSettings(model="qwen", temperature=2.1)
    with pytest.raises(ValidationError):
        LocalScoringSettings(model="qwen", max_output_tokens=0)


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
    cloud = CloudSettings(enabled=True, model="gpt-test", api_key_env="OPENAI_API_KEY")
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


def test_app_settings_repr_has_no_secret_values(tmp_path: Path) -> None:
    settings = load_settings(SETTINGS_EXAMPLE)
    dumped = settings.model_dump()
    blob = repr(settings) + repr(dumped)
    assert "sk-" not in blob
    assert "OPENAI_API_KEY" in blob


# ---------------------------------------------------------------------------
# Domain objects and provider contracts
# ---------------------------------------------------------------------------


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


def test_analysis_result_structure_and_evidence_refs() -> None:
    evidence = (
        EvidenceExcerpt(
            evidence_id="e1",
            source=EvidenceSource.TRANSCRIPT,
            excerpt="quoted text",
            start_seconds=1.0,
            end_seconds=2.0,
        ),
    )
    point = AnalysisPoint(
        text="A fact",
        kind=PointKind.FACT,
        evidence_ids=("e1",),
    )
    result = AnalysisResult(
        schema_version="1",
        one_sentence_summary="Summary",
        core_points=(
            AnalysisPoint(text="Core", kind=PointKind.INFERENCE, evidence_ids=("e1",)),
        ),
        key_facts=(point,),
        keywords=("ai",),
        evidence=evidence,
        provider="openai",
        model="gpt",
        prompt_version="v1",
        request_hash="h1",
    )
    assert len(result.core_points) == 1

    with pytest.raises(ValidationError, match="unknown evidence"):
        AnalysisResult(
            schema_version="1",
            one_sentence_summary="Summary",
            core_points=(
                AnalysisPoint(text="Core", kind=PointKind.INFERENCE, evidence_ids=("missing",)),
            ),
            keywords=("ai",),
            evidence=evidence,
            provider="openai",
            model="gpt",
            prompt_version="v1",
            request_hash="h1",
        )

    with pytest.raises(ValidationError, match="kind=fact"):
        AnalysisResult(
            schema_version="1",
            one_sentence_summary="Summary",
            core_points=(AnalysisPoint(text="Core", kind=PointKind.INFERENCE),),
            key_facts=(AnalysisPoint(text="Not fact", kind=PointKind.INFERENCE),),
            keywords=("ai",),
            evidence=(),
            provider="openai",
            model="gpt",
            prompt_version="v1",
            request_hash="h1",
        )

    with pytest.raises(ValidationError):
        EvidenceExcerpt(
            evidence_id="e2",
            source=EvidenceSource.METADATA,
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
        transcript_text="text",
        transcript_content_hash="h",
        language="zh",
        request_hash="rh",
    )
    analysis_in = AnalysisInput(
        video=_video(),
        transcript_text="text",
        transcript_content_hash="h",
        score=_score(),
        language="zh",
        request_hash="rh2",
    )
    assert scoring_in.language == "zh"
    assert analysis_in.score.score == 8.0

    na = NotAvailable(
        reason_code=NotAvailableReason.NO_CONTENT,
        message="empty",
        retryable=False,
        call=_call(),
    )
    assert na.reason_code is NotAvailableReason.NO_CONTENT

    note = NoteRef(kind=NoteKind.VIDEO, relative_path="Videos/x.md", content_hash="c")
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
    # Exact set from System Design §12 — no unapproved extras.
    assert codes == {
        "TRANSIENT_NETWORK",
        "RATE_LIMITED",
        "PROVIDER_UNAVAILABLE",
        "INVALID_RESPONSE",
        "CONTENT_UNAVAILABLE",
        "CONFIG_INVALID",
        "PERMISSION_DENIED",
        "LOCAL_RESOURCE",
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
            language_preferences: object,
        ) -> TranscriptArtifact | NotAvailable:
            return NotAvailable(
                reason_code=NotAvailableReason.NO_MATCHING_LANGUAGE,
                message="none",
                retryable=False,
                call=_call(),
            )

    assert isinstance(FakeTranscript(), TranscriptProvider)

    class FakeScore:
        def score(self, scoring_input: ScoringInput) -> ScoreResult:
            return _score(request_hash=scoring_input.request_hash)

    assert isinstance(FakeScore(), ScoringProvider)

    class FakeSummary:
        def summarize(self, analysis_input: AnalysisInput) -> AnalysisResult:
            return AnalysisResult(
                schema_version="1",
                one_sentence_summary="s",
                core_points=(AnalysisPoint(text="c", kind=PointKind.INFERENCE),),
                keywords=("k",),
                evidence=(),
                provider="p",
                model="m",
                prompt_version="v",
                request_hash=analysis_input.request_hash,
            )

    assert isinstance(FakeSummary(), SummaryProvider)

    class FakeSink:
        def upsert_video_note(
            self,
            video: VideoMetadata,
            transcript: TranscriptArtifact,
            score: ScoreResult,
            analysis: AnalysisResult | None,
        ) -> NoteRef:
            return NoteRef(kind=NoteKind.VIDEO, relative_path="a.md", content_hash="h")

        def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef:
            return NoteRef(kind=NoteKind.WEEKLY, relative_path="w.md", content_hash="h")

    assert isinstance(FakeSink(), KnowledgeSink)


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
        transcript_text="hello",
        transcript_content_hash="h",
        language="en",
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
        text_path="data/transcripts/v1/canonical.txt",
        content_hash="hash",
        char_count=10,
        segment_count=1,
        provider="youtube",
        created_at=NOW,
    )
    assert call.diagnostics[0].code == "INFO"
    assert artifact.source_type is TranscriptSourceType.MANUAL_SUBTITLE


def test_load_app_config_integration(tmp_path: Path) -> None:
    channels = _write_channels(tmp_path)
    settings = _write_settings(tmp_path)
    cfg = load_app_config(channels, settings)
    assert cfg.channels
    assert cfg.settings.local_scoring.model == "qwen2.5:14b"


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
