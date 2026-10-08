"""Public channel aliases and bounded Atom discovery, without account state."""
from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections.abc import Callable
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

from youtube_intel.discovery import AdapterError, YouTubeRssSourceProvider
from youtube_intel.following_provider import (
    Candidate,
    Enumeration,
    SourceIdentity,
    TrackingError,
)
from youtube_intel.providers.bilibili import (
    BilibiliError,
)
from youtube_intel.providers.youtube_network import channel_feed, channel_page

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
    return TrackingError('RATE_LIMITED' if '429' in text else 'ACCESS_DENIED' if any(x in text for x in ('403', 'sign in', 'private')) else 'NETWORK_UNAVAILABLE' if any(x in text for x in ('timed out', 'timeout', 'network', 'unable to download')) else 'METADATA_FAILED')


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
        raw = public_operation(lambda: self._fetch(identity.channel_id))
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
        prior = sorted((item for item in known if verified_at is not None and item.published_at <= verified_at), key=lambda item: (item.published_at, item.identity), reverse=True)[:3]
        complete = initial or (bool(prior) and all(item.identity in items and items[item.identity] == item for item in prior)) or (not known and len(items) < MAX_ENTRIES)
        return Enumeration(name, tuple(items.values()), complete, 1)

    def enroll(self, identity: str, *, channel_id: str, source_id: str,
               followed_at: datetime) -> str:
        enroll_video = self.enroll_video
        if enroll_video is None:
            raise TrackingError('CHECK_UNAVAILABLE')
        result = public_operation(lambda: enroll_video(identity, channel_id=channel_id, source_id=source_id, followed_at=followed_at))
        if result != identity:
            raise TrackingError('SOURCE_UNTRUSTED')
        return identity
