"""Pure subtitle selection, normalization, quality, and cache policy tests."""

from __future__ import annotations

import json

import pytest

from youtube_intel.domain import (
    SubtitleFormat,
    TranscriptQualityFlag,
    TranscriptSourceType,
)
from youtube_intel.transcripts import (
    QUALITY_POLICY_VERSION,
    SUBTITLE_QUALITY_POLICY,
    InvalidSubtitleCandidate,
    InvalidSubtitleReason,
    SubtitleQualityMetrics,
    SubtitleTrack,
    build_canonical_request_hash,
    build_raw_request_hash,
    normalize_subtitle,
    rank_subtitle_candidates,
    validate_subtitle_quality,
)


def _track(
    *,
    source_type: TranscriptSourceType,
    language: str,
    source_format: SubtitleFormat = SubtitleFormat.JSON3,
    name: str = "",
    position: int = 0,
) -> SubtitleTrack:
    return SubtitleTrack(
        source_type=source_type,
        language=language,
        source_format=source_format,
        name=name,
        url=f"https://example.invalid/{position}",
        provider_position=position,
    )


def test_manual_candidates_globally_precede_automatic_candidates() -> None:
    tracks = (
        _track(
            source_type=TranscriptSourceType.AUTO_SUBTITLE,
            language="zh-CN",
            position=0,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            position=1,
        ),
        _track(
            source_type=TranscriptSourceType.AUTO_SUBTITLE,
            language="en",
            position=2,
        ),
    )

    ranked = rank_subtitle_candidates(tracks, ("zh-CN", "en"))

    assert [
        (item.track.source_type, item.track.language, item.requested_language)
        for item in ranked
    ] == [
        (TranscriptSourceType.MANUAL_SUBTITLE, "en", "en"),
        (TranscriptSourceType.AUTO_SUBTITLE, "zh-CN", "zh-CN"),
        (TranscriptSourceType.AUTO_SUBTITLE, "en", "en"),
    ]


def test_language_matching_is_case_insensitive_with_exact_base_variant_order() -> None:
    tracks = (
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="ZH_tw",
            position=0,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="zh",
            position=1,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="zh-CN",
            position=2,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="zh-Hans",
            position=3,
        ),
    )

    ranked = rank_subtitle_candidates(tracks, ("ZH_cn",))

    assert [item.track.language for item in ranked] == [
        "zh-CN",
        "zh",
        "zh-Hans",
        "ZH_tw",
    ]
    assert [item.match_rank for item in ranked] == [0, 1, 2, 2]
    assert ranked[-1].track.language == "ZH_tw"


def test_format_name_and_provider_position_are_stable_tiebreakers() -> None:
    tracks = (
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.SRT,
            name="B track",
            position=0,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.VTT,
            name="A track",
            position=1,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.JSON3,
            name="beta",
            position=2,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.JSON3,
            name=" Alpha ",
            position=4,
        ),
        _track(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format=SubtitleFormat.JSON3,
            name="alpha",
            position=3,
        ),
    )

    ranked = rank_subtitle_candidates(tracks, ("en",))

    assert [
        (item.track.source_format, item.track.name, item.track.provider_position)
        for item in ranked
    ] == [
        (SubtitleFormat.JSON3, "alpha", 3),
        (SubtitleFormat.JSON3, " Alpha ", 4),
        (SubtitleFormat.JSON3, "beta", 2),
        (SubtitleFormat.VTT, "A track", 1),
        (SubtitleFormat.SRT, "B track", 0),
    ]


def test_subtitle_track_rejects_unfrozen_format_values() -> None:
    with pytest.raises(ValueError, match="source_format"):
        SubtitleTrack(
            source_type=TranscriptSourceType.MANUAL_SUBTITLE,
            language="en",
            source_format="json3",  # type: ignore[arg-type]
            name="English",
            url="https://example.invalid/track",
            provider_position=0,
        )


def test_unmatched_languages_are_excluded_without_rewriting_actual_language() -> None:
    track = _track(
        source_type=TranscriptSourceType.AUTO_SUBTITLE,
        language="pt_BR",
    )

    assert rank_subtitle_candidates((track,), ("en",)) == ()
    ranked = rank_subtitle_candidates((track,), ("PT-br",))
    assert ranked[0].track.language == "pt_BR"
    assert ranked[0].requested_language == "PT-br"


def test_json3_normalization_allows_bom_decodes_entities_once_and_uses_nfc() -> None:
    payload = {
        "events": [
            {
                "segs": [
                    {
                        "utf8": (
                            "Speaker: Cafe\u0301 &amp;lt;tag&amp;gt; "
                            "contains enough meaningful subtitle text."
                        )
                    }
                ]
            }
        ]
    }
    raw = b"\xef\xbb\xbf" + json.dumps(payload).encode()

    normalized = normalize_subtitle(raw, SubtitleFormat.JSON3)

    assert normalized.text == (
        "Speaker: Café &lt;tag&gt; contains enough meaningful subtitle text.\n"
    )
    assert normalized.char_count == len(normalized.text)
    assert normalized.segment_count == 1
    assert normalized.source_byte_count == len(raw)
    assert normalized.source_content_hash
    assert normalized.content_hash


def test_vtt_removes_controls_and_preserves_speaker_semantics() -> None:
    raw = b"""WEBVTT\r
\r
STYLE\r
::cue { color: lime }\r
\r
NOTE this block is ignored\r
secret control text\r
\r
cue-one\r
00:00:00.000 --> 00:00:03.000 align:start\r
<v Alice><i>Hello &amp; welcome to this detailed subtitle segment.</i></v>\r
"""

    normalized = normalize_subtitle(raw, SubtitleFormat.VTT)

    assert normalized.text == (
        "Alice: Hello & welcome to this detailed subtitle segment.\n"
    )
    assert normalized.quality_flags == (
        TranscriptQualityFlag.SPEAKER_LABELS_PRESENT,
    )


def test_srt_removes_timing_and_styles_but_keeps_non_speech_markers() -> None:
    raw = b"""1
00:00:00,000 --> 00:00:01,000
{\\an8}<b>[Music]</b>

2
00:00:01,000 --> 00:00:04,000
This spoken subtitle contains more than twenty useful characters.
"""

    normalized = normalize_subtitle(raw, SubtitleFormat.SRT)

    assert normalized.text == (
        "[Music]\n"
        "This spoken subtitle contains more than twenty useful characters.\n"
    )
    assert normalized.segment_count == 2
    assert normalized.quality_flags == (
        TranscriptQualityFlag.NON_SPEECH_MARKERS_PRESENT,
    )


def test_consecutive_duplicates_and_rolling_prefixes_are_deterministic() -> None:
    texts = [
        "This subtitle has enough content for testing",
        "This subtitle has enough content for testing",
        "This subtitle has enough content for testing today",
    ]
    payload = {"events": [{"segs": [{"utf8": text}]} for text in texts]}

    normalized = normalize_subtitle(
        json.dumps(payload).encode(),
        SubtitleFormat.JSON3,
    )

    assert normalized.text == (
        "This subtitle has enough content for testing\n"
        "today\n"
    )
    assert normalized.segment_count == 2
    assert normalized.quality_flags == (
        TranscriptQualityFlag.ROLLING_CUES_DEDUPED,
    )


@pytest.mark.parametrize(
    ("source_format", "raw"),
    [
        (SubtitleFormat.JSON3, b'{"events": {"not": "a list"}}'),
        (
            SubtitleFormat.VTT,
            b"WEBVTT\n\nnot-a-time-line\nThis is not a valid cue.\n",
        ),
        (
            SubtitleFormat.VTT,
            b"WEBVTTBROKEN\n\n00:00:00.000 --> 00:00:02.000\nInvalid header.\n",
        ),
        (
            SubtitleFormat.SRT,
            b"1\nnot-a-time-line\nThis is not a valid cue.\n",
        ),
    ],
)
def test_malformed_supported_formats_fail_closed(
    source_format: SubtitleFormat,
    raw: bytes,
) -> None:
    with pytest.raises(InvalidSubtitleCandidate) as exc_info:
        normalize_subtitle(raw, source_format)
    assert exc_info.value.reason is InvalidSubtitleReason.MALFORMED
    assert raw.decode(errors="ignore") not in str(exc_info.value)


def test_invalid_utf8_is_rejected_without_replacement_decode() -> None:
    with pytest.raises(InvalidSubtitleCandidate) as exc_info:
        normalize_subtitle(b"\xff\xfe\xfa", SubtitleFormat.SRT)
    assert exc_info.value.reason is InvalidSubtitleReason.INVALID_UTF8


def _quality_metrics(**overrides: int) -> SubtitleQualityMetrics:
    values = {
        "raw_byte_count": 1_000,
        "canonical_code_points": 100,
        "segment_count": 5,
        "semantic_character_count": 80,
        "replacement_character_count": 0,
        "non_whitespace_character_count": 80,
        "input_character_count": 100,
        "removed_character_count": 0,
        "canonical_byte_count": 100,
    }
    values.update(overrides)
    return SubtitleQualityMetrics(**values)


@pytest.mark.parametrize(
    ("valid_metrics", "invalid_metrics", "reason"),
    [
        (
            _quality_metrics(raw_byte_count=5_000_000, canonical_byte_count=50_000),
            _quality_metrics(raw_byte_count=5_000_001, canonical_byte_count=50_001),
            InvalidSubtitleReason.RESOURCE_LIMIT,
        ),
        (
            _quality_metrics(canonical_code_points=1_000_000),
            _quality_metrics(canonical_code_points=1_000_001),
            InvalidSubtitleReason.RESOURCE_LIMIT,
        ),
        (
            _quality_metrics(segment_count=100_000),
            _quality_metrics(segment_count=100_001),
            InvalidSubtitleReason.RESOURCE_LIMIT,
        ),
        (
            _quality_metrics(semantic_character_count=20),
            _quality_metrics(semantic_character_count=19),
            InvalidSubtitleReason.QUALITY,
        ),
        (
            _quality_metrics(
                replacement_character_count=1,
                non_whitespace_character_count=100,
            ),
            _quality_metrics(
                replacement_character_count=2,
                non_whitespace_character_count=100,
            ),
            InvalidSubtitleReason.QUALITY,
        ),
        (
            _quality_metrics(
                input_character_count=100,
                removed_character_count=79,
            ),
            _quality_metrics(
                input_character_count=100,
                removed_character_count=80,
            ),
            InvalidSubtitleReason.QUALITY,
        ),
        (
            _quality_metrics(
                raw_byte_count=10_000,
                canonical_byte_count=100,
            ),
            _quality_metrics(
                raw_byte_count=10_000,
                canonical_byte_count=99,
            ),
            InvalidSubtitleReason.QUALITY,
        ),
    ],
)
def test_quality_thresholds_accept_boundary_and_reject_first_invalid_value(
    valid_metrics: SubtitleQualityMetrics,
    invalid_metrics: SubtitleQualityMetrics,
    reason: InvalidSubtitleReason,
) -> None:
    validate_subtitle_quality(valid_metrics)
    with pytest.raises(InvalidSubtitleCandidate) as exc_info:
        validate_subtitle_quality(invalid_metrics)
    assert exc_info.value.reason is reason


def test_compression_ratio_is_not_applied_below_ten_thousand_raw_bytes() -> None:
    validate_subtitle_quality(
        _quality_metrics(raw_byte_count=9_999, canonical_byte_count=1)
    )


def test_quality_policy_exposes_the_frozen_v1_limits() -> None:
    assert SUBTITLE_QUALITY_POLICY.max_raw_bytes == 5_000_000
    assert SUBTITLE_QUALITY_POLICY.max_canonical_code_points == 1_000_000
    assert SUBTITLE_QUALITY_POLICY.max_segments == 100_000
    assert SUBTITLE_QUALITY_POLICY.min_semantic_characters == 20
    assert SUBTITLE_QUALITY_POLICY.max_replacement_ratio == 0.01
    assert SUBTITLE_QUALITY_POLICY.max_deduplication_ratio == 0.80
    assert SUBTITLE_QUALITY_POLICY.compression_check_min_raw_bytes == 10_000
    assert SUBTITLE_QUALITY_POLICY.min_compression_ratio == 0.01


def test_request_hashes_are_stable_layered_and_refresh_aware() -> None:
    raw_hash = build_raw_request_hash(
        video_id="video123",
        language_preferences=("zh_CN", "en"),
        provider="yt-dlp",
        provider_version="2026.7.4",
        refresh_generation=0,
    )
    assert raw_hash == build_raw_request_hash(
        video_id="video123",
        language_preferences=("ZH-cn", "en"),
        provider="yt-dlp",
        provider_version="2026.7.4",
        refresh_generation=0,
    )
    assert raw_hash != build_raw_request_hash(
        video_id="video123",
        language_preferences=("en", "zh-CN"),
        provider="yt-dlp",
        provider_version="2026.7.4",
        refresh_generation=0,
    )
    assert raw_hash != build_raw_request_hash(
        video_id="video123",
        language_preferences=("zh-CN", "en"),
        provider="yt-dlp",
        provider_version="2026.7.4",
        refresh_generation=1,
    )

    canonical_hash = build_canonical_request_hash(
        source_content_hash="a" * 64,
        source_format=SubtitleFormat.JSON3,
    )
    assert canonical_hash == build_canonical_request_hash(
        source_content_hash="a" * 64,
        source_format=SubtitleFormat.JSON3,
    )
    assert canonical_hash != build_canonical_request_hash(
        source_content_hash="b" * 64,
        source_format=SubtitleFormat.JSON3,
    )
    assert canonical_hash != build_canonical_request_hash(
        source_content_hash="a" * 64,
        source_format=SubtitleFormat.VTT,
    )
    assert canonical_hash != build_canonical_request_hash(
        source_content_hash="a" * 64,
        source_format=SubtitleFormat.JSON3,
        normalization_version="subtitle-normalization-v2",
    )
    assert canonical_hash != build_canonical_request_hash(
        source_content_hash="a" * 64,
        source_format=SubtitleFormat.JSON3,
        quality_policy_version=f"{QUALITY_POLICY_VERSION}-changed",
    )
