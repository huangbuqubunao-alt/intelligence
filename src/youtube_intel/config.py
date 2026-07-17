"""Configuration loading and validation for YouTube Intelligence Agent.

Priority: built-in defaults < YAML < explicit CLI overrides.
Secrets are referenced only by environment variable name; values are never read.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml  # type: ignore[import-untyped]
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

_ENV_NAME_RE: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REDACTED: Final = "[REDACTED]"
_SENSITIVE_CONFIG_FIELDS: Final = frozenset({"api_key_env"})
_LOOPBACK_HTTP_HOSTS: Final = frozenset({"127.0.0.1", "localhost", "::1"})
# extra=forbid at every boundary; not strict so YAML ints may coerce to floats.
_FROZEN: Final = ConfigDict(extra="forbid", frozen=True)


class _ConfigModel(BaseModel):
    model_config = _FROZEN


# ---------------------------------------------------------------------------
# Path validators (pure; no filesystem writes)
# ---------------------------------------------------------------------------


def _reject_project_relative_path(value: str, *, field_name: str) -> str:
    if not value or value != value.strip():
        msg = f"{field_name} must be a non-empty path without surrounding whitespace"
        raise ValueError(msg)
    path = Path(value)
    if path.is_absolute():
        msg = f"{field_name} must be a project-root-relative path, not absolute"
        raise ValueError(msg)
    posix = PurePosixPath(value.replace("\\", "/"))
    if posix.is_absolute():
        msg = f"{field_name} must be a project-root-relative path, not absolute"
        raise ValueError(msg)
    if any(part == ".." for part in posix.parts):
        msg = f"{field_name} must not contain '..'"
        raise ValueError(msg)
    if any(part == "" for part in posix.parts):
        msg = f"{field_name} must not contain empty path segments"
        raise ValueError(msg)
    collapsed_parts = _collapse_parts(posix.parts)
    if not collapsed_parts or ".." in collapsed_parts:
        msg = f"{field_name} escapes the project root after normalization"
        raise ValueError(msg)
    return value


def _collapse_parts(parts: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for part in parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not out:
                out.append("..")
            else:
                out.pop()
            continue
        out.append(part)
    return out


def _reject_absolute_vault_root(value: str) -> str:
    if not value or value != value.strip():
        msg = "vault_root must be a non-empty absolute path without surrounding whitespace"
        raise ValueError(msg)
    path = Path(value)
    if not path.is_absolute():
        msg = "vault_root must be an absolute path"
        raise ValueError(msg)
    return value


def _reject_safe_relative_subdir(value: str, *, vault_root: str | None = None) -> str:
    if not value or value != value.strip():
        msg = "vault_subdir must be a non-empty relative path without surrounding whitespace"
        raise ValueError(msg)
    path = Path(value)
    if path.is_absolute():
        msg = "vault_subdir must be a relative path, not absolute"
        raise ValueError(msg)
    posix = PurePosixPath(value.replace("\\", "/"))
    if posix.is_absolute() or any(part == ".." for part in posix.parts):
        msg = "vault_subdir must not be absolute or contain '..'"
        raise ValueError(msg)
    if any(part == "" for part in posix.parts):
        msg = "vault_subdir must not contain empty path segments"
        raise ValueError(msg)
    collapsed = PurePosixPath(*_collapse_parts(posix.parts))
    if collapsed.is_absolute() or ".." in collapsed.parts or str(collapsed) in {"", "."}:
        msg = "vault_subdir escapes vault_root after normalization"
        raise ValueError(msg)
    if vault_root is not None:
        root = Path(vault_root)
        # Pure join check without resolving symlinks that may not exist
        joined = (root / value).resolve(strict=False)
        try:
            joined.relative_to(root.resolve(strict=False))
        except ValueError as exc:
            msg = "vault_subdir must remain inside vault_root after resolution"
            raise ValueError(msg) from exc
    return value


def _validate_iana_timezone(value: str) -> str:
    if not value or value != value.strip():
        msg = "timezone must be a non-empty IANA timezone name"
        raise ValueError(msg)
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, KeyError) as exc:
        msg = f"invalid IANA timezone: {value}"
        raise ValueError(msg) from exc
    return value


def _validate_env_var_name(value: str) -> str:
    # Never embed the rejected input in the message: callers may paste secrets here.
    if not isinstance(value, str) or not _ENV_NAME_RE.fullmatch(value):
        msg = (
            "api_key_env must match [A-Za-z_][A-Za-z0-9_]* "
            "(environment variable name only; values are never stored)"
        )
        raise ValueError(msg)
    return value


def _validate_loopback_http_base_url(value: str) -> str:
    if not value or value != value.strip():
        msg = "local_scoring.base_url must be a non-empty URL without surrounding whitespace"
        raise ValueError(msg)
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        msg = "local_scoring.base_url must contain a valid loopback port"
        raise ValueError(msg) from exc
    if parsed.scheme != "http":
        msg = "local_scoring.base_url must use http"
        raise ValueError(msg)
    if (
        "@" in parsed.netloc
        or parsed.hostname not in _LOOPBACK_HTTP_HOSTS
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        msg = (
            "local_scoring.base_url must be a loopback http origin without "
            "userinfo, path, query, or fragment"
        )
        raise ValueError(msg)
    if port is not None and not 0 < port <= 65535:
        msg = "local_scoring.base_url port must be in 1..65535"
        raise ValueError(msg)
    return value


def _redact_sensitive_validation_error(exc: ValidationError) -> ValidationError:
    """Return a ValidationError that never echoes api_key_env input values."""
    line_errors: list[dict[str, Any]] = []
    changed = False
    for err in exc.errors(include_url=False):
        loc = err.get("loc", ())
        if any(part in _SENSITIVE_CONFIG_FIELDS for part in loc):
            changed = True
            line_errors.append(
                {
                    "type": "value_error",
                    "loc": loc,
                    "msg": (
                        "api_key_env must match [A-Za-z_][A-Za-z0-9_]* "
                        "(environment variable name only; values are never stored)"
                    ),
                    "input": _REDACTED,
                    "ctx": {"error": "invalid environment variable name"},
                }
            )
        else:
            line_errors.append(
                {
                    "type": err["type"],
                    "loc": err["loc"],
                    "msg": err["msg"],
                    "input": err.get("input"),
                    **(
                        {"ctx": err["ctx"]}
                        if "ctx" in err and err["ctx"] is not None
                        else {}
                    ),
                }
            )
    if not changed:
        return exc
    return ValidationError.from_exception_data(exc.title, line_errors)  # type: ignore[arg-type]


def _format_config_error(prefix: str, path: Path, exc: BaseException) -> str:
    if isinstance(exc, ValidationError):
        exc = _redact_sensitive_validation_error(exc)
    text = str(exc)
    # Defense in depth: never leave raw secret-shaped tokens in ConfigError text.
    return f"{prefix} for {path}: {text}"


def _dedupe_preserve_order(items: list[str], *, field_name: str) -> tuple[str, ...]:
    if not items:
        msg = f"{field_name} must be a non-empty list"
        raise ValueError(msg)
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item or item != item.strip():
            msg = f"{field_name} items must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        if item in seen:
            msg = f"{field_name} must not contain duplicates: {item}"
            raise ValueError(msg)
        seen.add(item)
        out.append(item)
    return tuple(out)


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


class ChannelConfig(_ConfigModel):
    channel_id: str = Field(min_length=1)
    enabled: bool = True
    priority: int = Field(default=50, ge=0, le=100)

    @field_validator("channel_id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        if not value or value != value.strip():
            msg = "channel_id must be non-empty without surrounding whitespace"
            raise ValueError(msg)
        return value


class ChannelsFile(_ConfigModel):
    channels: tuple[ChannelConfig, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_and_sorted(self) -> ChannelsFile:
        ids = [c.channel_id for c in self.channels]
        if len(ids) != len(set(ids)):
            msg = "channel_id values must be unique"
            raise ValueError(msg)
        ordered = tuple(
            sorted(self.channels, key=lambda c: (-c.priority, c.channel_id))
        )
        if self.channels != ordered:
            return self.model_copy(update={"channels": ordered})
        return self


class GeneralSettings(_ConfigModel):
    timezone: str = "Asia/Shanghai"
    output_language: str = "zh-CN"
    transcript_languages: tuple[str, ...]

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str) -> str:
        return _validate_iana_timezone(value)

    @field_validator("output_language")
    @classmethod
    def _output_lang(cls, value: str) -> str:
        if not value or value != value.strip():
            msg = "output_language must be a non-empty language tag"
            raise ValueError(msg)
        return value

    @field_validator("transcript_languages", mode="before")
    @classmethod
    def _langs(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            msg = "transcript_languages must be a list of language tags"
            raise ValueError(msg)
        return _dedupe_preserve_order(list(value), field_name="transcript_languages")


class ExecutionSettings(_ConfigModel):
    worker_concurrency: int = 1
    max_video_duration_minutes: int = Field(default=180, gt=0)

    @field_validator("worker_concurrency")
    @classmethod
    def _concurrency(cls, value: int) -> int:
        if value != 1:
            msg = "worker_concurrency must be 1 in V1"
            raise ValueError(msg)
        return value


class ThresholdSettings(_ConfigModel):
    summary_score: float = Field(default=7.0, ge=0, le=10)


class WeeklySettings(_ConfigModel):
    top_n: int = Field(default=10, ge=1, le=100)


class RetrySettings(_ConfigModel):
    max_attempts: int = Field(default=3, gt=0)
    base_delay_seconds: float = Field(default=2, gt=0)
    max_delay_seconds: float = Field(default=60, gt=0)
    jitter_ratio: float = Field(default=0.2, ge=0, le=1)

    @model_validator(mode="after")
    def _delay_order(self) -> RetrySettings:
        if self.base_delay_seconds > self.max_delay_seconds:
            msg = "base_delay_seconds must be <= max_delay_seconds"
            raise ValueError(msg)
        return self


class TimeoutSettings(_ConfigModel):
    http_seconds: float = Field(default=30, gt=0)
    local_model_seconds: float = Field(default=300, gt=0)
    cloud_model_seconds: float = Field(default=120, gt=0)


class TranscriptionSettings(_ConfigModel):
    model: str = "mlx-community/whisper-large-v3-turbo"
    model_revision: Literal["a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"] = (
        "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb"
    )
    model_weights_bytes: Literal[1_613_977_612] = 1_613_977_612
    model_weights_sha256: Literal[
        "951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6"
    ] = "951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6"
    parameter_policy_version: Literal["mlx-whisper-v1"] = "mlx-whisper-v1"
    task: Literal["transcribe"] = "transcribe"
    language_hint: str | None = None
    temperature: float = 0.0
    compression_ratio_threshold: float = 2.4
    logprob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    condition_on_previous_text: Literal[True] = True
    word_timestamps: Literal[False] = False
    initial_prompt: None = None
    fp16: Literal[True] = True
    min_free_disk_gib: int = Field(default=8, gt=0)
    min_available_memory_gib: int = Field(default=6, gt=0)
    max_audio_bytes: int = Field(default=2_000_000_000, gt=0)

    @field_validator("model")
    @classmethod
    def _model(cls, value: str) -> str:
        if not value or value != value.strip():
            msg = "transcription.model must be a non-empty model identifier"
            raise ValueError(msg)
        return value

    @field_validator("language_hint")
    @classmethod
    def _language_hint(cls, value: str | None) -> str | None:
        if value is not None and (not value or value != value.strip()):
            msg = "transcription.language_hint must be None or a non-empty language tag"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _fixed_decode_parameters(self) -> TranscriptionSettings:
        if (
            self.temperature != 0.0
            or self.compression_ratio_threshold != 2.4
            or self.logprob_threshold != -1.0
            or self.no_speech_threshold != 0.6
        ):
            msg = "transcription decode parameters are fixed by mlx-whisper-v1"
            raise ValueError(msg)
        return self


class LocalScoringSettings(_ConfigModel):
    model: str = Field(min_length=1)
    base_url: str = "http://127.0.0.1:11434"
    expected_model_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_output_tokens: int = Field(default=1200, gt=0)
    max_transcript_chars: int = Field(default=30000, ge=3)
    max_description_chars: int = Field(default=4000, ge=0, le=20_000)

    @field_validator("model")
    @classmethod
    def _model(cls, value: str) -> str:
        if not value or value != value.strip():
            msg = "local_scoring.model must be a non-empty Ollama model identifier"
            raise ValueError(msg)
        return value

    @field_validator("base_url")
    @classmethod
    def _base_url(cls, value: str) -> str:
        return _validate_loopback_http_base_url(value)

    @field_validator("expected_model_digest")
    @classmethod
    def _expected_model_digest(cls, value: str) -> str:
        if value != value.strip():
            msg = "local_scoring.expected_model_digest must not contain surrounding whitespace"
            raise ValueError(msg)
        return value


class CloudSettings(_ConfigModel):
    enabled: bool = False
    provider: Literal["openai"] = "openai"
    model: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    max_calls_per_run: int = Field(default=5, gt=0, le=5)
    max_input_tokens_per_video: int = Field(default=30000, gt=0, le=30000)

    @field_validator("api_key_env")
    @classmethod
    def _env_name(cls, value: str) -> str:
        return _validate_env_var_name(value)

    @model_validator(mode="after")
    def _enabled_requires_model(self) -> Self:
        if self.enabled:
            if self.model is None or not str(self.model).strip():
                msg = "cloud.model is required when cloud.enabled is true"
                raise ValueError(msg)
        return self

    @model_validator(mode="wrap")
    @classmethod
    def _redact_sensitive_validation(cls, data: Any, handler: Any) -> Self:
        try:
            return handler(data)  # type: ignore[no-any-return]
        except ValidationError as exc:
            raise _redact_sensitive_validation_error(exc) from None

    def __repr__(self) -> str:
        # Valid instances only store env var names; never values.
        return (
            "CloudSettings("
            f"enabled={self.enabled!r}, provider={self.provider!r}, "
            f"model={self.model!r}, api_key_env={self.api_key_env!r}, "
            f"max_calls_per_run={self.max_calls_per_run!r}, "
            f"max_input_tokens_per_video={self.max_input_tokens_per_video!r})"
        )


class StorageSettings(_ConfigModel):
    data_dir: str = "data"
    logs_dir: str = "logs"
    templates_dir: str = "templates"
    vault_root: str
    vault_subdir: str

    @field_validator("data_dir", "logs_dir", "templates_dir")
    @classmethod
    def _project_paths(cls, value: str, info: ValidationInfo) -> str:
        return _reject_project_relative_path(value, field_name=info.field_name or "path")

    @field_validator("vault_root")
    @classmethod
    def _vault_root(cls, value: str) -> str:
        return _reject_absolute_vault_root(value)

    @model_validator(mode="after")
    def _vault_subdir_bounds(self) -> StorageSettings:
        _reject_safe_relative_subdir(self.vault_subdir, vault_root=self.vault_root)
        return self


class AppSettings(_ConfigModel):
    general: GeneralSettings
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)
    weekly: WeeklySettings = Field(default_factory=WeeklySettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    timeouts: TimeoutSettings = Field(default_factory=TimeoutSettings)
    transcription: TranscriptionSettings = Field(default_factory=TranscriptionSettings)
    local_scoring: LocalScoringSettings
    cloud: CloudSettings = Field(default_factory=CloudSettings)
    storage: StorageSettings

    @model_validator(mode="wrap")
    @classmethod
    def _redact_sensitive_validation(cls, data: Any, handler: Any) -> Self:
        try:
            return handler(data)  # type: ignore[no-any-return]
        except ValidationError as exc:
            raise _redact_sensitive_validation_error(exc) from None


class SettingsOverrides(_ConfigModel):
    """Named, validated CLI override surface. No free-form dicts."""

    general: GeneralSettings | None = None
    execution: ExecutionSettings | None = None
    thresholds: ThresholdSettings | None = None
    weekly: WeeklySettings | None = None
    retry: RetrySettings | None = None
    timeouts: TimeoutSettings | None = None
    transcription: TranscriptionSettings | None = None
    local_scoring: LocalScoringSettings | None = None
    cloud: CloudSettings | None = None
    storage: StorageSettings | None = None


class AppConfig(_ConfigModel):
    channels: tuple[ChannelConfig, ...]
    settings: AppSettings


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Configuration load or validation failure with field-level detail."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Internal YAML mapping load via SafeLoader only; not part of the public contract."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config file: {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"config root in {path} must be a mapping")
    return data


def load_channels(path: Path) -> tuple[ChannelConfig, ...]:
    raw = _load_yaml_mapping(path)
    try:
        channels_file = ChannelsFile.model_validate(raw)
    except Exception as exc:
        raise ConfigError(_format_config_error("channels validation failed", path, exc)) from exc
    return channels_file.channels


def _apply_overrides(settings: AppSettings, overrides: SettingsOverrides) -> AppSettings:
    updates: dict[str, Any] = {}
    for name in (
        "general",
        "execution",
        "thresholds",
        "weekly",
        "retry",
        "timeouts",
        "transcription",
        "local_scoring",
        "cloud",
        "storage",
    ):
        value = getattr(overrides, name)
        if value is not None:
            updates[name] = value
    if not updates:
        return settings
    return settings.model_copy(update=updates)


def load_settings(
    path: Path,
    *,
    overrides: SettingsOverrides | None = None,
) -> AppSettings:
    raw = _load_yaml_mapping(path)
    try:
        settings = AppSettings.model_validate(raw)
    except Exception as exc:
        raise ConfigError(_format_config_error("settings validation failed", path, exc)) from exc
    if overrides is not None:
        settings = _apply_overrides(settings, overrides)
    return settings


def load_app_config(
    channels_path: Path,
    settings_path: Path,
    *,
    overrides: SettingsOverrides | None = None,
) -> AppConfig:
    channels = load_channels(channels_path)
    settings = load_settings(settings_path, overrides=overrides)
    return AppConfig(channels=channels, settings=settings)


__all__ = [
    "ChannelConfig",
    "ChannelsFile",
    "GeneralSettings",
    "ExecutionSettings",
    "ThresholdSettings",
    "WeeklySettings",
    "RetrySettings",
    "TimeoutSettings",
    "TranscriptionSettings",
    "LocalScoringSettings",
    "CloudSettings",
    "StorageSettings",
    "AppSettings",
    "SettingsOverrides",
    "AppConfig",
    "ConfigError",
    "load_channels",
    "load_settings",
    "load_app_config",
]
