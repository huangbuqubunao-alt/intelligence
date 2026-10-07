"""Real observed Atom identity shape through the existing tracking authority."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from conftest import _load_module

from youtube_intel.following_provider import SourceIdentity, TrackingError
from youtube_intel.following_tracking import FollowingTrackingService, verify_tracking
from youtube_intel.providers.youtube_channel import (
    YouTubeFollowingProvider,
    canonical_channel,
)
from youtube_intel.state import SQLiteStateRepository

CHANNEL = "UCLA_DiR1FfKNvjuUpBHmylQ"
RAW = (Path(__file__).parents[1] / "fixtures/youtube/rss_live_shape.xml").read_bytes()
NEW_RAW = (
    Path(__file__).parents[1] / "fixtures/youtube/rss_live_shape_new.xml"
).read_bytes()
ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"


def mutated_feed(mutation):
    root = ET.fromstring(NEW_RAW)
    feed_id = root.find(YT + "channelId")
    entries = root.findall(ATOM + "entry")
    if mutation == "root":
        root.tag = ATOM + "not-feed"
    elif mutation == "missing_feed_id":
        root.remove(feed_id)
    elif mutation == "missing_entry_id":
        entries[0].remove(entries[0].find(YT + "channelId"))
    elif mutation == "missing_published":
        entries[0].remove(entries[0].find(ATOM + "published"))
    elif mutation == "mixed":
        entries[1].find(YT + "channelId").text = "UC" + "b" * 22
    elif mutation == "foreign_entry":
        for entry in entries:
            entry.find(YT + "channelId").text = "UC" + "b" * 22
    elif mutation == "stripped_entry":
        entries[0].find(YT + "channelId").text = CHANNEL[2:]
    else:
        feed_id.text = mutation
    return ET.tostring(root)


@pytest.mark.parametrize("channel", [CHANNEL, "UC_x5XG1OV2P6uZZ5FSM9Ttw", "UCBR8-60-B28hp2BmDPdntcQ", "UC" + "UC" + "a" * 20])
@pytest.mark.parametrize("full_form", [False, True])
def test_exact_feed_identity_forms(monkeypatch, channel, full_form):
    monkeypatch.setattr(
        "youtube_intel.providers.youtube_channel.public_operation", lambda op: op()
    )
    root = ET.fromstring(RAW)
    root.find(YT + "channelId").text = channel if full_form else channel[2:]
    root.find(ATOM + "entry").find(YT + "channelId").text = channel
    provider = YouTubeFollowingProvider()
    provider._fetch = lambda _: ET.tostring(root)
    result = provider.enumerate(
        canonical_channel(channel), initial=True, next_page=1, known=(), verified_at=None
    )
    assert result.complete and len(result.items) == 1


BAD_FEEDS = [
    "b" * 22, "UC" + "b" * 22, "unrelated", CHANNEL[2:] + "x",
    "x" + CHANNEL[2:], CHANNEL[2:][:-1], " " + CHANNEL[2:], CHANNEL[2:] + " ",
    CHANNEL.lower(), "UC" + CHANNEL, "root", "missing_feed_id",
    "foreign_entry", "mixed", "stripped_entry", "missing_entry_id", "missing_published",
]


@pytest.mark.parametrize("mutation", BAD_FEEDS)
def test_feed_contract_fail_closed(monkeypatch, mutation):
    monkeypatch.setattr(
        "youtube_intel.providers.youtube_channel.public_operation", lambda op: op()
    )
    provider = YouTubeFollowingProvider()
    provider._fetch = lambda _: mutated_feed(mutation)
    with pytest.raises(TrackingError, match="METADATA_FAILED"):
        provider.enumerate(
            canonical_channel(CHANNEL), initial=True, next_page=1, known=(), verified_at=None
        )


@pytest.mark.parametrize("invalid", [CHANNEL[2:], "UC" + "a" * 21, "UC" + "a" * 23, "UC" + "/" * 22])
def test_invalid_canonical_identity_rejected_before_transport(monkeypatch, invalid):
    provider = YouTubeFollowingProvider()

    def forbidden(_):
        raise AssertionError("invalid identity must not reach the transport")

    provider._fetch = forbidden
    identity = SourceIdentity("YOUTUBE", "CHANNEL", invalid, "forged", "", "Fixture")
    with pytest.raises(TrackingError, match="SOURCE_UNTRUSTED"):
        provider.enumerate(identity, initial=True, next_page=1, known=(), verified_at=None)


def live_shape_setup(tmp_path, monkeypatch):
    support = _load_module("test_youtube_following")
    monkeypatch.setattr(support, "CHANNEL", CHANNEL)
    repo, tracker, fixture, runtime = support.youtube_setup(tmp_path, monkeypatch)
    tracker.providers["YOUTUBE"]._fetch = lambda _: RAW
    return repo, tracker, fixture, runtime


def observations(repo):
    with repo._connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM source_observations ORDER BY canonical_identity")]


def test_real_feed_shape_enumerates(monkeypatch):
    monkeypatch.setattr(
        "youtube_intel.providers.youtube_channel.public_operation", lambda op: op()
    )
    provider = YouTubeFollowingProvider()
    provider._fetch = lambda channel: RAW
    result = provider.enumerate(
        canonical_channel(CHANNEL), initial=True, next_page=1, known=(), verified_at=None
    )
    assert result.complete
    assert [item.identity for item in result.items] == ["oldvideo001"]


def test_real_feed_shape_establishes_baseline_without_history(tmp_path, monkeypatch):
    repo, tracker, fixture, runtime = live_shape_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    state = tracker.projection(source.source_id)
    assert state["baseline_at"] is not None
    assert state["verified_at"] is not None
    assert state["health"] == "HEALTHY"
    assert repo.list_videos() == ()
    assert source.channel_id == CHANNEL
    assert state["latest_published_at"] is not None
    baseline = observations(repo)
    assert len(baseline) == 1 and baseline[0]["enrollment"] == "BASELINE"
    assert baseline[0]["baseline"] == 1
    assert tracker.check(source.source_id) == "COOLDOWN"
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert observations(repo) == baseline
    assert repo.list_videos() == ()
    after = tracker.projection(source.source_id)
    assert after["latest_published_at"] == state["latest_published_at"]
    assert after["verified_at"] != state["verified_at"]  # truthful fresh verification
    assert repo.get_source_subscription(source.source_id).last_success_at == fixture.now
    fixture.publish("newvideo001")
    tracker.providers["YOUTUBE"]._fetch = lambda _: NEW_RAW
    assert tracker.check(source.source_id) == "COMPLETE"
    assert [v.video_id for v in repo.list_videos()] == ["newvideo001"]
    assert repo.get_verified_timed_transcript(video_id="newvideo001") is not None
    assert repo.current_local_summary_pointer("newvideo001") is not None
    assert len(repo.list_evidence_for_presentation("newvideo001")) > 0
    assert tracker.projection(source.source_id)["latest_published_at"] > after["latest_published_at"]
    enrolled = observations(repo)
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert observations(repo) == enrolled
    assert len(repo.list_videos()) == 1
    reopened_repo = SQLiteStateRepository(repo._database_path)
    reopened_repo.bind_source_storage(runtime._data_root)
    reopened = FollowingTrackingService(
        reopened_repo, tracker.publisher, youtube=tracker.providers["YOUTUBE"], now=lambda: fixture.now
    )
    assert reopened.projection(source.source_id) == tracker.projection(source.source_id)
    assert reopened_repo.get_source_subscription(source.source_id).channel_id == CHANNEL
    repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
    fixture.tick()
    assert reopened.check(source.source_id) == "PAUSED"
    repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
    assert reopened.check(source.source_id) == "COMPLETE"
    with repo._connect() as db:
        verify_tracking(db, repository=repo)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 34
        for pragma in ("quick_check", "integrity_check"):
            assert db.execute("PRAGMA " + pragma).fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("mutation", BAD_FEEDS + ["network"])
@pytest.mark.parametrize("initial", [False, True])
def test_invalid_feed_never_writes_partial_observations(tmp_path, monkeypatch, mutation, initial):
    repo, tracker, fixture, _ = live_shape_setup(tmp_path, monkeypatch)
    if not initial:
        source = tracker.follow(CHANNEL, provider="YOUTUBE")
        before = tracker.projection(source.source_id)
        success = repo.get_source_subscription(source.source_id).last_success_at
        old = observations(repo)
        fixture.tick()
    if mutation == "network":
        def fail(_):
            raise TrackingError("NETWORK_UNAVAILABLE")
        tracker.providers["YOUTUBE"]._fetch = fail
    else:
        tracker.providers["YOUTUBE"]._fetch = lambda _: mutated_feed(mutation)
    expected = "OFFLINE" if mutation == "network" else "PROVIDER_ERROR"
    if initial:
        source = tracker.follow(CHANNEL, provider="YOUTUBE")
        before = {key: None for key in ("baseline_at", "verified_at", "latest_published_at")}
        success, old = None, []
    else:
        assert tracker.check(source.source_id) == expected
    after = tracker.projection(source.source_id)
    assert after["health"] == expected and after["checking"] is False
    assert all(after[key] == before[key] for key in ("baseline_at", "verified_at", "latest_published_at"))
    assert repo.get_source_subscription(source.source_id).last_success_at == success
    assert observations(repo) == old
    assert repo.list_videos() == ()
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM source_checks WHERE status='RUNNING'").fetchone()[0] == 0
