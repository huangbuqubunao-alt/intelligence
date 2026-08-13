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
from youtube_intel.notes import build_video_note_filename
from youtube_intel.reporting import (
    WeeklyReportValidationError,
    _safe_note_path,
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


def _scoring(
    *,
    score: float = 9.0,
    reason: str = "This video provides directly useful guidance.",
) -> ScoringOutcome:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=score,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="fixture-score",
        model="fixture-model",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
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
    reason: str = "This video provides directly useful guidance.",
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
    rendered = render_weekly_report(
        _report(
            title=payload,
            summary=payload,
            reason=f"The video provides a detailed practical explanation. {payload}",
        )
    )
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


@pytest.mark.parametrize(
    "relative_path",
    (
        "Videos/中文产品分析--abc123.md",
        "Videos/日本語分析--abc123.md",
        # Devanagari with explicit combining marks (ma + halant + ra).
        "Videos/हिन्दीमेंविश्लेषण--abc123.md",
        # Arabic with tashkil combining marks.
        "Videos/تحليل_عَرَبِيّ--abc123.md",
        # Latin base + combining acute accent (NFD then normalized to NFC by the validator).
        "Videos/café_analysis--abc123.md",
    ),
    ids=("chinese", "japanese", "hindi-combining", "arabic-combining", "latin-combining"),
)
def test_weekly_report_accepts_unicode_note_path(relative_path: str) -> None:
    report = _report()
    item = report.items[0].model_copy(
        update={
            "note_ref": NoteRef(
                kind=NoteKind.VIDEO,
                relative_path=relative_path,
                content_hash="c" * 64,
            ),
        }
    )
    rendered = render_weekly_report(report.model_copy(update={"items": (item,)}))
    # The base name (without extension) must appear safely inside the wiki link.
    base = relative_path.split("/")[1].rsplit("--", 1)[0]
    assert base in rendered
    assert f"[[{relative_path}|" in rendered


def test_safe_note_path_rejects_traversal_and_absolute_paths() -> None:
    with pytest.raises(WeeklyReportValidationError, match="note path is unsafe"):
        _safe_note_path("../evil.md")
    with pytest.raises(WeeklyReportValidationError, match="note path is unsafe"):
        _safe_note_path("/absolute/path.md")


@pytest.mark.parametrize(
    "relative_path",
    (
        "[link].md",
        "![[embed]].md",
        "Videos/[link]--abc123.md",
        "Videos/![[embed]]--abc123.md",
    ),
    ids=("plain-link", "plain-embed", "video-link", "video-embed"),
)
def test_safe_note_path_rejects_markdown_and_obsidian_injection(relative_path: str) -> None:
    with pytest.raises(WeeklyReportValidationError, match="note path is unsafe"):
        _safe_note_path(relative_path)


@pytest.mark.parametrize(
    "relative_path",
    (
        "Videos/[link](evil)--abc123.md",
        "Videos/![image](evil)--abc123.md",
        "Videos/[[wiki]]--abc123.md",
        "Videos/![[embed]]--abc123.md",
        "Videos/auto<link>--abc123.md",
        "Videos/pipe|alias--abc123.md",
    ),
    ids=("md-link", "md-image", "wiki-link", "obsidian-embed", "auto-link", "pipe-alias"),
)
def test_weekly_report_rejects_markdown_and_obsidian_injection_in_path(relative_path: str) -> None:
    report = _report()
    item = report.items[0].model_copy(
        update={
            "note_ref": NoteRef(
                kind=NoteKind.VIDEO,
                relative_path=relative_path,
                content_hash="c" * 64,
            ),
        }
    )
    with pytest.raises(WeeklyReportValidationError, match="note path is unsafe"):
        render_weekly_report(report.model_copy(update={"items": (item,)}))


def test_weekly_report_preserves_unicode_and_chinese_text() -> None:
    rendered = render_weekly_report(_report(title="产品策略：Café", summary="中文摘要。"))
    assert "产品策略" in rendered
    assert "Café" in rendered
    assert "中文摘要" in rendered


def _report_with_generated_path(title: str) -> _VerifiedWeeklyReport:
    """Build a weekly report whose note path comes from the real producer."""
    video_id = "video-a"
    relative_path = f"Videos/{build_video_note_filename(title, video_id)}"
    video = _video(video_id=video_id, title=title)
    analysis = _analysis()
    return _VerifiedWeeklyReport(
        iso_year=2026,
        iso_week=1,
        timezone="Asia/Shanghai",
        items=(
            WeeklyReportItem(
                video=video,
                score=_scoring().result,
                note_ref=NoteRef(
                    kind=NoteKind.VIDEO,
                    relative_path=relative_path,
                    content_hash="c" * 64,
                ),
                one_sentence_summary="A compact summary.",
            ),
        ),
        analysis_results=(analysis,),
        generated_at=NOW,
    )


@pytest.mark.parametrize(
    "title",
    (
        "Product 2026",
        "版本２",
        # Devanagari with explicit combining marks.
        "हिन्दी में",
        # Latin base + combining acute accent.
        "cafe\u0301",
    ),
    ids=("latin-number", "chinese-number", "hindi-combining", "latin-combining"),
)
def test_weekly_report_renders_real_producer_unicode_path(title: str) -> None:
    """A filename produced by notes.py must render through reporting.py unchanged."""
    report = _report_with_generated_path(title)
    rendered = render_weekly_report(report)
    expected_path = report.items[0].note_ref.relative_path
    assert f"[[{expected_path}|" in rendered


def test_weekly_report_rejects_injected_path_through_shared_validator() -> None:
    """If reporting.py bypassed the shared validator, an injected path would render.

    The producer sanitizes ``[injected]`` to a safe base, so this test mutates
    the report to an unsafe path and proves ``render_weekly_report`` still
    rejects it via ``validate_video_note_relative_path``.
    """
    report = _report_with_generated_path("safe title")
    unsafe_item = report.items[0].model_copy(
        update={
            "note_ref": NoteRef(
                kind=NoteKind.VIDEO,
                relative_path="Videos/[injected]--video-a.md",
                content_hash="c" * 64,
            ),
        }
    )
    unsafe_report = report.model_copy(update={"items": (unsafe_item,)})
    with pytest.raises(WeeklyReportValidationError, match="note path is unsafe"):
        render_weekly_report(unsafe_report)
