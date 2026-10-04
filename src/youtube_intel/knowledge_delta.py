"""Stateless, factual Home projection over a single seven-day SQLite snapshot.

These are recorded changes, not a new issuer of Intelligence/Topic conclusions.
Original titles are navigation context; no generated interpretation is read.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from youtube_intel.state import (
    SQLiteStateRepository,
    StateStoreError,
    format_utc_datetime,
)

DeltaKind = Literal[
    "content_completed",
    "intelligence_added",
    "intelligence_revised",
    "topic_updated",
    "source_health",
]
Availability = Literal["available", "partial", "unavailable"]
KINDS: tuple[DeltaKind, ...] = (
    "content_completed",
    "intelligence_added",
    "intelligence_revised",
    "topic_updated",
    "source_health",
)
DETAIL_LIMIT = 2
INTELLIGENCE_KINDS: tuple[DeltaKind, ...] = (
    "intelligence_added",
    "intelligence_revised",
)


@dataclass(frozen=True, slots=True)
class DeltaTarget:
    kind: Literal["content", "intelligence", "topic", "source"]
    id: str


@dataclass(frozen=True, slots=True)
class DeltaFacts:
    revision_count: int | None = None
    evidence_before: int | None = None
    evidence_after: int | None = None
    evidence_set_changed: bool | None = None
    state_before: str | None = None
    state_after: str | None = None
    state_changed_at: str | None = None
    topic_event_count: int | None = None
    failure_count: int | None = None


@dataclass(frozen=True, slots=True)
class DeltaItem:
    id: str
    kind: DeltaKind
    label: str
    title: str | None
    target: DeltaTarget
    occurred_at: str
    facts: DeltaFacts = DeltaFacts()


@dataclass(frozen=True, slots=True)
class DeltaCategory:
    kind: DeltaKind
    status: Literal["available", "unavailable"]
    count: int | None
    items: tuple[DeltaItem, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeDelta:
    window_start: str
    window_end: str
    timezone: str
    status: Availability
    categories: tuple[DeltaCategory, ...]
    detail_limit: int = DETAIL_LIMIT

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["categories"] = [
            {**asdict(category), "items": [asdict(item) for item in category.items]}
            for category in self.categories
        ]
        return result


_CONTENT = """
SELECT video_id, substr(title, 1, 240) AS title, delta_time(completed_at) AS completed_at,
       COUNT(*) OVER () AS total
FROM videos
WHERE pipeline_status = 'COMPLETE'
  AND delta_time(completed_at) BETWEEN :start AND :end
  AND delta_time(discovered_at) <= delta_time(completed_at)
ORDER BY completed_at DESC, video_id ASC
LIMIT :limit
"""


def _normalized_timestamp(value: object) -> str | None:
    """Exact UTC comparison; accept aware legacy ISO forms, never guess a zone."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return format_utc_datetime(parsed.astimezone(UTC))
    except (ValueError, OverflowError):
        return None


# Read facts only when recent revision metadata has the structural proof already
# required by the existing Intelligence reader. Missing authority is partial,
# never silently reported as zero or newly admitted Intelligence.
_INTELLIGENCE_AUTHORITY = """
SELECT EXISTS (
    SELECT 1 FROM intelligence_revisions r
    LEFT JOIN intelligence_state_history h ON h.revision_id = r.revision_id
    LEFT JOIN intelligence_revisions prior ON prior.revision_id = r.prior_revision_id
    LEFT JOIN intelligence_state_history prior_state ON prior_state.revision_id = prior.revision_id
    WHERE delta_time(r.created_at) BETWEEN :start AND :end
      AND r.claim_kind <> 'UNCLASSIFIED'
      AND (
        h.revision_id IS NULL OR h.intelligence_id <> r.intelligence_id
        OR delta_time(h.created_at) IS NOT delta_time(r.created_at)
        OR (r.revision_number = 1 AND (r.prior_revision_id IS NOT NULL OR h.state <> 'NEW' OR h.prior_state IS NOT NULL))
        OR (r.revision_number > 1 AND (
            prior.revision_id IS NULL OR prior.intelligence_id <> r.intelligence_id
            OR prior.revision_number <> r.revision_number - 1
            OR delta_time(prior.created_at) > delta_time(r.created_at)
            OR prior_state.state IS NULL OR h.prior_state IS NOT prior_state.state
        ))
        OR NOT EXISTS (SELECT 1 FROM intelligence_revision_evidence link
                       WHERE link.revision_id = r.revision_id AND link.evidence_id = h.evidence_id)
        OR EXISTS (SELECT 1 FROM intelligence_revision_evidence link
                   LEFT JOIN evidence e ON e.evidence_id = link.evidence_id
                   LEFT JOIN artifacts a ON a.artifact_id = e.artifact_id
                   WHERE link.revision_id = r.revision_id AND (
                     e.evidence_id IS NULL OR a.artifact_id IS NULL OR a.video_id <> e.video_id
                     OR NOT EXISTS (SELECT 1 FROM dependency_edges edge
                                    WHERE edge.dependent_revision_id = r.revision_id
                                      AND edge.relation = 'EVIDENCE_SUPPORT'
                                      AND edge.input_evidence_id = link.evidence_id)
                   ))
      )
) AS invalid
"""

# Revisions and their immutable state/support are admission metadata, not card
# text. Coalesce per identity; revision 1 determines admission, not allocation.
_INTELLIGENCE = """
WITH recent AS (
    SELECT r.revision_id, r.intelligence_id, r.revision_number, r.prior_revision_id,
           delta_time(r.created_at) AS created_at, h.state, h.prior_state,
           ROW_NUMBER() OVER (PARTITION BY r.intelligence_id ORDER BY r.revision_number DESC) AS latest,
           SUM(r.revision_number > 1) OVER (PARTITION BY r.intelligence_id) AS revision_count,
           FIRST_VALUE(r.prior_revision_id) OVER (
               PARTITION BY r.intelligence_id ORDER BY r.revision_number
           ) AS baseline_id
    FROM intelligence_revisions r
    JOIN intelligences i ON i.intelligence_id = r.intelligence_id
    JOIN intelligence_state_history h ON h.revision_id = r.revision_id
      AND h.intelligence_id = r.intelligence_id
    WHERE delta_time(r.created_at) BETWEEN :start AND :end
      AND delta_time(h.created_at) = delta_time(r.created_at) AND r.claim_kind <> 'UNCLASSIFIED'
      AND EXISTS (SELECT 1 FROM intelligence_revision_evidence support
                  JOIN evidence e ON e.evidence_id = support.evidence_id
                  WHERE support.revision_id = r.revision_id AND e.evidence_id = h.evidence_id)
), significant_states AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY intelligence_id ORDER BY revision_number DESC
    ) AS state_latest
    FROM recent
    WHERE prior_state IS NOT NULL AND prior_state <> state
      AND state IN ('PENDING_CONFIRMATION', 'CONFIRMED', 'DISPUTED', 'INVALIDATED', 'OVERTURNED')
), classified AS (
    SELECT recent.*,
           CASE WHEN delta_time(first.created_at) >= :start THEN 'intelligence_added'
                ELSE 'intelligence_revised' END AS kind,
           CASE WHEN delta_time(first.created_at) >= :start THEN first.revision_id
                ELSE baseline_id END AS comparison_id
    FROM recent
    JOIN intelligence_revisions first ON first.intelligence_id = recent.intelligence_id
      AND first.revision_number = 1 AND delta_time(first.created_at) <= recent.created_at
    WHERE latest = 1
), ranked AS (
    SELECT *, COUNT(*) OVER (PARTITION BY kind) AS total,
           ROW_NUMBER() OVER (PARTITION BY kind ORDER BY created_at DESC, intelligence_id ASC) AS rank
    FROM classified
), bounded AS (
    SELECT * FROM ranked WHERE rank <= :limit
)
SELECT bounded.*,
       state_change.prior_state AS state_before, state_change.state AS state_after,
       state_change.created_at AS state_changed_at,
       (SELECT substr(v.title, 1, 240) FROM intelligence_revision_evidence support
        JOIN evidence e ON e.evidence_id = support.evidence_id
        JOIN videos v ON v.video_id = e.video_id
        WHERE support.revision_id = bounded.revision_id
        ORDER BY v.video_id, e.evidence_id LIMIT 1) AS title,
       (SELECT COUNT(*) FROM intelligence_revision_evidence WHERE revision_id = comparison_id) AS evidence_before,
       (SELECT COUNT(*) FROM intelligence_revision_evidence WHERE revision_id = bounded.revision_id) AS evidence_after,
       (EXISTS (SELECT evidence_id FROM intelligence_revision_evidence WHERE revision_id = comparison_id
                EXCEPT SELECT evidence_id FROM intelligence_revision_evidence WHERE revision_id = bounded.revision_id)
        OR EXISTS (SELECT evidence_id FROM intelligence_revision_evidence WHERE revision_id = bounded.revision_id
                   EXCEPT SELECT evidence_id FROM intelligence_revision_evidence WHERE revision_id = comparison_id)) AS evidence_set_changed
FROM bounded
LEFT JOIN significant_states state_change
  ON state_change.intelligence_id = bounded.intelligence_id AND state_change.state_latest = 1
ORDER BY kind, created_at DESC, intelligence_id ASC
"""

_STATE_LABELS = {
    "NEW": "New",
    "UPDATED": "Updated",
    "PENDING_CONFIRMATION": "Pending confirmation",
    "CONFIRMED": "Confirmed",
    "DISPUTED": "Disputed",
    "INVALIDATED": "Invalidated",
    "OVERTURNED": "Overturned",
}

_TOPICS = """
WITH changed AS (
    SELECT t.topic_id, substr(t.name, 1, 240) AS title,
           MAX(delta_time(event.created_at)) AS occurred_at, COUNT(*) AS event_count
    FROM topics t
    JOIN topic_timeline_events event ON event.topic_id = t.topic_id
    JOIN topic_memberships membership ON membership.membership_id = event.primary_membership_id
      AND membership.topic_id = t.topic_id
    JOIN intelligence_revisions r ON r.revision_id = membership.revision_id
      AND r.intelligence_id = membership.intelligence_id
    WHERE t.lifecycle = 'ACTIVE' AND delta_time(event.created_at) BETWEEN :start AND :end
      AND delta_time(membership.created_at) <= delta_time(event.created_at)
      AND delta_time(r.created_at) <= delta_time(event.created_at)
      AND EXISTS (SELECT 1 FROM topic_timeline_event_memberships dependency
                  WHERE dependency.event_id = event.event_id
                    AND dependency.membership_id = membership.membership_id)
      AND EXISTS (SELECT 1 FROM topic_membership_evidence support
                  JOIN intelligence_revision_evidence original
                    ON original.evidence_id = support.evidence_id AND original.revision_id = r.revision_id
                  WHERE support.membership_id = membership.membership_id)
    GROUP BY t.topic_id
)
SELECT *, COUNT(*) OVER () AS total FROM changed
ORDER BY occurred_at DESC, topic_id ASC LIMIT :limit
"""

# Only discovery-blocked runs with the explicit execution-condition reason are
# source freshness failures. Model/budget/selection/child failures are excluded.
# A successful complete check after >=2 consecutive blocked discoveries is
# recovery of checking; it does not assert that any new Content was discovered.
_SOURCE_HEALTH = """
WITH attempts AS (
    SELECT s.source_id, s.display_name, e.event_id, delta_time(e.occurred_at) AS occurred_at,
           e.state = 'COMPLETED' AS success,
           delta_time(e.occurred_at) || ':' || printf('%020d', e.event_id) AS sort_key
    FROM source_run_state_events e
    JOIN source_runs run ON run.run_id = e.run_id
    JOIN source_subscriptions s ON s.source_id = run.source_id
    WHERE s.enabled = 1 AND s.source_type = 'CHANNEL'
      AND run.trigger IN ('MANUAL_CHECK_NOW', 'SCHEDULED_SOURCE_RUN')
      AND delta_time(e.occurred_at) BETWEEN :start AND :end
      AND delta_time(run.created_at) <= delta_time(e.occurred_at)
      AND (e.state = 'COMPLETED' OR (
          e.state = 'NEEDS_ATTENTION' AND e.attention_reason = 'EXECUTION_CONDITION_UNRESOLVED'
          AND EXISTS (SELECT 1 FROM source_run_checkpoint_events checkpoint
                      WHERE checkpoint.run_id = run.run_id AND checkpoint.checkpoint = 'DISCOVERY'
                        AND checkpoint.event_status = 'BLOCKED' AND delta_time(checkpoint.created_at) <= delta_time(e.occurred_at))
          AND NOT EXISTS (SELECT 1 FROM source_run_checkpoint_events checkpoint
                          WHERE checkpoint.run_id = run.run_id AND checkpoint.checkpoint = 'DISCOVERY'
                            AND checkpoint.event_status = 'COMPLETED')
      ))
    UNION ALL
    SELECT s.source_id, s.display_name, check_record.check_id,
           delta_time(check_record.finished_at),
           check_record.status = 'SUCCEEDED' AND check_record.complete = 1,
           delta_time(check_record.finished_at) || ':' || check_record.check_id
    FROM source_checks check_record
    JOIN source_subscriptions s ON s.source_id = check_record.source_id
    WHERE s.enabled = 1 AND s.source_type = 'CREATOR'
      AND check_record.status IN ('SUCCEEDED','FAILED','INTERRUPTED')
      AND delta_time(check_record.finished_at) IS NOT NULL
), ordered AS (
    SELECT *, COALESCE(SUM(success) OVER (
        PARTITION BY source_id ORDER BY sort_key
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ), 0) AS preceding_successes
    FROM attempts
), measured AS (
    SELECT *, SUM(NOT success) OVER (
        PARTITION BY source_id, preceding_successes ORDER BY sort_key
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS failure_count
    FROM ordered
), candidates AS (
    SELECT source_id, substr(display_name, 1, 240) AS title, occurred_at, failure_count,
           CASE WHEN success THEN 'Source checks resumed'
                ELSE 'Source discovery repeatedly blocked' END AS label, 1 AS priority, sort_key
    FROM measured WHERE failure_count >= 2
    UNION ALL
    SELECT source_id, substr(display_name, 1, 240), delta_time(last_checked_at), NULL,
           'Source check failed', 0, delta_time(last_checked_at)
    FROM source_subscriptions
    WHERE enabled = 1 AND source_type = 'CHANNEL'
      AND last_error_code = 'SOURCE_CHECK_FAILED'
      AND delta_time(last_checked_at) BETWEEN :start AND :end
), deduplicated AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY source_id ORDER BY occurred_at DESC, priority DESC, sort_key DESC
    ) AS latest FROM candidates
)
SELECT *, COUNT(*) OVER () AS total FROM deduplicated WHERE latest = 1
ORDER BY occurred_at DESC, source_id ASC LIMIT :limit
"""


class KnowledgeDeltaService:
    def __init__(
        self,
        repository: SQLiteStateRepository,
        *,
        now: Callable[[], datetime],
        timezone: str = "Asia/Shanghai",
    ) -> None:
        ZoneInfo(timezone)
        self._repository = repository
        self._now = now
        self._timezone = timezone

    def read(self) -> KnowledgeDelta:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Knowledge Delta clock must be timezone-aware")
        end = now.astimezone(UTC)
        start = end - timedelta(days=7)
        params: dict[str, str | int] = {
            "start": format_utc_datetime(start),
            "end": format_utc_datetime(end),
            "limit": DETAIL_LIMIT,
        }
        categories = {kind: DeltaCategory(kind, "available", 0, ()) for kind in KINDS}
        connection: sqlite3.Connection | None = None
        try:
            connection = self._repository._connect(read_only=True)
            connection.create_function(
                "delta_time", 1, _normalized_timestamp, deterministic=True
            )
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            try:
                rows = connection.execute(_CONTENT, params).fetchall()
                categories["content_completed"] = DeltaCategory(
                    "content_completed",
                    "available",
                    int(rows[0]["total"]) if rows else 0,
                    tuple(
                        DeltaItem(
                            id=f"content-completed:{row['video_id']}",
                            kind="content_completed",
                            label="Content completed",
                            title=row["title"],
                            target=DeltaTarget("content", row["video_id"]),
                            occurred_at=row["completed_at"],
                        )
                        for row in rows
                    ),
                )
            except (sqlite3.Error, ValueError, TypeError):
                categories["content_completed"] = DeltaCategory(
                    "content_completed", "unavailable", None, ()
                )
            try:
                if connection.execute(_INTELLIGENCE_AUTHORITY, params).fetchone()[
                    "invalid"
                ]:
                    raise ValueError("Recent revision authority is incomplete")
                rows = connection.execute(_INTELLIGENCE, params).fetchall()
                for kind in INTELLIGENCE_KINDS:
                    matched = [row for row in rows if row["kind"] == kind]
                    items = tuple(self._intelligence_item(row) for row in matched)
                    categories[kind] = DeltaCategory(
                        kind,
                        "available",
                        int(matched[0]["total"]) if matched else 0,
                        items,
                    )
            except (sqlite3.Error, ValueError, TypeError, KeyError):
                for kind in INTELLIGENCE_KINDS:
                    categories[kind] = DeltaCategory(kind, "unavailable", None, ())
            for kind, query in (
                ("topic_updated", _TOPICS),
                ("source_health", _SOURCE_HEALTH),
            ):
                try:
                    rows = connection.execute(query, params).fetchall()
                    items = tuple(self._context_item(row, kind) for row in rows)
                    categories[kind] = DeltaCategory(
                        kind,
                        "available",
                        int(rows[0]["total"]) if rows else 0,
                        items,
                    )
                except (sqlite3.Error, ValueError, TypeError, KeyError):
                    categories[kind] = DeltaCategory(kind, "unavailable", None, ())
        except (sqlite3.Error, StateStoreError):
            categories = {
                kind: DeltaCategory(kind, "unavailable", None, ()) for kind in KINDS
            }
        finally:
            if connection is not None:
                connection.close()
        unavailable = sum(
            category.status == "unavailable" for category in categories.values()
        )
        status: Availability = (
            "unavailable"
            if unavailable == len(KINDS)
            else "partial"
            if unavailable
            else "available"
        )
        return KnowledgeDelta(
            window_start=str(params["start"]),
            window_end=str(params["end"]),
            timezone=self._timezone,
            status=status,
            categories=tuple(categories[kind] for kind in KINDS),
        )

    @staticmethod
    def _intelligence_item(row: sqlite3.Row) -> DeltaItem:
        kind: DeltaKind = (
            "intelligence_added"
            if row["kind"] == "intelligence_added"
            else "intelligence_revised"
        )
        return DeltaItem(
            id=f"{kind}:{row['intelligence_id']}:{row['revision_id']}",
            kind=kind,
            label="Intelligence admitted"
            if kind == "intelligence_added"
            else "Intelligence revised",
            title=row["title"],
            target=DeltaTarget("intelligence", row["intelligence_id"]),
            occurred_at=row["created_at"],
            facts=DeltaFacts(
                revision_count=int(row["revision_count"]),
                evidence_before=int(row["evidence_before"]),
                evidence_after=int(row["evidence_after"]),
                evidence_set_changed=bool(row["evidence_set_changed"]),
                state_before=_STATE_LABELS[row["state_before"]]
                if row["state_before"]
                else None,
                state_after=_STATE_LABELS[row["state_after"]]
                if row["state_after"]
                else None,
                state_changed_at=row["state_changed_at"],
            ),
        )

    @staticmethod
    def _context_item(row: sqlite3.Row, kind: DeltaKind) -> DeltaItem:
        topic = kind == "topic_updated"
        identity = row["topic_id"] if topic else row["source_id"]
        return DeltaItem(
            id=f"{kind}:{identity}:{row['occurred_at']}",
            kind=kind,
            label="Topic received material" if topic else row["label"],
            title=row["title"],
            target=DeltaTarget("topic" if topic else "source", identity),
            occurred_at=row["occurred_at"],
            facts=DeltaFacts(
                topic_event_count=int(row["event_count"]) if topic else None,
                failure_count=row["failure_count"] if not topic else None,
            ),
        )
