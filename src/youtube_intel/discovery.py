"""Channel discovery application service and YouTube RSS Source Adapter.

Consumes frozen domain contracts from ``domain.py``. Does not import SQLite
implementations (TASK-003) or mutate ``domain.py`` / ``state.py``.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Protocol, runtime_checkable
from xml.etree.ElementTree import Element

from youtube_intel.domain import (
    AppError,
    Availability,
    ChannelRef,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    MetadataProvider,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    SourceProvider,
    VideoMetadata,
)

# Atom / YouTube RSS namespaces
_ATOM_NS = "http://www.w3.org/2005/Atom"
_YT_NS = "http://www.youtube.com/xml/schemas/2015"
_NS = {"atom": _ATOM_NS, "yt": _YT_NS}

_DEFAULT_USER_AGENT = "youtube-intel/0.1 (+local; RSS discovery; no media download)"
_DEFAULT_MAX_RESPONSE_BYTES = 2_000_000
_RSS_PROVIDER_NAME = "youtube-rss"
_RSS_FEED_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

Clock = Callable[[], datetime]
UrlOpener = Callable[[urllib.request.Request, float], object]


class AdapterError(Exception):
    """Task-scoped wrapper carrying a safe, named ``AppError`` payload.

    Not a public cross-module contract; call sites inspect ``error``.
    """

    def __init__(self, error: AppError) -> None:
        super().__init__(error.message)
        self.error = error


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _redact_message(message: str) -> str:
    """Keep messages short and free of response bodies / paths / secrets."""
    cleaned = " ".join(message.split())
    if len(cleaned) > 500:
        cleaned = cleaned[:500] + "…"
    # Drop absolute filesystem paths if any slipped in.
    parts: list[str] = []
    for token in cleaned.split():
        if token.startswith("/") and len(token) > 1 and not token.startswith("//"):
            parts.append("[path]")
        elif "cookie" in token.lower() or "authorization=" in token.lower():
            parts.append("[redacted]")
        else:
            parts.append(token)
    return " ".join(parts) or "provider error"


def _app_error(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool,
    retry_after_seconds: float | None = None,
    video_id: str | None = None,
    stage: ProcessingStage | None = ProcessingStage.DISCOVERY,
) -> AppError:
    return AppError(
        code=code,
        message=_redact_message(message),
        retryable=retryable,
        retry_after_seconds=retry_after_seconds,
        video_id=video_id,
        stage=stage,
    )


def _raise_adapter(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool,
    retry_after_seconds: float | None = None,
    video_id: str | None = None,
    stage: ProcessingStage | None = ProcessingStage.DISCOVERY,
) -> None:
    raise AdapterError(
        _app_error(
            code,
            message,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
            video_id=video_id,
            stage=stage,
        )
    )


# ---------------------------------------------------------------------------
# Narrow repository consumer protocol (TASK-003 implements; Fake for tests)
# ---------------------------------------------------------------------------


@runtime_checkable
class DiscoveryRepository(Protocol):
    """Consumer-side store semantics for discovery + metadata persistence.

    Concrete SQLite classes live in TASK-003 and must not be imported here.
    """

    def get_cursor(self, channel_id: str) -> DiscoveryCursor:
        """Return the persisted cursor for ``channel_id`` (or an empty one)."""
        ...

    def save_discovery_batch(
        self,
        batch: DiscoveryBatch,
        *,
        expected_cursor: DiscoveryCursor,
    ) -> None:
        """Atomically upsert all batch candidates as DISCOVERED and CAS cursor.

        All candidates and ``batch.next_cursor`` succeed together, or the whole
        transaction rolls back (including when expected cursor does not match).
        """
        ...

    def upsert_metadata(self, metadata: VideoMetadata) -> None:
        """Persist complete video metadata for an already-discovered candidate."""
        ...

    def mark_unavailable(
        self,
        video_id: str,
        *,
        availability: Availability,
        error: AppError,
    ) -> None:
        """Record content unavailability without rolling back discovery state."""
        ...


@dataclass
class FakeDiscoveryRepository:
    """In-memory Fake proving all-or-nothing batch/cursor and independent metadata."""

    cursors: dict[str, DiscoveryCursor] = field(default_factory=dict)
    videos: dict[str, PipelineStatus] = field(default_factory=dict)
    metadata: dict[str, VideoMetadata] = field(default_factory=dict)
    unavailable: dict[str, tuple[Availability, AppError]] = field(default_factory=dict)
    save_events: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    fail_save_once: bool = False
    fail_on_video_id: str | None = None
    cursor_conflict: bool = False

    def get_cursor(self, channel_id: str) -> DiscoveryCursor:
        existing = self.cursors.get(channel_id)
        if existing is not None:
            return existing
        return DiscoveryCursor(channel_id=channel_id)

    def save_discovery_batch(
        self,
        batch: DiscoveryBatch,
        *,
        expected_cursor: DiscoveryCursor,
    ) -> None:
        if batch.channel_id != expected_cursor.channel_id:
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "discovery batch channel_id does not match expected cursor",
                    retryable=False,
                )
            )
        if batch.next_cursor.channel_id != batch.channel_id:
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "next_cursor.channel_id must match batch channel_id",
                    retryable=False,
                )
            )
        if self.cursor_conflict:
            raise AdapterError(
                _app_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "expected cursor conflict; discovery batch rolled back",
                    retryable=True,
                )
            )
        current = self.get_cursor(batch.channel_id)
        if current != expected_cursor:
            raise AdapterError(
                _app_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "expected cursor mismatch; discovery batch rolled back",
                    retryable=True,
                )
            )
        if self.fail_save_once:
            self.fail_save_once = False
            raise AdapterError(
                _app_error(
                    ErrorCode.LOCAL_RESOURCE,
                    "simulated repository write failure; batch rolled back",
                    retryable=True,
                )
            )
        if self.fail_on_video_id is not None and self.fail_on_video_id in batch.video_ids:
            raise AdapterError(
                _app_error(
                    ErrorCode.LOCAL_RESOURCE,
                    f"simulated failure on candidate {self.fail_on_video_id}; batch rolled back",
                    retryable=True,
                )
            )

        # Snapshot for rollback semantics
        videos_before = dict(self.videos)
        cursors_before = dict(self.cursors)
        try:
            for video_id in batch.video_ids:
                # Idempotent upsert: never create a second row or regress pipeline.
                if video_id not in self.videos:
                    self.videos[video_id] = PipelineStatus.DISCOVERED
            self.cursors[batch.channel_id] = batch.next_cursor
            self.save_events.append((batch.channel_id, batch.video_ids))
        except Exception:
            self.videos = videos_before
            self.cursors = cursors_before
            raise

    def upsert_metadata(self, metadata: VideoMetadata) -> None:
        self.metadata[metadata.video_id] = metadata

    def mark_unavailable(
        self,
        video_id: str,
        *,
        availability: Availability,
        error: AppError,
    ) -> None:
        self.unavailable[video_id] = (availability, error)


# ---------------------------------------------------------------------------
# Discovery application service
# ---------------------------------------------------------------------------


class DiscoveryService:
    """Applies SourceProvider batches via DiscoveryRepository; metadata is independent."""

    def __init__(
        self,
        source: SourceProvider,
        repository: DiscoveryRepository,
        metadata_provider: MetadataProvider | None = None,
    ) -> None:
        self._source = source
        self._repository = repository
        self._metadata_provider = metadata_provider

    def discover_and_save(self, channel: ChannelRef) -> DiscoveryBatch:
        expected = self._repository.get_cursor(channel.channel_id)
        if expected.channel_id != channel.channel_id:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "stored cursor channel_id does not match channel",
                retryable=False,
            )
        batch = self._source.discover(channel, expected)
        if batch.channel_id != channel.channel_id:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "provider returned discovery batch for a different channel",
                retryable=False,
            )
        if batch.next_cursor.channel_id != channel.channel_id:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "provider next_cursor.channel_id does not match channel",
                retryable=False,
            )
        self._repository.save_discovery_batch(batch, expected_cursor=expected)
        return batch

    def fetch_and_store_metadata(self, video_id: str) -> VideoMetadata:
        """Fetch one video's metadata; failures never roll back discovery batches."""
        if self._metadata_provider is None:
            _raise_adapter(
                ErrorCode.CONFIG_INVALID,
                "metadata provider is not configured",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
            raise AssertionError("unreachable")
        try:
            metadata = self._metadata_provider.fetch(video_id)
        except AdapterError as exc:
            if exc.error.code is ErrorCode.CONTENT_UNAVAILABLE:
                availability = _availability_from_error_message(exc.error.message)
                self._repository.mark_unavailable(
                    video_id,
                    availability=availability,
                    error=exc.error,
                )
            raise
        self._repository.upsert_metadata(metadata)
        return metadata


def _availability_from_error_message(message: str) -> Availability:
    lower = message.lower()
    if "private" in lower:
        return Availability.PRIVATE
    if "delete" in lower:
        return Availability.DELETED
    if "restrict" in lower or "geo" in lower or "region" in lower:
        return Availability.RESTRICTED
    return Availability.UNAVAILABLE


# ---------------------------------------------------------------------------
# RSS entry model + cursor comparison
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RssEntry:
    video_id: str
    channel_id: str
    published_at: datetime
    title: str


def _cursor_key(
    published_at: datetime | None,
    video_id: str | None,
) -> tuple[datetime, str] | None:
    if published_at is None:
        return None
    return (_ensure_aware(published_at), video_id or "")


def is_newer_than_cursor(
    published_at: datetime,
    video_id: str,
    cursor: DiscoveryCursor,
) -> bool:
    """True when (published_at, video_id) is strictly newer than the cursor frontier."""
    frontier = _cursor_key(cursor.latest_published_at, cursor.latest_video_id)
    if frontier is None:
        return True
    candidate = (_ensure_aware(published_at), video_id)
    return candidate > frontier


def max_cursor_frontier(
    entries: list[_RssEntry],
    current: DiscoveryCursor,
) -> tuple[datetime | None, str | None]:
    """Return the max (published_at, video_id) among current frontier and entries."""
    best_pub = current.latest_published_at
    best_vid = current.latest_video_id
    best = _cursor_key(best_pub, best_vid)
    for entry in entries:
        key = (entry.published_at, entry.video_id)
        if best is None or key > best:
            best = key
            best_pub = entry.published_at
            best_vid = entry.video_id
    return best_pub, best_vid


# ---------------------------------------------------------------------------
# YouTube RSS SourceProvider
# ---------------------------------------------------------------------------


class YouTubeRssSourceProvider:
    """SourceProvider backed by YouTube channel Atom RSS (stdlib only)."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        user_agent: str = _DEFAULT_USER_AGENT,
        max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES,
        opener: UrlOpener | None = None,
        clock: Clock | None = None,
        feed_url_template: str = _RSS_FEED_TEMPLATE,
    ) -> None:
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be positive"
            raise ValueError(msg)
        if max_response_bytes <= 0:
            msg = "max_response_bytes must be positive"
            raise ValueError(msg)
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._max_response_bytes = max_response_bytes
        self._opener = opener or _default_urlopen
        self._clock = clock or _utcnow
        self._feed_url_template = feed_url_template

    def discover(self, channel: ChannelRef, cursor: DiscoveryCursor) -> DiscoveryBatch:
        if cursor.channel_id != channel.channel_id:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "cursor.channel_id does not match channel.channel_id",
                retryable=False,
            )
        started = self._clock()
        url = self._feed_url_template.format(channel_id=channel.channel_id)
        raw = self._fetch_feed(url)
        entries = self._parse_feed(raw, expected_channel_id=channel.channel_id)
        finished = self._clock()

        # Provider order; first occurrence of each video_id wins.
        ordered_unique: list[_RssEntry] = []
        seen: set[str] = set()
        for entry in entries:
            if entry.video_id in seen:
                continue
            seen.add(entry.video_id)
            ordered_unique.append(entry)

        new_entries = [
            e for e in ordered_unique if is_newer_than_cursor(e.published_at, e.video_id, cursor)
        ]
        video_ids = tuple(e.video_id for e in new_entries)

        if new_entries:
            latest_pub, latest_vid = max_cursor_frontier(new_entries, cursor)
            next_cursor = DiscoveryCursor(
                channel_id=channel.channel_id,
                last_checked_at=_ensure_aware(finished),
                latest_published_at=latest_pub,
                latest_video_id=latest_vid,
                provider_cursor=cursor.provider_cursor,
            )
        else:
            # Empty batch: update last_checked_at only; preserve other cursor fields.
            next_cursor = DiscoveryCursor(
                channel_id=channel.channel_id,
                last_checked_at=_ensure_aware(finished),
                latest_published_at=cursor.latest_published_at,
                latest_video_id=cursor.latest_video_id,
                provider_cursor=cursor.provider_cursor,
            )

        call = ProviderCallMetadata(
            provider=_RSS_PROVIDER_NAME,
            started_at=_ensure_aware(started),
            finished_at=_ensure_aware(finished),
            provider_version="stdlib-rss",
            diagnostics=(),
        )
        return DiscoveryBatch(
            channel_id=channel.channel_id,
            video_ids=video_ids,
            next_cursor=next_cursor,
            call=call,
        )

    def _fetch_feed(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/atom+xml, application/xml, text/xml, */*",
            },
            method="GET",
        )
        try:
            response = self._opener(request, self._timeout_seconds)
        except TimeoutError as exc:
            _raise_adapter(
                ErrorCode.TRANSIENT_NETWORK,
                "RSS feed request timed out",
                retryable=True,
            )
            raise AssertionError("unreachable") from exc
        except socket.timeout as exc:
            _raise_adapter(
                ErrorCode.TRANSIENT_NETWORK,
                "RSS feed request timed out",
                retryable=True,
            )
            raise AssertionError("unreachable") from exc
        except urllib.error.HTTPError as exc:
            self._map_http_error(exc)
            raise AssertionError("unreachable") from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                _raise_adapter(
                    ErrorCode.TRANSIENT_NETWORK,
                    "RSS feed request timed out",
                    retryable=True,
                )
            _raise_adapter(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "RSS feed provider unavailable",
                retryable=True,
            )
            raise AssertionError("unreachable") from exc
        except OSError as exc:
            _raise_adapter(
                ErrorCode.TRANSIENT_NETWORK,
                "RSS feed network error",
                retryable=True,
            )
            raise AssertionError("unreachable") from exc

        return self._read_limited(response)

    def _read_limited(self, response: object) -> bytes:
        read_attr = getattr(response, "read", None)
        if not callable(read_attr):
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS response object is not readable",
                retryable=False,
            )
            raise AssertionError("unreachable")
        read_fn: Callable[..., object] = read_attr
        # Prefer reading max+1 to detect overflow without trusting Content-Length.
        try:
            data = read_fn(self._max_response_bytes + 1)
        except TimeoutError:
            _raise_adapter(
                ErrorCode.TRANSIENT_NETWORK,
                "RSS feed read timed out",
                retryable=True,
            )
            raise AssertionError("unreachable")
        except OSError:
            _raise_adapter(
                ErrorCode.TRANSIENT_NETWORK,
                "RSS feed read failed",
                retryable=True,
            )
            raise AssertionError("unreachable")
        if not isinstance(data, (bytes, bytearray)):
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS response body is not bytes",
                retryable=False,
            )
            raise AssertionError("unreachable")
        body = bytes(data)
        if len(body) > self._max_response_bytes:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS response exceeds configured size limit",
                retryable=False,
            )
        close = getattr(response, "close", None)
        if callable(close):
            try:
                close()
            except OSError:
                pass
        return body

    def _map_http_error(self, exc: urllib.error.HTTPError) -> None:
        status = int(getattr(exc, "code", 0) or 0)
        # Never attach response body to the error.
        try:
            exc.close()
        except OSError:
            pass
        if status == 429:
            retry_after = _parse_retry_after_header(getattr(exc, "headers", None))
            _raise_adapter(
                ErrorCode.RATE_LIMITED,
                "RSS feed rate limited",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if 500 <= status <= 599:
            _raise_adapter(
                ErrorCode.PROVIDER_UNAVAILABLE,
                f"RSS feed provider HTTP {status}",
                retryable=True,
            )
        if status in {401, 403}:
            _raise_adapter(
                ErrorCode.PERMISSION_DENIED,
                f"RSS feed access denied HTTP {status}",
                retryable=False,
            )
        if status == 404:
            _raise_adapter(
                ErrorCode.CONTENT_UNAVAILABLE,
                "RSS feed not found",
                retryable=False,
            )
        _raise_adapter(
            ErrorCode.PROVIDER_UNAVAILABLE,
            f"RSS feed HTTP error {status}",
            retryable=True,
        )

    def _parse_feed(self, raw: bytes, *, expected_channel_id: str) -> list[_RssEntry]:
        if not raw.strip():
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS feed body is empty",
                retryable=False,
            )
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS feed XML is malformed",
                retryable=False,
            )
            raise AssertionError("unreachable")

        entries: list[_RssEntry] = []
        # Support default Atom namespace and un-namespaced test fixtures.
        entry_nodes = list(root.findall("atom:entry", _NS))
        if not entry_nodes:
            entry_nodes = list(root.findall("entry"))
        for node in entry_nodes:
            parsed = self._parse_entry(node, expected_channel_id=expected_channel_id)
            if parsed is not None:
                entries.append(parsed)
        return entries

    def _parse_entry(
        self,
        node: Element,
        *,
        expected_channel_id: str,
    ) -> _RssEntry | None:
        video_id = _child_text(node, "yt:videoId") or _child_text(node, "videoId")
        channel_id = (
            _child_text(node, "yt:channelId")
            or _child_text(node, "channelId")
            or expected_channel_id
        )
        title = _child_text(node, "atom:title") or _child_text(node, "title") or ""
        published_raw = _child_text(node, "atom:published") or _child_text(node, "published")
        if not video_id or not published_raw:
            # Skip incomplete entries rather than failing the whole feed.
            return None
        if channel_id != expected_channel_id:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS entry channel_id does not match requested channel",
                retryable=False,
            )
        published_at = _parse_datetime(published_raw)
        if published_at is None:
            _raise_adapter(
                ErrorCode.INVALID_RESPONSE,
                "RSS entry has invalid published timestamp",
                retryable=False,
            )
            raise AssertionError("unreachable")
        return _RssEntry(
            video_id=video_id,
            channel_id=channel_id,
            published_at=published_at,
            title=title,
        )


def _child_text(node: Element, path: str) -> str | None:
    if ":" in path:
        found = node.find(path, _NS)
    else:
        found = node.find(path)
    if found is None or found.text is None:
        return None
    text = found.text.strip()
    return text or None


def _parse_datetime(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    # ISO-8601 / RFC 3339 (YouTube Atom uses this).
    iso = text.replace("Z", "+00:00")
    try:
        return _ensure_aware(datetime.fromisoformat(iso))
    except ValueError:
        pass
    try:
        return _ensure_aware(parsedate_to_datetime(text))
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _parse_retry_after_header(headers: Mapping[str, str] | None) -> float | None:
    if headers is None:
        return None
    raw = None
    for key in ("Retry-After", "retry-after"):
        if key in headers:
            raw = headers[key]
            break
    if raw is None:
        return None
    try:
        seconds = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds


def _default_urlopen(request: urllib.request.Request, timeout: float) -> object:
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 — URL from channel_id template


__all__ = [
    "AdapterError",
    "DiscoveryRepository",
    "DiscoveryService",
    "FakeDiscoveryRepository",
    "YouTubeRssSourceProvider",
    "is_newer_than_cursor",
]
