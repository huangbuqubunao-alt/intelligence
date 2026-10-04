"""Public channel aliases and bounded Atom discovery, without account state."""
from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections.abc import Callable
from datetime import datetime
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
    _PinnedHTTPS,
    public_addresses,
)
from youtube_intel.providers.youtube import _build_ydl_opts

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
    canonical_channel(channel_id)
    host = 'www.youtube.com'
    connection = _PinnedHTTPS(host, public_addresses(host)[0])
    deadline = time.monotonic() + 10
    try:
        connection.request('GET', '/feeds/videos.xml?channel_id=' + channel_id,
                           headers={'User-Agent': 'YIA-PublicContent/1.0', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        if response.status != 200:
            raise TrackingError({429: 'RATE_LIMITED', 401: 'ACCESS_DENIED', 403: 'ACCESS_DENIED', 404: 'NOT_FOUND'}.get(response.status, 'NETWORK_UNAVAILABLE' if response.status >= 500 else 'METADATA_FAILED'))
        if response.getheader('Content-Encoding', 'identity') != 'identity':
            raise TrackingError('METADATA_FAILED')
        body = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TrackingError('NETWORK_UNAVAILABLE')
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(16384, MAX_FEED + 1 - len(body)))
            if not chunk:
                return bytes(body)
            body.extend(chunk)
            if len(body) > MAX_FEED:
                raise TrackingError('RESPONSE_TOO_LARGE')
    finally:
        connection.close()


class YouTubeFollowingProvider:
    provider = 'YOUTUBE'

    def __init__(self, *, enroll_video: Callable[..., str] | None = None) -> None:
        self.enroll_video = enroll_video
        self._fetch: Callable[[str], bytes] = _feed
        self._resolve: Callable[[str], SourceIdentity] = self._resolve_public

    def _resolve_public(self, alias: str) -> SourceIdentity:
        url = 'https://www.youtube.com/' + (alias if alias.startswith('@') else 'channel/' + alias)
        opts = _build_ydl_opts(socket_timeout=10)
        opts.update(noplaylist=False, extract_flat=True, playlistend=1, lazy_playlist=True,
                    retries=0, extractor_retries=0, fragment_retries=0, proxy='')
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url + '/videos', download=False)
        if not isinstance(info, dict):
            raise TrackingError('METADATA_FAILED')
        channel = canonical_channel(info.get('channel_id') or info.get('id') or '', info.get('channel') or info.get('uploader') or info.get('title') or '')
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
        raw = public_operation(lambda: self._fetch(identity.channel_id))
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FEED or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise TrackingError('METADATA_FAILED')
        try:
            root = ET.fromstring(raw)
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
            if root.tag != '{' + ns['atom'] + '}feed' or root.findtext('yt:channelId', namespaces=ns) != identity.channel_id:
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
