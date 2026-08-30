"""TASK-016F deterministic Weekly V2 aggregation from verified Note artifacts."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from tests.unit.test_verified_note_v2 import _artifact
from youtube_intel.weekly_v2 import WeeklyV2Error, build_weekly_v2, render_weekly_v2


def test_weekly_v2_requires_admitted_artifacts_and_rejects_raw_note_and_lookalikes() -> None:
    artifact = _artifact()

    with pytest.raises(WeeklyV2Error, match="verified Note V2 artifact"):
        build_weekly_v2((artifact.note,), now=datetime(2026, 8, 30, tzinfo=UTC), timezone="Asia/Shanghai", top_n=10)
    with pytest.raises(WeeklyV2Error, match="verified Note V2 artifact"):
        build_weekly_v2((replace(artifact),), now=datetime(2026, 8, 30, tzinfo=UTC), timezone="Asia/Shanghai", top_n=10)
    with pytest.raises(WeeklyV2Error, match="verified Note V2 artifact"):
        build_weekly_v2(({"identity": artifact.identity},), now=datetime(2026, 8, 30, tzinfo=UTC), timezone="Asia/Shanghai", top_n=10)


@pytest.mark.parametrize(
    ("completed_at", "included"),
    (
        (datetime(2026, 8, 23, 15, 59, 59, tzinfo=UTC), False),
        (datetime(2026, 8, 23, 16, tzinfo=UTC), True),
        (datetime(2026, 8, 27, 12, tzinfo=UTC), True),
        (datetime(2026, 8, 30, 15, 59, 59, tzinfo=UTC), True),
        (datetime(2026, 8, 30, 16, tzinfo=UTC), False),
    ),
)
def test_weekly_v2_uses_authoritative_completed_at_in_configured_iso_window(completed_at: datetime, included: bool) -> None:
    report = build_weekly_v2(
        (_artifact(completed_at=completed_at),),
        now=datetime(2026, 8, 27, 12, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=10,
    )

    assert bool(report.items) is included


def test_weekly_v2_top_n_ties_duplicates_and_input_permutation_are_deterministic() -> None:
    highest = _artifact(video_id="video-a", score=9.0)
    tied_first = _artifact(video_id="video-b", score=8.0)
    tied_second = _artifact(video_id="video-c", score=8.0)
    low = _artifact(video_id="video-d", score=7.1)
    duplicate = _artifact(video_id="video-a", score=9.0)
    forward = build_weekly_v2(
        (low, tied_second, highest, tied_first, duplicate),
        now=datetime(2026, 8, 30, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=3,
    )
    reverse = build_weekly_v2(
        (duplicate, tied_first, highest, tied_second, low),
        now=datetime(2026, 8, 30, tzinfo=UTC),
        timezone="Asia/Shanghai",
        top_n=3,
    )

    assert forward == reverse
    assert [item.video_id for item in forward.items] == ["video-a", "video-b", "video-c"]
    assert render_weekly_v2(forward) == render_weekly_v2(reverse)
    assert "SECRET_WEEKLY_UNSELECTED_TEXT" not in repr(forward)
    assert "SECRET_WEEKLY_UNSELECTED_TEXT" not in render_weekly_v2(forward)
