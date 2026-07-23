"""Deterministic, local-only weekly reporting helpers."""

from __future__ import annotations

import hashlib
import os
import stat
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast
from zoneinfo import ZoneInfo

from jinja2 import StrictUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment

from youtube_intel.domain import (
    AnalysisResult,
    Availability,
    LiveStatus,
    NoteKind,
    NoteRef,
    ScoreResult,
    VideoMetadata,
    WeeklyReportInput,
    WeeklyReportItem,
)
from youtube_intel.state import ArtifactKind, StorageRoot, WeeklyCandidateRecord

_TEMPLATE_RESOURCE = ("templates", "weekly.md")
_MAX_ARTIFACT_BYTES = 5 << 20
_MAX_NOTE_BYTES = 5 << 20


class _WeeklyRepository(Protocol):
    def list_weekly_candidates(
        self, *, start_utc: datetime, end_utc: datetime
    ) -> tuple[WeeklyCandidateRecord, ...]: ...


class _WeeklySink(Protocol):
    def upsert_weekly_report(self, report: WeeklyReportInput) -> NoteRef: ...


class WeeklyReportValidationError(ValueError):
    """Raised before writing when a report input lacks verified local facts."""


class _VerifiedWeeklyReport(WeeklyReportInput):
    """Internal render input that keeps Analysis facts aligned with report items."""

    analysis_results: tuple[AnalysisResult, ...]


@dataclass(frozen=True, slots=True)
class WeekPeriod:
    """One configured-timezone ISO week represented by UTC instants."""

    timezone: str
    iso_year: int
    iso_week: int
    start_utc: datetime
    end_utc: datetime

    @property
    def relative_path(self) -> str:
        return f"Weekly/{self.iso_year}-W{self.iso_week:02d}.md"

    def contains(self, value: datetime) -> bool:
        _require_utc(value, field_name="value")
        return self.start_utc <= value < self.end_utc


@dataclass(frozen=True, slots=True)
class GeneratedWeeklyReport:
    period: WeekPeriod
    report: WeeklyReportInput
    note_ref: NoteRef


class WeeklyReportService:
    """Build a weekly report from locally verified, immutable facts only."""

    def __init__(
        self,
        *,
        repository: _WeeklyRepository,
        sink: _WeeklySink,
        artifact_root: Path,
        timezone: str,
        top_n: int,
    ) -> None:
        if top_n < 1:
            msg = "top_n must be positive"
            raise ValueError(msg)
        self._repository = repository
        self._sink = sink
        self._artifact_root = artifact_root
        self._timezone = timezone
        self._top_n = top_n

    def generate(self, *, now: datetime) -> GeneratedWeeklyReport:
        period = week_period_for(now, timezone=self._timezone)
        verified = tuple(
            self._verified_item(candidate)
            for candidate in self._repository.list_weekly_candidates(
                start_utc=period.start_utc, end_utc=period.end_utc
            )
        )[: self._top_n]
        report = _VerifiedWeeklyReport(
            iso_year=period.iso_year,
            iso_week=period.iso_week,
            timezone=period.timezone,
            items=tuple(item for item, _ in verified),
            generated_at=now,
            analysis_results=tuple(analysis for _, analysis in verified),
        )
        return GeneratedWeeklyReport(
            period=period,
            report=report,
            note_ref=self._sink.upsert_weekly_report(report),
        )

    def _verified_item(
        self, candidate: WeeklyCandidateRecord
    ) -> tuple[WeeklyReportItem, AnalysisResult]:
        try:
            video = _video_metadata(candidate.video)
            score = _verified_score(self._artifact_root, candidate.score_artifact, video.video_id)
            analysis = _verified_analysis(
                self._artifact_root, candidate.analysis_artifact, video.video_id
            )
        except (OSError, TypeError, ValueError):
            raise WeeklyReportValidationError("weekly analysis inputs are invalid") from None
        try:
            note = candidate.note_artifact
            if (
                note.kind is not ArtifactKind.VIDEO_NOTE
                or note.storage_root is not StorageRoot.VAULT
                or note.video_id != video.video_id
                or note.deleted_at is not None
                or not note.relative_path.startswith("Videos/")
                or note.artifact_key
                != f"video-note/{candidate.video.pipeline_version}/{video.video_id}"
            ):
                raise WeeklyReportValidationError("weekly note reference is invalid")
            note_ref = NoteRef(
                kind=NoteKind.VIDEO,
                relative_path=note.relative_path,
                content_hash=note.content_hash,
            )
            _verify_managed_note_file(self._sink, note_ref, video.video_id)
            if not score.should_summarize or candidate.video.score != score.score:
                raise WeeklyReportValidationError("weekly score result is invalid")
            return (
                WeeklyReportItem(
                    video=video,
                    score=score,
                    note_ref=note_ref,
                    one_sentence_summary=analysis.one_sentence_summary,
                ),
                analysis,
            )
        except WeeklyReportValidationError:
            raise
        except (OSError, TypeError, ValueError):
            raise WeeklyReportValidationError("weekly note reference is invalid") from None


def week_period_for(now: datetime, *, timezone: str) -> WeekPeriod:
    """Return the configured local ISO week that contains a UTC instant."""

    _require_utc(now, field_name="now")
    if not timezone.strip():
        msg = "timezone must be non-empty"
        raise ValueError(msg)
    local_now = now.astimezone(ZoneInfo(timezone))
    iso_year, iso_week, iso_day = local_now.isocalendar()
    local_start = datetime.combine(
        local_now.date() - timedelta(days=iso_day - 1),
        time.min,
        tzinfo=local_now.tzinfo,
    )
    local_end = local_start + timedelta(days=7)
    return WeekPeriod(
        timezone=timezone,
        iso_year=iso_year,
        iso_week=iso_week,
        start_utc=local_start.astimezone(UTC),
        end_utc=local_end.astimezone(UTC),
    )


def _require_utc(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        msg = f"{field_name} must be a UTC-aware datetime"
        raise ValueError(msg)


def render_weekly_report(report: WeeklyReportInput) -> str:
    """Render fixed Markdown using no user-controlled template or loader."""

    items = tuple(
        {
            "title": _inline(item.video.title),
            "note_path": item.note_ref.relative_path,
            "score": f"{item.score.score:g}",
            "reason": _inline(item.score.reason),
            "summary": _inline(item.one_sentence_summary),
        }
        for item in report.items
    )
    analyses = _analyses_for_report(report)
    keywords = _keyword_counts(analyses)
    directions = _trend_and_direction_lines(keywords, analyses)
    content = _template().render(
        iso_year=report.iso_year,
        iso_week=report.iso_week,
        timezone=_inline(report.timezone),
        item_count=len(items),
        items=items,
        keywords=keywords,
        directions=directions,
    )
    return cast(str, content).replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def _template() -> Any:
    environment = ImmutableSandboxedEnvironment(
        autoescape=False, undefined=StrictUndefined, loader=None
    )
    environment.globals.clear()
    source = resources.files("youtube_intel").joinpath(*_TEMPLATE_RESOURCE).read_text(
        encoding="utf-8"
    )
    return environment.from_string(source)


def _analyses_for_report(report: WeeklyReportInput) -> tuple[AnalysisResult, ...]:
    analyses = getattr(report, "analysis_results", None)
    if not isinstance(analyses, tuple) or len(analyses) != len(report.items):
        raise WeeklyReportValidationError("weekly analysis inputs are missing")
    if not all(isinstance(analysis, AnalysisResult) for analysis in analyses):
        raise WeeklyReportValidationError("weekly analysis inputs are invalid")
    return analyses


def _keyword_counts(analyses: tuple[AnalysisResult, ...]) -> tuple[dict[str, object], ...]:
    return _normalized_counts(
        keyword
        for analysis in analyses
        for keyword in _deduplicated_keywords(analysis.keywords)
    )


def _trend_and_direction_lines(
    keywords: tuple[dict[str, object], ...], analyses: tuple[AnalysisResult, ...]
) -> tuple[str, ...]:
    trends = tuple(
        f"趋势：{entry['keyword']}（{entry['count']}）" for entry in keywords
    )
    directions = _normalized_counts(
        _normalized_text(point.text)
        for analysis in analyses
        for group in (
            analysis.actionable_directions,
            analysis.action_recommendations,
            analysis.product_opportunities,
            analysis.business_opportunities,
        )
        for point in group
    )
    return trends + tuple(f"持续关注：{entry['keyword']}" for entry in directions)


def _normalized_counts(values: Any) -> tuple[dict[str, object], ...]:
    counts: dict[str, tuple[str, int]] = {}
    for value in values:
        display = _normalized_text(value)
        normalized = display.casefold()
        previous = counts.get(normalized)
        if previous is None:
            counts[normalized] = (display, 1)
        else:
            counts[normalized] = (min(previous[0], display), previous[1] + 1)
    return tuple(
        {"keyword": display, "count": count}
        for _, (display, count) in sorted(
            counts.items(), key=lambda entry: (-entry[1][1], entry[0])
        )
    )


def _deduplicated_keywords(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized: dict[str, str] = {}
    for value in values:
        display = _normalized_text(value)
        key = display.casefold()
        normalized[key] = min(normalized.get(key, display), display)
    return tuple(normalized[key] for key in sorted(normalized))


def _normalized_text(value: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not normalized:
        raise WeeklyReportValidationError("weekly analysis text is invalid")
    return normalized


def _verified_score(root: Path, artifact: Any, video_id: str) -> ScoreResult:
    content = _verified_data_artifact(root, artifact, video_id, ArtifactKind.SCORING_STRUCTURED)
    result = ScoreResult.model_validate_json(content)
    if (
        artifact.artifact_key != f"scoring/{result.request_hash}/structured"
        or artifact.relative_path != f"scoring/{result.request_hash}/structured.json"
        or artifact.provider != result.provider
        or artifact.model != result.model
    ):
        raise ValueError("scoring artifact provenance is invalid")
    return result


def _verified_analysis(root: Path, artifact: Any, video_id: str) -> AnalysisResult:
    content = _verified_data_artifact(root, artifact, video_id, ArtifactKind.ANALYSIS_STRUCTURED)
    result = AnalysisResult.model_validate_json(content)
    if (
        artifact.artifact_key != f"analysis/{result.request_hash}/structured"
        or artifact.relative_path != f"analysis/{result.request_hash}/structured.json"
        or artifact.provider != result.provider
        or artifact.model != result.model
    ):
        raise ValueError("analysis artifact provenance is invalid")
    return result


def _verified_data_artifact(root: Path, artifact: Any, video_id: str, kind: ArtifactKind) -> bytes:
    relative = artifact.relative_path
    path = PurePosixPath(relative)
    if (
        artifact.kind is not kind
        or artifact.storage_root is not StorageRoot.DATA
        or artifact.video_id != video_id
        or artifact.deleted_at is not None
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("artifact is invalid")
    content = (root / Path(*path.parts)).read_bytes()
    if len(content) > _MAX_ARTIFACT_BYTES or hashlib.sha256(content).hexdigest() != artifact.content_hash:
        raise ValueError("artifact contents are invalid")
    return content


def _verify_managed_note_file(sink: _WeeklySink, ref: NoteRef, video_id: str) -> None:
    vault_root = getattr(sink, "_vault_root", None)
    vault_subdir = getattr(sink, "_vault_subdir", None)
    relative_path = PurePosixPath(ref.relative_path)
    if (
        not isinstance(vault_root, Path)
        or not vault_root.is_absolute()
        or not isinstance(vault_subdir, PurePosixPath)
        or relative_path.parts[:1] != ("Videos",)
        or len(relative_path.parts) != 2
        or any(part in {"", ".", ".."} for part in relative_path.parts)
        or not relative_path.name.endswith(f"--{video_id}.md")
    ):
        raise WeeklyReportValidationError("weekly note reference is invalid")
    root_fd = _open_directory(vault_root)
    subdir_fd: int | None = None
    videos_fd: int | None = None
    note_fd: int | None = None
    try:
        current_fd = root_fd
        for part in vault_subdir.parts:
            if not part or part in {".", ".."}:
                raise WeeklyReportValidationError("weekly note vault path is invalid")
            next_fd = _open_directory(part, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        subdir_fd = current_fd
        videos_fd = _open_directory("Videos", dir_fd=subdir_fd)
        note_fd = os.open(
            relative_path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=videos_fd
        )
        if not stat.S_ISREG(os.fstat(note_fd).st_mode):
            raise WeeklyReportValidationError("weekly note is not a regular file")
        content = _read_limited(note_fd, _MAX_NOTE_BYTES)
        if hashlib.sha256(content).hexdigest() != ref.content_hash:
            raise WeeklyReportValidationError("weekly note content hash is invalid")
    finally:
        if note_fd is not None:
            os.close(note_fd)
        if videos_fd is not None:
            os.close(videos_fd)
        if subdir_fd is not None and subdir_fd != root_fd:
            os.close(subdir_fd)
        os.close(root_fd)


def _open_directory(path: Path | str, *, dir_fd: int | None = None) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if dir_fd is None:
        return os.open(path, flags)
    return os.open(path, flags, dir_fd=dir_fd)


def _read_limited(fd: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(fd, min(65536, limit + 1 - size))
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > limit:
            raise WeeklyReportValidationError("weekly note is too large")
        chunks.append(chunk)


def _video_metadata(record: Any) -> VideoMetadata:
    if any(
        getattr(record, name) is None
        for name in ("channel_name", "title", "source_url", "published_at", "duration_seconds", "live_status", "availability")
    ):
        raise ValueError("weekly video metadata is incomplete")
    return VideoMetadata(
        video_id=record.video_id,
        channel_id=record.channel_id,
        channel_name=record.channel_name,
        title=record.title,
        description=record.description or "",
        source_url=record.source_url,
        published_at=record.published_at,
        duration_seconds=record.duration_seconds,
        default_language=record.default_language,
        available_languages=record.available_languages,
        live_status=LiveStatus(record.live_status),
        availability=Availability(record.availability),
    )


def _inline(value: str) -> str:
    return " ".join(value.replace("\r", "\n").splitlines()).strip()
