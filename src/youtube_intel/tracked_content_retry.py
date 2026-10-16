"""Explicit tracked Content retry application boundary; never the full pipeline."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from youtube_intel.domain import VideoMetadata
from youtube_intel.state import SQLiteStateRepository, VideoRecord
from youtube_intel.tracked_retry_context import RetryConflict, store_lock
from youtube_intel.tracked_retry_store import admit, canonical, identifier, public, read
from youtube_intel.transcripts import (
    FORMAT_POLICY_VERSION,
    NORMALIZATION_VERSION,
    QUALITY_POLICY_VERSION,
    SELECTION_POLICY_VERSION,
    SubtitleAdapter,
)


class TrackedContentRetryService:
    def __init__(self, repository: SQLiteStateRepository, data_root: Path, *,
                 adapter_factory: Callable[[], SubtitleAdapter], language_preferences: Sequence[str],
                 metadata_for_video: Callable[[VideoRecord], VideoMetadata], now: Callable[[], datetime] | None = None) -> None:
        self.repository = repository
        self.data_root = data_root.resolve()
        repository.bind_source_storage(self.data_root)
        self.adapter_factory = adapter_factory
        self.languages = tuple(language_preferences)
        self.metadata_for_video = metadata_for_video
        self.now = now or (lambda: datetime.now(UTC))

    def request(self, video_id: str, *, command_id: str, expected_job_id: str) -> dict[str, Any]:
        identifier(command_id)
        identifier(expected_job_id)
        with self.repository._connect(read_only=True) as connection:
            prior = connection.execute("SELECT request_id FROM tracked_content_retry_requests WHERE video_id=? AND command_id=? LIMIT 2", (video_id, command_id)).fetchall()
            if prior:
                if len(prior) != 1:
                    raise RetryConflict("Content retry command is ambiguous")
                request, execution = read(connection, prior[0][0])
                client = {"contract": request["contract"], "operation": request["operation"], "video_id": video_id, "command_id": command_id, "expected_job_id": expected_job_id}
                if request["client_input_json"] != canonical(client):
                    raise RetryConflict("Content retry command input conflicts")
                return public(request, execution)
        video = self.repository.get_video(video_id)
        if video is None:
            raise RetryConflict("Content is unavailable")
        adapter = self.adapter_factory()
        parameters = {"language_preferences": list(self.languages), "adapter_name": adapter.provider_name,
            "adapter_version": adapter.provider_version, "selection_policy_version": SELECTION_POLICY_VERSION,
            "format_policy_version": FORMAT_POLICY_VERSION, "native_timing_policy_version": "tracked-native-timed-v1",
            "normalization_version": NORMALIZATION_VERSION, "quality_policy_version": QUALITY_POLICY_VERSION,
            "metadata_snapshot": self.metadata_for_video(video).model_dump(mode="json"), "local_finalize_max_attempts": 3}
        with store_lock(self.repository._database_path):
            return admit(self.repository, video_id, command_id=command_id, expected_job_id=expected_job_id, parameters=parameters, now=self.now())
