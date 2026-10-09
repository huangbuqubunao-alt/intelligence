"""Provider-neutral tracking contract exercised by public YouTube fixtures."""

from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path

import pytest
from conftest import _load_module

from youtube_intel.bilibili_content import BilibiliContentProvider
from youtube_intel.config import load_app_config
from youtube_intel.domain import Availability, LiveStatus, VideoMetadata
from youtube_intel.following_provider import TrackingError
from youtube_intel.following_tracking import FollowingTrackingService
from youtube_intel.providers.youtube_channel import (
    YouTubeFollowingProvider,
    channel_input,
)
from youtube_intel.runtime import RuntimeDependencies, RuntimeOperations
from youtube_intel.state import SQLiteStateRepository

CHANNEL = "UC" + "a" * 22
NOW = datetime(2026, 10, 4, tzinfo=UTC)


def test_youtube_baseline_reuses_shared_tracking_without_history(
    tmp_path: Path,
) -> None:
    from youtube_intel.following_provider import Candidate, Enumeration, SourceIdentity

    class Fixture:
        provider = "YOUTUBE"

        def resolve(self, value):
            return SourceIdentity(
                "YOUTUBE",
                "CHANNEL",
                CHANNEL,
                "youtube-channel-" + CHANNEL,
                "https://www.youtube.com/channel/" + CHANNEL,
                "Public channel",
            )

        def enumerate(self, identity, *, initial, next_page, known, verified_at):
            return Enumeration(
                "Public channel",
                (Candidate("aaaaaaaaaaa", NOW - timedelta(days=1)),),
                True,
                1,
            )

        def enroll(self, *args, **kwargs):
            raise AssertionError("baseline must not import history")

    repo = SQLiteStateRepository(tmp_path / "state.sqlite")
    repo.initialize(now=NOW)
    publisher = BilibiliContentProvider(repo, tmp_path / "data")
    tracker = FollowingTrackingService(
        repo, publisher, youtube=Fixture(), now=lambda: NOW
    )
    source = tracker.follow("@public", provider="YOUTUBE")
    assert source.channel_id == CHANNEL
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["update_count"] == 0
    assert tracker.projection(source.source_id)["coverage"] == "COMPLETE"
    assert tracker.follow(CHANNEL, provider="YOUTUBE").source_id == source.source_id
    assert tracker.check(source.source_id) == "COOLDOWN"


OLD = "oldvideo001"
NEW = "newvideo001"
NEXT = "newvideo002"


class YouTubeFixture:
    def __init__(self):
        self.now = NOW
        self.name = "Public channel"
        self.items = [(OLD, NOW - timedelta(days=10))]
        self.failure = None
        self.caption = True
        self.live = LiveStatus.NONE
        self.metadata_channel = CHANNEL
        self.calls = []

    def feed(self, channel):
        self.calls.append(channel)
        if self.failure:
            raise TrackingError(self.failure)
        body = "".join(
            f"<entry><yt:videoId>{id}</yt:videoId><yt:channelId>{channel}</yt:channelId><title>Public video</title><published>{date.isoformat()}</published></entry>"
            for id, date in self.items
        )
        return (
            f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><yt:channelId>{channel}</yt:channelId><title>{escape(self.name)}</title>{body}</feed>'
        ).encode()

    def fetch(self, video_id):
        return VideoMetadata(
            video_id=video_id,
            channel_id=self.metadata_channel,
            channel_name=self.name,
            title="Sentence1 YouTube " + video_id,
            description="Public metadata",
            source_url="https://www.youtube.com/watch?v=" + video_id,
            published_at=dict(self.items)[video_id],
            duration_seconds=120,
            live_status=self.live,
            availability=Availability.PUBLIC,
            default_language="en",
            available_languages=("en",) if self.caption else (),
        )

    def tick(self):
        self.now += timedelta(hours=1)

    def publish(self, *ids):
        self.items = [
            (id, self.now + timedelta(seconds=i + 1)) for i, id in enumerate(ids)
        ] + self.items
        self.tick()


def youtube_setup(tmp_path, monkeypatch):
    from youtube_intel.providers import youtube_channel as module

    support = _load_module("test_runtime_composition")
    fixture = YouTubeFixture()
    project = support._project(tmp_path)
    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )
    subtitle = support._TimedSubtitleAdapter()
    original = subtitle.enumerate_tracks

    def enumerate_tracks(video_id):
        from youtube_intel.transcripts import SubtitleTrackListing

        listing = original(support.VIDEO_ID)
        return (
            listing
            if fixture.caption
            else SubtitleTrackListing(tracks=(), call=listing.call)
        )

    subtitle.enumerate_tracks = enumerate_tracks

    def denied():
        raise AssertionError("source discovery must never construct a model provider")

    runtime = RuntimeOperations(
        config=config,
        project_root=project,
        repository=SQLiteStateRepository(project / "state.sqlite"),
        dependencies=RuntimeDependencies(
            discovery_source=support._DiscoverySource(),
            metadata_provider=fixture,
            subtitle_adapter_factory=lambda: subtitle,
            scoring_provider_factory=denied,
            analysis_provider_factory=denied,
            quality_judge_provider_factory=denied,
        ),
    )
    monkeypatch.setattr("youtube_intel.runtime._utcnow", lambda: fixture.now)
    monkeypatch.setattr(module, "public_operation", lambda operation: operation())
    provider = YouTubeFollowingProvider(
        enroll_video=runtime.enroll_followed_youtube_video
    )
    provider._fetch = fixture.feed
    provider._resolve = lambda alias: module.canonical_channel(CHANNEL, fixture.name)
    repo = runtime._repository
    tracker = FollowingTrackingService(
        repo,
        BilibiliContentProvider(repo, runtime._data_root, now=lambda: fixture.now),
        youtube=provider,
        now=lambda: fixture.now,
    )
    tracker.providers["BILIBILI"].available = True  # Historical coexistence fixture only.
    return repo, tracker, fixture, runtime


@pytest.mark.parametrize(
    "value",
    [
        CHANNEL,
        "https://youtube.com/channel/" + CHANNEL,
        "https://www.youtube.com/channel/" + CHANNEL + "/",
        "@public",
        "https://youtube.com/@public",
    ],
)
def test_channel_inputs(value):
    assert channel_input(value) in {CHANNEL, "@public"}


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/@public",
        "https://youtube.com.evil/channel/" + CHANNEL,
        "http://youtube.com/@public",
        "https://youtube.com/watch?v=aaaaaaaaaaa",
        "https://127.0.0.1/@public",
        "https://youtube.com:443/@public",
        "https://user@youtube.com/@public",
        "https://youtube.com/@public?next=evil",
        "https://youtube.com/@public#x",
        "https://youtube.com/channel/UCbad",
        "@x",
        "@public\n",
        "file:///tmp/x",
    ],
)
def test_channel_inputs_reject_arbitrary_urls(value):
    with pytest.raises(TrackingError, match="INVALID_INPUT"):
        channel_input(value)


def test_full_incremental_normal_ingestion_restart_dedupe(tmp_path, monkeypatch):
    repo, tracker, fixture, runtime = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow("https://youtube.com/@public", provider="YOUTUBE")
    assert repo.list_videos() == ()
    assert tracker.projection(source.source_id)["update_count"] == 0
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    fixture.publish(NEW, NEXT)
    # An ordinary manual YouTube import before discovery uses the same id.
    repo.upsert_video_metadata(
        fixture.fetch(NEW), pipeline_version="runtime-v1", now=fixture.now
    )
    assert tracker.check(source.source_id) == "COMPLETE"
    assert {v.video_id for v in repo.list_videos()} == {NEW, NEXT}
    for id in (NEW, NEXT):
        assert repo.get_verified_timed_transcript(video_id=id) is not None
        assert repo.current_local_summary_pointer(id) is not None
        assert repo.list_evidence_for_presentation(id)
        assert all(
            job.target_stage.value != "SCORING" for job in repo.list_video_jobs(id)
        )
    assert tracker.follow_content(NEW, provider="YOUTUBE").source_id == source.source_id
    fixture.name = "Renamed channel"
    fixture.items.reverse()
    fixture.items.append(fixture.items[0])
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert tracker.follow("@renamed", provider="YOUTUBE").source_id == source.source_id
    reopened = FollowingTrackingService(
        SQLiteStateRepository(runtime._repository._database_path),
        tracker.publisher,
        youtube=tracker.providers["YOUTUBE"],
        now=lambda: fixture.now,
    )
    fixture.tick()
    assert reopened.check(source.source_id) == "COMPLETE"
    assert reopened.projection(source.source_id)["update_count"] == 2


@pytest.mark.parametrize(
    "failure,health",
    [
        ("NETWORK_UNAVAILABLE", "OFFLINE"),
        ("RATE_LIMITED", "RATE_LIMITED"),
        ("ACCESS_DENIED", "ACCESS_DENIED"),
        ("METADATA_FAILED", "PROVIDER_ERROR"),
    ],
)
def test_youtube_failure_preserves_frontier(tmp_path, monkeypatch, failure, health):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    before = tracker.projection(source.source_id)
    fixture.tick()
    fixture.failure = failure
    assert tracker.check(source.source_id) == health
    assert tracker.projection(source.source_id)["verified_at"] == before["verified_at"]
    assert repo.get_source_subscription(source.source_id).last_success_at == NOW
    assert repo.list_videos() == ()


def test_lost_overlap_partial_retry_and_historical_resurfacing(tmp_path, monkeypatch):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    before = tracker.projection(source.source_id)["verified_at"]
    fixture.publish(NEW)
    old = fixture.items.pop()
    assert tracker.check(source.source_id) == "UPDATE_GAP"
    assert tracker.projection(source.source_id)["verified_at"] == before
    assert repo.get_source_subscription(source.source_id).last_success_at == NOW
    assert repo.get_video(NEW) is not None  # durable pending acquisition remains usable
    fixture.items += [old, ("olderitem01", NOW - timedelta(days=100))]
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert tracker.projection(source.source_id)["update_count"] == 1
    assert repo.get_video("olderitem01") is None


def test_pause_no_transcript_no_models_and_wrong_channel(tmp_path, monkeypatch):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    fixture.publish(NEW)
    repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
    assert tracker.check(source.source_id) == "PAUSED"
    assert repo.list_videos() == ()
    repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
    fixture.caption = False
    assert tracker.check(source.source_id) == "COMPLETE"
    assert repo.get_video(NEW) is not None
    assert repo.get_verified_timed_transcript(video_id=NEW) is None
    assert repo.current_local_summary_pointer(NEW) is None
    fixture.publish(NEXT)
    fixture.metadata_channel = "UC" + "b" * 22
    tracker.check(source.source_id)
    assert repo.get_video(NEXT) is None
    assert tracker.projection(source.source_id)["update_count"] == 1


def test_mixed_provider_backup_restore_research_delta_and_database(
    tmp_path, monkeypatch
):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.following_tracking import verify_tracking
    from youtube_intel.local_content import LocalContentProvider
    from youtube_intel.providers.bilibili import BilibiliAdapter
    from youtube_intel.research_contract import ResearchRequest
    from youtube_intel.research_lite import ResearchLiteService

    repo, tracker, fixture, runtime = youtube_setup(tmp_path, monkeypatch)
    bili = _load_module("test_creator_following").CreatorFixture()
    tracker.publisher.adapter = BilibiliAdapter(fetch=bili.fetch)
    yt = tracker.follow("@public", provider="YOUTUBE")
    bs = tracker.follow("123")
    fixture.publish(NEW)
    bili.items.insert(0, ("BV1xx411c7mE", NOW + timedelta(seconds=1)))
    bili.now = fixture.now
    assert tracker.check(yt.source_id) == "COMPLETE"
    assert tracker.check(bs.source_id) == "COMPLETE"
    local = LocalContentProvider(
        repo, runtime._data_root, now=lambda: fixture.now
    ).import_bytes("Sentence1 local.md", b"Sentence1 local public evidence.\n")
    research = ResearchLiteService(repo, now=lambda: fixture.now)
    packet = research.assemble(
        ResearchRequest(
            question="sentence1 public",
            content_ids=[NEW, "bilibili-BV1xx411c7mE", local.content_id],
        ),
        output_language="en",
    )
    assert {item.provider for item in packet.packet.evidence} == {
        "YOUTUBE",
        "BILIBILI",
        "LOCAL",
    }
    from youtube_intel.intelligence_read import AuthoritativeIntelligenceReader
    from youtube_intel.research_contract import digest
    from youtube_intel.state import (
        DependencyEdgeWrite,
        DependencyRelation,
        IntelligenceClaimKind,
        IntelligenceInterpretationKind,
        IntelligenceRevisionWrite,
        IntelligenceState,
    )

    refs = tuple(item.evidence_id for item in packet.packet.evidence)
    repo.create_intelligence(intelligence_id="followed-mixed", now=fixture.now)
    repo.append_intelligence_revision(
        intelligence_id="followed-mixed",
        revision=IntelligenceRevisionWrite(
            revision_id="followed-mixed-revision",
            interpretation_kind=IntelligenceInterpretationKind.SYNTHESIS,
            claim_kind=IntelligenceClaimKind.EVIDENCE_BACKED_STATEMENT,
            content_hash=digest({"evidence": refs}),
            state=IntelligenceState.NEW,
            reason="Normal sealed evidence admission across followed sources",
            evidence_ids=refs,
        ),
        now=fixture.now,
    )
    for index, evidence_id in enumerate(refs):
        repo.create_dependency_edge(
            DependencyEdgeWrite(
                edge_id=f"followed-edge-{index}",
                dependent_revision_id="followed-mixed-revision",
                relation=DependencyRelation.EVIDENCE_SUPPORT,
                input_evidence_id=evidence_id,
                input_revision_id=None,
            ),
            now=fixture.now,
        )
    assert set(
        AuthoritativeIntelligenceReader(repo)
        .read_current("followed-mixed")
        .evidence_ids
    ) == set(refs)
    assert repo.list_topics() == ()
    before = {id: tracker.projection(id) for id in (yt.source_id, bs.source_id)}
    backup = BackupRestoreService(
        database=repo._database_path, data_root=runtime._data_root
    )
    result = backup.create_backup()
    archive, _ = backup.backup_download(result.backup_id)
    staged = backup.stage_restore(archive.read_bytes())
    backup.confirm_restore(staged.restore_id)
    backup.recover_and_apply_pending_restore()
    assert {id: tracker.projection(id) for id in before} == before
    fixture.tick()
    bili.now = fixture.now
    assert tracker.check(yt.source_id) == "COMPLETE"
    assert tracker.check(bs.source_id) == "COMPLETE"
    assert len(repo.list_videos()) == 3
    with repo._connect() as connection:
        verify_tracking(connection, repository=repo)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 36
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("mutation", ["cross_provider", "wrong_channel", "extra_link"])
def test_forged_tracking_relationships_rejected(tmp_path, monkeypatch, mutation):
    from youtube_intel.following_tracking import verify_tracking

    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    fixture.publish(NEW)
    assert tracker.check(source.source_id) == "COMPLETE"
    with repo._connect() as connection:
        if mutation == "cross_provider":
            import sqlite3

            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(
                    "UPDATE videos SET provider='BILIBILI' WHERE video_id=?", (NEW,)
                )
            # Simulate a forged archive in this temporary fixture only.
            connection.execute("DROP TRIGGER video_provider_identity_immutable")
            connection.execute(
                "UPDATE videos SET provider='BILIBILI' WHERE video_id=?", (NEW,)
            )
        elif mutation == "wrong_channel":
            connection.execute(
                "UPDATE videos SET channel_id=? WHERE video_id=?",
                ("UC" + "b" * 22, NEW),
            )
        else:
            repo.upsert_video_metadata(
                fixture.fetch(OLD), pipeline_version="runtime-v1", now=fixture.now
            )
            connection.execute(
                "INSERT INTO source_video_links(source_id,video_id,discovered_at) VALUES(?,?,?)",
                (source.source_id, OLD, fixture.now.isoformat()),
            )
        with pytest.raises(ValueError):
            verify_tracking(connection, repository=repo)
    assert tracker.projection(source.source_id)["health"] == "STATE_INVALID"
    assert repo.get_video(NEW) is not None


@pytest.mark.parametrize(
    "raw",
    [
        b"<html>changed provider</html>",
        b"<feed/>",
        b"bad xml",
        b"x" * (256 * 1024 + 1),
        b'<!DOCTYPE x [<!ENTITY y "oops">]><feed/>',
    ],
)
def test_malformed_bounded_feed_cannot_advance(tmp_path, monkeypatch, raw):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    before = tracker.projection(source.source_id)["verified_at"]
    tracker.providers["YOUTUBE"]._fetch = lambda channel: raw
    fixture.tick()
    assert tracker.check(source.source_id) == "PROVIDER_ERROR"
    assert tracker.projection(source.source_id)["verified_at"] == before
    assert repo.list_videos() == ()


def test_enrollment_bounded_pending_retry_and_removed_authority(tmp_path, monkeypatch):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    fixture.publish(*["video%06d" % i for i in range(9)])
    assert tracker.check(source.source_id) == "COMPLETE"
    assert len(repo.list_videos()) == 5
    assert tracker.projection(source.source_id)["pending_count"] == 4
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert len(repo.list_videos()) == 9
    fixture.items = [(OLD, NOW - timedelta(days=10))]
    fixture.tick()
    assert tracker.check(source.source_id) == "UPDATE_GAP"
    assert len(repo.list_videos()) == 9
    assert all(
        repo.current_local_summary_pointer(v.video_id) for v in repo.list_videos()
    )


def test_public_provider_budget_is_independent_bounded_and_rate_cooled(monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from youtube_intel.following_tracking import _CHECK_SLOTS
    from youtube_intel.providers import youtube_channel as module

    monkeypatch.setattr(module, "_NEXT", 0.0)
    monkeypatch.setattr(module, "_RATE_UNTIL", 0.0)
    entered, release = threading.Event(), threading.Event()

    def blocked():
        entered.set()
        assert release.wait(5)
        return "finished"

    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(module.public_operation, blocked)
        assert entered.wait(5)
        try:
            with pytest.raises(TrackingError, match="RATE_LIMITED"):
                module.public_operation(lambda: "must not run")
            assert _CHECK_SLOTS["BILIBILI"] is not _CHECK_SLOTS["YOUTUBE"]
        finally:
            release.set()
        assert pending.result() == "finished"

    def limited():
        raise TrackingError("RATE_LIMITED")

    with pytest.raises(TrackingError, match="RATE_LIMITED"):
        module.public_operation(limited)
    with pytest.raises(TrackingError, match="RATE_LIMITED"):
        module.public_operation(lambda: pytest.fail("provider cooldown must block"))


@pytest.mark.parametrize("live", [LiveStatus.LIVE, LiveStatus.UPCOMING])
def test_unsupported_video_does_not_enroll_or_trigger_models(
    tmp_path, monkeypatch, live
):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    fixture.publish(NEW)
    fixture.live = live
    assert tracker.check(source.source_id) == "COMPLETE"
    assert repo.get_video(NEW) is None
    assert tracker.projection(source.source_id)["unavailable_count"] == 1
    assert tracker.projection(source.source_id)["update_count"] == 0


def test_pause_during_metadata_blocks_atomic_content_enrollment(tmp_path, monkeypatch):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    fixture.publish(NEW)
    original = fixture.fetch

    def pause(video_id):
        repo.update_source_subscription(
            source.source_id, enabled=False, now=fixture.now
        )
        return original(video_id)

    fixture.fetch = pause
    tracker.check(source.source_id)
    assert repo.get_video(NEW) is None
    assert tracker.projection(source.source_id)["pending_count"] == 1
    fixture.fetch = original
    repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert repo.get_video(NEW) is not None


def test_healthy_polling_has_no_knowledge_delta_and_empty_channel_is_safe(
    tmp_path, monkeypatch
):
    from youtube_intel.knowledge_delta import KnowledgeDeltaService

    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    fixture.items = []
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    before = (
        KnowledgeDeltaService(repo, now=lambda: fixture.now)
        .read()
        .as_dict()["categories"]
    )
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert (
        KnowledgeDeltaService(repo, now=lambda: fixture.now)
        .read()
        .as_dict()["categories"]
        == before
    )
    fixture.publish(NEW)
    assert tracker.check(source.source_id) == "COMPLETE"
    assert tracker.projection(source.source_id)["update_count"] == 1
    assert repo.list_topics() == ()


def test_initial_caption_network_retry_remains_durable_and_recovers(
    tmp_path, monkeypatch
):
    from youtube_intel.discovery import AdapterError
    from youtube_intel.domain import AppError, ErrorCode

    repo, tracker, fixture, runtime = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    adapter = runtime._dependencies.subtitle_adapter_factory()
    original = adapter.enumerate_tracks

    def offline(video_id):
        raise AdapterError(
            AppError(
                code=ErrorCode.TRANSIENT_NETWORK,
                message="Public caption network unavailable",
                retryable=True,
                retry_after_seconds=1,
            )
        )

    adapter.enumerate_tracks = offline
    fixture.publish(NEW)
    assert tracker.check(source.source_id) == "OFFLINE"
    assert repo.get_video(NEW) is not None
    assert repo.get_source_subscription(source.source_id).last_success_at == NOW
    assert tracker.projection(source.source_id)["pending_count"] == 1
    assert repo.current_local_summary_pointer(NEW) is None
    adapter.enumerate_tracks = original
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert tracker.projection(source.source_id)["pending_count"] == 0
    assert tracker.projection(source.source_id)["update_count"] == 1
    assert len(repo.list_videos()) == 1
    assert repo.current_local_summary_pointer(NEW) is not None


def test_stable_source_id_rejects_channel_rebinding_before_content(
    tmp_path, monkeypatch
):
    from youtube_intel.following_tracking import verify_tracking

    repo, tracker, _, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    forged = "UC" + "b" * 22
    with repo._connect() as connection:
        connection.execute(
            "UPDATE source_subscriptions SET channel_id=?,canonical_url=? WHERE source_id=?",
            (forged, "https://www.youtube.com/channel/" + forged, source.source_id),
        )
        with pytest.raises(ValueError, match="identity is corrupt"):
            verify_tracking(connection, source.source_id, repository=repo)
    assert tracker.projection(source.source_id)["health"] == "STATE_INVALID"
    assert repo.list_videos() == ()


@pytest.mark.parametrize("provider", ["YOUTUBE", "BILIBILI"])
def test_failed_bounded_tracking_run_is_terminal_and_backups_work_offline(
    tmp_path, monkeypatch, provider
):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.providers.bilibili import BilibiliAdapter
    from youtube_intel.runtime_composition import RuntimeSourceRunIngestion
    from youtube_intel.source_run import SourceRunPriority, SourceRunState

    repo, tracker, fixture, runtime = youtube_setup(tmp_path, monkeypatch)
    bili = _load_module("test_creator_following").CreatorFixture()
    tracker.publisher.adapter = BilibiliAdapter(fetch=bili.fetch)
    source = tracker.follow(
        CHANNEL if provider == "YOUTUBE" else "123", provider=provider
    )
    before = tracker.projection(source.source_id)["verified_at"]
    fixture.tick()
    bili.now = fixture.now
    fixture.failure = bili.failure = "NETWORK_UNAVAILABLE"
    support = _load_module("test_task024_processing_orchestration")
    transport = support._Transport(available=False)
    orchestration = support._orchestrator(repo, transport)
    orchestration._now = lambda: fixture.now
    orchestration._ingestion = RuntimeSourceRunIngestion(
        runtime, orchestration._source_policy, tracker
    )
    run = orchestration.enqueue_manual_check_now(
        source_id=source.source_id,
        command_id="offline-tracked",
        priority=SourceRunPriority.P0,
    )
    assert orchestration.resume(run.run_id).state is SourceRunState.FAILED
    assert tracker.projection(source.source_id)["health"] == "OFFLINE"
    assert tracker.projection(source.source_id)["verified_at"] == before
    assert not tracker.projection(source.source_id)["checking"]
    assert transport.calls == 0
    service = BackupRestoreService(
        database=repo._database_path, data_root=runtime._data_root
    )
    created = service.create_backup()
    archive, _ = service.backup_download(created.backup_id)
    staged = service.stage_restore(archive.read_bytes())
    service.confirm_restore(staged.restore_id)
    service.recover_and_apply_pending_restore()
    assert tracker.projection(source.source_id)["verified_at"] == before


def test_pause_cancels_queued_tracking_run_without_blocking_backup(
    tmp_path, monkeypatch
):
    from youtube_intel.backup_restore import BackupRestoreService
    from youtube_intel.runtime_composition import RuntimeSourceRunIngestion
    from youtube_intel.source_run import SourceRunPriority, SourceRunState

    repo, tracker, fixture, runtime = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    support = _load_module("test_task024_processing_orchestration")
    transport = support._Transport(available=False)
    orchestration = support._orchestrator(repo, transport)
    orchestration._now = lambda: fixture.now
    orchestration._ingestion = RuntimeSourceRunIngestion(
        runtime, orchestration._source_policy, tracker
    )
    run = orchestration.enqueue_manual_check_now(
        source_id=source.source_id,
        command_id="queued-before-pause",
        priority=SourceRunPriority.P0,
    )
    repo.update_source_subscription(source.source_id, enabled=False, now=fixture.now)
    calls = len(fixture.calls)
    assert orchestration.resume(run.run_id).state is SourceRunState.CANCELLED
    assert len(fixture.calls) == calls and transport.calls == 0
    assert repo.list_videos() == ()
    assert BackupRestoreService(
        database=repo._database_path, data_root=runtime._data_root
    ).create_backup()


def test_stale_lifecycle_check_is_bounded_fair_across_providers(tmp_path, monkeypatch):
    monkeypatch.setattr("youtube_intel.local_api.CREATOR_FOLLOWING_AVAILABLE", True)  # Fixture availability.
    from youtube_intel.local_api import LocalApiApplication
    from youtube_intel.orchestration_service import ProductOrchestrationService
    from youtube_intel.providers.bilibili import BilibiliAdapter
    from youtube_intel.providers.youtube_channel import canonical_channel

    repo, tracker, fixture, runtime = youtube_setup(tmp_path, monkeypatch)
    bili = _load_module("test_creator_following").CreatorFixture()
    tracker.publisher.adapter = BilibiliAdapter(fetch=bili.fetch)
    bs = tracker.follow("123")
    tracker.providers["YOUTUBE"]._resolve = lambda alias: canonical_channel(
        alias, "Public channel"
    )
    ys = []
    for letter in "abcd":
        fixture.now += timedelta(minutes=1)
        ys.append(tracker.follow("UC" + letter * 22, provider="YOUTUBE"))
    fixture.tick()
    bili.now = fixture.now
    for source in ys:
        repo.update_source_subscription(source.source_id, enabled=True, now=fixture.now)
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(
            repo, source_tracking=tracker, now=lambda: fixture.now
        ),
        source_tracking=tracker,
        data_root=runtime._data_root,
        now=lambda: fixture.now,
    )
    status, result = app.handle("POST", "/api/v1/sources/check-stale", b"{}")
    assert status == 202
    assert len(result["checks"]) == 3
    assert repo.get_source_subscription(bs.source_id).last_checked_at == fixture.now
    status, result = app.handle("POST", "/api/v1/sources/check-stale", b"{}")
    assert status == 202 and len(result["checks"]) == 2
    assert all(
        repo.get_source_subscription(s.source_id).last_checked_at == fixture.now
        for s in [bs, *ys]
    )
    assert repo.list_videos() == ()


@pytest.mark.parametrize("older_day", [False, True])
def test_feed_publication_disambiguates_date_only_metadata(tmp_path, monkeypatch, older_day):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    fixture.publish(NEW)
    fetch = fixture.fetch

    def date_only(video_id):
        metadata = fetch(video_id)
        return metadata.model_copy(update={
            "published_at": NOW - timedelta(days=int(older_day))
        })

    fixture.fetch = date_only
    assert tracker.check(source.source_id) == "COMPLETE"
    if older_day:
        assert repo.list_videos() == ()
        assert tracker.projection(source.source_id)["update_count"] == 0
    else:
        assert [video.video_id for video in repo.list_videos()] == [NEW]
        assert repo.get_verified_timed_transcript(video_id=NEW) is not None
        assert tracker.projection(source.source_id)["update_count"] == 1


def test_invalid_video_metadata_preserves_pending_and_truthful_health(tmp_path, monkeypatch):
    repo, tracker, fixture, _ = youtube_setup(tmp_path, monkeypatch)
    source = tracker.follow(CHANNEL, provider="YOUTUBE")
    trusted_success = repo.get_source_subscription(source.source_id).last_success_at
    fixture.publish(NEW)
    fetch = fixture.fetch

    def invalid(video_id):
        raise TrackingError("METADATA_FAILED")

    fixture.fetch = invalid
    assert tracker.check(source.source_id) == "PROVIDER_ERROR"
    assert repo.get_source_subscription(source.source_id).last_success_at == trusted_success
    assert tracker.projection(source.source_id)["pending_count"] == 1
    assert repo.list_videos() == ()
    fixture.fetch = fetch
    fixture.tick()
    assert tracker.check(source.source_id) == "COMPLETE"
    assert [video.video_id for video in repo.list_videos()] == [NEW]
