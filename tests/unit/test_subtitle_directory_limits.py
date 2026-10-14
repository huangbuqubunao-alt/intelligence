"""Bounded compatibility tests for yt-dlp subtitle directory shapes."""

from __future__ import annotations

import json

import pytest

from youtube_intel.domain import SubtitleFormat, TranscriptSourceType
from youtube_intel.providers import subtitles as provider_module
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


@pytest.mark.parametrize("raw_count", [4096, 4097, 32768, 32769])
@pytest.mark.parametrize("manual_count", [0, 16384])
def test_translations_still_consume_raw_entry_bound(monkeypatch: pytest.MonkeyPatch, raw_count: int, manual_count: int) -> None:
    manual_count = min(manual_count, raw_count - 1)
    translated = _native_entry(query="&tlang=fr")
    payload = {"id": _VIDEO_ID, "subtitles": {"fr": [translated] * manual_count}, "automatic_captions": {"en": [translated] * (raw_count - manual_count - 1) + [_native_entry()]}}
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    if raw_count <= 32768:
        tracks = adapter.enumerate_tracks(_VIDEO_ID).tracks
        assert len(tracks) == 1 and tracks[0].provider_position == raw_count - 1
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
@pytest.mark.parametrize("prefix_count", [1024, 4500])
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
def test_malformed_translated_entry_is_not_hidden_after_large_valid_translation_prefix(monkeypatch: pytest.MonkeyPatch, extension: str, prefix_count: int, bad_fields: dict[str, object], expected: str) -> None:
    bad = {**_native_entry(extension=extension, query="&tlang=fr"), **bad_fields}
    payload = {"id": _VIDEO_ID, "subtitles": {}, "automatic_captions": {"en": [_native_entry()] + [_native_entry(query="&tlang=fr")] * prefix_count + [bad]}}
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


def test_synthetic_measured_fanout_shape_keeps_all_129_native_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Synthesized from measured aggregate counts, not a signed metadata replay.
    manual = _entries("en")
    automatic = {"en": _entries("en") * 21, "en-orig": _entries("en") * 21}
    for index in range(175):
        entries = _entries("en") * (19 if index < 105 else 18)
        automatic[f"lang-{index}"] = [{**entry, "url": entry["url"] + f"&tlang=lang-{index}"} for entry in entries]
    # Include all five measured field names, the longest measured URL and name
    # sizes, and at least the measured complete catalog byte size. All data is
    # invented; no expiring signed URL or downloaded subtitle is replayed.
    for directory in ({"en": manual}, automatic):
        for language, entries in directory.items():
            entries[:] = [{**entry, "name": "Native subtitle track", "__yt_dlp_client": "web", "impersonate": None,
                           "url": entry["url"] + "&signature=" + "a" * (391 - len(entry["url"]) - len("&signature="))}
                          for entry in entries]
    payload = {"id": _VIDEO_ID, "subtitles": {"en": manual}, "automatic_captions": automatic}
    assert len(manual) + sum(map(len, automatic.values())) == 23086
    assert 10966987 <= _directory_bytes(payload) < 16 * 1024 * 1024
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    tracks = adapter.enumerate_tracks(_VIDEO_ID).tracks
    assert len(tracks) == 129
    assert tracks[0].provider_position == 0
    assert tracks[-1].provider_position == 300
    flattened = manual + [entry for entries in automatic.values() for entry in entries]
    for track in tracks:
        assert track.url == flattened[track.provider_position]["url"]
    assert len(calls) == 1


def _byte_payload(extra: object) -> dict[str, object]:
    return {"id": _VIDEO_ID, "subtitles": {"en": [{**_native_entry(), "extra": extra}]}, "automatic_captions": {}}


def _directory_bytes(payload: dict[str, object]) -> int:
    return len(json.dumps({key: payload[key] for key in ("subtitles", "automatic_captions")}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


@pytest.mark.parametrize("overflow", [0, 1])
def test_full_directory_utf8_byte_boundary_includes_unknown_fields_and_json_escaping(monkeypatch: pytest.MonkeyPatch, overflow: int) -> None:
    payload = _byte_payload('汉"\n')
    payload["subtitles"]["en"][0]["extra"] += "x" * (16 * 1024 * 1024 - _directory_bytes(payload) + overflow)
    assert _directory_bytes(payload) == 16 * 1024 * 1024 + overflow
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    if overflow:
        with pytest.raises(_DirectoryInvalidResponse, match="byte limit"):
            adapter.enumerate_tracks(_VIDEO_ID)
    else:
        assert len(adapter.enumerate_tracks(_VIDEO_ID).tracks) == 1
    assert len(calls) == 1


@pytest.mark.parametrize("overflow", [0, 1])
def test_full_directory_bytes_are_shared_across_sources_and_nested_name_metadata(monkeypatch: pytest.MonkeyPatch, overflow: int) -> None:
    manual = {**_native_entry(), "name": {"simpleText": " Native ", "extra": '汉"\n'}}
    automatic = {**_native_entry(), "name": {"runs": [{"text": " Auto ", "extra": '界"\n'}]}}
    payload = {"id": _VIDEO_ID, "subtitles": {"en": [manual]}, "automatic_captions": {"en": [automatic]}}
    remaining = 16 * 1024 * 1024 - _directory_bytes(payload) + overflow
    manual["name"]["extra"] += "x" * (remaining // 2)
    automatic["name"]["runs"][0]["extra"] += "x" * (remaining - remaining // 2)
    assert _directory_bytes(payload) == 16 * 1024 * 1024 + overflow
    adapter, calls = _no_body_adapter(monkeypatch, payload)
    if overflow:
        with pytest.raises(_DirectoryInvalidResponse, match="byte limit"):
            adapter.enumerate_tracks(_VIDEO_ID)
    else:
        listing = adapter.enumerate_tracks(_VIDEO_ID)
        assert [track.name for track in listing.tracks] == ["Native", "Auto"]
        assert [track.provider_position for track in listing.tracks] == [0, 1]
    assert len(calls) == 1


@pytest.mark.parametrize("wrappers", [4, 5])
def test_directory_depth_boundary_in_unknown_translated_metadata(monkeypatch: pytest.MonkeyPatch, wrappers: int) -> None:
    value: object = None
    for _ in range(wrappers):
        value = [value]
    payload = _byte_payload(value)
    payload["subtitles"]["en"][0]["url"] += "&tlang=fr"
    adapter, _ = _no_body_adapter(monkeypatch, payload)
    if wrappers == 4:
        assert adapter.enumerate_tracks(_VIDEO_ID).tracks == ()
    else:
        with pytest.raises(_DirectoryInvalidResponse, match="depth limit"):
            adapter.enumerate_tracks(_VIDEO_ID)


@pytest.mark.parametrize("value", [object(), float("nan"), float("inf"), b"not-json", {1: "bad-key"}, range(3)])
def test_unknown_non_json_directory_metadata_fails_closed(monkeypatch: pytest.MonkeyPatch, value: object) -> None:
    adapter, _ = _no_body_adapter(monkeypatch, _byte_payload(value))
    with pytest.raises(_DirectoryInvalidResponse):
        adapter.enumerate_tracks(_VIDEO_ID)


def test_directory_cycles_are_rejected_without_partial_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    cycle: list[object] = []
    cycle.append(cycle)
    adapter, _ = _no_body_adapter(monkeypatch, _byte_payload(cycle))
    with pytest.raises(_DirectoryInvalidResponse, match="cycle"):
        adapter.enumerate_tracks(_VIDEO_ID)


def _json_nodes(value: object) -> int:
    if isinstance(value, dict):
        return 1 + sum(1 + _json_nodes(item) for item in value.values())
    if isinstance(value, list):
        return 1 + sum(map(_json_nodes, value))
    return 1


@pytest.mark.parametrize("overflow", [0, 1])
def test_directory_node_boundary_counts_each_shared_reference_occurrence(monkeypatch: pytest.MonkeyPatch, overflow: int) -> None:
    payload = _byte_payload([])
    payload["automatic_captions"] = {"en": [{**_native_entry(), "extra": []}]}
    directory = {key: payload[key] for key in ("subtitles", "automatic_captions")}
    # Repeated identity is not a reason to avoid paying the scan cost.
    remaining = 524288 - _json_nodes(directory) + overflow
    payload["subtitles"]["en"][0]["extra"] = [None] * (remaining // 2)
    payload["automatic_captions"]["en"][0]["extra"] = [None] * (remaining - remaining // 2)
    adapter, _ = _no_body_adapter(monkeypatch, payload)
    if overflow:
        with pytest.raises(_DirectoryInvalidResponse, match="node limit"):
            adapter.enumerate_tracks(_VIDEO_ID)
    else:
        assert len(adapter.enumerate_tracks(_VIDEO_ID).tracks) == 2


@pytest.mark.parametrize("elapsed", [4.999, 5.0])
def test_manual_and_automatic_share_monotonic_mapping_deadline(monkeypatch: pytest.MonkeyPatch, elapsed: float) -> None:
    clock = [0.0]
    monkeypatch.setattr(provider_module, "monotonic", lambda: clock[0], raising=False)
    class LaterMapping(dict):
        def items(self):
            clock[0] = elapsed
            return super().items()
    payload = {"id": _VIDEO_ID, "subtitles": {"en": [_native_entry()]}, "automatic_captions": LaterMapping(en=[_native_entry()])}
    adapter, _ = _no_body_adapter(monkeypatch, payload)
    if elapsed < 5:
        assert len(adapter.enumerate_tracks(_VIDEO_ID).tracks) == 2
    else:
        with pytest.raises(_DirectoryInvalidResponse, match="time limit"):
            adapter.enumerate_tracks(_VIDEO_ID)


@pytest.mark.parametrize("bad", [{"url": "https://evil.test/?tlang=fr"}, {"name": "x" * 1001}])
def test_malformed_translation_after_old_4096_boundary_is_still_rejected(monkeypatch: pytest.MonkeyPatch, bad: dict[str, str]) -> None:
    entry = _native_entry(query="&tlang=fr")
    payload = {"id": _VIDEO_ID, "subtitles": {"en": [entry] * 4500 + [{**entry, **bad}]}, "automatic_captions": {}}
    adapter, _ = _no_body_adapter(monkeypatch, payload)
    with pytest.raises(_DirectoryInvalidResponse):
        adapter.enumerate_tracks(_VIDEO_ID)
