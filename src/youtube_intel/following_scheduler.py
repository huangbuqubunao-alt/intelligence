"""Deadline scheduling over the existing durable Following authority."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from youtube_intel.following_tracking import (
    AUTOMATIC_REFUSAL_HEALTH,
    FollowingTrackingService,
    _stamp,
)
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.source_run import SOURCE_RUN_ACTIVE_STATES

AUTOMATIC_CHECK_PREFIX = "following-auto:"
MAX_CLOCK_RECONCILIATION_SECONDS = 300.0


class FollowingScheduler:
    """Admit one due command; the existing worker owns all execution.

    No in-memory source jobs, timer queue, provider calls or model authority.
    Every decision re-reads SQLite. A command's existing identity records its
    automatic origin and due frontier without a second schedule authority.
    """

    def __init__(
        self, tracking: FollowingTrackingService,
        product: ProductOrchestrationService, *, now: Callable[[], datetime],
    ) -> None:
        self.tracking = tracking
        self.product = product
        self.now = now

    def _eligible(self) -> list[tuple[datetime, str, str]]:
        states = tuple(state.value for state in SOURCE_RUN_ACTIVE_STATES)
        with self.tracking.repository._connect() as connection:
            rows = connection.execute(
                "SELECT s.source_id,s.provider,t.next_check_at FROM "
                "source_tracking_state t JOIN source_subscriptions s USING(source_id) "
                "WHERE s.enabled=1 AND t.health NOT IN "
                "(" + ",".join("?" for _ in AUTOMATIC_REFUSAL_HEALTH) + ") "
                "AND NOT EXISTS(SELECT 1 FROM source_runs r WHERE r.source_id=s.source_id "
                "AND r.state IN (" + ",".join("?" for _ in states) + "))",
                (*sorted(AUTOMATIC_REFUSAL_HEALTH), *states),
            ).fetchall()
        eligible = []
        for row in rows:
            provider = self.tracking.providers.get(row["provider"])
            if provider is None or not getattr(provider, "available", True):
                continue
            try:
                due = _stamp(row["next_check_at"])
            except (ValueError, TypeError):
                # Invalid authority is already projected as STATE_INVALID;
                # never replace it or hammer its provider.
                continue
            eligible.append((due, row["source_id"], row["next_check_at"]))
        return sorted(eligible)

    def admit_due(self) -> None:
        eligible = self._eligible()
        if eligible and eligible[0][0] <= self.now():
            _, source_id, due = eligible[0]
            self.product.check_source(
                source_id, command_id=AUTOMATIC_CHECK_PREFIX + source_id + ":" + due,
                automatic=True,
            )

    def wait_seconds(self) -> float | None:
        eligible = self._eligible()
        if not eligible:
            return None
        return min(MAX_CLOCK_RECONCILIATION_SECONDS,
                   max(0.0, (eligible[0][0] - self.now()).total_seconds()))
