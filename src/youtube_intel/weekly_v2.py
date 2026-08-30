"""Pure deterministic Weekly V2 aggregation over admitted Note V2 artifacts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from youtube_intel.deep_analysis_contracts import dacs1_sha256
from youtube_intel.note_v2 import NoteV2SectionKind
from youtube_intel.notes import _safe_inline
from youtube_intel.reporting import WeekPeriod, week_period_for
from youtube_intel.verified_note_v2 import (
    VerifiedNoteV2Artifact,
    verify_verified_note_v2_artifact,
)


class WeeklyV2Error(ValueError):
    """Weekly V2 received data outside its verified artifact boundary."""


@dataclass(frozen=True, slots=True)
class WeeklyV2Item:
    artifact_identity: str
    note_identity: str
    video_id: str
    title: str
    source_url: str
    language: str
    ranking_score: float
    ranking_reason: str
    one_sentence_summary: str
    themes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeeklyV2:
    schema_version: str
    period: WeekPeriod
    top_n: int
    items: tuple[WeeklyV2Item, ...]
    identity: str


def build_weekly_v2(
    artifacts: Iterable[object], *, now: datetime, timezone: str, top_n: int
) -> WeeklyV2:
    """Select and aggregate only process-admitted Note V2 artifact handoffs."""

    if top_n < 1:
        raise WeeklyV2Error("top_n must be positive")
    period = week_period_for(now, timezone=timezone)
    verified = tuple(_require_verified(artifact) for artifact in artifacts)
    unique = {artifact.identity: artifact for artifact in verified}
    selected = tuple(
        artifact
        for artifact in sorted(
            unique.values(),
            key=lambda value: (-value.ranking_score, value.video_id, value.identity),
        )
        if period.contains(artifact.completed_at)
    )[:top_n]
    report = WeeklyV2(
        schema_version="weekly-v2",
        period=period,
        top_n=top_n,
        items=tuple(_item(artifact) for artifact in selected),
        identity="",
    )
    return WeeklyV2(
        schema_version=report.schema_version,
        period=report.period,
        top_n=report.top_n,
        items=report.items,
        identity=_identity(report),
    )


def render_weekly_v2(report: WeeklyV2) -> str:
    """Render a fixed Markdown representation without repositories or providers."""

    if report.identity != _identity(report):
        raise WeeklyV2Error("Weekly V2 identity is invalid")
    lines = [
        "---",
        "type: weekly-v2",
        f"weekly_identity: {report.identity}",
        f"timezone: {_safe_inline(report.period.timezone)}",
        f"iso_year: {report.period.iso_year}",
        f"iso_week: {report.period.iso_week}",
        "---",
        "",
        f"# Weekly {report.period.iso_year}-W{report.period.iso_week:02d}",
        "",
        f"本周新增数：{len(report.items)}",
        "",
        "## Top N",
        "",
    ]
    if not report.items:
        lines.append("本周没有符合条件的高价值视频。")
    for item in report.items:
        lines.extend(
            (
                f"- {_safe_inline(item.title)}（评分：{item.ranking_score:g}）",
                f"  - 总结：{_safe_inline(item.one_sentence_summary)}",
                f"  - 推荐原因：{_safe_inline(item.ranking_reason)}",
                f"  - 来源：{_safe_inline(item.source_url)}",
            )
        )
    lines.extend(("", "## Repeated themes", ""))
    themes = _theme_counts(report.items)
    lines.extend(
        (f"- {_safe_inline(theme)}（{count}）" for theme, count in themes)
        if themes
        else ("本周暂无可持续关注方向。",)
    )
    return "\n".join(lines).rstrip() + "\n"


def _require_verified(value: object) -> VerifiedNoteV2Artifact:
    if type(value) is not VerifiedNoteV2Artifact or not verify_verified_note_v2_artifact(value):
        raise WeeklyV2Error("Weekly V2 requires a verified Note V2 artifact")
    return value


def _item(artifact: VerifiedNoteV2Artifact) -> WeeklyV2Item:
    summary = artifact.note.sections[0].entries[0].text
    return WeeklyV2Item(
        artifact_identity=artifact.identity,
        note_identity=artifact.note_identity,
        video_id=artifact.video_id,
        title=artifact.title,
        source_url=artifact.source_url,
        language=artifact.language,
        ranking_score=artifact.ranking_score,
        ranking_reason=artifact.ranking_reason,
        one_sentence_summary=summary,
        themes=tuple(
            entry.text
            for section in artifact.note.sections
            if section.kind is NoteV2SectionKind.KNOWLEDGE_GRAPH
            for entry in section.entries
        ),
    )


def _theme_counts(items: tuple[WeeklyV2Item, ...]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, tuple[str, int]] = {}
    for item in items:
        for theme in sorted(set(item.themes)):
            key = " ".join(theme.split()).casefold()
            if not key:
                continue
            display, count = counts.get(key, (" ".join(theme.split()), 0))
            counts[key] = (display, count + 1)
    return tuple(
        (display, count)
        for _key, (display, count) in sorted(
            counts.items(), key=lambda pair: (-pair[1][1], pair[0])
        )
    )


def _identity(report: WeeklyV2) -> str:
    if report.schema_version != "weekly-v2":
        raise WeeklyV2Error("Weekly V2 schema is invalid")
    return dacs1_sha256(
        {
            "schema_version": report.schema_version,
            "timezone": report.period.timezone,
            "iso_year": report.period.iso_year,
            "iso_week": report.period.iso_week,
            "top_n": report.top_n,
            "items": [
                {
                    "artifact_identity": item.artifact_identity,
                    "note_identity": item.note_identity,
                    "video_id": item.video_id,
                    "title": item.title,
                    "source_url": item.source_url,
                    "language": item.language,
                    "ranking_score": item.ranking_score,
                    "ranking_reason": item.ranking_reason,
                    "one_sentence_summary": item.one_sentence_summary,
                    "themes": list(item.themes),
                }
                for item in report.items
            ],
        }
    )


__all__ = ["WeeklyV2", "WeeklyV2Error", "WeeklyV2Item", "build_weekly_v2", "render_weekly_v2"]
