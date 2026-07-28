"""Offline-testable yt-dlp subtitle Adapter with no media or auth side effects."""

from __future__ import annotations

import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPMessage
from io import StringIO
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
_MAX_TRACK_COUNT: Final = 512
_MAX_TRACK_NAME_CODE_POINTS: Final = 1_000
_MAX_LANGUAGE_CODE_POINTS: Final = 128
_MAX_EXTENSION_CODE_POINTS: Final = 32
_MAX_TRACK_URL_CODE_POINTS: Final = 8_192
DIRECTORY_DIAGNOSTIC_CODES: Final[frozenset[str]] = frozenset(
    {
        "directory_shape_missing",
        "directory_shape_not_object",
        "directory_shape_not_list",
        "directory_shape_empty_list",
        "directory_shape_unsupported_entry",
        "directory_extractor_directory_error",
        "directory_shape_unknown",
    }
)
DIRECTORY_ORIGIN_CODES: Final[frozenset[str]] = frozenset(
    {
        "directory_origin_extractor",
        "directory_origin_decode",
        "directory_origin_mapping",
        "directory_origin_unknown",
    }
)
DIRECTORY_FINGERPRINT_CODES: Final[frozenset[str]] = frozenset(
    {
        "directory_fingerprint_top_level_not_mapping",
        "directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
        "directory_fingerprint_language_bucket_missing_or_not_sequence",
        "directory_fingerprint_track_entry_not_mapping",
        "directory_fingerprint_required_field_missing",
        "directory_fingerprint_unknown",
    }
)
_DIRECTORY_UNKNOWN_DIAGNOSTIC: Final = "directory_shape_unknown"

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


class _DirectoryInvalidResponse(TranscriptError):
    def __init__(
        self,
        error: AppError,
        *,
        diagnostic: str,
        origin: str | None = None,
        fingerprint: str | None = None,
    ) -> None:
        self.diagnostic = diagnostic
        self.directory_origin = origin
        self.directory_fingerprint = fingerprint
        super().__init__(error)


def _directory_error(
    diagnostic: str,
    message: str,
    *,
    video_id: str,
    origin: str = "directory_origin_mapping",
    fingerprint: str = "directory_fingerprint_unknown",
) -> _DirectoryInvalidResponse:
    return _DirectoryInvalidResponse(
        _error(
            ErrorCode.INVALID_RESPONSE,
            message,
            retryable=False,
            video_id=video_id,
        ).error,
        diagnostic=diagnostic,
        origin=origin,
        fingerprint=fingerprint,
    )


def _safe_boundary_error(
    error: AppError,
    *,
    subject: str,
    video_id: str | None,
) -> TranscriptError:
    messages = {
        ErrorCode.CONFIG_INVALID: f"{subject} configuration is invalid",
        ErrorCode.PERMISSION_DENIED: f"{subject} access denied",
        ErrorCode.CONTENT_UNAVAILABLE: f"{subject} content unavailable",
        ErrorCode.RATE_LIMITED: f"{subject} rate limited",
        ErrorCode.TRANSIENT_NETWORK: f"{subject} request failed",
        ErrorCode.PROVIDER_UNAVAILABLE: f"{subject} provider unavailable",
        ErrorCode.INVALID_RESPONSE: f"{subject} response is invalid",
        ErrorCode.LOCAL_RESOURCE: f"{subject} local resource failed",
    }
    return _error(
        error.code,
        messages[error.code],
        retryable=error.retryable,
        retry_after_seconds=error.retry_after_seconds,
        video_id=video_id,
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
    if len(value) > _MAX_TRACK_URL_CODE_POINTS:
        raise _error(
            ErrorCode.INVALID_RESPONSE,
            "subtitle track URL is invalid",
            retryable=False,
            video_id=video_id,
        )
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


def _track_name(value: Any, *, video_id: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        if len(value) > _MAX_TRACK_NAME_CODE_POINTS:
            raise _error(
                ErrorCode.INVALID_RESPONSE,
                "subtitle track name is invalid",
                retryable=False,
                video_id=video_id,
            )
        return " ".join(value.split())
    if isinstance(value, Mapping):
        simple = value.get("simpleText")
        if isinstance(simple, str):
            if len(simple) > _MAX_TRACK_NAME_CODE_POINTS:
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "subtitle track name is invalid",
                    retryable=False,
                    video_id=video_id,
                )
            return " ".join(simple.split())
        runs = value.get("runs")
        if isinstance(runs, Sequence) and not isinstance(
            runs,
            (str, bytes, bytearray),
        ):
            joined = StringIO()
            code_point_count = 0
            iteration_failed = False
            try:
                for run_count, run in enumerate(runs, start=1):
                    if run_count > _MAX_TRACK_NAME_CODE_POINTS:
                        raise _error(
                            ErrorCode.INVALID_RESPONSE,
                            "subtitle track name is invalid",
                            retryable=False,
                            video_id=video_id,
                        )
                    if not isinstance(run, Mapping):
                        raise _error(
                            ErrorCode.INVALID_RESPONSE,
                            "subtitle track name is invalid",
                            retryable=False,
                            video_id=video_id,
                        )
                    text = run.get("text")
                    if not isinstance(text, str):
                        raise _error(
                            ErrorCode.INVALID_RESPONSE,
                            "subtitle track name is invalid",
                            retryable=False,
                            video_id=video_id,
                        )
                    code_point_count += len(text)
                    if code_point_count > _MAX_TRACK_NAME_CODE_POINTS:
                        raise _error(
                            ErrorCode.INVALID_RESPONSE,
                            "subtitle track name is invalid",
                            retryable=False,
                            video_id=video_id,
                        )
                    joined.write(text)
            except TranscriptError:
                raise
            except Exception:
                iteration_failed = True
            if iteration_failed:
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "subtitle track name is invalid",
                    retryable=False,
                    video_id=video_id,
                )
            return " ".join(joined.getvalue().split())
    raise _error(
        ErrorCode.INVALID_RESPONSE,
        "subtitle track name is invalid",
        retryable=False,
        video_id=video_id,
    )


@dataclass(frozen=True, slots=True)
class _MappedDirectory:
    tracks: tuple[SubtitleTrack, ...]
    next_position: int
    bucket_count: int


def _map_directory(
    payload: Any,
    *,
    source_type: TranscriptSourceType,
    start_position: int,
    start_bucket_count: int,
    video_id: str,
) -> _MappedDirectory:
    if payload is None:
        raise _directory_error(
            "directory_shape_missing",
            "subtitle track directory payload is missing",
            video_id=video_id,
            fingerprint="directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
        )
    if isinstance(payload, list) and not payload:
        raise _directory_error(
            "directory_shape_empty_list",
            "subtitle track directory payload is an empty list",
            video_id=video_id,
            fingerprint="directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
        )
    if not isinstance(payload, Mapping):
        raise _directory_error(
            "directory_shape_not_object",
            "subtitle track directory payload is malformed",
            video_id=video_id,
            fingerprint="directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
        )
    tracks: list[SubtitleTrack] = []
    position = start_position
    bucket_count = start_bucket_count
    iteration_failed = False
    try:
        for raw_language, raw_entries in payload.items():
            bucket_count += 1
            if bucket_count > _MAX_TRACK_COUNT:
                raise _directory_error(
                    _DIRECTORY_UNKNOWN_DIAGNOSTIC,
                    "subtitle track directory exceeds its language bucket limit",
                    video_id=video_id,
                )
            if (
                not isinstance(raw_language, str)
                or not raw_language
                or len(raw_language) > _MAX_LANGUAGE_CODE_POINTS
                or raw_language.strip() != raw_language
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", raw_language)
                is None
            ):
                raise _directory_error(
                    _DIRECTORY_UNKNOWN_DIAGNOSTIC,
                    "subtitle track directory payload is malformed",
                    video_id=video_id,
                )
            if not isinstance(raw_entries, list):
                raise _directory_error(
                    "directory_shape_not_list",
                    "subtitle track directory entries are malformed",
                    video_id=video_id,
                    fingerprint="directory_fingerprint_language_bucket_missing_or_not_sequence",
                )
            for raw_entry in raw_entries:
                if position >= _MAX_TRACK_COUNT:
                    raise _directory_error(
                        _DIRECTORY_UNKNOWN_DIAGNOSTIC,
                        "subtitle track directory exceeds its track limit",
                        video_id=video_id,
                    )
                current_position = position
                position += 1
                if not isinstance(raw_entry, Mapping):
                    raise _directory_error(
                        "directory_shape_unsupported_entry",
                        "subtitle track payload is malformed",
                        video_id=video_id,
                        fingerprint="directory_fingerprint_track_entry_not_mapping",
                    )
                if "ext" not in raw_entry or "url" not in raw_entry:
                    raise _directory_error(
                        "directory_shape_unsupported_entry",
                        "subtitle track payload is malformed",
                        video_id=video_id,
                        fingerprint="directory_fingerprint_required_field_missing",
                    )
                raw_extension = raw_entry.get("ext")
                if (
                    not isinstance(raw_extension, str)
                    or not raw_extension
                    or len(raw_extension) > _MAX_EXTENSION_CODE_POINTS
                    or raw_extension.strip() != raw_extension
                ):
                    raise _directory_error(
                        "directory_shape_unsupported_entry",
                        "subtitle track format is invalid",
                        video_id=video_id,
                    )
                raw_url = raw_entry.get("url")
                if (
                    not isinstance(raw_url, str)
                    or not raw_url
                    or len(raw_url) > _MAX_TRACK_URL_CODE_POINTS
                ):
                    raise _directory_error(
                        "directory_shape_unsupported_entry",
                        "subtitle track URL is invalid",
                        video_id=video_id,
                    )
                try:
                    _validate_track_url(raw_url, video_id=video_id)
                except TranscriptError as exc:
                    raise _directory_error(
                        "directory_shape_unsupported_entry",
                        "subtitle track URL is invalid",
                        video_id=video_id,
                    ) from exc
                try:
                    name = _track_name(raw_entry.get("name"), video_id=video_id)
                except TranscriptError as exc:
                    raise _directory_error(
                        "directory_shape_unsupported_entry",
                        "subtitle track name is invalid",
                        video_id=video_id,
                    ) from exc
                source_format = _format_from_extension(raw_extension)
                if source_format is None:
                    continue
                tracks.append(
                    SubtitleTrack(
                        source_type=source_type,
                        language=raw_language,
                        source_format=source_format,
                        name=name,
                        url=raw_url,
                        provider_position=current_position,
                    )
                )
    except _DirectoryInvalidResponse:
        raise
    except TranscriptError:
        raise
    except Exception:
        iteration_failed = True
    if iteration_failed:
        raise _directory_error(
            _DIRECTORY_UNKNOWN_DIAGNOSTIC,
            "subtitle track directory payload is malformed",
            video_id=video_id,
        )
    return _MappedDirectory(tuple(tracks), position, bucket_count)


def _content_length(
    headers: object,
    *,
    max_response_bytes: int,
) -> int | None:
    values: list[object] = []
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        raw_values = get_all("Content-Length")
        if raw_values is not None:
            if not isinstance(raw_values, list):
                raise _error(
                    ErrorCode.INVALID_RESPONSE,
                    "selected subtitle content length is invalid",
                    retryable=False,
                    video_id=None,
                )
            values.extend(raw_values)
    elif isinstance(headers, Mapping):
        values.extend(
            value
            for key, value in headers.items()
            if isinstance(key, str) and key.casefold() == "content-length"
        )
    else:
        raise _error(
            ErrorCode.INVALID_RESPONSE,
            "selected subtitle response headers are invalid",
            retryable=False,
            video_id=None,
        )
    if not values:
        return None
    if len(values) != 1 or not isinstance(values[0], str):
        raise _error(
            ErrorCode.INVALID_RESPONSE,
            "selected subtitle content length is invalid",
            retryable=False,
            video_id=None,
        )
    raw_length = values[0].strip()
    if not raw_length.isascii() or not raw_length.isdecimal():
        raise _error(
            ErrorCode.INVALID_RESPONSE,
            "selected subtitle content length is invalid",
            retryable=False,
            video_id=None,
        )
    content_length = int(raw_length)
    if content_length > max_response_bytes:
        raise InvalidSubtitleCandidate(InvalidSubtitleReason.RESOURCE_LIMIT)
    return content_length


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
        failure: TranscriptError | None = None
        payload: object | None = None
        try:
            payload = self._ydl_factory(opts).extract_info(
                _WATCH_URL.format(video_id=video_id),
                download=False,
            )
        except TranscriptError as exc:
            failure = _safe_boundary_error(
                exc.error,
                subject="subtitle track directory",
                video_id=video_id,
            )
            if failure.error.code is ErrorCode.INVALID_RESPONSE:
                failure = _DirectoryInvalidResponse(
                    failure.error,
                    diagnostic=_DIRECTORY_UNKNOWN_DIAGNOSTIC,
                    origin="directory_origin_decode",
                    fingerprint="directory_fingerprint_unknown",
                )
            self.last_call = _call(
                started,
                self._clock(),
                diagnostic=(
                    _DIRECTORY_UNKNOWN_DIAGNOSTIC
                    if failure.error.code is ErrorCode.INVALID_RESPONSE
                    else "directory_error"
                ),
            )
        except (DownloadError, ExtractorError) as exc:
            failure = _map_directory_error(exc, video_id=video_id)
            if failure.error.code is ErrorCode.INVALID_RESPONSE:
                failure = _DirectoryInvalidResponse(
                    failure.error,
                    diagnostic="directory_extractor_directory_error",
                    origin="directory_origin_extractor",
                )
            self.last_call = _call(
                started,
                self._clock(),
                diagnostic=(
                    "directory_extractor_directory_error"
                    if failure.error.code is ErrorCode.INVALID_RESPONSE
                    else "directory_error"
                ),
            )
        except (TimeoutError, socket.timeout):
            self.last_call = _call(started, self._clock(), diagnostic="directory_timeout")
            failure = _error(
                ErrorCode.TRANSIENT_NETWORK,
                "subtitle track directory request timed out",
                retryable=True,
                video_id=video_id,
            )
        except OSError as exc:
            self.last_call = _call(started, self._clock(), diagnostic="directory_os_error")
            failure = _map_directory_error(exc, video_id=video_id)
        except Exception:
            self.last_call = _call(started, self._clock(), diagnostic="directory_error")
            failure = _error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "subtitle track directory provider failed",
                retryable=True,
                video_id=video_id,
            )
        if failure is not None:
            raise failure

        finished = self._clock()
        self.last_call = _call(started, finished)
        if not isinstance(payload, Mapping):
            failure = _directory_error(
                "directory_shape_not_object",
                "subtitle track directory payload is malformed",
                video_id=video_id,
                fingerprint="directory_fingerprint_top_level_not_mapping",
            )
            self.last_call = _call(started, self._clock(), diagnostic=failure.diagnostic)
            raise failure
        if payload.get("id") != video_id:
            failure = _directory_error(
                _DIRECTORY_UNKNOWN_DIAGNOSTIC,
                "subtitle track directory identity is invalid",
                video_id=video_id,
            )
            self.last_call = _call(started, self._clock(), diagnostic=failure.diagnostic)
            raise failure
        if "subtitles" not in payload or "automatic_captions" not in payload:
            failure = _directory_error(
                "directory_shape_missing",
                "subtitle track directory payload is missing",
                video_id=video_id,
                fingerprint="directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
            )
            self.last_call = _call(started, self._clock(), diagnostic=failure.diagnostic)
            raise failure
        try:
            manual = _map_directory(
                payload.get("subtitles"),
                source_type=TranscriptSourceType.MANUAL_SUBTITLE,
                start_position=0,
                start_bucket_count=0,
                video_id=video_id,
            )
            automatic = _map_directory(
                payload.get("automatic_captions"),
                source_type=TranscriptSourceType.AUTO_SUBTITLE,
                start_position=manual.next_position,
                start_bucket_count=manual.bucket_count,
                video_id=video_id,
            )
            tracks = (*manual.tracks, *automatic.tracks)
            if automatic.next_position > 0 and not tracks:
                raise _directory_error(
                    "directory_shape_unsupported_entry",
                    "subtitle track directory has no supported formats",
                    video_id=video_id,
                )
        except _DirectoryInvalidResponse as exc:
            self.last_call = _call(started, self._clock(), diagnostic=exc.diagnostic)
            raise
        except TranscriptError as exc:
            if exc.error.code is ErrorCode.INVALID_RESPONSE:
                self.last_call = _call(
                    started,
                    self._clock(),
                    diagnostic=_DIRECTORY_UNKNOWN_DIAGNOSTIC,
                )
            raise
        return SubtitleTrackListing(
            tracks=tracks,
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
        response: object | None = None
        failure: TranscriptError | None = None
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
            failure = mapped
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            self.last_call = _call(started, self._clock(), diagnostic="body_network_error")
            failure = _error(
                ErrorCode.TRANSIENT_NETWORK,
                "selected subtitle body request failed",
                retryable=True,
                video_id=None,
            )
        except Exception:
            self.last_call = _call(started, self._clock(), diagnostic="body_error")
            failure = _error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "selected subtitle body provider failed",
                retryable=True,
                video_id=None,
            )
        if failure is not None:
            raise failure
        if response is None:
            raise _error(
                ErrorCode.PROVIDER_UNAVAILABLE,
                "selected subtitle body provider failed",
                retryable=True,
                video_id=None,
            )

        result: SubtitleReadResult | None = None
        invalid_reason: InvalidSubtitleReason | None = None
        failure = None
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
            content_length = _content_length(
                headers_value,
                max_response_bytes=self._max_response_bytes,
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
            result = SubtitleReadResult(body=b"".join(chunks), call=self.last_call)
        except TranscriptError as exc:
            failure = _safe_boundary_error(
                exc.error,
                subject="selected subtitle body",
                video_id=None,
            )
        except InvalidSubtitleCandidate as exc:
            invalid_reason = exc.reason
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            self.last_call = _call(started, self._clock(), diagnostic="body_network_error")
            failure = _error(
                ErrorCode.TRANSIENT_NETWORK,
                "selected subtitle body request failed",
                retryable=True,
                video_id=None,
            )
        except Exception:
            self.last_call = _call(started, self._clock(), diagnostic="body_error")
            failure = _error(
                ErrorCode.INVALID_RESPONSE,
                "selected subtitle body response is invalid",
                retryable=False,
                video_id=None,
            )
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass
        if invalid_reason is not None:
            raise InvalidSubtitleCandidate(invalid_reason)
        if failure is not None:
            raise failure
        if result is None:
            raise _error(
                ErrorCode.INVALID_RESPONSE,
                "selected subtitle body response is invalid",
                retryable=False,
                video_id=None,
            )
        return result


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


__all__ = ["DIRECTORY_DIAGNOSTIC_CODES", "YtDlpSubtitleAdapter"]
