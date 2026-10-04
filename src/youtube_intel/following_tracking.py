"""Portable Following discovery authority, using ordinary source and Content domains.

An offset is never a verified watermark. Incomplete scans keep the last verified
frontier and expose their gap. The identity ledger also records pending enrollment
before any Content acquisition, so interruption cannot forget a discovered video.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.orchestration import ProcessingPolicy, SourceType
from youtube_intel.providers.bilibili import BilibiliError, normalize_input
from youtube_intel.providers.bilibili_creator import (
    PAGE_SIZE,
    CreatorVideo,
    normalize_creator,
)
from youtube_intel.source_authority import read_managed, verify_source
from youtube_intel.state import (
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    format_utc_datetime,
)

MAX_PAGES = 3
MAX_ENROLLMENTS = 5
CHECK_SECONDS = 180.0
COOLDOWN = timedelta(minutes=15)
LEASE = timedelta(minutes=10)
_CHECK_SLOT = threading.BoundedSemaphore(1)
_HEALTH = {"NETWORK_UNAVAILABLE": "OFFLINE", "METADATA_FAILED": "PROVIDER_ERROR",
           "RESPONSE_TOO_LARGE": "PROVIDER_ERROR", "SOURCE_UNTRUSTED": "STATE_INVALID"}


def _stamp(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError("tracking time must be UTC")
    return stamp


def verify_tracking(connection: sqlite3.Connection, source_id: str | None = None, *,
                    repository: SQLiteStateRepository | None = None) -> None:
    """Reject corrupt portable tracking, never silently bootstrap it from zero."""
    if connection.execute("SELECT 1 FROM source_tracking_state t JOIN source_subscriptions s USING(source_id) WHERE s.source_type!='CREATOR' LIMIT 1").fetchone() is not None:
        raise ValueError("tracking source kind is corrupt")
    for table in ("source_observations", "source_checks"):
        if connection.execute(f"SELECT 1 FROM {table} o LEFT JOIN source_tracking_state t USING(source_id) WHERE t.source_id IS NULL LIMIT 1").fetchone() is not None:
            raise ValueError("tracking relationship is absent")
    rows = connection.execute(
        "SELECT s.*,t.contract,t.followed_at,t.baseline_at,t.verified_at,t.latest_published_at,t.next_check_at,t.next_page,t.coverage,t.health FROM source_subscriptions s LEFT JOIN source_tracking_state t USING(source_id) WHERE s.source_type='CREATOR'" +
        (" AND s.source_id=?" if source_id else ""), (source_id,) if source_id else (),
    ).fetchall()
    for row in rows:
        identity = normalize_creator(str(row["channel_id"]))
        if (row["source_id"] != identity.source_id or row["provider"] != "BILIBILI"
            or row["canonical_url"] != identity.canonical_url or row["contract"] != "source-tracking-v1"
            or row["processing_policy"] != ProcessingPolicy.DISCOVER_ONLY.value):
            raise ValueError("tracking identity is corrupt")
        followed = _stamp(row["followed_at"])
        if followed != _stamp(row["created_at"]):
            raise ValueError("tracking origin is corrupt")
        _stamp(row["next_check_at"])
        for key in ("baseline_at", "verified_at"):
            if row[key] is not None and _stamp(row[key]) < followed:
                raise ValueError("tracking frontier is corrupt")
        if row["baseline_at"] is None and row["coverage"] != "BASELINE_PENDING":
            raise ValueError("tracking baseline is absent")
        if row["verified_at"] is not None and row["baseline_at"] is None:
            raise ValueError("tracking verification is absent")
        if row["latest_published_at"] is not None:
            _stamp(row["latest_published_at"])
        for item in connection.execute("SELECT * FROM source_observations WHERE source_id=?", (row["source_id"],)):
            video = normalize_input(item["canonical_identity"])
            published = _stamp(item["published_at"])
            observed = _stamp(item["observed_at"])
            if observed < followed or (not item["baseline"] and published <= followed):
                raise ValueError("tracking observation is corrupt")
            if item["enrollment"] == "ENROLLED":
                if item["content_id"] != video.content_id or connection.execute(
                    "SELECT 1 FROM source_video_links l JOIN videos v USING(video_id) WHERE l.source_id=? AND l.video_id=? AND v.provider='BILIBILI'",
                    (row["source_id"], video.content_id),
                ).fetchone() is None:
                    raise ValueError("tracking Content relationship is corrupt")
                if repository is not None:
                    accepted = verify_source(repository, connection, video.content_id)
                    if accepted is None or accepted["provider"] != "BILIBILI":
                        raise ValueError("tracking Content source is corrupt")
                    artifact = repository.get_artifact(accepted["snapshot_artifact_id"])
                    root = repository._source_data_root
                    if artifact is None or root is None or json.loads(read_managed(root, artifact.relative_path, maximum=256 * 1024))["uploader_id"] != identity.mid:
                        raise ValueError("tracking Content creator is corrupt")
        for receipt in connection.execute("SELECT * FROM source_checks WHERE source_id=?", (row["source_id"],)):
            started = _stamp(receipt["started_at"])
            if started < followed or (receipt["finished_at"] is not None and _stamp(receipt["finished_at"]) < started):
                raise ValueError("tracking check time is corrupt")
            identities = json.loads(receipt["discovered_identities_json"])
            if not isinstance(identities, list) or len(identities) > MAX_PAGES * PAGE_SIZE or len(set(identities)) != len(identities):
                raise ValueError("tracking check discoveries are corrupt")
            for bv in identities:
                normalize_input(bv)
                if connection.execute("SELECT 1 FROM source_observations WHERE source_id=? AND canonical_identity=? AND baseline=0", (row["source_id"], bv)).fetchone() is None:
                    raise ValueError("tracking check discovery is absent")


def tracking_due(repository: SQLiteStateRepository, source_id: str, now: datetime) -> bool:
    with repository._connect() as connection:
        row = connection.execute("SELECT next_check_at FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone()
        if row is None:
            return False
        try:
            return _stamp(row[0]) <= now
        except (TypeError, ValueError):
            # Let the normal check reject invalid state; never replace it.
            return True


class FollowingTrackingService:
    def __init__(self, repository: SQLiteStateRepository, publisher: BilibiliContentProvider,
                 *, now: Callable[[], datetime] | None = None) -> None:
        self.repository = repository
        self.publisher = publisher
        repository.bind_source_storage(publisher.data_root)
        self.now = now or (lambda: datetime.now(UTC))

    def follow(self, value: str) -> SourceSubscriptionRecord:
        identity = normalize_creator(value)
        existing = self.repository.get_source_subscription(identity.source_id)
        if existing is not None:
            with self.repository._connect() as connection:
                verify_tracking(connection, identity.source_id, repository=self.repository)
            return existing
        metadata = self.publisher.adapter.fetch_creator(identity)
        now = format_utc_datetime(self.now())
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO source_subscriptions(source_id,provider,source_type,canonical_url,channel_id,display_name,enabled,processing_policy,created_at,updated_at) VALUES(?,'BILIBILI','CREATOR',?,?,?,1,'DISCOVER_ONLY',?,?)",
                               (identity.source_id, identity.canonical_url, identity.mid, metadata.name, now, now))
            connection.execute("INSERT OR IGNORE INTO source_tracking_state(source_id,contract,followed_at,next_check_at) VALUES(?,'source-tracking-v1',?,?)", (identity.source_id, now, now))
        self.check(identity.source_id)
        result = self.repository.get_source_subscription(identity.source_id)
        assert result is not None
        return result

    def follow_content(self, content_id: str) -> SourceSubscriptionRecord:
        with self.repository._connect() as connection:
            source = verify_source(self.repository, connection, content_id)
            if source is None or source["provider"] != "BILIBILI":
                raise BilibiliError("SOURCE_UNTRUSTED")
            artifact = self.repository.get_artifact(source["snapshot_artifact_id"])
            if artifact is None:
                raise BilibiliError("SOURCE_UNTRUSTED")
            doc = json.loads(read_managed(self.publisher.data_root, artifact.relative_path, maximum=256 * 1024))
            mid = doc["uploader_id"]
        return self.follow(mid)

    def projection(self, source_id: str) -> dict[str, object] | None:
        with self.repository._connect() as connection:
            row = connection.execute("SELECT * FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone()
            if row is None:
                return None
            try:
                verify_tracking(connection, source_id, repository=self.repository)
            except (ValueError, KeyError, TypeError, OSError):
                return {"health": "STATE_INVALID", "coverage": "CHECK_INCOMPLETE", "update_count": 0, "pending_count": 0}
            counts = connection.execute("SELECT SUM(baseline=0),SUM(enrollment='PENDING'),SUM(enrollment IN ('UNSUPPORTED','UNAVAILABLE')),SUM(enrollment='ENROLLED') FROM source_observations WHERE source_id=?", (source_id,)).fetchone()
            processing = connection.execute("SELECT COUNT(*) FROM source_video_links l JOIN content_source_snapshots c ON c.content_id=l.video_id WHERE l.source_id=? AND c.status!='READY'", (source_id,)).fetchone()[0]
            active = connection.execute("SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING'", (source_id,)).fetchone() is not None
            return {**dict(row), "discovered_count": counts[0] or 0, "pending_count": counts[1] or 0,
                    "unavailable_count": counts[2] or 0, "update_count": counts[3] or 0, "checking": active, "processing_count": processing}

    def check(self, source_id: str) -> str:
        if not _CHECK_SLOT.acquire(blocking=False):
            return "BUSY"
        try:
            return self._check(source_id)
        finally:
            _CHECK_SLOT.release()

    def _check(self, source_id: str) -> str:
        source = self.repository.get_source_subscription(source_id)
        if source is None or source.source_type is not SourceType.CREATOR:
            raise BilibiliError("SOURCE_UNTRUSTED")
        if not source.enabled:
            return "PAUSED"
        now = self.now()
        stamp = format_utc_datetime(now)
        check_id = str(uuid4())
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                verify_tracking(connection, source_id, repository=self.repository)
            except (ValueError, KeyError, TypeError, OSError):
                connection.execute("UPDATE source_subscriptions SET last_checked_at=?,last_error_code='STATE_INVALID' WHERE source_id=?", (stamp, source_id))
                return "STATE_INVALID"
            state = connection.execute("SELECT * FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone()
            if state is None:
                raise BilibiliError("SOURCE_UNTRUSTED")
            connection.execute("UPDATE source_checks SET status='INTERRUPTED',finished_at=?,result_category='INTERRUPTED' WHERE source_id=? AND status='RUNNING' AND started_at<=?",
                               (stamp, source_id, format_utc_datetime(now - LEASE)))
            if connection.execute("SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING'", (source_id,)).fetchone():
                return "BUSY"
            if _stamp(state["next_check_at"]) > now:
                return "COOLDOWN"
            connection.execute("INSERT INTO source_checks(check_id,source_id,started_at,status) VALUES(?,?,?,'RUNNING')", (check_id, source_id, stamp))
            connection.execute("UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?", (format_utc_datetime(now + COOLDOWN), source_id))
        identity = normalize_creator(source.channel_id or "")
        deadline = time.monotonic() + CHECK_SECONDS
        discovered: list[str] = []
        try:
            metadata = self.publisher.adapter.fetch_creator(identity)
            items: dict[str, CreatorVideo] = {}
            initial = state["baseline_at"] is None
            # Every pass starts at the head. Deeper offsets are only recovery hints.
            start_page = 1 if initial else state["next_page"]
            pages = [1] if initial else ([1, 2, 3] if start_page == 1 else [1, start_page, start_page + 1])
            complete = False
            last_page = 1
            total: int | None = None
            overlap = False
            for page_number in pages:
                if time.monotonic() >= deadline:
                    raise BilibiliError("NETWORK_UNAVAILABLE")
                page = self.publisher.adapter.fetch_creator_page(identity, page_number)
                if total is not None and total != page.total:
                    raise BilibiliError("METADATA_FAILED")
                total = page.total
                last_page = page_number
                for item in page.items:
                    previous = items.get(item.bvid)
                    if previous is not None and previous.published_at != item.published_at:
                        raise BilibiliError("METADATA_FAILED")
                    overlap = overlap or previous is not None
                    items[item.bvid] = item
                reached_end = page_number * PAGE_SIZE >= page.total
                # Neither a pinned item nor an old page proves that later pages
                # contain no new identities. Completeness requires list end.
                if initial or reached_end:
                    complete = initial or (start_page == 1 and not overlap)
                    break
            coverage = "COMPLETE" if complete else "UPDATE_GAP"
            next_page = 1 if complete or (last_page * PAGE_SIZE >= page.total) else min(last_page + 1, 33333)
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                enabled = connection.execute("SELECT enabled FROM source_subscriptions WHERE source_id=?", (source_id,)).fetchone()[0]
                if not enabled:
                    connection.execute("UPDATE source_checks SET status='PAUSED',finished_at=?,result_category='PAUSED' WHERE check_id=?", (format_utc_datetime(self.now()), check_id))
                    return "PAUSED"
                for item in sorted(items.values(), key=lambda item: (item.published_at, item.bvid)):
                    baseline = initial or item.published_at <= _stamp(state["followed_at"])
                    changed = connection.execute("INSERT OR IGNORE INTO source_observations(source_id,canonical_identity,published_at,observed_at,baseline,enrollment) VALUES(?,?,?,?,?,?)",
                        (source_id, item.bvid, format_utc_datetime(item.published_at), stamp, int(baseline), "BASELINE" if baseline else "PENDING")).rowcount
                    if changed and not baseline:
                        discovered.append(item.bvid)
                latest = max((item.published_at for item in items.values()), default=None)
                connection.execute("UPDATE source_tracking_state SET baseline_at=COALESCE(baseline_at,?),verified_at=CASE WHEN ? THEN ? ELSE verified_at END,latest_published_at=CASE WHEN ? THEN ? ELSE latest_published_at END,coverage=?,health=?,next_page=? WHERE source_id=?",
                    (stamp, complete, stamp, complete, None if latest is None else format_utc_datetime(latest), coverage,
                     "HEALTHY" if complete else coverage, next_page, source_id))
                connection.execute("UPDATE source_subscriptions SET display_name=?,last_checked_at=?,last_success_at=?,last_error_code=?,last_error_message=NULL,updated_at=? WHERE source_id=?",
                    (metadata.name, stamp, stamp, None if complete else coverage, stamp, source_id))
                connection.execute("UPDATE source_checks SET discovered_identities_json=?,complete=? WHERE check_id=?", (json.dumps(discovered), int(complete), check_id))
            self._enroll(source_id, identity.mid, deadline)
            with self.repository._connect() as connection:
                connection.execute("UPDATE source_checks SET status='SUCCEEDED',finished_at=?,result_category=?,discovered_identities_json=?,complete=? WHERE check_id=?",
                    (format_utc_datetime(self.now()), coverage, json.dumps(discovered), int(complete), check_id))
            return coverage
        except Exception as failure:
            code = failure.code if isinstance(failure, BilibiliError) else "METADATA_FAILED"
            health = _HEALTH.get(code, code if code in {"RISK_CONTROLLED", "RATE_LIMITED", "ACCESS_DENIED", "NOT_FOUND"} else "PROVIDER_ERROR")
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE source_tracking_state SET health=? WHERE source_id=?", (health, source_id))
                connection.execute("UPDATE source_checks SET status='FAILED',finished_at=?,result_category=?,discovered_identities_json=? WHERE check_id=?", (format_utc_datetime(self.now()), health, json.dumps(discovered), check_id))
                connection.execute("UPDATE source_subscriptions SET last_checked_at=?,last_error_code=?,last_error_message=NULL,updated_at=? WHERE source_id=?", (stamp, health, stamp, source_id))
            return health

    def _enroll(self, source_id: str, mid: str, deadline: float) -> None:
        with self.repository._connect() as connection:
            pending = connection.execute("SELECT canonical_identity FROM source_observations WHERE source_id=? AND enrollment='PENDING' ORDER BY published_at,canonical_identity LIMIT ?", (source_id, MAX_ENROLLMENTS)).fetchall()
        for row in pending:
            if time.monotonic() >= deadline:
                return
            source = self.repository.get_source_subscription(source_id)
            if source is None or not source.enabled:
                return
            bv = row[0]
            try:
                result = self.publisher.import_input(bv, expected_uploader=mid, following_source_id=source_id)
                with self.repository._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute("INSERT OR IGNORE INTO source_video_links(source_id,video_id,discovered_at) VALUES(?,?,?)", (source_id, result.content_id, format_utc_datetime(self.now())))
                    connection.execute("UPDATE source_observations SET enrollment='ENROLLED',content_id=?,error_code=NULL WHERE source_id=? AND canonical_identity=? AND enrollment='PENDING'", (result.content_id, source_id, bv))
            except BilibiliError as failure:
                if failure.code == "FOLLOWING_PAUSED":
                    return
                with self.repository._connect() as connection:
                    connection.execute("UPDATE source_observations SET error_code=? WHERE source_id=? AND canonical_identity=?", (failure.code, source_id, bv))
                    if failure.code in {"DURATION_UNSUPPORTED", "NOT_FOUND", "SOURCE_UNTRUSTED"}:
                        connection.execute("UPDATE source_observations SET enrollment=? WHERE source_id=? AND canonical_identity=? AND enrollment='PENDING'", ("UNSUPPORTED" if failure.code == "DURATION_UNSUPPORTED" else "UNAVAILABLE", source_id, bv))
                if failure.code in {"NETWORK_UNAVAILABLE", "RATE_LIMITED", "ACCESS_DENIED", "RISK_CONTROLLED"}:
                    raise
