"""Following from now on, durable incremental state, no historical flood."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.following_tracking import FollowingTrackingService
from youtube_intel.providers.bilibili import BilibiliAdapter, BilibiliError
from youtube_intel.state import SQLiteStateRepository, format_utc_datetime

NOW = datetime(2026, 10, 4, tzinfo=UTC)
BV = "BV1xx411c7mD"
NEW = "BV1xx411c7mE"
NEXT = "BV1xx411c7mF"


class CreatorFixture:
    def __init__(self) -> None:
        self.now = NOW
        self.name = "公开 UP 主"
        self.items = [(BV, NOW - timedelta(days=100))]
        self.failure: str | None = None
        self.fail_page = 0
        self.calls: list[str] = []
        self.caption = True

    def fetch(self, url: str, maximum: int) -> bytes:
        self.calls.append(url)
        if self.failure:
            raise BilibiliError(self.failure)
        query = parse_qs(urlsplit(url).query)
        if "/card?" in url:
            data = {"card": {"mid": "123", "name": self.name}}
        elif "/search?" in url:
            page = int(query["pn"][0])
            if page == self.fail_page:
                raise BilibiliError("NETWORK_UNAVAILABLE")
            rows = self.items[(page-1)*30:page*30]
            data = {"list": {"vlist": [{"bvid": bv, "mid": 123, "created": int(stamp.timestamp())} for bv, stamp in rows]},
                    "page": {"pn": page, "ps": 30, "count": len(self.items)}}
        elif "/view?" in url:
            bv = query["bvid"][0]
            data = {"bvid": bv, "cid": 12345, "title": "公开视频 " + bv,
                    "owner": {"mid": 123, "name": self.name}, "pubdate": int(dict(self.items)[bv].timestamp()),
                    "duration": 60, "state": 0, "rights": {"pay": 0}}
        elif "/v2?" in url:
            data = {"subtitle": {"subtitles": [] if not self.caption else [{"id": 678, "lan": "zh-CN", "lan_doc": "中文",
                    "subtitle_url": "//aisubtitle.hdslb.com/bfs/subtitle/fixture.json"}]}}
        else:
            return json.dumps({"body": [{"from": 0, "to": 3, "content": "Sentence1 公开字幕支持可信的来源证据。"},
                                        {"from": 4, "to": 8, "content": "新内容通过正常资料库路径处理。"}]}).encode()
        return json.dumps({"code": 0, "data": data}).encode()

    def tick(self) -> None:
        self.now += timedelta(hours=1)


def setup(tmp_path: Path) -> tuple[SQLiteStateRepository, FollowingTrackingService, CreatorFixture]:
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=NOW)
    fixture = CreatorFixture()
    publisher = BilibiliContentProvider(repo, tmp_path / "data", adapter=BilibiliAdapter(fetch=fixture.fetch), now=lambda: fixture.now)
    return repo, FollowingTrackingService(repo, publisher, now=lambda: fixture.now), fixture


def test_baseline_repeat_new_and_reorder_are_idempotent(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("https://space.bilibili.com/123/video")
    assert source.source_id == "bilibili-creator-123"
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["coverage"] == "COMPLETE"
    fixture.tick()
    tracker.check(source.source_id)
    assert tracker.projection(source.source_id)["update_count"] == 0
    fixture.items.insert(0, (NEW, fixture.now + timedelta(seconds=1)))
    fixture.tick()
    tracker.check(source.source_id)
    assert [v.video_id for v in repo.list_videos()] == ["bilibili-" + NEW]
    assert repo.get_verified_timed_transcript(video_id="bilibili-" + NEW) is not None
    fixture.items.reverse()
    fixture.name = "改名之后"
    fixture.tick()
    tracker.check(source.source_id)
    assert tracker.follow("00123").source_id == source.source_id
    assert len(repo.list_source_videos(source.source_id)) == 1
    assert tracker.projection(source.source_id)["update_count"] == 1
    assert repo.get_source_subscription(source.source_id).display_name == fixture.name  # type: ignore[union-attr]


@pytest.mark.parametrize("failure,health", [("NETWORK_UNAVAILABLE", "OFFLINE"), ("RATE_LIMITED", "RATE_LIMITED"),
    ("RISK_CONTROLLED", "RISK_CONTROLLED"), ("ACCESS_DENIED", "ACCESS_DENIED"), ("METADATA_FAILED", "PROVIDER_ERROR")])
def test_failure_preserves_verified_baseline(tmp_path: Path, failure: str, health: str) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    before = tracker.projection(source.source_id)
    fixture.tick()
    fixture.failure = failure
    tracker.check(source.source_id)
    after = tracker.projection(source.source_id)
    assert after["verified_at"] == before["verified_at"]
    assert after["health"] == health
    assert repo.get_source_subscription(source.source_id).last_success_at == NOW  # type: ignore[union-attr]
    assert repo.list_videos() == ()


def test_restart_pause_cooldown_and_manual_dedupe(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    calls = len(fixture.calls)
    tracker.check(source.source_id)
    assert len(fixture.calls) == calls
    fixture.items.insert(0, (NEW, fixture.now + timedelta(seconds=1)))
    fixture.tick()
    repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
    tracker.check(source.source_id)
    assert repo.list_videos() == ()
    repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
    manual = tracker.publisher.import_input(NEW)
    reopened = FollowingTrackingService(SQLiteStateRepository(tmp_path / "state.sqlite"), tracker.publisher, now=lambda: fixture.now)
    reopened.check(source.source_id)
    assert len(repo.list_videos()) == 1
    assert repo.list_source_videos(source.source_id)[0].video_id == manual.content_id


def bvid(index: int) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    digits = ""
    while index:
        digits = alphabet[index % len(alphabet)] + digits
        index //= len(alphabet)
    return "BV1" + digits.rjust(9, "x")


def test_partial_page_failure_retries_without_advancing_or_losing_content(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    before = tracker.projection(source.source_id)
    fixture.items = [(bvid(i), NOW + timedelta(seconds=i)) for i in range(1, 41)] + fixture.items
    fixture.tick()
    fixture.fail_page = 2
    assert tracker.check(source.source_id) == "OFFLINE"
    assert tracker.projection(source.source_id)["verified_at"] == before["verified_at"]
    assert repo.list_videos() == ()
    fixture.fail_page = 0
    for _ in range(8):
        fixture.tick()
        assert tracker.check(source.source_id) == "COMPLETE"
    assert len(repo.list_source_videos(source.source_id, limit=100)) == 40
    assert tracker.projection(source.source_id)["pending_count"] == 0
    with repo._connect() as connection:
        failed = connection.execute("SELECT * FROM source_checks WHERE status='FAILED'").fetchone()
        assert failed["complete"] == 0 and failed["discovered_identities_json"] == "[]"


def test_gap_is_truthful_deep_recovery_never_uses_offset_as_verified_cursor(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    baseline = tracker.projection(source.source_id)["verified_at"]
    fixture.items = [(bvid(i), NOW + timedelta(seconds=i)) for i in range(1, 102)] + fixture.items
    for _ in range(3):
        fixture.tick()
        start = len(fixture.calls)
        assert tracker.check(source.source_id) == "UPDATE_GAP"
        assert len([url for url in fixture.calls[start:] if "/search?" in url]) <= 3
        assert tracker.projection(source.source_id)["verified_at"] == baseline
    with repo._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM source_observations WHERE baseline=0").fetchone()[0] == 101
    assert len(repo.list_videos()) == 15


def test_pinned_unobserved_history_and_equal_timestamp_do_not_become_updates(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items = [(NEXT, NOW), (NEW, NOW - timedelta(days=50)), *fixture.items]
    fixture.tick()
    tracker.check(source.source_id)
    fixture.items.reverse()
    fixture.tick()
    tracker.check(source.source_id)
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["update_count"] == 0


def test_follow_from_verified_content_and_caption_authority_is_immutable(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    result = tracker.publisher.import_input(BV)
    source = tracker.follow_content(result.content_id)
    assert source.source_id == "bilibili-creator-123"
    transcript = repo.get_verified_timed_transcript(video_id=result.content_id)
    fixture.caption = False
    fixture.items = [(NEW, NOW + timedelta(seconds=1)), *fixture.items]
    fixture.tick()
    tracker.check(source.source_id)
    assert repo.get_verified_timed_transcript(video_id=result.content_id) == transcript
    assert repo.get_verified_timed_transcript(video_id="bilibili-" + NEW) is None
    assert repo.get_video("bilibili-" + NEW) is not None
    assert tracker.follow_content(result.content_id).source_id == source.source_id
    with pytest.raises(BilibiliError, match="SOURCE_UNTRUSTED"):
        tracker.follow_content("made-up-video")


def test_backup_restore_preserves_observations_and_never_manufactures_updates(tmp_path: Path) -> None:
    from youtube_intel.backup_restore import BackupRestoreService
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items = [(NEW, NOW + timedelta(seconds=1)), *fixture.items]
    fixture.tick()
    tracker.check(source.source_id)
    before = tracker.projection(source.source_id)
    backup_service = BackupRestoreService(database=tmp_path / "state.sqlite", data_root=tmp_path / "data")
    backup = backup_service.create_backup()
    archive, _ = backup_service.backup_download(backup.backup_id) or (None, None)
    assert archive is not None
    staged = backup_service.stage_restore(archive.read_bytes())
    backup_service.confirm_restore(staged.restore_id)
    backup_service.recover_and_apply_pending_restore()
    assert tracker.projection(source.source_id) == before
    fixture.tick()
    tracker.check(source.source_id)
    assert len(repo.list_videos()) == 1
    assert tracker.projection(source.source_id)["update_count"] == 1
    with repo._connect() as connection:
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_corrupt_tracking_fails_safely_and_backup_rejects_it(tmp_path: Path) -> None:
    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.tick()
    with repo._connect() as connection:
        connection.execute("UPDATE source_tracking_state SET baseline_at='invalid' WHERE source_id=?", (source.source_id,))
    calls = len(fixture.calls)
    assert tracker.check(source.source_id) == "STATE_INVALID"
    assert len(fixture.calls) == calls
    service = BackupRestoreService(database=tmp_path / "state.sqlite", data_root=tmp_path / "data")
    with pytest.raises(BackupRestoreError):
        service.create_backup()


def test_creator_api_follow_check_pause_and_content_follow(tmp_path: Path) -> None:
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    repo, tracker, fixture = setup(tmp_path)
    application = LocalApiApplication(repo, ProductOrchestrationService(repo, now=lambda: fixture.now),
        data_root=tmp_path / "data", source_tracking=tracker, now=lambda: fixture.now)
    status, body = application.handle("POST", "/api/v1/sources/creators", json.dumps({"input": "123"}).encode())
    assert status == 200
    assert body["source"]["tracking"]["update_count"] == 0
    fixture.tick()
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    status, _ = application.handle("POST", "/api/v1/sources/bilibili-creator-123/check", b'{"command_id":"check-1"}')
    assert status == 200 and len(repo.list_videos()) == 1
    status, followed = application.handle("POST", "/api/v1/videos/bilibili-" + NEW + "/follow-creator", b'{}')
    assert status == 200 and followed["source"]["source_id"] == "bilibili-creator-123"
    application.handle("PATCH", "/api/v1/sources/bilibili-creator-123", b'{"enabled":false}')
    fixture.tick()
    calls = len(fixture.calls)
    application.handle("POST", "/api/v1/sources/check-stale", b'{}')
    assert len(fixture.calls) == calls


def test_delta_reports_repeated_health_failure_and_recovery_without_polling_noise(tmp_path: Path) -> None:
    from youtube_intel.knowledge_delta import KnowledgeDeltaService
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    def health() -> dict[str, object]:
        report = KnowledgeDeltaService(repo, now=lambda: fixture.now).read().as_dict()
        return next(item for item in report["categories"] if item["kind"] == "source_health")
    fixture.tick()
    tracker.check(source.source_id)
    assert health()["count"] == 0
    fixture.failure = "NETWORK_UNAVAILABLE"
    fixture.tick()
    tracker.check(source.source_id)
    assert health()["count"] == 0
    fixture.tick()
    tracker.check(source.source_id)
    assert health()["count"] == 1
    fixture.failure = None
    fixture.tick()
    tracker.check(source.source_id)
    assert health()["items"][0]["label"] == "Source checks resumed"


def test_active_check_blocks_backup_and_pausing_during_fetch_prevents_discovery(tmp_path: Path) -> None:
    from youtube_intel.backup_restore import BackupRestoreService
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    fixture.tick()
    original_fetch = fixture.fetch
    service = BackupRestoreService(database=tmp_path / "state.sqlite", data_root=tmp_path / "data")
    def pause(url: str, maximum: int) -> bytes:
        if "/search?" in url:
            assert service.readiness()["ready"] is False
            repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
        return original_fetch(url, maximum)
    tracker.publisher.adapter.fetch = pause
    assert tracker.check(source.source_id) == "PAUSED"
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["verified_at"] == format_utc_datetime(NOW)


def test_pause_during_video_metadata_prevents_new_content_admission(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    fixture.tick()
    original_fetch = fixture.fetch
    def pause(url: str, maximum: int) -> bytes:
        if "/view?" in url:
            repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
        return original_fetch(url, maximum)
    tracker.publisher.adapter.fetch = pause
    tracker.check(source.source_id)
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["pending_count"] == 1
    repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
    tracker.publisher.adapter.fetch = original_fetch
    fixture.tick()
    tracker.check(source.source_id)
    assert len(repo.list_source_videos(source.source_id)) == 1


def test_enrollment_failure_keeps_pending_identity_and_retry_recovers(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    fixture.tick()
    original_fetch = fixture.fetch
    def fail(url: str, maximum: int) -> bytes:
        if "/view?" in url:
            raise BilibiliError("NETWORK_UNAVAILABLE")
        return original_fetch(url, maximum)
    tracker.publisher.adapter.fetch = fail
    assert tracker.check(source.source_id) == "OFFLINE"
    assert tracker.projection(source.source_id)["pending_count"] == 1
    with repo._connect() as connection:
        receipt = connection.execute("SELECT * FROM source_checks WHERE status='FAILED'").fetchone()
        assert receipt["complete"] == 1 and json.loads(receipt["discovered_identities_json"]) == [NEW]
    tracker.publisher.adapter.fetch = original_fetch
    fixture.tick()
    tracker.check(source.source_id)
    assert len(repo.list_videos()) == 1 and tracker.projection(source.source_id)["pending_count"] == 0


@pytest.mark.parametrize("field,value", [("duration", 7201), ("owner", {"mid": 456, "name": "Other creator"})])
def test_unsupported_or_wrong_creator_video_never_gets_trusted_content(tmp_path: Path, field: str, value: object) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    fixture.tick()
    original_fetch = fixture.fetch
    def invalid(url: str, maximum: int) -> bytes:
        payload = original_fetch(url, maximum)
        if "/view?" in url:
            data = json.loads(payload)
            data["data"][field] = value
            return json.dumps(data).encode()
        return payload
    tracker.publisher.adapter.fetch = invalid
    tracker.check(source.source_id)
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["unavailable_count"] == 1


def test_remote_deletion_and_unavailable_creator_preserve_trusted_history(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    fixture.tick()
    tracker.check(source.source_id)
    transcript = repo.get_verified_timed_transcript(video_id="bilibili-" + NEW)
    evidence = repo.list_evidence_for_presentation("bilibili-" + NEW)
    fixture.items = []
    fixture.tick()
    tracker.check(source.source_id)
    fixture.failure = "NOT_FOUND"
    fixture.tick()
    assert tracker.check(source.source_id) == "NOT_FOUND"
    assert repo.get_verified_timed_transcript(video_id="bilibili-" + NEW) == transcript
    assert repo.list_evidence_for_presentation("bilibili-" + NEW) == evidence
    assert len(repo.list_source_videos(source.source_id)) == 1


def test_provider_budget_prevents_concurrent_creator_checks(tmp_path: Path) -> None:
    import threading
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    original_fetch = fixture.fetch
    def creators(url: str, maximum: int) -> bytes:
        payload = original_fetch(url, maximum)
        if "mid=456" in url:
            data = json.loads(payload)
            if "/card?" in url:
                data["data"]["card"]["mid"] = "456"
            else:
                for item in data["data"]["list"]["vlist"]:
                    item["mid"] = 456
            return json.dumps(data).encode()
        return payload
    tracker.publisher.adapter.fetch = creators
    second = tracker.follow("456")
    fixture.tick()
    started = threading.Event()
    release = threading.Event()
    def blocked(url: str, maximum: int) -> bytes:
        started.set()
        assert release.wait(5)
        return creators(url, maximum)
    tracker.publisher.adapter.fetch = blocked
    thread = threading.Thread(target=tracker.check, args=(source.source_id,))
    thread.start()
    assert started.wait(5)
    calls = len(fixture.calls)
    other = FollowingTrackingService(repo, tracker.publisher, now=lambda: fixture.now)
    assert other.check(second.source_id) == "BUSY"
    assert len(fixture.calls) == calls
    release.set()
    thread.join(5)
    assert not thread.is_alive()


def test_changing_page_total_cannot_advance_verified_state(tmp_path: Path) -> None:
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    before = tracker.projection(source.source_id)["verified_at"]
    fixture.items = [(bvid(i), NOW + timedelta(seconds=i)) for i in range(1, 32)]
    fixture.tick()
    original_fetch = fixture.fetch
    def changing(url: str, maximum: int) -> bytes:
        payload = original_fetch(url, maximum)
        if "pn=2&" in url:
            data = json.loads(payload)
            data["data"]["page"]["count"] = 32
            return json.dumps(data).encode()
        return payload
    tracker.publisher.adapter.fetch = changing
    assert tracker.check(source.source_id) == "PROVIDER_ERROR"
    assert tracker.projection(source.source_id)["verified_at"] == before
    assert repo.list_videos() == ()
    tracker.publisher.adapter.fetch = original_fetch
    fixture.tick()
    tracker.check(source.source_id)
    assert tracker.projection(source.source_id)["discovered_count"] == 31


def test_migration34_failure_is_atomic_and_upgrade_preserves_bilibili_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from youtube_intel.state import MigrationError
    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    migrations = repo._load_migrations()
    old = tuple(m for m in migrations if m.version <= 33)
    monkeypatch.setattr(repo, "_load_migrations", lambda: old)
    assert repo.initialize(now=NOW).version == 33
    fixture = CreatorFixture()
    publisher = BilibiliContentProvider(repo, tmp_path / "data", adapter=BilibiliAdapter(fetch=fixture.fetch), now=lambda: fixture.now)
    imported = publisher.import_input(BV)
    before = repo.get_verified_timed_transcript(video_id=imported.content_id)
    evidence = repo.list_evidence_for_presentation(imported.content_id)
    broken = replace(migrations[-1], sql=migrations[-1].sql + "\nCREATE TABLE invalid_syntax(;", checksum="f" * 64)
    monkeypatch.setattr(repo, "_load_migrations", lambda: (*old, broken))
    with pytest.raises(MigrationError, match="failed to apply migration 34"):
        repo.initialize(now=NOW)
    assert repo.schema_version().version == 33
    assert repo.get_verified_timed_transcript(video_id=imported.content_id) == before
    monkeypatch.setattr(repo, "_load_migrations", lambda: migrations)
    assert repo.initialize(now=NOW).version == 34
    assert repo.get_verified_timed_transcript(video_id=imported.content_id) == before
    assert repo.list_evidence_for_presentation(imported.content_id) == evidence


def test_wrong_creator_relationship_fails_tracking_and_portable_backup_validation(tmp_path: Path) -> None:
    from youtube_intel.backup_restore import BackupRestoreError, BackupRestoreService
    repo, tracker, fixture = setup(tmp_path)
    source = tracker.follow("123")
    fixture.items.insert(0, (NEW, NOW + timedelta(seconds=1)))
    fixture.tick()
    tracker.check(source.source_id)
    stamp = format_utc_datetime(NOW)
    with repo._connect() as connection:
        connection.execute("INSERT INTO source_subscriptions(source_id,provider,source_type,canonical_url,channel_id,display_name,enabled,processing_policy,created_at,updated_at) VALUES('bilibili-creator-456','BILIBILI','CREATOR','https://space.bilibili.com/456','456','Other creator',1,'DISCOVER_ONLY',?,?)", (stamp, stamp))
        connection.execute("INSERT INTO source_tracking_state(source_id,contract,followed_at,baseline_at,verified_at,next_check_at,coverage,health) VALUES('bilibili-creator-456','source-tracking-v1',?,?,?,?,'COMPLETE','HEALTHY')", (stamp, stamp, stamp, stamp))
        connection.execute("INSERT INTO source_video_links(source_id,video_id,discovered_at) VALUES('bilibili-creator-456',?,?)", ("bilibili-" + NEW, stamp))
        connection.execute("INSERT INTO source_observations SELECT 'bilibili-creator-456',canonical_identity,published_at,observed_at,baseline,enrollment,content_id,error_code FROM source_observations WHERE source_id=? AND baseline=0", (source.source_id,))
    assert tracker.projection("bilibili-creator-456")["health"] == "STATE_INVALID"
    assert tracker.check("bilibili-creator-456") == "STATE_INVALID"
    assert len(repo.list_videos()) == 1
    service = BackupRestoreService(database=tmp_path / "state.sqlite", data_root=tmp_path / "data")
    with pytest.raises(BackupRestoreError, match="Following Content relationship"):
        service.create_backup()
