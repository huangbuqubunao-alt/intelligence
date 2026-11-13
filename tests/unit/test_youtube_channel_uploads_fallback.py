"""TDD coverage for YouTube Following uploads-playlist fallback when /feeds/videos.xml is 404."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from youtube_intel.following_provider import Candidate, TrackingError
from youtube_intel.providers import youtube_channel as yt

CHANNEL = "UCPjNBjflYl0-HQtUvOx0Ibw"
OTHER = "UCXZCJLdBC09xxGZ6gcdrc6A"
VERIFIED_AT = datetime(2026, 10, 20, 14, 49, 41, 404620, tzinfo=UTC)


def _anchors() -> tuple[Candidate, ...]:
    return (
        Candidate("tpZOU1ugODQ", datetime(2026, 10, 18, 16, 12, 5, 123456, tzinfo=UTC)),
        Candidate("jEOUUAPC1sc", datetime(2026, 10, 15, 20, 40, 35, tzinfo=UTC)),
        Candidate("rkK8ZyzYyEA", datetime(2026, 10, 12, 11, 3, 9, tzinfo=UTC)),
    )


def test_enumerate_falls_back_to_uploads_playlist_when_rss_feed_returns_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(yt, "public_operation", lambda op: op())
    monkeypatch.setattr(
        yt,
        "channel_feed",
        lambda _cid: (_ for _ in ()).throw(TrackingError("NOT_FOUND")),
    )
    provider = yt.YouTubeFollowingProvider()
    anchors = _anchors()
    calls: list[tuple[str, int, int]] = []

    def fake_playlist(channel_id: str, start: int, end: int) -> dict[str, Any]:
        calls.append((channel_id, start, end))
        return {
            "channel_id": CHANNEL,
            "channel": "Greg Isenberg",
            "entries": [
                {"id": "upcom000001", "timestamp": 1799999999, "live_status": "is_upcoming"},
                {"id": "live0000001", "timestamp": None, "live_status": "is_live"},
                {"id": "1cWZ7Ekff6E", "timestamp": 1762905600, "live_status": None},
                {"id": "6DT8Cy2rnd0", "timestamp": 1762819200, "live_status": "was_live"},
                # Anchor timestamps from youtubetab are rounded to midnight,
                # so fallback MUST preserve exact known Candidate.published_at!
                {"id": "tpZOU1ugODQ", "timestamp": 1760745600, "live_status": None},
                {"id": "jEOUUAPC1sc", "timestamp": 1760486400, "live_status": None},
                {"id": "rkK8ZyzYyEA", "timestamp": 1760227200, "live_status": None},
            ],
        }

    provider._playlist_page = fake_playlist
    identity = yt.canonical_channel(CHANNEL, "Old Name")
    result = provider.enumerate(
        identity,
        initial=False,
        next_page=1,
        known=anchors,
        verified_at=VERIFIED_AT,
    )

    assert calls == [(CHANNEL, 1, 30)]
    assert result.name == "Greg Isenberg"
    assert result.complete is True
    assert result.next_page == 1
    by_id = {item.identity: item for item in result.items}
    assert set(by_id) == {
        "1cWZ7Ekff6E",
        "6DT8Cy2rnd0",
        "tpZOU1ugODQ",
        "jEOUUAPC1sc",
        "rkK8ZyzYyEA",
    }
    for anchor in anchors:
        assert by_id[anchor.identity] == anchor


def test_enumerate_uploads_extends_to_90_when_first_30_miss_prior_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(yt, "public_operation", lambda op: op())
    monkeypatch.setattr(
        yt,
        "channel_feed",
        lambda _cid: (_ for _ in ()).throw(TrackingError("NOT_FOUND")),
    )
    provider = yt.YouTubeFollowingProvider()
    anchors = _anchors()
    calls: list[tuple[str, int, int]] = []

    page_1 = [
        {"id": f"newvid{i:05d}", "timestamp": 1762905600 - i * 60}
        for i in range(1, 31)
    ]
    page_2 = [
        {"id": f"newvid{i:05d}", "timestamp": 1762905600 - i * 60}
        for i in range(31, 65)
    ] + [
        {"id": a.identity, "timestamp": int(a.published_at.timestamp())}
        for a in anchors
    ]

    def fake_playlist(channel_id: str, start: int, end: int) -> dict[str, Any]:
        calls.append((channel_id, start, end))
        return {
            "channel_id": OTHER,
            "channel": "OpenAI",
            "entries": page_1 if start == 1 else page_2,
        }

    provider._playlist_page = fake_playlist
    identity = yt.canonical_channel(OTHER, "OpenAI")
    result = provider.enumerate(
        identity,
        initial=False,
        next_page=1,
        known=anchors,
        verified_at=VERIFIED_AT,
    )

    assert calls == [(OTHER, 1, 30), (OTHER, 31, 90)]
    assert len(result.items) == 67
    assert result.complete is True
    assert result.next_page == 1


def test_enumerate_uploads_rejects_mismatched_channel_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(yt, "public_operation", lambda op: op())
    monkeypatch.setattr(
        yt,
        "channel_feed",
        lambda _cid: (_ for _ in ()).throw(TrackingError("NOT_FOUND")),
    )
    provider = yt.YouTubeFollowingProvider()
    provider._playlist_page = lambda _cid, _s, _e: {
        "channel_id": OTHER,
        "channel": "Wrong Channel",
        "entries": [],
    }
    with pytest.raises(TrackingError, match="METADATA_FAILED"):
        provider.enumerate(
            yt.canonical_channel(CHANNEL, "Greg Isenberg"),
            initial=True,
            next_page=1,
            known=(),
            verified_at=None,
        )


def test_custom_fetch_fixture_raising_not_found_does_not_invoke_playlist_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(yt, "public_operation", lambda op: op())
    provider = yt.YouTubeFollowingProvider()
    provider._fetch = lambda _cid: (_ for _ in ()).throw(TrackingError("NOT_FOUND"))
    provider._playlist_page = lambda *_args: pytest.fail("must not call live fallback for custom _fetch fixture")  # type: ignore[assignment]
    # Note: when _fetch is customized by an existing test fixture, _fetch stays authoritative.
    provider._playlist_page = yt._playlist_page
    monkeypatch.setattr(
        yt,
        "_playlist_page",
        lambda *_args: pytest.fail("must not call live fallback"),
    )
    with pytest.raises(TrackingError, match="NOT_FOUND"):
        provider.enumerate(
            yt.canonical_channel(CHANNEL, "Greg Isenberg"),
            initial=False,
            next_page=1,
            known=_anchors(),
            verified_at=VERIFIED_AT,
        )


def test_manual_check_recovers_during_automatic_provider_error_or_not_found_backoff(
    tmp_path: Any,
) -> None:
    from datetime import timedelta
    from pathlib import Path

    from youtube_intel.bilibili_content import BilibiliContentProvider
    from youtube_intel.following_provider import Enumeration, SourceIdentity
    from youtube_intel.following_tracking import FollowingTrackingService, tracking_due
    from youtube_intel.state import SQLiteStateRepository

    now = VERIFIED_AT
    mode = {"fail": ""}

    class ProviderStub:
        provider = "YOUTUBE"

        def resolve(self, value: str) -> SourceIdentity:
            return yt.canonical_channel(CHANNEL, "Greg Isenberg")

        def enumerate(self, identity: SourceIdentity, **kwargs: Any) -> Enumeration:
            if mode["fail"]:
                raise TrackingError(mode["fail"])
            return Enumeration("Greg Isenberg", (_anchors()[0],), True, 1)

        def enroll(self, *args: Any, **kwargs: Any) -> str:
            return str(args[0])

    root = Path(tmp_path)
    repo = SQLiteStateRepository(root / "state.sqlite")
    repo.initialize(now=now)
    tracker = FollowingTrackingService(
        repo,
        BilibiliContentProvider(repo, root / "data", now=lambda: now),
        youtube=ProviderStub(),
        now=lambda: now,
    )
    source = tracker.follow(CHANNEL, provider="YOUTUBE")

    for error_code in ("METADATA_FAILED", "NOT_FOUND"):
        now = now + timedelta(minutes=16)
        mode["fail"] = error_code
        failed_health = tracker.check(source.source_id, automatic=True)
        assert failed_health in {"PROVIDER_ERROR", "NOT_FOUND"}
        # Automatic check must remain backed off for 1 hour, while manual Check Now
        # is permitted after the 5-second debounce.
        now = now + timedelta(seconds=6)
        assert tracking_due(repo, source.source_id, now, manual=False) is False
        assert tracking_due(repo, source.source_id, now, manual=True) is True
        mode["fail"] = ""
        assert tracker.check(source.source_id, automatic=False) == "COMPLETE"
        assert tracker.projection(source.source_id)["health"] == "HEALTHY"

