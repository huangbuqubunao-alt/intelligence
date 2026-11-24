"""YouTube metadata Adapter via official yt-dlp Python API (no shell).

External free-form info dicts exist only as private implementation details inside
this module and are mapped to frozen ``VideoMetadata`` before leaving the
Adapter. Cross-module public API is ``YtDlpMetadataProvider`` only (see
``__all__``). Does not download media/subtitles, load cookies, enable remote
components, or invoke ffmpeg.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, MutableSequence
from datetime import UTC, datetime
from typing import Any, Final, Protocol

# yt-dlp is the only approved direct runtime dependency for this adapter.
import yt_dlp  # type: ignore[import-untyped]
from yt_dlp.utils import (  # type: ignore[import-untyped]
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
)

from youtube_intel.discovery import (
    AdapterError,
    _app_error,
    _ensure_aware,
    _redact_message,
)
from youtube_intel.domain import (
    Availability,
    DiagnosticEntry,
    ErrorCode,
    LiveStatus,
    ProcessingStage,
    ProviderCallMetadata,
    VideoMetadata,
)

_PROVIDER_NAME: Final = "yt-dlp"
_WATCH_URL: Final = "https://www.youtube.com/watch?v={video_id}"
_VIDEO_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


class _SilentYtDlpLogger:
    """Prevent the dependency from bypassing the Adapter's safe error boundary."""

    def debug(self, message: str) -> None:
        del message

    def warning(self, message: str) -> None:
        del message

    def error(self, message: str) -> None:
        del message

# ---------------------------------------------------------------------------
# Private yt-dlp option / mapping internals (NOT part of cross-module API)
# ---------------------------------------------------------------------------

# Options equivalent to single-video, skip_download, noplaylist, quiet, no media writes.
_SAFE_YDL_OPTS: Final[dict[str, Any]] = {
    "skip_download": True,
    "ignore_no_formats_error": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "ignoreconfig": True,
    "no_color": True,
    "cachedir": False,
    "writesubtitles": False,
    "writeautomaticsub": False,
    "writethumbnail": False,
    "writeinfojson": False,
    "writedescription": False,
    "writeannotations": False,
    "keepvideo": False,
    # Explicitly avoid network side-channels and local auth.
    "usenetrc": False,
    "extract_flat": False,
    "logger": _SilentYtDlpLogger(),
    # Do not set cookiefile / cookiesfrombrowser / username / password / netrc_location.
    # Do not set remote_components / allow_remote / ffmpeg_location / paths that download media.
}

_AUTH_GATE_MARKERS: Final[tuple[str, ...]] = (
    "sign in to confirm",
    "confirm you're not a bot",
    "confirm you\u2019re not a bot",
    "not a bot",
    "login_required",
)

_NETWORK_ERROR_MARKERS: Final[tuple[str, ...]] = (
    "unable to download webpage",
    "failed to establish",
    "connection refused",
    "connection reset",
    "connection aborted",
    "name or service not known",
    "nodename nor servname",
    "network is unreachable",
    "cannot connect to proxy",
    "proxy error",
    "proxyerror",
    "ssl:",
    "eof occurred in violation of protocol",
    "getaddrinfo failed",
)


def _resolve_system_proxy_url() -> str | None:
    try:
        from youtube_intel.providers.youtube_network import system_http_proxy_url

        proxy_url = system_http_proxy_url()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(proxy_url, str) or not proxy_url:
        return None
    if proxy_url.startswith("/Users/") or "cookie" in proxy_url.lower():
        return None
    return proxy_url


class _YdlHandle(Protocol):
    def extract_info(self, url: str, download: bool = True) -> object: ...


_Clock = Callable[[], datetime]
_YdlFactory = Callable[[dict[str, Any]], _YdlHandle]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _build_ydl_opts(*, socket_timeout: float | None = None) -> dict[str, Any]:
    """Private: fresh opts dict for a single metadata extract call."""
    opts = dict(_SAFE_YDL_OPTS)
    if socket_timeout is not None:
        opts["socket_timeout"] = socket_timeout
    proxy_url = _resolve_system_proxy_url()
    if proxy_url is not None:
        opts["proxy"] = proxy_url
    return opts


def _summarize_available_languages(
    subtitles: Mapping[str, Any] | None,
    automatic_captions: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Private: manual order first, then new auto languages; no URLs/types."""
    out: list[str] = []
    seen: set[str] = set()
    for source in (subtitles, automatic_captions):
        if not source:
            continue
        for lang in source.keys():
            if not isinstance(lang, str):
                continue
            code = lang.strip()
            if not code or code in seen:
                continue
            seen.add(code)
            out.append(code)
    return tuple(out)


def _map_live_status(info: Mapping[str, Any]) -> LiveStatus:
    raw = info.get("live_status")
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"is_live", "live"}:
            return LiveStatus.LIVE
        if normalized in {"is_upcoming", "upcoming"}:
            return LiveStatus.UPCOMING
        if normalized in {"was_live", "post_live", "ended"}:
            return LiveStatus.ENDED
        if normalized in {"not_live", "none"}:
            return LiveStatus.NONE
    if info.get("is_live") is True:
        return LiveStatus.LIVE
    if info.get("was_live") is True:
        return LiveStatus.ENDED
    return LiveStatus.NONE


def _coerce_age_limit(
    info: Mapping[str, Any],
    *,
    video_id: str | None = None,
) -> int | None:
    """Parse optional age_limit safely; malformed values become INVALID_RESPONSE.

    Always attaches the request/response video identity when available so callers
    never receive an identity-less AppError for this external field.
    """
    age_raw = info.get("age_limit")
    if age_raw is None or age_raw == "":
        return None
    try:
        return int(age_raw)
    except (TypeError, ValueError):
        raise AdapterError(
            _app_error(
                ErrorCode.INVALID_RESPONSE,
                "yt-dlp info has invalid age_limit",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        ) from None


def _map_availability(
    info: Mapping[str, Any],
    *,
    video_id: str | None = None,
) -> Availability:
    # Validate age_limit whenever present so free-form payload cannot raise ValueError.
    age_limit = _coerce_age_limit(info, video_id=video_id)

    raw = info.get("availability")
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"public", "unlisted"}:
            return Availability.PUBLIC
        if value == "needs_auth":
            # V1 has no login/cookie path; treat as restricted, never public.
            return Availability.RESTRICTED
        if value == "private":
            return Availability.PRIVATE
        if value in {"premium", "subscriber_only", "premium_only"}:
            return Availability.RESTRICTED
        if value in {"unavailable"}:
            return Availability.UNAVAILABLE
    if age_limit is not None and age_limit >= 18 and not info.get("title"):
        return Availability.RESTRICTED
    return Availability.PUBLIC


def _map_published_at(info: Mapping[str, Any]) -> datetime | None:
    """Return a UTC datetime or None; never raise on malformed external fields."""
    try:
        ts = info.get("timestamp")
        if isinstance(ts, (int, float)) and ts > 0:
            return datetime.fromtimestamp(float(ts), tz=UTC)
        release = info.get("release_timestamp")
        if isinstance(release, (int, float)) and release > 0:
            return datetime.fromtimestamp(float(release), tz=UTC)
        upload_date = info.get("upload_date")
        if isinstance(upload_date, str) and len(upload_date) == 8 and upload_date.isdigit():
            year = int(upload_date[0:4])
            month = int(upload_date[4:6])
            day = int(upload_date[6:8])
            return datetime(year, month, day, tzinfo=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return None


def _map_info_dict_to_video_metadata(
    info: Mapping[str, Any],
    *,
    requested_video_id: str | None = None,
) -> VideoMetadata:
    """Private: map a yt-dlp info mapping to approved ``VideoMetadata``.

    All external field conversion failures become safe ``AdapterError`` payloads.
    When ``requested_video_id`` is set, response identity must match exactly.
    """
    safe_video_id = requested_video_id
    try:
        video_id = info.get("id") or info.get("display_id")
        if not isinstance(video_id, str) or not video_id.strip():
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info missing video id",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=safe_video_id,
                )
            )
        video_id = video_id.strip()
        if safe_video_id is None:
            safe_video_id = video_id

        title = info.get("title")
        if not isinstance(title, str) or not title.strip():
            availability = _map_availability(info, video_id=safe_video_id)
            if availability is Availability.PUBLIC:
                availability = Availability.UNAVAILABLE
            raise AdapterError(
                _app_error(
                    ErrorCode.CONTENT_UNAVAILABLE,
                    f"video content unavailable ({availability.value})",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=safe_video_id,
                )
            )
        title = title.strip()

        channel_id = info.get("channel_id") or info.get("uploader_id")
        if not isinstance(channel_id, str) or not channel_id.strip():
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info missing channel_id",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=safe_video_id,
                )
            )
        channel_id = channel_id.strip()

        channel_name = info.get("channel") or info.get("uploader") or info.get("channel_name")
        if not isinstance(channel_name, str) or not channel_name.strip():
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info missing channel name",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=safe_video_id,
                )
            )
        channel_name = channel_name.strip()

        description = info.get("description")
        if description is None:
            description = ""
        elif not isinstance(description, str):
            description = str(description)

        source_url = info.get("webpage_url") or info.get("original_url")
        if not isinstance(source_url, str) or not source_url.strip():
            source_url = _WATCH_URL.format(video_id=video_id)
        else:
            source_url = source_url.strip()

        published_at = _map_published_at(info)
        if published_at is None:
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info missing or invalid publish timestamp",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=safe_video_id,
                )
            )

        duration_raw = info.get("duration")
        if duration_raw is None:
            duration_seconds = 0
        else:
            try:
                duration_seconds = int(duration_raw)
            except (TypeError, ValueError):
                raise AdapterError(
                    _app_error(
                        ErrorCode.INVALID_RESPONSE,
                        "yt-dlp info has invalid duration",
                        retryable=False,
                        stage=ProcessingStage.METADATA,
                        video_id=safe_video_id,
                    )
                ) from None
            if duration_seconds < 0:
                raise AdapterError(
                    _app_error(
                        ErrorCode.INVALID_RESPONSE,
                        "yt-dlp info has negative duration",
                        retryable=False,
                        stage=ProcessingStage.METADATA,
                        video_id=safe_video_id,
                    )
                )

        default_language: str | None = None
        for key in ("language", "original_language"):
            val = info.get(key)
            if isinstance(val, str) and val.strip():
                default_language = val.strip()
                break

        subtitles = info.get("subtitles") if isinstance(info.get("subtitles"), Mapping) else None
        auto = (
            info.get("automatic_captions")
            if isinstance(info.get("automatic_captions"), Mapping)
            else None
        )
        available_languages = _summarize_available_languages(subtitles, auto)

        live_status = _map_live_status(info)
        availability = _map_availability(info, video_id=safe_video_id)

        metadata = VideoMetadata(
            video_id=video_id,
            channel_id=channel_id,
            channel_name=channel_name,
            title=title,
            description=description,
            source_url=source_url,
            published_at=published_at,
            duration_seconds=duration_seconds,
            default_language=default_language,
            available_languages=available_languages,
            live_status=live_status,
            availability=availability,
        )
    except AdapterError:
        raise
    except (TypeError, ValueError, OverflowError, OSError):
        raise AdapterError(
            _app_error(
                ErrorCode.INVALID_RESPONSE,
                "yt-dlp info payload is malformed",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=safe_video_id,
            )
        ) from None

    if requested_video_id is not None and metadata.video_id != requested_video_id:
        raise AdapterError(
            _app_error(
                ErrorCode.INVALID_RESPONSE,
                "yt-dlp info video id does not match request",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=requested_video_id,
            )
        )
    return metadata


def _default_ydl_factory(opts: dict[str, Any]) -> _YdlHandle:
    handle: _YdlHandle = yt_dlp.YoutubeDL(opts)
    return handle


# ---------------------------------------------------------------------------
# Public Adapter (cross-module contract surface)
# ---------------------------------------------------------------------------


class YtDlpMetadataProvider:
    """MetadataProvider implementation using yt-dlp Python API only.

    Public construction is domain configuration only (``timeout_seconds``).
    Free-form yt-dlp option/info dicts, factories, clocks, and option sinks are
    private implementation details and must not appear on the public surface.
    """

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be positive"
            raise ValueError(msg)
        self._timeout_seconds = timeout_seconds
        self._ydl_factory: _YdlFactory = _default_ydl_factory
        self._clock: _Clock = _utcnow
        # Private sink used only when tests call ``_bind_test_hooks``.
        self._opts_sink: MutableSequence[object] | None = None
        self.last_call: ProviderCallMetadata | None = None

    def fetch(self, video_id: str) -> VideoMetadata:
        if not isinstance(video_id, str) or not _VIDEO_ID_RE.fullmatch(video_id):
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "invalid video_id for metadata fetch",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id if isinstance(video_id, str) else None,
                )
            )
        started = self._clock()
        opts = _build_ydl_opts(socket_timeout=self._timeout_seconds)
        if self._opts_sink is not None:
            # Evidence copy stays inside the private sink; not a public attribute.
            self._opts_sink.append(dict(opts))
        url = _WATCH_URL.format(video_id=video_id)
        try:
            ydl = self._ydl_factory(opts)
            # extract_info with download=False is belt-and-suspenders with skip_download.
            info = ydl.extract_info(url, download=False)
        except AdapterError:
            raise
        except GeoRestrictedError:
            finished = self._clock()
            self.last_call = _call_meta(started, finished, diagnostics_code="geo_restricted")
            raise AdapterError(
                _app_error(
                    ErrorCode.CONTENT_UNAVAILABLE,
                    "video content unavailable (restricted)",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            ) from None
        except (DownloadError, ExtractorError) as exc:
            finished = self._clock()
            self.last_call = _call_meta(started, finished, diagnostics_code="extract_error")
            raise _map_ytdlp_exception(exc, video_id=video_id) from None
        except TimeoutError:
            finished = self._clock()
            self.last_call = _call_meta(started, finished, diagnostics_code="timeout")
            raise AdapterError(
                _app_error(
                    ErrorCode.TRANSIENT_NETWORK,
                    "yt-dlp metadata request timed out",
                    retryable=True,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            ) from None
        except OSError as exc:
            finished = self._clock()
            self.last_call = _call_meta(started, finished, diagnostics_code="os_error")
            msg = str(exc).lower()
            if "timed out" in msg or "timeout" in msg:
                code = ErrorCode.TRANSIENT_NETWORK
                text = "yt-dlp metadata request timed out"
                retryable = True
            else:
                code = ErrorCode.PROVIDER_UNAVAILABLE
                text = "yt-dlp metadata provider unavailable"
                retryable = True
            raise AdapterError(
                _app_error(
                    code,
                    text,
                    retryable=retryable,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            ) from None
        except Exception:  # noqa: BLE001 — map unknown provider failures safely
            finished = self._clock()
            self.last_call = _call_meta(started, finished, diagnostics_code="unknown_error")
            raise AdapterError(
                _app_error(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    "yt-dlp metadata provider failed",
                    retryable=True,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            ) from None

        finished = self._clock()
        self.last_call = _call_meta(started, finished)

        if not isinstance(info, Mapping):
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp returned a non-mapping info payload",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            )
        # Drop free-form dict at the boundary immediately; keep request identity.
        try:
            return _map_info_dict_to_video_metadata(info, requested_video_id=video_id)
        except AdapterError:
            raise
        except (TypeError, ValueError, OverflowError, OSError):
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info payload is malformed",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            ) from None


def _call_meta(
    started: datetime,
    finished: datetime,
    *,
    diagnostics_code: str | None = None,
) -> ProviderCallMetadata:
    version: str | None
    try:
        version = getattr(yt_dlp.version, "__version__", None)
        if version is not None:
            version = str(version)
    except Exception:  # noqa: BLE001
        version = None
    diagnostics: tuple[DiagnosticEntry, ...] = ()
    if diagnostics_code is not None:
        diagnostics = (
            DiagnosticEntry(
                code=diagnostics_code,
                message=_redact_message(diagnostics_code.replace("_", " ")),
            ),
        )
    return ProviderCallMetadata(
        provider=_PROVIDER_NAME,
        started_at=_ensure_aware(started),
        finished_at=_ensure_aware(finished),
        provider_version=version,
        diagnostics=diagnostics,
    )


def _extract_http_status(message_lower: str) -> int | None:
    """Extract HTTP status before broad free-text matching."""
    match = re.search(r"\bhttp(?:\s+error)?\s+(\d{3})\b", message_lower)
    if match:
        return int(match.group(1))
    match = re.search(r"\b([45]\d{2})\b", message_lower)
    if match:
        return int(match.group(1))
    return None


def _map_ytdlp_exception(exc: BaseException, *, video_id: str) -> AdapterError:
    # Redact for safety; classification uses a lower-cased copy only.
    text = _redact_message(str(exc) or exc.__class__.__name__)
    lower = text.lower()

    # Fixed HTTP classification order (before broad text matches).
    status = _extract_http_status(lower)
    if status == 429 or "rate limit" in lower or "too many requests" in lower:
        return AdapterError(
            _app_error(
                ErrorCode.RATE_LIMITED,
                "yt-dlp metadata rate limited",
                retryable=True,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )
    if status == 404:
        return AdapterError(
            _app_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                "video content unavailable (unavailable)",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )
    if status in {401, 403}:
        return AdapterError(
            _app_error(
                ErrorCode.PERMISSION_DENIED,
                "yt-dlp metadata access denied",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )
    if status is not None and 500 <= status <= 599:
        return AdapterError(
            _app_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "yt-dlp metadata provider unavailable",
                retryable=True,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    if "timed out" in lower or "timeout" in lower or "temporarily" in lower:
        return AdapterError(
            _app_error(
                ErrorCode.TRANSIENT_NETWORK,
                "yt-dlp metadata request timed out",
                retryable=True,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    if any(marker in lower for marker in _NETWORK_ERROR_MARKERS):
        return AdapterError(
            _app_error(
                ErrorCode.TRANSIENT_NETWORK,
                "yt-dlp metadata network request failed",
                retryable=True,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    private = "private video" in lower or ("private" in lower and "video" in lower)
    if private:
        return AdapterError(
            _app_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                "video content unavailable (private)",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    if any(marker in lower for marker in _AUTH_GATE_MARKERS):
        return AdapterError(
            _app_error(
                ErrorCode.PERMISSION_DENIED,
                "youtube authentication required (anonymous verification gate)",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    deleted = "removed" in lower or "deleted" in lower or "no longer available" in lower
    restricted = (
        "not available in your country" in lower
        or "geo" in lower
        or "region" in lower
        or "who has blocked it" in lower
        or "confirm your age" in lower
        or "members-only" in lower
        or "join this channel" in lower
    )
    unavailable = (
        "video unavailable" in lower
        or "is unavailable" in lower
        or "unavailable" in lower
        or "live event will begin" in lower
        or "premieres in" in lower
        or "live stream recording is not available" in lower
        or "video is not available" in lower
    )
    if deleted:
        return AdapterError(
            _app_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                "video content unavailable (deleted)",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )
    if restricted:
        return AdapterError(
            _app_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                "video content unavailable (restricted)",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )
    if unavailable:
        return AdapterError(
            _app_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                "video content unavailable (unavailable)",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    if "unable to extract" in lower or "json" in lower or "parse" in lower:
        return AdapterError(
            _app_error(
                ErrorCode.INVALID_RESPONSE,
                "yt-dlp metadata parse error",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    if "http error" in lower:
        return AdapterError(
            _app_error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "yt-dlp metadata provider unavailable",
                retryable=True,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    return AdapterError(
        _app_error(
            ErrorCode.PROVIDER_UNAVAILABLE,
            "yt-dlp metadata provider failed",
            retryable=True,
            stage=ProcessingStage.METADATA,
            video_id=video_id,
        )
    )


def _bind_test_hooks(
    provider: YtDlpMetadataProvider,
    *,
    ydl_factory: _YdlFactory | None = None,
    clock: _Clock | None = None,
    opts_sink: MutableSequence[object] | None = None,
) -> None:
    """Private, test-scoped wiring for offline fakes (not a public constructor).

    Cross-module product code must not call this. Unit/integration tests may use
    it (or assign the same private attributes) after constructing the provider.
    """
    if ydl_factory is not None:
        provider._ydl_factory = ydl_factory
    if clock is not None:
        provider._clock = clock
    if opts_sink is not None:
        provider._opts_sink = opts_sink


__all__ = [
    "YtDlpMetadataProvider",
]
