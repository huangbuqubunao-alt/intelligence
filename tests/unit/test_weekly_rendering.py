"""Offline unit tests for weekly report Markdown safety."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from youtube_intel.domain import (
    AnalysisPoint,
    AnalysisResult,
    Availability,
    EvidenceExcerpt,
    EvidenceSource,
    LiveStatus,
    NoteKind,
    NoteRef,
    PointKind,
    ProviderCallMetadata,
    ScoreResult,
    ScoringDecision,
    ScoringOutcome,
    VideoMetadata,
    WeeklyReportItem,
)
from youtube_intel.reporting import (
    WeeklyReportValidationError,
    _VerifiedWeeklyReport,
    render_weekly_report,
)

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)


def _video(*, video_id: str = "video-a", title: str = "A safe product note") -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        channel_id="channel-1",
        channel_name="Channel",
        title=title,
        description="",
        source_url=f"https://example.invalid/{video_id}",
        published_at=NOW,
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


def _scoring(*, score: float = 9.0, reason: str = "Directly useful.") -> ScoringOutcome:
    result = ScoreResult(
        schema_version="score-result-v1",
        score=score,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="fixture-score",
        model="fixture-model",
        prompt_version="scoring-prompt-v1",
        request_hash="a" * 64,
    )
    return ScoringOutcome(
        result=result,
        decision=ScoringDecision(
            threshold=7.0,
            final_should_summarize=True,
            model_disagrees=False,
        ),
        call=ProviderCallMetadata(
            provider="fixture-score",
            model="fixture-model",
            started_at=NOW,
            finished_at=NOW,
        ),
    )


def _analysis(*, keyword: str = "product", direction: str = "Use the verified direction.") -> AnalysisResult:
    return AnalysisResult(
        one_sentence_summary="A compact summary.",
        core_points=(
            AnalysisPoint(
                text="Verified local fact.",
                kind=PointKind.FACT,
                evidence_ids=("evidence-1",),
            ),
        ),
        actionable_directions=(
            AnalysisPoint(
                text=direction,
                kind=PointKind.RECOMMENDATION,
                evidence_ids=("evidence-1",),
            ),
        ),
        keywords=(keyword,),
        evidence=(
            EvidenceExcerpt(
                evidence_id="evidence-1",
                source=EvidenceSource.TRANSCRIPT_SAMPLE,
                excerpt="Verified excerpt.",
            ),
        ),
        provider="fixture-analysis",
        model="fixture-model",
        request_hash="b" * 64,
    )


def _report(
    *,
    title: str = "A safe product note",
    summary: str = "A compact summary.",
    reason: str = "Directly useful.",
    keyword: str = "product",
    direction: str = "Use the verified direction.",
) -> _VerifiedWeeklyReport:
    video = _video(title=title)
    analysis = _analysis(keyword=keyword, direction=direction)
    return _VerifiedWeeklyReport(
        iso_year=2026,
        iso_week=1,
        timezone="Asia/Shanghai",
        items=(
            WeeklyReportItem(
                video=video,
                score=_scoring(reason=reason).result,
                note_ref=NoteRef(
                    kind=NoteKind.VIDEO,
                    relative_path="Videos/Title-video-a--video-a.md",
                    content_hash="c" * 64,
                ),
                one_sentence_summary=summary,
            ),
        ),
        analysis_results=(analysis,),
        generated_at=NOW,
    )


@pytest.mark.parametrize(
    ("payload", "dangerous_literal"),
    (
        ("<script>alert('x')</script>", "<script>"),
        ('<img src="x">', "<img"),
        ("![x](https://example.com/x.png)", "![x]("),
        ("[x](https://example.com)", "[x]("),
        ("# heading", "\n# heading"),
        ("> quote", "\n> quote"),
        ("- list", "\n- list"),
        ("1. ordered", "\n1. ordered"),
        ("```code```", "```code```"),
        ("---", "\n---"),
    ),
)
def test_weekly_report_neutralizes_html_and_markdown_in_items(payload: str, dangerous_literal: str) -> None:
    rendered = render_weekly_report(_report(title=payload, summary=payload, reason=payload))
    assert dangerous_literal not in rendered
    assert "<!-- youtube-intel:weekly:v1 -->" in rendered


@pytest.mark.parametrize(
    "payload",
    (
        "product#tag",
        "product*emphasis*",
        "product[link]",
        "product![image]",
    ),
)
def test_weekly_report_neutralizes_markdown_in_keywords(payload: str) -> None:
    rendered = render_weekly_report(_report(keyword=payload))
    assert payload not in rendered
    assert "product" in rendered


@pytest.mark.parametrize(
    "payload",
    (
        "dir#heading",
        "dir*emphasis*",
        "dir[link]",
        "dir![image]",
    ),
)
def test_weekly_report_neutralizes_markdown_in_directions(payload: str) -> None:
    rendered = render_weekly_report(_report(direction=payload))
    assert payload not in rendered
    assert "dir" in rendered


def test_weekly_report_rejects_unsafe_note_path() -> None:
    report = _report()
    item = report.items[0].model_copy(
        update={
            "note_ref": NoteRef(
                kind=NoteKind.VIDEO,
                relative_path="Videos/Note--x.md",
                content_hash="c" * 64,
            ),
        }
    )
    bad_report = report.model_copy(update={"items": (item,)})
    with pytest.raises(WeeklyReportValidationError, match="note path is unsafe"):
        render_weekly_report(bad_report)


def test_weekly_report_preserves_unicode_and_chinese_text() -> None:
    rendered = render_weekly_report(_report(title="产品策略：Café", summary="中文摘要。"))
    assert "产品策略" in rendered
    assert "Café" in rendered
    assert "中文摘要" in rendered
