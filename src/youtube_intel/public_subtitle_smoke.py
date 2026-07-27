"""Restricted, auditable composition for public subtitle release QA only."""

from __future__ import annotations

import re
import sqlite3
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from youtube_intel.domain import AppError, ErrorCode, VideoMetadata
from youtube_intel.logging import JsonlLogger
from youtube_intel.providers.subtitles import YtDlpSubtitleAdapter
from youtube_intel.providers.youtube import YtDlpMetadataProvider
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.transcripts import (
    SubtitleReadResult,
    SubtitleTrack,
    SubtitleTrackListing,
    rank_subtitle_candidates,
)

if TYPE_CHECKING:
    from youtube_intel.cli import CommandOutcome

_HTTP_TIMEOUT_SECONDS = 30.0
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


class _MetadataProvider(Protocol):
    def fetch(self, video_id: str) -> VideoMetadata: ...


class _SubtitleAdapter(Protocol):
    def enumerate_tracks(self, video_id: str) -> SubtitleTrackListing: ...

    def read_track(self, track: SubtitleTrack) -> SubtitleReadResult: ...


_MetadataProviderFactory = Callable[[float], _MetadataProvider]
_SubtitleAdapterFactory = Callable[[float], _SubtitleAdapter]
_Clock = Callable[[], datetime]


def _metadata_provider(timeout_seconds: float) -> _MetadataProvider:
    return YtDlpMetadataProvider(timeout_seconds=timeout_seconds)


def _subtitle_adapter(timeout_seconds: float) -> _SubtitleAdapter:
    return YtDlpSubtitleAdapter(timeout_seconds=timeout_seconds)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PublicSubtitleSmoke:
    """Perform the single, bounded read sequence permitted by ADR-013."""

    def __init__(
        self,
        *,
        metadata_provider_factory: _MetadataProviderFactory = _metadata_provider,
        subtitle_adapter_factory: _SubtitleAdapterFactory = _subtitle_adapter,
        now: _Clock = _utcnow,
    ) -> None:
        self._metadata_provider_factory = metadata_provider_factory
        self._subtitle_adapter_factory = subtitle_adapter_factory
        self._now = now

    def run(
        self,
        *,
        temporary_root: Path,
        video_ids: Sequence[str],
        run_id: str,
    ) -> CommandOutcome:
        from youtube_intel.cli import CommandOutcome
        if not _valid_inputs(temporary_root, video_ids):
            return CommandOutcome(prerequisite_failed=True)

        try:
            _initialize_root(temporary_root, now=self._now())
        except (OSError, sqlite3.Error):
            return CommandOutcome(local_resource_failed=True)

        try:
            logger = JsonlLogger(temporary_root / "logs" / "smoke-public-subtitles.jsonl")
            logger.emit(
                level="INFO",
                event="smoke.started",
                run_id=run_id,
                stage="smoke-public-subtitles",
                safe_message="restricted subtitle smoke started",
            )
            metadata_provider = self._metadata_provider_factory(_HTTP_TIMEOUT_SECONDS)
            subtitle_adapter = self._subtitle_adapter_factory(_HTTP_TIMEOUT_SECONDS)
            failed = 0
            for video_id in video_ids:
                if not self._run_target(
                    video_id=video_id,
                    metadata_provider=metadata_provider,
                    subtitle_adapter=subtitle_adapter,
                    logger=logger,
                    run_id=run_id,
                ):
                    failed += 1

            logger.emit(
                level="INFO" if failed == 0 else "ERROR",
                event="smoke.finished" if failed == 0 else "smoke.failed",
                run_id=run_id,
                stage="smoke-public-subtitles",
                safe_message=f"targets={len(video_ids)} failed={failed}",
            )
        except OSError:
            return CommandOutcome(local_resource_failed=True)
        except Exception:  # noqa: BLE001 - do not expose factory failures
            return CommandOutcome(local_resource_failed=True)
        return CommandOutcome(attempted=len(video_ids), failed=failed)

    def _run_target(
        self,
        *,
        video_id: str,
        metadata_provider: _MetadataProvider,
        subtitle_adapter: _SubtitleAdapter,
        logger: JsonlLogger,
        run_id: str,
    ) -> bool:
        started = time.monotonic()
        metadata_calls = 0
        enumerate_calls = 0
        read_calls = 0
        try:
            metadata_calls = 1
            metadata_provider.fetch(video_id)
            enumerate_calls = 1
            listing = subtitle_adapter.enumerate_tracks(video_id)
            ranked = rank_subtitle_candidates(
                listing.tracks,
                _language_preferences(listing.tracks),
            )
            if not ranked:
                raise _SmokeTargetError(ErrorCode.CONTENT_UNAVAILABLE)
            read_calls = 1
            result = subtitle_adapter.read_track(ranked[0].track)
            del result
        except Exception as error:  # noqa: BLE001 - emit only a fixed safe category
            logger.emit(
                level="ERROR",
                event="smoke.target.failed",
                run_id=run_id,
                stage="smoke-public-subtitles",
                video_id=video_id,
                error_code=_error_code(error),
                duration_ms=int((time.monotonic() - started) * 1000),
                safe_message=(
                    "metadata_calls="
                    f"{metadata_calls} enumerate_tracks_calls={enumerate_calls} "
                    f"read_track_calls={read_calls}"
                ),
            )
            return False

        logger.emit(
            level="INFO",
            event="smoke.target.finished",
            run_id=run_id,
            stage="smoke-public-subtitles",
            video_id=video_id,
            duration_ms=int((time.monotonic() - started) * 1000),
            safe_message=(
                "metadata_calls=1 enumerate_tracks_calls=1 read_track_calls=1"
            ),
        )
        return True


class _SmokeTargetError(Exception):
    def __init__(self, code: ErrorCode) -> None:
        self.code = code


def _valid_inputs(temporary_root: Path, video_ids: Sequence[str]) -> bool:
    if not temporary_root.is_absolute() or temporary_root.exists() or temporary_root.is_symlink():
        return False
    if not temporary_root.parent.is_dir() or not 1 <= len(video_ids) <= 3:
        return False
    return len(set(video_ids)) == len(video_ids) and all(
        _VIDEO_ID_RE.fullmatch(video_id) is not None for video_id in video_ids
    )


def _initialize_root(temporary_root: Path, *, now: datetime) -> None:
    temporary_root.mkdir(mode=0o700)
    (temporary_root / "data").mkdir(mode=0o700)
    (temporary_root / "test-vault").mkdir(mode=0o700)
    (temporary_root / "logs").mkdir(mode=0o700)
    SQLiteStateRepository(temporary_root / "state.sqlite").initialize(now=now)


def _language_preferences(tracks: Sequence[SubtitleTrack]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(track.language for track in tracks))


def _error_code(error: Exception) -> str:
    if isinstance(error, _SmokeTargetError):
        return error.code.value
    app_error = getattr(error, "error", None)
    if isinstance(app_error, AppError):
        return app_error.code.value
    return ErrorCode.PROVIDER_UNAVAILABLE.value


__all__ = ["PublicSubtitleSmoke"]
