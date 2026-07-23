from __future__ import annotations

from datetime import UTC, datetime

from youtube_intel.reporting import week_period_for


def test_week_period_uses_configured_timezone_and_cross_year_iso_identity() -> None:
    period = week_period_for(
        datetime(2025, 12, 29, 0, 30, tzinfo=UTC),
        timezone="Asia/Shanghai",
    )

    assert (period.iso_year, period.iso_week) == (2026, 1)
    assert period.start_utc == datetime(2025, 12, 28, 16, tzinfo=UTC)
    assert period.end_utc == datetime(2026, 1, 4, 16, tzinfo=UTC)
    assert period.relative_path == "Weekly/2026-W01.md"


def test_week_period_has_local_monday_boundaries_across_dst() -> None:
    period = week_period_for(
        datetime(2026, 3, 11, 12, tzinfo=UTC),
        timezone="America/New_York",
    )

    assert (period.iso_year, period.iso_week) == (2026, 11)
    assert period.start_utc == datetime(2026, 3, 9, 4, tzinfo=UTC)
    assert period.end_utc == datetime(2026, 3, 16, 4, tzinfo=UTC)
    assert period.contains(datetime(2026, 3, 9, 4, tzinfo=UTC))
    assert not period.contains(datetime(2026, 3, 16, 4, tzinfo=UTC))
