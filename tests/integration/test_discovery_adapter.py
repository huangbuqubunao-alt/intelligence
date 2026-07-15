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
    DiscoveryRepository,
    DiscoveryService,
    FakeChannelCursor,
    FakeDiscoveryRepository,
    YouTubeRssSourceProvider,
)
from youtube_intel.domain import (
    Availability,
    ChannelRef,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
    ProviderCallMetadata,
    SourceProvider,
    VideoMetadata,
)
from youtube_intel.providers import youtube as youtube_mod
from youtube_intel.providers.youtube import YtDlpMetadataProvider
from youtube_intel.state import ConcurrencyConflict, SQLiteStateRepository

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "youtube"
FIXED_NOW = datetime(2026, 7, 15, 9, 30, 0, tzinfo=UTC)
CHANNEL = ChannelRef(channel_id="UC_example")
PIPELINE_VERSION = "pipeline-v1"
SAVE_KW = {"pipeline_version": PIPELINE_VERSION, "now": FIXED_NOW}


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

    batch = service.discover_and_save(CHANNEL, **SAVE_KW)
    assert batch.video_ids == ("vid_new_1", "vid_dup", "vid_mid", "vid_old")
    assert all(v is PipelineStatus.DISCOVERED for v in repo.videos.values())
    assert repo.cursors["UC_example"].cursor.latest_video_id == "vid_new_1"

    # Second run is stable / empty and does not duplicate
    batch2 = service.discover_and_save(CHANNEL, **SAVE_KW)
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
                "deleted_vid1": DownloadError("This video has been removed by the uploader"),
                "restricted_vid1": ExtractorError(
                    "This video is not available in your country",
                    expected=True,
                ),
                "rate_vid1": DownloadError("HTTP Error 429: Too Many Requests"),
                "timeout_vid1": DownloadError("The read operation timed out"),
                "parse_vid1": DownloadError("Unable to extract yt initial player response"),
                # Use a discovered candidate id so mark_video_unavailable has a real row.
                "vid_dup": DownloadError("Private video. Sign in if you've been granted access"),
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

    public = service_m.fetch_and_store_metadata("public_vid1", **SAVE_KW)
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
        service_m.fetch_and_store_metadata("vid_dup", **SAVE_KW)
    assert private_exc.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert repo.unavailable["vid_dup"] is Availability.PRIVATE
    # Discovery state not rolled back for RSS candidates
    for video_id in ("vid_new_1", "vid_dup", "vid_mid", "vid_old"):
        assert video_id in repo.videos
        assert repo.videos[video_id] is PipelineStatus.DISCOVERED
    assert repo.cursors["UC_example"].cursor.latest_video_id == "vid_new_1"

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
    seeded_cursor = DiscoveryCursor(
        channel_id="UC_example",
        latest_video_id="seed",
    )
    repo.cursors["UC_example"] = FakeChannelCursor(
        channel_id=seeded_cursor.channel_id,
        revision=1,
        cursor=seeded_cursor,
    )
    repo.cursor_conflict = True
    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL, **SAVE_KW)
    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert repo.videos == {}
    # Pre-seeded cursor remains (write rolled back before mutation in Fake)
    assert repo.cursors["UC_example"].cursor.latest_video_id == "seed"


def test_repeated_discovery_batch_does_not_duplicate_or_regress() -> None:
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    service, repo = _rss_service(body)
    service.discover_and_save(CHANNEL, **SAVE_KW)
    # Manually advance one video's pipeline to ensure upsert does not regress it
    repo.videos["vid_dup"] = PipelineStatus.METADATA_READY
    # Force re-save of same ids by resetting cursor without clearing videos
    repo.cursors["UC_example"] = FakeChannelCursor(
        channel_id="UC_example",
        revision=0,
        cursor=DiscoveryCursor(channel_id="UC_example"),
    )
    service.discover_and_save(CHANNEL, **SAVE_KW)
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
    seeded_cursor = DiscoveryCursor(channel_id="UC_example", latest_video_id="seed_keep")
    seeded = FakeChannelCursor(channel_id="UC_example", revision=1, cursor=seeded_cursor)
    repo.cursors["UC_example"] = seeded
    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL, **SAVE_KW)
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
    repo.cursors["UC_example"] = FakeChannelCursor(
        channel_id="UC_example",
        revision=0,
        cursor=DiscoveryCursor(channel_id="UC_example"),
    )
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
    batch = service2.discover_and_save(CHANNEL, **SAVE_KW)
    assert "vid_no_ch" in batch.video_ids
    assert "vid_new_1" in batch.video_ids
    assert repo.cursors["UC_example"].cursor.latest_video_id == "vid_new_1"


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
        service.fetch_and_store_metadata("reqid01", **SAVE_KW)
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


# ---------------------------------------------------------------------------
# Real SQLite combination (TASK-003 repository + TASK-004 DiscoveryService)
# ---------------------------------------------------------------------------


def _sqlite_repo(tmp_path: Path) -> SQLiteStateRepository:
    path = tmp_path / "discovery-combo.sqlite3"
    repository = SQLiteStateRepository(path)
    repository.initialize(now=FIXED_NOW)
    return repository


def _rss_source(body: bytes) -> YouTubeRssSourceProvider:
    return YouTubeRssSourceProvider(
        timeout_seconds=20.0,
        opener=lambda request, timeout: _FakeResponse(body),
        clock=lambda: FIXED_NOW,
        feed_url_template="https://example.invalid/feeds/{channel_id}.xml",
    )


def _wire_sqlite_discovery_service(
    source: SourceProvider,
    repository: SQLiteStateRepository,
) -> DiscoveryService:
    """Real static wiring: SQLiteStateRepository is assignable to DiscoveryRepository.

    Independent reviewers re-run the same assignment under ``MYPYPATH=src uv run mypy -c``.
    """
    checked: DiscoveryRepository = repository
    return DiscoveryService(source, checked)


def test_sqlite_repository_matches_discovery_protocol(tmp_path: Path) -> None:
    """Runtime structural check: initialized SQLite repo is a DiscoveryRepository."""
    repository = _sqlite_repo(tmp_path)
    assert isinstance(repository, DiscoveryRepository)

    def _accepts_discovery_repository(repo: DiscoveryRepository) -> str:
        return type(repo).__name__

    # Static typing must accept the concrete SQLite repository here.
    assert _accepts_discovery_repository(repository) == "SQLiteStateRepository"

    body = (FIXTURES / "rss_sample.xml").read_bytes()
    source = _rss_source(body)
    wired = _wire_sqlite_discovery_service(source, repository)
    assert isinstance(wired, DiscoveryService)


def test_sqlite_discovery_service_atomic_batch_and_stable_rerun(tmp_path: Path) -> None:
    """Empty DB batch writes all candidates+cursor; second run is stable/idempotent."""
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    repository = _sqlite_repo(tmp_path)
    service = DiscoveryService(_rss_source(body), repository)

    batch = service.discover_and_save(CHANNEL, **SAVE_KW)
    assert batch.video_ids == ("vid_new_1", "vid_dup", "vid_mid", "vid_old")

    cursor = repository.get_channel_cursor("UC_example")
    assert cursor is not None
    assert cursor.revision == 1
    assert cursor.as_discovery_cursor().latest_video_id == "vid_new_1"
    assert cursor.as_discovery_cursor().last_checked_at == FIXED_NOW
    for video_id in batch.video_ids:
        record = repository.get_video(video_id)
        assert record is not None
        assert record.pipeline_status is PipelineStatus.DISCOVERED
        assert record.pipeline_version == PIPELINE_VERSION

    # Second stable run: empty new candidates, revision advances, no pipeline regress.
    batch2 = service.discover_and_save(CHANNEL, **SAVE_KW)
    assert batch2.video_ids == ()
    cursor2 = repository.get_channel_cursor("UC_example")
    assert cursor2 is not None
    assert cursor2.revision == 2
    assert cursor2.as_discovery_cursor().latest_video_id == "vid_new_1"
    for video_id in batch.video_ids:
        record = repository.get_video(video_id)
        assert record is not None
        assert record.pipeline_status is PipelineStatus.DISCOVERED

    # CAS conflict: stale expected revision leaves state unchanged.
    with pytest.raises(ConcurrencyConflict):
        repository.save_discovery_batch(
            batch,
            expected_cursor=None,
            expected_revision=0,
            pipeline_version=PIPELINE_VERSION,
            now=FIXED_NOW,
        )
    cursor3 = repository.get_channel_cursor("UC_example")
    assert cursor3 is not None
    assert cursor3.revision == 2
    assert len([v for v in batch.video_ids if repository.get_video(v) is not None]) == 4


def test_sqlite_metadata_success_and_unavailable_paths(tmp_path: Path) -> None:
    """Metadata upsert updates real rows; CONTENT_UNAVAILABLE marks availability safely."""
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    repository = _sqlite_repo(tmp_path)
    source = _rss_source(body)

    # Discover real candidates first.
    DiscoveryService(source, repository).discover_and_save(CHANNEL, **SAVE_KW)

    public_payload = _load_json("info_public.json")
    # Map fixture id onto a discovered candidate for real-row updates.
    public_payload = {**public_payload, "id": "vid_new_1"}

    class _Handle:
        def __init__(self, result: object) -> None:
            self._result = result

        def extract_info(self, url: str, download: bool = True) -> object:
            assert download is False
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result

    meta = YtDlpMetadataProvider(timeout_seconds=20.0)
    youtube_mod._bind_test_hooks(
        meta,
        ydl_factory=lambda opts: _Handle(public_payload),
        clock=lambda: FIXED_NOW,
    )
    service = DiscoveryService(source, repository, meta)
    saved = service.fetch_and_store_metadata("vid_new_1", **SAVE_KW)
    assert isinstance(saved, VideoMetadata)
    assert saved.video_id == "vid_new_1"
    record = repository.get_video("vid_new_1")
    assert record is not None
    assert record.title == "Public Example Video"
    assert record.pipeline_status is PipelineStatus.DISCOVERED  # no regress
    assert record.pipeline_version == PIPELINE_VERSION
    assert record.availability is Availability.PUBLIC

    # Advance pipeline then re-upsert metadata: status must not regress.
    assert repository.advance_pipeline(
        "vid_new_1",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version=PIPELINE_VERSION,
        now=FIXED_NOW,
    )
    renamed = {**public_payload, "title": "Public Example Video (Updated Title)"}
    youtube_mod._bind_test_hooks(
        meta,
        ydl_factory=lambda opts: _Handle(renamed),
        clock=lambda: FIXED_NOW,
    )
    service.fetch_and_store_metadata("vid_new_1", **SAVE_KW)
    after = repository.get_video("vid_new_1")
    assert after is not None
    assert after.title == "Public Example Video (Updated Title)"
    assert after.pipeline_status is PipelineStatus.METADATA_READY

    # CONTENT_UNAVAILABLE on another discovered candidate.
    youtube_mod._bind_test_hooks(
        meta,
        ydl_factory=lambda opts: _Handle(
            DownloadError("Private video. Sign in if you've been granted access")
        ),
        clock=lambda: FIXED_NOW,
    )
    with pytest.raises(AdapterError) as private_exc:
        service.fetch_and_store_metadata("vid_dup", **SAVE_KW)
    err = private_exc.value.error
    assert err.code is ErrorCode.CONTENT_UNAVAILABLE
    assert err.video_id == "vid_dup"
    assert "Sign in" not in err.message or "private" in err.message.lower()
    assert "cookie" not in err.message.lower()
    unavailable = repository.get_video("vid_dup")
    assert unavailable is not None
    assert unavailable.availability is Availability.PRIVATE
    assert unavailable.title is None  # no fabricated metadata
    assert unavailable.pipeline_status is PipelineStatus.DISCOVERED


def test_sqlite_service_cas_conflict_after_intervening_commit(tmp_path: Path) -> None:
    """Service-level CAS: intervening commit after cursor read must reject stale save."""
    body = (FIXTURES / "rss_sample.xml").read_bytes()
    repository = _sqlite_repo(tmp_path)
    inner = _rss_source(body)
    intervening_revision: list[int] = []

    def _intervene() -> None:
        # Service has already read expected_cursor=None/revision=0.
        # Commit a different batch through the real Repository first.
        intervening = DiscoveryBatch(
            channel_id="UC_example",
            video_ids=("vid_intervening",),
            next_cursor=DiscoveryCursor(
                channel_id="UC_example",
                last_checked_at=FIXED_NOW,
                latest_published_at=FIXED_NOW,
                latest_video_id="vid_intervening",
                provider_cursor="intervening",
            ),
            call=ProviderCallMetadata(
                provider="intervening-test",
                started_at=FIXED_NOW,
                finished_at=FIXED_NOW,
            ),
        )
        saved = repository.save_discovery_batch(
            intervening,
            expected_cursor=None,
            expected_revision=0,
            pipeline_version=PIPELINE_VERSION,
            now=FIXED_NOW,
        )
        intervening_revision.append(saved.revision)

    class _RacingSource:
        def discover(
            self,
            channel: ChannelRef,
            cursor: DiscoveryCursor,
        ) -> DiscoveryBatch:
            assert cursor.channel_id == channel.channel_id
            _intervene()
            # Stale batch returned after intervening commit advanced the cursor.
            return inner.discover(channel, cursor)

    service = DiscoveryService(_RacingSource(), repository)
    with pytest.raises(ConcurrencyConflict):
        service.discover_and_save(CHANNEL, **SAVE_KW)

    assert intervening_revision == [1]
    kept = repository.get_channel_cursor("UC_example")
    assert kept is not None
    assert kept.revision == 1
    assert kept.as_discovery_cursor().latest_video_id == "vid_intervening"
    assert repository.get_video("vid_intervening") is not None
    # Stale Service batch candidates must not be written.
    for stale_id in ("vid_new_1", "vid_dup", "vid_mid", "vid_old"):
        assert repository.get_video(stale_id) is None
