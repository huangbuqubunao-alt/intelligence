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
        schema_version="score-result-v1",
        score=8.5,
        reason="Directly useful to product strategy.",
        topics=("product", "strategy"),
        should_summarize=True,
        provider="fixture-scoring",
        model="fixture-model",
        prompt_version="scoring-prompt-v1",
        request_hash="c" * 64,
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
