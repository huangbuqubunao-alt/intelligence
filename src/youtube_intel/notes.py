"""Pure, bounded rendering for managed Obsidian video notes."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from typing import Final

from jinja2 import StrictUndefined, Template
from jinja2.sandbox import ImmutableSandboxedEnvironment

from youtube_intel.domain import (
    AnalysisCompleted,
    AnalysisOutcome,
    AnalysisSkipped,
    ScoringOutcome,
    TranscriptArtifact,
    VideoMetadata,
)

_SAFE_VIDEO_ID: Final = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
_WINDOWS_DEVICE_NAMES: Final = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{number}" for number in range(1, 10)), *(f"lpt{number}" for number in range(1, 10))}
)
_MAX_SAFE_TITLE_BYTES: Final = 120
_MAX_MANAGED_BYTES: Final = 1 << 20
_TEMPLATE_RESOURCE: Final = ("templates", "video.md")


class NoteRenderingError(ValueError):
    """Raised when a note cannot be safely rendered from trusted domain data."""


@dataclass(frozen=True, slots=True)
class RenderedVideoNote:
    """A canonical managed note before its user-editable region is merged."""

    relative_path: str
    content: str
    content_hash: str


def build_video_note_filename(title: str, video_id: str) -> str:
    """Return the stable, portable filename for one video identity."""
    if not _SAFE_VIDEO_ID.fullmatch(video_id):
        raise NoteRenderingError("video identity is invalid")
    normalized = unicodedata.normalize("NFC", title)
    safe = "".join(_safe_title_character(character) for character in normalized)
    safe = re.sub(r"[\s-]+", lambda match: " " if match.group().isspace() else "-", safe)
    safe = safe.strip(" .-") or "video"
    safe = _truncate_utf8(safe, _MAX_SAFE_TITLE_BYTES).strip(" .-") or "video"
    if safe.split(".", maxsplit=1)[0].casefold() in _WINDOWS_DEVICE_NAMES:
        safe = f"video-{safe}"
    return f"{safe}--{video_id}.md"


def is_video_note_candidate(filename: str, video_id: str) -> bool:
    """Return whether one directory entry claims this video identity."""
    if not _SAFE_VIDEO_ID.fullmatch(video_id):
        raise NoteRenderingError("video identity is invalid")
    normalized = unicodedata.normalize("NFC", filename)
    suffix = f"--{video_id}.md"
    return normalized.casefold().endswith(suffix.casefold())


def render_video_note(
    *,
    video: VideoMetadata,
    transcript: TranscriptArtifact,
    scoring: ScoringOutcome,
    analysis: AnalysisOutcome,
    processed_at: datetime,
    pipeline_version: str,
) -> RenderedVideoNote:
    """Render the immutable managed portion of a high-value video note."""
    if transcript.video_id != video.video_id:
        raise NoteRenderingError("transcript identity does not match video")
    if processed_at.tzinfo is None or processed_at.utcoffset() != UTC.utcoffset(processed_at):
        raise NoteRenderingError("processed_at must be UTC-aware")
    if not pipeline_version or pipeline_version.strip() != pipeline_version:
        raise NoteRenderingError("pipeline_version is invalid")
    if not scoring.decision.final_should_summarize:
        raise NoteRenderingError("low-value videos cannot render a note")

    relative_path = "Videos/" + build_video_note_filename(video.title, video.video_id)
    content = _template().render(
        frontmatter=_frontmatter(
            video=video,
            transcript=transcript,
            scoring=scoring,
            processed_at=processed_at,
            pipeline_version=pipeline_version,
        ),
        title=_inline(video.title),
        score=_inline(f"{scoring.result.score:g}"),
        scoring_reason=_inline(scoring.result.reason),
        topics=tuple(_inline(topic) for topic in scoring.result.topics),
        analysis=_analysis_values(analysis),
    )
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    if not content.endswith("\n"):
        content += "\n"
    encoded = content.encode("utf-8")
    if len(encoded) > _MAX_MANAGED_BYTES:
        raise NoteRenderingError("rendered managed note exceeds the resource limit")
    _validate_marker_shape(content)
    return RenderedVideoNote(
        relative_path=relative_path,
        content=content,
        content_hash=hashlib.sha256(encoded).hexdigest(),
    )


def _safe_title_character(character: str) -> str:
    category = unicodedata.category(character)
    if category.startswith(("L", "N", "M")) or character in " -_.()":
        return character
    return "-"


def _truncate_utf8(value: str, limit: int) -> str:
    kept: list[str] = []
    used = 0
    for character in value:
        size = len(character.encode("utf-8"))
        if used + size > limit:
            break
        kept.append(character)
        used += size
    return "".join(kept)


def _frontmatter(
    *,
    video: VideoMetadata,
    transcript: TranscriptArtifact,
    scoring: ScoringOutcome,
    processed_at: datetime,
    pipeline_version: str,
) -> str:
    published = video.published_at.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    processed = processed_at.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    values = (
        ("type", "video"),
        ("video_id", video.video_id),
        ("title", _inline(video.title)),
        ("channel", _inline(video.channel_name)),
        ("published", published),
        ("source", video.source_url),
        ("language", transcript.language),
        ("transcript_source", transcript.source_type.value),
    )
    lines = [f"{name}: {json.dumps(value, ensure_ascii=False)}" for name, value in values]
    lines.append(f"score: {scoring.result.score!r}")
    lines.append(
        "topics: [" + ", ".join(json.dumps(_inline(topic), ensure_ascii=False) for topic in scoring.result.topics) + "]"
    )
    lines.append(f"processed_at: {json.dumps(processed)}")
    lines.append(f"pipeline_version: {json.dumps(pipeline_version)}")
    return "\n".join(lines)


def _analysis_values(analysis: AnalysisOutcome) -> dict[str, object]:
    if isinstance(analysis, AnalysisSkipped):
        return {
            "skipped": True,
            "skip_reason": analysis.reason.value,
            "skip_message": _inline(analysis.safe_message),
            "summary": "未生成：云端分析按策略跳过。",
            "core_points": (),
            "key_facts": (),
            "product_opportunities": (),
            "business_opportunities": (),
            "actionable_directions": (),
            "hypotheses_to_validate": (),
            "action_recommendations": (),
            "risks": (),
            "evidence": (),
            "keywords": (),
        }
    if not isinstance(analysis, AnalysisCompleted):
        raise NoteRenderingError("analysis outcome is invalid")
    result = analysis.result
    return {
        "skipped": False,
        "skip_reason": "",
        "skip_message": "",
        "summary": _inline(result.one_sentence_summary),
        "core_points": tuple(_inline(point.text) for point in result.core_points),
        "key_facts": tuple(_inline(point.text) for point in result.key_facts),
        "product_opportunities": tuple(_inline(point.text) for point in result.product_opportunities),
        "business_opportunities": tuple(_inline(point.text) for point in result.business_opportunities),
        "actionable_directions": tuple(_inline(point.text) for point in result.actionable_directions),
        "hypotheses_to_validate": tuple(_inline(point.text) for point in result.hypotheses_to_validate),
        "action_recommendations": tuple(_inline(point.text) for point in result.action_recommendations),
        "risks": tuple(_inline(point.text) for point in result.risks),
        "evidence": tuple(
            _inline(f"{item.evidence_id}（{item.source.value}）：{item.excerpt}")
            for item in result.evidence
        ),
        "keywords": tuple(_inline(keyword) for keyword in result.keywords),
    }


def _inline(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    return " ".join(
        "".join(character for character in normalized if unicodedata.category(character) != "Cc").split()
    )


def _template() -> Template:
    environment = ImmutableSandboxedEnvironment(
        autoescape=False,
        undefined=StrictUndefined,
        loader=None,
    )
    environment.globals.clear()
    source = resources.files("youtube_intel").joinpath(*_TEMPLATE_RESOURCE).read_text(
        encoding="utf-8"
    )
    return environment.from_string(source)


def _validate_marker_shape(content: str) -> None:
    expected = (
        "<!-- youtube-intel:managed:start:v1 -->",
        "<!-- youtube-intel:managed:end:v1 -->",
        "<!-- youtube-intel:user:start:v1 -->",
        "<!-- youtube-intel:user:end:v1 -->",
    )
    lines = content.splitlines()
    positions: list[int] = []
    for marker in expected:
        if lines.count(marker) != 1:
            raise NoteRenderingError("rendered marker shape is invalid")
        positions.append(lines.index(marker))
    if positions != sorted(positions):
        raise NoteRenderingError("rendered marker order is invalid")
