"""Public channel aliases and bounded Atom discovery, without account state."""
from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, cast
from urllib.parse import urlsplit

import yt_dlp  # type: ignore[import-untyped]

from youtube_intel.discovery import AdapterError, YouTubeRssSourceProvider
from youtube_intel.following_provider import (
    Candidate,
    Enumeration,
    SourceIdentity,
    TrackingError,
)
from youtube_intel.providers.bilibili import (
    BilibiliError,
    public_addresses,
)
from youtube_intel.providers.youtube_network import (
    _HOST,
    _current_proxy,
    _proxy_address,
    channel_feed,
    channel_page,
)

CHANNEL_ID = re.compile(r'UC[A-Za-z0-9_-]{22}\Z')
VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}\Z')
HANDLE = re.compile(r'@[A-Za-z0-9._-]{3,100}\Z')
MAX_FEED = 256 * 1024
MAX_ENTRIES = 15
_SLOT = threading.BoundedSemaphore(1)
_LOCK = threading.Lock()
_NEXT = 0.0
_RATE_UNTIL = 0.0


def channel_input(value: str) -> str:
    if not isinstance(value, str) or not 0 < len(value) <= 2048 or any(unicodedata.category(c) in {'Cc', 'Cf', 'Cs'} for c in value):
        raise TrackingError('INVALID_INPUT')
    raw = value.strip()
    if CHANNEL_ID.fullmatch(raw) or HANDLE.fullmatch(raw):
        return raw
    try:
        url = urlsplit(raw)
        if url.scheme != 'https' or url.netloc.lower() not in {'youtube.com', 'www.youtube.com'} or url.query or url.fragment:
            raise ValueError()
        path = url.path.rstrip('/')
        if path.rsplit('/', 1)[-1] in {'videos', 'shorts', 'streams', 'playlists', 'about', 'featured'}:
            path = path.rsplit('/', 1)[0]
        if path.startswith('/channel/') and CHANNEL_ID.fullmatch(path[9:]):
            return path[9:]
        if path.startswith('/@') and HANDLE.fullmatch(path[1:]):
            return path[1:]
    except ValueError:
        pass
    raise TrackingError('INVALID_INPUT')


def canonical_channel(value: str, name: str = '') -> SourceIdentity:
    if not CHANNEL_ID.fullmatch(value):
        raise TrackingError('SOURCE_UNTRUSTED')
    if not isinstance(name, str) or len(name) > 200 or any(unicodedata.category(c) in {'Cc', 'Cf', 'Cs'} for c in name):
        raise TrackingError('METADATA_FAILED')
    return SourceIdentity('YOUTUBE', 'CHANNEL', value, 'youtube-channel-' + value,
                          'https://www.youtube.com/channel/' + value, name or value)


def youtube_error(error: Exception) -> TrackingError:
    if isinstance(error, TrackingError):
        return error
    if isinstance(error, AdapterError):
        return TrackingError({'TRANSIENT_NETWORK': 'NETWORK_UNAVAILABLE', 'PROVIDER_UNAVAILABLE': 'NETWORK_UNAVAILABLE',
            'RATE_LIMITED': 'RATE_LIMITED', 'PERMISSION_DENIED': 'ACCESS_DENIED', 'CONTENT_UNAVAILABLE': 'NOT_FOUND'}.get(error.error.code.value, 'METADATA_FAILED'))
    if isinstance(error, BilibiliError):
        return TrackingError(error.code)
    text = str(error).lower()
    if '429' in text:
        return TrackingError('RATE_LIMITED')
    if any(x in text for x in ('403', 'sign in', 'private')):
        return TrackingError('ACCESS_DENIED')
    if any(x in text for x in ('404', 'does not exist', 'not found')):
        return TrackingError('NOT_FOUND')
    if any(x in text for x in ('timed out', 'timeout', 'network', 'unable to download')):
        return TrackingError('NETWORK_UNAVAILABLE')
    return TrackingError('METADATA_FAILED')


def public_operation(operation: Callable[[], object]) -> object:
    """Independent YouTube budget; no retry loop or credential resolution."""
    global _NEXT, _RATE_UNTIL
    if not _SLOT.acquire(blocking=False):
        raise TrackingError('RATE_LIMITED')
    try:
        with _LOCK:
            if time.monotonic() < _RATE_UNTIL:
                raise TrackingError('RATE_LIMITED')
            delay = max(0.0, _NEXT - time.monotonic())
            if delay:
                time.sleep(delay)
            _NEXT = time.monotonic() + .5
        try:
            return operation()
        except Exception as failure:
            error = youtube_error(failure)
            if error.code in {'RATE_LIMITED', 'ACCESS_DENIED'}:
                with _LOCK:
                    _RATE_UNTIL = time.monotonic() + 900
            raise error from None
    finally:
        _SLOT.release()


def _feed(channel_id: str) -> bytes:
    return channel_feed(channel_id)


class _SilentYtDlpLogger:
    def debug(self, message: str) -> None:
        del message

    def warning(self, message: str) -> None:
        del message

    def error(self, message: str) -> None:
        del message


def _playlist_page(channel_id: str, start: int, end: int) -> Mapping[str, Any]:
    canonical_channel(channel_id)
    if start < 1 or end < start:
        raise TrackingError("METADATA_FAILED")
    proxy = _current_proxy()
    if proxy is None:
        try:
            addresses = public_addresses(_HOST)
        except BilibiliError:
            raise TrackingError("NETWORK_UNAVAILABLE") from None
        if not addresses:
            raise TrackingError("NETWORK_UNAVAILABLE")
        proxy_url = ""
    else:
        proxy_url = f"http://{_proxy_address(proxy)}:{proxy.port}"
    opts: dict[str, Any] = {
        "skip_download": True,
        "extract_flat": True,
        "playliststart": start,
        "playlistend": end,
        "socket_timeout": 15.0,
        "quiet": True,
        "no_warnings": True,
        "ignoreconfig": True,
        "no_color": True,
        "cachedir": False,
        "usenetrc": False,
        "proxy": proxy_url,
        "extractor_args": {"youtubetab": {"approximate_date": ["true"]}},
        "logger": _SilentYtDlpLogger(),
    }
    url = f"https://www.youtube.com/playlist?list=UU{channel_id[2:]}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, Mapping):
        raise TrackingError("METADATA_FAILED")
    return cast(Mapping[str, Any], info)


class _ChannelMetadata(HTMLParser):
    """Only public page identity metadata, never executable/content URLs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.identities: set[str] = set()
        self.name = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        identity_url = None
        if tag == "link" and values.get("rel") == "canonical":
            identity_url = values.get("href")
        elif tag == "meta" and values.get("property") == "og:url":
            identity_url = values.get("content")
        if identity_url is not None:
            parsed = urlsplit(identity_url)
            if (parsed.scheme != "https" or parsed.netloc != "www.youtube.com"
                    or parsed.query or parsed.fragment
                    or not parsed.path.startswith("/channel/")):
                raise TrackingError("METADATA_FAILED")
            self.identities.add(canonical_channel(parsed.path[9:]).channel_id)
        if tag == "meta" and values.get("itemprop") in {"identifier", "channelId"}:
            self.identities.add(canonical_channel(values.get("content") or "").channel_id)
        if tag == "meta" and values.get("property") == "og:title":
            self.name = values.get("content") or ""


class YouTubeFollowingProvider:
    provider = 'YOUTUBE'

    def __init__(self, *, enroll_video: Callable[..., str] | None = None) -> None:
        self.enroll_video = enroll_video
        self._fetch: Callable[[str], bytes] = _feed
        self._playlist_page: Callable[[str, int, int], Mapping[str, Any]] = _playlist_page
        self._resolve: Callable[[str], SourceIdentity] = self._resolve_public

    def _resolve_public(self, alias: str) -> SourceIdentity:
        raw = channel_page(alias)
        metadata = _ChannelMetadata()
        try:
            metadata.feed(raw.decode("utf-8"))
            metadata.close()
        except (UnicodeError, ValueError):
            raise TrackingError("METADATA_FAILED") from None
        if len(metadata.identities) != 1:
            raise TrackingError("METADATA_FAILED")
        channel = canonical_channel(next(iter(metadata.identities)), metadata.name)
        if CHANNEL_ID.fullmatch(alias) and channel.channel_id != alias:
            raise TrackingError('SOURCE_UNTRUSTED')
        return channel

    def resolve(self, value: str) -> SourceIdentity:
        alias = channel_input(value)
        result = public_operation(lambda: self._resolve(alias))
        if not isinstance(result, SourceIdentity) or result.provider != self.provider:
            raise TrackingError('METADATA_FAILED')
        canonical_channel(result.channel_id, result.name)
        return result

    def enumerate(self, identity: SourceIdentity, *, initial: bool, next_page: int,
                  known: tuple[Candidate, ...], verified_at: datetime | None) -> Enumeration:
        from xml.etree import ElementTree as ET
        canonical_channel(identity.channel_id, identity.name)
        prior = sorted(
            (item for item in known if verified_at is not None and item.published_at <= verified_at),
            key=lambda item: (item.published_at, item.identity),
            reverse=True,
        )[:3]
        try:
            raw = public_operation(lambda: self._fetch(identity.channel_id))
        except TrackingError as failure:
            if failure.code == 'NOT_FOUND' and self._fetch is _feed:
                return self._enumerate_uploads(
                    identity,
                    initial=initial,
                    next_page=next_page,
                    known=known,
                    prior=tuple(prior),
                )
            raise
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FEED or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise TrackingError('METADATA_FAILED')
        try:
            root = ET.fromstring(raw)
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
            feed_channel_id = root.findtext('yt:channelId', namespaces=ns)
            # Real YouTube Atom feed IDs omit UC; entry IDs remain canonical.
            # Retain the exact full form supported by historical fixtures.
            if feed_channel_id is not None and not CHANNEL_ID.fullmatch(feed_channel_id):
                feed_channel_id = 'UC' + feed_channel_id
            if root.tag != '{' + ns['atom'] + '}feed' or feed_channel_id != identity.channel_id:
                raise ValueError()
            entries = YouTubeRssSourceProvider()._parse_feed(raw, expected_channel_id=identity.channel_id)
            if len(entries) > MAX_ENTRIES:
                raise ValueError()
            items: dict[str, Candidate] = {}
            for entry in entries:
                if not VIDEO_ID.fullmatch(entry.video_id):
                    raise ValueError()
                item = Candidate(entry.video_id, entry.published_at)
                if item.identity in items and items[item.identity] != item:
                    raise ValueError()
                items[item.identity] = item
            name = root.findtext('atom:title', namespaces=ns) or identity.name
            canonical_channel(identity.channel_id, name)
        except (ValueError, ET.ParseError, AdapterError):
            raise TrackingError('METADATA_FAILED') from None
        # The newest three identities from the last verified window form an
        # overlap boundary. A missing anchor, empty changed shape or window jump
        # cannot close the gap. Failed scans never replace this boundary.
        complete = initial or (bool(prior) and all(item.identity in items and items[item.identity] == item for item in prior)) or (not known and len(items) < MAX_ENTRIES)
        return Enumeration(name, tuple(items.values()), complete, 1)

    def _enumerate_uploads(
        self,
        identity: SourceIdentity,
        *,
        initial: bool,
        next_page: int,
        known: tuple[Candidate, ...],
        prior: tuple[Candidate, ...],
    ) -> Enumeration:
        known_by_id = {item.identity: item for item in known}
        items: dict[str, Candidate] = {}
        name = identity.name
        reached_end = False

        def read_slice(start: int, end: int) -> None:
            nonlocal name, reached_end
            raw_page = public_operation(
                lambda: self._playlist_page(identity.channel_id, start, end)
            )
            if not isinstance(raw_page, Mapping) or raw_page.get('channel_id') != identity.channel_id:
                raise TrackingError('METADATA_FAILED')
            raw_name = raw_page.get('channel') or raw_page.get('uploader')
            if isinstance(raw_name, str) and raw_name.strip():
                canonical_channel(identity.channel_id, raw_name)
                name = raw_name
            entries = raw_page.get('entries')
            if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
                raise TrackingError('METADATA_FAILED')
            expected = end - start + 1
            if len(entries) > expected:
                raise TrackingError('METADATA_FAILED')
            if len(entries) < expected:
                reached_end = True
            for entry in entries:
                if not isinstance(entry, Mapping):
                    raise TrackingError('METADATA_FAILED')
                vid = entry.get('id')
                if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid):
                    raise TrackingError('METADATA_FAILED')
                if vid in known_by_id:
                    candidate = known_by_id[vid]
                else:
                    if entry.get('live_status') in {'is_upcoming', 'is_live'} or entry.get('is_live') is True:
                        continue
                    ts = entry.get('timestamp')
                    if not isinstance(ts, (int, float)) or isinstance(ts, bool) or ts <= 0:
                        continue
                    candidate = Candidate(vid, datetime.fromtimestamp(int(ts), tz=UTC))
                if vid in items and items[vid] != candidate:
                    raise TrackingError('METADATA_FAILED')
                items[vid] = candidate

        def anchors_matched() -> bool:
            return bool(prior) and all(
                item.identity in items and items[item.identity] == item for item in prior
            )

        if initial or (not prior and not known):
            read_slice(1, MAX_ENTRIES)
        elif next_page <= 1:
            read_slice(1, 30)
            if not reached_end and prior and not anchors_matched():
                read_slice(31, 90)
        else:
            read_slice(1, 30)
            if not reached_end and not anchors_matched():
                offset_start = 30 * next_page + 1
                read_slice(offset_start, offset_start + 59)

        complete = initial or anchors_matched() or (not known and reached_end)
        next_offset = 1 if complete or reached_end else min((3 if next_page <= 1 else next_page + 2), 33333)
        return Enumeration(name, tuple(items.values()), complete, next_offset)

    def enroll(self, identity: str, *, channel_id: str, source_id: str,
               followed_at: datetime) -> str:
        enroll_video = self.enroll_video
        if enroll_video is None:
            raise TrackingError('CHECK_UNAVAILABLE')
        result = public_operation(lambda: enroll_video(identity, channel_id=channel_id, source_id=source_id, followed_at=followed_at))
        if result != identity:
            raise TrackingError('SOURCE_UNTRUSTED')
        return identity
