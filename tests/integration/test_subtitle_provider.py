"""Offline integration tests for subtitle Adapter, files, cache, and SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import traceback
import urllib.error
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from datetime import timedelta as td
from http.client import HTTPMessage
from pathlib import Path
from typing import Any

import pytest
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    UnavailableVideoError,
)

from youtube_intel import transcripts as transcripts_mod
from youtube_intel.domain import (
    AppError,
    Availability,
    DiscoveryBatch,
    DiscoveryCursor,
    ErrorCode,
    JobStatus,
    LiveStatus,
    PipelineStatus,
    ProcessingStage,
    ProviderCallMetadata,
    SubtitleFormat,
    TranscriptionReason,
    TranscriptionRequired,
    TranscriptProvider,
    TranscriptReady,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.providers import subtitles as subtitles_mod
from youtube_intel.providers.subtitles import (
    DIRECTORY_DIAGNOSTIC_CODES,
    DIRECTORY_FINGERPRINT_CODES,
    DIRECTORY_ORIGIN_CODES,
    YtDlpSubtitleAdapter,
)
from youtube_intel.state import (
    JobType,
    ProviderCallRecord,
    ProviderCallRequest,
    ProviderCallStatus,
    ProviderReservation,
    SQLiteStateRepository,
    VerifiedArtifact,
)
from youtube_intel.transcripts import (
    FORMAT_POLICY_VERSION,
    QUALITY_POLICY_VERSION,
    SELECTION_POLICY_VERSION,
    InvalidSubtitleCandidate,
    InvalidSubtitleReason,
    SubtitleAcquisitionService,
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
    TranscriptError,
    TranscriptJobContext,
    TranscriptRepository,
    build_raw_request_hash,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "subtitles"
NOW = datetime(2026, 7, 16, 10, 0, 0, tzinfo=UTC)
_SAFE_EXCEPTION_PLACEHOLDER = "synthetic provider failure"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class _YdlHandle:
    def __init__(self, result: object) -> None:
        self._result = result
        self.calls: list[tuple[str, bool]] = []

    def extract_info(self, url: str, download: bool = True) -> object:
        self.calls.append((url, download))
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _IdentityShapeMismatchPayload(Mapping[object, object]):
    """Expose only a non-user sentinel at the outer downloader boundary."""

    _sentinel = object()

    def __getitem__(self, item_ref: object) -> object:
        del item_ref
        return self._sentinel

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __len__(self) -> int:
        return 1


class _Response:
    def __init__(
        self,
        body: bytes,
        *,
        content_length: int | None = None,
        final_url: str | None = None,
        headers: object | None = None,
    ) -> None:
        if content_length is not None and headers is not None:
            raise ValueError("content_length and headers are mutually exclusive")
        self._body = body
        self._offset = 0
        self.headers = headers if headers is not None else (
            {} if content_length is None else {"Content-Length": str(content_length)}
        )
        self.closed = False
        self._final_url = final_url
        self.read_calls = 0

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if size < 0:
            size = len(self._body) - self._offset
        chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True

    def geturl(self) -> str | None:
        return self._final_url


def _adapter_for_info(
    result: object,
    *,
    captured_opts: list[object] | None = None,
) -> tuple[YtDlpSubtitleAdapter, _YdlHandle]:
    handle = _YdlHandle(result)
    adapter = YtDlpSubtitleAdapter(timeout_seconds=12.0)
    subtitles_mod._bind_test_hooks(
        adapter,
        ydl_factory=lambda opts: handle,
        clock=lambda: NOW,
        opts_sink=captured_opts,
    )
    return adapter, handle


def test_ytdlp_adapter_enumerates_tracks_with_safe_no_download_options(
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: list[object] = []
    adapter, handle = _adapter_for_info(
        _load_json("info_tracks.json"),
        captured_opts=captured,
    )

    listing = adapter.enumerate_tracks("video123")

    assert handle.calls == [
        ("https://www.youtube.com/watch?v=video123", False)
    ]
    assert [
        (track.source_type, track.language, track.source_format)
        for track in listing.tracks
    ] == [
        (
            TranscriptSourceType.MANUAL_SUBTITLE,
            "en",
            SubtitleFormat.JSON3,
        ),
        (
            TranscriptSourceType.MANUAL_SUBTITLE,
            "en",
            SubtitleFormat.VTT,
        ),
        (
            TranscriptSourceType.AUTO_SUBTITLE,
            "zh-CN",
            SubtitleFormat.VTT,
        ),
        (
            TranscriptSourceType.AUTO_SUBTITLE,
            "en",
            SubtitleFormat.JSON3,
        ),
    ]
    opts = captured[0]
    assert isinstance(opts, dict)
    assert opts["skip_download"] is True
    assert opts["ignoreconfig"] is True
    assert opts["usenetrc"] is False
    assert opts["writesubtitles"] is False
    assert opts["writeautomaticsub"] is False
    assert opts["writethumbnail"] is False
    assert opts["socket_timeout"] == 12.0
    assert opts["logger"].error("sensitive provider error") is None
    assert capsys.readouterr() == ("", "")
    assert all(
        key not in opts
        for key in (
            "cookiefile",
            "cookiesfrombrowser",
            "username",
            "password",
            "netrc_location",
            "remote_components",
            "ffmpeg_location",
            "postprocessors",
        )
    )


@pytest.mark.parametrize(
    ("failure", "code", "retryable"),
    [
        (
            DownloadError("HTTP Error 403: Forbidden"),
            ErrorCode.PERMISSION_DENIED,
            False,
        ),
        (
            DownloadError("HTTP Error 401: Unauthorized"),
            ErrorCode.PERMISSION_DENIED,
            False,
        ),
        (
            DownloadError("HTTP Error 404: Not Found"),
            ErrorCode.CONTENT_UNAVAILABLE,
            False,
        ),
        (
            DownloadError("HTTP Error 429: Too Many Requests"),
            ErrorCode.RATE_LIMITED,
            True,
        ),
        (
            DownloadError("HTTP Error 503: Service Unavailable"),
            ErrorCode.PROVIDER_UNAVAILABLE,
            True,
        ),
        (
            DownloadError("The read operation timed out"),
            ErrorCode.TRANSIENT_NETWORK,
            True,
        ),
        (
            DownloadError("Private video. Sign in if granted access"),
            ErrorCode.CONTENT_UNAVAILABLE,
            False,
        ),
    ],
)
def test_track_directory_errors_map_to_existing_error_codes(
    failure: BaseException,
    code: ErrorCode,
    retryable: bool,
) -> None:
    adapter, _ = _adapter_for_info(failure)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is code
    assert exc_info.value.error.retryable is retryable
    assert exc_info.value.error.video_id == "video123"
    assert "http" not in exc_info.value.error.message.lower()


def test_wrapped_extractor_error_reaches_compatibility_through_adapter() -> None:
    extractor_error = ExtractorError(_SAFE_EXCEPTION_PLACEHOLDER)
    failure = DownloadError(
        _SAFE_EXCEPTION_PLACEHOLDER,
        exc_info=(ExtractorError, extractor_error, None),
    )
    adapter, _ = _adapter_for_info(failure)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert getattr(exc_info.value, "content_availability", None) == (
        "content_availability_extractor_compatibility"
    )


@pytest.mark.parametrize(
    ("exception_type", "expected"),
    [
        (
            GeoRestrictedError,
            "content_availability_environment_restricted",
        ),
        (
            UnavailableVideoError,
            "content_availability_video_unavailable",
        ),
    ],
)
def test_other_typed_availability_states_remain_reachable_through_adapter(
    exception_type: Callable[[str], BaseException],
    expected: str,
) -> None:
    typed_error = exception_type(_SAFE_EXCEPTION_PLACEHOLDER)
    failure = DownloadError(
        _SAFE_EXCEPTION_PLACEHOLDER,
        exc_info=(type(typed_error), typed_error, None),
    )
    adapter, _ = _adapter_for_info(failure)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert getattr(exc_info.value, "content_availability", None) == expected


def _ordinary_download_error() -> BaseException:
    return DownloadError(_SAFE_EXCEPTION_PLACEHOLDER)


def _direct_extractor_error() -> BaseException:
    return ExtractorError(_SAFE_EXCEPTION_PLACEHOLDER)


def _empty_exception_info() -> BaseException:
    return DownloadError(
        _SAFE_EXCEPTION_PLACEHOLDER,
        exc_info=(None, None, None),
    )


def _malformed_exception_info() -> BaseException:
    return DownloadError(
        _SAFE_EXCEPTION_PLACEHOLDER,
        exc_info=(ExtractorError, object(), None),
    )


def _uncertain_exception_info() -> BaseException:
    error = ValueError(_SAFE_EXCEPTION_PLACEHOLDER)
    return DownloadError(
        _SAFE_EXCEPTION_PLACEHOLDER,
        exc_info=(ValueError, error, None),
    )


def _cyclic_exception_info() -> BaseException:
    outer = DownloadError(_SAFE_EXCEPTION_PLACEHOLDER)
    inner = DownloadError(_SAFE_EXCEPTION_PLACEHOLDER)
    outer.exc_info = (DownloadError, inner, None)
    inner.exc_info = (DownloadError, outer, None)
    return outer


def _overdeep_exception_info() -> BaseException:
    error: BaseException = ExtractorError(_SAFE_EXCEPTION_PLACEHOLDER)
    for _ in range(32):
        error = DownloadError(
            _SAFE_EXCEPTION_PLACEHOLDER,
            exc_info=(type(error), error, None),
        )
    return error


@pytest.mark.parametrize(
    "failure_factory",
    [
        _ordinary_download_error,
        _direct_extractor_error,
        _empty_exception_info,
        _malformed_exception_info,
        _uncertain_exception_info,
        _cyclic_exception_info,
        _overdeep_exception_info,
    ],
    ids=[
        "ordinary",
        "direct-extractor",
        "empty",
        "malformed",
        "uncertain",
        "cycle",
        "overdeep",
    ],
)
def test_unreliable_exception_chains_fail_closed_to_unknown_through_adapter(
    failure_factory: Callable[[], BaseException],
) -> None:
    adapter, _ = _adapter_for_info(failure_factory())

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.CONTENT_UNAVAILABLE
    assert getattr(exc_info.value, "content_availability", None) == (
        "content_availability_unknown"
    )


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (
            "VIDEO_UNAVAILABLE",
            "content_availability_video_unavailable",
        ),
        (
            "ENVIRONMENT_RESTRICTED",
            "content_availability_environment_restricted",
        ),
        (
            "EXTRACTOR_COMPATIBILITY",
            "content_availability_extractor_compatibility",
        ),
        ("UNKNOWN", "content_availability_unknown"),
    ],
)
def test_content_availability_states_map_to_closed_safe_codes(
    state: str,
    expected: str,
) -> None:
    availability_state = getattr(subtitles_mod._ContentAvailabilityState, state)

    assert subtitles_mod._content_availability_code(availability_state) == expected


def test_dangerous_selected_track_url_fails_closed() -> None:
    payload = _load_json("info_tracks.json")
    payload["subtitles"]["en"][0]["url"] = "http://127.0.0.1/private"
    adapter, _ = _adapter_for_info(payload)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert "127.0.0.1" not in exc_info.value.error.message


def _directory_entry(
    *,
    source_format: str = "json3",
    name: str = "English",
    url: str = "https://www.youtube.com/api/timedtext?v=video123",
) -> dict[str, str]:
    return {"ext": source_format, "name": name, "url": url}


def _directory_payload(
    entries: list[dict[str, str]],
    *,
    language: str = "en",
) -> dict[str, object]:
    return {
        "id": "video123",
        "subtitles": {language: entries},
        "automatic_captions": {},
    }


def _url_with_length(length: int) -> str:
    prefix = "https://www.youtube.com/api/timedtext?"
    assert length >= len(prefix)
    return prefix + ("q" * (length - len(prefix)))


def test_directory_diagnostic_codes_are_exactly_the_fixed_b6_classifications() -> None:
    assert DIRECTORY_DIAGNOSTIC_CODES == frozenset(
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


def test_directory_origin_and_fingerprint_codes_are_exactly_the_frozen_b7_vocabularies() -> None:
    assert DIRECTORY_ORIGIN_CODES == frozenset(
        {
            "directory_origin_extractor",
            "directory_origin_decode",
            "directory_origin_mapping",
            "directory_origin_unknown",
        }
    )
    assert DIRECTORY_FINGERPRINT_CODES == frozenset(
        {
            "directory_fingerprint_top_level_not_mapping",
            "directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
            "directory_fingerprint_language_bucket_missing_or_not_sequence",
            "directory_fingerprint_track_entry_not_mapping",
            "directory_fingerprint_required_field_missing",
            "directory_fingerprint_unknown",
        }
    )


def test_directory_contract_state_vocabularies_are_exactly_frozen() -> None:
    assert subtitles_mod._DIRECTORY_CONTRACT_FIELDS == (
        "video_identity_shape",
        "manual_directory_shape",
        "automatic_directory_shape",
        "caption_bucket_shape",
        "track_entry_shape",
        "required_members_shape",
    )
    assert tuple(member.value for member in subtitles_mod._VideoIdentityShape) == (
        "missing",
        "string",
        "other",
        "unknown",
    )
    assert tuple(member.value for member in subtitles_mod._DirectoryShape) == (
        "missing",
        "mapping",
        "other",
        "unknown",
    )
    assert tuple(member.value for member in subtitles_mod._CaptionBucketShape) == (
        "not_evaluated",
        "absent",
        "sequence",
        "other",
        "unknown",
    )
    assert tuple(member.value for member in subtitles_mod._TrackEntryShape) == (
        "not_evaluated",
        "absent",
        "mapping",
        "other",
        "unknown",
    )
    assert tuple(member.value for member in subtitles_mod._RequiredMembersShape) == (
        "not_evaluated",
        "complete",
        "missing",
        "wrong_type",
        "unknown",
    )


def test_directory_contract_state_uses_only_frozen_no_value_enums() -> None:
    state = subtitles_mod._directory_contract_state(
        subtitles_mod._VideoIdentityShape.UNKNOWN,
        subtitles_mod._DirectoryShape.UNKNOWN,
        subtitles_mod._DirectoryShape.UNKNOWN,
        subtitles_mod._CaptionBucketShape.NOT_EVALUATED,
        subtitles_mod._TrackEntryShape.NOT_EVALUATED,
        subtitles_mod._RequiredMembersShape.NOT_EVALUATED,
    )

    assert state == (
        "unknown",
        "unknown",
        "unknown",
        "not_evaluated",
        "not_evaluated",
        "not_evaluated",
    )
    with pytest.raises(TypeError):
        subtitles_mod._directory_contract_state(
            object(),
            subtitles_mod._DirectoryShape.UNKNOWN,
            subtitles_mod._DirectoryShape.UNKNOWN,
            subtitles_mod._CaptionBucketShape.NOT_EVALUATED,
            subtitles_mod._TrackEntryShape.NOT_EVALUATED,
            subtitles_mod._RequiredMembersShape.NOT_EVALUATED,
        )


def test_ytdlp_adapter_maps_contract_mismatch_to_frozen_no_value_state() -> None:
    adapter, _ = _adapter_for_info(_IdentityShapeMismatchPayload())

    with pytest.raises(TranscriptError) as captured:
        adapter.enumerate_tracks("video123")

    assert captured.value.error.code is ErrorCode.INVALID_RESPONSE
    assert captured.value.directory_origin == "directory_origin_mapping"
    assert captured.value.directory_contract_state == (
        "other",
        "unknown",
        "unknown",
        "not_evaluated",
        "not_evaluated",
        "not_evaluated",
    )


@pytest.mark.parametrize(
    ("state", "fingerprint"),
    [
        (
            subtitles_mod._DirectoryStructureState.TOP_LEVEL_NOT_MAPPING,
            "directory_fingerprint_top_level_not_mapping",
        ),
        (
            subtitles_mod._DirectoryStructureState.SUBTITLE_BUCKET_MISSING_OR_NOT_MAPPING,
            "directory_fingerprint_subtitle_bucket_missing_or_not_mapping",
        ),
        (
            subtitles_mod._DirectoryStructureState.LANGUAGE_BUCKET_MISSING_OR_NOT_SEQUENCE,
            "directory_fingerprint_language_bucket_missing_or_not_sequence",
        ),
        (
            subtitles_mod._DirectoryStructureState.TRACK_ENTRY_NOT_MAPPING,
            "directory_fingerprint_track_entry_not_mapping",
        ),
        (
            subtitles_mod._DirectoryStructureState.REQUIRED_FIELD_MISSING,
            "directory_fingerprint_required_field_missing",
        ),
        (
            subtitles_mod._DirectoryStructureState.UNKNOWN,
            "directory_fingerprint_unknown",
        ),
    ],
)
def test_directory_structure_states_map_to_frozen_origin_and_fingerprints(
    state: object,
    fingerprint: str,
) -> None:
    classification = subtitles_mod._classify_directory_structure(state)

    assert classification.origin == "directory_origin_mapping"
    assert classification.fingerprint == fingerprint
    assert classification.origin in DIRECTORY_ORIGIN_CODES
    assert classification.fingerprint in DIRECTORY_FINGERPRINT_CODES


def test_directory_structure_classifier_rejects_nonstructural_state() -> None:
    with pytest.raises(TypeError):
        subtitles_mod._classify_directory_structure(object())


@pytest.mark.parametrize(
    ("fixture_name", "diagnostic"),
    [
        ("directory_identity", "directory_shape_unknown"),
        ("directory_bucket_shape", "directory_shape_not_list"),
        ("directory_track_shape", "directory_shape_unsupported_entry"),
        ("directory_track_format", "directory_shape_unsupported_entry"),
        ("directory_track_url", "directory_shape_unsupported_entry"),
        ("directory_track_name", "directory_shape_unsupported_entry"),
        ("directory_no_supported_format", "directory_shape_unsupported_entry"),
    ],
)
def test_directory_invalid_response_has_only_a_fixed_diagnostic_code(
    fixture_name: str,
    diagnostic: str,
) -> None:
    payload = _load_json("directory_diagnostics.json")[fixture_name]
    adapter, _ = _adapter_for_info(payload)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert adapter.last_call is not None
    assert adapter.last_call.diagnostics[0].code == diagnostic
    assert adapter.last_call.diagnostics[0].code in DIRECTORY_DIAGNOSTIC_CODES
    assert "127.0.0.1" not in adapter.last_call.diagnostics[0].message


@pytest.mark.parametrize(
    ("fixture_name", "diagnostic"),
    [
        ("directory_shape_missing", "directory_shape_missing"),
        ("directory_shape_not_object", "directory_shape_not_object"),
        ("directory_shape_not_list", "directory_shape_not_list"),
        ("directory_shape_empty_list", "directory_shape_empty_list"),
        ("directory_shape_unsupported_entry", "directory_shape_unsupported_entry"),
        ("directory_shape_unknown", "directory_shape_unknown"),
    ],
)
def test_directory_shape_invalid_response_has_only_a_fixed_b6_code(
    fixture_name: str,
    diagnostic: str,
) -> None:
    payload = _load_json("directory_shape_diagnostics.json")[fixture_name]
    adapter, _ = _adapter_for_info(payload)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert adapter.last_call is not None
    assert adapter.last_call.diagnostics[0].code == diagnostic
    assert adapter.last_call.diagnostics[0].code in DIRECTORY_DIAGNOSTIC_CODES
    assert adapter.last_call.diagnostics[0].message == diagnostic.replace("_", " ")


def test_directory_extractor_and_decode_invalid_responses_preserve_b6_codes_and_b7_origins() -> None:
    extractor, _ = _adapter_for_info(DownloadError("extract failed with token=private"))
    unknown, _ = _adapter_for_info(
        TranscriptError(
            AppError(
                code=ErrorCode.INVALID_RESPONSE,
                message="private directory payload",
                retryable=False,
                video_id="video123",
                stage=ProcessingStage.TRANSCRIPT,
            )
        )
    )

    for adapter, diagnostic, origin, fingerprint in (
        (
            extractor,
            "directory_extractor_directory_error",
            "directory_origin_extractor",
            None,
        ),
        (
            unknown,
            "directory_shape_unknown",
            "directory_origin_decode",
            "directory_fingerprint_unknown",
        ),
    ):
        with pytest.raises(TranscriptError) as exc_info:
            adapter.enumerate_tracks("video123")

        assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
        assert adapter.last_call is not None
        assert adapter.last_call.diagnostics[0].code == diagnostic
        assert getattr(exc_info.value, "directory_origin") == origin
        assert getattr(exc_info.value, "directory_fingerprint") == fingerprint
        assert adapter.last_call.diagnostics[0].message not in {
            "extract failed with token=private",
            "private directory payload",
        }


def test_directory_compatible_empty_buckets_remain_valid() -> None:
    payload = _load_json("directory_diagnostics.json")["directory_compatible_empty_buckets"]
    adapter, _ = _adapter_for_info(payload)

    listing = adapter.enumerate_tracks("video123")

    assert listing.tracks == ()
    assert listing.call.diagnostics == ()


def test_directory_rejects_unsupported_only_but_keeps_supported_mixed_tracks() -> None:
    unsupported, _ = _adapter_for_info(
        _directory_payload([_directory_entry(source_format="ttml")])
    )

    with pytest.raises(TranscriptError) as unsupported_exc:
        unsupported.enumerate_tracks("video123")

    assert unsupported_exc.value.error.code is ErrorCode.INVALID_RESPONSE
    assert unsupported_exc.value.error.retryable is False

    mixed, _ = _adapter_for_info(
        _directory_payload(
            [
                _directory_entry(source_format="ttml"),
                _directory_entry(source_format="json3"),
            ]
        )
    )
    listing = mixed.enumerate_tracks("video123")

    assert len(listing.tracks) == 1
    assert listing.tracks[0].source_format is SubtitleFormat.JSON3


@pytest.mark.parametrize(
    ("field", "boundary", "first_invalid"),
    [
        ("name", 1_000, 1_001),
        ("language", 128, 129),
        ("ext", 32, 33),
        ("url", 8_192, 8_193),
    ],
)
def test_directory_field_limits_accept_boundary_and_reject_first_invalid(
    field: str,
    boundary: int,
    first_invalid: int,
) -> None:
    def payload_for(length: int) -> dict[str, object]:
        language = "e" * length if field == "language" else "en"
        supported = _directory_entry(
            name=("n" * length if field == "name" else "English"),
            url=(_url_with_length(length) if field == "url" else _url_with_length(80)),
        )
        entries = [supported]
        if field == "ext":
            entries.append(
                _directory_entry(
                    source_format="x" * length,
                    url=_url_with_length(80),
                )
            )
        return _directory_payload(entries, language=language)

    at_boundary, _ = _adapter_for_info(payload_for(boundary))
    listing = at_boundary.enumerate_tracks("video123")
    assert len(listing.tracks) == 1

    over_boundary, _ = _adapter_for_info(payload_for(first_invalid))
    with pytest.raises(TranscriptError) as exc_info:
        over_boundary.enumerate_tracks("video123")
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


def test_directory_track_count_accepts_1024_and_rejects_1025() -> None:
    at_boundary, _ = _adapter_for_info(
        _directory_payload([_directory_entry()] * 1_024)
    )
    assert len(at_boundary.enumerate_tracks("video123").tracks) == 1_024

    over_boundary, _ = _adapter_for_info(
        _directory_payload([_directory_entry()] * 1_025)
    )
    with pytest.raises(TranscriptError) as exc_info:
        over_boundary.enumerate_tracks("video123")
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


def test_directory_track_count_is_cumulative_across_caption_sources() -> None:
    at_boundary, _ = _adapter_for_info(
        {
            "id": "video123",
            "subtitles": {"en": [_directory_entry()] * 512},
            "automatic_captions": {"en": [_directory_entry()] * 512},
        }
    )
    assert len(at_boundary.enumerate_tracks("video123").tracks) == 1_024

    over_boundary, _ = _adapter_for_info(
        {
            "id": "video123",
            "subtitles": {"en": [_directory_entry()] * 512},
            "automatic_captions": {"en": [_directory_entry()] * 513},
        }
    )
    with pytest.raises(TranscriptError) as exc_info:
        over_boundary.enumerate_tracks("video123")
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


def test_directory_track_limit_counts_only_supported_ytdlp_formats() -> None:
    formats = ("json3", "srv1", "srv2", "srv3", "ttml", "vtt", "srt")
    automatic_captions = {
        f"lang-{index}": [
            _directory_entry(source_format=source_format)
            for source_format in formats
        ]
        for index in range(157)
    }
    adapter, _ = _adapter_for_info(
        {
            "id": "video123",
            "subtitles": {},
            "automatic_captions": automatic_captions,
        }
    )

    listing = adapter.enumerate_tracks("video123")

    assert len(listing.tracks) == 471
    assert {track.source_format for track in listing.tracks} == {
        SubtitleFormat.JSON3,
        SubtitleFormat.VTT,
        SubtitleFormat.SRT,
    }
    assert listing.tracks[-1].provider_position == 1_098


def test_directory_raw_entry_scan_remains_finitely_bounded() -> None:
    at_boundary, _ = _adapter_for_info(
        _directory_payload(
            [
                *[_directory_entry(source_format="ttml")] * 4_095,
                _directory_entry(source_format="json3"),
            ]
        )
    )
    listing = at_boundary.enumerate_tracks("video123")
    assert len(listing.tracks) == 1
    assert listing.tracks[0].provider_position == 4_095

    over_boundary, _ = _adapter_for_info(
        _directory_payload(
            [
                *[_directory_entry(source_format="ttml")] * 4_096,
                _directory_entry(source_format="json3"),
            ]
        )
    )
    with pytest.raises(TranscriptError) as exc_info:
        over_boundary.enumerate_tracks("video123")
    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


def test_structurally_invalid_unsupported_track_invalidates_mixed_directory() -> None:
    payload = _directory_payload(
        [
            _directory_entry(source_format="json3"),
            {"ext": "ttml", "name": "Unsupported without URL"},
        ]
    )
    adapter, _ = _adapter_for_info(payload)

    with pytest.raises(TranscriptError) as exc_info:
        adapter.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE


def test_selected_body_read_is_limited_closed_and_returns_call_metadata() -> None:
    response = _Response(
        (FIXTURES / "manual_en.json3").read_bytes(),
        content_length=(FIXTURES / "manual_en.json3").stat().st_size,
    )
    adapter = YtDlpSubtitleAdapter(timeout_seconds=7.0)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: response,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    result = adapter.read_track(track)

    assert result.body == (FIXTURES / "manual_en.json3").read_bytes()
    assert result.call.provider == "yt-dlp"
    assert response.closed is True


def test_selected_body_short_read_and_size_limit_close_response() -> None:
    short = _Response(b"short", content_length=10)
    adapter = YtDlpSubtitleAdapter(max_response_bytes=20)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: short,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    with pytest.raises(TranscriptError) as short_exc:
        adapter.read_track(track)
    assert short_exc.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert short.closed is True

    oversized = _Response(b"x" * 9)
    adapter = YtDlpSubtitleAdapter(max_response_bytes=8)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: oversized,
    )
    with pytest.raises(InvalidSubtitleCandidate) as size_exc:
        adapter.read_track(track)
    assert size_exc.value.reason is InvalidSubtitleReason.RESOURCE_LIMIT
    assert oversized.closed is True


def test_real_http_message_content_length_is_case_insensitive_and_detects_short_read(
) -> None:
    headers = HTTPMessage()
    headers.add_header("cOnTeNt-LeNgTh", "10")
    response = _Response(b"short", headers=headers)
    adapter = YtDlpSubtitleAdapter(max_response_bytes=20)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: response,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    with pytest.raises(TranscriptError) as exc_info:
        adapter.read_track(track)

    assert exc_info.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert exc_info.value.error.retryable is True
    assert response.closed is True


@pytest.mark.parametrize(
    "values",
    [
        ("invalid",),
        ("-1",),
        ("5", "5"),
        ("5", "6"),
    ],
)
def test_invalid_or_duplicate_content_length_fails_before_body_read(
    values: tuple[str, ...],
) -> None:
    headers = HTTPMessage()
    for value in values:
        headers.add_header("Content-Length", value)
    response = _Response(b"valid body", headers=headers)
    adapter = YtDlpSubtitleAdapter(max_response_bytes=20)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: response,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    with pytest.raises(TranscriptError) as exc_info:
        adapter.read_track(track)

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert response.read_calls == 0
    assert response.closed is True


def test_overlimit_content_length_fails_before_body_read() -> None:
    headers = HTTPMessage()
    headers.add_header("Content-Length", "21")
    response = _Response(b"valid body", headers=headers)
    adapter = YtDlpSubtitleAdapter(max_response_bytes=20)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: response,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    with pytest.raises(InvalidSubtitleCandidate) as exc_info:
        adapter.read_track(track)

    assert exc_info.value.reason is InvalidSubtitleReason.RESOURCE_LIMIT
    assert response.read_calls == 0
    assert response.closed is True


@pytest.mark.parametrize(
    ("status", "code", "retryable", "retry_after"),
    [
        (401, ErrorCode.PERMISSION_DENIED, False, None),
        (403, ErrorCode.TRANSIENT_NETWORK, True, None),
        (404, ErrorCode.TRANSIENT_NETWORK, True, None),
        (429, ErrorCode.RATE_LIMITED, True, 17.0),
        (503, ErrorCode.PROVIDER_UNAVAILABLE, True, None),
    ],
)
def test_selected_body_http_errors_follow_t11(
    status: int,
    code: ErrorCode,
    retryable: bool,
    retry_after: float | None,
) -> None:
    headers = {"Retry-After": "17"} if status == 429 else {}

    def raise_http_error(request: object, timeout: float) -> object:
        raise urllib.error.HTTPError(
            "https://www.youtube.com/api/timedtext",
            status,
            "error",
            headers,
            None,
        )

    adapter = YtDlpSubtitleAdapter()
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=raise_http_error,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.AUTO_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.VTT,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=vtt",
        provider_position=0,
    )

    with pytest.raises(TranscriptError) as exc_info:
        adapter.read_track(track)

    assert exc_info.value.error.code is code
    assert exc_info.value.error.retryable is retryable
    assert exc_info.value.error.retry_after_seconds == retry_after
    assert "timedtext" not in exc_info.value.error.message


def test_redirect_to_unsafe_final_url_is_rejected_and_closed() -> None:
    response = _Response(
        (FIXTURES / "manual_en.json3").read_bytes(),
        final_url="http://127.0.0.1/private",
    )
    adapter = YtDlpSubtitleAdapter()
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: response,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    with pytest.raises(TranscriptError) as exc_info:
        adapter.read_track(track)

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert response.closed is True


def test_read_timeout_after_response_open_is_mapped_and_closed() -> None:
    class FailingResponse(_Response):
        def read(self, size: int = -1) -> bytes:
            raise TimeoutError("timed out while reading private URL")

    response = FailingResponse(b"")
    adapter = YtDlpSubtitleAdapter()
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=lambda request, timeout: response,
        clock=lambda: NOW,
    )
    track = SubtitleTrack(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        language="en",
        source_format=SubtitleFormat.JSON3,
        name="English",
        url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
        provider_position=0,
    )

    with pytest.raises(TranscriptError) as exc_info:
        adapter.read_track(track)

    assert exc_info.value.error.code is ErrorCode.TRANSIENT_NETWORK
    assert response.closed is True


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video123",
        channel_id="UC_TEST",
        channel_name="Test channel",
        title="Subtitle test video",
        description="",
        source_url="https://www.youtube.com/watch?v=video123",
        published_at=NOW,
        duration_seconds=180,
        default_language="en",
        available_languages=("en", "zh-CN"),
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _repository_with_transcript_job(
    tmp_path: Path,
    *,
    job_id: str = "subtitle-job",
    now: datetime = NOW,
) -> SQLiteStateRepository:
    repository = SQLiteStateRepository(tmp_path / "state.sqlite3")
    repository.initialize(now=now)
    repository.save_discovery_batch(
        DiscoveryBatch(
            channel_id="UC_TEST",
            video_ids=("video123",),
            next_cursor=DiscoveryCursor(
                channel_id="UC_TEST",
                last_checked_at=now,
                latest_published_at=now,
                latest_video_id="video123",
                provider_cursor="cursor-1",
            ),
            call=ProviderCallMetadata(
                provider="fake-source",
                started_at=now,
                finished_at=now,
            ),
        ),
        expected_cursor=None,
        expected_revision=0,
        pipeline_version="pipeline-v1",
        now=now,
    )
    repository.upsert_video_metadata(
        _video(),
        pipeline_version="pipeline-v1",
        now=now,
    )
    assert repository.advance_pipeline(
        "video123",
        expected_status=PipelineStatus.DISCOVERED,
        target_status=PipelineStatus.METADATA_READY,
        pipeline_version="pipeline-v1",
        now=now,
    )
    _create_and_claim_transcript_job(repository, job_id=job_id, now=now)
    return repository


def _create_and_claim_transcript_job(
    repository: SQLiteStateRepository,
    *,
    job_id: str,
    now: datetime,
) -> None:
    repository.create_job(
        job_id=job_id,
        scope_key="video:video123:TRANSCRIPT",
        video_id="video123",
        job_type=JobType.VIDEO_STAGE,
        target_stage=ProcessingStage.TRANSCRIPT,
        pipeline_version="pipeline-v1",
        max_attempts=3,
        available_at=now,
        now=now,
    )
    claimed = repository.claim_next_job(
        owner="worker-1",
        lease_until=now + td(minutes=10),
        now=now,
    )
    assert claimed is not None
    assert claimed.job_id == job_id


class _BodyOpener:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls = 0
        self.responses: list[_Response] = []

    def __call__(self, request: object, timeout: float) -> object:
        self.calls += 1
        response = _Response(self.body, content_length=len(self.body))
        self.responses.append(response)
        return response


def _bound_adapter(
    payload: object,
    opener: _BodyOpener,
) -> tuple[YtDlpSubtitleAdapter, _YdlHandle]:
    adapter, handle = _adapter_for_info(payload)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=opener,
        clock=lambda: NOW,
    )
    return adapter, handle


def _service(
    *,
    adapter: YtDlpSubtitleAdapter,
    repository: SQLiteStateRepository,
    data_root: Path,
    job_id: str,
    now: datetime = NOW,
    refresh_generation: int = 0,
) -> SubtitleAcquisitionService:
    return SubtitleAcquisitionService(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        context=TranscriptJobContext(
            job_id=job_id,
            owner="worker-1",
            pipeline_version="pipeline-v1",
            refresh_generation=refresh_generation,
        ),
        clock=lambda: now,
    )


def _provider_request_for(
    adapter: YtDlpSubtitleAdapter,
    languages: tuple[str, ...] = ("en",),
) -> ProviderCallRequest:
    raw_request_hash = build_raw_request_hash(
        video_id="video123",
        language_preferences=languages,
        provider=adapter.provider_name,
        provider_version=adapter.provider_version,
        refresh_generation=0,
    )
    return ProviderCallRequest(
        operation="subtitle.fetch",
        normalized_input_hash=raw_request_hash,
        provider=adapter.provider_name,
        model=None,
        prompt_version=SELECTION_POLICY_VERSION,
        schema_version=FORMAT_POLICY_VERSION,
        deterministic_artifact_key=f"subtitle-source:{raw_request_hash}",
    )


def _reset_pipeline_for_cache_test(
    tmp_path: Path,
    repository: SQLiteStateRepository,
    *,
    job_id: str,
    now: datetime,
) -> None:
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE videos SET pipeline_status = ? WHERE video_id = ?",
            (PipelineStatus.METADATA_READY.value, "video123"),
        )
    _create_and_claim_transcript_job(repository, job_id=job_id, now=now)


def _use_next_canonical_version(
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    original_builder = transcripts_mod.build_canonical_request_hash
    next_normalization_version = "subtitle-normalization-v2"

    def versioned_canonical_hash(
        *,
        source_content_hash: str,
        source_format: SubtitleFormat,
        normalization_version: str = next_normalization_version,
        quality_policy_version: str = QUALITY_POLICY_VERSION,
    ) -> str:
        return original_builder(
            source_content_hash=source_content_hash,
            source_format=source_format,
            normalization_version=normalization_version,
            quality_policy_version=quality_policy_version,
        )

    monkeypatch.setattr(
        transcripts_mod,
        "NORMALIZATION_VERSION",
        next_normalization_version,
    )
    monkeypatch.setattr(
        transcripts_mod,
        "_CANONICAL_PRODUCER_VERSION",
        f"{next_normalization_version}+{QUALITY_POLICY_VERSION}",
    )
    monkeypatch.setattr(
        transcripts_mod,
        "build_canonical_request_hash",
        versioned_canonical_hash,
    )
    return next_normalization_version


def test_first_success_writes_two_artifacts_and_completes_real_sqlite(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"

    service = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    )
    assert isinstance(service, TranscriptProvider)
    result = service.fetch(_video(), ("en",))

    assert isinstance(result, TranscriptReady)
    assert result.artifact.source_type is TranscriptSourceType.MANUAL_SUBTITLE
    assert result.artifact.requested_language == "en"
    assert result.artifact.source_format is SubtitleFormat.JSON3
    assert result.artifact.text_path.startswith("transcripts/video123/")
    assert result.artifact.timed_text_path is not None
    assert (data_root / result.artifact.text_path).read_text(encoding="utf-8")
    assert (data_root / result.artifact.timed_text_path).read_bytes()
    assert repository.get_job("subtitle-job").status is JobStatus.SUCCEEDED
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.TRANSCRIPT_READY
    )
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        artifact_rows = connection.execute(
            "SELECT kind, storage_root, relative_path, content_hash, "
            "retention_class, expires_at FROM artifacts ORDER BY kind"
        ).fetchall()
        provider_row = connection.execute(
            "SELECT status, response_artifact_id FROM provider_calls"
        ).fetchone()
    assert len(artifact_rows) == 2
    assert {row[0] for row in artifact_rows} == {
        "subtitle_source",
        "transcript_canonical",
    }
    assert all(row[1] == "DATA" for row in artifact_rows)
    assert all(row[4] == "LONG_LIVED" and row[5] is None for row in artifact_rows)
    assert provider_row is not None
    assert provider_row[0] == ProviderCallStatus.SUCCEEDED.value
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        cue_texts = [
            str(row[0])
            for row in connection.execute(
                "SELECT cue_text FROM timed_transcript_cues ORDER BY cue_index"
            )
        ]
    database_bytes = (tmp_path / "state.sqlite3").read_bytes()
    # The provider URL and the raw subtitle payload are never persisted.
    assert b"api/timedtext" not in database_bytes
    assert (FIXTURES / "manual_en.json3").read_bytes() not in database_bytes
    assert b"tStartMs" not in database_bytes
    # The verified cue text that *is* present is the trusted cue-level
    # authority, not a copy of the provider response.
    assert cue_texts
    assert cue_texts[0].encode() in database_bytes


def test_sqlite_repository_satisfies_static_and_runtime_transcript_wiring(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)

    def accept_repository(value: TranscriptRepository) -> TranscriptRepository:
        return value

    assert accept_repository(repository) is repository
    assert isinstance(repository, TranscriptRepository)


def test_empty_language_preferences_are_config_invalid_before_network(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, handle = _bound_adapter(_load_json("info_tracks.json"), opener)

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=tmp_path / "data",
            job_id="subtitle-job",
        ).fetch(_video(), ())

    assert exc_info.value.error.code is ErrorCode.CONFIG_INVALID
    assert handle.calls == []
    assert opener.calls == 0


@pytest.mark.parametrize("existing_state", ["pending", "retry_not_due"])
def test_existing_unavailable_provider_call_is_checked_before_any_network(
    tmp_path: Path,
    existing_state: str,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, handle = _bound_adapter(_load_json("info_tracks.json"), opener)
    request = _provider_request_for(adapter)
    repository.reserve_provider_call(
        request,
        owner="competing-worker",
        lease_until=NOW + td(minutes=5),
        available_at=NOW,
        now=NOW,
    )
    if existing_state == "retry_not_due":
        repository.fail_provider_call(
            request.request_hash,
            owner="competing-worker",
            retryable=True,
            available_at=NOW + td(minutes=5),
            error_code=ErrorCode.TRANSIENT_NETWORK,
            error_message="safe retryable provider failure",
            now=NOW,
        )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=tmp_path / "data",
            job_id="subtitle-job",
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.PROVIDER_UNAVAILABLE
    assert exc_info.value.error.retryable is True
    assert handle.calls == []
    assert opener.calls == 0


def _assert_exception_graph_is_redacted(
    error: BaseException,
    *,
    forbidden: tuple[str, ...],
) -> None:
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        rendered = "".join(
            traceback.format_exception(
                type(current),
                current,
                current.__traceback__,
                chain=False,
            )
        )
        retained = (
            str(current),
            repr(current.args),
            repr(vars(current)),
            rendered,
        )
        for value in forbidden:
            assert all(value not in payload for payload in retained)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)


def test_adapter_directory_error_is_redacted_through_service_exception_graph(
    tmp_path: Path,
) -> None:
    marker = "PRIVATE_DIRECTORY_ERROR_MARKER_8A19F"
    private_url = "https://private.invalid/timedtext?token=secret"
    private_path = "/Users/example/private/subtitle.json3"
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, handle = _bound_adapter(
        DownloadError(
            f"HTTP Error 403: Forbidden {marker} {private_url} {private_path}"
        ),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=tmp_path / "data",
            job_id="subtitle-job",
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.PERMISSION_DENIED
    assert exc_info.value.error.retryable is False
    assert exc_info.value.error.stage is ProcessingStage.TRANSCRIPT
    assert exc_info.value.error.video_id == "video123"
    assert len(handle.calls) == 1
    assert opener.calls == 0
    _assert_exception_graph_is_redacted(
        exc_info.value,
        forbidden=(marker, private_url, private_path),
    )


def test_recovered_invalid_raw_file_does_not_leak_through_service_exception_chain(
    tmp_path: Path,
) -> None:
    marker = "PRIVATE_NESTED_SUBTITLE_MARKER_4B670"
    raw = f'{{"events":[{{"segs":[{{"utf8":"{marker}"}}]}}]'.encode()
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener(raw)
    payload = _load_json("info_tracks.json")
    payload["subtitles"]["en"] = [payload["subtitles"]["en"][0]]
    payload["automatic_captions"] = {}
    adapter, _ = _bound_adapter(payload, opener)
    raw_request_hash = build_raw_request_hash(
        video_id="video123",
        language_preferences=("en",),
        provider=adapter.provider_name,
        provider_version=adapter.provider_version,
        refresh_generation=0,
    )
    metadata = transcripts_mod._SourceMetadata(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="en",
        actual_language="en",
        source_format=SubtitleFormat.JSON3,
    )
    relative_path = transcripts_mod._source_relative_path(
        video_id="video123",
        raw_request_hash=raw_request_hash,
        metadata=metadata,
    )
    data_root = tmp_path / "data"
    raw_path = data_root / relative_path
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(raw)

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="subtitle-job",
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    _assert_exception_graph_is_redacted(
        exc_info.value,
        forbidden=(marker, str(raw), str(raw_path), "api/timedtext"),
    )


def test_verified_cache_hit_uses_empty_stage_completion_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="cache-job",
        now=cache_now,
    )
    network_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("network must not be used on cache hit"),
        opener,
    )
    monkeypatch.setattr(
        transcripts_mod,
        "normalize_subtitle",
        lambda body, source_format: pytest.fail(
            "normalization must not repeat on verified cache hit"
        ),
    )

    cached = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="cache-job",
        now=cache_now,
    ).fetch(_video(), ("en",))

    assert isinstance(cached, TranscriptReady)
    assert cached.artifact == first.artifact
    assert opener.calls == network_calls_before
    assert handle.calls == []
    assert repository.get_job("cache-job").status is JobStatus.SUCCEEDED
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.TRANSCRIPT_READY
    )


def test_explicit_refresh_generation_reenumerates_and_uses_a_new_path(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)

    refresh_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="refresh-job",
        now=refresh_now,
    )
    network_before = opener.calls
    adapter, handle = _bound_adapter(_load_json("info_tracks.json"), opener)
    refreshed = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="refresh-job",
        now=refresh_now,
        refresh_generation=1,
    ).fetch(_video(), ("en",))

    assert isinstance(refreshed, TranscriptReady)
    assert handle.calls
    assert opener.calls == network_before + 1
    assert refreshed.artifact.text_path != first.artifact.text_path
    assert refreshed.artifact.timed_text_path != first.artifact.timed_text_path


def test_missing_current_canonical_is_rebuilt_from_verified_raw_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    old_raw_path = data_root / first.artifact.timed_text_path
    old_canonical_path = data_root / first.artifact.text_path
    next_normalization_version = _use_next_canonical_version(monkeypatch)

    rebuild_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="canonical-rebuild-job",
        now=rebuild_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("canonical rebuild must not enumerate tracks"),
        opener,
    )
    rebuilt = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="canonical-rebuild-job",
        now=rebuild_now,
    ).fetch(_video(), ("en",))

    assert isinstance(rebuilt, TranscriptReady)
    assert handle.calls == []
    assert opener.calls == body_calls_before
    assert rebuilt.artifact.timed_text_path == first.artifact.timed_text_path
    assert rebuilt.artifact.text_path != first.artifact.text_path
    assert rebuilt.artifact.normalization_version == next_normalization_version
    assert old_raw_path.exists()
    assert old_canonical_path.exists()
    assert (data_root / rebuilt.artifact.text_path).exists()
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        artifact_rows = connection.execute(
            "SELECT kind, job_id, artifact_key, relative_path "
            "FROM artifacts ORDER BY created_at, artifact_id"
        ).fetchall()
    assert len(artifact_rows) == 3
    raw_rows = [row for row in artifact_rows if row[0] == "subtitle_source"]
    canonical_rows = [
        row for row in artifact_rows if row[0] == "transcript_canonical"
    ]
    assert len(raw_rows) == 1
    assert raw_rows[0][1] == "subtitle-job"
    assert len(canonical_rows) == 2
    assert {row[1] for row in canonical_rows} == {
        "subtitle-job",
        "canonical-rebuild-job",
    }

    repeat_now = NOW + td(minutes=40)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="canonical-repeat-job",
        now=repeat_now,
    )
    adapter, repeat_handle = _bound_adapter(
        DownloadError("rebuilt canonical cache must not enumerate tracks"),
        opener,
    )
    monkeypatch.setattr(
        transcripts_mod,
        "normalize_subtitle",
        lambda body, source_format: pytest.fail(
            "normalization must not repeat after canonical rebuild"
        ),
    )
    repeated = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="canonical-repeat-job",
        now=repeat_now,
    ).fetch(_video(), ("en",))

    assert isinstance(repeated, TranscriptReady)
    assert repeated.artifact == rebuilt.artifact
    assert repeat_handle.calls == []
    assert opener.calls == body_calls_before


def test_invalid_utf8_canonical_cache_is_redacted_without_network(
    tmp_path: Path,
) -> None:
    marker = "PRIVATE_CANONICAL_UTF8_MARKER_B640C"
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    canonical_path = data_root / first.artifact.text_path
    invalid_body = marker.encode() + b"\xff"
    canonical_path.write_bytes(invalid_body)
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE artifacts SET content_hash = ? WHERE kind = ?",
            (
                hashlib.sha256(invalid_body).hexdigest(),
                "transcript_canonical",
            ),
        )

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="invalid-canonical-utf8-job",
        now=cache_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("invalid canonical UTF-8 must not trigger network repair"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="invalid-canonical-utf8-job",
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == body_calls_before
    _assert_exception_graph_is_redacted(
        exc_info.value,
        forbidden=(marker, repr(invalid_body), str(canonical_path)),
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "tampered",
        "provider_metadata",
        "model_metadata",
        "producer_metadata",
        "path_metadata",
        "format_metadata",
    ],
)
def test_invalid_raw_cache_still_fails_closed_during_canonical_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    assert first.artifact.timed_text_path is not None
    raw_path = data_root / first.artifact.timed_text_path
    _use_next_canonical_version(monkeypatch)
    if mutation == "missing":
        raw_path.unlink()
    elif mutation == "tampered":
        raw_path.write_bytes(b"tampered raw subtitle body")
    elif mutation == "provider_metadata":
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                "UPDATE artifacts SET provider = ? WHERE kind = ?",
                ("unexpected-provider", "subtitle_source"),
            )
    elif mutation == "model_metadata":
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                "UPDATE artifacts SET model = ? WHERE kind = ?",
                ("unexpected-model", "subtitle_source"),
            )
    elif mutation == "producer_metadata":
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                "UPDATE artifacts SET producer_version = ? WHERE kind = ?",
                ("unexpected-producer", "subtitle_source"),
            )
    elif mutation == "path_metadata":
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                "UPDATE artifacts SET relative_path = ? WHERE kind = ?",
                (
                    f"transcripts/video123/wrong-request/{raw_path.name}",
                    "subtitle_source",
                ),
            )
    else:
        raw_request_hash = build_raw_request_hash(
            video_id="video123",
            language_preferences=("en",),
            provider=adapter.provider_name,
            provider_version=adapter.provider_version,
            refresh_generation=0,
        )
        vtt_metadata = transcripts_mod._SourceMetadata(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            requested_language="en",
            actual_language="en",
            source_format=SubtitleFormat.VTT,
        )
        vtt_relative_path = transcripts_mod._source_relative_path(
            video_id="video123",
            raw_request_hash=raw_request_hash,
            metadata=vtt_metadata,
        )
        raw_path.rename(data_root / vtt_relative_path)
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                "UPDATE artifacts SET relative_path = ? WHERE kind = ?",
                (vtt_relative_path, "subtitle_source"),
            )

    rebuild_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id=f"invalid-raw-{mutation}-job",
        now=rebuild_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("invalid raw cache must not trigger network repair"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id=f"invalid-raw-{mutation}-job",
            now=rebuild_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == body_calls_before


def test_raw_metadata_requested_language_must_match_current_ordered_preferences(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    assert first.artifact.timed_text_path is not None
    raw_request_hash = build_raw_request_hash(
        video_id="video123",
        language_preferences=("en",),
        provider=adapter.provider_name,
        provider_version=adapter.provider_version,
        refresh_generation=0,
    )
    tampered_metadata = transcripts_mod._SourceMetadata(
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="fr",
        actual_language="en",
        source_format=SubtitleFormat.JSON3,
    )
    tampered_relative_path = transcripts_mod._source_relative_path(
        video_id="video123",
        raw_request_hash=raw_request_hash,
        metadata=tampered_metadata,
    )
    original_path = data_root / first.artifact.timed_text_path
    tampered_path = data_root / tampered_relative_path
    original_path.rename(tampered_path)
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE artifacts SET relative_path = ? WHERE kind = ?",
            (tampered_relative_path, "subtitle_source"),
        )
    _use_next_canonical_version(monkeypatch)

    rebuild_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="requested-language-mismatch-job",
        now=rebuild_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("provenance mismatch must not trigger network repair"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="requested-language-mismatch-job",
            now=rebuild_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == body_calls_before
    assert repository.get_job("requested-language-mismatch-job").status is JobStatus.RUNNING
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


@pytest.mark.parametrize("artifact_kind", ["raw", "canonical"])
def test_indexed_cache_symlink_escape_is_local_resource_without_network(
    tmp_path: Path,
    artifact_kind: str,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    assert first.artifact.timed_text_path is not None
    relative_path = (
        first.artifact.timed_text_path
        if artifact_kind == "raw"
        else first.artifact.text_path
    )
    cached_path = data_root / relative_path
    cached_body = cached_path.read_bytes()
    outside_path = tmp_path / f"outside-{artifact_kind}.cache"
    outside_path.write_bytes(cached_body)
    cached_path.unlink()
    cached_path.symlink_to(outside_path)

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id=f"{artifact_kind}-symlink-job",
        now=cache_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("cache symlink must not trigger network repair"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id=f"{artifact_kind}-symlink-job",
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == body_calls_before
    assert repository.get_job(f"{artifact_kind}-symlink-job").status is JobStatus.RUNNING
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


@pytest.mark.parametrize(
    "mutation",
    ["model", "provider", "producer", "path", "quality"],
)
def test_canonical_metadata_mismatch_fails_closed_without_network(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    canonical_path = data_root / first.artifact.text_path
    if mutation == "quality":
        name_parts = canonical_path.name.split(".")
        replacement = "n" if name_parts[2] != "n" else "s"
        tampered_path = canonical_path.with_name(
            f"{name_parts[0]}.{name_parts[1]}.{replacement}.{name_parts[3]}"
        )
        canonical_path.rename(tampered_path)
        relative_path = str(tampered_path.relative_to(data_root))
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                "UPDATE artifacts SET relative_path = ? WHERE kind = ?",
                (relative_path, "transcript_canonical"),
            )
    else:
        column, value = {
            "model": ("model", "unexpected-model"),
            "provider": ("provider", "unexpected-provider"),
            "producer": ("producer_version", "unexpected-producer"),
            "path": (
                "relative_path",
                f"transcripts/video123/wrong-request/{canonical_path.name}",
            ),
        }[mutation]
        with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
            connection.execute(
                f"UPDATE artifacts SET {column} = ? WHERE kind = ?",
                (value, "transcript_canonical"),
            )

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id=f"canonical-{mutation}-mismatch-job",
        now=cache_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("canonical metadata mismatch must not trigger network repair"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id=f"canonical-{mutation}-mismatch-job",
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == body_calls_before
    assert (
        repository.get_job(f"canonical-{mutation}-mismatch-job").status
        is JobStatus.RUNNING
    )
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


@pytest.mark.parametrize("mutation", ["missing", "tampered"])
def test_tampered_cached_file_returns_local_resource_and_does_not_advance(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    canonical_path = data_root / first.artifact.text_path
    if mutation == "missing":
        canonical_path.unlink()
    else:
        canonical_path.write_text(
            "tampered transcript content\n",
            encoding="utf-8",
        )

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="tamper-job",
        now=cache_now,
    )
    adapter, handle = _bound_adapter(
        DownloadError("network must not repair corrupt cache"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="tamper-job",
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert handle.calls == []
    assert repository.get_job("tamper-job").status is JobStatus.RUNNING
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


class _RoutingBodyOpener:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, request: object, timeout: float) -> object:
        url = request.full_url
        self.calls.append(url)
        body = (
            (FIXTURES / "manual_en.json3").read_bytes()
            if "kind=asr" in url
            else (FIXTURES / "malformed.json3").read_bytes()
        )
        return _Response(body, content_length=len(body))


def test_invalid_manual_candidate_falls_back_to_valid_automatic_candidate(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    payload = _load_json("info_tracks.json")
    payload["subtitles"]["en"] = [payload["subtitles"]["en"][0]]
    payload["automatic_captions"] = {
        "en": [payload["automatic_captions"]["en"][0]]
    }
    opener = _RoutingBodyOpener()
    adapter, _ = _adapter_for_info(payload)
    subtitles_mod._bind_test_hooks(
        adapter,
        opener=opener,
        clock=lambda: NOW,
    )

    result = _service(
        adapter=adapter,
        repository=repository,
        data_root=tmp_path / "data",
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))

    assert isinstance(result, TranscriptReady)
    assert result.artifact.source_type is TranscriptSourceType.AUTO_SUBTITLE
    assert len(opener.calls) == 2
    assert "kind=asr" not in opener.calls[0]
    assert "kind=asr" in opener.calls[1]


@pytest.mark.parametrize(
    ("payload", "languages", "reason", "attempted"),
    [
        (
            {"id": "video123", "subtitles": {}, "automatic_captions": {}},
            ("en",),
            TranscriptionReason.NO_TRACKS,
            0,
        ),
        (
            _load_json("info_tracks.json"),
            ("fr",),
            TranscriptionReason.NO_MATCHING_LANGUAGE,
            0,
        ),
    ],
)
def test_no_tracks_and_no_matching_language_are_named_results(
    tmp_path: Path,
    payload: object,
    languages: tuple[str, ...],
    reason: TranscriptionReason,
    attempted: int,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, handle = _bound_adapter(payload, opener)
    service = _service(
        adapter=adapter,
        repository=repository,
        data_root=tmp_path / "data",
        job_id="subtitle-job",
    )

    result = service.fetch(_video(), languages)

    assert isinstance(result, TranscriptionRequired)
    assert result.reason is reason
    assert result.attempted_track_count == attempted
    assert opener.calls == 0
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        provider_status = connection.execute(
            "SELECT status, reservation_owner, lease_until FROM provider_calls"
        ).fetchone()
    assert provider_status == (ProviderCallStatus.FAILED_FINAL.value, None, None)
    directory_calls_before = len(handle.calls)

    repeated = service.fetch(_video(), languages)

    assert isinstance(repeated, TranscriptionRequired)
    assert repeated.reason is reason
    assert repeated.attempted_track_count == 0
    assert len(handle.calls) == directory_calls_before
    assert opener.calls == 0
    assert repository.get_job("subtitle-job").status is JobStatus.RUNNING
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


def test_all_invalid_candidates_return_named_result_after_trying_each(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "malformed.json3").read_bytes())
    payload = _load_json("info_tracks.json")
    payload["subtitles"]["en"] = [payload["subtitles"]["en"][0]]
    payload["automatic_captions"] = {}
    adapter, _ = _bound_adapter(payload, opener)

    result = _service(
        adapter=adapter,
        repository=repository,
        data_root=tmp_path / "data",
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))

    assert isinstance(result, TranscriptionRequired)
    assert result.reason is TranscriptionReason.ALL_CANDIDATES_INVALID
    assert result.attempted_track_count == 1
    assert opener.calls == 1
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        provider_status = connection.execute(
            "SELECT status, last_error_code, last_error_message FROM provider_calls"
        ).fetchone()
    assert provider_status == (
        ProviderCallStatus.FAILED_FINAL.value,
        ErrorCode.INVALID_RESPONSE.value,
        "all subtitle candidates invalid",
    )


def test_recorded_all_invalid_result_is_stable_without_repeating_provider_calls(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "malformed.json3").read_bytes())
    payload = _load_json("info_tracks.json")
    payload["subtitles"]["en"] = [payload["subtitles"]["en"][0]]
    payload["automatic_captions"] = {}
    adapter, handle = _bound_adapter(payload, opener)
    service = _service(
        adapter=adapter,
        repository=repository,
        data_root=tmp_path / "data",
        job_id="subtitle-job",
    )

    first = service.fetch(_video(), ("en",))
    assert isinstance(first, TranscriptionRequired)
    assert first.reason is TranscriptionReason.ALL_CANDIDATES_INVALID
    assert first.attempted_track_count == 1
    directory_calls_before = len(handle.calls)
    body_calls_before = opener.calls

    repeated = service.fetch(_video(), ("en",))

    assert isinstance(repeated, TranscriptionRequired)
    assert repeated.reason is TranscriptionReason.ALL_CANDIDATES_INVALID
    assert repeated.attempted_track_count == 0
    assert repeated.call.provider == first.call.provider
    assert repeated.call.started_at == first.call.started_at
    assert repeated.call.finished_at == first.call.finished_at
    assert len(handle.calls) == directory_calls_before
    assert opener.calls == body_calls_before


def test_non_all_invalid_final_provider_error_replays_exact_persisted_semantics(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, handle = _bound_adapter(_load_json("info_tracks.json"), opener)
    request = _provider_request_for(adapter)
    repository.reserve_provider_call(
        request,
        owner="worker-1",
        lease_until=NOW + td(minutes=5),
        available_at=NOW,
        now=NOW,
    )
    repository.fail_provider_call(
        request.request_hash,
        owner="worker-1",
        retryable=False,
        available_at=NOW,
        error_code=ErrorCode.PERMISSION_DENIED,
        error_message="selected subtitle body access denied",
        now=NOW,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=tmp_path / "data",
            job_id="subtitle-job",
        ).fetch(_video(), ("en",))

    error = exc_info.value.error
    assert error.code is ErrorCode.PERMISSION_DENIED
    assert error.message == "selected subtitle body access denied"
    assert error.retryable is False
    assert error.stage is ProcessingStage.TRANSCRIPT
    assert error.video_id == "video123"
    assert handle.calls == []
    assert opener.calls == 0


class _ConcurrentAdapterProbe:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.enumerate_calls = 0
        self.read_calls = 0
        self.acquired_lease_until: datetime | None = None


class _StaticSubtitleAdapter:
    provider_name = "static-subtitles"
    provider_version = "1"

    def __init__(self, probe: _ConcurrentAdapterProbe) -> None:
        self._probe = probe
        self._call = ProviderCallMetadata(
            provider=self.provider_name,
            provider_version=self.provider_version,
            started_at=NOW,
            finished_at=NOW,
        )
        self._track = SubtitleTrack(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.JSON3,
            name="English",
            url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
            provider_position=0,
        )

    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        with self._probe.lock:
            self._probe.enumerate_calls += 1
        return SubtitleTrackListing(tracks=(self._track,), call=self._call)

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        with self._probe.lock:
            self._probe.read_calls += 1
        return SubtitleReadResult(
            body=(FIXTURES / "manual_en.json3").read_bytes(),
            call=self._call,
        )


class _BarrierSQLiteStateRepository(SQLiteStateRepository):
    def __init__(
        self,
        path: Path,
        *,
        preflight_barrier: threading.Barrier,
        competitor_observed: threading.Event,
        probe: _ConcurrentAdapterProbe,
    ) -> None:
        super().__init__(path)
        self._preflight_barrier = preflight_barrier
        self._competitor_observed = competitor_observed
        self._probe = probe

    def get_provider_call(self, request_hash: str) -> ProviderCallRecord | None:
        self._preflight_barrier.wait(timeout=5)
        record = super().get_provider_call(request_hash)
        self._preflight_barrier.wait(timeout=5)
        return record

    def reserve_provider_call(
        self,
        request: ProviderCallRequest,
        *,
        owner: str,
        lease_until: datetime,
        available_at: datetime,
        now: datetime,
        verified_artifact: VerifiedArtifact | None = None,
    ) -> ProviderReservation:
        reservation = super().reserve_provider_call(
            request,
            owner=owner,
            lease_until=lease_until,
            available_at=available_at,
            now=now,
            verified_artifact=verified_artifact,
        )
        if reservation.acquired:
            with self._probe.lock:
                self._probe.acquired_lease_until = reservation.record.lease_until
            if not self._competitor_observed.wait(timeout=5):
                raise AssertionError("competing reservation was not observed")
        else:
            self._competitor_observed.set()
        return reservation


def test_two_real_sqlite_services_compete_before_any_remote_or_file_side_effect(
    tmp_path: Path,
) -> None:
    _repository_with_transcript_job(tmp_path)
    preflight_barrier = threading.Barrier(2)
    competitor_observed = threading.Event()
    probe = _ConcurrentAdapterProbe()

    def service() -> SubtitleAcquisitionService:
        repository = _BarrierSQLiteStateRepository(
            tmp_path / "state.sqlite3",
            preflight_barrier=preflight_barrier,
            competitor_observed=competitor_observed,
            probe=probe,
        )
        return SubtitleAcquisitionService(
            adapter=_StaticSubtitleAdapter(probe),
            repository=repository,
            data_root=tmp_path / "data",
            context=TranscriptJobContext(
                job_id="subtitle-job",
                owner="worker-1",
                pipeline_version="pipeline-v1",
            ),
            clock=lambda: NOW,
        )

    def run(candidate: SubtitleAcquisitionService) -> object:
        try:
            return candidate.fetch(_video(), ("en",))
        except TranscriptError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(run, (service(), service())))

    ready = tuple(result for result in results if isinstance(result, TranscriptReady))
    errors = tuple(result for result in results if isinstance(result, TranscriptError))
    assert len(ready) == 1, results
    assert len(errors) == 1
    assert errors[0].error.code is ErrorCode.PROVIDER_UNAVAILABLE
    assert errors[0].error.retryable is True
    assert probe.enumerate_calls == 1
    assert probe.read_calls == 1
    assert probe.acquired_lease_until == NOW + td(seconds=300)
    assert len(tuple((tmp_path / "data").rglob("source.*"))) == 1
    assert len(tuple((tmp_path / "data").rglob("canonical.*.txt"))) == 1


def test_files_survive_stage_db_failure_and_next_attempt_repairs_indexes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"

    def fail_after_files(point: str) -> None:
        if point == "stage.after_artifacts":
            raise RuntimeError("injected stage failure")

    monkeypatch.setattr(repository, "_inject_failure", fail_after_files)
    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="subtitle-job",
        ).fetch(_video(), ("en",))
    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert tuple(data_root.rglob("source.*"))
    assert tuple(data_root.rglob("canonical.*.txt"))
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    request = _provider_request_for(adapter)
    provider_record = repository.get_provider_call(request.request_hash)
    assert provider_record is not None
    assert provider_record.status is ProviderCallStatus.FAILED_RETRYABLE
    assert provider_record.reservation_owner is None
    assert provider_record.lease_until is None
    assert provider_record.available_at == NOW

    monkeypatch.setattr(repository, "_inject_failure", lambda point: None)
    repository.fail_job(
        "subtitle-job",
        owner="worker-1",
        error_code=ErrorCode.LOCAL_RESOURCE,
        error_message="stage persistence failed",
        retry_at=NOW + td(seconds=2),
        now=NOW + td(seconds=1),
    )
    retry_now = NOW + td(seconds=2)
    repository.activate_retry_jobs(now=retry_now)
    claimed = repository.claim_next_job(
        owner="worker-1",
        lease_until=retry_now + td(minutes=10),
        now=retry_now,
    )
    assert claimed is not None
    body_calls_before = opener.calls
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)

    recovered = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
        now=retry_now,
    ).fetch(_video(), ("en",))

    assert isinstance(recovered, TranscriptReady)
    assert opener.calls == body_calls_before
    assert repository.get_job("subtitle-job").status is JobStatus.SUCCEEDED
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.TRANSCRIPT_READY
    )
    assert not tuple(path for path in data_root.rglob(".*") if path.is_file())


def test_permission_error_during_atomic_write_is_safe_and_not_indexed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)

    def deny_temp_file(*args: object, **kwargs: object) -> object:
        raise PermissionError("private absolute path /Users/example/secret")

    monkeypatch.setattr(
        transcripts_mod.tempfile,
        "NamedTemporaryFile",
        deny_temp_file,
    )
    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=tmp_path / "data",
            job_id="subtitle-job",
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.PERMISSION_DENIED
    assert "/Users/" not in exc_info.value.error.message
    _assert_exception_graph_is_redacted(
        exc_info.value,
        forbidden=("/Users/example/secret",),
    )
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    request = _provider_request_for(adapter)
    provider_record = repository.get_provider_call(request.request_hash)
    assert provider_record is not None
    assert provider_record.status is ProviderCallStatus.FAILED_FINAL
    assert provider_record.last_error_code == ErrorCode.PERMISSION_DENIED.value
    assert provider_record.reservation_owner is None
    assert provider_record.lease_until is None


class _HostileAdapterBase:
    provider_name = "hostile-subtitles"
    provider_version = "1"

    def __init__(self, marker: str, private_url: str, private_path: str) -> None:
        self._marker = marker
        self._private_url = private_url
        self._private_path = private_path
        self._call = ProviderCallMetadata(
            provider=self.provider_name,
            provider_version=self.provider_version,
            started_at=NOW,
            finished_at=NOW,
        )
        self._track = SubtitleTrack(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.JSON3,
            name="English",
            url="https://www.youtube.com/api/timedtext?v=video123&lang=en&fmt=json3",
            provider_position=0,
        )

    def _raise_hostile_error(self) -> None:
        app_error = AppError(
            code=ErrorCode.RATE_LIMITED,
            message=f"{self._marker} {self._private_url} {self._private_path}",
            retryable=True,
            retry_after_seconds=23,
            video_id="wrong-video",
            stage=ProcessingStage.METADATA,
        )
        try:
            raise RuntimeError(f"nested cause {self._marker}")
        except RuntimeError as cause:
            try:
                raise ValueError(f"nested context {self._private_path}")
            except ValueError:
                raise TranscriptError(app_error) from cause


class _HostileEnumerateAdapter(_HostileAdapterBase):
    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        self._raise_hostile_error()
        raise AssertionError("unreachable")

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        raise AssertionError("body read must not run")


class _HostileReadAdapter(_HostileAdapterBase):
    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing:
        return SubtitleTrackListing(tracks=(self._track,), call=self._call)

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult:
        self._raise_hostile_error()
        raise AssertionError("unreachable")


@pytest.mark.parametrize(
    "adapter_type",
    [_HostileEnumerateAdapter, _HostileReadAdapter],
)
def test_public_adapter_errors_are_rebuilt_at_the_service_boundary(
    tmp_path: Path,
    adapter_type: type[_HostileAdapterBase],
) -> None:
    marker = f"HOSTILE_{adapter_type.__name__}_MARKER_79C2"
    private_url = "https://private.invalid/timedtext?token=hostile"
    private_path = "/Users/example/private/hostile-subtitle.json3"
    repository = _repository_with_transcript_job(tmp_path)
    adapter = adapter_type(marker, private_url, private_path)
    service = SubtitleAcquisitionService(
        adapter=adapter,
        repository=repository,
        data_root=tmp_path / "data",
        context=TranscriptJobContext(
            job_id="subtitle-job",
            owner="worker-1",
            pipeline_version="pipeline-v1",
        ),
        clock=lambda: NOW,
    )

    with pytest.raises(TranscriptError) as exc_info:
        service.fetch(_video(), ("en",))

    error = exc_info.value.error
    assert error.code is ErrorCode.RATE_LIMITED
    assert error.retryable is True
    assert error.retry_after_seconds == 23
    assert error.video_id == "video123"
    assert error.stage is ProcessingStage.TRANSCRIPT
    expected_message = (
        "subtitle adapter rate limited during track enumeration"
        if adapter_type is _HostileEnumerateAdapter
        else "subtitle adapter rate limited during body read"
    )
    assert error.message == expected_message
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    _assert_exception_graph_is_redacted(
        exc_info.value,
        forbidden=(marker, private_url, private_path, "wrong-video"),
    )
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        provider_row = connection.execute(
            "SELECT last_error_code, last_error_message FROM provider_calls"
        ).fetchone()
    assert provider_row == (error.code.value, error.message)
    database_bytes = (tmp_path / "state.sqlite3").read_bytes()
    assert all(
        value.encode() not in database_bytes
        for value in (marker, private_url, private_path, "wrong-video")
    )


@pytest.mark.parametrize("mutation", ["source_type", "actual_language"])
def test_raw_cache_provenance_is_bound_to_the_provider_response_record(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    assert first.artifact.timed_text_path is not None
    raw_request_hash = build_raw_request_hash(
        video_id="video123",
        language_preferences=("en",),
        provider=adapter.provider_name,
        provider_version=adapter.provider_version,
        refresh_generation=0,
    )
    tampered_metadata = transcripts_mod._SourceMetadata(
        source_type=(
            TranscriptSourceType.AUTO_SUBTITLE
            if mutation == "source_type"
            else TranscriptSourceType.MANUAL_SUBTITLE
        ),
        requested_language="en",
        actual_language="en-US" if mutation == "actual_language" else "en",
        source_format=SubtitleFormat.JSON3,
    )
    tampered_relative_path = transcripts_mod._source_relative_path(
        video_id="video123",
        raw_request_hash=raw_request_hash,
        metadata=tampered_metadata,
    )
    original_path = data_root / first.artifact.timed_text_path
    original_path.rename(data_root / tampered_relative_path)
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE artifacts SET relative_path = ? WHERE kind = ?",
            (tampered_relative_path, "subtitle_source"),
        )

    cache_now = NOW + td(minutes=20)
    job_id = f"raw-{mutation}-provenance-job"
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id=job_id,
        now=cache_now,
    )
    body_calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("raw provenance failure must not trigger network"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id=job_id,
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == body_calls_before
    assert repository.get_job(job_id).status is JobStatus.RUNNING
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


def test_raw_cache_must_match_the_succeeded_provider_response_artifact(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE provider_calls SET response_artifact_id = ?",
            ("forged-response-artifact",),
        )

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="response-binding-job",
        now=cache_now,
    )
    calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("response binding failure must not trigger network"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="response-binding-job",
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == calls_before


def test_canonical_rolling_flag_is_bound_to_its_production_record(
    tmp_path: Path,
) -> None:
    repository = _repository_with_transcript_job(tmp_path)
    opener = _BodyOpener((FIXTURES / "manual_en.json3").read_bytes())
    adapter, _ = _bound_adapter(_load_json("info_tracks.json"), opener)
    data_root = tmp_path / "data"
    first = _service(
        adapter=adapter,
        repository=repository,
        data_root=data_root,
        job_id="subtitle-job",
    ).fetch(_video(), ("en",))
    assert isinstance(first, TranscriptReady)
    canonical_path = data_root / first.artifact.text_path
    name_parts = canonical_path.name.split(".")
    assert "r" not in name_parts[2]
    forged_flags = f"r{name_parts[2]}"
    tampered_path = canonical_path.with_name(
        f"{name_parts[0]}.{name_parts[1]}.{forged_flags}.{name_parts[3]}"
    )
    canonical_path.rename(tampered_path)
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        connection.execute(
            "UPDATE artifacts SET relative_path = ? WHERE kind = ?",
            (
                str(tampered_path.relative_to(data_root)),
                "transcript_canonical",
            ),
        )

    cache_now = NOW + td(minutes=20)
    _reset_pipeline_for_cache_test(
        tmp_path,
        repository,
        job_id="rolling-provenance-job",
        now=cache_now,
    )
    calls_before = opener.calls
    adapter, handle = _bound_adapter(
        DownloadError("quality provenance failure must not trigger network"),
        opener,
    )

    with pytest.raises(TranscriptError) as exc_info:
        _service(
            adapter=adapter,
            repository=repository,
            data_root=data_root,
            job_id="rolling-provenance-job",
            now=cache_now,
        ).fetch(_video(), ("en",))

    assert exc_info.value.error.code is ErrorCode.LOCAL_RESOURCE
    assert exc_info.value.error.retryable is False
    assert handle.calls == []
    assert opener.calls == calls_before
    assert repository.get_job("rolling-provenance-job").status is JobStatus.RUNNING
    assert (
        repository.get_video("video123").pipeline_status
        is PipelineStatus.METADATA_READY
    )


class _CountingRuns(Sequence[Mapping[str, str]]):
    def __init__(self, count: int, *, text: str = "x") -> None:
        self._count = count
        self._text = text
        self.consumed = 0

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, index: int) -> Mapping[str, str]:
        if index < 0 or index >= self._count:
            raise IndexError
        self.consumed += 1
        return {"text": self._text}


class _CountingBuckets(Mapping[str, list[dict[str, str]]]):
    def __init__(self, count: int) -> None:
        self._count = count
        self.consumed = 0

    def __len__(self) -> int:
        return self._count

    def __iter__(self) -> Iterator[str]:
        for index in range(self._count):
            self.consumed += 1
            yield f"en-{index}"

    def __getitem__(self, key: str) -> list[dict[str, str]]:
        return []


def _streaming_directory_payload(
    *,
    subtitles: Mapping[str, object],
) -> dict[str, object]:
    return {
        "id": "video123",
        "subtitles": subtitles,
        "automatic_captions": {},
    }


def test_directory_key_names_are_bounded_sorted_and_never_read_values() -> None:
    names = dict.fromkeys(("Bravo_2", "Alpha", "Bravo_2"))

    assert subtitles_mod._directory_key_names(names) == ("Alpha", "Bravo_2")

    too_many = dict.fromkeys(tuple(f"Key{index:02d}" for index in range(17)))
    assert subtitles_mod._directory_key_names(too_many) is None

    invalid = dict.fromkeys(("Alpha", object()))
    assert subtitles_mod._directory_key_names(invalid) is None


def test_track_name_runs_stop_at_the_first_frozen_boundary_overflow() -> None:
    boundary_runs = _CountingRuns(1_000)
    boundary_payload = _directory_payload(
        [
            {
                "ext": "json3",
                "name": {"runs": boundary_runs},
                "url": _url_with_length(80),
            }
        ]
    )
    at_boundary, _ = _adapter_for_info(boundary_payload)

    listing = at_boundary.enumerate_tracks("video123")

    assert len(listing.tracks) == 1
    assert len(listing.tracks[0].name) == 1_000
    assert boundary_runs.consumed == 1_000

    oversized_runs = _CountingRuns(500_000)
    oversized_payload = _directory_payload(
        [
            {
                "ext": "json3",
                "name": {"runs": oversized_runs},
                "url": _url_with_length(80),
            }
        ]
    )
    oversized, _ = _adapter_for_info(oversized_payload)

    with pytest.raises(TranscriptError) as exc_info:
        oversized.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert exc_info.value.error.retryable is False
    assert oversized_runs.consumed == 1_001

    empty_runs = _CountingRuns(1_001, text="")
    empty_payload = _directory_payload(
        [
            {
                "ext": "json3",
                "name": {"runs": empty_runs},
                "url": _url_with_length(80),
            }
        ]
    )
    empty, _ = _adapter_for_info(empty_payload)

    with pytest.raises(TranscriptError) as empty_exc:
        empty.enumerate_tracks("video123")

    assert empty_exc.value.error.code is ErrorCode.INVALID_RESPONSE
    assert empty_runs.consumed == 1_001


def test_empty_language_buckets_stop_at_the_first_track_limit_overflow() -> None:
    boundary_buckets = _CountingBuckets(512)
    boundary, _ = _adapter_for_info(
        _streaming_directory_payload(subtitles=boundary_buckets)
    )

    assert boundary.enumerate_tracks("video123").tracks == ()
    assert boundary_buckets.consumed == 512

    oversized_buckets = _CountingBuckets(200_000)
    oversized, _ = _adapter_for_info(
        _streaming_directory_payload(subtitles=oversized_buckets)
    )

    with pytest.raises(TranscriptError) as exc_info:
        oversized.enumerate_tracks("video123")

    assert exc_info.value.error.code is ErrorCode.INVALID_RESPONSE
    assert exc_info.value.error.retryable is False
    assert oversized_buckets.consumed == 513


def test_nested_metadata_iteration_errors_are_safe_and_fail_closed() -> None:
    marker = "PRIVATE_ITERATION_MARKER_6D30"

    class FailingRuns(_CountingRuns):
        def __getitem__(self, index: int) -> Mapping[str, str]:
            if index == 2:
                raise RuntimeError(marker)
            return super().__getitem__(index)

    runs = FailingRuns(10)
    runs_payload = _directory_payload(
        [
            {
                "ext": "json3",
                "name": {"runs": runs},
                "url": _url_with_length(80),
            }
        ]
    )
    runs_adapter, _ = _adapter_for_info(runs_payload)

    with pytest.raises(TranscriptError) as runs_exc:
        runs_adapter.enumerate_tracks("video123")

    assert runs_exc.value.error.code is ErrorCode.INVALID_RESPONSE
    assert runs_exc.value.error.retryable is False
    _assert_exception_graph_is_redacted(runs_exc.value, forbidden=(marker,))

    class FailingBuckets(_CountingBuckets):
        def __iter__(self) -> Iterator[str]:
            yield "en-0"
            raise RuntimeError(marker)

    buckets_adapter, _ = _adapter_for_info(
        _streaming_directory_payload(subtitles=FailingBuckets(10))
    )

    with pytest.raises(TranscriptError) as buckets_exc:
        buckets_adapter.enumerate_tracks("video123")

    assert buckets_exc.value.error.code is ErrorCode.INVALID_RESPONSE
    assert buckets_exc.value.error.retryable is False
    _assert_exception_graph_is_redacted(buckets_exc.value, forbidden=(marker,))
