"""Offline unit tests for scoring sampling, cache, and threshold policy."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    ScoreResult,
    VideoMetadata,
)
from youtube_intel.scoring import (
    InMemoryScoringCache,
    ScoringService,
    build_scoring_input,
    sample_transcript,
)


def _settings(*, max_transcript_chars: int = 8) -> LocalScoringSettings:
    return LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + ("a" * 64),
        max_transcript_chars=max_transcript_chars,
        max_description_chars=5,
    )


def _video(*, description: str = "abcdef") -> VideoMetadata:
    return VideoMetadata(
        video_id="video-123",
        channel_id="channel-123",
        channel_name="Example Channel",
        title="A useful title",
        description=description,
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 7, 19, tzinfo=UTC),
        duration_seconds=120,
        default_language="en",
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


class _CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def score(self, scoring_input: object) -> ScoreResult:
        self.calls += 1
        request_hash = getattr(scoring_input, "request_hash")
        return ScoreResult(
            schema_version="score-result-v1",
            score=6.5,
            reason="Useful but below the configured summary threshold.",
            topics=("product",),
            should_summarize=True,
            provider="fake-scoring",
            model="fake-model",
            prompt_version="scoring-prompt-v1",
            request_hash=request_hash,
        )


def test_sample_transcript_uses_bounded_head_center_tail_segments() -> None:
    sample = sample_transcript("0123456789", max_chars=8)

    assert (sample.head, sample.body, sample.tail) == ("012", "456", "89")
    assert sample.selected_char_count == 8
    assert sample.sampling_version == "sampling-v1"


def test_scoring_input_hash_covers_truncated_description_and_sample() -> None:
    settings = _settings()

    first = build_scoring_input(
        video=_video(description="abcdef"),
        transcript_text="0123456789",
        language="en",
        settings=settings,
    )
    same_prefix = build_scoring_input(
        video=_video(description="abcdeZ"),
        transcript_text="0123456789",
        language="en",
        settings=settings,
    )
    changed_sample = build_scoring_input(
        video=_video(description="abcdef"),
        transcript_text="012345678X",
        language="en",
        settings=settings,
    )

    assert first.request_hash == same_prefix.request_hash
    assert first.request_hash != changed_sample.request_hash
    assert first.sample.source_content_hash == first.transcript_content_hash


def test_scoring_service_caches_canonical_input_and_records_policy_disagreement() -> None:
    provider = _CountingProvider()
    service = ScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7.0,
        cache=InMemoryScoringCache(),
    )

    first = service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
    )
    second = service.score(
        video=_video(),
        transcript_text="0123456789",
        language="en",
    )

    assert provider.calls == 1
    assert first.result == second.result
    assert first.decision.final_should_summarize is False
    assert first.decision.model_disagrees is True
    assert [item.code for item in first.call.diagnostics] == [
        "MODEL_POLICY_DISAGREEMENT"
    ]
    assert [item.code for item in second.call.diagnostics] == [
        "CACHE_HIT",
        "MODEL_POLICY_DISAGREEMENT",
    ]


def test_sample_transcript_rejects_text_too_short_for_frozen_contract() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        sample_transcript("hi", max_chars=8)
