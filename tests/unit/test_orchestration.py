from datetime import UTC, datetime

import pytest

from youtube_intel.orchestration import (
    AutomationTargetType,
    ProcessingPolicy,
    ScheduleFrequency,
    SourceNormalizationError,
    SourceType,
    due_scheduled_for,
    next_scheduled_for,
    normalize_source_url,
    validate_policy,
    validate_schedule,
)


def test_normalizes_channel_and_video_without_network() -> None:
    channel = normalize_source_url(
        "https://youtube.com/channel/UC1234567890123456789012"
    )
    video = normalize_source_url("https://youtu.be/abcdefghijk?t=2")
    assert channel.source_type is SourceType.CHANNEL
    assert channel.canonical_url.endswith("UC1234567890123456789012")
    assert video.source_type is SourceType.VIDEO_URL
    assert video.canonical_url == "https://www.youtube.com/watch?v=abcdefghijk"


def test_rejects_untrusted_or_unsupported_source_urls() -> None:
    for url in (
        "http://youtube.com/watch?v=abcdefghijk",
        "https://evil.example/watch?v=abcdefghijk",
        "https://youtube.com/playlist?list=x",
    ):
        with pytest.raises(SourceNormalizationError):
            normalize_source_url(url)


def test_full_policy_cannot_activate_without_qualified_provider() -> None:
    with pytest.raises(ValueError, match="production-eligible"):
        validate_policy(
            ProcessingPolicy.FULL_INTELLIGENCE, deep_analysis_eligible=False
        )


def test_schedule_validation_and_next_time() -> None:
    validate_schedule(
        target_type=AutomationTargetType.SOURCE_CHECK,
        frequency=ScheduleFrequency.DAILY,
        weekday=None,
        local_time="09:30",
        timezone="Asia/Shanghai",
    )
    next_time = next_scheduled_for(
        frequency=ScheduleFrequency.DAILY,
        weekday=None,
        local_time="09:30",
        timezone="Asia/Shanghai",
        after=datetime(2026, 9, 1, 2, 0, tzinfo=UTC),
    )
    assert next_time == datetime(2026, 9, 2, 1, 30, tzinfo=UTC)


def test_missed_schedule_returns_one_catch_up_only() -> None:
    due = due_scheduled_for(
        frequency=ScheduleFrequency.DAILY,
        weekday=None,
        local_time="09:00",
        timezone="UTC",
        last_scheduled_for=datetime(2026, 8, 28, 9, tzinfo=UTC),
        now=datetime(2026, 9, 1, 12, tzinfo=UTC),
    )
    assert due == datetime(2026, 8, 29, 9, tzinfo=UTC)
