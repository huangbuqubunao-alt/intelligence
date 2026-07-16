"""Offline-testable yt-dlp subtitle Adapter with no media or auth side effects."""

from __future__ import annotations

import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, MutableSequence
from datetime import UTC, datetime
from http.client import HTTPMessage
from typing import IO, Any, Final, Protocol
from urllib.parse import urlsplit

import yt_dlp  # type: ignore[import-untyped]
from yt_dlp.utils import DownloadError, ExtractorError  # type: ignore[import-untyped]

from youtube_intel.domain import (
    AppError,
    DiagnosticEntry,
    ErrorCode,
    ProcessingStage,
    ProviderCallMetadata,
    SubtitleFormat,
    TranscriptSourceType,
)
from youtube_intel.transcripts import (
    InvalidSubtitleCandidate,
    InvalidSubtitleReason,
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
    TranscriptError,
)

_PROVIDER_NAME: Final = "yt-dlp"
_WATCH_URL: Final = "https://www.youtube.com/watch?v={video_id}"
_VIDEO_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
_SAFE_HOST_RE: Final = re.compile(
    r"^(?:[A-Za-z0-9-]+\.)*(?:youtube\.com|googlevideo\.com)$",
    re.IGNORECASE,
)
_USER_AGENT: Final = "youtube-intel/0.1 (+local subtitle fetch; no media)"
_READ_CHUNK_BYTES: Final = 64 * 1024

_SAFE_YDL_OPTS: Final[dict[str, Any]] = {
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
    "usenetrc": False,
    "extract_flat": False,
}


class _YdlHandle(Protocol):
    def extract_info(self, url: str, download: bool = True) -> object: ...


_YdlFactory = Callable[[dict[str, Any]], _YdlHandle]
_Opener = Callable[[urllib.request.Request, float], object]
_Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _provider_version() -> str:
    try:
        version = getattr(yt_dlp.version, "__version__", None)
    except Exception:  # noqa: BLE001
        version = None
    return str(version) if version is not None else "unknown"


def _safe_message(value: str) -> str:
    lowered = value.casefold()
    if "cookie" in lowered or "authorization" in lowered or "token" in lowered:
        return "subtitle provider error"
    return " ".join(value.split())[:300] or "subtitle provider error"


def _error(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool,
    video_id: str | None,
    retry_after_seconds: float | None = None,
) -> TranscriptError:
    return TranscriptError(
        AppError(
            code=code,
            message=_safe_message(message),
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
            video_id=video_id,
            stage=ProcessingStage.TRANSCRIPT,
        )
    )


def _call(
    started: datetime,
    finished: datetime,
    *,
    diagnostic: str | None = None,
) -> ProviderCallMetadata:
    diagnostics: tuple[DiagnosticEntry, ...] = ()
    if diagnostic is not None:
        diagnostics = (
            DiagnosticEntry(
                code=diagnostic,
                message=diagnostic.replace("_", " "),
            ),
        )
    return ProviderCallMetadata(
        provider=_PROVIDER_NAME,
        provider_version=_provider_version(),
        started_at=started.astimezone(UTC),
        finished_at=finished.astimezone(UTC),
        diagnostics=diagnostics,
    )


def _extract_status(message: str) -> int | None:
    match = re.search(r"\b(?:http(?:\s+error)?\s+)?([45]\d{2})\b", message.casefold())
    return None if match is None else int(match.group(1))


def _map_directory_error(error: BaseException, *, video_id: str) -> TranscriptError:
    message = str(error)
    lowered = message.casefold()
    status = _extract_status(message)
    if status == 429 or "rate limit" in lowered or "too many requests" in lowered:
        return _error(
            ErrorCode.RATE_LIMITED,
            "subtitle track directory rate limited",
            retryable=True,
            video_id=video_id,
        )
    if status in {401, 403}:
        return _error(
            ErrorCode.PERMISSION_DENIED,
            "subtitle track directory access denied",
            retryable=False,
            video_id=video_id,
        )
    if status == 404:
        return _error(
            ErrorCode.CONTENT_UNAVAILABLE,
            "video content unavailable for subtitles",
            retryable=False,
            video_id=video_id,
        )
    if status is not None and 500 <= status <= 599:
        return _error(
            ErrorCode.PROVIDER_UNAVAILABLE,
            "subtitle track directory provider unavailable",
            retryable=True,
            video_id=video_id,
        )
    if "timeout" in lowered or "timed out" in lowered:
        return _error(
            ErrorCode.TRANSIENT_NETWORK,
            "subtitle track directory request timed out",
            retryable=True,
            video_id=video_id,
        )
    if any(
        marker in lowered
        for marker in (
            "private video",
            "removed",
            "deleted",
            "video unavailable",
            "not available in your country",
            "geo",
            "region",
            "sign in to confirm",
        )
    ):
        return _error(
            ErrorCode.CONTENT_UNAVAILABLE,
            "video content unavailable for subtitles",
            retryable=False,
            video_id=video_id,
        )
    if "extract" in lowered or "parse" in lowered or "json" in lowered:
        return _error(
            ErrorCode.INVALID_RESPONSE,
            "subtitle track directory payload is invalid",
            retryable=False,
            video_id=video_id,
        )
    return _error(
        ErrorCode.PROVIDER_UNAVAILABLE,
        "subtitle track directory provider failed",
        retryable=True,
        video_id=video_id,
    )


def _validate_track_url(value: str, *, video_id: str | None) -> None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        parsed = None
        port = None
    if (
        parsed is None
        or parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or bool(parsed.fragment)
        or _SAFE_HOST_RE.fullmatch(parsed.hostname) is None
    ):
        raise _error(
            ErrorCode.INVALID_RESPONSE,
            "subtitle track URL is unsafe",
            retryable=False,
            video_id=video_id,
        )


def _format_from_extension(value: str) -> SubtitleFormat | None:
    normalized = value.strip().casefold()
    for source_format in SubtitleFormat:
        if source_format.value == normalized:
            return source_format
    return None


def _track_name(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, Mapping):
        simple = value.get("simpleText")
        if isinstance(simple, str):
            return " ".join(simple.split())
        runs = value.get("runs")
        if isinstance(runs, list):
            pieces: list[str] = []
            for run in runs:
                if isinstance(run, Mapping) and isinstance(run.get("text"), str):
                    pieces.append(str(run["text"]))
            return " ".join("".join(pieces).split())
    return ""


def _map_directory(
    payload: Any,
    *,
    source_type: TranscriptSourceType,
    start_position: int,
    video_id: str,
) -> tuple[list[SubtitleTrack], int]:
    if payload is None:
        return [], start_position
    if not isinstance(payload, Mapping):
        raise _error(
            ErrorCode.INVALID_RESPONSE,
            "subtitle track directory payload is malformed",
            retryable=False,
            video_id=video_id,
        )
    tracks: list[SubtitleTrack] = []
    position = start_position
    for raw_language, raw_entries in payload.items():
        if (
            not isinstance(raw_language, str)
            or not raw_language
            or raw_language.strip() != raw_language
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", raw_language)
            is None
            or not isinstance(raw_entries, list)
        ):
            raise _error(
                ErrorCode.INVALID_RESPONSE,
                "subtitle track directory payload is malformed",
                retryable=False,
                video_id=video_id,
            )
        for raw_entry in raw_entries:
            current_position = position
            position += 1
            if not isinstance(raw_entry, Mapping):
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "subtitle track payload is malformed",
                    retryable=False,
                    video_id=video_id,
                )
            raw_extension = raw_entry.get("ext")
            if not isinstance(raw_extension, str):
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "subtitle track format is missing",
                    retryable=False,
                    video_id=video_id,
                )
            source_format = _format_from_extension(raw_extension)
            if source_format is None:
                continue
            raw_url = raw_entry.get("url")
            if not isinstance(raw_url, str) or not raw_url:
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "subtitle track URL is missing",
                    retryable=False,
                    video_id=video_id,
                )
            _validate_track_url(raw_url, video_id=video_id)
            tracks.append(
                SubtitleTrack(
                    source_type=source_type,
                    language=raw_language,
                    source_format=source_format,
                    name=_track_name(raw_entry.get("name")),
                    url=raw_url,
                    provider_position=current_position,
                )
            )
    return tracks, position


def _parse_retry_after(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        seconds = float(raw.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def _default_ydl_factory(opts: dict[str, Any]) -> _YdlHandle:
    handle: _YdlHandle = yt_dlp.YoutubeDL(opts)
    return handle


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: IO[bytes],
        code: int,
        message: str,
        headers: HTTPMessage,
        new_url: str,
    ) -> urllib.request.Request | None:
        _validate_track_url(new_url, video_id=None)
        redirected = super().redirect_request(
            request,
            file_pointer,
            code,
            message,
            headers,
            new_url,
        )
        return redirected


_SAFE_URL_OPENER: Final = urllib.request.build_opener(_SafeRedirectHandler())


def _default_open(request: urllib.request.Request, timeout: float) -> object:
    return _SAFE_URL_OPENER.open(request, timeout=timeout)  # noqa: S310


class YtDlpSubtitleAdapter:
    """Enumerate track metadata and read only the selected subtitle body."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        max_response_bytes: int = 5_000_000,
    ) -> None:
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be positive"
            raise ValueError(msg)
        if max_response_bytes <= 0 or max_response_bytes > 5_000_000:
            msg = "max_response_bytes must be within 1..5_000_000"
            raise ValueError(msg)
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._ydl_factory: _YdlFactory = _default_ydl_factory
        self._opener: _Opener = _default_open
        self._clock: _Clock = _utcnow
        self._opts_sink: MutableSequence[object] | None = None
        self.last_call: ProviderCallMetadata | None = None

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    @property
    def provider_version(self) -> str:
        return _provider_version()

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        if _VIDEO_ID_RE.fullmatch(video_id) is None:
            raise _error(
                ErrorCode.INVALID_RESPONSE,
                "video_id is invalid for subtitle enumeration",
                retryable=False,
                video_id=None,
            )
        started = self._clock()
        opts = dict(_SAFE_YDL_OPTS)
        opts["socket_timeout"] = self._timeout_seconds
        if self._opts_sink is not None:
            self._opts_sink.append(dict(opts))
        try:
            payload = self._ydl_factory(opts).extract_info(
                _WATCH_URL.format(video_id=video_id),
                download=False,
            )
        except TranscriptError:
            raise
        except (DownloadError, ExtractorError) as exc:
            self.last_call = _call(started, self._clock(), diagnostic="directory_error")
            raise _map_directory_error(exc, video_id=video_id) from None
        except (TimeoutError, socket.timeout):
            self.last_call = _call(started, self._clock(), diagnostic="directory_timeout")
            raise _error(
                ErrorCode.TRANSIENT_NETWORK,
                "subtitle track directory request timed out",
                retryable=True,
                video_id=video_id,
            ) from None
        except OSError as exc:
            self.last_call = _call(started, self._clock(), diagnostic="directory_os_error")
            raise _map_directory_error(exc, video_id=video_id) from None
        except Exception:
            self.last_call = _call(started, self._clock(), diagnostic="directory_error")
            raise _error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "subtitle track directory provider failed",
                retryable=True,
                video_id=video_id,
            ) from None

        finished = self._clock()
        self.last_call = _call(started, finished)
        if not isinstance(payload, Mapping) or payload.get("id") != video_id:
            raise _error(
                ErrorCode.INVALID_RESPONSE,
                "subtitle track directory identity is invalid",
                retryable=False,
                video_id=video_id,
            )
        manual, position = _map_directory(
            payload.get("subtitles"),
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            start_position=0,
            video_id=video_id,
        )
        automatic, _ = _map_directory(
            payload.get("automatic_captions"),
            source_type=TranscriptSourceType.AUTO_SUBTITLE,
            start_position=position,
            video_id=video_id,
        )
        return SubtitleTrackListing(
            tracks=tuple((*manual, *automatic)),
            call=self.last_call,
        )

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        _validate_track_url(track.url, video_id=None)
        started = self._clock()
        request = urllib.request.Request(
            track.url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/json,text/vtt,text/plain;q=0.9,*/*;q=0.1",
                "Accept-Encoding": "identity",
            },
        )
        try:
            response = self._opener(request, self._timeout_seconds)
        except urllib.error.HTTPError as exc:
            self.last_call = _call(started, self._clock(), diagnostic="body_http_error")
            retry_after = _parse_retry_after(
                None if exc.headers is None else exc.headers.get("Retry-After")
            )
            mapped: TranscriptError
            if exc.code in {403, 404}:
                mapped = _error(
                    ErrorCode.TRANSIENT_NETWORK,
                    "selected subtitle URL expired",
                    retryable=True,
                    video_id=None,
                )
            elif exc.code == 429:
                mapped = _error(
                    ErrorCode.RATE_LIMITED,
                    "selected subtitle body rate limited",
                    retryable=True,
                    retry_after_seconds=retry_after,
                    video_id=None,
                )
            elif 500 <= exc.code <= 599:
                mapped = _error(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    "selected subtitle body provider unavailable",
                    retryable=True,
                    video_id=None,
                )
            elif exc.code in {401}:
                mapped = _error(
                    ErrorCode.PERMISSION_DENIED,
                    "selected subtitle body access denied",
                    retryable=False,
                    video_id=None,
                )
            else:
                mapped = _error(
                    ErrorCode.INVALID_RESPONSE,
                    "selected subtitle body returned an invalid HTTP response",
                    retryable=False,
                    video_id=None,
                )
            try:
                exc.close()
            except Exception:  # noqa: BLE001
                pass
            raise mapped from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            self.last_call = _call(started, self._clock(), diagnostic="body_network_error")
            raise _error(
                ErrorCode.TRANSIENT_NETWORK,
                "selected subtitle body request failed",
                retryable=True,
                video_id=None,
            ) from None

        try:
            final_url = None
            geturl = getattr(response, "geturl", None)
            if callable(geturl):
                final_url = geturl()
            if final_url is not None:
                if not isinstance(final_url, str):
                    raise _error(
                        ErrorCode.INVALID_RESPONSE,
                        "selected subtitle response URL is invalid",
                        retryable=False,
                        video_id=None,
                    )
                _validate_track_url(final_url, video_id=None)
            read = getattr(response, "read", None)
            if not callable(read):
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "selected subtitle response is unreadable",
                    retryable=False,
                    video_id=None,
                )
            headers_value = getattr(response, "headers", None)
            headers = headers_value if isinstance(headers_value, Mapping) else None
            content_length: int | None = None
            if headers is not None:
                raw_length = headers.get("Content-Length") or headers.get(
                    "content-length"
                )
                if raw_length is not None:
                    try:
                        content_length = int(str(raw_length))
                    except ValueError:
                        raise _error(
                            ErrorCode.INVALID_RESPONSE,
                            "selected subtitle content length is invalid",
                            retryable=False,
                            video_id=None,
                        ) from None
                    if content_length < 0:
                        raise _error(
                            ErrorCode.INVALID_RESPONSE,
                            "selected subtitle content length is invalid",
                            retryable=False,
                            video_id=None,
                        )
                    if content_length > self._max_response_bytes:
                        raise InvalidSubtitleCandidate(
                            InvalidSubtitleReason.RESOURCE_LIMIT
                        )

            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = read(_READ_CHUNK_BYTES)
                if not isinstance(chunk, bytes):
                    raise _error(
                        ErrorCode.INVALID_RESPONSE,
                        "selected subtitle response returned invalid bytes",
                        retryable=False,
                        video_id=None,
                    )
                if not chunk:
                    break
                total += len(chunk)
                if total > self._max_response_bytes:
                    raise InvalidSubtitleCandidate(
                        InvalidSubtitleReason.RESOURCE_LIMIT
                    )
                chunks.append(chunk)
            if content_length is not None and total != content_length:
                raise _error(
                    ErrorCode.TRANSIENT_NETWORK,
                    "selected subtitle body ended before the declared length",
                    retryable=True,
                    video_id=None,
                )
            finished = self._clock()
            self.last_call = _call(started, finished)
            return SubtitleReadResult(body=b"".join(chunks), call=self.last_call)
        except TranscriptError:
            raise
        except InvalidSubtitleCandidate:
            raise
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            self.last_call = _call(started, self._clock(), diagnostic="body_network_error")
            raise _error(
                ErrorCode.TRANSIENT_NETWORK,
                "selected subtitle body request failed",
                retryable=True,
                video_id=None,
            ) from None
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass


def _bind_test_hooks(
    adapter: YtDlpSubtitleAdapter,
    *,
    ydl_factory: _YdlFactory | None = None,
    opener: _Opener | None = None,
    clock: _Clock | None = None,
    opts_sink: MutableSequence[object] | None = None,
) -> None:
    """Private offline-test wiring; not part of the product constructor."""
    if ydl_factory is not None:
        adapter._ydl_factory = ydl_factory
    if opener is not None:
        adapter._opener = opener
    if clock is not None:
        adapter._clock = clock
    if opts_sink is not None:
        adapter._opts_sink = opts_sink


__all__ = ["YtDlpSubtitleAdapter"]
