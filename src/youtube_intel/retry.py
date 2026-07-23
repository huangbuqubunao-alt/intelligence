"""Deterministic retry timing for the application orchestration layer."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from youtube_intel.domain import AppError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Calculate retry times without changing Job or Pipeline state."""

    base_delay_seconds: float
    max_delay_seconds: float
    jitter_ratio: float
    random_source: Callable[[], float] = field(default=random.random, compare=False)

    def __post_init__(self) -> None:
        if self.base_delay_seconds <= 0 or self.max_delay_seconds <= 0:
            raise ValueError("retry delays must be positive")
        if self.base_delay_seconds > self.max_delay_seconds:
            raise ValueError("base retry delay must not exceed maximum retry delay")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("retry jitter ratio must be in 0..1")

    def retry_at(
        self,
        error: AppError,
        *,
        attempt_count: int,
        now: datetime,
    ) -> datetime | None:
        """Return the provider-directed or exponential retry time, if retryable."""

        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ValueError("retry clock must return a UTC datetime")
        if attempt_count <= 0:
            raise ValueError("attempt_count must be positive")
        if not error.retryable:
            return None
        if error.retry_after_seconds is not None:
            return now + timedelta(seconds=error.retry_after_seconds)
        capped_delay = min(
            self.max_delay_seconds,
            self.base_delay_seconds * (2 ** (attempt_count - 1)),
        )
        random_value = self.random_source()
        if not 0 <= random_value <= 1:
            raise ValueError("retry random source must return a value in 0..1")
        jitter = (random_value * 2 - 1) * self.jitter_ratio
        delay = min(self.max_delay_seconds, capped_delay * (1 + jitter))
        return now + timedelta(seconds=delay)
