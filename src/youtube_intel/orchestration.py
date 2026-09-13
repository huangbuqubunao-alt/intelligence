"""Safe product-orchestration contracts.

This module deliberately owns configuration and scheduled-work state only.  It
does not create VideoRecord authority, call providers, or bypass RuntimeOperations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo


class SourceType(str, Enum):
    CHANNEL = "CHANNEL"
    VIDEO_URL = "VIDEO_URL"


class ProcessingPolicy(str, Enum):
    DISCOVER_ONLY = "DISCOVER_ONLY"
    STANDARD_INTELLIGENCE = "STANDARD_INTELLIGENCE"
    FULL_INTELLIGENCE = "FULL_INTELLIGENCE"

    @property
    def deep_analysis_requested(self) -> bool:
        return self is ProcessingPolicy.FULL_INTELLIGENCE


class AutomationTargetType(str, Enum):
    SOURCE_CHECK = "SOURCE_CHECK"
    WEEKLY_GENERATION = "WEEKLY_GENERATION"


class ScheduleFrequency(str, Enum):
    MANUAL = "MANUAL"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class AutomationRunStatus(str, Enum):
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"
    BLOCKED = "BLOCKED"


class SourceNormalizationError(ValueError):
    """The submitted URL is not an accepted deterministic YouTube identity."""


@dataclass(frozen=True, slots=True)
class NormalizedSource:
    source_type: SourceType
    canonical_url: str
    channel_id: str | None
    video_id: str | None


_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
_HANDLE = re.compile(r"^@[A-Za-z0-9._-]{3,100}$")
_CUSTOM_CHANNEL = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def normalize_source_url(value: str) -> NormalizedSource:
    """Validate a YouTube channel/video URL without network access or redirects."""

    raw = value.strip()
    if len(raw) > 2048 or not raw:
        raise SourceNormalizationError("a non-empty YouTube URL is required")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
        "youtu.be",
    }:
        raise SourceNormalizationError("only explicit HTTPS YouTube URLs are supported")
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if host == "youtu.be":
        video_id = path.lstrip("/")
        if _VIDEO_ID.fullmatch(video_id):
            return NormalizedSource(
                SourceType.VIDEO_URL,
                f"https://www.youtube.com/watch?v={video_id}",
                None,
                video_id,
            )
        raise SourceNormalizationError("the short YouTube URL has no valid video id")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if path == "/watch":
        video_id = query.get("v", [""])[0]
        if _VIDEO_ID.fullmatch(video_id):
            return NormalizedSource(
                SourceType.VIDEO_URL,
                f"https://www.youtube.com/watch?v={video_id}",
                None,
                video_id,
            )
        raise SourceNormalizationError("the YouTube video URL has no valid video id")
    if path.startswith("/shorts/") or path.startswith("/live/"):
        video_id = path.split("/")[2] if len(path.split("/")) == 3 else ""
        if _VIDEO_ID.fullmatch(video_id):
            return NormalizedSource(
                SourceType.VIDEO_URL,
                f"https://www.youtube.com/watch?v={video_id}",
                None,
                video_id,
            )
        raise SourceNormalizationError("the YouTube video URL has no valid video id")
    if path.startswith("/channel/"):
        channel_id = path.removeprefix("/channel/")
        if _CHANNEL_ID.fullmatch(channel_id):
            return NormalizedSource(
                SourceType.CHANNEL,
                f"https://www.youtube.com/channel/{channel_id}",
                channel_id,
                None,
            )
        raise SourceNormalizationError("the YouTube channel id is invalid")
    candidate = path.lstrip("/")
    if (
        _HANDLE.fullmatch(candidate)
        or path.startswith("/c/")
        and _CUSTOM_CHANNEL.fullmatch(path.removeprefix("/c/"))
    ):
        normalized = (
            candidate if candidate.startswith("@") else f"c/{path.removeprefix('/c/')}"
        )
        return NormalizedSource(
            SourceType.CHANNEL, f"https://www.youtube.com/{normalized}", None, None
        )
    raise SourceNormalizationError("unsupported YouTube URL form")


def validate_policy(policy: ProcessingPolicy, *, deep_analysis_eligible: bool) -> None:
    if policy.deep_analysis_requested and not deep_analysis_eligible:
        raise ValueError(
            "FULL_INTELLIGENCE is unavailable: no production-eligible Deep Analysis model"
        )


def validate_schedule(
    *,
    target_type: AutomationTargetType,
    frequency: ScheduleFrequency,
    weekday: int | None,
    local_time: str | None,
    timezone: str,
) -> None:
    try:
        ZoneInfo(timezone)
    except Exception as error:
        raise ValueError("timezone is invalid") from error
    if frequency is ScheduleFrequency.MANUAL:
        if weekday is not None or local_time is not None:
            raise ValueError("manual schedules cannot include time fields")
        return
    if (
        local_time is None
        or not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", local_time)
        or int(local_time[:2]) > 23
    ):
        raise ValueError("scheduled work requires a valid local HH:MM time")
    if frequency is ScheduleFrequency.DAILY and weekday is not None:
        raise ValueError("daily schedules cannot include weekday")
    if frequency is ScheduleFrequency.WEEKLY and (
        weekday is None or weekday < 0 or weekday > 6
    ):
        raise ValueError("weekly schedules require weekday 0 through 6")
    if (
        target_type is AutomationTargetType.WEEKLY_GENERATION
        and frequency is ScheduleFrequency.DAILY
    ):
        raise ValueError("weekly generation supports MANUAL or WEEKLY only")


def next_scheduled_for(
    *,
    frequency: ScheduleFrequency,
    weekday: int | None,
    local_time: str | None,
    timezone: str,
    after: datetime,
) -> datetime | None:
    if frequency is ScheduleFrequency.MANUAL:
        return None
    if after.tzinfo is None:
        raise ValueError("after must be timezone-aware")
    assert local_time is not None
    zone = ZoneInfo(timezone)
    local_after = after.astimezone(zone)
    hour, minute = (int(part) for part in local_time.split(":"))
    candidate = local_after.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_after:
        candidate += timedelta(days=1)
    if frequency is ScheduleFrequency.WEEKLY:
        assert weekday is not None
        candidate += timedelta(days=(weekday - candidate.weekday()) % 7)
    return candidate.astimezone(UTC)


def due_scheduled_for(
    *,
    frequency: ScheduleFrequency,
    weekday: int | None,
    local_time: str | None,
    timezone: str,
    now: datetime,
    last_scheduled_for: datetime | None,
) -> datetime | None:
    """Return one due occurrence only: missed time produces one catch-up, never a storm."""

    if frequency is ScheduleFrequency.MANUAL or last_scheduled_for is None:
        return None
    next_time = next_scheduled_for(
        frequency=frequency,
        weekday=weekday,
        local_time=local_time,
        timezone=timezone,
        after=last_scheduled_for,
    )
    if next_time is not None and next_time <= now:
        return next_time
    return None


@dataclass(frozen=True, slots=True)
class ProviderModelStatus:
    provider: str
    model: str | None
    configured: bool
    credential_status: str
    adapter_available: bool
    qualification_status: str
    authorized: bool
    production_eligible: bool
    scope: str
    reason: str


def provider_model_statuses(
    desired_provider: str | None, desired_model: str | None
) -> tuple[ProviderModelStatus, ...]:
    """Static safe projections of the currently approved qualification facts."""
    return (
        ProviderModelStatus(
            provider="NVIDIA NIM",
            model="moonshotai/kimi-k3",
            configured=desired_provider == "NVIDIA NIM"
            and desired_model == "moonshotai/kimi-k3",
            credential_status="AVAILABLE",
            adapter_available=True,
            qualification_status="QUALIFIED",
            authorized=True,
            production_eligible=True,
            scope="V1_VIDEO_DISTILLATION_ONLY",
            reason="Approved for V1 Video Distillation only.",
        ),
        ProviderModelStatus(
            provider="OpenAI",
            model=desired_model if desired_provider == "OpenAI" else None,
            configured=desired_provider == "OpenAI",
            credential_status="BLOCKED",
            adapter_available=True,
            qualification_status="UNQUALIFIED",
            authorized=False,
            production_eligible=False,
            scope="NONE",
            reason="Not approved for production use.",
        ),
        ProviderModelStatus(
            provider="Local",
            model=desired_model if desired_provider == "Local" else None,
            configured=desired_provider == "Local",
            credential_status="NOT_CONFIGURED",
            adapter_available=True,
            qualification_status="UNQUALIFIED",
            authorized=False,
            production_eligible=False,
            scope="NONE",
            reason="Not approved for production use.",
        ),
    )
