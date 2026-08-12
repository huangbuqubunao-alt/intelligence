"""Offline unit tests for Obsidian note rendering and stable note identity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import yaml

from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisPoint,
    AnalysisResult,
    AnalysisSkipped,
    AnalysisSkipReason,
    Availability,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    PointKind,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
    SubtitleFormat,
    TranscriptArtifact,
    TranscriptSourceType,
    VideoMetadata,
)
from youtube_intel.notes import (
    NoteRenderingError,
    build_video_note_filename,
    render_video_note,
)

NOW = datetime(2026, 7, 22, 9, 8, 7, 654321, tzinfo=UTC)
VIDEO_ID = "video-123"


def _video(*, title: str = "Café: product / roadmap") -> VideoMetadata:
    return VideoMetadata(
        video_id=VIDEO_ID,
        channel_id="channel-123",
        channel_name="Example Channel",
        title=title,
        description="A concise description.",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 7, 20, 9, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _transcript() -> TranscriptArtifact:
    return TranscriptArtifact(
        video_id=VIDEO_ID,
        language="en",
        source_type=TranscriptSourceType.MANUAL_SUBTITLE,
        requested_language="en",
        source_format=SubtitleFormat.VTT,
        text_path="transcripts/video-123.txt",
        timed_text_path="transcripts/video-123.vtt",
        source_content_hash="a" * 64,
        source_byte_count=100,
        content_hash="b" * 64,
        char_count=100,
        segment_count=3,
        normalization_version="subtitle-normalization-v1",
        provider="fixture",
        created_at=NOW,
    )


def _scoring() -> ScoringOutcome:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8.5,
        reason="Directly useful to product strategy.",
        topics=("product", "strategy"),
        should_summarize=True,
        provider="fixture-scoring",
        model="fixture-model",
        prompt_version="scoring-prompt-v2",
        request_hash="c" * 64,
        output_language="en",
    )
    call = ProviderCallMetadata(
        provider="fixture-scoring",
        model="fixture-model",
        started_at=NOW,
        finished_at=NOW,
    )
    return ScoringOutcome(
        result=result,
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=True,
            model_disagrees=False,
        ),
        call=call,
    )


def _analysis() -> AnalysisCompleted:
    result = AnalysisResult(
        one_sentence_summary="A compact summary.",
        core_points=(
            AnalysisPoint(
                text="The product has a clear user need.",
                kind=PointKind.FACT,
                evidence_ids=("evidence-1",),
            ),
        ),
        product_opportunities=(
            AnalysisPoint(
                text="Test a focused onboarding flow.",
                kind=PointKind.INFERENCE,
                evidence_ids=("evidence-1",),
            ),
        ),
        keywords=("product",),
        evidence=(
            EvidenceExcerpt(
                evidence_id="evidence-1",
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="A verified excerpt.",
            ),
        ),
        provider="fixture-analysis",
        model="fixture-model",
        request_hash="d" * 64,
    )
    return AnalysisCompleted(
        result=result,
        call=ProviderCallMetadata(
            provider="fixture-analysis",
            model="fixture-model",
            started_at=NOW,
            finished_at=NOW,
        ),
    )


def test_filename_is_stable_unicode_safe_and_bounded() -> None:
    filename = build_video_note_filename("CON", VIDEO_ID)

    assert filename == "video-CON--video-123.md"
    assert len(filename.rsplit("--", maxsplit=1)[0].encode("utf-8")) <= 120
    assert build_video_note_filename("Café: product / roadmap", VIDEO_ID) == (
        "Café-product-roadmap--video-123.md"
    )
    assert build_video_note_filename("new title", VIDEO_ID).endswith("--video-123.md")


def test_filename_rejects_invalid_video_identity() -> None:
    with pytest.raises(NoteRenderingError):
        build_video_note_filename("A title", "../video")


def test_rendered_completed_note_has_stable_frontmatter_and_markers() -> None:
    rendered = render_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis(),
        processed_at=NOW,
        pipeline_version="pipeline-v1",
    )

    frontmatter_text, body = rendered.content.split("---\n", maxsplit=2)[1:]
    frontmatter = yaml.safe_load(frontmatter_text)
    assert list(frontmatter) == [
        "type",
        "video_id",
        "title",
        "channel",
        "published",
        "source",
        "language",
        "transcript_source",
        "score",
        "topics",
        "processed_at",
        "pipeline_version",
    ]
    assert frontmatter["type"] == "video"
    assert frontmatter["score"] == 8.5
    assert frontmatter["topics"] == ["product", "strategy"]
    assert frontmatter["processed_at"] == "2026-07-22T09:08:07.654321Z"
    assert rendered.relative_path == "Videos/Café-product-roadmap--video-123.md"
    assert body.count("<!-- youtube-intel:managed:start:v1 -->") == 1
    assert body.count("<!-- youtube-intel:managed:end:v1 -->") == 1
    assert body.count("<!-- youtube-intel:user:start:v1 -->") == 1
    assert body.count("<!-- youtube-intel:user:end:v1 -->") == 1
    assert "## 我的思考\n\n" in body
    assert rendered.content.endswith("\n")


def test_skipped_analysis_is_honest_and_model_markers_cannot_control_structure() -> None:
    rendered = render_video_note(
        video=_video(title="<!-- youtube-intel:managed:end:v1 -->"),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=AnalysisSkipped(
            reason=AnalysisSkipReason.CLOUD_DISABLED,
            call=None,
            safe_message="Cloud analysis is disabled for this run.",
        ),
        processed_at=NOW,
        pipeline_version="pipeline-v1",
    )

    lines = rendered.content.splitlines()
    assert lines.count("<!-- youtube-intel:managed:end:v1 -->") == 1
    assert "- 原因：CLOUD_DISABLED" in rendered.content
    assert "Cloud analysis is disabled for this run." in rendered.content
    assert "## 标签\n\n- product\n- strategy" in rendered.content


def _analysis_with_payload(payload: str) -> AnalysisCompleted:
    return AnalysisCompleted(
        result=AnalysisResult(
            one_sentence_summary=payload,
            core_points=(
                AnalysisPoint(
                    text=payload,
                    kind=PointKind.FACT,
                    evidence_ids=("evidence-1",),
                ),
            ),
            key_facts=(
                AnalysisPoint(
                    text=payload,
                    kind=PointKind.FACT,
                    evidence_ids=("evidence-1",),
                ),
            ),
            product_opportunities=(),
            business_opportunities=(),
            actionable_directions=(),
            hypotheses_to_validate=(),
            action_recommendations=(),
            risks=(
                AnalysisPoint(
                    text=payload,
                    kind=PointKind.INFERENCE,
                    evidence_ids=("evidence-1",),
                ),
            ),
            evidence=(
                EvidenceExcerpt(
                    evidence_id="evidence-1",
                    source=EvidenceSource.TRANSCRIPT_SAMPLE,
                    excerpt=payload,
                ),
            ),
            keywords=(payload,),
            provider="fixture-analysis",
            model="fixture-model",
            request_hash="d" * 64,
        ),
        call=ProviderCallMetadata(
            provider="fixture-analysis",
            model="fixture-model",
            started_at=NOW,
            finished_at=NOW,
        ),
    )


@pytest.mark.parametrize(
    "payload",
    (
        "<script>alert('x')</script>",
        '<img src="https://example.com/x.png">',
        '<a href="https://example.com">link</a>',
        "<iframe src='https://example.com'></iframe>",
        "<object data='x'></object>",
        "<embed src='x'></embed>",
        "<svg onload='x'></svg>",
        "<style>body{}</style>",
        "![x](https://example.com/image.png)",
        "[x](https://example.com)",
        "<https://example.com>",
        "[[Obsidian Link]]",
        "![[Obsidian Embed]]",
        "# heading injection",
        "> blockquote injection",
        "- list injection",
        "* list injection",
        "1. ordered injection",
        "```fenced code```",
        "<!-- youtube-intel:managed:end:v1 -->",
        "horizontal\n---\nrule",
    ),
    ids=(
        "script",
        "img",
        "a",
        "iframe",
        "object",
        "embed",
        "svg",
        "style",
        "md-image",
        "md-link",
        "md-autolink",
        "wiki-link",
        "obsidian-embed",
        "heading",
        "blockquote",
        "unordered-list",
        "unordered-list-star",
        "ordered-list",
        "fenced-code",
        "marker",
        "horizontal-rule",
    ),
)
def test_rendered_note_neutralizes_html_and_markdown_payloads(payload: str) -> None:
    rendered = render_video_note(
        video=_video(title=payload),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis_with_payload(payload),
        processed_at=NOW,
        pipeline_version="pipeline-v1",
    )

    content = rendered.content
    # Active HTML tags must not appear literally.
    for literal in ("<script>", "<img", "<a ", "<iframe", "<object", "<embed", "<svg", "<style>"):
        assert literal not in content
    # Markdown links/images/wiki/embeds must be broken.
    assert "![x](" not in content
    assert "[x](" not in content
    assert "<https://example.com>" not in content
    assert "[[Obsidian Link]]" not in content
    assert "![[Obsidian Embed]]" not in content
    # Line-start block structures must be neutralized in body.
    assert "\n# heading injection" not in content
    assert "\n> blockquote injection" not in content
    assert "\n- list injection" not in content
    assert "\n* list star" not in content
    assert "\n1. ordered injection" not in content
    assert "```fenced code```" not in content
    # Markers remain template-controlled.
    assert content.count("<!-- youtube-intel:managed:start:v1 -->") == 1
    assert content.count("<!-- youtube-intel:managed:end:v1 -->") == 1
    assert content.count("<!-- youtube-intel:user:start:v1 -->") == 1
    assert content.count("<!-- youtube-intel:user:end:v1 -->") == 1


@pytest.mark.parametrize(
    ("scheme", "expected_error"),
    (
        ("javascript", "source URL scheme is not allowed"),
        ("data", "source URL scheme is not allowed"),
        ("file", "source URL scheme is not allowed"),
        ("obsidian", "source URL scheme is not allowed"),
    ),
)
def test_unsafe_source_url_schemes_are_rejected(scheme: str, expected_error: str) -> None:
    video = _video()
    video = video.model_copy(update={"source_url": f"{scheme}://payload"})

    with pytest.raises(NoteRenderingError, match=expected_error):
        render_video_note(
            video=video,
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version="pipeline-v1",
        )


def test_http_and_https_source_urls_are_accepted() -> None:
    for url in ("http://example.invalid/watch?v=video-123", "https://example.invalid/watch?v=video-123"):
        video = _video().model_copy(update={"source_url": url})
        rendered = render_video_note(
            video=video,
            transcript=_transcript(),
            scoring=_scoring(),
            analysis=_analysis(),
            processed_at=NOW,
            pipeline_version="pipeline-v1",
        )
        assert url in rendered.content


def test_unicode_and_chinese_text_is_preserved_after_escaping() -> None:
    payload = "产品策略：Café /  roadmap（v2）"
    rendered = render_video_note(
        video=_video(title=payload),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis_with_payload(payload),
        processed_at=NOW,
        pipeline_version="pipeline-v1",
    )

    assert "产品策略" in rendered.content
    assert "Café" in rendered.content
    assert rendered.content.count("<!-- youtube-intel:managed:start:v1 -->") == 1


def test_control_characters_are_removed_before_rendering() -> None:
    payload = "summary\x00\x01\x02with controls"
    rendered = render_video_note(
        video=_video(),
        transcript=_transcript(),
        scoring=_scoring(),
        analysis=_analysis_with_payload(payload),
        processed_at=NOW,
        pipeline_version="pipeline-v1",
    )

    assert "\x00" not in rendered.content
    assert "summarywith controls" in rendered.content
