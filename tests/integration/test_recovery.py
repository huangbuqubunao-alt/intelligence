"""Recovery-focused integration tests for TASK-010 retry helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from youtube_intel.domain import AppError, ErrorCode
from youtube_intel.retry import RetryPolicy


def test_retry_policy_respects_provider_retry_after_and_exponential_cap() -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)
    policy = RetryPolicy(base_delay_seconds=2, max_delay_seconds=5, jitter_ratio=0)

    assert policy.retry_at(
        AppError(code=ErrorCode.TRANSIENT_NETWORK, message="temporary", retryable=True),
        attempt_count=3,
        now=now,
    ) == datetime(2026, 7, 23, 0, 0, 5, tzinfo=UTC)
    assert policy.retry_at(
        AppError(code=ErrorCode.RATE_LIMITED, message="slow down", retryable=True, retry_after_seconds=9),
        attempt_count=1,
        now=now,
    ) == datetime(2026, 7, 23, 0, 0, 9, tzinfo=UTC)
    assert policy.retry_at(
        AppError(code=ErrorCode.CONTENT_UNAVAILABLE, message="gone", retryable=False),
        attempt_count=1,
        now=now,
    ) is None
