"""Forward-integration acceptance: production capability vs retained authority."""

import json
from datetime import timedelta

import pytest
from conftest import _load_module

from youtube_intel.following_provider import TrackingError
from youtube_intel.local_api import ApiError, LocalApiApplication
from youtube_intel.orchestration_service import ProductOrchestrationService
from youtube_intel.providers.bilibili import BilibiliAdapter
from youtube_intel.runtime_composition import RuntimeSourceRunIngestion
from youtube_intel.source_run import SourceRunState


def setup(tmp_path, monkeypatch):
    youtube = _load_module("test_youtube_following")
    repo, tracker, fixture, runtime = youtube.youtube_setup(tmp_path, monkeypatch)
    bili = _load_module("test_creator_following").CreatorFixture()
    tracker.publisher.adapter = BilibiliAdapter(fetch=bili.fetch)
    stored = tracker.follow("123")  # Historical provider fixture, before withdrawal.
    tracker.providers["BILIBILI"].available = False
    app = LocalApiApplication(
        repo,
        ProductOrchestrationService(repo, source_tracking=tracker, now=lambda: fixture.now),
        source_tracking=tracker,
        bilibili_adapter=tracker.publisher.adapter,
        data_root=runtime._data_root,
        now=lambda: fixture.now,
    )
    return youtube, repo, tracker, fixture, runtime, bili, stored, app


def test_public_youtube_api_survives_bilibili_withdrawal(tmp_path, monkeypatch):
    youtube, repo, tracker, fixture, runtime, bili, stored, app = setup(tmp_path, monkeypatch)
    calls = len(bili.calls)
    status, settings = app.handle("GET", "/api/v1/settings")
    assert status == 200
    assert settings["bilibili"]["creator_following"]["available"] is False
    assert settings["bilibili"]["public_captions"]["available"] is False
    assert settings["bilibili"]["video_ingestion"]["available"] is True
    assert settings["youtube"]["channel_following"]["available"] is True
    status, body = app.handle("POST", "/api/v1/sources/channels", b'{"input":"@public"}')
    assert status == 200
    source_id = body["source"]["source_id"]
    assert body["source"]["tracking"]["baseline_at"] is not None
    assert repo.list_videos() == ()
    fixture.tick()
    status, body = app.handle("POST", f"/api/v1/sources/{source_id}/check", b'{"command_id":"youtube-check"}')
    assert status == 200 and body["message"] == "COMPLETE"
    before = tracker.projection(stored.source_id)
    status, body = app.handle("POST", f"/api/v1/sources/{stored.source_id}/check", b'{"command_id":"withdrawn-check"}')
    assert status == 200 and body["status"] == "CAPABILITY_UNAVAILABLE"
    assert tracker.projection(stored.source_id) == before
    assert len(bili.calls) == calls
    with pytest.raises(ApiError) as refusal:
        app.handle("POST", "/api/v1/sources/creators", b'{"input":"456"}')
    assert refusal.value.status == 409
    assert refusal.value.code == "BILIBILI_CREATOR_TRACKING_UNAVAILABLE"
    assert repo.get_source_subscription("bilibili-creator-456") is None
    assert len(bili.calls) == calls


def test_withdrawn_due_creators_do_not_starve_youtube(tmp_path, monkeypatch):
    youtube, repo, tracker, fixture, runtime, bili, stored, app = setup(tmp_path, monkeypatch)
    from youtube_intel.providers.youtube_channel import canonical_channel

    tracker.providers["YOUTUBE"]._resolve = lambda alias: canonical_channel(alias, "Public channel")
    channels = []
    for letter in "abcd":
        fixture.now += timedelta(minutes=1)
        channels.append(tracker.follow("UC" + letter * 22, provider="YOUTUBE"))
    fixture.tick()
    calls = len(bili.calls)
    for _ in range(2):
        status, body = app.handle("POST", "/api/v1/sources/check-stale", b"{}")
        assert status == 202
        assert sum(check == "SUCCEEDED" for check in body["checks"]) <= 3
        assert "CAPABILITY_UNAVAILABLE" in body["checks"]
    assert all(repo.get_source_subscription(source.source_id).last_checked_at == fixture.now for source in channels)
    assert repo.get_source_subscription(stored.source_id).last_checked_at != fixture.now
    assert len(bili.calls) == calls
    assert repo.list_videos() == ()


def test_withdrawal_blocks_direct_and_previously_queued_execution(tmp_path, monkeypatch):
    youtube, repo, tracker, fixture, runtime, bili, stored, app = setup(tmp_path, monkeypatch)
    fixture.tick()
    calls = len(bili.calls)
    assert tracker.check(stored.source_id) == "CAPABILITY_UNAVAILABLE"
    try:
        tracker.follow("456")
    except TrackingError as error:
        assert error.code == "CREATOR_TRACKING_UNAVAILABLE"
    else:
        raise AssertionError("A withdrawn provider cannot create a live Following")
    runs = _load_module("test_task024_processing_orchestration")
    orchestrator = runs._orchestrator(repo, runs._Transport(available=False))
    orchestrator._now = lambda: fixture.now
    orchestrator._ingestion = RuntimeSourceRunIngestion(runtime, orchestrator._source_policy, tracker)
    run = orchestrator.enqueue_manual_check_now(source_id=stored.source_id, command_id="pre-withdrawal-queued")
    outcome = orchestrator.resume(run.run_id)
    assert outcome.state is SourceRunState.FAILED
    assert len(bili.calls) == calls
    assert repo.get_source_subscription("bilibili-creator-456") is None
    assert tracker.projection(stored.source_id)["checking"] is False


def test_initial_failed_youtube_baseline_is_durable_and_retryable(tmp_path, monkeypatch):
    youtube, repo, tracker, fixture, runtime, bili, stored, app = setup(tmp_path, monkeypatch)
    fixture.failure = "NETWORK_UNAVAILABLE"
    status, body = app.handle("POST", "/api/v1/sources/channels", b'{"input":"@public"}')
    assert status == 200
    source = body["source"]
    assert source["tracking"]["baseline_at"] is None
    assert source["tracking"]["health"] == "OFFLINE"
    assert source["last_success_at"] is None
    assert repo.list_videos() == ()
    fixture.failure = None
    fixture.tick()
    status, body = app.handle("POST", f'/api/v1/sources/{source["source_id"]}/check', json.dumps({"command_id": "baseline-retry"}).encode())
    assert status == 200 and body["message"] == "COMPLETE"
    projection = tracker.projection(source["source_id"])
    assert projection["baseline_at"] is not None and projection["update_count"] == 0
    assert repo.list_videos() == ()
