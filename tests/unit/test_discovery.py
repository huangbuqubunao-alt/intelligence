"""Unit tests for RSS discovery, batch application service, and language summary."""

from __future__ import annotations

import inspect
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints
from urllib.error import HTTPError, URLError

import pytest
from yt_dlp.utils import DownloadError

from youtube_intel.discovery import (
    AdapterError,
    DiscoveryService,
    FakeDiscoveryRepository,
    YouTubeRssSourceProvider,
    is_newer_than_cursor,
)
from youtube_intel.domain import (
    Availability,
    ChannelRef,
    DiscoveryCursor,
    ErrorCode,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    VideoMetadata,
)
from youtube_intel.providers import youtube as youtube_mod
from youtube_intel.providers.youtube import YtDlpMetadataProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "youtube"
CHANNEL = ChannelRef(channel_id="UC_example")
T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
T8 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
T9 = datetime(2026, 7, 9, 12, 0, 0, tzinfo=UTC)
T10 = datetime(2026, 7, 10, 12, 0, 0, tzinfo=UTC)
FIXED_NOW = datetime(2026, 7, 15, 8, 0, 0, tzinfo=UTC)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.closed = False

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._body
        return self._body[:n]

    def close(self) -> None:
        self.closed = True


def _load_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _rss_provider(
    body: bytes,
    *,
    channel_id: str = "UC_example",
    max_response_bytes: int = 2_000_000,
    raise_on_open: BaseException | None = None,
) -> YouTubeRssSourceProvider:
    def opener(request: object, timeout: float) -> object:
        assert timeout > 0
        headers = getattr(request, "headers", {}) or {}
        # urllib lowercases header keys in Request
        ua = headers.get("User-agent") or headers.get("User-Agent")
        assert ua
        if raise_on_open is not None:
            raise raise_on_open
        return _FakeResponse(body)

    return YouTubeRssSourceProvider(
        timeout_seconds=15.0,
        max_response_bytes=max_response_bytes,
        opener=opener,
        clock=lambda: FIXED_NOW,
        feed_url_template="https://example.invalid/feeds/videos.xml?channel_id={channel_id}",
    )


# ---------------------------------------------------------------------------
# Cursor comparison
# ---------------------------------------------------------------------------


def test_is_newer_than_cursor_empty_frontier() -> None:
    cursor = DiscoveryCursor(channel_id="UC_example")
    assert is_newer_than_cursor(T0, "vid_a", cursor) is True


def test_is_newer_than_cursor_time_and_video_id_tiebreak() -> None:
    cursor = DiscoveryCursor(
        channel_id="UC_example",
        latest_published_at=T9,
        latest_video_id="vid_m",
    )
    assert is_newer_than_cursor(T10, "anything", cursor) is True
    assert is_newer_than_cursor(T8, "anything", cursor) is False
    assert is_newer_than_cursor(T9, "vid_z", cursor) is True
    assert is_newer_than_cursor(T9, "vid_a", cursor) is False
    assert is_newer_than_cursor(T9, "vid_m", cursor) is False


# ---------------------------------------------------------------------------
# RSS happy paths
# ---------------------------------------------------------------------------


def test_rss_provider_order_and_in_batch_dedup() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    cursor = DiscoveryCursor(channel_id="UC_example")
    batch = provider.discover(CHANNEL, cursor)
    assert batch.channel_id == "UC_example"
    assert batch.video_ids == ("vid_new_1", "vid_dup", "vid_mid", "vid_old")
    assert batch.next_cursor.channel_id == "UC_example"
    assert batch.next_cursor.latest_video_id == "vid_new_1"
    assert batch.next_cursor.latest_published_at == T10
    assert batch.next_cursor.last_checked_at == FIXED_NOW
    assert batch.call.provider == "youtube-rss"


def test_rss_skips_seen_and_old_unknown_without_backfill() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    cursor = DiscoveryCursor(
        channel_id="UC_example",
        latest_published_at=T9,
        latest_video_id="vid_dup",
        provider_cursor="keep-me",
    )
    batch = provider.discover(CHANNEL, cursor)
    # Only items strictly newer than (T9, vid_dup)
    assert batch.video_ids == ("vid_new_1",)
    # Old unknown vid_old / vid_mid are not backfilled
    assert "vid_old" not in batch.video_ids
    assert "vid_mid" not in batch.video_ids
    assert batch.next_cursor.provider_cursor == "keep-me"
    assert batch.next_cursor.latest_video_id == "vid_new_1"


def test_rss_empty_batch_preserves_cursor_fields() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    cursor = DiscoveryCursor(
        channel_id="UC_example",
        latest_published_at=T10,
        latest_video_id="vid_new_1",
        provider_cursor="p1",
        last_checked_at=T0,
    )
    batch = provider.discover(CHANNEL, cursor)
    assert batch.video_ids == ()
    assert batch.next_cursor.latest_published_at == T10
    assert batch.next_cursor.latest_video_id == "vid_new_1"
    assert batch.next_cursor.provider_cursor == "p1"
    assert batch.next_cursor.last_checked_at == FIXED_NOW


def test_rss_same_publish_time_tiebreak_keeps_provider_order() -> None:
    channel = ChannelRef(channel_id="UC_tie")
    provider = _rss_provider(_load_bytes("rss_tiebreak.xml"))
    # Cursor frontier is mid-alphabet at same timestamp: only higher video_id is new
    cursor = DiscoveryCursor(
        channel_id="UC_tie",
        latest_published_at=datetime(2026, 7, 5, 10, 0, 0, tzinfo=UTC),
        latest_video_id="vid_b",
    )
    batch = provider.discover(channel, cursor)
    # Provider order was b, a, c — only c is newer than vid_b at same time
    assert batch.video_ids == ("vid_c",)
    assert batch.next_cursor.latest_video_id == "vid_c"


def test_rss_stable_results_for_same_fixture_and_cursor() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    cursor = DiscoveryCursor(
        channel_id="UC_example",
        latest_published_at=T8,
        latest_video_id="vid_mid",
    )
    first = provider.discover(CHANNEL, cursor)
    second = provider.discover(CHANNEL, cursor)
    assert first.video_ids == second.video_ids
    assert first.next_cursor.latest_video_id == second.next_cursor.latest_video_id
    assert first.next_cursor.latest_published_at == second.next_cursor.latest_published_at


# ---------------------------------------------------------------------------
# RSS error mapping + redaction
# ---------------------------------------------------------------------------


def test_rss_timeout_maps_to_transient_network() -> None:
    provider = _rss_provider(b"", raise_on_open=TimeoutError("sleeping"))
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    err = exc_info.value.error
    assert err.code is ErrorCode.TRANSIENT_NETWORK
    assert err.retryable is True
    assert err.stage is ProcessingStage.DISCOVERY
    assert "sleeping" not in err.message


def test_rss_http_429_is_rate_limited() -> None:
    headers = {"Retry-After": "12"}
    http_err = HTTPError(
        "https://example.invalid/feed",
        429,
        "Too Many",
        headers,  # type: ignore[arg-type]
        io.BytesIO(b"SECRET_BODY_SHOULD_NOT_LEAK"),
    )
    provider = _rss_provider(b"", raise_on_open=http_err)
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    err = exc_info.value.error
    assert err.code is ErrorCode.RATE_LIMITED
    assert err.retryable is True
    assert err.retry_after_seconds == 12.0
    assert "SECRET_BODY" not in err.message
    assert "SECRET_BODY" not in str(exc_info.value)


def test_rss_http_503_is_provider_unavailable() -> None:
    http_err = HTTPError(
        "https://example.invalid/feed",
        503,
        "Unavailable",
        None,
        io.BytesIO(b"<html>raw</html>"),
    )
    provider = _rss_provider(b"", raise_on_open=http_err)
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    assert exc_info.value.error.code is ErrorCode.PROVIDER_UNAVAILABLE
    assert "raw" not in exc_info.value.error.message


def test_rss_oversized_response_is_invalid_response() -> None:
    body = b"x" * 100
    provider = _rss_provider(body, max_response_bytes=50)
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert "size" in exc_info.value.error.message.lower()


def test_rss_malformed_xml_is_invalid_response() -> None:
    provider = _rss_provider(b"<feed><entry></broken")
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    err = exc_info.value.error
    assert err.code is ErrorCode.INVALID_RESPONSE
    assert "<feed>" not in err.message
    assert "/Users/" not in err.message


def test_rss_url_error_is_provider_unavailable() -> None:
    provider = _rss_provider(b"", raise_on_open=URLError("connection refused"))
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    assert exc_info.value.error.code is ErrorCode.PROVIDER_UNAVAILABLE


def test_rss_mismatched_cursor_channel_fails() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(
            CHANNEL,
            DiscoveryCursor(channel_id="UC_other"),
        )
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


# ---------------------------------------------------------------------------
# DiscoveryService + Fake repository transaction semantics
# ---------------------------------------------------------------------------


def test_discover_and_save_all_or_nothing_and_idempotent() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    repo = FakeDiscoveryRepository()
    service = DiscoveryService(provider, repo)

    batch = service.discover_and_save(CHANNEL)
    assert batch.video_ids == ("vid_new_1", "vid_dup", "vid_mid", "vid_old")
    assert set(repo.videos) == set(batch.video_ids)
    assert all(status is PipelineStatus.DISCOVERED for status in repo.videos.values())
    assert repo.cursors["UC_example"].latest_video_id == "vid_new_1"
    assert len(repo.save_events) == 1

    # Repeat with advanced cursor → empty batch still updates last_checked_at
    batch2 = service.discover_and_save(CHANNEL)
    assert batch2.video_ids == ()
    assert len(repo.videos) == 4
    assert len(repo.save_events) == 2
    # No duplicate rows / pipeline regression
    assert all(status is PipelineStatus.DISCOVERED for status in repo.videos.values())


def test_candidate_write_failure_rolls_back_cursor() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    repo = FakeDiscoveryRepository(fail_on_video_id="vid_mid")
    service = DiscoveryService(provider, repo)
    with pytest.raises(AdapterError):
        service.discover_and_save(CHANNEL)
    assert repo.videos == {}
    assert "UC_example" not in repo.cursors
    assert repo.save_events == []


def test_expected_cursor_conflict_rolls_back() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    repo = FakeDiscoveryRepository(cursor_conflict=True)
    service = DiscoveryService(provider, repo)
    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL)
    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert repo.videos == {}
    assert repo.cursors == {}


def test_metadata_failure_does_not_rollback_discovery() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    repo = FakeDiscoveryRepository()
    service = DiscoveryService(provider, repo)

    batch = service.discover_and_save(CHANNEL)
    assert batch.video_ids
    saved_cursor = repo.cursors["UC_example"]
    saved_videos = dict(repo.videos)

    class BoomMeta:
        def fetch(self, video_id: str) -> object:
            raise AdapterError(
                __import__("youtube_intel.discovery", fromlist=["_app_error"])._app_error(
                    ErrorCode.CONTENT_UNAVAILABLE,
                    "video content unavailable (private)",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            )

    service_with_meta = DiscoveryService(provider, repo, BoomMeta())
    with pytest.raises(AdapterError) as exc_info:
        service_with_meta.fetch_and_store_metadata("vid_new_1")
    assert exc_info.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    # Discovery state intact
    assert repo.cursors["UC_example"] == saved_cursor
    assert repo.videos == saved_videos
    assert "vid_new_1" in repo.unavailable
    assert repo.unavailable["vid_new_1"][0] is Availability.PRIVATE


def test_metadata_success_upserts_independently() -> None:
    provider = _rss_provider(_load_bytes("rss_sample.xml"))
    repo = FakeDiscoveryRepository()
    service = DiscoveryService(provider, repo)
    service.discover_and_save(CHANNEL)

    class FixedMeta:
        def fetch(self, video_id: str) -> VideoMetadata:
            return youtube_mod._map_info_dict_to_video_metadata(_load_json("info_public.json"))

    service_with_meta = DiscoveryService(provider, repo, FixedMeta())
    meta = service_with_meta.fetch_and_store_metadata("public_vid1")
    assert meta.video_id == "public_vid1"
    assert repo.metadata["public_vid1"].title == "Public Example Video"
    # Discovery still present
    assert "vid_new_1" in repo.videos


# ---------------------------------------------------------------------------
# Language summary + metadata mapping (unit, private helpers + Provider path)
# ---------------------------------------------------------------------------


def test_available_languages_manual_then_auto_dedup_no_urls() -> None:
    info = _load_json("info_public.json")
    langs = youtube_mod._summarize_available_languages(
        info["subtitles"], info["automatic_captions"]
    )
    assert langs == ("en", "zh-Hans", "ja", "fr")
    serialized = json.dumps(langs)
    assert "http" not in serialized
    assert "vtt" not in serialized


def test_map_public_shorts_live_upcoming_ended_restricted() -> None:
    public = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_public.json"))
    assert public.availability is Availability.PUBLIC
    assert public.live_status is LiveStatus.NONE
    assert public.duration_seconds == 600
    assert public.default_language == "en"
    assert public.available_languages[0] == "en"
    assert public.title == "Public Example Video"

    shorts = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_shorts.json"))
    assert shorts.duration_seconds == 45
    assert shorts.availability is Availability.PUBLIC

    live = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_live.json"))
    assert live.live_status is LiveStatus.LIVE

    upcoming = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_upcoming.json"))
    assert upcoming.live_status is LiveStatus.UPCOMING

    ended = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_ended.json"))
    assert ended.live_status is LiveStatus.ENDED

    restricted = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_restricted.json"))
    assert restricted.availability is Availability.RESTRICTED


def test_title_update_mapping() -> None:
    updated = youtube_mod._map_info_dict_to_video_metadata(_load_json("info_title_update.json"))
    assert updated.video_id == "public_vid1"
    assert "Updated Title" in updated.title


def test_private_partial_does_not_forge_empty_metadata() -> None:
    with pytest.raises(AdapterError) as exc_info:
        youtube_mod._map_info_dict_to_video_metadata(_load_json("info_private_partial.json"))
    err = exc_info.value.error
    assert err.code is ErrorCode.CONTENT_UNAVAILABLE
    assert "private" in err.message.lower()


def test_safe_ydl_opts_have_no_download_cookie_remote_or_ffmpeg() -> None:
    """Prove safe options via private builder + private test hooks on Provider."""
    opts = youtube_mod._build_ydl_opts(socket_timeout=30.0)
    assert opts["skip_download"] is True
    assert opts["noplaylist"] is True
    assert opts["quiet"] is True
    assert opts["ignoreconfig"] is True
    assert opts["writesubtitles"] is False
    assert opts["writeautomaticsub"] is False
    assert opts["writethumbnail"] is False
    assert opts["usenetrc"] is False
    forbidden_keys = {
        "cookiefile",
        "cookiesfrombrowser",
        "username",
        "password",
        "netrc_location",
        "remote_components",
        "ffmpeg_location",
        "hls_prefer_native",
    }
    assert forbidden_keys.isdisjoint(opts.keys())
    assert forbidden_keys.isdisjoint(youtube_mod._SAFE_YDL_OPTS.keys())
    for value in opts.values():
        if isinstance(value, str):
            assert not value.startswith("/Users/")
            assert "cookie" not in value.lower()

    captured: list[object] = []

    class _Handle:
        def extract_info(self, url: str, download: bool = True) -> object:
            assert download is False
            assert "public_vid1" in url
            return _load_json("info_public.json")

    def factory(raw_opts: dict[str, Any]) -> _Handle:
        captured.append(dict(raw_opts))
        return _Handle()

    provider = YtDlpMetadataProvider(timeout_seconds=30.0)
    youtube_mod._bind_test_hooks(
        provider,
        ydl_factory=factory,
        opts_sink=captured,
        clock=lambda: FIXED_NOW,
    )
    meta = provider.fetch("public_vid1")
    assert isinstance(meta, VideoMetadata)
    assert meta.title == "Public Example Video"
    assert captured
    for item in captured:
        assert isinstance(item, dict)
        assert item["skip_download"] is True
        assert item["writesubtitles"] is False
        assert "cookiefile" not in item
        assert "remote_components" not in item
        assert "ffmpeg_location" not in item
    assert "last_opts" not in vars(provider)
    assert not hasattr(YtDlpMetadataProvider, "last_opts")


def _annotation_mentions_free_dict(annotation: object) -> bool:
    """True for free-form dict/Mapping or unchecked wide types (Any/object)."""
    if annotation is Any or annotation is object:
        return True
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is dict:
        return True
    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin))
        if origin_name in {"Mapping", "MutableMapping", "dict"}:
            return True
        return any(_annotation_mentions_free_dict(arg) for arg in args)

    if annotation is dict:
        return True
    text = str(annotation)
    if text in {"typing.Any", "Any", "object"}:
        return True
    if "dict[" in text or "Dict[" in text:
        return True
    if "Mapping[" in text:
        return True
    return False


def test_public_youtube_api_has_no_free_form_dict_surface() -> None:
    """Regression (P1): public surface has no free-dict helpers or test injection."""
    assert youtube_mod.__all__ == ["YtDlpMetadataProvider"]

    # Non-private raw-boundary callables/values must not exist.
    banned_public_names = (
        "SAFE_YDL_OPTS",
        "build_ydl_opts",
        "summarize_available_languages",
        "map_live_status",
        "map_availability",
        "map_published_at",
        "map_info_dict_to_video_metadata",
        "bind_test_hooks",
        "YdlFactory",
        "Clock",
    )
    for banned in banned_public_names:
        assert banned not in youtube_mod.__all__
        assert banned not in vars(youtube_mod), f"non-private residual still present: {banned}"

    # Private builders / hooks exist only under private names.
    assert hasattr(youtube_mod, "_SAFE_YDL_OPTS")
    assert hasattr(youtube_mod, "_build_ydl_opts")
    assert hasattr(youtube_mod, "_map_info_dict_to_video_metadata")
    assert hasattr(youtube_mod, "_bind_test_hooks")
    assert getattr(youtube_mod, "map_info_dict_to_video_metadata", None) is None

    public_cls = YtDlpMetadataProvider
    sig = inspect.signature(public_cls.__init__)
    param_names = [name for name in sig.parameters if name != "self"]
    assert param_names == ["timeout_seconds"], (
        f"public constructor must only take timeout_seconds, got {param_names}"
    )
    forbidden_ctor = {"ydl_factory", "last_opts", "clock", "opts_sink", "factory"}
    assert forbidden_ctor.isdisjoint(sig.parameters.keys())

    for name, method in (
        ("__init__", public_cls.__init__),
        ("fetch", public_cls.fetch),
    ):
        hints = get_type_hints(method, include_extras=True)
        for param, annotation in hints.items():
            assert not _annotation_mentions_free_dict(annotation), (
                f"YtDlpMetadataProvider.{name} param {param} has free-dict annotation: {annotation!r}"
            )
            # No object/Any disguised injection slots on the public constructor.
            if name == "__init__" and param not in {"return", "timeout_seconds"}:
                assert annotation is not object and annotation is not Any

    for attr_name, annotation in getattr(public_cls, "__annotations__", {}).items():
        if attr_name.startswith("_"):
            continue
        assert not _annotation_mentions_free_dict(annotation), (
            f"public attribute {attr_name} has free-dict annotation: {annotation!r}"
        )
        assert attr_name not in {"last_opts", "ydl_factory", "clock"}


# ---------------------------------------------------------------------------
# Reviewer REJECT regressions (P1/P2/P3)
# ---------------------------------------------------------------------------


def test_malformed_ytdlp_payload_is_safe_adapter_error() -> None:
    """P1: invalid external fields must not leak ValueError/TypeError/payload text."""
    bad_date = {
        "id": "public1x",
        "title": "T",
        "channel_id": "UC_example",
        "channel": "Example Channel",
        "upload_date": "20261399",  # invalid calendar date
        "duration": 10,
        "availability": "public",
        "live_status": "not_live",
    }
    with pytest.raises(AdapterError) as exc_info:
        youtube_mod._map_info_dict_to_video_metadata(bad_date, requested_video_id="public1x")
    err = exc_info.value.error
    assert err.code is ErrorCode.INVALID_RESPONSE
    assert err.retryable is False
    assert err.stage is ProcessingStage.METADATA
    assert err.video_id == "public1x"
    assert "20261399" not in err.message
    assert "Traceback" not in err.message

    bad_age = {
        "id": "public1x",
        "title": "T",
        "channel_id": "UC_example",
        "channel": "Example Channel",
        "timestamp": 1720612800,
        "duration": 10,
        "availability": "public",
        "live_status": "not_live",
        "age_limit": "not-a-number",
    }
    with pytest.raises(AdapterError) as exc_info2:
        youtube_mod._map_info_dict_to_video_metadata(bad_age, requested_video_id="public1x")
    age_err = exc_info2.value.error
    assert age_err.code is ErrorCode.INVALID_RESPONSE
    assert age_err.retryable is False
    assert age_err.stage is ProcessingStage.METADATA
    assert age_err.video_id == "public1x"
    assert "not-a-number" not in age_err.message
    assert "age_limit" not in age_err.message or "invalid age_limit" in age_err.message

    # Via Provider.fetch path as well.
    class _Handle:
        def extract_info(self, url: str, download: bool = True) -> object:
            return bad_date

    provider = YtDlpMetadataProvider(timeout_seconds=10.0)
    youtube_mod._bind_test_hooks(provider, ydl_factory=lambda opts: _Handle())
    with pytest.raises(AdapterError) as fetch_exc:
        provider.fetch("public1x")
    assert fetch_exc.value.error.code is ErrorCode.INVALID_RESPONSE
    assert fetch_exc.value.error.video_id == "public1x"
    assert not isinstance(fetch_exc.value.__cause__, (ValueError, TypeError))


def test_illegal_age_limit_preserves_requested_video_id() -> None:
    """P1 (correction 4): invalid age_limit AppError always carries request identity."""
    requested = "reqage1"
    payload = {
        "id": requested,
        "title": "Age gated title",
        "description": "desc",
        "channel_id": "UC_example",
        "channel": "Example Channel",
        "timestamp": 1720612800,
        "duration": 90,
        "availability": "public",
        "live_status": "not_live",
        "age_limit": {"nested": "illegal"},  # non-int-coercible free-form value
        "subtitles": {},
        "automatic_captions": {},
    }

    # Direct helper path.
    with pytest.raises(AdapterError) as map_exc:
        youtube_mod._map_info_dict_to_video_metadata(payload, requested_video_id=requested)
    map_err = map_exc.value.error
    assert map_err.code is ErrorCode.INVALID_RESPONSE
    assert map_err.retryable is False
    assert map_err.stage is ProcessingStage.METADATA
    assert map_err.video_id == requested
    assert "nested" not in map_err.message
    assert "illegal" not in map_err.message
    assert not isinstance(map_exc.value.__cause__, (ValueError, TypeError))

    # Provider.fetch + repository must not store anything.
    class _Handle:
        def extract_info(self, url: str, download: bool = True) -> object:
            assert requested in url
            return payload

    provider = YtDlpMetadataProvider(timeout_seconds=10.0)
    youtube_mod._bind_test_hooks(provider, ydl_factory=lambda opts: _Handle())
    repo = FakeDiscoveryRepository()
    service = DiscoveryService(
        _rss_provider(_load_bytes("rss_sample.xml")),
        repo,
        provider,
    )
    with pytest.raises(AdapterError) as fetch_exc:
        service.fetch_and_store_metadata(requested)
    fetch_err = fetch_exc.value.error
    assert fetch_err.code is ErrorCode.INVALID_RESPONSE
    assert fetch_err.retryable is False
    assert fetch_err.stage is ProcessingStage.METADATA
    assert fetch_err.video_id == requested
    assert repo.metadata == {}
    assert requested not in repo.metadata


def test_response_video_id_must_match_request() -> None:
    """P1: mismatched payload id must not be stored under the wrong identity."""
    payload = _load_json("info_public.json")
    assert payload["id"] == "public_vid1"

    class _Handle:
        def extract_info(self, url: str, download: bool = True) -> object:
            return payload

    provider = YtDlpMetadataProvider(timeout_seconds=10.0)
    youtube_mod._bind_test_hooks(provider, ydl_factory=lambda opts: _Handle())
    repo = FakeDiscoveryRepository()
    service = DiscoveryService(
        _rss_provider(_load_bytes("rss_sample.xml")),
        repo,
        provider,
    )
    with pytest.raises(AdapterError) as exc_info:
        service.fetch_and_store_metadata("request1")
    err = exc_info.value.error
    assert err.code is ErrorCode.INVALID_RESPONSE
    assert err.video_id == "request1"
    assert "other" not in err.message
    assert "public_vid1" not in err.message or err.video_id == "request1"
    assert repo.metadata == {}
    assert "public_vid1" not in repo.metadata
    assert "request1" not in repo.metadata


def test_incomplete_rss_entry_fails_without_advancing_cursor() -> None:
    """P1: incomplete entry fails whole batch; later fixed older entry can still be found."""
    incomplete = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>vid_new_1</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Newest</title>
    <published>2026-07-10T12:00:00+00:00</published>
  </entry>
  <entry>
    <yt:channelId>UC_example</yt:channelId>
    <title>Missing video id</title>
    <published>2026-07-09T12:00:00+00:00</published>
  </entry>
</feed>
"""
    provider = _rss_provider(incomplete)
    repo = FakeDiscoveryRepository()
    service = DiscoveryService(provider, repo)
    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL)
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert exc_info.value.error.retryable is False
    assert repo.videos == {}
    assert "UC_example" not in repo.cursors

    # Later provider returns complete feed including older fixed entry.
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
    <yt:videoId>vid_fixed_old</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Previously incomplete</title>
    <published>2026-07-09T12:00:00+00:00</published>
  </entry>
</feed>
"""
    provider2 = _rss_provider(fixed)
    service2 = DiscoveryService(provider2, repo)
    batch = service2.discover_and_save(CHANNEL)
    assert "vid_fixed_old" in batch.video_ids
    assert "vid_new_1" in batch.video_ids
    assert repo.cursors["UC_example"].latest_video_id == "vid_new_1"


def test_rss_missing_channel_id_fails_without_backfill_or_cursor_advance() -> None:
    """P1 (correction 4): entry channelId is required; never backfill from request channel."""
    missing_channel = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>vid_new_1</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Newest</title>
    <published>2026-07-10T12:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>vid_fixed_old</yt:videoId>
    <title>Missing channel id</title>
    <published>2026-07-09T12:00:00+00:00</published>
  </entry>
</feed>
"""
    provider = _rss_provider(missing_channel)
    repo = FakeDiscoveryRepository()
    # Seed a pre-existing cursor that must remain untouched on failure.
    seeded = DiscoveryCursor(
        channel_id="UC_example",
        latest_video_id="seed_vid",
        latest_published_at=T0,
        provider_cursor="seed-cursor",
    )
    repo.cursors["UC_example"] = seeded
    videos_before = dict(repo.videos)
    service = DiscoveryService(provider, repo)

    with pytest.raises(AdapterError) as exc_info:
        service.discover_and_save(CHANNEL)
    err = exc_info.value.error
    assert err.code is ErrorCode.INVALID_RESPONSE
    assert err.retryable is False
    assert "backfill" not in err.message.lower()
    # Repository and cursor must be unchanged.
    assert repo.videos == videos_before
    assert repo.cursors["UC_example"] == seeded
    assert repo.save_events == []

    # After the feed is fixed (older entry now has channelId), discovery succeeds.
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
    <yt:videoId>vid_fixed_old</yt:videoId>
    <yt:channelId>UC_example</yt:channelId>
    <title>Previously missing channel</title>
    <published>2026-07-09T12:00:00+00:00</published>
  </entry>
</feed>
"""
    # Reset to empty cursor frontier so both entries are candidates.
    repo.cursors["UC_example"] = DiscoveryCursor(channel_id="UC_example")
    service2 = DiscoveryService(_rss_provider(fixed), repo)
    batch = service2.discover_and_save(CHANNEL)
    assert "vid_fixed_old" in batch.video_ids
    assert "vid_new_1" in batch.video_ids
    assert repo.cursors["UC_example"].latest_video_id == "vid_new_1"


def test_ytdlp_http_status_classification_order() -> None:
    """P1: 404/403/503 must classify before broad 'unavailable' text matches."""
    cases = [
        (
            "HTTP Error 404: Not Found (video unavailable)",
            ErrorCode.CONTENT_UNAVAILABLE,
            False,
        ),
        (
            "HTTP Error 403: Forbidden (video unavailable)",
            ErrorCode.PERMISSION_DENIED,
            False,
        ),
        (
            "HTTP Error 503: Service Unavailable",
            ErrorCode.PROVIDER_UNAVAILABLE,
            True,
        ),
        (
            "HTTP Error 429: Too Many Requests",
            ErrorCode.RATE_LIMITED,
            True,
        ),
    ]
    for message, code, retryable in cases:
        err = youtube_mod._map_ytdlp_exception(
            DownloadError(message),
            video_id="vid_http1",
        ).error
        assert err.code is code, message
        assert err.retryable is retryable, message
        assert err.video_id == "vid_http1"
        assert "HTML" not in err.message
        assert "<" not in err.message
        # Safe fixed messages only — never the raw provider exception text.
        assert message not in err.message
        assert err.message.startswith("yt-dlp") or err.message.startswith("video content")


def test_rss_response_closed_on_read_timeout() -> None:
    """P2: response must close on read failures, not only success."""

    class _TimeoutResponse:
        def __init__(self) -> None:
            self.closed = False

        def read(self, n: int = -1) -> bytes:
            raise TimeoutError("read timed out")

        def close(self) -> None:
            self.closed = True

    resp = _TimeoutResponse()
    provider = YouTubeRssSourceProvider(
        timeout_seconds=5.0,
        opener=lambda request, timeout: resp,
        clock=lambda: FIXED_NOW,
    )
    with pytest.raises(AdapterError) as exc_info:
        provider.discover(CHANNEL, DiscoveryCursor(channel_id="UC_example"))
    assert exc_info.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert resp.closed is True


def test_needs_auth_is_restricted_not_public() -> None:
    """P2: needs_auth under V1 no-login policy maps to RESTRICTED."""
    info = {
        "id": "authvid1",
        "title": "Members content",
        "description": "x",
        "channel_id": "UC_example",
        "channel": "Example Channel",
        "timestamp": 1720612800,
        "duration": 60,
        "availability": "needs_auth",
        "live_status": "not_live",
        "subtitles": {},
        "automatic_captions": {},
    }
    meta = youtube_mod._map_info_dict_to_video_metadata(info, requested_video_id="authvid1")
    assert meta.availability is Availability.RESTRICTED
