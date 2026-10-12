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
