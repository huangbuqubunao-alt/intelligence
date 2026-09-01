"""Offline local API fixture for browser product verification only.

It deliberately supplies a ``VerifiedScoringRead``-shaped value to the local
API boundary.  Production ``serve-api`` constructs the real reader; this
fixture exists solely to exercise the browser with deterministic safe DTOs.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from youtube_intel.domain import Availability, LiveStatus, VideoMetadata
from youtube_intel.local_api import LocalApiApplication, serve_loopback
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.scoring import AuthoritativeScoringReader
from youtube_intel.state import SQLiteStateRepository

_NOW = datetime(2026, 9, 1, tzinfo=UTC)


class _FixtureVerifiedReader:
    def read(self, video_id: str) -> object:
        if video_id != "abcdefghijk":
            raise ValueError("no verified fixture result")
        return SimpleNamespace(
            scoring_outcome=SimpleNamespace(
                result=SimpleNamespace(
                    score=8.5,
                    reason="Fixture evidence is verified.",
                    topics=("product", "strategy"),
                    provider="fixture",
                    model="verified-model",
                    prompt_version="v1",
                ),
                decision=SimpleNamespace(final_should_summarize=True),
                call=SimpleNamespace(finished_at=_NOW),
            ),
            scoring_success_provenance="VERIFIED_FIXTURE",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    repository = SQLiteStateRepository(Path(args.database))
    repository.initialize(now=_NOW)
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id="abcdefghijk",
            channel_id="UC1234567890123456789012",
            channel_name="Fixture channel",
            title="Verified fixture video",
            description="Fixture only.",
            source_url="https://www.youtube.com/watch?v=abcdefghijk",
            published_at=_NOW,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=_NOW,
    )
    repository.upsert_video_metadata(
        VideoMetadata(
            video_id="unverif0001",
            channel_id="UC1234567890123456789012",
            channel_name="Fixture channel",
            title="Unverified fixture video",
            description="A synthetic rejected scoring attempt is never exposed.",
            source_url="https://www.youtube.com/watch?v=unverif0001",
            published_at=_NOW,
            duration_seconds=60,
            default_language="en",
            available_languages=("en",),
            live_status=LiveStatus.NONE,
            availability=Availability.PUBLIC,
        ),
        pipeline_version="fixture-v1",
        now=_NOW,
    )
    service = ProductOrchestrationService(repository, now=lambda: _NOW)
    application = LocalApiApplication(
        repository,
        service,
        scoring_reader=cast(AuthoritativeScoringReader, _FixtureVerifiedReader()),
        timezone="Asia/Shanghai",
        now=lambda: _NOW,
    )
    serve_loopback(application, port=args.port).serve_forever()


if __name__ == "__main__":
    main()
