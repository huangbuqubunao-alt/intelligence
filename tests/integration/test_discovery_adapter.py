"""Integration tests for discovery adapters with offline fixtures (no real YouTube)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from yt_dlp.utils import DownloadError, ExtractorError

from youtube_intel.discovery import (
    AdapterError,
    DiscoveryService,
    FakeDiscoveryRepository,
    YouTubeRssSourceProvider,
)
from youtube_intel.domain import (
    Availability,
    ChannelRef,
    DiscoveryCursor,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
)
from youtube_intel.providers import youtube as youtube_mod
from youtube_intel.providers.youtube import YtDlpMetadataProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "youtube"
FIXED_NOW = datetime(2026, 7, 15, 9, 30, 0, tzinfo=UTC)
CHANNEL = ChannelRef(channel_id="UC_example")


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._body
        return self._body[:n]

    def close(self) -> None:
        return None


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _rss_service(body: bytes) -> tuple[DiscoveryService, FakeDiscoveryRepository]:
    def opener(request: object, timeout: float) -> object:
        return _FakeResponse(body)

    provider = YouTubeRssSourceProvider(
        timeout_seconds=20.0,
        opener=opener,
        clock=lambda: FIXED_NOW,
        feed_url_template="https://example.invalid/feeds/{channel_id}.xml",
    )
    repo = FakeDiscoveryRepository()
    return DiscoveryService(provider, repo), repo


class _ScriptedYdl:
    """Minimal YoutubeDL stand-in: records opts and returns scripted results."""

    def __init__(self, opts: dict[str, Any], script: dict[str, Any | BaseException]) -> None:
        self.opts = opts
        self._script = script
        self.extract_calls: list[tuple[str, bool]] = []

    def extract_info(self, url: str, download: bool = True) -> Any:
        self.extract_calls.append((url, download))
        assert download is False
        # Key by video id suffix of watch URL
        video_id = url.rsplit("=", 1)[-1]
        if video_id not in self._script:
            raise DownloadError(f"unexpected video_id {video_id}")
        result = self._script[video_id]
        if isinstance(result, BaseException):
            raise result
        return result


def test_end_to_end_discovery_then_metadata_offline() -> None:
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    service, repo = _rss_service(body)

    batch = service.discover_and_save(CHANNEL)
    assert batch.video_ids == ("vid_new_1", "vid_dup", "vid_mid", "vid_old")
    assert all(v is PipelineStatus.DISCOVERED for v in repo.videos.values())
    assert repo.cursors["UC_example"].latest_video_id == "vid_new_1"

    # Second run is stable / empty and does not duplicate
    batch2 = service.discover_and_save(CHANNEL)
    assert batch2.video_ids == ()
    assert len(repo.videos) == 4
    assert len(repo.save_events) == 2

    captured: list[object] = []
    ydl_holder: list[_ScriptedYdl] = []

    def factory(opts: dict[str, Any]) -> _ScriptedYdl:
        scripted = _ScriptedYdl(
            opts,
            {
                "public_vid1": _load_json("info_public.json"),
                "shorts_vid1": _load_json("info_shorts.json"),
                "live_vid1": _load_json("info_live.json"),
                "upcoming_vid1": _load_json("info_upcoming.json"),
                "ended_vid1": _load_json("info_ended.json"),
                "private_vid1": DownloadError("Private video. Sign in if you've been granted access"),
                "deleted_vid1": DownloadError("This video has been removed by the uploader"),
                "restricted_vid1": ExtractorError(
                    "This video is not available in your country",
                    expected=True,
                ),
                "rate_vid1": DownloadError("HTTP Error 429: Too Many Requests"),
                "timeout_vid1": DownloadError("The read operation timed out"),
                "parse_vid1": DownloadError("Unable to extract yt initial player response"),
            },
        )
        ydl_holder.append(scripted)
        return scripted

    # Public constructor is domain config only; fakes bind through private hooks.
    meta = YtDlpMetadataProvider(timeout_seconds=25.0)
    youtube_mod._bind_test_hooks(
        meta,
        ydl_factory=factory,
        clock=lambda: FIXED_NOW,
        opts_sink=captured,
    )
    service_m = DiscoveryService(
        YouTubeRssSourceProvider(opener=lambda r, t: _FakeResponse(body), clock=lambda: FIXED_NOW),
        repo,
        meta,
    )

    public = service_m.fetch_and_store_metadata("public_vid1")
    assert public.title == "Public Example Video"
    assert public.available_languages == ("en", "zh-Hans", "ja", "fr")
    assert "http" not in "".join(public.available_languages)
    assert repo.metadata["public_vid1"].channel_name == "Example Channel"

    shorts = meta.fetch("shorts_vid1")
    assert shorts.duration_seconds == 45
    live = meta.fetch("live_vid1")
    assert live.live_status is LiveStatus.LIVE
    upcoming = meta.fetch("upcoming_vid1")
    assert upcoming.live_status is LiveStatus.UPCOMING
    ended = meta.fetch("ended_vid1")
    assert ended.live_status is LiveStatus.ENDED

    with pytest.raises(AdapterError) as private_exc:
        service_m.fetch_and_store_metadata("private_vid1")
    assert private_exc.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert repo.unavailable["private_vid1"][0] is Availability.PRIVATE
    # Discovery state not rolled back
    assert len(repo.videos) == 4
    assert repo.cursors["UC_example"].latest_video_id == "vid_new_1"

    with pytest.raises(AdapterError) as deleted_exc:
        meta.fetch("deleted_vid1")
    assert deleted_exc.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert "deleted" in deleted_exc.value.error.message.lower()

    with pytest.raises(AdapterError) as restricted_exc:
        meta.fetch("restricted_vid1")
    assert restricted_exc.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert "restricted" in restricted_exc.value.error.message.lower()

    with pytest.raises(AdapterError) as rate_exc:
        meta.fetch("rate_vid1")
    assert rate_exc.value.error.code is ErrorCode.RATE_LIMITED

    with pytest.raises(AdapterError) as timeout_exc:
        meta.fetch("timeout_vid1")
    assert timeout_exc.value.error.code is ErrorCode.TRANSIENT_NETWORK

    with pytest.raises(AdapterError) as parse_exc:
        meta.fetch("parse_vid1")
    assert parse_exc.value.error.code is ErrorCode.INVALID_RESPONSE

    # Option capture: no media download / cookies / remote components / ffmpeg
    assert captured
    for opts in captured:
        assert isinstance(opts, dict)
        assert opts["skip_download"] is True
        assert opts["noplaylist"] is True
        assert opts["writesubtitles"] is False
        assert opts["writeautomaticsub"] is False
        assert opts["usenetrc"] is False
        assert opts["ignoreconfig"] is True
        assert "cookiefile" not in opts
        assert "cookiesfrombrowser" not in opts
        assert "username" not in opts
        assert "password" not in opts
        assert "remote_components" not in opts
        assert "ffmpeg_location" not in opts
        for value in opts.values():
            if isinstance(value, str):
                assert not value.startswith("/Users/")
                assert "SECRET" not in value

    for ydl in ydl_holder:
        assert ydl.extract_calls
        assert all(download is False for _, download in ydl.extract_calls)

    # Error messages must not leak bodies / cookies / absolute paths
    for exc in (private_exc, deleted_exc, restricted_exc, rate_exc, timeout_exc, parse_exc):
        msg = exc.value.error.message
        assert "Sign in" not in msg or "private" in msg.lower()
        assert "cookie" not in msg.lower()
        assert "/Users/" not in msg
        assert "player response" not in msg.lower()


def test_metadata_mapping_from_all_fixtures_is_stable() -> None:
    names = [
        "info_public.json",
        "info_shorts.json",
        "info_live.json",
        "info_upcoming.json",
        "info_ended.json",
        "info_title_update.json",
        "info_restricted.json",
    ]
    for name in names:
        first = youtube_mod._map_info_dict_to_video_metadata(_load_json(name))
        second = youtube_mod._map_info_dict_to_video_metadata(_load_json(name))
        assert first == second


def test_cursor_cas_conflict_leaves_no_partial_state() -> None:
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    service, repo = _rss_service(body)
    # Seed an advanced cursor that will mismatch when we force conflict flag
    repo.cursors["UC_example"] = DiscoveryCursor(
        channel_id="UC_example",
        latest_video_id="seed",
    )
    repo.cursor_conflict = True
    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL)
    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert repo.videos == {}
    # Pre-seeded cursor remains (write rolled back before mutation in Fake)
    assert repo.cursors["UC_example"].latest_video_id == "seed"


def test_repeated_discovery_batch_does_not_duplicate_or_regress() -> None:
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    service, repo = _rss_service(body)
    service.discover_and_save(CHANNEL)
    # Manually advance one video's pipeline to ensure upsert does not regress it
    repo.videos["vid_dup"] = PipelineStatus.METADATA_READY
    # Force re-save of same ids by resetting cursor without clearing videos
    repo.cursors["UC_example"] = DiscoveryCursor(channel_id="UC_example")
    service.discover_and_save(CHANNEL)
    assert repo.videos["vid_dup"] is PipelineStatus.METADATA_READY
    assert len([e for e in repo.save_events]) == 2


def test_rss_missing_channel_id_does_not_mutate_repository() -> None:
    """Integration: missing entry channelId fails safely without candidates/cursor advance."""
    missing = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>vid_new_1</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Newest</title>
    <published>2026-07-10T12:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>vid_no_ch</yt:videoId>
    <title>No channel</title>
    <published>2026-07-09T12:00:00+00:00</published>
  </entry>
</feed>
"""
    service, repo = _rss_service(missing)
    seeded = DiscoveryCursor(channel_id="UC_example", latest_video_id="seed_keep")
    repo.cursors["UC_example"] = seeded
    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL)
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert exc_info.value.error.retryable is False
    assert repo.videos == {}
    assert repo.cursors["UC_example"] == seeded
    assert repo.save_events == []

    # Fixed feed: older entry now complete and discoverable from empty frontier.
    fixed = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>vid_new_1</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Newest</title>
    <published>2026-07-10T12:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>vid_no_ch</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Restored channel</title>
    <published>2026-07-09T12:00:00+00:00</published>
  </entry>
</feed>
"""
    repo.cursors["UC_example"] = DiscoveryCursor(channel_id="UC_example")
    service2, _ = _rss_service(fixed)
    # Reuse same repo for cursor/candidate assertions.
    service2 = DiscoveryService(
        YouTubeRssSourceProvider(
            timeout_seconds=20.0,
            opener=lambda request, timeout: _FakeResponse(fixed),
            clock=lambda: FIXED_NOW,
            feed_url_template="https://example.invalid/feeds/{channel_id}.xml",
        ),
        repo,
    )
    batch = service2.discover_and_save(CHANNEL)
    assert "vid_no_ch" in batch.video_ids
    assert "vid_new_1" in batch.video_ids
    assert repo.cursors["UC_example"].latest_video_id == "vid_new_1"


def test_provider_rejects_mismatched_and_http_errors_offline() -> None:
    """Integration: request/response id match + HTTP classification stay safe offline."""
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    _, repo = _rss_service(body)

    class _Handle:
        def __init__(self, result: object) -> None:
            self._result = result

        def extract_info(self, url: str, download: bool = True) -> object:
            assert download is False
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result

    # Mismatched id must not land in repository.
    wrong = _load_json("info_public.json")
    meta = YtDlpMetadataProvider(timeout_seconds=20.0)
    youtube_mod._bind_test_hooks(meta, ydl_factory=lambda opts: _Handle(wrong))
    service = DiscoveryService(
        YouTubeRssSourceProvider(opener=lambda r, t: _FakeResponse(body), clock=lambda: FIXED_NOW),
        repo,
        meta,
    )
    with pytest.raises(AdapterError) as mismatch:
        service.fetch_and_store_metadata("reqid01")
    assert mismatch.value.error.code is ErrorCode.INVALID_RESPONSE
    assert mismatch.value.error.video_id == "reqid01"
    assert repo.metadata == {}

    # 503 is retryable provider unavailable even when message says unavailable.
    youtube_mod._bind_test_hooks(
        meta,
        ydl_factory=lambda opts: _Handle(DownloadError("HTTP Error 503: Service Unavailable")),
    )
    with pytest.raises(AdapterError) as http503:
        meta.fetch("reqid01")
    assert http503.value.error.code is ErrorCode.PROVIDER_UNAVAILABLE
    assert http503.value.error.retryable is True
