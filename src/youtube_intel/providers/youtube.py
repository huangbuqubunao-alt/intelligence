"""YouTube metadata Adapter via official yt-dlp Python API (no shell).

External free-form info dicts exist only inside this module and are mapped to
frozen ``VideoMetadata``. Does not download media/subtitles, load cookies,
enable remote components, or invoke ffmpeg.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Final

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

# Options equivalent to single-video, skip_download, noplaylist, quiet, no media writes.
# Captured in tests to prove no cookie/login/remote-components/ffmpeg usage.
SAFE_YDL_OPTS: Final[dict[str, Any]] = {
    "skip_download": True,
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
    # Do not set cookiefile / cookiesfrombrowser / username / password / netrc_location.
    # Do not set remote_components / allow_remote / ffmpeg_location / paths that download media.
}

Clock = Callable[[], datetime]
YdlFactory = Callable[[dict[str, Any]], Any]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def build_ydl_opts(*, socket_timeout: float | None = None) -> dict[str, Any]:
    """Return a fresh opts dict for a single metadata extract call."""
    opts = dict(SAFE_YDL_OPTS)
    if socket_timeout is not None:
        opts["socket_timeout"] = socket_timeout
    return opts


def summarize_available_languages(
    subtitles: Mapping[str, Any] | None,
    automatic_captions: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Stable language summary: manual order first, then new auto languages.

    Never exposes track URLs, formats, or manual/auto type flags.
    """
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


def map_live_status(info: Mapping[str, Any]) -> LiveStatus:
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


def map_availability(info: Mapping[str, Any]) -> Availability:
    raw = info.get("availability")
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"public", "unlisted", "needs_auth"}:
            # needs_auth with full info still means we got metadata; treat carefully.
            if value == "needs_auth" and not info.get("title"):
                return Availability.PRIVATE
            if value in {"public", "unlisted"}:
                return Availability.PUBLIC
        if value == "private":
            return Availability.PRIVATE
        if value in {"premium", "subscriber_only", "premium_only"}:
            return Availability.RESTRICTED
        if value in {"unavailable"}:
            return Availability.UNAVAILABLE
    # Geo / age / login walls sometimes still produce partial dicts.
    if info.get("age_limit") and int(info.get("age_limit") or 0) >= 18 and not info.get("title"):
        return Availability.RESTRICTED
    return Availability.PUBLIC


def map_published_at(info: Mapping[str, Any]) -> datetime | None:
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
    return None


def map_info_dict_to_video_metadata(info: Mapping[str, Any]) -> VideoMetadata:
    """Map a yt-dlp info dict to approved ``VideoMetadata`` or raise AdapterError."""
    video_id = info.get("id") or info.get("display_id")
    if not isinstance(video_id, str) or not video_id.strip():
        raise AdapterError(
            _app_error(
                ErrorCode.INVALID_RESPONSE,
                "yt-dlp info missing video id",
                retryable=False,
                stage=ProcessingStage.METADATA,
            )
        )
    video_id = video_id.strip()

    title = info.get("title")
    if not isinstance(title, str) or not title.strip():
        # Incomplete metadata for inaccessible content — do not forge empty strings.
        availability = map_availability(info)
        if availability is Availability.PUBLIC:
            availability = Availability.UNAVAILABLE
        raise AdapterError(
            _app_error(
                ErrorCode.CONTENT_UNAVAILABLE,
                f"video content unavailable ({availability.value})",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
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
                video_id=video_id,
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
                video_id=video_id,
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

    published_at = map_published_at(info)
    if published_at is None:
        raise AdapterError(
            _app_error(
                ErrorCode.INVALID_RESPONSE,
                "yt-dlp info missing publish timestamp",
                retryable=False,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    duration_raw = info.get("duration")
    if duration_raw is None:
        duration_seconds = 0
    else:
        try:
            duration_seconds = int(duration_raw)
        except (TypeError, ValueError) as exc:
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info has invalid duration",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
                )
            ) from exc
        if duration_seconds < 0:
            raise AdapterError(
                _app_error(
                    ErrorCode.INVALID_RESPONSE,
                    "yt-dlp info has negative duration",
                    retryable=False,
                    stage=ProcessingStage.METADATA,
                    video_id=video_id,
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
    available_languages = summarize_available_languages(subtitles, auto)

    live_status = map_live_status(info)
    availability = map_availability(info)

    return VideoMetadata(
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


class YtDlpMetadataProvider:
    """MetadataProvider implementation using yt-dlp Python API only."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        ydl_factory: YdlFactory | None = None,
        clock: Clock | None = None,
        last_opts: list[dict[str, Any]] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be positive"
            raise ValueError(msg)
        self._timeout_seconds = timeout_seconds
        self._ydl_factory = ydl_factory or _default_ydl_factory
        self._clock = clock or _utcnow
        self.last_opts: list[dict[str, Any]] = last_opts if last_opts is not None else []
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
        opts = build_ydl_opts(socket_timeout=self._timeout_seconds)
        self.last_opts.append(dict(opts))
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
        # Drop free-form dict at the boundary immediately.
        return map_info_dict_to_video_metadata(info)


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


def _map_ytdlp_exception(exc: BaseException, *, video_id: str) -> AdapterError:
    text = _redact_message(str(exc) or exc.__class__.__name__)
    lower = text.lower()

    # Rate limit
    if "429" in lower or "rate limit" in lower or "too many requests" in lower:
        return AdapterError(
            _app_error(
                ErrorCode.RATE_LIMITED,
                "yt-dlp metadata rate limited",
                retryable=True,
                stage=ProcessingStage.METADATA,
                video_id=video_id,
            )
        )

    # Timeouts / transient network
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

    # Content unavailability classes
    private = "private video" in lower or "private" in lower and "video" in lower
    deleted = "removed" in lower or "deleted" in lower or "no longer available" in lower
    restricted = (
        "not available in your country" in lower
        or "geo" in lower
        or "region" in lower
        or "who has blocked it" in lower
        or "confirm your age" in lower
    )
    unavailable = (
        "video unavailable" in lower
        or "is unavailable" in lower
        or "unavailable" in lower
        or "sign in to confirm" in lower
    )
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

    # Parse / extract failures
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

    # HTTP 5xx / generic provider issues
    if re.search(r"\b5\d\d\b", lower) or "http error" in lower:
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


def _default_ydl_factory(opts: dict[str, Any]) -> Any:
    return yt_dlp.YoutubeDL(opts)


__all__ = [
    "SAFE_YDL_OPTS",
    "YtDlpMetadataProvider",
    "build_ydl_opts",
    "map_availability",
    "map_info_dict_to_video_metadata",
    "map_live_status",
    "summarize_available_languages",
]
