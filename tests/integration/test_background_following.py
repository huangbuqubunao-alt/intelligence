"""Phase 13 uses production composition; only external boundaries are controlled."""

import threading
from datetime import timedelta

import pytest
from conftest import _load_module

from youtube_intel.config import load_app_config
from youtube_intel.following_tracking import _stamp
from youtube_intel.providers.youtube_channel import canonical_channel
from youtube_intel.runtime import RuntimeDependencies
from youtube_intel.runtime_composition import build_local_source_run_runtime
from youtube_intel.source_run import SourceRunState


def setup_runtime(tmp_path, monkeypatch, fixture=None):
    support = _load_module("test_runtime_composition")
    youtube = _load_module("test_youtube_following")
    fixture = fixture or youtube.YouTubeFixture()
    project = tmp_path if (tmp_path / "config").exists() else support._project(tmp_path)
    config = load_app_config(
        project / "config/channels.yaml", project / "config/settings.yaml"
    )

    def denied():
        raise AssertionError("automatic tracking must never construct a model")

    subtitle = support._TimedSubtitleAdapter()
    original_enumerate = subtitle.enumerate_tracks
    subtitle.enumerate_tracks = lambda video_id: original_enumerate(support.VIDEO_ID)

    monkeypatch.setattr("youtube_intel.runtime._utcnow", lambda: fixture.now)
    monkeypatch.setattr(
        "youtube_intel.providers.youtube_channel.public_operation",
        lambda operation: operation(),
    )
    composition = build_local_source_run_runtime(
        config=config, project_root=project, database=project / "state.sqlite",
        dependencies=RuntimeDependencies(
            discovery_source=support._DiscoverySource(), metadata_provider=fixture,
            subtitle_adapter_factory=lambda: subtitle, scoring_provider_factory=denied,
            analysis_provider_factory=denied, quality_judge_provider_factory=denied,
        ),
        now=lambda: fixture.now,
    )
    tracker = composition.application._source_tracking
    tracker.providers["YOUTUBE"]._fetch = fixture.feed
    tracker.providers["YOUTUBE"]._resolve = lambda value: canonical_channel(youtube.CHANNEL, fixture.name)
    source = tracker.follow(youtube.CHANNEL, provider="YOUTUBE")
    return composition, fixture, source


def test_due_following_is_checked_without_a_ui_event(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    run = composition.worker.run_once()
    assert run is not None and run.state is SourceRunState.COMPLETED
    assert run.source_id == source.source_id
    assert len(fixture.calls) == 2  # baseline, then one automatic check
    assert composition.repository.get_source_subscription(source.source_id).last_success_at == fixture.now
    assert composition.repository.list_videos() == ()


def test_not_due_source_is_not_checked(tmp_path, monkeypatch):
    composition, fixture, _ = setup_runtime(tmp_path, monkeypatch)
    assert composition.worker.run_once() is None
    assert len(fixture.calls) == 1


def test_pause_and_resume_reenter_durable_scheduling(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    composition.product.update_source(source.source_id, enabled=False)
    assert composition.worker.run_once() is None
    assert len(fixture.calls) == 1
    composition.product.update_source(source.source_id, enabled=True)
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(fixture.calls) == 2


@pytest.mark.parametrize("failure,minimum", [
    ("NETWORK_UNAVAILABLE", 60), ("RATE_LIMITED", 900),
    ("METADATA_FAILED", 3600), ("RESPONSE_TOO_LARGE", 3600),
])
def test_automatic_failures_back_off_without_fabricating_frontier(
    tmp_path, monkeypatch, failure, minimum
):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    tracker = composition.application._source_tracking
    before = tracker.projection(source.source_id)
    fixture.now += timedelta(minutes=16)
    fixture.failure = failure
    run = composition.worker.run_once()
    assert run.state is SourceRunState.FAILED
    after = tracker.projection(source.source_id)
    assert after["verified_at"] == before["verified_at"]
    assert after["latest_published_at"] == before["latest_published_at"]
    assert (_stamp(after["next_check_at"]) - fixture.now).total_seconds() >= minimum
    assert after["checking"] is False
    assert composition.worker.run_once() is None


def test_network_backoff_grows_and_recovery_needs_no_restart(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    tracker = composition.application._source_tracking
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NETWORK_UNAVAILABLE"
    assert composition.worker.run_once().state is SourceRunState.FAILED
    first_due = _stamp(tracker.projection(source.source_id)["next_check_at"])
    fixture.now = first_due
    assert composition.worker.run_once().state is SourceRunState.FAILED
    second_due = _stamp(tracker.projection(source.source_id)["next_check_at"])
    assert second_due - fixture.now >= timedelta(minutes=2)
    fixture.now = second_due
    fixture.failure = None
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert tracker.projection(source.source_id)["health"] == "HEALTHY"
    assert _stamp(tracker.projection(source.source_id)["next_check_at"]) - fixture.now == timedelta(minutes=15)


def test_manual_retry_after_five_seconds_bypasses_only_network_backoff(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    fixture.failure = "NETWORK_UNAVAILABLE"
    assert composition.worker.run_once().state is SourceRunState.FAILED
    fixture.now += timedelta(seconds=5)
    fixture.failure = None
    status, payload = composition.application.handle(
        "POST", f"/api/v1/sources/{source.source_id}/check",
        b'{"command_id":"explicit-network-retry"}',
    )
    assert status == 202
    assert composition.worker.run_once().run_id == payload["source_run"]["run_id"]
    assert composition.application._source_tracking.projection(source.source_id)["health"] == "HEALTHY"


def test_protected_backup_window_does_not_admit_automatic_work(tmp_path, monkeypatch):
    composition, fixture, _ = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    with composition.backup_restore._protect_background():
        assert composition.worker.run_once() is None
        assert len(fixture.calls) == 1
        assert composition.repository.list_source_runs() == ()
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert composition.backup_restore.readiness()["ready"] is True


def test_manual_and_background_admission_reuse_one_run(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    scheduler = composition.worker.scheduler
    scheduler.admit_due()
    manual = composition.product.check_source(source.source_id, command_id="manual-race")
    runs = composition.repository.list_source_runs()
    assert len(runs) == 1 and manual.source_run.run_id == runs[0].run_id
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(fixture.calls) == 2


def test_overlapping_worker_ticks_and_backup_are_bounded(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    fixture.now += timedelta(minutes=16)
    entered, release = threading.Event(), threading.Event()
    tracker = composition.application._source_tracking

    def blocked(channel):
        entered.set()
        assert release.wait(5)
        return fixture.feed(channel)

    tracker.providers["YOUTUBE"]._fetch = blocked
    results = []
    thread = threading.Thread(target=lambda: results.append(composition.worker.run_once()))
    thread.start()
    try:
        assert entered.wait(5)
        assert composition.worker.run_once() is None
        assert tracker.projection(source.source_id)["checking"] is True
        assert composition.backup_restore.readiness()["ready"] is False
        assert len(composition.repository.list_source_runs()) == 1
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert results[0].state is SourceRunState.COMPLETED
    assert composition.backup_restore.readiness()["ready"] is True


def test_restart_preserves_next_check_and_paused_state(tmp_path, monkeypatch):
    first, fixture, source = setup_runtime(tmp_path, monkeypatch)
    before = first.application._source_tracking.projection(source.source_id)
    second, fixture, source = setup_runtime(tmp_path, monkeypatch, fixture)
    assert second.worker.run_once() is None
    assert second.application._source_tracking.projection(source.source_id) == before
    first.product.update_source(source.source_id, enabled=False)
    third, fixture, source = setup_runtime(tmp_path, monkeypatch, fixture)
    fixture.now += timedelta(minutes=16)
    assert third.worker.run_once() is None
    assert third.repository.get_source_subscription(source.source_id).enabled is False
    third.product.update_source(source.source_id, enabled=True)
    assert third.worker.run_once().state is SourceRunState.COMPLETED
    assert len(fixture.calls) == 2


def test_background_enrollment_is_once_and_has_no_model_work(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    youtube = _load_module("test_youtube_following")
    assert composition.repository.list_videos() == ()
    fixture.tick()
    fixture.publish(youtube.NEW)
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(composition.repository.list_videos()) == 1
    assert composition.repository.get_verified_timed_transcript(video_id=youtube.NEW) is not None
    assert composition.repository.current_local_summary_pointer(youtube.NEW) is not None
    fixture.tick()
    assert composition.worker.run_once().state is SourceRunState.COMPLETED
    assert len(composition.repository.list_videos()) == 1
    with composition.repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM distillation_execution_checkpoints").fetchone()[0] == 0
    assert composition.application._source_tracking.projection(source.source_id)["update_count"] == 1


def test_idle_wait_is_a_deadline_and_paused_sources_have_no_wakeup(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    assert composition.worker.scheduler.wait_seconds() == 300
    composition.product.update_source(source.source_id, enabled=False)
    assert composition.worker.scheduler.wait_seconds() is None
    assert composition.worker.run_once() is None


def test_restored_authority_replaces_all_pre_restore_scheduling(tmp_path, monkeypatch):
    composition, fixture, source = setup_runtime(tmp_path, monkeypatch)
    composition.product.update_source(source.source_id, enabled=False)
    backup = composition.backup_restore.create_backup()
    saved = composition.application._source_tracking.projection(source.source_id)
    composition.product.update_source(source.source_id, enabled=True)
    fixture.now += timedelta(minutes=16)
    archive = composition.backup_restore.backup_download(backup.backup_id)[0].read_bytes()
    staged = composition.backup_restore.stage_restore(archive)
    composition.backup_restore.confirm_restore(staged.restore_id)
    assert composition.worker.run_once() is None
    assert composition.repository.list_source_runs() == ()
    composition.worker.stop()
    restored, fixture, source = setup_runtime(tmp_path, monkeypatch, fixture)
    assert restored.worker.run_once() is None
    assert restored.repository.get_source_subscription(source.source_id).enabled is False
    assert restored.application._source_tracking.projection(source.source_id) == saved
    assert restored.backup_restore.readiness()["ready"] is True
