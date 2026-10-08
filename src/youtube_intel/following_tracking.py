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
from youtube_intel.following_provider import (
    BilibiliFollowingProvider,
    Candidate,
    FollowingProvider,
    SourceIdentity,
    TrackingError,
)
from youtube_intel.orchestration import ProcessingPolicy
from youtube_intel.providers.bilibili import BilibiliError, normalize_input
from youtube_intel.providers.bilibili_creator import (
    normalize_creator,
)
from youtube_intel.providers.youtube_channel import (
    VIDEO_ID,
    canonical_channel,
    channel_input,
)
from youtube_intel.source_authority import read_managed, verify_source
from youtube_intel.source_run import SOURCE_RUN_ACTIVE_STATES
from youtube_intel.state import (
    SourceSubscriptionRecord,
    SQLiteStateRepository,
    format_utc_datetime,
)

MAX_CANDIDATES = 90
MAX_ENROLLMENTS = 5
CHECK_SECONDS = 180.0
COOLDOWN = timedelta(minutes=15)
LEASE = timedelta(minutes=10)
AUTOMATIC_REFUSAL_HEALTH = frozenset({"STATE_INVALID", "RISK_CONTROLLED", "ACCESS_DENIED"})
_CHECK_SLOTS = {provider: threading.BoundedSemaphore(1) for provider in ("BILIBILI", "YOUTUBE")}
# Derived from the single definition of "a Source Run still holds live
# execution", so this projection can never disagree with the Backup gate.
_ACTIVE_SOURCE_RUN_STATES = tuple(
    state.value for state in sorted(SOURCE_RUN_ACTIVE_STATES, key=lambda item: item.value)
)
_ACTIVE_SOURCE_RUN_SQL = (
    "SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING' UNION ALL "
    "SELECT 1 FROM source_runs WHERE source_id=? AND state IN ("
    + ",".join("?" for _ in _ACTIVE_SOURCE_RUN_STATES)
    + ") LIMIT 1"
)
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
    if connection.execute("SELECT 1 FROM source_tracking_state t JOIN source_subscriptions s USING(source_id) WHERE NOT ((s.source_type='CREATOR' AND s.provider='BILIBILI') OR (s.source_type='CHANNEL' AND s.provider='YOUTUBE')) LIMIT 1").fetchone() is not None:
        raise ValueError("tracking source kind is corrupt")
    for table in ("source_observations", "source_checks"):
        if connection.execute(f"SELECT 1 FROM {table} o LEFT JOIN source_tracking_state t USING(source_id) WHERE t.source_id IS NULL LIMIT 1").fetchone() is not None:
            raise ValueError("tracking relationship is absent")
    rows = connection.execute(
        "SELECT s.*,t.contract,t.followed_at,t.baseline_at,t.verified_at,t.latest_published_at,t.next_check_at,t.next_page,t.coverage,t.health FROM source_subscriptions s LEFT JOIN source_tracking_state t USING(source_id) WHERE (s.source_type='CREATOR' OR t.source_id IS NOT NULL)" +
        (" AND s.source_id=?" if source_id else ""), (source_id,) if source_id else (),
    ).fetchall()
    for row in rows:
        identity = source_identity(row["provider"], str(row["channel_id"]), row["display_name"] or "")
        if ((((row["provider"] == "BILIBILI" or row["source_id"].startswith("youtube-channel-")) and row["source_id"] != identity.source_id) or row["source_type"] != identity.kind)
            or row["canonical_url"] != identity.canonical_url or row["contract"] != "source-tracking-v1"
            or row["processing_policy"] != ProcessingPolicy.DISCOVER_ONLY.value):
            raise ValueError("tracking identity is corrupt")
        followed = _stamp(row["followed_at"])
        if followed < _stamp(row["created_at"]):
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
            content_id = content_identity(row["provider"], item["canonical_identity"])
            published = _stamp(item["published_at"])
            observed = _stamp(item["observed_at"])
            if observed < followed or (not item["baseline"] and published <= followed):
                raise ValueError("tracking observation is corrupt")
            if item["enrollment"] == "ENROLLED":
                if item["content_id"] != content_id or connection.execute(
                    "SELECT 1 FROM source_video_links l JOIN videos v USING(video_id) WHERE l.source_id=? AND l.video_id=? AND v.provider=?",
                    (row["source_id"], content_id, row["provider"]),
                ).fetchone() is None:
                    raise ValueError("tracking Content relationship is corrupt")
                if repository is not None:
                    if trusted_content_channel(repository, connection, content_id, row["provider"]) != identity.channel_id:
                        raise ValueError("tracking Content channel is corrupt")
        for linked in connection.execute("SELECT video_id FROM source_video_links WHERE source_id=?", (row["source_id"],)):
            if connection.execute("SELECT 1 FROM source_observations WHERE source_id=? AND content_id=? AND enrollment='ENROLLED'", (row["source_id"], linked[0])).fetchone() is None:
                raise ValueError("tracking Content has no enrollment authority")
        for receipt in connection.execute("SELECT * FROM source_checks WHERE source_id=?", (row["source_id"],)):
            started = _stamp(receipt["started_at"])
            if started < followed or (receipt["finished_at"] is not None and _stamp(receipt["finished_at"]) < started):
                raise ValueError("tracking check time is corrupt")
            identities = json.loads(receipt["discovered_identities_json"])
            if not isinstance(identities, list) or len(identities) > MAX_CANDIDATES or len(set(identities)) != len(identities):
                raise ValueError("tracking check discoveries are corrupt")
            for bv in identities:
                content_identity(row["provider"], bv)
                if connection.execute("SELECT 1 FROM source_observations WHERE source_id=? AND canonical_identity=? AND baseline=0", (row["source_id"], bv)).fetchone() is None:
                    raise ValueError("tracking check discovery is absent")


def tracking_due(repository: SQLiteStateRepository, source_id: str, now: datetime,
                 *, manual: bool = False) -> bool:
    with repository._connect() as connection:
        row = connection.execute("SELECT t.next_check_at,t.health,s.last_checked_at FROM source_tracking_state t JOIN source_subscriptions s USING(source_id) WHERE source_id=?", (source_id,)).fetchone()
        if row is None:
            return False
        if not manual and row["health"] in AUTOMATIC_REFUSAL_HEALTH:
            return False
        try:
            if manual and row["health"] == "OFFLINE" and row["last_checked_at"] is not None:
                return _stamp(row["last_checked_at"]) + timedelta(seconds=5) <= now
            return _stamp(row[0]) <= now
        except (TypeError, ValueError):
            # Let the normal check reject invalid state; never replace it.
            return True


def source_identity(provider: str, channel_id: str, name: str = "") -> SourceIdentity:
    if provider == "YOUTUBE":
        return canonical_channel(channel_id, name)
    if provider == "BILIBILI":
        identity = normalize_creator(channel_id)
        return SourceIdentity(provider, "CREATOR", identity.mid, identity.source_id, identity.canonical_url, name)
    raise ValueError("unsupported tracking provider")


def content_identity(provider: str, value: str) -> str:
    if provider == "YOUTUBE" and isinstance(value, str) and VIDEO_ID.fullmatch(value):
        return value
    if provider == "BILIBILI":
        return normalize_input(value).content_id
    raise ValueError("invalid provider Content identity")


def trusted_content_channel(repository: SQLiteStateRepository, connection: sqlite3.Connection,
                            content_id: str, provider: str) -> str:
    if provider == "YOUTUBE":
        row = connection.execute("SELECT * FROM videos WHERE video_id=? AND provider='YOUTUBE' AND availability='public'", (content_id,)).fetchone()
        if row is None or row["source_url"] != "https://www.youtube.com/watch?v=" + content_identity(provider, content_id):
            raise ValueError("untrusted YouTube metadata")
        return canonical_channel(row["channel_id"]).channel_id
    accepted = verify_source(repository, connection, content_id)
    if accepted is None or accepted["provider"] != provider:
        raise ValueError("untrusted Content metadata")
    artifact = repository.get_artifact(accepted["snapshot_artifact_id"])
    root = repository._source_data_root
    if artifact is None or root is None:
        raise ValueError("untrusted Content snapshot")
    return str(json.loads(read_managed(root, artifact.relative_path, maximum=256 * 1024))["uploader_id"])


def is_tracked(repository: SQLiteStateRepository, source_id: str) -> bool:
    with repository._connect() as connection:
        return connection.execute("SELECT 1 FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone() is not None


class FollowingTrackingService:
    def __init__(self, repository: SQLiteStateRepository, publisher: BilibiliContentProvider,
                 *, youtube: FollowingProvider | None = None,
                 now: Callable[[], datetime] | None = None) -> None:
        self.repository = repository
        self.publisher = publisher
        repository.bind_source_storage(publisher.data_root)
        from youtube_intel.providers.youtube_channel import YouTubeFollowingProvider
        self.providers: dict[str, FollowingProvider] = {"BILIBILI": BilibiliFollowingProvider(publisher),
                                                      "YOUTUBE": youtube or YouTubeFollowingProvider()}
        self.now = now or (lambda: datetime.now(UTC))

    def follow(self, value: str, *, provider: str = "BILIBILI") -> SourceSubscriptionRecord:
        if not getattr(self.providers[provider], "available", True):
            raise TrackingError("CREATOR_TRACKING_UNAVAILABLE")
        # Stable ids can reuse stored sources without a provider call.
        channel_id = channel_input(value) if provider == "YOUTUBE" else normalize_creator(value).mid
        if not channel_id.startswith("@"):
            canonical = source_identity(provider, channel_id)
            existing = self.repository.get_source_by_canonical_url(canonical.canonical_url)
            if existing is not None and is_tracked(self.repository, existing.source_id):
                with self.repository._connect() as connection:
                    verify_tracking(connection, existing.source_id, repository=self.repository)
                return existing
        identity = self.providers[provider].resolve(value)
        expected = source_identity(provider, identity.channel_id, identity.name)
        if identity != expected:
            raise TrackingError("SOURCE_UNTRUSTED")
        now = format_utc_datetime(self.now())
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute("SELECT * FROM source_subscriptions WHERE canonical_url=?", (identity.canonical_url,)).fetchone()
            source_id = identity.source_id if existing_row is None else existing_row["source_id"]
            if existing_row is not None and (existing_row["provider"] != provider or existing_row["channel_id"] != identity.channel_id or existing_row["source_type"] != identity.kind):
                raise TrackingError("SOURCE_UNTRUSTED")
            connection.execute("INSERT OR IGNORE INTO source_subscriptions(source_id,provider,source_type,canonical_url,channel_id,display_name,enabled,processing_policy,created_at,updated_at) VALUES(?,?,?,?,?,?,1,'DISCOVER_ONLY',?,?)",
                (source_id, provider, identity.kind, identity.canonical_url, identity.channel_id, identity.name, now, now))
            if existing_row is not None and connection.execute("SELECT 1 FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone() is None:
                # Adopt a canonical legacy channel configuration, without using
                # its historical scalar cursor or importing history.
                if connection.execute("SELECT 1 FROM source_video_links WHERE source_id=?", (source_id,)).fetchone():
                    raise TrackingError("SOURCE_UNTRUSTED")
                connection.execute("UPDATE source_subscriptions SET processing_policy='DISCOVER_ONLY' WHERE source_id=?", (source_id,))
            connection.execute("INSERT OR IGNORE INTO source_tracking_state(source_id,contract,followed_at,next_check_at) VALUES(?,'source-tracking-v1',?,?)", (source_id, now, now))
            verify_tracking(connection, source_id, repository=self.repository)
        self.check(source_id)
        result = self.repository.get_source_subscription(source_id)
        assert result is not None
        return result

    def follow_content(self, content_id: str, *, provider: str = "BILIBILI") -> SourceSubscriptionRecord:
        try:
            with self.repository._connect() as connection:
                channel_id = trusted_content_channel(self.repository, connection, content_id, provider)
        except (ValueError, TypeError, KeyError, OSError):
            raise (BilibiliError("SOURCE_UNTRUSTED") if provider == "BILIBILI" else TrackingError("SOURCE_UNTRUSTED")) from None
        return self.follow(channel_id, provider=provider)

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
            processing = connection.execute("SELECT COUNT(*) FROM source_video_links l JOIN videos v ON v.video_id=l.video_id LEFT JOIN content_source_snapshots c ON c.content_id=l.video_id WHERE l.source_id=? AND ((v.provider='YOUTUBE' AND NOT EXISTS(SELECT 1 FROM timed_transcripts t WHERE t.video_id=v.video_id)) OR (c.content_id IS NOT NULL AND c.status!='READY'))", (source_id,)).fetchone()[0]
            active = connection.execute(
                _ACTIVE_SOURCE_RUN_SQL,
                (source_id, source_id, *_ACTIVE_SOURCE_RUN_STATES),
            ).fetchone() is not None
            source = connection.execute("SELECT last_checked_at FROM source_subscriptions WHERE source_id=?", (source_id,)).fetchone()
            manual_check_at = row["next_check_at"]
            if row["health"] == "OFFLINE" and source[0] is not None:
                manual_check_at = format_utc_datetime(_stamp(source[0]) + timedelta(seconds=5))
            return {**dict(row), "discovered_count": counts[0] or 0, "pending_count": counts[1] or 0,
                    "unavailable_count": counts[2] or 0, "update_count": counts[3] or 0, "checking": active, "processing_count": processing,
                    "manual_check_at": manual_check_at}

    def defer_automatic(self, source_id: str) -> None:
        """Slot contention is neither a check nor success; retry later durably."""
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT next_check_at FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone()
            if row is not None:
                due = max(_stamp(row[0]), self.now() + timedelta(minutes=1))
                connection.execute("UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?", (format_utc_datetime(due), source_id))

    def settle_local_failure(self, source_id: str) -> None:
        """Settle an owning worker's local failure without advancing frontier."""
        stamp = format_utc_datetime(self.now())
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            verify_tracking(connection, source_id, repository=self.repository)
            connection.execute("UPDATE source_checks SET status='FAILED',finished_at=?,result_category='LOCAL_PROCESSING_FAILED' WHERE source_id=? AND status='RUNNING'", (stamp, source_id))
            connection.execute("UPDATE source_tracking_state SET health='PROVIDER_ERROR',next_check_at=? WHERE source_id=?", (format_utc_datetime(self.now() + timedelta(hours=1)), source_id))
            connection.execute("UPDATE source_subscriptions SET last_checked_at=?,last_error_code='PROVIDER_ERROR',last_error_message=NULL WHERE source_id=?", (stamp, source_id))

    def check(self, source_id: str, *, automatic: bool = False) -> str:
        source = self.repository.get_source_subscription(source_id)
        if source is None or source.provider not in _CHECK_SLOTS:
            raise TrackingError("SOURCE_UNTRUSTED")
        if not getattr(self.providers[source.provider], "available", True):
            return "CAPABILITY_UNAVAILABLE"
        slot = _CHECK_SLOTS[source.provider]
        if not slot.acquire(blocking=False):
            return "BUSY"
        try:
            return self._check(source_id, automatic=automatic)
        finally:
            slot.release()

    def _check(self, source_id: str, *, automatic: bool = False) -> str:
        source = self.repository.get_source_subscription(source_id)
        if source is None or not is_tracked(self.repository, source_id):
            raise BilibiliError("SOURCE_UNTRUSTED")
        if not source.enabled:
            return "PAUSED"
        now = self.now()
        stamp = format_utc_datetime(now)
        check_id = str(uuid4())
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not connection.execute("SELECT enabled FROM source_subscriptions WHERE source_id=?", (source_id,)).fetchone()[0]:
                return "PAUSED"
            try:
                verify_tracking(connection, source_id, repository=self.repository)
            except (ValueError, KeyError, TypeError, OSError):
                connection.execute("UPDATE source_subscriptions SET last_checked_at=?,last_error_code='STATE_INVALID' WHERE source_id=?", (stamp, source_id))
                connection.execute("UPDATE source_tracking_state SET health='STATE_INVALID' WHERE source_id=?", (source_id,))
                return "STATE_INVALID"
            state = connection.execute("SELECT * FROM source_tracking_state WHERE source_id=?", (source_id,)).fetchone()
            if state is None:
                raise BilibiliError("SOURCE_UNTRUSTED")
            if automatic and state["health"] in AUTOMATIC_REFUSAL_HEALTH:
                return str(state["health"])
            connection.execute("UPDATE source_checks SET status='INTERRUPTED',finished_at=?,result_category='INTERRUPTED' WHERE source_id=? AND status='RUNNING' AND started_at<=?",
                               (stamp, source_id, format_utc_datetime(now - LEASE)))
            if connection.execute("SELECT 1 FROM source_checks WHERE source_id=? AND status='RUNNING'", (source_id,)).fetchone():
                return "BUSY"
            manual_network_retry = (
                not automatic and state["health"] == "OFFLINE"
                and source.last_checked_at is not None
                and source.last_checked_at + timedelta(seconds=5) <= now
            )
            if _stamp(state["next_check_at"]) > now and not manual_network_retry:
                return "COOLDOWN"
            connection.execute("INSERT INTO source_checks(check_id,source_id,started_at,status) VALUES(?,?,?,'RUNNING')", (check_id, source_id, stamp))
            connection.execute("UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?", (format_utc_datetime(now + COOLDOWN), source_id))
        identity = source_identity(source.provider, source.channel_id or "", source.display_name or "")
        deadline = time.monotonic() + CHECK_SECONDS
        discovered: list[str] = []
        try:
            initial = state["baseline_at"] is None
            with self.repository._connect() as connection:
                known = tuple(Candidate(row["canonical_identity"], _stamp(row["published_at"])) for row in connection.execute("SELECT canonical_identity,published_at FROM source_observations WHERE source_id=? AND observed_at<=? ORDER BY published_at DESC,canonical_identity DESC LIMIT 90", (source_id, state["verified_at"] or stamp)))
            enumeration = self.providers[source.provider].enumerate(identity, initial=initial,
                next_page=state["next_page"], known=known,
                verified_at=None if state["verified_at"] is None else _stamp(state["verified_at"]))
            items = {item.identity: item for item in enumeration.items}
            if len(enumeration.items) > MAX_CANDIDATES or len(items) != len(enumeration.items):
                raise TrackingError("METADATA_FAILED")
            for item in items.values():
                content_identity(source.provider, item.identity)
                if item.published_at.tzinfo is None or item.published_at > now + timedelta(days=1):
                    raise TrackingError("METADATA_FAILED")
            complete = enumeration.complete
            coverage = "COMPLETE" if complete else "UPDATE_GAP"
            next_page = enumeration.next_page
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                enabled = connection.execute("SELECT enabled FROM source_subscriptions WHERE source_id=?", (source_id,)).fetchone()[0]
                if not enabled:
                    connection.execute("UPDATE source_checks SET status='PAUSED',finished_at=?,result_category='PAUSED' WHERE check_id=?", (format_utc_datetime(self.now()), check_id))
                    return "PAUSED"
                for item in sorted(items.values(), key=lambda item: (item.published_at, item.identity)):
                    baseline = initial or item.published_at <= _stamp(state["followed_at"])
                    changed = connection.execute("INSERT OR IGNORE INTO source_observations(source_id,canonical_identity,published_at,observed_at,baseline,enrollment) VALUES(?,?,?,?,?,?)",
                        (source_id, item.identity, format_utc_datetime(item.published_at), stamp, int(baseline), "BASELINE" if baseline else "PENDING")).rowcount
                    if changed and not baseline:
                        discovered.append(item.identity)
                latest = max((item.published_at for item in items.values()), default=None)
                if state["latest_published_at"] is not None:
                    previous_latest = _stamp(state["latest_published_at"])
                    latest = previous_latest if latest is None else max(latest, previous_latest)
                connection.execute("UPDATE source_tracking_state SET baseline_at=COALESCE(baseline_at,?),verified_at=CASE WHEN ? THEN ? ELSE verified_at END,latest_published_at=CASE WHEN ? THEN ? ELSE latest_published_at END,coverage=?,health=?,next_page=? WHERE source_id=?",
                    (stamp, complete, stamp, complete, None if latest is None else format_utc_datetime(latest), coverage,
                     "HEALTHY" if complete else coverage, next_page, source_id))
                connection.execute("UPDATE source_subscriptions SET display_name=?,last_checked_at=?,last_error_code=?,last_error_message=NULL,updated_at=? WHERE source_id=?",
                    (enumeration.name, stamp, None if complete else coverage, stamp, source_id))
                connection.execute("UPDATE source_checks SET discovered_identities_json=?,complete=? WHERE check_id=?", (json.dumps(discovered), int(complete), check_id))
            self._enroll(source_id, identity, deadline, _stamp(state["followed_at"]))
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if automatic:
                    connection.execute("UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?",
                                       (format_utc_datetime(self.now() + COOLDOWN), source_id))
                if complete:
                    connection.execute("UPDATE source_subscriptions SET last_success_at=? WHERE source_id=?", (stamp, source_id))
                connection.execute("UPDATE source_checks SET status='SUCCEEDED',finished_at=?,result_category=?,discovered_identities_json=?,complete=? WHERE check_id=?",
                    (format_utc_datetime(self.now()), coverage, json.dumps(discovered), int(complete), check_id))
            return coverage
        except Exception as failure:
            code = failure.code if isinstance(failure, (BilibiliError, TrackingError)) else "METADATA_FAILED"
            health = _HEALTH.get(code, code if code in {"RISK_CONTROLLED", "RATE_LIMITED", "ACCESS_DENIED", "NOT_FOUND"} else "PROVIDER_ERROR")
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE source_tracking_state SET health=? WHERE source_id=?", (health, source_id))
                if automatic:
                    previous = connection.execute(
                        "SELECT status,result_category FROM source_checks WHERE source_id=? AND check_id!=? ORDER BY started_at DESC,check_id DESC LIMIT 8",
                        (source_id, check_id),
                    ).fetchall()
                    consecutive = 0
                    for receipt in previous:
                        if receipt["status"] != "FAILED" or receipt["result_category"] != health:
                            break
                        consecutive += 1
                    base, maximum = ((60, 3600) if health == "OFFLINE" else
                                     (900, 14400) if health == "RATE_LIMITED" else (3600, 86400))
                    delay = min(maximum, base * 2 ** consecutive)
                    connection.execute("UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?",
                                       (format_utc_datetime(self.now() + timedelta(seconds=delay)), source_id))
                elif source.provider == "YOUTUBE" and code == "NETWORK_UNAVAILABLE":
                    # A failed network attempt is not a successful provider check.
                    # Permit a bounded user retry after VPN/network changes.
                    connection.execute("UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?",
                                       (format_utc_datetime(now + timedelta(seconds=5)), source_id))
                connection.execute("UPDATE source_checks SET status='FAILED',finished_at=?,result_category=?,discovered_identities_json=? WHERE check_id=?", (format_utc_datetime(self.now()), health, json.dumps(discovered), check_id))
                connection.execute("UPDATE source_subscriptions SET last_checked_at=?,last_error_code=?,last_error_message=NULL,updated_at=? WHERE source_id=?", (stamp, health, stamp, source_id))
            return health

    def _enroll(self, source_id: str, identity: SourceIdentity, deadline: float, followed_at: datetime) -> None:
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
                result = self.providers[identity.provider].enroll(bv, channel_id=identity.channel_id, source_id=source_id, followed_at=followed_at)
                with self.repository._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    current = connection.execute("SELECT enabled FROM source_subscriptions WHERE source_id=?", (source_id,)).fetchone()
                    if current is None or not current[0]:
                        return
                    if result != content_identity(identity.provider, bv) or trusted_content_channel(self.repository, connection, result, identity.provider) != identity.channel_id:
                        raise TrackingError("SOURCE_UNTRUSTED")
                    connection.execute("INSERT OR IGNORE INTO source_video_links(source_id,video_id,discovered_at) VALUES(?,?,?)", (source_id, result, format_utc_datetime(self.now())))
                    connection.execute("UPDATE source_observations SET enrollment='ENROLLED',content_id=?,error_code=NULL WHERE source_id=? AND canonical_identity=? AND enrollment='PENDING'", (result, source_id, bv))
            except (BilibiliError, TrackingError) as failure:
                if failure.code == "FOLLOWING_PAUSED":
                    return
                with self.repository._connect() as connection:
                    connection.execute("UPDATE source_observations SET error_code=? WHERE source_id=? AND canonical_identity=?", (failure.code, source_id, bv))
                    if failure.code in {"DURATION_UNSUPPORTED", "VIDEO_UNSUPPORTED", "NOT_FOUND", "SOURCE_UNTRUSTED", "HISTORICAL_VIDEO"}:
                        connection.execute("UPDATE source_observations SET enrollment=? WHERE source_id=? AND canonical_identity=? AND enrollment='PENDING'", ("UNSUPPORTED" if failure.code in {"DURATION_UNSUPPORTED", "VIDEO_UNSUPPORTED"} else "UNAVAILABLE", source_id, bv))
                if failure.code not in {"DURATION_UNSUPPORTED", "VIDEO_UNSUPPORTED", "NOT_FOUND", "SOURCE_UNTRUSTED", "HISTORICAL_VIDEO"}:
                    raise
