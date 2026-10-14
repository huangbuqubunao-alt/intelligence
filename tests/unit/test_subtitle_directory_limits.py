"""Bounded compatibility tests for yt-dlp subtitle directory shapes."""

from __future__ import annotations

import pytest

from youtube_intel.domain import SubtitleFormat, TranscriptSourceType
from youtube_intel.providers.subtitles import (
    _MAX_TRACK_COUNT,
    YtDlpSubtitleAdapter,
    _DirectoryInvalidResponse,
)

_VIDEO_ID = "LPZh9BOjkQs"
_FORMAT_ENTRIES = ("json3", "srv1", "srv2", "srv3", "ttml", "srt", "vtt")


class _Ydl:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def extract_info(self, _url: str, *, download: bool) -> object:
        assert download is False
        return self._payload


def _entries(language: str) -> list[dict[str, str]]:
    return [
        {
            "ext": extension,
            "url": (
                "https://www.youtube.com/api/timedtext"
                f"?fmt={extension}&lang={language}&v={_VIDEO_ID}"
            ),
            "name": language,
        }
        for extension in _FORMAT_ENTRIES
    ]


def _directory_payload(
    *, manual_languages: list[str], automatic_languages: list[str]
) -> dict[str, object]:
    return {
        "id": _VIDEO_ID,
        "subtitles": {language: _entries(language) for language in manual_languages},
        "automatic_captions": {
            language: _entries(language) for language in automatic_languages
        },
    }


def _adapter_for_payload(monkeypatch: pytest.MonkeyPatch, payload: object) -> YtDlpSubtitleAdapter:
    adapter = YtDlpSubtitleAdapter()
    monkeypatch.setattr(adapter, "_ydl_factory", lambda _options: _Ydl(payload))
    return adapter


def test_real_3blue1brown_directory_shape_fits_supported_track_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The bounded upstream metadata shape has 17 manual and 157 automatic
    # language buckets, each with seven formats; three formats are supported.
    payload = _directory_payload(
        manual_languages=["en", *(f"manual-{index:03d}" for index in range(1, 17))],
        automatic_languages=[
            "en",
            "en-orig",
            *(f"auto-{index:03d}" for index in range(2, 157)),
        ],
    )
    adapter = _adapter_for_payload(monkeypatch, payload)

    listing = adapter.enumerate_tracks(_VIDEO_ID)

    assert len(listing.tracks) == 522
    assert sum(
        track.source_type is TranscriptSourceType.MANUAL_SUBTITLE
        for track in listing.tracks
    ) == 51
    assert sum(
        track.source_type is TranscriptSourceType.AUTO_SUBTITLE
        for track in listing.tracks
    ) == 471
    assert {track.source_format for track in listing.tracks} == {
        SubtitleFormat.JSON3,
        SubtitleFormat.VTT,
        SubtitleFormat.SRT,
    }


@pytest.mark.parametrize("translation_query", [
    "tlang=zh-Hans", "tlang=", "tlang=zh-Hans&tlang=en", "%74lang=zh-Hans",
])
def test_provider_translation_is_not_exposed_as_original_subtitle(
    monkeypatch: pytest.MonkeyPatch, translation_query: str,
) -> None:
    payload = _directory_payload(manual_languages=["zh"], automatic_languages=["en", "en-orig", "zh-Hans"])
    for entry in payload["automatic_captions"]["zh-Hans"]:
        entry["url"] += "&" + translation_query
    listing = _adapter_for_payload(monkeypatch, payload).enumerate_tracks(_VIDEO_ID)
    assert {track.language for track in listing.tracks} == {"zh", "en", "en-orig"}
    from youtube_intel.transcripts import rank_subtitle_candidates
    ranked = rank_subtitle_candidates(listing.tracks, ("zh", "en"))
    assert ranked[0].track.source_type is TranscriptSourceType.MANUAL_SUBTITLE
    assert ranked[0].track.language == "zh"


def test_translation_only_directory_has_no_original_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _directory_payload(manual_languages=[], automatic_languages=["zh-Hans"])
    for entry in payload["automatic_captions"]["zh-Hans"]:
        entry["url"] += "&tlang=zh-Hans"
    assert _adapter_for_payload(monkeypatch, payload).enumerate_tracks(_VIDEO_ID).tracks == ()


def test_supported_track_bound_still_rejects_more_than_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language_count = _MAX_TRACK_COUNT // 3 + 1
    payload = _directory_payload(
        manual_languages=[],
        automatic_languages=[f"lang-{index:03d}" for index in range(language_count)],
    )
    adapter = _adapter_for_payload(monkeypatch, payload)

    with pytest.raises(_DirectoryInvalidResponse) as exc_info:
        adapter.enumerate_tracks(_VIDEO_ID)

    assert exc_info.value.error.message == (
        "subtitle track directory exceeds its supported track limit"
    )


def _native_entry(*, extension: str = "json3", query: str = "") -> dict[str, str]:
    return {"ext": extension, "url": f"https://www.youtube.com/api/timedtext?lang=en&v={_VIDEO_ID}" + query, "name": "Native"}


def _no_body_adapter(monkeypatch: pytest.MonkeyPatch, payload: object) -> tuple[YtDlpSubtitleAdapter, list[str]]:
    directory_calls: list[str] = []
    class Directory(_Ydl):
        def extract_info(self, url: str, *, download: bool) -> object:
            directory_calls.append(url)
            return super().extract_info(url, download=download)
    adapter = YtDlpSubtitleAdapter()
    monkeypatch.setattr(adapter, "_ydl_factory", lambda _options: Directory(payload))
    monkeypatch.setattr(adapter, "_opener", lambda *_args: pytest.fail("Enumeration must not read any subtitle body"))
    return adapter, directory_calls


@pytest.mark.parametrize("translation_query", ["&tlang=fr", "&tlang=", "&tlang=fr&tlang=en", "&%74lang=fr"])
def test_native_capacity_excludes_validated_translations_before_counting_and_preserves_positions(monkeypatch: pytest.MonkeyPatch, translation_query: str) -> None:
    translated = _native_entry(query=translation_query)
    manual = [_native_entry(query="&signature=A%2BB&tlangx=fr"), _native_entry(extension="vtt", query="&Tlang=fr")]
    automatic = _native_entry()
    payload = {"id": _VIDEO_ID, "subtitles": {"zh": [translated] * 512 + manual}, "automatic_captions": {"en": [translated] * 512 + [_native_entry(extension="ttml"), automatic]}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    tracks = adapter.enumerate_tracks(_VIDEO_ID).tracks
    assert len(tracks) == 3
    assert [(t.source_type, t.source_format, t.provider_position) for t in tracks] == [
        (TranscriptSourceType.MANUAL_SUBTITLE, SubtitleFormat.JSON3, 512),
        (TranscriptSourceType.MANUAL_SUBTITLE, SubtitleFormat.VTT, 513),
        (TranscriptSourceType.AUTO_SUBTITLE, SubtitleFormat.JSON3, 1027),
    ]
    assert [t.url for t in tracks] == [manual[0]["url"], manual[1]["url"], automatic["url"]]
    assert [t.language for t in tracks] == ["zh", "zh", "en"]
    assert len(calls) == 1


def test_native_capacity_keeps_1024_native_boundary_across_sources_even_with_translations(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"id": _VIDEO_ID, "subtitles": {"en": [_native_entry(query="&tlang=fr")] * 1024 + [_native_entry()] * 512}, "automatic_captions": {"en": [_native_entry()] * 512}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    tracks = adapter.enumerate_tracks(_VIDEO_ID).tracks
    assert len(tracks) == 1024
    assert tracks[0].provider_position == 1024 and tracks[-1].provider_position == 2047
    assert len(calls) == 1
    payload["automatic_captions"]["en"].append(_native_entry())
    with pytest.raises(_DirectoryInvalidResponse) as rejected:
        adapter.enumerate_tracks(_VIDEO_ID)
    assert rejected.value.error.message == "subtitle track directory exceeds its supported track limit"
    assert len(calls) == 2


@pytest.mark.parametrize("raw_count", [4096, 4097])
def test_translations_still_consume_raw_entry_bound(monkeypatch: pytest.MonkeyPatch, raw_count: int) -> None:
    payload = {"id": _VIDEO_ID, "subtitles": {}, "automatic_captions": {"en": [_native_entry(query="&tlang=fr")] * (raw_count - 1) + [_native_entry()]}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    if raw_count == 4096:
        tracks = adapter.enumerate_tracks(_VIDEO_ID).tracks
        assert len(tracks) == 1 and tracks[0].provider_position == 4095
    else:
        with pytest.raises(_DirectoryInvalidResponse) as rejected:
            adapter.enumerate_tracks(_VIDEO_ID)
        assert rejected.value.error.message == "subtitle track directory exceeds its entry limit"
    assert len(calls) == 1


@pytest.mark.parametrize("bucket_count", [512, 513])
def test_translations_still_consume_language_bucket_bound(monkeypatch: pytest.MonkeyPatch, bucket_count: int) -> None:
    payload = {"id": _VIDEO_ID, "subtitles": {}, "automatic_captions": {f"lang-{n}": [_native_entry(query="&tlang=fr")] for n in range(bucket_count)}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    if bucket_count == 512:
        assert adapter.enumerate_tracks(_VIDEO_ID).tracks == ()
    else:
        with pytest.raises(_DirectoryInvalidResponse) as rejected:
            adapter.enumerate_tracks(_VIDEO_ID)
        assert rejected.value.error.message == "subtitle track directory exceeds its language bucket limit"
    assert len(calls) == 1


@pytest.mark.parametrize("extension", ["json3", "ttml"])
@pytest.mark.parametrize(("bad_fields", "expected"), [
    ({"url": "https://evil.test/api/timedtext?tlang=fr"}, "URL"),
    ({"url": "https://user:pass@www.youtube.com/api/timedtext?tlang=fr"}, "URL"),
    ({"url": "https://www.youtube.com/api/timedtext?tlang=fr#fragment"}, "URL"),
    ({"url": "http://www.youtube.com/api/timedtext?tlang=fr"}, "URL"),
    ({"url": "https://www.youtube.com/api/timedtext?tlang=fr&x=" + "x" * 8192}, "URL"),
    ({"url": None}, "URL"),
    ({"name": "x" * 1001}, "name"),
    ({"name": {"unexpected": "value"}}, "name"),
    ({"name": ["invalid"]}, "name"),
    ({"ext": None}, "format"),
])
def test_malformed_translated_entry_is_not_hidden_after_large_valid_translation_prefix(monkeypatch: pytest.MonkeyPatch, extension: str, bad_fields: dict[str, object], expected: str) -> None:
    bad = {**_native_entry(extension=extension, query="&tlang=fr"), **bad_fields}
    payload = {"id": _VIDEO_ID, "subtitles": {}, "automatic_captions": {"en": [_native_entry()] + [_native_entry(query="&tlang=fr")] * 1024 + [bad]}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    with pytest.raises(_DirectoryInvalidResponse) as rejected:
        adapter.enumerate_tracks(_VIDEO_ID)
    assert rejected.value.error.message == f"subtitle track {expected} is invalid"
    assert rejected.value.error.retryable is False
    assert len(calls) == 1


@pytest.mark.parametrize("missing", ["url", "ext"])
def test_missing_member_in_translated_entry_still_invalidates_directory(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    bad = _native_entry(query="&tlang=fr")
    del bad[missing]
    payload = {"id": _VIDEO_ID, "subtitles": {}, "automatic_captions": {"en": [_native_entry()] + [_native_entry(query="&tlang=fr")] * 1024 + [bad]}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    with pytest.raises(_DirectoryInvalidResponse) as rejected:
        adapter.enumerate_tracks(_VIDEO_ID)
    assert rejected.value.error.message == "subtitle track payload is malformed"
    assert len(calls) == 1


@pytest.mark.parametrize("extension", ["json3", "ttml"])
def test_large_translated_only_supported_directory_keeps_empty_listing_but_unsupported_rejects(monkeypatch: pytest.MonkeyPatch, extension: str) -> None:
    payload = {"id": _VIDEO_ID, "subtitles": {}, "automatic_captions": {"en": [_native_entry(extension=extension, query="&tlang=fr")] * 1025}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    if extension == "json3":
        assert adapter.enumerate_tracks(_VIDEO_ID).tracks == ()
    else:
        with pytest.raises(_DirectoryInvalidResponse) as rejected:
            adapter.enumerate_tracks(_VIDEO_ID)
        assert rejected.value.error.message == "subtitle track directory has no supported formats"
    assert len(calls) == 1
